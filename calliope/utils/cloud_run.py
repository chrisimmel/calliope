"""
Utilities for triggering Cloud Run jobs programmatically.
"""

import asyncio
import logging
from typing import Optional

import httpx

from calliope.utils.google import is_google_cloud_run_environment

logger = logging.getLogger(__name__)


async def trigger_maintenance_worker_if_needed() -> bool:
    """
    Trigger the story maintenance worker Cloud Run job if running in Google Cloud.

    This is designed to be called when image generation fails in strategies
    to provide faster retry processing than waiting for scheduled execution.

    Returns:
        True if trigger was attempted, False if skipped (not in cloud environment)
    """
    if not is_google_cloud_run_environment():
        logger.debug(
            "Not in Google Cloud environment, skipping maintenance worker trigger"
        )
        return False

    try:
        # Use asyncio to run the trigger in the background without blocking
        # the main story generation flow
        task = asyncio.create_task(_trigger_maintenance_worker_async())
        # Don't await - this is intentionally fire-and-forget
        _ = task  # Store reference to prevent garbage collection
        logger.info("🚀 Triggered background maintenance worker for immediate retry")
        return True
    except Exception as e:
        logger.warning(f"Failed to trigger maintenance worker: {e}")
        return False


async def _trigger_maintenance_worker_async() -> None:
    """
    Asynchronously trigger the maintenance worker Cloud Run job.

    This uses the Cloud Run Admin API to execute the job with
    a focus on processing the Firebase queue only.
    """
    import os

    try:
        # Get project ID from metadata server or environment
        project_id = await _get_project_id()
        if not project_id:
            logger.error("Could not determine project ID for Cloud Run trigger")
            return

        # Get access token
        access_token = await _get_access_token()
        if not access_token:
            logger.error("Could not get access token for Cloud Run trigger")
            return

        # Cloud Run Jobs API endpoint
        region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        job_name = "calliope-story-maintenance"

        url = (
            f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
            f"namespaces/{project_id}/jobs/{job_name}:run"
        )

        # Execute the job with focus on queue processing only
        # This avoids long-running corpus scans during immediate retries
        payload = {
            "spec": {
                "template": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "args": [
                                            "--max-queue",
                                            "50",  # Process more queue items
                                            "--max-backfill",
                                            "10",  # Fewer direct scans
                                            "--skip-cleanup",  # Skip cleanup during immediate retry
                                            "--skip-dead-stories",  # Skip cleanup during immediate retry
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info("✅ Successfully triggered maintenance worker job")
            elif response.status_code == 409:
                logger.info(
                    "⏳ Maintenance worker job already running, skipping trigger"
                )
            else:
                logger.warning(
                    f"Maintenance worker trigger returned status {response.status_code}: {response.text}"
                )

    except Exception as e:
        logger.error(f"Failed to trigger maintenance worker job: {e}")


async def _get_project_id() -> Optional[str]:
    """Get the current Google Cloud project ID."""
    import os

    # Try environment variable first
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if project_id:
        return project_id

    # Try metadata server
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"},
            )
            if response.status_code == 200:
                return response.text.strip()
    except Exception:
        pass

    return None


async def _get_access_token() -> Optional[str]:
    """Get an access token for Cloud Run API calls."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get("access_token")
    except Exception as e:
        logger.error(f"Failed to get access token: {e}")

    return None
