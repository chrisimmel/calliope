import asyncio
import os
from typing import Any, cast, Optional
import aiofiles

import httpx
import concurrent.futures
import replicate

from calliope.models import (
    KeysModel,
)
from calliope.tables import ModelConfig
from calliope.utils.piccolo import load_json_if_necessary


async def replicate_vision_inference(
    httpx_client: httpx.AsyncClient,
    image_file: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes a stream of bytes representing an image. Returns text about the image.
    Currently hardcoded to use the MiniGPT-4 model.
    """
    model = model_config.model

    if not keys.replicate_api_key:
        raise ValueError(
            "Warning: Missing Replicate authentication key. Aborting request."
        )

    os.environ["REPLICATE_API_TOKEN"] = keys.replicate_api_key

    prompt = "Tell me everything about this scene."

    parameters = {
        "top_p": 1,
        "max_tokens": 1024,
        "temperature": 0.2,
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

    loop = asyncio.get_event_loop()

    def make_replicate_request() -> Any:
        """
        MiniGPT-4 is another multimodal model that is powerful for image analysis.
        model_name = (
            "daanelson/minigpt-4:"
            "b96a2f33cc8e4b0aa23eacfce731b9c41a7d9466d9ed4e167375587b54db9423"
        )
        ... But LLaVa 13B is the new kid on the block.
        """
        model_name = (
            "yorickvp/llava-13b:"
            "e272157381e2a3bf12df3a8edd1f38d1dbd736bbb7437277c8b34175f8fce358"
        )
        return replicate.run(
            model_name,
            input={"image": open(image_file, "rb"), "prompt": prompt, **parameters},
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(make_replicate_request)
        output = await loop.run_in_executor(None, future.result)

    return "".join(list(output))


async def replicate_text_to_text_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    model = model_config.model

    if not keys.replicate_api_key:
        raise ValueError(
            "Warning: Missing Replicate authentication key. Aborting request."
        )

    os.environ["REPLICATE_API_TOKEN"] = keys.replicate_api_key

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

    parameters = {
        "debug": False,
        "top_k": 50,
        "top_p": 0.9,
        "temperature": 0.7,
        "max_new_tokens": 600,
        "min_new_tokens": -1,
        # **parameters
    }

    loop = asyncio.get_event_loop()

    def make_replicate_request() -> Any:
        return replicate.run(
            "mistralai/mistral-7b-v0.1:3e8a0fb6d7812ce30701ba597e5080689bef8a013e5c6a724fafb108cc2426a0",
            input={
                "prompt": text,
                **parameters
            }
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(make_replicate_request)
        output = await loop.run_in_executor(None, future.result)

    return "".join(list(output))


async def text_to_image_file_inference_replicate(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[str]:
    model = model_config.model
    model_name = model.provider_model_name

    if not keys.replicate_api_key:
        raise ValueError(
            "Warning: Missing Replicate authentication key. Aborting request."
        )

    parameters = {
        # "width": 1024,
        # "height": 1024,
        "prompt": text,
        # "refine": "expert_ensemble_refiner",
        # "scheduler": "KarrasDPM",
        "num_outputs": 1,
        "guidance_scale": 8,
        # "high_noise_frac": 0.8,
        # "prompt_strength": 0.9,
        "num_inference_steps": 100,
        "negative_prompt": ",".join(
            [
                "Signature",
                "people",
                "photorealism",
                "cell phones",
                "weird faces or hands",
                "artist name",
                "artist logo.",
            ]
        ),
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

    os.environ["REPLICATE_API_TOKEN"] = keys.replicate_api_key

    loop = asyncio.get_event_loop()

    def make_replicate_request() -> Any:
        return replicate.run(
            # "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            model_name,
            input={
                **parameters
            }
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(make_replicate_request)
        image_urls = await loop.run_in_executor(None, future.result)

    print(f"{image_urls=}")
    if image_urls:
        response = await httpx_client.get(image_urls[0])
        response.raise_for_status()
        f = await aiofiles.open(output_image_filename, mode="wb")
        await f.write(response.read())
        await f.close()

        return output_image_filename

    return None
