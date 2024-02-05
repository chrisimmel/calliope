from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import JSONB
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


class PromptTemplate(Table, tablename="prompt_template", schema=None):
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


ID = "2024-01-12T09:35:22:532352"
VERSION = "1.1.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Story",
        tablename="story",
        column_name="state_props",
        db_column_name="state_props",
        column_class_name="JSONB",
        column_class=JSONB,
        params={
            "default": "{}",
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
        column_name="provider_api_variant",
        db_column_name="provider_api_variant",
        params={
            "choices": Enum(
                "InferenceModelProviderVariant",
                {
                    "DEFAULT": "default",
                    "OPENAI_COMPLETION": "openai_completion",
                    "OPENAI_CHAT_COMPLETION": "openai_chat_completion",
                },
            )
        },
        old_params={
            "choices": Enum(
                "InferenceModelProviderVariant",
                {
                    "OPENAI_COMPLETION": "openai_completion",
                    "OPENAI_CHAT_COMPLETION": "openai_chat_completion",
                },
            )
        },
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
