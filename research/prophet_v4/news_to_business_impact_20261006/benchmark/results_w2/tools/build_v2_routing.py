"""Seat tool: routing verdicts for the gated_v2 continuation draw (ni-edgar-body-2, gates-2 as draw filter).
usage (from the repository tree root):
  PYTHONPATH=.:<this dir> python3.12 build_v2_routing.py SCRATCH_W2 BENCH_DIR OUT_DIR            (census + blind cards)
  PYTHONPATH=.:<this dir> python3.12 build_v2_routing.py SCRATCH_W2 BENCH_DIR OUT_DIR VERDICTS   (also score the verdicts)
BENCH_DIR is results_w2; the draw is ../gated_v2/cases.jsonl and the graded draw ../graded/cases.jsonl.
DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 3: every scored case keeps its own routing verdict and
only MATCH cases score. 69 of the 99 drawn cases already carry a verdict from a card the seat read
(audit/routing_verdicts.json, gate_verdicts.json, gates2_verdicts.json, paired_verdicts.json). This
tool classes the rest, so that every drawn case has exactly one verdict.
Pre-registered, fixed in this file before any card of the census population was read:
  population  every gated_v2 drawn case no earlier card has shown. A census: no sampling. Card order is
              the sorted ids shuffled with seed 20261020.
  cards       built from the ni-edgar-body-2 bodies (--as-of 2026-10-14). Each filing shows its session
              offset, relation and items; for a graded case it also shows whether the filing is in the
              body that was graded (the graded bundle's accessions).
  classes     the four routing-check classes (MATCH, NO_EVENT, OTHER_EVENT, WRONG_ISSUER), unchanged.
  graded      a graded case's grade stands on its graded body (DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND, the
              73 graded cases are not regraded). For a graded case MATCH therefore requires a filing in
              the graded body that reports the event; a report only in a v2-added filing is OTHER_EVENT
              with kind graded_body_lacks_report.
  never graded a case never graded is classed against its v2 filings; its MATCH makes it a labeling case.
  information the census MATCH share with a Wilson 95% interval is printed beside 0.85 as information
              only. Gates-2 is frozen (5baa4b10); no gate revision is validated on this population.
  auditor     the seat classes the cards; this is disclosed in the output. A second auditor classes the
              same cards when a labeling lane opens.
OUT_DIR mode writes:
  v2_routing_spec.json   population counts, the census ids with template and graded flag, card order.
  batch_v2_routing_1.txt one card per census case. Cards quote headlines and filing text: scratch-only,
                         never committed.
VERDICTS mode also writes:
  v2_routing.json  per census case the class, kind and paraphrased note; class counts with Wilson 95%
                   intervals; the routing map for all drawn cases (verdict source and class); scorable
                   MATCH ids; the labeling queue (MATCH, never graded); per-template scorable counts beside
                   the masterplan's 200 with the shortfall printed.
The JSON outputs carry ids, codes, counts and paraphrased notes only, never text.
"""
import collections
import json
import random
import re
import sys
from pathlib import Path

import build_gate_validation as v1

SEED = 20261020
MATCH_SHARE = 0.85
TARGET_PER_TEMPLATE = 200
TEMPLATES = ("T1", "T2", "T3")
SOURCES = ("routing_verdicts", "gate_verdicts", "gates2_verdicts", "paired_verdicts")
BODY_VERSION = "ni-edgar-body-2"
GATES_FREEZE = "5baa4b10912d"


def prior_verdicts(bench, drawn):
    out = {}
    for name in SOURCES:
        for x in json.loads((bench / "audit" / f"{name}.json").read_text())["verdicts"]:
            if x["case_id"] not in drawn:
                continue
            if x["case_id"] in out:
                raise SystemExit(f"drawn case {x['case_id']} carded twice")
            out[x["case_id"]] = {"source": name, "class": x["class"], "kind": x["kind"]}
    return out


