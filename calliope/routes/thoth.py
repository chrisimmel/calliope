import os
from calliope.models import ImageFormat
from calliope.models.story_frame import StoryFrameModel
from calliope.utils.file import get_base_filename
from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.image import convert_grayscale16_to_png, convert_rgb565_to_png
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from calliope.models import StoryModel
from calliope.storage.state_manager import get_story, list_stories


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")


@router.get("/thoth/", response_class=HTMLResponse)
async def thoth_root(request: Request):
    stories = list_stories()
    story_thumbs_by_story_id = {}

    for story in stories:
        if len(story.frames):
            _prepare_frame_image(story.frames[0])
            thumb = story.frames[0].image
            if thumb:
                longer_dim = max(thumb.width, thumb.height)
                scale = 48 / longer_dim
                thumb.width *= scale
                thumb.height *= scale
                story_thumbs_by_story_id[story.story_id] = thumb

    context = {
        "request": request,
        "stories": stories,
        "story_thumbs_by_story_id": story_thumbs_by_story_id,
    }
    return templates.TemplateResponse("thoth.html", context)


@router.get("/thoth/story/{story_id}", response_class=HTMLResponse)
async def thoth_root(request: Request, story_id: str):
    story = get_story(story_id)
    _prepare_frame_images(story)

    context = {
        "request": request,
        "story": story,
    }
    return templates.TemplateResponse("thoth_story.html", context)


def _prepare_frame_image(frame: StoryFrameModel) -> None:
    if frame.image and frame.image.format != ImageFormat.PNG:
        # The image isn't PNG. See if we have a PNG.
        base_filename = get_base_filename(frame.image.url)
        filename = f"{base_filename}.png"
        local_filename = f"media/{filename}"
        filename_parts = "-".split(base_filename)
        found = os.path.isfile(local_filename)

        if found:
            print("original PNG found")
            # We already have a PNG locally! Use it!
            frame.image.format = ImageFormat.PNG
            frame.image.url = local_filename
        elif len(filename_parts) > 2:
            # We have some strangely formatted filenames due to a
            # historical bug when generating rgb565 files. See if
            # there's an original PNG under an alternate name.
            base_filename = "-".join(filename_parts[1:])
            filename = f"{base_filename}.png"
            local_filename = f"media/{filename}"
            found = os.path.isfile(local_filename)
            if found:
                # We already have a PNG locally! Use it!
                frame.image.format = ImageFormat.PNG
                frame.image.url = local_filename

        if not found:
            if is_google_cloud_run_environment():
                try:
                    get_media_file(filename, local_filename)
                    # We were able to get a PNG from GCS.
                    frame.image.format = ImageFormat.PNG
                    frame.image.url = local_filename
                except Exception as e:
                    pass

        if not found:
            original_found = os.path.isfile(frame.image.url)
            if original_found:
                # Convert to PNG if we know how...
                if frame.image.format == ImageFormat.RGB565:
                    frame.image = convert_rgb565_to_png(
                        frame.image.url,
                        local_filename,
                        frame.image.width,
                        frame.image.height,
                    )
                    if is_google_cloud_run_environment():
                        try:
                            put_media_file(filename, local_filename)
                        except Exception as e:
                            print(f"Error saving media file: {e}")

                elif frame.image.format == ImageFormat.GRAYSCALE16:
                    frame.image = convert_grayscale16_to_png(
                        frame.image.url,
                        local_filename,
                        frame.image.width,
                        frame.image.height,
                    )
                    if is_google_cloud_run_environment():
                        try:
                            put_media_file(filename, local_filename)
                        except Exception as e:
                            print(f"Error saving media file: {e}")


def _prepare_frame_images(story: StoryModel) -> None:
    """
    Apply various tricks to try to get viewable images ready,
    even for images in non-PNG formats.
    """
    for frame in story.frames:
        _prepare_frame_image(frame)
