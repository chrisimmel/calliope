"""Migration counters — what got moved, what got skipped and why."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MigrationStats:
    users_created: int = 0
    users_skipped_existing: int = 0

    images_created: int = 0
    images_skipped_existing: int = 0

    videos_created: int = 0
    videos_skipped_existing: int = 0

    stories_created: int = 0
    stories_skipped_existing: int = 0
    stories_skipped_no_owner: int = 0

    frames_created: int = 0
    frames_skipped_existing: int = 0
    frames_skipped_orphan_story: int = 0

    bookmarks_created: int = 0
    bookmarks_skipped_existing: int = 0
    bookmarks_skipped_orphan: int = 0

    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"users:     created={self.users_created} skipped_existing={self.users_skipped_existing}",
            f"images:    created={self.images_created} skipped_existing={self.images_skipped_existing}",
            f"videos:    created={self.videos_created} skipped_existing={self.videos_skipped_existing}",
            (
                "stories:   "
                f"created={self.stories_created} "
                f"skipped_existing={self.stories_skipped_existing} "
                f"skipped_no_owner={self.stories_skipped_no_owner}"
            ),
            (
                "frames:    "
                f"created={self.frames_created} "
                f"skipped_existing={self.frames_skipped_existing} "
                f"skipped_orphan_story={self.frames_skipped_orphan_story}"
            ),
            (
                "bookmarks: "
                f"created={self.bookmarks_created} "
                f"skipped_existing={self.bookmarks_skipped_existing} "
                f"skipped_orphan={self.bookmarks_skipped_orphan}"
            ),
        ]
        if self.errors:
            lines.append(f"errors:    {len(self.errors)}")
        return "\n".join(lines)
