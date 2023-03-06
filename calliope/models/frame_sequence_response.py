from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# from pydantic import BaseModel

from calliope.tables.story import StoryFrame


@dataclass
class StoryFrameSequenceResponseModel:
    """
    A sequence of story frames.
    """

    # A list of story frames.
    frames: List[StoryFrame]

    # Whether these frames should be appended to those delivered
    # previously.
    append_to_prior_frames: bool = False

    # Optional debug data.
    debug_data: Optional[Dict[str, Any]] = None

    # A list of non-fatal error messages.
    errors: List[str] = field(default_factory=list)
