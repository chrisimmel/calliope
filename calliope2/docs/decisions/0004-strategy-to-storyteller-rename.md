# 0004 — "Strategy" → "Storyteller"

Date: 2026-05-13
Status: Accepted

## Context

The legacy code calls these things "strategies" — `/calliope/strategies/`,
`StrategyConfig`, `strategy_name` column, `/v1/config/strategy/` route.
The Clio UI has always called them "**storytellers**" — that's the term
end users see and what the project's docs use externally.

Two vocabularies for the same concept is friction: every conversation
between "user feedback says X about storyteller Y" and "we'll change
strategy Y" needs a mental translation. New contributors trip over the
mismatch.

## Decision

In the v3 code, the user-facing term is canonical. Everywhere:

- Directory: `apps/api/calliope2/storytellers/`
- Class: `Storyteller`
- Entry points: `run_storyteller()`, `list_storytellers()`
- Errors: `StorytellerError`, `UnknownStoryteller`, `StorytellerSchemaError`
- DB column: `stories.storyteller_name`
- API route: `GET /v3/storytellers`
- CLI: `calliope2-cli ... run-storyteller`

The legacy `/calliope/strategies/` paths and the legacy
`StrategyConfig` table are unchanged — those are frozen alongside the
old app.

## Consequences

**Wins:**
- One vocabulary. UI, code, docs, and conversations all match.
- Greppable boundary: any reference to "strategy" in `calliope2/` should
  be referring to the legacy code; in the legacy app it's the local
  noun.

**Costs:**
- The rename was a pure-mechanical commit (`sed` + git mv) before any
  v3 deployment, so it landed cleanly. Had we deployed first and
  renamed later, this would have required a data migration on
  `stories.strategy_name` and a route alias for `/v3/strategies`.

## Alternatives considered

- **Stay with "strategy".** Rejects the user-facing vocabulary; keeps
  the friction.
- **Pick a third term.** No advantage; "storyteller" is already in use
  and matches the metaphor.

## Related

- [`concepts/storytellers.md`](../concepts/storytellers.md)
- Commit `bf43867` (pure-mechanical rename, before any v3 deploy)
