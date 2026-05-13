"""One-shot read-only migration from the legacy Piccolo schema to calliope2."""

from calliope2.migration.legacy_schema import legacy_metadata
from calliope2.migration.migrate import migrate_all
from calliope2.migration.stats import MigrationStats

__all__ = ["MigrationStats", "legacy_metadata", "migrate_all"]
