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

    # Hosts permitted to submit forms (including the login form) to the Piccolo
    # Admin, as a comma-separated list. Piccolo's CSRF middleware rejects any
    # request whose Origin/Referer host is absent from this list, but only when
    # the request is served over HTTPS. See create_admin() in calliope/app.py.
    ADMIN_ALLOWED_HOSTS: str = (
        "calliope.chrisimmel.com,"
        "calliope-59295831264.us-central1.run.app,"
        "calliope-59295831264.us-east4.run.app,"
        # Local development. The CSRF referer check is skipped over plain HTTP,
        # so these matter only when local traffic is served over TLS (e.g. behind
        # an ngrok tunnel or a local HTTPS proxy).
        "localhost,"
        "127.0.0.1"
    )

    @property
    def admin_allowed_hosts(self) -> list[str]:
        """
        ADMIN_ALLOWED_HOSTS parsed into a list of hostnames.
        """
        return [
            host.strip() for host in self.ADMIN_ALLOWED_HOSTS.split(",") if host.strip()
        ]

    def update(self, name: str, value: str) -> None:
        """
        Updates settings and the system environment variable 'name' to 'value'.
        """
        setattr(self, name, value)
        os.environ[name] = value


settings = Settings()
