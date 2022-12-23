from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Request,
)

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security.api_key import APIKey
from starlette.responses import FileResponse, JSONResponse, RedirectResponse

from calliope.routes.v1.media import handle_media_request
from calliope.utils.authentication import get_api_key
from calliope.utils.fastapi import get_domain


router = APIRouter()


@router.get("/robots.txt")
async def empty_response() -> str:
    return ""


@router.get("/media/{filename}")
async def get_media(
    filename: str,
    # api_key: APIKey = Depends(get_api_key),
) -> Optional[FileResponse]:
    return await handle_media_request(filename)


@router.get("/favicon.ico")
@router.get("/apple-touch-icon.png")
@router.get("/apple-touch-icon-precomposed.png")
async def get_favicon() -> FileResponse:
    return FileResponse("static/icons8-lyre-32.png", media_type="image/png")


@router.get("/docs", tags=["documentation"])
async def get_documentation(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
):
    domain = get_domain(request)

    response = get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    response.set_cookie(
        "api_key",
        value=api_key,
        domain=domain,
        httponly=True,
        max_age=1800,
        expires=1800,
    )
    return response


@router.get("/logout", tags=["authentication"])
async def route_logout_and_remove_cookie(
    request: Request,
):
    domain = get_domain(request)
    response = RedirectResponse(url="/")
    response.delete_cookie("api_key", domain=domain)
    return response
