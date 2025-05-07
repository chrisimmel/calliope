from enum import Enum
from typing import Any, cast, Dict, List, Optional, Sequence, Tuple

from rich import print

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    StrategyConfigDescriptortModel,
)
from calliope.storage.state_manager import get_sparrow_state
from calliope.tables import (
    ClientTypeConfig,
    SparrowConfig,
    SparrowState,
)
from calliope.tables.model_config import StrategyConfig
from calliope.utils.piccolo import load_json_if_necessary


class ConfigType(Enum):
    SPARROW = "sparrow"
    CLIENT_TYPE = "client-type"


async def get_sparrow_config(sparrow_or_flock_id: str) -> Optional[SparrowConfig]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    return cast(
        Optional[SparrowConfig],
        await SparrowConfig.objects()
        .where(SparrowConfig.client_id == sparrow_or_flock_id)
        .first()
        .output(load_json=True)
        .run(),
    )


async def get_client_type_config(client_type_id: str) -> Optional[ClientTypeConfig]:
    """
    Retrieves the given client type config.
    """
    return cast(
        Optional[ClientTypeConfig],
        await ClientTypeConfig.objects()
        .where(ClientTypeConfig.client_id == client_type_id)
        .first()
        .output(load_json=True)
        .run(),
    )


async def get_sparrow_story_parameters_and_keys(
    request_params: FramesRequestParamsModel, sparrow_state: SparrowState
) -> Tuple[FramesRequestParamsModel, KeysModel, StrategyConfig]:
    """
    Gets the story parameters and keys given a set of request
    parameters, taking into account the sparrow and flock
    configurations and schedules.
    """
    sparrow_or_flock_id: Optional[str] = request_params.client_id

    sparrows_and_flocks_visited: List[str] = []

    # Assemble the story parameters...
    # 1. Take as the story params the request_params furnished with the API request.
    params_dict = _get_non_default_parameters(request_params.model_dump())
    keys_dict: Dict[str, Any] = {}

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
                    load_json_if_necessary(sparrow_or_flock_config.parameters)
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
                sparrow_or_flock_keys_dict = load_json_if_necessary(
                    sparrow_or_flock_config.keys
                )
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
                        "Flock inheritance loop: "
                        f"{','.join(new_sparrows_and_flocks_visited)}"
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
                load_json_if_necessary(client_type_config.parameters)
            )
            # As with other parameter merging, parameters passed with
            # the request take precedence.
            params_dict = {**client_type_config_dict, **params_dict}

    if not params_dict.get("strategy"):
        params_dict["strategy"] = "fern"

    strategy_config = await get_strategy_config(params_dict["strategy"])
    if strategy_config:
        strategy_params = _get_non_default_parameters(
            load_json_if_necessary(strategy_config.parameters)
        )
        params_dict = {**strategy_params, **params_dict}

    print(
        f"Merged parameters: {str({key: val for key, val in params_dict.items() if key not in ('input_image', 'input_audio')})}"
    )

    return (
        FramesRequestParamsModel(**params_dict),
        KeysModel(**keys_dict),
        strategy_config,
    )


def _get_non_default_parameters(params_dict: Dict[str, Any]) -> Dict[str, Any]:
    non_default_request_params = {}
    # Get the request parameters with non-default values.
    for field_name, field in FramesRequestParamsModel.model_fields.items():
        value = params_dict.get(field_name)
        if value != field.default:
            non_default_request_params[field_name] = value

    return non_default_request_params


async def get_strategy_config(strategy_config_slug: str) -> StrategyConfig:
    """
    Retrieves the given StrategyConfig, if any.
    Also loads referenced model configs, models, and prompt templates.
    """
    print(f"get_strategy_config({strategy_config_slug})")
    strategy_config: Optional[StrategyConfig] = cast(
        Optional[StrategyConfig],
        await StrategyConfig.objects(
            StrategyConfig.text_to_image_model_config.all_related(),
            StrategyConfig.text_to_text_model_config.all_related(),
        )
        .where(StrategyConfig.slug == strategy_config_slug)
        .first()
        .output(load_json=True)
        .run(),
    )

    if not strategy_config:
        print(
            f"There isn't a strategy_config called {strategy_config_slug}. "
            "Looking for a default strategy_config for strategy {strategy_config_slug}."
        )
        # If StrategyConfig of the given slug is not found, then look for one that
        # references a strategy of that name and for which is_default is True.
        strategy_config = cast(
            StrategyConfig,
            await StrategyConfig.objects(
                StrategyConfig.text_to_image_model_config.all_related(),
                StrategyConfig.text_to_text_model_config.all_related(),
            )
            .where(
                (StrategyConfig.strategy_name == strategy_config_slug)
                & (StrategyConfig.is_default == True)  # noqa: E712
            )
            .first()
            .output(load_json=True)
            .run(),
        )
        print(f"Found {strategy_config.slug if strategy_config else None}.")

    if not strategy_config:
        raise ValueError(f"No strategy config found for {strategy_config_slug}.")

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


async def get_strategy_config_descriptors(
    client_id: Optional[str],
) -> Sequence[StrategyConfigDescriptortModel]:
    if client_id:
        frames_request = FramesRequestParamsModel(client_id=client_id)
        sparrow_state = await get_sparrow_state(client_id)

        _, _, default_strategy_config = await get_sparrow_story_parameters_and_keys(
            frames_request, sparrow_state
        )
    else:
        default_strategy_config = None

    strategy_configs: Sequence[StrategyConfig] = await StrategyConfig.objects(
        StrategyConfig.text_to_image_model_config.all_related(),
        StrategyConfig.text_to_text_model_config.all_related(),
    ).run()

    descriptors = [
        StrategyConfigDescriptortModel(
            slug=strategy_config.slug,
            strategy_name=strategy_config.strategy_name,
            description=strategy_config.description,
            is_default_for_client=default_strategy_config is not None
            and strategy_config.slug == default_strategy_config.slug,
            is_experimental=strategy_config.is_experimental,
        )
        for strategy_config in strategy_configs
    ]

    return descriptors
