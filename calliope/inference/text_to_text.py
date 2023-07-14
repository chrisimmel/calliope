import json

import aiohttp
import openai

from calliope.inference.engines.hugging_face import hugging_face_request
from calliope.models import (
    InferenceModelProvider,
    KeysModel,
    InferenceModelProviderVariant,
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

    parameters = {
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

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
        openai.api_key = keys.openapi_api_key
        openai.aiosession.set(aiohttp_session)

        if (
            model.provider_api_variant
            == InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION
        ):
            messages = [
                {
                    "role": "user",
                    "content": text,
                }
            ]

            response = await openai.ChatCompletion.acreate(
                model=model.provider_model_name,
                messages=messages,
                **parameters,
            )

            extended_text = None
            print(f"Chat Completion response is: '{response}'")
            if response:
                choices = response.get("choices", [])
                if len(choices):
                    message = choices[0].get("message", {})
                    if message:
                        extended_text = message.get("content")
        else:
            completion = await openai.Completion.acreate(
                engine=model.provider_model_name,
                prompt=text,
                **parameters,
            )
            extended_text = completion.choices[0].text
        print(f'extended_text="{extended_text}"')
    else:
        raise ValueError(
            "Don't know how to do text->text inference for provider "
            f"{model_config.provider}."
        )

    return extended_text
