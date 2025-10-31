#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIMIT="${LIMIT:-50}"            # 默认 50
PARALLEL="${PARALLEL:-4}"       # 默认 4
MYTH_TIMEOUT="${MYTH_TIMEOUT:-60}"
MYTH_DEPTH="${MYTH_DEPTH:-128}"
LIST="${1:-}"                   # 可选：传文件清单

echo "[I] LIMIT=$LIMIT PARALLEL=$PARALLEL TIMEOUT=$MYTH_TIMEOUT DEPTH=$MYTH_DEPTH"

if [[ -n "$LIST" ]]; then
  PARALLEL="$PARALLEL" LIMIT="$LIMIT" MYTH_TIMEOUT="$MYTH_TIMEOUT" MYTH_DEPTH="$MYTH_DEPTH" tools/run_batch.sh "$LIST"
else
  PARALLEL="$PARALLEL" LIMIT="$LIMIT" MYTH_TIMEOUT="$MYTH_TIMEOUT" MYTH_DEPTH="$MYTH_DEPTH" tools/run_batch.sh
fi

python3 tools/summarize.py out

# 统计速览
python3 tools/quick_stats.py out/summary.csv --top 10 --by slither

# 生成详细“命中漏洞 + 命中率 + P-映射”报告
python3 tools/make_report.py out --emit-md out/report_${LIMIT}.md --emit-csv out/findings_${LIMIT}.csv --pmap config/p_mapping.yaml || {
  echo "[WARN] p_mapping.yaml 未提供或解析失败，跳过 P 维度汇总。"
}

echo "[OK] 02-Quickscan 完成。产物：out/summary.csv、out/findings_${LIMIT}.csv、out/report_${LIMIT}.md"
