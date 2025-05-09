import httpx
from typing import Optional

from calliope.inference.engines.runway import runway_image_and_text_to_video_inference
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


async def image_and_text_to_video_file_inference(
    httpx_client: httpx.AsyncClient,
    prompt_image_file: str,
    prompt_text: str,
    output_video_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
    """
    Converts image and text descriptions into video using text-to-video generation models.
    Currently supports Runway's Gen-4 models.

    Args:
        httpx_client: the async HTTP session.
        prompt_image_file: the input image, to be sent as a prompt.
        prompt_text: the input text, to be sent as a prompt.
        output_video_filename: the filename indicating where to write the
            generated video.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the filename of the generated video, or None if generation failed.
    """
    model = model_config.model
    model = await model_config.get_related(ModelConfig.model)

    if model.provider == InferenceModelProvider.RUNWAY:
        print(
            f"text_and_image_to_video_inference.runway {model.provider_model_name} "
        )
        return await runway_image_and_text_to_video_inference(
            httpx_client=httpx_client,
            prompt_image_file=prompt_image_file,
            prompt_text=prompt_text,
            output_video_filename=output_video_filename,
            model=model,
            model_config=model_config,
            keys=keys,
        )
    else:
        raise ValueError(
            "Don't know how to do image+text->video inference for provider "
            f"{model.provider}."
        )
