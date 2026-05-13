"""One-shot data migration from the legacy Piccolo DB to the calliope2 schema.

**Read-only against the legacy DB.** This module issues only ``SELECT`` against
the legacy engine; never ``INSERT``/``UPDATE``/``DELETE``/``ALTER``. In
production, configure the legacy DB user with read-only grants as defense in
depth.

**Idempotent.** Repeated runs do not duplicate rows:
- ``Image``/``Video``: dedupe by ``gcs_uri`` (GCS paths are unique per blob).
- ``Story``/``StoryFrame``: a marker is written to ``metadata->>'legacy_id'``;
  pre-existing rows with that marker are skipped.
- ``User``: keyed by ``firebase_uid``; sparrows are mapped to
  ``f"{user_prefix}{sparrow_id}"`` unless an explicit override is provided via
  ``sparrow_map``.
- ``Bookmark``: dedupe by ``(owner_id, story_id, frame_id, list_name)``.

**Dry-run.** ``dry_run=True`` reads everything, builds the would-write maps,
returns counts, and writes nothing.

GCS URIs are reused verbatim — no blob copy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from calliope2.db.models import Bookmark, Image, Story, StoryFrame, User, Video
from calliope2.migration.legacy_schema import (
    LegacyBookmarkList,
    LegacyImage,
    LegacySparrowState,
    LegacyStory,
    LegacyStoryBookmark,
    LegacyStoryFrame,
    LegacyStoryFrameBookmark,
    LegacyVideo,
)
from calliope2.migration.stats import MigrationStats

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def migrate_all(
    legacy_engine: AsyncEngine,
    new_sessionmaker: async_sessionmaker[AsyncSession],
    *,
    dry_run: bool = False,
    limit: int | None = None,
    sparrow_map: Mapping[str, str] | None = None,
    user_prefix: str = "legacy:",
) -> MigrationStats:
    """Migrate sparrows/users → images → videos → stories → frames → bookmarks.

    Each phase reads from ``legacy_engine`` (SELECT only) and writes via
    ``new_sessionmaker``. Phases must run in order — frames depend on stories,
    bookmarks on frames + stories.
    """
    stats = MigrationStats()
    sparrow_map = dict(sparrow_map or {})

    async with new_sessionmaker() as new_session:
        # One scan up front gives us idempotency keys without per-row queries.
        user_by_firebase_uid = await _existing_users(new_session)
        image_by_url = await _existing_by_url(new_session, Image)
        video_by_url = await _existing_by_url(new_session, Video)
        story_by_legacy_id = await _existing_by_legacy_metadata_id(new_session, Story)
        frame_by_legacy_id = await _existing_by_legacy_metadata_id(new_session, StoryFrame)
        bookmark_keys = await _existing_bookmark_keys(new_session)

    async with legacy_engine.connect() as legacy:
        sparrows = (await legacy.execute(select(LegacySparrowState))).mappings().all()
        legacy_sparrow_pk_to_user_id: dict[int, int] = {}
        legacy_sparrow_pk_to_sparrow_id: dict[int, str] = {}

        for sp in sparrows:
            legacy_sparrow_pk_to_sparrow_id[sp["id"]] = sp["sparrow_id"]
            firebase_uid = sparrow_map.get(
                sp["sparrow_id"], f"{user_prefix}{sp['sparrow_id']}"
            )
            existing = user_by_firebase_uid.get(firebase_uid)
            if existing is not None:
                legacy_sparrow_pk_to_user_id[sp["id"]] = existing
                stats.users_skipped_existing += 1
                continue
            if dry_run:
                # Use a sentinel so downstream phases see this sparrow as "mapped";
                # actual user_id is irrelevant since dry-run writes nothing.
                legacy_sparrow_pk_to_user_id[sp["id"]] = -1
                stats.users_created += 1
                continue
            async with new_sessionmaker() as s:
                user = User(firebase_uid=firebase_uid, display_name=sp["sparrow_id"])
                s.add(user)
                await s.commit()
                await s.refresh(user)
                user_by_firebase_uid[firebase_uid] = user.id
                legacy_sparrow_pk_to_user_id[sp["id"]] = user.id
                stats.users_created += 1

        # ----- Images -----
        legacy_image_id_to_new_id: dict[int, int] = {}
        images = (await legacy.execute(select(LegacyImage))).mappings().all()
        for img in images:
            existing = image_by_url.get(img["url"])
            if existing is not None:
                legacy_image_id_to_new_id[img["id"]] = existing
                stats.images_skipped_existing += 1
                continue
            if dry_run:
                legacy_image_id_to_new_id[img["id"]] = -1
                stats.images_created += 1
                continue
            async with new_sessionmaker() as s:
                row = Image(
                    gcs_uri=img["url"],
                    width=img["width"],
                    height=img["height"],
                    format=img["format"],
                )
                s.add(row)
                await s.commit()
                await s.refresh(row)
                image_by_url[img["url"]] = row.id
                legacy_image_id_to_new_id[img["id"]] = row.id
                stats.images_created += 1

        # ----- Videos -----
        legacy_video_id_to_new_id: dict[int, int] = {}
        videos = (await legacy.execute(select(LegacyVideo))).mappings().all()
        for vid in videos:
            existing = video_by_url.get(vid["url"])
            if existing is not None:
                legacy_video_id_to_new_id[vid["id"]] = existing
                stats.videos_skipped_existing += 1
                continue
            if dry_run:
                legacy_video_id_to_new_id[vid["id"]] = -1
                stats.videos_created += 1
                continue
            async with new_sessionmaker() as s:
                row = Video(
                    gcs_uri=vid["url"],
                    width=vid["width"],
                    height=vid["height"],
                    format=vid["format"],
                    duration_seconds=vid["duration_seconds"],
                    frame_rate=vid["frame_rate"],
                )
                s.add(row)
                await s.commit()
                await s.refresh(row)
                video_by_url[vid["url"]] = row.id
                legacy_video_id_to_new_id[vid["id"]] = row.id
                stats.videos_created += 1

        # ----- Stories -----
        legacy_story_id_to_new_id: dict[int, int] = {}
        story_stmt = select(LegacyStory)
        if limit is not None:
            story_stmt = story_stmt.limit(limit)
        stories = (await legacy.execute(story_stmt)).mappings().all()
        for st in stories:
            if st["id"] in story_by_legacy_id:
                legacy_story_id_to_new_id[st["id"]] = story_by_legacy_id[st["id"]]
                stats.stories_skipped_existing += 1
                continue
            sparrow_pk = _resolve_owner_pk(st["created_for_sparrow_id"], sparrows)
            owner_user_id = legacy_sparrow_pk_to_user_id.get(sparrow_pk) if sparrow_pk else None
            if owner_user_id is None and not dry_run:
                stats.stories_skipped_no_owner += 1
                continue
            if dry_run:
                if owner_user_id is None:
                    stats.stories_skipped_no_owner += 1
                else:
                    legacy_story_id_to_new_id[st["id"]] = -1  # sentinel, see users phase
                    stats.stories_created += 1
                continue
            async with new_sessionmaker() as s:
                new_story = Story(
                    owner_id=owner_user_id,
                    slug=st["slug"] or st["cuid"],
                    title=st["title"],
                    thumbnail_image_id=legacy_image_id_to_new_id.get(st["thumbnail_image"])
                    if st["thumbnail_image"]
                    else None,
                    storyteller_name=st["strategy_name"],
                    metadata_={
                        "legacy_id": st["id"],
                        "legacy_cuid": st["cuid"],
                        "state_props": st["state_props"],
                    },
                    created_at=st["date_created"],
                    updated_at=st["date_updated"],
                )
                s.add(new_story)
                await s.commit()
                await s.refresh(new_story)
                legacy_story_id_to_new_id[st["id"]] = new_story.id
                story_by_legacy_id[st["id"]] = new_story.id
                stats.stories_created += 1

        # ----- Frames -----
        frame_stmt = select(LegacyStoryFrame)
        frames = (await legacy.execute(frame_stmt)).mappings().all()
        for fr in frames:
            if fr["id"] in frame_by_legacy_id:
                stats.frames_skipped_existing += 1
                continue
            new_story_id = legacy_story_id_to_new_id.get(fr["story"])
            if new_story_id is None:
                stats.frames_skipped_orphan_story += 1
                continue
            if dry_run:
                frame_by_legacy_id[fr["id"]] = -1
                stats.frames_created += 1
                continue
            async with new_sessionmaker() as s:
                frame = StoryFrame(
                    story_id=new_story_id,
                    number=fr["number"] or 0,
                    text=fr["text"],
                    image_id=legacy_image_id_to_new_id.get(fr["image"]) if fr["image"] else None,
                    video_id=legacy_video_id_to_new_id.get(fr["video"]) if fr["video"] else None,
                    source_image_id=(
                        legacy_image_id_to_new_id.get(fr["source_image"])
                        if fr["source_image"]
                        else None
                    ),
                    min_duration_seconds=(
                        float(fr["min_duration_seconds"])
                        if fr["min_duration_seconds"] is not None
                        else None
                    ),
                    metadata_={
                        "legacy_id": fr["id"],
                        "legacy_metadata": fr["metadata"],
                        "trigger_condition": fr["trigger_condition"],
                    },
                    created_at=fr["date_created"],
                )
                s.add(frame)
                await s.commit()
                await s.refresh(frame)
                frame_by_legacy_id[fr["id"]] = frame.id
                stats.frames_created += 1

        # ----- Bookmarks -----
        bookmark_lists = (
            await legacy.execute(select(LegacyBookmarkList))
        ).mappings().all()
        bookmark_list_meta = {bl["id"]: bl for bl in bookmark_lists}

        story_bookmarks = (
            await legacy.execute(select(LegacyStoryBookmark))
        ).mappings().all()
        for bm in story_bookmarks:
            new_story_id = legacy_story_id_to_new_id.get(bm["story"])
            owner_user_id = legacy_sparrow_pk_to_user_id.get(bm["sparrow"])
            if new_story_id is None or owner_user_id is None:
                stats.bookmarks_skipped_orphan += 1
                continue
            blist = bookmark_list_meta.get(bm["list"])
            list_name = blist["name"] if blist else None
            is_public = bool(blist["is_public"]) if blist else False
            key = (owner_user_id, new_story_id, None, list_name)
            if key in bookmark_keys:
                stats.bookmarks_skipped_existing += 1
                continue
            if dry_run:
                stats.bookmarks_created += 1
                continue
            async with new_sessionmaker() as s:
                s.add(
                    Bookmark(
                        owner_id=owner_user_id,
                        story_id=new_story_id,
                        list_name=list_name,
                        comments=bm["comments"],
                        is_public=is_public,
                        created_at=bm["date_created"],
                    )
                )
                await s.commit()
                bookmark_keys.add(key)
                stats.bookmarks_created += 1

        frame_bookmarks = (
            await legacy.execute(select(LegacyStoryFrameBookmark))
        ).mappings().all()
        for fb in frame_bookmarks:
            new_frame_id = frame_by_legacy_id.get(fb["frame"])
            owner_user_id = legacy_sparrow_pk_to_user_id.get(fb["sparrow"])
            # Look up the parent story for this frame
            frame_row = next((f for f in frames if f["id"] == fb["frame"]), None)
            new_story_id = (
                legacy_story_id_to_new_id.get(frame_row["story"]) if frame_row else None
            )
            if new_frame_id is None or owner_user_id is None or new_story_id is None:
                stats.bookmarks_skipped_orphan += 1
                continue
            key = (owner_user_id, new_story_id, new_frame_id, None)
            if key in bookmark_keys:
                stats.bookmarks_skipped_existing += 1
                continue
            if dry_run:
                stats.bookmarks_created += 1
                continue
            async with new_sessionmaker() as s:
                s.add(
                    Bookmark(
                        owner_id=owner_user_id,
                        story_id=new_story_id,
                        frame_id=new_frame_id,
                        comments=fb["comments"],
                        is_public=False,
                        created_at=fb["date_created"],
                    )
                )
                await s.commit()
                bookmark_keys.add(key)
                stats.bookmarks_created += 1

    return stats


# ----- Helpers -----


def _resolve_owner_pk(
    created_for_sparrow_id: str | None, sparrows: list[Mapping]
) -> int | None:
    """Map the legacy ``Story.created_for_sparrow_id`` (a string) to the sparrowstate PK."""
    if not created_for_sparrow_id:
        return None
    for sp in sparrows:
        if sp["sparrow_id"] == created_for_sparrow_id:
            return sp["id"]
    return None


async def _existing_users(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(User.id, User.firebase_uid))
    return {fb_uid: id_ for id_, fb_uid in rows}


async def _existing_by_url(session: AsyncSession, model) -> dict[str, int]:
    rows = await session.execute(select(model.id, model.gcs_uri))
    return {uri: id_ for id_, uri in rows}


async def _existing_by_legacy_metadata_id(session: AsyncSession, model) -> dict[int, int]:
    rows = await session.execute(select(model.id, model.metadata_))
    out: dict[int, int] = {}
    for id_, meta in rows:
        if isinstance(meta, dict) and "legacy_id" in meta:
            out[int(meta["legacy_id"])] = id_
    return out


async def _existing_bookmark_keys(
    session: AsyncSession,
) -> set[tuple[int, int, int | None, str | None]]:
    rows = await session.execute(
        select(Bookmark.owner_id, Bookmark.story_id, Bookmark.frame_id, Bookmark.list_name)
    )
    return {tuple(row) for row in rows}
