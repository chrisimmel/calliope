from typing import Any, Dict
from urllib.parse import urlencode

import aiohttp

from calliope.models import KeysModel
from calliope.tables import ModelConfig


def _azure_endpoint_to_api_url(azure_api_host: str, endpoint_name: str) -> str:
    """
    Example:
    https://calliope-cognitive-services-1.cognitiveservices.azure.com/vision/v3.2/
    analyze?visualFeatures=Categories,Description,Faces,Objects,Tags
    """
    return f"{azure_api_host}{endpoint_name}"


async def azure_vision_inference(
    aiohttp_session: aiohttp.ClientSession,
    image_data: bytes,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
    model = model_config.model

    parameters = {
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

    api_host = keys.azure_api_host
    api_key = keys.azure_api_key
    endpoint_name = model.provider_model_name
    api_url = _azure_endpoint_to_api_url(api_host, endpoint_name)

    if parameters:
        params_str = urlencode(parameters)
        api_url += f"?{params_str}"

    headers = {
        "Content-Type": "application/octet-stream",
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
        # "Accept-Encoding": "gzip, deflate, br",
    }
    response = await aiohttp_session.post(api_url, headers=headers, data=image_data)
    return await response.json()


def interpret_azure_v3_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
    captions = [
        caption.get("text", "")
        for caption in raw_metadata.get("description", {}).get("captions", [])
    ]
    captions = [caption[0:1].upper() + caption[1:] for caption in captions]

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


def interpret_azure_v4_metadata(raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
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
    captions = [caption[0:1].upper() + caption[1:] for caption in captions]
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
