"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

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
        self._model = model

    def generate_structured_response(self, user_message: str) -> dict[str, Any]:
        """Envía un mensaje de prueba y devuelve el JSON generado por el modelo."""

        instruction = (
            "Responde ÚNICAMENTE con JSON válido usando esta estructura exacta: "
            "{\n"
            '  "summary": string en español,\n'
            '  "user_needs": lista de strings,\n'
            '  "response_guidance": {\n'
            '    "allowed_topics": lista de strings,\n'
            '    "tone": string,\n'
            '    "formatting": string,\n'
            '    "helpful_phrases": lista de strings\n'
            "  },\n"
            '  "suggested_reply": string,\n'
            '  "follow_up_questions": lista de strings\n'
            "}\n"
            "No agregues texto adicional fuera del JSON."
        )

        prompt = f"{instruction}\n\nUsuario: {user_message}"

        try:
            response = self._client.responses.create(
                model=self._model,
                input=prompt,
            )
        except OpenAIError as exc:
            raise OpenAIServiceError("No se pudo realizar la solicitud a OpenAI.") from exc

        text = getattr(response, "output_text", None)
        if not text:
            try:
                text = response.output[0].content[0].text
            except (AttributeError, IndexError, TypeError) as exc:
                raise OpenAIServiceError(
                    "La respuesta de OpenAI no contiene texto utilizable.",
                ) from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenAIServiceError("La respuesta de OpenAI no es un JSON válido.") from exc
