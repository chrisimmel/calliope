"""
V2 Story API with asynchronous processing.

This module provides endpoints for creating and managing stories with
asynchronous background processing for time-consuming operations.
Uses Firebase Realtime Database for real-time updates.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from calliope.storage.state_manager import (
    put_story,
)
from calliope.tables import Story
from calliope.tasks.factory import configure_task_queue
from calliope.tasks.queue import TaskQueue
from calliope.storage.firebase import get_firebase_manager, FirebaseManager

from calliope.routes.v2.models import CreateStoryRequest, AddSnippetsRequest

logger = logging.getLogger(__name__)

# --- Additional Pydantic Models ---


class CreateStoryResponse(BaseModel):
    """Response for story creation"""

    story_id: str
    message: str
    task_id: Optional[str] = None


# --- Router Setup ---
router = APIRouter(prefix="/v2/stories", tags=["stories_v2"])


# Configure task queue dependency
def get_task_queue() -> TaskQueue:
    """Dependency for getting the configured task queue"""
    return configure_task_queue()


# Configure Firebase dependency
def get_firebase() -> FirebaseManager:
    """Dependency for getting the Firebase manager"""
    return get_firebase_manager()


# --- Endpoint Implementations ---

"""
create_story:
   creates story
   requests initial frame (with optional snippets)

add_frame:
    requests a frame (with optional snippets)

illustrate_frame:
    requests a new illustration for an existing frame

clean_story:
    cleans up a story
    - remove empty frames
    - add illustrations where missing
    - fix common formatting issues

