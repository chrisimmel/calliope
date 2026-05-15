# 0003 — YAML storytellers over DB-stored config

Date: 2026-05-13
Status: Accepted

## Context

In the legacy app, prompts and model selections live in Postgres
(`prompt_template`, `inference_model`, `model_config`, `strategy_config`).
Each strategy is wired up by joining those four tables. Editing a prompt
or swapping a model means updating rows in production (or a SQL dump
synced down to staging).

That's a poor fit for the kind of iteration prompts demand: small,
frequent, version-controlled changes; A/B comparisons against earlier
versions; rollback as easy as `git revert`. Treating prompts as code —
text in the repo, reviewed, tagged, deployed atomically with the
runtime that uses them — is the right shape.

## Decision

Storytellers (and, per Phase 10, Illustrators) are **YAML files in the
repo** under `apps/api/calliope2/storytellers/defs/` and
`apps/api/calliope2/illustrators/defs/`. Prompts are **Jinja2 templates**
under `storytellers/prompts/<name>/*.j2`. Each YAML is a sequence of
typed steps (`generate_text`, `generate_image`, etc.); each step
references a provider, model, and prompt.

Drop the legacy `prompt_template`, `inference_model`, `model_config`,
`strategy_config` tables from the new schema entirely.

## Consequences

**Wins:**
- Iteration is `vim → git commit → deploy`. No DB writes for prompt
  tuning.
- Diffs are reviewable. Rollback is trivial.
- The full storyteller behavior is grep-able from one file.
- Tests can include snapshot tests on prompt rendering with no DB at all.

**Costs:**
- Non-engineer collaborators can't tweak prompts without a deploy. This
  is a real cost for prompt-engineering workflows. If/when we have
  collaborators who need that, we can add a thin UI layer that writes to
  a separate `prompt_overrides` table and reads-through to YAML — but
  that's speculative; we shouldn't build it now.
- The `output_image_style` per-storyteller string the legacy app keeps
  in the DB now lives on each Illustrator's `style:` field (Phase 10).
  Same trade-off applies.

## Alternatives considered

- **Keep DB-driven config.** Wins on live editing, loses on
  reviewability, history, rollback, atomicity-with-deploy. Net loss for
  a small-team project.
- **YAML + Git, but config rows in DB shadow it.** Doubled source of
  truth; eventual drift. Avoided.

## Related

- [`concepts/storytellers.md`](../concepts/storytellers.md)
- [`concepts/illustrators.md`](../concepts/illustrators.md)
- [`storytellers/`](../../apps/api/calliope2/storytellers/)
