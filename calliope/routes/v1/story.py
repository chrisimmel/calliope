from datetime import datetime
import sys
import traceback
from typing import Any, Dict, List, Optional

import httpx
import cuid
from fastapi import APIRouter, Depends, Request
from fastapi.security.api_key import APIKey
from pydantic import BaseModel

from calliope.inference import image_analysis_inference
from calliope.inference.audio_to_text import audio_to_text_inference
from calliope.intel.location import get_location_metadata_for_ip
from calliope.models import (
    FramesRequestParamsModel,
    ImageModel,
    StoriesRequestParamsModel,
    StoryFrameModel,
    StoryRequestParamsModel,
)
from calliope.storage.config_manager import (
    get_sparrow_story_parameters_and_keys,
    load_json_if_necessary,
)
from calliope.storage.state_manager import (
    get_sparrow_state,
    get_stories_by_client,
    get_story,
    put_sparrow_state,
    put_story,
)
from calliope.strategies import StoryStrategyRegistry
from calliope.tables import Image, ModelConfig, Story, StoryFrame
from calliope.utils.fastapi import get_base_url
from calliope.utils.file import (
    create_sequential_filename,
    decode_b64_to_file,
    get_base_filename,
)
from calliope.utils.google import (
    get_media_file,
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

    # The story ID.
    story_id: Optional[str]

    # The number of frames so far in the entire story.
    story_frame_count: int

    # Whether these frames should be appended to those delivered
    # previously.
    append_to_prior_frames: bool = False

    strategy: Optional[str]

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


class StoryInfo(BaseModel):
    story_id: str
    title: str
    story_frame_count: int
    is_bookmarked: bool
    is_current: bool
    is_read_only: bool

    strategy_name: str
    created_for_sparrow_id: str
    thumbnail_image: Optional[ImageModel] = None

    # The dates the story was created and updated.
    date_created: str
    date_updated: str


class StoriesResponseV1(BaseModel):
    stories: List[StoryInfo]
    request_id: str
    generation_date: str


@router.put("/story/reset/")
async def put_story_reset(
    request: Request,
    client_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    """
    Resets the client's story state, forcing Calliope to begin a new story for this
    client.
    """
    sparrow_state = await get_sparrow_state(client_id)
    sparrow_state.current_story = None
    await put_sparrow_state(sparrow_state)


@router.get("/story/", response_model=StoryResponseV1)
async def get_story_request(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    request_params: StoryRequestParamsModel = Depends(StoryRequestParamsModel),
) -> StoryResponseV1:
    """
    Get some frames from the current story.
    """
    base_url = get_base_url(request)

    return await handle_existing_frames_request(request_params, base_url)


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

    return await handle_frames_request(request, request_params, base_url)
    # return await handle_frames_request_sleep(request_params, base_url)


@router.get("/frames/", response_model=StoryResponseV1)
async def get_frames(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    request_params: FramesRequestParamsModel = Depends(FramesRequestParamsModel),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    base_url = get_base_url(request)

    return await handle_frames_request(request, request_params, base_url)
    # return await handle_frames_request_sleep(request_params, base_url)


async def handle_frames_request_sleep(
    request_params: FramesRequestParamsModel,
    base_url: str,
) -> StoryResponseV1:
    image_filename = "media/Calliope-sleeps.png"

    if is_google_cloud_run_environment():
        try:
            get_media_file(image_filename, image_filename)
        except Exception as e:
            print(f"Error retrieving file {image_filename}: {e}")

    image = Image(format="image/png", width=512, height=512, url=image_filename)

    frames = [
        StoryFrame(
            image=image,
            source_image=image,
            text="""
O soft embalmer of the still midnight,
      Shutting, with careful fingers and benign,
Our gloom-pleas'd eyes, embower'd from the light,
      Enshaded in forgetfulness divine:
O soothest Sleep! if so it please thee, close
      In midst of this thine hymn my willing eyes,
Or wait the "Amen," ere thy poppy throws
      Around my bed its lulling charities.
Then save me, or the passed day will shine
Upon my pillow, breeding many woes,—
      Save me from curious Conscience, that still lords
Its strength for darkness, burrowing like a mole;
      Turn the key deftly in the oiled wards,
And seal the hushed Casket of my Soul.

                    --John Keats

Calliope sleeps. She will awake shortly, improved.
            """,
            metadata={},
            min_duration_seconds=60,
        )
    ]

    await prepare_frame_images(request_params, frames, save=False)

    frame_models = [frame.to_pydantic() for frame in frames]

    response = StoryResponseV1(
        frames=frame_models,
        story_id=None,
        story_frame_count=1,
        append_to_prior_frames=False,
        strategy=None,
        request_id=cuid.cuid(),
        generation_date=str(datetime.utcnow()),
        debug_data={},
        errors=[],
    )
    return response


async def handle_frames_request(
    request: Request,
    request_params: FramesRequestParamsModel,
    base_url: str,
) -> StoryResponseV1:
    print("handle_frames_request")
    client_id = request_params.client_id
    sparrow_state = await get_sparrow_state(client_id)
    story_id = request_params.story_id

    (
        parameters,
        keys,
        strategy_config,
    ) = await get_sparrow_story_parameters_and_keys(request_params, sparrow_state)
    parameters.strategy = parameters.strategy or "continuous-v1"
    parameters.debug = parameters.debug or False
    errors: List[str] = []

    strategy_name = (
        strategy_config.strategy_name if strategy_config else parameters.strategy
    )
    strategy_class = StoryStrategyRegistry.get_strategy_class(strategy_name)

    if story_id:
        story = await get_story(story_id)
    else:
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
        print(f"Created new story: {story.to_dict()}")

    if sparrow_state.current_story != story.id:
        # We're starting a new story.
        sparrow_state.current_story = story.id
        story.created_for_sparrow_id = client_id
        await put_sparrow_state(sparrow_state)
        await put_story(story)

    parameters = await prepare_input_files(parameters, story)
    image_analysis = None

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        forwarded_header = request.headers.get("X-Forwarded-For")
        if forwarded_header:
            # Handle case where request comes through a load balancer, altering
            # request.client.host.
            source_ip_address: Optional[str] = request.headers.getlist(
                "X-Forwarded-For"
            )[0]
        else:
            # Handle the normal case of a direct request.
            source_ip_address = request.client.host if request.client else None
        location_metadata = await get_location_metadata_for_ip(
            httpx_client,
            source_ip_address,
        )
        print(f"{location_metadata=}")

        if parameters.input_image_filename:
            print(f"{parameters.input_image_filename=}")
            vision_model_slug = "azure-vision-analysis"
            model_config = (
                await ModelConfig.objects(ModelConfig.model)
                .where(ModelConfig.slug == vision_model_slug)
                .first()
                .output(load_json=True)
                .run()
            )
            if (
                model_config
                and model_config.model
                and model_config.model.model_parameters
            ):
                model_config.model.model_parameters = load_json_if_necessary(
                    model_config.model.model_parameters
                )
            try:
                image_analysis = await image_analysis_inference(
                    httpx_client,
                    parameters.input_image_filename,
                    parameters.input_image,  # original b64-encoded image.
                    model_config,
                    keys,
                )
                print(f"{image_analysis=}")

            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        if parameters.input_audio:
            text = await audio_to_text_inference(
                httpx_client, parameters.input_audio, keys
            )
            parameters.input_text = text

        story_frames_response = await strategy_class().get_frame_sequence(
            parameters,
            image_analysis,
            location_metadata,
            strategy_config,
            keys,
            sparrow_state,
            story,
            httpx_client,
        )

    story_frames_response.debug_data = {
        **(story_frames_response.debug_data or {}),
        "story_id": story.cuid,
        "story_title": story.title,
        "thoth_link": f"{base_url}thoth/story/{story.cuid}",
    }
    if image_analysis:
        i_see = image_analysis.get("description")
        story_frames_response.debug_data["i_see"] = i_see

    await prepare_frame_images(parameters, story_frames_response.frames)

    await put_story(story)
    await put_sparrow_state(sparrow_state)

    frame_models = [frame.to_pydantic() for frame in story_frames_response.frames]

    response = StoryResponseV1(
        frames=frame_models,
        story_id=story.cuid,
        story_frame_count=await story.get_num_frames(),
        append_to_prior_frames=story_frames_response.append_to_prior_frames,
        strategy=story.strategy_name,
        request_id=cuid.cuid(),
        generation_date=str(datetime.utcnow()),
        debug_data=story_frames_response.debug_data if parameters.debug else {},
        errors=story_frames_response.errors + errors,
    )
    return response


async def handle_existing_frames_request(
    request_params: StoryRequestParamsModel,
    base_url: str,
) -> StoryResponseV1:
    print("handle_existing_frames_request")
    client_id = request_params.client_id
    sparrow_state = await get_sparrow_state(client_id)

    errors: List[str] = []
    story_id = request_params.story_id
    if story_id:
        # Get the specified story.
        story = await get_story(story_id)
    else:
        # Use Sparrow's current story.
        story = sparrow_state.current_story

    frame_parameters = FramesRequestParamsModel(**request_params.dict())

    (
        frame_parameters,
        keys,
        strategy_config,
    ) = await get_sparrow_story_parameters_and_keys(frame_parameters, sparrow_state)

    if not story:
        story = Story.create_new(
            strategy_name=frame_parameters.strategy,
            created_for_sparrow_id=client_id,
        )
        story.created_for_sparrow_id = client_id
        await put_story(story)
        sparrow_state.current_story = story.id
        await put_sparrow_state(sparrow_state)
        print(f"Created new story: {story.to_dict()}")

    debug_data = {
        "story_id": story.cuid,
        "story_title": story.title,
        "thoth_link": f"{base_url}thoth/story/{story.cuid}",
    }

    frames = await story.get_frames(include_images=True)
    # await prepare_frame_images(request_params, frames)
    frame_models = [frame.to_pydantic() for frame in frames]

    response = StoryResponseV1(
        frames=frame_models,
        story_id=story.cuid,
        story_frame_count=await story.get_num_frames(),
        append_to_prior_frames=False,
        request_id=cuid.cuid(),
        strategy=story.strategy_name,
        generation_date=str(datetime.utcnow()),
        debug_data=debug_data if request_params.debug else {},
        errors=errors,
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
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)

    for frame in frames:
        image = frame.image
        if image:
            image_updated = False
            if save:
                # Save the original image.
                await image.save().run()
            if is_google_cloud:
                # Save the original PNG image in case we want to see it later.
                put_media_file(image.url)

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
            base_filename = get_base_filename(image.url)
            resized_image_filename = f"media/{base_filename}.rsz.png"
            resized_image = resize_image_if_needed(
                image,
                output_image_width,
                output_image_height,
                resized_image_filename,
            )
            if resized_image:
                image_updated = True
                image = resized_image

            if output_image_format == ImageFormat.RGB565:
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.raw"
                image = convert_png_to_rgb565(image.url, output_image_filename_raw)
                image_updated = True
            elif output_image_format == ImageFormat.GRAYSCALE16:
                if is_google_cloud:
                    # Also save the original PNG image in case we want to see it later.
                    put_media_file(image.url)
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.grayscale16"
                image = convert_png_to_grayscale16(image.url, output_image_filename_raw)
                image_updated = True

            if image_updated:
                frame.image = image
                if save:
                    await image.save().run()
                    await frame.save().run()
                if is_google_cloud:
                    put_media_file(image.url)


def shorten_title(title: Optional[str], max_length: int = 64) -> str:
    if not title:
        return ""

    lines: List[str] = title.split("\n")
    title = ""
    for line in lines:
        if len(title):
            title += " "
        title += line
        if len(title) > max_length:
            break

    if len(title) > max_length:
        return title[:max_length] + "..."

    return title


@router.get("/stories/", response_model=StoriesResponseV1)
async def get_stories(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    request_params: StoriesRequestParamsModel = Depends(StoriesRequestParamsModel),
) -> StoriesResponseV1:
    """
    Gets all stories attributed to this client_id.
    """
    client_id = request_params.client_id
    sparrow_state = await get_sparrow_state(client_id)

    current_story = sparrow_state.current_story

    all_stories = await get_stories_by_client(client_id)

    story_infos = [
        StoryInfo(
            story_id=story.cuid,
            title=shorten_title(story.title),
            story_frame_count=1,  # await story.get_num_frames(),
            is_bookmarked=False,
            is_current=story.cuid == current_story is not None and current_story.cuid,
            is_read_only=False,
            strategy_name=story.strategy_name,
            created_for_sparrow_id=story.created_for_sparrow_id,
            thumbnail_image=(
                story.thumbnail_image.to_pydantic() if story.thumbnail_image else None
            ),
            date_created=str(story.date_created.date()),
            date_updated=str(story.date_updated.date()),
        )
        for story in all_stories
    ]

    response = StoriesResponseV1(
        stories=story_infos,
        request_id=cuid.cuid(),
        generation_date=str(datetime.utcnow()),
    )

    return response
