"""Discovery for the strategy YAML defs."""

from __future__ import annotations

from calliope2.strategies.runtime import DEFS_DIR


def list_strategies() -> list[str]:
    """Return the names of all strategy definitions, sorted alphabetically."""
    return sorted(p.stem for p in DEFS_DIR.glob("*.yaml"))


__all__ = ["list_strategies"]
