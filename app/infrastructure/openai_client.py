"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import inspect
import json
import logging
import unicodedata
from collections.abc import Sequence
from typing import Any

from openai import OpenAI, OpenAIError
try:  # pragma: no cover - compat import for older SDKs
    from openai.resources.responses import Responses  # type: ignore
except Exception:  # pragma: no cover - keep runtime dependency optional
    Responses = None  # type: ignore[misc, assignment]
from app.config import get_settings
from app.schemas import load_regla_de_campo_schema


logger = logging.getLogger(__name__)

_RELEVANT_KEYWORDS: tuple[str, ...] = (
    "regla",
    "reglas",
    "validacion",
    "validación",
    "validar",
    "campo",
    "columna",
    "plantilla",
    "header",
    "lista",
    "rango",
    "formato",
    "dependencia",
    "error",
    "rule",
    "validation",
    "dataset",
    "schema",
)

_LARGE_MESSAGE_THRESHOLD = 1800


def _is_broad_catalog_request(message: str) -> bool:
    """Detect requests that ask for exhaustive catalog listings."""

    normalized = _normalize_for_matching(message)
    broad_markers = (
        "lista de todos",
        "listado de todos",
        "todos los",
        "todas las",
        "catalogo completo",
        "catalogo de todos",
    )
    if not any(marker in normalized for marker in broad_markers):
        return False

    catalog_keywords = (
        "departamento",
        "provincia",
        "distrito",
        "pais",
        "regla",
        "reglas",
        "campos",
        "plantilla",
        "catalogo",
    )
    return any(keyword in normalized for keyword in catalog_keywords)


def _normalize_for_matching(text: str) -> str:
    """Return a lowercase, accent-free version of the text."""

    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _is_relevant_message(message: str) -> bool:
    """Check if the incoming message references validation rule concepts."""

    normalized = _normalize_for_matching(message)
    return any(keyword in normalized for keyword in _RELEVANT_KEYWORDS)


def _build_off_topic_error(user_message: str) -> str:
    """Return a concise error message for off-topic prompts."""

    snippet = user_message.strip()
    if len(snippet) > 120:
        snippet = snippet[:117].rstrip() + "..."

    return (
        "El mensaje recibido no describe una regla de validación. "
        "Por favor indica el campo, los límites o el formato que deseas validar para continuar. "
        f"Mensaje detectado: \"{snippet}\"."
    )


def _should_retry(error: Exception, user_message: str) -> bool:
    """Determine if the OpenAI call should be retried with a constrained prompt."""

    if len(user_message) > _LARGE_MESSAGE_THRESHOLD:
        return True

    message = str(error)
    retry_markers = (
        "no es un JSON válido",
        "no coincide con el esquema",
        "no contiene el campo obligatorio",
        "no contiene texto utilizable",
    )
    return any(marker in message for marker in retry_markers)


def _truncate_message(message: str, limit: int = 2000) -> tuple[str, bool]:
    """Trim the message to the provided limit, returning the trimmed text and a flag."""

    if len(message) <= limit:
        return message, False
    return message[:limit], True


def _strip_code_fences(text: str) -> str:
    """Return JSON text without Markdown code fences."""

    s = text.strip()
    if not s.startswith("```"):
        return text

    # remove the opening fences and keep only the JSON payload between the
    # first "{" and the matching closing "}".
    cleaned = s.strip("`")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return text
    return cleaned[start : end + 1]


def _remove_trailing_commas(text: str) -> str:
    """Remove trailing commas that break strict JSON decoding."""

    # This is a very small sanitiser aimed at fixing answers such as
    # "{ \"foo\": 1, }" or "[1, 2, ]" that occasionally appear in LLM
    # outputs.  The regex is conservative and only removes a comma when the
    # next non-whitespace character closes the object/array.
    import re

    return re.sub(r",(\s*[}\]])", r"\1", text)

class OpenAIConfigurationError(RuntimeError):
    """Error lanzado cuando faltan datos básicos de configuración."""


class OpenAIServiceError(RuntimeError):
    """Error lanzado cuando la API de OpenAI no responde como se espera."""


class OffTopicMessageError(OpenAIServiceError):
    """Error lanzado cuando el mensaje no está relacionado con reglas de validación."""


