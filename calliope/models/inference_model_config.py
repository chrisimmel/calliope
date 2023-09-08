from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, StrictStr


class InferenceModelProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    STABILITY = "stability"
    OPENAI = "openai"
    AZURE = "azure"
    REPLICATE = "replicate"
    MODAL_STABLE_DIFFUSION = "modal_stable_diffusion"


class InferenceModelProviderVariant(str, Enum):
    OPENAI_COMPLETION = "openai_completion"
    OPENAI_CHAT_COMPLETION = "openai_chat_completion"


class InferenceModelConfigModel(BaseModel):
    """
    The configuration for a specific inference model.
    """

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
    "azure_vision_analysis": InferenceModelConfigModel(
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
    "azure_vision_ocr": InferenceModelConfigModel(
        provider=InferenceModelProvider.AZURE,
        model_name="/vision/v3.2/ocr",
    ),
    # HuggingFace models...
    "huggingface_image_captioning": InferenceModelConfigModel(
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="nlpconnect/vit-gpt2-image-captioning",
    ),
    "huggingface_stable_diffusion_1.5": InferenceModelConfigModel(
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="runwayml/stable-diffusion-v1-5",
    ),
    "huggingface_gpt_neo_2.7B": InferenceModelConfigModel(
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="EleutherAI/gpt-neo-2.7B",
        parameters={
            "temperature": 1,
            "max_new_tokens": 250,
            "return_full_text": False,
            # "repetition_penalty": 80,
        },
    ),
    "huggingface_wav2vec2": InferenceModelConfigModel(
        provider=InferenceModelProvider.HUGGINGFACE,
        model_name="facebook/wav2vec2-large-960h-lv60-self",
    ),
    # Stability.ai models...
    "stability_stable_diffusion_1.5": InferenceModelConfigModel(
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
    "openai_gpt_4": InferenceModelConfigModel(
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
    "openai_chat_gpt": InferenceModelConfigModel(
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
    "openai_curie": InferenceModelConfigModel(
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
    "openai_davinci_03": InferenceModelConfigModel(
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
    "openai_dall_e_2": InferenceModelConfigModel(
        provider=InferenceModelProvider.OPENAI,
        model_name="DALL-E-2",
        parameters={},
    ),
    # Audio->Text...
    "openai_whisper": InferenceModelConfigModel(
        provider=InferenceModelProvider.OPENAI,
        model_name="whisper",
        parameters={},
    ),
}


def get_model_config_by_name(name: str) -> Optional[InferenceModelConfigModel]:
    return _model_configs_by_name.get(name)


class InferenceModelConfigsModel(BaseModel):
    """
    The configurations of all inference models.
    """

    # Image analysis
    image_analysis_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("azure_vision_analysis")

    # Image OCR
    image_ocr_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("azure_vision_ocr")

    # Image -> text
    image_to_text_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("huggingface_image_captioning")

    # Text -> image
    text_to_image_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("stability_stable_diffusion_1.5")

    # Text -> text
    text_to_text_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("huggingface_gpt_neo_2.7B")

    # Audio -> text
    audio_to_text_model_config: Optional[
        InferenceModelConfigModel
    ] = get_model_config_by_name("openai_whisper")


def load_model_configs(
    image_analysis_model_config: str = "azure_vision_analysis",
    image_ocr_model_config: str = "azure_vision_ocr",
    image_to_text_model_config: str = "huggingface_image_captioning",
    text_to_image_model_config: str = "stability_stable_diffusion_1.5",
    text_to_text_model_config: str = "huggingface_gpt_neo_2.7B",
    audio_to_text_model_config: str = "openai_whisper",
) -> InferenceModelConfigsModel:
    return InferenceModelConfigsModel(
        image_analysis_model_config=get_model_config_by_name(
            image_analysis_model_config
        ),
        image_ocr_model_config=get_model_config_by_name(image_ocr_model_config),
        image_to_text_model_config=get_model_config_by_name(image_to_text_model_config),
        text_to_image_model_config=get_model_config_by_name(text_to_image_model_config),
        text_to_text_model_config=get_model_config_by_name(text_to_text_model_config),
        audio_to_text_model_config=get_model_config_by_name(audio_to_text_model_config),
    )
