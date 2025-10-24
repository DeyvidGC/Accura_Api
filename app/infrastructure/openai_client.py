"""Utilities for interacting with the OpenAI API."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from app.config import get_settings


class OpenAIConfigurationError(RuntimeError):
    """Raised when the OpenAI client is misconfigured."""


class OpenAIServiceError(RuntimeError):
    """Raised when the OpenAI service returns an unexpected response."""


class StructuredChatService:
    """Service responsible for producing structured assistant replies."""

    def __init__(self, client: OpenAI | None = None) -> None:
        self._client: OpenAI | None = client
        self._model: str | None = None
        self._is_configured = False
        self._configure_from_settings()

    def _configure_from_settings(self) -> None:
        """Load OpenAI settings and lazily initialize the SDK client."""

        if self._is_configured:
            return

        settings = get_settings()
        if not settings.openai_api_key and self._client is None:
            raise OpenAIConfigurationError(
                "La clave de API de OpenAI no está configurada. Define OPENAI_API_KEY en las variables de entorno.",
            )

        if self._client is None:
            client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
            sanitized_base_url = self._sanitize_base_url(settings.openai_base_url)
            if sanitized_base_url:
                client_kwargs["base_url"] = sanitized_base_url

            self._client = OpenAI(**client_kwargs)

        self._model = settings.openai_model
        self._is_configured = True

    @staticmethod
    def _sanitize_base_url(raw_base_url: str | None) -> str | None:
        """Normalize optional base URL values provided via configuration."""

        if not raw_base_url:
            return None

        base_url = raw_base_url.strip().rstrip("/")
        if not base_url:
            return None

        if base_url.endswith("/responses"):
            base_url = base_url[: -len("/responses")].rstrip("/")

        # Avoid redundantly setting the official API base when matching defaults.
        if base_url in {"https://api.openai.com", "https://api.openai.com/v1"}:
            return None

        return base_url

    def _get_client(self) -> OpenAI:
        """Return an initialized OpenAI client instance."""

        self._configure_from_settings()
        if self._client is None:  # pragma: no cover - defensive guard
            raise OpenAIConfigurationError(
                "No se pudo inicializar el cliente de OpenAI. Verifica la configuración proporcionada.",
            )
        return self._client

    def generate_structured_response(self, user_message: str) -> dict[str, Any]:
        """Return a structured JSON response for the given user message."""

        system_prompt = (
            "Eres un asistente que analiza la solicitud del usuario y responde únicamente con JSON. "
            "El JSON debe describir lo que el usuario necesita y cómo debe responder el asistente."
        )

        text_config = {
            "format": {
                "type": "json_schema",
                "name": "structured_assistant_reply",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Resumen breve en español de la petición del usuario.",
                        },
                        "user_needs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de elementos concretos que el usuario solicita o espera.",
                            "minItems": 1,
                        },
                        "response_guidance": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "allowed_topics": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Temas que el asistente puede abordar en su respuesta.",
                                    "minItems": 1,
                                },
                                "tone": {
                                    "type": "string",
                                    "description": "Indicaciones sobre el tono apropiado de la respuesta.",
                                },
                                "formatting": {
                                    "type": "string",
                                    "description": "Formato o estructura sugerida para responder (por ejemplo, viñetas, pasos, etc.).",
                                },
                                "helpful_phrases": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Frases concretas que podrían ser útiles en la respuesta.",
                                },
                            },
                            "required": ["allowed_topics", "tone", "formatting"],
                        },
                        "suggested_reply": {
                            "type": "string",
                            "description": "Propuesta de respuesta redactada que siga las indicaciones dadas.",
                        },
                        "follow_up_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Preguntas adicionales que ayudarían a completar la asistencia.",
                        },
                    },
                    "required": [
                        "summary",
                        "user_needs",
                        "response_guidance",
                        "suggested_reply",
                    ],
                },
            },
        }

        client = self._get_client()
        model = self._model
        if model is None:  # pragma: no cover - defensive guard
            raise OpenAIConfigurationError(
                "No se pudo determinar el modelo de OpenAI configurado.",
            )

        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": user_message}],
                    },
                ],
                text=text_config,
            )
        except OpenAIError as exc:  # pragma: no cover - depends on external service
            raise OpenAIServiceError("No se pudo generar la respuesta usando OpenAI.") from exc

        raw_text = getattr(response, "output_text", None)
        if not raw_text:
            try:
                first_output = response.output[0]
                content_block = first_output.content[0]
                raw_text = getattr(content_block, "text", None)
            except (AttributeError, IndexError, TypeError) as exc:  # pragma: no cover
                raise OpenAIServiceError("La respuesta de OpenAI no contiene texto utilizable.") from exc

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OpenAIServiceError("La respuesta de OpenAI no es un JSON válido.") from exc

        return payload
