"""Replicate inference client (image + video only)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import replicate
from replicate.helpers import FileOutput
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from calliope2.inference.errors import InferenceError, UnsupportedOperation
from calliope2.inference.types import ImageBlob, VideoBlob

if TYPE_CHECKING:
    from collections.abc import Sequence

_RETRYABLE = (replicate.exceptions.ReplicateError,)
_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
)


class ReplicateClient:
    provider: str = "replicate"

    def __init__(self, *, api_token: str, client: replicate.Client | None = None) -> None:
        self._client = client or replicate.Client(api_token=api_token)

    async def text(self, *args: Any, **kwargs: Any) -> str:
        raise UnsupportedOperation("replicate text models are not supported by this client")

    async def embed(self, *args: Any, **kwargs: Any) -> list[float]:
        raise UnsupportedOperation("replicate does not provide embeddings via this client")

    async def analyze_image(self, *args: Any, **kwargs: Any) -> str:
        raise UnsupportedOperation("use OpenAICompatibleClient for image analysis")

    async def transcribe(self, *args: Any, **kwargs: Any) -> str:
        raise UnsupportedOperation("use OpenAICompatibleClient for audio transcription")

    @_retry
    async def image(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        size: str | None = None,
    ) -> ImageBlob:
        inputs: dict[str, Any] = {"prompt": prompt}
        if size is not None:
            inputs["size"] = size
        if refs:
            inputs["image"] = _image_ref_input(refs[0])

        output = await self._client.async_run(model, input=inputs, use_file_output=True)
        return ImageBlob(**await _file_output_to_blob_kwargs(output, default_format="png"))

    @_retry
    async def video(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        duration_seconds: float | None = None,
    ) -> VideoBlob:
        inputs: dict[str, Any] = {"prompt": prompt}
        if duration_seconds is not None:
            inputs["duration"] = duration_seconds
        if refs:
            inputs["image"] = _image_ref_input(refs[0])

        output = await self._client.async_run(model, input=inputs, use_file_output=True)
        kwargs = await _file_output_to_blob_kwargs(output, default_format="mp4")
        return VideoBlob(**kwargs, duration_seconds=duration_seconds)


def _image_ref_input(ref: ImageBlob) -> str:
    """Turn a reference image into a Replicate ``image`` input. Replicate accepts
    both ``http(s)`` URLs and ``data:`` URIs, so a bytes-only blob (e.g. a
    captured photo ingested from a data URL) is encoded inline rather than
    requiring a hosted URL."""
    if ref.url is not None:
        return ref.url
    if ref.data is not None:
        mime = f"image/{ref.format or 'png'}"
        return f"data:{mime};base64,{base64.b64encode(ref.data).decode('ascii')}"
    raise InferenceError("replicate image ref has neither url nor data")


async def _file_output_to_blob_kwargs(output: Any, *, default_format: str) -> dict[str, Any]:
    """Normalize Replicate's variable output (FileOutput | list[FileOutput] | str) to blob kwargs."""
    if isinstance(output, list):
        if not output:
            raise InferenceError("replicate returned empty output list")
        output = output[0]
    if isinstance(output, FileOutput):
        return {"url": output.url, "format": default_format}
    if isinstance(output, str):
        return {"url": output, "format": default_format}
    raise InferenceError(f"replicate returned unrecognized output type: {type(output).__name__}")
