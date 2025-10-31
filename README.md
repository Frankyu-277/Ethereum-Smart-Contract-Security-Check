# ETH Check

A lightweight, local-first Ethereum smart contract security checker that orchestrates **Slither + Mythril** with sane defaults, multi-`solc` support, and a one-command batch pipeline.

- **Batch scan** flattened Solidity files with per-file `pragma` → auto switch `solc` (via `solc-select`)
- **Dual-engine**: run both Slither (static) + Mythril (symbolic) and aggregate
- **P-Category mapping (15 classes)** to present high-level, auditor-friendly findings
- **Out-of-the-box report**: summary CSV + per-file table + Markdown report

> Recent batch (50 files): Mythril hit ≥1: **76%**, Slither hit ≥1: **100%**, Either ≥1: **100%**  
> Top P-categories: P1 (Reentrancy), P9 (Visibility), P8 (Insecure Ether Handling), P10 (Cross-func reentrancy)

---

## Why this vs single-tool Slither/Mythril?

1) **Coverage**：静态 + 符号执行双引擎互补（可解释的规则 + 深路径探索）。  
2) **版本对齐**：自动解析 `pragma`，为每个文件切换匹配的 `solc` 版本，减少误报/漏报。  
3) **可复现批处理**：一条命令跑全流程（准备→扫描→聚合→出报表）。  
4) **审计友好映射**：把分散的 SWC/检测器统一映射成 15 个 P 类别，快速“看大图”。  
5) **轻量本地**：无需云端，终端即可完成扫描与统计。

---

## Repository Structure

eth-check/
├── configs/ # 配置（如 p_mapping.yaml：SWC/Detector → P 类别）
├── scripts/ # Python 辅助脚本（准备、筛选、统计、出报告）
├── tools/ # 终端脚本（批处理入口、单项运行器）
├── datasets/ # 可选：示例列表（如 list_top5.txt）
├── requirements.txt # Python 依赖
└── out/ # 运行产物（自动生成，不建议提交到 git）






## Quick Start（macOS / Linux）

### 0) 环境准备

```bash
# Python 3.9+ 建议使用 3.10/3.11
python3 -V

# 在仓库根目录创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装 Python 依赖
pip install -U pip
pip install -r requirements.txt

# macOS 建议
brew install solidity
pip install solc-select

# 准备常用版本（与本仓库的脚本一致）
solc-select install 0.4.25
solc-select install 0.5.17
solc-select install 0.6.12
solc-select install 0.7.6
solc-select install 0.8.20

# 设置一个默认（脚本会按文件切换，此处只是兜底）
solc-select use 0.8.20

安装扫描器（若 requirements 已含可跳过）：
pip install slither-analyzer mythril
slither --version
myth --version

chmod +x tools/*.sh

1) 准备输入（flattened 源码）

将你的 *.sol（已 flatten）放到 work/flattened/（若不存在可自行创建）。
或使用 datasets/list_top5.txt 这类文件清单来限制扫描范围（可选）。
# 全量流程（Prepare → Scan → Aggregate → Report）
# 可通过环境变量快速限速/并行/深度/超时

LIMIT=50 PARALLEL=4 MYTH_TIMEOUT=60 MYTH_DEPTH=128 \
bash tools/00_fullscan.sh

脚本会自动：

预装/检测 5 个 solc 版本

逐文件解析 pragma → 切换对应 solc

运行 Slither 与 Mythril

统计并生成报告

产物输出（默认写入 out/）：

out/summary.csv：全局摘要（每文件 Slither/Mythril 统计、命中率等）

out/findings_50.csv：汇总后的逐条发现

out/report_50.md：Markdown 报告（命中率、Top SWC/Detectors、P 类别热度、Per-file 表格）


只跑 Slither 或 Mythril（调试用）：
# 仅 Slither
ONLY=slither bash tools/00_fullscan.sh

# 仅 Mythril
ONLY=mythril bash tools/00_fullscan.sh
参数说明：

LIMIT：最多扫描的文件数（默认 50）

PARALLEL：并发进程数（默认 4）

MYTH_TIMEOUT：单文件 Mythril 超时秒数（默认 60）

MYTH_DEPTH：Mythril 探索深度（默认 128）

LIST：文件清单路径（可选）

FILE：单文件路径（可选）

ONLY：slither / mythril（可选）


