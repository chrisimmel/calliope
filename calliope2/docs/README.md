# calliope2 documentation

In-repo docs for `calliope2/` — the modernized Calliope. Lives next to the
code so it stays honest: any change to YAML schemas, the `/v3` API,
settings, the CLI, or the architecture should land in the same commit as
the matching doc update.

## Reading order

If you're new, read in this order:

1. **[architecture.md](architecture.md)** — the monorepo layout, request
   lifecycle, and how the pieces fit together. Start here.
2. **[concepts/](concepts/)** — per-subsystem deep dives:
   [storytellers](concepts/storytellers.md),
   [illustrators](concepts/illustrators.md),
   [auth](concepts/auth.md),
   [background-tasks](concepts/background-tasks.md),
   [realtime](concepts/realtime.md),
   [vector-search](concepts/vector-search.md).
3. **[ops/local-dev.md](ops/local-dev.md)** — get the app running on your
   machine.
4. **[ops/migration.md](ops/migration.md)** — the cutover playbook from
   legacy `/calliope/` to `calliope2/`.
5. **[decisions/](decisions/)** — short ADRs (Architecture Decision
   Records) for the choices that aren't obvious from the code. Worth
   skimming if you're about to argue with one of them.

## What's *not* here

- **API reference** — FastAPI auto-generates the interactive Swagger UI
  at `/docs` and the OpenAPI JSON at `/openapi.json`. That's the canonical
  reference; per-endpoint usage examples live in code and tests.
- **Public user-facing guides** — none yet. This doc set is for builders
  and operators.
- **Legacy `/calliope/` docs** — the legacy app is in maintenance mode
  and isn't documented here. See `/calliope/`'s own files.

## Maintaining these docs

Every commit that changes one of the following must update the matching
doc in the same commit:

| Change touches… | Update… |
|---|---|
| Storyteller or Illustrator YAML schema | `concepts/storytellers.md` or `concepts/illustrators.md` |
| `/v3` endpoint surface | the relevant concept doc (e.g. `auth.md` for new auth flows) |
| Settings / env vars | `ops/local-dev.md` |
| `calliope2-cli` commands | the concept doc for the area (e.g. `vector-search.md` for `vector reindex`) |
| Architectural choice that could be revisited later | a new ADR in `decisions/` |

Reviewers should reject PRs that change behavior in those areas without
the matching doc update. Cheap to enforce, expensive to recover from.
