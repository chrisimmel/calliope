import io
from typing import Any, Dict, Optional, Union
import numpy as np

import cv2

from fastapi import FastAPI, File, UploadFile
from starlette.responses import FileResponse, StreamingResponse

from calliope.files import zipfiles
from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/image/")
async def post_image(
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
