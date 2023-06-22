from datetime import datetime, timezone
from typing import Optional
from calliope.utils.file import FileMetadata

from piccolo.table import Table
from piccolo.columns import (
    Boolean,
    JSONB,
    Text,
    Timestamptz,
    Varchar,
)


from calliope.models import ClientTypeConfigModel, SparrowConfigModel


class SparrowConfig(Table):
    """
    The configuration of a sparrow, flock of sparrows, or flock of flocks.
    """

    # The sparrow or flock ID. For a sparrow, the client ID or client type.
    # For a flock, a human-readable slug.
    client_id = Varchar(length=50, unique=True, index=True)

    # Notes about the sparrow, flock, or client type.
    description = Text(null=True, required=False)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    # The client_id of the flock to which the sparrow or flock belongs, if any.
    # A sparrow or flock inherits the parameters and schedule of its parent
    # flock as defaults,
    parent_flock_client_id = Varchar(length=50, null=True)

    # Whether to follow the parent flock's story state rather than
    # maintaining one's own. Default is False so each Sparrow normally has
    # its own independent story thread.
    # Note that this will be ignored if the child sparrow uses a different
    # strategy than the parent (since the two by definition can't share
    # the same story).
    follow_parent_story = Boolean()

    # Optional strategy parameters.
    parameters = JSONB(null=True)

    # An optional dictionary of things like API keys.
    keys = JSONB(null=True)

    @classmethod
    async def from_pydantic(
        cls, model: SparrowConfigModel, file_metadata: FileMetadata
    ) -> "SparrowConfig":
        client_id = model.id
        description = model.description
        parent_flock_id = model.parent_flock_id
        follow_parent_story = model.follow_parent_story
        parameters = (
            model.parameters.dict(exclude_none=True) if model.parameters else None
        )
        keys = model.keys.dict(exclude_none=True) if model.keys else None

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[SparrowConfig] = (
            await SparrowConfig.objects()
            .where(SparrowConfig.client_id == client_id)
            .first()
            .run()
        )

        if instance:
            instance.date_created = date_created
            instance.date_updated = date_updated
            instance.description = description
            instance.parent_flock_client_id = parent_flock_id
            instance.follow_parent_story = follow_parent_story
            instance.parameters = parameters
            instance.keys = keys
        else:
            instance = SparrowConfig(
                date_created=date_created,
                date_updated=date_updated,
                client_id=client_id,
                description=description,
                parent_flock_client_id=parent_flock_id,
                follow_parent_story=follow_parent_story,
                parameters=parameters,
                keys=keys,
            )

        return instance


class ClientTypeConfig(Table):
    """
    The definition of a client type.
    """

    # The sparrow or flock ID. For a sparrow, the client ID or client type.
    # For a flock, a human-readable slug.
    client_id = Varchar(length=50, unique=True, index=True)

    # Notes about the sparrow, flock, or client type.
    description = Text(null=True, required=False)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    # Optional strategy parameters.
    parameters = JSONB(null=True)

    @classmethod
    async def from_pydantic(
        cls, model: ClientTypeConfigModel, file_metadata: FileMetadata
    ) -> "ClientTypeConfig":
        client_id = model.id
        description = model.description
        parameters = (
            model.parameters.dict(exclude_none=True) if model.parameters else None
        )
        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[ClientTypeConfig] = (
            await ClientTypeConfig.objects()
            .where(ClientTypeConfig.client_id == client_id)
            .first()
            .run()
        )
        if instance:
            instance.date_created = date_created
            instance.date_updated = date_updated
            instance.description = description
            instance.parameters = parameters
        else:
            instance = ClientTypeConfig(
                date_created=date_created,
                date_updated=date_updated,
                client_id=client_id,
                description=description,
                parameters=parameters,
            )

        return instance
