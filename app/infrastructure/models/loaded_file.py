"""SQLAlchemy model storing generated reports for loads."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class LoadedFileModel(Base):
    """Database representation of a generated report associated with a load."""

    __tablename__ = "loaded_file"

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(
        Integer,
        ForeignKey("load.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    path = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    num_load = Column(Integer, nullable=False)
    created_user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    load = relationship("LoadModel", lazy="joined")
    created_user = relationship("UserModel", lazy="joined")


__all__ = ["LoadedFileModel"]
