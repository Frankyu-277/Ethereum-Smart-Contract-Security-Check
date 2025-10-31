#!/usr/bin/env bash
# auto_solc_use.sh
# 功能：
# 1) 预热：先“读取数据库的任意五个 solc”（此处提供常用 5 个稳定版本；也提供远端随机挑选的占位逻辑）
# 2) 自动从合约文件 pragma 推断版本，并用 solc-select 切换
# 3) 全流程计时：预热、解析、切换、总时长
#
# 用法：
#   ./tools/auto_solc_use.sh <path/to/contract.sol>
#
# 依赖：
#   - solc-select 已安装并可用
#   - 已配置 PATH: export PATH="$HOME/.solc-select/current:$PATH"

set -euo pipefail

# -------------------- 基础校验与工具函数 --------------------
die(){ echo "[ERROR] $*" >&2; exit 1; }
need(){ command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

need solc-select
need grep
need sed
need awk

# 计时工具：使用 Bash 内置 SECONDS（跨平台，macOS/Linux 都可用）
reset_timer(){ SECONDS=0; }
elapsed(){ printf "%ds" "$SECONDS"; }

# 记录总时长
reset_timer
TOTAL_START=$SECONDS

# -------------------- 选择 5 个要预热安装的 solc 版本 --------------------
# 方案 A（默认）：使用 5 个常用稳定版本（覆盖 0.4~0.8 主线）
PREFETCH_VERSIONS=(0.4.25 0.5.17 0.6.12 0.7.6 0.8.20)

# 方案 B（可选）：从远端“数据库”随机取 5 个版本（占位逻辑）
# 若你希望真随机 5 个版本，可解开注释并安装 jq，然后替换 PREFETCH_VERSIONS：
# 注意：此逻辑会访问 https://binaries.soliditylang.org ，网络需通。
#: <<'RANDOM5'
#need curl
#need jq
#reset_timer
#echo "[INFO] Fetching remote solc version index..."
#REMOTE_JSON=$(curl -fsSL https://binaries.soliditylang.org/macosx-amd64/list.json)
#mapfile -t RANDOM_FIVE < <(echo "$REMOTE_JSON" | jq -r '.releases | keys[]' | shuf -n 5)
#PREFETCH_VERSIONS=("${RANDOM_FIVE[@]}")
#echo "[INFO] Picked 5 random versions: ${PREFETCH_VERSIONS[*]} (in $(elapsed))"
#RANDOM5

# -------------------- 预热安装（带计时） --------------------
echo "[STEP] Prefetch & ensure 5 solc versions installed: ${PREFETCH_VERSIONS[*]}"
for ver in "${PREFETCH_VERSIONS[@]}"; do
  reset_timer
  if solc-select versions | awk '{print $1}' | grep -qx "${ver}"; then
    echo "  - ${ver} already installed (skip) [${ver}] in $(elapsed)"
  else
    echo "  - installing ${ver} ..."
    solc-select install "${ver}" >/dev/null
    echo "    installed ${ver} in $(elapsed)"
  fi
done

# -------------------- 读取 pragma 并映射到可用版本 --------------------
FILE="${1:-}"
[[ -n "$FILE" ]] || die "usage: auto_solc_use.sh <solidity_file>"
[[ -f "$FILE" ]] || die "file not found: $FILE"

reset_timer
# 抽取第一条 pragma；兼容如：pragma solidity ^0.8.0; / >=0.6.0 <0.9.0; / =0.5.17; 等
PRAGMA_LINE=$(grep -Eo 'pragma[[:space:]]+solidity[^;]*;' "$FILE" | head -n1 || true)
[[ -n "$PRAGMA_LINE" ]] || echo "[WARN] No pragma found; will keep current solc."

# 提取第一个 x.y.z（若找不到精确 x.y.z，退化到 x.y.* 的策略）
EXACT_VER=$(echo "$PRAGMA_LINE" | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)
BASE_VER=""
if [[ -n "$EXACT_VER" ]]; then
  BASE_VER="$(echo "$EXACT_VER" | awk -F. '{printf("%d.%d.*",$1,$2)}')"
else
  # 尝试仅提取 x.y
  MAJMIN=$(echo "$PRAGMA_LINE" | grep -Eo '[0-9]+\.[0-9]+' | head -n1 || true)
  [[ -n "$MAJMIN" ]] && BASE_VER="${MAJMIN}.*"
fi

echo "[STEP] Parse pragma"
echo "  - pragma: ${PRAGMA_LINE:-<none>}"
echo "  - exact : ${EXACT_VER:-<none>}"
echo "  - base  : ${BASE_VER:-<none>}  (elapsed $(elapsed))"

# 映射函数：把 base 归到一版稳定可用版本
pick_version(){
  local base="${1:-}"
  case "$base" in
    0.4.*) echo 0.4.25;;
    0.5.*) echo 0.5.17;;
    0.6.*) echo 0.6.12;;
    0.7.*) echo 0.7.6;;
    0.8.*) 
      # 若 EXACT_VER 存在并且等于 0.8.2x 可优先使用 0.8.20（或你喜欢的 0.8.24）
      # 这里可按需调整到 0.8.24/0.8.26 等
      echo 0.8.20
      ;;
    *)
      # 无法解析则使用你项目里默认设定
      echo 0.8.20
      ;;
  esac
}

TARGET_VER="$(pick_version "${BASE_VER}")"

# -------------------- 切换 solc（带计时） --------------------
reset_timer
echo "[STEP] Switch solc"
echo "  - target version: ${TARGET_VER}"
solc-select use "${TARGET_VER}" >/dev/null
# 验证当前版本
CUR_SOLC=$(solc --version 2>/dev/null | head -n1 | sed -E 's/.*([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
echo "  - current solc  : ${CUR_SOLC}  (switched in $(elapsed))"

# -------------------- 总时长 --------------------
TOTAL_ELAPSED=$((SECONDS - TOTAL_START))
echo "[DONE] All steps completed in ${TOTAL_ELAPSED}s"
