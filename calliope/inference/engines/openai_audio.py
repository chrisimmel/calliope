import httpx

from openai import AsyncOpenAI

from calliope.models import (
    KeysModel,
)


async def openai_audio_to_text_inference(
    httpx_client: httpx.AsyncClient,
    input_audio_filename: str,
    language: str,
    keys: KeysModel,
) -> str:
    """
    Performs an audio->text inference using the OpenAI Whisper API.

    Args:
        httpx_client: the async HTTP session.
        input_audio_filename: the name of a file containing the input audio.
        language: the expected language of the audio.
        keys: API keys, etc.

    Returns:
        the generated text.
    """

    with open(input_audio_filename, "rb") as audio_file:
        client = AsyncOpenAI(api_key=keys.openai_api_key, http_client=httpx_client)
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="text",
        )
    print(f"Transcribed audio is: '{transcription}'")

    return transcription
