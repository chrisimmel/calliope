from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from calliope2 import __version__
from calliope2.api.v3 import bookmarks, illustrators, search, stories, storytellers
from calliope2.api.v3.admin import actions as admin_actions
from calliope2.api.v3.admin import resources as admin_resources
from calliope2.api.v3.admin import search as admin_search
from calliope2.api.v3.admin import stories as admin_stories
from calliope2.settings import get_settings

STATIC_ROOT = Path(__file__).parent / "static"


class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` for unmatched paths, so a
    client-side deep link (e.g. ``/clio/story/<slug>/3``) refreshed in the
    browser serves the SPA shell instead of 404ing. Real asset 404s also fall
    back to the shell — standard SPA behavior."""

    async def get_response(self, path: str, scope: Any):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


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
    app.include_router(illustrators.router)
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
        app.mount("/clio", SPAStaticFiles(directory=clio_dir, html=True), name="clio")

    admin_dir = STATIC_ROOT / "admin"
    if admin_dir.exists():
        app.mount("/admin", SPAStaticFiles(directory=admin_dir, html=True), name="admin")

    return app


app = create_app()
