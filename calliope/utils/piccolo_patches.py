"""
Runtime patches for third-party library bugs.

Kept in one place and applied once at import time (see calliope/__init__.py).
"""

import logging

logger = logging.getLogger(__name__)


def apply_piccolo_patches() -> None:
    """Make Piccolo's ``load_json`` tolerate NULL / already-deserialized values.

    Piccolo 1.34's ``make_nested_object`` (used when a query loads nested related
    rows, e.g. ``Table.objects(FK.all_related()).output(load_json=True)``) calls
    ``encoding.load_json(value)`` for every JSON column of each nested row, with
    no guard for ``None``. A nullable JSON column whose value is SQL ``NULL`` —
    e.g. ``ModelConfig.model_parameters = JSONB(null=True)`` — therefore reaches
    ``orjson.loads(None)`` and raises::

        orjson.JSONDecodeError: Input must be bytes, bytearray, memoryview, or str

    That broke ``get_strategy_config`` (and thus all frame generation) the moment
    the Cloud Tasks worker actually started running. The unnested/top-level
    code path guards ``None`` already; only the nested path is affected.

    We wrap ``load_json`` so ``None`` and any already-deserialized value pass
    through unchanged. This only adds behavior for inputs that previously raised,
    so it cannot change any currently-working path. Patching the module
    attribute is sufficient because ``make_nested_object`` calls it as
    ``encoding.load_json(...)`` (resolved at call time).
    """
    from piccolo.utils import encoding

    if getattr(encoding.load_json, "_calliope_null_safe", False):
        return

    original_load_json = encoding.load_json

    def null_safe_load_json(data):
        if data is None:
            return None
        if not isinstance(data, (str, bytes, bytearray, memoryview)):
            # Already deserialized (dict / list / number / bool): return as-is.
            return data
        return original_load_json(data)

    null_safe_load_json._calliope_null_safe = True  # type: ignore[attr-defined]
    encoding.load_json = null_safe_load_json
    logger.info("Applied Piccolo load_json NULL-safety patch")
