from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import Boolean
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class BookmarkList(Table, tablename="bookmark_list", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class SparrowState(Table, tablename="sparrow_state", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class Story(Table, tablename="story", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class StoryFrame(Table, tablename="story_frame", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


ID = "2024-01-12T09:59:51:216818"
VERSION = "1.1.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_table(
        class_name="BookmarkList",
        tablename="bookmark_list",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="StoryBookmark",
        tablename="story_bookmark",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="name",
        db_column_name="name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 128,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="descriiption",
        db_column_name="descriiption",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="sparrow",
        db_column_name="sparrow",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": SparrowState,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="is_public",
        db_column_name="is_public",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="date_created",
        db_column_name="date_created",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BookmarkList",
        tablename="bookmark_list",
        column_name="date_updated",
        db_column_name="date_updated",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="story",
        db_column_name="story",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Story,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="sparrow",
        db_column_name="sparrow",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": SparrowState,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="list",
        db_column_name="list",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": BookmarkList,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="comments",
        db_column_name="comments",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="date_created",
        db_column_name="date_created",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryBookmark",
        tablename="story_bookmark",
        column_name="date_updated",
        db_column_name="date_updated",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        column_name="frame",
        db_column_name="frame",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": StoryFrame,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        column_name="sparrow",
        db_column_name="sparrow",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": SparrowState,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        column_name="comments",
        db_column_name="comments",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        column_name="date_created",
        db_column_name="date_created",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="StoryFrameBookmark",
        tablename="story_frame_bookmark",
        column_name="date_updated",
        db_column_name="date_updated",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.rename_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        old_column_name="model_id",
        new_column_name="model",
        old_db_column_name="model_id",
        new_db_column_name="model",
        schema=None,
    )

    manager.rename_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        old_column_name="prompt_template_id",
        new_column_name="prompt_template",
        old_db_column_name="prompt_template_id",
        new_db_column_name="prompt_template",
        schema=None,
    )

    manager.rename_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        old_column_name="seed_prompt_template_id",
        new_column_name="seed_prompt_template",
        old_db_column_name="seed_prompt_template_id",
        new_db_column_name="seed_prompt_template",
        schema=None,
    )

    manager.rename_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        old_column_name="text_to_image_model_config_id",
        new_column_name="text_to_image_model_config",
        old_db_column_name="text_to_image_model_config_id",
        new_db_column_name="text_to_image_model_config",
        schema=None,
    )

    manager.rename_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        old_column_name="text_to_text_model_config_id",
        new_column_name="text_to_text_model_config",
        old_db_column_name="text_to_text_model_config_id",
        new_db_column_name="text_to_text_model_config",
        schema=None,
    )

    manager.alter_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="provider_api_variant",
        db_column_name="provider_api_variant",
        params={"default": "default"},
        old_params={"default": ""},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    # Note: this migration actually failed for some reason, although
    # I've forced it to be marked as run.
    # TODO: Go back and figure out what happened when bringing bookmark
    # features online. Other functions appear fine.

    return manager
