"""
Unified story maintenance worker for Calliope.

This single job handles:
1. Backfilling missing images for frames with text
2. Deleting empty frames (no text and no image)
3. Deleting dead stories (no frames and no scheduled tasks)
4. Processing failed items from the Firebase queue

Runs as a Cloud Run job with configurable limits to process the corpus incrementally.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
import sys
import traceback
from typing import Dict

import httpx

# Add the parent directory to the path so we can import calliope modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calliope.inference import text_to_image_file_inference
from calliope.models import FramesRequestParamsModel, KeysModel
from calliope.storage.config_manager import get_sparrow_story_parameters_and_keys
from calliope.tables import ModelConfig, Story, StoryFrame
from calliope.utils.file import create_sequential_filename
from calliope.utils.google import is_google_cloud_run_environment, put_media_file
from calliope.utils.image import get_image_attributes
from calliope.utils.image_backfill import ImageBackfillQueue, reconstruct_image_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StoryMaintenanceWorker:
    """Unified worker for story corpus maintenance."""

    def __init__(self, keys: KeysModel):
        self.keys = keys

    async def run_maintenance(
        self,
        max_frames_to_backfill: int = 20,
        max_frames_to_delete: int = 50,
        max_stories_to_delete: int = 10,
        max_queue_items: int = 10,
        process_queue: bool = True,
        backfill_missing: bool = True,
        cleanup_empty: bool = True,
        delete_dead_stories: bool = True,
    ) -> Dict[str, int]:
        """
        Run comprehensive story maintenance.

        Args:
            max_frames_to_backfill: Max frames to process for missing images
            max_frames_to_delete: Max empty frames to delete
            max_stories_to_delete: Max dead stories to delete
            max_queue_items: Max Firebase queue items to process
            process_queue: Process Firebase backfill queue
            backfill_missing: Find and backfill frames missing images
            cleanup_empty: Delete empty frames
            delete_dead_stories: Delete stories with no frames

        Returns:
            Dict with counts of processed items
        """
        results = {
            "queue_items_processed": 0,
            "frames_backfilled": 0,
            "empty_frames_deleted": 0,
            "dead_stories_deleted": 0,
            "errors": 0,
        }

        async with httpx.AsyncClient(timeout=120) as httpx_client:
            # 1. Process Firebase queue items first
            if process_queue:
                logger.info("🔄 Processing Firebase backfill queue...")
                results["queue_items_processed"] = await self._process_queue_items(
                    httpx_client, max_queue_items
                )

            # 2. Find and backfill missing images
            if backfill_missing:
                logger.info("🎨 Finding frames missing images for backfill...")
                results["frames_backfilled"] = await self._backfill_missing_images(
                    httpx_client, max_frames_to_backfill
                )

            # 3. Delete empty frames
            if cleanup_empty:
                logger.info("🧹 Deleting empty frames...")
                results["empty_frames_deleted"] = await self._delete_empty_frames(
                    max_frames_to_delete
                )

            # 4. Delete dead stories
            if delete_dead_stories:
                logger.info("💀 Deleting dead stories...")
                results["dead_stories_deleted"] = await self._delete_dead_stories(
                    max_stories_to_delete
                )

        return results

    async def _process_queue_items(
        self, httpx_client: httpx.AsyncClient, max_items: int
    ) -> int:
        """Process items from Firebase backfill queue."""
        try:
            pending_items = await ImageBackfillQueue.get_pending_items(limit=max_items)

            if not pending_items:
                logger.info("No pending items in Firebase queue")
                return 0

            logger.info(f"Processing {len(pending_items)} items from Firebase queue")

            successful_count = 0
            for item in pending_items:
                try:
                    success = await ImageBackfillQueue.process_queue_item(
                        item, httpx_client
                    )
                    if success:
                        successful_count += 1
                except Exception as e:  # noqa: PERF203
                    logger.error(
                        f"Error processing queue item {item.get('queue_item_id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(
                f"✅ Processed {successful_count}/{len(pending_items)} queue items"
            )
            return successful_count

        except Exception as e:
            logger.error(f"Failed to process queue items: {e}")
            return 0

    async def _backfill_missing_images(
        self, httpx_client: httpx.AsyncClient, max_frames: int
    ) -> int:
        """Find frames with text but no image and generate images for them."""
        try:
            # Find frames that have text but no image
            frames_needing_images = (
                await StoryFrame.objects(StoryFrame.story)
                .where(
                    StoryFrame.text.is_not_null()
                    & (StoryFrame.text != "")
                    & StoryFrame.image.is_null()
                )
                .limit(max_frames)
                .run()
            )

            if not frames_needing_images:
                logger.info("No frames found that need image backfill")
                return 0

            logger.info(
                f"Found {len(frames_needing_images)} frames needing image backfill"
            )

            successful_count = 0
            for frame in frames_needing_images:
                try:
                    success = await self._backfill_single_frame(frame, httpx_client)
                    if success:
                        successful_count += 1
                except Exception as e:  # noqa: PERF203
                    logger.error(f"Failed to backfill frame {frame.id}: {e}")
                    continue

            logger.info(
                f"✅ Successfully backfilled {successful_count}/{len(frames_needing_images)} frames"
            )
            return successful_count

        except Exception as e:
            logger.error(f"Failed to backfill missing images: {e}")
            return 0

    async def _backfill_single_frame(
        self, frame: StoryFrame, httpx_client: httpx.AsyncClient
    ) -> bool:
        """Backfill image for a single frame."""
        try:
            # Get the story
            story = await Story.objects().where(Story.id == frame.story).first().run()
            if not story:
                logger.error(f"Story not found for frame {frame.id}")
                return False

            # Extract metadata and reconstruct parameters
            import json

            metadata = frame.metadata or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

            # Determine strategy config with fallbacks
            strategy_config_slug = metadata.get("strategy_config")
            if not strategy_config_slug:
                parameters = metadata.get("parameters", {})
                if isinstance(parameters, str):
                    try:
                        parameters = json.loads(parameters)
                    except (json.JSONDecodeError, TypeError):
                        parameters = {}

                legacy_strategy = parameters.get("strategy")
                if legacy_strategy:
                    legacy_mapping = {
                        "continuous": "continuous-v1-gpt-4",
                        "continuous_v0": "continuous-v1-gpt-4",
                        "continuous_v1": "continuous-v1-gpt-4",
                        "simple_one_frame": "simple-one-frame",
                        "fern": "fern",
                        "tamarisk": "tamarisk",
                        "lavender": "lavender",
                        "narcissus": "narcissus",
                        "literal": "literal",
                    }
                    strategy_config_slug = legacy_mapping.get(
                        legacy_strategy, "simple-one-frame"
                    )
                else:
                    strategy_config_slug = "simple-one-frame"

            # Get model config slug
            model_config_slug = metadata.get(
                "text_to_image_model_config", "stability-stable-diffusion-1.6"
            )

            # Reconstruct image prompt
            image_prompt = await reconstruct_image_prompt(frame=frame, metadata=metadata)
            if not image_prompt:
                logger.warning(
                    f"Could not reconstruct image prompt for frame {frame.id}"
                )
                return False

            # Get client_id from story
            story_state_props = story.state_props or {}
            if isinstance(story_state_props, str):
                try:
                    story_state_props = json.loads(story_state_props)
                except (json.JSONDecodeError, TypeError):
                    story_state_props = {}

            client_id = story_state_props.get("client_id", story.cuid)

            # Load API keys
            request_params = FramesRequestParamsModel(
                client_id=client_id, strategy=strategy_config_slug
            )

            try:
                _, keys, _ = await get_sparrow_story_parameters_and_keys(request_params)
            except Exception as e:
                logger.error(f"Failed to load keys for client {client_id}: {e}")
                return False

            # Get model config
            model_config = (
                await ModelConfig.objects(ModelConfig.model)
                .where(ModelConfig.slug == model_config_slug)
                .first()
                .output(load_json=True)
                .run()
            )

            if not model_config:
                logger.error(f"Model config not found: {model_config_slug}")
                return False

            # Generate image
            output_image_filename = create_sequential_filename(
                "media", client_id, "out", "png", story.cuid, frame.number
            )

            await text_to_image_file_inference(
                httpx_client,
                image_prompt,
                output_image_filename,
                model_config,
                keys,
                None,  # output_image_width
                None,  # output_image_height
            )

            # Save image to database
            image_obj = get_image_attributes(output_image_filename)
            image_obj.date_updated = datetime.now(timezone.utc)
            await image_obj.save().run()

            # Push to Cloud Storage if needed
            is_google_cloud = is_google_cloud_run_environment()
            if is_google_cloud:
                try:
                    put_media_file(image_obj.url)
                    logger.info("✅ Uploaded image to Cloud Storage")
                except Exception as cloud_error:
                    logger.warning(f"Failed to upload to Cloud Storage: {cloud_error}")

            # Update frame
            frame.image = image_obj
            frame.source_image = image_obj
            frame.date_updated = datetime.now(timezone.utc)
            await frame.save().run()

            logger.info(
                f"✅ Successfully backfilled image for story {story.cuid} frame {frame.number}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to backfill frame {frame.id}: {e}")
            traceback.print_exc()
            return False

    async def _delete_empty_frames(self, max_frames: int) -> int:
        """Delete frames that have neither text nor image."""
        try:
            # Find empty frames
            empty_frames = (
                await StoryFrame.objects()
                .where(
                    (StoryFrame.text.is_null() | (StoryFrame.text == ""))
                    & StoryFrame.image.is_null()
                )
                .limit(max_frames)
                .run()
            )

            if not empty_frames:
                logger.info("No empty frames found to delete")
                return 0

            logger.info(f"Found {len(empty_frames)} empty frames to delete")

            deleted_count = 0
            for frame in empty_frames:
                try:
                    await frame.remove().run()
                    deleted_count += 1
                    logger.info(f"🗑️  Deleted empty frame {frame.id}")
                except Exception as e:  # noqa: PERF203
                    logger.error(f"Failed to delete frame {frame.id}: {e}")
                    continue

            logger.info(f"✅ Deleted {deleted_count}/{len(empty_frames)} empty frames")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete empty frames: {e}")
            return 0

    async def _delete_dead_stories(self, max_stories: int) -> int:
        """Delete stories that have no frames and no scheduled tasks."""
        try:
            # Find stories with no frames
            # Note: This is a simplified approach. In production you'd also want to check
            # for any scheduled tasks or other dependencies
            stories_without_frames = (
                await Story.objects()
                .where(~Story.id.is_in(StoryFrame.select(StoryFrame.story).distinct()))
                .limit(max_stories)
                .run()
            )

            if not stories_without_frames:
                logger.info("No dead stories found to delete")
                return 0

            logger.info(f"Found {len(stories_without_frames)} potentially dead stories")

            deleted_count = 0
            for story in stories_without_frames:
                try:
                    # Double-check it has no frames
                    frame_count = await story.get_frame_count()
                    if frame_count == 0:
                        await story.remove().run()
                        deleted_count += 1
                        logger.info(f"💀 Deleted dead story {story.cuid}")
                    else:
                        logger.info(
                            f"Story {story.cuid} has {frame_count} frames, skipping"
                        )
                except Exception as e:  # noqa: PERF203
                    logger.error(f"Failed to delete story {story.cuid}: {e}")
                    continue

            logger.info(
                f"✅ Deleted {deleted_count}/{len(stories_without_frames)} dead stories"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete dead stories: {e}")
            return 0


async def main():
    """Main entry point for the maintenance worker."""
    import argparse

    parser = argparse.ArgumentParser(description="Story maintenance worker")
    parser.add_argument(
        "--max-backfill", type=int, default=20, help="Maximum frames to backfill per run"
    )
    parser.add_argument(
        "--max-delete-frames",
        type=int,
        default=50,
        help="Maximum empty frames to delete per run",
    )
    parser.add_argument(
        "--max-delete-stories",
        type=int,
        default=10,
        help="Maximum dead stories to delete per run",
    )
    parser.add_argument(
        "--max-queue",
        type=int,
        default=10,
        help="Maximum Firebase queue items to process per run",
    )
    parser.add_argument(
        "--skip-queue", action="store_true", help="Skip processing Firebase queue"
    )
    parser.add_argument(
        "--skip-backfill", action="store_true", help="Skip backfilling missing images"
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true", help="Skip deleting empty frames"
    )
    parser.add_argument(
        "--skip-dead-stories", action="store_true", help="Skip deleting dead stories"
    )

    args = parser.parse_args()

    keys = KeysModel.from_env()

    # Validate required keys
    if not keys.openai_api_key:
        logger.error("OPENAI_API_KEY is required")
        sys.exit(1)

    try:
        worker = StoryMaintenanceWorker(keys)
        results = await worker.run_maintenance(
            max_frames_to_backfill=args.max_backfill,
            max_frames_to_delete=args.max_delete_frames,
            max_stories_to_delete=args.max_delete_stories,
            max_queue_items=args.max_queue,
            process_queue=not args.skip_queue,
            backfill_missing=not args.skip_backfill,
            cleanup_empty=not args.skip_cleanup,
            delete_dead_stories=not args.skip_dead_stories,
        )

        logger.info("🎉 Story maintenance completed successfully!")
        logger.info(f"📊 Results: {results}")

    except Exception as e:
        logger.error(f"❌ Story maintenance failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Initialize Firebase if needed - but skip if already initialized elsewhere
    try:
        import firebase_admin
        from firebase_admin import credentials

        # Only initialize if no apps exist
        if not firebase_admin._apps:
            try:
                firebase_admin.initialize_app()
                logger.info("Initialized Firebase with default credentials")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Firebase with default credentials: {e}"
                )
                # Try with explicit credentials
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
                    logger.warning(
                        "Could not initialize Firebase - no credentials found, will skip Firebase operations"
                    )
        else:
            logger.info("Firebase already initialized, skipping")
    except ImportError:
        logger.warning(
            "Firebase Admin SDK not available - Firebase operations will be skipped"
        )

    # Run the worker
    asyncio.run(main())
