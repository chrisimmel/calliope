"""
Firebase-based image backfill system for handling failed image generations.

This module provides utilities to queue failed image generations for retry,
process the backfill queue, and handle legacy frames without images.
"""

from datetime import datetime, timezone
import json
import logging
import traceback
from typing import Any, Dict, List, Optional

import httpx

from calliope.inference import text_to_image_file_inference
from calliope.models import FramesRequestParamsModel
from calliope.routes.v2.stories import put_story
from calliope.storage.config_manager import get_sparrow_story_parameters_and_keys
from calliope.tables import ModelConfig, Story, StoryFrame
from calliope.utils.file import create_sequential_filename
from calliope.utils.google import is_google_cloud_run_environment, put_media_file
from calliope.utils.image import get_image_attributes
from calliope.utils.text import translate_text

logger = logging.getLogger(__name__)


class ImageBackfillQueue:
    """Manages the Firestore-based image backfill queue."""

    COLLECTION_NAME = "image_backfill_queue"
    MAX_RETRIES = 5

    @classmethod
    def _get_firebase_manager(cls):
        """Get a Firebase manager instance."""
        from calliope.storage.firebase import get_firebase_manager

        return get_firebase_manager()

    @classmethod
    async def add_to_queue(
        cls,
        story_cuid: str,
        frame_number: int,
        image_prompt: str,
        strategy_config_slug: str,
        model_config_slug: str,
        client_id: str,
        output_image_width: Optional[int] = None,
        output_image_height: Optional[int] = None,
        force_replace: bool = False,
    ) -> None:
        """
        Add a failed image generation to the backfill queue.

        Args:
            story_cuid: The story CUID
            frame_number: The frame number
            image_prompt: The image generation prompt
            strategy_config_slug: The strategy config slug
            model_config_slug: The model config slug
            client_id: The client ID for file naming
            output_image_width: Desired image width
            output_image_height: Desired image height
            force_replace: If True, replace image even if frame already has one
        """
        queue_item_id = f"{story_cuid}_{frame_number}"
        queue_item = {
            "story_cuid": story_cuid,
            "frame_number": frame_number,
            "image_prompt": image_prompt,
            "strategy_config_slug": strategy_config_slug,
            "model_config_slug": model_config_slug,
            "client_id": client_id,
            "output_image_width": output_image_width,
            "output_image_height": output_image_height,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "last_attempt": None,
            "status": "pending",
            "force_replace": force_replace,
        }

        try:
            firebase_manager = cls._get_firebase_manager()
            doc_ref = firebase_manager.db.collection(cls.COLLECTION_NAME).document(
                queue_item_id
            )
            doc_ref.set(queue_item)
            logger.info(
                f"Added frame {frame_number} from story {story_cuid} to backfill queue"
            )
        except Exception as e:
            logger.error(f"Failed to add item to backfill queue: {e}")
            traceback.print_exc()

    @classmethod
    async def get_pending_items(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending items from the backfill queue.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of pending queue items
        """
        try:
            firebase_manager = cls._get_firebase_manager()
            collection_ref = firebase_manager.db.collection(cls.COLLECTION_NAME)

            # Simple query for pending items (no ordering to avoid index requirement)
            query = collection_ref.where("status", "==", "pending").limit(limit)
            docs = query.stream()

            pending_items = []
            for doc in docs:
                item_data = doc.to_dict()
                item_data["queue_item_id"] = doc.id
                pending_items.append(item_data)

            # Sort in Python by created_at if needed
            pending_items.sort(key=lambda x: x.get("created_at", ""))

            return pending_items
        except Exception as e:
            logger.error(f"Failed to get pending queue items: {e}")
            return []

    @classmethod
    async def mark_processing(cls, queue_item_id: str) -> None:
        """Mark a queue item as being processed."""
        try:
            firebase_manager = cls._get_firebase_manager()
            doc_ref = firebase_manager.db.collection(cls.COLLECTION_NAME).document(
                queue_item_id
            )
            doc_ref.update(
                {
                    "status": "processing",
                    "last_attempt": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to mark item as processing: {e}")

    @classmethod
    async def mark_completed(cls, queue_item_id: str) -> None:
        """Mark a queue item as completed and remove from queue."""
        try:
            firebase_manager = cls._get_firebase_manager()
            doc_ref = firebase_manager.db.collection(cls.COLLECTION_NAME).document(
                queue_item_id
            )
            doc_ref.delete()
            logger.info(f"Completed and removed queue item {queue_item_id}")
        except Exception as e:
            logger.error(f"Failed to mark item as completed: {e}")

    @classmethod
    async def mark_failed(cls, queue_item_id: str, error_message: str) -> None:
        """Mark a queue item as failed or increment retry count."""
        try:
            firebase_manager = cls._get_firebase_manager()
            doc_ref = firebase_manager.db.collection(cls.COLLECTION_NAME).document(
                queue_item_id
            )
            doc = doc_ref.get()

            if not doc.exists:
                return

            item_data = doc.to_dict()
            retry_count = item_data.get("retry_count", 0) + 1

            if retry_count >= cls.MAX_RETRIES:
                # Max retries reached, mark as permanently failed
                doc_ref.update(
                    {
                        "status": "failed",
                        "retry_count": retry_count,
                        "last_attempt": datetime.now(timezone.utc).isoformat(),
                        "error_message": error_message,
                    }
                )
                logger.warning(
                    f"Queue item {queue_item_id} permanently failed after {retry_count} attempts"
                )
            else:
                # Increment retry count and reset to pending
                doc_ref.update(
                    {
                        "status": "pending",
                        "retry_count": retry_count,
                        "last_attempt": datetime.now(timezone.utc).isoformat(),
                        "last_error": error_message,
                    }
                )
                logger.info(
                    f"Queue item {queue_item_id} retry {retry_count}/{cls.MAX_RETRIES}"
                )
        except Exception as e:
            logger.error(f"Failed to mark item as failed: {e}")

    @classmethod
    async def process_queue_item(
        cls,
        queue_item: Dict[str, Any],
        httpx_client: httpx.AsyncClient,
    ) -> bool:
        """
        Process a single backfill queue item.

        Args:
            queue_item: The queue item data
            httpx_client: HTTP client

        Returns:
            True if successful, False if failed
        """
        queue_item_id = queue_item["queue_item_id"]
        story_cuid = queue_item["story_cuid"]
        frame_number = queue_item["frame_number"]

        try:
            # Mark as processing
            await cls.mark_processing(queue_item_id)

            # Get the story frame
            story_frame = (
                await StoryFrame.objects()
                .where(
                    StoryFrame.story.cuid == story_cuid,
                    StoryFrame.number == frame_number,
                )
                .first()
                .run()
            )

            if not story_frame:
                logger.error(f"Story frame not found: {story_cuid} frame {frame_number}")
                await cls.mark_failed(queue_item_id, "Story frame not found")
                return False

            # Check if frame already has an image and if we should skip
            force_replace = queue_item.get("force_replace", False)
            if story_frame.image and not force_replace:
                # Before skipping, check if we need to patch missing source_image
                if not story_frame.source_image:
                    logger.info(
                        f"Patching missing source_image for frame {story_cuid} frame {frame_number}"
                    )
                    story_frame.source_image = story_frame.image
                    story_frame.date_updated = datetime.now(timezone.utc)
                    await story_frame.save().run()
                    logger.info(
                        f"✅ Patched source_image for frame {story_cuid} frame {frame_number}"
                    )
                else:
                    logger.info(
                        f"Frame already has image, skipping: {story_cuid} frame {frame_number}"
                    )

                await cls.mark_completed(queue_item_id)
                return True

            # Load API keys using the config manager
            # Extract base strategy name from config slug for config manager
            strategy_config_slug = queue_item["strategy_config_slug"]

            # For the config manager, we should use the strategy config slug directly
            # since that's what get_sparrow_story_parameters_and_keys expects
            strategy_name = strategy_config_slug

            request_params = FramesRequestParamsModel(
                client_id=queue_item["client_id"], strategy=strategy_name
            )

            try:
                _, keys, _ = await get_sparrow_story_parameters_and_keys(request_params)
            except Exception as e:
                logger.error(
                    f"Failed to load keys for client {queue_item['client_id']}: {e}"
                )
                await cls.mark_failed(queue_item_id, f"Failed to load API keys: {e}")
                return False

            # Get the model config for image generation
            model_config = (
                await ModelConfig.objects(ModelConfig.model)
                .where(ModelConfig.slug == queue_item["model_config_slug"])
                .first()
                .output(load_json=True)
                .run()
            )

            if not model_config:
                logger.error(
                    f"Model config not found: {queue_item['model_config_slug']}"
                )
                await cls.mark_failed(queue_item_id, "Model config not found")
                return False

            # Generate the image
            output_image_filename = create_sequential_filename(
                "media", queue_item["client_id"], "out", "png", story_cuid, frame_number
            )

            await text_to_image_file_inference(
                httpx_client,
                queue_item["image_prompt"],
                output_image_filename,
                model_config,
                keys,
                queue_item.get("output_image_width"),
                queue_item.get("output_image_height"),
            )

            # Update the story frame with the new image
            image_obj = get_image_attributes(output_image_filename)
            image_obj.date_updated = datetime.now(timezone.utc)
            await image_obj.save().run()

            # Push image to Cloud Storage if in production
            is_google_cloud = is_google_cloud_run_environment()
            if is_google_cloud:
                logger.info(f"Uploading image to Cloud Storage: {image_obj.url}")
                try:
                    put_media_file(image_obj.url)
                    logger.info("✅ Successfully uploaded image to Cloud Storage")
                except Exception as cloud_error:
                    logger.error(
                        f"❌ Failed to upload image to Cloud Storage: {cloud_error}"
                    )
                    # Continue anyway - the image exists locally and may work

            # Set both image and source_image fields (both are needed for proper display)
            story_frame.image = image_obj
            story_frame.source_image = image_obj  # Thoth uses source_image for display
            story_frame.date_updated = datetime.now(timezone.utc)
            await story_frame.save().run()

            # Update story thumbnail if needed (frame 0 and story has no thumbnail)
            if frame_number == 0:
                story = (
                    await Story.objects().where(Story.cuid == story_cuid).first().run()
                )
                if story:
                    logger.info(
                        f"Updating story thumbnail from frame 0 for story {story_cuid}"
                    )
                    thumbnail_image = await story.compute_thumbnail()
                    # This doesn't actually generate a new image file, so we don't need
                    # to push an image to GCS.
                    if thumbnail_image:
                        # But we do need to save to the database.
                        await thumbnail_image.save().run()

                        story.thumbnail_image = thumbnail_image
                        logger.info(f"Computed story thumbnail: '{thumbnail_image}'")
                        await put_story(story)

                    logger.info(f"✅ Updated story thumbnail for story {story_cuid}")

            # Notify clients via Firebase (optional)
            try:
                from calliope.storage.firebase import get_firebase_manager

                firebase = get_firebase_manager()
                await firebase.add_story_update(
                    story_cuid,
                    {
                        "type": "frame_image_added",
                        "frame_number": frame_number,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "image_url": image_obj.url
                        if hasattr(image_obj, "url")
                        else None,
                    },
                )
                logger.info(
                    f"Sent Firebase notification for story {story_cuid} frame {frame_number}"
                )
            except Exception as firebase_error:
                logger.warning(
                    f"Failed to send Firebase notification (this is optional): {firebase_error}"
                )

            # Mark as completed
            await cls.mark_completed(queue_item_id)
            logger.info(
                f"✅ Successfully backfilled image for story {story_cuid} frame {frame_number}"
            )
            return True

        except Exception as e:
            error_msg = f"Image generation failed: {e!s}"
            logger.error(
                f"❌ Backfill failed for {story_cuid} frame {frame_number}: {error_msg}"
            )
            await cls.mark_failed(queue_item_id, error_msg)
            return False


async def scan_and_queue_legacy_frames(limit: Optional[int] = None) -> int:
    """
    Scan for legacy frames without images and add them to the backfill queue.

    Args:
        keys: API keys for accessing models
        limit: Optional limit on number of frames to process

    Returns:
        Number of frames added to queue
    """
    try:
        query = StoryFrame.objects().where(StoryFrame.image.is_null())
        if limit:
            query = query.limit(limit)

        frames_without_images = await query.run()
        queued_count = 0

        for frame in frames_without_images:
            try:
                # Get the story to extract client_id and other metadata
                story = (
                    await Story.objects().where(Story.id == frame.story).first().run()
                )
                if not story:
                    continue

                # Extract original config from frame metadata
                # Handle both dict and string (JSON) formats for legacy compatibility
                metadata = frame.metadata or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(
                            f"Failed to parse metadata for frame {frame.id}: {e}"
                        )
                        metadata = {}

                # Try modern format first, then legacy format
                strategy_config_slug = metadata.get("strategy_config")
                model_config_slug = metadata.get("text_to_image_model_config")

                # Handle legacy format where strategy is in parameters.strategy
                if not strategy_config_slug:
                    parameters = metadata.get("parameters", {})
                    if isinstance(parameters, str):
                        try:
                            parameters = json.loads(parameters)
                        except (json.JSONDecodeError, TypeError):
                            parameters = {}

                    legacy_strategy = parameters.get("strategy")
                    if legacy_strategy:
                        # Map legacy strategy names to current config slugs
                        legacy_mapping = {
                            "continuous": "continuous-v1-gpt-4",  # Old 'continuous' strategy
                            "continuous_v0": "continuous-v1-gpt-4",  # Use similar strategy
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

                # Use default model config if not specified
                if not model_config_slug:
                    model_config_slug = "stability-stable-diffusion-1.6"

                if not strategy_config_slug:
                    logger.warning(
                        f"Cannot determine strategy for frame {frame.id}, skipping"
                    )
                    continue

                # Try to reconstruct the image prompt from frame text and strategy
                image_prompt = await reconstruct_image_prompt(
                    frame,
                    metadata,
                )
                if not image_prompt:
                    logger.warning(
                        f"Could not reconstruct image prompt for frame {frame.id}, skipping"
                    )
                    continue

                # Extract client_id from story state_props or use story cuid
                # Handle both dict and string formats for story state_props too
                story_state_props = story.state_props or {}
                if isinstance(story_state_props, str):
                    try:
                        story_state_props = json.loads(story_state_props)
                    except (json.JSONDecodeError, TypeError):
                        story_state_props = {}

                client_id = (
                    story_state_props.get("client_id")
                    if story_state_props
                    else story.cuid
                )

                await ImageBackfillQueue.add_to_queue(
                    story_cuid=story.cuid,
                    frame_number=frame.number,
                    image_prompt=image_prompt,
                    strategy_config_slug=strategy_config_slug,
                    model_config_slug=model_config_slug,
                    client_id=client_id,
                )

                queued_count += 1
                logger.info(f"Queued legacy frame {story.cuid} frame {frame.number}")

            except Exception as e:
                logger.error(f"Failed to queue legacy frame {frame.id}: {e}")
                continue

        logger.info(f"Queued {queued_count} legacy frames for image backfill")
        return queued_count

    except Exception as e:
        logger.error(f"Failed to scan legacy frames: {e}")
        return 0


async def reconstruct_image_prompt(
    frame: StoryFrame,
    metadata: Dict[str, Any],
) -> Optional[str]:
    """
    Reconstruct the image prompt that would have been used for this frame.

    Args:
        frame: The story frame
        story: The story object
        metadata: Frame metadata
        strategy_config_slug: Strategy config slug to check target language

    Returns:
        Reconstructed image prompt or None if can't be determined
    """
    try:
        # Get the original parameters used for this frame
        parameters = metadata.get("parameters", {})
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except (json.JSONDecodeError, TypeError):
                parameters = {}

        # Get image style from parameters or use default
        output_image_style = parameters.get(
            "output_image_style", "A watercolor, paper texture."
        )

        # Try multiple sources for the image prompt content
        image_content = None

        # First, try to use the frame text.
        frame_text = frame.text or ""
        if frame_text.strip():
            image_content = frame_text

            # Translate to English in case target language is not English
            if image_content:
                try:
                    logger.info("Translating frame text to English")
                    image_content = translate_text("en", image_content)
                    logger.info("Translation successful")
                except Exception as e:
                    logger.warning(f"Translation failed, using original text: {e}")
                    # Continue with original text if translation fails

        i_see = metadata.get("i_see")
        if not image_content and i_see:
            # Fall back to i_see if available.
            if isinstance(i_see, str):
                image_content = i_see  # Use the vision description
            elif isinstance(i_see, dict):
                # Handle structured i_see data
                captions = i_see.get("captions", [])
                if captions and isinstance(captions, list):
                    image_content = captions[0]
                else:
                    # Fall back to tags if available
                    tags = i_see.get("tags", [])
                    if tags and isinstance(tags, list):
                        image_content = ", ".join(tags[:5])  # Use first 5 tags

        # Final fallback: use a generic prompt
        if not image_content:
            image_content = "abstract artistic composition"

        # Combine style and content
        image_prompt = f"{output_image_style} {image_content}".strip()

        # Clean up the prompt - remove extra whitespace
        image_prompt = " ".join(image_prompt.split())

        return image_prompt if image_prompt else None

    except Exception as e:
        logger.error(f"Failed to reconstruct image prompt for frame {frame.id}: {e}")
        return None
