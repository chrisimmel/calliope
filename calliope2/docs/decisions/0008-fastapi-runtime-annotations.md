# 0008 — Per-file ruff exclusions for runtime-evaluated annotations

Date: 2026-05-13
Status: Accepted

## Context

ruff's `flake8-type-checking` (TC001/TC002/TC003) flags imports used
only in type annotations and asks for them to be moved into a
`TYPE_CHECKING` block. With `from __future__ import annotations`,
moving the imports is safe for type checkers and saves a small amount
of runtime work.

Two things in this codebase break that assumption:

1. **FastAPI** evaluates `Annotated[T, Depends(...)]` aliases at
   runtime via `get_type_hints()` when building the dependency graph
   for a route. If `T` (or `Depends`) was only imported under
   `TYPE_CHECKING`, the eval fails and the route returns 422.
2. **Pydantic v2** resolves field types at `model_validate()` time, also
   via `get_type_hints()`. If a field type (e.g. `datetime`) is only
   imported under `TYPE_CHECKING`, validation explodes with
   `PydanticUserError`.
3. **Typer** reads parameter type annotations at command-registration
   time to construct argument parsers. Same failure mode for
   `Path`, `Optional[int]`, etc.

We hit each of these failures during Phase 4 and Phase 9 when ruff's
auto-fix moved imports into `TYPE_CHECKING` blocks; routes returned 422
or commands failed to start.

## Decision

Per-file ruff exclusions in `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
# FastAPI evaluates Annotated[T, Depends(...)] aliases at runtime; Pydantic
# v2 resolves schema field types via get_type_hints during model_validate.
"apps/api/calliope2/api/**/*.py" = ["TC001", "TC002", "TC003"]
# Pytest fixtures resolve return-type annotations at runtime in some configs.
"apps/api/tests/conftest.py" = ["TC002", "TC003"]
# Typer reads parameter type annotations at runtime to validate CLI args.
"apps/cli/calliope2_cli/commands/**/*.py" = ["TC001", "TC002", "TC003"]
```

Elsewhere in the codebase the TC rules apply normally.

## Consequences

**Wins:**
- Routes / Pydantic models / Typer commands work, full stop.
- The exclusion is scoped to the directories that genuinely need it;
  the rest of the codebase still benefits from TC enforcement.

**Costs:**
- A small extra-vigilance burden in those directories: imports stay at
  module level even when "only used in type hints" looks true. A
  comment in `pyproject.toml` explains why.
- New contributors might be confused on first encounter. The comment
  in `pyproject.toml` is the first line of defense; this ADR is the
  second.

## Alternatives considered

- **Drop `from __future__ import annotations` in those files.**
  Equivalent effect but less explicit; ruff's intent is still that the
  files are wrong, and the next maintainer might just put the
  `__future__` import back.
- **Use ruff's `runtime-evaluated-decorators` config.** That option
  doesn't match `Annotated[T, Depends(...)]` patterns (which aren't
  decorators); we'd need a more granular knob ruff doesn't offer.
- **Pin every offending import with `# noqa: TC001`.** Noisier than a
  per-file ignore; same effect.

## Related

- [`pyproject.toml`](../../pyproject.toml) (the `per-file-ignores` block)
- Phase 4 PR commit history (where this first bit us)
