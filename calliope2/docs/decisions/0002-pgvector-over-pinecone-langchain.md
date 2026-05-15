# 0002 — pgvector over Pinecone + LangChain

Date: 2026-05-13
Status: Accepted

## Context

The legacy app uses Pinecone for vector storage and LangChain as the
embedding wrapper (`/calliope/storage/vector_manager.py`). Calliope is a
small-traffic project — single-digit thousands of frames, low query
volume. Pinecone's free tier and LangChain's abstraction layer both
cost more than they earn at this scale:

- **Pinecone** is a separate hosted service with its own auth, billing,
  and outage envelope.
- **LangChain** adds a large dependency tree and an indirection that we
  hit-tested once and never used the flexibility of.

We already pay for Postgres on Cloud SQL. Postgres has had pgvector for
years, and it supports HNSW indexes with cosine distance — which is all
this app needs.

## Decision

Store embeddings as a `vector(1536)` column on `story_frames`. Use the
HNSW index with `vector_cosine_ops`. Query via SQLAlchemy + pgvector's
SA integration (`StoryFrame.embedding.cosine_distance(query_vec)`).
Embedding generation goes through the same provider-agnostic
`InferenceClient` as everything else (default: OpenAI
`text-embedding-3-small`).

Drop `langchain*`, `pinecone*`, `langchain-pinecone` from the dependency
list.

## Consequences

**Wins:**
- One fewer hosted service to manage. One fewer outage envelope.
- Search joins naturally with `Story` and `Image` rows — no
  cross-system reconciliation.
- pgvector's HNSW index is fast enough for our scale (and far beyond).
- The reindex story is a single CLI: `calliope2-cli vector reindex`.

**Costs:**
- pgvector's `Vector` type has no SQLite implementation, so test
  infrastructure registers a `Vector → TEXT` DDL compile override.
  Tests leave `embedding` NULL since they don't exercise vector queries.
  See [`concepts/vector-search.md`](../concepts/vector-search.md) and
  [`decisions/0008`](0008-fastapi-runtime-annotations.md).
- We're committed to Postgres. If a future deployment needs a different
  backing store, the abstraction is thin enough to swap without much
  code change, but the search query (`.cosine_distance()`) leaks
  pgvector specifics.

## Alternatives considered

- **Keep Pinecone.** Operational simplicity until traffic grows; not
  worth the cost at our scale.
- **pgvector inside Supabase.** The plan ruled out Supabase as a
  cross-cloud dependency.
- **Embedded vector store (FAISS / Chroma).** Would require a separate
  process or shared volume; loses transactional consistency with the
  story/frame rows. Postgres + pgvector wins on simplicity.

## Related

- [`concepts/vector-search.md`](../concepts/vector-search.md)
- [`vector/embedding.py`](../../apps/api/calliope2/vector/embedding.py)
- [`vector/search.py`](../../apps/api/calliope2/vector/search.py)
- [`apps/cli/calliope2_cli/commands/vector.py`](../../apps/cli/calliope2_cli/commands/vector.py)
- `alembic/versions/0002_pgvector.py`
