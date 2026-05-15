# Realtime status

Clio shows live progress while a story is generating: "running… 40% …
done". The mechanism is a single Firestore collection,
`tasks/{task_id}`, that the backend writes to and the frontend
subscribes to. **Postgres remains the source of truth for content;
Firestore is purely a status mailbox.** See [`ADR 0006`](../decisions/0006-narrowed-firestore-mailbox.md).

The module lives at
[`apps/api/calliope2/realtime/`](../../apps/api/calliope2/realtime/).

## The document shape

```jsonc
// tasks/{task_id}
{
  "user_id":      7,              // int — Postgres User.id
  "story_id":     42,
  "type":         "create_story", // or "create_frame"
  "status":       "running",      // pending | running | completed | failed
  "progress":    0.0,             // 0.0–1.0
  "error":       null,            // string when status == failed
  "started_at":  2026-05-13T12:00:00Z,
  "completed_at": null            // set when status in {completed, failed}
}
```

The Pydantic shape is [`TaskRecord`](../../apps/api/calliope2/realtime/task_status.py).
`TaskStatus` and `TaskType` are `StrEnum`s — JSON serialization gives
plain strings, which is what Firestore + the JS client expect.

## Writer API

```python
from calliope2.realtime import get_task_writer, TaskRecord, TaskType

writer = get_task_writer()

await writer.started(TaskRecord(task_id=..., user_id=..., story_id=...,
                                type=TaskType.CREATE_STORY,
                                started_at=now))
await writer.progress(task_id, 0.4)         # optional mid-task signal
await writer.completed(task_id)
await writer.failed(task_id, "openai timed out")
```

The `TaskWriter` Protocol:

```python
class TaskWriter(Protocol):
    async def started(self, task: TaskRecord) -> None: ...
    async def progress(self, task_id: str, progress: float) -> None: ...
    async def completed(self, task_id: str) -> None: ...
    async def failed(self, task_id: str, error: str) -> None: ...
```

Two implementations:

- **`FirestoreTaskWriter`** — wraps `google.cloud.firestore.AsyncClient`
  and writes to the `tasks` collection. **Write errors are caught and
  logged.** The wrapping `_safe_write()` ensures a Firestore outage
  never propagates into the calling task.
- **`LoggingTaskWriter`** — no-op fallback that logs the same calls.
  Used when `firebase_project_id` is empty (local-dev default).

`get_task_writer()` picks one based on settings:

```python
@lru_cache(maxsize=1)
def get_task_writer() -> TaskWriter:
    settings = get_settings()
    if not settings.firebase_project_id:
        return LoggingTaskWriter()
    from google.cloud.firestore import AsyncClient
    client = AsyncClient(project=settings.firebase_project_id)
    return FirestoreTaskWriter(client)
```

Tests reset the cache via `reset_task_writer_cache()`.

## How the frontend reads it

From [`apps/web/clio/src/services/firebase.ts`](../../apps/web/clio/src/services/firebase.ts):

```typescript
// Watch all tasks for a story (filtered to the current user)
watchTasksForStory(userId, storyId, (tasks: TaskStatus[]) => {
  // re-render with new task statuses
});

// Or watch a single task
watchTask(taskId, (status: TaskStatus | null) => { ... });
```

The Firestore query is
`where('user_id', '==', userId) AND where('story_id', '==', storyId)`.
That's why `user_id` lives on every document and why routes thread
`user.id` into the background task ([`background-tasks.md`](background-tasks.md)).

## Why best-effort

The plan calls Firestore "a status mailbox, not durable state". If a
write fails:

- The story generation still completes (or fails) on its own merits;
  the work is in Postgres.
- Clio's listener simply doesn't see the update. The next time the
  page loads, `GET /v3/stories/{id}` returns the actual state from
  Postgres.
- The error is logged so we can diagnose Firestore-side problems
  without firefighting a content outage.

This is the same shape the embedding step uses
([`vector-search.md`](vector-search.md)): the side-channel failure
mode is "log and continue", because the primary work is what users
care about.

## Configuration

| Setting | Env var | Default | Notes |
|---|---|---|---|
| `firebase_project_id` | `CALLIOPE2_FIREBASE_PROJECT_ID` | `""` | When empty, `get_task_writer` returns `LoggingTaskWriter` |

In production, `google.cloud.firestore.AsyncClient(project=...)` uses
Application Default Credentials (the Cloud Run service-account
identity).

## What's *not* here

- **SSE / WebSocket** fallback for clients without Firestore — deferred.
  Firestore subscriptions are the only realtime path today.
- **Append-only event log** — gone. The legacy `stories/{id}/updates`
  collection isn't replaced. If we ever want timeline data, we add it
  to Postgres (or the task document).
- **Reliable delivery** — the writer is at-most-once. Re-emit logic
  isn't built; if Firestore is down for the entire lifecycle of a task,
  the client never sees a status update.

## Tests

[`apps/api/tests/test_realtime_writer.py`](../../apps/api/tests/test_realtime_writer.py)
covers:

- `LoggingTaskWriter` satisfies the protocol; all methods are callable.
- `FirestoreTaskWriter.started/progress/completed/failed` write the
  expected document shape (with a mocked `firestore.AsyncClient`).
- A Firestore write failure is swallowed, not raised.
- `get_task_writer()` selects the right implementation by
  `firebase_project_id`.
- `TaskRecord` validation (bounded progress, defaults).

[`apps/api/tests/test_v3_task_status_emission.py`](../../apps/api/tests/test_v3_task_status_emission.py)
covers the task-layer wiring: `started → completed` on success,
`started → failed` on storyteller error.

## Related

- [`background-tasks.md`](background-tasks.md) — who calls the writer.
- [`auth.md`](auth.md) — how `user.id` (Postgres) maps to `user_id` on
  the task document.
- [`ADR 0006`](../decisions/0006-narrowed-firestore-mailbox.md) — why
  this collection design.
