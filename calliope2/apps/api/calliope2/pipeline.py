"""Shared substrate for YAML-driven pipelines (Storytellers + Illustrators).

This module is the small, reusable kernel that both ``Storyteller`` and
``Illustrator`` build on. It exposes:

- ``BASE_STEP_TYPES`` — the five step types every pipeline supports
  (``generate_text``, ``generate_image``, ``generate_video``,
  ``analyze_image``, ``set``). Subclasses add their own (Storyteller adds
  ``use_illustrator``).
- Helper functions to build a Jinja environment, render a prompt,
  execute a base step, validate a steps list, and load a YAML def.
- Shared error types — ``UnknownStepType``, ``MissingVariable``,
  ``PipelineSchemaError`` (which the pipeline packages subclass).

No class inheritance: the two runtimes compose these helpers. Easier to
test, no LSP gymnastics around per-subclass step dispatch.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import ChainableUndefined, Environment, FileSystemLoader, TemplateNotFound

from calliope2.inference import ImageBlob, get_client

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from jinja2 import Template

_NAME_RE = re.compile(r"^[a-z0-9_-]+$")


# ----- Errors -----


class PipelineError(Exception):
    """Base for all YamlPipeline errors."""


class PipelineSchemaError(PipelineError):
    """Raised on invalid YAML shape. Pipeline packages typically subclass this."""


class UnknownStepType(PipelineError):
    """Pipeline YAML references a step type the runtime doesn't know."""


class MissingVariable(PipelineError):
    """A step references a context variable that hasn't been produced."""


# ----- Step types -----


BASE_STEP_TYPES: frozenset[str] = frozenset(
    {"generate_text", "generate_image", "generate_video", "analyze_image", "set"}
)


# ----- Loader / env helpers -----


def load_yaml_def(
    name: str,
    defs_dir: Path,
    unknown_error_cls: type[Exception],
    *,
    kind: str = "definition",
) -> dict[str, Any]:
    """Read ``defs_dir/<name>.yaml`` and return the parsed dict.

    ``kind`` flavors the error message: e.g. ``kind="storyteller definition"``
    produces ``no storyteller definition for 'fern' at ...``.
    """
    if not _NAME_RE.match(name):
        raise unknown_error_cls(
            f"invalid {kind} name {name!r}: names must match [a-z0-9_-]+"
        )
    path = (defs_dir / f"{name}.yaml").resolve()
    if not path.is_relative_to(defs_dir.resolve()):
        raise unknown_error_cls(f"invalid {kind} name {name!r}")
    if not path.exists():
        raise unknown_error_cls(f"no {kind} for {name!r} at {path}")
    with path.open() as f:
        return yaml.safe_load(f) or {}


def jinja_env_for(package_root: Path) -> Environment:
    """Build the Jinja environment rooted at ``package_root`` (a pipeline package dir)."""
    return Environment(
        loader=FileSystemLoader(str(package_root)),
        undefined=ChainableUndefined,
        keep_trailing_newline=False,
        autoescape=False,
    )


def render_prompt(
    env: Environment,
    prompt: str,
    ctx: Mapping[str, Any],
    *,
    schema_error_cls: type[PipelineSchemaError] = PipelineSchemaError,
) -> str:
    """Render ``prompt`` (either an inline template or a ``.j2`` path) with ``ctx``."""
    template = _resolve_template(env, prompt, schema_error_cls=schema_error_cls)
    return template.render(**ctx)


def _resolve_template(
    env: Environment, prompt: str, *, schema_error_cls: type[PipelineSchemaError]
) -> Template:
    if prompt.endswith(".j2"):
        try:
            return env.get_template(prompt)
        except TemplateNotFound as e:
            raise schema_error_cls(f"prompt template not found: {prompt}") from e
    return env.from_string(prompt)


# ----- Step validation + execution -----


def validate_steps_schema(
    steps: list[Any],
    known_step_types: frozenset[str],
    *,
    schema_error_cls: type[PipelineSchemaError],
    unknown_step_type_cls: type[Exception] = UnknownStepType,
) -> None:
    """Check that ``steps`` is well-shaped. Raises on the first problem."""
    if not isinstance(steps, list):
        raise schema_error_cls("'steps' must be a list")
    for i, step in enumerate(steps):
        if not isinstance(step, dict) or len(step) != 1:
            raise schema_error_cls(f"step {i} must be a single-key dict (got {step!r})")
        (step_type,) = step.keys()
        if step_type not in known_step_types:
            raise unknown_step_type_cls(
                f"step {i}: unknown step type {step_type!r}; "
                f"expected one of {sorted(known_step_types)}"
            )


def require_param(
    params: Mapping[str, Any],
    field_name: str,
    step_type: str,
    *,
    schema_error_cls: type[PipelineSchemaError],
) -> Any:
    """Return ``params[field_name]`` or raise a clear schema error."""
    if field_name not in params:
        raise schema_error_cls(f"step {step_type!r} requires field {field_name!r}")
    return params[field_name]


async def execute_base_step(
    step_type: str,
    params: Mapping[str, Any],
    ctx: dict[str, Any],
    *,
    render: Callable[[str], str],
    schema_error_cls: type[PipelineSchemaError] = PipelineSchemaError,
) -> Any:
    """Dispatch any step type in ``BASE_STEP_TYPES``.

    ``render(prompt)`` should be a closure that renders against the active
    context (a Jinja env + ctx pair). Caller is responsible for assigning
    the return value to ``ctx[params['out']]``.
    """
    if step_type == "set":
        return render(require_param(params, "value", "set", schema_error_cls=schema_error_cls))

    provider = require_param(params, "provider", step_type, schema_error_cls=schema_error_cls)
    model = require_param(params, "model", step_type, schema_error_cls=schema_error_cls)
    client = get_client(provider)

    if step_type == "generate_text":
        prompt = render(require_param(params, "prompt", step_type, schema_error_cls=schema_error_cls))
        return await client.text(prompt, model=model)
    if step_type == "generate_image":
        prompt = render(require_param(params, "prompt", step_type, schema_error_cls=schema_error_cls))
        return await client.image(prompt, model=model)
    if step_type == "generate_video":
        prompt = render(require_param(params, "prompt", step_type, schema_error_cls=schema_error_cls))
        return await client.video(prompt, model=model)
    if step_type == "analyze_image":
        input_var = require_param(params, "input", step_type, schema_error_cls=schema_error_cls)
        if input_var not in ctx:
            raise MissingVariable(
                f"analyze_image input {input_var!r} not in context "
                f"(available: {sorted(ctx.keys())})"
            )
        image = ctx[input_var]
        if not isinstance(image, ImageBlob):
            raise schema_error_cls(
                f"analyze_image input {input_var!r} must be an ImageBlob, "
                f"got {type(image).__name__}"
            )
        prompt = render(require_param(params, "prompt", step_type, schema_error_cls=schema_error_cls))
        return await client.analyze_image(image, prompt, model=model)

    raise UnknownStepType(step_type)  # pragma: no cover — guarded by validate_steps_schema
