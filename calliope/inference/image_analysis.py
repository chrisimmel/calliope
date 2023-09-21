import asyncio
from typing import Any, Dict

import aiohttp

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
from calliope.utils.image import convert_pil_image_to_png


# The number of seconds to wait for a Replicate request to complete.
# This is to prevent long waits for model cold starts.
REPLICATE_REQUEST_TIMEOUT_SECONDS = 10


# Some interesting models not currently in use...
# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
# image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
# text_to_image_model = "runwayml/stable-diffusion-v1-5"
# text_prediction_model = "EleutherAI/gpt-neo-2.7B"
# text_prediction_model = "EleutherAI/gpt-neox-20b"
# speech_recognition_model = "facebook/wav2vec2-large-960h-lv60-self"
# voice_activity_detection_model = "pyannote/voice-activity-detection"


async def _image_analysis_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    provider: InferenceModelProvider,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of information about
    the contents of the image.

    Args:
        aiohttp_session: the async HTTP session.
        image_filename: the filename of the input image.
        provider: the InferenceModelProvider.
        model_config: the model configuration.
        keys: API keys, etc.

    Returns:
        a dictionary containing the image analysis. The
        analysis adheres to the following schema:

            "captions": a list of captions describing the image.
            "all_captions": the captions list, concatenated into a
                string for humans or LLMs to read.
            "tags": a list of tags appropriate to the image.
            "objects": a list of objects detected in the image.
            "all_tags_and_objects": the tags and objects lists,
                concatenated into a single string for humans
                and LLMs. 
            "text": any text seen in the image.
            "description": a text description, summarizing all the
                above.

        The description and all_captions fields are provided at a
        minimum, regardless of the InferenceModelProvider.
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
        image_filename = convert_pil_image_to_png(image_filename)

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
    the contents of the image. The analysis is drawn from two distinct
    resources:
        Azure Computer Vision: The Azure Computer Vision API is used to
           generate a high-level image description, lists of recognized
           objects and tags, and any text detected in the image.

        Mini-GPT-4: The multi-modal Mini-GPT-4 model is used to generate
           a very rich image description with much more detail than Azure
           produces. This includes text seen in the image, but also a
           much more human-like summary of the scene.

    API calls are made to both Azure and Mini-GPT-4 simultaneously, and
    the results are combined in the returned analysis. Because cold start
    on the Replicate service that hosts Mini-GPT-4 can be lengthy (up to
    a minute or so to load the model it hasn't been used recently), we set
    a 10-second timeout on the Mini-GPT-4 call, and just return the Azure
    analysis if there is a problem.

    Args:
        aiohttp_session: the async HTTP session.
        image_filename: the filename of the input image.
        provider: the InferenceModelProvider.
        model_config: the model configuration.
        keys: API keys, etc.

    Returns:
        a dictionary containing the image analysis. The
        analysis adheres to the following schema:

            "captions": a list of captions describing the image.
            "all_captions": the captions list, concatenated into a
                string for humans or LLMs to read.
            "tags": a list of tags appropriate to the image.
            "objects": a list of objects detected in the image.
            "all_tags_and_objects": the tags and objects lists,
                concatenated into a single string for humans
                and LLMs. 
            "text": any text seen in the image.
            "description": a text description, summarizing all the
                above.

        The description and all_captions fields are provided at a
        minimum, regardless of the InferenceModelProvider.
    """

    # Note that we ignore model_config.model.provider. For now this
    # is hardcoded to always use InferenceModelProvider.REPLICATE
    # and InferenceModelProvider.AZURE.
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

    # Execute Azure CV and MiniGPT-4 analyis in parallel so we can use both
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
        print(f"Error running MiniGPT-4: {e}")

    try:
        azure_analysis = await azure_cv_task
        print(f"{azure_analysis=}")
    except Exception as e:
        azure_analysis = {}
        print(f"Error running Azure Computer Vision: {e}")

    # Merge the Azure and Mini-GPT-4 analyses.
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
            f"Don't know how to do image OCR for provider {model.provider}."
        )

    # Don't know why, but Azure comp vision doesn't seem to like JPG files.
    # Convert to PNG.
    image_filename = convert_pil_image_to_png(image_filename)
    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        return await azure_vision_inference(
            aiohttp_session, image_data, model_config, keys
        )

    raise ValueError("No input image data to image_analysis_inference.")
