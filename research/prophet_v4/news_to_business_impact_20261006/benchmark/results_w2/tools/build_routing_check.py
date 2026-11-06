"""Seat tool: check whether the w2 graded draw routed each case to a real event with an on-event body.
usage (from the repository tree root):
  PYTHONPATH=. python3.11 build_routing_check.py SCRATCH_W2 BENCH_DIR OUT_DIR             (census + sample + cards)
  PYTHONPATH=. python3.11 build_routing_check.py SCRATCH_W2 BENCH_DIR OUT_DIR VERDICTS    (also score the verdicts)
The w2 draw routes a headline to a template with the tape_draw headline patterns, resolves its
issuer from the first entity token that maps to a ticker, and attaches up to three qualifying
8-K filings from that issuer inside the session window. Nothing checks that the attached body
reports the headline's event. This tool measures how often the three steps line up.
OUT_DIR mode writes:
  sample_routing.json   the 40-case sample (seed 20261016, case ids sorted) plus the three cases
                        behind malformed cards M3, M7 and M9. Ids only.
  batch_routing_1.txt   one card per sampled case with the headline, registrant, item text and
                        exhibit opening. The cards quote headlines and filing text: they are
                        scratch-only and are never committed.
VERDICTS mode also writes:
  routing_check.json    per sampled case the template, proxy cell, fold, qualifying items, the
                        automated flags, slot classes and the seat verdict; then the class rates
                        with Wilson 95% intervals, each automated flag's precision and recall
                        against the verdicts, and the critical-slot classes by verdict class.
The JSON outputs carry ids, codes, counts, booleans and paraphrased notes only, never text.
"""
import collections
import json
import math
import random
import re
import sys
from pathlib import Path

from engine.news_impact import tape_draw as td

SEED = 20261016
N_SAMPLE = 40
MOTIVATING = ["69cdff734be8096d", "942a8b6e282f8f76", "cda8daa3f5309de6"]  # malformed cards M3, M7, M9
QUALIFYING = ("1.01", "2.02", "7.01", "8.01")
STOP = {"inc", "corp", "corporation", "company", "co", "ltd", "plc", "holdings", "group", "the", "of", "and",
        "n.v.", "s.a.", "limited", "trust", "international", "technologies", "incorporated", "sa", "nv", "llc",
        "lp", "l.p.", "&"}


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def segment(raw, s):
    return raw[s["byte_start"]:s["byte_end"]].decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", s)


def census(w2, bench):
    """One row per graded case: routing codes and automated flags, no text."""
    cases = jl(bench / "graded" / "cases.jsonl")
    cand = {r["item_id"]: r for r in jl(w2 / "candidates_all.jsonl")}
    bodies = {(r.get("case_id") or r.get("item_id")): r for r in jl(w2 / "bodies_all" / "bodies.jsonl")}
    slots = collections.defaultdict(list)
    for r in jl(w2 / "score" / "critical_slots.jsonl"):
        slots[r["case_id"]].append(r["class"])
    rows = {}
    for c in cases:
        cid = c["item_id"]
        title, tk = cand[cid]["title"], cand[cid]["ticker"]
        b = json.load(open(w2 / "bundles_graded" / cid / "bundle.json"))
        raw = (w2 / "bundles_graded" / cid / "source.txt").read_bytes()
        text = raw.decode("utf-8", "replace")
        accs = sorted({s["accession"] for s in b["segments"]})
        fil = {f["accession"]: f for f in bodies[cid]["filings"]}
        items = sorted({i for a in accs for i in fil[a]["items"]})
        seg0 = next(s for s in b["segments"] if s["doc_type"] == "8-K")
        cover = segment(raw, seg0)
        m = re.search(r"\)\s*(.{3,120}?)\s*\(Exact name of registrant", cover.replace("\n", " "), re.I)
        reg = re.split(r"\d{4}\s", m.group(1).strip() if m else "")[-1].strip()
        toks = [w for w in re.findall(r"[A-Za-z][A-Za-z.&'-]+", reg) if w.lower() not in STOP and len(w) > 1]
        name_hit = any(re.search(r"\b" + re.escape(w.lower()) + r"\b", title.lower()) for w in toks)
        tick_hit = bool(tk) and bool(re.search(r"(?<![A-Za-z])" + re.escape(tk) + r"(?![A-Za-z])", title))
        q = sorted(set(items) & set(QUALIFYING))
        rows[cid] = {"case_id": cid, "template": c["template"], "proxy_cell": c["proxy_cell"], "fold": c["fold"],
                     "items": items, "qualifying_items": q, "n_filings": len(accs),
                     "issuer_named_in_headline": bool(name_hit or tick_hit),
                     "body_family_hits": len(td.FAMILY_PATTERNS[c["template"]].findall(text)),
                     "headline_families": sorted(k for k, v in td.family_hits(title).items() if v),
                     "slot_classes": dict(sorted(collections.Counter(slots[cid]).items()))}
    return rows, cand


def draw(rows):
    ids = sorted(rows)
    sample = sorted(random.Random(SEED).sample(ids, N_SAMPLE))
    return {"seed": SEED, "n_population": len(ids), "sample": sample, "motivating": MOTIVATING}


