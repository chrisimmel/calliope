from datetime import datetime  # noqa: TC003
from typing import Optional, Sequence, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from calliope.storage.vector_manager import semantic_search
from calliope.tables import Story, StoryFrame
from calliope.utils.image_backfill import ImageBackfillQueue
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
            "Sequence[Story]",
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
    return cast("HTMLResponse", templates.TemplateResponse("thoth.html", context))


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
    story.date_created = cast("datetime", story.date_created.date())
    story.date_updated = cast("datetime", story.date_updated.date())

    context = {
        "request": request,
        "story": story,
        "frames": frames,
        "show_metadata": meta,
        "pagination": pagination,
    }
    return cast("HTMLResponse", templates.TemplateResponse("thoth_story.html", context))


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

            frame.date_created = cast("datetime", frame.date_created.date())

            result_frames.append(frame)

    context = {
        "request": request,
        "query": query,
        "results": result_frames,
        "show_metadata": meta,
        "story_page_size": PAGE_SIZE,
    }
    return cast("HTMLResponse", templates.TemplateResponse("thoth_search.html", context))


@router.post("/thoth/backfill-frame/{story_cuid}/{frame_number}")
async def backfill_frame_image(
    story_cuid: str, frame_number: int, immediate: bool = True
) -> JSONResponse:
    """
    Process a frame for image backfill - either immediately or queued.

    Args:
        story_cuid: Story CUID
        frame_number: Frame number
        immediate: If True, process immediately; if False, add to queue only
    """
    try:
        # Get the story and frame
        story: Optional[Story] = (
            await Story.objects().where(Story.cuid == story_cuid).first().run()
        )
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {story_cuid}")

        frame: Optional[StoryFrame] = (
            await StoryFrame.objects()
            .where(
                StoryFrame.story.cuid == story_cuid, StoryFrame.number == frame_number
            )
            .first()
            .run()
        )
        if not frame:
            raise HTTPException(
                status_code=404,
                detail=f"Frame {frame_number} not found in story {story_cuid}",
            )

        # Extract metadata to reconstruct backfill parameters
        import json

        from calliope.utils.image_backfill import reconstruct_image_prompt

        metadata = frame.metadata or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        # Get strategy config slug with fallbacks
        strategy_config_slug = metadata.get("strategy_config")
        if not strategy_config_slug:
            # Handle legacy format
            parameters = metadata.get("parameters", {})
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except (json.JSONDecodeError, TypeError):
                    parameters = {}

            legacy_strategy = parameters.get("strategy")
            if legacy_strategy:
                legacy_mapping = {
                    "continuous": "continuous-v1-gpt-4",
                    "continuous_v0": "continuous-v1-gpt-4",
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
            else:
                strategy_config_slug = "simple-one-frame"  # Default fallback

        # Get model config slug with fallback
        model_config_slug = metadata.get(
            "text_to_image_model_config", "stability-stable-diffusion-1.6"
        )

        # Reconstruct image prompt
        image_prompt = await reconstruct_image_prompt(frame=frame, metadata=metadata)
        if not image_prompt:
            image_prompt = f"A watercolor, paper texture. {frame.text[:200] if frame.text else 'abstract artistic composition'}"

        # Extract client_id from story
        story_state_props = story.state_props or {}
        if isinstance(story_state_props, str):
            try:
                story_state_props = json.loads(story_state_props)
            except (json.JSONDecodeError, TypeError):
                story_state_props = {}

        client_id = story_state_props.get("client_id", story.cuid)

        if immediate:
            # Process immediately using the same logic as the worker
            import httpx

            # Create a queue item structure for immediate processing
            queue_item = {
                "queue_item_id": f"{story_cuid}_{frame_number}_immediate",
                "story_cuid": story_cuid,
                "frame_number": frame_number,
                "image_prompt": image_prompt,
                "strategy_config_slug": strategy_config_slug,
                "model_config_slug": model_config_slug,
                "client_id": client_id,
                "force_replace": True,
            }

            # Process immediately with a reasonable timeout
            async with httpx.AsyncClient(timeout=120) as httpx_client:
                success = await ImageBackfillQueue.process_queue_item(
                    queue_item, httpx_client
                )

                if success:
                    return JSONResponse(
                        {
                            "success": True,
                            "message": f"Frame {frame_number} image generated successfully",
                            "story_cuid": story_cuid,
                            "frame_number": frame_number,
                            "processed_immediately": True,
                        }
                    )
                else:
                    # If immediate processing fails, fall back to queueing
                    await ImageBackfillQueue.add_to_queue(
                        story_cuid=story_cuid,
                        frame_number=frame_number,
                        image_prompt=image_prompt,
                        strategy_config_slug=strategy_config_slug,
                        model_config_slug=model_config_slug,
                        client_id=client_id,
                        force_replace=True,
                    )

                    return JSONResponse(
                        {
                            "success": True,
                            "message": f"Immediate processing failed, frame {frame_number} queued for retry",
                            "story_cuid": story_cuid,
                            "frame_number": frame_number,
                            "processed_immediately": False,
                            "fallback_queued": True,
                        }
                    )
        else:
            # Add to backfill queue only
            await ImageBackfillQueue.add_to_queue(
                story_cuid=story_cuid,
                frame_number=frame_number,
                image_prompt=image_prompt,
                strategy_config_slug=strategy_config_slug,
                model_config_slug=model_config_slug,
                client_id=client_id,
                force_replace=True,
            )

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Frame {frame_number} queued for image backfill",
                    "story_cuid": story_cuid,
                    "frame_number": frame_number,
                    "processed_immediately": False,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to queue frame for backfill: {e!s}"
        ) from e
