#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
明显风险快速筛查（关键词/模式）
Quick screening using regex patterns to prioritize suspicious files/functions.

输出 / Output:
- out/quick_screen.csv: file, category, pattern, context_snippet

说明 / Notes:
- 这不是“漏洞定论”，而是帮助你挑出“优先跑 Mythril / 高价值复核”的样本
- 你可按需扩展 PATTERNS 中的正则
"""

import re
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

# 可扩展的关键词/模式（大小写不敏感）
# Extensible patterns (case-insensitive)
PATTERNS = {
    "P1_Reentrancy": [
        r"\.call\(", r"\.delegatecall\(", r"call\.value", r"send\(", r"transfer\(",
        r"reentrancy", r"Checks-Effects-Interactions"
    ],
    "P2_AccessControl": [
        r"tx\.origin", r"onlyOwner", r"onlyRole", r"owner\(", r"AccessControl"
    ],
    "P3_Integer": [
        r"unchecked\s*\{", r"SafeMath", r"\badd\s*\(", r"\bsub\s*\(", r"\bmul\s*\("
    ],
    "P11_Multisig": [
        r"multisig", r"threshold", r"confirmations", r"requiredSigners"
    ]
}

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except:
        return p.read_text(errors="ignore")

def scan_file(p: Path):
    text = read_text(p)
    hits = []
    for cat, patterns in PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                s = max(0, m.start()-80)
                e = min(len(text), m.end()+80)
                ctx = text[s:e].replace("\n", " ")
                hits.append((cat, pat, ctx))
    return hits

def main():
    sol_files = list(DATASETS.rglob("*.sol"))
    rows = []
    for f in sol_files:
        for cat, pat, ctx in scan_file(f):
            rows.append([str(f), cat, pat, ctx])

    out_csv = OUT / "quick_screen.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as w:
        writer = csv.writer(w)
        writer.writerow(["file", "category", "pattern", "context"])
        writer.writerows(rows)

    print(f"[OK] Wrote quick screen results: {out_csv} (rows={len(rows)})")

if __name__ == "__main__":
    main()
