#!/bin/zsh

set -e
set -u
set -o pipefail

ROOT="/opt"
OUT_DIR="$ROOT/bskiplist/openevolve_output"

cd "$ROOT"

for i in {1..10}; do
    echo "[run_scope_exp] Starting run $i with prompt 8"

    # Ensure a fresh start for OpenEvolve
    rm -rf "$OUT_DIR"

    # Run evolution with prompt 8
    python3 "$ROOT/run_skip.py" 8

    # Verify output exists
    if [ ! -d "$OUT_DIR" ]; then
        echo "[run_scope_exp] ERROR: Expected output directory not found: $OUT_DIR" >&2
        exit 1
    fi

    DEST="$ROOT/bskiplist/openevolve_output_scope_${i}"
    # If destination exists, remove it to avoid mv failure
    if [ -d "$DEST" ]; then
        echo "[run_scope_exp] Warning: $DEST exists, removing it to overwrite"
        rm -rf "$DEST"
    fi

    mv "$OUT_DIR" "$DEST"
    echo "[run_scope_exp] Saved run $i to $DEST"
done

echo "[run_scope_exp] All runs completed."


