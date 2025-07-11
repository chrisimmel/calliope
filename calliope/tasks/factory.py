"""
Factory function to get the appropriate task queue implementation.

This module selects either the local or GCP task queue implementation
based on the current environment.
"""

from functools import lru_cache
import logging
import os

from calliope.utils.google import (
    CLOUD_ENV_GCP_PROD,
    get_cloud_environment,
    get_project_id,
)

from .local_queue import LocalTaskQueue
from .queue import TaskQueue

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_task_queue() -> TaskQueue:
    """
    Factory function to get the appropriate task queue implementation

    Uses environment variables to determine which implementation to use:
    - CLOUD_ENV: Set to 'gcp-prod' to use GCP, anything else for local
    - GCP_REGION: GCP region (defaults to 'us-central1')
    - GCP_QUEUE_NAME: Cloud Tasks queue name (defaults to 'calliope-tasks')
    - SERVICE_URL: URL of service handling tasks (required for GCP)

    Returns:
        The appropriate TaskQueue implementation
    """
    is_production = get_cloud_environment() == CLOUD_ENV_GCP_PROD

    if is_production:
        # Use Google Cloud Tasks in production
        logger.info("Using Google Cloud Tasks queue for production")

        # Check required environment variables
        gcp_project_id = get_project_id()
        if not gcp_project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT environment variable is required for production"
            )

        service_url = os.environ.get("SERVICE_URL")
        if not service_url:
            raise ValueError(
                "SERVICE_URL environment variable is required for production"
            )

        # Get optional environment variables with defaults
        gcp_region = os.environ.get("GCP_REGION", "us-central1")
        gcp_queue_name = os.environ.get("GCP_QUEUE_NAME", "calliope-tasks")

        # Import GCP task queue implementation
        try:
            from .gcp_queue import GCPTaskQueue

            return GCPTaskQueue(
                project=gcp_project_id,
                location=gcp_region,
                queue_name=gcp_queue_name,
                service_url=service_url,
            )
        except ImportError as e:
            logger.error(f"Failed to import GCPTaskQueue: {e!s}")
            logger.warning(
                "Falling back to LocalTaskQueue despite production environment"
            )
            return LocalTaskQueue()
    else:
        # Use local task queue for development
        logger.info("Using local task queue for development")
        return LocalTaskQueue()


# Helper to get a configured task queue and register handlers
_TASK_QUEUE_INSTANCE = None


def configure_task_queue():
    """
    Configure the task queue and register handlers

    This should be called during application startup to ensure handlers
    are registered before tasks are enqueued.

    Returns:
        The configured task queue instance
    """
    global _TASK_QUEUE_INSTANCE

    if _TASK_QUEUE_INSTANCE is None:
        _TASK_QUEUE_INSTANCE = get_task_queue()

        # Only register handlers for LocalTaskQueue
        if isinstance(_TASK_QUEUE_INSTANCE, LocalTaskQueue):
            # Import handlers to avoid circular imports
            from .handlers import register_handlers

            register_handlers(_TASK_QUEUE_INSTANCE)

    return _TASK_QUEUE_INSTANCE
