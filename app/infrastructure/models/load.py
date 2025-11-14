"""SQLAlchemy model for template data loads."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base
from app.utils import now_in_app_naive_datetime


class LoadModel(Base):
    """Database representation of a data import performed against a template."""

    __tablename__ = "load"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("template.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(40), nullable=False, default="Procesando")
    file_name = Column(String(100), nullable=False)
    total_rows = Column(Integer, nullable=False, default=0)
    error_rows = Column(Integer, nullable=False, default=0)
    report_path = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(), nullable=False, default=now_in_app_naive_datetime
    )
    started_at = Column(DateTime(), nullable=True)
    finished_at = Column(DateTime(), nullable=True)

    template = relationship("TemplateModel", lazy="joined")
    user = relationship("UserModel", lazy="joined")


__all__ = ["LoadModel"]
