import sys
import traceback
from typing import Optional

import httpx

from .text_to_text import text_to_text_inference
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
from calliope.tables import (
    InferenceModel,
    ModelConfig,
)


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

    for attempt in range(1, 3):
        try:
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
            elif model.provider == InferenceModelProvider.HUGGINGFACE:
                print(
                    f"text_to_image_file_inference.huggingface {model.provider_model_name}"
                )
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
        except ValueError as e:
            raise e
        except Exception as e:
            # This is simplistic. Assume that any error encountered may be due
            # to risqué content in the prompt. Censor it and try again.
            print(f"attempt {attempt} failed with error: {e}")
            text = censor_text(
                text,
                keys,
                httpx_client,
            )
            print(f"Retrying with censored text: {text}")


async def censor_text(
    text: str,
    keys: KeysModel,
    errors: list[str],
    httpx_client: httpx.AsyncClient,
) -> str:
    """
    Censors the text, such as for use in an image prompt.
    """
    text = (text or "").strip()
    if not text:
        return text

    prompt = f"""You are a copy editor, given a text that may contain sexual, violent,
or otherwise sensitive content not appropriate for all audiences. Modify the text as
necessary to remove any inappropriate content, while doing your best to preserve the author's
tone and the overal meaning and feeling of the text.

Include nothing in your response but the adjusted text.

Here is the text to review:

{text}
"""
    model = (
        await InferenceModel.objects()
        .where(InferenceModel.slug == "openai-gpt-4o")
        .first()
        .output(load_json=True)
        .run()
    )
    if model:
        model_config = ModelConfig(
            slug="gpt-4o-cleaner",
            description="",
            model_parameters={},
            model=model,
        )
    else:
        raise ValueError("No gpt-4o model found.")

    # Use gpt-4o and the prompt above to clean up the text.
    try:
        print(f"Censoring text: {text}")
        text = await text_to_text_inference(httpx_client, prompt, model_config, keys)
        print(f"Censored text: {text}")
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        errors.append(str(e))

    return text
