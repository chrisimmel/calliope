# type: ignore
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns import (
    ForeignKey,
    Serial,
    Varchar,
)
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
    slug = Varchar(length=80, unique=True, index=True)


class InferenceModel(Table, tablename="inference_model"):
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
    slug = Varchar(length=80, unique=True, index=True)


class ModelConfig(Table, tablename="model_config"):
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
    slug = Varchar(length=80, unique=True, index=True)


class StrategyConfig(Table, tablename="strategy_config"):
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
    slug = Varchar(length=80, unique=True, index=True)


ID = "2023-05-05T10:52:55:011937"
VERSION = "0.106.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        column_name="model_id",
        db_column_name="model_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": InferenceModel,
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
    )

    manager.add_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        column_name="prompt_template_id",
        db_column_name="prompt_template_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PromptTemplate,
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="seed_prompt_template_id",
        db_column_name="seed_prompt_template_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PromptTemplate,
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_image_model_config_id",
        db_column_name="text_to_image_model_config_id",
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
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_text_model_config_id",
        db_column_name="text_to_text_model_config_id",
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
    )

    return manager
