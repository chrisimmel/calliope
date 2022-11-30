import argparse
import json
from pprint import pprint
from typing import Any, Optional

import cv2

import requests
from requests.models import Response

# from PIL import Image
# from image_captioning.model import predict


API_TOKEN = "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"


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
text_to_image_model = "runwayml/stable-diffusion-v1-5"
text_prediction_model = "EleutherAI/gpt-neo-2.7B"


def _hugging_face_model_to_api_url(model_name: str) -> str:
    return f"https://api-inference.huggingface.co/models/{model_name}"


def hugging_face_request(data: Any, model_name: str) -> Response:
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.request("POST", api_url, headers=headers, data=data)
    response.raise_for_status()
    return response


def image_to_text_inference(image_data: Optional[bytes] = None) -> str:
    """
    Takes the filename of an image. Returns a caption.
    """
    response = hugging_face_request(image_data, image_to_text_model)
    predictions = json.loads(response.content.decode("utf-8"))
    caption = predictions[0]["generated_text"]

    return caption


def image_file_to_text_inference(image_filename: str) -> str:
    """
    Takes the filename of an image. Returns a caption.
    """
    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        return image_to_text_inference(image_data)

    return "A long the riverrun"


def text_to_image_file_inference(text: str) -> str:
    """
    Interprets a piece of text as an image. Returns the filename of the resulting image.
    """
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = hugging_face_request(data, text_to_image_model)
    output_image_filename = "output_image.jpg"

    if response.status_code == 200:
        with open(output_image_filename, "wb") as f:
            for chunk in response:
                f.write(chunk)

    return output_image_filename


def text_to_extended_text_inference(text: str) -> str:
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = hugging_face_request(data, text_prediction_model)
    predictions = json.loads(response.content.decode("utf-8"))
    extended_text = predictions[0]["generated_text"]
    return extended_text


CAPTION_TOKEN = "{x}"


def caption_to_prompt(caption: str, prompt_template: str) -> Optional[str]:
    prompt = prompt_template.replace(CAPTION_TOKEN, caption) if caption else None

    """
    # Try to prevent caching in inference API. Salt the prompt with a timestamp...
    import datetime
    timestamp = str(datetime.datetime.now())
    prompt = f"{prompt} {timestamp}"
    """

    return prompt
