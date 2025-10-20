"""SQLAlchemy model for the user table."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.infrastructure.database import Base


class UserModel(Base):
    """Database representation of the system user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    alias = Column(String(50), nullable=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    last_login = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_active = Column(Boolean, nullable=False, default=True)

    def touch_last_login(self) -> None:
        """Update the last login timestamp to now."""

        self.last_login = datetime.utcnow()
