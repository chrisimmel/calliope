from datetime import datetime, timezone
from enum import Enum
import glob
import os
from typing import cast, List, Optional, Sequence

from calliope.models import (
    SparrowStateModel,
    StoryModel,
)
from calliope.tables import (
    SparrowState,
    Story,
)
from calliope.utils.file import (
    FileMetadata,
    ModelAndMetadata,
    get_file_metadata,
    load_json_into_pydantic_model,
)
from calliope.utils.google import (
    get_google_file,
    is_google_cloud_run_environment,
    list_google_files_with_prefix,
)


class StateType(Enum):
    SPARROW = "sparrow"
    STORY = "story"


async def get_sparrow_state(sparrow_id: str) -> SparrowState:
    """
    Retrieves the state of the given sparrow. If a stored state isn't found, creates a new one.
    """

    sparrow_state = (
        await SparrowState.objects()
        .where(SparrowState.sparrow_id == sparrow_id)
        .first()
        .run()
    )

    if not sparrow_state:
        print("Creating a new sparrow state.")
        sparrow_state = SparrowState(
            sparrow_id=sparrow_id,
            date_created=datetime.now(timezone.utc),
        )
        await sparrow_state.save().run()

    return sparrow_state


async def put_sparrow_state(state: SparrowState) -> None:
    """
    Stores the given sparrow state.
    """
    await state.save().run()


def list_legacy_sparrow_states() -> Sequence[ModelAndMetadata]:
    """
    Lists all Sparrow states.
    """
    filenames_and_dates: List[FileMetadata] = []

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("state/sparrow")
        for blob_name in blob_names:
            local_filename = blob_name
            filenames_and_dates.append(get_google_file(blob_name, local_filename))
    else:
        dir_path = r"state/sparrow*"
        state_filenames = glob.glob(dir_path)
        for filename in state_filenames:
            filenames_and_dates.append(get_file_metadata(filename))

    return [
        ModelAndMetadata(
            load_json_into_pydantic_model(file_metadata.filename, SparrowStateModel),
            file_metadata,
        )
        for file_metadata in filenames_and_dates
    ]


def list_legacy_stories() -> Sequence[ModelAndMetadata]:
    """
    Lists all stories.
    """
    filenames_and_dates: List[FileMetadata] = []

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("state/story")
        for blob_name in blob_names:
            local_filename = blob_name
            filenames_and_dates.append(get_google_file(blob_name, local_filename))
    else:
        dir_path = r"state/story*"
        story_filenames = glob.glob(dir_path)
        for filename in story_filenames:
            filenames_and_dates.append(get_file_metadata(filename))

    return sorted(
        [
            ModelAndMetadata(
                load_json_into_pydantic_model(file_metadata.filename, StoryModel),
                file_metadata,
            )
            for file_metadata in filenames_and_dates
        ],
        key=lambda model_and_metadata: cast(
            StoryModel, model_and_metadata.model
        ).date_updated,
        reverse=True,
    )


def get_legacy_story(story_id: str) -> Optional[StoryModel]:
    """
    Retrieves the given story.
    """
    filename = _compose_state_filename(StateType.STORY, story_id)

    folder = "state"
    local_filename = f"{folder}/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_google_file(local_filename, local_filename)
        except Exception as e:
            return None

    if not os.path.isfile(local_filename):
        return None

    story = cast(
        Optional[StoryModel], load_json_into_pydantic_model(local_filename, StoryModel)
    )

    return story


async def get_story(story_cuid: str) -> Optional[Story]:
    """
    Retrieves the given story.
    """
    return await Story.objects().where(Story.cuid == story_cuid).first().run()


async def put_story(story: Story, update_dates: bool = True) -> None:
    """
    Stores the given story state.
    """
    await story.save().run()


def _compose_state_filename(type: StateType, id: str) -> str:
    """
    Composes the filename of a sparrow or story state file.

    Args:
        type - The type of state: sparrow or story.
        id - The ID of the sparrow or story.
    """
    return f"{type.value}-{id}.state.json"
