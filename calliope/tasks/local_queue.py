"""
In-memory task queue implementation for local development.

This implementation uses asyncio to run tasks in the background without
blocking the main API server thread.
"""

import asyncio
from datetime import datetime
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Set

from calliope.storage.firebase import get_firebase_manager

from .queue import Task, TaskQueue

logger = logging.getLogger(__name__)


class LocalTaskQueue(TaskQueue):
    """In-memory task queue for local development"""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.handlers: Dict[str, Callable] = {}
        self.running_tasks: Set[str] = set()
        self.task_results: Dict[str, Any] = {}
        self.firebase = get_firebase_manager()

    def register_handler(self, task_type: str, handler: Callable):
        """
        Register a handler function for a task type

        Args:
            task_type: The type of task the handler processes
            handler: The function that will process tasks of this type
        """
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

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
        if task_type not in self.handlers:
            raise ValueError(f"No handler registered for task type: {task_type}")

        task = Task.create(task_type, payload)
        self.tasks[task.task_id] = task

        # Create Firebase task record
        try:
            firebase_task_data = {
                "task_id": task.task_id,
                "task_type": task_type,
                "payload": payload,
                "story_id": payload.get("story_id"),
                "client_id": payload.get("client_id"),
            }
            await self.firebase.create_task(firebase_task_data)
        except Exception as e:
            logger.error(f"Failed to create Firebase task record: {e}")
            # Continue anyway - task will still run locally

        # Schedule the task to run asynchronously with optional delay
        if delay_seconds > 0:
            logger.info(
                f"Task {task.task_id} of type {task_type} scheduled with {delay_seconds}s delay"
            )
            async_task = asyncio.create_task(
                self._run_task_with_delay(task.task_id, delay_seconds)
            )
        else:
            # Schedule immediately
            async_task = asyncio.create_task(self._run_task(task.task_id))
        print(f"Enqueued task: {async_task}")

        return task.task_id

    async def _run_task_with_delay(self, task_id: str, delay_seconds: int):
        """Run a task after a specified delay"""
        await asyncio.sleep(delay_seconds)
        await self._run_task(task_id)

    async def _run_task(self, task_id: str):
        """
        Run a task in the background

        Args:
            task_id: The ID of the task to run
        """
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return

        task = self.tasks[task_id]
        handler = self.handlers[task.task_type]

        self.running_tasks.add(task_id)
        task.status = "running"

        # Update Firebase task status to running
        try:
            await self.firebase.update_task(task_id, {"status": "running"})
        except Exception as e:
            logger.error(f"Failed to update Firebase task status to running: {e}")

        try:
            # Execute the task handler
            start_time = time.time()
            logger.info(f"Starting task {task_id} of type {task.task_type}")

            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                # Run synchronous handlers in a thread pool
                result = await asyncio.to_thread(handler, task.payload)

            task.status = "completed"
            duration = time.time() - start_time
            logger.info(f"Task {task_id} completed in {duration:.2f}s")

            # Store result
            self.task_results[task_id] = {
                "result": result,
                "completed_at": datetime.now().isoformat(),
            }

            # Update Firebase task status to completed
            try:
                # Serialize the result for Firestore storage
                serializable_result = self._serialize_task_result(result)
                await self.firebase.update_task(
                    task_id, {"status": "completed", "result": serializable_result}
                )
            except Exception as e:
                logger.error(f"Failed to update Firebase task status to completed: {e}")

        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e!s}")
            task.status = "failed"
            self.task_results[task_id] = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "failed_at": datetime.now().isoformat(),
            }

            # Update Firebase task status to failed
            try:
                await self.firebase.update_task(
                    task_id, {"status": "failed", "error": str(e)}
                )
            except Exception as e:
                logger.error(f"Failed to update Firebase task status to failed: {e}")

        finally:
            self.running_tasks.remove(task_id)

    def _serialize_task_result(self, result: Any) -> Dict[str, Any]:
        """
        Serialize task result for Firestore storage.
        Converts Pydantic models and other non-serializable objects to dictionaries.
        """
        if result is None:
            return {"success": True}

        if isinstance(result, dict):
            serialized = {}
            for key, value in result.items():
                serialized[key] = self._serialize_value(value)
            return serialized

        # For non-dict results, wrap in a result object
        return {"result": self._serialize_value(result)}

    def _serialize_value(self, value: Any) -> Any:
        """Helper method to serialize individual values."""
        if value is None:
            return None
        elif hasattr(value, "model_dump"):
            # Pydantic model - convert to dict
            return value.model_dump()
        elif isinstance(value, list):
            # List - recursively serialize each item
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            # Dict - recursively serialize each value
            return {k: self._serialize_value(v) for k, v in value.items()}
        else:
            # Primitive value (str, int, float, bool) - return as-is
            return value

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task by ID

        Args:
            task_id: The task ID to lookup

        Returns:
            Task status information or None if not found
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        result = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        }

        # Include result if available
        if task_id in self.task_results:
            result.update(self.task_results[task_id])

        return result

    async def list_tasks(self, story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List active tasks, optionally filtered by story_id

        Args:
            story_id: Optional story ID to filter tasks by

        Returns:
            List of task status dictionaries
        """
        results = []

        for task_id, task in self.tasks.items():
            # Filter by story_id if provided
            if story_id and task.payload.get("story_id") != story_id:
                continue

            task_info = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
            }

            # Include result if available
            if task_id in self.task_results:
                task_info.update(self.task_results[task_id])

            results.append(task_info)

        return results
