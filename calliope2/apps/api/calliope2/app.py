from contextlib import asynccontextmanager

from fastapi import FastAPI

from calliope2 import __version__
from calliope2.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Calliope v2",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/v3/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
