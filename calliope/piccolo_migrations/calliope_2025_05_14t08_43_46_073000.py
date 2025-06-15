from datetime import datetime
import re

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import (
    Text,
    Timestamptz,
    Varchar,
)
from piccolo.table import Table


ID = "2025-05-14T08:43:46:073000"
VERSION = "1.7.0"
DESCRIPTION = ""


class Story(Table):
    """
    A story.
    """

    # A visible unique ID, a CUID.
    cuid = Varchar(length=50, unique=True, index=True)

    # The story's title.
    title = Text()

    # A URL-friendly slug for the story (unique).
    slug = Varchar(length=100, unique=True, index=True, null=True)

    # The dates the story was created and updated.
    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    # Ignore other columns for brevity.

    @staticmethod
    def generate_slug_base(title: str) -> str:
        """
        Generate a base URL-friendly slug from a title.
        Converts to lowercase, removes non-alphanumeric characters,
        and replaces spaces with hyphens.

        This is a base slug that might need to be modified to ensure uniqueness.
        """
        # Convert to lowercase.
        slug = title.lower()

        # Replace non-alphanumeric characters with spaces.
        slug = re.sub(r'[^a-z0-9\s]', ' ', slug)

        # Replace multiple spaces with a single space.
        slug = re.sub(r'\s+', ' ', slug).strip()

        # Replace spaces with hyphens.
        slug = slug.replace(' ', '-')

        # Limit to first few words (up to 40 chars).
        slug_parts = slug.split('-')
        slug = '-'.join(slug_parts[:5])[:40]

        # Ensure slug is not empty.
        if not slug:
            slug = "story"

        return slug

    async def generate_unique_slug(self) -> str:
        """
        Generate a unique slug based on the story's title.
        The slug is only generated when we have at least one frame with text.
        """
        if not self.title:
            return None

        # Generate base slug.
        base_slug = Story.generate_slug_base(self.title)

        # Check if the slug already exists.
        query = Story.objects().where(Story.slug == base_slug, Story.id != self.id)
        existing = await query.first().run()

        if not existing:
            return base_slug

        # Slug exists, so append a number.
        counter = 1
        while True:
            new_slug = f"{base_slug}-{counter}"

            query = Story.objects().where(Story.slug == new_slug, Story.id != self.id)
            existing = await query.first().run()

            if not existing:
                return new_slug

            counter += 1


async def backfill_story_slugs() -> None:
    """
    Backfill slugs for all stories that don't have them yet.

    Returns:
        Dictionary with counts of updated, failed, and total stories processed
    """
    # Get all stories without a slug
    stories_without_slug = await Story.objects().where(
        Story.slug.is_null()
    ).run()

    updated_count = 0
    failed_count = 0

    # Generate and set slugs
    for story in stories_without_slug:
        try:
            # Generate slug for this story
            new_slug = await story.generate_unique_slug()

            # Skip if we couldn't generate a slug (no title yet)
            if not new_slug:
                failed_count += 1
                continue

            # Update the story with the new slug
            story.slug = new_slug
            await story.save().run()
            updated_count += 1

        except Exception as e:
            print(f"Error generating slug for story {story.id}: {e}")
            failed_count += 1

    print({
        "updated": updated_count,
        "failed": failed_count,
        "total": len(stories_without_slug)
    })


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="", description=DESCRIPTION
    )

    async def run():
        print(f"running {ID}")

        await backfill_story_slugs()

    manager.add_raw(run)

    return manager
