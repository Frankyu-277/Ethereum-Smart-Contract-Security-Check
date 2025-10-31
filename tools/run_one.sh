#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-"$PROJECT_DIR/out"}"
MYTH_TIMEOUT="${MYTH_TIMEOUT:-60}"
MYTH_DEPTH="${MYTH_DEPTH:-128}"

SLITHER_BIN="$PROJECT_DIR/.venv-slither/bin/slither"
MYTH_BIN="$PROJECT_DIR/.venv-mythril/bin/myth"
AUTO_SOLC="$PROJECT_DIR/tools/auto_solc_use.sh"

CONTRACT="${1:-}"
if [[ -z "$CONTRACT" || ! -f "$CONTRACT" ]]; then
  echo "[ERR] run_one.sh 需要一个存在的 .sol 文件参数"
  exit 1
fi

mkdir -p "$OUT_DIR"

# 1) 自动切换 solc
"$AUTO_SOLC" "$CONTRACT"

# 2) Slither（JSON + ERR）
/usr/bin/time -p "$SLITHER_BIN" \
  --solc "$(command -v solc)" \
  --solc-args="--optimize" \
  --json "$OUT_DIR/$(basename "$CONTRACT").slither.json" \
  "$CONTRACT" 2> "$OUT_DIR/$(basename "$CONTRACT").slither.err" || true

# 3) Mythril（JSON + ERR）
/usr/bin/time -p "$MYTH_BIN" analyze "$CONTRACT" \
  --execution-timeout "$MYTH_TIMEOUT" \
  --strategy dfs \
  --max-depth "$MYTH_DEPTH" \
  -o json > "$OUT_DIR/$(basename "$CONTRACT").myth.json" \
  2> "$OUT_DIR/$(basename "$CONTRACT").myth.err" || true

# 不再做每文件的内联 Python 汇总，改为批量结束后 summarize.py 统一统计
