#!/usr/bin/env bash
set -euo pipefail

# 可选：指定解释器和映射
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
export PYTHON_BIN
export P_MAPPING="${P_MAPPING:-configs/p_mapping.yaml}"

# 1) 准备环境（solc 多版本、slither/mythril 检查）
tools/01_prepare.sh

# 2) 快速扫描（使用外部传入的 LIMIT/PARALLEL/MYTH_*；没有就走默认）
LIMIT="${LIMIT:-50}"
PARALLEL="${PARALLEL:-4}"
MYTH_TIMEOUT="${MYTH_TIMEOUT:-60}"
MYTH_DEPTH="${MYTH_DEPTH:-128}"

echo "[I] 00_fullscan: LIMIT=$LIMIT PARALLEL=$PARALLEL TIMEOUT=$MYTH_TIMEOUT DEPTH=$MYTH_DEPTH"
LIMIT="$LIMIT" PARALLEL="$PARALLEL" MYTH_TIMEOUT="$MYTH_TIMEOUT" MYTH_DEPTH="$MYTH_DEPTH" tools/02_quickscan.sh
