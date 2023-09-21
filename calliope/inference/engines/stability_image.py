import io
import math
from typing import Optional

import aiohttp
from PIL import Image
from stability_sdk import client as stability_client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from calliope.models import KeysModel
from calliope.tables import ModelConfig


async def text_to_image_file_inference_stability(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Uses Stable Diffusion via the Stability API to interpret a piece of text as
    an image.

    Args:
        aiohttp_session: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_image_filename: the filename indicating where to write the
            generated image.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        width: the desired image width in pixels.
        height: the desired image height in pixels.

    Returns:
        the filename of the generated image.
    """
    model = model_config.model

    parameters = {
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

    # I see no way to use aiohttp with the Stability Inference API. :-(
    stability_api = stability_client.StabilityInference(
        key=keys.stability_api_key,
        host=keys.stability_api_host,
        verbose=True,  # Print debug messages.
        engine=model.provider_model_name,  # Set the engine to use for generation.
        # Available engines: stable-diffusion-v1 stable-diffusion-v1-5
        # stable-diffusion-512-v2-0 stable-diffusion-768-v2-0
        # stable-diffusion-512-v2-1 stable-diffusion-768-v2-1 stable-inpainting-v1-0
        # stable-inpainting-512-v2-0
    )

    width = width or 512
    height = height or 512

    # Stable Diffusion accepts only multiples of 64 for image dimensions. Can scale or
    # crop afterward to match requested size.
    width = math.ceil(width / 64) * 64
    height = math.ceil(height / 64) * 64

    prompt = [
        # Things we want (positive prompt):
        generation.Prompt(text=text, parameters=generation.PromptParameters(weight=1)),
        # Things we don't want (negative prompt):
        generation.Prompt(
            text=",".join(
                [
                    "Signature",
                    "photorealism",
                    "cell phones",
                    "weird faces or hands",
                    "artist name",
                    "artist logo.",
                ]
            ),
            parameters=generation.PromptParameters(weight=-1),
        ),
    ]

    responses = stability_api.generate(
        prompt=prompt,
        width=width,
        height=height,
        **parameters,
    )
    for response in responses:
        for artifact in response.artifacts:
            if artifact.finish_reason == generation.FILTER:
                raise ValueError(
                    "Your request activated the API's safety filters and could not be "
                    "processed. Please modify the prompt and try again."
                )
            if artifact.type == generation.ARTIFACT_IMAGE:
                img = Image.open(io.BytesIO(artifact.binary))
                img.save(output_image_filename)
                return output_image_filename
    return None
