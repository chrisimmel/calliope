from piccolo.engine.postgres import PostgresEngine
from piccolo.conf.apps import AppRegistry

from calliope.settings import settings

DB = PostgresEngine(
    config={
        "host": settings.POSTGRESQL_HOSTNAME,
        "database": settings.POSTGRESQL_DATABASE,
        "user": settings.POSTGRESQL_USERNAME,
        "password": settings.POSTGRESQL_PASSWORD,
    }
)


APP_REGISTRY = AppRegistry(apps=["calliope.piccolo_app", "piccolo_admin.piccolo_app"])
