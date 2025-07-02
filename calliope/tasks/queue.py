"""
Abstract task queue interface that can be implemented for different backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable, List
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Task:
    """Represents a background task with metadata"""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        status: str = "pending",
        created_at: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.payload = payload
        self.status = status  # pending, running, completed, failed
        self.created_at = created_at or datetime.now()

    @classmethod
    def create(cls, task_type: str, payload: Dict[str, Any]) -> "Task":
        """Create a new task with a unique ID"""
        return cls(task_id=str(uuid.uuid4()), task_type=task_type, payload=payload)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "payload": self.payload,
        }


class TaskQueue(ABC):
    """Abstract task queue interface that can be implemented for different backends"""

    @abstractmethod
    async def enqueue(
        self, task_type: str, payload: Dict[str, Any], delay_seconds: int = 0
    ) -> str:
        """
        Add a task to the queue and return its ID

        Args:
            task_type: The type of task to run
            payload: Data to pass to the task handler
            delay_seconds: Optional delay before executing the task

        Returns:
            The task ID
        """
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task by ID

        Args:
            task_id: The task ID to lookup

        Returns:
            Task status information or None if not found
        """
        pass

    @abstractmethod
    async def list_tasks(self, story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List active tasks, optionally filtered by story_id

        Args:
            story_id: Optional story ID to filter tasks by

        Returns:
            List of task status dictionaries
        """
        pass
