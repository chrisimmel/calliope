import argparse
import json
from pprint import pprint
from typing import Any

import cv2

import requests
from requests.models import Response

# from PIL import Image
# from image_captioning.model import predict
from formats import rgb565_to_png


API_TOKEN = "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"


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
text_to_image_model = "runwayml/stable-diffusion-v1-5"


frame_file = "frame.jpg"
output_image_file = "output_image.jpg"


def _hugging_face_model_to_api_url(model_name: str) -> str:
    return f"https://api-inference.huggingface.co/models/{model_name}"


def hugging_face_request(data: Any, model_name: str) -> Response:
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.request("POST", api_url, headers=headers, data=data)
    response.raise_for_status()
    return response


def image_to_text_inference(image_filename: str) -> str:
    """
    Takes the filename of an image. Returns a caption.
    """
    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        response = hugging_face_request(image_data, image_to_text_model)
        predictions = json.loads(response.content.decode("utf-8"))
        caption = predictions[0]["generated_text"]

    return caption


def text_to_image_inference(text: str) -> str:
    """
    Interprets a piece of text as an image. Returns the filename of the resulting image.
    """
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = hugging_face_request(data, text_to_image_model)

    if response.status_code == 200:
        with open(output_image_file, "wb") as f:
            for chunk in response:
                f.write(chunk)

    return output_image_file


CAPTION_TOKEN = "{x}"


def _caption_to_prompt(caption: str) -> str:
    prompt = prompt_template.replace(CAPTION_TOKEN, caption)

    """
    # Try to prevent caching in inference API. Salt the prompt with a timestamp...
    import datetime
    timestamp = str(datetime.datetime.now())
    prompt = f"{prompt} {timestamp}"
    """

    return prompt


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
                caption = image_to_text_inference(frame_file)
            except Exception as e:
                print(e)

            if caption:
                prompt = prompt_template.replace(CAPTION_TOKEN, caption)
                # print(caption)

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


def image_serve_request(filename: str) -> Response:
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


def image_loop_image_serve() -> None:
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
                response = image_serve_request(frame_file)
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
    image_loop_image_serve()
    # rgb565_to_png("19.260280.173624.png.scaled.png.raw", 256, 256)
    # rgb565_to_png("Back0 (1).raw", 240, 240)
