import math
from typing import Optional

import httpx

from calliope.models import KeysModel
from calliope.tables import ModelConfig
from calliope.utils.file import decode_b64_to_file
from calliope.utils.piccolo import load_json_if_necessary


async def text_to_image_file_inference_stability(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[str]:
    """
    Uses Stable Diffusion via the Stability REST API to interpret a piece of text as
    an image.

    Args:
        httpx_client: the async HTTP session.
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
    api_host = "https://api.stability.ai"

    parameters = {
        **(
            load_json_if_necessary(model.model_parameters)
            if model.model_parameters
            else {}
        ),
        **(
            load_json_if_necessary(model_config.model_parameters)
            if model_config.model_parameters
            else {}
        ),
    }
    engine_id = model.provider_model_name
    url = f"{api_host}/v1/generation/{engine_id}/text-to-image"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {keys.stability_api_key}"
    }

    """
    The current engines as of 16.12.2023:

    'esrgan-v1-x2plus', # Gives status 500
    'stable-diffusion-xl-1024-v0-9',
    'stable-diffusion-xl-1024-v1-0',
    'stable-diffusion-v1-6',
    'stable-diffusion-512-v2-1',  # Older version, more basic output.
    'stable-diffusion-xl-beta-v2-2-2'

    To print a fresh list, uncomment the following:
    response = await httpx_client.get(
        "https://api.stability.ai/v1/engines/list",
        headers=headers
    )
    print(f"Stable Diffusion engines: {[e['id'] for e in response.json()]}")
    """

    width = width or 512
    height = height or 512

    """
    Error: "for stable-diffusion-xl-1024-v0-9 and
    stable-diffusion-xl-1024-v1-0 the allowed dimensions are
    1024x1024, 1152x896, 1216x832, 1344x768, 1536x640,
    640x1536, 768x1344, 832x1216, 896x1152,
    but we received 512x512
    """
    if (
        engine_id not in (
            'stable-diffusion-v1-6',
            'stable-diffusion-512-v2-1',
            'stable-diffusion-xl-beta-v2-2-2'
        ) and width < 1024 and height < 1024
    ):
        # Small image sizes are rejected by big SD models.
        # Force a 1024x1024 image size.
        width = 1024
        height = 1024
        
    # Stable Diffusion accepts only multiples of 64 for image dimensions. Can scale or
    # crop afterward to match requested size.
    width = math.ceil(width / 64) * 64
    height = math.ceil(height / 64) * 64

    payload = {
        # "cfg_scale": 7,
        # "clip_guidance_preset": "FAST_BLUE",
        "height": height,
        "width": width,
        # "sampler": "K_DPM_2_ANCESTRAL",
        # "samples": 1,
        # "steps": 30,
        **parameters,
        "text_prompts": [
            {
                # Things we want (positive prompt):
                "text": text,
                "weight": 1
            },
            {
                # Things we don't want (negative prompt):
                "text": ",".join(
                    [
                        "Signature",
                        "photorealism",
                        "cell phones",
                        "weird faces or hands",
                        "artist name",
                        "artist logo",
                        "Eiffel tower."
                    ]),
                "weight": -1
            }
        ]
    }

    response = await httpx_client.post(
        url,
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        print(f"{response.text=}")
        response.raise_for_status()

    json_response = response.json()
    artifacts = json_response.get("artifacts", [])
    for artifact in artifacts:
        finish_reason = artifact.get("finish_reason")
        if finish_reason == "CONTENT_FILTERED":
            print(
                "Your request activated the API's safety filters and could not be "
                "processed. Please modify the prompt and try again."
            )

        b64_image = artifact.get("base64")
        if b64_image:
            decode_b64_to_file(b64_image, output_image_filename)
            return output_image_filename

    return None


"""
Am deprecating use of the Stability Python SDK in Calliope.

It appears to be impossible to use aiohttp/httpx with the
Stability Inference API. Per Stability staff, this is due to a
fundamental limitation of their gRPC-based implementation, ad the
only way to get async support is through use of their REST API.
https://github.com/Stability-AI/stability-sdk/issues/197#issuecomment-1496027391
Hence the alternative REST version of this function above, now preferred.

import io
from PIL import Image
from stability_sdk import client as stability_client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

async def text_to_image_file_inference_stability_sdk(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[str]:
    ""
    Uses Stable Diffusion via the Stability API and SDK to interpret a
    piece of text as an image.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_image_filename: the filename indicating where to write the
            generated image.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        width: the desired image width in pixels.
        height: the desired image height in pixels.

    Returns:
        the filename of the generated image.
    ""
    model = model_config.model

    parameters = {
        **(
            load_json_if_necessary(model.model_parameters)
            if model.model_parameters
            else {}
        ),
        **(
            load_json_if_necessary(model_config.model_parameters)
            if model_config.model_parameters
            else {}
        ),
    }

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
"""
