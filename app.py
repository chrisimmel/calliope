import io
from typing import Any, Dict, Optional, Union
import numpy as np

import cv2

from fastapi import APIRouter, Depends, FastAPI, File, Form
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from calliope.files import zipfiles
from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.utils.authentication import get_api_key

app = FastAPI(
    title="Calliope",
    description="""Let me tell you a story.""",
    version="0.0.1",
)

# router = APIRouter(prefix="/v1")
# app.include_router(router)


# @app.get("/")
# def read_root(api_key: APIKey = Depends(get_api_key)):
#    return {"message": "Hello!"}


@app.post("/image/")
async def post_image(
    api_key: APIKey = Depends(get_api_key),
    image_file: bytes = File(default=None),
    requested_image_format: Optional[str] = Form(),
    requested_image_width: Optional[int] = Form(),
    requested_image_height: Optional[int] = Form(),
) -> Optional[FileResponse]:
    input_image_filename = "input_image.jpg"
    caption = "Along the riverrun"
    try:
        print(
            f"{requested_image_format=}, {requested_image_width=}, {requested_image_height=}, {len(image_file)=}("
        )
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
        output_image_file_name = None
        text_file_name = "output_text"

        try:
            output_image_file_name = text_to_image_file_inference(prompt)
            # image_np_array = np.frombuffer(image_data, dtype=np.int32)
            # cv2.imwrite(output_image_file, image_np_array)

            # output_image = cv2.imread(input_image_file)

            # cv2.imwrite(output_image_file, output_image)
            # return StreamingResponse(
            #     io.BytesIO(image.tobytes()), media_type="image/jpeg"
            # )
            return FileResponse(output_image_file_name, media_type="image/jpeg")
        except Exception as e:
            print(e)

        # return zipfiles([output_image_file_name, text_file_name])

    return None


@app.post("/story/")
async def post_story(
    api_key: APIKey = Depends(get_api_key),
    image_file: bytes = File(default=None),
    requested_image_format: Optional[str] = None,
    requested_image_width: Optional[int] = None,
    requested_image_height: Optional[int] = None,
) -> Optional[FileResponse]:
    input_image_filename = "input_image.jpg"
    caption = "Along the riverrun"
    try:
        # print(
        #    f"{requested_image_format=}, {requested_image_width=}, {requested_image_height=}, {len(image_file)=}("
        # )
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
        output_image_file_name = None
        text_file_name = "output_text"

        try:
            output_image_file_name = text_to_image_file_inference(prompt)
            # image_np_array = np.frombuffer(image_data, dtype=np.int32)
            # cv2.imwrite(output_image_file, image_np_array)

            # output_image = cv2.imread(input_image_file)

            # cv2.imwrite(output_image_file, output_image)
            # return StreamingResponse(
            #     io.BytesIO(image.tobytes()), media_type="image/jpeg"
            # )
            return FileResponse(output_image_file_name, media_type="image/jpeg")
        except Exception as e:
            print(e)

        # return zipfiles([output_image_file_name, text_file_name])

    return None


# Mount the static HTML front end.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
