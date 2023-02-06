import asyncio
import io
import json
import math
from pprint import pprint
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import aiohttp
import aiofiles
from calliope.utils.file import get_file_extension
import cv2
import openai
from PIL import Image
import requests
from requests.models import Response
from stability_sdk import client as stability_client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from calliope.models import (
    InferenceModelProvider,
    InferenceModelConfigModel,
    InferenceModelConfigsModel,
    KeysModel,
)

# from PIL import Image
# from image_captioning.model import predict


# image_to_text_model = "ydshieh/vit-gpt2-coco-en-ckpts"
# image_to_text_model = "nlpconnect/vit-gpt2-image-captioning"
# text_to_image_model = "runwayml/stable-diffusion-v1-5"
# text_prediction_model = "EleutherAI/gpt-neo-2.7B"
# text_prediction_model = "EleutherAI/gpt-neox-20b"
# speech_recognition_model = "facebook/wav2vec2-large-960h-lv60-self"
# voice_activity_detection_model = "pyannote/voice-activity-detection"


def _hugging_face_model_to_api_url(model_name: str) -> str:
    return f"https://api-inference.huggingface.co/models/{model_name}"


async def _hugging_face_request(
    aiohttp_session: aiohttp.ClientSession,
    data: Any,
    model_name: str,
    keys: KeysModel,
) -> Response:
    api_key = keys.huggingface_api_key
    api_url = _hugging_face_model_to_api_url(model_name)
    headers = {"Authorization": f"Bearer {api_key}"}
    return await aiohttp_session.post(api_url, headers=headers, data=data)


async def _hugging_face_image_to_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_data: bytes,
    inference_model_config: InferenceModelConfigModel,
    keys: KeysModel,
) -> str:
    """
    Takes the filename of an image. Returns a caption.
    """
    response = await _hugging_face_request(
        aiohttp_session, image_data, inference_model_config.model_name, keys
    )
    # predictions = json.loads(response.content.decode("utf-8"))
    predictions = await response.json()
    caption = predictions[0]["generated_text"]

    return caption


async def image_file_to_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    inference_model_configs: InferenceModelConfigsModel,
    keys: KeysModel,
) -> Optional[str]:
    """
    Takes the filename of an image. Returns a caption.
    """
    model_config = inference_model_configs.image_to_text_model_config

    if model_config.provider == InferenceModelProvider.AZURE:
        image_metadata = await image_analysis_inference(
            aiohttp_session,
            image_filename,
            inference_model_configs,
            keys,
        )
        return image_metadata.get("description")
    elif model_config.provider != InferenceModelProvider.HUGGINGFACE:
        raise ValueError(
            f"Don't know how to do image->text inference for provider {model_config.provider}."
        )

    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        return await _hugging_face_image_to_text_inference(
            aiohttp_session, image_data, model_config, keys
        )

    return None


def _convert_image_to_png(image_filename: str) -> str:
    extension = get_file_extension(image_filename)
    if extension != "png":
        image_filename_png = image_filename + ".png"
        img = Image.open(image_filename)
        img.save(image_filename_png)
        image_filename = image_filename_png

    return image_filename


def _azure_endpoint_to_api_url(azure_api_host: str, endpoint_name: str) -> str:
    """
    Example:
    https://calliope-cognitive-services-1.cognitiveservices.azure.com/vision/v3.2/analyze?visualFeatures=Categories,Description,Faces,Objects,Tags
    """
    return f"{azure_api_host}{endpoint_name}"


async def _azure_vision_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_data: bytes,
    inference_model_config: InferenceModelConfigModel,
    keys: KeysModel,
) -> Dict[str, Any]:
    api_host = keys.azure_api_host
    api_key = keys.azure_api_key
    endpoint_name = inference_model_config.model_name
    params = inference_model_config.parameters or {}
    api_url = _azure_endpoint_to_api_url(api_host, endpoint_name)

    if params:
        params_str = urlencode(params)
        api_url += f"?{params_str}"

    headers = {
        "Content-Type": "application/octet-stream",
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
        # "Accept-Encoding": "gzip, deflate, br",
    }
    response = await aiohttp_session.post(api_url, headers=headers, data=image_data)
    return await response.json()


