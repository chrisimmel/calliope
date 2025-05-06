import json
from typing import Any, Optional

import httpx
import aiofiles
import openai
from openai import AsyncOpenAI

from calliope.models import KeysModel
from calliope.tables import ModelConfig
from calliope.utils.file import decode_b64_to_file, encode_image_file_to_b64


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
    Generate an image from a prompt using an OpenAI model (gpt-image-1, DALL-E 3, DALL-E 2).

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
    model_name = model_config.model.provider_model_name

    params = {
        "prompt": text,
        "n": 1,
    }
    if width and height and "DALL-E" in model_name:
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
    else:
        # Hardcode to a square image for gpt-image-1.
        # (fastest, and fits our standard usecase)
        params["size"] = "1024x1024"

    client = AsyncOpenAI(api_key=keys.openai_api_key, http_client=httpx_client)

    # openai_response = await openai.Image.acreate(**params)
    response = await client.images.generate(
        model=model_name,
        prompt=text,
    )

    image_base64 = response.data[0].b64_json
    decode_b64_to_file(image_base64, output_image_filename)
    return output_image_filename


async def openai_vision_inference_ext(
    httpx_client: httpx.AsyncClient,
    image_file: str,
    b64_encoded_image: Optional[str],
    model_config: ModelConfig,
    keys: KeysModel,
) -> dict[str, Any]:
    """
    Takes a stream of bytes representing an image. Returns text about the image.
    """
    model = model_config.model
    # model = "gpt-4-vision-preview"
    model = "gpt-4o"

    if not keys.openai_api_key:
        raise ValueError("Warning: Missing OpenAI authentication key. Aborting request.")

    prompt = """Tell me everything you see. Focus especially on these elements:
* People. People you see will be cast in the story like actors in a play. Describe each of
them carefully, so the casting director can make good casting decisions and recognize
whether they have already been seen in an earlier image.

* Anything you can understand about the setting and atmosphere.

* Objects that may be interesting to include in the story, now or later.

* Text. If there is any text in the image, transcribe it and try to understand its
context and significance. If text fragments are independent, describe them separately. If.
for instance, there are multiple books with visible titles, describe each book separately.
If there are multiple signs, describe each sign separately. Etc. Only report text you
actually see in the image.

Assemble your observations into the following JSON structure:
{
    "description": "<OVERALL DESCRIPTION OF THE SCENE>",
    "people": [
        {
            "description": "<OVERALL DESCRIPTION OF PERSON 1>",
            "hair_color": "<HAIR COLOR OF PERSON 1>",
            "gender": "<ESTIMATED BIOLOGICAL GENDER OF PERSON 1>",
            "approximate_age": "<ONE OF: 'child', 'young_adult', 'adult', 'middle_aged', 'old_and_wise'>",
            "emotions": "<EMOTIONS OF PERSON 1>",
            "attire": "<NOTABLE ASPECTS OF ATTIRE>"
            "other_attributes": {
                <ANYTHING NOTABLE ABOUT THE PERSON THAT ISN'T OTHERWISE CAPTURED BY THIS SCHEMA>
            }
        },
        {
            <SAME FOR PERSON 2>
        },
        etc.
    ],
    "objects": [
        {
            "description": "<OVERALL DESCRIPTION OF OBJECT 1>",
            "purpose": "<WHAT IS THIS OBJECT FOR?>",
            "location": "<WHERE IS THIS OBJECT IN THE IMAGE?>",
            "other_attributes": {
                <ANYTHING NOTABLE ABOUT THE OBJECT THAT ISN'T OTHERWISE CAPTURED BY THIS SCHEMA>
            }
        },
        {
            <SAME FOR OBJECT 2>
        },
        etc.
    ],
    "text_fragments": [
        {
            "text": "<TEXT FRAGMENT 1>",
            "language": "<LANGUAGE OF TEXT FRAGMENT 1>",
            "context": "<CONTEXT OF TEXT FRAGMENT 1>",
            "significance": "<SIGNIFICANCE OF TEXT FRAGMENT 1>"
        },
        {
            <SAME FOR TEXT FRAGMENT 2>
        },
        etc.
    ],
    "atmosphere": "<A DESCRIPTION OF THE SCENE'S ATMOSPHERE, IF PERTINENT.",
    "setting": "<A DESCRIPTION OF THE SPACE: INTERIOR OR EXTERIOR, WHAT KIND OF PLACE, ARCHITECTURE?, CULTURAL MARKERS?, ETC.>",
}
        """
    base64_image = b64_encoded_image or encode_image_file_to_b64(image_file)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {keys.openai_api_key}",
    }

    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You are a very watchful and insightful analyzer of images. "
                "You are analyzing a sequence of images, one at a time. "
                "Your observations will be used as elements in an ongoing story. "
                "You are especially good at describing the mood and atmosphere of a space, "
                "as well as the physical attributes, attire, and emotions of people.",
            },
            {
                "role": "system",
                "content": "It is IMPORTANT that you only include things you really see. "
                "Don't imagine or invent book titles, other text fragments, or people that "
                "aren't actually there, for instance. Your job is to faithfully report what "
                "you see, not to be imaginitive or creative.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ],
        "max_tokens": 2000,
        "temperature": 0,
    }

    response = await httpx_client.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    # TODO: Use OpenAI SDK?
    response.raise_for_status()

    json_response = response.json()
    json_str = json_response["choices"][0]["message"]["content"]
    json_response = json.loads(json_str)
    print(json.dumps(json_response, indent=2))

    return json_response


async def openai_vision_inference(
    httpx_client: httpx.AsyncClient,
    image_file: str,
    b64_encoded_image: Optional[str],
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Takes a stream of bytes representing an image. Returns text about the image.
    Currently hardcoded to use the gpt-4o model.
    """
    model = model_config.model
    # model = "gpt-4-vision-preview"
    model = "gpt-4o"

    if not keys.openai_api_key:
        raise ValueError("Warning: Missing OpenAI authentication key. Aborting request.")

    prompt = "Tell me everything you see."
    base64_image = b64_encoded_image or encode_image_file_to_b64(image_file)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {keys.openai_api_key}",
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
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }

    response = await httpx_client.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    response.raise_for_status()

    json_response = response.json()
    print(json_response)
    return json_response["choices"][0]["message"]["content"]
