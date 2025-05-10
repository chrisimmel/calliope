from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import Float
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Integer
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class ModelConfig(Table, tablename="model_config", schema=None):
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


class Video(Table, tablename="video", schema=None):
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


ID = "2025-05-09T14:33:40:364069"
VERSION = "1.7.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_table("Video", tablename="video")

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="width",
        db_column_name="width",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="height",
        db_column_name="height",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="format",
        db_column_name="format",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
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
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="url",
        db_column_name="url",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
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
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="duration_seconds",
        db_column_name="duration_seconds",
        column_class_name="Float",
        column_class=Float,
        params={
            "default": 5.0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
        column_name="frame_rate",
        db_column_name="frame_rate",
        column_class_name="Float",
        column_class=Float,
        params={
            "default": 24.0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
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
    )

    manager.add_column(
        table_class_name="Video",
        tablename="video",
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_video_model_config",
        db_column_name="text_to_video_model_config",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": ModelConfig,
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
        table_class_name="StoryFrame",
        tablename="story_frame",
        column_name="video",
        db_column_name="video",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Video,
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

    manager.alter_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="provider",
        db_column_name="provider",
        params={
            "choices": Enum(
                "InferenceModelProvider",
                {
                    "HUGGINGFACE": "huggingface",
                    "STABILITY": "stability",
                    "OPENAI": "openai",
                    "AZURE": "azure",
                    "REPLICATE": "replicate",
                    "RUNWAY": "runway",
                },
            )
        },
        old_params={
            "choices": Enum(
                "InferenceModelProvider",
                {
                    "HUGGINGFACE": "huggingface",
                    "STABILITY": "stability",
                    "OPENAI": "openai",
                    "AZURE": "azure",
                    "REPLICATE": "replicate",
                },
            )
        },
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
