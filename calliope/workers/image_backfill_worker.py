"""
Background worker for processing the Firebase image backfill queue.

This worker can be run as a scheduled Cloud Run job or standalone script
to retry failed image generations.
"""

import asyncio
import logging
import os
import sys
from typing import Optional

import httpx

# Add the parent directory to the path so we can import calliope modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calliope.models import KeysModel
from calliope.utils.image_backfill import (
    ImageBackfillQueue,
    scan_and_queue_legacy_frames,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_backfill_queue(max_items: int = 10, timeout_per_item: int = 60) -> int:
    """
    Process items from the Firebase image backfill queue.

    Args:
        max_items: Maximum number of items to process in this run
        timeout_per_item: Timeout in seconds per item

    Returns:
        Number of items successfully processed
    """
    logger.info(f"Starting backfill worker - processing up to {max_items} items")

    async with httpx.AsyncClient(timeout=timeout_per_item) as httpx_client:
        pending_items = await ImageBackfillQueue.get_pending_items(limit=max_items)

        if not pending_items:
            logger.info("No pending items in backfill queue")
            return 0

        logger.info(f"Found {len(pending_items)} pending items to process")

        successful_count = 0
        for item in pending_items:
            try:
                logger.info(
                    f"Processing: {item['story_cuid']} frame {item['frame_number']}"
                )
                success = await ImageBackfillQueue.process_queue_item(item, httpx_client)
                if success:
                    successful_count += 1
            except Exception as e:  # noqa: PERF203
                logger.error(
                    f"Unexpected error processing item {item.get('queue_item_id', 'unknown')}: {e}"
                )
                continue

        logger.info(
            f"Backfill worker completed: {successful_count}/{len(pending_items)} items successful"
        )
        return successful_count


async def scan_legacy_frames_worker(limit: Optional[int] = 50) -> int:
    """
    Scan for legacy frames without images and queue them for backfill.

    Args:
        keys: API keys (needed for model access)
        limit: Maximum number of frames to scan and queue

    Returns:
        Number of frames queued
    """
    logger.info(f"Starting legacy frame scanner - limit: {limit}")

    queued_count = await scan_and_queue_legacy_frames(limit)

    logger.info(f"Legacy frame scanner completed: {queued_count} frames queued")
    return queued_count


async def main():
    """Main entry point for the backfill worker."""
    import argparse

    parser = argparse.ArgumentParser(description="Image backfill worker")
    parser.add_argument(
        "--mode",
        choices=["backfill", "scan_legacy", "both"],
        default="backfill",
        help="Worker mode: process backfill queue, scan legacy frames, or both",
    )
    parser.add_argument(
        "--max-items", type=int, default=10, help="Maximum number of items to process"
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout per item in seconds"
    )
    parser.add_argument(
        "--legacy-limit",
        type=int,
        default=50,
        help="Maximum number of legacy frames to scan and queue",
    )

    args = parser.parse_args()

    keys = KeysModel.from_env()

    # Validate required keys
    if not keys.openai_api_key:
        logger.error("OPENAI_API_KEY is required")
        sys.exit(1)

    try:
        if args.mode in ["scan_legacy", "both"]:
            queued_count = await scan_legacy_frames_worker(args.legacy_limit)
            logger.info(f"✅ Queued {queued_count} legacy frames")

        if args.mode in ["backfill", "both"]:
            processed_count = await process_backfill_queue(args.max_items, args.timeout)
            logger.info(f"✅ Processed {processed_count} backfill items")

        logger.info("🎉 Image backfill worker completed successfully")

    except Exception as e:
        logger.error(f"❌ Image backfill worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Initialize Firebase if needed
    try:
        import firebase_admin
        from firebase_admin import credentials

        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            # Try to use default credentials first
            try:
                firebase_admin.initialize_app()
                logger.info("Initialized Firebase with default credentials")
            except Exception:
                # Fall back to explicit credentials file if available
                cred_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if cred_file and os.path.exists(cred_file):
                    cred = credentials.Certificate(cred_file)
                    firebase_admin.initialize_app(
                        cred,
                        {
                            "databaseURL": os.getenv(
                                "FIREBASE_DATABASE_URL",
                                "https://calliope-firebase-default-rtdb.firebaseio.com/",
                            )
                        },
                    )
                    logger.info("Initialized Firebase with credentials file")
                else:
                    logger.error("Could not initialize Firebase - no credentials found")
                    sys.exit(1)
    except ImportError:
        logger.error("Firebase Admin SDK not available")
        sys.exit(1)

    # Run the worker
    asyncio.run(main())
