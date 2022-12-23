from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKey
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import JSONResponse

from calliope.models import StoryFrameModel
from calliope.routes import meta as meta_routes
from calliope.routes.v1 import config as config_routes
from calliope.routes.v1 import story as story_routes
from calliope.utils.authentication import get_api_key


class StoryResponseV1(BaseModel):
    # Some frames of the story to display, with optional start/stop times.
    frames: List[StoryFrameModel]

    request_id: str
    generation_date: str
    debug_data: Optional[Dict[str, Any]] = None
    errors: List[str]


app = FastAPI(
    title="Calliope",
    description="""Let me tell you a story.""",
    version="0.0.1",
)

app.include_router(meta_routes.router)
app.include_router(story_routes.router)
app.include_router(config_routes.router)


@app.get("/openapi.json", tags=["documentation"])
async def get_open_api_endpoint(api_key: APIKey = Depends(get_api_key)):
    response = JSONResponse(
        get_openapi(title="FastAPI security test", version=1, routes=app.routes)
    )
    return response


# Mount the static HTML front end.
app.mount("/clio/", StaticFiles(directory="static", html=True), name="static")
