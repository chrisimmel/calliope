import datetime
from typing import Any, Dict, List, Optional
from calliope.models.story import StoryModel
from calliope.storage.state_manager import (
    get_sparrow_state,
    get_story,
    put_sparrow_state,
    put_story,
)

import cuid
from fastapi import APIRouter, Depends, File
from fastapi.security.api_key import APIKey
from pydantic import BaseModel
from starlette.responses import FileResponse

from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.models import FramesRequestParamsModel, StoryFrameModel, StoryParamsModel
from calliope.storage.config_manager import get_sparrow_story_parameters_and_keys
from calliope.strategies import StoryStrategyRegistry
from calliope.utils.file import (
    compose_full_filename,
    create_sequential_filename,
    create_unique_filename,
    decode_b64_to_file,
    get_base_filename,
)
from calliope.utils.google import (
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.authentication import get_api_key
from calliope.utils.image import (
    convert_png_to_rgb565,
    image_is_monochrome,
    ImageFormat,
    resize_image_if_needed,
)


router = APIRouter(prefix="/v1", tags=["story"])


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


@router.post("/frames/", response_model=StoryResponseV1)
async def post_frames(
    request_params: FramesRequestParamsModel,
    api_key: APIKey = Depends(get_api_key),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    return await handle_frames_request(request_params)


@router.get("/frames/", response_model=StoryResponseV1)
async def get_frames(
    api_key: APIKey = Depends(get_api_key),
    request_params=Depends(FramesRequestParamsModel),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    return await handle_frames_request(request_params)


async def handle_frames_request(
    request_params: FramesRequestParamsModel,
) -> StoryResponseV1:
    client_id = request_params.client_id
    sparrow_state = get_sparrow_state(client_id)

    parameters, keys, inference_model_configs = get_sparrow_story_parameters_and_keys(
        request_params, sparrow_state
    )
    parameters.strategy = parameters.strategy or "simple_one_frame"
    parameters.debug = parameters.debug or False

    strategy_class = StoryStrategyRegistry.get_strategy_class(parameters.strategy)

    story = None
    if sparrow_state.current_story_id and not parameters.reset_strategy_state:
        story = get_story(sparrow_state.current_story_id)
    if story and story.strategy_name != parameters.strategy:
        # The story in progress was created by a different strategy. Start a new one.
        story = None

    if not story:
        story = StoryModel(
            story_id=cuid.cuid(),
            strategy_name=parameters.strategy,
            created_for_id=client_id,
            text="",
        )
    if sparrow_state.current_story_id != story.story_id:
        # We're starting a new story.
        sparrow_state.current_story_id = story.story_id
        sparrow_state.story_ids.append(story.story_id)

    parameters = prepare_input_files(parameters, story)

    story_frames_response = await strategy_class().get_frame_sequence(
        parameters, inference_model_configs, keys, sparrow_state, story
    )

    prepare_frame_images(parameters, story_frames_response.frames)

    put_story(story)
    put_sparrow_state(sparrow_state)

    response = StoryResponseV1(
        frames=story_frames_response.frames,
        request_id=cuid.cuid(),
        generation_date=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        debug_data=story_frames_response.debug_data if parameters.debug else {},
        errors=story_frames_response.errors,
    )
    return response


def prepare_input_files(
    request_params: FramesRequestParamsModel, story: StoryModel
) -> FramesRequestParamsModel:
    sparrow_id = request_params.client_id

    # Decode b64-encoded file inputs and store to files.
    if request_params.input_image:
        input_image_filename = create_sequential_filename(
            "input", sparrow_id, "in", "jpg", story  # TODO: Handle non-jpeg image input.
        )
        decode_b64_to_file(request_params.input_image, input_image_filename)
        request_params.input_image_filename = input_image_filename

    if request_params.input_audio:
        input_audio_filename = create_sequential_filename(
            "input", sparrow_id, "in", "wav", story
        )
        decode_b64_to_file(request_params.input_audio, input_audio_filename)
        request_params.input_audio_filename = input_audio_filename

    return request_params


def prepare_frame_images(
    parameters: FramesRequestParamsModel, frames: List[StoryFrameModel]
) -> None:
    is_google_cloud = is_google_cloud_run_environment()
    client_id = parameters.client_id
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)

    for frame in frames:
        if frame.image:
            if image_is_monochrome(frame.image.url):
                print(f"Image {frame.image.url} is monochrome. Skipping.")
                # Skip the image if it has only a single color (usually black).
                frame.image = None
                continue

            output_image_width = parameters.output_image_width
            output_image_height = parameters.output_image_height
            frame.image = resize_image_if_needed(
                frame.image, output_image_width, output_image_height
            )

            if output_image_format == ImageFormat.RGB565:
                base_filename = get_base_filename(frame.image.url)

                output_image_filename_raw = compose_full_filename(
                    "media", client_id, f"{base_filename}.raw"
                )
                frame.image = convert_png_to_rgb565(
                    frame.image.url, output_image_filename_raw
                )

            if is_google_cloud:
                put_media_file(frame.image.url)


@router.post("/image/", tags=["story"])
async def post_image(
    api_key: APIKey = Depends(get_api_key),
    image_file: bytes = File(None),
) -> Optional[FileResponse]:
    """
    Give an image, get an image.
    This is an older version of the story API.
    """
    input_image_filename = "input_image.jpg"
    caption = "Along the riverrun"
    try:
        # image_file.filename = output_image_file
        with open(input_image_filename, "wb") as f:
            f.write(image_file)
        caption = image_file_to_text_inference(input_image_filename)
    except Exception as e:
        print(e)

    text = text_to_extended_text_inference(caption)
    prompt_template = "A watercolor of {x}"
    print(text)

    if text:
        prompt = caption_to_prompt(text, prompt_template)
        output_image_filename = None
        text_file_name = "output_text"

        try:
            output_image_filename = create_unique_filename("media", "", "jpg")
            text_to_image_file_inference(prompt, output_image_filename)
            # image_np_array = np.frombuffer(image_data, dtype=np.int32)
            # cv2.imwrite(output_image_file, image_np_array)

            # output_image = cv2.imread(input_image_file)

            # cv2.imwrite(output_image_file, output_image)
            return FileResponse(output_image_filename, media_type="image/jpeg")
        except Exception as e:
            print(e)

        # return zipfiles([output_image_file_name, text_file_name])

    return None
