from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import (
    Varchar,
)
from piccolo.columns.indexes import IndexMethod

ID = "2025-05-14T08:21:26:355485"
VERSION = "1.7.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Story",
        tablename="story",
        column_name="slug",
        db_column_name="slug",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 100,
            "default": None,
            "null": True,
            "primary_key": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
