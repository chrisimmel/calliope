import httpx
from typing import Any, cast, Dict, Tuple

from openai import AsyncOpenAI

from calliope.models import (
    KeysModel,
    InferenceModelProviderVariant,
)
from calliope.tables import ModelConfig


async def openai_text_to_text_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
    """
    Performs a text->text inference using an OpenAI-provided LLM.

    Note that model.provider_api_variant determines whether the
    completion or chat completion API is used.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the generated text.
    """
    model = model_config.model

    parameters = {
        **(
            cast(Dict[str, Any], model.model_parameters)
            if model.model_parameters else {}
        ),
        **(
            cast(Dict[str, Any], model_config.model_parameters)
            if model_config.model_parameters else {}
        ),
    }

    client = AsyncOpenAI(
        api_key=keys.openai_api_key,
        http_client=httpx_client
    )

    if (
        model.provider_api_variant
        == InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION
    ):
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ],
            model=model.provider_model_name,
        )

        extended_text = (
            chat_completion.choices[0].message.content
            if (chat_completion.choices and chat_completion.choices[0].message)
            else None
        )
    else:
        extended_text = ""
        completion = await client.completions.create(
            prompt=text,
            model=model.provider_model_name,
            **parameters,
        )

        extended_text = completion.choices[0].text
        extended_text = (
            completion.choices[0].text
            if completion.choices
            else None
        )
        print(f"Completion response is: '{extended_text}'")

    return extended_text
