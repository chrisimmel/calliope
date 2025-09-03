import os
from typing import Optional

from pydantic import BaseModel


class KeysModel(BaseModel):
    """
    API keys, etc.
    """

    azure_api_key: Optional[str] = None
    azure_api_host: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    pinecone_api_key: Optional[str] = None
    replicate_api_key: Optional[str] = None
    runway_api_key: Optional[str] = None
    stability_api_host: Optional[str] = None
    stability_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "KeysModel":
        """Get API keys from environment variables."""
        return cls(
            azure_api_key=os.getenv("AZURE_API_KEY"),
            azure_api_host=os.getenv("AZURE_API_HOST"),
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            replicate_api_key=os.getenv("REPLICATE_API_KEY"),
            runway_api_key=os.getenv("RUNWAY_API_KEY"),
            stability_api_host=os.getenv("STABILITY_API_HOST"),
            stability_api_key=os.getenv("STABILITY_API_KEY"),
        )
