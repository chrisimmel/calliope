import httpx

from calliope.inference.engines.openai_audio import openai_text_to_text_inference
from calliope.models import (
    KeysModel,
)


async def audio_to_text_inference(
    httpx_client: httpx.AsyncClient,
    input_audio_filename: str,
    keys: KeysModel,
) -> str:
    """
    Takes an audio file as input and produces text.

    Args:
        httpx_client: the async HTTP session.
        input_audio_filename: the filename of the input audio.
        keys: API keys, etc.

    Returns:
        a string containing the transcribed text.
    """

    return await openai_text_to_text_inference(httpx_client, input_audio_filename, keys)
