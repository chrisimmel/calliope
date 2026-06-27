"""Calliope package."""

# Apply third-party runtime patches as early as possible, before any database
# query runs (the API server, the Cloud Tasks worker, and CLI tools all import
# the calliope package first).
from calliope.utils.piccolo_patches import apply_piccolo_patches

apply_piccolo_patches()
