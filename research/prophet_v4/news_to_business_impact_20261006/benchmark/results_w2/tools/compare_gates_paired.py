"""Seat tool: pick the draw filter between the frozen routing gates 1 and 2 on the gates-2 validation pool.
usage (from the repository tree root):
  PYTHONPATH=. python3.12 compare_gates_paired.py SCRATCH_W2 BENCH_DIR OUT_DIR            (disagreement set + blind cards)
  PYTHONPATH=. python3.12 compare_gates_paired.py SCRATCH_W2 BENCH_DIR OUT_DIR VERDICTS   (also score the verdicts)
Both gate sets missed the 34 of 40 bar (DSC:NEWS-IMPACT-ROUTING-GATES-1-VALIDATION,
DSC:NEWS-IMPACT-ROUTING-GATES-2-VALIDATION), so neither is an on-event guarantee and every scored
case keeps its own routing verdict. This tool answers the narrower question the continuation still
has: which of the two filters the draw should use. It is a post-hoc comparison. Its rule is fixed in
this file and committed before any of the cards it writes is read.
  pool        the 132-case pool of the gates-2 validation (build_gates2_validation.pool): no card had
              shown any of them before that validation, and neither gate set was built on them.
  paired set  the pool cases on which the two gate sets disagree (one gates in, the other gates out).
              Agreeing cases enter both filters' gated-in sets alike, so the disagreement set decides
              the comparison exactly; it is classed in full, not sampled.
  classes     a disagreement case already classed in the gates-2 validation keeps that class
              (audit/gates2_validation.json). Every other one gets a blind card here, shuffled on seed
              20261019 with both gate statuses hidden.
  right       a gate set is right on a case when it gates in a MATCH or gates out a non-MATCH.
  rule        gates 2 replaces gates 1 as the draw filter when it is right on more disagreement cases
              than gates 1. A tie keeps gates 1. Either filter stays a filter, never a guarantee.
OUT_DIR mode writes:
  sample_paired.json    pool cross-tab, the disagreement ids with both statuses, which ones need cards,
                        and the card order.
  batch_paired_1.txt    one blind card per unclassed disagreement case (same layout as the validation
                        cards). The cards quote headlines and filing text: scratch-only, never committed.
VERDICTS mode also writes:
  gates_paired.json     per disagreement case both statuses, the class and its source; the count each
                        gate set is right on; the filter the rule picks.
The JSON outputs carry ids, codes, counts and paraphrased notes only, never text.
"""
import collections
import json
import random
import sys
from pathlib import Path

import build_gate_validation as v1
import build_gates2_validation as v2
from engine.news_impact import routing_gates as g1
from engine.news_impact import routing_gates_2 as g2

SEED = 20261019


def disagreements(w2, bench):
    ids, gates2, cand, bodies, _, _ = v2.pool(w2, bench)
    gates1 = g1.build_gate_map([cand[c] for c in ids], bodies, w2 / "bodies_all" / "texts")
    cross = collections.Counter(
        f"g1_{'in' if gates1[c] == g1.GATED_IN else 'out'}/g2_{'in' if gates2[c] == g2.GATED_IN else 'out'}" for c in ids
    )
    paired = sorted(c for c in ids if (gates1[c] == g1.GATED_IN) != (gates2[c] == g2.GATED_IN))
    return ids, paired, gates1, gates2, cand, bodies, dict(sorted(cross.items()))


def prior_classes(bench):
    val = json.loads((bench / "audit" / "gates2_validation.json").read_text())
    return {c["case_id"]: c for c in val["cases"]}


def spec_for(ids, paired, gates1, gates2, cross, prior):
    need = [c for c in paired if c not in prior]
    order = list(need)
    random.Random(SEED).shuffle(order)
    return {"seed": SEED, "n_pool": len(ids), "pool_cross_tab": cross, "paired": paired,
            "paired_status": {c: {"gates_1": gates1[c], "gates_2": gates2[c]} for c in paired},
            "already_classed": [c for c in paired if c in prior], "card_order": order}


def _right(status, cls, gated_in):
    return (status == gated_in) == (cls == "MATCH")


def score(spec, prior, verdicts):
    v = {x["case_id"]: x for x in verdicts["verdicts"]}
    missing = [c for c in spec["card_order"] if c not in v]
    if missing:
        raise SystemExit(f"verdicts missing for {missing}")
    extra = sorted(set(v) - set(spec["card_order"]))
    if extra:
        raise SystemExit(f"verdicts for cases outside the card set: {extra}")
    bad = sorted({x["class"] for x in v.values()} - set(verdicts["classes"]))
    if bad:
        raise SystemExit(f"unknown classes {bad}")
    rows, right = [], collections.Counter()
    for c in spec["paired"]:
        src = prior.get(c) or v[c]
        st = spec["paired_status"][c]
        r1 = _right(st["gates_1"], src["class"], g1.GATED_IN)
        r2 = _right(st["gates_2"], src["class"], g2.GATED_IN)
        right["gates_1"] += r1
        right["gates_2"] += r2
        rows.append({"case_id": c, "gates_1": st["gates_1"], "gates_2": st["gates_2"], "class": src["class"],
                     "kind": src["kind"], "note": src["note"],
                     "class_source": "gates2_validation" if c in prior else "paired_verdicts",
                     "right": "gates_2" if r2 and not r1 else "gates_1" if r1 and not r2 else "both" if r1 else "neither"})
    pick = "ni-routing-gates-2" if right["gates_2"] > right["gates_1"] else "ni-routing-gates-1"
    cells = collections.Counter((r["gates_1"] == g1.GATED_IN, r["gates_2"] == g2.GATED_IN, r["class"]) for r in rows)
    return {"seed": spec["seed"], "auditor": verdicts["auditor"], "n_pool": spec["n_pool"],
            "pool_cross_tab": spec["pool_cross_tab"], "n_paired": len(rows),
            "n_classed_here": len(spec["card_order"]), "n_classed_in_validation": len(spec["already_classed"]),
            "paired_cells": {f"g1_{'in' if a else 'out'}/g2_{'in' if b else 'out'}/{k}": n
                             for (a, b, k), n in sorted(cells.items())},
            "right": dict(sorted(right.items())), "rule": "gates 2 when right on more paired cases; a tie keeps gates 1",
            "filter_pick": pick, "cases": rows}


def main():
    w2, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    ids, paired, gates1, gates2, cand, bodies, cross = disagreements(w2, bench)
    prior = prior_classes(bench)
    spec = spec_for(ids, paired, gates1, gates2, cross, prior)
    (out / "sample_paired.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    for old in out.glob("batch_paired_*.txt"):
        old.unlink()
    (out / "batch_paired_1.txt").write_text("\n".join(v1.cards(w2, cand, bodies, spec)) + "\n")
    print("pool", spec["n_pool"], "cross", cross, "paired", len(paired), "already classed",
          len(spec["already_classed"]), "cards", len(spec["card_order"]))
    if len(sys.argv) > 4:
        res = score(spec, prior, json.loads(Path(sys.argv[4]).read_text()))
        (out / "gates_paired.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        print("cells", res["paired_cells"])
        print("right", res["right"], "->", res["filter_pick"])


if __name__ == "__main__":
    main()
