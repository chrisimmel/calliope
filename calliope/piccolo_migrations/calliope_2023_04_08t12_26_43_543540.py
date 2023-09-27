# type: ignore
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    JSONB,
    Timestamptz,
    Varchar,
    Text,
)
from piccolo.table import Table
from pydantic import BaseModel, StrictStr

from calliope.models import InferenceModelProvider, InferenceModelProviderVariant

ID = "2023-04-08T12:26:43:543540"
VERSION = "0.106.0"
DESCRIPTION = "Seeding the InferenceModel table."


class InferenceModelProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    STABILITY = "stability"
    OPENAI = "openai"
    AZURE = "azure"


class InferenceModelProviderVariant(str, Enum):
    OPENAI_COMPLETION = "openai_completion"
    OPENAI_CHAT_COMPLETION = "openai_chat_completion"


class InferenceModelConfigModel(BaseModel):
    """
    The configuration for a specific inference model.
    """

    description: StrictStr

    # Who hosts the model?
    provider: InferenceModelProvider

    # The provider's API variant, if pertinent.
    provider_variant: Optional[InferenceModelProviderVariant]

    # The model's name. There may be multiple configurations per model.
    model_name: StrictStr

    # Any parameters the model takes (provider- and model-specific).
    parameters: Dict[str, Any] = {}


# A registry of inference model configs. This can be selected by name when
# performing inferences.
_model_configs_by_name = {
    # Azure models...
    "azure-vision-analysis": InferenceModelConfigModel(
        description="Analyze images via the Azure Computer Vision API.",
        provider=InferenceModelProvider.AZURE,
        # model_name="/vision/v3.2/analyze",
        model_name="/computervision/imageanalysis:analyze",
        # parameters={"visualFeatures": "Categories,Description,Faces,Objects,Tags"},
        parameters={
            "features": "tags,objects,description,read,people",
            "language": "en",
            "model-version": "latest",
            "api-version": "2022-10-12-preview",
        },
    ),
    "azure-vision-ocr": InferenceModelConfigModel(
        description="Perform OCR via the Azure Computer Vision API (now included in computervision/imageanalysis).",
        provider=InferenceModelProvider.AZURE,
        model_name="/vision/v3.2/ocr",
    ),
    # HuggingFace models...
    "huggingface-image-captioning": InferenceModelConfigModel(
        description="Simple image captioning using Hugging Face",
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="nlpconnect/vit-gpt2-image-captioning",
    ),
    "huggingface-stable-diffusion-1.5": InferenceModelConfigModel(
        description="Stable Diffusion, hosted by Hugging Face",
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="runwayml/stable-diffusion-v1-5",
    ),
    "huggingface-gpt-neo-2.7B": InferenceModelConfigModel(
        description="GPT-NEO 2.7B, hosted by Hugging Face",
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="EleutherAI/gpt-neo-2.7B",
        parameters={
            "temperature": 1,
            "max_new_tokens": 250,
            "return_full_text": False,
            # "repetition_penalty": 80,
        },
    ),
    "huggingface-wav2vec2": InferenceModelConfigModel(
        description="The Facebook wav2vec2 speech recognition model, hosted by Hugging Face",
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="facebook/wav2vec2-large-960h-lv60-self",
    ),
    # Stability.ai models...
    "stability-stable-diffusion-1.5": InferenceModelConfigModel(
        description="The full Stable Diffusion, on Stability",
        provider=InferenceModelProvider.STABILITY,
        model_name="stable-diffusion-v1-5",  # engine
        # Available engines:
        # stable-diffusion-v1
        # stable-diffusion-v1-5
        # stable-diffusion-512-v2-0
        # stable-diffusion-768-v2-0
        # stable-diffusion-512-v2-1
        # stable-diffusion-768-v2-1
        # stable-inpainting-v1-0
        # stable-inpainting-512-v2-0
        parameters={
            # See https://platform.stability.ai/docs/features/api-parameters for all options.
            "steps": 30,
            "seed": 0,
            "cfg_scale": 7.0,
        },
    ),
    # OpenAI models...
    # Text->Text:
    "openai-gpt-4": InferenceModelConfigModel(
        description="OpenAI GPT-4",
        provider=InferenceModelProvider.OPENAI,
        provider_variant=InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION,
        model_name="gpt-4",
        parameters={
            "max_tokens": 512,
            "temperature": 1,
            "presence_penalty": 1.5,
            "frequency_penalty": 1.5,
        },
    ),
    "openai-chat-gpt": InferenceModelConfigModel(
        description="OpenAI ChatGPT Curie",
        provider=InferenceModelProvider.OPENAI,
        provider_variant=InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION,
        model_name="curie",
        parameters={
            "max_tokens": 256,
            "temperature": 0.85,
            "presence_penalty": 1.5,
            "frequency_penalty": 1.5,
        },
    ),
    "openai-curie": InferenceModelConfigModel(
        description="OpenAI GPT-3 Curie",
        provider=InferenceModelProvider.OPENAI,
        provider_variant=InferenceModelProviderVariant.OPENAI_COMPLETION,
        model_name="curie",
        parameters={
            "max_tokens": 256,
            "temperature": 0.85,
            "presence_penalty": 1.5,
            "frequency_penalty": 1.5,
        },
    ),
    "openai-davinci-03": InferenceModelConfigModel(
        description="OpenAI GPT-3 Davinci",
        provider=InferenceModelProvider.OPENAI,
        provider_variant=InferenceModelProviderVariant.OPENAI_COMPLETION,
        model_name="text-davinci-003",
        parameters={
            "max_tokens": 1024,
            "temperature": 0.85,
            "presence_penalty": 1.5,
            "frequency_penalty": 1.5,
        },
    ),
    # Text->Image...
    "openai-dall-e-2": InferenceModelConfigModel(
        description="OpenAI DALL-E 2",
        provider=InferenceModelProvider.OPENAI,
        model_name="DALL-E-2",
        parameters={},
    ),
    # Audio->Text...
    "openai-whisper": InferenceModelConfigModel(
        description="OpenAI Whisper speech recognition",
        provider=InferenceModelProvider.OPENAI,
        model_name="whisper",
        parameters={},
    ),
}


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
    provider_model_name = Varchar(length=80)

    # Any parameters the model takes (provider- and model-specific).
    # These are defaults that may be overridden elsewhere.
    model_parameters = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")

        for name, model_config in _model_configs_by_name.items():
            now = datetime.now()
            model = InferenceModel(
                slug=name,
                description=model_config.description,
                provider=model_config.provider,
                provider_api_variant=model_config.provider_variant,
                provider_model_name=model_config.model_name,
                model_parameters=model_config.parameters,
                date_created=now,
                date_updated=now,
            )
            print(f"Saving model {model}...")
            await model.save().run()

    manager.add_raw(run)

    return manager
