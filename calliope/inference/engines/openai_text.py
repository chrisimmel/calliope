import aiohttp
from typing import Any, Dict, Optional, Tuple

from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.schema import HumanMessage
import openai

from calliope.models import (
    KeysModel,
    InferenceModelProviderVariant,
)
from calliope.tables import ModelConfig


def _filter_langchain_chat_parameters(
    parameters: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Separates model parameters into those that should be passed as first-class
    parameters to ChatOpenAI from those that should be passed in model_kwargs.

    Note that this filtering is appropriate only when using the Chat API, not
    the Completion API.
    """
    kw_params = ("presence_penalty", "frequency_penalty")
    langchain_parameters = {}
    langchain_model_kwargs = {}

    for key, value in parameters.items():
        if key in kw_params:
            langchain_model_kwargs[key] = value
        else:
            langchain_parameters[key] = value
    return langchain_parameters, langchain_model_kwargs


async def openai_text_to_text_inference(
    aiohttp_session: aiohttp.ClientSession,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
    model = model_config.model

    parameters = {
        **(model.model_parameters if model.model_parameters else {}),
        **(model_config.model_parameters if model_config.model_parameters else {}),
    }

    openai.api_key = keys.openai_api_key
    openai.aiosession.set(aiohttp_session)

    if (
        model.provider_api_variant
        == InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION
    ):
        """
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
        """

        extended_text = None
        parameters, model_kwargs = _filter_langchain_chat_parameters(parameters)

        chat = ChatOpenAI(
            openai_api_key=keys.openai_api_key,
            model_name=model.provider_model_name,
            **parameters,
            model_kwargs=model_kwargs,
        )
        llm_result = await chat.agenerate([[HumanMessage(content=text)]])
        print(f"Chat Completion response is: '{llm_result}'")
        if (
            llm_result.generations
            and llm_result.generations[0]
            and llm_result.generations[0][0]
        ):
            # generations=[[ChatGeneration(text='The room was bathed in soft, muted
            extended_text = llm_result.generations[0][0].text
    else:
        """
        completion = await openai.Completion.acreate(
            engine=model.provider_model_name,
            prompt=text,
            **parameters,
        )
        extended_text = completion.choices[0].text
        """

        extended_text = None
        chat = OpenAI(
            openai_api_key=keys.openai_api_key,
            model_name=model.provider_model_name,
            **parameters,
        )
        llm_result = await chat.agenerate([text])
        print(f"Completion response is: '{llm_result}'")
        if (
            llm_result.generations
            and llm_result.generations[0]
            and llm_result.generations[0][0]
        ):
            # generations=[[Generation(text="\nA portrait of a moment in time
            extended_text = llm_result.generations[0][0].text

    return extended_text
