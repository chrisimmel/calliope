import asyncio
import datetime
from enum import Enum
import glob
import os
from typing import Any, cast, Dict, List, Optional, Sequence, Tuple

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
    StoryModel,
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
    ModelAndMetadata,
    get_file_metadata,
    load_json_into_pydantic_model,
)
from calliope.utils.google import (
    FileMetadata,
    delete_google_file,
    get_google_file,
    get_google_file_metadata,
    is_google_cloud_run_environment,
    list_google_files_with_prefix,
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


def list_legacy_configs() -> Sequence[ModelAndMetadata]:
    """
    Lists all legacy configs (ones stored as Pydantic JSON).
    """

    filenames_and_dates: List[FileMetadata] = []

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("config/")
        for blob_name in blob_names:
            local_filename = blob_name
            filenames_and_dates.append(get_google_file(blob_name, local_filename))
    else:
        dir_path = r"config/*"
        config_filenames = glob.glob(dir_path)
        for filename in config_filenames:
            filenames_and_dates.append(get_file_metadata(filename))

    return [
        ModelAndMetadata(
            load_json_into_pydantic_model(
                filename_and_dates.filename,
                SparrowConfigModel
                if filename_and_dates.filename.startswith("config/sparrow")
                else ClientTypeConfigModel,
            ),
            filename_and_dates,
        )
        for filename_and_dates in filenames_and_dates
    ]


async def copy_configs_to_piccolo() -> None:
    legacy_configs = list_legacy_configs()

    for model_and_metadata in legacy_configs:
        print(f"Copying model {model_and_metadata.model.id}")
        if isinstance(model_and_metadata.model, SparrowConfigModel):
            config = await SparrowConfig.from_pydantic(
                model_and_metadata.model, model_and_metadata.metadata
            )
        else:
            config = await ClientTypeConfig.from_pydantic(
                model_and_metadata.model, model_and_metadata.metadata
            )
        await config.save().run()

    for model_and_metadata in legacy_configs:
        if isinstance(model_and_metadata.model, SparrowConfigModel):
            print(f"Connecting flocks for {model_and_metadata.model.id}")
            config = await SparrowConfig.from_pydantic(
                model_and_metadata.model, model_and_metadata.metadata
            )
            await config.save().run()


def get_local_or_cloud_file_metadata(filename: str) -> FileMetadata:
    if is_google_cloud_run_environment():
        return get_google_file_metadata(filename)
    else:
        return get_file_metadata(filename)


async def copy_stories_to_piccolo() -> None:
    legacy_stories = list_legacy_stories()

    for model_and_metadata in legacy_stories:
        story_model = cast(StoryModel, model_and_metadata.model)
        file_metadata = model_and_metadata.metadata

        print(f"Copying story {story_model.title}")
        story = await Story.from_pydantic(story_model, file_metadata)
        await story.save().run()

        for frame_number, frame_model in enumerate(story_model.frames):
            print(f"Frame {frame_number}")
            date_created = None
            date_updated = None

            if frame_model.image:
                try:
                    image_file_metadata = get_local_or_cloud_file_metadata(
                        frame_model.image.url
                    )
                    image = await Image.from_pydantic(
                        frame_model.image, image_file_metadata
                    )
                    await image.save().run()

                    date_created = image_file_metadata.date_created
                    date_updated = image_file_metadata.date_updated
                except Exception as e:
                    print(f"Error getting image file {frame_model.image.url}: {e}")
                    image = None
            else:
                image = None

            if frame_model.source_image:
                try:
                    source_image_file_metadata = get_local_or_cloud_file_metadata(
                        frame_model.source_image.url
                    )
                    source_image = await Image.from_pydantic(
                        frame_model.source_image, source_image_file_metadata
                    )
                    await source_image.save().run()

                    if not date_created:
                        date_created = image_file_metadata.date_created
                    if not date_updated:
                        date_updated = image_file_metadata.date_updated
                except Exception as e:
                    print(
                        f"Error getting image file {frame_model.source_image.url}: {e}"
                    )
                    source_image = None
            else:
                source_image = None

            if not date_created:
                date_created = file_metadata.date_created
            if not date_updated:
                date_updated = file_metadata.date_updated

            frame_file_metadata = FileMetadata(
                None,
                date_created,
                date_updated,
            )

            frame = await StoryFrame.from_pydantic(
                frame_model, frame_file_metadata, story.cuid, frame_number
            )
            frame.image = image.id if image else None
            frame.source_image = source_image.id if source_image else None
            frame.story = story.id
            await frame.save().run()


async def copy_sparrow_states_to_piccolo() -> None:
    legacy_sparrow_states = list_legacy_sparrow_states()

    for model_and_metadata in legacy_sparrow_states:
        sparrow_state_model = cast(SparrowStateModel, model_and_metadata.model)
        file_metadata = model_and_metadata.metadata

        print(f"Copying state for Sparrow {sparrow_state_model.sparrow_id}")
        sparrow_state = await SparrowState.from_pydantic(
            sparrow_state_model, file_metadata
        )
        await sparrow_state.save()


async def get_sparrow_config(sparrow_or_flock_id: str) -> Optional[SparrowConfig]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    return (
        await SparrowConfig.objects()
        .where(SparrowConfig.client_id == sparrow_or_flock_id)
        .first()
        .output(load_json=True)
        .run()
    )


async def put_sparrow_config(sparrow_config_model: SparrowConfigModel) -> None:
    """
    Stores the given sparrow or flock config.
    """
    config = SparrowConfig.from_pydantic(sparrow_config_model)
    await config.save().run()


async def delete_sparrow_config(sparrow_or_flock_id: str) -> None:
    """
    Deletes the given sparrow or flock config.
    """
    await SparrowConfig.filter(client_id=sparrow_or_flock_id).delete()


async def get_client_type_config(client_type_id: str) -> Optional[ClientTypeConfig]:
    """
    Retrieves the given client type config.
    """
    return (
        await ClientTypeConfig.objects()
        .where(ClientTypeConfig.client_id == client_type_id)
        .first()
        .output(load_json=True)
        .run()
    )


async def put_client_type_config(client_type_config: ClientTypeConfig) -> None:
    """
    Stores the given client type config.
    """
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
                    sparrow_or_flock_config.parameters
                )

            """
            if sparrow_or_flock_config.schedule:
                # Does it have a schedule? (If so, merge the sparrow schedule with its
                # parameters, giving precedence to the schedule.)
                sparrow_or_flock_params_dict = {
                    **sparrow_or_flock_params_dict,
                    **check_schedule(sparrow_or_flock_config, sparrow_state),
                }
            """

            if sparrow_or_flock_params_dict:
                # Merge the sparrow params with the params already assembled, giving
                # precedence to those already assembled.
                params_dict = {**sparrow_or_flock_params_dict, **params_dict}

            if sparrow_or_flock_config.keys:
                # 3.5 Merge keys similarly.
                sparrow_or_flock_keys_dict = sparrow_or_flock_config.keys
                keys_dict = {**sparrow_or_flock_keys_dict, **keys_dict}

            # 4. Take the flock ID from the parent flock.
            sparrow_or_flock_id = sparrow_or_flock_config.parent_flock_client_id
            if (
                not sparrow_or_flock_id
                and sparrow_or_flock_config.client_id != "default"
            ):
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
                client_type_config.parameters  # .dict()
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
