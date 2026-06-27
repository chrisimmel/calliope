"""Discovery for the Illustrator YAML defs."""

from __future__ import annotations

from calliope2.illustrators.runtime import DEFS_DIR


def list_illustrators() -> list[str]:
    """Return the names of all illustrator definitions, sorted alphabetically."""
    return sorted(p.stem for p in DEFS_DIR.glob("*.yaml"))


__all__ = ["list_illustrators"]
