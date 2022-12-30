from typing import Optional

from pydantic import BaseModel


class KeysModel(BaseModel):
    """
    API keys, etc.
    """

    stability_api_host: Optional[str]
    stability_api_key: Optional[str]
    huggingface_api_key: Optional[str]