def census(w2, bench):
    root = bench.parent
    drawn = {r["item_id"]: r for r in v1.jl(root / "gated_v2" / "cases.jsonl")}
    graded = {r["item_id"] for r in v1.jl(root / "graded" / "cases.jsonl")}
    prior = prior_verdicts(bench, drawn)
    pop = sorted(c for c in drawn if c not in prior)
    order = list(pop)
    random.Random(SEED).shuffle(order)
    spec = {"seed": SEED, "body_version": BODY_VERSION, "gates_freeze_commit": GATES_FREEZE,
            "n_drawn": len(drawn), "n_drawn_graded": sum(c in graded for c in drawn),
            "n_prior_verdicts": len(prior),
            "prior_by_source": dict(sorted(collections.Counter(p["source"] for p in prior.values()).items())),
            "n_census": len(pop), "census_template": {c: drawn[c]["template"] for c in pop},
            "census_graded": {c: c in graded for c in pop}, "card_order": order}
    return spec, drawn, graded, prior


def graded_accessions(w2, cid):
    p = w2 / "bundles_graded" / cid / "bundle.json"
    if not p.exists():
        raise SystemExit(f"graded case {cid} has no graded bundle")
    b = json.loads(p.read_text())
    if b["case_id"] != cid:
        raise SystemExit(f"bundle case id mismatch for {cid}")
    return {s["accession"] for s in b["segments"]}


def cards(w2, spec):
    cand = {r["item_id"]: r for r in v1.jl(w2 / "candidates_all.jsonl")}
    bodies = {r["item_id"]: r for r in v1.jl(w2 / "bodies_v2" / "bodies.jsonl")}
    texts = w2 / "bodies_v2" / "texts"
    lines = []
    for n, cid in enumerate(spec["card_order"], 1):
        c, b = cand[cid], bodies[cid]
        g = spec["census_graded"][cid]
        acc = graded_accessions(w2, cid) if g else set()
        lines.append(f"=== R{n} {cid} {c['template']} graded={'Y' if g else 'N'}")
        lines.append(f"  HEAD: {c.get('title') or ''}  [tk={c['ticker']} issuer={c.get('issuer')}]")
        for j, f in enumerate(b["filings"], 1):
            docs = [d for d in f.get("documents") or () if d.get("status") == "available"]
            k8 = next((d for d in docs if str(d.get("doc_type")).upper() == "8-K"), None)
            ex = next((d for d in docs if str(d.get("doc_type")).upper().startswith("EX-99")), None)
            mark = ("in_graded_body" if f.get("accession") in acc else "v2_added") if g else "-"
            lines.append(f"  F{j} {f.get('form')} {f.get('filing_date')} off={f.get('session_offset')} "
                         f"{f.get('relation')} items={f.get('items')} {mark}")
            if k8:
                t = v1.clean((texts / f"{k8['text_sha256']}.txt").read_text(encoding="utf-8", errors="replace"))
                reg = re.search(r"(\S.{2,100}?)\s*\(Exact name of (?:the )?registrant", t, re.I)
                m = re.search(r"Item\s+\d\.\d{2}.*", t)
                lines.append(f"    REG: {reg.group(1)[-80:] if reg else '?'}")
                lines.append(f"    ITEM: {m.group(0)[:v1.ITEM_CHARS] if m else t[-300:]}")
            if ex:
                t = v1.clean((texts / f"{ex['text_sha256']}.txt").read_text(encoding="utf-8", errors="replace"))
                lines.append(f"    EX: {t[:v1.EX_CHARS]}")
    return lines


