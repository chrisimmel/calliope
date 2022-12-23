import os
from typing import cast, Optional

from calliope.models import (
    StoryModel,
    ScheduleModel,
    ScheduleStateModel,
    SparrowStateModel,
)
from calliope.utils.file import (
    load_json_into_pydantic_model,
    write_pydantic_model_to_json,
)
from calliope.utils.google import get_google_file, is_google_cloud_run_environment


def put_sparrow_state():
    ...


def get_sparrow_state():
    ...
