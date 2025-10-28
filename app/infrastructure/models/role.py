"""SQLAlchemy model for user roles."""

from sqlalchemy import Column, Integer, String

from app.infrastructure.database import Base


class RoleModel(Base):
    """Database representation of the system roles."""

    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    alias = Column(String(50), nullable=False, unique=True)


__all__ = ["RoleModel"]
