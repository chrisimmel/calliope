from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.security.api_key import APIKey
from pydantic import BaseModel

from calliope.tables import Story, StoryFrame, StoryFrameBookmark
from calliope.storage.state_manager import get_sparrow_state
from calliope.utils.authentication import get_api_key
from calliope.utils.id import create_cuid


router = APIRouter(prefix="/v1/bookmarks", tags=["bookmarks"])


class StoryFrameBookmarkRequest(BaseModel):
    """Request body for creating a bookmark."""
    story_id: str
    frame_number: int
    comments: Optional[str] = None


class StoryFrameBookmarkResponse(BaseModel):
    """Response model for a frame bookmark."""
    id: int
    story_id: str
    frame_number: int
    frame_id: int
    comments: Optional[str]
    date_created: str
    date_updated: str
    frame_text: Optional[str] = None
    frame_image_url: Optional[str] = None


class StoryFrameBookmarksResponse(BaseModel):
    """Response model for listing frame bookmarks."""
    bookmarks: List[StoryFrameBookmarkResponse]
    request_id: str
    generation_date: str


@router.post("/frame", response_model=StoryFrameBookmarkResponse)
async def create_frame_bookmark(
    bookmark_request: StoryFrameBookmarkRequest,
    api_key: APIKey = Depends(get_api_key),
    client_id: str = Query(..., description="The client ID"),
) -> StoryFrameBookmarkResponse:
    """Create a bookmark for a specific story frame."""

    # Get the sparrow state
    sparrow_state = await get_sparrow_state(client_id)

    # Find the story
    story = await Story.objects().where(
        Story.cuid == bookmark_request.story_id
    ).first().run()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Find the frame
    frame = await StoryFrame.objects().where(
        StoryFrame.story.id == story.id,
        StoryFrame.number == bookmark_request.frame_number
    ).first().run()

    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    # Check if bookmark already exists
    existing_bookmark = await StoryFrameBookmark.objects().where(
        StoryFrameBookmark.frame.id == frame.id,
        StoryFrameBookmark.sparrow.id == sparrow_state.id
    ).first().run()

    if existing_bookmark:
        # Update existing bookmark
        existing_bookmark.comments = bookmark_request.comments
        existing_bookmark.date_updated = datetime.now()
        await existing_bookmark.save().run()
        bookmark = existing_bookmark
    else:
        # Create new bookmark
        bookmark = StoryFrameBookmark(
            frame=frame.id,
            sparrow=sparrow_state.id,
            comments=bookmark_request.comments,
            date_created=datetime.now(),
            date_updated=datetime.now()
        )
        await bookmark.save().run()

    # Get frame image URL if available
    frame_image_url = None
    if frame.image and hasattr(frame.image, 'url') and frame.image.url:
        frame_image_url = f"/{frame.image.url}"

    # Return the bookmark
    return StoryFrameBookmarkResponse(
        id=bookmark.id,
        story_id=story.cuid,
        frame_number=frame.number,
        frame_id=frame.id,
        client_id=sparrow_state.id,
        comments=bookmark.comments,
        date_created=str(bookmark.date_created),
        date_updated=str(bookmark.date_updated),
        frame_text=frame.text,
        frame_image_url=frame_image_url
    )


@router.delete("/frame/{bookmark_id}", status_code=204)
async def delete_frame_bookmark(
    bookmark_id: int = Path(..., description="The bookmark ID"),
    api_key: APIKey = Depends(get_api_key),
    client_id: str = Query(..., description="The client ID"),
) -> None:
    """Delete a frame bookmark."""

    # Get the sparrow state
    sparrow_state = await get_sparrow_state(client_id)

    await StoryFrameBookmark.delete().where(
        StoryFrameBookmark.id == bookmark_id,
        StoryFrameBookmark.sparrow == sparrow_state.id
    )


@router.get("/frame", response_model=StoryFrameBookmarksResponse)
async def list_frame_bookmarks(
    api_key: APIKey = Depends(get_api_key),
    client_id: str = Query(..., description="The client ID"),
    story_id: Optional[str] = Query(None, description="Optional story ID to filter by"),
) -> StoryFrameBookmarksResponse:
    """List all frame bookmarks for the client."""

    # Get the sparrow state
    sparrow_state = await get_sparrow_state(client_id)

    # Build the query
    query = StoryFrameBookmark.objects(
        StoryFrameBookmark.frame,
        StoryFrameBookmark.sparrow,
    ).where(
        StoryFrameBookmark.sparrow.id == sparrow_state.id
    )

    # Add story filter if provided
    if story_id:
        story = await Story.objects().where(
            Story.cuid == story_id
        ).first().run()

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        query = query.where(
            StoryFrameBookmark.frame.story.id == story.id
        )

    # Get the bookmarks
    bookmarks = await query.order_by(
        StoryFrameBookmark.date_created, ascending=False
    ).run()

    # Build the response
    bookmark_responses = []
    for bookmark in bookmarks:
        # Get the frame info
        frame = await StoryFrame.objects(StoryFrame.image).where(
            StoryFrame.id == bookmark.frame.id
        ).first().run()

        # Get the story info
        story = await Story.objects().where(
            Story.id == frame.story
        ).first().run()

        # Get frame image URL if available
        frame_image_url = None
        if frame.image and hasattr(frame.image, 'url') and frame.image.url:
            frame_image_url = f"/{frame.image.url}"

        bookmark_responses.append(
            StoryFrameBookmarkResponse(
                id=bookmark.id,
                story_id=story.cuid,
                frame_number=frame.number,
                frame_id=frame.id,
                comments=bookmark.comments,
                date_created=str(bookmark.date_created),
                date_updated=str(bookmark.date_updated),
                frame_text=frame.text,
                frame_image_url=frame_image_url
            )
        )

    return StoryFrameBookmarksResponse(
        bookmarks=bookmark_responses,
        request_id=create_cuid(),
        generation_date=str(datetime.now())
    )


@router.get("/frame/story/{story_id}/frame/{frame_number}", response_model=StoryFrameBookmarkResponse)
async def get_frame_bookmark(
    story_id: str = Path(..., description="The story ID"),
    frame_number: int = Path(..., description="The frame number"),
    api_key: APIKey = Depends(get_api_key),
    client_id: str = Query(..., description="The client ID"),
) -> StoryFrameBookmarkResponse:
    """Get a specific frame bookmark by story ID and frame number."""
    
    # Get the sparrow state
    sparrow_state = await get_sparrow_state(client_id)
    
    # Find the story
    story = await Story.objects().where(
        Story.cuid == story_id
    ).first().run()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Find the frame
    frame = await StoryFrame.objects().where(
        StoryFrame.story.id == story.id,
        StoryFrame.number == frame_number
    ).first().run()
    
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")
    
    # Get the bookmark
    bookmark = await StoryFrameBookmark.objects().where(
        StoryFrameBookmark.frame.id == frame.id,
        StoryFrameBookmark.sparrow.id == sparrow_state.id
    ).first().run()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    # Get frame image URL if available
    frame_image_url = None
    if frame.image and hasattr(frame.image, 'url') and frame.image.url:
        frame_image_url = f"/{frame.image.url}"

    # Return the bookmark
    return StoryFrameBookmarkResponse(
        id=bookmark.id,
        story_id=story.cuid,
        frame_number=frame.number,
        frame_id=frame.id,
        sparrow_id=sparrow_state.id,
        comments=bookmark.comments,
        date_created=str(bookmark.date_created),
        date_updated=str(bookmark.date_updated),
        frame_text=frame.text,
        frame_image_url=frame_image_url
    )