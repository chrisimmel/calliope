# Migration & cutover playbook

The legacy `/calliope/` app keeps running on its own Cloud Run service
while the new `calliope2/` app comes up alongside. This document is the
runbook for **moving content into the new DB and switching users to
the new app**.

The contract that matters most:

> **The legacy DB is never written to.** Migration reads only. The legacy
> service stays serving traffic until the explicit cutover step.

That's enforced in code ([`migration/migrate.py`](../../apps/api/calliope2/migration/migrate.py)
issues only `SELECT`s against the legacy engine) and should be enforced
operationally too — configure the legacy DB user with read-only grants
when the migration runs.

## What gets migrated

The seven legacy tables read by the migration:

| Legacy table | New destination |
|---|---|
| `sparrowstate` | `users` (each sparrow becomes a placeholder User with `firebase_uid = legacy:<sparrow_id>` unless overridden by `--sparrow-map`) |
| `image` | `images` (dedupe by `gcs_uri`) |
| `video` | `videos` (dedupe by `gcs_uri`) |
| `story` | `stories` (legacy_id stored in `metadata->>'legacy_id'`) |
| `storyframe` | `story_frames` (same idempotency marker) |
| `bookmarklist` + `storybookmark` + `storyframebookmark` | `bookmarks` (consolidated; (owner, story, frame, list_name) natural key) |

What stays on legacy:
- The `prompt_template`, `inference_model`, `model_config`,
  `strategy_config`, `client_type_config`, `sparrow_config` config
  tables. v3 doesn't have equivalent tables — that content lives in
  YAML files under `apps/api/calliope2/storytellers/` (and Phase 10's
  Illustrators).
- Hardware sparrows (ESP32 devices). The plan keeps the legacy app live
  indefinitely for the hardware path. Sparrows with no real web origin
  become orphaned placeholder Users in v3 — harmless, easy to clean up
  later if desired.

## The CLI

```
uv run calliope2-cli migrate from-v1 \
  --source-url postgresql+asyncpg://USER:PASS@HOST/DB \
  [--dry-run] \
  [--limit N] \
  [--sparrow-map sparrows.json] \
  [--user-prefix legacy:]
```

| Flag | Effect |
|---|---|
| `--source-url` | Legacy Postgres URL. Use a read-only role in production. Env: `CALLIOPE2_LEGACY_DATABASE_URL`. |
| `--dry-run` | Reads everything, builds the would-write maps, reports counts, writes nothing. |
| `--limit N` | Caps the number of legacy stories considered. Useful for staged runs; frames whose parent story isn't migrated get counted as orphans. |
| `--sparrow-map FILE` | JSON `{sparrow_id: firebase_uid}`. Maps known sparrows to their real Firebase UIDs so their stories land attached to the right post-cutover user. Unmapped sparrows become `legacy:<sparrow_id>` placeholders. |
| `--user-prefix` | Prefix for placeholder firebase_uids. Default `legacy:`. |

## Idempotency

Run the migration as many times as you want. Existing rows are
skipped:

- **Users**: keyed by `firebase_uid`. Existing rows are not
  overwritten.
- **Images / Videos**: dedupe by `gcs_uri`.
- **Stories / Frames**: `metadata->>'legacy_id'` marker is set on every
  migrated row. Pre-scan at the start of each run builds a `legacy_id
  → new_id` map; rows already present are skipped (and counted as
  `*_skipped_existing`).
- **Bookmarks**: dedupe by `(owner_id, story_id, frame_id, list_name)`.

Two consecutive real runs of the same legacy DB produce identical state
on the new DB.

## The cutover sequence

### 1. Stand up the v3 services

Before migrating anything:

1. Provision Postgres (Cloud SQL) with `pgvector`. Apply the
   migrations:
   ```bash
   cd calliope2/apps/api
   uv run alembic upgrade head
   ```
2. Configure Firebase (project ID, service-account credentials) for the
   new Cloud Run service.
3. Configure inference API keys (OpenAI / Replicate / Runway).
4. Deploy the new app to a **separate Cloud Run service** —
   `calliope-v3`, distinct from the legacy `calliope-v1`. Both can be
   up; only the legacy one currently receives user traffic.
5. Smoke `GET /v3/health` against the new service.

### 2. Dry-run migration

```bash
uv run calliope2-cli migrate from-v1 \
  --source-url $LEGACY_DB_URL \
  --dry-run
```

Inspect the counts. Expected pattern: lots of `*_created`, zero
`*_skipped_existing` (first run), zero `errors`. If `stories_skipped_no_owner`
is non-zero, those stories have a `created_for_sparrow_id` that isn't
in any `sparrowstate` row — examine why, decide whether to fix the
legacy data first or accept the loss.

