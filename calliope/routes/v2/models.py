from typing import List, Dict, Any, Literal, Optional

from pydantic import BaseModel, root_validator


SnippetType = Literal["image", "audio", "text", "video"]


class Snippet(BaseModel):
    """Represents a single data snippet (image, audio, text, etc.)"""

    snippet_type: SnippetType  # e.g., "image", "audio", "text"
    content: str  # Base64 encoded data, text string, etc.
    metadata: Dict[str, Any] = {}  # Optional metadata


class AddFrameRequest(BaseModel):
    """Request body for requesting a new frame be added to an existing story, with optional input snippets."""

    snippets: List[Snippet]
    extra_fields: Optional[Dict[str, Any]] = None

    @root_validator(pre=True)
    def build_extra_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collects any fields that aren't explicitly modeled into extra_fields.
        """
        modeled_field_names = set(cls.model_fields.keys())

        extra_fields: Dict[str, Any] = {}
        for field_name in list(values):
            if field_name not in modeled_field_names:
                extra_fields[field_name] = values.pop(field_name)
        values["extra_fields"] = extra_fields
        return values


class CreateStoryRequest(AddFrameRequest):
    """Request body for creating a new story."""

    title: Optional[str] = None  # Example initial parameter
    strategy: Optional[str] = None  # Example initial parameter
