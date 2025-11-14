"""SQLAlchemy model for user access to templates."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base
from app.utils import now_in_app_timezone


class TemplateUserAccessModel(Base):
    """Database representation of template access assignments."""

    __tablename__ = "template_user_access"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("template.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date = Column(
        DateTime(timezone=True), nullable=False, default=now_in_app_timezone
    )
    end_date = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey("user.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=now_in_app_timezone
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=True, onupdate=now_in_app_timezone
    )

    template = relationship(
        "TemplateModel",
        back_populates="access_records",
        lazy="joined",
    )
    user = relationship(
        "UserModel",
        back_populates="template_accesses",
        foreign_keys=[user_id],
        lazy="joined",
    )
    revoked_by_user = relationship(
        "UserModel",
        foreign_keys=[revoked_by],
        lazy="joined",
    )


__all__ = ["TemplateUserAccessModel"]