def _interpret_azure_v3_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    captions = [
        caption.get("text", "")
        for caption in raw_metadata.get("description", {}).get("captions", [])
    ]
    tags = [tag.get("name", "") for tag in raw_metadata.get("tags", [])]
    for tag in raw_metadata.get("description", {}).get("tags", []):
        if tag not in tags:
            tags.append(tag)

    objects = [object.get("object") for object in raw_metadata.get("objects", [])]

    description = ". ".join(captions)
    if description:
        description += ". "

    if tags:
        tags_phrase = ", ".join(tags)
        description += " " + tags_phrase

    if objects:
        objects_phrase = ""
        for object in objects:
            if object.lower() not in tags:
                if objects_phrase:
                    objects_phrase += ", "
                objects_phrase += object
        if objects_phrase:
            description += f", {objects_phrase}"

    return {
        "captions": captions,
        "tags": tags,
        "objects": objects,
        "description": description,
    }


def _interpret_azure_v4_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    ignore_items = (
        "selfie",
        "human face",
        "jaw",
        "eyeball",
        "eyebrow",
        "forehead",
        "chin",
        "cheek",
        "clothing",
        "wearing",
        "wrinkle",
        "skin",
    )
    captions = [
        description.get("text", "").replace("taking a selfie", "looking at me")
        for description in raw_metadata.get("descriptionResult", {}).get("values", [])
    ]
    tags = [
        tag.get("name", "")
        for tag in raw_metadata.get("tagsResult", {}).get("values", [])
    ]
    tags = [thing for thing in tags if thing not in ignore_items]

    objects = [
        object.get("name")
        for object in raw_metadata.get("objectsResult", {}).get("values", [])
    ]
    objects = [thing for thing in objects if thing not in ignore_items]

    text = raw_metadata.get("readResult", {}).get("content")

    all_captions = ". ".join(captions)
    if all_captions:
        all_captions += "."

    description = all_captions
    if description:
        description += " "

    all_tags_and_objects = ""
    if tags:
        all_tags_and_objects = ", ".join(tags)

    if objects:
        objects_phrase = ""
        for object in objects:
            object = object.lower()
            if object not in tags and object:
                if objects_phrase:
                    objects_phrase += ", "
                objects_phrase += object
        if objects_phrase:
            all_tags_and_objects += f", {objects_phrase}"

    if all_tags_and_objects:
        description += all_tags_and_objects

    if text:
        description += ". " + text

    return {
        "captions": captions,
        "tags": tags,
        "objects": objects,
        "all_captions": all_captions,
        "all_tags_and_objects": all_tags_and_objects,
        "text": text,
        "description": description,
    }


