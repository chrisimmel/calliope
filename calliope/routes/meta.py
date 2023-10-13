from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)

from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import FileResponse, RedirectResponse

from calliope.utils.authentication import get_api_key
from calliope.utils.fastapi import get_base_url


router = APIRouter()


@router.get("/robots.txt")
async def empty_response() -> str:
    return ""


@router.get("/favicon.ico")
@router.get("/apple-touch-icon.png")
@router.get("/apple-touch-icon-precomposed.png")
async def get_favicon() -> FileResponse:
    return FileResponse("static/Calliope-icon-32x32.png", media_type="image/png")


@router.get("/docs", tags=["documentation"])
async def get_documentation(
    request: Request,
    api_key: str = Depends(get_api_key),
) -> Response:
    domain = get_base_url(request)

    response = get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
    response.set_cookie(
        "api_key",
        value=str(api_key),
        domain=domain,
        httponly=True,
        max_age=1800,
        expires=1800,
    )
    return response


@router.get("/logout", tags=["authentication"])
async def route_logout_and_remove_cookie(
    request: Request,
) -> Response:
    domain = get_base_url(request)
    response = RedirectResponse(url="/")
    response.delete_cookie("api_key", domain=domain)
    return response
