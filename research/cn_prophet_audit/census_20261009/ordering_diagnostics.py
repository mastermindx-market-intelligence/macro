"""Reproduce October 9 routing and shortlist sensitivity from immutable Git blobs.

Research only. This script neither grades returns nor writes a candidate store.
It holds published qualification fixed, checks exact v3 cap parity, and permutes
only names already qualified before the existing featured and sector caps.
The counterfactual order is NOT a recommendation or an estimate of improved alpha.

Usage:
  python3 ordering_diagnostics.py --repo /path/to/macro --sha COMMIT > ordering_diagnostics.json
Requires pandas and the repository's parquet engine. No network data access.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import math
import subprocess
from typing import Any, Iterable, Mapping

import pandas as pd

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", default=PIN)
    args = parser.parse_args()
    inputs: dict[str, str] = {}

    def raw(path: str) -> bytes:
        result = subprocess.check_output(
            ["git", "-C", args.repo, "show", args.sha + ":" + path]
        )
        inputs[path] = hashlib.sha256(result).hexdigest()
        return result

    board = json.loads(raw("site/factordata/china_standouts.json"))
    candidates = pd.read_parquet(io.BytesIO(raw("data/china_prophet_rank/candidates.parquet")))
    source = raw("engine/china_board_rank.py")
    tree = ast.parse(source)
    constants = {
        "FEATURED_CAP", "SECTOR_CAP", "INTEL_BASIS_MEASURED", "INTEL_BASIS_FALLBACK",
        "INTEL_INTEREST_ORDER", "V3_SCORE_ORDER", "ORDER_MODE_INTELLIGENCE",
        "ORDER_MODE_V3_FALLBACK", "FALLBACK_REASON_INCOMPLETE_COVERAGE", "SCORE_WEIGHTS",
    }
    functions = {
        "_finite_float", "_attach_intel", "intel_order_key", "intel_interest_is_measured",
        "intel_coverage_summary", "order_provenance", "_stamp_order_provenance",
        "emit_intel_coverage_warning", "apply_v4_board_order",
    }
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in constants for t in node.targets
        ):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
    scope = {"math": math, "Any": Any, "Iterable": Iterable, "Mapping": Mapping}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "ranker@" + args.sha, "exec"), scope)
    assert functions <= scope.keys() and constants <= scope.keys()

    # These controls exercise the exact source functions, not a copy of the rule.
    def order(rows: list[dict]) -> tuple[list[dict], dict]:
        rows = deepcopy(rows)
        with redirect_stdout(io.StringIO()):
            provenance = scope["apply_v4_board_order"](rows)
        return rows, provenance

    high_v3 = {"ticker": "A", "score_rank": 1, "prophet_score": 90,
               "intel_interest_score": 0.0, "intel_interest_basis": "measured"}
    high_intel = {"ticker": "B", "score_rank": 2, "prophet_score": 50,
                 "intel_interest_score": 50.0, "intel_interest_basis": "measured"}
    clean, clean_mode = order([high_v3, high_intel])
    assert [r["ticker"] for r in clean] == ["B", "A"]
    assert clean_mode["intel_order_active"] is True
    irrelevant = {"ticker": "UNBUYABLE", "score_rank": 99, "prophet_score": 0,
                  "raw_eligible": False, "buyable": False,
                  "intel_interest_score": None, "intel_interest_basis": "fallback_v3"}
    contaminated, contaminated_mode = order([high_v3, high_intel, irrelevant])
    assert [r["ticker"] for r in contaminated[:2]] == ["A", "B"]
    assert contaminated_mode["intel_order_active"] is False
    malformed_controls = {}
    for label, value in [("none", None), ("nan", float("nan")), ("text", "bad")]:
        record: dict[str, Any] = {}
        scope["_attach_intel"](record, {"basis": "measured", "score": value})
        malformed_controls[label] = record["intel_interest_basis"]
        assert record["intel_interest_basis"] == "fallback_v3"
    zero: dict[str, Any] = {}
    scope["_attach_intel"](zero, {"basis": "measured", "score": 0})
    assert zero["intel_interest_basis"] == "measured"
    assert zero["intel_interest_score"] == 0.0

    current = candidates[candidates["stamp_date"].astype(str).str[:10] == board["as_of"]].copy()
    assert current["ticker"].is_unique
    current_rows = []
    for r in current.to_dict("records"):
        current_rows.append({**r, "intel_interest_score": r.get("intel_score"),
                             "intel_interest_basis": r.get("intel_basis")})
    coverage = scope["intel_coverage_summary"](current_rows)
    assert coverage["n_rows"] == board["universe"]
    assert coverage["n_measured"] == board["ranking"]["input_coverage"]["intel_interest"]["n_measured"]
    unavailable = [r for r in current_rows if not scope["intel_interest_is_measured"](r)]
    # Equal calendar dates and counts do not imply identical publication vintages.
    # Keep this diagnostic anchored to the PUBLIC row values used below.
    public_rows = [r for lane in ("buy", "more_actionable", "late_or_unfillable", "forming")
                   for r in board[lane]]
    candidate_map = {r["ticker"]: r for r in current_rows}
    coherence = {"public_rows": len(public_rows), "missing_in_candidate_snapshot": [],
                 "lane_disagreements": [], "v3_score_disagreements": [],
                 "intel_score_disagreements": []}
    for row in public_rows:
        candidate = candidate_map.get(row["ticker"])
        if candidate is None:
            coherence["missing_in_candidate_snapshot"].append(row["ticker"])
            continue
        if row["lane"] != candidate["lane"]:
            coherence["lane_disagreements"].append(row["ticker"])
        for output_key, public_value, candidate_value in (
            ("v3_score_disagreements", row["prophet"]["score"], candidate["prophet_score"]),
            ("intel_score_disagreements", row.get("intel_interest_score"), candidate.get("intel_score")),
        ):
            a, b = scope["_finite_float"](public_value), scope["_finite_float"](candidate_value)
            different = (a is None) != (b is None) or (a is not None and b is not None and abs(a - b) > 1e-6)
            if different:
                coherence[output_key].append({"ticker": row["ticker"], "public": a, "candidate": b})
    admissible = list(board["buy"]) + [
        r for r in board["more_actionable"]
        if r.get("lane_reasons") and set(r["lane_reasons"]) <= {"featured_cap", "sector_cap"}
    ]
    assert len({r["ticker"] for r in admissible}) == len(admissible)
    assert all(scope["intel_interest_is_measured"](r) for r in admissible)
    for row in admissible:
        row["prophet_score"] = row["prophet"]["score"]
        assert round(sum(row["prophet"]["points"].values()), 2) == row["prophet_score"]

    # This is only the cap-allocation portion of _partition, after published
    # qualification. Exact current-output parity below is a required control.
    def admit(rows: list[dict], sector_cap: int | None = None) -> list[dict]:
        chosen = []
        sectors: Counter = Counter()
        sector_cap = scope["SECTOR_CAP"] if sector_cap is None else sector_cap
        for row in rows:
            sector = str(row.get("sector") or "—")
            if len(chosen) < scope["FEATURED_CAP"] and sectors[sector] < sector_cap:
                chosen.append(row)
                sectors[sector] += 1
        return chosen

    v3 = sorted(admissible, key=lambda r: (r["score_rank"], r["ticker"]))
    before = admit(v3)
    published_names = [r["ticker"] for r in board["buy"]]
    assert [r["ticker"] for r in before] == published_names, "STOP: current v3 positive control failed"
    intel_order, intel_provenance = order(admissible)
    after = admit(intel_order)
    before_set = set(published_names)
    after_set = {r["ticker"] for r in after}

    def compact(rows: list[dict]) -> list[dict]:
        return [{k: r.get(k) for k in ("ticker", "sector", "prophet_score", "intel_interest_score")}
                for r in rows]

    ablations = {}
    for component in scope["SCORE_WEIGHTS"]:
        ranked = sorted(admissible, key=lambda r: (
            -round(max(0.0, min(100.0, sum(
                float(value) for key, value in r["prophet"]["points"].items()
                if key != component
            ))), 2), r["ticker"]
        ))
        selected = admit(ranked)
        selected_set = {r["ticker"] for r in selected}
        ablations[component] = {
            "overlap_with_published_24": len(selected_set & before_set),
            "displaced_count": len(before_set - selected_set),
        }

    actionable = [r for r in current_rows if bool(r.get("buyable"))]
    raw_eligible = [r for r in current_rows if bool(r.get("raw_eligible"))]
    result = {
        "source_sha": args.sha, "input_sha256": inputs, "as_of": board["as_of"],
        "claim_boundary": "Observed routing and same-day selection sensitivity only; no realized-return, alpha, PIT replay, deployment or recommendation claim.",
        "population_sources": "All-scored coverage and unavailable records use the candidate ledger; shortlist sensitivity uses the public artifact. Same-date value differences are retained below, not treated as one proven publication vintage.",
        "public_candidate_same_date_coherence": coherence,
        "controls": {
            "exact_v3_featured_24_and_order_reproduced": True,
            "measured_zero_keeps_intelligence_mode": True,
            "unbuyable_missing_row_reverses_existing_pair_order": True,
            "malformed_record_controls": malformed_controls,
            "all_pre_cap_qualified_have_measured_intel": True,
        },
        "coverage": {"all_scored": coverage,
                     "raw_eligible": scope["intel_coverage_summary"](raw_eligible),
                     "buyable": scope["intel_coverage_summary"](actionable)},
        "unavailable_current_records": [{k: (None if pd.isna(r.get(k)) else r.get(k)) for k in
            ("ticker", "lane", "score_rank", "prophet_score", "raw_eligible", "buyable", "entry_status", "intel_unavailable_reason")}
            for r in unavailable],
        "frozen_pre_cap_qualified_n": len(admissible),
        "same_qualification_intel_counterfactual": {
            "mode": intel_provenance, "featured_n": len(after),
            "overlap_at_24": len(before_set & after_set),
            "overlap_fraction": len(before_set & after_set) / len(before_set),
            "jaccard": len(before_set & after_set) / len(before_set | after_set),
            "replaced_fraction": len(before_set - after_set) / len(before_set),
            "entrants": compact([r for r in after if r["ticker"] not in before_set]),
            "displaced": compact([r for r in before if r["ticker"] not in after_set]),
            "published_sector_counts": dict(Counter(r["sector"] for r in before)),
            "counterfactual_sector_counts": dict(Counter(r["sector"] for r in after)),
        },
        "structural_ablations_no_outcome_claim": ablations,
        "v3_without_sector_cap_no_outcome_claim": {
            "overlap_with_published_24": len({r["ticker"] for r in admit(v3, 24)} & before_set),
            "sector_counts": dict(Counter(r["sector"] for r in admit(v3, 24))),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
