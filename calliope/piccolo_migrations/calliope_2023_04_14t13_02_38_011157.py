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


ID = "2023-04-14T13:02:38:011157"
VERSION = "0.106.0"
DESCRIPTION = ""


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


class ModelConfig(Table):
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
    # Image-to-text models...
    # for azure-vision-analysis
    {
        "slug": "azure-vision-analysis",
        "description": """A configuration for Azure vision analysis.""",
        "model": "azure-vision-analysis",
        "prompt_template": None,
        "model_parameters": {},
    },
]


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")
        now = datetime.now()

        for config_spec in _model_config_specs:
            model_config = ModelConfig(
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
