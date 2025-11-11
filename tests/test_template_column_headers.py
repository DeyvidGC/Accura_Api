import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app.application.use_cases.template_columns.validators import (
    ensure_rule_header_dependencies,
)
from app.domain.entities import Rule, TemplateColumn, TemplateColumnRule


class _StubRuleRepository:
    def __init__(self, rules):
        self._rules = {rule.id: rule for rule in rules}

    def get(self, rule_id):
        return self._rules.get(rule_id)


def _build_dependency_rule(rule_id: int = 2) -> Rule:
    payload = {
        "Nombre de la regla": "Validación de longitud de documento según tipo de documento en InsurTech",
        "Tipo de dato": "Dependencia",
        "Header": ["Tipo Documento", "Longitud minima", "Longitud maxima"],
        "Header rule": ["Tipo Documento", "Documento"],
        "Regla": {
            "reglas especifica": [
                {
                    "Documento": {"Longitud minima": 8, "Longitud maxima": 8},
                    "Tipo Documento": "DNI",
                },
                {
                    "Documento": {"Longitud minima": 11, "Longitud maxima": 11},
                    "Tipo Documento": "RUC",
                },
            ]
        },
    }

    return Rule(
        id=rule_id,
        rule=payload,
        created_by=None,
        created_at=None,
        updated_by=None,
        updated_at=None,
        is_active=True,
        deleted=False,
        deleted_by=None,
        deleted_at=None,
    )


def _build_column(
    *,
    column_id: int,
    name: str,
    rule_id: int,
    header: str | None,
) -> TemplateColumn:
    headers = (header,) if header is not None else None
    return TemplateColumn(
        id=column_id,
        template_id=1,
        rules=(TemplateColumnRule(id=rule_id, headers=headers),),
        name=name,
        description=None,
        data_type="Dependencia",
        created_by=None,
        created_at=None,
        updated_by=None,
        updated_at=None,
        is_active=True,
        deleted=False,
        deleted_by=None,
        deleted_at=None,
    )


def test_dependency_rule_accepts_distributed_headers_across_columns():
    rule = _build_dependency_rule()
    repository = _StubRuleRepository([rule])

    columns = (
        _build_column(column_id=1, name="Tipo_Documento", rule_id=rule.id, header="Tipo Documento"),
        _build_column(column_id=2, name="Documento", rule_id=rule.id, header="Documento"),
    )

    ensure_rule_header_dependencies(columns=columns, rule_repository=repository)


def test_dependency_rule_requires_unique_header_assignments():
    rule = _build_dependency_rule()
    repository = _StubRuleRepository([rule])

    columns = (
        _build_column(column_id=1, name="Tipo_Documento", rule_id=rule.id, header="Tipo Documento"),
        _build_column(column_id=2, name="Documento", rule_id=rule.id, header="Tipo Documento"),
    )

    with pytest.raises(ValueError) as exc:
        ensure_rule_header_dependencies(columns=columns, rule_repository=repository)

    assert "ya fue asignado" in str(exc.value)


def test_dependency_rule_requires_all_headers_to_be_assigned():
    rule = _build_dependency_rule()
    repository = _StubRuleRepository([rule])

    columns = (
        _build_column(column_id=1, name="Tipo_Documento", rule_id=rule.id, header="Tipo Documento"),
        _build_column(column_id=2, name="Documento", rule_id=rule.id, header=None),
    )

    with pytest.raises(ValueError) as exc:
        ensure_rule_header_dependencies(columns=columns, rule_repository=repository)

    assert "debe definir headers" in str(exc.value)

