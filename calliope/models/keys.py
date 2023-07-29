from typing import Optional

from pydantic import BaseModel


class KeysModel(BaseModel):
    """
    API keys, etc.
    """

    azure_api_key: Optional[str]
    azure_api_host: Optional[str]
    huggingface_api_key: Optional[str]
    openai_api_key: Optional[str]
    pinecone_api_key: Optional[str]
    replicate_api_key: Optional[str]
    stability_api_host: Optional[str]
    stability_api_key: Optional[str]
