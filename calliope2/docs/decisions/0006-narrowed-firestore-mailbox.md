# 0006 — Single `tasks/{task_id}` Firestore collection

Date: 2026-05-13
Status: Accepted

## Context

The legacy app writes realtime status across three Firestore
collections: `stories/{id}` (story-level state), `stories/{id}/updates`
(append-only event log), and `tasks/{id}` (per-job state). The shapes
overlap, the writers are scattered, and clients have to merge data from
multiple snapshot listeners to render a coherent view. Every new event
type required reasoning about which of the three collections it
belonged in.

It also wasn't clear what role Firestore played: the legacy code
sometimes treated it as durable state (story snapshots had fields that
existed nowhere else), making schema changes nervous.

## Decision

**One collection: `tasks/{task_id}`.** Postgres is the single source of
truth for content (stories, frames, images). Firestore is a status
mailbox: clients subscribe to get live progress updates, and that's it.

Each document carries:

```
{
  user_id, story_id, type, status, progress,
  error?, started_at, completed_at?
}
```

Clio listens with `where('user_id', '==', currentUid)`, optionally
narrowed by `story_id`. Writes are best-effort — Firestore errors are
caught and logged but never propagated, so a Firestore outage cannot
fail a story generation.

When `CALLIOPE2_FIREBASE_PROJECT_ID` is empty (the local-dev default),
`get_task_writer()` returns a `LoggingTaskWriter` that just logs the
status updates. No Firebase access is required for local development.

## Consequences

**Wins:**
- Clients have one listener pattern, not three.
- New event types just need to choose a `type` value; no
  collection-design conversation.
- Schema changes are scoped to one document shape.
- Local dev is unblocked from needing Firebase access at all.
- Firestore outages can no longer fail story generation.

**Costs:**
- The append-only event log from the legacy `stories/{id}/updates`
  collection is gone. If we ever need fine-grained timeline data for a
  task, we'll add it as fields on the task document or store it in
  Postgres (the embedding lifecycle is a precedent — we log to stdout
  for development).
- Story-level state that lived on `stories/{id}` in Firestore is now in
  Postgres only. Clients fetch story content via `GET /v3/stories/{id}`
  rather than subscribing to it. This is a feature, not a bug — story
  content shouldn't be in a status mailbox.

## Alternatives considered

- **Keep the 3-collection schema.** Carries the existing complexity
  forward with no upside; the new app doesn't have any legacy clients
  that need the old shape (v3 Clio is a fork).
- **Replace Firestore entirely with SSE / WebSocket from FastAPI.**
  Considered. Firestore's free tier and managed client subscriptions
  beat building our own pub/sub for this scale, and Clio already had
  the Firestore client wired up.

## Related

- [`concepts/realtime.md`](../concepts/realtime.md)
- [`realtime/`](../../apps/api/calliope2/realtime/)
