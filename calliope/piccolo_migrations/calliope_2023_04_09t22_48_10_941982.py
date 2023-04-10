from datetime import datetime
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    ForeignKey,
    JSONB,
    Timestamptz,
    Varchar,
    Text,
)
from piccolo.table import Table


ID = "2023-04-09T22:48:10:941982"
VERSION = "0.106.0"
DESCRIPTION = "Seeding the InferenceModelConfig table."


class InferenceModel(Table):
    """
    A stub for the real model, needed just to resolve the foreign key.
    """

    slug = Varchar(length=80, unique=True, index=True)


class PromptTemplate(Table):
    """
    A stub for the real model, needed just to resolve the foreign key.
    """

    slug = Varchar(length=80, unique=True, index=True)


class InferenceModelConfig(Table):
    """
    An inference model configuration.
    """

    # A slug naming the model config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # THe inference model.
    model = ForeignKey(references=InferenceModel, target_column=InferenceModel.slug)

    # Optional slug of the prompt template to use when invoking the model.
    prompt_template = ForeignKey(
        references=PromptTemplate, target_column=PromptTemplate.slug, null=True
    )

    # Parameters for the model (overriding those set in the InferenceModel).
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


_model_config_specs = [
    #
    # Text-to-text models...
    # for GTP-Neo
    {
        "slug": "gpt-neo-default",
        "description": """The default configuration for GPT-NEO carries a simple pass-through prompt and no extra parameters.""",
        "model": "huggingface-gpt-neo-2.7B",
        "prompt_template": "continue-pass-through",
        "model_parameters": {},
    },
    # for GPT-3 Curie
    {
        "slug": "curie-default",
        "description": """The default configuration for GPT-3 Curie works well with strategy continuous-v1.""",
        "model": "openai-curie",
        "prompt_template": "continuous-v1-curie-simple",
        "model_parameters": {},
    },
    # for GPT-3 Davinci
    {
        "slug": "davinci-default",
        "description": """The default configuration for GPT-3 Davinci works well with strategy continuous-v1.""",
        "model": "openai-davinci-03",
        "prompt_template": "continuous-v1-davinci-few-shot-00",
        "model_parameters": {},
    },
    # for GPT-4
    {
        "slug": "gpt-4-default",
        "description": """The default configuration for GPT-4 works well with strategy continuous-v1.""",
        "model": "openai-gpt-4",
        "prompt_template": "continuous-v1-gpt-4-few-shot-00",
        "model_parameters": {},
    },
    #
    # Text-to-image models...
    # for huggingface-stable-diffusion-1.5
    {
        "slug": "huggingface-stable-diffusion-1.5",
        "description": """The default configuration for Hugging Face Stable Diffusion.""",
        "model": "huggingface-stable-diffusion-1.5",
        "prompt_template": "styled-image",
        "model_parameters": {},
    },
    # for stability-stable-diffusion-1.5
    {
        "slug": "stability-stable-diffusion-1.5",
        "description": """The default configuration for Stability Stable Diffusion.""",
        "model": "stability-stable-diffusion-1.5",
        "prompt_template": "styled-image",
        "model_parameters": {},
    },
    # for openai-dall-e-2
    {
        "slug": "openai-dall-e-2",
        "description": """The default configuration for DALL-E 2.""",
        "model": "openai-dall-e-2",
        "prompt_template": "styled-image",
        "model_parameters": {},
    },
]


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")
        now = datetime.now()

        for config_spec in _model_config_specs:
            model_config = InferenceModelConfig(
                slug=config_spec["slug"],
                description=config_spec["description"],
                model=config_spec["model"],
                prompt_template=config_spec["prompt_template"],
                model_parameters=config_spec["model_parameters"],
                date_created=now,
                date_updated=now,
            )
            print(f"Saving model config {model_config}...")
            await model_config.save().run()

    manager.add_raw(run)

    return manager
