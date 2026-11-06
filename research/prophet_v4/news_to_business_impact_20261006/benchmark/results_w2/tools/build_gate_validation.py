"""Seat tool: validate the frozen routing gates (ni-routing-gates-1, commit a8f98d21) on a fresh seed.
usage (from the repository tree root):
  PYTHONPATH=. python3.12 build_gate_validation.py SCRATCH_W2 BENCH_DIR OUT_DIR            (pool + sample + blind cards)
  PYTHONPATH=. python3.12 build_gate_validation.py SCRATCH_W2 BENCH_DIR OUT_DIR VERDICTS   (also score the verdicts)
BENCH_DIR is results_w2. The pool is every w2 candidate with an available attached body, less the
43 cases already classed by the routing check (audit/routing_verdicts.json), which trained the gates.
Gate statuses are recomputed here from the frozen engine.news_impact.routing_gates.
Pre-registered by DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES (3), fixed before any card was read:
  sample      seed 20261017; 40 gated-in cases, then 20 gated-out cases, each a simple random sample
              of the sorted case ids; the 60 cards are shuffled with the same generator so a card
              never shows its gate status.
  classes     the four routing-check classes (MATCH, NO_EVENT, OTHER_EVENT, WRONG_ISSUER).
  gated-in    the gates are accepted when MATCH is at least 34 of 40.
  gated-out   a real event is a case classed MATCH. The share of real events the gates dropped is
              the population-weighted estimate dropped / (dropped + kept), where dropped is the
              gated-out MATCH rate times the gated-out pool and kept is the gated-in MATCH rate
              times the gated-in pool. Bar: 0.20 or less. OTHER_EVENT cases (a real event no
              attached filing reports) are printed beside it and do not count as dropped, because
              no gate can keep a case whose body does not report the event.
  a miss is printed, not hidden.
OUT_DIR mode writes:
  sample_gates.json     seed, pool counts, the sampled case ids with their gate status, card order.
  batch_gates_1.txt     one blind card per sampled case: headline, ticker, issuer, registrant, and per
                        attached filing its items, item text and exhibit opening. The cards quote
                        headlines and filing text: they are scratch-only and are never committed.
VERDICTS mode also writes:
  gate_validation.json  per case the gate status, class, kind and paraphrased note; the class counts
                        with Wilson 95% intervals for each arm; both bars with PASS or MISS.
The JSON outputs carry ids, codes, counts and paraphrased notes only, never text.
"""
import collections
import json
import math
import random
import re
import sys
from pathlib import Path

from engine.news_impact import routing_gates as rg

SEED = 20261017
N_IN = 40
N_OUT = 20
MATCH_BAR = 34
DROP_BAR = 0.20
ITEM_CHARS = 600
EX_CHARS = 450


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def clean(s):
    return re.sub(r"\s+", " ", s)


def pool(w2, bench):
    """Body-available candidates outside the gate-training set, with recomputed gate statuses."""
    trained = {v["case_id"] for v in json.loads((bench / "audit" / "routing_verdicts.json").read_text())["verdicts"]}
    cand = {r["item_id"]: r for r in jl(w2 / "candidates_all.jsonl")}
    bodies = {r["item_id"]: r for r in jl(w2 / "bodies_all" / "bodies.jsonl")}
    avail = sorted(c for c in cand if bodies.get(c, {}).get("status") == "available")
    missing = sorted(trained - set(avail))
    if missing:
        raise SystemExit(f"trained cases without an available body: {missing}")
    ids = [c for c in avail if c not in trained]
    gates = rg.build_gate_map([cand[c] for c in ids], bodies, w2 / "bodies_all" / "texts")
    return ids, gates, cand, bodies, len(avail), len(trained)


def draw(ids, gates, n_avail, n_trained):
    rng = random.Random(SEED)
    gin = sorted(c for c in ids if gates[c] == rg.GATED_IN)
    gout = sorted(c for c in ids if gates[c] != rg.GATED_IN)
    s_in = sorted(rng.sample(gin, N_IN))
    s_out = sorted(rng.sample(gout, N_OUT))
    order = s_in + s_out
    rng.shuffle(order)
    return {"seed": SEED, "gates_version": rg.GATES_VERSION, "n_body_available": n_avail,
            "n_training_excluded": n_trained, "n_pool": len(ids), "n_pool_gated_in": len(gin),
            "n_pool_gated_out": len(gout),
            "pool_gated_out_codes": dict(sorted(collections.Counter(gates[c] for c in gout).items())),
            "sample_gated_in": s_in, "sample_gated_out": s_out,
            "sample_status": {c: gates[c] for c in sorted(order)}, "card_order": order}


