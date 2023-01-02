from datetime import datetime, timedelta
from typing import cast, Optional

from calliope.models import (
    AfterWaitTriggerConditionModel,
    AtTimeTriggerConditionModel,
    ScheduleStateModel,
    SparrowConfigModel,
    SparrowStateModel,
    StoryParamsModel,
    TriggerConditionModel,
    TriggerType,
)


def format_time(timestamp: datetime) -> str:
    """
    Formats a datetime as an ISO 8601 UTC time.
    """
    return timestamp.isoformat()


def parse_time(timestamp_string: str) -> datetime:
    """
    Parses a string containing an ISO 8601 UTC time into a datetime.
    """
    return datetime.fromisoformat(timestamp_string)


def check_schedule(
    sparrow_config: SparrowConfigModel, sparrow_state: SparrowStateModel
) -> Optional[StoryParamsModel]:
    """
    Checks the sparrow's or flock's schedule, potentially advancing to the next
    step. Updates the sparrow state as needed.

    Returns:
        The parameters currently in effect according to the schedule.
    """
    schedule = sparrow_config.schedule

    if not schedule:
        # There is no schedule in effect.
        return None

    if sparrow_state.schedule_state.schedule_ended_at:
        # The schedule was already completed.
        return None

    now = datetime.datetime.utcnow()
    if not sparrow_state.schedule_state:
        sparrow_state.schedule_state = ScheduleStateModel(
            schedule_started_at=format_time(now)
        )
    schedule_state = sparrow_state.schedule_state

    current_step_index = schedule_state.current_step_index
    current_step = (
        schedule.steps[schedule_state.current_step_index] if current_step_index else None
    )
    if current_step and current_step.min_duration_seconds:
        step_started_at = parse_time(schedule_state.step_started_at)
        retain_step_until = step_started_at + timedelta(
            seconds=current_step.min_duration_seconds
        )
        if retain_step_until > now:
            # This step's minimum duration has not passed,
            # so it's too early to even check the trigger condition for the next step.
            return current_step.parameters

    # Check to see whether we can start the next step...
    if not current_step_index and len(schedule.steps):
        next_step_index = 0
    elif current_step_index < len(schedule.steps) - 1:
        next_step_index = current_step_index + 1
    else:
        next_step_index = None

    next_step = schedule.steps[next_step_index] if next_step_index else None
    if next_step and trigger_condition_is_met(
        next_step.trigger_condition, schedule_state
    ):
        # Advance to the next step...
        print(
            f"Advancing to schedule step {next_step_index} for sparrow {sparrow_config.id}."
        )
        schedule_state.current_step_index = next_step_index
        return next_step.parameters

    if not next_step:
        schedule_state.schedule_ended_at = format_time(now)
        print(
            f"Completing schedule for sparrow {sparrow_config.id} at "
            f"{schedule_state.schedule_ended_at}."
        )
        return None

    # We're still on the current step.
    return current_step.parameters if current_step else None


def trigger_condition_is_met(
    trigger_condition: TriggerConditionModel, schedule_state: ScheduleStateModel
) -> bool:
    """
    Evaluates the given trigger condition to see whether it has been met.
    """
    if not trigger_condition:
        # A null trigger condition is always met.
        return True

    now = datetime.datetime.utcnow()
    if trigger_condition.trigger_type == TriggerType.AT_TIME:
        at_time = parse_time(
            cast(AtTimeTriggerConditionModel, trigger_condition).at_time
        )
        return at_time < now
    elif trigger_condition.trigger_type == TriggerType.AFTER_WAIT:
        wait_seconds = cast(
            AfterWaitTriggerConditionModel, trigger_condition
        ).wait_seconds
        if not schedule_state.wait_until:
            schedule_state.wait_until = now.isoformat() + timedelta(seconds=wait_seconds)
        wait_until = parse_time(schedule_state.wait_until)
        if wait_until < now:
            # We've waited enough.
            # Cancel the "wait_until" time.
            schedule_state.wait_until = None
            return True

        # We need to wait more.
        return False

    print(
        f"Don't yet know how to evaluate trigger condition: {trigger_condition.trigger_type}"
    )
    return False
