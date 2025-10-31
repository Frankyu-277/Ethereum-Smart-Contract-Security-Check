#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_report.py
- 汇总 out/summary.csv
- 解析每个文件的 Mythril/Slither 结果，列出命中的 SWC、detector、标题
- 计算工具命中率
- （新增）加载 config/p_mapping.yaml，将 SWC / detector 映射到 P1..P15
  输出每个文件命中的 P 类别 & 各 P 的命中率
"""
import json, csv, argparse, pathlib, collections, sys

def read_json(p):
    try:
        with open(p, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def mythril_findings(myth):
    if not myth or not isinstance(myth, dict):
        return 0, set(), set()
    issues = myth.get("issues", []) or []
    swcs, titles = set(), set()
    for it in issues:
        swc = it.get("swc-id")
        title = it.get("title")
        if swc: swcs.add(swc.strip())
        if title: titles.add(str(title).strip())
    return len(issues), swcs, titles

def slither_findings(sli):
    if not sli: 
        return 0, set()
    detectors, count = set(), 0

    def try_collect(obj):
        nonlocal count
        if isinstance(obj, dict):
            if "check" in obj and isinstance(obj["check"], str):
                detectors.add(obj["check"].strip()); count += 1
            if "description" in obj and isinstance(obj["description"], dict):
                c = obj["description"].get("check")
                if isinstance(c, str):
                    detectors.add(c.strip()); count += 1
            for v in obj.values():
                try_collect(v)
        elif isinstance(obj, list):
            for v in obj:
                try_collect(v)

    try_collect(sli)
    return count, detectors

def load_pmap(yaml_path):
    """
    读取 YAML（如果提供）：
    Pk:
      name: xxx
      mythril_swc: [SWC-107, ...]
      slither: [reentrancy-eth, ...]
    """
    if not yaml_path:
        return {}
    try:
        import yaml
    except Exception:
        print("[WARN] 缺少 pyyaml，无法解析 P 映射；执行 pip install pyyaml 可启用。", file=sys.stderr)
        return {}
    p = pathlib.Path(yaml_path)
    if not p.exists():
        print(f"[WARN] 未找到映射文件：{p}", file=sys.stderr)
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # 规范化
    norm = {}
    for key, val in data.items():
        if not isinstance(val, dict): 
            continue
        name = val.get("name", key)
        swcs = set([s.strip() for s in val.get("mythril_swc", []) or []])
        dets = set([s.strip() for s in val.get("slither", []) or []])
        norm[key] = {"name": name, "mythril_swc": swcs, "slither": dets}
    return norm

def map_to_p(per_file_item, pmap):
    """
    根据 pmap 把当前文件的 {swcs, detectors} 映射到若干 P 类别
    返回：命中的P集合(set) 与 命中明细 dict(P -> {"swc":{...}, "det":{...}})
    """
    swcs = set(filter(None, (per_file_item.get("mythril_swcs") or "").split(";")))
    dets = set(filter(None, (per_file_item.get("slither_detectors") or "").split(";")))
    ps_hit = set()
    detail = {}
    for P, rule in pmap.items():
        s_hit = swcs & rule["mythril_swc"] if rule["mythril_swc"] else set()
        d_hit = set()
        if rule["slither"]:
            # 支持前缀匹配：配置中写 reentrancy 则 reentrancy-* 也算
            for pat in rule["slither"]:
                for d in dets:
                    if d == pat or d.startswith(pat):
                        d_hit.add(d)
        if s_hit or d_hit:
            ps_hit.add(P)
            detail[P] = {"swc": s_hit, "det": d_hit}
    return ps_hit, detail

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", help="例如: out")
    ap.add_argument("--emit-md", default="out/report.md")
    ap.add_argument("--emit-csv", default="out/findings.csv")
    ap.add_argument("--pmap", default="", help="P 映射 YAML 路径，如 config/p_mapping.yaml")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    summary_csv = outdir / "summary.csv"
    if not summary_csv.exists():
        print(f"[ERR] 找不到 {summary_csv}", file=sys.stderr)
        sys.exit(1)

    rows = list(csv.DictReader(open(summary_csv)))
    pmap = load_pmap(args.pmap) if args.pmap else {}

    myth_any = 0
    slit_any = 0
    myth_swc_freq = collections.Counter()
    myth_title_freq = collections.Counter()
    slit_detector_freq = collections.Counter()
    p_freq = collections.Counter()

    per_file = []

    for r in rows:
        fname = r.get("file_path") or r.get("file")
        base = pathlib.Path(fname).name
        myth_p = outdir / (base + ".myth.json")
        slit_p = outdir / (base + ".slither.json")

        myth = read_json(myth_p)
        slit = read_json(slit_p)

        m_cnt, m_swcs, m_titles = mythril_findings(myth)
        s_cnt, s_detectors = slither_findings(slit)

        if m_cnt > 0: myth_any += 1
        if s_cnt > 0: slit_any += 1

        myth_swc_freq.update(m_swcs)
        myth_title_freq.update(m_titles)
        slit_detector_freq.update(s_detectors)

        item = {
            "file": base,
            "slither_issues": int(r.get("slither_issues") or 0),
            "mythril_issues": int(r.get("mythril_issues") or 0),
            "mythril_swcs": ";".join(sorted(m_swcs)) if m_swcs else "",
            "mythril_titles": ";".join(sorted(m_titles)) if m_titles else "",
            "slither_detectors": ";".join(sorted(s_detectors)) if s_detectors else "",
        }

        # P 映射
        if pmap:
            ps_hit, detail = map_to_p(item, pmap)
            for P in ps_hit:
                p_freq.update([P])
            item["P_hits"] = ";".join(sorted(ps_hit))
            # 人类可读的 P->(swc|det) 汇总
            pretty = []
            for P in sorted(ps_hit):
                part = []
                if detail[P]["swc"]:
                    part.append("SWC=" + "|".join(sorted(detail[P]["swc"])))
                if detail[P]["det"]:
                    part.append("Det=" + "|".join(sorted(detail[P]["det"])))
                pretty.append(f"{P}({','.join(part)})")
            item["P_detail"] = ";".join(pretty)
        else:
            item["P_hits"] = ""
            item["P_detail"] = ""

        per_file.append(item)

    total = len(rows)
    hit_rate_myth = myth_any / total if total else 0.0
    hit_rate_slit = slit_any / total if total else 0.0
    hit_rate_any = sum(1 for x in per_file if (x["slither_issues"]>0 or x["mythril_issues"]>0)) / total if total else 0.0

    # 写 CSV
    header = list(per_file[0].keys()) if per_file else ["file"]
    with open(args.emit_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(per_file)

    # 写 Markdown
    md = []
    md.append(f"# Batch Report ({total} files)\n")
    md.append("## Hit Rates\n")
    md.append(f"- Mythril 命中率（≥1 条）: **{hit_rate_myth:.2%}**")
    md.append(f"- Slither 命中率（≥1 条）: **{hit_rate_slit:.2%}**")
    md.append(f"- 任一工具命中率（≥1 条）: **{hit_rate_any:.2%}**\n")

    if pmap:
        md.append("## P 类别命中率（文件层去重）\n")
        # 计算：命中过该 P 的文件数 / 总数
        # 我们已在 p_freq 中累计“每个命中过 P 的文件一次”
        # 需要从 per_file 逐个文件统计命中过的 P（去重）
        per_p_counts = collections.Counter()
        for item in per_file:
            if item["P_hits"]:
                for P in item["P_hits"].split(";"):
                    per_p_counts[P] += 1
        for P in sorted(pmap.keys()):
            n = per_p_counts.get(P, 0)
            rate = (n/total) if total else 0.0
            name = pmap[P]["name"]
            md.append(f"- {P} ({name}): **{rate:.2%}**  （{n}/{total}）")
        md.append("")

    md.append("## Top Mythril SWC\n")
    for swc, c in myth_swc_freq.most_common(15):
        md.append(f"- {swc}: {c}")

    md.append("\n## Top Slither Detectors\n")
    for d, c in slit_detector_freq.most_common(15):
        md.append(f"- {d}: {c}")

    if pmap:
        md.append("\n## Top P 类别（出现频次，仅用于粗略热度）\n")
        for P, c in p_freq.most_common(15):
            md.append(f"- {P} ({pmap[P]['name']}): {c}")

    md.append("\n## Per-file Findings\n")
    cols = ["file","slither_issues","mythril_issues","mythril_swcs","mythril_titles","slither_detectors"]
    if pmap:
        cols += ["P_hits","P_detail"]
    md.append("| " + " | ".join(cols) + " |")
    md.append("|" + "|".join(["---"]*len(cols)) + "|")
    for r in per_file:
        md.append("| " + " | ".join(str(r.get(k,"") or "-") for k in cols) + " |")

    pathlib.Path(args.emit_md).write_text("\n".join(md), encoding="utf-8")

    print(f"[OK] Wrote Markdown -> {args.emit_md}")
    print(f"[OK] Wrote CSV      -> {args.emit_csv}")
    print(f"HitRates: mythril={hit_rate_myth:.2%} slither={hit_rate_slit:.2%} any={hit_rate_any:.2%}")
    if pmap:
        print(f"[OK] P 映射启用：{len(pmap)} 类别")

if __name__ == "__main__":
    main()
