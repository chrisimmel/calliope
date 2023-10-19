from datetime import datetime
from typing import Iterator, cast, Optional, Sequence

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from calliope.tables import Story, StoryFrame
from calliope.storage.vector_manager import semantic_search


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")

PAGE_SIZE = 10


class Pagination:
    total_rows: int
    page_size: int
    page: int
    row_offset: int
    num_pages: int
    max_shown_pages: int

    def __init__(
        self,
        total_rows: int,
        page: int,
        page_size: int = 10,
        max_shown_pages: int = 5
    ) -> None:
        self.total_rows = total_rows
        self.page = page
        self.page_size = page_size
        self.num_pages = (total_rows // page_size) + 1
        self.max_shown_pages = max_shown_pages

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def prev_page(self) -> int:
        return self.page - 1

    @property
    def next_page(self) -> int:
        return self.page + 1 if self.page < self.num_pages else 0

    @property
    def pages_in_range(self) -> int:
        range_start_page = max(1, self.page - self.max_shown_pages // 2)
        range_end_page = min(self.num_pages + 1, range_start_page + self.max_shown_pages)
        for show_page in range(range_start_page, range_end_page):
            yield show_page


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
            await Story.objects(Story.thumbnail_image).order_by(
                Story.date_updated, ascending=False
            ).offset(pagination.offset).limit(pagination.page_size),
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
    return cast(
        HTMLResponse, templates.TemplateResponse("thoth.html", context)
    )


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
            include_images=True,
            max_frames=pagination.page_size
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
    return cast(
        HTMLResponse, templates.TemplateResponse("thoth_story.html", context)
    )


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
                StoryFrame.image, StoryFrame.source_image, StoryFrame.story
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
    }
    return cast(
        HTMLResponse, templates.TemplateResponse("thoth_search.html", context)
    )

