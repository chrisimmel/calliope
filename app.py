import datetime
from http.client import HTTPException
import os
from typing import Any, Dict, List, Optional
from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
    stash_media_file,
)

import cuid
from fastapi import Depends, FastAPI, File, Form, Query, Request
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
from calliope.utils.authentication import get_api_key
from calliope.utils.image import (
    convert_png_to_rgb565,
    guess_image_format_from_filename,
    image_format_to_media_type,
    ImageFormat,
)
from calliope.utils.string import slugify


class StoryResponse(BaseModel):
    text: Optional[str]
    image_url: Optional[str]
    request_id: str
    generation_date: str
    debug: Optional[Dict[str, Any]]
    errors: List[str]


app = FastAPI(
    title="Calliope",
    description="""Let me tell you a story.""",
    version="0.0.1",
)


@app.post("/story/", response_model=StoryResponse)
async def post_story(
    api_key: APIKey = Depends(get_api_key),
    input_image: bytes = File(
        default=None,
        description="An image file, optional (harvested image, for now, common web image formats work, jpg, png, etc.)",
    ),
    input_audio: bytes = File(
        default=None,
        description="An audio file, optional (harvested sound, not quite ready to use it... format?)",
    ),
    client_id: str = Form(
        description="Required. Could be a mac address, or, for testing, any string will do."
    ),
    location: str = Form(None, description="The geolocation of the client."),
    input_text: str = Form(
        None,
        description="Harvested text from client environment, not sure where you'd get this, here just in case.",
    ),
    output_image_format: Optional[str] = Form(
        None,
        description="The requested image format. Default is whatever comes out of the image generator, usually jpg or png",
    ),
    output_image_width: Optional[int] = Form(
        None,
        description="The requested image width. Default is whatever comes out of the image generator.",
    ),
    output_image_height: Optional[int] = Form(
        None,
        description="The requested image height. Default is whatever comes out of the image generator.",
    ),
    output_image_style: Optional[str] = Form(
        None, description="Optional description of the desired image style."
    ),
    output_text_length: Optional[int] = Form(
        None,
        description="Optional, the nominal length of the returned text, advisory, might be ignored.",
    ),
    output_text_style: Optional[str] = Form(
        None, description="Optional description of the desired text style."
    ),
    strategy: Optional[str] = Form(
        None,
        description="Optional, helps Calliope select what algorithm to use to generate the output. The idea is that we'll be able to build new ones and plug them in easily.",
    ),
    debug: bool = Form(
        False, description="Enables richer diagnostic output in the response."
    ),
) -> StoryResponse:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    output_image_style = output_image_style or "A watercolor of"
    if output_image_format:
        output_image_format = ImageFormat(output_image_format)
    debug_data = {}
    errors = []
    caption = ""

    if input_image:
        # TODO: Support other input image formats as needed.
        input_image_filename = "input_image.jpg"
        caption = "Along the riverrun"
        try:
            with open(input_image_filename, "wb") as f:
                f.write(input_image)
            caption = image_file_to_text_inference(input_image_filename)
        except Exception as e:
            print(e)
            errors.append(str(e))

    debug_data["image_caption"] = caption
    if input_text:
        caption = f"{caption}. {input_text}"
    text = text_to_extended_text_inference(caption)
    prompt_template = output_image_style + " {x}"
    print(text)

    if text:
        prompt = caption_to_prompt(text, prompt_template)

        try:
            output_image_filename_png = _compose_filename(
                "media", client_id, "output_image.png"
            )
            text_to_image_file_inference(prompt, output_image_filename_png)

            if output_image_format == ImageFormat.RGB565:
                output_image_filename_raw = _compose_filename(
                    "media", client_id, "output_image.raw"
                )
                convert_png_to_rgb565(
                    output_image_filename_png, output_image_filename_raw
                )
                output_image_filename = output_image_filename_raw
            else:
                output_image_filename = output_image_filename_png

            if is_google_cloud_run_environment():
                stash_media_file(output_image_filename)

        except Exception as e:
            output_image_filename = None
            print(e)
            errors.append(str(e))

    response = StoryResponse(
        text=text,
        image_url=output_image_filename,
        request_id=cuid.cuid(),
        generation_date=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        debug=debug_data if debug else None,
        errors=errors,
    )

    return response


