#!/usr/bin/env bash
# Dump Calliope config tables to a SQL file (data-only, INSERT statements).
# Redacts sparrow_config.keys (API credentials) via a Python post-processor.
#
# Output: scratch/calliope-config.sql
#
# Requires: the calliope-postgres-1 container to be running.
set -euo pipefail

CONTAINER="calliope-postgres-1"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW_OUT="$REPO_ROOT/scratch/calliope-config.raw.sql"
FINAL_OUT="$REPO_ROOT/scratch/calliope-config.sql"

mkdir -p "$REPO_ROOT/scratch"

docker exec "$CONTAINER" pg_dump \
    --data-only --inserts --no-owner --no-privileges \
    -t prompt_template \
    -t inference_model \
    -t model_config \
    -t strategy_config \
    -t client_type_config \
    -t sparrow_config \
    -U postgres calliope > "$RAW_OUT"

python3 "$REPO_ROOT/scripts/redact_sparrow_keys.py" "$RAW_OUT" "$FINAL_OUT"
rm "$RAW_OUT"
echo "Wrote $FINAL_OUT"
