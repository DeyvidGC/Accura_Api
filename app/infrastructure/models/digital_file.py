"""SQLAlchemy model for stored digital files."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.infrastructure.database import Base
from app.utils import now_in_app_naive_datetime


class DigitalFileModel(Base):
    """Database representation of a generated template file."""

    __tablename__ = "digital_file"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("template.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    path = Column(String(255), nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=now_in_app_naive_datetime)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime(), nullable=True, onupdate=now_in_app_naive_datetime
    )


__all__ = ["DigitalFileModel"]
