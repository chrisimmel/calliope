# Local development

This walks through getting calliope2 running on your machine from a
fresh `git clone`.

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.11+ | Required by the workspace |
| [uv](https://docs.astral.sh/uv/) | latest | The dependency / workspace manager |
| Node.js | 20+ | For the two frontend SPAs |
| Postgres | 14+ with `pgvector` extension | The DB (real one — only needed when you want to exercise the full stack) |

## Quick check

```bash
git clone https://github.com/chrisimmel/calliope.git
cd calliope/calliope2
uv sync                                    # creates .venv, installs deps
uv run pytest                              # 107 / 107 pass
uv run ruff check apps/
```

If those work, you have a sound Python environment.

## Running the backend

You can boot the API **without Postgres**, **without Firebase**, and
**without inference API keys**. Many tests run that way. What works
without those:

- `GET /v3/health` — always returns 200
- `GET /v3/storytellers` — returns 401 (no token), but the route is up

With a Postgres + Firebase + OpenAI configured, everything works.

### Step-by-step

```bash
cd calliope2
uv sync

# Run the API on http://localhost:8000
uv run uvicorn calliope2.app:app --app-dir apps/api --reload

# In another shell:
curl http://localhost:8000/v3/health
# → {"status":"ok","version":"0.1.0"}
```

### Environment variables

Settings come from env vars (prefixed `CALLIOPE2_`) or a `.env` file in
the working directory. Defaults are in
[`apps/api/calliope2/settings.py`](../../apps/api/calliope2/settings.py).

Minimum for local dev (sane defaults, no external services):

```bash
# Optional — defaults to localhost:5432; only matters once you boot Postgres
CALLIOPE2_DATABASE_URL=postgresql+asyncpg://calliope:calliope@localhost:5432/calliope2

# Leave empty in dev: get_task_writer falls back to LoggingTaskWriter
# (no Firestore access required)
CALLIOPE2_FIREBASE_PROJECT_ID=
```

For full-stack dev:

```bash
# Postgres
CALLIOPE2_DATABASE_URL=postgresql+asyncpg://calliope:calliope@localhost:5432/calliope2

# Firebase (for auth + realtime status writes)
CALLIOPE2_FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# OpenAI (for inference + embeddings)
CALLIOPE2_OPENAI_API_KEY=sk-...

# Replicate (for image/video generation via flux/runway)
CALLIOPE2_REPLICATE_API_TOKEN=r8_...

# GCS bucket (for media storage — wired up in the storage phase)
CALLIOPE2_GCS_BUCKET=your-bucket
```

See [`apps/api/calliope2/settings.py`](../../apps/api/calliope2/settings.py)
for the full list — every field is annotated.

## Setting up Postgres + pgvector

The fastest path is Docker:

```bash
docker run -d --name calliope2-db \
  -e POSTGRES_USER=calliope \
  -e POSTGRES_PASSWORD=calliope \
  -e POSTGRES_DB=calliope2 \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

The `pgvector/pgvector` image bundles the `vector` extension. Then:

```bash
cd calliope2/apps/api
uv run alembic upgrade head
```

This applies `0001_initial` (all 6 tables) and `0002_pgvector` (the
extension + embedding column + HNSW index).

If you don't have Docker, install Postgres locally and add the
`pgvector` extension:

```bash
brew install postgresql
brew install pgvector       # macOS
# or follow https://github.com/pgvector/pgvector#installation
psql -U calliope -d calliope2 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

`0002_pgvector` runs the `CREATE EXTENSION` for you, so on a fresh DB
`alembic upgrade head` from scratch is enough.

### Verifying the DB

```bash
uv run alembic current        # should show f2e3d4c5b6a7 (head)
uv run alembic upgrade head --sql   # dry-run; prints DDL without applying
```

## Running the CLI

```bash
uv run calliope2-cli --help
uv run calliope2-cli vector reindex --dry-run
uv run calliope2-cli migrate from-v1 --help
```

The CLI imports from the API package via the uv workspace, so it shares
the same Settings / DB session machinery.

## Running the frontends

### Clio v3

```bash
cd calliope2/apps/web/clio
npm install
npm run build         # builds to apps/api/calliope2/static/clio/
# or:
npm start             # dev server on http://localhost:3000
```

Required env vars (typically in a `.env` next to `package.json`):

```
FIREBASE_API_KEY=...
FIREBASE_PROJECT_ID=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_APP_ID=...
```

When `npm run build` finishes, the FastAPI app serves the SPA at
`/clio/` (`apps/api/calliope2/app.py` mounts the static dir).

### Admin

```bash
cd calliope2/apps/web/admin
npm install
npm run build         # builds to apps/api/calliope2/static/admin/
# or:
npm run dev           # Vite dev server on http://localhost:3001
```

Same Firebase env vars apply. Mounted at `/admin/` once built.

## Running tests

```bash
cd calliope2
uv run pytest -q                       # all tests
uv run pytest apps/api/tests/test_v3_stories.py -v
uv run pytest -k "storyteller"         # by name
```

Tests use **aiosqlite in-memory** for the DB — no real Postgres
needed. The `conftest.py` registers DDL compile overrides for
`pgvector.Vector` → `TEXT` and `JSONB` → `JSON` so the schema builds
on SQLite. See [`vector-search.md`](../concepts/vector-search.md) for
why.

### Linting / formatting

```bash
uv run ruff check apps/                # lint
uv run ruff check apps/ --fix          # autofix what it can (safe)
uv run ruff format apps/               # format (not enforced in CI yet)
```

There are per-file `TC001/TC002/TC003` ignores for the FastAPI router
and Typer command directories; see
[`ADR 0008`](../decisions/0008-fastapi-runtime-annotations.md) for why.

## Adding a storyteller

1. Create `apps/api/calliope2/storytellers/defs/<name>.yaml`.
2. Create the referenced `prompts/<name>/*.j2` files.
3. Add a snapshot test in `apps/api/tests/test_storyteller_runtime.py`
   if the behavior is non-obvious.
4. The new name auto-appears in `GET /v3/storytellers`.

See [`storytellers.md`](../concepts/storytellers.md) for the YAML
reference.

## Adding a migration

```bash
cd calliope2/apps/api

# Generate a new revision against the current schema
uv run alembic revision --autogenerate -m "add foo column"

# Inspect and edit alembic/versions/<timestamp>_add_foo_column.py

# Preview the SQL
CALLIOPE2_DATABASE_URL=postgresql+asyncpg://x:x@localhost/x \
  uv run alembic upgrade head --sql

# Apply
uv run alembic upgrade head
```

`alembic --autogenerate` requires a live DB to introspect. The
existing migrations were hand-written and tested via `--sql` against a
postgres-dialect connection string — see
[`apps/api/alembic/versions/`](../../apps/api/alembic/versions/) for
the pattern.

## Troubleshooting

**Symptom:** routes return 422 with `loc: ["query", "session"]` errors.
**Likely cause:** a dependency import got moved into a `TYPE_CHECKING`
block. FastAPI evaluates `Annotated[T, Depends(...)]` at runtime. Move
the import back to module level and add a per-file `TC001/2` ignore in
`pyproject.toml` if ruff complains. See
[`ADR 0008`](../decisions/0008-fastapi-runtime-annotations.md).

**Symptom:** `alembic upgrade head` complains about `Vector` or
`JSONB` not being compilable.
**Likely cause:** you're trying to apply the migration against SQLite,
which doesn't have pgvector or JSONB. Use Postgres for migrations; the
tests use SQLite with DDL overrides only.

**Symptom:** `firebase_admin.auth.InvalidIdTokenError` on every request.
**Likely cause:** local backend running with no `GOOGLE_APPLICATION_CREDENTIALS`
and a real Firebase token. Either point at a real service account, or
override `get_firebase_claims` in your tests, or skip auth-needing
endpoints until you have Firebase configured.

**Symptom:** Storyteller hangs on `text:` step.
**Likely cause:** No `OPENAI_API_KEY`; the request goes out and hangs
on the retry loop. Set the key, or use a mocked client in tests.

## Related

- [`ops/migration.md`](migration.md) — the legacy → v3 cutover playbook.
- [`architecture.md`](../architecture.md) — the high-level shape.
- [`concepts/`](../concepts/) — each subsystem in detail.
