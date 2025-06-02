"""
V2 Story API with asynchronous processing.

This module provides endpoints for creating and managing stories with
asynchronous background processing for time-consuming operations.
Uses Firebase Realtime Database for real-time updates.
"""

from datetime import datetime
from urllib import request
from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from pydantic import BaseModel
from typing import Any, Optional

from calliope.storage.state_manager import (
    get_sparrow_state,
    put_sparrow_state,
    get_story,
    put_story,
)
from calliope.tables import Story
from calliope.tasks.factory import configure_task_queue
from calliope.tasks.queue import TaskQueue
from calliope.storage.firebase import get_firebase_manager, FirebaseManager

from calliope.routes.v2.models import AddFrameRequest, CreateStoryRequest, Snippet

logger = logging.getLogger(__name__)

# --- Additional Pydantic Models ---


class CreateStoryResponse(BaseModel):
    """Response for story creation"""

    story_id: str
    message: str
    task_id: Optional[str] = None


class AddFrameResponse(BaseModel):
    """Response for adding a new frame to a story"""

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
GET /stories/
list_stories:
   lists stories with pagination

POST /stories/
create_story:
   creates empty story
   requests initial frame (with optional snippets)
   returns story ID and task ID for processing

GET /stories/{story_id}/
get_story:
   returns story attributes, optionally including frames

POST /stories/{story_id}/frames/
create_frame:
    requests a frame (with optional snippets)
    returns task ID for processing

GET /stories/{story_id}/frames/{frame_index}/
get_frame:
   returns frame attributes

POST /stories/{story_id}/frames/{frame_index}/illustrate/
illustrate_frame:
    requests a new illustration for an existing frame
    returns task ID for processing

POST /stories/{story_id}/fix/
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
) -> CreateStoryResponse:
    """
    Create a new story and optionally start processing initial snippets

    This endpoint creates a new story record and then asynchronously
    processes any provided snippets to generate initial story content.
    """
    try:
        client_id = request_data.client_id
        sparrow_state = await get_sparrow_state(client_id)

        story = Story.create_new(
            strategy_name=request_data.strategy,
            created_for_sparrow_id=client_id,
            title=request_data.title,
        )
        await put_story(story)
        print(f"Created new story: {story.to_dict()}")

        # We're starting a new story.
        sparrow_state.current_story = story.id
        await put_sparrow_state(sparrow_state)
        await put_story(story)

        new_story_cuid = story.cuid

        # Initialize Firebase entry for this story
        await firebase.update_story_status(
            new_story_cuid,
            {
                "status": "created",
                "title": request_data.title,
                "created_at": story.date_created.isoformat(),
                "client_id": client_id,
                "strategy": request_data.strategy,
                "frame_count": 0,
            },
        )

        message_parts = [f"Story {new_story_cuid} created."]
        task_id = None

        task_id = await _request_new_frame(
            story=story,
            snippets=request_data.snippets,
            task_queue=task_queue,
            firebase=firebase,
            extra_parameters=request_data.extra_parameters,
        )
        return CreateStoryResponse(
            story_id=new_story_cuid,
            message=" ".join(message_parts),
            task_id=task_id,
        )

    except Exception as e:
        logger.exception(f"Error creating story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create story: {str(e)}")


@router.post("/{story_id}/frames/", response_model=AddFrameResponse)
async def request_new_frame(
    story_id: str,
    request_data: AddFrameRequest,
    task_queue: TaskQueue = Depends(get_task_queue),
    firebase: FirebaseManager = Depends(get_firebase),
) -> AddFrameResponse:
    """
    Requests a new frame be added to an existing story, with optional input snippets.
    """
    try:
        story = get_story(story_id)

        task_id = await _request_new_frame(
            story=story,
            snippets=request_data.snippets,
            task_queue=task_queue,
            firebase=firebase,
        )

        return AddFrameResponse(
            story_id=story_id,
            message="Frame request received and processing.",
            task_id=task_id,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error adding snippets to story {story_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add snippets: {str(e)}")


async def _request_new_frame(
    client_id: str,
    story: Story,
    snippets: list[Snippet],
    task_queue: TaskQueue,
    firebase: FirebaseManager,
    extra_parameters: Optional[dict[str, Any]] = None,
):
    """
    Internal function to request a new frame for the current story.

    This function is called when a new frame is requested, either during
    story creation or when adding snippets to an existing story.
    """
    # Enqueue a task to create and add a frame.
    snippet_data = []
    if snippets:
        for snippet in snippets:
            snippet_data.append(snippet.model_dump(exclude_unset=True))

    forwarded_header = request.headers.get("X-Forwarded-For")
    if forwarded_header:
        # Handle case where request comes through a load balancer, altering
        # request.client.host.
        source_ip_address: Optional[str] = request.headers.getlist("X-Forwarded-For")[0]
    else:
        # Handle the normal case of a direct request.
        source_ip_address = request.client.host if request.client else None

    # Create a task payload
    task_payload = {
        "story_id": story.cuid,
        "client_id": client_id,
        "snippets": snippet_data,
        "source_ip_address": source_ip_address,
        "extra_parameters": extra_parameters or {},
    }

    # Enqueue the task
    task_id = await task_queue.enqueue(task_type="add_frame", payload=task_payload)

    # Update Firebase with task info
    await firebase.update_story_status(
        story.cuid,
        {
            "status": "processing",
            "task_id": task_id,
            "processing_started_at": datetime.now().isoformat(),
        },
    )

    logger.info(
        f"Story {story.cuid}: Enqueued task {task_id} to add frame with {len(snippets)} snippets"
    )

    return task_id


@router.get("/{story_id}/")
async def get_story_state(
    story_id: str,
    include_frames: bool = Query(True),
    firebase: FirebaseManager = Depends(get_firebase),
) -> dict[str, Any]:
    """
    Get the current state of a story

    Args:
        story_id: The story ID to retrieve
        include_frames: Whether to include story frames in the response
    """
    try:
        # Fetch the story from the database
        # Get the specified story.
        story = await get_story(story_id)
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story with id {story_id} not found"
            )

        # Convert to dictionary
        story_dict = story.model_dump(exclude_unset=True)

        # Get Firebase status
        firebase_status = await firebase.get_story_status(story_id)
        if firebase_status:
            story_dict["status"] = firebase_status

        # If requested, include frames
        if include_frames:
            # This would be implemented based on your data model
            # For example, if frames are in a separate table with a foreign key
            frames = await story.get_frames(include_media=True)
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
