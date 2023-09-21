import asyncio
import os
from typing import Any, Dict

import aiohttp
import concurrent.futures
import replicate

from calliope.models import (
    KeysModel,
)
from calliope.tables import ModelConfig


async def replicate_vision_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_file: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
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
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

    loop = asyncio.get_event_loop()

    def make_replicate_request():
        model_name = (
            "daanelson/minigpt-4:"
            "b96a2f33cc8e4b0aa23eacfce731b9c41a7d9466d9ed4e167375587b54db9423"
        )
        return replicate.run(
            model_name,
            input={"image": open(image_file, "rb"), "prompt": prompt, **parameters},
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(make_replicate_request)
        output = await loop.run_in_executor(None, future.result)

    return output