class StructuredChatService:
    """Servicio muy simple para verificar la conexión con OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()

        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY no está definido en las variables de entorno.",
            )

        base_url = (settings.openai_base_url or "").strip()
        model = (settings.openai_model or "gpt-4.1-mini").strip() or "gpt-4.1-mini"
        temperature = float(settings.openai_temperature)
        max_output_tokens = settings.openai_max_output_tokens
        if isinstance(max_output_tokens, str):  # defensive: settings may coerce str
            max_output_tokens = int(max_output_tokens)
        if max_output_tokens is not None and max_output_tokens <= 0:
            max_output_tokens = None

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)
        responses_client = getattr(self._client, "responses", None)
        if responses_client is None and Responses is not None:
            # Algunas versiones antiguas del SDK no inicializan automáticamente
            # el cliente de Responses. Creamos la instancia manualmente para
            # mantener compatibilidad con openai>=1.0.<X>.
            responses_client = Responses(self._client)

        if responses_client is None:
            raise OpenAIConfigurationError(
                "La librería 'openai' instalada no expone la API 'responses'. "
                "Actualiza a la versión 1.3.0 o superior.",
            )

        self._responses = responses_client
        self._supports_response_format = False
        try:  # pragma: no cover - defensive for exotic SDKs
            params = inspect.signature(self._responses.create).parameters
            self._supports_response_format = "response_format" in params
        except (TypeError, ValueError):
            # Algunos SDK personalizados pueden no exponer la firma completa.
            # En ese caso asumimos que no soportan response_format.
            self._supports_response_format = False
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    def generate_structured_response(
        self,
        user_message: str,
        *,
        recent_rules: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Envía un mensaje y devuelve JSON validado por el modelo, usando JSON Schema estricto.
        """
        json_schema_definition = load_regla_de_campo_schema()

        if not _is_relevant_message(user_message):
            message = _build_off_topic_error(user_message)
            raise OffTopicMessageError(message)

        last_exception: OpenAIServiceError | None = None
        limit_mode = False
        broad_catalog_request = _is_broad_catalog_request(user_message)
        for attempt in range(2):
            try:
                return self._generate_structured_response_once(
                    user_message,
                    json_schema_definition,
                    recent_rules=recent_rules,
                    limit_mode=limit_mode,
                    broad_catalog_request=broad_catalog_request,
                )
            except OpenAIServiceError as exc:
                last_exception = exc
                if attempt == 0 and _should_retry(exc, user_message):
                    limit_mode = True
                    continue
                raise

        assert last_exception is not None  # pragma: no cover - defensive
        raise last_exception

    def _generate_structured_response_once(
        self,
        user_message: str,
        json_schema_definition: dict[str, Any],
        *,
        recent_rules: Sequence[dict[str, Any]] | None,
        limit_mode: bool,
        broad_catalog_request: bool,
    ) -> dict[str, Any]:
        system_prompt = (
            "Eres un asistente que responde ÚNICAMENTE con JSON válido según el schema dado. "
            "No incluyas texto fuera del JSON."
        )

        instruction = (
            "Analiza el mensaje del usuario y construye una definición de regla de validación para campos de "
            "formularios usados en el sector InsurTech (tecnología aplicada a seguros). "
            "Ten en cuenta que en este sector los formularios suelen incluir datos de pólizas, clientes, "
            "riesgos, coberturas, siniestros, y entidades aseguradoras. "
            "Debes responder con un JSON que cumpla EXACTAMENTE con el esquema 'Regla de Campo'. "
            "Asegúrate de definir todas las propiedades requeridas y de que 'Regla' siga las restricciones "
            "correspondientes según el tipo de dato. "
            "Cuando definas reglas del tipo 'Dependencia', omite la propiedad 'Nombre dependiente'. "
            "En 'Header' incluye siempre el campo dependiente junto a cada encabezado exigido por los tipos "
            "configurados (por ejemplo: 'Tipo Documento', 'Longitud minima', 'Longitud maxima'). "
            "Dentro de 'Regla', cada elemento de 'reglas especifica' debe repetir el campo dependiente con su "
            "valor y un objeto separado para cada tipo soportado usando los nombres exactos del esquema. "
            "Si el mensaje del usuario no especifica algún valor requerido, dedúcelo o propón uno coherente "
            "con las prácticas y terminología del sector asegurador, manteniendo consistencia con casos de uso reales "
            "de validación de datos en InsurTech (por ejemplo: verificación de formatos de pólizas, número de documento, "
            "fechas de vigencia, montos asegurados, o nombres de aseguradoras). "
            "Nunca uses textos genéricos como 'N/A', 'Por definir' ni dejes campos vacíos. "
            "En el campo 'Ejemplo' entrega un caso detallado que describa valores de entrada valido e invalido que sea los mas reales posibles."
            "Solo brindar un ejemplo de valido y otro de invalido"
        )

        message_to_use = user_message
        was_truncated = False
        if limit_mode:
            message_to_use, was_truncated = _truncate_message(user_message)
            instruction += (
                " El mensaje original era muy extenso o difícil de estructurar. "
                "Prioriza la información esencial, evita catálogos interminables y explica dentro de 'Descripción' "
                "qué datos adicionales serían necesarios si la solicitud resulta ambigua."
            )
            if was_truncated:
                instruction += (
                    " El contenido del usuario se truncó para volver a procesarlo; si detectas que faltan parámetros "
                    "clave, sugiere explícitamente los valores mínimos requeridos sin inventar catálogos completos."
                )

        if broad_catalog_request:
            instruction += (
                " Si la solicitud exige catálogos extensos (por ejemplo, todos los departamentos, provincias o "
                "reglas posibles), responde únicamente con una muestra representativa de 3 a 5 elementos y explica "
                "en 'Descripción' cómo obtener el listado completo. Nunca dejes la respuesta sin datos útiles."
            )

        if not self._supports_response_format:
            schema_text = json.dumps(json_schema_definition, ensure_ascii=False)
            instruction += (
                "\nEl SDK actual de OpenAI no soporta `response_format`, así que debes "
                "asegurarte manualmente de que la respuesta sea un JSON válido que "
                "cumpla EXACTAMENTE con este JSON Schema: "
                f"{schema_text}."
            )

        # Mensajes en formato Responses API (content blocks con input_text)
        messages = [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": instruction}]},
        ]

        if recent_rules:
            recent_rules_payload = json.dumps(recent_rules, ensure_ascii=False, indent=2)
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Estas son las reglas de validación más recientes registradas en el sistema. "
                                "Úsalas como conocimiento previo para mantener consistencia y evitar duplicados:\n"
                                f"{recent_rules_payload}"
                            ),
                        }
                    ],
                }
            )

        if was_truncated:
            message_to_use += (
                "\n\n[El mensaje original fue truncado automáticamente para facilitar el procesamiento.]"
            )

        messages.append(
            {"role": "user", "content": [{"type": "input_text", "text": message_to_use}]}
        )

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "schema_columna",
                "strict": True,  # fuerza EXACTAMENTE el JSON válido
                "schema": json_schema_definition,
            },
        }

        try:
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "input": messages,
            }
            if self._temperature is not None:
                request_kwargs["temperature"] = self._temperature
            if self._max_output_tokens is not None:
                request_kwargs["max_output_tokens"] = self._max_output_tokens
            if self._supports_response_format:
                request_kwargs["response_format"] = response_format

            resp = self._responses.create(**request_kwargs)
        except OpenAIError as exc:
            raise OpenAIServiceError("No se pudo realizar la solicitud a OpenAI.") from exc

        # Atajo estándar del SDK 1.x
        text = getattr(resp, "output_text", None)
        if not text:
            try:
                text = resp.output[0].content[0].text
            except (AttributeError, IndexError, TypeError) as exc:
                raise OpenAIServiceError("La respuesta de OpenAI no contiene texto utilizable.") from exc

        logger.debug("Respuesta sin procesar del modelo: %s", text)

        # Ya que usamos response_format estricto, debería ser JSON “limpio”. En la
        # práctica podemos recibir ligeras variaciones (code fences, comas sobrantes).
        json_text = text
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            json_text = _strip_code_fences(json_text)
            try:
                payload = json.loads(json_text)
            except json.JSONDecodeError:
                json_text = _remove_trailing_commas(json_text)
                try:
                    payload = json.loads(json_text)
                except json.JSONDecodeError as exc:
                    logger.error("No se pudo decodificar la respuesta de OpenAI: %s", json_text)
                    raise OpenAIServiceError("La respuesta de OpenAI no es un JSON válido.") from exc

        logger.debug("Respuesta del modelo convertida a JSON: %s", payload)

        # Validaciones extra (por si cambias el schema arriba en el futuro)
        required_fields = [
            "Nombre de la regla",
            "Tipo de dato",
            "Campo obligatorio",
            "Header",
            "Mensaje de error",
            "Descripción",
            "Ejemplo",
            "Regla",
        ]
        for field in required_fields:
            if field not in payload:
                raise OpenAIServiceError(f"La respuesta de OpenAI no contiene el campo obligatorio '{field}'.")

        if not isinstance(payload["Nombre de la regla"], str) or not payload["Nombre de la regla"].strip():
            raise OpenAIServiceError("'Nombre de la regla' debe ser una cadena no vacía.")

        tipo = payload.get("Tipo de dato")
        allowed_types = {
            "Texto",
            "Número",
            "Documento",
            "Lista",
            "Lista compleja",
            "Telefono",
            "Correo",
            "Fecha",
            "Dependencia",
            "Validación conjunta",
        }
        if not isinstance(tipo, str) or tipo not in allowed_types:
            raise OpenAIServiceError("'Tipo de dato' no es válido o no coincide con los valores permitidos.")

        if not isinstance(payload["Campo obligatorio"], bool):
            raise OpenAIServiceError("'Campo obligatorio' debe ser booleano.")

        for field in ("Mensaje de error", "Descripción"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise OpenAIServiceError(f"'{field}' debe ser una cadena no vacía.")

        header = payload.get("Header")
        if not isinstance(header, list) or not header:
            raise OpenAIServiceError("'Header' debe ser una lista con al menos un elemento.")
        for index, entry in enumerate(header, start=1):
            if not isinstance(entry, str) or not entry.strip():
                raise OpenAIServiceError(
                    "Cada elemento de 'Header' debe ser una cadena no vacía. "
                    f"Elemento inválido en la posición {index}."
                )

        if not isinstance(payload.get("Regla"), dict):
            raise OpenAIServiceError("'Regla' debe ser un objeto JSON.")

        return payload
