from datetime import datetime
from calliope.models import InferenceModelProvider, InferenceModelProviderVariant

from piccolo.table import Table
from piccolo.columns import (
    ForeignKey,
    JSONB,
    Timestamptz,
    Varchar,
    Text,
)


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
    strategy_name = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The strategy parameters.
    parameters = JSONB(null=True)

    # THe default text -> text inference model config.
    text_to_text_inference_model_config = ForeignKey(
        references="InferenceModelConfig", target_column="slug", null=True
    )

    # THe default text -> image inference model config.
    text_to_image_inference_model_config = ForeignKey(
        references="InferenceModelConfig", target_column="slug", null=True
    )

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


class InferenceModelConfig(Table):
    """
    An inference model configuration,
    """

    # A slug naming the model config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # THe inference model.
    model = ForeignKey(references="InferenceModel", target_column="slug")

    # Optional slug of the prompt template to use when invoking the model.
    prompt_template = ForeignKey(
        references="PromptTemplate", target_column="slug", null=True
    )

    # Parameters for the model (overriding those set in the InferenceModel).
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


class InferenceModel(Table):
    """
    An inference model.

    For example:
        model = {
            "slug": "openai-gpt-4",
            "provider": InferenceModelProvider.OPENAI,
            "provider_api_variant": InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION,
            "provider_model_name": "gpt-4",
            "model_parameters": {
                "max_tokens": 512,
                "temperature": 1,
                "presence_penalty": 1.5,
                "frequency_penalty": 1.5,
            }
        },
    """

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
    provider_model_name: Varchar(length=80)

    # Any parameters the model takes (provider- and model-specific).
    # These are defaults that may be overridden elsewhere.
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


"""
A strategy has a default model config.
The model config used by a strategy can be overridden via sparrow or API params.
It would be desirable for default parameters to be configurable per strategy, so
if I ask for strategy continuous_v1 I should get different default parameters than
if I ask for strategy continuous_v0.


(Classic)
sparrow config =
{
    "debug": false,
    "strategy": "continuous_v1",
    "extra_fields": {},
    "output_image_width": 512,
    "output_image_height": 512,
    "text_to_text_model_config": "openai_gpt_4"
}


(Updated v0)
sparrow config =
{
    "debug": false,
    "strategy": "continuous_v1",
    "output_image_width": 512,
    "output_image_height": 512,

    "parameters_by_strategy": {
        "continuous_v1": {
            "text_to_text_model_config": "openai_gpt_4"
        },
        "continuous_v0": {
            "text_to_text_model_config": "huggingface_gpt_neo_2.7B"
        },
    },
}

(Updated v1)
sparrow/flock config =
{
    "debug": false,
    "strategy": "continuous_v1_chris",
    "output_image_width": 512,
    "output_image_height": 512,
}

strategy_config = {
    "slug": "continuous-v1-chris",
    "strategy_name": "continuous-v1",
    "text_to_text_model_config": "gpt-4-chris-desnos-calm",
},

# A custom config that attaches a particular prompt and
# potentially adjusted model parameters.
model_config = {
    "slug": "gpt-4-chris-desnos-calm",
    "model": "openai-gpt-4",
    "prompt": "gpt-4-desnos-calm",
    "model_parameters": {
        "temperature": 1.2,
    }
},

# The base model config that sets reasonable default parameters.
model = {
    "slug": "openai-gpt-4",
    "provider": InferenceModelProvider.OPENAI,
    "provider_variant": InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION,
    "model_name": "gpt-4",
    "model_parameters": {
        "max_tokens": 512,
        "temperature": 1,
        "presence_penalty": 1.5,
        "frequency_penalty": 1.5,
    }
},

....

strategy_config = {
    "slug": "continuous_v0",
    "text_to_text_model_config": "huggingface_gpt_neo_2.7B"
},

"""
