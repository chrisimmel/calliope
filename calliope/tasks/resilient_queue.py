"""
A task queue wrapper that degrades gracefully to in-process execution.

In production we use Google Cloud Tasks. If Cloud Tasks is unreachable or
misconfigured (e.g. the Cloud Tasks API is disabled, the queue doesn't exist,
or IAM permissions are missing), enqueueing would otherwise raise and surface
to the user as a 500 when creating a story or requesting a frame.

ResilientTaskQueue wraps a primary queue and, on enqueue failure, falls back to
running the task in-process via a LocalTaskQueue. This keeps story/frame
generation working (without the durability, retries, or distribution of Cloud
Tasks) instead of failing the request outright.
"""

import logging
from typing import Any, Dict, List, Optional

from .queue import TaskQueue

logger = logging.getLogger(__name__)


class ResilientTaskQueue(TaskQueue):
    """Delegates to a primary queue, falling back to in-process execution."""

    def __init__(self, primary: TaskQueue):
        self.primary = primary
        # The in-process fallback is created lazily on first failure so we don't
        # pay its setup cost (or register handlers) unless we actually need it.
        self._fallback: Optional[TaskQueue] = None

    def _get_fallback(self) -> TaskQueue:
        if self._fallback is None:
            # Imported here to avoid import cycles (handlers import the queue).
            from .handlers import register_handlers
            from .local_queue import LocalTaskQueue

            fallback = LocalTaskQueue()
            register_handlers(fallback)
            self._fallback = fallback
            logger.warning(
                "Initialized in-process LocalTaskQueue fallback. Tasks will run "
                "in-process with no durability, retries, or distribution until "
                "the primary task queue is healthy again."
            )
        return self._fallback

    async def enqueue(
        self, task_type: str, payload: Dict[str, Any], delay_seconds: int = 0
    ) -> str:
        try:
            return await self.primary.enqueue(task_type, payload, delay_seconds)
        except Exception as e:
            logger.exception(
                f"Primary task queue failed to enqueue task '{task_type}'; "
                f"falling back to in-process execution: {e!s}"
            )
            return await self._get_fallback().enqueue(task_type, payload, delay_seconds)

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        result = await self.primary.get_task_status(task_id)
        if result is None and self._fallback is not None:
            return await self._fallback.get_task_status(task_id)
        return result

    async def list_tasks(self, story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Both the primary (GCP) and the fallback record task state in Firebase,
        # so the primary's view already reflects fallback-run tasks. Merge defensively.
        results = await self.primary.list_tasks(story_id)
        if self._fallback is not None:
            seen = {t.get("task_id") for t in results}
            for task in await self._fallback.list_tasks(story_id):
                if task.get("task_id") not in seen:
                    results.append(task)
        return results
