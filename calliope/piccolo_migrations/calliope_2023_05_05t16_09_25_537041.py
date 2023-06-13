from piccolo.apps.migrations.auto.migration_manager import MigrationManager


ID = "2023-05-05T16:09:25:537041"
VERSION = "0.106.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        column_name="model",
        db_column_name="model",
    )

    manager.drop_column(
        table_class_name="ModelConfig",
        tablename="model_config",
        column_name="prompt_template",
        db_column_name="prompt_template",
    )

    manager.drop_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="seed_prompt_template",
        db_column_name="seed_prompt_template",
    )

    manager.drop_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_image_model_config",
        db_column_name="text_to_image_model_config",
    )

    manager.drop_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="text_to_text_model_config",
        db_column_name="text_to_text_model_config",
    )

    return manager
