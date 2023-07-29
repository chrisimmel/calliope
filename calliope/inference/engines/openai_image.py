from typing import Optional

import aiohttp
import aiofiles
import openai

from calliope.models import KeysModel
from calliope.tables import ModelConfig


async def text_to_image_file_inference_openai(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    params = {
        "prompt": text,
        "n": 1,
    }

    if width and height:
        # DALL-E supports images of size 256x256, 512x512, or 1024x1024.
        # The resulting image will be scaled and padded downstream to fit the
        # client's requested dimensions.
        if width >= 1024 or height >= 1024:
            width = height = 1024
        elif width >= 512 or height >= 512:
            width = height = 512
        else:
            width = height = 256
        params["size"] = f"{width}x{height}"
    # If width and height aren't given, we let them default in the API/model.

    openai.api_key = keys.openai_api_key
    openai.aiosession.set(aiohttp_session)
    openai_response = await openai.Image.acreate(**params)

    image_url = openai_response["data"][0]["url"]
    async with aiohttp_session.get(image_url) as resp:
        if resp.status == 200:
            f = await aiofiles.open(output_image_filename, mode="wb")
            await f.write(await resp.read())
            await f.close()

    return output_image_filename
