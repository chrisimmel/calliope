"""YAML-driven Storyteller runtime.

A ``Storyteller`` is declared in ``defs/<name>.yaml`` as a list of steps.
Each step is a single-key dict whose key is the step type
(``generate_text``, ``generate_image``, ``generate_video``,
``analyze_image``, ``set``, ``use_illustrator``) and whose value is a
parameter map. Each step writes its result to ``out: <var>`` and
subsequent steps can reference any variable in the context via Jinja2
in their ``prompt`` field (templates can be inline or ``.j2`` file
paths rooted at the storyteller package).

The ``use_illustrator`` step invokes an Illustrator
(``calliope2.illustrators``) with a request-time-overridable name and
typed inputs; see ``docs/concepts/illustrators.md``.

The runtime is purely functional: ``run_storyteller(name, inputs)``
returns a ``FrameOutput`` and never touches the database, GCS, or
Firestore — the caller is responsible for persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from calliope2.pipeline import (
    BASE_STEP_TYPES,
    execute_base_step,
    jinja_env_for,
    load_yaml_def,
    render_prompt,
    require_param,
    validate_steps_schema,
)
from calliope2.storytellers.errors import (
    MissingVariable,
    StorytellerError,
    StorytellerSchemaError,
    UnknownStepType,
    UnknownStoryteller,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from jinja2 import Environment

    from calliope2.inference import ImageBlob, VideoBlob

STORYTELLERS_ROOT = Path(__file__).parent
DEFS_DIR = STORYTELLERS_ROOT / "defs"

# Storytellers extend the base set with use_illustrator.
KNOWN_STEP_TYPES = BASE_STEP_TYPES | {"use_illustrator"}


@dataclass(slots=True)
class FrameOutput:
    text: str | None = None
    image: ImageBlob | None = None
    video: VideoBlob | None = None


@dataclass
class Storyteller:
    name: str
    description: str
    steps: list[dict[str, Any]]
    output: dict[str, str]
    illustrator: str | None = None
    _env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._env = jinja_env_for(STORYTELLERS_ROOT)

    @classmethod
    def load(cls, name: str) -> Storyteller:
        data = load_yaml_def(name, DEFS_DIR, UnknownStoryteller, kind="storyteller definition")
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Mapping[str, Any]) -> Storyteller:
        if "name" not in data:
            raise StorytellerSchemaError("storyteller YAML missing required field 'name'")
        steps = data.get("steps") or []
        validate_steps_schema(
            steps,
            KNOWN_STEP_TYPES,
            schema_error_cls=StorytellerSchemaError,
            unknown_step_type_cls=UnknownStepType,
        )
        return cls(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            steps=steps,
            output=dict(data.get("output") or {}),
            illustrator=data.get("illustrator"),
        )

    @property
    def uses_illustrator(self) -> bool:
        """True if any step is ``use_illustrator``. Used by the API to decide
        whether to pre-validate that an illustrator is resolvable."""
        return any("use_illustrator" in step for step in self.steps)

    async def run(
        self,
        inputs: Mapping[str, Any] | None = None,
        *,
        illustrator_override: str | None = None,
    ) -> FrameOutput:
        ctx: dict[str, Any] = dict(inputs or {})
        for i, step in enumerate(self.steps):
            (step_type, params) = next(iter(step.items()))
            params = params or {}
            try:
                if step_type == "use_illustrator":
                    result = await self._execute_use_illustrator(
                        params, ctx, illustrator_override
                    )
                else:
                    result = await execute_base_step(
                        step_type,
                        params,
                        ctx,
                        render=lambda p: render_prompt(
                            self._env, p, ctx, schema_error_cls=StorytellerSchemaError
                        ),
                        schema_error_cls=StorytellerSchemaError,
                    )
            except (MissingVariable, StorytellerSchemaError, StorytellerError):
                raise
            except Exception as e:
                from calliope2.illustrators.errors import IllustratorError
                if isinstance(e, IllustratorError):
                    raise
                raise StorytellerError(f"step {i} ({step_type}): {e}") from e  # pragma: no cover
            if "out" in params:
                ctx[params["out"]] = result
        return self._build_output(ctx)

    async def _execute_use_illustrator(
        self,
        params: Mapping[str, Any],
        ctx: dict[str, Any],
        illustrator_override: str | None,
    ) -> Any:
        """Dispatch to a named Illustrator with rendered inputs.

        Resolution order for which Illustrator runs:
          1. ``params['name']`` if present (pins the illustrator regardless of override)
          2. ``illustrator_override`` (the request-time override)
          3. ``self.illustrator`` (the storyteller's default)
        """
        # Local import to break the storyteller ↔ illustrator import cycle.
        from calliope2.illustrators import Illustrator, UnknownIllustrator

        name = params.get("name") or illustrator_override or self.illustrator
        if not name:
            raise StorytellerSchemaError(
                "use_illustrator: no illustrator name supplied, no request override, "
                "and the storyteller has no default `illustrator:`"
            )
        illustrator = Illustrator.load(name)
        raw_inputs = params.get("inputs") or {}
        if not isinstance(raw_inputs, dict):
            raise StorytellerSchemaError(
                f"use_illustrator: `inputs` must be a dict, got {type(raw_inputs).__name__}"
            )
        rendered_inputs = {
            k: render_prompt(self._env, str(v), ctx, schema_error_cls=StorytellerSchemaError)
            if isinstance(v, str)
            else v
            for k, v in raw_inputs.items()
        }
        return await illustrator.run(rendered_inputs)

    def _build_output(self, ctx: dict[str, Any]) -> FrameOutput:
        out = FrameOutput()
        if (key := self.output.get("text")) and key in ctx:
            out.text = ctx[key]
        if (key := self.output.get("image")) and key in ctx:
            out.image = ctx[key]
        if (key := self.output.get("video")) and key in ctx:
            out.video = ctx[key]
        return out


async def run_storyteller(
    name: str,
    inputs: Mapping[str, Any] | None = None,
    *,
    illustrator_override: str | None = None,
) -> FrameOutput:
    """Load and execute a named storyteller. Pure async function."""
    return await Storyteller.load(name).run(
        inputs, illustrator_override=illustrator_override
    )


# Re-export for callers that previously imported from this module directly.
__all__ = [
    "FrameOutput",
    "Storyteller",
    "require_param",  # used by tests that hand-build YAML dicts
    "run_storyteller",
]
