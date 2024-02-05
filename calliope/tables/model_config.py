from datetime import datetime
from typing import Any, Dict

import jinja2
from piccolo.table import Table
from piccolo.columns import (
    Boolean,
    ForeignKey,
    JSONB,
    Timestamptz,
    Varchar,
    Text,
)
from piccolo.columns.readable import Readable

from calliope.models import InferenceModelProvider, InferenceModelProviderVariant


class PromptTemplate(Table, tablename="prompt_template"):
    """
    A template for a text prompt to be sent to an inference model, with support for template
    variables and control structures in Jinja2 format.
    """

    # A slug naming the prompt template. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary on the template. What is it for? Which model(s) does it target?
    description = Text()

    # The raw template text, in Jinja2 format.
    text = Text()

    # The language this prompt is expected to produce.
    target_language = Varchar(length=10, default="en")

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    def render(self, context: Dict[str, Any]) -> str:
        """
        Renders the template, replacing variables and executing control structures.

        Args:
            context: a dictionary of context variables available in the template.

        Returns:
            the rendered template.
        """
        environment = jinja2.Environment()
        template = environment.from_string(self.text)
        return template.render(context)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.slug])


class InferenceModel(Table, tablename="inference_model"):
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
        length=80,
        null=True,
        choices=InferenceModelProviderVariant,
        default=InferenceModelProviderVariant.DEFAULT,
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

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.slug])


class ModelConfig(Table, tablename="model_config"):
    """
    An inference model configuration.
    """

    # A slug naming the model config. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The inference model.
    model = ForeignKey(references=InferenceModel)

    # Optional link to the prompt template to use when invoking the model.
    prompt_template = ForeignKey(references=PromptTemplate, null=True)

    # Parameters for the model (overriding those set in the InferenceModel).
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.slug])


class StrategyConfig(Table, tablename="strategy_config"):
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

    # Whether this strategy config is experimental. True unless
    # chosen to be ready for the general public.
    is_experimental = Boolean(default=True)

    # Description and commentary.
    description = Text(null=True, required=False)

    # The strategy parameters.
    parameters = JSONB(null=True)

    # The default text -> text inference model config.
    text_to_text_model_config = ForeignKey(
        references=ModelConfig,
        null=True,
    )
    # THe default text -> image inference model config.
    text_to_image_model_config = ForeignKey(
        references=ModelConfig,
        null=True,
    )

    # Optional link to the prompt template to use as the hidden seed text to get a story
    # going when there is no prior story text.
    seed_prompt_template = ForeignKey(references=PromptTemplate, null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.slug])


"""
A strategy has a default model config.
The model config used by a strategy can be overridden via sparrow or API params.
It would be desirable for default parameters to be configurable per strategy, so
if I ask for strategy continuous-v1 I should get different default parameters than
if I ask for strategy continuous-v0.


(Classic)
sparrow config =
{
    "debug": false,
    "strategy": "continuous-v1",
    "extra_fields": {},
    "output_image_width": 512,
    "output_image_height": 512,
    "text_to_text_model_config": "openai_gpt_4"
}


(Updated v0)
sparrow config =
{
    "debug": false,
    "strategy": "continuous-v1",
    "output_image_width": 512,
    "output_image_height": 512,

    "parameters_by_strategy": {
        "continuous-v1": {
            "text_to_text_model_config": "openai_gpt_4"
        },
        "continuous-v0": {
            "text_to_text_model_config": "huggingface_gpt_neo_2.7B"
        },
    },
}

(Updated v1)
sparrow/flock config =
{
    "debug": false,
    "strategy": "continuous_=0v1_chris",
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
    "slug": "continuous-v0",
    "text_to_text_model_config": "huggingface-gpt-neo-2.7B"
},

"""
