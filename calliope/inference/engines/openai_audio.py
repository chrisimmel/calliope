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
    """
    bytes = str.encode(audio_base64)
    decoded_bytes = base64.b64decode(bytes)
    input_image_filename = create_sequential_filename(
        "input",
        sparrow_id,
        "in",
        "jpg",
        story.cuid,
        0,  # TODO: Handle non-jpeg image input.
    )


    with open("input_audio.webm", "wb") as f:
        f.write(decoded_bytes)
    """

    # For some reason, writing, then reading the file works, where reading
    # through a BytesIO object does not.
    # audio_file = BytesIO(decoded_bytes)
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
