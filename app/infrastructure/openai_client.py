"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import inspect
import json
import os
from typing import Any

from openai import OpenAI, OpenAIError
try:  # pragma: no cover - compat import for older SDKs
    from openai.resources.responses import Responses  # type: ignore
except Exception:  # pragma: no cover - keep runtime dependency optional
    Responses = None  # type: ignore[misc, assignment]
from app.config import get_settings

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

    def generate_structured_response(self, user_message: str) -> dict[str, Any]:
        """
        Envía un mensaje y devuelve JSON validado por el modelo, usando JSON Schema estricto.
        """
        json_schema_definition = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "user_needs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "response_guidance": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "allowed_topics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "tone": {"type": "string"},
                        "formatting": {"type": "string"},
                        "helpful_phrases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        },
                    },
                    "required": ["allowed_topics", "tone", "formatting"],
                },
                "suggested_reply": {"type": "string"},
                "follow_up_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
            "required": [
                "summary",
                "user_needs",
                "response_guidance",
                "suggested_reply",
            ],
        }

        system_prompt = (
            "Eres un asistente que responde ÚNICAMENTE con JSON válido según el schema dado. "
            "No incluyas texto fuera del JSON."
        )

        instruction = (
            "Analiza el mensaje del usuario y responde con un JSON que cumpla EXACTAMENTE con las "
            "siguientes claves: summary, user_needs, response_guidance, suggested_reply y, opcional, "
            "follow_up_questions. Describe lo que necesita el usuario y cómo debe responder el asistente."
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
            {"role": "user", "content": [{"type": "input_text", "text": user_message}]},
        ]

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

        # Ya que usamos response_format estricto, debería ser JSON “limpio”
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            # Fallback defensivo por si el proveedor devuelve code fences (raro con strict)
            s = text.strip()
            if s.startswith("```"):
                # quita fences tipo ```json ... ```
                s = s.strip("`")
                s = s[s.find("{"): s.rfind("}") + 1]
                payload = json.loads(s)
            else:
                raise OpenAIServiceError("La respuesta de OpenAI no es un JSON válido.") from exc

        # Validaciones extra (por si cambias el schema arriba en el futuro)
        if "summary" not in payload or not isinstance(payload["summary"], str):
            raise OpenAIServiceError("La respuesta de OpenAI no contiene 'summary' válido.")

        if "suggested_reply" not in payload or not isinstance(payload["suggested_reply"], str):
            raise OpenAIServiceError("La respuesta de OpenAI no contiene 'suggested_reply' válido.")

        user_needs = payload.get("user_needs")
        if not isinstance(user_needs, list) or not all(isinstance(x, str) for x in user_needs):
            raise OpenAIServiceError("'user_needs' debe ser una lista de cadenas.")

        follow_up = payload.setdefault("follow_up_questions", [])
        if not isinstance(follow_up, list) or not all(isinstance(x, str) for x in follow_up):
            raise OpenAIServiceError("'follow_up_questions' debe ser una lista de cadenas.")

        guidance = payload.get("response_guidance")
        if not isinstance(guidance, dict):
            raise OpenAIServiceError("'response_guidance' debe ser un objeto JSON.")

        for key in ("allowed_topics", "tone", "formatting"):
            if key not in guidance:
                raise OpenAIServiceError(f"'response_guidance' debe incluir '{key}'.")

        allowed_topics = guidance.get("allowed_topics")
        if not isinstance(allowed_topics, list) or not all(isinstance(x, str) for x in allowed_topics):
            raise OpenAIServiceError("'allowed_topics' debe ser una lista de cadenas.")
        if not allowed_topics:
            raise OpenAIServiceError("'allowed_topics' debe contener al menos un elemento.")

        for key in ("tone", "formatting"):
            if not isinstance(guidance.get(key), str):
                raise OpenAIServiceError(f"'{key}' debe ser una cadena dentro de 'response_guidance'.")

        helpful = guidance.setdefault("helpful_phrases", [])
        if not isinstance(helpful, list) or not all(isinstance(x, str) for x in helpful):
            raise OpenAIServiceError("'helpful_phrases' debe ser una lista de cadenas.")

        return payload
