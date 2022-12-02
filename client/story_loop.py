import argparse
import json
from pprint import pprint
from typing import Any

import cv2

from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)

# from PIL import Image
# from image_captioning.model import predict
# from .formats import rgb565_to_png


API_TOKEN = "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"


frame_file = "frame.jpg"
output_image_file = "output_image.jpg"


CAPTION_TOKEN = "{x}"


def story_loop_inference_api(prompt_template: str) -> None:
    """
    Read images from the camera, caption them, interpret the captions as images.
    Run forever.
    This version uses the Hugging Face inference API to run the models remotely.
    """
    vid = cv2.VideoCapture(0)
    last_text = None

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            caption = None
            prompt = None
            text = None
            fragment_len = 0
            if last_text:
                fragment_len = int(len(last_text) / 2)
                caption = last_text[fragment_len:]
                print(f"{fragment_len=}")
            else:
                try:
                    caption = image_file_to_text_inference(frame_file)
                except Exception as e:
                    print(e)

            if caption:
                text = text_to_extended_text_inference(caption)
                text = text[fragment_len + 1 :]
                print(text)
                last_text = text

            if text:
                prompt = caption_to_prompt(text, prompt_template)
                try:
                    output_image_file = text_to_image_file_inference(prompt)
                    image = cv2.imread(output_image_file)
                    cv2.imshow("Calliope", image)
                except Exception as e:
                    print(e)

            cv2.waitKey(5000)


if __name__ == "__main__":
    prompt_template = "A watercolor of {x}"
    story_loop_inference_api(prompt_template)
