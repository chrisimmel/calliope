from typing import Optional

from pydantic import BaseModel, StrictStr

from calliope.models.keys import KeysModel
from calliope.models.parameters import StoryParamsModel
from calliope.models.schedule import ScheduleModel


class SparrowConfigModel(BaseModel):
    """
    The configuration of a sparrow, flock of sparrows, or flock of flocks.
    """

    # The ID of this sparrow or flock.
    id: StrictStr

    # The ID of the flock to which the sparrow or flock belongs, if any.
    # A sparrow or flock inherits the parameters and schedule of its parent
    # flock as defaults,
    parent_flock_id: Optional[StrictStr]

    # Optional strategy parameters.
    parameters: Optional[StoryParamsModel]

    # An optional schedule to follow.
    schedule: Optional[ScheduleModel]

    # An optional dictionary of things like API keys.
    keys: Optional[KeysModel]
