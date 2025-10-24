"""Routes for managing validation rules."""

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
    _: User = Depends(require_admin),
) -> RuleRead:
    """Create a new validation rule."""

    try:
        rule = create_rule_uc(db, name=rule_in.name, rule=rule_in.rule)
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
    """Return a paginated list of validation rules."""

    rules = list_rules_uc(db, skip=skip, limit=limit)
    return [_to_read_model(rule) for rule in rules]


@router.get("/{rule_id}", response_model=RuleRead)
def read_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> RuleRead:
    """Return the rule identified by ``rule_id``."""

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
    _: User = Depends(require_admin),
) -> RuleRead:
    """Update an existing validation rule."""

    if hasattr(rule_in, "model_dump"):
        update_data = rule_in.model_dump(exclude_unset=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        update_data = rule_in.dict(exclude_unset=True)

    name = update_data.get("name")
    rule_body = update_data.get("rule")

    try:
        rule = update_rule_uc(
            db,
            rule_id=rule_id,
            name=name,
            rule=rule_body,
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
    """Delete a validation rule."""

    try:
        delete_rule_uc(db, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
