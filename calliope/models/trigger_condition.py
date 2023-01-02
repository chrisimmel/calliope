from enum import Enum

from pydantic import BaseModel, StrictInt, StrictStr


class TriggerType(Enum):
    AT_TIME = "at_time"
    AFTER_WAIT = "after_wait"
    ON_MOTION = "on_motion"
    ON_SOUND = "on_sound"
    ON_LIGHT = "on_light"


class TriggerConditionModel(BaseModel):
    """
    A trigger condition for an event or sequence of events.
    """

    trigger_type: TriggerType


class AtTimeTriggerConditionModel(TriggerConditionModel):
    """
    Trigger an event at a given time.
    """

    trigger_type = TriggerType.AT_TIME

    # Trigger the event at or after the given Zulu time (ISO format).
    at_time: StrictStr


class AfterWaitTriggerConditionModel(BaseModel):
    """
    Trigger an event after waiting a given number of seconds.
    """

    trigger_type = TriggerType.AFTER_WAIT

    # Trigger the event after waiting the given number of seconds.
    wait_seconds: StrictInt


class OnMotionTriggerConditionModel(BaseModel):
    """
    Trigger an event when something moves.
    """

    trigger_type = TriggerType.ON_MOTION


class OnSoundTriggerConditionModel(BaseModel):
    """
    Trigger an event when you hear something.
    """

    trigger_type = TriggerType.ON_SOUND


class OnLightTriggerConditionModel(BaseModel):
    """
    Trigger an event when you see light.
    """

    trigger_type = TriggerType.ON_LIGHT
