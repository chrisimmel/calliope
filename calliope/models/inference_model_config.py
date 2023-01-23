from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, StrictStr


class InferenceModelProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    STABILITY = "stability"
    OPENAI = "openai"


class InferenceModelConfigModel(BaseModel):
    """
    The configuration for a specific inference model.
    """

    # Who hosts the model?
    provider: InferenceModelProvider

    # The model's name. There may be multiple configurations per model.
    model_name: StrictStr

    # Any parameters the model takes (provider- and model-specific).
    parameters: Dict[str, Any] = {}


# A registry of inference model configs. This can be selected by name when
# performing inferences.
_model_configs_by_name = {
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
    "openai_curie": InferenceModelConfigModel(
        provider=InferenceModelProvider.OPENAI,
        model_name="curie",
        parameters={
            "max_tokens": 1024,
        },
    ),
    "openai_dall_e_2": InferenceModelConfigModel(
        provider=InferenceModelProvider.OPENAI,
        model_name="DALL-E-2",
        parameters={},
    ),
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


def load_inference_model_configs(
    image_to_text_model_config: str = "huggingface_image_captioning",
    text_to_image_model_config: str = "stability_stable_diffusion_1.5",
    text_to_text_model_config: str = "huggingface_gpt_neo_2.7B",
    audio_to_text_model_config: str = "openai_whisper",
) -> InferenceModelConfigsModel:
    return InferenceModelConfigsModel(
        image_to_text_model_config=get_model_config_by_name(image_to_text_model_config),
        text_to_image_model_config=get_model_config_by_name(text_to_image_model_config),
        text_to_text_model_config=get_model_config_by_name(text_to_text_model_config),
        audio_to_text_model_config=get_model_config_by_name(audio_to_text_model_config),
    )
