import os
from typing import cast, Optional, Sequence

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from calliope.models import ImageFormat, StoryModel, StoryFrameModel
from calliope.tables import Story
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


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")


@router.get("/thoth/", response_class=HTMLResponse)
async def thoth_root(request: Request, meta: Optional[str] = False):
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
    return templates.TemplateResponse("thoth.html", context)


@router.get("/thoth/story/{story_cuid}", response_class=HTMLResponse)
async def thoth_story(request: Request, story_cuid: str, meta: Optional[str] = False):
    story: Optional[Story] = (
        await Story.objects().where(Story.cuid == story_cuid).first().run()
    )
    if not story:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown story: {story_cuid}",
        )

    frames = await story.get_frames(include_images=True)

    context = {
        "request": request,
        "story": story,
        "frames": frames,
        "show_metadata": meta,
    }
    return templates.TemplateResponse("thoth_story.html", context)


def _prepare_frame_image(frame: StoryFrameModel) -> bool:
    frame_modified = False

    if frame.image and not frame.source_image:
        # All new frames generated from 01/20/23 onward will have a source_image,
        # but legacy ones may need to have this backfilled.

        print(f"Backfilling source_image for frame image {frame.image.url}.")

        if frame.image.format == ImageFormat.PNG:
            frame.source_image = frame.image
            frame_modified = True
        else:
            # The image isn't PNG. See if we have a PNG.
            base_filename = get_base_filename(frame.image.url)
            filename = f"{base_filename}.png"
            local_filename = f"media/{filename}"
            filename_parts = "-".split(base_filename)
            found = os.path.isfile(local_filename)

            if found:
                print(f"original PNG found: {local_filename}")
                # We already have a PNG locally! Use it!
                frame.source_image = get_image_attributes(local_filename)
                frame_modified = True
            elif len(filename_parts) > 2:
                # We have some strangely formatted filenames due to a
                # historical bug when generating rgb565 files. See if
                # there's an original PNG under an alternate name.
                base_filename = "-".join(filename_parts[1:])
                print(f"****{base_filename=}")
                filename = f"{base_filename}.png"
                local_filename = f"media/{filename}"
                found = os.path.isfile(local_filename)
                if found:
                    print(f"Oddly named PNG found: {local_filename}")
                    # We already have a PNG locally! Use it!
                    frame.source_image = get_image_attributes(local_filename)
                    rewrite_frame = True

            if found and is_google_cloud_run_environment():
                try:
                    print(f"Copying back to GCS: {local_filename}")
                    put_media_file(local_filename)
                except Exception as e:
                    print(f"Error saving media file: {e}")

            if not found:
                if is_google_cloud_run_environment():
                    try:
                        get_media_file(local_filename, local_filename)
                        # We were able to get a PNG from GCS.
                        frame.source_image = get_image_attributes(local_filename)
                        frame_modified = True
                        print(f"Found in GCS: {local_filename}")
                        found = True
                    except Exception as e:
                        print(f"Not found in GCS: {local_filename} ({filename=}")
                        # This is ok. We'll convert and copy back to GCS below.

            if not found:
                original_found = os.path.isfile(frame.image.url)
                if not original_found and is_google_cloud_run_environment():
                    # Be sure we have the original non-PNG file locally.
                    try:
                        get_media_file(
                            frame.image.url,
                            frame.image.url,
                        )
                        original_found = True
                    except Exception as e:
                        print(
                            f"Original not found in GCS: {get_base_filename_and_extension(frame.image.url)} ({frame.image.ur=}"
                        )

                if original_found:
                    # Convert to PNG if we know how...
                    if frame.image.format == ImageFormat.RGB565:
                        print(f"Converting from rgb565: {frame.image.url}")

                        frame.source_image = convert_rgb565_to_png(
                            frame.image.url,
                            local_filename,
                            frame.image.width,
                            frame.image.height,
                        )
                        frame_modified = True
                        if is_google_cloud_run_environment():
                            try:
                                print(f"Copying back to GCS: {local_filename}")
                                put_media_file(local_filename)
                            except Exception as e:
                                print(f"Error saving media file: {e}")

                    elif frame.image.format == ImageFormat.GRAYSCALE16:
                        print(f"Converting from grayscale16: {frame.image.url}")

                        frame.source_image = convert_grayscale16_to_png(
                            frame.image.url,
                            local_filename,
                            frame.image.width,
                            frame.image.height,
                        )
                        frame_modified = True
                        if is_google_cloud_run_environment():
                            try:
                                print(f"Copying back to GCS: {local_filename}")
                                put_media_file(local_filename)
                            except Exception as e:
                                print(f"Error saving media file: {e}")
    return frame_modified


def _prepare_frame_images(story: StoryModel) -> bool:
    """
    Apply various tricks to try to get viewable images ready,
    even for images in non-PNG formats.
    """
    story_modified = False
    for frame in story.frames:
        if _prepare_frame_image(frame):
            story_modified = True

    return story_modified
