import asyncio
from enum import Enum
import glob
import os
from typing import Any, cast, Dict, Optional, Sequence, Tuple

from piccolo.engine import engine_finder

from calliope.models import (
    ClientTypeConfigModel,
    ConfigModel,
    FramesRequestParamsModel,
    InferenceModelConfigsModel,
    KeysModel,
    load_inference_model_configs,
    SparrowConfigModel,
    SparrowStateModel,
)
from calliope.tables import (
    ClientTypeConfig,
    Image,
    SparrowConfig,
    SparrowState,
    Story,
    StoryFrame,
)
from calliope.storage.schedule import check_schedule
from calliope.storage.state_manager import (
    list_legacy_sparrow_states,
    list_legacy_stories,
)
from calliope.utils.file import (
    load_json_into_pydantic_model,
    write_pydantic_model_to_json,
)
from calliope.utils.google import (
    delete_google_file,
    get_google_file,
    is_google_cloud_run_environment,
    list_google_files_with_prefix,
    put_google_file,
)


class ConfigType(Enum):
    SPARROW = "sparrow"
    CLIENT_TYPE = "client-type"


def _compose_config_filename(config_type: ConfigType, config_id: str) -> str:
    """
    Composes the filename of a config file for a sparrow, flock, or client type.

    Args:
        config_type - The kind of configuration.
        config_id - The ID of the sparrow, flock, or client type.
    """
    return f"{config_type.value}-{config_id}.cfg.json"


