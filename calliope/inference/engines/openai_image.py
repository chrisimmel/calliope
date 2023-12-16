from typing import Optional

import httpx
import aiofiles
import openai

from calliope.models import KeysModel
from calliope.tables import ModelConfig
from calliope.utils.file import encode_image_file_to_b64


async def text_to_image_file_inference_openai(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Uses DALL-E 2 via the OpenAI API to interpret a piece of text as
    an image.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_image_filename: the filename indicating where to write the
            generated image.
        model_config: the ModelConfig with model and parameters (ignored).
        keys: API keys, etc.
        width: the desired image width in pixels.
        height: the desired image height in pixels.

    Returns:
        the filename of the generated image.
    """
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
    openai.aiosession.set(httpx_client)
    openai_response = await openai.Image.acreate(**params)

    image_url = openai_response["data"][0]["url"]
    response = await httpx_client.get(image_url)
    response.raise_for_status()
    f = await aiofiles.open(output_image_filename, mode="wb")
    await f.write(response.read())
    await f.close()

    return output_image_filename


async def openai_vision_inference(
    httpx_client: httpx.AsyncClient,
    image_file: str,
    b64_encoded_image: Optional[str],
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes a stream of bytes representing an image. Returns text about the image.
    Currently hardcoded to use the MiniGPT-4 model.
    """
    model = model_config.model
    model = "gpt-4-vision-preview"

    if not keys.openai_api_key:
        raise ValueError(
            "Warning: Missing OpenAI authentication key. Aborting request."
        )

    prompt = "Tell me everything you see."
    base64_image = b64_encoded_image or encode_image_file_to_b64(image_file)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {keys.openai_api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    response = await httpx_client.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )
    response.raise_for_status()

    json_response = response.json()
    print(json_response)
    return json_response["choices"][0]["message"]["content"]
