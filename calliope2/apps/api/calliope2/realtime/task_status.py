"""Task status types written to Firestore as a status mailbox.

Postgres remains the source of truth for story content; this collection is
just a place clients (Clio) can subscribe to for live progress. Schema:

  tasks/{task_id} = {
    user_id, story_id, type, status, progress,
    error?, started_at, completed_at?
  }
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(StrEnum):
    CREATE_STORY = "create_story"
    CREATE_FRAME = "create_frame"


class TaskRecord(BaseModel):
    """One row in the ``tasks/{task_id}`` collection.

    Constructed by the API layer when a background task is enqueued; the
    writer is responsible for converting to/from the Firestore document
    representation.
    """

    task_id: str
    user_id: int
    story_id: int
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
