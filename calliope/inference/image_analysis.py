from typing import Any, Dict

import aiohttp
from PIL import Image

from calliope.inference.engines.azure_vision import (
    azure_vision_inference,
    interpret_azure_v3_metadata,
    interpret_azure_v4_metadata,
)
from calliope.inference.engines.hugging_face import hugging_face_image_to_text_inference
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig
from calliope.utils.file import get_file_extension


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
# image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
# text_to_image_model = "runwayml/stable-diffusion-v1-5"
# text_prediction_model = "EleutherAI/gpt-neo-2.7B"
# text_prediction_model = "EleutherAI/gpt-neox-20b"
# speech_recognition_model = "facebook/wav2vec2-large-960h-lv60-self"
# voice_activity_detection_model = "pyannote/voice-activity-detection"


def _convert_image_to_png(image_filename: str) -> str:
    extension = get_file_extension(image_filename)
    if extension != "png":
        image_filename_png = image_filename + ".png"
        img = Image.open(image_filename)
        img.save(image_filename_png)
        image_filename = image_filename_png

    return image_filename


async def image_analysis_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of metadata about the image.
    """
    model = model_config.model

    if model.provider == InferenceModelProvider.AZURE:
        # Don't know why, but Azure comp vision doesn't seem to like JPG files.
        # Convert to PNG.
        image_filename = _convert_image_to_png(image_filename)

    with open(image_filename, "rb") as f:
        image_data = f.read()

        if image_data:
            if model.provider == InferenceModelProvider.HUGGINGFACE:
                description = await hugging_face_image_to_text_inference(
                    aiohttp_session, image_data, model_config, keys
                )

                return {
                    "description": description,
                }
            elif model.provider == InferenceModelProvider.AZURE:
                raw_metadata = await azure_vision_inference(
                    aiohttp_session, image_data, model_config, keys
                )

                if not raw_metadata:
                    raise ValueError(
                        "Unexpected empty response from image analysis API."
                    )

                if model.provider_model_name.find("v3.2") >= 0:
                    return interpret_azure_v3_metadata(raw_metadata)
                else:
                    return interpret_azure_v4_metadata(raw_metadata)
            else:
                raise ValueError(
                    "Don't know how to do image->text inference for provider "
                    f"{model.provider}."
                )

    raise ValueError("No input image data to image_analysis_inference.")


async def image_ocr_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of metadata.
    """
    model = model_config.model

    if model.provider != InferenceModelProvider.AZURE:
        raise ValueError(
            f"Don't know how to do image OCR for provider {model_config.provider}."
        )

    # Don't know why, but Azure comp vision doesn't seem to like JPG files.
    # Convert to PNG.
    image_filename = _convert_image_to_png(image_filename)
    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        return await azure_vision_inference(
            aiohttp_session, image_data, model_config, keys
        )

    raise ValueError("No input image data to image_analysis_inference.")
