from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Boolean
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class InferenceModel(Table, tablename="inference_model", schema=None):
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


ID = "2023-07-21T16:24:55:013766"
VERSION = "0.116.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="StoryFrame",
        tablename="story_frame",
        column_name="indexed_for_search",
        db_column_name="indexed_for_search",
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
                },
            )
        },
        column_class=Varchar,
        old_column_class=Varchar,
    )

    return manager
