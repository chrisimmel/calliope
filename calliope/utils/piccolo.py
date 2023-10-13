import json
from typing import Any, cast, Dict, Union


def load_json_if_necessary(json_field: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Loads a dictionary from Piccolo JSONB field if it hasn't already been done.
    """
    if isinstance(json_field, str):
        return cast(Dict[str, Any], json.loads(json_field))
    else:
        return json_field


