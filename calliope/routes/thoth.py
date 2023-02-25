import os
from calliope.models import ImageFormat, StoryFrameModel
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
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from calliope.models import ImageModel, StoryModel, Story, StoryFrameModel
from calliope.storage.state_manager import get_story, list_legacy_stories, put_story


router = APIRouter()
templates = Jinja2Templates(directory="calliope/templates")


@router.get("/thoth/", response_class=HTMLResponse)
async def thoth_root(request: Request):
    # stories = list_legacy_stories()
    stories = await Story.all().order_by("-date_updated")
    story_thumbs_by_story_id = {}
    story_modified = False

    for story in stories:
        thumb = None
        for frame in await story.frames.all():
            if frame.image:
                # if _prepare_frame_image(frame):
                #     story_modified = True
                thumb = await frame.source_image
                break

        # if story_modified:
        #    put_story(story)

        if thumb:
            longer_dim = max(thumb.width, thumb.height)
            scale = 48 / longer_dim
            thumb.width *= scale
            thumb.height *= scale
            story_thumbs_by_story_id[story.id] = thumb

    context = {
        "request": request,
        "stories": stories,
        "story_thumbs_by_story_id": story_thumbs_by_story_id,
    }
    return templates.TemplateResponse("thoth.html", context)


@router.get("/thoth/story/{story_id}", response_class=HTMLResponse)
async def thoth_story(request: Request, story_id: str):
    # story = get_story(story_id)
    story = await Story.get(id=story_id)
    await story.fetch_related("frames", "frames__image", "frames__source_image")

    frames = []

    for frame in await story.frames.all().order_by("number"):
        image = await frame.image
        source_image = await frame.source_image
        metadata = frame.metadata

        frames.append(
            StoryFrameModel(
                text=frame.text,
                metadata=metadata,
                image=ImageModel(
                    width=image.width,
                    height=image.height,
                    format=image.format,
                    url=image.url,
                )
                if image
                else None,
                source_image=ImageModel(
                    width=source_image.width,
                    height=source_image.height,
                    format=source_image.format,
                    url=source_image.url,
                )
                if source_image
                else None,
            )
        )
    # story_modified = _prepare_frame_images(story)
    # if story_modified:
    #     put_story(story)

    print(f"{len(frames)=}")
    context = {
        "request": request,
        "story": story,
        "frames": frames,
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
                        get_media_file(filename, local_filename)
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
                            get_base_filename_and_extension(frame.image.url),
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
