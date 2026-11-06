"""Seat tool: audit the malformed_value slots of the w2 benchmark (every slot, no sampling).
usage (from the repository tree root):
  PYTHONPATH=. python3 build_audit_malformed.py SCRATCH_W2 BENCH_DIR --census       (period shape census)
  PYTHONPATH=. python3 build_audit_malformed.py SCRATCH_W2 BENCH_DIR OUT_DIR        (re-grade + cards)
A slot is malformed_value when one direction of the frozen grader raises on a reference it
cannot use. --census counts how each family wrote the period of every present quantity, by
prompt version, so the malformed slots can be traced to one return shape.
OUT_DIR mode writes:
  regrade_malformed.json  for each malformed slot, the counterfactual class when a period
                          written as null is read as a field_absence.v1 not_stated period.
                          Diagnostic only: score_benchmark.py deliberately leaves the null
                          malformed (rule Q1), and summary.json is not re-scored.
  batch_malformed_*.txt   one card per slot with both quantities and both evidence spans.
The cards quote filing text: they are scratch-only and are never committed. The JSON output
carries ids, classes and shape names only, never a value or a span.
"""
import collections
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_benchmark as sb  # noqa: E402

NULL_PERIOD = {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
               "subject": "quantity.period", "detail": "counterfactual: period written as null",
               "missing_fields": ["period"]}


def load(w2, cid, fam):
    return json.loads((w2 / "labels_canon_full" / f"{cid}.{fam}.json").read_text())


def period_shape(p):
    if p is None:
        return "null"
    if isinstance(p, dict) and p.get("schema") == "field_absence.v1":
        return "typed_absence"
    if isinstance(p, dict) and "period_kind" in p:
        return "fiscal_period"
    if isinstance(p, dict):
        return "other_object"
    return type(p).__name__


def census(w2):
    cnt = collections.Counter()
    for fn in sorted((w2 / "labels_canon_full").glob("*.json")):
        rec = json.loads(fn.read_text())
        fam = fn.name.split(".")[1]
        for entry in (rec.get("fields") or {}).values():
            v = entry.get("value") if isinstance(entry, dict) else None
            if isinstance(v, dict) and v.get("form") in ("point", "range") and "period" in v:
                cnt[(fam, rec.get("prompt_version"), period_shape(v["period"]))] += 1
    rows = [{"family": f, "prompt_version": pv, "period_shape": s, "n": n} for (f, pv, s), n in sorted(cnt.items())]
    print(json.dumps(rows, indent=1))
    return rows


def null_to_absence(entry):
    if not isinstance(entry, dict):
        return entry, False
    v = entry.get("value")
    if isinstance(v, dict) and v.get("form") in ("point", "range") and "period" in v and v["period"] is None:
        e = copy.deepcopy(entry)
        e["value"]["period"] = dict(NULL_PERIOD)
        return e, True
    return entry, False


def describe(entry):
    """Card text for one family's entry: shape and value, never written to committed output."""
    if not isinstance(entry, dict):
        return "MISSING"
    ta = entry.get("typed_absence")
    v = entry.get("value")
    if isinstance(ta, dict) and (v is None or v == {"form": "absent"}):
        return f"ABSENT reason={ta.get('reason')}"
    if isinstance(v, dict):
        keep = {k: v.get(k) for k in ("form", "value", "low", "high", "bound", "unit", "currency", "basis", "negated")
                if k in v}
        return f"{json.dumps(keep)} period={period_shape(v.get('period'))}"
    return f"RAW {json.dumps(v)[:160]}"


def excerpt(entry):
    sp = (entry or {}).get("source_span") or {}
    return re.sub(r"\s+", " ", str(sp.get("excerpt", "")))[:400]


def run(w2, bench, out):
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(w2 / "score" / "critical_slots.jsonl")]
    mal = sorted((r for r in rows if r["class"] == "malformed_value"), key=lambda r: (r["case_id"], r["field"]))
    code_to_full = {v: k for k, v in sb.TEMPLATE_CODE.items()}
    cases = {c["item_id"]: c for c in sb.jl(bench / "graded" / "cases.jsonl")}
    regrade, lines = [], []
    for i, r in enumerate(mal, 1):
        cid, f = r["case_id"], r["field"]
        c = dict(cases[cid])
        c["template_full"] = code_to_full[c["template"]]
        bundle = sb.Bundle(w2 / "bundles_graded" / cid)
        ea, eb = (load(w2, cid, fam)["fields"].get(f) for fam in ("fam_a", "fam_b"))
        ea2, ma = null_to_absence(ea)
        eb2, mb = null_to_absence(eb)
        ab = sb.grade_slot(c, "fam_a", "fam_b", f, ea2, eb2, bundle)
        ba = sb.grade_slot(c, "fam_b", "fam_a", f, eb2, ea2, bundle)
        cls = sb.slot_class(ab, ba, ea2, eb2)
        regrade.append({"n": i, "case_id": cid, "field": f, "template": r["template"], "fold": r["fold"],
                        "prompt_version": r.get("prompt_version"),
                        "null_period": {"fam_a": ma, "fam_b": mb},
                        "class_as_scored": r["class"], "class_counterfactual": cls,
                        "outcome_fam_b_graded": ab["outcome"], "outcome_fam_a_graded": ba["outcome"],
                        "notes": sorted(set(ab.get("notes", [])) | set(ba.get("notes", [])))})
        text = (w2 / "bundles_graded" / cid / "source.txt").read_bytes().decode("utf-8", "replace")
        lines.append(f"=== M{i} {cid} {r['template']} {f} [counterfactual {cls}] body_chars={len(text)}")
        for fam, e in (("fam_a", ea), ("fam_b", eb)):
            lines.append(f"  {fam}: {describe(e)}")
            lines.append(f"     span: {excerpt(e)}")
    summary = collections.Counter(x["class_counterfactual"] for x in regrade)
    (out / "regrade_malformed.json").write_text(json.dumps(
        {"rule": "period null read as field_absence.v1 not_stated (diagnostic only)",
         "n": len(regrade), "class_counterfactual": dict(sorted(summary.items())), "slots": regrade},
        indent=1, sort_keys=True) + "\n")
    for old in out.glob("batch_malformed_*.txt"):
        old.unlink()
    (out / "batch_malformed_1.txt").write_text("\n".join(lines) + "\n")
    print(len(regrade), "slots;", dict(sorted(summary.items())))


if __name__ == "__main__":
    w2, bench = Path(sys.argv[1]), Path(sys.argv[2])
    if sys.argv[3] == "--census":
        census(w2)
    else:
        run(w2, bench, Path(sys.argv[3]))
