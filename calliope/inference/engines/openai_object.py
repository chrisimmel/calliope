from typing import Any, cast, Dict, Iterable, TypeVar, Union

import httpx
from instructor import from_openai, Mode
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from calliope.models import (
    KeysModel,
)
from calliope.tables import ModelConfig


T = TypeVar("T", bound=Union[BaseModel, "Iterable[Any]"])


async def openai_messages_to_object_inference(
    httpx_client: httpx.AsyncClient,
    messages: list[ChatCompletionMessageParam],
    model_config: ModelConfig,
    keys: KeysModel,
    response_model: type[T],
) -> T:
    """
    Performs a messages->object inference using an OpenAI-provided LLM.

    Note that model.provider_api_variant determines whether the
    completion or chat completion API is used.

    Args:
        httpx_client: the async HTTP session.
        messages: the input messages.
        model_config: the ModelConfig with model and parameters.
        keys: API keys, etc.
        response_model: the response model to use.

    Returns:
        the generated object (an instance of response_model).
    """
    model = model_config.model

    parameters = {
        **(
            cast(Dict[str, Any], model.model_parameters)
            if model.model_parameters
            else {}
        ),
        **(
            cast(Dict[str, Any], model_config.model_parameters)
            if model_config.model_parameters
            else {}
        ),
    }

    openai_client = AsyncOpenAI(api_key=keys.openai_api_key, http_client=httpx_client)
    client = from_openai(openai_client)  # , mode=Mode.TOOLS_STRICT)

    response = await client.chat.completions.create(
        response_model=response_model,
        messages=messages,
        model=model.provider_model_name,
        **parameters,
    )

    return response