def score(spec, drawn, graded, prior, verdicts):
    pop = spec["card_order"]
    v = {x["case_id"]: x for x in verdicts["verdicts"]}
    missing = [c for c in pop if c not in v]
    if missing:
        raise SystemExit(f"verdicts missing for {missing}")
    extra = sorted(set(v) - set(pop))
    if extra:
        raise SystemExit(f"verdicts for cases outside the census: {extra}")
    bad = sorted({x["class"] for x in v.values()} - set(verdicts["classes"]))
    if bad:
        raise SystemExit(f"unknown classes {bad}")
    arm = v1._arm(sorted(pop), v)
    k = arm["class_counts"].get("MATCH", 0)
    rmap = {c: dict(prior[c]) for c in prior}
    for c in pop:
        rmap[c] = {"source": "v2_routing", "class": v[c]["class"], "kind": v[c]["kind"]}
    for c in rmap:
        rmap[c] |= {"template": drawn[c]["template"], "graded": c in graded}
    scorable = sorted(c for c in rmap if rmap[c]["class"] == "MATCH")
    queue = sorted(c for c in scorable if not rmap[c]["graded"])
    fam = {}
    for t in TEMPLATES:
        ids = [c for c in rmap if rmap[c]["template"] == t]
        s = [c for c in ids if rmap[c]["class"] == "MATCH"]
        fam[t] = {"drawn": len(ids), "scorable_match": len(s),
                  "scorable_graded": sum(rmap[c]["graded"] for c in s),
                  "label_queue": sum(not rmap[c]["graded"] for c in s),
                  "non_match": dict(sorted(collections.Counter(rmap[c]["class"] for c in ids if c not in s).items())),
                  "target": TARGET_PER_TEMPLATE, "shortfall_vs_target": TARGET_PER_TEMPLATE - len(s)}
    per_case = [{"case_id": c, "template": spec["census_template"][c], "graded": spec["census_graded"][c],
                 "class": v[c]["class"], "kind": v[c]["kind"], "note": v[c]["note"]} for c in sorted(pop)]
    return {"seed": spec["seed"], "body_version": spec["body_version"],
            "gates_freeze_commit": spec["gates_freeze_commit"], "auditor": verdicts["auditor"],
            "class_definitions": verdicts["classes"],
            "population": {key: spec[key] for key in ("n_drawn", "n_drawn_graded", "n_prior_verdicts",
                                                      "prior_by_source", "n_census")},
            "census": arm | {"match": k, "information_only": f"MATCH share beside {MATCH_SHARE}; gates-2 frozen, no revision"},
            "census_by_graded": {str(g): dict(sorted(collections.Counter(v[c]["class"] for c in pop
                                                                          if spec["census_graded"][c] == g).items()))
                                 for g in (True, False)},
            "routing_map": {c: rmap[c] for c in sorted(rmap)},
            "routing_map_class_counts": dict(sorted(collections.Counter(x["class"] for x in rmap.values()).items())),
            "scorable_match": scorable, "label_queue": queue, "families": fam,
            "scorable_total": len(scorable),
            "shortfall_total": TARGET_PER_TEMPLATE * len(TEMPLATES) - len(scorable),
            "cases": per_case}


def main():
    w2, bench, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    spec, drawn, graded, prior = census(w2, bench)
    (out / "v2_routing_spec.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    for old in out.glob("batch_v2_routing_*.txt"):
        old.unlink()
    (out / "batch_v2_routing_1.txt").write_text("\n".join(cards(w2, spec)) + "\n")
    print("drawn", spec["n_drawn"], "graded", spec["n_drawn_graded"], "prior verdicts", spec["n_prior_verdicts"],
          spec["prior_by_source"], "census", spec["n_census"],
          "census graded", sum(spec["census_graded"].values()))
    if len(sys.argv) > 4:
        res = score(spec, drawn, graded, prior, json.loads(Path(sys.argv[4]).read_text()))
        (out / "v2_routing.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        print("census", res["census"]["class_counts"], res["census"]["class_rate_wilson95"].get("MATCH"))
        print("census by graded", res["census_by_graded"])
        print("routing map", res["routing_map_class_counts"], "scorable", res["scorable_total"],
              "label queue", len(res["label_queue"]), "shortfall", res["shortfall_total"])
        for t, row in res["families"].items():
            print(" ", t, row)


if __name__ == "__main__":
    main()
