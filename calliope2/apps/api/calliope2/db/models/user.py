from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from calliope2.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    stories: Mapped[list["Story"]] = relationship(back_populates="owner", lazy="noload")  # type: ignore[name-defined]
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="owner", lazy="noload")  # type: ignore[name-defined]
