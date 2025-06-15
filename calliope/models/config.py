from typing import Optional

from pydantic import BaseModel, StrictStr


from calliope.models.keys import KeysModel
from calliope.models.parameters import ClientTypeParamsModel, StoryParamsModel
from calliope.models.schedule import ScheduleModel


class ConfigModel(BaseModel):
    """
    A generic base configuration.
    """

    # The ID of this configuration.
    id: StrictStr

    # Description of or commentary on this configuration.
    description: Optional[str] = None


class SparrowConfigModel(ConfigModel):
    """
    The configuration of a sparrow, flock of sparrows, or flock of flocks.
    """

    # The ID of the flock to which the sparrow or flock belongs, if any.
    # A sparrow or flock inherits the parameters and schedule of its parent
    # flock as defaults,
    parent_flock_id: Optional[StrictStr]

    # Whether to follow the parent flock's story state rather than
    # maintaining one's own. Default is False so each Sparrow normally has
    # its own independent story thread.
    # Note that this will be ignored if the child sparrow uses a different
    # strategy than the parent (since the two by definition can't share
    # the same story).
    follow_parent_story: bool = False

    # Optional strategy parameters.
    parameters: Optional[StoryParamsModel]

    # An optional schedule to follow.
    schedule: Optional[ScheduleModel]

    # An optional dictionary of things like API keys.
    keys: Optional[KeysModel]


class ClientTypeConfigModel(ConfigModel):
    """
    The definition of a client type.
    """

    # Optional client type parameters.
    parameters: Optional[ClientTypeParamsModel]


class StrategyConfigDescriptortModel(BaseModel):
    """
    A small amount of information about a strategy config.
    """

    # The unique slug for this strategy config.
    slug: str

    # Identifies the strategy.
    strategy_name: str

    # A human-readable description.
    description: str

    # Whether this strategy config is the default for the
    # requesting client.
    is_default_for_client: bool

    # Whether this strategy config is considered experimental.
    is_experimental: bool
