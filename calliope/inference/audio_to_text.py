import httpx

from calliope.inference.engines.openai_audio import openai_text_to_text_inference
from calliope.models import (
    KeysModel,
)


async def audio_to_text_inference(
    httpx_client: httpx.AsyncClient,
    b64_encoded_audio: str,
    keys: KeysModel,
) -> str:
    """
    Takes a base64-encoded audio file and produces text.

    Args:
        httpx_client: the async HTTP session.
        b64_encoded_audio: the filename of the input image.
        keys: API keys, etc.

    Returns:
        a string containing the transcribed text.
    """

    return await openai_text_to_text_inference(httpx_client, b64_encoded_audio, keys)
