"""
Firebase Firestore integration for real-time updates.
"""

from datetime import datetime
from functools import lru_cache
import logging
import os
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from calliope.utils.google import (
    CLOUD_ENV_GCP_PROD,
    get_cloud_environment,
    get_project_id,
    is_google_cloud_run_environment,
)

logger = logging.getLogger(__name__)


class FirebaseManager:
    """
    Manages connection to Firebase Firestore for real-time updates.
    Provides methods for storing and retrieving story status updates.
    """

    def __init__(
        self, project_id: str, database_id: str, credential_path: Optional[str] = None
    ):
        """
        Initialize the Firebase connection.

        Args:
            project_id: Firebase project ID
            database_id: Firestore database ID (for multi-database support)
            credential_path: Path to service account credentials JSON file (optional in GCP)
        """

        self.project_id = project_id
        self.database_id = database_id

        try:
            if is_google_cloud_run_environment():
                # In GCP, can use default credentials.
                self.app = firebase_admin.initialize_app(
                    options={"projectId": project_id, "databaseId": database_id}
                )
            elif credential_path and os.path.exists(credential_path):
                # Use application default credentials but in a way Firebase can use them
                try:
                    # First try with Certificate - requires specific Firebase service account format
                    cred = credentials.Certificate(credential_path)
                    self.app = firebase_admin.initialize_app(
                        cred, {"projectId": project_id, "databaseId": database_id}
                    )
                except (OSError, ValueError) as e:
                    # If Certificate fails, try with ApplicationDefault instead
                    logger.info(
                        f"Using application default credentials for Firebase: {e}"
                    )
                    self.app = firebase_admin.initialize_app(
                        options={"projectId": project_id, "databaseId": database_id}
                    )
            else:
                # Try with application default credentials in env var
                try:
                    self.app = firebase_admin.initialize_app(
                        options={"projectId": project_id, "databaseId": database_id}
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to initialize Firebase with default credentials: {e}"
                    )
                    raise ValueError("Firebase credentials not found or invalid.") from e

            # Get the Firestore client
            firestore_client = firestore.client(database_id=database_id)
            self.db = firestore_client
            logger.info(f"Firestore initialized with database {database_id}")
        except Exception as e:
            logger.error(f"Error initializing Firebase Firestore: {e}")
            raise

    async def update_story_status(self, story_id: str, status: Dict[str, Any]) -> None:
        """
        Update the status of a story in Firestore.

        Args:
            story_id: ID of the story
            status: Status information to update
        """
        try:
            # Get a reference to the story status document
            status_ref = self.db.collection("stories").document(story_id)

            # Merge the status update with existing data
            status_ref.set({"status": status}, merge=True)
            logger.debug(f"Updated story {story_id} status in Firestore")
        except Exception as e:
            logger.error(f"Error updating story status in Firestore: {e}")
            raise

    async def get_story_status(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a story from Firestore.

        Args:
            story_id: ID of the story

        Returns:
            Status information or None if not found
        """
        try:
            # Get a reference to the story status document
            status_ref = self.db.collection("stories").document(story_id)

            # Get the status
            status_doc = status_ref.get()
            if status_doc.exists:
                status_data = status_doc.to_dict()
                return status_data.get("status", {}) if status_data else {}
            return None
        except Exception as e:
            logger.error(f"Error getting story status from Firestore: {e}")
            return None

    async def add_story_update(self, story_id: str, update: Dict[str, Any]) -> str:
        """
        Add an update to a story's updates collection.

        Args:
            story_id: ID of the story
            update: Update information to add

        Returns:
            ID of the new update document
        """
        try:
            # Ensure the update has a timestamp if not provided
            if "timestamp" not in update:
                update["timestamp"] = datetime.now().isoformat()

            # Get a reference to the story updates collection
            updates_ref = (
                self.db.collection("stories").document(story_id).collection("updates")
            )

            # Add the update as a new document
            update_doc = updates_ref.add(update)

            # Return the ID of the new document
            return update_doc[1].id
        except Exception as e:
            logger.error(f"Error adding story update to Firestore: {e}")
            raise

    async def get_story_updates(
        self, story_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent updates for a story from Firestore.

        Args:
            story_id: ID of the story
            limit: Maximum number of updates to return

        Returns:
            List of update objects
        """
        try:
            # Get a reference to the story updates collection
            updates_ref = (
                self.db.collection("stories").document(story_id).collection("updates")
            )

            # Get the updates, ordered by timestamp descending (newest first)
            query = updates_ref.order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            ).limit(limit)
            updates_docs = query.stream()

            # Convert documents to dictionaries with IDs
            updates = []
            for doc in updates_docs:
                update_data = doc.to_dict()
                update_data["id"] = doc.id
                updates.append(update_data)

            return updates
        except Exception as e:
            logger.error(f"Error getting story updates from Firestore: {e}")
            return []

    async def delete_story_data(self, story_id: str) -> None:
        """
        Delete all data for a story from Firestore.
        Useful for cleanup.

        Args:
            story_id: ID of the story
        """
        try:
            # Delete the main story document
            story_ref = self.db.collection("stories").document(story_id)

            # First, delete all documents in the updates subcollection
            batch_size = 500
            updates_ref = story_ref.collection("updates")
            docs = updates_ref.limit(batch_size).stream()
            deleted = 0

            # Delete documents in batches
            for doc in docs:
                doc.reference.delete()
                deleted += 1

            # If we've deleted a full batch, there might be more documents
            while deleted >= batch_size:
                docs = updates_ref.limit(batch_size).stream()
                deleted = 0
                for doc in docs:
                    doc.reference.delete()
                    deleted += 1

            # Finally, delete the story document itself
            story_ref.delete()

            logger.info(f"Deleted story {story_id} data from Firestore")
        except Exception as e:
            logger.error(f"Error deleting story data from Firestore: {e}")
            raise

    # --- Task Management Methods ---

    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Create a new task record in Firebase.

        Args:
            task_data: Task information including task_id, task_type, payload, etc.

        Returns:
            The task ID
        """
        try:
            task_id = task_data.get("task_id")
            if not task_id:
                raise ValueError("task_id is required in task_data")

            # Ensure required fields are present
            task_record = {
                "task_id": task_id,
                "task_type": task_data.get("task_type"),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "payload": task_data.get("payload", {}),
                "story_id": task_data.get("story_id"),
                "client_id": task_data.get("client_id"),
            }

            # Add optional fields if present
            if "progress" in task_data:
                task_record["progress"] = task_data["progress"]
            if "error" in task_data:
                task_record["error"] = task_data["error"]

            # Create the task document
            task_ref = self.db.collection("tasks").document(task_id)
            task_ref.set(task_record)

            # If associated with a story, update the story's active_tasks
            story_id = task_data.get("story_id")
            if story_id:
                await self.add_active_task_to_story(story_id, task_id)

            logger.debug(f"Created task {task_id} in Firebase")
            return task_id
        except Exception as e:
            logger.error(f"Error creating task in Firebase: {e}")
            raise

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a task record in Firebase.

        Args:
            task_id: ID of the task to update
            updates: Dictionary of fields to update
        """
        try:
            task_ref = self.db.collection("tasks").document(task_id)

            # Add timestamp for status changes
            if "status" in updates:
                timestamp = datetime.now().isoformat()
                if updates["status"] == "running":
                    updates["started_at"] = timestamp
                elif updates["status"] in ["completed", "failed"]:
                    updates["completed_at"] = timestamp
                    # Move task from active to recent for associated story
                    task_doc = task_ref.get()
                    if task_doc.exists:
                        task_data = task_doc.to_dict()
                        story_id = task_data.get("story_id")
                        if story_id:
                            await self.move_task_to_recent(story_id, task_id)

            task_ref.update(updates)
            logger.debug(f"Updated task {task_id} in Firebase")
        except Exception as e:
            logger.error(f"Error updating task in Firebase: {e}")
            raise

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task record from Firebase.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task data or None if not found
        """
        try:
            task_ref = self.db.collection("tasks").document(task_id)
            task_doc = task_ref.get()

            if task_doc.exists:
                return task_doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting task from Firebase: {e}")
            return None

    async def get_tasks_for_story(
        self, story_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent tasks associated with a story.

        Args:
            story_id: ID of the story
            limit: Maximum number of tasks to return

        Returns:
            List of task records
        """
        try:
            tasks_ref = self.db.collection("tasks")
            query = (
                tasks_ref.where("story_id", "==", story_id)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            tasks_docs = query.stream()
            tasks = []
            for doc in tasks_docs:
                task_data = doc.to_dict()
                tasks.append(task_data)

            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks for story from Firebase: {e}")
            return []

    async def add_active_task_to_story(self, story_id: str, task_id: str) -> None:
        """
        Add a task ID to a story's active_tasks list.
        Creates the story document with minimal schema if it doesn't exist.

        Args:
            story_id: ID of the story
            task_id: ID of the task to add
        """
        try:
            story_ref = self.db.collection("stories").document(story_id)

            # Check if document exists first
            story_doc = story_ref.get()
            if story_doc.exists:
                # Document exists, just add the task
                story_ref.update({"active_tasks": firestore.ArrayUnion([task_id])})
            else:
                # Document doesn't exist, create it with minimal schema
                # The task handler will fill in the full harmonized fields later
                story_ref.set(
                    {
                        "cuid": story_id,
                        "active_tasks": [task_id],
                        "recent_tasks": [],
                        "frame_count": 0,
                    }
                )
        except Exception as e:
            logger.error(f"Error adding active task to story: {e}")

    async def move_task_to_recent(self, story_id: str, task_id: str) -> None:
        """
        Move a task from active_tasks to recent_tasks for a story.

        Args:
            story_id: ID of the story
            task_id: ID of the task to move
        """
        try:
            story_ref = self.db.collection("stories").document(story_id)

            # Get current story data
            story_doc = story_ref.get()
            if not story_doc.exists:
                return

            story_data = story_doc.to_dict()
            active_tasks = story_data.get("active_tasks", [])
            recent_tasks = story_data.get("recent_tasks", [])

            # Remove from active, add to recent (keeping only last 5)
            if task_id in active_tasks:
                active_tasks.remove(task_id)
                recent_tasks.insert(0, task_id)  # Add to front
                recent_tasks = recent_tasks[:5]  # Keep only last 5

                story_ref.update(
                    {"active_tasks": active_tasks, "recent_tasks": recent_tasks}
                )
        except Exception as e:
            logger.error(f"Error moving task to recent: {e}")

    async def update_story_fields(self, story_id: str, fields: Dict[str, Any]) -> None:
        """
        Update story fields in Firebase (for schema harmonization).

        Args:
            story_id: ID of the story
            fields: Dictionary of story fields to update
        """
        try:
            story_ref = self.db.collection("stories").document(story_id)
            story_ref.set(fields, merge=True)
            logger.debug(f"Updated story {story_id} fields in Firebase")
        except Exception as e:
            logger.error(f"Error updating story fields in Firebase: {e}")
            raise


@lru_cache(maxsize=1)
def get_firebase_manager() -> FirebaseManager:
    # Get environment
    is_production = get_cloud_environment() == CLOUD_ENV_GCP_PROD

    # Same project ID for both environments
    project_id = get_project_id()

    database_id = os.environ.get(
        "FIREBASE_DATABASE_ID",
        "calliope-production" if is_production else "calliope-development",
    )
    credential_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")

    # Create and return the manager
    return FirebaseManager(project_id, database_id, credential_path)
