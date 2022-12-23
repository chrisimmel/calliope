from pydantic import StrictStr

from calliope.models.base_config import BaseConfigModel, ConfigType


class SparrowConfigModel(BaseConfigModel):
    """
    The configuration of a given sparrow.
    """

    _config_type: ConfigType = ConfigType.SPARROW

    # The sparrow's ID.
    sparrow_id: StrictStr

    # The ID of the flock to which the sparrow belongs.
    flock_id: StrictStr
