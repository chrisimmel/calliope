import aiofiles
import httpx
import json
import os
from typing import Any, cast, Dict, Optional

from langchain_community.llms import HuggingFaceHub
from tenacity import retry, stop_after_attempt, wait_exponential

# from requests.models import Response

from calliope.models import KeysModel
from calliope.tables import ModelConfig


def _hugging_face_model_to_api_url(model_name: str) -> str:
    # A HuggingFace model name may instead be a direct URL to an inference endpoint.
    return model_name if model_name.startswith("https") else f"https://api-inference.huggingface.co/models/{model_name}"


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1))
async def _hugging_face_request(
    httpx_client: httpx.AsyncClient,
    data: Any,
    model_name: str,
    keys: KeysModel,
    content_type: Optional[str] = None,
) -> httpx.Response:
    """
    Makes a request to the HuggingFace inference API.

    Args:
        httpx_client: the async HTTP session.
        data: input data to pass with the request.
        model_name: the name of the model to invoke.
        keys: API keys, etc.
        content_type: the expected content type.

    Returns:
        the API response.
    """
    api_key = keys.huggingface_api_key
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = content_type

    print(f"_hugging_face_request: {api_url=}, {headers=}, {data=}")
    response = await httpx_client.post(api_url, headers=headers, data=data)
    print(f"{response=}")
    response.raise_for_status()
    return response


async def _text_to_text_inference_hugging_face_http(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Does a text->text inference on HuggingFace Hub via a simple HTTP POST.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the generated text.
    """
    model = model_config.model
    text = text.replace(":", "")
    text = text[-100:]
    payload = {"inputs": text, "max_new_tokens": 150}
    data = json.dumps(payload)
    response = await _hugging_face_request(
        httpx_client, data, model.provider_model_name, keys, "application/json"
    )
    predictions = response.json()
    out_text = predictions[0]["generated_text"] or ""

    if "neo" in model.slug:
        # Hack to remove input text from the output of gpt-neo output if there is any overlap.
        prefix = text
        while len(prefix):
            if out_text.startswith(prefix):
                out_text = out_text[len(prefix):]
                break
            prefix = prefix[1:]

    return out_text

async def _text_to_text_inference_hugging_face_langchain(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Does a text->text inference on HuggingFace Hub via LangChain.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the generated text.
    """
    model = model_config.model

    if keys.huggingface_api_key:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = keys.huggingface_api_key

    parameters = {
        **(
            cast(Dict[str, Any], model.model_parameters)
            if model.model_parameters
            else {}
        ),
        **(
            cast(Dict[str, Any], model_config.model_parameters)
            if model_config.model_parameters
            else {}
        ),
    }

    text = text.replace(":", "")

    extended_text = ""
    chat = HuggingFaceHub(  # type: ignore[call-arg]
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
        extended_text = llm_result.generations[0][0].text or ""

    return extended_text


async def text_to_text_inference_hugging_face(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Performs a text->text inference using a HuggingFace-hosted language
    model.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the generated text.
    """
    return await _text_to_text_inference_hugging_face_http(
        httpx_client, text, model_config, keys
    )


async def text_to_image_file_inference_hugging_face(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Performs a text->image inference using a HuggingFace-hosted model
    such as Stable Diffusion.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_image_filename: the filename indicating where to write the
            generated image.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        width: the desired image width in pixels (ignored).
        height: the desired image height in pixels (ignored).

    Returns:
        the filename of the generated image.
    """
    model = model_config.model

    # width and height are ignored by HuggingFace.
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = await _hugging_face_request(
        httpx_client, data, model.provider_model_name, keys
    )

    f = await aiofiles.open(output_image_filename, mode="wb")
    await f.write(response.content)
    await f.close()

    return output_image_filename


async def image_to_text_inference_hugging_face(
    httpx_client: httpx.AsyncClient,
    image_data: bytes,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes the filename of an image. Returns text derived from the image.
    The specified model must be one that supports this kind of data flow,
    such as an image captioning model.

    Args:
        httpx_client: the async HTTP session.
        image_data: the bytes of the input image.
        model_config: the model configuration.
        keys: API keys, etc.

    Returns:
        a string describing the image.
    """
    model = model_config.model

    response = await _hugging_face_request(
        httpx_client, image_data, model.provider_model_name, keys
    )
    predictions = response.json()
    caption = cast(str, predictions[0]["generated_text"])

    return caption
