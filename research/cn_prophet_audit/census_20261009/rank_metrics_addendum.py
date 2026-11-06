#!/usr/bin/env python3
"""Complete prespecified rank metrics from unchanged, hash-pinned audit outputs.

No network, subprocess, price calculation, source checkout or production write.
Reads three local JSON inputs. Writes only the two independent addendum outputs.
The pool input is a lossless CSV-string subset of the existing analytical archive,
extracted before filtering outcome status or feature missingness.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import fmean


SOURCE_SHA = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
INPUT_HASHES = {
    "v4_review_rows.json": "626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830",
    "historical_evidence.json": "8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d",
    "rank_metrics_pool_input.json": "1f6708ca0e8ec12d2983900f5d5d0313a9272e726730d7a91a220b4165bb6976",
}
CSV_HASH = "2db25adc73e9e5e5a934898edb4da6ae6852b43b096613acbe5724b8f622a1b3"
MANIFEST_HASH = "80f38bdd75cff63d87190081c4edf027bdce5d564dc23740f9203750b70209c4"
DATE_BOOTSTRAP_SEED = 20261009
DATE_BOOTSTRAP_REPLICATES = 10000
SCOPE = "rankable_common_features"
FEATURES = ["prophet_score", "intel_score", "ret_3m", "quality_z"]
# Direction is +1 for ascending and -1 for descending; ticker always ascends.
ARMS = [
    ("score_top6", "Score", [("prophet_score", -1)]),
    ("intel_top6", "Stored intel; ticker tie-break", [("intel_score", -1)]),
    ("momentum_top6", "Momentum", [("ret_3m", -1)]),
    ("reversal_top6", "Reversal", [("ret_3m", 1)]),
    ("quality_top6", "Quality", [("quality_z", -1)]),
]
INTENDED_INTEL_KEYS = [("intel_score", -1), ("prophet_score", -1)]
FLOAT_COLUMNS = FEATURES + ["pnl_cc", "benchmark_cc", "excess_cc"]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def near(left, right, message):
    check(math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-10), message)


def load_inputs(directory):
    inputs = {}
    for name, expected in INPUT_HASHES.items():
        payload = (directory / name).read_bytes()
        check(hashlib.sha256(payload).hexdigest() == expected, f"Unaccepted input hash: {name}")
        inputs[name] = json.loads(payload)
    evidence = inputs["historical_evidence.json"]["autopsy"]
    pool = inputs["rank_metrics_pool_input.json"]
    check(evidence["source_sha"] == pool["source_sha"] == SOURCE_SHA, "Source pin mismatch")
    check(pool["source_csv"]["sha256"] == CSV_HASH, "Archive CSV hash mismatch")
    check(pool["source_manifest"]["sha256"] == MANIFEST_HASH, "Archive manifest hash mismatch")
    manifest = pool["source_manifest"]["contents"]
    check(manifest["eligible_candidate_horizon_returns.csv"]["sha256"] == CSV_HASH, "CSV does not match archive manifest")
    check(manifest["eligible_candidate_horizon_returns.csv"]["bytes"] == pool["source_csv"]["bytes"], "CSV byte count mismatch")
    for name in ["v4_review_rows.json", "historical_evidence.json"]:
        check(manifest[name]["sha256"] == INPUT_HASHES[name], "Archive/accepted output mismatch")
    return inputs["v4_review_rows.json"], evidence, pool


def matrix_records(matrix):
    columns = matrix["columns"]
    check(len(columns) == len(set(columns)), "Duplicate matrix columns")
    for values in matrix["data"]:
        check(len(values) == len(columns), "Wrong matrix row length")
        yield dict(zip(columns, values))


def relevant(row, definition_key="board_definition"):
    return row.get(definition_key) == "cn_prophet_v4" and row.get("horizon") == 10 and row.get("scope") == SCOPE


def optional_float(value):
    if value is None or value == "":
        return None
    number = float(value)
    check(math.isfinite(number), "Nonfinite CSV value; do not silently change missingness")
    return number


def parse_pool(pool):
    parsed = []
    seen = set()
    for raw in matrix_records(pool):
        row = dict(raw)
        check(row["board_definition"] == "cn_prophet_v4" and row["horizon"] == "10", "Unexpected definition/horizon")
        qualified = row["lane"] == "featured" or (row["lane"] == "more_actionable" and row["lane_reasons"] in ["featured_cap", "sector_cap"])
        check(qualified, "Nonqualified row in subset")
        identity = (row["date"], row["ticker"])
        check(identity not in seen, "Duplicate date/ticker in qualified pool")
        seen.add(identity)
        for column in FLOAT_COLUMNS:
            row[column] = optional_float(row[column])
        row["sector"] = row["sector"] or None
        if row["status"] == "observed":
            check(all(row[column] is not None for column in ["pnl_cc", "benchmark_cc", "excess_cc"]), "Observed row missing outcome")
            near(row["pnl_cc"] - row["benchmark_cc"], row["excess_cc"], "Outcome algebra mismatch")
        parsed.append(row)
    check(len(parsed) == pool["extraction"]["qualified_rows"] == 1488, "Wrong qualified denominator")
    check(dict(Counter(r["status"] for r in parsed)) == pool["extraction"]["qualified_status_counts"], "Subset status census mismatch")
    return parsed


def frozen_select(rows, keys, k, sector_cap):
    """Selection accesses frozen features, ticker and sector only, never outcomes."""
    ordered = sorted(rows, key=lambda row: tuple(direction * row[column] for column, direction in keys) + (row["ticker"],))
    selected, sector_counts = [], Counter()
    for row in ordered:
        if sector_cap is not None and sector_counts[row["sector"]] >= sector_cap:
            continue
        selected.append(row)
        sector_counts[row["sector"]] += 1
        if len(selected) == k:
            break
    return selected


def complete(rows):
    return bool(rows) and all(row["status"] == "observed" and row["excess_cc"] is not None for row in rows)


def metrics(rows):
    check(complete(rows), "Attempt to grade unresolved original selections")
    hits = sum(row["excess_cc"] > 0 for row in rows)
    return {
        "n": len(rows), "positive_excess_n": hits, "precision": hits / len(rows),
        "mean_excess_cc_pp": fmean(row["excess_cc"] for row in rows),
        "mean_pnl_cc_pct": fmean(row["pnl_cc"] for row in rows),
    }


def membership_receipt(rows):
    return {
        "tickers": [row["ticker"] for row in rows],
        "selected_n": len(rows),
        "unresolved": [{"ticker": row["ticker"], "status": row["status"]} for row in rows if row["status"] != "observed"],
    }


def aggregate_daily(daily):
    check(bool(daily), "Empty comparison")
    selected_n = sum(row["n"] for row in daily)
    hits = sum(row["positive_excess_n"] for row in daily)
    return {
        "n_dates": len(daily), "n_selected_observations": selected_n,
        "positive_excess_n": hits,
        "date_weighted_precision": fmean(row["precision"] for row in daily),
        "pooled_precision": hits / selected_n,
        "date_weighted_mean_excess_cc_pp": fmean(row["mean_excess_cc_pp"] for row in daily),
    }


def paired_date_intervals(vectors):
    """Shared date resamples; percentile endpoints use linear interpolation."""
    lengths = {len(values) for values in vectors.values()}
    check(len(lengths) == 1, "Paired bootstrap must use identical dates for every arm")
    n_dates = next(iter(lengths))
    check(n_dates > 1, "Too few dates for the specified descriptive interval")
    rng = random.Random(DATE_BOOTSTRAP_SEED)
    draws = [rng.choices(range(n_dates), k=n_dates) for _ in range(DATE_BOOTSTRAP_REPLICATES)]
    intervals = {}
    for name, values in vectors.items():
        samples = sorted(fmean(values[index] for index in draw) for draw in draws)
        endpoints = []
        for quantile in [0.025, 0.975]:
            position = (len(samples) - 1) * quantile
            lower, upper = math.floor(position), math.ceil(position)
            fraction = position - lower
            endpoints.append(samples[lower] * (1 - fraction) + samples[upper] * fraction)
        intervals[name] = endpoints
    return intervals


def analyze(review, evidence, pool_input, script_hash):
    baseline = [row for row in matrix_records(review["baseline_dates"]) if relevant(row)]
    expected = defaultdict(dict)
    for row in baseline:
        check(row["date"] not in expected[row["baseline"]], "Duplicate accepted arm/date")
        expected[row["baseline"]][row["date"]] = row
    dates = sorted(expected["score_top6"])
    check(len(dates) == 11, "Wrong accepted date denominator")
    for name, _, _ in ARMS:
        check(sorted(expected[name]) == dates, "Accepted arm date mismatch")
    summaries = {row["baseline"]: row for row in evidence["baseline_comparison"] if relevant(row)}
    by_date = defaultdict(list)
    for row in parse_pool(pool_input):
        by_date[row["date"]].append(row)
    discordant = {
        row["date"] for row in evidence["cohort_vintage_coherence"]
        if row["definition"] == "cn_prophet_v4" and (not row["same_featured_set"] or row["score_disagreements"] > 0)
    }
    common_pools, selections, date_audit = {}, {}, []
    reconstructed_dates = []
    for date, qualified in sorted(by_date.items()):
        pool = [row for row in qualified if all(row[column] is not None for column in FEATURES)]
        item = {
            "date": date, "qualified_n": len(qualified), "common_feature_pool_n": len(pool),
            "missing_feature_n": {column: sum(row[column] is None for row in qualified) for column in FEATURES},
            "qualified_status_counts": dict(Counter(row["status"] for row in qualified)),
            "common_pool_status_counts": dict(Counter(row["status"] for row in pool)),
            "vintage_discordant": date in discordant,
        }
        if date in discordant:
            item["gate"] = "existing_vintage_exclusion"
        elif len(pool) < 6:
            item["gate"] = "fewer_than_six_common_feature_names"
        else:
            # All five memberships are frozen before outcome completeness checks.
            frozen = {name: frozen_select(pool, keys, 6, 4) for name, _, keys in ARMS}
            common_pools[date] = pool
            selections[date] = frozen
            item["frozen_selections"] = {name: membership_receipt(rows) for name, rows in frozen.items()}
            if not any(row["status"] == "observed" for row in pool):
                item["gate"] = "no_observed_h10_outcomes"
            elif not all(len(rows) == 6 and complete(rows) for rows in frozen.values()):
                item["gate"] = "incomplete_frozen_selection"
            else:
                item["gate"] = "accepted_common_date"
                reconstructed_dates.append(date)
        date_audit.append(item)
    check(reconstructed_dates == dates, "Reconstructed cohort differs from accepted 11 dates")
    daily, precision_rows = [], []
    for date in dates:
        pool = common_pools[date]
        item = {
            "date": date, "pool_n": len(pool),
            "pool_observed_n": sum(row["status"] == "observed" for row in pool),
            "pool_complete": complete(pool), "decile_k": math.ceil(len(pool) / 10), "arms": {},
        }
        for name, _, _ in ARMS:
            selection = selections[date][name]
            actual = metrics(selection)
            receipt = expected[name][date]
            check(actual["n"] == receipt["n"] == 6, "Wrong original K")
            check(len(pool) == receipt["pool_n"] and item["pool_observed_n"] == receipt["observed_n"], "Pool denominator mismatch")
            near(actual["precision"], receipt["hit_rate"], "Original daily precision mismatch")
            near(actual["mean_excess_cc_pp"], receipt["excess_cc"], "Original daily mean excess mismatch")
            near(actual["mean_pnl_cc_pct"], receipt["pnl_cc"], "Original daily mean stock return mismatch")
            item["arms"][name] = {**actual, **membership_receipt(selection)}
        if complete(pool):
            actual_pool = metrics(pool)
            check(date in expected["eligible_equal"], "Missing accepted complete-pool receipt")
            near(actual_pool["precision"], expected["eligible_equal"][date]["hit_rate"], "Full-pool precision mismatch")
            near(actual_pool["mean_excess_cc_pp"], expected["eligible_equal"][date]["excess_cc"], "Full-pool excess mismatch")
            item["pool_metrics"] = actual_pool
        else:
            check(date not in expected["eligible_equal"], "Accepted pool should be unresolved")
            item["pool_unresolved"] = membership_receipt(pool)["unresolved"]
        daily.append(item)
    for name, label, keys in ARMS:
        summary = aggregate_daily([row["arms"][name] for row in daily])
        check(summary["n_dates"] == 11 and summary["n_selected_observations"] == 66, "Wrong accepted precision denominator")
        near(summary["date_weighted_precision"], summaries[name]["average_precision"], "Accepted summary precision mismatch")
        near(summary["date_weighted_mean_excess_cc_pp"], summaries[name]["mean_pct"], "Accepted summary excess mismatch")
        precision_rows.append({"baseline": name, "label": label, "sort_keys": keys, "ticker_tiebreak": "ascending", **summary})
    # One prespecified intended intel tie-break; all 11 original dates retained as attempts.
    intended_daily = []
    for date in dates:
        old = selections[date]["intel_top6"]
        new = frozen_select(common_pools[date], INTENDED_INTEL_KEYS, 6, 4)
        old_names, new_names = [r["ticker"] for r in old], [r["ticker"] for r in new]
        paired_complete = len(new) == 6 and complete(new)
        item = {
            "date": date, "old_tickers": old_names, "new_tickers": new_names,
            "order_changed": old_names != new_names,
            "membership_changed": set(old_names) != set(new_names),
            "old_only": sorted(set(old_names) - set(new_names)),
            "new_only": sorted(set(new_names) - set(old_names)),
            "paired_complete": paired_complete,
            "new_unresolved": membership_receipt(new)["unresolved"],
            "old_metrics": metrics(old),
        }
        if paired_complete:
            item["new_metrics"] = metrics(new)
            item["precision_delta_pp"] = 100 * (item["new_metrics"]["precision"] - item["old_metrics"]["precision"])
            item["mean_excess_delta_pp"] = item["new_metrics"]["mean_excess_cc_pp"] - item["old_metrics"]["mean_excess_cc_pp"]
        intended_daily.append(item)
    paired = [r for r in intended_daily if r["paired_complete"]]
    old_summary = aggregate_daily([r["old_metrics"] for r in paired])
    new_summary = aggregate_daily([r["new_metrics"] for r in paired])
    intended = {
        "scope": "One separately labeled intended-policy top-six tie-break check; identical original common pools.",
        "accepted_sort": ["intel_score descending", "ticker ascending"],
        "intended_sort": ["intel_score descending", "prophet_score descending", "ticker ascending"],
        "policy_source": "Integrated source-policy review supplied by the parent; stored prophet_score is the secondary v3 score in this diagnostic.",
        "k": 6, "sector_cap": 4, "attempted_dates": dates,
        "paired_dates": [r["date"] for r in paired],
        "new_excluded_dates": [r["date"] for r in intended_daily if not r["paired_complete"]],
        "membership_changed_dates": [r["date"] for r in intended_daily if r["membership_changed"]],
        "order_changed_dates": [r["date"] for r in intended_daily if r["order_changed"]],
        "replacement_slots": sum(len(r["new_only"]) for r in intended_daily),
        "accepted_stored_intel_on_paired_dates": old_summary,
        "intended_intel_on_paired_dates": new_summary,
        "precision_delta_pp": 100 * (new_summary["date_weighted_precision"] - old_summary["date_weighted_precision"]),
        "mean_excess_delta_pp": new_summary["date_weighted_mean_excess_cc_pp"] - old_summary["date_weighted_mean_excess_cc_pp"],
        "daily": intended_daily,
    }
    # Prespecified five existing feature orderings; no new model/parameter sweep.
    decile_attempts, decile_complete = [], []
    for date in dates:
        pool = common_pools[date]
        k = math.ceil(len(pool) / 10)
        frozen = {name: frozen_select(pool, keys, k, None) for name, _, keys in ARMS}
        # Completeness is checked only after membership and K are fixed.
        admissible = complete(pool) and all(len(rows) == k and complete(rows) for rows in frozen.values())
        item = {
            "date": date, "original_pool_n": len(pool), "k": k, "complete_original_pool": complete(pool),
            "admissible": admissible, "pool_unresolved": membership_receipt(pool)["unresolved"],
            "selections": {name: membership_receipt(rows) for name, rows in frozen.items()},
        }
        if admissible:
            item["pool_metrics"] = metrics(pool)
            item["arm_metrics"] = {name: metrics(rows) for name, rows in frozen.items()}
            decile_complete.append(item)
        decile_attempts.append(item)
    check([r["date"] for r in decile_complete] == sorted(expected["eligible_equal"]), "Decile/full-pool date mismatch")
    pool_summary = aggregate_daily([r["pool_metrics"] for r in decile_complete])
    paired_return_lifts = {
        name: [row["arm_metrics"][name]["mean_excess_cc_pp"] - row["pool_metrics"]["mean_excess_cc_pp"] for row in decile_complete]
        for name, _, _ in ARMS
    }
    paired_intervals = paired_date_intervals(paired_return_lifts)
    decile_summaries = []
    for name, label, keys in ARMS:
        summary = aggregate_daily([r["arm_metrics"][name] for r in decile_complete])
        pool_precision = pool_summary["date_weighted_precision"]
        mean_lift = summary["date_weighted_mean_excess_cc_pp"] - pool_summary["date_weighted_mean_excess_cc_pp"]
        near(mean_lift, fmean(paired_return_lifts[name]), "Paired date lift mean mismatch")
        decile_summaries.append({
            "ordering": name.removesuffix("_top6"), "label": label, "sort_keys": keys, "ticker_tiebreak": "ascending",
            **summary, "pool_date_weighted_precision": pool_precision,
            "precision_lift_ratio": summary["date_weighted_precision"] / pool_precision if pool_precision > 0 else None,
            "precision_lift_pp": 100 * (summary["date_weighted_precision"] - pool_precision),
            "mean_excess_lift_pp": mean_lift,
            "paired_date_return_lifts_pp": paired_return_lifts[name],
            "mean_excess_lift_paired_datecluster95_pp": paired_intervals[name],
        })
    decile = {
        "k_rule": "ceil(0.1 * original common-feature eligible pool_n), before outcome lookup",
        "sector_cap": None, "date_weighting": "Equal weight per date for both selected precision and full-pool precision.",
        "lift_definition": "Primary commission metric: equal-date-weighted mean of (frozen decile mean excess_cc minus the same original eligible pool mean excess_cc), in percentage points.",
        "additional_precision_lift_definition": "Ratio of the two date-weighted precisions, plus their percentage-point difference; not the mean of per-date ratios.",
        "return_lift_bootstrap": {
            "seed": DATE_BOOTSTRAP_SEED, "replicates": DATE_BOOTSTRAP_REPLICATES,
            "resampling_unit": "One entire date, retaining the paired selected-minus-pool difference; sample ten dates with replacement for each replicate.",
            "shared_resamples_across_arms": True, "interval": "2.5th and 97.5th percentiles with linear interpolation",
            "rng": "Python standard-library random.Random(seed).choices; one shared sequence of date-index resamples.",
            "interpretation": "Descriptive paired date-cluster interval. Does not fully correct serially overlapping holding periods or repeated issuers; not adjusted for five-arm multiplicity.",
        },
        "candidate_dates": dates, "complete_dates": [r["date"] for r in decile_complete],
        "excluded_dates": [r["date"] for r in decile_attempts if not r["admissible"]],
        "pool_summary": pool_summary, "arms": decile_summaries, "daily": decile_attempts,
    }
    return {
        "schema": "cn-prophet-rank-metrics-addendum/v2", "source_sha": SOURCE_SHA,
        "input_sha256": INPUT_HASHES, "script_sha256": script_hash,
        "archive_source_csv": pool_input["source_csv"], "archive_manifest": pool_input["source_manifest"],
        "archive_extraction": pool_input["extraction"],
        "scope": {"definition": "cn_prophet_v4", "horizon": 10, "pool_scope": SCOPE, "feature_columns": FEATURES,
                  "hit_rule": "excess_cc > 0 strictly, on existing current-vintage H10 matched close/close outcomes",
                  "benchmark": "CSI300 ETF proxy 510300.SS", "regraded_prices": False},
        "common_dates": dates, "precision_at_6": precision_rows, "accepted_daily_reconstruction": daily,
        "all_qualified_date_gates": date_audit, "gate_date_counts": dict(Counter(r["gate"] for r in date_audit)),
        "existing_vintage_exclusion_dates": sorted(discordant),
        "vintage_exclusion_dates_without_qualified_input_rows": sorted(discordant - set(by_date)),
        "intended_intel_tiebreak_top6": intended, "frozen_top_decile": decile,
        "source_selection_changed_examples": [r for r in evidence["selection_changed_examples"] if relevant(r, "definition")],
        "limits": evidence["methodology"]["limitations"] + [
            "All results are conditional on the accepted feature-complete cohort and completeness gates. No new point-in-time proof is provided.",
            "Top-six has a sector cap of four; top-decile deliberately has no sector cap. These are separately labeled ranking diagnostics, not an optimization.",
            "Selected name/date observations can overlap or repeat issuers; they are not independent trades. No net costs, portfolio weights, 24-name board performance, or executable alpha are claimed.",
            "New return-lift intervals use paired date resampling with fixed seed20261009 and10,000 shared replicates; they do not fully correct serial dependence and are not multiplicity-adjusted.",
        ],
        "verification": {
            "accepted_input_hashes_match": True, "archive_manifest_hash_chain_matches": True,
            "all_55_original_arm_date_memberships_recomputed_from_frozen_features": True,
            "all_55_original_arm_date_counts_precision_and_mean_returns_match": True,
            "all_5_summary_precision_and_mean_excess_values_match": True,
            "all_10_complete_pool_precision_and_mean_excess_values_match": True,
            "all_date_maturity_missingness_and_vintage_gates_retained": True,
            "outcome_recalculation": False, "accepted_original_files_modified": False,
        },
    }


def render(result):
    precision_table = "\n".join(
        f"| {r['label']} | {r['positive_excess_n']}/{r['n_selected_observations']} | {100*r['date_weighted_precision']:.4f}% | {r['n_dates']} | 6 |"
        for r in result["precision_at_6"]
    )
    daily_table = "\n".join(
        f"| {r['date']} | {r['pool_observed_n']}/{r['pool_n']} | {r['decile_k']} | "
        + " | ".join(str(r["arms"][name]["positive_excess_n"]) for name, _, _ in ARMS) + " |"
        for r in result["accepted_daily_reconstruction"]
    )
    decile = result["frozen_top_decile"]
    pool = decile["pool_summary"]
    decile_table = "\n".join(
        f"| {r['label']} | {r['positive_excess_n']}/{r['n_selected_observations']} | {100*r['date_weighted_precision']:.4f}% | {r['precision_lift_pp']:+.4f} pp | {r['precision_lift_ratio']:.4f}× |"
        for r in decile["arms"]
    )
    return_lift_table = "\n".join(
        f"| {r['label']} | {r['date_weighted_mean_excess_cc_pp']:+.4f} pp | {pool['date_weighted_mean_excess_cc_pp']:+.4f} pp | {r['mean_excess_lift_pp']:+.4f} pp | [{r['mean_excess_lift_paired_datecluster95_pp'][0]:+.4f}, {r['mean_excess_lift_paired_datecluster95_pp'][1]:+.4f}] pp |"
        for r in decile["arms"]
    )
    intended = result["intended_intel_tiebreak_top6"]
    old, new = intended["accepted_stored_intel_on_paired_dates"], intended["intended_intel_on_paired_dates"]
    changed_rows = []
    for r in intended["daily"]:
        if r["order_changed"]:
            changed_rows.append(
                f"| {r['date']} | {', '.join(r['old_only']) or 'None; order only'} | {', '.join(r['new_only']) or 'None; order only'} | "
                + (f"{r['old_metrics']['positive_excess_n']} → {r['new_metrics']['positive_excess_n']} | {r['mean_excess_delta_pp']:+.4f} pp |" if r['paired_complete'] else "Unresolved | Unavailable |")
            )
    changed_table = "\n".join(changed_rows) or "| No changed dates | — | — | — | — |"
    gate_table = "\n".join(f"| `{gate}` | {n} |" for gate, n in sorted(result["gate_date_counts"].items()))
    hash_table = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in result["input_sha256"].items())
    dates_text = ", ".join(result["common_dates"])
    no_qualified_vintage_dates = ", ".join(result["vintage_exclusion_dates_without_qualified_input_rows"]) or "None"
    new_exclusions = ", ".join(intended["new_excluded_dates"]) or "None"
    return f"""# Ranking metrics addendum

