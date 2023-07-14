import json

import aiohttp

from calliope.inference.engines.hugging_face import hugging_face_request
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
        text = text.replace(":", "")
        payload = {"inputs": text, "return_full_text": False, "max_new_tokens": 250}
        data = json.dumps(payload)
        # data = text
        response = await hugging_face_request(
            aiohttp_session, data, model.provider_model_name, keys
        )
        predictions = await response.json()
        extended_text = predictions[0]["generated_text"]
    elif model.provider == InferenceModelProvider.OPENAI:
        print(f"text_to_text_inference.openai {model.provider_model_name}")
        extended_text = openai_text_to_text_inference(
            aiohttp_session, text, model_config, keys
        )
        print(f'extended_text="{extended_text}"')
    else:
        raise ValueError(
            "Don't know how to do text->text inference for provider "
            f"{model_config.provider}."
        )

    return extended_text
