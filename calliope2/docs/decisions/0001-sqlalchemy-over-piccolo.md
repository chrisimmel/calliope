# 0001 — SQLAlchemy 2.0 over Piccolo

Date: 2026-05-13
Status: Accepted

## Context

The legacy `/calliope/` app uses [Piccolo](https://piccolo-orm.com/) for
its ORM and migrations. Piccolo is a small, async-native ORM with its
own admin UI (`piccolo_admin`) and migration system. It has worked, but
it's niche — limited middleware, fewer integrations, smaller community.

For the v3 rewrite we wanted to remove a category of friction: every
time we needed to integrate with a tool from the broader Python data
ecosystem (sqladmin, alembic, sqlmodel snippets, dataclass adapters,
type stubs, IDE inspection), Piccolo was a roadblock.

## Decision

Use **SQLAlchemy 2.0** with `async_engine` + `async_sessionmaker`, the
`Mapped` / `mapped_column` declarative syntax, and **Alembic** for
migrations. Keep Postgres-specific types (`JSONB`, pgvector `Vector`)
because we'll never deploy on anything else.

## Consequences

**Wins:**
- Standard SQLAlchemy code is the most-documented pattern in the Python
  data ecosystem; new contributors don't need to learn a niche library.
- Alembic is the de-facto migration tool. Async support is mature.
- pgvector's SA integration (`.cosine_distance()` etc.) just works.
- IDE / type-checker support is excellent.

**Costs:**
- More boilerplate than Piccolo for simple models. Acceptable; the
  payoff is at every other layer.
- We had to hand-write SQLite compile overrides for `Vector` and `JSONB`
  to make the test backend work. See
  [`decisions/0008`](0008-fastapi-runtime-annotations.md) (related test-
  infrastructure trade-off).

## Alternatives considered

- **Stay on Piccolo.** Lowest migration cost but locks us into the
  niche-tool problem indefinitely.
- **SQLModel.** Combines SA + Pydantic. Considered, but it has rough
  edges with async + complex relationships and doesn't materially reduce
  code volume over SA 2.0's modern syntax.
- **Tortoise / Edgy / others.** All async-native ORMs, but each carries
  Piccolo's same "small community" problem with extra migration cost.

## Related

- [`db/base.py`](../../apps/api/calliope2/db/base.py)
- [`db/session.py`](../../apps/api/calliope2/db/session.py)
- [`db/models/`](../../apps/api/calliope2/db/models/)
- `alembic/versions/0001_initial.py`, `0002_pgvector.py`