## Finding

**The accepted five-arm comparison has precision@6 of 42.4242% for score, 43.9394% for stored intel, 50.0000% for momentum, 50.0000% for reversal, and 46.9697% for quality.** These are 28, 29, 33, 33 and 31 positive H10 excess outcomes, respectively, from 66 selected observations per arm over the same 11 dates.

The existing analytical candidate archive was sufficient to complete the requested **frozen top-decile lift** and the **single intended intel tie-break check** without recalculating prices or outcomes. All 55 original arm/date counts, precisions and mean returns were first reproduced from the original frozen features. The accepted historical files remain unchanged. This addendum adds separate conditional ranking diagnostics; it does not change the original performance definitions or establish executable alpha.

## Source, selection rules and precision definition

All data remain pinned to Macro `{SOURCE_SHA}`. The additional input is a lossless subset of the existing `eligible_candidate_horizon_returns.csv`: `cn_prophet_v4`, horizon 10, and recorded featured candidates plus more-actionable candidates whose sole exclusion reason is `featured_cap` or `sector_cap`. Extraction retained missing features and all outcome statuses. It contains **1,488 qualified rows over 29 dates: 949 observed, 537 immature and two missing-exact-session outcomes**. The full source CSV has 30,582 rows; its V4 H10 slice has 2,917 rows. Extraction details and the original manifest are embedded in `rank_metrics_pool_input.json`.