def _get_config(config_type: ConfigType, config_id: str) -> Optional[ConfigModel]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    filename = _compose_config_filename(config_type, config_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    model_class = (
        SparrowConfigModel
        if config_type == ConfigType.SPARROW
        else ClientTypeConfigModel
    )
    try:
        return load_json_into_pydantic_model(local_filename, model_class)
    except Exception as e:
        print(f"Error loading configuration {local_filename}: {e}")
        return None


def _put_config(config_type: ConfigType, config: ConfigModel) -> None:
    """
    Stores the given sparrow or flock config.
    """
    filename = _compose_config_filename(config_type, config.id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(config, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, local_filename)


def _delete_config(config_type: ConfigType, config_id: str) -> None:
    filename = _compose_config_filename(config_type, config_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            delete_google_file(folder, filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        os.remove(local_filename)


def list_legacy_configs() -> Sequence[ConfigModel]:
    """
    Lists all legacy configs (ones stored as Pydantic JSON).
    """

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("config/")
        for blob_name in blob_names:
            local_filename = blob_name  # os.path.basename(blob_name)
            get_google_file("config", blob_name, local_filename)

    dir_path = r"config/*"
    config_filenames = glob.glob(dir_path)

    for fname in config_filenames:
        print(f"{fname=}")

    configs = [
        load_json_into_pydantic_model(
            config_filename,
            SparrowConfigModel
            if config_filename.startswith("config/sparrow")
            else ClientTypeConfigModel,
        )
        for config_filename in config_filenames
    ]

    return configs


async def copy_configs_to_piccolo() -> None:
    for config_model in list_legacy_configs():
        print(f"Copying model {config_model}")
        if isinstance(config_model, SparrowConfigModel):
            config = await SparrowConfig.from_pydantic(config_model)
        else:
            config = await ClientTypeConfig.from_pydantic(config_model)
        await config.save().run()


async def copy_stories_to_piccolo() -> None:
    for story_model in list_legacy_stories():
        print(f"Copying story {story_model.title}")
        story = await Story.from_pydantic(story_model)
        await story.save().run()

        for frame_number, frame_model in enumerate(story_model.frames):
            print(f"Frame {frame_number}")
            image = (
                await Image.from_pydantic(frame_model.image)
                if frame_model.image
                else None
            )
            if image:
                await image.save().run()
            source_image = (
                await Image.from_pydantic(frame_model.source_image)
                if frame_model.source_image
                else None
            )
            if source_image:
                await source_image.save().run()
            frame = await StoryFrame.from_pydantic(frame_model, story.cuid, frame_number)
            frame.image = image.id if image else None
            frame.source_image = source_image.id if source_image else None
            frame.story = story.id
            await frame.save().run()


async def copy_sparrow_states_to_piccolo() -> None:
    for sparrow_state_model in list_legacy_sparrow_states():
        print(f"Copying state for Sparrow {sparrow_state_model.sparrow_id}")
        sparrow_state = await SparrowState.from_pydantic(sparrow_state_model)
        await sparrow_state.save()


def get_legacy_sparrow_config(sparrow_or_flock_id: str) -> Optional[SparrowConfigModel]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    return cast(
        Optional[SparrowConfigModel],
        _get_config(ConfigType.SPARROW, sparrow_or_flock_id),
    )


async def get_sparrow_config(sparrow_or_flock_id: str) -> Optional[SparrowConfig]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    return (
        await SparrowConfig.objects()
        .where(SparrowConfig.client_id == sparrow_or_flock_id)
        .first()
        .run()
    )


async def put_sparrow_config(sparrow_config: SparrowConfig) -> None:
    """
    Stores the given sparrow or flock config.
    """
    await sparrow_config.save().run()


async def delete_sparrow_config(sparrow_or_flock_id: str) -> None:
    """
    Deletes the given sparrow or flock config.
    """
    await SparrowConfig.filter(client_id=sparrow_or_flock_id).delete()


def get_legacy_client_type_config(
    client_type_id: str,
) -> Optional[ClientTypeConfigModel]:
    """
    Retrieves the given client type config.
    """
    return cast(
        Optional[ClientTypeConfigModel],
        _get_config(ConfigType.CLIENT_TYPE, client_type_id),
    )


async def get_client_type_config(client_type_id: str) -> Optional[ClientTypeConfig]:
    """
    Retrieves the given client type config.
    """
    return (
        await ClientTypeConfig.objects()
        .where(ClientTypeConfig.client_id == client_type_id)
        .first()
        .run()
    )


async def put_client_type_config(client_type_config: ClientTypeConfigModel) -> None:
    """
    Stores the given client type config.
    """
    # _put_config(ConfigType.CLIENT_TYPE, client_type_config)
    config = ClientTypeConfig.from_pydantic(client_type_config)
    await config.save().run()


def delete_client_type_config(client_type_id: str) -> None:
    """
    Deletes the given client type config.
    """
    _delete_config(ConfigType.CLIENT_TYPE, client_type_id)


async def get_sparrow_story_parameters_and_keys(
    request_params: FramesRequestParamsModel, sparrow_state: SparrowStateModel
) -> Tuple[FramesRequestParamsModel, KeysModel, InferenceModelConfigsModel]:
    """
    Gets the story parameters and keys given a set of request
    parameters, taking into account the sparrow and flock
    configurations and schedules.
    """
    sparrow_or_flock_id = request_params.client_id

    sparrows_and_flocks_visited = []

    # Assemble the story parameters...
    # 1. Take as the story params the request_params furnished with the API request.
    params_dict = _get_non_default_parameters(request_params.dict())
    keys_dict = {}

    while sparrow_or_flock_id:
        # 2. Check to see whether there is a config for the given sparrow or flock ID.
        sparrow_or_flock_config = await get_sparrow_config(sparrow_or_flock_id)
        if not sparrow_or_flock_config:
            # Fall back on the default config.
            sparrow_or_flock_id = "default"
            sparrow_or_flock_config = await get_sparrow_config(sparrow_or_flock_id)

        if sparrow_or_flock_config:
            # 3. If there's a sparrow/flock config, collect its parameters and merge
            # them with those already assembled...
            sparrow_or_flock_params_dict = {}

            if sparrow_or_flock_config.parameters:
                # Does the sparrow or flock have parameters?
                sparrow_or_flock_params_dict = _get_non_default_parameters(
                    sparrow_or_flock_config.parameters.dict()
                )

            if sparrow_or_flock_config.schedule:
                # Does it have a schedule? (If so, merge the sparrow schedule with its
                # parameters, giving precedence to the schedule.)
                sparrow_or_flock_params_dict = {
                    **sparrow_or_flock_params_dict,
                    **check_schedule(sparrow_or_flock_config, sparrow_state),
                }

            if sparrow_or_flock_params_dict:
                # Merge the sparrow params with the params already assembled, giving
                # precedence to those already assembled.
                params_dict = {**sparrow_or_flock_params_dict, **params_dict}

            if sparrow_or_flock_config.keys:
                # 3.5 Merge keys similarly.
                sparrow_or_flock_keys_dict = sparrow_or_flock_config.keys.dict()
                keys_dict = {**sparrow_or_flock_keys_dict, **keys_dict}

            # 4. Take the flock ID from the parent flock.
            sparrow_or_flock_id = sparrow_or_flock_config.parent_flock_id
            if not sparrow_or_flock_id and sparrow_or_flock_config.id != "default":
                sparrow_or_flock_id = "default"

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

    # 5. Check for a configuration for the client_type.
    # Note that the client type can either be passed with the request or
    # come from a sparrow config.
    client_type = params_dict.get("client_type")
    if client_type:
        client_type_config = await get_client_type_config(client_type)
        if client_type_config:
            # 5.1. If there is one, merge it with the request parameters.
            client_type_config_dict = _get_non_default_parameters(
                client_type_config.parameters.dict()
            )
            # As with other parameter merging, parameters passed with
            # the request take precedence.
            params_dict = {**client_type_config_dict, **params_dict}

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
    for field in FramesRequestParamsModel.__fields__.values():
        value = params_dict.get(field.alias)
        if value != field.default:
            non_default_request_params[field.alias] = value

    return non_default_request_params


async def main():
    engine = engine_finder()
    await engine.start_connection_pool()

    try:
        await copy_configs_to_piccolo()
        await copy_stories_to_piccolo()
        await copy_sparrow_states_to_piccolo()
    finally:
        await engine.close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
