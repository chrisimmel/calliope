"""
Task handlers for background processing in Calliope.

This module contains handler functions for different task types
that are executed asynchronously by the task queue.
"""

import logging
from typing import Dict, Any
import uuid
import os
from datetime import datetime

from .local_queue import LocalTaskQueue
from ..storage.state_manager import StateManager
from ..strategies.registry import get_strategy
from ..inference import text_to_image
from ..storage.firebase import get_firebase_manager

logger = logging.getLogger(__name__)


async def create_story_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new story and generate initial content

    Args:
        payload: Task payload containing:
            - client_id: Client identifier
            - strategy_name: Strategy to use for generation
            - title: Optional story title
            - generate_image: Whether to generate an image

    Returns:
        Dictionary with story details
    """
    client_id = payload.get("client_id")
    strategy_name = payload.get("strategy_name")
    title = payload.get("title")

    logger.info(f"Creating story with strategy {strategy_name} for client {client_id}")

    # Get Firebase manager
    firebase = get_firebase_manager()

    # Create a new story in the database
    state_manager = StateManager()

    # Check if story_id is provided (for continuation)
    story_id = payload.get("story_id")
    if not story_id:
        # Create new story
        story = await state_manager.create_story(
            client_id=client_id, strategy=strategy_name, title=title
        )
        story_id = story["story_id"]
        logger.info(f"Created new story with ID: {story_id}")
    else:
        # Get existing story
        story = await state_manager.get_story(story_id)
        if not story:
            logger.error(f"Story {story_id} not found")
            # Update Firebase with error status
            await firebase.update_story_status(
                story_id,
                {
                    "status": "error",
                    "error": f"Story {story_id} not found",
                    "error_time": datetime.now().isoformat(),
                },
            )
            raise ValueError(f"Story {story_id} not found")

        logger.info(f"Continuing existing story with ID: {story_id}")

    # Update Firebase with progress
    await firebase.update_story_status(
        story_id,
        {
            "status": "generating_content",
            "progress": "Loading strategy",
            "updated_at": datetime.now().isoformat(),
        },
    )

    # Load the appropriate strategy
    strategy = get_strategy(strategy_name)
    if not strategy:
        logger.error(f"Strategy {strategy_name} not found")
        # Update Firebase with error status
        await firebase.update_story_status(
            story_id,
            {
                "status": "error",
                "error": f"Strategy {strategy_name} not found",
                "error_time": datetime.now().isoformat(),
            },
        )
        raise ValueError(f"Strategy {strategy_name} not found")

    # Generate initial content
    try:
        logger.info(f"Generating initial content for story {story_id}")

        # Update Firebase with progress
        await firebase.update_story_status(
            story_id,
            {
                "status": "generating_content",
                "progress": "Generating text content",
                "updated_at": datetime.now().isoformat(),
            },
        )

        content = await strategy.generate_initial_frame(story)

        # Generate image if requested
        if payload.get("generate_image", True):
            logger.info(f"Generating image for story {story_id}")

            # Update Firebase with progress
            await firebase.update_story_status(
                story_id,
                {
                    "status": "generating_content",
                    "progress": "Generating image",
                    "updated_at": datetime.now().isoformat(),
                },
            )

            image_prompt = content.get("image_prompt", content.get("text", ""))

            # Create a unique filename for the image
            image_filename = f"generated_{uuid.uuid4()}.png"

            # Generate the image
            image_result = await text_to_image.generate(
                prompt=image_prompt, filename=image_filename
            )

            # Add image data to content
            if image_result and "url" in image_result:
                content["image"] = image_result
                logger.info(
                    f"Added image to story {story_id}: {image_result.get('url')}"
                )

                # Add image info to Firebase
                await firebase.add_story_update(
                    story_id,
                    {
                        "type": "image_generated",
                        "timestamp": datetime.now().isoformat(),
                        "image_url": image_result.get("url"),
                        "prompt": image_prompt[:100],  # Truncate long prompts
                    },
                )

        # Update the story with new content
        logger.info(f"Adding frame to story {story_id}")
        updated_story = await state_manager.add_frame(story_id, content)

        # Update Firebase with completion status
        await firebase.update_story_status(
            story_id,
            {
                "status": "completed",
                "frame_count": updated_story.get("frame_count", 1),
                "completed_at": datetime.now().isoformat(),
            },
        )

        # Add completion update
        await firebase.add_story_update(
            story_id,
            {
                "type": "frame_added",
                "timestamp": datetime.now().isoformat(),
                "frame_number": updated_story.get("frame_count", 1),
                "has_image": "image" in content and "url" in content["image"],
            },
        )

        return {
            "story_id": story_id,
            "frame_added": True,
            "frame_count": updated_story.get("frame_count", 1),
        }
    except Exception as e:
        logger.exception(f"Error generating content for story {story_id}: {str(e)}")
        # Update Firebase with error status
        await firebase.update_story_status(
            story_id,
            {
                "status": "error",
                "error": str(e),
                "error_time": datetime.now().isoformat(),
            },
        )
        raise


async def generate_story_snippet(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a new snippet for an existing story

    Args:
        payload: Task payload containing:
            - story_id: Story identifier
            - strategy_name: Strategy to use for generation
            - generate_image: Whether to generate an image
            - user_input: Optional user input to influence generation

    Returns:
        Dictionary with snippet details
    """
    story_id = payload.get("story_id")
    if not story_id:
        raise ValueError("story_id is required")

    # Get Firebase manager
    firebase = get_firebase_manager()

    state_manager = StateManager()
    story = await state_manager.get_story(story_id)

    if not story:
        logger.error(f"Story {story_id} not found")
        # Update Firebase with error status
        await firebase.update_story_status(
            story_id,
            {
                "status": "error",
                "error": f"Story {story_id} not found",
                "error_time": datetime.now().isoformat(),
            },
        )
        raise ValueError(f"Story {story_id} not found")

    strategy_name = payload.get("strategy_name", story.get("strategy"))
    user_input = payload.get("user_input")

    logger.info(
        f"Generating snippet for story {story_id} with strategy {strategy_name}"
    )

    # Update Firebase with progress
    await firebase.update_story_status(
        story_id,
        {
            "status": "generating_content",
            "progress": "Loading strategy",
            "updated_at": datetime.now().isoformat(),
        },
    )

    # Load the appropriate strategy
    strategy = get_strategy(strategy_name)
    if not strategy:
        logger.error(f"Strategy {strategy_name} not found")
        # Update Firebase with error status
        await firebase.update_story_status(
            story_id,
            {
                "status": "error",
                "error": f"Strategy {strategy_name} not found",
                "error_time": datetime.now().isoformat(),
            },
        )
        raise ValueError(f"Strategy {strategy_name} not found")

    try:
        # Generate new content
        # Update Firebase with progress
        await firebase.update_story_status(
            story_id,
            {
                "status": "generating_content",
                "progress": "Generating text content",
                "updated_at": datetime.now().isoformat(),
            },
        )

        context = {"user_input": user_input} if user_input else {}
        content = await strategy.generate_next_frame(story, context)

        # Generate image if requested
        if payload.get("generate_image", True):
            logger.info(f"Generating image for story snippet in {story_id}")

            # Update Firebase with progress
            await firebase.update_story_status(
                story_id,
                {
                    "status": "generating_content",
                    "progress": "Generating image",
                    "updated_at": datetime.now().isoformat(),
                },
            )

            image_prompt = content.get("image_prompt", content.get("text", ""))

            # Create a unique filename for the image
            image_filename = f"generated_{uuid.uuid4()}.png"

            # Generate the image
            image_result = await text_to_image.generate(
                prompt=image_prompt, filename=image_filename
            )

            # Add image data to content
            if image_result and "url" in image_result:
                content["image"] = image_result
                logger.info(
                    f"Added image to snippet in story {story_id}: {image_result.get('url')}"
                )

                # Add image info to Firebase
                await firebase.add_story_update(
                    story_id,
                    {
                        "type": "image_generated",
                        "timestamp": datetime.now().isoformat(),
                        "image_url": image_result.get("url"),
                        "prompt": image_prompt[:100],  # Truncate long prompts
                    },
                )

        # Update the story with new content
        logger.info(f"Adding snippet to story {story_id}")
        updated_story = await state_manager.add_frame(story_id, content)

        # Update Firebase with completion status
        await firebase.update_story_status(
            story_id,
            {
                "status": "completed",
                "frame_count": updated_story.get("frame_count", 0),
                "completed_at": datetime.now().isoformat(),
            },
        )

        # Add completion update
        await firebase.add_story_update(
            story_id,
            {
                "type": "frame_added",
                "timestamp": datetime.now().isoformat(),
                "frame_number": updated_story.get("frame_count", 0),
                "has_image": "image" in content and "url" in content["image"],
            },
        )

        return {
            "story_id": story_id,
            "snippet_added": True,
            "frame_count": updated_story.get("frame_count", 0),
        }
    except Exception as e:
        logger.exception(f"Error generating snippet for story {story_id}: {str(e)}")
        # Update Firebase with error status
        await firebase.update_story_status(
            story_id,
            {
                "status": "error",
                "error": str(e),
                "error_time": datetime.now().isoformat(),
            },
        )
        raise


