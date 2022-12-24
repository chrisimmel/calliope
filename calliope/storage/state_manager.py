import os
from typing import cast, Optional

from calliope.models import (
    SparrowStateModel,
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


def put_sparrow_state(state: SparrowStateModel) -> None:
    """
    Stores the given sparrow state.
    """
    sparrow_id = state.sparrow_id

    filename = _compose_state_filename(sparrow_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(state, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, filename)


def get_sparrow_state(sparrow_id: str) -> Optional[SparrowStateModel]:
    """
    Retrieves the config for the given sparrow or flock.
    """
    filename = _compose_state_filename(sparrow_id)

    folder = "config"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    model = SparrowStateModel
    return load_json_into_pydantic_model(local_filename, model)


def _compose_state_filename(sparrow_or_flock_id: str) -> str:
    """
    Composes the filename of a sparrow or flock config file.

    Args:
        sparrow_or_flock_id - The ID of the sparrow or flock.
    """
    return f"sparrow-{sparrow_or_flock_id}.state"
