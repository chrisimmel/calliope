from datetime import datetime

from piccolo.table import Table
from piccolo.columns import (
    Boolean,
    ForeignKey,
    Text,
    Timestamptz,
    Varchar,
)

from calliope.tables.sparrow_state import SparrowState
from calliope.tables.story import Story, StoryFrame


class BookmarkList(Table):
    """
    A list of bookmarks.
    """

    # The name of the list.
    name = Varchar(length=128, required=True)

    # Description, notes, etc.
    descriiption = Text(null=True, required=False)

    # The Sparrow who created the list, if any.
    sparrow = ForeignKey(references=SparrowState)

    # Whether this is a public list.
    is_public = Boolean(default=False)

    # The dates the bookmark was created and updated.
    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


class StoryBookmark(Table):
    """
    A bookmark pointing to a story.
    """

    # The story.
    story = ForeignKey(references=Story)

    # The Sparrow.
    sparrow = ForeignKey(references=SparrowState)

    # The list of which this is a part.
    list = ForeignKey(references=BookmarkList)

    # Comments about the story.
    comments = Text(null=True, required=False)

    # The dates the bookmark was created and updated.
    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


class StoryFrameBookmark(Table):
    """
    A bookmark pointing to an individual frame.
    """

    # The frame.
    frame = ForeignKey(references=StoryFrame)

    # The Sparrow.
    sparrow = ForeignKey(references=SparrowState)

    # Comments about the frame.
    comments = Text(null=True, required=False)

    # The dates the bookmark was created and updated.
    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)
