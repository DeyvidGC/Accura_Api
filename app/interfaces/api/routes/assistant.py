"""Rutas para interactuar con el asistente basado en OpenAI."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.rules import list_recent_rules as list_recent_rules_uc
from app.domain.entities import Rule, User
from app.infrastructure.database import get_db
from app.infrastructure.openai_client import (
    OffTopicMessageError,
    OpenAIServiceError,
    StructuredChatService,
)
from app.interfaces.api.dependencies import (
    get_structured_chat_service,
    require_admin,
)
from app.interfaces.api.schemas import (
    AssistantMessageRequest,
    AssistantMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

_DEPENDENCY_TYPE_ALIASES: dict[str, str] = {
    "texto": "Texto",
    "numero": "Número",
    "documento": "Documento",
    "lista": "Lista",
    "lista compleja": "Lista compleja",
    "telefono": "Telefono",
    "correo": "Correo",
    "fecha": "Fecha",
}


def _normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    collapsed = re.sub(r"[\s\-_]+", " ", ascii_text)
    return collapsed.lower().strip()


def _iter_rule_definitions(rule_payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(rule_payload, Mapping):
        return [rule_payload]
    if isinstance(rule_payload, Sequence) and not isinstance(rule_payload, (str, bytes)):
        definitions: list[Mapping[str, Any]] = []
        for entry in rule_payload:
            definitions.extend(_iter_rule_definitions(entry))
        return definitions
    return []


def _build_rule_summary(rule_id: int, definition: Mapping[str, Any], type_label: str) -> dict[str, Any]:
    summary: dict[str, Any] = {"id": rule_id, "Tipo de dato": type_label}
    for key in (
        "Nombre de la regla",
        "Campo obligatorio",
        "Mensaje de error",
        "Descripción",
        "Ejemplo",
        "Header",
    ):
        if key in definition:
            summary[key] = deepcopy(definition[key])
    if "Regla" in definition:
        summary["Regla"] = deepcopy(definition["Regla"])
    return summary


def _extract_dependency_variants(definition: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rule_block = definition.get("Regla")
    if not isinstance(rule_block, Mapping):
        return []
    specifics = rule_block.get("reglas especifica")
    if not isinstance(specifics, Sequence):
        return []

    variants: list[tuple[str, dict[str, Any]]] = []
    for entry in specifics:
        if not isinstance(entry, Mapping):
            continue
        dependency_context = {
            key: deepcopy(value)
            for key, value in entry.items()
            if isinstance(key, str) and _normalize_label(key) not in _DEPENDENCY_TYPE_ALIASES
        }
        for key, value in entry.items():
            if not isinstance(key, str):
                continue
            canonical_type = _DEPENDENCY_TYPE_ALIASES.get(_normalize_label(key))
            if canonical_type is None or not isinstance(value, Mapping):
                continue
            payload: dict[str, Any] = {"Regla": deepcopy(value)}
            if dependency_context:
                payload["Dependencia"] = dependency_context
            variants.append((canonical_type, payload))
    return variants


def _build_rules_catalog(rules: Sequence[Rule]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for rule in rules:
        for definition in _iter_rule_definitions(rule.rule):
            if not isinstance(definition, Mapping):
                continue
            type_label = definition.get("Tipo de dato")
            if not isinstance(type_label, str):
                continue

            summary = _build_rule_summary(rule.id, definition, type_label)
            grouped[type_label].append(summary)

            if _normalize_label(type_label) == "dependencia":
                for subtype, payload in _extract_dependency_variants(definition):
                    variant_summary = _build_rule_summary(rule.id, definition, subtype)
                    variant_summary["Regla"] = payload["Regla"]
                    if "Dependencia" in payload:
                        variant_summary["Dependencia"] = payload["Dependencia"]
                    variant_summary["Tipo de dato original"] = type_label
                    grouped[subtype].append(variant_summary)

    catalog = [
        {"Tipo de dato": type_label, "Reglas": entries}
        for type_label, entries in sorted(grouped.items(), key=lambda item: item[0])
    ]
    return catalog


@router.post("/analyze", response_model=AssistantMessageResponse)
def analyze_message(
    payload: AssistantMessageRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    assistant: StructuredChatService = Depends(get_structured_chat_service),
) -> AssistantMessageResponse:
    """Genera una respuesta estructurada que indica cómo atender el mensaje del usuario."""

    try:
        recent_rules = list_recent_rules_uc(db, limit=5)
        serialized_rules = _build_rules_catalog(recent_rules)
        raw_response = assistant.generate_structured_response(
            payload.message,
            recent_rules=serialized_rules or None,
        )
        logger.debug("Respuesta sin validar del asistente: %s", raw_response)
    except OffTopicMessageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OpenAIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        if hasattr(AssistantMessageResponse, "model_validate"):
            return AssistantMessageResponse.model_validate(raw_response)
        return AssistantMessageResponse.parse_obj(raw_response)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive against schema drift
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="La respuesta recibida no coincide con el esquema esperado.",
        ) from exc
