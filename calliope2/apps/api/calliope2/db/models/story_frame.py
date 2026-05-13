from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from calliope2.db.base import Base

EMBEDDING_DIM = 1536


class StoryFrame(Base):
    __tablename__ = "story_frames"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    image_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("images.id", ondelete="SET NULL")
    )
    video_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="SET NULL")
    )
    source_image_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("images.id", ondelete="SET NULL")
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    min_duration_seconds: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    story: Mapped["Story"] = relationship(back_populates="frames", lazy="noload")  # type: ignore[name-defined]
    image: Mapped["Image | None"] = relationship(foreign_keys=[image_id], lazy="noload")  # type: ignore[name-defined]
    video: Mapped["Video | None"] = relationship(foreign_keys=[video_id], lazy="noload")  # type: ignore[name-defined]
    source_image: Mapped["Image | None"] = relationship(foreign_keys=[source_image_id], lazy="noload")  # type: ignore[name-defined]
