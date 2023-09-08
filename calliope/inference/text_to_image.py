from typing import Optional

import aiohttp

from calliope.inference.engines.hugging_face import (
    text_to_image_file_inference_hugging_face,
)
from calliope.inference.engines.openai_image import text_to_image_file_inference_openai
from calliope.inference.engines.stability_image import (
    text_to_image_file_inference_stability,
)
from calliope.inference.engines.modal_stable_diffusion_image import (
    text_to_image_file_inference_modal_stable
)
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


async def text_to_image_file_inference(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """
    Interprets a piece of text as an image. Returns the filename of the resulting image.
    """
    model = model_config.model

    if model.provider == InferenceModelProvider.HUGGINGFACE:
        print(f"text_to_image_file_inference.huggingface {model.provider_model_name}")
        return await text_to_image_file_inference_hugging_face(
            aiohttp_session,
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
            aiohttp_session,
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
            aiohttp_session,
            text,
            output_image_filename,
            model_config,
            keys,
            width,
            height,
        )
    elif model.provider == InferenceModelProvider.MODAL_STABLE_DIFFUSION:
        return await text_to_image_file_inference_modal_stable(
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
            "Don't know how to do text->image inference for provider "
            f"{model_config.provider}."
        )
