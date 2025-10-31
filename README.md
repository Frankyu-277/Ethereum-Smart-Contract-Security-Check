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

