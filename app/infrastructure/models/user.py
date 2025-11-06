"""SQLAlchemy model for the user table."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.sql import expression
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base

class UserModel(Base):
    """Database representation of the system user."""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(120), nullable=False, index=True)
    password = Column(String(255), nullable=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    last_login = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)
    deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    deleted_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    role = relationship("RoleModel", lazy="joined")
    template_accesses = relationship(
        "TemplateUserAccessModel",
        back_populates="user",
        foreign_keys="TemplateUserAccessModel.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

