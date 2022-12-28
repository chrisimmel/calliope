from enum import Enum
import os
from typing import cast, Optional

from calliope.models import (
    SparrowStateModel,
    StoryModel,
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


class StateType(Enum):
    SPARROW = "sparrow"
    STORY = "story"


def get_sparrow_state(sparrow_id: str) -> SparrowStateModel:
    """
    Retrieves the state of the given sparrow. If a stored state isn't found, creates a new one.
    """
    filename = _compose_state_filename(StateType.SPARROW, sparrow_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            pass

    print(f"Looking for {local_filename}.")
    if os.path.isfile(local_filename):
        print(f"Preparing to load {local_filename}.")
        sparrow_state = cast(
            Optional[SparrowStateModel],
            load_json_into_pydantic_model(local_filename, SparrowStateModel),
        )
        print(f"{sparrow_state=}")
    else:
        sparrow_state = None

    if not sparrow_state:
        print("Creating a new sparrow state.")
        sparrow_state = SparrowStateModel(sparrow_id=sparrow_id)
    return sparrow_state


def put_sparrow_state(state: SparrowStateModel) -> None:
    """
    Stores the given sparrow state.
    """
    sparrow_id = state.sparrow_id

    filename = _compose_state_filename(StateType.SPARROW, sparrow_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(state, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, filename)


def get_story(story_id: str) -> Optional[StoryModel]:
    """
    Retrieves the given story.
    """
    filename = _compose_state_filename(StateType.STORY, story_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(folder, filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    return cast(
        Optional[StoryModel], load_json_into_pydantic_model(local_filename, StoryModel)
    )


def put_story(story: StoryModel) -> None:
    """
    Stores the given story state.
    """
    story_id = story.story_id

    filename = _compose_state_filename(StateType.STORY, story_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    write_pydantic_model_to_json(story, local_filename)

    if is_google_cloud_run_environment():
        put_google_file(folder, filename)


def _compose_state_filename(type: StateType, id: str) -> str:
    """
    Composes the filename of a sparrow or story state file.

    Args:
        type - The type of state: sparrow or story.
        id - The ID of the sparrow or story.
    """
    return f"{type.value}-{id}.state.json"
