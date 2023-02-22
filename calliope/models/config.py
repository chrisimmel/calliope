from typing import Optional

from pydantic import BaseModel, StrictStr
from tortoise.models import Model
from tortoise import fields


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


class Config(Model):
    """
    Abstract base Tortoise model for a configuration.
    """

    id = fields.CharField(max_length=50, pk=True, generated=False)
    description = fields.CharField(max_length=1000, null=True)
    date_created = fields.DatetimeField(auto_now_add=True)
    date_updated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True


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


class SparrowConfig(Config):
    """
    The configuration of a sparrow, flock of sparrows, or flock of flocks.
    """

    # The ID of the flock to which the sparrow or flock belongs, if any.
    # A sparrow or flock inherits the parameters and schedule of its parent
    # flock as defaults,
    parent_flock_id: fields.ForeignKeyField(
        "models.SparrowConfig", related_name="child_sparrows"
    )

    # Whether to follow the parent flock's story state rather than
    # maintaining one's own. Default is False so each Sparrow normally has
    # its own independent story thread.
    # Note that this will be ignored if the child sparrow uses a different
    # strategy than the parent (since the two by definition can't share
    # the same story).
    follow_parent_story = fields.BooleanField()

    # Optional strategy parameters.
    parameters = fields.JSONField(null=True)

    # An optional schedule to follow.
    schedule = fields.JSONField(null=True)

    # An optional dictionary of things like API keys.
    keys = fields.JSONField(null=True)

    class Meta:
        table = "sparrow_config"

    @classmethod
    async def from_pydantic(cls, model: SparrowConfigModel) -> "SparrowConfig":
        id = model.id
        description = model.description
        parent_flock_id = model.parent_flock_id
        follow_parent_story = model.follow_parent_story
        parameters = (
            model.parameters.dict(exclude_none=True) if model.parameters else None
        )
        schedule = model.schedule.dict(exclude_none=True) if model.schedule else None
        keys = model.keys.dict(exclude_none=True) if model.keys else None

        instance: SparrowConfig = await SparrowConfig.get_or_none(id=id)
        if instance:
            instance.description = description
            instance.parent_flock_id = parent_flock_id
            instance.follow_parent_story = follow_parent_story
            instance.parameters = parameters
            instance.schedule = schedule
            instance.keys = keys
        else:
            instance = SparrowConfig(
                id=id,
                description=description,
                parent_flock_id=parent_flock_id,
                follow_parent_story=follow_parent_story,
                parameters=parameters,
                schedule=schedule,
                keys=keys,
            )

        return instance


class ClientTypeConfigModel(ConfigModel):
    """
    The definition of a client type.
    """

    # Optional client type parameters.
    parameters: Optional[ClientTypeParamsModel]


class ClientTypeConfig(Config):
    """
    The definition of a client type.
    """

    # Optional strategy parameters.
    parameters = fields.JSONField(null=True)

    class Meta:
        table = "client_type_config"

    @classmethod
    async def from_pydantic(cls, model: ClientTypeConfigModel) -> "ClientTypeConfig":
        id = model.id
        description = model.description
        parameters = (
            model.parameters.dict(exclude_none=True) if model.parameters else None
        )

        instance: ClientTypeConfig = await ClientTypeConfig.get_or_none(id=id)
        if instance:
            instance.description = description
            instance.parameters = parameters
        else:
            instance = ClientTypeConfig(
                id=id,
                description=description,
                parameters=parameters,
            )

        return instance
