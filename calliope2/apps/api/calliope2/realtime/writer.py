"""TaskWriter Protocol + a logging fallback used when Firestore is unconfigured.

The realtime writer is best-effort: Firestore is a status mailbox, not source
of truth, so write failures are logged but never raised. This matches the
plan's "Postgres remains source of truth for content; Firestore is a status
mailbox" framing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from calliope2.realtime.task_status import TaskRecord

logger = logging.getLogger(__name__)


@runtime_checkable
class TaskWriter(Protocol):
    async def started(self, task: TaskRecord) -> None: ...
    async def progress(self, task_id: str, progress: float) -> None: ...
    async def completed(self, task_id: str) -> None: ...
    async def failed(self, task_id: str, error: str) -> None: ...


class LoggingTaskWriter:
    """No-op writer used in local dev when no Firebase project is configured."""

    async def started(self, task: TaskRecord) -> None:
        logger.info("task started: %s (story=%s, type=%s)", task.task_id, task.story_id, task.type)

    async def progress(self, task_id: str, progress: float) -> None:
        logger.info("task %s: progress %.0f%%", task_id, progress * 100)

    async def completed(self, task_id: str) -> None:
        logger.info("task %s: complete", task_id)

    async def failed(self, task_id: str, error: str) -> None:
        logger.warning("task %s: failed — %s", task_id, error)
