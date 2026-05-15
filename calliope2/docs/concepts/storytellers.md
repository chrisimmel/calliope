# Storytellers

A **Storyteller** is a YAML-declared pipeline that turns inputs (an
optional source image, the previous frame's text, user-supplied
context) into a `FrameOutput` — text, image, video, or some
combination. The runtime that executes one is at
[`apps/api/calliope2/storytellers/runtime.py`](../../apps/api/calliope2/storytellers/runtime.py).

Storytellers are **code, not config rows** ([`ADR 0003`](../decisions/0003-yaml-storytellers-over-db-config.md)).
Iterating on one is `vim → git commit → deploy`.

## Where they live

```
apps/api/calliope2/storytellers/
  __init__.py
  runtime.py              # Storyteller class, FrameOutput, run_storyteller()
  registry.py             # list_storytellers()
  errors.py               # UnknownStoryteller, UnknownStepType, etc.
  defs/<name>.yaml        # one file per storyteller
  prompts/<name>/*.j2     # Jinja templates referenced by that storyteller
```

## YAML shape

```yaml
name: fern
description: |
  Image-driven literary fiction. Observe a source_image, narrate,
  illustrate.

steps:
  - analyze_image:
      provider: openai
      model: gpt-4o
      input: source_image          # variable in scope must hold an ImageBlob
      prompt: prompts/fern/observe.j2
      out: scene

  - generate_text:
      provider: openai
      model: gpt-4o-mini
      prompt: prompts/fern/narrate.j2
      out: frame_text

  - generate_image:
      provider: openai
      model: gpt-image-1
      prompt: prompts/fern/illustrate.j2
      out: frame_image

output:
  text: frame_text
  image: frame_image
```

(Phase 10 introduces `use_illustrator` as a new step type and an
`illustrator:` field at the YAML root. See
[`illustrators.md`](illustrators.md).)

### Top-level fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | Storyteller name; must match the YAML filename |
| `description` | string | no | Human-readable description; shown in `/v3/storytellers` and the admin UI |
| `steps` | list of step dicts | yes | Executed in order |
| `output` | dict[str, str] | yes | Maps `text` / `image` / `video` → variable name in scope at the end |

### Step types

Each step is a **single-key dict** where the key is the step type and
the value is a parameter dict.

#### `generate_text`

```yaml
- generate_text:
    provider: openai           # required; one of: openai, anthropic, openrouter, replicate
    model: gpt-4o-mini         # required; passed through to the provider
    prompt: prompts/fern/narrate.j2   # required; Jinja .j2 path or inline template string
    out: frame_text            # required; variable name to assign the result
```

The rendered prompt is sent to the inference client's `text()` method.
The result is a string assigned to `ctx[params['out']]`.

#### `generate_image`

```yaml
- generate_image:
    provider: openai
    model: gpt-image-1
    prompt: "{{ frame_text }}"
    out: frame_image
```

The result is an `ImageBlob` (DTO from
[`inference/types.py`](../../apps/api/calliope2/inference/types.py)).

#### `generate_video`

```yaml
- generate_video:
    provider: replicate
    model: google/veo-2
    prompt: "{{ topic }}"
    out: frame_video
```

Result is a `VideoBlob`.

#### `analyze_image`

```yaml
- analyze_image:
    provider: openai
    model: gpt-4o-mini
    input: source_image        # variable name; must hold an ImageBlob
    prompt: prompts/fern/observe.j2
    out: scene
```

Sends a vision request: the image + the rendered prompt. Returns
a string description.

#### `set`

```yaml
- set:
    value: "{{ source_text }}"   # Jinja template or literal string
    out: frame_text
```

Assigns a (Jinja-rendered) value to a variable without calling any
inference. Useful for pass-through storytellers like `literal`.

## Prompts

Prompts live under `prompts/<storyteller_name>/`. They're standard
Jinja2 templates. The runtime renders them with the current context
(everything in scope at that step). With Jinja's default `Undefined`,
missing variables render as the empty string — strategies can branch
naturally on `{% if previous_text %}...{% endif %}`.

Inline prompt strings (instead of `.j2` paths) work too and are useful
for short single-line prompts.

## Variable lifecycle

The runtime starts with `ctx = dict(inputs)` (the dict passed to
`run_storyteller()`). Each step's `out:` value is added to `ctx`.
Subsequent steps reference any var in `ctx` via their `prompt` template.

Conventional input variables (the API layer threads these in):

| Variable | Type | Set by |
|---|---|---|
| `source_image` | `ImageBlob` | Caller, when starting a story with an image |
| `previous_text` | str | API layer (Phase 4), from the most recent frame |
| `previous_image` | `ImageBlob` | API layer, from the most recent frame |
| `source_text` | str | Caller, for `literal` storyteller |
| `theme` / `topic` / etc. | str | Caller, storyteller-specific |

The `output:` block at the bottom of the YAML maps which final
variables become `FrameOutput.text` / `.image` / `.video`. Unmapped
output channels stay `None`.

## Listing & loading

```python
from calliope2.storytellers import list_storytellers, Storyteller, run_storyteller

list_storytellers()                # ['continuous_v1', 'fern', 'literal', ...]
s = Storyteller.load("fern")       # parses + validates
frame = await run_storyteller("fern", {"source_image": ImageBlob(url="...")})
```

`Storyteller.load()` validates the schema at parse time: known step
types only, single-key step dicts, all required fields present.
Unknown step types raise `UnknownStepType`; missing fields raise
`StorytellerSchemaError`. **Failures happen at load time, not at run
time** — a misconfigured YAML can never wait until a real inference
call to blow up.

## Tests

[`apps/api/tests/test_storyteller_runtime.py`](../../apps/api/tests/test_storyteller_runtime.py)
mocks the inference clients with `AsyncMock` and asserts the step
dispatch, variable threading, error paths, and the output mapping.
Tests run with no DB, no network, no real prompts.

[`apps/api/tests/test_storyteller_registry.py`](../../apps/api/tests/test_storyteller_registry.py)
asserts every YAML in `defs/` loads cleanly and validates schema
errors at parse time.

## Currently shipped storytellers

The five YAMLs in `defs/` today are **minimal scaffolds**. Phase 10
will replace them with the production-tuned prompts from the legacy
DB (see [`illustrators.md`](illustrators.md) for the mapping table):

| Name | What it does |
|---|---|
| `literal` | Echoes `source_text`; no inference |
| `simple_one_frame` | generate_text → generate_image |
| `narcissus` | analyze_image → generate_image (image-only) |
| `fern` | analyze_image → generate_text → generate_image |
| `continuous_v1` | generate_text → generate_image; templated branch on `previous_text` for multi-frame continuity |

## Related

- [`illustrators.md`](illustrators.md) — the visual axis (Phase 10).
- [`background-tasks.md`](background-tasks.md) — how storytellers are
  invoked from a `/v3/stories` POST.
- [`ADR 0003`](../decisions/0003-yaml-storytellers-over-db-config.md) — why YAML.
- [`ADR 0007`](../decisions/0007-illustrator-concept.md) — why Illustrators are a separate concept.
