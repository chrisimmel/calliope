from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Snippet(BaseModel):
    """Represents a single data snippet (image, audio, text, etc.)"""
    data_type: str  # e.g., "image", "audio", "text"
    content: str    # Base64 encoded data, text string, etc.
    metadata: Dict[str, Any] = {} # Optional metadata


class CreateStoryRequest(BaseModel):
    """Request body for creating a new story."""
    title: Optional[str] = None  # Example initial parameter
    strategy: Optional[str] = None # Example initial parameter
    snippets: List[Snippet] = [] # Optional list of initial snippets


class AddSnippetsRequest(BaseModel):
    """Request body for adding snippets to an existing story."""
    snippets: List[Snippet]
