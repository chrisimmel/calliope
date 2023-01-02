# Scheduling

A sparrow can be configured to follow a given schedule, switching among planned
parameter configurations according to an agenda.

A schedule consists of a sequence of _steps_. Where each step has the following
components:

* `parameters` - The strategy parameters to be in effect during this step.
* `min_duration_seconds` - The minimum duration of this step, in seconds. If unspecified,
there is no minimum duration, and the following step can be activated as soon as its
trigger condition, if any, is met.
* `trigger_condition` - The condition that triggers this step, if any.

The `min_duration_seconds` and `trigger_condition` fields function exactly as they do for
frames in a story.

The `trigger_condition` can be any of the following:

* `at_time`: The step is activated the first time a request for frames arrives
after the given time.
* `after_wait`: The step is activated after waiting a given number of seconds.
* `on_motion`: The step is activated when motion is detected (not yet implemented).
* `on_sound`: The step is activated when sound is detected (not yet implemented).
* `on_light`: The step is activated when light is detected (not yet implemented).

