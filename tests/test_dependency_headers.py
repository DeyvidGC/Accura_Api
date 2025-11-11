import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.openai_client import (
    _extract_dependency_header_fields,
    _infer_header_rule,
)


def _build_rule_config(overrides=None):
    base = {
        "Tipo de dato": "Dependencia",
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
    if overrides:
        base = {
            **base,
            **overrides,
        }
    return base


def test_extract_dependency_header_fields_with_default_key():
    rule = _build_rule_config()
    assert _extract_dependency_header_fields(rule["Regla"]) == [
        "Tipo Documento",
        "Documento",
    ]


def test_extract_dependency_header_fields_with_accented_key():
    rule = _build_rule_config(
        {
            "Regla": {
                "Reglas específicas": _build_rule_config()["Regla"]["reglas especifica"],
            }
        }
    )
    assert _extract_dependency_header_fields(rule["Regla"]) == [
        "Tipo Documento",
        "Documento",
    ]


def test_extract_dependency_header_fields_with_unknown_key_uses_first_sequence():
    sequence = _build_rule_config()["Regla"]["reglas especifica"]
    rule = _build_rule_config(
        {
            "Regla": {
                "Configuraciones": sequence,
            }
        }
    )
    assert _extract_dependency_header_fields(rule["Regla"]) == [
        "Tipo Documento",
        "Documento",
    ]


def test_infer_header_rule_relies_on_extracted_headers():
    payload = _build_rule_config()
    assert _infer_header_rule(payload) == [
        "Tipo Documento",
        "Documento",
    ]
