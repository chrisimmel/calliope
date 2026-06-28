"""get_task_writer must target the configured (named) Firestore database — the
one the web client listens on — not the implicit "(default)"."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import google.cloud.firestore as gcf

import calliope2.realtime.firestore as fs


def _settings(project: str, database: str):
    return SimpleNamespace(firebase_project_id=project, firebase_database_id=database)


def test_writer_targets_named_database(monkeypatch):
    fs.reset_task_writer_cache()
    monkeypatch.setattr(fs, "get_settings", lambda: _settings("proj", "calliope2-production"))
    captured = {}

    def fake_async_client(*, project, database):
        captured["project"] = project
        captured["database"] = database
        return MagicMock()

    monkeypatch.setattr(gcf, "AsyncClient", fake_async_client)

    writer = fs.get_task_writer()
    assert isinstance(writer, fs.FirestoreTaskWriter)
    assert captured == {"project": "proj", "database": "calliope2-production"}
    fs.reset_task_writer_cache()


def test_writer_falls_back_to_default_database(monkeypatch):
    fs.reset_task_writer_cache()
    monkeypatch.setattr(fs, "get_settings", lambda: _settings("proj", ""))
    captured = {}
    monkeypatch.setattr(
        gcf,
        "AsyncClient",
        lambda *, project, database: captured.update(database=database) or MagicMock(),
    )
    fs.get_task_writer()
    assert captured["database"] == "(default)"
    fs.reset_task_writer_cache()


def test_logging_writer_without_project(monkeypatch):
    fs.reset_task_writer_cache()
    monkeypatch.setattr(fs, "get_settings", lambda: _settings("", ""))
    from calliope2.realtime.writer import LoggingTaskWriter

    assert isinstance(fs.get_task_writer(), LoggingTaskWriter)
    fs.reset_task_writer_cache()
