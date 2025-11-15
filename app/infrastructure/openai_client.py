"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import inspect
import json
import logging
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Callable

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
    "correo",
    "email",
    "telefono",
    "fecha",
)

_SIMPLE_RULE_HEADERS: dict[str, tuple[str, ...]] = {
    "Texto": ("Longitud mínima", "Longitud máxima"),
    "Número": ("Valor mínimo", "Valor máximo", "Número de decimales"),
    "Documento": ("Longitud mínima", "Longitud máxima"),
    "Lista": ("Lista",),
    "Teléfono": ("Longitud mínima", "Código de país"),
    "Correo": ("Formato", "Longitud máxima"),
    "Fecha": ("Formato", "Fecha mínima", "Fecha máxima"),
}

_DEPENDENCY_TYPE_ALIASES: set[str] = {
    "texto",
    "numero",
    "documento",
    "lista",
    "lista compleja",
    "telefono",
    "correo",
    "fecha",
}

_DEPENDENCY_SPECIFICS_KEYS: set[str] = {
    "reglas especifica",
    "reglas especificas",
    "reglas especificacion",
    "configuracion",
    "configuraciones",
    "detalles",
    "detalle",
    "opciones",
    "dependencia",
    "dependiendo"
}

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


def _extract_composite_header_fields(rule_config: Any) -> list[str]:
    """Derive header labels from the combinations defined in a complex list rule."""

    if not isinstance(rule_config, Mapping):
        return []

    candidate_keys = ("Lista compleja", "Lista", "Listas", "Combinaciones")
    collected: list[str] = []
    seen: set[str] = set()

    for key in candidate_keys:
        entries = rule_config.get(key)
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
            continue

        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            for field_name in entry.keys():
                if not isinstance(field_name, str):
                    continue
                candidate = field_name.strip()
                if not candidate:
                    continue
                normalized = _normalize_for_matching(candidate)
                if normalized in seen:
                    continue
                seen.add(normalized)
                collected.append(candidate)

        if collected:
            break

    return collected


