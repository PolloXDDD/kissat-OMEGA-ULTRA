#!/usr/bin/env bash
# One-command exact SHA3 SUPREME benchmark. Native OMEGA has NO enable flags.
set -euo pipefail
cd "$(dirname "$0")/.."
budget="${1:-500000}"
case "$budget" in *[!0-9]*|'') echo "Budget must be a positive integer" >&2; exit 2;; esac
echo "[1/4] Building native OMEGA"
./configure >/dev/null
make -C build -j2 >/dev/null
echo "[2/4] Generating SHA3 CNF and checking the exact original SHA-256"
python3 scripts/generate-sha3-collision.py
echo "[3/4] Building untouched original Kissat as control"
if ! git cat-file -e 8af8e56f174b778aef3aa45af9f739b2a5f492c2^{commit} 2>/dev/null; then
  git fetch --no-tags origin 8af8e56f174b778aef3aa45af9f739b2a5f492c2
fi
if [ ! -d baseline ]; then
  git worktree add --detach baseline 8af8e56f174b778aef3aa45af9f739b2a5f492c2
fi
(
  cd baseline
  ./configure >/dev/null
  make -C build -j2 >/dev/null
)
echo "[4/4] Equal-decision benchmark: original Kissat vs mandatory OMEGA V3"
python3 scripts/benchmark-sha3-supreme.py \
  --decisions "$budget" \
  --time 90 \
  --seeds 0 \
  --out "benchmarks/results/manual-${budget}"
echo "See benchmarks/results/manual-${budget}/SHA3_SUPREME_RESULTS.md"
