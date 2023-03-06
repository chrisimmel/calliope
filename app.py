from typing import Sequence, Union

from fastapi import Depends, FastAPI
from fastapi.routing import Mount
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from piccolo_admin.endpoints import create_admin, FormConfig, TableConfig
from piccolo_api.media.local import LocalMediaStorage
from piccolo.engine import engine_finder
from piccolo.table import Table
from starlette.responses import JSONResponse


from calliope.forms.migrate_pydantic_to_piccolo import (
    MigrateFromPydanticFormModel,
    migrate_from_pydantic_endpoint,
)
from calliope.forms.run_command import RunCommandFormModel, run_command_endpoint
from calliope.routes import media as media_routes
from calliope.routes import meta as meta_routes
from calliope.routes import thoth as thoth_routes
from calliope.routes.v1 import config as config_routes
from calliope.routes.v1 import story as story_routes
from calliope.utils.authentication import get_api_key
from calliope.utils.google import is_google_cloud_run_environment
from calliope.settings import settings

from calliope.tables import (
    ClientTypeConfig,
    Image,
    SparrowConfig,
    SparrowState,
    Story,
    StoryFrame,
)


def register_views(app: FastAPI):
    print(f"Registering views for port {settings.PORT}")
    app.include_router(meta_routes.router)
    app.include_router(story_routes.router)
    app.include_router(media_routes.router)
    app.include_router(config_routes.router)
    app.include_router(thoth_routes.router)


def get_db_uri(user, passwd, host, db):
    return f"postgres://{user}:{passwd}@{host}:5432/{db}"


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


PICCOLO_TABLES = [
    ClientTypeConfig,
    Image,
    SparrowConfig,
    SparrowState,
    Story,
    StoryFrame,
]


def config_piccolo_tables() -> Sequence[Union[Table, TableConfig]]:
    if is_google_cloud_run_environment:
        # TODO: GCP custom MediaStorage for images.
        return PICCOLO_TABLES
    else:
        return [
            ClientTypeConfig,
            image_local_config,
            SparrowConfig,
            SparrowState,
            Story,
            StoryFrame,
        ]


def create_app() -> FastAPI:
    print("Creating app...")
    admin_route = None
    try:
        admin_route = Mount(
            path="/admin/",
            app=create_admin(
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
                ],
            ),
        )
    except Exception as e:
        print(f"Error creating admin route: {e}")

    routes = [admin_route] if admin_route else []

    app = FastAPI(
        title="Calliope",
        description="Let me tell you a story.",
        version=settings.APP_VERSION,
        routes=routes,
    )

    print("Registering views...")
    register_views(app)

    return app


app = create_app()
print("Created app.")


@app.on_event("startup")
async def open_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.start_connection_pool()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@app.on_event("shutdown")
async def close_database_connection_pool():
    try:
        engine = engine_finder()
        await engine.close_connection_pool()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)):
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version=1, routes=app.routes)
    )
    return response


# Mount the static HTML front ends.
app.mount("/clio/", StaticFiles(directory="static/clio", html=True), name="static")
app.mount("/thoth/", StaticFiles(directory="static/thoth", html=True), name="static")
