"""
Regression test for the Piccolo NULL-JSON crash that broke frame generation.

Piccolo 1.34's make_nested_object calls encoding.load_json(value) for each JSON
column of a nested related row with no None guard, so a nullable JSON column
(e.g. ModelConfig.model_parameters = JSONB(null=True)) whose value is NULL
raised orjson.JSONDecodeError. That blew up get_strategy_config (and thus all
frame generation) once the Cloud Tasks worker started running.

Importing `calliope` applies the null-safety patch (calliope/__init__.py).

Run with:
    PINECONE_API_KEY=dummy OPENAI_API_KEY=dummy uv run python tests/test_piccolo_patches.py
"""

from piccolo.columns import JSONB, Varchar
from piccolo.table import Table
from piccolo.utils import encoding
from piccolo.utils.objects import make_nested_object

import calliope  # noqa: F401  (import applies the Piccolo patch)


class _StrategyConfigStub(Table):
    name = Varchar()
    params = JSONB(null=True)


def test_load_json_none_is_safe():
    assert encoding.load_json(None) is None


def test_load_json_still_parses_strings():
    assert encoding.load_json('{"a": 1}') == {"a": 1}


def test_load_json_passes_through_already_parsed():
    assert encoding.load_json({"a": 1}) == {"a": 1}


def test_make_nested_object_tolerates_null_json_column():
    """The exact failure mode: a NULL nullable-JSON column in a loaded row."""
    obj = make_nested_object(
        {"name": "lavender", "params": None},
        _StrategyConfigStub,
        load_json=True,
    )
    assert obj.params is None
    assert obj.name == "lavender"


if __name__ == "__main__":
    test_load_json_none_is_safe()
    test_load_json_still_parses_strings()
    test_load_json_passes_through_already_parsed()
    test_make_nested_object_tolerates_null_json_column()
    print("All Piccolo patch tests passed.")
