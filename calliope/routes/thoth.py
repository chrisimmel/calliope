from datetime import datetime
import os
from typing import cast, Optional, Sequence

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from calliope.models import ImageFormat, StoryModel, StoryFrameModel
from calliope.tables import Story, StoryFrame
from calliope.utils.file import (
    get_base_filename,
    get_base_filename_and_extension,
)
from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.image import (
    convert_grayscale16_to_png,
    convert_rgb565_to_png,
    get_image_attributes,
)
from calliope.storage.vector_manager import semantic_search


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")


@router.get("/thoth/", response_class=HTMLResponse)
async def thoth_root(
    request: Request, meta: Optional[bool] = False
) -> HTMLResponse:
    stories = cast(
        Sequence[Story],
        await Story.objects(Story.thumbnail_image).order_by(
            Story.date_updated, ascending=False
        ),
    )

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
    }
    return cast(
        HTMLResponse, templates.TemplateResponse("thoth.html", context)
    )


@router.get("/thoth/story/{story_cuid}", response_class=HTMLResponse)
async def thoth_story(
    request: Request, story_cuid: str, meta: Optional[bool] = False
) -> HTMLResponse:
    story: Optional[Story] = (
        await Story.objects().where(Story.cuid == story_cuid).first().run()
    )
    if not story:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown story: {story_cuid}",
        )

    frames = await story.get_frames(include_images=True)

    # Truncate datetimes to dates to clean up display.
    story.date_created = cast(datetime, story.date_created.date())
    story.date_updated = cast(datetime, story.date_updated.date())

    context = {
        "request": request,
        "story": story,
        "frames": frames,
        "show_metadata": meta,
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

