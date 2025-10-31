#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAT = ROOT / "work" / "flattened"
OUT_DIR = ROOT / "out" / "slither"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PRAGMA_RE = re.compile(r'pragma\s+solidity\s+([^;]+);', re.IGNORECASE)

PIN_MAP = [("0.4","0.4.25"),("0.5","0.5.17"),("0.6","0.6.12"),("0.7","0.7.6"),("0.8","0.8.20")]

def which(cmd:str)->str:
    from shutil import which as _which
    return _which(cmd) or ""

def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err

def detect_version(text:str)->str:
    m = PRAGMA_RE.search(text)
    if not m: return ""
    clause = m.group(1)
    m2 = re.search(r"0\.(\d+)", clause)
    if not m2: return ""
    mm = f"0.{m2.group(1)}"
    for key,p in PIN_MAP:
        if mm.startswith(key): return p
    return ""

def solc_use(ver:str)->bool:
    if not ver: return True
    if not which("solc-select"):
        print("[WARN] solc-select not found, skip version switch")
        return True
    code, out, err = run(["solc-select","use",ver])
    if code!=0:
        print(f"[WARN] solc-select use {ver} failed: {err or out}")
        return False
    return True

def main():
    if not which("slither"):
        raise SystemExit("slither not found. pip install slither-analyzer")

    files = sorted(FLAT.glob("*.sol"))
    if not files:
        raise SystemExit("No flattened files. Run 01_prepare.py first.")

    ok=fail=0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        ver = detect_version(text)
        solc_use(ver)

        out_json = OUT_DIR / (f.stem + ".json")
        code,out,err = run(["slither", str(f), "--json", str(out_json)])
        if code==0:
            ok+=1; print(f"[OK] Slither => {out_json}")
        else:
            fail+=1; (OUT_DIR / (f.stem + ".err.txt")).write_text(err or out, encoding="utf-8")
            print(f"[ERR] Slither failed: {f.name}")

    print(f"[DONE] Slither ok={ok}, fail={fail}")

if __name__ == "__main__":
    main()
