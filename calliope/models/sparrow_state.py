from typing import List, Optional

from pydantic import BaseModel, StrictStr

from calliope.models.schedule import ScheduleStateModel


class SparrowStateModel(BaseModel):
    """
    The state of a given sparrow or flock.
    """

    # The sparrow's ID.
    sparrow_id: StrictStr

    # The IDs of all stories created for this client.
    story_ids: List[StrictStr]

    # The scheduling state, if any.
    schedule_state: Optional[ScheduleStateModel]
