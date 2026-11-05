"""Seat tool: validate the frozen routing gates 2 (ni-routing-gates-2, commit 5baa4b10) on a fresh seed.
usage (from the repository tree root):
  PYTHONPATH=. python3.12 build_gates2_validation.py SCRATCH_W2 BENCH_DIR OUT_DIR            (pool + sample + blind cards)
  PYTHONPATH=. python3.12 build_gates2_validation.py SCRATCH_W2 BENCH_DIR OUT_DIR VERDICTS   (also score the verdicts)
BENCH_DIR is results_w2. The pool is every w2 candidate with an available attached body, less every
case a card has already shown: the 43 routing-check cases (audit/routing_verdicts.json) and the 60
gates-1 validation cases (audit/gate_verdicts.json). The seat read those 103 cards while building
gates-2, so none of them can test it. Gate statuses are recomputed here from the frozen
engine.news_impact.routing_gates_2.
Pre-registered by DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH (3), fixed in this file and committed
before any gates-2 status on the uncarded pool was computed:
  sample      seed 20261018; n_in = min(40, gated-in pool) gated-in cases, then n_out = min(20,
              gated-out pool) gated-out cases, each a simple random sample of the sorted case ids;
              the cards are shuffled with the same generator so a card never shows its gate status.
  classes     the four routing-check classes (MATCH, NO_EVENT, OTHER_EVENT, WRONG_ISSUER).
  gated-in    the gates are accepted when MATCH is at least ceil(0.85 * n_in) of n_in (34 of 40).
              n_in under 30 is flagged underpowered; the bar still applies.
  gated-out   the same population-weighted share of real events dropped as the gates-1 validation,
              with the same bound interval. Bar: 0.20 or less. OTHER_EVENT cases do not count as dropped.
  per family  pool and sample counts by template, MATCH by template, and each template's estimated
              on-event cases in this pool beside the masterplan's 200 per template (the shortfall
              is printed, never hidden).
  auditor     the seat wrote gates-2 and classes the cards; this is disclosed in the output. A second
              auditor classes the same cards when a labeling lane opens.
  no rule change after this tool first runs on the uncarded pool; a miss is printed, not hidden.
OUT_DIR mode writes:
  sample_gates2.json    seed, pool counts, the sampled case ids with their gate status, card order.
  batch_gates2_1.txt    one blind card per sampled case (same layout as the gates-1 cards). The cards
                        quote headlines and filing text: they are scratch-only and are never committed.
VERDICTS mode also writes:
  gates2_validation.json  per case the gate status, class, kind and paraphrased note; class counts with
                          Wilson 95% intervals for each arm; both bars with PASS or MISS; per-family rows.
The JSON outputs carry ids, codes, counts and paraphrased notes only, never text.
"""
import collections
import json
import math
import random
import sys
from pathlib import Path

import build_gate_validation as v1
from engine.news_impact import routing_gates_2 as rg

SEED = 20261018
N_IN_MAX = 40
N_OUT_MAX = 20
MATCH_SHARE = 0.85
UNDERPOWERED_BELOW = 30
DROP_BAR = 0.20
TARGET_PER_TEMPLATE = 200
FREEZE_COMMIT = "5baa4b10912d"
TEMPLATES = ("T1", "T2", "T3")


def carded(bench):
    ids = set()
    for name in ("routing_verdicts.json", "gate_verdicts.json"):
        ids |= {v["case_id"] for v in json.loads((bench / "audit" / name).read_text())["verdicts"]}
    return ids


def pool(w2, bench):
    """Body-available candidates no card has shown, with recomputed gates-2 statuses."""
    seen = carded(bench)
    cand = {r["item_id"]: r for r in v1.jl(w2 / "candidates_all.jsonl")}
    bodies = {r["item_id"]: r for r in v1.jl(w2 / "bodies_all" / "bodies.jsonl")}
    avail = sorted(c for c in cand if bodies.get(c, {}).get("status") == "available")
    missing = sorted(seen - set(avail))
    if missing:
        raise SystemExit(f"carded cases without an available body: {missing}")
    ids = [c for c in avail if c not in seen]
    gates = rg.build_gate_map([cand[c] for c in ids], bodies, w2 / "bodies_all" / "texts")
    return ids, gates, cand, bodies, len(avail), len(seen)


def draw(ids, gates, cand, n_avail, n_carded):
    rng = random.Random(SEED)
    gin = sorted(c for c in ids if gates[c] == rg.GATED_IN)
    gout = sorted(c for c in ids if gates[c] != rg.GATED_IN)
    n_in, n_out = min(N_IN_MAX, len(gin)), min(N_OUT_MAX, len(gout))
    s_in = sorted(rng.sample(gin, n_in))
    s_out = sorted(rng.sample(gout, n_out))
    order = s_in + s_out
    rng.shuffle(order)
    by_tpl = {arm: dict(sorted(collections.Counter(cand[c]["template"] for c in grp).items()))
              for arm, grp in (("gated_in", gin), ("gated_out", gout))}
    return {"seed": SEED, "gates_version": rg.GATES_VERSION, "n_body_available": n_avail,
            "n_carded_excluded": n_carded, "n_pool": len(ids), "n_pool_gated_in": len(gin),
            "n_pool_gated_out": len(gout), "pool_by_template": by_tpl,
            "pool_gated_out_codes": dict(sorted(collections.Counter(gates[c] for c in gout).items())),
            "n_in": n_in, "n_out": n_out, "match_bar": math.ceil(MATCH_SHARE * n_in),
            "underpowered": n_in < UNDERPOWERED_BELOW,
            "sample_gated_in": s_in, "sample_gated_out": s_out,
            "sample_template": {c: cand[c]["template"] for c in sorted(order)},
            "sample_status": {c: gates[c] for c in sorted(order)}, "card_order": order}