def _deduplicate_headers(headers: Sequence[str]) -> list[str]:
    """Return the headers keeping the first occurrence of each label."""

    seen: set[str] = set()
    ordered: list[str] = []
    for entry in headers:
        if not isinstance(entry, str):
            continue
        candidate = entry.strip()
        if not candidate:
            continue
        normalized = _normalize_for_matching(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(candidate)
    return ordered


def _extract_header_entries(raw_headers: Any) -> list[str]:
    """Return a normalized list of header labels from arbitrary payloads."""

    if isinstance(raw_headers, str):
        candidate = raw_headers.strip()
        return [candidate] if candidate else []
    if isinstance(raw_headers, Sequence) and not isinstance(raw_headers, (str, bytes)):
        return [
            entry.strip()
            for entry in raw_headers
            if isinstance(entry, str) and entry.strip()
        ]
    return []


def _iter_dependency_specifics(rule_config: Any) -> list[Mapping[str, Any]]:
    """Return the specific dependency configurations defined in a rule."""

    if not isinstance(rule_config, Mapping):
        return []

    specifics: Sequence[Any] | None = None

    direct_specifics = rule_config.get("reglas especifica")
    if isinstance(direct_specifics, Sequence) and not isinstance(
        direct_specifics, (str, bytes)
    ):
        specifics = direct_specifics

    if specifics is None:
        for key, value in rule_config.items():
            if not isinstance(key, str):
                continue
            normalized_key = _normalize_for_matching(key)
            if normalized_key not in _DEPENDENCY_SPECIFICS_KEYS:
                continue
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                specifics = value
                break

    if specifics is None:
        for value in rule_config.values():
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                continue
            if any(isinstance(item, Mapping) for item in value):
                specifics = value
                break

    if specifics is None:
        return []

    return [entry for entry in specifics if isinstance(entry, Mapping)]


def _is_leaf_value(value: Any) -> bool:
    """Return True when the provided value represents a leaf node."""

    if isinstance(value, Mapping):
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if not value:
            return True
        return not any(
            isinstance(entry, Mapping)
            or (
                isinstance(entry, Sequence)
                and not isinstance(entry, (str, bytes))
            )
            for entry in value
        )
    return True


def _collect_leaf_labels(value: Any, add_label: Callable[[str], None]) -> None:
    """Collect leaf labels from the provided dependency configuration."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                _collect_leaf_labels(nested, add_label)
                continue

            candidate = key.strip()
            if not candidate:
                _collect_leaf_labels(nested, add_label)
                continue

            if _is_leaf_value(nested):
                add_label(candidate)
            else:
                _collect_leaf_labels(nested, add_label)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for entry in value:
            _collect_leaf_labels(entry, add_label)


def _extract_dependency_leaf_labels(rule_block: Any) -> list[str]:
    """Return the leaf labels that exist in the dependency specifics block."""

    if isinstance(rule_block, Sequence) and not isinstance(rule_block, (str, bytes)):
        collected: list[str] = []
        seen: set[str] = set()
        for entry in rule_block:
            nested_labels = _extract_dependency_leaf_labels(entry)
            for label in nested_labels:
                normalized = _normalize_for_matching(label)
                if normalized in seen:
                    continue
                seen.add(normalized)
                collected.append(label)
        return collected

    specifics = _iter_dependency_specifics(rule_block)
    if not specifics:
        return []

    seen: set[str] = set()
    ordered: list[str] = []

    def add_label(label: str) -> None:
        if not isinstance(label, str):
            return
        candidate = label.strip()
        if not candidate:
            return
        normalized = _normalize_for_matching(candidate)
        if normalized in seen:
            return
        seen.add(normalized)
        ordered.append(candidate)

    _collect_leaf_labels(specifics, add_label)

    return ordered


def _extract_dependency_header_fields(rule_config: Any) -> list[str]:
    """Infer header combinations for dependency rules."""

    specifics = _iter_dependency_specifics(rule_config)
    if not specifics:
        return []

    dependent_label: str | None = None
    header_candidates: list[str] = []
    seen_normalized: set[str] = set()

    for entry in specifics:
        for key, value in entry.items():
            if not isinstance(key, str):
                continue
            normalized_key = _normalize_for_matching(key)
            stripped_key = key.strip()
            if not stripped_key:
                continue
            if normalized_key in _DEPENDENCY_TYPE_ALIASES:
                if normalized_key not in seen_normalized:
                    header_candidates.append(stripped_key)
                    seen_normalized.add(normalized_key)
                continue
            if dependent_label is None:
                dependent_label = stripped_key
                seen_normalized.add(normalized_key)
            elif _normalize_for_matching(dependent_label) == normalized_key:
                continue

    if dependent_label:
        normalized_required = {
            _normalize_for_matching(item) for item in header_candidates
        }
        dependent_normalized = _normalize_for_matching(dependent_label)
        if dependent_normalized not in normalized_required:
            header_candidates.insert(0, dependent_label)
        elif header_candidates and _normalize_for_matching(header_candidates[0]) != dependent_normalized:
            header_candidates.insert(0, dependent_label)

    return header_candidates


def _infer_dependency_headers(payload: Mapping[str, Any]) -> list[str]:
    """Infer detailed headers for dependency rules including specific constraints."""

    rule_block = payload.get("Regla")
    if not isinstance(rule_block, Mapping):
        return []

    return _extract_dependency_leaf_labels(rule_block)


def _infer_header_rule(payload: Mapping[str, Any]) -> list[str]:
    """Infer the header rule labels based on the rule definition."""

    rule_type = payload.get("Tipo de dato")
    if not isinstance(rule_type, str):
        return []

    normalized_type = _normalize_for_matching(rule_type)
    rule_block = payload.get("Regla")
    if not isinstance(rule_block, Mapping):
        return []

    if normalized_type in {"lista compleja", "lista completa"}:
        return _deduplicate_headers(
            _extract_composite_header_fields(rule_block)
        )

    if normalized_type == "dependencia":
        return _deduplicate_headers(
            _extract_dependency_header_fields(rule_block)
        )

    if normalized_type == "validacion conjunta":
        return _deduplicate_headers(
            _extract_header_entries(rule_block.get("Nombre de campos"))
        )

    if normalized_type == "duplicados":
        for candidate_key in ("Campos", "Columnas", "Fields", "fields"):
            headers = _extract_header_entries(rule_block.get(candidate_key))
            if headers:
                return _deduplicate_headers(headers)
        return []

    return []


def _is_relevant_message(message: str) -> bool:
    """Check if the incoming message references validation rule concepts."""

    normalized = _normalize_for_matching(message)
    if any(keyword in normalized for keyword in _RELEVANT_KEYWORDS):
        return True
    return _looks_like_validation_constraint(normalized)


def _looks_like_validation_constraint(normalized_message: str) -> bool:
    """Identify free-form requests that still describe validation constraints."""

    constraint_markers = (
        "longitud",
        "caracter",
        "caracteres",
        "digito",
        "digitos",
        "maximo",
        "maxima",
        "minimo",
        "minima",
        "formato",
        "obligatorio",
        "permitidos",
        "rango",
    )
    domain_markers = (
        "campo",
        "columna",
        "cliente",
        "nombre",
        "poliza",
        "documento",
        "numero",
        "codigo",
        "identificador",
        "correo",
        "email",
        "telefono",
        "asegur",
        "riesgo",
        "cobertura",
    )

    has_constraint = any(marker in normalized_message for marker in constraint_markers)
    if not has_constraint:
        return False

    has_domain = any(marker in normalized_message for marker in domain_markers)
    has_numeric_detail = any(ch.isdigit() for ch in normalized_message)
    return has_domain or has_numeric_detail


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
            "En 'Header' incluye únicamente las propiedades configurables de la regla "
            "(por ejemplo: 'Tipo de documento', 'Longitud mínima', 'Longitud máxima') "
            "recorriendo las claves finales (hojas) definidas dentro de 'reglas especifica'. "
            "No agregues etiquetas que no existan literalmente como claves finales dentro de ese bloque. "
            "En 'Header rule' registra primero la propiedad condicionante y luego la propiedad dependiente "
            "(por ejemplo: 'Tipo de documento', 'Número de documento'). "
            "Dentro de 'Regla', cada elemento de 'reglas especifica' debe definir el valor del campo condicionante y, "
            "además, incluir objetos separados por cada tipo aplicable (Texto, Número, Documento, Lista, Lista compleja, "
            "Teléfono, Correo o Fecha) usando exactamente los nombres del esquema y solo las restricciones relevantes. "
            "Si el mensaje del usuario no especifica algún valor requerido, dedúcelo o propón uno coherente "
            "con las prácticas y terminología del sector asegurador, manteniendo consistencia con casos de uso reales "
            "de validación de datos en InsurTech (por ejemplo: verificación de formatos de pólizas, número de documento, "
            "fechas de vigencia, montos asegurados, o nombres de aseguradoras). "
            "Nunca uses textos genéricos como 'N/A', 'Por definir' ni dejes campos vacíos. "
            "En el campo 'Ejemplo' entrega un caso detallado que describa valores de entrada válido e inválido lo más realista posible, "
            "limitado a un ejemplo de cada tipo."
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
            "Header rule",
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
            "Teléfono",
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

        header_entries = _deduplicate_headers(
            _extract_header_entries(payload.get("Header"))
        )

        expected_header_list: list[str] | None = None

        if tipo == "Lista compleja":
            derived_header = _extract_composite_header_fields(payload.get("Regla"))
            if derived_header:
                header_entries = derived_header

        if tipo == "Dependencia":
            inferred_header = _infer_dependency_headers(payload)
            if inferred_header:
                header_entries = inferred_header

        expected_simple_headers = _SIMPLE_RULE_HEADERS.get(tipo)
        if expected_simple_headers is not None:
            normalized_header = [
                _normalize_for_matching(item) for item in header_entries
            ]
            expected_list = list(expected_simple_headers)
            normalized_expected = [_normalize_for_matching(item) for item in expected_list]
            if normalized_header != normalized_expected:
                logger.debug(
                    "Normalizando header para el tipo '%s': recibido=%s, esperado=%s",
                    tipo,
                    header_entries,
                    expected_list,
                )
                header_entries = expected_list
            expected_header_list = expected_list

        if not header_entries:
            raise OpenAIServiceError(
                "'Header' debe contener al menos una etiqueta válida derivada de la regla."
            )

        payload["Header"] = header_entries

        header_rule_entries = payload.get("Header rule")
        if isinstance(header_rule_entries, list):
            header_rule_entries = _deduplicate_headers(header_rule_entries)
        else:
            header_rule_entries = []

        if not header_rule_entries:
            header_rule_entries = _infer_header_rule(payload)

        if not header_rule_entries and expected_header_list is not None:
            header_rule_entries = list(expected_header_list)

        if not header_rule_entries:
            header_rule_entries = _deduplicate_headers(header_entries)

        if not header_rule_entries:
            raise OpenAIServiceError(
                "'Header rule' debe ser una lista con al menos un elemento."
            )

        payload["Header rule"] = header_rule_entries

        if not isinstance(payload.get("Regla"), dict):
            raise OpenAIServiceError("'Regla' debe ser un objeto JSON.")

        return payload
