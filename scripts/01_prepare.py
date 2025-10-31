#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, subprocess
from pathlib import Path
from typing import List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
FLAT_DIR = ROOT / "work" / "flattened"
OUT_DIR = ROOT / "out"
FLAT_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

PRAGMA_RE = re.compile(r'pragma\s+solidity\s+([^;]+);', re.IGNORECASE)

# 将 ^、~ 等范围限定到一个“代表版本”
# Map a pragma range to a pinned compiler version you installed via solc-select.
PIN_MAP = [
    ("0.4", "0.4.25"),
    ("0.5", "0.5.17"),
    ("0.6", "0.6.12"),
    ("0.7", "0.7.6"),
    ("0.8", "0.8.20"),
]

def which(cmd: str) -> str:
    from shutil import which as _which
    return _which(cmd) or ""

def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err

def detect_version_by_pragma(sol_path: Path) -> str:
    """根据 pragma 推断主版本 → 映射到已安装的固定版本"""
    try:
        text = sol_path.read_text(encoding="utf-8", errors="ignore")
    except:
        text = sol_path.read_text(errors="ignore")
    m = PRAGMA_RE.search(text)
    if not m:
        return ""  # 未声明 pragma 就用当前系统默认
    clause = m.group(1)
    # 找到第一个形如 0.x 的主版本号
    m2 = re.search(r"0\.(\d+)", clause)
    if not m2:
        return ""
    major_minor = f"0.{m2.group(1)}"
    for key, pinned in PIN_MAP:
        if major_minor.startswith(key):
            return pinned
    return ""

def solc_use(ver: str) -> Tuple[bool, str]:
    if not ver:
        return True, "no-switch"
    if not which("solc-select"):
        return False, "solc-select not installed"
    code, out, err = run(["solc-select", "use", ver])
    if code == 0:
        return True, ver
    return False, err or out

def try_compile(sol_file: Path, ver: str) -> Tuple[bool, str]:
    if not which("solc"):
        return False, "solc not found"
    # 切版本
    ok_switch, msg = solc_use(ver)
    if not ok_switch:
        return False, f"solc-select failed: {msg}"
    code, out, err = run(["solc", "--combined-json", "abi,bin", str(sol_file)])
    if code == 0:
        return True, ""
    return False, (err or out).strip()[:800]

IMPORT_RE = re.compile(r'^\s*import\s+["\']([^"\']+)["\'];', re.MULTILINE)
def read_file(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except:
        return p.read_text(errors="ignore")

def simple_flatten(entry: Path) -> str:
    visited: Set[Path] = set()
    parts: List[str] = []
    def dfs(fp: Path):
        if fp in visited: return
        visited.add(fp)
        content = read_file(fp)
        pos = 0
        for m in IMPORT_RE.finditer(content):
            s, e = m.span()
            parts.append(content[pos:s])
            pos = e
            imp = m.group(1)
            cand = (fp.parent / imp).resolve()
            if cand.exists():
                dfs(cand)
            else:
                parts.append(f"// [WARN] unresolved import kept: {m.group(0)}\n")
        parts.append(content[pos:])
    header = f"// Flattened simple\n// Entry: {entry}\n\n"
    dfs(entry.resolve())
    return header + "".join(parts)

def forge_flatten(entry: Path) -> str:
    if not which("forge"):
        raise RuntimeError("forge not found")
    code, out, err = run(["forge", "flatten", str(entry)])
    if code != 0:
        raise RuntimeError((err or out)[:800])
    return out

def main():
    sol_files = [p for p in DATASETS.rglob("*.sol") if p.is_file()]
    pass_list, fail_list = [], []

    for f in sol_files:
        pinned = detect_version_by_pragma(f)  # e.g., '0.4.25'
        ok, reason = try_compile(f, pinned)
        if ok: pass_list.append(str(f))
        else:  fail_list.append(f"{f} ::: {reason}")

        out_name = f"{f.stem}__flattened.sol"
        out_path = FLAT_DIR / out_name
        try:
            if which("forge"):
                flat_src = forge_flatten(f)
            else:
                flat_src = simple_flatten(f)
        except Exception as e:
            flat_src = "// [WARN] flatten failed; fallback\n" + read_file(f)
        out_path.write_text(flat_src, encoding="utf-8")

    (OUT_DIR / "compile_pass.txt").write_text("\n".join(pass_list), encoding="utf-8")
    (OUT_DIR / "compile_fail.txt").write_text("\n".join(fail_list), encoding="utf-8")
    print(f"[OK] Compile pass: {len(pass_list)}; fail: {len(fail_list)}")
    print(f"[OK] Flattened -> {FLAT_DIR}")

if __name__ == "__main__":
    main()
