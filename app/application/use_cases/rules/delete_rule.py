"""Use case for deleting validation rules."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import RuleRepository, TemplateColumnRepository


def delete_rule(session: Session, rule_id: int, *, deleted_by: int | None = None) -> None:
    """Delete the specified validation rule."""

    repository = RuleRepository(session)
    rule = repository.get(rule_id)
    if rule is None:
        raise ValueError("Regla no encontrada")

    column_repository = TemplateColumnRepository(session)
    if column_repository.is_rule_in_use(rule_id):
        raise ValueError(
            "No se puede eliminar una regla que está asignada a una columna."
        )

    repository.delete(rule_id, deleted_by=deleted_by)
