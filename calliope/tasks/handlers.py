"""
Task handlers for background processing in Calliope.

This module contains handler functions for different task types
that are executed asynchronously by the task queue.
"""

import logging
import sys
import traceback
from typing import Any, Dict

import httpx

from calliope.inference import image_analysis_inference
from calliope.inference.audio_to_text import audio_to_text_inference
from calliope.location.location import get_location_metadata_for_ip
from calliope.models import FramesRequestParamsModel
from calliope.storage.config_manager import (
    get_sparrow_story_parameters_and_keys,
    load_json_if_necessary,
)
from calliope.storage.firebase import get_firebase_manager
from calliope.storage.state_manager import (
    get_sparrow_state,
    get_story,
    put_sparrow_state,
    put_story,
)
from calliope.strategies import StoryStrategyRegistry
from calliope.tables import ModelConfig
from calliope.tasks.local_queue import LocalTaskQueue
from calliope.utils.google import CLOUD_ENV_GCP_PROD, get_cloud_environment
from calliope.utils.story import prepare_frame_images, prepare_input_files

logger = logging.getLogger(__name__)


def prepare_frame_request_params(
    payload: Dict[str, Any], strategy_name: str
) -> FramesRequestParamsModel:
    """
    Prepare the request parameters for frame generation.

    Returns:
        FramesRequestParamsModel: The prepared request parameters.
    """
    story_id = payload.get("story_id")
    client_id = payload.get("client_id")
    snippets = payload.get("snippets", [])

    request_params = FramesRequestParamsModel(
        story_id=story_id,
        client_id=client_id,
        strategy=strategy_name,
        extra_fields=payload.get("extra_fields", {}),
        debug=True,
    )

    for snippet in snippets:
        # Add snippets to request parameters based on type.
        # (Can only handle one snippet of each type for now due to v1 limitations.)
        if snippet.get("snippet_type") == "image":
            request_params.input_image = snippet.get("content")
        elif snippet.get("snippet_type") == "audio":
            request_params.input_audio = snippet.get("content")
        elif snippet.get("snippet_type") == "text":
            request_params.input_text = snippet.get("content")

    return request_params


