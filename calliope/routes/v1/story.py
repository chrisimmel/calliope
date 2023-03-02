from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import cuid
from fastapi import APIRouter, Depends, Request
from fastapi.security.api_key import APIKey
from pydantic import BaseModel

from calliope.models import FramesRequestParamsModel, StoryFrameModel
from calliope.storage.config_manager import get_sparrow_story_parameters_and_keys
from calliope.storage.state_manager import (
    get_sparrow_state,
    get_story,
    put_sparrow_state,
    put_story,
)
from calliope.strategies import StoryStrategyRegistry
from calliope.tables import Image, Story, StoryFrame
from calliope.utils.fastapi import get_base_url
from calliope.utils.file import (
    create_sequential_filename,
    decode_b64_to_file,
    get_base_filename,
)
from calliope.utils.google import (
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.authentication import get_api_key
from calliope.utils.image import (
    convert_png_to_grayscale16,
    convert_png_to_rgb565,
    image_is_monochrome,
    ImageFormat,
    resize_image_if_needed,
)


router = APIRouter(prefix="/v1", tags=["story"])


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    # Whether these frames should be appended to those delivered
    # previously.
    append_to_prior_frames: bool = False

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


@router.post("/frames/", response_model=StoryResponseV1)
async def post_frames(
    request: Request,
    request_params: FramesRequestParamsModel,
    api_key: APIKey = Depends(get_api_key),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    base_url = get_base_url(request)

    # return await handle_frames_request(request_params, base_url)
    return await handle_frames_request_sleep(request_params, base_url)


@router.get("/frames/", response_model=StoryResponseV1)
async def get_frames(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    request_params=Depends(FramesRequestParamsModel),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    base_url = get_base_url(request)

    # return await handle_frames_request(request_params, base_url)
    return await handle_frames_request_sleep(request_params, base_url)


async def handle_frames_request_sleep(
    request_params: FramesRequestParamsModel,
    base_url: str,
) -> StoryResponseV1:

    image = Image(
        format="image/png", width=512, height=512, url="media/Calliope-sleeps.png"
    )

    frames = [
        StoryFrame(
            image=image,
            source_image=image,
            text="Calliope sleeps a dream of angels. She will awake shortly, stronger for having slept.",
            metadata={},
            min_duration_seconds=60,
        )
    ]

    await prepare_frame_images(request_params, frames, save=False)

    frame_models = [frame.to_pydantic() for frame in frames]

    response = StoryResponseV1(
        frames=frame_models,
        append_to_prior_frames=False,
        request_id=cuid.cuid(),
        generation_date=str(datetime.utcnow()),
        debug_data={},
        errors=[],
    )
    return response


async def handle_frames_request(
    request_params: FramesRequestParamsModel,
    base_url: str,
) -> StoryResponseV1:
    print("handle_frames_request")
    client_id = request_params.client_id
    sparrow_state = await get_sparrow_state(client_id)

    (
        parameters,
        keys,
        inference_model_configs,
    ) = await get_sparrow_story_parameters_and_keys(request_params, sparrow_state)
    parameters.strategy = parameters.strategy or "continuous_v1"
    parameters.debug = parameters.debug or False

    strategy_class = StoryStrategyRegistry.get_strategy_class(parameters.strategy)

    story = None
    if sparrow_state.current_story and not parameters.reset_strategy_state:
        story = sparrow_state.current_story
    if story and story.strategy_name != parameters.strategy:
        # The story in progress was created by a different strategy. Start a new one.
        story = None

    if not story:
        story = Story.create_new(
            strategy_name=parameters.strategy,
            created_for_sparrow_id=client_id,
        )
        await put_story(story)

    if sparrow_state.current_story != story.id:
        # We're starting a new story.
        sparrow_state.current_story = story.id
        story.created_for_sparrow_id = client_id
        await put_sparrow_state(sparrow_state)
        await put_story(story)

    parameters = await prepare_input_files(parameters, story)
    async with aiohttp.ClientSession(raise_for_status=True) as aiohttp_session:

        story_frames_response = await strategy_class().get_frame_sequence(
            parameters,
            inference_model_configs,
            keys,
            sparrow_state,
            story,
            aiohttp_session,
        )

    story_frames_response.debug_data = {
        **story_frames_response.debug_data,
        "story_id": story.cuid,
        "story_title": story.title,
        "thoth_link": f"{base_url}thoth/story/{story.cuid}",
    }

    await prepare_frame_images(parameters, story_frames_response.frames)

    await put_story(story)
    await put_sparrow_state(sparrow_state)

    frame_models = [frame.to_pydantic() for frame in story_frames_response.frames]

    response = StoryResponseV1(
        frames=frame_models,
        append_to_prior_frames=story_frames_response.append_to_prior_frames,
        request_id=cuid.cuid(),
        generation_date=str(datetime.utcnow()),
        debug_data=story_frames_response.debug_data if parameters.debug else {},
        errors=story_frames_response.errors,
    )
    return response


async def prepare_input_files(
    request_params: FramesRequestParamsModel, story: Story
) -> FramesRequestParamsModel:
    sparrow_id = request_params.client_id

    # Decode b64-encoded file inputs and store to files.
    if request_params.input_image:
        input_image_filename = create_sequential_filename(
            "input",
            sparrow_id,
            "in",
            "jpg",
            story.cuid,
            0,  # TODO: Handle non-jpeg image input.
        )
        decode_b64_to_file(request_params.input_image, input_image_filename)
        request_params.input_image_filename = input_image_filename

    if request_params.input_audio:
        input_audio_filename = create_sequential_filename(
            "input", sparrow_id, "in", "wav", story.cuid, 0
        )
        decode_b64_to_file(request_params.input_audio, input_audio_filename)
        request_params.input_audio_filename = input_audio_filename

    return request_params


async def prepare_frame_images(
    parameters: FramesRequestParamsModel,
    frames: List[StoryFrame],
    save: bool = True,
) -> None:
    is_google_cloud = is_google_cloud_run_environment()
    client_id = parameters.client_id
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)

    for frame in frames:
        # image = await frame.get_related(StoryFrame.image)
        image = frame.image
        if image:
            image_updated = False

            if image_is_monochrome(image.url):
                print(f"Image {image.url} is monochrome. Skipping.")
                # Skip the image if it has only a single color (usually black).
                # (This doesn't appear to work.)
                frame.image = None
                if save:
                    await frame.save().run()
                continue

            output_image_width = parameters.output_image_width
            output_image_height = parameters.output_image_height
            if save and is_google_cloud:
                # Save the original PNG image in case we want to see it later.
                put_media_file(image.url)
            original_image = image
            image = resize_image_if_needed(
                image, output_image_width, output_image_height
            )
            image_updated = image.id != original_image.id

            if output_image_format == ImageFormat.RGB565:
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.raw"
                image = convert_png_to_rgb565(image.url, output_image_filename_raw)
                frame.image = image
                image_updated = True
            elif output_image_format == ImageFormat.GRAYSCALE16:
                if save and is_google_cloud:
                    # Also save the original PNG image in case we want to see it later.
                    put_media_file(image.url)
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.grayscale16"
                image = convert_png_to_grayscale16(image.url, output_image_filename_raw)
                frame.image = image

            if image_updated and save:
                frame.image = image
                await image.save().run()
                await frame.save().run()
                if is_google_cloud:
                    put_media_file(image.url)
