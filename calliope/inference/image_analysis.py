import asyncio
from typing import Any, Dict

import aiohttp
from PIL import Image

from calliope.inference.engines.azure_vision import (
    azure_vision_inference,
    interpret_azure_v3_metadata,
    interpret_azure_v4_metadata,
)
from calliope.inference.engines.hugging_face import image_to_text_inference_hugging_face
from calliope.inference.engines.replicate import replicate_vision_inference
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig
from calliope.utils.file import get_file_extension


# The number of seconds to wait for a Replicate request to complete.
# This is to prevent long waits for model cold starts.
REPLICATE_REQUEST_TIMEOUT_SECONDS = 10


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


async def _image_analysis_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    provider: InferenceModelProvider,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes the filename of an image. Returns a description of the image.
    """
    model = model_config.model
    print(f"_image_analysis_inference: {provider=}")

    if provider == InferenceModelProvider.REPLICATE:
        description = await replicate_vision_inference(
            aiohttp_session, image_filename, model_config, keys
        )
        return {
            "all_captions": description,
            "description": description,
        }
    elif provider == InferenceModelProvider.AZURE:
        # Don't know why, but Azure comp vision doesn't seem to like JPG files.
        # Convert to PNG.
        image_filename = _convert_image_to_png(image_filename)

        with open(image_filename, "rb") as f:
            image_data = f.read()
            if not image_data:
                raise ValueError("No input image data to image_analysis_inference.")

            raw_metadata = await azure_vision_inference(
                aiohttp_session, image_data, model_config, keys
            )

            if not raw_metadata:
                raise ValueError("Unexpected empty response from image analysis API.")

            if model.provider_model_name.find("v3.2") >= 0:
                return interpret_azure_v3_metadata(raw_metadata)
            else:
                return interpret_azure_v4_metadata(raw_metadata)

    elif provider == InferenceModelProvider.HUGGINGFACE:
        with open(image_filename, "rb") as f:
            image_data = f.read()
            if not image_data:
                raise ValueError("No input image data to image_analysis_inference.")

            description = await image_to_text_inference_hugging_face(
                aiohttp_session, image_data, model_config, keys
            )

            return {
                "all_captions": description,
                "description": description,
            }
    else:
        raise ValueError(
            "Don't know how to do image->text inference for provider "
            f"{model.provider}."
        )


async def image_analysis_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of information about
    the contents of the image.
    """
    mini_gpt_4_task = asyncio.create_task(
        _image_analysis_inference(
            aiohttp_session,
            image_filename,
            InferenceModelProvider.REPLICATE,
            model_config,
            keys,
        )
    )

    azure_cv_task = asyncio.create_task(
        _image_analysis_inference(
            aiohttp_session,
            image_filename,
            InferenceModelProvider.AZURE,
            model_config,
            keys,
        )
    )

    # Execute Azure CV and MiniGPT-4 analsysi in parallel so we can use both
    # without suffering a time penalty.
    # Even though MiniGPT-4 gives a richer description of the scene. Azure is useful
    # because it lists objects and reads text. The combination gives the LLM much
    # more context.
    #
    # On cold starts, a Replicate request can take a very long time while the model
    # loads. Wait only 10s, falling back to just Azure in this case.
    try:
        mini_gpt_4_analysis = await asyncio.wait_for(
            mini_gpt_4_task, REPLICATE_REQUEST_TIMEOUT_SECONDS
        )
        print(f"{mini_gpt_4_analysis=}")
    except Exception as e:
        mini_gpt_4_analysis = {}
        print(f"Error running MiniGTP-4: {e}")

    try:
        azure_analysis = await azure_cv_task
        print(f"{azure_analysis=}")
    except Exception as e:
        azure_analysis = {}
        print(f"Error running Azure Computer Vision: {e}")

    analysis = {
        **azure_analysis,
        "description": (
            f"{mini_gpt_4_analysis.get('description', '')} "
            f"{azure_analysis.get('description', '')}"
        ),
        "all_captions": (
            f"{mini_gpt_4_analysis.get('all_captions', '')} "
            f"{azure_analysis.get('all_captions', '')}"
        ),
    }

    # Return the combined image analysis.
    return analysis


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
