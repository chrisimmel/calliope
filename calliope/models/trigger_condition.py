from typing import Optional

from pydantic import BaseModel, StrictBool, StrictInt


class TriggerConditionModel(BaseModel):
    """
    A trigger condition for an event or sequence of events.
    """


class AtTimeTriggerConditionModel(TriggerConditionModel):
    """
    Trigger an event at a given time.
    """

    # Trigger the event at the given time, a Unix timestamp (seconds since epoch).
    at_time: StrictInt


class OnMotionTriggerConditionModel(BaseModel):
    """
    Trigger an event when something moves.
    """

    # An image illustrating the story.
    on_motion: StrictBool