The comparison then preserves the accepted `{SCOPE}` pool: all of `prophet_score`, `intel_score`, `ret_3m` and `quality_z` must be present, and the existing board/candidate vintage exclusions remain. This is a cap-qualified common-feature cohort, not the entire raw-eligible universe. Membership is sorted using frozen features and ticker before inspecting outcome status. Unknown outcomes never trigger replacement.

A hit means **strictly positive `excess_cc`** under the unchanged diagnostic: entry is the first benchmark-session close after the recorded board date, and exit is ten benchmark sessions later, with identical dates for stock and **CSI300 ETF proxy `510300.SS`**. This current-vintage close/close outcome differs from the separately reconciled production H10 open/HL2 and latched-fill conventions.

The original six-name arms use a maximum of four names per sector. Their primary orders are score descending, intel descending, three-month momentum descending, three-month reversal ascending, and quality descending; each uses ticker ascending for ties. The separate intended intel arm adds v3 score descending ahead of ticker. Top-decile selections use the same five original feature orders with **no sector cap**, as explicitly specified below.

## Accepted precision@6, independently reaggregated

Each date contributes equally to precision. Because every original selection has six names, mean daily precision also equals total positive outcomes divided by 66. The source field `average_precision` is a mean of daily precision@6; it is not average precision over a retrieval curve.

