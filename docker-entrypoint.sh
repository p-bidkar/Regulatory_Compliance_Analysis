#!/usr/bin/env bash
set -euo pipefail

if [ -z "$(ls -A /app/chroma_db 2>/dev/null)" ]; then
    echo "[entrypoint] No existing policy index found in /app/chroma_db - building it now..."
    python scripts/build_index.py
else
    echo "[entrypoint] Existing policy index found in /app/chroma_db - skipping build."
fi

exec "$@"
