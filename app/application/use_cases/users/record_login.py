"""Use case for registering the last login of a user."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.models import UserModel


def record_login(session: Session, user_id: int) -> None:
    """Persist the last login timestamp for the given user."""

    model = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not model:
        return

    model.last_login = datetime.utcnow()
    session.add(model)
    session.commit()
