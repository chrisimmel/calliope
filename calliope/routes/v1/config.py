from calliope.storage.config_manager import (
    get_sparrow_config,
    put_sparrow_config,
)
from fastapi import APIRouter, Depends
from fastapi.security.api_key import APIKey

from calliope.models import (
    SparrowConfigModel,
)
from calliope.utils.authentication import get_api_key


router = APIRouter(prefix="/v1", tags=["config"])


@router.get("/config/sparrow/{sparrow_or_flock_id}")
async def request_get_sparrow_config(
    sparrow_or_flock_id: str,
    api_key: APIKey = Depends(get_api_key),
) -> SparrowConfigModel:
    return get_sparrow_config(sparrow_or_flock_id)


@router.put("/config/sparrow/{sparrow_or_flock_id}")
async def request_put_sparrow_config(
    sparrow_or_flock_id: str,
    sparrow_config: SparrowConfigModel,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    sparrow_config.id = sparrow_or_flock_id
    return put_sparrow_config(sparrow_config)
