# type: ignore
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod


ID = "2023-07-06T14:14:49:664537"
VERSION = "0.116.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="PromptTemplate",
        tablename="prompt_template",
        column_name="target_language",
        db_column_name="target_language",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 10,
            "default": "en",
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
