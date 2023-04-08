from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import JSONB
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class PromptTemplate(Table, tablename="prompt_template"):
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
    slug = Varchar(
        length=80,
        default="",
        null=False,
        primary_key=False,
        unique=True,
        index=True,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2023-04-08T03:39:06:521711"
VERSION = "0.106.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_table("InferenceModelConfig", tablename="inference_model_config")

    manager.add_table("PromptTemplate", tablename="prompt_template")

    manager.add_table("InferenceModel", tablename="inference_model")

    manager.add_table("StrategyConfig", tablename="strategy_config")

    manager.add_column(
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
        column_name="description",
        db_column_name="description",
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
    )

    manager.add_column(
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
        column_name="model",
        db_column_name="model",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": "InferenceModel",
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": "slug",
            "null": True,
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
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
        column_name="prompt_template",
        db_column_name="prompt_template",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PromptTemplate,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": "slug",
            "null": True,
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
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
        column_name="model_parameters",
        db_column_name="model_parameters",
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
    )

    manager.add_column(
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
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
        table_class_name="InferenceModelConfig",
        tablename="inference_model_config",
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
        table_class_name="PromptTemplate",
        tablename="prompt_template",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="PromptTemplate",
        tablename="prompt_template",
        column_name="title",
        db_column_name="title",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
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
        table_class_name="PromptTemplate",
        tablename="prompt_template",
        column_name="description",
        db_column_name="description",
        column_class_name="Text",
        column_class=Text,
        params={
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
        table_class_name="PromptTemplate",
        tablename="prompt_template",
        column_name="text",
        db_column_name="text",
        column_class_name="Text",
        column_class=Text,
        params={
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
        table_class_name="PromptTemplate",
        tablename="prompt_template",
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
        table_class_name="PromptTemplate",
        tablename="prompt_template",
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
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="description",
        db_column_name="description",
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
    )

    manager.add_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="provider",
        db_column_name="provider",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "InferenceModelProvider",
                {
                    "HUGGINGFACE": "huggingface",
                    "STABILITY": "stability",
                    "OPENAI": "openai",
                    "AZURE": "azure",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="provider_api_variant",
        db_column_name="provider_api_variant",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "InferenceModelProviderVariant",
                {
                    "OPENAI_COMPLETION": "openai_completion",
                    "OPENAI_CHAT_COMPLETION": "openai_chat_completion",
                },
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
        column_name="model_parameters",
        db_column_name="model_parameters",
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
    )

    manager.add_column(
        table_class_name="InferenceModel",
        tablename="inference_model",
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
        table_class_name="InferenceModel",
        tablename="inference_model",
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
        column_name="slug",
        db_column_name="slug",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="strategy_name",
        db_column_name="strategy_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 80,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="description",
        db_column_name="description",
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="parameters",
        db_column_name="parameters",
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_text_inference_model_config",
        db_column_name="text_to_text_inference_model_config",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": "InferenceModelConfig",
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": "slug",
            "null": True,
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
        column_name="text_to_image_inference_model_config",
        db_column_name="text_to_image_inference_model_config",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": "InferenceModelConfig",
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": "slug",
            "null": True,
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
        table_class_name="StrategyConfig",
        tablename="strategy_config",
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

    return manager
