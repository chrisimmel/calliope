import json

import aiohttp
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.schema import HumanMessage
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
            chat = ChatOpenAI(
                openai_api_key=keys.openapi_api_key,
                model_name=model.provider_model_name,
                **parameters,
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
                openai_api_key=keys.openapi_api_key,
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

        print(f'extended_text="{extended_text}"')
    else:
        raise ValueError(
            "Don't know how to do text->text inference for provider "
            f"{model_config.provider}."
        )

    return extended_text
