from typing import Sequence, Union

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from piccolo_admin.endpoints import create_admin, FormConfig, TableConfig
from piccolo_api.media.local import LocalMediaStorage
from piccolo.engine import engine_finder
from piccolo.table import Table
from starlette.responses import JSONResponse


from calliope.forms.add_story_thumbnails import (
    AddStoryThumbnailsFormModel,
    add_story_thumbnails_endpoint,
)
from calliope.forms.run_command import RunCommandFormModel, run_command_endpoint
from calliope.routes import media as media_routes
from calliope.routes import meta as meta_routes
from calliope.routes import thoth as thoth_routes
from calliope.routes.v1 import story as story_routes
from calliope.routes.v1 import config as config_routes
from calliope.routes.v1 import test as test_routes
from calliope.routes.v1 import bookmark as bookmark_routes
from calliope.utils.authentication import get_api_key
from calliope.utils.google import is_google_cloud_run_environment
from calliope.settings import settings

from calliope.tables import (
    BookmarkList,
    ClientTypeConfig,
    Image,
    InferenceModel,
    ModelConfig,
    PromptTemplate,
    SparrowConfig,
    SparrowState,
    Story,
    StoryBookmark,
    StoryFrame,
    StoryFrameBookmark,
    StrategyConfig,
    Video,
)


def register_views(app: FastAPI) -> None:
    print(f"Registering views for port {settings.PORT}")
    app.include_router(meta_routes.router)
    app.include_router(story_routes.router)
    app.include_router(config_routes.router)
    app.include_router(media_routes.router)
    app.include_router(thoth_routes.router)
    app.include_router(test_routes.router)
    app.include_router(bookmark_routes.router)


def get_db_uri(user: str, passwd: str, host: str, db: str) -> str:
    return f"postgres://{user}:{passwd}@{host}:5432/{db}"


PICCOLO_TABLES = [
    BookmarkList,
    ClientTypeConfig,
    Image,
    InferenceModel,
    ModelConfig,
    PromptTemplate,
    SparrowConfig,
    SparrowState,
    Story,
    StoryBookmark,
    StoryFrame,
    StoryFrameBookmark,
    StrategyConfig,
    Video,
]


# Use a custom TableConfig and LocalMediaStorage for local images...

MEDIA_ROOT = "./"

IMAGE_MEDIA = LocalMediaStorage(
    column=Image.url,
    media_path=MEDIA_ROOT,
    allowed_extensions=["jpg", "jpeg", "png", "raw"],
)

image_local_config = TableConfig(
    table_class=Image,
    media_storage=[IMAGE_MEDIA],
)

prompt_template_config = TableConfig(
    table_class=PromptTemplate, link_column=PromptTemplate.slug
)
inference_model_config = TableConfig(
    table_class=InferenceModel, link_column=InferenceModel.slug
)
model_config_config = TableConfig(table_class=ModelConfig, link_column=ModelConfig.slug)
strategy_config_config = TableConfig(
    table_class=StrategyConfig, link_column=StrategyConfig.slug
)


def maybe_create_table_config(table: type[Table]) -> Union[type[Table], TableConfig]:
    return (
        image_local_config
        # TODO: GCP custom MediaStorage for images.
        if table == Image and not is_google_cloud_run_environment()
        # else prompt_template_config
        # if table == PromptTemplate
        # else inference_model_config
        # if table == InferenceModel
        # else model_config_config
        # if table == ModelConfig
        # else strategy_config_config
        # if table == StrategyConfig
        else table
    )


def config_piccolo_tables() -> Sequence[Union[type[Table], TableConfig]]:
    return [maybe_create_table_config(table) for table in PICCOLO_TABLES]


def create_app() -> FastAPI:
    print("Creating app...")

    app = FastAPI(
        title="Calliope",
        description="Let me tell you a story.",
        version=settings.APP_VERSION,
    )

    try:
        # Create and mount Piccolo Admin sub-app...
        admin_app = create_admin(
            tables=config_piccolo_tables(),
            site_name="Calliope Admin",
            # Required when running under HTTPS:
            # allowed_hosts=["my_site.com"],
            forms=[
                # FormConfig(
                #     name="Migrate from Pydantic to Piccolo",
                #     pydantic_model=MigrateFromPydanticFormModel,
                #     endpoint=migrate_from_pydantic_endpoint,
                # ),
                FormConfig(
                    name="Run Command",
                    pydantic_model=RunCommandFormModel,
                    endpoint=run_command_endpoint,
                ),
                FormConfig(
                    name="Add Story Thumbnails",
                    pydantic_model=AddStoryThumbnailsFormModel,
                    endpoint=add_story_thumbnails_endpoint,
                ),
            ],
        )
        app.mount("/admin", admin_app)
    except Exception as e:
        print(f"Error creating admin route: {e}")

    print("Registering views...")
    register_views(app)

    return app


app = create_app()
print("Created app.")


@app.on_event("startup")
async def open_database_connection_pool() -> None:
    try:
        engine = engine_finder()
        if engine:
            await engine.start_connection_pool()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@app.on_event("shutdown")
async def close_database_connection_pool() -> None:
    try:
        engine = engine_finder()
        if engine:
            await engine.close_connection_pool()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)) -> JSONResponse:
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version="1", routes=app.routes)
    )
    return response


# Mount the static HTML front ends.
# Add routes to support client-side routing in Clio
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
import os

# Revert to a simpler and more direct approach
from starlette.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Mount Thoth static files
app.mount("/thoth/", StaticFiles(directory="static/thoth", html=True), name="thoth_static")

# Root redirect
@app.get("/clio", include_in_schema=False)
async def clio_root_redirect():
    return RedirectResponse("/clio/")

# Root Clio route
@app.get("/clio/", include_in_schema=False)
async def serve_clio_root():
    return FileResponse("static/clio/index.html")

# Define Clio routes more explicitly
@app.get("/clio/main.js", include_in_schema=False)
async def serve_js_file():
    # Find the main.js file with any query parameters
    import glob
    js_files = glob.glob("static/clio/main.js*")
    if js_files:
        return FileResponse(js_files[0])
    return FileResponse("static/clio/main.js")

# All other Clio routes (for client-side routing)
@app.get("/clio/{path:path}", include_in_schema=False)
async def serve_clio(path: str = ""):
    # First, try to serve static files
    static_path = f"static/clio/{path}"
    if os.path.isfile(static_path):
        return FileResponse(static_path)

    # For all other routes, serve index.html for client-side routing
    return FileResponse("static/clio/index.html")
