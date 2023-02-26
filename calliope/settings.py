from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_VERSION: str = "0.0.1"

    CALLIOPE_API_KEY: str = "xyzzy"
    CALLIOPE_BUCKET_NAME: str = "artifacts.ardent-course-370411.appspot.com"
    MEDIA_FOLDER: str = "media"

    POSTGRESQL_HOSTNAME: str = "postgres"
    POSTGRESQL_USERNAME: str = "postgres"
    POSTGRESQL_PASSWORD: str = "postgres"
    POSTGRESQL_DATABASE: str = "postgres"
    PORT: str = "1234"


settings = Settings()
