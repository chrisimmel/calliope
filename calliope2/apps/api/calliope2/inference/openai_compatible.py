"""OpenAI-compatible inference client.

One implementation that covers any provider speaking the OpenAI HTTP API:
OpenAI itself, Anthropic's OpenAI-compat endpoint, OpenRouter, local vLLM,
etc. Provider switching is by ``base_url`` + ``api_key`` at construction.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from calliope2.inference.errors import InferenceError, UnsupportedOperation
from calliope2.inference.types import ImageBlob, VideoBlob

if TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T", bound=BaseModel)

_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
)


class OpenAICompatibleClient:
    provider: str

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        provider: str = "openai",
        timeout: float = 60.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.provider = provider
        self._client = client or AsyncOpenAI(
            api_key=api_key or "missing-credentials",
            base_url=base_url,
            timeout=timeout,
        )

    @_retry
    async def text(
        self,
        prompt: str,
        *,
        model: str,
        schema: type[T] | None = None,
        system: str | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | T:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {"model": model, "messages": messages}
        if max_output_tokens is not None:
            kwargs["max_tokens"] = max_output_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature

        if schema is not None:
            response = await self._client.chat.completions.parse(
                **kwargs, response_format=schema
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise InferenceError("structured-output response did not parse")
            return parsed

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise InferenceError("text response had no content")
        return content

    @_retry
    async def embed(self, text: str, *, model: str) -> list[float]:
        response = await self._client.embeddings.create(model=model, input=text)
        return list(response.data[0].embedding)

    @_retry
    async def image(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        size: str | None = None,
    ) -> ImageBlob:
        if refs:
            raise UnsupportedOperation(
                f"{self.provider} image generation does not accept reference images"
            )
        kwargs: dict = {"model": model, "prompt": prompt, "response_format": "b64_json"}
        if size is not None:
            kwargs["size"] = size
        response = await self._client.images.generate(**kwargs)
        b64 = response.data[0].b64_json
        if b64 is None:
            raise InferenceError("image response had no b64_json")
        return ImageBlob(data=base64.b64decode(b64), format="png")

    async def video(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        duration_seconds: float | None = None,
    ) -> VideoBlob:
        raise UnsupportedOperation(f"{self.provider} does not support video generation")

    @_retry
    async def analyze_image(
        self,
        image: ImageBlob,
        prompt: str,
        *,
        model: str,
    ) -> str:
        image_url = image.url or _data_uri(image)
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise InferenceError("analyze_image response had no content")
        return content


def _data_uri(image: ImageBlob) -> str:
    if image.data is None:
        raise InferenceError("ImageBlob has no data and no url")
    mime = f"image/{image.format or 'png'}"
    return f"data:{mime};base64,{base64.b64encode(image.data).decode('ascii')}"
