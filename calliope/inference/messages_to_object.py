from typing import Any, Iterable, TypeVar, Union

from calliope.inference.engines.openai_object import openai_messages_to_object_inference
import httpx
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from calliope.models import (
    InferenceModelProvider,
    KeysModel,
)
from calliope.tables import ModelConfig


T = TypeVar("T", bound=Union[BaseModel, "Iterable[Any]"])


async def messages_to_object_inference(
    httpx_client: httpx.AsyncClient,
    messages: list[ChatCompletionMessageParam],
    model_config: ModelConfig,
    keys: KeysModel,
    response_model: type[T],
) -> T:
    """
    Performs a text->text inference using an LLM.

    Args:
        httpx_client: the async HTTP session.
        text: the input text, to be sent as a prompt.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.

    Returns:
        the generated text.
    """
    print(f"text_to_text_inference: {model_config.slug}, {model_config.model}")
    model = model_config.model

    if model.provider == InferenceModelProvider.OPENAI:
        print(f"text_to_text_inference.openai {model.provider_model_name}")
        response = await openai_messages_to_object_inference(
            httpx_client, messages, model_config, keys, response_model
        )
        print(f'response="{response}"')
    else:
        raise ValueError(
            "Don't know how to do messages->object inference for provider "
            f"{model.provider}."
        )

    return response