def _families(spec, v):
    rows = {}
    for t in TEMPLATES:
        est, row = 0.0, {}
        for arm in ("gated_in", "gated_out"):
            ids = [c for c in spec[f"sample_{arm}"] if spec["sample_template"][c] == t]
            k = sum(v[c]["class"] == "MATCH" for c in ids)
            n_pool = spec["pool_by_template"][arm].get(t, 0)
            rate = k / len(ids) if ids else None
            if rate is not None:
                est += rate * n_pool
            row[arm] = {"pool": n_pool, "sampled": len(ids), "match": k,
                        "match_rate": None if rate is None else round(rate, 3)}
        unmeasured = [a for a in ("gated_in", "gated_out") if row[a]["sampled"] == 0 and row[a]["pool"] > 0]
        row["on_event_in_pool_est"] = round(est, 1)
        row["unmeasured_arms"] = unmeasured
        row["target"] = TARGET_PER_TEMPLATE
        row["shortfall_vs_target"] = round(TARGET_PER_TEMPLATE - est, 1)
        rows[t] = row
    return rows


def score(spec, verdicts):
    v = {x["case_id"]: x for x in verdicts["verdicts"]}
    missing = [c for c in spec["card_order"] if c not in v]
    if missing:
        raise SystemExit(f"verdicts missing for {missing}")
    extra = sorted(set(v) - set(spec["card_order"]))
    if extra:
        raise SystemExit(f"verdicts for cases outside the sample: {extra}")
    bad = sorted({x["class"] for x in v.values()} - set(verdicts["classes"]))
    if bad:
        raise SystemExit(f"unknown classes {bad}")
    s_in, s_out = spec["sample_gated_in"], spec["sample_gated_out"]
    arm_in, arm_out = v1._arm(s_in, v), v1._arm(s_out, v)
    k_in = arm_in["class_counts"].get("MATCH", 0)
    k_out = arm_out["class_counts"].get("MATCH", 0)
    drop = v1._drop_share(k_in, len(s_in), k_out, len(s_out), spec["n_pool_gated_in"], spec["n_pool_gated_out"])
    by_code = collections.defaultdict(collections.Counter)
    for c in s_out:
        by_code[spec["sample_status"][c]][v[c]["class"]] += 1
    per_case = [{"case_id": c, "arm": "gated_in" if c in s_in else "gated_out", "template": spec["sample_template"][c],
                 "gate_status": spec["sample_status"][c], "class": v[c]["class"], "kind": v[c]["kind"],
                 "note": v[c]["note"]} for c in sorted(spec["card_order"])]
    bar = spec["match_bar"]
    return {"seed": spec["seed"], "gates_version": spec["gates_version"], "gates_freeze_commit": FREEZE_COMMIT,
            "auditor": verdicts["auditor"], "class_definitions": verdicts["classes"],
            "pool": {k: spec[k] for k in ("n_body_available", "n_carded_excluded", "n_pool", "n_pool_gated_in",
                                          "n_pool_gated_out", "pool_by_template", "pool_gated_out_codes")},
            "gated_in": arm_in | {"bar": f"MATCH >= {bar} of {spec['n_in']}", "match": k_in,
                                  "underpowered": spec["underpowered"],
                                  "verdict": "PASS" if k_in >= bar else "MISS"},
            "gated_out": arm_out | {"classes_by_gate_code": {g: dict(sorted(x.items())) for g, x in sorted(by_code.items())},
                                    "real_events_dropped": drop, "bar": f"share <= {DROP_BAR}",
                                    "verdict": "PASS" if drop["share"] is not None and drop["share"] <= DROP_BAR else "MISS"},
            "families": _families(spec, v),
            "cases": per_case}


def main():
    w2, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    ids, gates, cand, bodies, n_avail, n_carded = pool(w2, bench)
    spec = draw(ids, gates, cand, n_avail, n_carded)
    (out / "sample_gates2.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    for old in out.glob("batch_gates2_*.txt"):
        old.unlink()
    (out / "batch_gates2_1.txt").write_text("\n".join(v1.cards(w2, cand, bodies, spec)) + "\n")
    print("pool", spec["n_pool"], "gated_in", spec["n_pool_gated_in"], "gated_out", spec["n_pool_gated_out"],
          "sampled", len(spec["card_order"]), "bar", spec["match_bar"], "of", spec["n_in"],
          "underpowered" if spec["underpowered"] else "")
    print("pool by template", spec["pool_by_template"])
    if len(sys.argv) > 4:
        res = score(spec, json.loads(Path(sys.argv[4]).read_text()))
        (out / "gates2_validation.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        gi, go = res["gated_in"], res["gated_out"]
        print("gated_in ", gi["class_counts"], gi["bar"], "->", gi["verdict"])
        print("gated_out", go["class_counts"], "dropped", go["real_events_dropped"], go["bar"], "->", go["verdict"])
        for g, x in go["classes_by_gate_code"].items():
            print(" ", g, x)
        for t, row in res["families"].items():
            print(" ", t, "on-event est", row["on_event_in_pool_est"], "shortfall vs", row["target"],
                  row["shortfall_vs_target"], "unmeasured", row["unmeasured_arms"])


if __name__ == "__main__":
    main()
