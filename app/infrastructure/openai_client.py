"""Cliente sencillo para probar la conexión con la API de OpenAI."""

from __future__ import annotations

import json
import os
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
        """
        Envía un mensaje y devuelve JSON validado por el modelo, usando JSON Schema estricto.
        """
        # OJO: mantengo tus claves exactas, incluso "regla generales"
        json_schema_definition = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "Nombre columna": {"type": "string"},
                "Tipo de dato": {"type": "string"},
                "Campo obligatorio": {"type": "boolean"},
                "regla generales": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "valor mínimo": {"type": ["number", "null"]},
                            "valor máximo": {"type": ["number", "null"]}
                        },
                        "required": ["valor mínimo", "valor máximo"]
                    }
                }
            },
            "required": ["Nombre columna", "Tipo de dato", "Campo obligatorio", "regla generales"]
        }

        system_prompt = (
            "Eres un asistente que responde ÚNICAMENTE con JSON válido según el schema dado. "
            "No incluyas texto fuera del JSON."
        )

        instruction = (
            "Genera el objeto JSON solicitado con las siguientes claves EXACTAS:\n"
            '"Nombre columna", "Tipo de dato", "Campo obligatorio", "regla generales" '
            "(con 'valor mínimo' y 'valor máximo' en cada regla)."
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
            resp = self._client.responses.create(
                model=self._model,
                input=messages,
                response_format=response_format,
                # Opcionales útiles:
                # temperature=0,  # para mayor determinismo
                # max_output_tokens=256,
            )
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
        required_keys = {
            "Nombre columna": str,
            "Tipo de dato": str,
            "Campo obligatorio": bool,
            "regla generales": list,
        }
        for k, t in required_keys.items():
            if k not in payload or not isinstance(payload[k], t):
                raise OpenAIServiceError(f"La respuesta de OpenAI no contiene '{k}' con el tipo esperado.")

        if not payload["regla generales"]:
            raise OpenAIServiceError("La respuesta de OpenAI debe incluir al menos una regla general.")

        for regla in payload["regla generales"]:
            if not isinstance(regla, dict):
                raise OpenAIServiceError("Cada elemento de 'regla generales' debe ser un objeto JSON.")
            for bk in ("valor mínimo", "valor máximo"):
                if bk not in regla:
                    raise OpenAIServiceError("Las reglas deben incluir 'valor mínimo' y 'valor máximo'.")

        return payload
