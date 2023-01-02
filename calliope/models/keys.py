from typing import Optional

from pydantic import BaseModel


class KeysModel(BaseModel):
    """
    API keys, etc.
    """

    huggingface_api_key: Optional[str]
    openapi_api_key: Optional[str]
    stability_api_host: Optional[str]
    stability_api_key: Optional[str]
