"""Seat tool: score the two-family labels on the gated_v2 label queue and join them to the graded MATCH cases.

usage (from the repository tree root):
  PYTHONPATH=.:<results_w2>/tools python3.12 score_v2_queue.py --w2q SCRATCH_W2Q --results RESULTS_W2 \
      --bench BENCH_DIR --out OUT_DIR

Inputs (all already on disk, nothing fetched):
  RESULTS_W2/audit/v2_routing.json        label_queue (12 ids) and scorable_match (74 ids), seed 20261020
  RESULTS_W2/critical_slots.jsonl         the committed 157-case slots; the 62 graded MATCH cases are read from it
  BENCH_DIR/gated_v2/cases.jsonl          case meta for the continuation draw
  SCRATCH_W2Q/bundles/<case>/{bundle.json,source.txt}       ni-edgar-body-2 bodies, internal_only
  SCRATCH_W2Q/labels_canon/<case>.fam_{a,b}.json            canonicalised label_return.v1 (canon_returns.py)
  SCRATCH_W2Q/agreement/agreement_summary.json              agreement module over the same returns

What it prints, and why it is a separate tool: score_benchmark.py is pinned to the 157-case
draw and stays unchanged. This tool reuses its grading functions by import so a queue slot is
graded exactly as a graded slot was: the frozen grade_critical_numeric_field in both directions,
the same symmetric class, the same span replay. It adds nothing new to the method.

  * span replay per family over every present field of the 12 queue cases;
  * the critical-slot taxonomy of the 12 queue cases;
  * all-field agreement status of the 12 queue cases;
  * the scorable view: the 74 MATCH cases (62 graded slots read from the committed file plus
    the 12 queue cases), by template and by prompt version, with the shortfall against 200 per
    template. Only MATCH cases score (DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH item 3).

Output is value-free: per slot it keeps the class, the two directional outcomes and the
mismatch components, never the reference or candidate value.
"""
import argparse
import collections
import json
from pathlib import Path

from engine.news_impact.agreement import parse_label_return, replay_return_spans
from engine.news_impact.eval_grade import CRITICAL_NUMERIC_FIELDS

from score_benchmark import FAMILIES, TEMPLATE_CODE, Bundle, grade_slot, jl, mismatch_components, slot_class, wilson

TARGET_PER_TEMPLATE = 200


