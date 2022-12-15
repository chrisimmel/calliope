import datetime
import os
from typing import Any, Dict, List, Optional

import cuid
from fastapi import Depends, FastAPI, File, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from urllib.parse import urlparse

from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.models import StoryFrameModel, TriggerConditionModel
from calliope.strategies import (
    FramesRequestParams,
    StoryStrategyParams,
    StoryStrategyRegistry,
)
from calliope.utils.file import compose_filename
from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
    stash_media_file,
)
from calliope.utils.authentication import get_api_key
from calliope.utils.image import (
    convert_png_to_rgb565,
    guess_image_format_from_filename,
    image_format_to_media_type,
    ImageFormat,
    resize_image_if_needed,
)
from calliope.utils.string import slugify


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


app = FastAPI(
    title="Calliope",
    description="""Let me tell you a story.""",
    version="0.0.1",
)


@app.post("/v1/frames/", response_model=StoryResponseV1)
async def post_frames(
    request_params: FramesRequestParams,
    api_key: APIKey = Depends(get_api_key),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    return await handle_frames_request(request_params)


@app.get("/v1/frames/", response_model=StoryResponseV1)
async def get_frames(
    api_key: APIKey = Depends(get_api_key),
    request_params=Depends(FramesRequestParams),
) -> StoryResponseV1:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    return await handle_frames_request(request_params)


async def handle_frames_request(request_params: FramesRequestParams) -> StoryResponseV1:
    parameters = StoryStrategyParams.from_frame_request_params(request_params)
    parameters.strategy = parameters.strategy or "simple_one_frame"
    parameters.debug = parameters.debug or False

    strategy_class = StoryStrategyRegistry.get_strategy_class(parameters.strategy)
    story_frames_response = await strategy_class().get_frame_sequence(parameters)

    prepare_frame_images(parameters, story_frames_response.frames)

    response = StoryResponseV1(
        frames=story_frames_response.frames,
        request_id=cuid.cuid(),
        generation_date=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        debug_data=story_frames_response.debug_data if parameters.debug else {},
        errors=story_frames_response.errors,
    )
    return response


def prepare_frame_images(
    parameters: StoryStrategyParams, frames: List[StoryFrameModel]
) -> None:
    is_google_cloud = is_google_cloud_run_environment()
    client_id = parameters.client_id
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)

    for frame in frames:
        if frame.image:
            output_image_width = parameters.output_image_width
            output_image_height = parameters.output_image_height
            frame.image = resize_image_if_needed(
                frame.image, output_image_width, output_image_height
            )

            if output_image_format == ImageFormat.RGB565:
                output_image_filename_raw = compose_filename(
                    "media", client_id, "output_image.raw"
                )
                frame.image = convert_png_to_rgb565(
                    frame.image.url, output_image_filename_raw
                )

            if is_google_cloud:
                stash_media_file(frame.image.url)


@app.get("/media/{filename}")
async def get_media(
    filename: str,
    fizzlebuzz: Optional[int] = 0,  # A throwaway param to let a client force reload.
    # api_key: APIKey = Depends(get_api_key),
) -> Optional[FileResponse]:
    base_filename = filename
    format = guess_image_format_from_filename(base_filename)
    media_type = image_format_to_media_type(format)

    local_filename = f"media/{base_filename}"
    if is_google_cloud_run_environment():
        try:
            get_media_file(base_filename, local_filename)
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"Error retrieving file {local_filename}: {e}"
            )

    if not os.path.isfile(local_filename):
        raise HTTPException(
            status_code=404, detail=f"Media file not found: {local_filename}"
        )

    return FileResponse(local_filename, media_type=media_type)


@app.post("/image/")
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
            output_image_filename = compose_filename("media", "", "output_image.jpg")
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


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)):
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version=1, routes=app.routes)
    )
    return response


@app.get("/docs", tags=["documentation"])
async def get_documentation(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
):
    domain = _get_domain(request)

    response = get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    response.set_cookie(
        "api_key",
        value=api_key,
        domain=domain,
        httponly=True,
        max_age=1800,
        expires=1800,
    )
    return response


@app.get("/logout")
async def route_logout_and_remove_cookie(
    request: Request,
):
    domain = _get_domain(request)
    response = RedirectResponse(url="/")
    response.delete_cookie("api_key", domain=domain)
    return response


# Mount the static HTML front end.
app.mount("/clio/", StaticFiles(directory="static", html=True), name="static")


def _get_domain(request: Request) -> str:
    uri = urlparse(str(request.url))
    return f"{uri.scheme}://{uri.netloc}/"