"""


@router.post("/", response_model=CreateStoryResponse)
async def create_story(
    request_data: CreateStoryRequest,
    task_queue: TaskQueue = Depends(get_task_queue),
    firebase: FirebaseManager = Depends(get_firebase),
):
    """
    Create a new story and optionally start processing initial snippets

    This endpoint creates a new story record and then asynchronously
    processes any provided snippets to generate initial story content.
    """
    try:
        # Create the story record in the database
        story = Story.create_new(
            strategy_name=request_data.strategy,
            created_for_sparrow_id=request_data.client_id,
            title=request_data.title,
        )
        new_story_id = story.cuid
        await put_story(story)
        logger.info(f"Created new story with ID: {new_story_id}")

        # Initialize Firebase entry for this story
        await firebase.update_story_status(
            new_story_id,
            {
                "status": "created",
                "title": request_data.title,
                "created_at": datetime.now().isoformat(),
                "client_id": request_data.client_id,
                "strategy": request_data.strategy,
                "frame_count": 0,
            },
        )

        message_parts = [f"Story {new_story_id} created."]
        task_id = None

        # If snippets were provided, enqueue a task to process them
        if request_data.snippets:
            # Convert snippets to the format expected by task handlers
            snippet_data = []
            for snippet in request_data.snippets:
                snippet_data.append(snippet.model_dump(exclude_unset=True))

            # Create a task payload
            task_payload = {
                "story_id": new_story_id,
                "client_id": request_data.client_id,
                "strategy_name": request_data.strategy,
                "snippets": snippet_data,
                "generate_image": True,  # Default to generating images
            }

            # Enqueue the task
            task_id = await task_queue.enqueue(
                task_type="create_story", payload=task_payload
            )

            # Update Firebase with task info
            await firebase.update_story_status(
                new_story_id,
                {
                    "status": "processing",
                    "task_id": task_id,
                    "processing_started_at": datetime.now().isoformat(),
                },
            )

            logger.info(
                f"Story {new_story_id}: Enqueued task {task_id} to process {len(request_data.snippets)} initial snippets"
            )
            message_parts.append("Initial snippets will be processed asynchronously.")
        else:
            # If no snippets, we might still want to generate initial content
            # based on the strategy
            task_payload = {
                "story_id": new_story_id,
                "client_id": request_data.client_id,
                "strategy_name": request_data.strategy,
                "generate_image": True,
            }

            # Enqueue the task
            task_id = await task_queue.enqueue(
                task_type="create_story", payload=task_payload
            )

            # Update Firebase with task info
            await firebase.update_story_status(
                new_story_id,
                {
                    "status": "processing",
                    "task_id": task_id,
                    "processing_started_at": datetime.now().isoformat(),
                },
            )

            logger.info(
                f"Story {new_story_id}: Enqueued task {task_id} to generate initial content"
            )
            message_parts.append("Initial content will be generated asynchronously.")

        return CreateStoryResponse(
            story_id=new_story_id, message=" ".join(message_parts), task_id=task_id
        )

    except Exception as e:
        logger.exception(f"Error creating story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create story: {str(e)}")


@router.post("/{story_id}/snippets/")
async def add_snippets(
    story_id: str,
    request_data: AddSnippetsRequest,
    task_queue: TaskQueue = Depends(get_task_queue),
    firebase: FirebaseManager = Depends(get_firebase),
):
    """
    Add new snippets to an existing story

    This endpoint validates that the story exists and then asynchronously
    processes the provided snippets to generate new story content.
    """
    try:
        # Verify the story exists
        story = await Story.objects().where(Story.cuid == story_id).first()
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story with id {story_id} not found"
            )

        # Convert snippets to the format expected by task handlers
        snippet_data = []
        for snippet in request_data.snippets:
            snippet_data.append(snippet.model_dump(exclude_unset=True))

        # Create a task payload
        task_payload = {
            "story_id": story_id,
            "strategy_name": story.strategy_name,
            "snippets": snippet_data,
            "generate_image": True,  # Default to generating images
        }

        # Enqueue the task
        task_id = await task_queue.enqueue(
            task_type="generate_story_snippet", payload=task_payload
        )

        # Update Firebase with task info
        await firebase.update_story_status(
            story_id,
            {
                "status": "processing",
                "task_id": task_id,
                "processing_started_at": datetime.now().isoformat(),
            },
        )

        # Add an update to the story updates list
        await firebase.add_story_update(
            story_id,
            {
                "type": "snippet_requested",
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "snippet_count": len(request_data.snippets),
            },
        )

        logger.info(
            f"Story {story_id}: Enqueued task {task_id} to process {len(request_data.snippets)} snippets"
        )

        return {
            "message": "Snippets received and queued for processing.",
            "story_id": story_id,
            "task_id": task_id,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error adding snippets to story {story_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add snippets: {str(e)}")


@router.get("/{story_id}/updates")
async def get_story_updates(
    story_id: str, firebase: FirebaseManager = Depends(get_firebase)
):
    """
    Get updates for a story from Firebase

    This endpoint returns the latest updates for a story,
    which are stored in Firebase Realtime Database.
    """
    try:
        # Verify the story exists
        story = await Story.objects().where(Story.cuid == story_id).first()
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story with id {story_id} not found"
            )

        # Get status and updates from Firebase
        status = await firebase.get_story_status(story_id)
        updates = await firebase.get_story_updates(story_id)

        # Return the updates
        return {"story_id": story_id, "status": status or {}, "updates": updates or []}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error getting updates for story {story_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get story updates: {str(e)}"
        )


@router.get("/{story_id}/")
async def get_story_state(
    story_id: str,
    include_frames: bool = Query(True),
    firebase: FirebaseManager = Depends(get_firebase),
):
    """
    Get the current state of a story

    Args:
        story_id: The story ID to retrieve
        include_frames: Whether to include story frames in the response
    """
    try:
        # Fetch the story from the database
        story = await Story.objects().where(Story.cuid == story_id).first()
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story with id {story_id} not found"
            )

        # Convert to dictionary
        story_dict = story.to_dict()

        # Get Firebase status
        firebase_status = await firebase.get_story_status(story_id)
        if firebase_status:
            story_dict["firebase_status"] = firebase_status

        # If requested, include frames
        if include_frames:
            # This would be implemented based on your data model
            # For example, if frames are in a separate table with a foreign key
            frames = await get_story_frames(story_id)
            story_dict["frames"] = frames

        return story_dict

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error retrieving story {story_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve story: {str(e)}"
        )


@router.get("/")
async def list_stories(
    client_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List stories with pagination

    Args:
        client_id: Optional client ID to filter by
        limit: Maximum number of stories to return
        offset: Number of stories to skip
    """
    try:
        # Build the query
        query = Story.select()
        if client_id:
            query = query.where(Story.created_for_sparrow_id == client_id)

        # Add pagination and ordering
        query = query.order_by(Story.date_created, ascending=False)
        query = query.limit(limit).offset(offset)

        # Execute the query
        stories = await query

        # Get total count for pagination
        count_query = Story.count()
        if client_id:
            count_query = count_query.where(Story.created_for_sparrow_id == client_id)
        total_count = await count_query

        # Convert to dictionaries
        story_dicts = [story.to_dict() for story in stories]

        # Return with pagination metadata
        return {
            "stories": story_dicts,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(stories)) < total_count,
            },
        }

    except Exception as e:
        logger.exception(f"Error listing stories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list stories: {str(e)}")


# --- Helper Functions ---


async def get_story_frames(story_id: str) -> List[Dict[str, Any]]:
    """
    Get all frames for a story

    Args:
        story_id: The story ID to get frames for

    Returns:
        List of frame dictionaries
    """
    from calliope.tables import StoryFrame

    # Query frames for this story
    frames = (
        await StoryFrame.objects()
        .where(StoryFrame.story_id == story_id)
        .order_by(StoryFrame.frame_number)
    )

    # Convert to dictionaries
    return [frame.to_dict() for frame in frames]
