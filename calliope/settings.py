from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_VERSION: str = "0.0.1"

    CALLIOPE_API_KEY: str = "xyzzy"
    CALLIOPE_BUCKET_NAME: str = "artifacts.ardent-course-370411.appspot.com"
    MEDIA_FOLDER: str = "media"

    POSTGRESQL_HOSTNAME: str = "localhost"
    POSTGRESQL_USERNAME: str = "guest"
    POSTGRESQL_PASSWORD: str = "guest"
    POSTGRESQL_DATABASE: str = "notesdb"
    PORT: str = "1234"


settings = Settings()
