"""Rutas para administrar reglas de validación."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.rules import (
    create_rule as create_rule_uc,
    delete_rule as delete_rule_uc,
    get_rule as get_rule_uc,
    list_rules as list_rules_uc,
    update_rule as update_rule_uc,
)
from app.domain.entities import Rule, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import RuleCreate, RuleRead, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


def _to_read_model(rule: Rule) -> RuleRead:
    if hasattr(RuleRead, "model_validate"):
        return RuleRead.model_validate(rule)
    return RuleRead.from_orm(rule)


@router.post("/", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def register_rule(
    rule_in: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RuleRead:
    """Crea una nueva regla de validación."""

    try:
        rule = create_rule_uc(
            db,
            rule=rule_in.rule,
            created_by=current_user.id,
            is_active=rule_in.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_read_model(rule)


@router.get("/", response_model=list[RuleRead])
def list_rules(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[RuleRead]:
    """Devuelve una lista paginada de reglas de validación."""

    rules = list_rules_uc(db, skip=skip, limit=limit)
    return [_to_read_model(rule) for rule in rules]


@router.get("/{rule_id}", response_model=RuleRead)
def read_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> RuleRead:
    """Obtiene la regla identificada por ``rule_id``."""

    try:
        rule = get_rule_uc(db, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_read_model(rule)


@router.put("/{rule_id}", response_model=RuleRead)
def update_rule(
    rule_id: int,
    rule_in: RuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RuleRead:
    """Actualiza una regla de validación existente."""

    if hasattr(rule_in, "model_dump"):
        update_data = rule_in.model_dump(exclude_unset=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        update_data = rule_in.dict(exclude_unset=True)

    rule_body = update_data.get("rule")
    is_active = update_data.get("is_active")

    try:
        rule = update_rule_uc(
            db,
            rule_id=rule_id,
            rule=rule_body,
            is_active=is_active,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        status_code = status.HTTP_400_BAD_REQUEST
        if str(exc) == "Regla no encontrada":
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _to_read_model(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """Elimina una regla de validación."""

    try:
        delete_rule_uc(db, rule_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail == "Regla no encontrada":
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
