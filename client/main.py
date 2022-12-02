import argparse
import json
from pprint import pprint
from typing import Any

import cv2

import requests
from requests.models import Response

# from PIL import Image
# from image_captioning.model import predict
# from calliope.client.formats import rgb565_to_png
from calliope.inference import caption_to_prompt, image_file_to_text_inference


API_TOKEN = "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"


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
text_to_image_model = "runwayml/stable-diffusion-v1-5"


frame_file = "frame.jpg"
output_image_file = "output_image.jpg"


CAPTION_TOKEN = "{x}"


def image_loop_inference_api(prompt_template: str) -> None:
    """
    Read images from the camera, caption them, interpret the captions as images.
    Run forever.
    This version uses the Hugging Face inference API to run the models remotely.
    """
    vid = cv2.VideoCapture(0)

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            caption = None
            prompt = None
            try:
                caption = image_file_to_text_inference(frame_file)
            except Exception as e:
                print(e)

            if caption:
                prompt = caption_to_prompt(caption)
                print(caption)

            if prompt:
                try:
                    output_image_file = text_to_image_inference(prompt)
                    image = cv2.imread(output_image_file)
                    cv2.imshow("weld", image)
                except Exception as e:
                    print(e)

            cv2.waitKey(2000)


def image_loop_local() -> None:
    """
    Read images from the camera, caption them. Run forever.
    This version uses a downloaded image captioning model running locally,
    Just prints the caption output.
    """
    vid = cv2.VideoCapture(0)

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            image = Image.open(frame_file)
            caption = predict(image)
            image.close()
            pprint(caption)


def calliope_request(filename: str) -> Response:
    api_url = "http://127.0.0.1:8000/image/"
    # headers = {"Authorization": f"Bearer {API_TOKEN}"}
    headers = {}

    values = {
        "requested_image_format": "RAW",
        "requested_image_width": 320,
        "requested_image_height": 320,
    }
    files = {"image_file": open(filename, "rb")}
    # response = requests.request("POST", api_url, headers=headers, files=files)
    response = requests.post(api_url, files=files, data=values)
    # print(response.status_code)
    response.raise_for_status()
    return response


def image_loop_calliope() -> None:
    """
    Read images from the camera, caption them. Run forever.
    This version uses a downloaded image captioning model running locally,
    Just prints the caption output.
    """
    vid = cv2.VideoCapture(0)

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            # with open(frame_file, "rb") as f:
            #    image_data = f.read()

            try:
                response = calliope_request(frame_file)
                if response.status_code == 200:
                    with open(output_image_file, "wb") as f:
                        for chunk in response:
                            f.write(chunk)
                    image = cv2.imread(output_image_file)
                    cv2.imshow("weld", image)
            except Exception as e:
                print(e)

        cv2.waitKey(10000)


if __name__ == "__main__":
    """
    parser = argparse.ArgumentParser(
        prog="Mirror",
    )
    parser.add_argument(
        "prompt_template",
        required=False,
        default=f"A watercolor of {CAPTION_TOKEN}",
        help="A template that will be used to produce the image generation prompt.",
    )
    args = parser.parse_args()
    prompt_template = args.prompt_template
    if CAPTION_TOKEN not in prompt_template:
        prompt_template = f"{prompt_template} {CAPTION_TOKEN}"
    """

    # image_loop_inference_api(prompt_template)
    image_loop_calliope()
    # rgb565_to_png("19.260280.173624.png.scaled.png.raw", 256, 256)
    # rgb565_to_png("Back0 (1).raw", 240, 240)
