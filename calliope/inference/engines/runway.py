import asyncio
import os
from typing import Literal, Optional
import aiofiles

from calliope.tables.model_config import InferenceModel
from calliope.utils.file import encode_image_file_to_b64
import httpx
from runwayml import RunwayML

from calliope.models import (
    KeysModel,
)
from calliope.tables import ModelConfig
from calliope.utils.piccolo import load_json_if_necessary


async def runway_image_and_text_to_video_inference(
    httpx_client: httpx.AsyncClient,
    prompt_image_file: str,
    prompt_text: str,
    output_video_filename: str,
    model: InferenceModel,
    model_config: ModelConfig,
    keys: KeysModel,
    duration: Literal[5, 10] = 5
) -> str:
    """
    Generates a video from a text prompt using Runway's models.

    Args:
        httpx_client: the async HTTP session (not used with the RunwayML client).
        promp_text: the input text prompt.
        prompt_image_file: the input image.
        output_video_filename: where to save the generated video.
        model_config: model configuration with parameters.
        keys: API keys, including runway_api_key.
        width: optional width override.
        height: optional height override.
        num_frames: optional number of frames override.
        fps: optional frames per second override.
        
    Returns:
        The path to the generated video file.
    """
    if not keys.runway_api_key:
        raise ValueError(
            "Missing Runway authentication key. Aborting request."
        )

    # Set the API key for the Runway client
    os.environ["RUNWAYML_API_SECRET"] = keys.runway_api_key

    # Get parameters from model_config, with overrides from function arguments
    parameters = {
        **(
            load_json_if_necessary(model.model_parameters)
            if model.model_parameters
            else {}
        ),
        **(
            load_json_if_necessary(model_config.model_parameters)
            if model_config.model_parameters
            else {}
        ),
    }
    prompt_image = encode_image_file_to_b64(prompt_image_file)

    # Get the model name from the configuration, default to gen4_turbo if not specified
    model_name = model.provider_model_name if model.provider_model_name else "gen4_turbo"

    # Create a RunwayML client
    client = RunwayML()

    parameters["prompt_image"] = f"data:image/png;base64,{prompt_image}"
    parameters["prompt_text"] = prompt_text
    parameters["ratio"] = "960:960"
    parameters["duration"] = duration

    print(f"Generating video with Runway model {model_name}")
    print(f"Video prompt: {prompt_text}")

    try:
        # Create a new text-to-video task using the specified model
        task = client.image_to_video.create(
            model=model_name,
            **parameters,
        )
        task_id = task.id
        print(f"Started Runway text-to-video generation task: {task_id}")

        # Poll the task until it's complete
        max_attempts = 30  # 5 minutes max (10 seconds per attempt)
        attempt = 0
        start_time = asyncio.get_event_loop().time()

        while attempt < max_attempts:
            await asyncio.sleep(10)  # Wait before polling
            attempt += 1
            elapsed_time = asyncio.get_event_loop().time() - start_time

            task = client.tasks.retrieve(task_id)
            status = task.status
            print(f"Task {task_id} status: {status}, elapsed time: {elapsed_time:.1f}s")
            print(f"Task: {task}")

            if status == 'SUCCEEDED':
                # Download the generated video
                video_url = task.output[0] if task.output else None
                print(f"Video URL: {video_url}")

                if video_url:
                    async with httpx_client.stream("GET", video_url) as response:
                        response.raise_for_status()
                        async with aiofiles.open(output_video_filename, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                await f.write(chunk)
      
                    print(f"Video saved to {output_video_filename}")
                    return output_video_filename
                else:
                    raise ValueError("No video recovered.")

            elif status == 'FAILED':
                error = f"Failure: {task.failure}, Failure code: {task.failure_code}"
                raise ValueError(f"Runway video generation failed: {error}")

            # Continue polling if still processing

        # If we get here, the generation is taking too long
        raise TimeoutError(f"Runway video generation timed out after {max_attempts * 10} seconds")

    except Exception as e:
        print(f"Error in Runway video generation: {str(e)}")
        raise


async def runway_retrieve_video(
    httpx_client: httpx.AsyncClient,
    task_id: str,
    output_video_filename: str,
    keys: KeysModel,
) -> str:
    """
    Retrieves a video from a Runway generation task.
    
    Args:
        httpx_client: the async HTTP session (not used with the RunwayML client).
        task_id: the ID of the Runway task.
        
    Returns:
        The path to the generated video file.
    """
    if not keys.runway_api_key:
        raise ValueError(
            "Missing Runway authentication key. Aborting request."
        )

    # Set the API key for the Runway client
    os.environ["RUNWAYML_API_SECRET"] = keys.runway_api_key

    # Create a RunwayML client
    client = RunwayML()

    try:
        task = client.tasks.retrieve(task_id)
        status = task.status
        print(f"Task: {task}")

        if status == 'SUCCEEDED':
            # Download the generated video
            video_url = task.output[0] if task.output else None
            print(f"Video URL: {video_url}")

            if video_url:
                async with httpx_client.stream("GET", video_url) as response:
                    response.raise_for_status()
                    async with aiofiles.open(output_video_filename, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                            
                print(f"Video saved to {output_video_filename}")
                return output_video_filename
            else:
                raise ValueError("No video recovered.")        
    except Exception as e:
        print(f"Error in Runway video generation: {str(e)}")
        raise
