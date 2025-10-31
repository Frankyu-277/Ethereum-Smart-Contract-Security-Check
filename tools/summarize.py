import json, csv, sys, pathlib

out_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("out")
rows = []
for slither_json in sorted(out_dir.glob("*.slither.json")):
    base = slither_json.name.replace(".slither.json","")
    myth_json = out_dir / f"{base}.myth.json"
    def cnt_s(f, key):
        try:
            d = json.load(open(f))
            return len(d.get("results",{}).get("detectors",[])) if key=="slither" else len(d.get("issues",[]))
        except Exception:
            return None
    rows.append({
        "file": base,
        "slither_issues": cnt_s(slither_json,"slither"),
        "mythril_issues": cnt_s(myth_json,"myth") if myth_json.exists() else None
    })

csv_fp = out_dir / "summary.csv"
with open(csv_fp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["file","slither_issues","mythril_issues"])
    w.writeheader(); w.writerows(rows)

print(f"Wrote {csv_fp}")
