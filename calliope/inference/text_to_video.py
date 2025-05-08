import httpx
from typing import Optional

from calliope.inference.engines.runway import runway_text_to_video_inference
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


async def text_to_video_file_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_video_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
    num_frames: Optional[int] = None,
    fps: Optional[int] = None,
) -> Optional[str]:
    """
    Converts text descriptions into video using text-to-video generation models.
    Currently supports Runway's Gen-4 Turbo model.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        output_video_filename: the filename indicating where to write the
            generated video.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        width: the desired video width in pixels.
        height: the desired video height in pixels.
        num_frames: the desired number of frames.
        fps: frames per second.

    Returns:
        the filename of the generated video, or None if generation failed.
    """
    model = model_config.model

    if model.provider == InferenceModelProvider.RUNWAY:
        print(
            f"text_to_video_file_inference.runway {model.provider_model_name} "
            f"({width}x{height}, {num_frames} frames @ {fps} fps)"
        )
        return await runway_text_to_video_inference(
            httpx_client,
            text,
            output_video_filename,
            model_config,
            keys,
            width,
            height,
            num_frames,
            fps,
        )
    else:
        raise ValueError(
            "Don't know how to do text->video inference for provider "
            f"{model.provider}."
        )