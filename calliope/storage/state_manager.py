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
    Retrieves the state of the given sparrow. If a stored state isn't found, creates a
    new one.

    Uses a race-condition-safe pattern to handle concurrent requests.
    """

    # First, try to fetch the existing sparrow state
    sparrow_state = (
        await SparrowState.objects(SparrowState.current_story)
        .where(SparrowState.sparrow_id == sparrow_id)
        .first()
        .run()
    )

    # If it exists, use it
    if sparrow_state:
        if sparrow_state.current_story and not sparrow_state.current_story.id:
            sparrow_state.current_story = None
        return sparrow_state

    # If no state exists, create a new one using a race-condition-safe pattern
    try:
        # Prepare a new state object
        print(f"Attempting to create a new sparrow state for {sparrow_id}.")
        sparrow_state = SparrowState(
            sparrow_id=sparrow_id,
            date_created=datetime.now(timezone.utc),
        )

        # Try to save it
        await put_sparrow_state(sparrow_state)
        print(f"Successfully created new sparrow state for {sparrow_id}.")
        return sparrow_state

    except Exception as e:
        # If we get an error (likely due to a unique constraint violation from a concurrent request),
        # try fetching again as it was likely created by another process
        print(f"Exception creating sparrow state: {e}. Retrying fetch.")
        sparrow_state = (
            await SparrowState.objects(SparrowState.current_story)
            .where(SparrowState.sparrow_id == sparrow_id)
            .first()
            .run()
        )

        if sparrow_state:
            # We successfully retrieved the state that was created by another process
            if sparrow_state.current_story and not sparrow_state.current_story.id:
                sparrow_state.current_story = None
            return sparrow_state

        # If we still don't have a state, there's a more serious issue
        raise Exception(f"Failed to create or retrieve sparrow state for {sparrow_id} after retry.")


async def put_sparrow_state(state: SparrowState) -> None:
    """
    Stores the given sparrow state.
    """
    state.date_updated = datetime.now(timezone.utc)
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
            str, cast(
                StoryModel, model_and_metadata.model
            ).date_updated
        ),
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
        except Exception:
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
    # TODO: Stop explicitly setting date_updated once possible.
    story.date_updated = datetime.now(timezone.utc)
    await story.save().run()


async def get_stories_by_client(client_id: str) -> Sequence[Story]:
    """
    Retrieves all stories attributed to the given client.
    """
    return await Story.objects(Story.thumbnail_image).where(
        Story.created_for_sparrow_id == client_id
    ).order_by(
        Story.date_updated, ascending=False
    ).run()


def _compose_state_filename(type: StateType, id: str) -> str:
    """
    Composes the filename of a sparrow or story state file.

    Args:
        type - The type of state: sparrow or story.
        id - The ID of the sparrow or story.
    """
    return f"{type.value}-{id}.state.json"
