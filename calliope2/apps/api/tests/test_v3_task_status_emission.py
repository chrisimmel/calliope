"""End-to-end: starting a generation task emits the right status writes.

We patch ``run_storyteller`` and the persistence helpers so no inference or DB
work happens, and we replace ``get_task_writer`` with an AsyncMock recorder.
That isolates the wiring between the task layer and the realtime writer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from calliope2.api.v3 import tasks as task_module

if TYPE_CHECKING:
    from calliope2.realtime.task_status import TaskRecord


@pytest.fixture
def recorder(monkeypatch):
    w = AsyncMock()
    monkeypatch.setattr(task_module, "get_task_writer", lambda: w)
    return w


@pytest.fixture(autouse=True)
def _stub_persistence(monkeypatch):
    """Storyteller invocation + frame persistence are out of scope here."""
    from calliope2.storytellers import FrameOutput

    monkeypatch.setattr(
        task_module, "run_storyteller", AsyncMock(return_value=FrameOutput(text="ok"))
    )
    monkeypatch.setattr(task_module, "_persist_frame", AsyncMock(return_value=None))


async def test_generate_first_frame_writes_started_then_completed(recorder):
    await task_module.generate_first_frame(
        task_id="t1", story_id=42, user_id=7, firebase_uid="uid-7",
        storyteller_name="literal", inputs={"source_text": "hi"},
    )
    first_call_args = next(c.args for c in recorder.started.await_args_list)
    assert first_call_args[0].task_id == "t1"
    record: TaskRecord = recorder.started.await_args.args[0]
    assert record.user_id == 7
    assert record.story_id == 42
    assert record.type.value == "create_story"
    recorder.completed.assert_awaited_once_with("t1")
    recorder.failed.assert_not_awaited()


async def test_generate_first_frame_writes_failed_on_storyteller_error(monkeypatch, recorder):
    monkeypatch.setattr(
        task_module, "run_storyteller", AsyncMock(side_effect=RuntimeError("inference down"))
    )
    with pytest.raises(RuntimeError):
        await task_module.generate_first_frame(
            task_id="t2", story_id=1, user_id=1, firebase_uid="uid-1",
            storyteller_name="literal", inputs={},
        )
    recorder.completed.assert_not_awaited()
    recorder.failed.assert_awaited_once()
    args = recorder.failed.await_args.args
    assert args == ("t2", "inference down")


async def test_generate_next_frame_marks_failed_when_story_vanished(monkeypatch, recorder):
    monkeypatch.setattr(task_module, "_load_story_with_frames", AsyncMock(return_value=None))

    await task_module.generate_next_frame(
        task_id="t3", story_id=999, user_id=1, firebase_uid="uid-1", inputs={}
    )
    recorder.failed.assert_awaited_once()
    msg = recorder.failed.await_args.args[1]
    assert "999" in msg