@app.get("/story/", response_model=StoryResponse)
async def get_story(
    api_key: APIKey = Depends(get_api_key),
    client_id: str = Query(
        description="Required. Could be a mac address, or, for testing, any string will do."
    ),
    location: str = Query(None, description="The geolocation of the client."),
    input_text: str = Query(
        None,
        description="Harvested text from client environment, not sure where you'd get this, here just in case.",
    ),
    output_image_format: Optional[str] = Query(
        None,
        description="The requested image format. Default is whatever comes out of the image generator, usually jpg or png",
    ),
    output_image_width: Optional[int] = Query(
        None,
        description="The requested image width. Default is whatever comes out of the image generator.",
    ),
    output_image_height: Optional[int] = Query(
        None,
        description="The requested image height. Default is whatever comes out of the image generator.",
    ),
    output_image_style: Optional[str] = Query(
        None, description="Optional description of the desired image style."
    ),
    output_text_length: Optional[int] = Query(
        None,
        description="Optional, the nominal length of the returned text, advisory, might be ignored.",
    ),
    output_text_style: Optional[str] = Query(
        None, description="Optional description of the desired text style."
    ),
    strategy: Optional[str] = Query(
        None,
        description="Optional, helps Calliope select what algorithm to use to generate the output. The idea is that we'll be able to build new ones and plug them in easily.",
    ),
    debug: bool = Query(
        False, description="Enables richer diagnostic output in the response."
    ),
) -> StoryResponse:
    """
    Provide some harvested data (image, sound, text). Get a new episode of an
    ongoing story, with text and image.
    """
    output_image_style = output_image_style or "A watercolor of"
    if output_image_format:
        output_image_format = ImageFormat(output_image_format)
    debug_data = {}
    errors = []
    caption = "Along the riverrun"

    print(f"{input_text=}, {client_id=}, {output_image_format=}")
    if input_text:
        caption = input_text
    try:
        text = text_to_extended_text_inference(caption)
    except Exception as e:
        output_image_filename = None
        text = caption
        print(e)
        errors.append(str(e))

    prompt_template = output_image_style + " {x}"
    print(text)

    if text:
        prompt = caption_to_prompt(text, prompt_template)

        try:
            output_image_filename_png = _compose_filename(
                "media", client_id, "output_image.png"
            )
            text_to_image_file_inference(prompt, output_image_filename_png)

            if output_image_format == ImageFormat.RGB565:
                output_image_filename_raw = _compose_filename(
                    "media", client_id, "output_image.raw"
                )
                convert_png_to_rgb565(
                    output_image_filename_png, output_image_filename_raw
                )
                output_image_filename = output_image_filename_raw
            else:
                output_image_filename = output_image_filename_png

            if is_google_cloud_run_environment():
                stash_media_file(output_image_filename)

        except Exception as e:
            output_image_filename = None
            print(e)
            errors.append(str(e))

    response = StoryResponse(
        text=text,
        image_url=output_image_filename,
        request_id=cuid.cuid(),
        generation_date=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        debug=debug_data if debug else None,
        errors=errors,
    )

    return response


@app.get("/media/{filename}", response_model=StoryResponse)
async def get_media(
    filename: str,
    api_key: APIKey = Depends(get_api_key),
) -> Optional[FileResponse]:
    base_filename = filename
    format = guess_image_format_from_filename(base_filename)
    media_type = image_format_to_media_type(format)

    local_filename = f"media/{base_filename}"
    if is_google_cloud_run_environment():
        get_media_file(base_filename, local_filename)

    if not os.path.isfile(local_filename):
        raise HTTPException(status_code=404, detail="Media file not found")

    return FileResponse(local_filename, media_type=media_type)


def _compose_filename(directory: str, client_id: str, base_filename: str) -> str:
    return f"{directory}/{slugify(client_id)}-{base_filename}"


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
            output_image_filename = _compose_filename("media", "", "output_image.jpg")
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
app.mount("/", StaticFiles(directory="static", html=True), name="static")


def _get_domain(request: Request) -> str:
    uri = urlparse(str(request.url))
    return f"{uri.scheme}://{uri.netloc}/"
