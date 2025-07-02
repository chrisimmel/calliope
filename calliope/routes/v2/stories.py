"""
V2 Story API with asynchronous processing.

This module provides endpoints for creating and managing stories with
asynchronous background processing for time-consuming operations.
Uses Firebase Realtime Database for real-time updates.
"""

from datetime import datetime
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from calliope.routes.v1.story import StoryResponseV1
from calliope.routes.v2.models import AddFrameRequest, CreateStoryRequest, Snippet
from calliope.storage.firebase import FirebaseManager, get_firebase_manager
from calliope.storage.state_manager import (
    get_sparrow_state,
    get_story,
    put_sparrow_state,
    put_story,
)
from calliope.tables import Story
from calliope.tasks.factory import configure_task_queue
from calliope.tasks.queue import TaskQueue
from calliope.utils.id import create_cuid
from calliope.utils.story import prepare_existing_frame_images

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
router = APIRouter(prefix="/stories", tags=["stories_v2"])


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
    request: Request,
    request_data: CreateStoryRequest,
    client_id: str = Query(...),
    task_queue: TaskQueue = Depends(get_task_queue),
    firebase: FirebaseManager = Depends(get_firebase),
) -> CreateStoryResponse:
    """
    Create a new story and optionally start processing initial snippets

    This endpoint creates a new story record and then asynchronously
    processes any provided snippets to generate initial story content.
    """
    try:
        sparrow_state = await get_sparrow_state(client_id)

        story = Story.create_new(
            strategy_name=request_data.strategy,
            created_for_sparrow_id=client_id,
            title=request_data.title or "Untitled",
        )
        await put_story(story)
        print(f"Created new story: {story.to_dict()}")

        # We're starting a new story.
        sparrow_state.current_story = story.id
        await put_sparrow_state(sparrow_state)
        await put_story(story)

        new_story_cuid = story.cuid

        # Initialize Firebase entry for this story with harmonized schema
        await firebase.update_story_fields(
            new_story_cuid,
            {
                "cuid": new_story_cuid,
                "title": request_data.title or "Untitled",
                "slug": None,  # Will be generated when first frame with text is added
                "strategy_name": request_data.strategy,
                "created_for_sparrow_id": client_id,
                "thumbnail_image": None,
                "state_props": None,
                "date_created": story.date_created.isoformat(),
                "date_updated": story.date_updated.isoformat(),
                "frame_count": 0,
                "active_tasks": [],
                "recent_tasks": [],
            },
        )

        message_parts = [f"Story {new_story_cuid} created."]
        task_id = None

        task_id = await _request_new_frame(
            request=request,
            client_id=client_id,
            story=story,
            snippets=request_data.snippets,
            task_queue=task_queue,
            firebase=firebase,
            extra_parameters={},  # request_data.extra_parameters,
        )
        return CreateStoryResponse(
            story_id=new_story_cuid,
            message=" ".join(message_parts),
            task_id=task_id,
        )

    except Exception as e:
        logger.exception(f"Error creating story: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create story: {e!s}"
        ) from e


@router.post("/{story_id}/frames/", response_model=AddFrameResponse)
async def request_new_frame(
    request: Request,
    story_id: str,
    request_data: AddFrameRequest,
    client_id: str = Query(...),
    task_queue: TaskQueue = Depends(get_task_queue),
    firebase: FirebaseManager = Depends(get_firebase),
) -> AddFrameResponse:
    """
    Requests a new frame be added to an existing story, with optional input snippets.
    """
    try:
        story = await get_story(story_id)

        task_id = await _request_new_frame(
            request=request,
            client_id=client_id,
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
        logger.exception(f"Error adding snippets to story {story_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to add snippets: {e!s}"
        ) from e


async def _request_new_frame(
    request: Request,
    client_id: str,
    story: Story,
    snippets: list[Snippet],
    task_queue: TaskQueue,
    firebase: FirebaseManager,  # noqa: ARG001
    extra_parameters: Optional[dict[str, Any]] = None,
):
    """
    Internal function to request a new frame for the current story.

    This function is called when a new frame is requested, either during
    story creation or when adding snippets to an existing story.
    """
    # Enqueue a task to create and add a frame.
    snippet_data = [snippet.model_dump(exclude_unset=True) for snippet in snippets or []]

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

    # Enqueue the task (Firebase task record created automatically by GCP queue)
    task_id = await task_queue.enqueue(task_type="add_frame", payload=task_payload)

    logger.info(
        f"Story {story.cuid}: Enqueued task {task_id} to add frame with {len(snippets)} snippets"
    )

    return task_id


@router.get("/{story_id}/")
async def get_story_state(
    story_id: str,
    client_id: str = Query(...),
    include_frames: bool = Query(True),
    firebase: FirebaseManager = Depends(get_firebase),
) -> StoryResponseV1:
    """
    Get the current state of a story

    Args:
        story_id: The story ID to retrieve
        include_frames: Whether to include story frames in the response
    """
    print(f"Retrieving story {story_id} with include_frames={include_frames}")
    try:
        # Fetch the story from the database
        # Get the specified story.
        story = await get_story(story_id)
        print(f"{story=}")
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story with id {story_id} not found"
            )

        print(f"Getting Firebase story data for {story_id}")
        # Get Firebase story data (harmonized schema)
        firebase_story_data = await firebase.get_story_status(story_id)

        # Get active tasks for status
        active_tasks = (
            firebase_story_data.get("active_tasks", []) if firebase_story_data else []
        )
        recent_tasks = (
            firebase_story_data.get("recent_tasks", []) if firebase_story_data else []
        )

        # Build status from task information
        status = {}
        if active_tasks:
            # Get the most recent active task
            latest_task = await firebase.get_task(active_tasks[0])
            if latest_task:
                status = {
                    "status": latest_task.get("status", "unknown"),
                    "task_id": latest_task.get("task_id"),
                    "task_type": latest_task.get("task_type"),
                    "started_at": latest_task.get("started_at"),
                }
        elif recent_tasks:
            # Get the most recent completed task
            latest_task = await firebase.get_task(recent_tasks[0])
            if latest_task:
                status = {
                    "status": "idle",  # Story is idle, last task completed
                    "last_task_id": latest_task.get("task_id"),
                    "last_task_type": latest_task.get("task_type"),
                    "completed_at": latest_task.get("completed_at"),
                }
        else:
            status = {"status": "idle"}

        print(f"{firebase_story_data=}")
        if include_frames:
            print("Getting frames")
            frames = await story.get_frames(include_media=True)
            prepare_existing_frame_images(frames)
            frame_models = [frame.to_pydantic() for frame in frames]
        else:
            frame_models = None

        print(f"{story.created_for_sparrow_id=} {client_id=}")
        response = StoryResponseV1(
            frames=frame_models,
            story_id=story.cuid,
            slug=story.slug,
            story_frame_count=await story.get_num_frames(),
            append_to_prior_frames=False,
            request_id=create_cuid(),
            status=status,
            strategy=story.strategy_name,
            is_read_only=story.created_for_sparrow_id != client_id,
            created_for_sparrow_id=story.created_for_sparrow_id,
            date_created=str(story.date_created.date()),
            date_updated=str(story.date_updated.date()),
            generation_date=str(datetime.utcnow()),
            debug_data={},
            errors=[],
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error retrieving story {story_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve story: {e!s}"
        ) from e


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
        logger.exception(f"Error listing stories: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list stories: {e!s}"
        ) from e
