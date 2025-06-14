# Inference Module

The `calliope.inference` module is a core component of Calliope, providing a unified interface for interacting with various AI models and services. It handles translating between different modalities (text, image, audio) by interfacing with multiple external AI providers.

## Overview

The inference module abstracts away the complexity of working with different AI providers, offering a consistent API for Calliope's storytelling strategies. It supports:

- **Text-to-Text**: Generate text from text input using LLMs
- **Text-to-Image**: Generate images from text descriptions
- **Image-and-Text-to-Video**: Generate video from input images and text
- **Image Analysis**: Extract descriptions, objects, and text from images
- **Audio-to-Text**: Transcribe spoken audio to text
- **Messages-to-Object**: Convert structured LLM interactions into Pydantic objects

This modular design allows Calliope to combine AI capabilities from multiple providers in flexible ways, enabling rich, multimodal storytelling experiences.

## Module Structure

The inference module is organized as follows:

- **Core Inference Files**: High-level abstraction layer for different conversion types

  - `text_to_text.py`: Text generation using LLMs
  - `text_to_image.py`: Image generation from text descriptions
  - `image_analysis.py`: Extract information from images
  - `audio_to_text.py`: Speech-to-text conversion
  - `messages_to_object.py`: Convert LLM outputs to structured objects

- **Provider-specific Engines**: Implementation details for different AI providers
  - `engines/azure_vision.py`: Azure Computer Vision API integration
  - `engines/hugging_face.py`: Hugging Face models integration
  - `engines/openai_*.py`: OpenAI API integrations for various tasks
  - `engines/replicate.py`: Replicate.com API integration
  - `engines/runway.py`: Runway API integration for generating video
  - `engines/stability_image.py`: Stability AI (Stable Diffusion) integration
  - `engines/runway.py`: Runway API integration

## Supported AI Providers

The module integrates with several AI service providers:

- **OpenAI**: GPT models for text generation, DALL-E for image generation, Whisper for audio transcription
- **Anthropic**: (Coming soon) Claude models for text generation and multimodal capabilities
- **Azure**: Computer Vision APIs for image analysis and OCR
- **Runway**: API access to Runway models for video generation
- **Stability AI**: Stable Diffusion models for image generation
- **Hugging Face**: Access to open source models for various tasks
- **Replicate**: Hosted inference for open-source AI models
- **Runway**: (In progress) Video generation capabilities

## Key Features

### Text-to-Text Inference

```python
async def text_to_text_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> str:
```

Generates text from a text prompt using configured language models. Supports OpenAI, Hugging Face, and Replicate models. The output can be used for story continuation, dialogue generation, and other text-based storytelling elements.

### Text-to-Image Inference

```python
async def text_to_image_file_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_image_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[str]:
```

Converts text descriptions into images using various image generation models. Supports Stability AI (Stable Diffusion), OpenAI (DALL-E), Replicate, and Hugging Face models. Includes automatic content filtering to ensure appropriate image generation.

### Image-and-Text-to-Video Inference

```python
async def image_and_text_to_video_file_inference(
    httpx_client: httpx.AsyncClient,
    prompt_image_file: str,
    prompt_text: str,
    output_video_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
) -> Optional[str]:
```

Converts an image and text prompt into a video clip. Currently supports only Runway as a model provider.

### Image Analysis

```python
async def image_analysis_inference(
    httpx_client: httpx.AsyncClient,
    image_filename: str,
    b64_encoded_image: Optional[str],
    model_config: ModelConfig,
    keys: KeysModel,
) -> Dict[str, Any]:
```

Analyzes images to extract descriptions, objects, tags, and text. Combines multimodal LLMs with computer vision services (Azure) to provide comprehensive image understanding. This enables Calliope to "see" through a webcam or analyze submitted images for storytelling context.

### Audio-to-Text

```python
async def audio_to_text_inference(
    httpx_client: httpx.AsyncClient,
    input_audio_filename: str,
    language: str,
    keys: KeysModel,
) -> str:
```

Transcribes speech from audio files into text, currently using OpenAI's Whisper model. This allows for voice input to influence story direction.

### Messages-to-Object

```python
async def messages_to_object_inference(
    httpx_client: httpx.AsyncClient,
    messages: list[ChatCompletionMessageParam],
    model_config: ModelConfig,
    keys: KeysModel,
    response_model: type[T],
) -> T:
```

Converts structured chat messages into Pydantic objects, enabling type-safe interactions with language models. This is especially useful for extracting structured data from LLM responses.

## Usage Examples

### Generating Story Text

