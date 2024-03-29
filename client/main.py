from pprint import pprint
import sys, traceback

import cv2

import requests
from requests.models import Response

# from PIL import Image
# from image_captioning.model import predict
from calliope.inference import (
    text_to_image_file_inference,
)
from calliope.models import KeysModel
from calliope.settings import settings


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
text_to_image_model = "runwayml/stable-diffusion-v1-5"


frame_file = "frame.jpg"
output_image_file = "output_image.jpg"


CAPTION_TOKEN = "{x}"


def image_loop_inference_api() -> None:
    """
    Read images from the camera, caption them, interpret the captions as images.
    Run forever.
    This version uses the Hugging Face inference API to run the models remotely.
    """

    # TODO: If we want to keep this legacy code, we need a way to load the
    # keys from a secrets file.
    # Also: this doesn't work with asyncio/aiohttp.
    keys = KeysModel()
    vid = cv2.VideoCapture(0)

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            caption = None
            prompt = None
            try:
                caption = image_file_to_text_inference(frame_file, keys)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)

            if caption:
                prompt = "A watercolor of " + caption
                print(caption)

            if prompt:
                try:
                    output_image_file = text_to_image_file_inference(prompt, keys)
                    image = cv2.imread(output_image_file)
                    cv2.imshow("weld", image)
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)

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
    # api_url = "http://127.0.0.1:8080/story/"  # local, Docker
    # api_url = "http://127.0.0.1:8008/story/"  # local, no Docker
    api_url = "http://127.0.0.1:8008/v1/frames/"  # local, no Docker
    # api_url = "https://calliope-ugaidvq5sa-uc.a.run.app/story/"  # Google Cloud
    headers = {"X-Api-Key": settings.CALLIOPE_API_KEY}

    values = {
        "client_id": "chris",
        "output_image_format": "image/png",
        "output_image_width": 320,
        "output_image_height": 320,
        "strategy": "continuous-v0",
        "debug": True,
    }
    files = {"input_image": open(filename, "rb")}

    response = requests.post(api_url, files=files, data=values, headers=headers)
    if response.status_code != 200:
        print(f"{response.status_code=}, {response.reason=}, {response.raw=}")
    response.raise_for_status()
    return response


def calliope_media_request(filename: str) -> str:
    # base_url = "http://127.0.0.1:8080/"  # local, Docker
    base_url = "http://127.0.0.1:8008/"  # local, no Docker
    # base_url = "https://calliope-ugaidvq5sa-uc.a.run.app/"  # Google Cloud
    media_url = f"{base_url}{filename}"
    headers = {"X-Api-Key": settings.CALLIOPE_API_KEY}

    response = requests.get(media_url, headers=headers)
    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)

    return filename


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

            try:
                response = calliope_request(frame_file)
                if response.status_code == 200:
                    """
                    with open(output_image_file, "wb") as f:
                        for chunk in response:
                            f.write(chunk)
                    image = cv2.imread(output_image_file)
                    cv2.imshow("Calliope", image)
                    """
                    response_json = response.json()
                    if "frames" in response_json and len(response_json["frames"]):
                        frame = response_json["frames"][0]
                        text = frame["text"]
                        image = frame.get("image")
                        image_url = image.get("url") if image else None
                    else:
                        text = response_json.get("text")
                        image_url = response_json.get("image_url")

                    print(text)
                    if image_url:
                        image_file = calliope_media_request(image_url)
                        image = cv2.imread(image_file)
                        cv2.imshow("Calliope", image)

            except Exception as e:
                traceback.print_exc(file=sys.stderr)

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