| Accepted arm | Positive H10 excess outcomes | Precision@6 | Same dates | K per date |
|---|---:|---:|---:|---:|
{precision_table}

All five arms use these dates: {dates_text}. Sources are `v4_review_rows.json` → `baseline_dates`, `historical_evidence.json` → `autopsy.baseline_comparison`, and the independently reconstructed memberships in `rank_metrics_addendum.json` → `accepted_daily_reconstruction`.

Every arm-count cell below is hits out of six. Pool counts include unobserved original members; decile K is fixed from that original pool size before outcomes.

| Date | Observed pool / original pool | Decile K | Score hits | Stored-intel hits | Momentum hits | Reversal hits | Quality hits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{daily_table}

## Frozen top-decile excess-return lift on identical complete pools

**K = ceil(0.1 × original common-feature pool size)**, with ticker ascending as the final tie-break and **no sector cap**. Selection is frozen before joining outcomes. Every reported arm uses exactly the same **{pool['n_dates']} dates**, and both the entire original pool and every frozen selected name have observed outcomes on those dates. K ranges from two to five, yielding **35 selected name/date observations per arm** and **{pool['n_selected_observations']} full-pool name/date observations**. Six-name results are not relabeled as decile results.

The commission's primary **top-decile lift** is the equal-date-weighted mean of **decile mean excess minus the mean excess of the same full eligible pool**. Both sides use identical dates and the original unchanged H10 outcomes. Full-pool mean excess is **{pool['date_weighted_mean_excess_cc_pp']:+.4f} pp**. The selected and full-pool means below use equal date weights; their difference equals the mean of the paired daily differences.

