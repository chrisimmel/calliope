import aiofiles
import aiohttp
import json
import os
from typing import Any, Optional

from langchain import HuggingFaceHub
from requests.models import Response

from calliope.models import KeysModel
from calliope.tables import ModelConfig


def _hugging_face_model_to_api_url(model_name: str) -> str:
    return f"https://api-inference.huggingface.co/models/{model_name}"


async def _hugging_face_request(
    aiohttp_session: aiohttp.ClientSession,
    data: Any,
    model_name: str,
    keys: KeysModel,
    content_type: Optional[str] = None,
) -> Response:
    api_key = keys.huggingface_api_key
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = content_type

    return await aiohttp_session.post(api_url, headers=headers, data=data)


async def _text_to_text_inference_hugging_face_http(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
    """
    Does a text->text inference on HuggingFace Hub via a simple HTTP POST.
    """
    model = model_config.model
    text = text.replace(":", "")
    payload = {"inputs": text, "return_full_text": False, "max_new_tokens": 250}
    data = json.dumps(payload)
    response = await _hugging_face_request(
        aiohttp_session, data, model.provider_model_name, keys, "application/json"
    )
    predictions = await response.json()
    return predictions[0]["generated_text"]


async def _text_to_text_inference_hugging_face_langchain(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
    """
    Does a text->text inference on HuggingFace Hub via LangChain.
    """
    model = model_config.model

    os.environ["HUGGINGFACEHUB_API_TOKEN"] = keys.huggingface_api_key

    parameters = {
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

    text = text.replace(":", "")

    extended_text = None
    chat = HuggingFaceHub(
        repo_id=model.provider_model_name,
        model_kwargs=parameters,
    )
    llm_result = chat.generate([text])
    print(f"Completion response is: '{llm_result}'")
    if (
        llm_result.generations
        and llm_result.generations[0]
        and llm_result.generations[0][0]
    ):
        # generations=[[Generation(text="\nA portrait of a moment in time
        extended_text = llm_result.generations[0][0].text

    return extended_text


async def text_to_text_inference_hugging_face(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
    return await _text_to_text_inference_hugging_face_http(
        aiohttp_session, text, model_config, keys
    )


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
    response = await _hugging_face_request(
        aiohttp_session, data, model.provider_model_name, keys
    )

    if response.status == 200:
        f = await aiofiles.open(output_image_filename, mode="wb")
        await f.write(await response.read())
        await f.close()

    return output_image_filename


async def image_to_text_inference_hugging_face(
    aiohttp_session: aiohttp.ClientSession,
    image_data: bytes,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes the filename of an image. Returns text derived from the image.
    """
    model = model_config.model

    response = await _hugging_face_request(
        aiohttp_session, image_data, model.provider_model_name, keys
    )
    # predictions = json.loads(response.content.decode("utf-8"))
    predictions = await response.json()
    caption = predictions[0]["generated_text"]

    return caption
