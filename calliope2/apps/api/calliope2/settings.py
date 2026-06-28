from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the calliope2 workspace root ``.env`` based on the location of this
# file, so it's found no matter where the process was launched from. Layout:
#   calliope2/apps/api/calliope2/settings.py  ← __file__
#   calliope2/.env                            ← parents[3] / ".env"
#
# pydantic-settings loads ``env_file`` in order; later files override earlier
# ones — so a ``.env`` in the current working directory (e.g. when running
# ``calliope2-cli`` from elsewhere) takes precedence over the workspace root.
_WORKSPACE_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CALLIOPE2_",
        env_file=(str(_WORKSPACE_ROOT_ENV), ".env"),
        extra="ignore",
    )

    env: str = Field(default="dev")
    database_url: str = Field(
        default="postgresql+asyncpg://calliope:calliope@localhost:5432/calliope2"
    )
    gcs_bucket: str = Field(default="")
    firebase_project_id: str = Field(default="")
    # Named Firestore database the backend writes task status to. Must match
    # the database the web client listens on. Empty → the "(default)" database.
    firebase_database_id: str = Field(default="")

    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_base_url: str | None = Field(default=None)
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_base_url: str = Field(default="https://api.anthropic.com/v1/")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""))
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1/")
    replicate_api_token: SecretStr = Field(default=SecretStr(""))

    embedding_provider: str = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dim: int = Field(default=1536)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