```python
async def generate_story_continuation(
    prompt: str,
    model_config: ModelConfig,
    keys: KeysModel
) -> str:
    async with httpx.AsyncClient() as client:
        continuation = await text_to_text_inference(
            client,
            prompt,
            model_config,
            keys
        )
        return continuation
```

### Creating an Image for a Story Frame

```python
async def generate_story_illustration(
    description: str,
    output_path: str,
    model_config: ModelConfig,
    keys: KeysModel
) -> str:
    async with httpx.AsyncClient() as client:
        image_path = await text_to_image_file_inference(
            client,
            description,
            output_path,
            model_config,
            keys,
            width=512,
            height=512
        )
        return image_path
```

### Analyzing an Input Image

```python
async def analyze_user_image(
    image_path: str,
    model_config: ModelConfig,
    keys: KeysModel
) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        analysis = await image_analysis_inference(
            client,
            image_path,
            None,  # b64_encoded_image
            model_config,
            keys
        )
        return analysis
```

## Configuration

The inference module uses a configuration system based on the `ModelConfig` and `InferenceModel` objects from Calliope's database, allowing for flexible model selection and parameter customization. Key configuration aspects include:

1. **Provider Selection**: Each inference type can use different AI providers
2. **Model Parameters**: Customizable parameters for each model (temperature, top_p, etc.)
3. **API Keys**: Managed through the `KeysModel` for secure access to various services

Example model configuration in the database:

```python
model_config = ModelConfig(
    slug="story-generation-model",
    description="GPT-4 model for story generation",
    model_parameters={
        "temperature": 0.7,
        "max_tokens": 500
    },
    model=InferenceModel(
        slug="openai-gpt-4",
        provider=InferenceModelProvider.OPENAI,
        provider_model_name="gpt-4",
        provider_api_variant=InferenceModelProviderVariant.OPENAI_CHAT_COMPLETION
    )
)
```

## Advanced Features

### Parallel Processing

The image analysis functionality demonstrates parallel processing by simultaneously querying both a multimodal LLM and Azure Computer Vision, then merging the results:

```python
# Execute Azure CV and multimodal LLM analysis in parallel
llm_analysis_task = asyncio.create_task(
    _image_analysis_inference(
        httpx_client, image_filename, b64_encoded_image,
        InferenceModelProvider.OPENAI, model_config, keys
    )
)

azure_cv_task = asyncio.create_task(
    _image_analysis_inference(
        httpx_client, image_filename, b64_encoded_image,
        InferenceModelProvider.AZURE, model_config, keys
    )
)

# Wait for both with timeout protection
llm_analysis = await asyncio.wait_for(llm_analysis_task, timeout)
azure_analysis = await azure_cv_task

# Merge results
analysis = {**azure_analysis, **llm_analysis}
```

### Content Filtering

The text-to-image functionality includes automatic content filtering to ensure appropriate image generation:

```python
# If generation fails, it may be due to content policy violations
# Censor the text and try again
if attempt < 3:
    text = await censor_text(
        text, keys, errors, httpx_client
    )
    print(f"Retrying with censored text: {text}")
```

## Extending the Module

To add support for new AI providers or capabilities:

1. Create a new engine file in the `engines/` directory
2. Implement the provider-specific API calls
3. Update the relevant inference function to include the new provider
4. Add the provider to the `InferenceModelProvider` enum in `calliope.models`

For example, to add a new text-to-text provider:

```python
# 1. Create engines/new_provider.py
async def new_provider_text_to_text_inference(
    httpx_client, text, model_config, keys
):
    # Implementation details
    return generated_text

# 2. Update text_to_text.py
async def text_to_text_inference(...):
    # ...
    elif model.provider == InferenceModelProvider.NEW_PROVIDER:
        extended_text = await new_provider_text_to_text_inference(
            httpx_client, text, model_config, keys
        )
    # ...
```

## Error Handling and Resilience

The inference module includes several resilience mechanisms:

- **Retry Logic**: API calls use tenacity for automatic retries with exponential backoff
- **Timeout Protection**: Long-running operations have configurable timeouts
- **Fallback Mechanisms**: If one service fails (e.g., multimodal LLM), the system can fall back to alternatives (e.g., Azure)
- **Content Safety**: Automatic content filtering for potentially inappropriate prompts

## Future Directions

The inference module is being expanded to include:

- **Video Generation**: Integration with video generation APIs like Runway
- **Additional Model Providers**: Support for more AI services and open-source models
- **Structured Output**: Enhanced capabilities for converting LLM outputs to structured data
- **Batch Processing**: Optimizations for processing multiple inference requests efficiently
