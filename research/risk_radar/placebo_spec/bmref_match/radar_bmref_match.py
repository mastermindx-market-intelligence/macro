"""Part (b) reference match on the Radar desk-side reads, under ceo-ruling-bm-ref-unmatched-share-20261113.

Reads only the stored per-series target and achieved shares of the price reference forms
(near, dd) in each read's committed result.json. No outcome is joined and nothing is rescored.

Matched iff the pooled achieved share is within 0.01 absolute AND within 20% relative of the
pooled target. "Pooled" is the per-series mean, which is how bm_ref forms target_budget_mean
and the reference's alert_budget; that equality is asserted for every form.
Per series: the same test is applied to that series' own target and achieved; the count of
misses and the largest absolute miss are printed. Description only (rule 2).
Rule 3: the stronger form is chosen among matched forms only; the recorded choice is shown
beside it, and no verdict is reopened.

Usage: python3 radar_bmref_match.py <catalogue_read dir> <out.json> <out.md>
"""
import json
import sys
from pathlib import Path

ABS, REL = 0.01, 0.20


def matched(t, a):
    return abs(a - t) <= ABS and abs(a - t) <= REL * t


def form_row(f):
    tgt, ach = f["target_budget"], f["achieved_share"]
    assert set(tgt) == set(ach)
    t = sum(tgt.values()) / len(tgt)
    a = sum(ach.values()) / len(ach)
    if "alert_budget" in f:
        assert abs(f["alert_budget"] - a) < 1e-9, (f["alert_budget"], a)
    per = {s: {"target": tgt[s], "achieved": ach[s], "matched": matched(tgt[s], ach[s])} for s in tgt}
    miss = {s: abs(v["achieved"] - v["target"]) for s, v in per.items() if not v["matched"]}
    worst = max(miss, key=miss.get) if miss else None
    return {"target_pooled": t, "achieved_pooled": a, "abs_gap": a - t,
            "rel_gap": (a - t) / t if t else None, "matched": matched(t, a),
            "series_n": len(per), "series_missing": len(miss),
            "largest_single_miss": None if worst is None else
            {"series": worst, "target": tgt[worst], "achieved": ach[worst]},
            "per_series": per}


def sets(root):
    v2 = json.load(open(root / "v2_bmref/result.json"))
    rows = {"479": "rr-roff-incumbent-v2", "480": "rr-ron-incumbent-v2",
            "481": "rr-roff-confluence-k4-v2", "482": "rr-ron-confluence-k4-v2",
            "483": "rr-ron-exit-v1-v2"}
    for row, sid in rows.items():
        s = v2["sets"][sid]
        yield row, sid, s["references"], s.get("better_reference")
    pre = json.load(open(root / "followup_pre/result.json"))
    yield "484", "rr-roff-confluence-k3-followup", pre["reference_match"], pre.get("better_reference")
    rev = json.load(open(root / "followup_rev1/result.json"))
    yield "512 (note under 484)", "rev1 a k3 repro", rev["a"]["reference_match"], rev["a"].get("better_reference")
    yield "514 (note)", "rev1 c realrate desc", rev["c"]["reference_match_own"], rev["c"].get("better_reference_own")
    bt = json.load(open(root / "bt1_pre/result.json"))
    yield "535", "bt1 dfii10", bt["dfii10"]["reference_match"], bt["dfii10"].get("better_reference")
    yield "537", "bt1 dgs10", bt["dgs10"]["reference_match"], bt["dgs10"].get("better_reference")


def main(root, out_json, out_md):
    root = Path(root)
    res, lines = [], []
    for row, sid, forms, recorded in sets(root):
        fr = {k: form_row(v) for k, v in forms.items() if k in ("near", "dd")}
        ok = [k for k, v in fr.items() if v["matched"]]
        res.append({"ledger_row": row, "set": sid, "forms": fr, "matched_forms": ok,
                    "recorded_better_reference": recorded,
                    "line_b": "matched" if ok else "(b) reference not matched at this exposure"})
        for k, v in fr.items():
            w = v["largest_single_miss"]
            lines.append(f"| {row} | {sid} | {k} | {v['target_pooled']:.4f} | {v['achieved_pooled']:.4f} | "
                         f"{'yes' if v['matched'] else '**no**'} | {v['series_missing']}/{v['series_n']} | "
                         + (f"{w['series']} {w['target']:.4f}→{w['achieved']:.4f}" if w else "—")
                         + f" | {recorded if k == list(fr)[0] else ''} |")
    json.dump({"rule": "ceo-ruling-bm-ref-unmatched-share-20261113", "abs": ABS, "rel": REL,
               "pooled": "per-series mean (= bm_ref target_budget_mean / alert_budget)",
               "sets": res}, open(out_json, "w"), indent=1)
    head = ("# Part (b) reference match — Radar desk-side reads (description; no verdict reopened)\n\n"
            "Rule ceo-ruling-bm-ref-unmatched-share-20261113: matched iff pooled achieved is within 0.01 "
            "absolute AND 20% relative of target; otherwise \"(b) reference not matched at this exposure\". "
            "Read from stored per-series shares; no outcome joined. Placebo p90 under repair; part (a) provisional.\n\n"
            "| row | set | form | target | achieved | matched | series missing | largest single miss | recorded stronger form |\n"
            "|---|---|---|---:|---:|---|---:|---|---|\n")
    Path(out_md).write_text(head + "\n".join(lines) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
