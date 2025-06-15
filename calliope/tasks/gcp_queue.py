"""
Google Cloud Tasks implementation of task queue.

This implementation uses Google Cloud Tasks for reliable and scalable
background processing in production environments.
"""

from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime, timedelta
import uuid

from protobuf import timestamp_pb2

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
            # Add the task to the queue
            response = self.client.create_task(
                request={"parent": self.parent, "task": task}
            )
            logger.info(f"Task {task_id} created and enqueued in GCP Tasks")

            # Extract just the task ID from the full name
            parts = response.name.split("/")
            return parts[-1]
        except Exception as e:
            logger.exception(f"Failed to enqueue task {task_id} in GCP Tasks: {str(e)}")
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
        task_path = self.client.task_path(
            self.project, self.location, self.queue_name, task_id
        )

        try:
            # Try to get the task from Cloud Tasks
            response = self.client.get_task(request={"name": task_path})

            # Determine status based on scheduling time
            status = "pending"
            if hasattr(response, "schedule_time") and response.schedule_time:
                # Task is scheduled but not yet running
                status = "pending"
            else:
                # Task is probably running or has run
                # This is a simplification - GCP Tasks doesn't track if a task is running
                status = "running"

            return {
                "task_id": task_id,
                "status": status,
                "created_at": datetime.now().isoformat(),  # We don't have the real creation time
            }
        except Exception:
            # Task not found in queue, might be completed or failed
            logger.warning(f"Task {task_id} not found in GCP Tasks queue")
            return None

    async def list_tasks(self, story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List active tasks, optionally filtered by story_id

        Note: GCP Tasks doesn't provide filtering by payload content.
        For a complete solution, you would need to store task metadata in a database.
        This implementation provides a simplified approach.

        Args:
            story_id: Optional story ID to filter tasks by

        Returns:
            List of task status dictionaries
        """
        # Request tasks from the queue
        request = {"parent": self.parent}

        try:
            tasks = self.client.list_tasks(request=request)

            results = []
            for task in tasks:
                # Extract the task ID from the name
                task_id = task.name.split("/")[-1]

                # In a real implementation, you'd look up task details in your database
                # Here we just return basic info from the task name
                task_info = {
                    "task_id": task_id,
                    "status": "pending"
                    if hasattr(task, "schedule_time") and task.schedule_time
                    else "running",
                }

                # Try to parse story_id from task_id if it follows our naming convention
                # This is a hack - in a real implementation you'd store this in a database
                parts = task_id.split("-")
                if len(parts) >= 3:
                    task_info["task_type"] = parts[0]
                    extracted_story_id = parts[1]

                    # Only include this task if it matches the story_id filter
                    if story_id and extracted_story_id != story_id:
                        continue

                results.append(task_info)

            return results
        except Exception as e:
            logger.exception(f"Error listing tasks from GCP Tasks: {str(e)}")
            return []
