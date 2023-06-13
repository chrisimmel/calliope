from datetime import datetime

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    Boolean,
    ForeignKey,
    JSONB,
    Serial,
    Text,
    Timestamptz,
    Varchar,
)
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table

from calliope.models import InferenceModelProvider, InferenceModelProviderVariant


ID = "2023-05-05T14:09:37:436612"
VERSION = "0.106.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    def run():
        print(f"running {ID}")

    manager.add_raw(run)

    return manager


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

    # A slug naming the prompt template. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary on the template. What is it for? Which model(s) does it target?
    description = Text()

    # The raw template text, in Jinja2 format.
    text = Text()

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


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

    # A slug naming the model. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The model provider. Who hosts this model?
    provider = Varchar(length=80, choices=InferenceModelProvider)

    # The provider's API variant, if pertinent.
    provider_api_variant = Varchar(
        length=80, null=True, choices=InferenceModelProviderVariant
    )

    # The provider's name for this model. There may be multiple configurations per
    # provider model. For example, we may have multiple configurations that target
    # GPT-3 curie.
    provider_model_name = Varchar(length=80)

    # Any parameters the model takes (provider- and model-specific).
    # These are defaults that may be overridden elsewhere.
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


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

    # A slug naming the model config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The inference model.
    model = ForeignKey(references=InferenceModel, target_column=InferenceModel.slug)
    model_id = ForeignKey(references=InferenceModel)

    # Optional link to the prompt template to use when invoking the model.
    prompt_template = ForeignKey(
        references=PromptTemplate, target_column=PromptTemplate.slug, null=True
    )
    prompt_template_id = ForeignKey(references=PromptTemplate, null=True)

    # Parameters for the model (overriding those set in the InferenceModel).
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


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

    # A slug naming the strategy config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Identifies the strategy.
    strategy_name = Varchar(length=80, unique=True, index=True)

    # Whether this is the default configuration for its strategy.
    is_default = Boolean(default=False)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The strategy parameters.
    parameters = JSONB(null=True)

    # The default text -> text inference model config.
    text_to_text_model_config = ForeignKey(
        references=ModelConfig,
        target_column=ModelConfig.slug,
        null=True,
    )
    text_to_text_model_config_id = ForeignKey(
        references=ModelConfig,
        null=True,
    )
    # THe default text -> image inference model config.
    text_to_image_model_config = ForeignKey(
        references=ModelConfig,
        target_column=ModelConfig.slug,
        null=True,
    )
    text_to_image_model_config_id = ForeignKey(
        references=ModelConfig,
        null=True,
    )

    # Optional link to the prompt template to use as the hidden seed text to get a story
    # going when there is no prior story text.
    seed_prompt_template = ForeignKey(
        references=PromptTemplate, target_column=PromptTemplate.slug, null=True
    )
    seed_prompt_template_id = ForeignKey(references=PromptTemplate, null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="calliope", description=DESCRIPTION
    )

    async def update_model_config():
        print(f"running {ID}: update_model_config")
        for model_config in await ModelConfig.objects(
            ModelConfig.model, ModelConfig.prompt_template
        ).run():
            if model_config.model:
                model_config.model_id = model_config.model.id
            if model_config.prompt_template:
                model_config.prompt_template_id = model_config.prompt_template.id

            await model_config.save().run()

    manager.add_raw(update_model_config)

    async def update_strategy_config():
        print(f"running {ID}: update_strategy_config")
        for strategy_config in await StrategyConfig.objects(
            StrategyConfig.seed_prompt_template,
            StrategyConfig.text_to_image_model_config,
            StrategyConfig.text_to_text_model_config,
        ).run():
            if strategy_config.seed_prompt_template:
                strategy_config.seed_prompt_template_id = (
                    strategy_config.seed_prompt_template.id
                )
            if strategy_config.text_to_image_model_config:
                strategy_config.text_to_image_model_config_id = (
                    strategy_config.text_to_image_model_config.id
                )
            if strategy_config.text_to_text_model_config:
                strategy_config.text_to_text_model_config_id = (
                    strategy_config.text_to_text_model_config.id
                )

            await strategy_config.save().run()

    manager.add_raw(update_strategy_config)

    return manager
