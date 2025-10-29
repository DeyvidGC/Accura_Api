"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import inspect
import json
import logging
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
            "Si el mensaje del usuario no especifica algún valor requerido, dedúcelo o propón uno coherente "
            "con las prácticas y terminología del sector asegurador, manteniendo consistencia con casos de uso reales "
            "de validación de datos en InsurTech (por ejemplo: verificación de formatos de pólizas, número de documento, "
            "fechas de vigencia, montos asegurados, o nombres de aseguradoras). "
            "Nunca uses textos genéricos como 'N/A', 'Por definir' ni dejes campos vacíos. "
            "En el campo 'Ejemplo' entrega un caso detallado que describa valores de entrada valido e invalido que sea los mas reales posibles."
            "Solo brindar un ejemplo de valido y otro de invalido"
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

        messages.append(
            {"role": "user", "content": [{"type": "input_text", "text": user_message}]}
        )

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "schema_columna",
                "strict": True,  # fuerza EXACTAMENTE el JSON válido
                "schema": json_schema_definition
            }
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
