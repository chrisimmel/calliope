"""Provider-agnostic inference layer.

Exposes a single Protocol (`InferenceClient`) covering text, image, video,
embed, and analyze_image, with two concrete implementations
(`OpenAICompatibleClient`, `ReplicateClient`) selectable by string key.
"""

from calliope2.inference.errors import InferenceError, UnsupportedOperation
from calliope2.inference.openai_compatible import OpenAICompatibleClient
from calliope2.inference.protocol import InferenceClient
from calliope2.inference.registry import get_client
from calliope2.inference.replicate_client import ReplicateClient
from calliope2.inference.types import AudioBlob, ImageBlob, VideoBlob

__all__ = [
    "AudioBlob",
    "ImageBlob",
    "InferenceClient",
    "InferenceError",
    "OpenAICompatibleClient",
    "ReplicateClient",
    "UnsupportedOperation",
    "VideoBlob",
    "get_client",
]
