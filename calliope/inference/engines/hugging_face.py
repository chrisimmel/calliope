import aiofiles
import aiohttp
import json
from typing import Any, Optional

from requests.models import Response

from calliope.models import KeysModel
from calliope.tables import ModelConfig


def _hugging_face_model_to_api_url(model_name: str) -> str:
    return f"https://api-inference.huggingface.co/models/{model_name}"


async def hugging_face_request(
    aiohttp_session: aiohttp.ClientSession,
    data: Any,
    model_name: str,
    keys: KeysModel,
) -> Response:
    api_key = keys.huggingface_api_key
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {api_key}"}
    return await aiohttp_session.post(api_url, headers=headers, data=data)


async def text_to_image_file_inference_hugging_face(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    model = model_config.model

    # width and height are ignored by HuggingFace.
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = await hugging_face_request(
        aiohttp_session, data, model.provider_model_name, keys
    )

    if response.status == 200:
        f = await aiofiles.open(output_image_filename, mode="wb")
        await f.write(await response.read())
        await f.close()

    return output_image_filename


async def hugging_face_image_to_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_data: bytes,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes the filename of an image. Returns a caption.
    """
    model = model_config.model

    response = await hugging_face_request(
        aiohttp_session, image_data, model.provider_model_name, keys
    )
    # predictions = json.loads(response.content.decode("utf-8"))
    predictions = await response.json()
    caption = predictions[0]["generated_text"]

    return caption
