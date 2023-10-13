from typing import Optional

from pydantic import BaseModel


class KeysModel(BaseModel):
    """
    API keys, etc.
    """

    azure_api_key: Optional[str] = None
    azure_api_host: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    pinecone_api_key: Optional[str] = None
    replicate_api_key: Optional[str] = None
    stability_api_host: Optional[str] = None
    stability_api_key: Optional[str] = None
