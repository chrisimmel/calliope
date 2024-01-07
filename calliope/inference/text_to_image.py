from typing import Optional

import httpx

from calliope.inference.engines.hugging_face import (
    text_to_image_file_inference_hugging_face,
)
from calliope.inference.engines.openai_image import text_to_image_file_inference_openai
from calliope.inference.engines.replicate import text_to_image_file_inference_replicate
from calliope.inference.engines.stability_image import (
    text_to_image_file_inference_stability,
)
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


async def text_to_image_file_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[str]:
    """
    Interprets a piece of text as an image. The supported providers are at this
    point Stability (Stable Diffusion), OpenAI (DALL-E), and HuggingFace (Stable
    Diffusion and others).

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_image_filename: the filename indicating where to write the
            generated image.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        width: the desired image width in pixels.
        height: the desired image height in pixels.

    Returns:
        the filename of the generated image.
    """
    model = model_config.model

    if model.provider == InferenceModelProvider.REPLICATE:
        print(
            f"text_to_image_file_inference.replicate {model.provider_model_name} "
            f"({width}x{height})"
        )
        return await text_to_image_file_inference_replicate(
            httpx_client,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    elif model.provider == InferenceModelProvider.STABILITY:
        print(
            f"text_to_image_file_inference.stability {model.provider_model_name} "
            f"({width}x{height})"
        )
        return await text_to_image_file_inference_stability(
            httpx_client,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    elif model.provider == InferenceModelProvider.OPENAI:
        print(
            f"text_to_image_file_inference.openai {model.provider_model_name} "
            f"({width}x{height})"
        )
        return await text_to_image_file_inference_openai(
            httpx_client,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    if model.provider == InferenceModelProvider.HUGGINGFACE:
        print(f"text_to_image_file_inference.huggingface {model.provider_model_name}")
        return await text_to_image_file_inference_hugging_face(
            httpx_client,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    else:
        raise ValueError(
            "Don't know how to do text->image inference for provider "
            f"{model.provider}."
        )
