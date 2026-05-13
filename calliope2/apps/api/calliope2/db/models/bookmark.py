from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from calliope2.db.base import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    frame_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("story_frames.id", ondelete="SET NULL")
    )
    list_name: Mapped[str | None] = mapped_column(String(256))
    comments: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="bookmarks", lazy="noload")  # type: ignore[name-defined]
    story: Mapped["Story"] = relationship(back_populates="bookmarks", lazy="noload")  # type: ignore[name-defined]
    frame: Mapped["StoryFrame | None"] = relationship(foreign_keys=[frame_id], lazy="noload")  # type: ignore[name-defined]
