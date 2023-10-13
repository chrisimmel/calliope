from typing import Optional, Sequence

from calliope.storage.config_manager import get_strategy_config_descriptors
from fastapi import APIRouter, Depends
from fastapi.security.api_key import APIKey

from calliope.models import StrategyConfigDescriptortModel
from calliope.utils.authentication import get_api_key


router = APIRouter(prefix="/v1/config", tags=["configuration"])


@router.get("/strategy/")
async def request_get_strategy_configs(
    client_id: Optional[str],
    api_key: APIKey = Depends(get_api_key),
) -> Sequence[StrategyConfigDescriptortModel]:
    return await get_strategy_config_descriptors(client_id)
