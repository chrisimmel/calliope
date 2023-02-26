from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.routing import Mount
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from piccolo_admin.endpoints import create_admin
from piccolo.engine import engine_finder
from pydantic import BaseModel
from starlette.responses import JSONResponse

from calliope.models import StoryFrameModel
from calliope.routes import media as media_routes
from calliope.routes import meta as meta_routes
from calliope.routes import thoth as thoth_routes
from calliope.routes.v1 import config as config_routes
from calliope.routes.v1 import story as story_routes
from calliope.utils.authentication import get_api_key
from calliope.settings import settings

from calliope.tables import (
    ClientTypeConfig,
    Image,
    SparrowConfig,
    SparrowState,
    Story,
    StoryFrame,
)


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


def register_views(app: FastAPI):
    print(f"Oye! {settings.PORT}")
    app.include_router(meta_routes.router)
    app.include_router(story_routes.router)
    app.include_router(media_routes.router)
    app.include_router(config_routes.router)
    app.include_router(thoth_routes.router)


def get_db_uri(user, passwd, host, db):
    return f"postgres://{user}:{passwd}@{host}:5432/{db}"


PICCOLO_TABLES = [
    ClientTypeConfig,
    Image,
    SparrowConfig,
    SparrowState,
    Story,
    StoryFrame,
]


def create_app() -> FastAPI:
    print("Creating app...")
    app = FastAPI(
        title="Calliope",
        description="Let me tell you a story.",
        version=settings.APP_VERSION,
        routes=[
            Mount(
                path="/admin/",
                app=create_admin(
                    tables=PICCOLO_TABLES,
                    site_name="Calliope Admin",
                    # Required when running under HTTPS:
                    # allowed_hosts=["my_site.com"],
                ),
            ),
        ],
    )

    print("Registering views...")
    register_views(app)

    return app


app = create_app()
print("Created app.")


@app.on_event("startup")
async def open_database_connection_pool():
    engine = engine_finder()
    await engine.start_connection_pool()


@app.on_event("shutdown")
async def close_database_connection_pool():
    engine = engine_finder()
    await engine.close_connection_pool()


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)):
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version=1, routes=app.routes)
    )
    return response


# Mount the static HTML front ends.
app.mount("/clio/", StaticFiles(directory="static/clio", html=True), name="static")
app.mount("/thoth/", StaticFiles(directory="static/thoth", html=True), name="static")
