# 0007 — Illustrator as a sibling concept to Storyteller

Date: 2026-05-13
Status: Accepted (implementation: Phase 10)

## Context

The legacy `strategy_config` table already separates *text behavior*
(`text_model_config`, seed prompts) from *visual behavior*
(`image_model_config`, `output_image_style`, `video_model_config`). The
runtime treats them as one package — every strategy is a tuple of all
of these — but the schema-level separation is real.

Inspecting the production rows in `calliopeconfig.sql` made the cost of
conflating them obvious:

- `lavender` and `tamarisk` share the **same** narrative prompt
  (`lavender-1`) and the same text model. They differ only in
  `output_image_style` (B&W film noir vs charcoal/watercolor abstract).
  Two storyteller rows; one piece of duplicated text-prompt content.
- `lavender` and `tamarisque` are an EN/FR pair of the same strategy
  with the same image style; again, duplicated config.

Lifting the visual axis to a first-class concept eliminates the
duplication and makes the orthogonality first-class.

## Decision

A new YAML-declared concept, **Illustrator** (sibling to Storyteller),
captures the visual axis. An Illustrator declares typed inputs, a
single output channel (image **or** video), an optional `style:` string,
and a sequence of steps. A new step type `use_illustrator` lets
Storytellers invoke them. The API accepts an optional `illustrator`
field on `POST /v3/stories` that overrides the storyteller's default.

Five active legacy strategies decompose into **5 Storytellers + 4
Illustrators**, with `lavender` collapsing two legacy rows
(`lavender` + `tamarisk`) into one Storyteller paired with two
Illustrators (`film_noir` + `charcoal_abstract`).

## Consequences

**Wins:**
- No duplicated text prompts across visually-different storytellers.
- New visual style = one new YAML file. Storytellers unchanged.
- A/B testing at request time: same narrative, swap the illustrator.
- Video sits naturally next to image as a separate single-channel
  Illustrator (`cinematic_motion`). Storytellers compose multiple
  `use_illustrator` calls when they want both.
- The Admin UI can present orthogonal pickers (Storyteller ×
  Illustrator), which matches how the operator actually thinks about
  the choice.

**Costs:**
- Two YAML config types to keep in sync. The input-contract validation
  (`inputs.required` declared on the Illustrator, checked at
  Storyteller-load time) catches mismatches early.
- Slightly more indirection: reading `fern.yaml` alone doesn't tell you
  the image style; you need to also read the linked Illustrator.
  Acceptable trade-off for the de-duplication win.

## Alternatives considered

- **Keep the conflated shape; tolerate duplication.** Cheapest now,
  most painful as styles multiply.
- **Combine image + video into a single Illustrator with two output
  channels.** Considered. Rejected for simplicity: a per-modality
  Illustrator is a smaller, more obviously-correct unit of composition.
- **Auto-pair storytellers and illustrators via a router.** Speculative
  abstraction; rejected. The Storyteller picks its default; the API
  accepts an override. That's the only routing needed today.

## Non-goals

- No chained Illustrators (Illustrator A → Illustrator B). Compose at
  the Storyteller level instead.
- No per-frame style switching within a single story. Override happens
  at story creation or per frame-request via the API.

## Related

- [`concepts/illustrators.md`](../concepts/illustrators.md) — full
  design doc, with YAML examples and the legacy-data mapping table.
- Phase 10 in the plan.
