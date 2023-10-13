from typing import cast, Sequence

from fastapi import Request
from pydantic import BaseModel

from calliope.tables.story import Story


class AddStoryThumbnailsFormModel(BaseModel):
    comment: str


# Run command action handler
async def add_story_thumbnails_endpoint(
    request: Request,
    data: AddStoryThumbnailsFormModel
) -> str:
    story_count = 0
    thumb_count = 0

    for story in cast(Sequence[Story], await Story.objects()):
        story_count += 1
        print(
            f"Story {story.id} has thumbnail "  # type: ignore[attr-defined]
            f"{story.thumbnail_image}."
        )
        if not story.thumbnail_image:
            thumbnail_image = await story.compute_thumbnail()
            if thumbnail_image:
                await thumbnail_image.save().run()
            story.thumbnail_image = thumbnail_image
            thumb_count += 1

            await story.save().run()

    return f"Found {story_count} stories. Set thumbnails for {thumb_count} of them."
