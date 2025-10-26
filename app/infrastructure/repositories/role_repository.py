"""Persistence layer for roles data."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import Role
from app.infrastructure.models import RoleModel


class RoleRepository:
    """Provide read access to roles stored in the database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, role_id: int) -> Role | None:
        model = self.session.query(RoleModel).filter_by(id=role_id).first()
        return self._to_entity(model) if model else None

    def get_by_alias(self, alias: str) -> Role | None:
        model = (
            self.session.query(RoleModel)
            .filter(func.lower(RoleModel.alias) == alias.lower())
            .first()
        )
        return self._to_entity(model) if model else None

    def list_aliases(self) -> set[str]:
        """Return the set of role aliases stored in the database."""

        aliases = self.session.query(RoleModel.alias).all()
        return {alias.lower() for (alias,) in aliases}

    @staticmethod
    def _to_entity(model: RoleModel) -> Role:
        return Role(id=model.id, name=model.name, alias=model.alias)


__all__ = ["RoleRepository"]
