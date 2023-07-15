import aiohttp

from calliope.inference.engines.hugging_face import text_to_text_inference_hugging_face
from calliope.inference.engines.openai_text import openai_text_to_text_inference
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


async def text_to_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    print(f"text_to_text_inference: {model_config.slug}, {model_config.model}")
    model = model_config.model

    if model.provider == InferenceModelProvider.HUGGINGFACE:
        print(f"text_to_text_inference.huggingface {model.provider_model_name}")
        extended_text = await text_to_text_inference_hugging_face(
            aiohttp_session, text, model_config, keys
        )
        print(f'extended_text="{extended_text}"')
    elif model.provider == InferenceModelProvider.OPENAI:
        print(f"text_to_text_inference.openai {model.provider_model_name}")
        extended_text = await openai_text_to_text_inference(
            aiohttp_session, text, model_config, keys
        )
        print(f'extended_text="{extended_text}"')
    else:
        raise ValueError(
            "Don't know how to do text->text inference for provider "
            f"{model_config.provider}."
        )

    return extended_text