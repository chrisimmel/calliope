# Illustrators — design doc

Status: proposed (no code yet)
Sibling to: [Storytellers](../apps/api/calliope2/storytellers/) (existing, Phase 3)
Motivates: Phase 10 in the modernization plan

## Why

Today, a v3 `Storyteller` YAML embeds everything: narrative steps, prompts,
inference model choices, and image-style strings. Inspecting the legacy
`strategy_config` schema makes clear that two orthogonal axes have been
conflated:

- **Text behavior** — the narrative shape, prompts, situation-awareness,
  language, model family
- **Visual behavior** — image style ("cinematic photo" vs "B&W film noir"
  vs "charcoal abstract"), image model, video model

The legacy DB carries `text_model_config` and `image_model_config` as
separate FKs on `strategy_config`, plus an `output_image_style` string
prepended to every illustration prompt. The runtime treats them as a
package; nothing can be reused.

The active production storytellers make the cost obvious:

- `lavender` and `tamarisk` use the **same** atmospheric narration prompt
  (`lavender-1`). They differ only in image style ("film noir" vs
  "charcoal/watercolor abstract").
- `lavender` and `tamarisque` are an English/French pair of the same text
  with the same image style. Same content, duplicated config.
- `fern` and `lavender` have **different** narrative voices but could in
  principle share image styles for A/B testing.

Without separating the axes, every new image style means a duplicated
storyteller; every new narrative variant means duplicated image config.

## Concept

An **Illustrator** is a sibling to a Storyteller: a YAML-declared pipeline
that turns inputs (typically a text prompt and optional reference images)
into a single output channel (image **or** video). Storytellers invoke
Illustrators by name via a new `use_illustrator` step.

```
Storyteller    ── narrative arc ──┐
                                  ├──► Frame { text, image, video }
Illustrator    ── visual style ───┘
```

The two are composable on every axis:

- A Storyteller can name a default Illustrator and still be overridden at
  request time (`POST /v3/stories {storyteller: "fern", illustrator: "film_noir"}`).
- An Illustrator can be invoked by many Storytellers.
- A Storyteller can call multiple Illustrators per frame (e.g. one image
  + one short video).

## YAML shape

### Illustrator

```yaml
# illustrators/defs/film_noir.yaml
name: film_noir
description: Black and white film-noir photography
outputs: image                # "image" | "video"; exactly one
inputs:
  required: [source]          # variables the caller must supply
  optional: [previous_image]  # variables the caller may supply
style: |
  A black and white photograph in a film noir style. As much detail as
  possible from this scene:
steps:
  - generate_image:
      provider: replicate
      model: black-forest-labs/flux-1.1-pro
      prompt: "{{ style }} {{ source }}"
      out: result
output: result
```

Notes:
- The `style` field is convenience: a frequently-edited string that the
  prompt template references. It lives on the Illustrator (not the
  Storyteller) because it's a visual property.
- `outputs: image|video` is single-channel. Video-capable variants are
  separate Illustrators (`cinematic_motion`, etc.) — keeps the unit of
  composition small.
- `inputs.required` / `inputs.optional` are the contract. The Storyteller
  runtime validates `use_illustrator` calls at load time, surfacing
  mismatches before any inference call.

### Storyteller (revised)

```yaml
# storytellers/defs/fern.yaml
name: fern
description: |
  Image-driven literary fiction. Observe a source_image, narrate, illustrate.
illustrator: cinematic_photo     # default; the API may override per-request
steps:
  - analyze_image:
      provider: openai
      model: gpt-4o
      input: source_image
      prompt: prompts/fern/observe.j2
      out: scene
  - generate_text:
      provider: openai
      model: gpt-4.1
      prompt: prompts/fern/narrate.j2
      out: frame_text
  - use_illustrator:
      # Resolves to the illustrator named at request time or the storyteller
      # default. Inputs are matched against the illustrator's contract.
      inputs:
        source: "{{ frame_text }}"
      out: frame_image
output:
  text: frame_text
  image: frame_image
```

A Storyteller that produces multiple media channels just calls
`use_illustrator` more than once:

```yaml
  - use_illustrator:
      name: cinematic_photo
      inputs: { source: "{{ frame_text }}" }
      out: frame_image
  - use_illustrator:
      name: cinematic_motion
      inputs: { source: "{{ frame_text }}" }
      out: frame_video
```

When `name:` is omitted, the runtime uses the request-level override or
the storyteller's `illustrator:` default. When `name:` is present, it
pins the illustrator regardless of override.

## Runtime model

`Storyteller` and `Illustrator` share enough that the existing
`storytellers/runtime.py` extracts a small `YamlPipeline` base — same step
executors, same Jinja environment, same context dict, different schema
validation and entry-point classes.

`use_illustrator` is a new step type the Storyteller runtime knows:

```python
async def _execute_use_illustrator(params, ctx, illustrator_override):
    name = params.get("name") or illustrator_override or self.default_illustrator
    if not name:
        raise StorytellerSchemaError("use_illustrator: no illustrator named or defaulted")
    ill = Illustrator.load(name)
    ill_inputs = {k: self._render(v, ctx) for k, v in params.get("inputs", {}).items()}
    ill.validate_inputs(ill_inputs)             # required/optional check
    result = await ill.run(ill_inputs)           # FrameOutput-like result
    return result  # caller assigns to ctx[params['out']]
```

