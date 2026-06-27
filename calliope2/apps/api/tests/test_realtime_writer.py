"""Tests for the FirestoreTaskWriter + the get_task_writer factory."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from calliope2.realtime import (
    FirestoreTaskWriter,
    LoggingTaskWriter,
    TaskRecord,
    TaskStatus,
    TaskType,
    TaskWriter,
    get_task_writer,
    reset_task_writer_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_task_writer_cache()
    yield
    reset_task_writer_cache()


@pytest.fixture
def record() -> TaskRecord:
    return TaskRecord(
        task_id="t-abc",
        user_id=7,
        firebase_uid="uid-7",
        story_id=42,
        type=TaskType.CREATE_STORY,
        started_at=datetime(2026, 5, 13, tzinfo=UTC),
    )


def _build_fake_firestore() -> tuple[MagicMock, MagicMock]:
    """Return (client, document_mock) where document_mock has set/update mocked."""
    client = MagicMock()
    doc = MagicMock()
    doc.set = AsyncMock()
    doc.update = AsyncMock()
    client.collection.return_value.document.return_value = doc
    return client, doc


# ----- LoggingTaskWriter satisfies the protocol -----

def test_logging_writer_satisfies_protocol():
    assert isinstance(LoggingTaskWriter(), TaskWriter)


async def test_logging_writer_methods_are_callable(record):
    w = LoggingTaskWriter()
    await w.started(record)
    await w.progress("t-abc", 0.5)
    await w.completed("t-abc")
    await w.failed("t-abc", "boom")


# ----- FirestoreTaskWriter writes the right payloads -----

async def test_started_sets_initial_document(record):
    client, doc = _build_fake_firestore()
    w = FirestoreTaskWriter(client)

    await w.started(record)

    client.collection.assert_called_once_with("tasks")
    client.collection.return_value.document.assert_called_once_with("t-abc")
    doc.set.assert_awaited_once()
    payload = doc.set.await_args.args[0]
    assert payload["user_id"] == 7
    assert payload["story_id"] == 42
    assert payload["type"] == "create_story"
    assert payload["status"] == "running"
    assert payload["started_at"] == record.started_at


async def test_progress_updates_running_status_and_value(record):
    client, doc = _build_fake_firestore()
    w = FirestoreTaskWriter(client)

    await w.progress("t-abc", 0.4)

    doc.set.assert_awaited_once()
    payload = doc.set.await_args.args[0]
    assert payload == {"status": "running", "progress": 0.4}


async def test_completed_writes_completed_status_and_timestamp():
    client, doc = _build_fake_firestore()
    w = FirestoreTaskWriter(client)

    await w.completed("t-abc")

    payload = doc.set.await_args.args[0]
    assert payload["status"] == "completed"
    assert payload["progress"] == 1.0
    assert isinstance(payload["completed_at"], datetime)


async def test_failed_writes_error_and_completed_at():
    client, doc = _build_fake_firestore()
    w = FirestoreTaskWriter(client)

    await w.failed("t-abc", "inference timeout")

    payload = doc.set.await_args.args[0]
    assert payload["status"] == "failed"
    assert payload["error"] == "inference timeout"
    assert isinstance(payload["completed_at"], datetime)


async def test_firestore_errors_are_swallowed_not_raised(record):
    """Status is best-effort — Firestore unreachable should not kill the task."""
    client = MagicMock()
    doc = MagicMock()
    doc.set = AsyncMock(side_effect=RuntimeError("firestore down"))
    client.collection.return_value.document.return_value = doc
    w = FirestoreTaskWriter(client)

    await w.started(record)  # must not raise


# ----- Factory -----

def test_get_task_writer_returns_logging_when_no_firebase_project(monkeypatch):
    from calliope2.settings import Settings, get_settings

    monkeypatch.setattr(
        "calliope2.realtime.firestore.get_settings",
        lambda: Settings(firebase_project_id=""),
    )
    get_settings.cache_clear()
    assert isinstance(get_task_writer(), LoggingTaskWriter)


def test_get_task_writer_constructs_firestore_when_project_set(monkeypatch):
    from calliope2.settings import Settings

    fake_async_client = MagicMock()
    monkeypatch.setattr(
        "calliope2.realtime.firestore.get_settings",
        lambda: Settings(firebase_project_id="my-project"),
    )
    monkeypatch.setattr(
        "google.cloud.firestore.AsyncClient", lambda **kw: fake_async_client
    )
    w = get_task_writer()
    assert isinstance(w, FirestoreTaskWriter)


# ----- TaskRecord schema -----

def test_task_record_defaults():
    t = TaskRecord(
        task_id="x", user_id=1, firebase_uid="uid-1", story_id=2,
        type=TaskType.CREATE_FRAME, started_at=datetime.now(UTC),
    )
    assert t.status == TaskStatus.PENDING
    assert t.progress == 0.0
    assert t.error is None
    assert t.completed_at is None


def test_task_record_progress_bounded():
    with pytest.raises(ValueError):
        TaskRecord(
            task_id="x", user_id=1, firebase_uid="uid-1", story_id=2,
            type=TaskType.CREATE_FRAME, started_at=datetime.now(UTC),
            progress=1.5,
        )
