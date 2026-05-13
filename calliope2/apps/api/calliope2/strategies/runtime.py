"""YAML-driven story-strategy runtime.

A ``StoryStrategy`` is declared in ``defs/<name>.yaml`` as a list of steps.
Each step is a single-key dict whose key is the step type (``generate_text``,
``generate_image``, ``generate_video``, ``analyze_image``, ``set``) and whose
value is a parameter map. Each step writes its result to ``out: <var>`` and
subsequent steps can reference any variable in the context via Jinja2 in
their ``prompt`` field (templates can be inline or ``.j2`` file paths
rooted at the strategy package).

The runtime is purely functional: ``run_strategy(name, inputs)`` returns a
``FrameOutput`` and never touches the database, GCS, or Firestore — the
caller is responsible for persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import ChainableUndefined, Environment, FileSystemLoader, TemplateNotFound

from calliope2.inference import ImageBlob, VideoBlob, get_client
from calliope2.strategies.errors import (
    MissingVariable,
    StrategySchemaError,
    UnknownStepType,
    UnknownStrategy,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from jinja2 import Template

STRATEGIES_ROOT = Path(__file__).parent
DEFS_DIR = STRATEGIES_ROOT / "defs"

KNOWN_STEP_TYPES = frozenset(
    {"generate_text", "generate_image", "generate_video", "analyze_image", "set"}
)


@dataclass(slots=True)
class FrameOutput:
    text: str | None = None
    image: ImageBlob | None = None
    video: VideoBlob | None = None


@dataclass
class StoryStrategy:
    name: str
    description: str
    steps: list[dict[str, Any]]
    output: dict[str, str]
    _env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(STRATEGIES_ROOT)),
            undefined=ChainableUndefined,
            keep_trailing_newline=False,
            autoescape=False,
        )

    @classmethod
    def load(cls, name: str) -> StoryStrategy:
        path = DEFS_DIR / f"{name}.yaml"
        if not path.exists():
            raise UnknownStrategy(f"no strategy definition for {name!r} at {path}")
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Mapping[str, Any]) -> StoryStrategy:
        if "name" not in data:
            raise StrategySchemaError("strategy YAML missing required field 'name'")
        steps = data.get("steps") or []
        if not isinstance(steps, list):
            raise StrategySchemaError("'steps' must be a list")
        for i, step in enumerate(steps):
            if not isinstance(step, dict) or len(step) != 1:
                raise StrategySchemaError(
                    f"step {i} must be a single-key dict (got {step!r})"
                )
            (step_type,) = step.keys()
            if step_type not in KNOWN_STEP_TYPES:
                raise UnknownStepType(
                    f"step {i}: unknown step type {step_type!r}; "
                    f"expected one of {sorted(KNOWN_STEP_TYPES)}"
                )
        return cls(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            steps=steps,
            output=dict(data.get("output") or {}),
        )

    async def run(self, inputs: Mapping[str, Any] | None = None) -> FrameOutput:
        ctx: dict[str, Any] = dict(inputs or {})
        for i, step in enumerate(self.steps):
            (step_type, params) = next(iter(step.items()))
            try:
                result = await self._execute_step(step_type, params or {}, ctx)
            except MissingVariable:
                raise
            except StrategySchemaError:
                raise
            except Exception as e:  # pragma: no cover — pass through with step context
                raise type(e)(f"step {i} ({step_type}): {e}") from e
            if "out" in (params or {}):
                ctx[params["out"]] = result
        return self._build_output(ctx)

    async def _execute_step(
        self, step_type: str, params: Mapping[str, Any], ctx: dict[str, Any]
    ) -> Any:
        if step_type == "set":
            return self._render(params["value"], ctx)

        client = get_client(_require(params, "provider", step_type))
        model = _require(params, "model", step_type)

        if step_type == "generate_text":
            prompt = self._render(_require(params, "prompt", step_type), ctx)
            return await client.text(prompt, model=model)
        if step_type == "generate_image":
            prompt = self._render(_require(params, "prompt", step_type), ctx)
            return await client.image(prompt, model=model)
        if step_type == "generate_video":
            prompt = self._render(_require(params, "prompt", step_type), ctx)
            return await client.video(prompt, model=model)
        if step_type == "analyze_image":
            input_var = _require(params, "input", step_type)
            if input_var not in ctx:
                raise MissingVariable(
                    f"analyze_image input {input_var!r} not in context "
                    f"(available: {sorted(ctx.keys())})"
                )
            image = ctx[input_var]
            if not isinstance(image, ImageBlob):
                raise StrategySchemaError(
                    f"analyze_image input {input_var!r} must be an ImageBlob, "
                    f"got {type(image).__name__}"
                )
            prompt = self._render(_require(params, "prompt", step_type), ctx)
            return await client.analyze_image(image, prompt, model=model)

        raise UnknownStepType(step_type)  # pragma: no cover — guarded by load()

    def _render(self, prompt: str, ctx: Mapping[str, Any]) -> str:
        template = self._resolve_template(prompt)
        return template.render(**ctx)

    def _resolve_template(self, prompt: str) -> Template:
        if prompt.endswith(".j2"):
            try:
                return self._env.get_template(prompt)
            except TemplateNotFound as e:
                raise StrategySchemaError(f"prompt template not found: {prompt}") from e
        return self._env.from_string(prompt)

    def _build_output(self, ctx: dict[str, Any]) -> FrameOutput:
        out = FrameOutput()
        if (key := self.output.get("text")) and key in ctx:
            out.text = ctx[key]
        if (key := self.output.get("image")) and key in ctx:
            out.image = ctx[key]
        if (key := self.output.get("video")) and key in ctx:
            out.video = ctx[key]
        return out


def _require(params: Mapping[str, Any], field_name: str, step_type: str) -> Any:
    if field_name not in params:
        raise StrategySchemaError(
            f"step {step_type!r} requires field {field_name!r}"
        )
    return params[field_name]


async def run_strategy(
    name: str, inputs: Mapping[str, Any] | None = None
) -> FrameOutput:
    """Load and execute a named strategy. Pure async function."""
    return await StoryStrategy.load(name).run(inputs)


__all__ = ["FrameOutput", "StoryStrategy", "run_strategy"]