async def analyze_image(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze an image and generate a description

    Args:
        payload: Task payload containing:
            - image_url: URL of the image to analyze
            - story_id: Optional story identifier to associate with

    Returns:
        Dictionary with analysis results
    """
    image_url = payload.get("image_url")
    if not image_url:
        raise ValueError("image_url is required")

    story_id = payload.get("story_id")

    # Get Firebase manager if we have a story ID
    firebase = None
    if story_id:
        firebase = get_firebase_manager()
        # Update Firebase with progress
        await firebase.update_story_status(
            story_id,
            {
                "status": "analyzing_image",
                "image_url": image_url,
                "started_at": datetime.now().isoformat(),
            },
        )

    logger.info(f"Analyzing image {image_url} for story {story_id}")

    try:
        # Import image analysis module
        from ..inference.image_analysis import analyze_image as analyze

        # Analyze the image
        analysis = await analyze(image_url)

        # If story_id is provided, store the result
        if story_id:
            state_manager = StateManager()
            story = await state_manager.get_story(story_id)

            if story:
                # Store analysis as a metadata update
                await state_manager.update_story_metadata(
                    story_id, {"image_analysis": analysis}
                )

                # Update Firebase with result
                if firebase:
                    # Update status
                    await firebase.update_story_status(
                        story_id,
                        {
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                        },
                    )

                    # Add analysis update
                    await firebase.add_story_update(
                        story_id,
                        {
                            "type": "image_analyzed",
                            "timestamp": datetime.now().isoformat(),
                            "image_url": image_url,
                            "analysis_summary": analysis.get("description", "")[
                                :200
                            ],  # Truncate long descriptions
                        },
                    )

        return {"image_url": image_url, "analysis": analysis, "story_id": story_id}
    except Exception as e:
        logger.exception(f"Error analyzing image {image_url}: {str(e)}")

        # Update Firebase with error if we have a story ID
        if story_id and firebase:
            await firebase.update_story_status(
                story_id,
                {
                    "status": "error",
                    "error": f"Error analyzing image: {str(e)}",
                    "error_time": datetime.now().isoformat(),
                },
            )

        raise


def is_development_environment() -> bool:
    """
    Check if the current environment is development

    Returns:
        True if running in development environment, False otherwise
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    return env != "production"


def register_handlers(task_queue: LocalTaskQueue):
    """
    Register all task handlers with the queue

    Args:
        task_queue: The LocalTaskQueue instance to register handlers with
    """
    task_queue.register_handler("create_story", create_story_task)
    task_queue.register_handler("generate_story_snippet", generate_story_snippet)
    task_queue.register_handler("analyze_image", analyze_image)

    logger.info("Registered task handlers with the queue")
