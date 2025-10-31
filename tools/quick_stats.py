#!/usr/bin/env python3
import argparse, csv, os, sys, statistics as st, pathlib as pl

def read_rows(csv_path):
    rows = []
    with open(csv_path, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def to_int(x):
    try:
        return int(x)
    except:
        return None

def mean_int(vals):
    vals = [v for v in vals if isinstance(v, int)]
    return st.mean(vals) if vals else None

def try_load_yaml(path):
    try:
        import yaml
    except Exception:
        return None, "NO_PYYAML"
    if not os.path.exists(path):
        return None, "NO_FILE"
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f), None
    except Exception:
        return None, "PARSE_ERR"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="out/summary.csv")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--by", choices=["slither","mythril"], default="slither")
    ap.add_argument("--filter", choices=["slither","mythril"])
    ap.add_argument("--ge", type=int)
    ap.add_argument("--emit-md")
    ap.add_argument("--emit-list")
    ap.add_argument("--abs", action="store_true")
    ap.add_argument("--show-p", action="store_true")
    ap.add_argument("--p-mapping", default=os.getenv("P_MAPPING","configs/p_mapping.yaml"))
    args = ap.parse_args()

    rows = read_rows(args.csv)
    files = len(rows)
    S = [to_int(r.get("slither_issues")) for r in rows]
    M = [to_int(r.get("mythril_issues")) for r in rows]
    s_mean = mean_int(S)
    m_mean = mean_int(M)
    s_min, s_max = (min([x for x in S if x is not None] or [None]) , max([x for x in S if x is not None] or [None]))
    m_min, m_max = (min([x for x in M if x is not None] or [None]) , max([x for x in M if x is not None] or [None]))

    print(f"files={files}  slither(mean)={s_mean if s_mean is not None else 'NA'}  mythril(mean)={m_mean if m_mean is not None else 'NA'}")
    print(f"slither[min,max]={s_min},{s_max}  mythril[min,max]={m_min},{m_max}\n")

    # sorting
    key_col = "slither_issues" if args.by == "slither" else "mythril_issues"
    sorted_rows = sorted(rows, key=lambda r: to_int(r.get(key_col)) or -1, reverse=True)

    # optional filter
    if args.filter and args.ge is not None:
        col = "slither_issues" if args.filter == "slither" else "mythril_issues"
        flt = [r for r in rows if (to_int(r.get(col)) or 0) >= args.ge]
        print(f"Filter: {args.filter} >= {args.ge}\n")
        header = f"{'file':<60} {'slither_issues':>14}  {'mythril_issues':>14}"
        print(header)
        print("-"*len(header))
        for r in flt:
            print(f"{r.get('file'):<60} {r.get('slither_issues', ''):>14}  {r.get('mythril_issues',''):>14}")
        # emit md
        if args.emit_md:
            with open(args.emit_md, "w") as f:
                f.write("| file | slither_issues | mythril_issues |\n|---|---:|---:|\n")
                for r in flt:
                    f.write(f"| {r.get('file')} | {r.get('slither_issues','')} | {r.get('mythril_issues','')} |\n")
            print(f"\n[OK] Wrote Markdown -> {args.emit_md}")
        return

    # top N table
    print(f"Top-{args.top} by {args.by}:\n")
    header = f"{'file':<60} {'slither_issues':>14}  {'mythril_issues':>14}"
    print(header)
    print("-"*len(header))
    for r in sorted_rows[:args.top]:
        print(f"{r.get('file'):<60} {r.get('slither_issues',''):>14}  {r.get('mythril_issues',''):>14}")

    # optional emit list
    if args.emit_list:
        items = sorted_rows[:args.top]
        out_lines = []
        for r in items:
            fp = r.get("file_path") or r.get("file") or ""
            if args.abs and r.get("file_path"):
                fp = r["file_path"]
            out_lines.append(fp)
        pl.Path(args.emit_list).write_text("\n".join(out_lines))
        # 方便连跑
        print(f"\n[OK] Wrote list -> {args.emit_list} ({'absolute paths' if args.abs else 'as-is'})")
        print(f"PARALLEL=2 LIMIT={len(items)} MYTH_TIMEOUT=120 MYTH_DEPTH=160 tools/run_batch.sh {args.emit_list}")

    # optional: show P histogram if mapping present
    if args.show_p:
        mapping, err = try_load_yaml(args.p_mapping)
        if err == "NO_PYYAML":
            print("\n[WARN] 未安装 pyyaml，无法加载 P 映射。请运行: python3 -m pip install pyyaml")
        elif err == "NO_FILE":
            print(f"\n[WARN] 未找到映射文件: {args.p_mapping} （可通过 P_MAPPING 环境变量或 --p-mapping 指定）")
        elif err == "PARSE_ERR":
            print(f"\n[WARN] 解析映射文件失败: {args.p_mapping}")
        else:
            # rows 来自 summarize 的 findings_*.csv 更全面；这里先用 summary.csv 的 P_hits（如有）
            # 如果 summary 没有 P_hits，可在 summarize 阶段写入一个文件级别的 P 集合统计。
            ph = {}
            for r in rows:
                ps = (r.get("P_hits") or "").strip()
                if not ps:
                    continue
                for p in [x.strip() for x in ps.split(";") if x.strip()]:
                    ph[p] = ph.get(p, 0) + 1
            if ph:
                print("\nP 类别（summary.csv 聚合的文件层命中数）：")
                for k in sorted(ph.keys()):
                    print(f"  {k}: {ph[k]}")
            else:
                print("\n[INFO] 当前 CSV 中未包含 P_hits 列，建议使用 tools/02_quickscan.sh 生成 findings_*.csv 并在 summarize 时写入。")

if __name__ == "__main__":
    main()
