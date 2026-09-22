"""Source-bound clean-entry attribution, not a new entry policy or return study.

Replay the native clean_entry owner on one dated exported frame. Then change
ONLY its relative-strength input in a copied research call. A separate existing
price-extension artifact is context, never replacement rank/entry authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import basket_score, theme_extension

RS_LIMIT = 0.75  # the existing clean_entry literal; not an optimized threshold
QUALITY_FLOOR = 0.60  # existing native flag condition, used only for attribution


def finite(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def iso_day(value):
    if not isinstance(value, str):
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def _extension_context(raw, as_of, identity, n_members):
    unavailable = {"status": "unavailable", "reason": "missing_extension_source"}
    if not isinstance(raw, dict):
        return unavailable
    if raw.get("region") != "us" or raw.get("as_of") != as_of:
        return {"status": "unavailable", "reason": "extension_region_or_date_mismatch"}
    rows = raw.get("themes")
    if not isinstance(rows, list):
        return unavailable
    matches = [r for r in rows if isinstance(r, dict) and r.get("id") == identity]
    if len(matches) != 1:
        return {"status": "unavailable", "reason": "extension_identity_missing_or_duplicated"}
    row = matches[0]
    value, count = row.get("atr_ext"), row.get("n_live")
    if not finite(value) or not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return {"status": "unavailable", "reason": "extension_value_or_coverage_missing"}
    if count != n_members:
        return {"status": "unavailable", "reason": "extension_population_count_mismatch"}
    if row.get("band_en") != theme_extension._band(value)[0]:
        return {"status": "unavailable", "reason": "extension_band_disagrees_with_owner"}
    return {"status": "date_and_count_matched", "as_of": as_of,
            "median_member_close_based_atr_extension": value,
            "band": row["band_en"], "n_live": count,
            "same_generation_and_membership_proven": False,
            "trade_authority": False}


def audit(payload: dict, extension: dict | None = None) -> dict:
    """Pure attribution with explicit refusals; all input objects stay untouched."""
    if not isinstance(payload, dict):
        raise ValueError("theme payload must be an object")
    ti, chart = payload.get("theme_intel"), payload.get("chart")
    if not isinstance(ti, dict) or not isinstance(chart, dict):
        raise ValueError("theme_intel and chart are required")
    as_of = iso_day(ti.get("as_of"))
    dates, levels, rows = chart.get("dates"), chart.get("baskets"), ti.get("themes")
    if (as_of is None or payload.get("as_of") != as_of
            or not isinstance(dates, list) or not dates
            or any(iso_day(d) is None for d in dates)
            or dates != sorted(set(dates)) or dates[-1] != as_of
            or not isinstance(levels, dict) or not isinstance(rows, list)):
        raise ValueError("one coherent, ordered, uniquely dated source frame is required")
    identities = [r.get("id") for r in rows if isinstance(r, dict)]
    if (len(identities) != len(rows) or any(not isinstance(k, str) or not k for k in identities)
            or len(set(identities)) != len(identities)):
        raise ValueError("theme identities must be present and unique")
    records = []
    for row in rows:
        out = {"id": row["id"], "name": row.get("name"), "reco": row.get("reco"),
               "constructive_recommendation": row.get("reco") in ("enter", "accumulate"),
               "status": "unavailable", "attribution": None}
        records.append(out)
        values = levels.get(row["id"])
        fp = {k: row.get(k) for k in ("accel_z", "rs_pctile")}
        breadth = row.get("breadth")
        textures = row.get("textures")
        stored = textures.get("clean_entry") if isinstance(textures, dict) else None
        if not isinstance(breadth, dict) or not isinstance(stored, dict):
            out["reason"] = "missing_or_invalid_native_inputs"
            continue
        if (not isinstance(values, list) or len(values) != len(dates)
                or not values or not finite(values[-1]) or values[-1] <= 0
                or any(v is not None and (not finite(v) or v <= 0) for v in values)):
            out["reason"] = "missing_invalid_or_unaligned_price_series"
            continue
        if (not all(finite(v) for v in fp.values()) or not 0 <= fp["rs_pctile"] <= 1
                or not finite(breadth.get("pct50")) or not 0 <= breadth["pct50"] <= 1
                or any(not isinstance(breadth.get(k), int) or isinstance(breadth[k], bool)
                       or breadth[k] < 0 for k in ("nh", "nl"))
                or not isinstance(stored.get("flag"), bool) or not finite(stored.get("quality"))
                or not 0 <= stored["quality"] <= 1):
            out["reason"] = "missing_or_invalid_native_inputs"
            continue
        level = pd.Series(values, index=pd.to_datetime(dates), dtype=float)
        rsi = basket_score._rsi(level)
        if not finite(rsi):
            out["reason"] = "rsi_history_unavailable"
            continue
        actual = basket_score.clean_entry(level, fp, breadth, rsi)
        if (actual["flag"] != stored["flag"]
                or not math.isclose(actual["quality"], stored["quality"], abs_tol=0.0005)):
            out.update(reason="rounded_export_does_not_reproduce_native_entry",
                       stored={"flag": stored["flag"], "quality": stored["quality"]},
                       replayed={"flag": actual["flag"], "quality": actual["quality"]})
            continue
        changed_fp = {**fp, "rs_pctile": math.nextafter(RS_LIMIT, 0.0)}
        counterfactual = basket_score.clean_entry(level, changed_fp, breadth, rsi)
        attribution = "entry_already_clear" if actual["flag"] else "other_entry_conditions"
        if not actual["flag"] and fp["rs_pctile"] >= RS_LIMIT and counterfactual["flag"]:
            attribution = ("relative_strength_veto_only" if actual["quality"] >= QUALITY_FLOOR
                           else "relative_strength_veto_and_quality_penalty")
        out.update(status="reproduced", attribution=attribution,
                   rs_percentile=fp["rs_pctile"], native_entry=actual,
                   research_counterfactual=counterfactual,
                   missing_chart_observations=sum(v is None for v in values),
                   extension_context=_extension_context(extension, as_of, row["id"], row.get("n_members")))
    reproduced = [r for r in records if r["status"] == "reproduced"]
    constructive = [r for r in reproduced if r["constructive_recommendation"]]
    counts = lambda items: dict(sorted(Counter(r["attribution"] for r in items).items()))
    return {"schema": "theme_entry_attribution_research.v1", "as_of": as_of,
            "scope": "single_dated_export_diagnostic", "policy_change_applied": False,
            "all_input_rows": len(rows), "reproduced_rows": len(reproduced),
            "unavailable_rows": len(rows) - len(reproduced),
            "constructive_reproduced_rows": len(constructive),
            "attribution_counts": counts(reproduced), "constructive_attribution_counts": counts(constructive),
            "records": records,
            "limitations": ["Rounded exported series and inputs, not a full nightly rebuild.",
                            "One snapshot, not episodes, out-of-sample results or forward returns.",
                            "Counterfactual changes one research input only; no trade, rank or size effect.",
                            "Extension matches date and population count, not an atomic generation or roster.",
                            "Basket-level entry texture cannot establish each constituent stock's entry."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.source_ref) is None:
        parser.error("--source-ref must be an immutable full commit SHA")
    # Reuse the existing same-carrier immutable Git reader, not a live fetcher.
    from prove import read_blob
    paths = ("site/basketdata/baskets.json", "site/basketdata/theme_extension.json")
    raw = {p: read_blob(args.source_ref, p) for p in paths}
    owner_digests = {}
    for path, module in (("engine/basket_score.py", basket_score),
                         ("engine/theme_extension.py", theme_extension)):
        source = read_blob(args.source_ref, path)
        if source != Path(module.__file__).read_bytes():
            raise ValueError(f"native owner differs from the input source revision: {path}")
        owner_digests[path] = hashlib.sha256(source).hexdigest()
    result = audit(json.loads(raw[paths[0]]), json.loads(raw[paths[1]]))
    result["source_ref"] = args.source_ref
    result["source_sha256"] = {p: hashlib.sha256(v).hexdigest() for p, v in raw.items()}
    result["native_owner_sha256"] = owner_digests
    result["native_owner_source_matches"] = True
    result["audit_module_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