async def image_analysis_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    inference_model_configs: InferenceModelConfigsModel,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of metadata about the image.
    """
    model_config = inference_model_configs.image_analysis_model_config

    if model_config.provider != InferenceModelProvider.AZURE:
        raise ValueError(
            f"Don't know how to do image analysis for provider {model_config.provider}."
        )

    # Don't know why, but Azure comp vision doesn't seem to like JPG files. Convert to PNG.
    image_filename = _convert_image_to_png(image_filename)
    with open(image_filename, "rb") as f:
        image_data = f.read()

        if image_data:
            raw_metadata = await _azure_vision_inference(
                aiohttp_session, image_data, model_config, keys
            )

            if not raw_metadata:
                return ValueError("Unexpected empty response from image analysis API.")

            if model_config.model_name.find("v3.2") >= 0:
                return _interpret_azure_v3_metadata(raw_metadata)
            else:
                return _interpret_azure_v4_metadata(raw_metadata)

    raise ValueError("No input image data to image_analysis_inference.")


async def image_ocr_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_filename: str,
    inference_model_configs: InferenceModelConfigsModel,
    keys: KeysModel,
) -> Dict[str, Any]:
    """
    Takes the filename of an image. Returns a dictionary of metadata.
    """
    model_config = inference_model_configs.image_ocr_model_config

    if model_config.provider != InferenceModelProvider.AZURE:
        raise ValueError(
            f"Don't know how to do image OCR for provider {model_config.provider}."
        )

    # Don't know why, but Azure comp vision doesn't seem to like JPG files. Convert to PNG.
    image_filename = _convert_image_to_png(image_filename)
    with open(image_filename, "rb") as f:
        image_data = f.read()

    if image_data:
        return await _azure_vision_inference(
            aiohttp_session, image_data, model_config, keys
        )

    raise ValueError("No input image data to image_analysis_inference.")


async def _text_to_image_file_inference_hugging_face(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: InferenceModelConfigModel,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    # width and height are ignored by HuggingFace.
    payload = {"inputs": text}
    data = json.dumps(payload)
    response = await _hugging_face_request(
        aiohttp_session, data, model_config.model_name, keys
    )

    if response.status == 200:
        f = await aiofiles.open(output_image_filename, mode="wb")
        await f.write(await response.read())
        await f.close()

    return output_image_filename


async def _text_to_image_file_inference_stability(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: InferenceModelConfigModel,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    # I see no way to use aiohttp with the Stability Inference API. :-(
    stability_api = stability_client.StabilityInference(
        key=keys.stability_api_key,
        host=keys.stability_api_host,
        verbose=True,  # Print debug messages.
        engine=model_config.model_name,  # Set the engine to use for generation.
        # Available engines: stable-diffusion-v1 stable-diffusion-v1-5 stable-diffusion-512-v2-0 stable-diffusion-768-v2-0
        # stable-diffusion-512-v2-1 stable-diffusion-768-v2-1 stable-inpainting-v1-0 stable-inpainting-512-v2-0
    )

    width = width or 512
    height = height or 512

    # Stable Diffusion accepts only multiples of 64 for image dimensions. Can scale or crop
    # afterward to mach requested size.
    width = math.ceil(width / 64) * 64
    height = math.ceil(height / 64) * 64

    responses = stability_api.generate(
        prompt=text,
        width=width,
        height=height,
        **model_config.parameters,
    )
    for response in responses:
        for artifact in response.artifacts:
            if artifact.finish_reason == generation.FILTER:
                raise ValueError(
                    "Your request activated the API's safety filters and could not be processed."
                    "Please modify the prompt and try again."
                )
            if artifact.type == generation.ARTIFACT_IMAGE:
                img = Image.open(io.BytesIO(artifact.binary))
                img.save(output_image_filename)
                return output_image_filename
    return None


async def _text_to_image_file_inference_openai(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: InferenceModelConfigModel,
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

    openai.api_key = keys.openapi_api_key
    openai.aiosession.set(aiohttp_session)
    openai_response = await openai.Image.acreate(**params)

    image_url = openai_response["data"][0]["url"]
    async with aiohttp_session.get(image_url) as resp:
        if resp.status == 200:
            f = await aiofiles.open(output_image_filename, mode="wb")
            await f.write(await resp.read())
            await f.close()

    return output_image_filename


async def text_to_image_file_inference(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    inference_model_configs: InferenceModelConfigsModel,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Interprets a piece of text as an image. Returns the filename of the resulting image.
    """
    model_config = inference_model_configs.text_to_image_model_config

    if model_config.provider == InferenceModelProvider.HUGGINGFACE:
        print(f"text_to_image_file_inference.huggingface {model_config.model_name}")
        return await _text_to_image_file_inference_hugging_face(
            aiohttp_session,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    elif model_config.provider == InferenceModelProvider.STABILITY:
        print(
            f"text_to_image_file_inference.stability {model_config.model_name} ({width}x{height})"
        )
        return await _text_to_image_file_inference_stability(
            aiohttp_session,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    elif model_config.provider == InferenceModelProvider.OPENAI:
        print(
            f"text_to_image_file_inference.openai {model_config.model_name} ({width}x{height})"
        )
        return await _text_to_image_file_inference_openai(
            aiohttp_session,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    else:
        raise ValueError(
            f"Don't know how to do text->image inference for provider {model_config.provider}."
        )


async def text_to_extended_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    inference_model_configs: InferenceModelConfigsModel,
    keys: KeysModel,
) -> str:
    model_config = inference_model_configs.text_to_text_model_config

    if model_config.provider == InferenceModelProvider.HUGGINGFACE:
        print(f"text_to_extended_text_inference.huggingface {model_config.model_name}")
        text = text.replace(":", "")
        payload = {"inputs": text}
        data = json.dumps(payload)
        response = await _hugging_face_request(
            aiohttp_session, data, model_config.model_name, keys
        )
        predictions = await response.json()
        extended_text = predictions[0]["generated_text"]
    elif model_config.provider == InferenceModelProvider.OPENAI:
        print(f"text_to_extended_text_inference.openai {model_config.model_name}")
        openai.api_key = keys.openapi_api_key

        openai.aiosession.set(aiohttp_session)
        completion = await openai.Completion.acreate(
            engine=model_config.model_name,
            prompt=text,
            **model_config.parameters,
        )
        extended_text = completion.choices[0].text
        print(f'extended_text="{extended_text}"')
    else:
        raise ValueError(
            f"Don't know how to do text->text inference for provider {model_config.provider}."
        )

    return extended_text


CAPTION_TOKEN = "{x}"


def caption_to_prompt(caption: str, prompt_template: str) -> Optional[str]:
    prompt = prompt_template.replace(CAPTION_TOKEN, caption) if caption else None

    """
    # Try to prevent caching in inference API. Salt the prompt with a timestamp...
    import datetime
    timestamp = str(datetime.datetime.now())
    prompt = f"{prompt} {timestamp}"
    """

    return prompt
