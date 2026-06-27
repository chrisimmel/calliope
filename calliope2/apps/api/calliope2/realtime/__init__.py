"""Realtime status mailbox: writes task progress to Firestore so clients can subscribe.

Postgres is the source of truth for story content; this collection is purely a
side-channel for live UI updates. Writes are best-effort — failures log and
return rather than propagating, since the underlying work is already durable.
"""

from calliope2.realtime.firestore import (
    FirestoreTaskWriter,
    get_task_writer,
    reset_task_writer_cache,
)
from calliope2.realtime.task_status import TaskRecord, TaskStatus, TaskType
from calliope2.realtime.writer import LoggingTaskWriter, TaskWriter

__all__ = [
    "FirestoreTaskWriter",
    "LoggingTaskWriter",
    "TaskRecord",
    "TaskStatus",
    "TaskType",
    "TaskWriter",
    "get_task_writer",
    "reset_task_writer_cache",
]