| Frozen ordering | Decile mean gross excess | Same-pool mean gross excess | Mean excess lift | Descriptive paired date-cluster 95% interval for lift |
|---|---:|---:|---:|---:|
{return_lift_table}

The intervals use **10,000 bootstrap resamples of the ten dates, with replacement, seed 20261009**. Each draw retains the complete selected-minus-pool date pair, and the same date-index draws are used for all five arms. Endpoints are the 2.5th and 97.5th percentiles with linear interpolation. These are **descriptive paired date-cluster intervals**: resampling individual dates does not fully address serially overlapping holding periods or recurring issuers, and the intervals are **not adjusted for the five-arm comparison**. They do not constitute a promotion or net-alpha test.

### Additional precision lift

Full-pool precision, weighted equally by date, is **{100*pool['date_weighted_precision']:.4f}%**. This supplementary precision-lift ratio divides selected precision by full-pool precision; the adjacent column gives their percentage-point difference. It is distinct from the commission's mean-excess lift above. Because decile K varies, the positive-count fraction is a pooled count and can differ from the reported date-weighted precision.

| Frozen ordering | Positive outcomes / selected observations | Date-weighted top-decile precision | Difference from same pool | Precision lift ratio |
|---|---:|---:|---:|---:|
{decile_table}

The ten complete-pool dates are the accepted 11-date set with **2026-09-01 excluded**. That date has 45/46 common-feature pool outcomes; `601059.SS` is `missing_exact_session`. Its five top-six selections are complete, which is why it remains in precision@6, but it cannot supply a complete-pool comparison. The already excluded **2026-08-31** remains excluded: its original score top-six contains unresolved `601059.SS`. The rejected outcome-first method would have substituted `601360.SS`. No such substitution occurs here.

