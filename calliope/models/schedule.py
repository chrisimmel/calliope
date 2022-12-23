from typing import List, Optional

from pydantic import BaseModel, StrictInt, StrictStr

from calliope.models.parameters import StoryParamsModel
from calliope.models.trigger_condition import TriggerConditionModel


class ScheduleStepModel(BaseModel):
    """
    A step in a configuration schedule.
    """

    # The strategy parameters to be in effect during this step.
    parameters: StoryParamsModel

    # The minimum duration of this step.
    min_duration: Optional[int]

    # The condition that triggers this step.
    trigger_condition: TriggerConditionModel


class ScheduleModel(BaseModel):
    """
    A sequence of configuration steps.
    """

    # The ID of the schedule.
    schedule_id: StrictStr

    # An optional name for the schedule.
    name: Optional[str]

    # The sequence of steps.
    steps: List[ScheduleStepModel]


class ScheduleStateModel(BaseModel):
    """
    The state of a schedule.
    """

    # The ID of the schedule.
    schedule_id: StrictStr

    # Zulu time when the schedule was started, if any.
    schedule_started_at: Optional[StrictStr] = None

    # Zulu time when the schedule was ended, if any.
    schedule_ended_at: Optional[StrictStr] = None

    # The index of the current step, if in progress.
    current_step_index: Optional[StrictInt] = None

    # Zulu time when the current step was started, if any.
    step_started_at: Optional[StrictStr] = None
