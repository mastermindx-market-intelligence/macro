"""Seat tool: representation-only canonicalisation of label_return.v1 files before agreement.

usage (from the repository tree root):
  PYTHONPATH=. python3 canon_returns.py --labels DIR [--labels DIR ...] --out DIR

Why: label_return.v1 leaves field_entry.value unconstrained, so a nested value can carry a
shape the frozen news_impact_event.v1 contract does not allow, and agreement then compares
the raw dict. This pass rewrites only those shapes, by a closed rule list. It never changes
a number, a unit dimension, a currency, a period component, an absence reason or a span.

Rules (each hit is counted per file in canon_manifest.json):
  C1 period_absence_unwrap  A quantity's `period` (or a period-kind field value) written as
                            {"form":"absent","absence":A}, A a field_absence.v1 /
                            owner_typed_absence.v1, becomes A. The contract types `period`
                            as fiscal_period | absence_union, so the wrapper is not a
                            contract shape (quantity_absent wraps the QUANTITY, not the period).
  C2 period_form_drop       A fiscal_period object carrying a `form` key (not a contract key)
                            loses that key. The other period keys are untouched.
  C3 per_share_unit         basis per_share, ISO currency X, unit "<X> per share" (any case)
                            becomes unit X. Annotation guide section 5.1: a currency slot's
                            unit is the ISO code; per-share lives in basis.
  C4 iso_unit_case          A unit equal to the ISO currency code apart from case becomes the
                            code in upper case (guide section 5.1).

Output files keep their names. canon_manifest.json records, per file, the input sha256, the
output sha256 and the rule hits, plus the rule list itself.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from engine.news_impact.agreement import ABSENCE_SCHEMA_CONSTS, FIELD_KINDS, KIND_PERIOD, KIND_QUANTITY

RULES = ["C1 period_absence_unwrap", "C2 period_form_drop", "C3 per_share_unit", "C4 iso_unit_case"]
ISO = re.compile(r"^[A-Z]{3}$")


def _is_absence(v):
    return isinstance(v, dict) and v.get("schema") in ABSENCE_SCHEMA_CONSTS


def _canon_period(p, hits):
    if isinstance(p, dict) and p.get("form") == "absent" and _is_absence(p.get("absence")) and set(p) <= {"form", "absence"}:
        hits["C1"] += 1
        return p["absence"]
    if isinstance(p, dict) and "period_kind" in p and "form" in p:
        hits["C2"] += 1
        p = {k: v for k, v in p.items() if k != "form"}
    return p


def _canon_quantity(q, hits):
    if not isinstance(q, dict) or q.get("form") not in ("point", "range"):
        return q
    q = dict(q)
    if "period" in q:
        q["period"] = _canon_period(q["period"], hits)
    cur, unit = q.get("currency"), q.get("unit")
    if isinstance(cur, str) and ISO.match(cur) and isinstance(unit, str):
        u = unit.strip()
        if q.get("basis") == "per_share" and u.lower() == f"{cur.lower()} per share":
            hits["C3"] += 1
            q["unit"] = cur
        elif u != cur and u.lower() == cur.lower():
            hits["C4"] += 1
            q["unit"] = cur
    return q


def canon_record(rec):
    hits = {"C1": 0, "C2": 0, "C3": 0, "C4": 0}
    out = copy.deepcopy(rec)
    kinds = FIELD_KINDS.get(out.get("template"), {})
    for name, entry in out.get("fields", {}).items():
        kind = kinds.get(name)
        v = entry.get("value")
        if v is None:
            continue
        if kind == KIND_QUANTITY:
            entry["value"] = _canon_quantity(v, hits)
        elif kind == KIND_PERIOD:
            entry["value"] = _canon_period(v, hits)
    return out, hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, action="append")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"rules": RULES, "files": {}}
    totals = {"C1": 0, "C2": 0, "C3": 0, "C4": 0}
    for d in args.labels:
        for f in sorted(Path(d).glob("*.fam_*.json")):
            raw = f.read_bytes()
            rec, hits = canon_record(json.loads(raw.decode("utf-8")))
            if (out / f.name).exists():
                raise SystemExit(f"duplicate return name across label dirs: {f.name}")
            body = (json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8") if any(hits.values()) else raw
            (out / f.name).write_bytes(body)
            manifest["files"][f.name] = {"source_dir": str(d), "in_sha256": hashlib.sha256(raw).hexdigest(),
                                         "out_sha256": hashlib.sha256(body).hexdigest(), "hits": hits}
            for k in totals:
                totals[k] += hits[k]
    manifest["totals"] = totals
    manifest["n_files"] = len(manifest["files"])
    manifest["n_changed"] = sum(1 for v in manifest["files"].values() if any(v["hits"].values()))
    (out / "canon_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"n_files": manifest["n_files"], "n_changed": manifest["n_changed"], "totals": totals}))


if __name__ == "__main__":
    main()
