# type: ignore
from datetime import datetime
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    Boolean,
    ForeignKey,
    JSONB,
    Timestamptz,
    Varchar,
    Text,
)
from piccolo.table import Table


ID = "2023-04-10T08:39:17:858265"
VERSION = "0.106.0"
DESCRIPTION = "Seeding the StrategyConfig table."


class ModelConfig(Table):
    """
    A stub for the real model, needed just to resolve the foreign key.
    """

    slug = Varchar(length=80, unique=True, index=True)


class PromptTemplate(Table):
    """
    A stub for the real model, needed just to resolve the foreign key.
    """

    slug = Varchar(length=80, unique=True, index=True)


class StrategyConfig(Table):
    """
    For example:
    strategy_config = {
        "slug": "continuous-v1-chris",
        "text_to_text_model_config": "gpt-4-chris-desnos-calm",
    },
    """

    # A slug naming the strategy config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Identifies the strategy.
    strategy_name = Varchar(length=80)

    # Whether this is the default configuration for its strategy.
    is_default = Boolean(default=False)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The strategy parameters.
    parameters = JSONB(null=True)

    # THe default text -> text inference model config.
    text_to_text_model_config = ForeignKey(
        references=ModelConfig,
        target_column=ModelConfig.slug,
        null=True,
    )

    # THe default text -> image inference model config.
    text_to_image_model_config = ForeignKey(
        references=ModelConfig,
        target_column=ModelConfig.slug,
        null=True,
    )

    # Optional link to the prompt template to use as the hidden seed text to get a story
    # going when there is no prior story text.
    seed_prompt_template = ForeignKey(
        references=PromptTemplate, target_column=PromptTemplate.slug, null=True
    )

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


_strategy_config_specs = [
    # for continuous-v0 w GTP-Neo
    {
        "slug": "continuous-v0",
        "strategy_name": "continuous-v0",
        "is_default": True,
        "description": """The default config for strategy continuous-v0.""",
        "parameters": {},
        "text_to_text_model_config": "gpt-neo-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
        "seed_prompt_template": "desnos-seed",
    },
    # for continuous-v1 w GPT-3 Curie
    {
        "slug": "continuous-v1-curie",
        "strategy_name": "continuous-v1",
        "is_default": True,
        "description": """The default config for strategy continuous-v1 with GPT-3 Curie.""",
        "parameters": {},
        "text_to_text_model_config": "curie-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
        "seed_prompt_template": "desnos-seed",
    },
    # for continuous-v1 w GPT-3 Davinci
    {
        "slug": "continuous-v1-davinci",
        "strategy_name": "continuous-v1",
        "is_default": False,
        "description": """The default config for strategy continuous-v1 with GPT-3 Davinci.""",
        "parameters": {},
        "text_to_text_model_config": "davinci-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
        "seed_prompt_template": "desnos-seed",
    },
    # for continuous-v1 w GPT-4
    {
        "slug": "continuous-v1-gpt-4",
        "strategy_name": "continuous-v1",
        "is_default": False,
        "description": """The default config for strategy continuous-v1 with GPT-4.""",
        "parameters": {},
        "text_to_text_model_config": "gpt-4-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
        "seed_prompt_template": "desnos-seed",
    },
    # for literal
    {
        "slug": "literal",
        "strategy_name": "literal",
        "is_default": True,
        "description": """The default config for strategy literal.""",
        "parameters": {},
        "text_to_text_model_config": None,
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
    },
    # for show-this-frame
    {
        "slug": "show-this-frame",
        "strategy_name": "show-this-frame",
        "is_default": True,
        "description": """The default config for strategy show-this-frame.""",
        "parameters": {},
        "text_to_text_model_config": None,
        "text_to_image_model_config": None,
    },
    # for simple-one-frame
    {
        "slug": "simple-one-frame",
        "strategy_name": "simple-one-frame",
        "is_default": True,
        "description": """The default config for strategy simple-one-frame.""",
        "parameters": {},
        "text_to_text_model_config": "gpt-neo-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
    },
    # for simple-one-frame w GPT-3 Davinci
    {
        "slug": "simple-one-frame-davinci",
        "strategy_name": "simple-one-frame",
        "is_default": False,
        "description": """A config for strategy simple-one-frame with GPT-3 Davinci.""",
        "parameters": {},
        "text_to_text_model_config": "davinci-default",
        "text_to_image_model_config": "stability-stable-diffusion-1.5",
    },
]


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")
        now = datetime.now()

        for config_spec in _strategy_config_specs:
            strategy_config = StrategyConfig(
                slug=config_spec["slug"],
                strategy_name=config_spec["strategy_name"],
                is_default=config_spec["is_default"],
                description=config_spec["description"],
                parameters=config_spec["parameters"],
                text_to_text_model_config=config_spec["text_to_text_model_config"],
                text_to_image_model_config=config_spec["text_to_image_model_config"],
                seed_prompt_template=config_spec.get("seed_prompt_template"),
                date_created=now,
                date_updated=now,
            )
            print(f"Saving strategy config {strategy_config}...")
            await strategy_config.save().run()

    manager.add_raw(run)

    return manager
