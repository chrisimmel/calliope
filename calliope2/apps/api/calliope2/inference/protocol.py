from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from calliope2.inference.types import ImageBlob, VideoBlob

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class InferenceClient(Protocol):
    """Provider-agnostic inference surface.

    Concrete clients implement the modalities they support; unsupported
    modalities should raise `UnsupportedOperation`. The `model` argument is
    a provider-specific identifier (e.g. ``"gpt-4o-mini"``,
    ``"black-forest-labs/flux-schnell"``); storytellers in YAML pin these.
    """

    provider: str

    async def text(
        self,
        prompt: str,
        *,
        model: str,
        schema: type[T] | None = None,
        system: str | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | T: ...

    async def embed(self, text: str, *, model: str) -> list[float]: ...

    async def image(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        size: str | None = None,
    ) -> ImageBlob: ...

    async def video(
        self,
        prompt: str,
        *,
        model: str,
        refs: Sequence[ImageBlob] = (),
        duration_seconds: float | None = None,
    ) -> VideoBlob: ...

    async def analyze_image(
        self,
        image: ImageBlob,
        prompt: str,
        *,
        model: str,
    ) -> str: ...
