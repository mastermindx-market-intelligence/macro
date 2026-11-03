"""Seat tool: seeded stratified audit sample of critical slots + compact cards for adjudication.
usage: python3 build_audit.py SCRATCH_W2 OUT_DIR
Strata (seed 20261014, rows sorted by (case_id, field) before sampling):
  agree_present 20, present_value_differs 10, present_vs_absent 10.
agree_absent / absent_reason_differs / malformed_value are not sampled (disclosed as unaudited).
"""
import json, random, re, sys
from pathlib import Path
w2, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in open(w2 / "score" / "critical_slots.jsonl")]
STRATA = [("agree_present", 20), ("present_value_differs", 10), ("present_vs_absent", 10)]
rng = random.Random(20261014)
sample = []
for cls, n in STRATA:
    pool = sorted((r for r in rows if r["class"] == cls), key=lambda r: (r["case_id"], r["field"]))
    pick = rng.sample(pool, min(n, len(pool)))
    sample += sorted(pick, key=lambda r: (r["case_id"], r["field"]))
def fmt(entry):
    v, ta = entry.get("value"), entry.get("typed_absence")
    if isinstance(ta, dict) and (v is None or v == {"form": "absent"}):
        return f"ABSENT reason={ta.get('reason')}"
    if not isinstance(v, dict):
        return f"RAW {json.dumps(v)[:200]}"
    nums = v.get("value") if v.get("form") == "point" else f"[{v.get('low')}..{v.get('high')}]"
    p = v.get("period")
    if isinstance(p, dict) and "period_kind" in p:
        ps = f"{p.get('period_kind')} y={p.get('year')} q={p.get('quarter')} end={p.get('calendar_end')} ey={p.get('end_year')}"
    elif isinstance(p, dict):
        ps = f"absent:{p.get('reason')}"
    else:
        ps = repr(p)
    return f"{v.get('form')} {nums} unit={v.get('unit')} cur={v.get('currency')} basis={v.get('basis')} bound={v.get('bound')} neg={v.get('negated')} period=({ps})"
def ctx(src, span, pad=260):
    bs, be = int(span["byte_start"]), int(span["byte_end"])
    a, b = max(0, bs - pad), min(len(src), be + pad)
    t = (src[a:bs].decode("utf-8", "replace") + "«" + src[bs:be].decode("utf-8", "replace") + "»" + src[be:b].decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", t)
cards, lines = [], []
for i, r in enumerate(sample, 1):
    cid, f = r["case_id"], r["field"]
    src = (w2 / "bundles_graded" / cid / "source.txt").read_bytes()
    b = json.loads((w2 / "bundles_graded" / cid / "bundle.json").read_text())
    ent = {fam: json.loads((w2 / "labels_canon_full" / f"{cid}.{fam}.json").read_text())["fields"].get(f) or {} for fam in ("fam_a", "fam_b")}
    card = {"n": i, "case_id": cid, "field": f, "template": r["template"], "class": r["class"], "fold": r["fold"]}
    cards.append(card)
    lines.append(f"=== #{i} {cid} {r['template']} {f} [{r['class']}] headline: {str(b.get('headline') or b.get('title') or '')[:160]}")
    spans = []
    for fam in ("fam_a", "fam_b"):
        lines.append(f"  {fam}: {fmt(ent[fam])}")
        sp = ent[fam].get("source_span") or ((ent[fam].get("typed_absence") or {}).get("evidence") or {}).get("span") if isinstance(ent[fam].get("typed_absence"), dict) else ent[fam].get("source_span")
        if isinstance(sp, dict) and "byte_start" in sp:
            spans.append((fam, sp))
    shown = []
    for fam, sp in spans:
        if any(abs(int(sp["byte_start"]) - s) < 200 for s in shown):
            lines.append(f"  {fam} span ~same region")
            continue
        shown.append(int(sp["byte_start"]))
        lines.append(f"  {fam} ctx: {ctx(src, sp)}")
(out / "sample.json").write_text(json.dumps({"seed": 20261014, "strata": STRATA, "cards": cards}, indent=1) + "\n")
for k in range(0, len(lines)):
    pass
txt = "\n".join(lines)
parts = re.split(r"(?m)^(?==== #)", txt)
parts = [p for p in parts if p.strip()]
for j in range(0, len(parts), 10):
    (out / f"batch_{j//10+1}.txt").write_text("".join(parts[j:j+10]))
print(len(cards), "cards;", {c: sum(1 for x in cards if x["class"] == c) for c, _ in STRATA}, "keys:", list(b.keys())[:12])
