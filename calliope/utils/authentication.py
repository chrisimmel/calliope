from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyCookie, APIKeyQuery, APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from calliope.settings import settings

api_key_query = APIKeyQuery(name="api_key", auto_error=False)
api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)
api_key_cookie = APIKeyCookie(name="api_key", auto_error=False)


async def get_api_key(
    api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
    api_key_cookie: str = Security(api_key_cookie),
) -> str:
    if api_key_query == settings.CALLIOPE_API_KEY:
        return api_key_query
    elif api_key_header == settings.CALLIOPE_API_KEY:
        return api_key_header
    elif api_key_cookie == settings.CALLIOPE_API_KEY:
        return api_key_cookie
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