Per-date original pool sizes, frozen decile memberships, unresolved rows, and outcomes are stored under `frozen_top_decile.daily`; each arm summary also contains its ten paired return-lift observations and interval. The stored-intel decile retains the original ticker-only tie-break; the intended intel policy is assessed only in the single separately labeled top-six check below. No additional feature or parameter search was performed.

## Intended intel tie-break: one separate completeness check

Integrated source review clarifies the intended ordering as **intel descending, v3 score (`prophet_score`) descending, then ticker ascending**. The accepted stored-intel baseline uses **intel descending, then ticker ascending**. They must remain distinct labels.

Applying the intended tie-break to the same original common-feature pools changes membership on **{len(intended['membership_changed_dates'])} of 11 dates**, replacing **{intended['replacement_slots']} selected name/date slots**; the ordered six-name list changes on **{len(intended['order_changed_dates'])} dates**. Both versions keep K=6 and the sector cap of four. There are **{len(intended['paired_dates'])} paired complete dates**. Newly excluded dates: **{new_exclusions}**.

| Ordering on paired complete dates | Positive outcomes | Date-weighted precision@6 | Mean gross H10 excess |
|---|---:|---:|---:|
| Accepted stored intel → ticker | {old['positive_excess_n']}/{old['n_selected_observations']} | {100*old['date_weighted_precision']:.4f}% | {old['date_weighted_mean_excess_cc_pp']:+.4f} pp |
| Intended intel → v3 score → ticker | {new['positive_excess_n']}/{new['n_selected_observations']} | {100*new['date_weighted_precision']:.4f}% | {new['date_weighted_mean_excess_cc_pp']:+.4f} pp |

