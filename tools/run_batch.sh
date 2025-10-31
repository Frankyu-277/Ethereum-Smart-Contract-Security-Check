#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-"$PROJECT_DIR/out"}"
RUN_ONE="$PROJECT_DIR/tools/run_one.sh"

# 参数
LIMIT="${LIMIT:-20}"               # 取前 N 个合约
PARALLEL="${PARALLEL:-3}"          # 并发数
MYTH_TIMEOUT="${MYTH_TIMEOUT:-45}" # Mythril 单文件超时(秒)
MYTH_DEPTH="${MYTH_DEPTH:-96}"     # Mythril 深度

# 依赖检查
SLITHER_BIN="$PROJECT_DIR/.venv-slither/bin/slither"
MYTH_BIN="$PROJECT_DIR/.venv-mythril/bin/myth"
[[ -x "$SLITHER_BIN" ]] || { echo "[ERR] Slither 不存在: $SLITHER_BIN"; exit 1; }
[[ -x "$MYTH_BIN"    ]] || { echo "[ERR] Mythril 不存在: $MYTH_BIN"; exit 1; }
[[ -x "$RUN_ONE"     ]] || { echo "[ERR] 缺少 $RUN_ONE"; exit 1; }

# 合约列表来源
SRC="${1:-}"
LIST_FILE="$(mktemp)"
if [[ -z "$SRC" ]]; then
  find "$PROJECT_DIR/work/flattened" -type f -name '*.sol' | head -n "$LIMIT" > "$LIST_FILE"
elif [[ -d "$SRC" ]]; then
  find "$SRC" -type f -name '*.sol' | head -n "$LIMIT" > "$LIST_FILE"
elif [[ -f "$SRC" ]]; then
  head -n "$LIMIT" "$SRC" > "$LIST_FILE"
else
  echo "usage: tools/run_batch.sh [contracts_dir | list.txt]"
  exit 1
fi

echo "[INFO] target files (<=${LIMIT}):"
nl -ba "$LIST_FILE"

export OUT_DIR MYTH_TIMEOUT MYTH_DEPTH PROJECT_DIR

mkdir -p "$OUT_DIR"
echo "[INFO] 并发运行：$PARALLEL"

# 关键修复：用 $1 传入路径，避免 {} 在脚本字符串内不展开的问题
cat "$LIST_FILE" | xargs -I{} -P "$PARALLEL" bash -c '
  set -euo pipefail
  CONTRACT="$1"
  echo "---- RUN: ${CONTRACT} ----"
  FORCE="${FORCE:-0}" OUT_DIR="${OUT_DIR}" MYTH_TIMEOUT="${MYTH_TIMEOUT}" MYTH_DEPTH="${MYTH_DEPTH}" \
    "'"$RUN_ONE"'" "$CONTRACT" || true
' _ {}

echo "[DONE] batch finished."
python3 "$PROJECT_DIR/tools/summarize.py" "$OUT_DIR" || true