async def add_frame_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a new frame to an existing story

    Args:
        payload: Task payload containing:
            - story_id: Story cuid
            - client_id: The requesting client
            - snippets: Any snippets to use when creating the frame
    Returns:
        Dictionary with new frame details
    """
    story_id = payload.get("story_id")
    client_id = payload.get("client_id")
    source_ip_address = payload.get("source_ip_address")

    if not story_id or not client_id:
        raise ValueError("story_id and client_id are required")

    logger.info(f"Adding frame to story {story_id}")

    # Get Firebase manager
    firebase = get_firebase_manager()

    # Update task status to running
    task_id = payload.get("_task_id")
    if task_id:
        await firebase.update_task(task_id, {"status": "running"})

    try:
        sparrow_state = await get_sparrow_state(client_id)
        story = await get_story(story_id) if story_id else None
        strategy_name = (story and story.strategy_name) or "tamarisk"

        request_params = prepare_frame_request_params(
            payload=payload, strategy_name=strategy_name
        )
        (
            parameters,
            keys,
            strategy_config,
        ) = await get_sparrow_story_parameters_and_keys(request_params)
        parameters.strategy = parameters.strategy or "tamarisk"
        parameters.debug = parameters.debug or False

        strategy_class = StoryStrategyRegistry.get_strategy_class(strategy_name)

        parameters = await prepare_input_files(parameters, story)
        image_analysis = None
        errors = []

        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            location_metadata = await get_location_metadata_for_ip(
                httpx_client,
                source_ip_address,
            )
            print(f"{location_metadata=}")

            if parameters.input_image_filename:
                print(f"{parameters.input_image_filename=}")
                vision_model_slug = "azure-vision-analysis"
                model_config = (
                    await ModelConfig.objects(ModelConfig.model)
                    .where(ModelConfig.slug == vision_model_slug)
                    .first()
                    .output(load_json=True)
                    .run()
                )
                if (
                    model_config
                    and model_config.model
                    and model_config.model.model_parameters
                ):
                    model_config.model.model_parameters = load_json_if_necessary(
                        model_config.model.model_parameters
                    )
                try:
                    image_analysis = await image_analysis_inference(
                        httpx_client,
                        parameters.input_image_filename,
                        parameters.input_image,  # original b64-encoded image.
                        model_config,
                        keys,
                    )
                    print(f"{image_analysis=}")

                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    errors.append(str(e))

            language = "en"
            if (
                strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config.prompt_template
                and strategy_config.text_to_text_model_config.prompt_template.target_language
            ):
                language = strategy_config.text_to_text_model_config.prompt_template.target_language

            if parameters.input_audio_filename:
                text = await audio_to_text_inference(
                    httpx_client, parameters.input_audio_filename, language, keys
                )
                parameters.input_text = text

            story_frames_response = await strategy_class().get_frame_sequence(
                parameters,
                image_analysis,
                location_metadata,
                strategy_config,
                keys,
                sparrow_state,
                story,
                httpx_client,
            )
            if story.title == "Untitled":
                story.title = story_frames_response.frames[0].title

        story_frames_response.debug_data = {
            **(story_frames_response.debug_data or {}),
            "story_id": story.cuid,
            "story_title": story.title,
        }
        if image_analysis:
            i_see = image_analysis.get("description")
            story_frames_response.debug_data["i_see"] = i_see
            story_frames_response.debug_data["image_analysis"] = image_analysis
        if parameters.input_audio_filename and parameters.input_text:
            i_hear = parameters.input_text
            story_frames_response.debug_data["i_hear"] = i_hear

        await prepare_frame_images(parameters, story_frames_response.frames)
        await put_story(story)
        await put_sparrow_state(sparrow_state)

        num_frames = await story.get_num_frames()

        # Update task status to completed with results
        if task_id:
            await firebase.update_task(
                task_id,
                {
                    "status": "completed",
                    "result": {
                        "frames_added": len(story_frames_response.frames),
                        "new_frame_count": num_frames,
                    },
                },
            )

        # Update story with new frame count and full harmonized schema
        await firebase.update_story_fields(
            story_id,
            {
                "cuid": story.cuid,
                "title": story.title,
                "slug": story.slug,
                "strategy_name": story.strategy_name,
                "created_for_sparrow_id": story.created_for_sparrow_id,
                "thumbnail_image": None,  # TODO: Handle thumbnail conversion
                "state_props": story.state_props,
                "date_created": story.date_created.isoformat(),
                "date_updated": story.date_updated.isoformat(),
                "frame_count": num_frames,
            },
        )

        # Add a frame_added update for Clio to detect new frames
        frames_added_count = len(story_frames_response.frames)
        if frames_added_count > 0:
            # Use the last frame number for the update (in case multiple frames were added)
            latest_frame_number = num_frames - 1
            await firebase.add_story_update(
                story_id,
                {
                    "type": "frame_added",
                    "frame_number": latest_frame_number,
                    "frames_added_count": frames_added_count,
                    "new_frame_count": num_frames,
                },
            )

        frame_models = [frame.to_pydantic() for frame in story_frames_response.frames]
        return {
            "story_id": story_id,
            "frames_added": frame_models,
            "frame_count": num_frames,
        }

    except Exception as e:
        logger.exception(f"Error generating content for story {story_id}: {e!s}")
        # Update task status to failed
        if task_id:
            await firebase.update_task(
                task_id,
                {
                    "status": "failed",
                    "error": str(e),
                },
            )
        raise


def is_development_environment() -> bool:
    """
    Check if the current environment is development

    Returns:
        True if running in development environment, False otherwise
    """
    is_production = get_cloud_environment() == CLOUD_ENV_GCP_PROD
    return not is_production


def register_handlers(task_queue: LocalTaskQueue):
    """
    Register all task handlers with the queue

    Args:
        task_queue: The LocalTaskQueue instance to register handlers with
    """
    task_queue.register_handler("add_frame", add_frame_task)
    # task_queue.register_handler("generate_story_snippet", generate_story_snippet)
    # task_queue.register_handler("analyze_image", analyze_image)

    logger.info("Registered task handlers with the queue")