def taxonomy_rows(slots, keys):
    tax = collections.defaultdict(collections.Counter)
    comp = collections.defaultdict(collections.Counter)
    for s in slots:
        for k in keys(s):
            tax[k][s["class"]] += 1
            for c in s["components"]:
                comp[k][c] += 1
    rows = []
    for k, cnt in sorted(tax.items()):
        n = sum(cnt.values())
        agreed = cnt["agree_present"] + cnt["agree_absent"]
        disputed = n - agreed
        rows.append({"key": list(k), "n_slots": n, "classes": dict(cnt),
                     "agreement_rate": agreed / n, "agreement_wilson95": wilson(agreed, n),
                     "disputed_rate": disputed / n, "worse_family_error_lower_bound": disputed / n / 2,
                     "mismatch_components": dict(comp.get(k, {}))})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--w2q", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    w2q, results, bench, out = Path(a.w2q), Path(a.results), Path(a.bench), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    routing = json.loads((results / "audit" / "v2_routing.json").read_text())
    queue = sorted(routing["label_queue"])
    scorable = set(routing["scorable_match"])
    assert len(queue) == 12 and set(queue) <= scorable, (len(queue), len(scorable))
    graded_ids = scorable - set(queue)

    code_to_full = {v: k for k, v in TEMPLATE_CODE.items()}
    meta = {c["item_id"]: c for c in jl(bench / "gated_v2" / "cases.jsonl")}
    assert scorable <= set(meta), "scorable ids missing from gated_v2"
    for c in meta.values():
        c["template_full"] = code_to_full[c["template"]]

    bundles = {cid: Bundle(w2q / "bundles" / cid) for cid in queue}
    returns = {}
    for cid in queue:
        for fam in FAMILIES:
            returns[(cid, fam)] = json.loads((w2q / "labels_canon" / f"{cid}.{fam}.json").read_text())

    # ---------------- span replay per family
    span_summary = {}
    for fam in FAMILIES:
        rs = []
        for cid in queue:
            b = bundles[cid]
            rs.append(replay_return_spans(parse_label_return(returns[(cid, fam)]), b.src, b.meta["source_sha256"],
                                          segments=b.meta["segments"]))
        checked = sum(r["n_spans_checked"] for r in rs)
        ok = sum(r["n_replayed"] for r in rs)
        span_summary[fam] = {"spans_checked": checked, "spans_replayed": ok,
                             "span_pass_rate": ok / checked if checked else None,
                             "span_pass_wilson95": wilson(ok, checked),
                             "cases_all_spans_pass": sum(1 for r in rs if r["n_failed"] == 0), "cases": len(rs),
                             "injection_flagged_cases": sum(1 for r in rs if r["injection_flagged"])}

    # ---------------- critical numeric slots on the queue, both directions, value-free output
    queue_slots = []
    for cid in queue:
        c = meta[cid]
        for field in CRITICAL_NUMERIC_FIELDS[c["template_full"]]:
            ea = returns[(cid, "fam_a")]["fields"].get(field)
            eb = returns[(cid, "fam_b")]["fields"].get(field)
            ab = grade_slot(c, "fam_a", "fam_b", field, ea, eb, bundles[cid])
            ba = grade_slot(c, "fam_b", "fam_a", field, eb, ea, bundles[cid])
            queue_slots.append({"case_id": cid, "template": c["template"], "fold": c["fold"],
                                "proxy_cell": c["proxy_cell"], "group_id": c["group_id"], "field": field,
                                "class": slot_class(ab, ba, ea, eb),
                                "fam_b_vs_fam_a": ab["outcome"], "fam_a_vs_fam_b": ba["outcome"],
                                "components": sorted(set(mismatch_components(ab)) | set(mismatch_components(ba))),
                                "prompt_version": returns[(cid, "fam_a")]["prompt_version"],
                                "source": "v2_queue"})
    (out / "critical_slots.jsonl").write_text("".join(json.dumps(s, sort_keys=True) + "\n" for s in queue_slots))

    # ---------------- the 62 graded MATCH cases, read from the committed 157-case slots
    graded_slots = []
    for s in jl(results / "critical_slots.jsonl"):
        if s["case_id"] in graded_ids:
            graded_slots.append({"case_id": s["case_id"], "template": s["template"], "field": s["field"],
                                 "class": s["class"], "components": s["components"],
                                 "prompt_version": s["prompt_version"], "source": "graded_v1_body"})
    missing = graded_ids - {s["case_id"] for s in graded_slots}
    assert not missing, f"graded MATCH cases absent from critical_slots.jsonl: {sorted(missing)}"
    assert not ({s["case_id"] for s in jl(results / "critical_slots.jsonl")} & set(queue)), "queue case already graded"

    # ---------------- all-field agreement on the queue
    agree = json.loads((w2q / "agreement" / "agreement_summary.json").read_text())
    assert set(agree["cases"]) == set(queue), "agreement run covers a different case set"
    field_status = collections.defaultdict(collections.Counter)
    for ac in agree["cases"].values():
        for fr in ac["fields"]:
            field_status[ac["template"]][fr["status"]] += 1
    agreement_rows = []
    for t, cnt in sorted(field_status.items()):
        n = sum(cnt.values())
        agreement_rows.append({"template": t, "n_fields": n, "statuses": dict(cnt),
                               "agreed_rate": cnt["agreed"] / n,
                               "agreed_or_span_only_rate": (cnt["agreed"] + cnt["span_only_divergence"]) / n})
    case_status = collections.Counter(ac["status"] for ac in agree["cases"].values())

    # ---------------- scorable view: 74 MATCH cases
    all_slots = graded_slots + queue_slots
    cases_by_template = collections.Counter()
    for cid in scorable:
        cases_by_template[meta[cid]["template"]] += 1
    shortfall = {t: {"scorable_cases": cases_by_template.get(t, 0), "target": TARGET_PER_TEMPLATE,
                     "shortfall": TARGET_PER_TEMPLATE - cases_by_template.get(t, 0)}
                 for t in sorted(set(TEMPLATE_CODE.values()))}

    summary = {
        "tool": "score_v2_queue.py",
        "routing_seed": routing["seed"],
        "families": FAMILIES,
        "queue": {"n_cases": len(queue), "prompt_versions": dict(collections.Counter(
                      returns[(cid, fam)]["prompt_version"] for cid in queue for fam in FAMILIES)),
                  "span_replay": span_summary,
                  "case_status": dict(case_status),
                  "field_agreement": agreement_rows,
                  "critical_taxonomy": taxonomy_rows(queue_slots, lambda s: [("ALL",), (s["template"],),
                                                                             (s["template"], s["field"])])},
        "scorable": {"n_cases": len(scorable), "n_graded_cases": len(graded_ids), "n_queue_cases": len(queue),
                     "n_slots": len(all_slots),
                     "critical_taxonomy_by_template": taxonomy_rows(all_slots, lambda s: [("ALL",), (s["template"],)]),
                     "critical_taxonomy_by_prompt_version": taxonomy_rows(
                         all_slots, lambda s: [(s["prompt_version"],), (s["prompt_version"], s["template"])]),
                     "critical_taxonomy_by_source": taxonomy_rows(all_slots, lambda s: [(s["source"],)]),
                     "shortfall": shortfall,
                     "shortfall_total": sum(v["shortfall"] for v in shortfall.values())},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"queue_cases": len(queue), "queue_slots": len(queue_slots), "scorable_cases": len(scorable),
                      "scorable_slots": len(all_slots), "case_status": dict(case_status),
                      "shortfall_total": summary["scorable"]["shortfall_total"]}, sort_keys=True))


if __name__ == "__main__":
    main()
