"""SQLAlchemy model for template data loads."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class LoadModel(Base):
    """Database representation of a data import performed against a template."""

    __tablename__ = "loads"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(40), nullable=False, default="Procesando")
    file_name = Column(String(100), nullable=False)
    total_rows = Column(Integer, nullable=False, default=0)
    error_rows = Column(Integer, nullable=False, default=0)
    report_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    template = relationship("TemplateModel", lazy="joined")
    user = relationship("UserModel", lazy="joined")


__all__ = ["LoadModel"]
