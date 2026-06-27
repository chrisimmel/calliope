# Vector search

Frames are searchable by meaning, not just keyword. Each
`StoryFrame.text` is embedded with a configurable model (default:
OpenAI `text-embedding-3-small`, 1536 dimensions) and stored in the
`embedding vector(1536)` column. Search queries embed the query string
and rank frames by cosine distance.

Backed by **pgvector on Cloud SQL** — no Pinecone, no LangChain. See
[`ADR 0002`](../decisions/0002-pgvector-over-pinecone-langchain.md).

The module lives at
[`apps/api/calliope2/vector/`](../../apps/api/calliope2/vector/).

## Where embeddings come from

Two paths get embeddings into the column:

### 1. Embed-on-create (online, best-effort)

When a background task persists a `StoryFrame` with text, it tries to
embed inline:

```python
# api/v3/tasks.py
embedding = await try_embed_text(output.text) if output.text else None
...
frame = StoryFrame(
    story_id=story_id, number=frame_number,
    text=output.text,
    embedding=embedding,
    ...
)
```

`try_embed_text` swallows failures and returns `None`. If the embedding
provider is down, the frame is still persisted; the column stays NULL.
The reindex CLI catches up later. This is the same "best-effort
side-channel" pattern as the realtime writer ([`realtime.md`](realtime.md)).

### 2. Reindex CLI (batch, offline)

```bash
uv run calliope2-cli vector reindex                # backfill all NULL embeddings
uv run calliope2-cli vector reindex --dry-run      # count what would happen
uv run calliope2-cli vector reindex --limit 100    # cap, for staged runs
uv run calliope2-cli vector reindex --batch-size 50
```

Selects `StoryFrame` rows where `embedding IS NULL`, embeds each
`frame.text`, commits in batches. Logs:

```
candidates=412 embedded=410 skipped_no_text=2 failed=0
```

The command lives at
[`apps/cli/calliope2_cli/commands/vector.py`](../../apps/cli/calliope2_cli/commands/vector.py).

## Search API

### Endpoint

`GET /v3/search?q=<query>&limit=<n>`

```python
@router.get("", response_model=SearchResponse)
async def search(user: CurrentUser, session: SessionDep,
                 q: str = Query(..., min_length=1),
                 limit: int = Query(20, ge=1, le=100)):
    embedding = await embed_text(q)
    hits = await search_frames(session, embedding,
                               owner_id=user.id, limit=limit)
    return SearchResponse(query=q, hits=[...])
```

Response shape (`SearchResponse`):

```jsonc
{
  "query": "quiet kitchen",
  "hits": [
    {
      "frame_id": 200,
      "story_id": 42,
      "story_title": "Sun on the linoleum",
      "frame_number": 1,
      "frame_text": "Sun on the linoleum...",
      "image_url": "gs://b/i.png",
      "distance": 0.21
    },
    ...
  ]
}
```

Errors:
- Empty `q` or out-of-range `limit` → **422** (FastAPI's automatic
  Pydantic validation).
- Embedding-service failure → **502** with the error detail.

### Admin variant

`GET /v3/admin/search?q=` is the cross-user counterpart. Same shape,
but the search isn't scoped to `owner_id` and each hit carries
`owner_id` + `owner_email`. Admin-only (`AdminUser` dependency).

See [`apps/api/calliope2/api/v3/admin/search.py`](../../apps/api/calliope2/api/v3/admin/search.py).

## How the query runs

[`vector/search.py`](../../apps/api/calliope2/vector/search.py):

```python
distance = StoryFrame.embedding.cosine_distance(list(embedding))
stmt = (
    select(StoryFrame.id, StoryFrame.story_id, StoryFrame.number,
           StoryFrame.text, Story.title, Image.gcs_uri,
           distance.label("distance"))
    .join(Story, StoryFrame.story_id == Story.id)
    .outerjoin(Image, StoryFrame.image_id == Image.id)
    .where(StoryFrame.embedding.is_not(None))
    .order_by(distance)
    .limit(limit)
)
if owner_id is not None:
    stmt = stmt.where(Story.owner_id == owner_id)
```

`.cosine_distance(vec)` comes from pgvector's SQLAlchemy integration
and compiles to the `<=>` operator on Postgres. The HNSW index
(`USING hnsw (embedding vector_cosine_ops)`, created in
`0002_pgvector`) makes the `ORDER BY distance LIMIT N` query fast.

## Configuration

| Setting | Env var | Default | Notes |
|---|---|---|---|
| `embedding_provider` | `CALLIOPE2_EMBEDDING_PROVIDER` | `"openai"` | Key in `get_client()` registry |
| `embedding_model` | `CALLIOPE2_EMBEDDING_MODEL` | `"text-embedding-3-small"` | Passed to `client.embed(model=...)` |
| `embedding_dim` | `CALLIOPE2_EMBEDDING_DIM` | `1536` | Must match the column's `vector(N)` |

If you switch to a different-dimension model, you'll need a migration
to alter the column type (and a full re-embed). The dimension is
checked at write time — pgvector raises if a vector of the wrong
length is inserted.

## Test infrastructure

pgvector's `Vector` type has no SQLite implementation, so tests
register a DDL compile override that emits `TEXT` on SQLite:

```python
# tests/conftest.py
@compiles(Vector, "sqlite")
def _vector_as_text_on_sqlite(_type, _compiler, **_kw) -> str:
    return "TEXT"
```

All Phase 4+ tests leave `embedding` NULL, so no bind/result processing
is exercised. The exception is the reindex CLI test
([`apps/api/tests/test_cli_vector_reindex.py`](../../apps/api/tests/test_cli_vector_reindex.py))
which writes a `list[float]` to the column — that round-trips cleanly
through pgvector's serializer-as-string on SQLite because the embedding
isn't queried.

See [`ADR 0002`](../decisions/0002-pgvector-over-pinecone-langchain.md)
for the broader cost/benefit and [`ADR 0008`](../decisions/0008-fastapi-runtime-annotations.md)
for the test-infrastructure pattern.

## What's *not* here

- **Hybrid search** (BM25 + vector). pgvector doesn't include
  full-text natively; we could add `tsvector` and a re-rank pass, but
  haven't needed it.
- **Per-storyteller / per-image filtering** beyond owner scope.
  Trivial to add as `where(...)` clauses on the query when needed.
- **Vector caching** for repeat queries. Embeddings are deterministic
  per model; if traffic warrants we can cache in Redis or in-process.

## Tests

- [`apps/api/tests/test_vector_embedding.py`](../../apps/api/tests/test_vector_embedding.py)
  — `embed_text` dispatches to the configured client; `try_embed_text`
  swallows errors.
- [`apps/api/tests/test_v3_search.py`](../../apps/api/tests/test_v3_search.py)
  — the route shape, 502 on embedding failure, 422 on bad input.
- [`apps/api/tests/test_cli_vector_reindex.py`](../../apps/api/tests/test_cli_vector_reindex.py)
  — reindex selects only NULL-embedding rows with text, batches commits,
  records failure counts.

## Related

- [`storytellers.md`](storytellers.md) — frames come from storyteller
  output.
- [`background-tasks.md`](background-tasks.md) — embed-on-create is
  inside the task layer.
- [`ADR 0002`](../decisions/0002-pgvector-over-pinecone-langchain.md) —
  why pgvector.