The paired change is **{intended['precision_delta_pp']:+.4f} percentage points in precision**, and **{intended['mean_excess_delta_pp']:+.4f} pp in mean gross excess**. These are deterministic effects within this frozen historical cohort; they do not establish an expected future advantage or net trading return.

| Changed date | Removed from accepted selection | Added by intended tie-break | Positive outcomes, old → new | Mean excess change |
|---|---|---|---:|---:|
{changed_table}

The full original and intended ticker orders, selected outcome receipts, and exclusion checks appear under `intended_intel_tiebreak_top6.daily`. This comparison neither rewrites the accepted stored-intel history nor claims to reconstruct the actual 24-name published board.

## Preserved cohort gates and limitations

The 29-date input is classified below using the existing vintage, common-feature, maturity and frozen-selection rules. Original rows are retained in the input even when their dates cannot enter a comparison. Full per-date counts, missing features and unresolved memberships are in `all_qualified_date_gates`.

| Gate | Qualified input dates |
|---|---:|
{gate_table}

The existing evidence quarantines five vintage-discordant dates. Only four appear among these 29 qualified input dates; the already quarantined date with no qualified input rows is **{no_qualified_vintage_dates}**. The source quarantine is preserved in full, rather than inferred from only the dates present in the subset.

These statistics use current adjusted-price outcomes and date-only candidate records. Original publication-time snapshots and original price vintages have not been recovered; intraday execution, suspensions and terminal outcomes remain incompletely certified. Date and issuer overlap mean selected observations are not independent trades. Top-six and top-decile are separate ranking diagnostics with explicitly different K/cap rules. There is no portfolio weighting, financing, transaction-cost model, executable fill proof, accepted point-in-time backtest, net-alpha claim, or recommendation to promote an ordering. Small conditional-cohort differences do not alter the accepted report's conclusion about the lack of a demonstrated stable ranking advantage.

