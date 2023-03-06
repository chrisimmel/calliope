from calliope.storage.config_manager import (
    delete_client_type_config,
    delete_sparrow_config,
    get_client_type_config,
    put_client_type_config,
    get_sparrow_config,
    put_sparrow_config,
)
from fastapi import APIRouter, Depends
from fastapi.security.api_key import APIKey

from calliope.models import (
    ClientTypeConfigModel,
    SparrowConfigModel,
)
from calliope.utils.authentication import get_api_key


router = APIRouter(prefix="/v1/config", tags=["configuration"])


@router.get("/sparrow/{sparrow_or_flock_id}")
async def request_get_sparrow_config(
    sparrow_or_flock_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> SparrowConfigModel:
    return await get_sparrow_config(sparrow_or_flock_id)


@router.put("/sparrow/{sparrow_or_flock_id}")
async def request_put_sparrow_config(
    sparrow_or_flock_id: str,
    config: SparrowConfigModel,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    config.id = sparrow_or_flock_id
    return await put_sparrow_config(config)


@router.delete("/sparrow/{sparrow_or_flock_id}")
async def request_delete_sparrow_config(
    sparrow_or_flock_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    return await delete_sparrow_config(sparrow_or_flock_id)


@router.get("/client_type/{client_type}")
async def request_get_client_type_config(
    client_type: str,
    api_key: APIKey = Depends(get_api_key),
) -> ClientTypeConfigModel:
    return await get_client_type_config(client_type)


@router.put("/client_type/{client_type}")
async def request_put_client_type_config(
    client_type: str,
    config: ClientTypeConfigModel,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    config.id = client_type
    return await put_client_type_config(config)


@router.delete("/client_type/{client_type}")
async def request_delete_client_type_config(
    client_type: str,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    return await delete_client_type_config(client_type)
