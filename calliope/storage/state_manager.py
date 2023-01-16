from enum import Enum
import glob
import os
from typing import cast, Optional, Sequence

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

    if os.path.isfile(local_filename):
        try:
            sparrow_state = cast(
                SparrowStateModel,
                load_json_into_pydantic_model(local_filename, SparrowStateModel),
            )
        except Exception as e:
            print(f"Error loading Sparrow state: {e}")
            sparrow_state = None
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
        put_google_file(folder, local_filename)


def list_stories() -> Sequence[StoryModel]:
    """
    Lists all stories.
    """
    dir_path = r"state/story*"
    story_filenames = glob.glob(dir_path)
    # TODO: Gcloud case.
    # https://cloud.google.com/storage/docs/listing-objects#storage-list-objects-python

    stories = [
        load_json_into_pydantic_model(story_filename, StoryModel)
        for story_filename in story_filenames
    ]

    return stories


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
        put_google_file(folder, local_filename)


def _compose_state_filename(type: StateType, id: str) -> str:
    """
    Composes the filename of a sparrow or story state file.

    Args:
        type - The type of state: sparrow or story.
        id - The ID of the sparrow or story.
    """
    return f"{type.value}-{id}.state.json"
