"""Persistence layer for user data."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session, joinedload

from app.domain.entities import Role, User
from app.infrastructure.models import RoleModel, UserModel


class UserRepository:
    """Provide CRUD operations for user entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int = 0, limit: int = 100) -> Sequence[User]:
        query = (
            self.session.query(UserModel)
            .options(joinedload(UserModel.role))
            .offset(skip)
            .limit(limit)
        )
        return [self._to_entity(model) for model in query.all()]

    def list_by_creator(self, creator_id: int) -> Sequence[User]:
        query = (
            self.session.query(UserModel)
            .options(joinedload(UserModel.role))
            .filter(UserModel.created_by == creator_id)
        )
        return [self._to_entity(model) for model in query.all()]

    def get(self, user_id: int) -> User | None:
        model = self._get_model(id=user_id)
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self._get_model(email=email)
        return self._to_entity(model) if model else None

    def create(self, user: User) -> User:
        model = UserModel()
        self._apply_entity_to_model(model, user, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if model.role is None:
            self.session.refresh(model, attribute_names=["role"])
        return self._to_entity(model)

    def update(self, user: User) -> User:
        model = self._get_model(id=user.id)
        if not model:
            msg = f"User with id {user.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, user, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if model.role is None:
            self.session.refresh(model, attribute_names=["role"])
        return self._to_entity(model)

    def delete(self, user_id: int) -> None:
        model = self._get_model(id=user_id)
        if not model:
            msg = f"User with id {user_id} not found"
            raise ValueError(msg)

        self.session.delete(model)
        self.session.commit()

    def list_ids_by_role_alias(self, alias: str) -> list[int]:
        query = (
            self.session.query(UserModel.id)
            .join(RoleModel, UserModel.role_id == RoleModel.id)
            .filter(RoleModel.alias.ilike(alias))
        )
        return [user_id for (user_id,) in query.all()]

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            role=UserRepository._role_to_entity(model.role),
            name=model.name,
            email=model.email,
            password=model.password,
            must_change_password=model.must_change_password,
            last_login=model.last_login,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
            is_active=model.is_active,
        )

    def _get_model(self, **filters) -> UserModel | None:
        query = self.session.query(UserModel).options(joinedload(UserModel.role))
        return query.filter_by(**filters).first()

    @staticmethod
    def _apply_entity_to_model(
        model: UserModel, user: User, *, include_creation_fields: bool
    ) -> None:
        if include_creation_fields:
            model.created_by = user.created_by
            model.created_at = user.created_at
        model.role_id = user.role.id
        model.name = user.name
        model.email = user.email
        model.password = user.password
        model.must_change_password = user.must_change_password
        model.last_login = user.last_login
        if not include_creation_fields:
            model.updated_by = user.updated_by
            model.updated_at = user.updated_at
        model.is_active = user.is_active

    @staticmethod
    def _role_to_entity(model_role) -> Role:
        if model_role is None:
            msg = "User role is not set"
            raise ValueError(msg)
        return Role(id=model_role.id, name=model_role.name, alias=model_role.alias)
