from typing import Optional

from pydantic import StrictStr

from calliope.models.base_config import BaseConfigModel, ConfigType


class FlockConfigModel(BaseConfigModel):
    """
    The configuration of a flock of sparrows.
    """

    _config_type: ConfigType = ConfigType.FLOCK

    # The ID of this flock.
    flock_id: StrictStr
