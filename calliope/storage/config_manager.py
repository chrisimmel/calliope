import os
from typing import cast, Optional

from calliope.models import (
    BaseConfigModel,
    ConfigType,
    FlockConfigModel,
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


def get_sparrow_config(sparrow_id: str) -> Optional[SparrowConfigModel]:
    """
    Retrieves a sparrow config.
    """
    return cast(Optional[SparrowConfigModel], get_config(ConfigType.SPARROW, sparrow_id))


def put_sparrow_config(sparrow_config: SparrowConfigModel):
    """
    Stores a sparrow config.
    """
    put_config(sparrow_config)


def get_flock_config(flock_id: str) -> Optional[FlockConfigModel]:
    """
    Retrieves a flock config.
    """
    return cast(Optional[FlockConfigModel], get_config(ConfigType.FLOCK, flock_id))


def put_flock_config(flock_config: FlockConfigModel):
    """
    Stores a flock config.
    """
    put_config(flock_config)


def compose_config_filename(config_type: ConfigType, client_id: str) -> str:
    """
    Composes the filename of a config file.

    Args:
        config_type - The type of configuration (ConfigType.SPARROW or
            ConfigType.FLOCK).
        client_id - The ID of the sparrow or flock.
    """
    return f"{config_type.value}-{client_id}.cfg"


def get_config(config_type: ConfigType, client_id: str) -> Optional[BaseConfigModel]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    filename = compose_config_filename(config_type, client_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    model = FlockConfigModel if config_type == ConfigType.FLOCK else SparrowConfigModel
    return load_json_into_pydantic_model(local_filename, model)


def put_config(config: BaseConfigModel) -> Optional[BaseConfigModel]:
    """
    Stores the given config.
    """
    if config._config_type == ConfigType.SPARROW:
        sparrow_config = cast(SparrowConfigModel, config)
        client_id = sparrow_config.sparrow_id
    else:
        flock_config = cast(FlockConfigModel, config)
        client_id = flock_config.flock_id

    filename = compose_config_filename(config._config_type, client_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(config, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, filename)


def get_sparrow_story_parameters(
    request_params: FramesRequestParamsModel,
) -> FramesRequestParamsModel:
    """
    Gets the StoryParamsModel for a given set of request parameters,
    taking into account the sparrow and flock configurations.
    Also decodes and stores the b64-encoded file parameters.
    """
    sparrow_id = request_params.client_id
    sparrow_config = get_sparrow_config(sparrow_id)
    flock_id = sparrow_config.flock_id if sparrow_config else None
    flock_config = get_flock_config(flock_id) if flock_id else None

    # Begin with the default parameters from the model.
    params_dict = FramesRequestParamsModel(client_id=sparrow_id).dict()

    if flock_config and flock_config.parameters:
        # Overlay the parameters from the flock config.
        params_dict = {**params_dict, **flock_config.parameters.dict()}

    if sparrow_config and sparrow_config.parameters:
        # Overlay the parameters from the sparrow config.
        params_dict = {**params_dict, **sparrow_config.parameters.dict()}

    request_params = request_params.dict()
    non_default_request_params = {}
    # Get the request parameters with non-default values.
    for field in StoryParamsModel.__fields__.values():
        value = request_params.get(field.alias)
        if value != field.default:
            non_default_request_params[field.alias] = value

    if non_default_request_params:
        # Overlay the non-default request parameters.
        params_dict = {**params_dict, **non_default_request_params}

    story_strategy_params = FramesRequestParamsModel(**params_dict)

    # Decode b64-encoded file inputs and store to files.
    if story_strategy_params.input_image:
        input_image_filename = create_unique_filename(
            "input",
            request_params.client_id,
            "jpg",  # TODO: Handle non-jpeg image input.
        )
        decode_b64_to_file(story_strategy_params.input_image, input_image_filename)
        story_strategy_params.input_image_filename = input_image_filename

    if story_strategy_params.input_audio:
        input_audio_filename = create_unique_filename(
            "input", request_params.client_id, "wav"
        )
        decode_b64_to_file(story_strategy_params.input_audio, input_audio_filename)
        story_strategy_params.input_audio_filename = input_audio_filename

    return story_strategy_params
