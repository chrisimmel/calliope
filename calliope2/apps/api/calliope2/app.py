from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from calliope2 import __version__
from calliope2.api.v3 import bookmarks, search, stories, storytellers
from calliope2.api.v3.admin import actions as admin_actions
from calliope2.api.v3.admin import resources as admin_resources
from calliope2.api.v3.admin import search as admin_search
from calliope2.api.v3.admin import stories as admin_stories
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

    # /v3/admin/* — admin-only; gated by is_admin in the dependency chain.
    app.include_router(admin_stories.router)
    app.include_router(admin_resources.router)
    app.include_router(admin_search.router)
    app.include_router(admin_actions.router)

    # SPAs — built by their respective `npm run build`. Mounted last so /v3/*
    # routers always take precedence. Tolerated-missing in tests that don't
    # build the frontends.
    clio_dir = STATIC_ROOT / "clio"
    if clio_dir.exists():
        app.mount("/clio", StaticFiles(directory=clio_dir, html=True), name="clio")

    admin_dir = STATIC_ROOT / "admin"
    if admin_dir.exists():
        app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")

    return app


app = create_app()
