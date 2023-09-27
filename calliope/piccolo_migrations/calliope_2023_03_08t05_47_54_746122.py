# type: ignore
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Serial
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


ID = "2023-03-08T05:47:54:746122"
VERSION = "0.106.0"
DESCRIPTION = "Adding a foreign key to Story from the Image table."


class Image(Table, tablename="image"):
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


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Story",
        tablename="story",
        column_name="thumbnail_image",
        db_column_name="thumbnail_image",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Image,
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
