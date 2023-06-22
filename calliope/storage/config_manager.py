import asyncio
from datetime import datetime, timezone
from enum import Enum
import json
import os
from typing import Any, Dict, Optional, Tuple, Union


from calliope.models import (
    FramesRequestParamsModel,
    InferenceModelConfigsModel,
    KeysModel,
    load_model_configs,
    SparrowConfigModel,
    SparrowStateModel,
)
from calliope.tables import (
    ClientTypeConfig,
    SparrowConfig,
)
from calliope.tables.model_config import ModelConfig, StrategyConfig
from calliope.utils.google import (
    delete_google_file,
    is_google_cloud_run_environment,
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
    config.date_updated = datetime.now(timezone.utc)
    await config.save().run()


def delete_client_type_config(client_type_id: str) -> None:
    """
    Deletes the given client type config.
    """
    _delete_config(ConfigType.CLIENT_TYPE, client_type_id)


async def get_sparrow_story_parameters_and_keys(
    request_params: FramesRequestParamsModel, sparrow_state: SparrowStateModel
) -> Tuple[FramesRequestParamsModel, KeysModel]:
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

    if not params_dict.get("strategy"):
        params_dict["strategy"] = "continuous-v1"

    # TODO: Either reconcile parameters coming from the strategy_config with the rest
    # of the params hierarchy, or remove them from the model.
    strategy_config = await get_strategy_config(params_dict["strategy"])

    return (
        FramesRequestParamsModel(**params_dict),
        KeysModel(**keys_dict),
        strategy_config,
    )


def _get_non_default_parameters(params_dict: Dict[str, Any]) -> Dict[str, Any]:
    non_default_request_params = {}
    # Get the request parameters with non-default values.
    for field in FramesRequestParamsModel.__fields__.values():
        value = params_dict.get(field.alias)
        if value != field.default:
            non_default_request_params[field.alias] = value

    return non_default_request_params


def load_json_if_necessary(json_field: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(json_field, str):
        return json.loads(json_field)
    else:
        return json_field


async def get_strategy_config(strategy_config_slug: str) -> Optional[StrategyConfig]:
    """
    Retrieves the given StrategyConfig, if any.
    Also loads referenced model configs, models, and prompt templates.
    """
    print(f"get_strategy_config({strategy_config_slug})")
    strategy_config = (
        await StrategyConfig.objects(
            StrategyConfig.text_to_image_model_config.all_related(),
            StrategyConfig.text_to_text_model_config.all_related(),
        )
        .where(StrategyConfig.slug == strategy_config_slug)
        .first()
        .output(load_json=True)
        .run()
    )

    if not strategy_config:
        print(
            f"There isn't a strategy_config called {strategy_config_slug}. Looking for a default strategy_config for strategy {strategy_config_slug}."
        )
        # If StrategyConfig of the given slug is not found, then look for one that references
        # a strategy of that name and for which is_default is True.
        strategy_config = (
            await StrategyConfig.objects(
                StrategyConfig.text_to_image_model_config.all_related(),
                StrategyConfig.text_to_text_model_config.all_related(),
            )
            .where(
                (StrategyConfig.strategy_name == strategy_config_slug)
                & (StrategyConfig.is_default == True)
            )
            .first()
            .output(load_json=True)
            .run()
        )
        print(f"Found {strategy_config.slug if strategy_config else None}.")

    if strategy_config:
        if strategy_config.text_to_text_model_config:
            strategy_config.text_to_text_model_config.model_parameters = (
                load_json_if_necessary(
                    strategy_config.text_to_text_model_config.model_parameters
                )
            )
            if strategy_config.text_to_text_model_config.model:
                strategy_config.text_to_text_model_config.model.model_parameters = (
                    load_json_if_necessary(
                        strategy_config.text_to_text_model_config.model.model_parameters
                    )
                )

        if strategy_config.text_to_image_model_config:
            strategy_config.text_to_image_model_config.model_parameters = (
                load_json_if_necessary(
                    strategy_config.text_to_image_model_config.model_parameters
                )
            )
            if strategy_config.text_to_image_model_config.model:
                strategy_config.text_to_image_model_config.model.model_parameters = (
                    load_json_if_necessary(
                        strategy_config.text_to_image_model_config.model.model_parameters
                    )
                )

    return strategy_config
