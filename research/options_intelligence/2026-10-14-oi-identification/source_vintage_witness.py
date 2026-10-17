#!/usr/bin/env python3
"""Reproduce bounded OI source-identity/netting counterexamples; synthetic only.

Loads the exact existing producer after checking its Git blob identity. This
is a pre-repair witness, not an alternative production source or an OI feed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

EXPECTED_BLOB = "917bbd225ab2ed3ad5668b38dcbb4f4c4d0c988f"
SOURCE_REF = "a3f3afa1e1268908a54263043f21048c1b5bc1b4"


def run(source: Path) -> dict:
    source = source.resolve(strict=True)
    raw = source.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != EXPECTED_BLOB:
        raise ValueError("SOURCE_IDENTITY_MISMATCH: re-evaluate before reusing this witness")
    sys.path.insert(0, str(source.parents[1]))
    spec = importlib.util.spec_from_file_location("oi_vintage_subject", source)
    if spec is None or spec.loader is None:
        raise ValueError("SOURCE_LOADER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    import pandas as pd

    def frame(quantities, *, one_strike=False, spot=100.0):
        return pd.DataFrame({
            "underlying": ["SYNTH", "SYNTH"],
            "strike_ticker": ["SYNTH-CALL-2026-11-20-100", "SYNTH-CALL-2026-12-18-100" if one_strike else "SYNTH-CALL-2026-11-20-110"],
            "K": [100.0, 100.0 if one_strike else 110.0],
            "is_call": [True, True],
            "oi": list(quantities),
            "spot": [spot, spot],
        })

    def inspect(prior, latest):
        first = module.vintage_fingerprints(prior)
        last = module.vintage_fingerprints(latest)
        same = bool(module.same_vintage_mask(first, last).loc["SYNTH"])
        grouped = module.matched_oi_delta(prior, latest)
        by_contract_old = dict(zip(prior["strike_ticker"], prior["oi"]))
        by_contract_new = dict(zip(latest["strike_ticker"], latest["oi"]))
        common = sorted(by_contract_old.keys() & by_contract_new.keys())
        contract_changes = {key: int(by_contract_new[key] - by_contract_old[key]) for key in common}
        cluster_output = module.clusters_for_underlying(grouped)
        return {
            "same_vintage_mask": same,
            "prior_summary": {"contracts": int(first.loc["SYNTH", "contracts"]), "oi_total": int(first.loc["SYNTH", "oi_total"]), "spot": float(first.loc["SYNTH", "spot"])},
            "latest_summary": {"contracts": int(last.loc["SYNTH", "contracts"]), "oi_total": int(last.loc["SYNTH", "oi_total"]), "spot": float(last.loc["SYNTH", "spot"])},
            "exact_contract_changes": contract_changes,
            "sum_absolute_exact_contract_change": sum(abs(x) for x in contract_changes.values()),
            "sum_absolute_strike_aggregated_change": float(grouped["oi_delta"].abs().sum()),
            "ungated_strike_clusters": cluster_output,
            "loader_same_vintage_branch_would_suppress": same,
        }

    redistribution = inspect(frame([50, 150]), frame([150, 50]))
    assert redistribution["same_vintage_mask"] is True
    assert redistribution["sum_absolute_exact_contract_change"] == 200
    assert len(redistribution["ungated_strike_clusters"]["new_oi"]) == 1
    assert len(redistribution["ungated_strike_clusters"]["exit_oi"]) == 1

    expiry_offset = inspect(frame([50, 150], one_strike=True), frame([150, 50], one_strike=True))
    assert expiry_offset["sum_absolute_exact_contract_change"] == 200
    assert expiry_offset["sum_absolute_strike_aggregated_change"] == 0

    price_only = inspect(frame([50, 150]), frame([50, 150], spot=101.0))
    assert price_only["same_vintage_mask"] is False
    assert price_only["sum_absolute_exact_contract_change"] == 0

    identical = inspect(frame([50, 150]), frame([50, 150]))
    assert identical["same_vintage_mask"] is True
    assert identical["sum_absolute_exact_contract_change"] == 0

    changed_total = inspect(frame([50, 150]), frame([51, 150]))
    assert changed_total["same_vintage_mask"] is False
    assert changed_total["sum_absolute_exact_contract_change"] == 1

    row_order = inspect(frame([50, 150]), frame([50, 150]).iloc[::-1].copy())
    assert row_order["same_vintage_mask"] is True
    assert row_order["sum_absolute_exact_contract_change"] == 0

    return {
        "schema": "options.oi.source_vintage_witness.v1",
        "source_ref": SOURCE_REF,
        "source_path": "engine/positioning_persistence.py",
        "source_blob": actual,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "synthetic_only": True,
        "source_modified": False,
        "cases": {"constant_total_redistribution": redistribution, "expiry_offset_hidden_by_strike_netting": expiry_offset, "same_oi_changed_spot": price_only, "identical_control": identical, "changed_total_control": changed_total, "row_order_control": row_order},
        "limits": [
            "Calls the exact producer kernels. Does not invoke the store loader or inspect live data.",
            "The documented loader branch at lines1208-1216 suppresses clusters when same_vintage is true; no production impact count is claimed.",
            "Strike netting is legitimate for a net-by-strike view, but is not the per-contract absolute-change numerator specified by OIF18.",
            "Equal full OI content would still not attest a common effective-session vintage. Receipt identity must be preserved separately.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.source)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
