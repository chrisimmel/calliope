from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from calliope2 import __version__
from calliope2.api.v3 import bookmarks, search, stories, storytellers
from calliope2.settings import get_settings

STATIC_ROOT = Path(__file__).parent / "static"


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

    app.include_router(stories.router)
    app.include_router(bookmarks.router)
    app.include_router(storytellers.router)
    app.include_router(search.router)

    # v3 Clio SPA — built by `npm run build` in apps/web/clio/. Mounted as the
    # last route so /v3/* takes precedence. The legacy /calliope/ app still
    # serves the v1/v2 Clio at /clio/ on its own service until Phase 9 cutover.
    clio_dir = STATIC_ROOT / "clio"
    if clio_dir.exists():
        app.mount("/clio", StaticFiles(directory=clio_dir, html=True), name="clio")

    return app


app = create_app()