## Reproduction and hashes

Run the standard-library script beside its three pinned JSON inputs:

```bash
python3 rank_metrics_addendum.py
```

It verifies input hashes and the archive manifest chain, reconstructs all 55 original arm/date metrics and ten full-pool controls, then computes only the five prespecified top-decile arms, their fixed paired date-bootstrap intervals, and the single intended intel tie-break. It never reads prices or reruns the original grader. It writes only `rank_metrics_addendum.json` and this addendum. Accepted inputs are checked again after output generation.

| Input | SHA256 |
|---|---|
{hash_table}

Original existing analytical CSV SHA256: `{CSV_HASH}`. Original results manifest SHA256: `{MANIFEST_HASH}`. Addendum script SHA256: `{result['script_sha256']}`. The extraction predicate, original CSV strings, source file sizes, full original manifest and all selection receipts make the new calculation reproducible without another host or vendor query. The accepted `HISTORICAL_EVALUATION.md`, `historical_evidence.json`, `v4_review_rows.json`, `autopsy.py` and `extend_audit.py` were not modified.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    directory = args.directory.resolve()
    review, evidence, pool = load_inputs(directory)
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = analyze(review, evidence, pool, script_hash)
    outputs = {
        "rank_metrics_addendum.json": json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        "RANK_METRICS_ADDENDUM.md": render(result),
    }
    for name, content in outputs.items():
        (directory / name).write_text(content, encoding="utf-8")
    load_inputs(directory)
    print(json.dumps({
        "status": "verified", "precision_at_6": result["precision_at_6"],
        "top_decile_pool": result["frozen_top_decile"]["pool_summary"],
        "top_decile_arms": result["frozen_top_decile"]["arms"],
        "intended_intel": {k: v for k, v in result["intended_intel_tiebreak_top6"].items() if k != "daily"},
        "gate_date_counts": result["gate_date_counts"],
        "output_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in outputs},
        "script_sha256": script_hash,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
