"""Discovery for the storyteller YAML defs."""

from __future__ import annotations

from calliope2.storytellers.runtime import DEFS_DIR


def list_storytellers() -> list[str]:
    """Return the names of all storyteller definitions, sorted alphabetically."""
    return sorted(p.stem for p in DEFS_DIR.glob("*.yaml"))


__all__ = ["list_storytellers"]
