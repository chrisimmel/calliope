"""Shared test fixtures for the API.

Strategy:
- Use aiosqlite for the test DB. SQLite is fast and dependency-free, but
  pgvector's ``Vector`` type has no SQLite impl, so we register a SQLite
  DDL compiler that emits ``TEXT`` for it. All Phase 4 tests leave
  ``embedding`` NULL, so no bind/result processing is exercised.
- Override the ``get_session`` and ``get_firebase_claims`` dependencies
  for each test, yielding a session bound to a per-test in-memory DB and
  a fixed Firebase claims payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from calliope2.app import create_app
from calliope2.auth.dependencies import get_firebase_claims
from calliope2.db import models  # noqa: F401 — register mappers
from calliope2.db.base import Base
from calliope2.db.session import get_session

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


@compiles(Vector, "sqlite")
def _vector_as_text_on_sqlite(_type, _compiler, **_kw) -> str:
    """Make CREATE TABLE story_frames work on SQLite. Embedding stays NULL in tests."""
    return "TEXT"


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(_type, _compiler, **_kw) -> str:
    """JSONB falls back to JSON on SQLite; bind/result processors come from the JSON base class."""
    return "JSON"


@pytest.fixture
async def db_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(db_sessionmaker) -> AsyncIterator[AsyncSession]:
    async with db_sessionmaker() as s:
        yield s


@pytest.fixture
def firebase_claims() -> dict[str, str]:
    return {"uid": "test-uid-1", "email": "tester@example.com", "name": "Tester One"}


@pytest.fixture
def app(db_sessionmaker, firebase_claims) -> FastAPI:
    """Build a FastAPI app with auth + session dependencies wired to the test DB."""
    app = create_app()

    async def _session_override() -> AsyncIterator[AsyncSession]:
        async with db_sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_firebase_claims] = lambda: firebase_claims
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac
