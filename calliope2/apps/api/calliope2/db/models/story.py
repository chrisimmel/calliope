from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from calliope2.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str | None] = mapped_column(String(256), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    thumbnail_image_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("images.id", ondelete="SET NULL")
    )
    strategy_name: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="stories", lazy="noload")  # type: ignore[name-defined]
    thumbnail_image: Mapped["Image | None"] = relationship(foreign_keys=[thumbnail_image_id], lazy="noload")  # type: ignore[name-defined]
    frames: Mapped[list["StoryFrame"]] = relationship(  # type: ignore[name-defined]
        back_populates="story", order_by="StoryFrame.number", lazy="noload"
    )
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="story", lazy="noload")  # type: ignore[name-defined]