def cards(w2, cand, bodies, spec):
    texts = w2 / "bodies_all" / "texts"
    lines = []
    for n, cid in enumerate(spec["card_order"], 1):
        c, b = cand[cid], bodies[cid]
        lines.append(f"=== V{n} {cid} {c['template']}")
        lines.append(f"  HEAD: {c.get('title') or ''}  [tk={c['ticker']} issuer={c.get('issuer')}]")
        for j, f in enumerate(b["filings"], 1):
            docs = [d for d in f.get("documents") or () if d.get("status") == "available"]
            k8 = next((d for d in docs if str(d.get("doc_type")).upper() == "8-K"), None)
            ex = next((d for d in docs if str(d.get("doc_type")).upper().startswith("EX-99")), None)
            lines.append(f"  F{j} {f.get('form')} {f.get('filing_date')} items={f.get('items')}")
            if k8:
                t = clean((texts / f"{k8['text_sha256']}.txt").read_text(encoding="utf-8", errors="replace"))
                reg = re.search(r"(\S.{2,100}?)\s*\(Exact name of (?:the )?registrant", t, re.I)
                m = re.search(r"Item\s+\d\.\d{2}.*", t)
                lines.append(f"    REG: {reg.group(1)[-80:] if reg else '?'}")
                lines.append(f"    ITEM: {m.group(0)[:ITEM_CHARS] if m else t[-300:]}")
            if ex:
                t = clean((texts / f"{ex['text_sha256']}.txt").read_text(encoding="utf-8", errors="replace"))
                lines.append(f"    EX: {t[:EX_CHARS]}")
    return lines


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def _arm(ids, v):
    n = len(ids)
    cls = collections.Counter(v[c]["class"] for c in ids)
    kinds = collections.Counter(f"{v[c]['class']}/{v[c]['kind']}" for c in ids if v[c]["class"] != "MATCH")
    return {"n": n, "class_counts": dict(sorted(cls.items())),
            "class_rate_wilson95": {k: {"rate": round(x / n, 3), "ci": wilson(x, n)} for k, x in sorted(cls.items())},
            "non_match_kinds": dict(sorted(kinds.items()))}


def _drop_share(k_in, n_in, k_out, n_out, pool_in, pool_out):
    kept = k_in / n_in * pool_in
    dropped = k_out / n_out * pool_out
    point = dropped / (dropped + kept) if dropped + kept else None
    lo_in, hi_in = wilson(k_in, n_in)
    lo_out, hi_out = wilson(k_out, n_out)
    lo = lo_out * pool_out / (lo_out * pool_out + hi_in * pool_in) if lo_out * pool_out + hi_in * pool_in else 0.0
    hi = hi_out * pool_out / (hi_out * pool_out + lo_in * pool_in) if hi_out * pool_out + lo_in * pool_in else 1.0
    return {"kept_real_est": round(kept, 1), "dropped_real_est": round(dropped, 1),
            "share": None if point is None else round(point, 3), "bound_interval": [round(lo, 3), round(hi, 3)]}


def score(spec, verdicts):
    v = {x["case_id"]: x for x in verdicts["verdicts"]}
    missing = [c for c in spec["card_order"] if c not in v]
    if missing:
        raise SystemExit(f"verdicts missing for {missing}")
    bad = sorted({x["class"] for x in v.values()} - set(verdicts["classes"]))
    if bad:
        raise SystemExit(f"unknown classes {bad}")
    s_in, s_out = spec["sample_gated_in"], spec["sample_gated_out"]
    arm_in, arm_out = _arm(s_in, v), _arm(s_out, v)
    k_in = arm_in["class_counts"].get("MATCH", 0)
    k_out = arm_out["class_counts"].get("MATCH", 0)
    drop = _drop_share(k_in, len(s_in), k_out, len(s_out), spec["n_pool_gated_in"], spec["n_pool_gated_out"])
    by_code = collections.defaultdict(collections.Counter)
    for c in s_out:
        by_code[spec["sample_status"][c]][v[c]["class"]] += 1
    per_case = [{"case_id": c, "arm": "gated_in" if c in s_in else "gated_out", "gate_status": spec["sample_status"][c],
                 "class": v[c]["class"], "kind": v[c]["kind"], "note": v[c]["note"]} for c in sorted(spec["card_order"])]
    return {"seed": spec["seed"], "gates_version": spec["gates_version"], "gates_freeze_commit": "a8f98d21e873",
            "auditor": verdicts["auditor"], "class_definitions": verdicts["classes"],
            "pool": {k: spec[k] for k in ("n_body_available", "n_training_excluded", "n_pool", "n_pool_gated_in",
                                          "n_pool_gated_out", "pool_gated_out_codes")},
            "gated_in": arm_in | {"bar": f"MATCH >= {MATCH_BAR} of {N_IN}", "match": k_in,
                                  "verdict": "PASS" if k_in >= MATCH_BAR else "MISS"},
            "gated_out": arm_out | {"classes_by_gate_code": {g: dict(sorted(x.items())) for g, x in sorted(by_code.items())},
                                    "real_events_dropped": drop, "bar": f"share <= {DROP_BAR}",
                                    "verdict": "PASS" if drop["share"] is not None and drop["share"] <= DROP_BAR else "MISS"},
            "cases": per_case}


def main():
    w2, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    ids, gates, cand, bodies, n_avail, n_trained = pool(w2, bench)
    spec = draw(ids, gates, n_avail, n_trained)
    (out / "sample_gates.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    for old in out.glob("batch_gates_*.txt"):
        old.unlink()
    (out / "batch_gates_1.txt").write_text("\n".join(cards(w2, cand, bodies, spec)) + "\n")
    print("pool", spec["n_pool"], "gated_in", spec["n_pool_gated_in"], "gated_out", spec["n_pool_gated_out"],
          "sampled", len(spec["card_order"]))
    if len(sys.argv) > 4:
        res = score(spec, json.loads(Path(sys.argv[4]).read_text()))
        (out / "gate_validation.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        gi, go = res["gated_in"], res["gated_out"]
        print("gated_in ", gi["class_counts"], gi["bar"], "->", gi["verdict"])
        print("gated_out", go["class_counts"], "dropped", go["real_events_dropped"], go["bar"], "->", go["verdict"])
        for g, x in go["classes_by_gate_code"].items():
            print(" ", g, x)


if __name__ == "__main__":
    main()
