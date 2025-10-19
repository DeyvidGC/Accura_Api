"""Persistence layer for user data."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.models import UserModel


class UserRepository:
    """Provide CRUD operations for user entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int = 0, limit: int = 100) -> Sequence[User]:
        query = self.session.query(UserModel).offset(skip).limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def get(self, user_id: int) -> User | None:
        model = self.session.query(UserModel).filter(UserModel.id == user_id).first()
        if not model:
            return None
        return self._to_entity(model)

    def get_by_email(self, email: str) -> User | None:
        model = self.session.query(UserModel).filter(UserModel.email == email).first()
        if not model:
            return None
        return self._to_entity(model)

    def create(self, user: User) -> User:
        model = UserModel(
            name=user.name,
            alias=user.alias,
            email=user.email,
            password=user.password,
            must_change_password=user.must_change_password,
            last_login=user.last_login,
            created_by=user.created_by,
            updated_by=user.updated_by,
            is_active=user.is_active,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def update(self, user: User) -> User:
        model = self.session.query(UserModel).filter(UserModel.id == user.id).first()
        if not model:
            msg = f"User with id {user.id} not found"
            raise ValueError(msg)

        model.name = user.name
        model.alias = user.alias
        model.email = user.email
        model.password = user.password
        model.must_change_password = user.must_change_password
        model.last_login = user.last_login
        model.updated_by = user.updated_by
        model.is_active = user.is_active

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def delete(self, user_id: int) -> None:
        model = self.session.query(UserModel).filter(UserModel.id == user_id).first()
        if not model:
            msg = f"User with id {user_id} not found"
            raise ValueError(msg)

        self.session.delete(model)
        self.session.commit()

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            alias=model.alias,
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