def cards(w2, rows, cand, spec):
    lines = []
    order = spec["sample"] + [m for m in spec["motivating"] if m not in spec["sample"]]
    for n, cid in enumerate(order, 1):
        r = rows[cid]
        b = json.load(open(w2 / "bundles_graded" / cid / "bundle.json"))
        raw = (w2 / "bundles_graded" / cid / "source.txt").read_bytes()
        segs = b["segments"]
        k8 = clean(segment(raw, segs[0]))
        m = re.search(r"Item\s+\d\.\d{2}.*", k8)
        ex = next((s for s in segs if s["doc_type"].upper().startswith("EX-99")), None)
        reg = re.search(r"(\S.{2,100}?)\s*\(Exact name of registrant", k8, re.I)
        tag = "Y" if cid in spec["sample"] else "motivating"
        lines.append(f"=== R{n} {cid} {r['template']} {r['proxy_cell']} items={r['items']} "
                     f"bodyfam={r['body_family_hits']} issuer_in_head={r['issuer_named_in_headline']} sample={tag}")
        lines.append(f"  HEAD: {cand[cid]['title']}  [tk={cand[cid]['ticker']}]")
        lines.append(f"  REG: {reg.group(1)[-80:] if reg else '?'}")
        lines.append(f"  ITEM: {m.group(0)[:420] if m else k8[-300:]}")
        lines.append(f"  EX: {clean(segment(raw, ex))[:380] if ex else '-'}")
    return lines


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


FLAGS = {
    "body_family_zero": lambda r: r["body_family_hits"] == 0,
    "issuer_not_in_headline": lambda r: not r["issuer_named_in_headline"],
    "earnings_only_items_T1_T3": lambda r: r["template"] in ("T1", "T3") and r["qualifying_items"] == ["2.02"],
}


def score(rows, spec, verdicts):
    v = {x["case_id"]: x for x in verdicts["verdicts"]}
    missing = [c for c in spec["sample"] + spec["motivating"] if c not in v]
    if missing:
        raise SystemExit(f"verdicts missing for {missing}")
    sample = spec["sample"]
    n = len(sample)
    cls = collections.Counter(v[c]["class"] for c in sample)
    kinds = collections.Counter((v[c]["class"], v[c]["kind"]) for c in sample if v[c]["class"] != "MATCH")
    non = n - cls["MATCH"]
    flags = {}
    for name, f in list(FLAGS.items()) + [("any_flag", lambda r: any(g(r) for g in FLAGS.values()))]:
        tp = sum(1 for c in sample if f(rows[c]) and v[c]["class"] != "MATCH")
        fp = sum(1 for c in sample if f(rows[c]) and v[c]["class"] == "MATCH")
        fn = non - tp
        flags[name] = {"flagged": tp + fp, "true_pos": tp, "false_pos": fp, "missed_non_match": fn,
                       "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                       "recall": round(tp / non, 3) if non else None,
                       "population_flag_rate": round(sum(1 for r in rows.values() if f(r)) / len(rows), 3)}
    slot_by = collections.defaultdict(collections.Counter)
    for c in sample:
        slot_by[v[c]["class"]].update(rows[c]["slot_classes"])
    slot_share = {k: {"n_slots": sum(cnt.values()),
                      "share": {s: round(x / sum(cnt.values()), 3) for s, x in sorted(cnt.items())}}
                  for k, cnt in sorted(slot_by.items())}
    by_template = collections.defaultdict(collections.Counter)
    for c in sample:
        by_template[rows[c]["template"]][v[c]["class"]] += 1
    per_case = []
    for c in sample + [m for m in spec["motivating"] if m not in sample]:
        r = rows[c]
        per_case.append({k: r[k] for k in ("case_id", "template", "proxy_cell", "fold", "qualifying_items",
                                           "issuer_named_in_headline", "body_family_hits", "slot_classes")}
                        | {"in_sample": c in sample, "class": v[c]["class"], "kind": v[c]["kind"],
                           "note": v[c]["note"], "flags": sorted(k for k, f in FLAGS.items() if f(r))})
    return {"seed": spec["seed"], "n_population": spec["n_population"], "n_sample": n,
            "auditor": verdicts["auditor"], "class_definitions": verdicts["classes"],
            "class_counts": dict(sorted(cls.items())),
            "class_rate_wilson95": {k: {"rate": round(x / n, 3), "ci": wilson(x, n)} for k, x in sorted(cls.items())},
            "non_match": {"n": non, "rate": round(non / n, 3), "ci": wilson(non, n)},
            "non_match_kinds": {f"{a}/{b}": x for (a, b), x in sorted(kinds.items())},
            "class_by_template": {t: dict(sorted(x.items())) for t, x in sorted(by_template.items())},
            "flags_vs_verdicts": flags, "slot_classes_by_verdict": slot_share, "cases": per_case}


def main():
    w2, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rows, cand = census(w2, bench)
    spec = draw(rows)
    (out / "sample_routing.json").write_text(json.dumps(spec, indent=1) + "\n")
    for old in out.glob("batch_routing_*.txt"):
        old.unlink()
    (out / "batch_routing_1.txt").write_text("\n".join(cards(w2, rows, cand, spec)) + "\n")
    print(len(spec["sample"]), "sampled of", spec["n_population"])
    if len(sys.argv) > 4:
        res = score(rows, spec, json.loads(Path(sys.argv[4]).read_text()))
        (out / "routing_check.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        print("classes", res["class_counts"], "non_match", res["non_match"])
        for k, f in res["flags_vs_verdicts"].items():
            print(" ", k, {x: f[x] for x in ("flagged", "precision", "recall", "population_flag_rate")})
        for k, s in res["slot_classes_by_verdict"].items():
            print(" ", k, s)


if __name__ == "__main__":
    main()
