"""Seat tool: score the W2 two-family news-impact benchmark (commission D).

usage (from the repository tree root):
  PYTHONPATH=. python3 score_benchmark.py --w2 SCRATCH_W2 --bench BENCH_DIR --out OUT_DIR [--audit AUDIT_JSON]

Inputs (all already on disk, nothing fetched):
  BENCH_DIR/graded/cases.jsonl, BENCH_DIR/routing/cases.jsonl, BENCH_DIR/graded/manifest.json
  SCRATCH_W2/bundles_graded/<case>/{bundle.json,source.txt}
  SCRATCH_W2/labels_canon_full/<case>.fam_{a,b}.json   (canonicalised label_return.v1)
  SCRATCH_W2/agreement_full/agreement_summary.json
  SCRATCH_W2/usage/*.usage.json                           (qwen lanes only; MiniMax wrote none)
  SCRATCH_W2/lanes*/lanes.json                            (batch -> case ids)
  SCRATCH_W2/returns/launch_ledger.txt                    (admission evidence)
  AUDIT_JSON (optional): seat audit verdicts, see build_audit.py and ../audit/audit.json

What it can and cannot say. Only two label families ran (fam_a MiniMax-M3, fam_b qwen3.7-plus).
Gold under the registered rule needs agreement or third-family resolution, so for every agreed
field the gold IS the families' shared value and grading either family against it is correct by
construction. This script therefore does not print a per-family accuracy from agreed gold. It prints:
  * the cross-family disagreement taxonomy on the critical numeric slots, graded with the frozen
    grade_critical_numeric_field in both directions (each family as the other's reference);
  * span replay per family over every present field (independent of the other family);
  * a lower bound: on each disputed slot at least one family is wrong, so the worse family's
    slot error rate is at least half the disputed rate;
  * actual token cost per case where a usage receipt exists;
  * burst / defer behaviour from seendates and the admission ledger;
  * calibration of the routing signal (case agreement) by proxy cell and, when an audit file is
    given, P(audited wrong | agreed) against P(audited wrong | disputed);
  * eval_receipt.v1 receipts per family, built only from non-circular items.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from engine.news_impact import eval_receipt as er
from engine.news_impact.agreement import parse_label_return, replay_return_spans
from engine.news_impact.eval_grade import CRITICAL_NUMERIC_FIELDS, EvalGradeError, grade_critical_numeric_field

FAMILIES = {"fam_a": "MiniMax-M3", "fam_b": "qwen3.7-plus"}
TEMPLATE_CODE = {"capital_allocation_event.v1": "T1", "demand_guidance_contract_event.v1": "T2",
                 "strategic_product_partnership_event.v1": "T3"}
BASELINE = "cheap_extractor_no_frontier"
ABLATION = "full"
T_PROSPECTIVE = "2026-10-14T00:00:00Z"
TAPE_SHA = "bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17"


def jl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Bundle:
    def __init__(self, d):
        self.meta = json.loads((d / "bundle.json").read_text())
        self.src = (d / "source.txt").read_bytes()
        assert sha(self.src) == self.meta["source_sha256"], d
        self.segments = {s["segment_index"]: s for s in self.meta["segments"]}

    def verify(self, span):
        """Same checks as agreement.replay_return_spans, for one span (text_sha256 is the SOURCE sha). Returns (ok, reason)."""
        if not isinstance(span, dict):
            return False, "span_missing"
        try:
            bs, be = int(span["byte_start"]), int(span["byte_end"])
            ex, seg_i, tsha = span["excerpt"], int(span["segment_index"]), span["text_sha256"]
        except (KeyError, TypeError, ValueError):
            return False, "span_malformed"
        if tsha != self.meta["source_sha256"]:
            return False, "text_sha_mismatch"
        if not (0 <= bs < be <= len(self.src)):
            return False, "byte_range_invalid"
        try:
            text = self.src[bs:be].decode("utf-8")
        except UnicodeDecodeError:
            return False, "slice_not_utf8"
        if text != ex:
            return False, "excerpt_mismatch"
        seg = self.segments.get(seg_i)
        if seg is None or not (seg["byte_start"] <= bs and be <= seg["byte_end"]):
            return False, "outside_segment"
        return True, ""


def to_quantity(entry):
    """label field entry -> eval_grade quantity. Evidence carries the span only, never a
    claimed_quote: the annotation guide folds scale words into the value, and eval_grade would
    multiply again by a scale word found in a quote (DEC recorded with this benchmark)."""
    if entry is None:
        return None
    v, ta = entry.get("value"), entry.get("typed_absence")
    # Q1 (structural only): an absent value written as {"form": "absent"} beside the entry's
    # typed_absence is the same claim as value null + typed_absence; the absence content is the
    # family's own. A period written as null is NOT rewritten: it is a contract-shape error and
    # stays malformed (counted per family), since mapping it would invent an absence reason.
    if isinstance(ta, dict) and (v is None or v == {"form": "absent"}):
        return {"form": "absent", "absence": ta}
    if isinstance(v, dict) and v.get("form") in ("point", "range"):
        q = dict(v)
        q["evidence"] = {"span": entry["source_span"]} if entry.get("source_span") else None
        return q
    return v


def grade_slot(case, fam_ref, fam_cand, field, ref_entry, cand_entry, bundle):
    reasons = []

    def verifier(evidence):
        ok, why = bundle.verify(evidence.get("span"))
        if not ok:
            reasons.append(why)
        return ok

    ref_q = to_quantity(ref_entry)
    if isinstance(ref_q, dict) and ref_q.get("form") in ("point", "range"):
        ok, why = bundle.verify((ref_q.get("evidence") or {}).get("span"))
        if not ok:
            return {"outcome": "reference_unevidenced", "notes": [why]}
    try:
        g = grade_critical_numeric_field(case_id=case["item_id"], fold=case["fold"], template=case["template_full"],
                                         field=field, gold_quantity=ref_q,
                                         candidate_quantity=to_quantity(cand_entry), span_verifier=verifier)
    except EvalGradeError as exc:
        return {"outcome": "reference_unusable", "notes": [exc.code]}
    return {"outcome": g.outcome, "notes": list(g.notes) + reasons, "ref": g.gold_value, "cand": g.candidate_value}


def slot_class(ab, ba, a_entry, b_entry):
    """Symmetric taxonomy class of one critical slot from the two directional grades."""
    def present(e):
        # Same reading as to_quantity (rule Q1): an absent value written as {"form": "absent"}
        # beside a typed_absence is absent, not present.
        q = to_quantity(e) if isinstance(e, dict) else None
        return q is not None and not (isinstance(q, dict) and q.get("form") == "absent")

    pa, pb = present(a_entry), present(b_entry)
    if "reference_unusable" in (ab["outcome"], ba["outcome"]):
        return "malformed_value"
    if "unevidenced" in (ab["outcome"], ba["outcome"]) or "reference_unevidenced" in (ab["outcome"], ba["outcome"]):
        return "unevidenced_span"
    if ab["outcome"] == "correct" and ba["outcome"] == "correct":
        return "agree_present" if pa else "agree_absent"
    if pa != pb:
        return "present_vs_absent"
    if not pa:
        return "absent_reason_differs"
    return "present_value_differs"


def mismatch_components(grade):
    out = []
    for n in grade.get("notes", []):
        if isinstance(n, str) and n.startswith("mismatch:"):
            out.extend(n[len("mismatch:"):].split("|"))
    return out


def lanes_map(w2):
    m = {}
    for f in sorted(w2.glob("lanes*/lanes.json")):
        for row in json.loads(f.read_text()):
            prev = m.get(row["lane"])
            if prev is not None and sorted(prev) != sorted(row["cases"]):
                m[row["lane"] + "@" + f.parent.name] = row["cases"]
            else:
                m[row["lane"]] = row["cases"]
    return m


def costs(w2, lane_cases):
    lanes, excluded = {}, {}
    for f in sorted((w2 / "usage").glob("*.usage.json")):
        u = json.loads(f.read_text())
        rid = u.get("run_id") or f.name.split(".usage")[0]
        lane = re.match(r"(W2_L_fam_[a-z]_\d+r?)", rid).group(1)
        cases = lane_cases.get(lane)
        if u.get("status") != "observed":
            excluded[rid] = {"lane": lane, "status": u.get("status"), "reason": u.get("reason")}
            continue
        lanes[rid] = {"lane": lane, "status": u.get("status"), "source": u.get("source"),
                      "input_tokens": u.get("input_tokens"), "cached_tokens": u.get("cached_tokens"),
                      "output_tokens": u.get("output_tokens"), "total_tokens": u.get("total_tokens"),
                      "n_cases": len(cases) if cases else None}
    per_case = []
    for r in lanes.values():
        if r["n_cases"]:
            per_case.append({k: r[k] / r["n_cases"] for k in ("input_tokens", "cached_tokens", "output_tokens", "total_tokens")})
    agg = {}
    if per_case:
        for k in per_case[0]:
            vals = sorted(p[k] for p in per_case)
            agg[k] = {"median_per_case": vals[len(vals) // 2], "min_per_case": vals[0], "max_per_case": vals[-1]}
        tot = {k: sum(r[k] for r in lanes.values()) for k in ("input_tokens", "cached_tokens", "output_tokens", "total_tokens")}
        n = sum(r["n_cases"] for r in lanes.values() if r["n_cases"])
        agg["pooled_per_case"] = {k: tot[k] / n for k in tot}
        agg["pooled_totals"] = tot
        agg["n_cases_covered"] = n
        agg["uncached_input_per_case"] = (tot["input_tokens"] - tot["cached_tokens"]) / n
    return {"fam_b": {"model": FAMILIES["fam_b"], "receipts": lanes, "excluded_receipts": excluded, "summary": agg,
                      "note": "codex_native_session cumulative counts; one native session per lane run, "
                              "includes the lane's tool-loop context, not just the prompt and answer"},
            "fam_a": {"model": FAMILIES["fam_a"], "receipts": {}, "summary": None,
                      "null_reason": "USAGE_RECEIPT_MISSING: the minimax lane mode wrote no usage file"}}


def ledger(w2):
    rows = collections.Counter()
    reasons = collections.Counter()
    per_lane_refusals = collections.Counter()
    for line in (w2 / "returns" / "launch_ledger.txt").read_text().splitlines():
        m = re.search(r"\[admit_drain (\S+)\] (OFFER|REFUSED|ADMITTED|EXITED_EARLY) (\S+)", line)
        if m:
            host, verb, lane = m.groups()
            fam = re.match(r"W2_L_(fam_[a-z])", lane)
            rows[(host, fam.group(1) if fam else "?", verb)] += 1
            if verb == "REFUSED":
                per_lane_refusals[lane] += 1
                r = re.search(r'"reasons":\[([^\]]*)\]', line)
                for x in (r.group(1).split(",") if r else ["unrecorded"]):
                    reasons[x.strip('"')] += 1
        for tag in ("FINDING", "CORRECTION", "SIGSTOP"):
            if f" {tag}" in line:
                rows[("-", "-", tag)] += 1
    return {"counts": [{"host": h, "family": f, "event": v, "n": n} for (h, f, v), n in sorted(rows.items())],
            "refusal_reasons": dict(reasons), "max_refusals_one_lane": max(per_lane_refusals.values(), default=0),
            "lanes_refused_at_least_once": len(per_lane_refusals)}


def wilson(k, n):
    if not n:
        return None
    w = er.wilson_interval(k, n)
    return [round(w["low"], 4), round(w["high"], 4)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--w2", required=True)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit")
    a = ap.parse_args(argv)
    w2, bench, out = Path(a.w2), Path(a.bench), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cases = jl(bench / "graded" / "cases.jsonl")
    routing = jl(bench / "routing" / "cases.jsonl")
    agree = json.loads((w2 / "agreement_full" / "agreement_summary.json").read_text())
    code_to_full = {v: k for k, v in TEMPLATE_CODE.items()}
    by_id = {}
    for c in cases:
        c["template_full"] = code_to_full[c["template"]]
        by_id[c["item_id"]] = c
    assert len(by_id) == len(cases) == 157, len(by_id)

    bundles = {cid: Bundle(w2 / "bundles_graded" / cid) for cid in by_id}
    returns = {}
    for cid in by_id:
        for fam in FAMILIES:
            returns[(cid, fam)] = json.loads((w2 / "labels_canon_full" / f"{cid}.{fam}.json").read_text())

    # ---------------- span replay per family (canonical replay over every present field)
    replay = {}
    replay_fail_reasons = collections.Counter()
    for (cid, fam), rec in returns.items():
        b = bundles[cid]
        parsed = parse_label_return(rec)
        r = replay_return_spans(parsed, b.src, b.meta["source_sha256"], segments=b.meta["segments"])
        replay[(cid, fam)] = r
        for f in r["failures"]:
            replay_fail_reasons[(fam, str(f.get("reason", f)) if isinstance(f, dict) else str(f))] += 1
    span_summary = {}
    for fam in FAMILIES:
        rs = [replay[(cid, fam)] for cid in by_id]
        checked = sum(r["n_spans_checked"] for r in rs)
        ok = sum(r["n_replayed"] for r in rs)
        cases_pass = sum(1 for r in rs if r["n_failed"] == 0)
        span_summary[fam] = {"spans_checked": checked, "spans_replayed": ok, "span_pass_rate": ok / checked if checked else None,
                             "span_pass_wilson95": wilson(ok, checked), "cases_all_spans_pass": cases_pass, "cases": len(rs),
                             "injection_flagged_cases": sum(1 for r in rs if r["injection_flagged"])}

    # ---------------- critical numeric slots, both directions
    slots = []
    for cid, c in sorted(by_id.items()):
        t = c["template_full"]
        for field in CRITICAL_NUMERIC_FIELDS[t]:
            ea = returns[(cid, "fam_a")]["fields"].get(field)
            eb = returns[(cid, "fam_b")]["fields"].get(field)
            ab = grade_slot(c, "fam_a", "fam_b", field, ea, eb, bundles[cid])  # fam_b graded, fam_a reference
            ba = grade_slot(c, "fam_b", "fam_a", field, eb, ea, bundles[cid])  # fam_a graded, fam_b reference
            cls = slot_class(ab, ba, ea, eb)
            slots.append({"case_id": cid, "template": c["template"], "fold": c["fold"], "proxy_cell": c["proxy_cell"],
                          "group_id": c["group_id"], "issuer": c["issuer"], "field": field, "class": cls,
                          "fam_b_vs_fam_a": ab, "fam_a_vs_fam_b": ba,
                          "components": sorted(set(mismatch_components(ab)) | set(mismatch_components(ba))),
                          "prompt_version": returns[(cid, "fam_a")]["prompt_version"]})
    (out / "critical_slots.jsonl").write_text("".join(json.dumps(s, sort_keys=True) + "\n" for s in slots))

    tax = collections.defaultdict(collections.Counter)
    comp = collections.defaultdict(collections.Counter)
    for s in slots:
        tax[(s["template"], s["field"])][s["class"]] += 1
        tax[("ALL", "ALL")][s["class"]] += 1
        tax[(s["template"], "ALL")][s["class"]] += 1
        for k in s["components"]:
            comp[(s["template"], s["field"])][k] += 1
            comp[("ALL", "ALL")][k] += 1
    taxonomy = []
    for (t, f), cnt in sorted(tax.items()):
        n = sum(cnt.values())
        agreed = cnt["agree_present"] + cnt["agree_absent"]
        disputed = n - agreed
        taxonomy.append({"template": t, "field": f, "n_slots": n, "classes": dict(cnt),
                         "agreement_rate": agreed / n, "agreement_wilson95": wilson(agreed, n),
                         "disputed_rate": disputed / n,
                         "worse_family_error_lower_bound": disputed / n / 2,
                         "mismatch_components": dict(comp.get((t, f), {}))})

    # directional outcome counts (per family as candidate)
    directional = collections.defaultdict(collections.Counter)
    for s in slots:
        directional[("fam_b", s["template"])][s["fam_b_vs_fam_a"]["outcome"]] += 1
        directional[("fam_a", s["template"])][s["fam_a_vs_fam_b"]["outcome"]] += 1

    # ---------------- all-field agreement (agreement module), by template and prompt version
    field_status = collections.defaultdict(collections.Counter)
    pv_status = collections.defaultdict(collections.Counter)
    abst = collections.Counter()
    for cid, ac in agree["cases"].items():
        pv = returns[(cid, "fam_a")]["prompt_version"] + "/" + returns[(cid, "fam_b")]["prompt_version"]
        for fr in ac["fields"]:
            field_status[(ac["template"], fr["field"])][fr["status"]] += 1
            pv_status[(pv, ac["template"])][fr["status"]] += 1
        abst["fam_a"] += len(ac["abstentions"]["first"])
        abst["fam_b"] += len(ac["abstentions"]["second"])
    case_status = collections.Counter(ac["status"] for ac in agree["cases"].values())

    def status_rows(d):
        rows = []
        for (k1, k2), cnt in sorted(d.items()):
            n = sum(cnt.values())
            rows.append({"k1": k1, "k2": k2, "n": n, "statuses": dict(cnt),
                         "agreed_rate": cnt["agreed"] / n,
                         "agreed_or_span_only_rate": (cnt["agreed"] + cnt["span_only_divergence"]) / n})
        return rows

    # ---------------- calibration: routing signal by proxy cell (no LLM confidence anywhere)
    calib = collections.defaultdict(collections.Counter)
    for s in slots:
        calib[(s["template"], s["proxy_cell"])]["agreed" if s["class"].startswith("agree") else "disputed"] += 1
        calib[(s["template"], s["proxy_cell"])]["present_any" if s["class"] in ("agree_present", "present_value_differs", "present_vs_absent", "unevidenced_span") else "absent_both"] += 1
    calibration = [{"template": t, "proxy_cell": p, **dict(cnt)} for (t, p), cnt in sorted(calib.items())]

    # ---------------- audit (optional): breaks circularity on a sample
    audit_out = None
    if a.audit:
        audit = json.loads(Path(a.audit).read_text())
        by_slot = {(s["case_id"], s["field"]): s for s in slots}
        cells = collections.defaultdict(collections.Counter)
        fam_err = collections.defaultdict(collections.Counter)
        for v in audit["verdicts"]:
            s = by_slot[(v["case_id"], v["field"])]
            stratum = "agreed" if s["class"].startswith("agree") else "disputed"
            cells[stratum]["n"] += 1
            if all(v[f"{fam}_correct"] is None for fam in FAMILIES):
                cells[stratum]["ambiguous_both"] += 1
                if v.get("severity") == "contract_gap":
                    cells[stratum]["contract_gap"] += 1
            for fam in FAMILIES:
                ok = v[f"{fam}_correct"]
                # null = no usable gold reading (guide or contract gap): ambiguous, never wrong
                fam_err[(fam, stratum)]["ambiguous" if ok is None else ("correct" if ok else "wrong")] += 1
            if stratum == "agreed" and v["fam_a_correct"] is False:
                cells[stratum]["shared_value_wrong"] += 1
        audit_out = {"auditor": audit["auditor"], "sample": audit["sample"], "strata": {k: dict(v) for k, v in cells.items()},
                     "per_family": [{"family": f, "stratum": st, **dict(c),
                                     "error_rate": c["wrong"] / (c["wrong"] + c["correct"]) if (c["wrong"] + c["correct"]) else None,
                                     "wilson95": wilson(c["wrong"], c["wrong"] + c["correct"])}
                                    for (f, st), c in sorted(fam_err.items())]}

    # ---------------- burst / defer
    by_day = collections.Counter(c["seendate"][:10] for c in cases)
    by_day_routing = collections.Counter(c["seendate"][:10] for c in routing)
    burst = {"graded_per_day": dict(sorted(by_day.items())), "routing_per_day": dict(sorted(by_day_routing.items())),
             "graded_max_day": max(by_day.values()), "graded_days": len(by_day),
             "routing_max_day": max(by_day_routing.values()), "routing_days": len(by_day_routing),
             "admission": ledger(w2),
             "defer": {"case_status": dict(case_status),
                       "deferred_cases": case_status.get("routed_pending_third", 0) + case_status.get("adjudication_needed", 0),
                       "auto_published_cases": case_status.get("accepted_first_pass", 0),
                       "why": "with two families the case gate accepts only when every field agrees; any disputed "
                              "field routes the whole case to a third family, which is not available until GLM resets"}}

    cost = costs(w2, lanes_map(w2))

    # ---------------- recall-versus-cost points (field-level, critical slots)
    n_slots = len(slots)
    agreed_slots = sum(1 for s in slots if s["class"].startswith("agree"))
    curve = []
    fb = cost["fam_b"]["summary"] or {}
    pc = (fb.get("pooled_per_case") or {})
    curve.append({"construction": "fam_b alone (qwen3.7-plus)", "tokens_per_case": pc.get("total_tokens"),
                  "uncached_input_per_case": fb.get("uncached_input_per_case"), "output_per_case": pc.get("output_tokens"),
                  "accepted_slot_rate": None, "note": "no acceptance without a second family under the registered rule"})
    curve.append({"construction": "fam_a alone (MiniMax-M3)", "tokens_per_case": None, "accepted_slot_rate": None,
                  "note": "USAGE_RECEIPT_MISSING"})
    curve.append({"construction": "fam_a + fam_b, agreement gate", "tokens_per_case": None,
                  "tokens_per_case_lower_bound": pc.get("total_tokens"),
                  "accepted_slot_rate": agreed_slots / n_slots, "accepted_case_rate": case_status.get("accepted_first_pass", 0) / 157,
                  "note": "slot-level acceptance if publication were per slot; the case gate as built accepts 0/157"})
    curve.append({"construction": "fam_a + fam_b + third family on disputed slots", "tokens_per_case": None,
                  "accepted_slot_rate": None, "note": "third family unavailable (GLM exhausted until 2026-10-19 05:16Z)"})

    # ---------------- eval_receipt.v1 per family from non-circular items only
    manifest_sha = sha((bench / "graded" / "manifest.json").read_bytes())
    registration = er.make_registration(tape_sha256=TAPE_SHA, sampler_version="ni-sampler-1", sampling_seed=20261014,
                                        t_prospective=T_PROSPECTIVE, mode="evaluate")
    cluster_map = {cid: c["group_id"] for cid, c in by_id.items()}
    issuer_map = {cid: c["issuer"] for cid, c in by_id.items()}
    ids = sorted(by_id)
    accounting = er.AccountingInput(
        manifest_n=157, discovered=157, unique_groups=len(set(cluster_map.values())), extracted_packets=157,
        issuer_impacts=0, deferred=burst["defer"]["deferred_cases"], rejected=0, quarantined=0,
        auto_published=burst["defer"]["auto_published_cases"], reviewed_published=0, abstained=0, evaluated=157,
        unresolved_identity=0, body_unavailable=0, short_cells=443, rights_blocked=0,
        manifest_case_ids=tuple(ids), output_case_ids=tuple(ids))
    receipts = {}
    for fam in FAMILIES:
        items = []
        for cid in ids:
            c = by_id[cid]
            r = replay[(cid, fam)]
            items.append(er.GradedItem(cid, c["fold"], c["template_full"], "span_replay",
                                       "pass" if r["n_failed"] == 0 else "fail"))
        if audit_out:
            for v in json.loads(Path(a.audit).read_text())["verdicts"]:
                c = by_id[v["case_id"]]
                ok = v[f"{fam}_correct"]
                # reference_unusable sits outside every critical-numeric denominator
                outcome = v.get(f"{fam}_outcome") or ("reference_unusable" if ok is None else ("correct" if ok else "wrong_value"))
                items.append(er.GradedItem(v["case_id"], c["fold"], c["template_full"], v["field"], outcome,
                                           notes=er.POP_ALL_DISPOSITIONS))
        try:
            rec = er.build_receipt(graded_by_construction={(BASELINE, ABLATION): items}, cluster_map=cluster_map,
                                   issuer_map=issuer_map, accounting=accounting, registration=registration,
                                   baselines_run=[BASELINE], ablations_run=[ABLATION],
                                   notes=f"family={fam} model={FAMILIES[fam]}; graded population 157 of 600; "
                                         "critical-numeric items only from the seat audit sample; "
                                         "material routing not labelled in this wave")
            receipts[fam] = rec
            (out / f"eval_receipt_{fam}.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        except er.EvalReceiptError as exc:
            receipts[fam] = {"error": str(exc)}

    summary = {
        "schema": "news_impact_w2_benchmark_summary.v0",
        "authority": "context_only",
        "population": {"graded": 157, "target": 600, "shortfall": 443, "routing_draw": len(routing),
                       "by_template": dict(collections.Counter(c["template"] for c in cases))},
        "families": FAMILIES,
        "registration": registration,
        "graded_manifest_sha256": manifest_sha,
        "span_replay": span_summary,
        "span_replay_failure_reasons": {f"{k[0]}:{k[1]}": v for k, v in replay_fail_reasons.items()},
        "critical_slot_taxonomy": taxonomy,
        "directional_outcomes": [{"candidate": f, "template": t, **dict(c)} for (f, t), c in sorted(directional.items())],
        "all_field_agreement_by_template_field": status_rows(field_status),
        "all_field_agreement_by_prompt_version": status_rows(pv_status),
        "abstentions": dict(abst),
        "case_status": dict(case_status),
        "calibration_by_proxy_cell": calibration,
        "audit": audit_out,
        "burst_defer": burst,
        "cost": cost,
        "recall_vs_cost": curve,
        "receipts": {f: ("error" if "error" in r else "written") for f, r in receipts.items()},
        "receipt_errors": {f: r["error"] for f, r in receipts.items() if "error" in r},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"slots": n_slots, "agreed_slots": agreed_slots, "span": span_summary,
                      "case_status": dict(case_status), "receipts": summary["receipts"],
                      "receipt_errors": summary["receipt_errors"]}, indent=1))


if __name__ == "__main__":
    main()
