"""YAML-driven Illustrator runtime.

An ``Illustrator`` is a YAML-declared pipeline that turns typed inputs
into one media channel (``image`` **or** ``video``). Storytellers
invoke them via the ``use_illustrator`` step; see
``docs/concepts/illustrators.md`` for the design.

Schema:

.. code-block:: yaml

    name: film_noir
    description: Black and white film-noir photography
    outputs: image                # "image" | "video"
    inputs:
      required: [source]
      optional: [previous_image]
    style: |
      A black and white photograph in a film noir style.
    steps:
      - generate_image:
          provider: replicate
          model: black-forest-labs/flux-1.1-pro
          prompt: "{{ style }} {{ source }}"
          out: result
    output: result

Variable scoping is tight: only declared inputs (+ ``style`` if set)
flow in; only the named ``output:`` variable flows out. The Storyteller
never sees Illustrator internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from calliope2.illustrators.errors import (
    IllustratorError,
    IllustratorSchemaError,
    MissingVariable,
    UnknownIllustrator,
    UnknownStepType,
)
from calliope2.pipeline import (
    BASE_STEP_TYPES,
    execute_base_step,
    jinja_env_for,
    load_yaml_def,
    render_prompt,
    validate_steps_schema,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from jinja2 import Environment

    from calliope2.inference import ImageBlob, VideoBlob

ILLUSTRATORS_ROOT = Path(__file__).parent
DEFS_DIR = ILLUSTRATORS_ROOT / "defs"

# Illustrators use only the base step types — no use_illustrator (no chaining,
# per the design doc's non-goals).
KNOWN_STEP_TYPES = BASE_STEP_TYPES

ALLOWED_OUTPUTS = frozenset({"image", "video"})


@dataclass
class Illustrator:
    name: str
    description: str
    outputs: str  # "image" | "video"
    required_inputs: list[str]
    optional_inputs: list[str]
    style: str | None
    steps: list[dict[str, Any]]
    output_var: str
    experimental: bool = False
    _env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._env = jinja_env_for(ILLUSTRATORS_ROOT)

    @classmethod
    def load(cls, name: str) -> Illustrator:
        data = load_yaml_def(name, DEFS_DIR, UnknownIllustrator, kind="illustrator definition")
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Mapping[str, Any]) -> Illustrator:
        if "name" not in data:
            raise IllustratorSchemaError("illustrator YAML missing required field 'name'")

        outputs = data.get("outputs")
        if outputs not in ALLOWED_OUTPUTS:
            raise IllustratorSchemaError(
                f"`outputs` must be one of {sorted(ALLOWED_OUTPUTS)} (got {outputs!r})"
            )

        output_var = data.get("output")
        if not isinstance(output_var, str) or not output_var:
            raise IllustratorSchemaError(
                "illustrator YAML requires `output: <var_name>` (single variable)"
            )

        inputs = data.get("inputs") or {}
        if not isinstance(inputs, dict):
            raise IllustratorSchemaError("`inputs` must be a dict with `required` / `optional` lists")
        required = list(inputs.get("required") or [])
        optional = list(inputs.get("optional") or [])

        steps = data.get("steps") or []
        validate_steps_schema(
            steps,
            KNOWN_STEP_TYPES,
            schema_error_cls=IllustratorSchemaError,
            unknown_step_type_cls=UnknownStepType,
        )

        return cls(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            outputs=outputs,
            required_inputs=required,
            optional_inputs=optional,
            style=data.get("style"),
            steps=steps,
            output_var=output_var,
            experimental=bool(data.get("experimental", False)),
        )

    def validate_inputs(self, supplied: Mapping[str, Any]) -> None:
        """Raise if any required inputs are missing. Caller passes the inputs
        dict it intends to invoke ``run()`` with."""
        missing = [k for k in self.required_inputs if k not in supplied]
        if missing:
            raise IllustratorSchemaError(
                f"illustrator {self.name!r} missing required inputs: {sorted(missing)}"
            )

    async def run(self, inputs: Mapping[str, Any]) -> ImageBlob | VideoBlob:
        self.validate_inputs(inputs)
        ctx: dict[str, Any] = dict(inputs)
        if self.style is not None and "style" not in ctx:
            ctx["style"] = self.style

        for i, step in enumerate(self.steps):
            (step_type, params) = next(iter(step.items()))
            params = params or {}
            try:
                result = await execute_base_step(
                    step_type,
                    params,
                    ctx,
                    render=lambda p: render_prompt(
                        self._env, p, ctx, schema_error_cls=IllustratorSchemaError
                    ),
                    schema_error_cls=IllustratorSchemaError,
                )
            except (MissingVariable, IllustratorSchemaError, IllustratorError):
                raise
            except Exception as e:  # pragma: no cover — pass through with step context
                raise IllustratorError(f"illustrator {self.name!r} step {i} ({step_type}): {e}") from e
            if "out" in params:
                ctx[params["out"]] = result

        if self.output_var not in ctx:
            raise IllustratorSchemaError(
                f"illustrator {self.name!r}: declared output variable "
                f"{self.output_var!r} was not produced by any step"
            )
        return ctx[self.output_var]


async def run_illustrator(
    name: str, inputs: Mapping[str, Any]
) -> ImageBlob | VideoBlob:
    """Load and execute a named Illustrator. Pure async function."""
    return await Illustrator.load(name).run(inputs)


__all__ = ["Illustrator", "run_illustrator"]
