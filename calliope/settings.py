import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_VERSION: str = "0.0.1"
    CLOUD_ENV: str = "local"

    CALLIOPE_API_KEY: str = "xyzzy"
    CALLIOPE_BUCKET_NAME: str = "artifacts.ardent-course-370411.appspot.com"
    MEDIA_FOLDER: str = "media"

    POSTGRESQL_HOSTNAME: str = "postgres"
    POSTGRESQL_USERNAME: str = "postgres"
    POSTGRESQL_PASSWORD: str = "postgres"
    POSTGRESQL_DATABASE: str = "postgres"
    PORT: str = "1234"

    SEMANTIC_SEARCH_INDEX: str = "story-semantic-search"
    PINECONE_API_KEY: str
    OPENAI_API_KEY: str

    def update(self, name: str, value: str) -> None:
        """
        Updates settings and the system environment variable 'name' to 'value'.
        """
        setattr(self, name, value)
        os.environ[name] = value


settings = Settings()
