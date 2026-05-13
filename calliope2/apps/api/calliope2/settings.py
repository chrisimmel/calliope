from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CALLIOPE2_",
        env_file=".env",
        extra="ignore",
    )

    env: str = Field(default="dev")
    database_url: str = Field(
        default="postgresql+asyncpg://calliope:calliope@localhost:5432/calliope2"
    )
    gcs_bucket: str = Field(default="")
    firebase_project_id: str = Field(default="")

    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_base_url: str | None = Field(default=None)
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_base_url: str = Field(default="https://api.anthropic.com/v1/")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""))
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1/")
    replicate_api_token: SecretStr = Field(default=SecretStr(""))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
