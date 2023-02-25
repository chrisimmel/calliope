import datetime
from enum import Enum
import glob
import os
from typing import cast, Optional, Sequence

from calliope.models import (
    SparrowStateModel,
    StoryModel,
)
from calliope.utils.file import (
    get_base_filename,
    load_json_into_pydantic_model,
    write_pydantic_model_to_json,
)
from calliope.utils.google import (
    get_google_file,
    get_google_file_dates,
    is_google_cloud_run_environment,
    list_google_files_with_prefix,
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


def list_legacy_stories() -> Sequence[StoryModel]:
    """
    Lists all stories.
    """

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("state/story")
        for blob_name in blob_names:
            local_filename = blob_name  # os.path.basename(blob_name)
            get_google_file("state", blob_name, local_filename)

    dir_path = r"state/story*"
    story_filenames = glob.glob(dir_path)

    stories = [
        load_json_into_pydantic_model(story_filename, StoryModel)
        for story_filename in story_filenames
    ]
    # Force full reload of each story in order to default dates properly.
    stories = [get_story(story.story_id) for story in stories]

    return sorted(stories, key=lambda story: story.date_updated, reverse=True)


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

    story = cast(
        Optional[StoryModel], load_json_into_pydantic_model(local_filename, StoryModel)
    )

    if not story.date_created or not story.date_updated:
        # TODO: Remove this as soon as set for all.
        # Handle legacy models with no date_created/date_updated.
        if is_google_cloud_run_environment():
            creation_datetime, updated_datetime = get_google_file_dates(
                "state", filename
            )
        else:
            # Get the file creation timestamp as a float, seconds since epoch.
            creation_time = os.path.getctime(local_filename)
            # Convert to a datetime.
            creation_datetime = datetime.datetime.fromtimestamp(creation_time)

            # Get the file modification timestamp as a float, seconds since epoch.
            updated_time = os.path.getmtime(local_filename)
            # Convert to a datetime.
            updated_datetime = datetime.datetime.fromtimestamp(updated_time)

        story.date_created = str(creation_datetime)
        story.date_updated = str(updated_datetime)
        put_story(story, update_dates=False)

    return story


def put_story(story: StoryModel, update_dates: bool = True) -> None:
    """
    Stores the given story state.
    """
    story_id = story.story_id

    if update_dates:
        now = str(datetime.datetime.utcnow())
        story.date_updated = now
        if not story.date_created:
            story.date_created = story.date_updated

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
