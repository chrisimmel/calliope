# Architecture

calliope2 is a small generative-story app. A user signs in with Google,
picks a Storyteller (and optionally an Illustrator), and gets back a
sequence of frames — short prose paragraphs paired with generated
images and occasionally videos. The new app runs alongside the legacy
`/calliope/` Piccolo app until per-feature cutover; both share a GCP
project and Firebase auth.

## Monorepo layout

```
calliope2/
  apps/
    api/                       # FastAPI service + shared Python core
      calliope2/               # the importable package
        app.py                 # FastAPI factory
        settings.py            # pydantic-v2 Settings
        db/                    # SQLAlchemy 2.0 models + session + base
        api/v3/                # routers (stories, bookmarks, search,
                               # storytellers, admin/*)
        auth/                  # Firebase ID-token verify + dependencies
        storytellers/          # YAML-declared narrative pipelines
        illustrators/          # YAML-declared visual pipelines (Phase 10)
        inference/             # provider-agnostic LLM/image/video clients
        realtime/              # narrowed Firestore task-status writer
        vector/                # pgvector embed + cosine-distance search
        migration/             # one-shot read-only migration from /calliope/
        static/                # built SPA assets (clio/, admin/)
      alembic/                 # async migrations (0001_initial, 0002_pgvector)
      tests/                   # pytest, aiosqlite in-memory DB
    cli/                       # calliope2-cli (Typer) — vector, migrate, version
    web/
      clio/                    # v3 reader (forked from /clio/; Phase 7)
      admin/                   # v3 admin SPA (Vite + React; Phase 8)
    mobile/                    # placeholder
  docs/                        # this directory
```

`apps/api/` and `apps/cli/` are a single uv workspace
(`[tool.uv.workspace] members = ["apps/api", "apps/cli"]`); the CLI
imports from the API package via a path dependency. The two web SPAs are
independent npm projects; both build to `apps/api/calliope2/static/`
which the FastAPI app mounts as static directories.

## Request lifecycle — creating a story

```
Clio (browser)                         FastAPI                     Postgres        Firestore
─────────────                          ───────                     ────────        ─────────
1. Google sign-in via popup
   (services/firebase.ts)
                ──── Firebase ID token ────►
                                       2. HTTPBearer → verify_id_token
                                       3. get_current_user
                                          (auto-create User if first sight)
                                                                   ◄── SELECT User
                                                                   ──► INSERT User (if new)
4. POST /v3/stories
   {storyteller, illustrator?,
    inputs: {source_image_url?}}
                ────────────►
                                       5. validate storyteller name
                                       6. INSERT Story
                                                                   ──► INSERT Story
                                       7. enqueue BackgroundTask:
                                          generate_first_frame
                ◄── 202 {story_id, task_id} ────
                                       8. background: writer.started(task)
                                                                                   ──► tasks/{task_id}
                                       9. background: run_storyteller
                                          (storyteller pipeline:
                                           analyze_image → generate_text →
                                           use_illustrator)
                                       10. background: try_embed_text
                                       11. background: persist Image, Frame
                                                                   ──► INSERT Image, StoryFrame
                                       12. background: writer.completed
                                                                                   ──► tasks/{task_id}
15. Firestore listener fires
    (watchTasksForStory)              ◄── snapshot ───────────────────────────────
16. GET /v3/stories/{id}
                ────────────►
                                                                   ◄── SELECT Story+frames
                ◄── 200 {story, frames}
```

Firestore is **a status mailbox, not durable state** — Postgres is the
source of truth for content. Firestore writes are best-effort and
failures are logged-and-swallowed; if Firestore is unreachable the
story is still generated and persisted. See
[concepts/realtime.md](concepts/realtime.md).

## Subsystem boundaries

