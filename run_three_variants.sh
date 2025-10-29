#!/usr/bin/env bash
set -euo pipefail

# Run multi-workload benchmark three times by swapping bskip.h:
# 1) p8 insertvalue A 100iter best_program.h
# 2) p8 insertvalue E 100iter best_program.h
# 3) original bskip.h

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BSKIP_DIR="$ROOT_DIR/bskiplist"
ORIG_H="$BSKIP_DIR/bskip.h"

P8A_H="$ROOT_DIR/EvolveResult/p8 insertvalue A 100iter/best_program.h"
P8E_H="$ROOT_DIR/EvolveResult/p8 insertvalue E 100iter/best_program.h"

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_H="$ORIG_H.bak.$TS"

echo "Backing up original header: $ORIG_H -> $BACKUP_H"
cp -f "$ORIG_H" "$BACKUP_H"

restore_original() {
  if [[ -f "$BACKUP_H" ]]; then
    echo "Restoring original header from backup..."
    cp -f "$BACKUP_H" "$ORIG_H"
  fi
}
trap restore_original EXIT

compile_bskip() {
  echo "Compiling in $BSKIP_DIR ..."
  make -C "$BSKIP_DIR" clean >/dev/null
  make -C "$BSKIP_DIR" -j ycsb >/dev/null
}

run_variant() {
  local header_path="$1"
  local tag="$2"

  if [[ ! -f "$header_path" ]]; then
    echo "ERROR: header not found: $header_path" >&2
    exit 1
  fi
  echo "\n=== Running variant '$tag' with header: $header_path ==="
  cp -f "$header_path" "$ORIG_H"
  compile_bskip
  python3 "$ROOT_DIR/run_multi_workloads_benchmark.py" --tag "$tag"
}

# 1) p8A
run_variant "$P8A_H" "p8A"

# 2) p8E
run_variant "$P8E_H" "p8E"

# 3) original
echo "\n=== Restoring original header and running 'original' ==="
cp -f "$BACKUP_H" "$ORIG_H"
compile_bskip
python3 "$ROOT_DIR/run_multi_workloads_benchmark.py" --tag "original"

echo "\nAll runs completed. Outputs saved under: $ROOT_DIR/ycsb_benchmark_results"

