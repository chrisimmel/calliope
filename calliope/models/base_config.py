from enum import Enum
from typing import Optional

from pydantic import BaseModel

from calliope.models.parameters import StoryParamsModel
from calliope.models.schedule import ScheduleModel


class ConfigType(Enum):
    SPARROW = "sparrow"
    FLOCK = "flock"


class BaseConfigModel(BaseModel):
    """
    The configuration of a flock or sparrow.
    """

    # The type of config. Must be set for each subclass.
    _config_type: ConfigType

    # Optional strategy parameters.
    parameters: Optional[StoryParamsModel]

    # An optional schedule to follow.
    schedule: Optional[ScheduleModel]
