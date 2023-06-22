from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    JSONB,
    Varchar,
)
from piccolo.table import Table


ID = "2023-04-10T13:48:59:155443"
VERSION = "0.106.0"
DESCRIPTION = "Move to hyphenated strategy names."


class SparrowConfig(Table):
    # Optional strategy parameters.
    parameters = JSONB(null=True)


class Story(Table):
    # The name of the strategy from which the story issues.
    strategy_name = Varchar(length=50, null=True)


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")
        for sparrow_config in await SparrowConfig.objects().output(load_json=True).run():
            strategy = (
                sparrow_config.parameters.get("strategy")
                if sparrow_config.parameters
                else None
            )
            if strategy:
                hyphenated_strategy = strategy.replace("_", "-")
                print(
                    f"Hyphenating strategy parameter {strategy} to {hyphenated_strategy}"
                )
                if hyphenated_strategy != strategy:
                    sparrow_config.parameters["strategy"] = hyphenated_strategy
                    await sparrow_config.save().run()

        for story in await Story.objects().output().run():
            strategy = story.strategy_name
            if strategy:
                hyphenated_strategy = strategy.replace("_", "-")
                print(
                    f"Hyphenating story strategy name {strategy} to {hyphenated_strategy}"
                )
                if hyphenated_strategy != strategy:
                    story.strategy_name = hyphenated_strategy
                    await story.save().run()

    manager.add_raw(run)

    return manager
