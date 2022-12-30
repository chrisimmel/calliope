import os
from typing import Any, cast, Dict, Optional, Tuple

from calliope.models import (
    FramesRequestParamsModel,
    InferenceModelConfigsModel,
    KeysModel,
    load_inference_model_configs,
    SparrowConfigModel,
    StoryParamsModel,
)
from calliope.utils.file import (
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


def get_sparrow_story_parameters_and_keys(
    request_params: FramesRequestParamsModel,
) -> Tuple[FramesRequestParamsModel, KeysModel, InferenceModelConfigsModel]:
    """
    Gets the story parameters and keys given a set of request
    parameters, taking into account the sparrow and flock
    configurations.
    """
    sparrow_or_flock_id = request_params.client_id

    sparrows_and_flocks_visited = []

    # Assemble the story parameters...
    # 1. Take as the story params the request_params furnished with the API request.
    params_dict = request_params.dict()
    keys_dict = {}

    while sparrow_or_flock_id:
        # 2. Check to see whether there is a config for the given sparrow or flock ID.
        sparrow_or_flock_config = get_sparrow_config(sparrow_or_flock_id)
        if sparrow_or_flock_config:
            if sparrow_or_flock_config.parameters:
                # 3. If so, merge the sparrow/flock config with the story params. The
                # story params take precedence.
                sparrow_or_flock_params_dict = _get_non_default_parameters(
                    sparrow_or_flock_config.parameters.dict()
                )
                params_dict = {**sparrow_or_flock_params_dict, **params_dict}

            if sparrow_or_flock_config.keys:
                # 3.5 Merge keys similarly.
                sparrow_or_flock_keys_dict = sparrow_or_flock_config.keys.dict()
                keys_dict = {**sparrow_or_flock_keys_dict, **keys_dict}

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

    inference_model_configs = _load_inference_model_configs(params_dict)

    return (
        FramesRequestParamsModel(**params_dict),
        KeysModel(**keys_dict),
        inference_model_configs,
    )


def _load_inference_model_configs(
    request_params_dict: Dict[str, Any]
) -> InferenceModelConfigsModel:
    config_names = {
        key: name
        for key, name in request_params_dict.items()
        if key
        in (
            "image_to_text_model_config",
            "text_to_image_model_config",
            "text_to_text_model_config",
            "audio_to_text_model_config",
        )
        and name
    }
    return load_inference_model_configs(**config_names)


def _get_non_default_parameters(params_dict: Dict[str, Any]) -> Dict[str, Any]:
    non_default_request_params = {}
    # Get the request parameters with non-default values.
    for field in StoryParamsModel.__fields__.values():
        value = params_dict.get(field.alias)
        if value != field.default:
            non_default_request_params[field.alias] = value

    return non_default_request_params
