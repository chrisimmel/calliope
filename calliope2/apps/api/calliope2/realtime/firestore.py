"""Firestore-backed task writer + the ``get_task_writer`` factory.

Settings drive resolution: if ``firebase_project_id`` is empty (the default in
local dev), ``get_task_writer`` returns a ``LoggingTaskWriter`` instead. Any
Firestore I/O exception is caught and logged — the writer never propagates
errors into the calling task, since Firestore is a status mailbox and the
work itself is durable in Postgres.

Tests override ``get_task_writer`` via ``app.dependency_overrides`` or
``monkeypatch`` to capture writes.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from calliope2.realtime.task_status import TaskRecord, TaskStatus
from calliope2.realtime.writer import LoggingTaskWriter, TaskWriter
from calliope2.settings import get_settings

if TYPE_CHECKING:
    from google.cloud.firestore import AsyncClient

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "tasks"


class FirestoreTaskWriter:
    """Writes task status updates to ``tasks/{task_id}`` in Firestore.

    Errors are caught and logged rather than raised — the caller (a background
    task generating story frames) shouldn't fail because the status mailbox
    is unreachable.
    """

    def __init__(self, client: AsyncClient, collection: str = DEFAULT_COLLECTION) -> None:
        self._client = client
        self._collection = collection

    def _doc(self, task_id: str):
        return self._client.collection(self._collection).document(task_id)

    async def started(self, task: TaskRecord) -> None:
        payload = {
            "user_id": task.user_id,
            "story_id": task.story_id,
            "type": task.type.value,
            "status": TaskStatus.RUNNING.value,
            "progress": task.progress,
            "started_at": task.started_at,
        }
        await self._safe_write("set", task.task_id, lambda: self._doc(task.task_id).set(payload))

    async def progress(self, task_id: str, progress: float) -> None:
        await self._safe_write(
            "update", task_id,
            lambda: self._doc(task_id).update(
                {"status": TaskStatus.RUNNING.value, "progress": progress}
            ),
        )

    async def completed(self, task_id: str) -> None:
        await self._safe_write(
            "update", task_id,
            lambda: self._doc(task_id).update(
                {
                    "status": TaskStatus.COMPLETED.value,
                    "progress": 1.0,
                    "completed_at": datetime.now(UTC),
                }
            ),
        )

    async def failed(self, task_id: str, error: str) -> None:
        await self._safe_write(
            "update", task_id,
            lambda: self._doc(task_id).update(
                {
                    "status": TaskStatus.FAILED.value,
                    "error": error,
                    "completed_at": datetime.now(UTC),
                }
            ),
        )

    async def _safe_write(self, op: str, task_id: str, do_write) -> None:
        try:
            await do_write()
        except Exception:
            logger.exception("firestore %s on tasks/%s failed", op, task_id)


@lru_cache(maxsize=1)
def get_task_writer() -> TaskWriter:
    """Return the configured TaskWriter — Firestore in prod, logging in dev."""
    settings = get_settings()
    if not settings.firebase_project_id:
        return LoggingTaskWriter()
    from google.cloud.firestore import AsyncClient  # imported lazily; needs GCP creds

    client = AsyncClient(project=settings.firebase_project_id)
    return FirestoreTaskWriter(client)


def reset_task_writer_cache() -> None:
    """Test hook — drop the cached writer so the next call re-resolves."""
    get_task_writer.cache_clear()
