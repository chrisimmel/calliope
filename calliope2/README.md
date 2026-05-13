# Calliope v2

Modernization of [Calliope](../calliope/) — a fresh tree built alongside the legacy app, cut over per feature. See the modernization plan in chat / planning notes for full context.

## Layout

```
apps/
  api/     # FastAPI service + shared Python core (`calliope2` package)
  cli/     # Typer CLI (`calliope2-cli`)
  web/
    clio/  # React story player (moved here in Phase 7)
    admin/ # New React Admin SPA (Phase 8 — replaces Thoth + Piccolo Admin)
  mobile/  # placeholder
docs/
scripts/
tests/     # cross-app integration tests
```

This is a uv workspace; `apps/api` and `apps/cli` are members.

## Quickstart

```bash
cd calliope2
uv sync                                  # resolve workspace
uv run uvicorn calliope2.app:app --reload --app-dir apps/api
uv run calliope2-cli version
uv run pytest
```

The old `/calliope/` app continues to serve `/v1`, `/v2`, `/admin`, `/clio/`, `/thoth/`, `/media/` until cutover. The new app exposes only `/v3`.
