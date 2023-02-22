from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import JSONResponse

from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from calliope.models import StoryFrameModel
from calliope.routes import media as media_routes
from calliope.routes import meta as meta_routes
from calliope.routes import thoth as thoth_routes
from calliope.routes.v1 import config as config_routes
from calliope.routes.v1 import story as story_routes
from calliope.utils.authentication import get_api_key
from calliope.settings import settings


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


TORTOISE_MODELS = [
    "calliope.models.config",
    "calliope.models.image",
    "calliope.models.story_frame",
    "calliope.models.story",
]

Tortoise.init_models(TORTOISE_MODELS, "models")


# def create_app() -> FastAPI:
print("Creating app...")
app = FastAPI(
    title="Calliope",
    description="Let me tell you a story.",
    version=settings.APP_VERSION,
)

print("Registering Tortoise...")
register_tortoise(
    app,
    db_url=get_db_uri(
        user=settings.POSTGRESQL_USERNAME,
        passwd=settings.POSTGRESQL_PASSWORD,
        host=settings.POSTGRESQL_HOSTNAME,
        db=settings.POSTGRESQL_DATABASE,
    ),
    modules={"models": TORTOISE_MODELS},
    # generate_schemas=True,
    # add_exception_handlers=True,
)
print("Registering views...")
register_views(app)

#    return app

# print("Creating app.")
# app = create_app()
# print("Created app.")


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)):
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version=1, routes=app.routes)
    )
    return response


# Mount the static HTML front ends.
app.mount("/clio/", StaticFiles(directory="static/clio", html=True), name="static")
app.mount("/thoth/", StaticFiles(directory="static/thoth", html=True), name="static")
