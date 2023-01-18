from pprint import pprint
import sys, traceback
from typing import Any

import cv2

from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.models import KeysModel


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
    last_text = ""

    # TODO: If we want to keep this legacy code, we need a way to load the
    # keys from a secrets file.
    keys = KeysModel()

    while True:
        ret, frame = vid.read()
        if frame is not None:
            cv2.imwrite(frame_file, frame)
            caption = ""
            prompt = None
            text = None
            fragment_len = 0

            try:
                caption = image_file_to_text_inference(frame_file, keys)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)

            if last_text:
                last_text_tokens = last_text.split()
                last_text_tokens = last_text_tokens[int(len(last_text_tokens) / 2) :]
                last_text = " ".join(last_text_tokens)

            text = f"{caption} {last_text}"
            fragment_len = len(text)
            try:
                text = text_to_extended_text_inference(text, keys)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)

            text = text[fragment_len + 1 :]
            text = " ".join(text.split(" "))
            text = text.replace("*", "")
            text = text.replace("_", "")
            text = text.strip()
            if not text:
                text = caption
            prompt = caption_to_prompt(text, prompt_template)

            last_text = text
            print(text)
            try:
                output_image_filename = "output_file.jpg"
                text_to_image_file_inference(prompt, output_image_filename, keys)
                image = cv2.imread(output_image_filename)
                cv2.imshow("Calliope", image)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)

            cv2.waitKey(5000)


if __name__ == "__main__":
    prompt_template = "A watercolor of {x}"
    story_loop_inference_api(prompt_template)
