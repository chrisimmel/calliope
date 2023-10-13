import asyncio
import glob
from typing import cast, List, Sequence

from fastapi import Request
from piccolo.engine import engine_finder
from piccolo.table import Table
from pydantic import BaseModel

from calliope.models import (
    ClientTypeConfigModel,
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
    get_google_file,
    get_google_file_metadata,
    is_google_cloud_run_environment,
    list_google_files_with_prefix,
)


# Pydantic model for form
class MigrateFromPydanticFormModel(BaseModel):
    comment: str


# Migrate action handler
async def migrate_from_pydantic_endpoint(
    request: Request, data: MigrateFromPydanticFormModel
) -> str:
    await main()
    return "Data migrated"


def list_legacy_configs() -> Sequence[ModelAndMetadata]:
    """
    Lists all legacy configs (ones stored as Pydantic JSON).
    """

    filenames_and_dates: List[FileMetadata] = []

    if is_google_cloud_run_environment():
        blob_names = list_google_files_with_prefix("config/")
        for blob_name in blob_names:
            if blob_name != "config/":
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
        print(
            f"Copying model {model_and_metadata.model.id}"  # type: ignore[attr-defined]
        )
        if isinstance(model_and_metadata.model, SparrowConfigModel):
            config: Table = await SparrowConfig.from_pydantic(
                model_and_metadata.model, model_and_metadata.metadata
            )
        elif isinstance(model_and_metadata.model, ClientTypeConfigModel):
            config = await ClientTypeConfig.from_pydantic(
                model_and_metadata.model, model_and_metadata.metadata
            )
        else:
            raise ValueError(f"Invalid model type for: {model_and_metadata.model}")

        await config.save().run()

    for model_and_metadata in legacy_configs:
        if isinstance(model_and_metadata.model, SparrowConfigModel):
            print(
                "Connecting flocks for "
                f"{model_and_metadata.model.id}"  # type: ignore[attr-defined]
            )
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

    # await Story.delete(force=True).run()
    # await StoryFrame.delete(force=True).run()
    # await Image.delete(force=True).run()

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

            if frame_model.image and frame_model.image.url:
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

            if frame_model.source_image and frame_model.source_image.url:
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
                "",  # This doesn't represent a real file.
                date_created,
                date_updated,
            )

            frame = await StoryFrame.from_pydantic(
                frame_model, frame_file_metadata, story.cuid, frame_number
            )
            frame.image = image.id if image else None  # type: ignore[attr-defined]
            frame.source_image = (
                source_image.id if source_image else None  # type: ignore[attr-defined]
            )
            frame.story = story.id  # type: ignore[attr-defined]
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


async def main() -> None:
    engine = engine_finder()
    if not engine:
        raise ValueError("No Piccolo engine found. Check the Piccolo configuration.")

    print("Starting connection pool.")
    await engine.start_connection_pool()

    try:
        print("Copy configs...")
        await copy_configs_to_piccolo()
        print("Copy stories...")
        await copy_stories_to_piccolo()
        print("Copy state...")
        await copy_sparrow_states_to_piccolo()
    finally:
        print("Closing connection pool.")
        await engine.close_connection_pool()


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
