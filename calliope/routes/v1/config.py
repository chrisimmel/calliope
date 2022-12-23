from calliope.storage.config_manager import (
    get_flock_config,
    get_sparrow_config,
    put_config,
)
from fastapi import APIRouter, Depends
from fastapi.security.api_key import APIKey

from calliope.models import (
    BaseConfigModel,
    ConfigType,
    FlockConfigModel,
    SparrowConfigModel,
)
from calliope.utils.authentication import get_api_key


router = APIRouter(prefix="/v1", tags=["media"])


@router.get("/config/sparrow/{client_id}")
async def request_get_sparrow_config(
    client_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> SparrowConfigModel:
    return get_sparrow_config(client_id)


@router.get("/config/flock/{client_id}")
async def request_get_flock_config(
    client_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> SparrowConfigModel:
    return get_flock_config(ConfigType.FLOCK, client_id)


@router.put("/config/sparrow/{sparrow_id}")
async def put_sparrow_config(
    sparrow_id: str,
    sparrow_config: SparrowConfigModel,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    return await handle_put_config_request("sparrow", sparrow_id, sparrow_config)


@router.put("/config/flock/{flock_id}")
async def put_flock_config(
    flock_id: str,
    flock_config: FlockConfigModel,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    return await handle_put_config_request("flock", flock_id, flock_config)


async def handle_put_config_request(
    config_type: str, client_id: str, config: BaseConfigModel
) -> BaseConfigModel:
    return put_config(config)
