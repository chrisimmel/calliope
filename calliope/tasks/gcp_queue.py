"""
Google Cloud Tasks implementation of task queue.

This implementation uses Google Cloud Tasks for reliable and scalable
background processing in production environments.
"""

from datetime import datetime, timedelta
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from protobuf import timestamp_pb2

from calliope.storage.firebase import get_firebase_manager

from .queue import TaskQueue

logger = logging.getLogger(__name__)


class GCPTaskQueue(TaskQueue):
    """Google Cloud Tasks implementation of task queue"""

    def __init__(self, project: str, location: str, queue_name: str, service_url: str):
        """
        Initialize the GCP Task Queue

        Args:
            project: GCP project ID
            location: GCP region (e.g., 'us-central1')
            queue_name: Name of the Cloud Tasks queue
            service_url: URL of the service that will process tasks
        """
        try:
            # Import Google Cloud Tasks client library
            from google.cloud import tasks_v2

            self.client = tasks_v2.CloudTasksClient()
            self.tasks_v2 = tasks_v2
        except ImportError:
            logger.error(
                "Google Cloud Tasks library not installed. "
                "Run: pip install google-cloud-tasks"
            )
            raise

        self.project = project
        self.location = location
        self.queue_name = queue_name
        self.service_url = service_url
        self.parent = self.client.queue_path(project, location, queue_name)
        self.firebase = get_firebase_manager()

        logger.info(f"Initialized GCP Task Queue: {queue_name} in {project}/{location}")

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
        # Generate a task ID that's unique but also somewhat descriptive
        story_id = payload.get("story_id", "")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        task_id = f"{task_type}-{story_id[:8]}-{timestamp}-{uuid.uuid4().hex[:6]}"
        task_id = task_id.replace(" ", "-").lower()

        # Add task metadata to payload
        task_payload = payload.copy()
        task_payload["_task_id"] = task_id
        task_payload["_task_type"] = task_type
        task_payload["_created_at"] = datetime.now().isoformat()

        # Prepare HTTP request for Cloud Tasks
        task = {
            "http_request": {
                "http_method": self.tasks_v2.HttpMethod.POST,
                "url": f"{self.service_url}/v2/tasks/{task_type}",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(task_payload).encode(),
            },
            "name": self.client.task_path(
                self.project, self.location, self.queue_name, task_id
            ),
        }

        # Add scheduling time if delay is specified
        if delay_seconds > 0:
            # The schedule time can't be in the past
            schedule_time = datetime.now(datetime.timezone.utc) + timedelta(
                seconds=delay_seconds
            )
            timestamp = schedule_time.timestamp()

            # Convert the timestamp to a Protobuf Timestamp
            timestamp_proto = timestamp_pb2.Timestamp()
            timestamp_proto.FromSeconds(int(timestamp))

            # Add the schedule time to the task
            task["schedule_time"] = timestamp_proto

        try:
            # Create task record in Firebase first
            firebase_task_data = {
                "task_id": task_id,
                "task_type": task_type,
                "payload": payload,
                "story_id": payload.get("story_id"),
                "client_id": payload.get("client_id"),
            }
            await self.firebase.create_task(firebase_task_data)

            # Add the task to the queue
            response = self.client.create_task(
                request={"parent": self.parent, "task": task}
            )
            logger.info(f"Task {task_id} created and enqueued in GCP Tasks")

            # Extract just the task ID from the full name
            parts = response.name.split("/")
            return parts[-1]
        except Exception as e:
            logger.exception(f"Failed to enqueue task {task_id} in GCP Tasks: {e!s}")
            raise

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task by ID

        Note: GCP Tasks doesn't provide detailed status tracking by default.
        For a complete solution, you would need to store task status in a database.
        This implementation provides a minimal approach.

        Args:
            task_id: The task ID to lookup

        Returns:
            Task status information or None if not found
        """
        try:
            # Get task status from Firebase
            task_data = await self.firebase.get_task(task_id)
            return task_data
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return None

    async def list_tasks(self, story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List tasks, optionally filtered by story_id using Firebase storage.

        Args:
            story_id: Optional story ID to filter tasks by

        Returns:
            List of task status dictionaries
        """
        try:
            if story_id:
                # Get tasks for specific story
                return await self.firebase.get_tasks_for_story(story_id)
            else:
                # For now, we don't have a "get all tasks" method in Firebase
                # This could be added if needed, but typically we query by story
                logger.warning(
                    "Listing all tasks not implemented - requires story_id filter"
                )
                return []
        except Exception as e:
            logger.exception(f"Error listing tasks from Firebase: {e!s}")
            return []