| Layer | Knows about | Doesn't know about |
|---|---|---|
| **Inference** (`inference/`) | HTTP to OpenAI / Replicate / etc.; bytes and URLs | DB models, Firestore, FastAPI |
| **Storytellers** (`storytellers/`) | Inference clients; Jinja prompts; storyteller YAML schema | DB models, FastAPI, persistence |
| **Illustrators** (`illustrators/`) | Same surface as Storytellers; single-channel output | DB models, FastAPI |
| **Background tasks** (`api/v3/tasks.py`) | Storyteller runtime, persistence (Image/Video/Frame), realtime writer | HTTP layer, frontend |
| **API** (`api/v3/`) | Auth dependencies, DB sessions, Pydantic schemas | Inference details, Firestore wire format |
| **Realtime** (`realtime/`) | Firestore writes for `tasks/{task_id}` | Postgres content, inference |
| **Vector** (`vector/`) | pgvector queries, the configured embedding client | API surface, frontend |
| **Migration** (`migration/`) | Both schemas — read-only against legacy | The running app (it's a CLI) |

Pure-functional dependencies flow downward in that list. The
**Storyteller / Illustrator → Inference** boundary is the most important
to preserve: Storytellers never instantiate clients directly; they ask
`get_client(provider_name)`. That's what lets a YAML edit swap an entire
model family.

## Data model — quick reference

Six tables. See [`apps/api/calliope2/db/models/`](../apps/api/calliope2/db/models/)
for the full SQLAlchemy 2.0 definitions.

| Table | Purpose | Key columns |
|---|---|---|
| `users` | Authenticated users | `firebase_uid` (unique), `email`, `display_name`, `is_admin` |
| `stories` | Story container | `owner_id` FK→User, `slug`, `storyteller_name`, `metadata` JSONB |
| `story_frames` | Per-frame content | `story_id`, `number`, `text`, `image_id`, `video_id`, `embedding vector(1536)` |
| `images` | GCS-hosted images | `gcs_uri`, dims, `format`, `content_hash` |
| `videos` | GCS-hosted videos | `gcs_uri`, dims, `duration_seconds`, `frame_rate` |
| `bookmarks` | User saves | `owner_id`, `story_id`, optional `frame_id`, `list_name`, `is_public` |

JSONB `metadata` on `stories` / `story_frames` carries legacy-id markers
during migration ([`concepts/migration`](ops/migration.md)) and is
otherwise free for storyteller-specific state.

Two Alembic migrations:
- `0001_initial` — all 6 tables, 14 FKs, indexes
- `0002_pgvector` — `CREATE EXTENSION vector`; ALTER TABLE story_frames
  ADD `embedding vector(1536)`; HNSW cosine-distance index

## What runs where

Each `apps/web/*` app and the FastAPI app are independent Cloud Run
services in the production target:

```
Cloud Run service "calliope-v3"  ─►  apps/api/calliope2 (FastAPI)
                                     mounts: /clio/, /admin/, /v3/*
Cloud Run service "calliope-v1"  ─►  /calliope/ (legacy Piccolo)
                                     mounts: /clio/ (v1), /thoth/, /admin/ (Piccolo)
GCP project                      ─►  Postgres + pgvector (Cloud SQL)
                                     Firestore (single db, two collections used)
                                     Cloud Storage (one bucket; both apps share)
                                     Firebase Auth (one project; both apps share)
```

A load balancer or DNS switch picks which service serves end users;
during cutover both can be up. The ESP32 / hardware sparrow path stays
on the v1 service indefinitely per the modernization plan.

## Tech stack snapshot

- **Python**: 3.11; FastAPI; SQLAlchemy 2.0 async; pgvector; pydantic v2;
  pydantic-settings; firebase-admin; google-cloud-firestore; openai
  (≥1.50); replicate (≥1.0); tenacity; Typer; Jinja2.
- **Frontend**: TypeScript; React 18; Firebase Web SDK 10; axios.
  - Clio: Webpack (inherited from v1 fork).
  - Admin: Vite (new build).
- **Tooling**: uv (workspace + lock); ruff; pytest + pytest-asyncio +
  aiosqlite for tests; alembic for schema.

## Where to look next

- Each subsystem has a concept doc in [`concepts/`](concepts/).
- Why we picked these tools / patterns: [`decisions/`](decisions/).
- How to run any of it: [`ops/local-dev.md`](ops/local-dev.md).
