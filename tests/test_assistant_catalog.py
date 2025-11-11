import os
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///memory.db")
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("SENDGRID_API_KEY", "test")
os.environ.setdefault("SENDGRID_SENDER", "test@example.com")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_TEMPERATURE", "0")
os.environ.setdefault("OPENAI_MAX_OUTPUT_TOKENS", "1024")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("AZURE_STORAGE_CONTAINER_NAME", "test-container")

import pytest

from app.interfaces.api.routes.assistant import _build_rule_summary


def _build_dependency_definition():
    return {
        "Nombre de la regla": "Validación de longitud de número de documento según tipo de documento",
        "Tipo de dato": "Dependencia",
        "Campo obligatorio": True,
        "Mensaje de error": "La longitud del número de documento no corresponde con el tipo de documento seleccionado.",
        "Descripción": "Valida que el número de documento tenga la longitud adecuada según el tipo de documento.",
        "Ejemplo": {
            "válido": {
                "Tipo Documento": "DNI",
                "Número de Documento": "12345678",
            },
            "inválido": {
                "Tipo Documento": "RUC",
                "Número de Documento": "12345678",
            },
        },
        "Header": ["Tipo Documento", "Longitud minima", "Longitud maxima"],
        "Regla": {
            "reglas especifica": [
                {
                    "Documento": {
                        "Longitud minima": 8,
                        "Longitud maxima": 8,
                    },
                    "Tipo Documento": "DNI",
                },
                {
                    "Documento": {
                        "Longitud minima": 11,
                        "Longitud maxima": 11,
                    },
                    "Tipo Documento": "RUC",
                },
            ]
        },
    }


def test_build_rule_summary_infers_header_rule_for_dependency():
    definition = _build_dependency_definition()
    summary = _build_rule_summary(1, definition, "Dependencia")

    assert summary["Header"] == ["Tipo Documento", "Longitud minima", "Longitud maxima"]
    assert summary["Header rule"] == ["Tipo Documento", "Documento"]


def test_build_rule_summary_uses_existing_header_rule_when_present():
    definition = _build_dependency_definition()
    definition["Header rule"] = ["Tipo Documento", "Documento"]

    summary = _build_rule_summary(1, definition, "Dependencia")

    assert summary["Header rule"] == ["Tipo Documento", "Documento"]


def test_build_rule_summary_handles_composite_list_headers():
    definition = {
        "Nombre de la regla": "Validación de combinación de productos",
        "Tipo de dato": "Lista compleja",
        "Campo obligatorio": True,
        "Mensaje de error": "La combinación seleccionada no está permitida.",
        "Descripción": "Solo ciertas combinaciones de producto y canal son válidas.",
        "Ejemplo": {
            "válido": {
                "Producto": "Auto Total",
                "Canal": "Web",
            },
            "inválido": {
                "Producto": "Hogar",
                "Canal": "Telemarketing",
            },
        },
        "Regla": {
            "Lista compleja": [
                {"Producto": "Auto Total", "Canal": "Web"},
                {"Producto": "Salud", "Canal": "Presencial"},
            ]
        },
    }

    summary = _build_rule_summary(2, definition, "Lista compleja")

    assert summary["Header"] == ["Producto", "Canal"]
    assert summary["Header rule"] == ["Producto", "Canal"]


def test_build_rule_summary_omits_header_rule_when_not_available():
    definition = {
        "Nombre de la regla": "Validación de texto libre",
        "Tipo de dato": "Texto",
        "Campo obligatorio": True,
        "Mensaje de error": "Texto inválido",
        "Descripción": "Ejemplo sin header definido.",
        "Ejemplo": {},
    }

    summary = _build_rule_summary(3, definition, "Texto")

    assert "Header" not in summary
    assert "Header rule" not in summary


def test_assistant_message_response_requires_header_rule():
    from pydantic import ValidationError

    from app.interfaces.api.schemas.assistant import AssistantMessageResponse

    payload = _build_dependency_definition()
    payload["Header rule"] = ["Tipo Documento", "Documento"]

    # Remove header rule to trigger validation error
    del payload["Header rule"]

    with pytest.raises(ValidationError):
        AssistantMessageResponse.model_validate(payload)
