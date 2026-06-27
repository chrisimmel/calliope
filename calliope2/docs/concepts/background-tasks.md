# Background tasks

`POST /v3/stories` and `POST /v3/stories/{id}/frames` don't generate
content inline — they enqueue a **background task** that does the
inference, persistence, and status writes. The request returns
**202 Accepted** with a `task_id`; the client subscribes to
`tasks/{task_id}` in Firestore for progress.

The task layer is at
[`apps/api/calliope2/api/v3/tasks.py`](../../apps/api/calliope2/api/v3/tasks.py).

## What runs the background task

FastAPI's built-in `BackgroundTasks` — same async event loop as the
request handler, runs after the response is sent. **Not** a separate
worker process or queue (Celery, Cloud Tasks, etc.). At our traffic
this is fine; if traffic grows we'd swap to Cloud Tasks behind the same
function signature without changing the storyteller or persistence
layer.

The route enqueues:

```python
@router.post("", response_model=StoryCreateResponse, status_code=202)
async def create_story(body, user: CurrentUser, session: SessionDep,
                       background: BackgroundTasks):
    # ... validate, INSERT Story ...
    task_id = new_task_id()
    background.add_task(
        generate_first_frame, task_id, story.id, user.id,
        body.storyteller, body.inputs,
    )
    return StoryCreateResponse(story_id=story.id, task_id=task_id)
```

## What the background task does

```python
async def generate_first_frame(task_id, story_id, user_id, storyteller_name, inputs):
    writer = get_task_writer()
    record = TaskRecord(task_id=..., user_id=..., story_id=...,
                        type=TaskType.CREATE_STORY, started_at=now)
    await writer.started(record)
    try:
        output = await run_storyteller(storyteller_name, _prepare_inputs(inputs))
        await _persist_frame(story_id, frame_number=1, output=output)
        await writer.completed(task_id)
    except Exception as e:
        await writer.failed(task_id, str(e))
        raise
```

Six things happen:

1. **Start status write**: `writer.started(record)` writes
   `tasks/{task_id}` in Firestore (or logs, locally). See
   [`realtime.md`](realtime.md).
2. **Input preparation**: `_prepare_inputs()` converts API-shaped
   inputs into storyteller-ready shapes (e.g., `source_image_url`
   string → `source_image: ImageBlob(url=...)`).
3. **Storyteller invocation**: `run_storyteller(name, inputs)` executes
   the YAML pipeline. See [`storytellers.md`](storytellers.md).
4. **Embed-on-create**: `_persist_frame` calls `try_embed_text(frame.text)`
   before commit. Failures log and leave `embedding=NULL`; the reindex
   CLI catches up. See [`vector-search.md`](vector-search.md).
5. **Persistence**: Image / Video rows are inserted (if the output has
   a URL); the StoryFrame row is inserted with the right FKs and
   timestamps.
6. **Completion / failure status write**: `writer.completed(task_id)` or
   `writer.failed(task_id, str(e))`. The exception is re-raised so the
   FastAPI logger sees the traceback.

## Continuation frames

`generate_next_frame(task_id, story_id, user_id, inputs)` loads the
most recent frame and threads its content into the storyteller inputs:

```python
threaded = _prepare_inputs(inputs) | {
    "previous_text": last_frame.text or "",
    "previous_image": ImageBlob(url=last_frame.image.gcs_uri) if last_frame.image else None,
}
```

The continuous-style storytellers (`continuous_v1`, `lavender`) use
`previous_text` to branch in their Jinja templates between "begin a new
story" and "continue from here".

## Persistence boundary

Storytellers return `FrameOutput(text, image, video)` — plain DTOs.
They never touch the database. Persistence happens in `_persist_frame`,
which:

- Skips bytes-only `ImageBlob`/`VideoBlob` outputs (no `url`) with a
  TODO log line. The storage phase (not yet built) will upload bytes to
  GCS and set the URL; for now, only URL-bearing outputs are persisted.
- Inserts `Image` / `Video` rows via their `gcs_uri`. The migration
  ([`ops/migration.md`](../ops/migration.md)) uses the same dedupe-by-URL
  pattern.
- Inserts the `StoryFrame` row with FKs to the new Image / Video.
- Sets `embedding` if `try_embed_text` succeeded.

## Why this shape

| Choice | Alternative | Why |
|---|---|---|
| `BackgroundTasks` instead of Cloud Tasks / Celery | Real queue | Today's traffic doesn't justify the operational complexity; swap is local-change-only |
| `task_id` returned, not awaited | Long-polling / sync inference | Inference takes 10s+; HTTP timeouts and proxy buffers don't tolerate that |
| Status writes best-effort (not transactional) | Persistent task queue with reliable status | Firestore is a status mailbox, not durable state; the work is durable in Postgres regardless ([`ADR 0006`](../decisions/0006-narrowed-firestore-mailbox.md)) |
| Embed inline with persistence | Separate embed background task | One commit, simpler reasoning; if embedding becomes a bottleneck we can lift it out |

## Caveats

- **In-process means at-least-once is hard.** If the FastAPI worker
  crashes mid-task, no retry. For now we accept this; users see a
  "running" task that never completes and can re-issue the request.
- **No backpressure.** Many concurrent story creations will run as
  many concurrent storyteller pipelines in one worker, fighting for
  the same event loop and OpenAI rate limits. Tenacity in the
  inference clients handles transient errors; sustained high load
  needs Cloud Tasks.
- **No task cancellation.** Once `BackgroundTasks` starts a coroutine,
  the user can't cancel it. Restart the worker if necessary.

## Tests

- [`apps/api/tests/test_v3_task_status_emission.py`](../../apps/api/tests/test_v3_task_status_emission.py)
  patches `run_storyteller` and `_persist_frame` with `AsyncMock`s and
  verifies the task layer's status writes (started → completed; started
  → failed) without doing any inference or DB work.
- [`apps/api/tests/test_v3_stories.py`](../../apps/api/tests/test_v3_stories.py)
  asserts the HTTP layer enqueues the right task with the right
  arguments.

## Related

- [`storytellers.md`](storytellers.md) — what `run_storyteller` does.
- [`realtime.md`](realtime.md) — the status writes.
- [`vector-search.md`](vector-search.md) — the embed-on-create step.
