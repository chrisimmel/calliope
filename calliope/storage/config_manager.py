import os
from typing import Any, cast, Dict, Optional

from calliope.models import (
    FramesRequestParamsModel,
    SparrowConfigModel,
    StoryParamsModel,
)
from calliope.utils.file import (
    create_unique_filename,
    decode_b64_to_file,
    load_json_into_pydantic_model,
    write_pydantic_model_to_json,
)
from calliope.utils.google import (
    get_google_file,
    is_google_cloud_run_environment,
    put_google_file,
)


def _compose_config_filename(sparrow_or_flock_id: str) -> str:
    """
    Composes the filename of a sparrow or flock config file.

    Args:
        sparrow_or_flock_id - The ID of the sparrow or flock.
    """
    return f"sparrow-{sparrow_or_flock_id}.cfg.json"


def get_sparrow_config(sparrow_or_flock_id: str) -> Optional[SparrowConfigModel]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    filename = _compose_config_filename(sparrow_or_flock_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    try:
        return load_json_into_pydantic_model(local_filename, SparrowConfigModel)
    except Exception as e:
        print(f"Error loading Sparrow config: {e}")
        return None


def put_sparrow_config(sparrow_config: SparrowConfigModel) -> None:
    """
    Stores the given sparrow or flock config.
    """
    sparrow_or_flock_id = sparrow_config.id

    filename = _compose_config_filename(sparrow_or_flock_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(sparrow_config, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, local_filename)


def get_sparrow_story_parameters(
    request_params: FramesRequestParamsModel,
) -> FramesRequestParamsModel:
    """
    Gets the StoryParamsModel for a given set of request parameters,
    taking into account the sparrow and flock configurations.
    Also decodes and stores the b64-encoded file parameters.
    """
    return _apply_sparrow_config_inheritance(request_params)


def _apply_sparrow_config_inheritance(
    request_params: FramesRequestParamsModel,
) -> FramesRequestParamsModel:
    sparrow_or_flock_id = request_params.client_id

    sparrows_and_flocks_visited = []

    # Assemble the story parameters...
    # 1. Take as the story params the request_params furnished with the API request.
    params_dict = request_params.dict()
    while sparrow_or_flock_id:
        # 2. Check to see whether there is a config for the given sparrow or flock ID.
        sparrow_or_flock_config = get_sparrow_config(sparrow_or_flock_id)
        if sparrow_or_flock_config:
            if sparrow_or_flock_config.parameters:
                sparrow_or_flock_params_dict = _get_non_default_parameters(
                    sparrow_or_flock_config.parameters.dict()
                )
                # 3. If so, merge the sparrow/flock config with the story params. The
                # story params take precedence.
                params_dict = {**sparrow_or_flock_params_dict, **params_dict}

            # 4. Take the flock ID from the sparrow/flock config.
            sparrow_or_flock_id = sparrow_or_flock_config.parent_flock_id

            if sparrow_or_flock_id:
                # Prepare to inherit from a parent flock.
                new_sparrows_and_flocks_visited = sparrows_and_flocks_visited + [
                    sparrow_or_flock_id
                ]
                # Avoid inheritance loops.
                if sparrow_or_flock_id in sparrows_and_flocks_visited:
                    raise ValueError(
                        f"Flock inheritance loop: {','.join(new_sparrows_and_flocks_visited)}"
                    )
                sparrows_and_flocks_visited = new_sparrows_and_flocks_visited
        else:
            # If there was no config for that sparrow or flock, we're done.
            sparrow_or_flock_id = None

    return FramesRequestParamsModel(**params_dict)


def _get_non_default_parameters(params_dict: Dict[str, Any]) -> Dict[str, Any]:
    non_default_request_params = {}
    # Get the request parameters with non-default values.
    for field in StoryParamsModel.__fields__.values():
        value = params_dict.get(field.alias)
        if value != field.default:
            non_default_request_params[field.alias] = value

    return non_default_request_params
