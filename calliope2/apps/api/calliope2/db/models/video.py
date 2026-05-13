from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from calliope2.db.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String(32))
    gcs_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    frame_rate: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
