import asyncio
import os
import time
from typing import Any, Dict, Optional, cast
import aiofiles
import json

import httpx
from runwayml import RunwayML

from calliope.models import (
    KeysModel,
)
from calliope.tables import ModelConfig
from calliope.utils.piccolo import load_json_if_necessary


async def runway_text_to_video_inference(
    httpx_client: httpx.AsyncClient,
    text: str,
    output_video_filename: str,
    model_config: ModelConfig,
    keys: KeysModel,
    width: Optional[int] = None,
    height: Optional[int] = None,
    num_frames: Optional[int] = None,
    fps: Optional[int] = None,
) -> str:
    """
    Generates a video from a text prompt using Runway's models.
    
    Args:
        httpx_client: the async HTTP session (not used with the RunwayML client).
        text: the input text prompt.
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
    model = model_config.model

    if not keys.runway_api_key:
        raise ValueError(
            "Missing Runway authentication key. Aborting request."
        )

    # Set the API key for the Runway client
    os.environ["RUNWAYML_API_KEY"] = keys.runway_api_key

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

    # Override parameters with function arguments if provided
    if width is not None and height is not None:
        parameters["dimensions"] = f"{width}x{height}"
    if num_frames is not None:
        parameters["num_frames"] = num_frames
    if fps is not None:
        parameters["fps"] = fps

    # Get the model name from the configuration, default to gen4_turbo if not specified
    model_name = model.provider_model_name if model.provider_model_name else "gen4_turbo"
    
    # Create a RunwayML client
    client = RunwayML()

    # Parameters for text to video generation
    prompt = text
    negative_prompt = parameters.get("negative_prompt", "blurry, distorted, watermark")
    num_frames = parameters.get("num_frames", 24)
    fps = parameters.get("fps", 8)
    
    print(f"Generating video with Runway model {model_name}")
    print(f"Text prompt: {prompt}")
    print(f"Parameters: {num_frames} frames @ {fps} fps, negative_prompt: {negative_prompt}")

    try:
        # Create a new text-to-video task using the specified model
        task = client.text_to_video.create(
            model=model_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            fps=fps
        )
        task_id = task.id
        print(f"Started Runway text-to-video generation task: {task_id}")

        # Poll the task until it's complete
        max_attempts = 30  # 5 minutes max (10 seconds per attempt)
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(10)  # Wait before polling
            attempt += 1
            
            task = client.tasks.retrieve(task_id)
            status = task.status
            print(f"Task {task_id} status: {status}, attempt {attempt}/{max_attempts}")
            
            if status == 'SUCCEEDED':
                # Download the generated video
                video_url = task.output.video
                print(f"Video URL: {video_url}")
                
                async with httpx_client.stream("GET", video_url) as response:
                    response.raise_for_status()
                    async with aiofiles.open(output_video_filename, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                            
                print(f"Video saved to {output_video_filename}")
                return output_video_filename
                
            elif status == 'FAILED':
                error = task.error or "Unknown error"
                raise ValueError(f"Runway video generation failed: {error}")
                
            # Continue polling if still processing
        
        # If we get here, the generation is taking too long
        raise TimeoutError(f"Runway video generation timed out after {max_attempts * 10} seconds")
        
    except Exception as e:
        print(f"Error in Runway video generation: {str(e)}")
        raise