from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean
from piccolo.columns.indexes import IndexMethod


ID = "2024-01-14T14:43:23:366807"
VERSION = "1.1.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="StrategyConfig",
        tablename="strategy_config",
        column_name="is_experimental",
        db_column_name="is_experimental",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": True,
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

    return manager