### 3. (Optional) Build a sparrow → firebase_uid map

If you know which sparrows correspond to which Google identities,
write a JSON file:

```json
{
  "chris": "firebase-uid-for-chris@gmail.com",
  "alice": "firebase-uid-for-alice@gmail.com"
}
```

These users will sign in with Google after cutover and see their
existing stories already attached to their `User` row. Unmapped
sparrows become placeholder Users; their stories show up if a future
"claim my legacy stories" UI is built (none today).

### 4. Real migration

```bash
uv run calliope2-cli migrate from-v1 \
  --source-url $LEGACY_DB_URL \
  --sparrow-map sparrows.json
```

Re-run is safe if interrupted. The CLI prints a per-phase summary at
the end:

```
users:     created=12 skipped_existing=0
images:    created=4521 skipped_existing=0
videos:    created=3 skipped_existing=0
stories:   created=87 skipped_existing=0 skipped_no_owner=0
frames:    created=2340 skipped_existing=0 skipped_orphan_story=0
bookmarks: created=15 skipped_existing=0 skipped_orphan=0
```

### 5. Backfill embeddings

The migrated frames don't carry legacy embeddings. The new app's
embed-on-create only fires for new frames. Backfill:

```bash
uv run calliope2-cli vector reindex
```

Watch the output for `failed=N` — if embedding API quota throttles
you, re-run; failures are retried on the next pass since they leave
the column NULL.

### 6. Verify

Spot-check ~5 stories end-to-end:

- `GET /v3/admin/stories?q=<title>` returns them (admin login required).
- Click into a story; frames load with correct `image_url`s.
- `GET /v3/admin/search?q=<distinctive phrase>` finds the right frame.
- Compare against `/thoth/story/<cuid>` on the legacy app for fidelity.

### 7. Switch user-visible traffic

Until now, all user traffic still hits the legacy `calliope-v1`
service. To cut over:

- Either flip a load-balancer URL map rule (preferred), or
- Update DNS to point the user-facing hostname at `calliope-v3`.

Per the plan, **DNS / load-balancer switch is the cutover** — not a
code deploy. This makes rollback trivial (flip back).

### 8. Decommission (eventually)

After parity is comfortable:

- v1 Clio is no longer served; the v1 service can serve only the ESP32
  hardware path (it stays live indefinitely per the plan).
- `/thoth/` and `/admin/` (Piccolo Admin) on the legacy service are
  replaced by `/admin/` on the v3 service. The v1 service no longer
  needs those routes; they can be removed or just ignored.
- The legacy DB and the new DB are now independent. The legacy DB
  remains the source of truth for hardware-only stories; new
  user-facing stories live in the new DB.

## What can go wrong

- **Legacy DB user has write grants**: the CLI only issues SELECT, but
  defense in depth says scope the role. `GRANT SELECT ON ALL TABLES IN
  SCHEMA public TO calliope_readonly;`
- **Mid-run interrupt**: safe. Re-run. Idempotency handles it.
- **Half the embeddings failed**: re-run `vector reindex`. Failures
  leave the column NULL, so they're picked up next time.
- **A migrated story shows up with no frames**: the parent story
  migrated but `frames_skipped_orphan_story` was non-zero — almost
  always means `--limit` truncated the story selection but you forgot
  to remove it.
- **Cutover happens but a user reports missing content**: check whether
  their sparrow had a real `--sparrow-map` entry. If not, their content
  is under `firebase_uid='legacy:<their_sparrow_id>'`, not their
  Google UID. Manually update:
  ```sql
  UPDATE users SET firebase_uid = 'firebase-uid-...'
   WHERE firebase_uid = 'legacy:chris';
  ```

## What's not automated (yet)

- A "claim your legacy stories" UI for users to link their post-cutover
  Google identity to a `legacy:<sparrow_id>` placeholder. The schema
  supports it (just update `users.firebase_uid`), but no endpoint
  exposes it. Build when needed.
- The cutover itself — the DNS / load-balancer switch is manual.

## Related

- [`migration/migrate.py`](../../apps/api/calliope2/migration/migrate.py)
  — the orchestrator.
- [`migration/legacy_schema.py`](../../apps/api/calliope2/migration/legacy_schema.py)
  — hand-written SQLAlchemy Core Table defs for the legacy schema.
- [`apps/api/tests/test_migration.py`](../../apps/api/tests/test_migration.py)
  — round-trip / dry-run / idempotency tests with two in-memory
  SQLite engines.
- [`ADR 0005`](../decisions/0005-clio-fork-not-move.md) — why Clio is a
  fork, not a move; sets up the cutover-via-DNS pattern.
