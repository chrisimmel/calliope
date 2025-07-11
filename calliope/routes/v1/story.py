from datetime import datetime
import sys
import traceback
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, Request
from fastapi.security.api_key import APIKey
import httpx
from pydantic import BaseModel

from calliope.inference import image_analysis_inference
from calliope.inference.audio_to_text import audio_to_text_inference
from calliope.location.location import get_location_metadata_for_ip
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
from calliope.utils.authentication import get_api_key
from calliope.utils.fastapi import get_base_url
from calliope.utils.google import get_media_file, is_google_cloud_run_environment
from calliope.utils.id import create_cuid
from calliope.utils.story import (
    prepare_existing_frame_images,
    prepare_frame_images,
    prepare_input_files,
    shorten_title,
)

router = APIRouter(prefix="/v1", tags=["story"])


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    # The story ID.
    story_id: Optional[str]

    # The story slug (URL-friendly identifier)
    slug: Optional[str] = None

    # The number of frames so far in the entire story.
    story_frame_count: int

    # Whether these frames should be appended to those delivered
    # previously.
    append_to_prior_frames: bool = False

    strategy: Optional[str]

    is_read_only: bool
    created_for_sparrow_id: str
    date_created: str
    date_updated: str

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


class StoryInfo(BaseModel):
    story_id: str
    title: str
    slug: Optional[str] = None
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
    request: Request,  # noqa: ARG001
    client_id: str,
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
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
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
    request_params: StoryRequestParamsModel = Depends(StoryRequestParamsModel),
) -> StoryResponseV1:
    """
    Get some frames from the current story.
    """
    base_url = get_base_url(request)

    return await handle_existing_frames_request(request_params, base_url)


@router.get("/story/slug/{story_slug}", response_model=StoryResponseV1)
async def get_story_by_slug(
    story_slug: str,
    request: Request,
    client_id: str,
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
) -> StoryResponseV1:
    """
    Get a story by its slug.
    """
    base_url = get_base_url(request)

    # Find story by slug
    story = await Story.objects().where(Story.slug == story_slug).first().run()

    if not story:
        return StoryResponseV1(
            frames=[],
            story_id=None,
            story_frame_count=0,
            append_to_prior_frames=False,
            strategy=None,
            is_read_only=False,
            created_for_sparrow_id=client_id,
            date_created=cast("datetime", datetime.now(datetime.timezone.utc).date()),
            date_updated=cast("datetime", datetime.now(datetime.timezone.utc).date()),
            request_id=create_cuid(),
            generation_date=str(datetime.utcnow()),
            debug_data={},
            errors=["Story not found"],
        )

    # Create params with found story ID
    request_params = StoryRequestParamsModel(
        client_id=client_id,
        story_id=story.cuid,
        debug=True,
    )

    return await handle_existing_frames_request(request_params, base_url)


@router.post("/frames/", response_model=StoryResponseV1)
async def post_frames(
    request: Request,
    request_params: FramesRequestParamsModel,
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
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
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
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
    base_url: str,  # noqa: ARG001
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
        is_read_only=True,
        created_for_sparrow_id="me",
        date_created=str(datetime.now(datetime.timezone.utc).date()),
        date_updated=str(datetime.now(datetime.timezone.utc).date()),
        request_id=create_cuid(),
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
    story = await get_story(story_id) if story_id else None
    if story:
        request_params.strategy = story.strategy_name

    (
        parameters,
        keys,
        strategy_config,
    ) = await get_sparrow_story_parameters_and_keys(request_params)
    parameters.strategy = parameters.strategy or "continuous-v1"
    parameters.debug = parameters.debug or False
    errors: List[str] = []

    strategy_name = (
        strategy_config.strategy_name if strategy_config else parameters.strategy
    )
    strategy_class = StoryStrategyRegistry.get_strategy_class(strategy_name)

    if not story:
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

    timeout = httpx.Timeout(180.0)
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

        language = "en"
        if (
            strategy_config.text_to_text_model_config
            and strategy_config.text_to_text_model_config
            and strategy_config.text_to_text_model_config.prompt_template
            and strategy_config.text_to_text_model_config.prompt_template.target_language
        ):
            language = (
                strategy_config.text_to_text_model_config.prompt_template.target_language
            )

        if parameters.input_audio_filename:
            text = await audio_to_text_inference(
                httpx_client, parameters.input_audio_filename, language, keys
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
        story_frames_response.debug_data["image_analysis"] = image_analysis
    if parameters.input_audio_filename and parameters.input_text:
        i_hear = parameters.input_text
        story_frames_response.debug_data["i_hear"] = i_hear

    await prepare_frame_images(parameters, story_frames_response.frames)
    await put_story(story)
    await put_sparrow_state(sparrow_state)

    frame_models = [frame.to_pydantic() for frame in story_frames_response.frames]

    response = StoryResponseV1(
        frames=frame_models,
        story_id=story.cuid,
        slug=story.slug,
        story_frame_count=await story.get_num_frames(),
        append_to_prior_frames=story_frames_response.append_to_prior_frames,
        strategy=story.strategy_name,
        is_read_only=story.created_for_sparrow_id != client_id,
        created_for_sparrow_id=story.created_for_sparrow_id,
        date_created=str(story.date_created.date()),
        date_updated=str(story.date_updated.date()),
        request_id=create_cuid(),
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
    ) = await get_sparrow_story_parameters_and_keys(frame_parameters)

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

    frames = await story.get_frames(include_media=True)
    prepare_existing_frame_images(frames)
    frame_models = [frame.to_pydantic() for frame in frames]

    print(f"{story.created_for_sparrow_id=} {client_id=}")
    response = StoryResponseV1(
        frames=frame_models,
        story_id=story.cuid,
        slug=story.slug,
        story_frame_count=await story.get_num_frames(),
        append_to_prior_frames=False,
        request_id=create_cuid(),
        strategy=story.strategy_name,
        is_read_only=story.created_for_sparrow_id != client_id,
        created_for_sparrow_id=story.created_for_sparrow_id,
        date_created=str(story.date_created.date()),
        date_updated=str(story.date_updated.date()),
        generation_date=str(datetime.utcnow()),
        debug_data=debug_data if request_params.debug else {},
        errors=errors,
    )
    return response


@router.get("/stories/", response_model=StoriesResponseV1)
async def get_stories(
    request: Request,  # noqa: ARG001
    api_key: APIKey = Depends(get_api_key),  # noqa: ARG001
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
            slug=story.slug,
            story_frame_count=1,  # await story.get_num_frames(),
            is_bookmarked=False,
            is_current=story.cuid == current_story is not None and current_story.cuid,
            is_read_only=client_id != story.created_for_sparrow_id,
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
        request_id=create_cuid(),
        generation_date=str(datetime.utcnow()),
    )

    return response
