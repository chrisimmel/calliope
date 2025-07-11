from datetime import datetime
from typing import cast, Optional, Sequence

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from calliope.tables import Story, StoryFrame
from calliope.storage.vector_manager import semantic_search
from calliope.utils.pagination import Pagination


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")

PAGE_SIZE = 10


@router.get("/thoth/", response_class=HTMLResponse)
async def thoth_root(
    request: Request, meta: Optional[bool] = False, page: int = 1
) -> HTMLResponse:
    num_stories = await Story.count()

    # Note: page is 1-based because it's user-visible.
    pagination = Pagination(total_rows=num_stories, page=page, page_size=PAGE_SIZE)

    if pagination.offset < num_stories:
        stories = cast(
            Sequence[Story],
            await Story.objects(Story.thumbnail_image)
            .order_by(Story.date_updated, ascending=False)
            .offset(pagination.offset)
            .limit(pagination.page_size),
        )
    else:
        stories = []

    story_thumbs_by_story_id = {}

    for story in stories:
        thumb = story.thumbnail_image
        if thumb and thumb.id:
            story_thumbs_by_story_id[story.cuid] = thumb

    context = {
        "request": request,
        "stories": stories,
        "story_thumbs_by_story_id": story_thumbs_by_story_id,
        "show_metadata": meta,
        "pagination": pagination,
    }
    return cast(HTMLResponse, templates.TemplateResponse("thoth.html", context))


@router.get("/thoth/story/{story_cuid}", response_class=HTMLResponse)
async def thoth_story(
    request: Request, story_cuid: str, meta: Optional[bool] = False, page: int = 1
) -> HTMLResponse:
    story: Optional[Story] = (
        await Story.objects().where(Story.cuid == story_cuid).first().run()
    )
    if not story:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown story: {story_cuid}",
        )

    num_frames = await story.get_frame_count()

    # Note: page is 1-based because it's user-visible.
    pagination = Pagination(total_rows=num_frames, page=page, page_size=PAGE_SIZE)

    if pagination.offset < num_frames:
        frames = await story.get_frames(
            offset=pagination.offset,
            include_media=True,
            max_frames=pagination.page_size,
        )
    else:
        frames = []

    # Truncate datetimes to dates to clean up display.
    story.date_created = cast(datetime, story.date_created.date())
    story.date_updated = cast(datetime, story.date_updated.date())

    context = {
        "request": request,
        "story": story,
        "frames": frames,
        "show_metadata": meta,
        "pagination": pagination,
    }
    return cast(HTMLResponse, templates.TemplateResponse("thoth_story.html", context))


@router.get("/thoth/search/", response_class=HTMLResponse)
async def thoth_search(
    request: Request, query: str, meta: Optional[bool] = False
) -> HTMLResponse:
    results = semantic_search(query)

    result_frames = []
    for result in results:
        frame_id = int(result[0].metadata.get("frame_id", 0))
        frame: Optional[StoryFrame] = (
            await StoryFrame.objects(
                StoryFrame.image,
                StoryFrame.source_image,
                StoryFrame.video,
                StoryFrame.story,
            )
            .where(StoryFrame.id == frame_id)  # type: ignore[attr-defined]
            .first()
            .run()
        )
        if frame:
            # This seems like a hack necessitated by a Piccolo quirk.
            if frame.image and not frame.image.id:
                frame.image = None
            if frame.source_image and not frame.source_image.id:
                frame.source_image = None
            if frame.video and not frame.video.id:
                frame.video = None

            frame.text = Markup(
                frame.text.replace(
                    result[0].page_content,
                    f"<mark>{result[0].page_content}</mark>",
                )
            )

            frame.date_created = cast(datetime, frame.date_created.date())

            result_frames.append(frame)

    context = {
        "request": request,
        "query": query,
        "results": result_frames,
        "show_metadata": meta,
        "story_page_size": PAGE_SIZE,
    }
    return cast(HTMLResponse, templates.TemplateResponse("thoth_search.html", context))