The illustrator runs in its own variable scope; only declared inputs
flow in, only `output:` flows out. This keeps the contract tight.

## Variable contract

Storyteller variables (in scope for storyteller steps): `source_image`,
`previous_text`, `previous_image`, `situation`, plus anything the
storyteller's steps emit.

Illustrator variables: only what the Storyteller passes via
`use_illustrator.inputs`. The Illustrator never sees the running story
text directly — it sees what the Storyteller chose to expose. That's the
boundary that makes Illustrators reusable.

## Mapping from legacy data

Reading the user's `calliopeconfig.sql` dump, the active rows decompose as
follows:

| Legacy strategy | New Storyteller | New Illustrator | Notes |
|---|---|---|---|
| `fern` (id=19) | `fern` | `cinematic_photo` | text via gpt-4.1 (model_config 34, prompt 12); image via flux-pro (config 26); video via runway gen-4 turbo (config 32, duration 10s) |
| `lavender` (id=12) | `lavender` | `film_noir` | text via gpt-4o (config 24) + lavender-1 prompt (12); image via flux-pro + `output_image_style` "B&W film noir" |
| `tamarisk` (id=16) | `lavender` (reuse!) | `charcoal_abstract` | same text behavior as lavender; image style "charcoal on paper, contemporary abstraction" |
| `tamarisque` (id=17) | `lavender_fr` | `charcoal_abstract` | French variant of lavender + same charcoal illustrator |
| `narcissus` (id=18) | `narcissus` | `period_photo` | image-only mirror; "1910's grainy B&W" |
| `simple-one-frame` (id=7) | `simple_one_frame` | (any) | brief text + image; illustrator picked at request time |
| `literal` (id=5) | `literal` | (none) | echo only; no illustrator step |
| `lichen` (id=1) | — | — | precursor to fern; drop |
| `continuous-v1-*` | — | — | precursor to fern; drop |

So **5 active legacy strategies → 5 Storytellers + 4 Illustrators**, with
`lavender` and `tamarisk` collapsing into one Storyteller (`lavender`)
paired with two Illustrators (`film_noir`, `charcoal_abstract`).

`output_image_style` strings from `strategy_config.parameters_json` move
into the corresponding Illustrator's `style:` field, verbatim.

## API surface

`POST /v3/stories` and `POST /v3/stories/{id}/frames` accept an optional
`illustrator` field:

```json
{
  "storyteller": "fern",
  "illustrator": "film_noir",
  "inputs": { "source_image_url": "..." }
}
```

Validation:
- If `illustrator` is omitted and the Storyteller has no `illustrator:`
  default, the request is 400.
- If `illustrator` names something nonexistent, 400.
- Anyone signed in may pick any non-experimental Illustrator. Experimental
  Illustrators (`experimental: true` in YAML) require `is_admin`.

`GET /v3/illustrators` — list available Illustrators (admin sees all;
non-admin sees `experimental: false` only).

## Decisions logged

| Question | Decision |
|---|---|
| Single output channel per Illustrator, or image+video in one? | **Single.** Smaller composition unit; storytellers can call multiple. |
| Where does `output_image_style` live? | Illustrator's `style:` field. Storyteller never sees it. |
| Required/optional inputs declared on Illustrator? | **Yes**, validated at storyteller-load time. |
| Per-request override allowed for non-admins? | **Yes** for `experimental: false` illustrators. |
| Storyteller without an illustrator default? | Allowed; the request must then provide one. |
| Multiple `use_illustrator` calls per storyteller? | **Yes**, e.g. image + motion. |
| Illustrator can be empty / no-op? | No — must declare at least one step and an output. Storytellers that produce no media simply omit `use_illustrator`. |

## Implementation outline

Lands as **Phase 10** in the plan; see `i-absolutely-want-to-whimsical-snowglobe.md`.

1. Extract `YamlPipeline` base from current `Storyteller` runtime; no
   behavior change, all storyteller tests still pass.
2. Add `Illustrator` class + `illustrators/defs/*.yaml` directory + loader.
3. Add `use_illustrator` step type to Storyteller runtime.
4. Port legacy prompts as the right Storyteller × Illustrator decomposition
   (see mapping table above). Replaces the current minimal scaffolds.
5. API: `illustrator` field on `POST /v3/stories` and `POST /v3/stories/{id}/frames`;
   `GET /v3/illustrators` listing.
6. Admin UI: Illustrator picker on the story detail / create flow.
7. Tests at each step; full suite green before commit.

## Non-goals

- No support for chaining Illustrators (Illustrator A → Illustrator B).
  If that's needed, build it as a Storyteller that calls both.
- No per-frame Illustrator overrides within a single story. The
  Illustrator chosen at story creation applies to every frame; changing
  it requires a new story or a per-frame request override at the API.
- No automatic style transfer / model-router logic. The Storyteller picks
  exactly one Illustrator per `use_illustrator` step (with an explicit
  request-time override).
