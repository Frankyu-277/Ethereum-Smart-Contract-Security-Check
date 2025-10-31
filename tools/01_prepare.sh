#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 目录
mkdir -p out config

# 必备工具检查
command -v slither >/dev/null 2>&1 || { echo "[ERR] slither 未安装"; exit 1; }
command -v myth >/dev/null 2>&1 || { echo "[ERR] mythril (myth) 未安装"; exit 1; }
command -v solc-select >/dev/null 2>&1 || { echo "[ERR] solc-select 未安装"; exit 1; }

# 预热常用 solc 版本（与你的 run_batch.sh 保持一致）
for v in 0.4.25 0.5.17 0.6.12 0.7.6 0.8.20; do
  echo "[STEP] ensure solc $v"
  solc-select install "$v" || true
done

# 清理旧汇总（可选）
: > out/summary.csv || true

echo "[OK] 01-Prepare 完成。"
