"""Strict display projection of the existing registered entry/regime experiment.

This is not a predictor, grader, ranking gate or publication owner. The Technical
Lab receives only allowlisted aggregates bound to the existing spec and arithmetic
receipt. Missing/corrupt evidence never becomes a sample result or zero outcome.
"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = Path("research/prophet_fusion/entry_regime_2026_11_14")
SPEC_PATH = Path("research/prophet_fusion/entry_regime_v1_spec.json")
MAX_FILE_BYTES = 512_000
COHORT_DIR = Path("research/prophet_fusion/prophet_screen_2026_11_14")
# Accepted immutable artifacts, not merely mutually consistent caller digests.
TRUSTED_SHA256 = {
    SPEC_PATH.as_posix(): "1f02b90917f69653b7659fc0b1883b6a7256224585ac22e1604293a8809b0a72",
    (STUDY_DIR / "report.json").as_posix(): "cc1f9a1df0efb76e3d769ce9b76ece1b1130bd36d6939e768425b9fc2e3b7567",
    (STUDY_DIR / "verification.json").as_posix(): "f841a2bc4253ffd0896f9ba232373d7b5755b24364cec01ac0200d466faa80a1",
    (STUDY_DIR / "timing_attribution.json").as_posix(): "de82ac5cdd185900b9ae7d4908657886a3b2191f4d072db979de16bbe204ce4f",
    (COHORT_DIR / "context_report.json").as_posix(): "c87dad6e7fd62c5771ea995b8f74981fa4bdbbf5978d0c9ef4101e939845e634",
    (COHORT_DIR / "metadata_receipt.json").as_posix(): "2e486b65dfe5d6d10625cb0c88d3db4b9cc5e350c26cbbe4893916fb30cb1786",
}

TRIGGERS = {
    "technical_core_t12": ("Technical T1/T2 core", "T1/T2 technical core", "T1/T2 \u6280\u672f\u6838\u5fc3"),
    "trend_126_20_50": ("Trend-state onset", "Trend-state onset", "\u8d8b\u52bf\u72b6\u6001\u521d\u73b0"),
    "breakout_63": ("Prior-high breakout", "Prior-high breakout", "\u7a81\u7834\u524d\u9ad8"),
    "pullback_reclaim_20": ("Pullback and reclaim", "Pullback and reclaim", "\u56de\u8c03\u540e\u91cd\u65b0\u7ad9\u4e0a"),
}
CONTEXTS = {
    "unfiltered": ("No regime filter", "\u65e0\u72b6\u6001\u7b5b\u9009"),
    "market_uptrend": ("Market uptrend", "\u5e02\u573a\u4e0a\u884c\u8d8b\u52bf"),
    "no_volatility_stress": ("No volatility stress", "\u65e0\u6ce2\u52a8\u538b\u529b"),
}
ARM_IDS = {f"{t}__{c}" for t in TRIGGERS for c in CONTEXTS}


class EvidenceRefusal(ValueError):
    """A display refusal is not a negative investment signal."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise EvidenceRefusal(code)


def _read(root: Path, relative: Path) -> tuple[bytes, dict]:
    path = (root / relative).resolve(strict=True)
    _require(path.is_relative_to(root.resolve()), "SOURCE_PATH_ESCAPE")
    _require(path.is_file() and 0 < path.stat().st_size <= MAX_FILE_BYTES, "SOURCE_SIZE_CONTRACT")
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE_BYTES + 1)
    _require(0 < len(raw) <= MAX_FILE_BYTES, "SOURCE_SIZE_CONTRACT")
    _require(_digest(raw) == TRUSTED_SHA256.get(relative.as_posix()), "UNPINNED_EVIDENCE")
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    # Reject nonstandard values and duplicate keys, not merely malformed JSON.
    value = json.loads(raw, object_pairs_hook=object_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(EvidenceRefusal("NONFINITE_JSON")))
    _require(isinstance(value, dict), "SOURCE_OBJECT_REQUIRED")
    return raw, value


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _number(value: Any, code: str, *, unknown: bool = False, rate: bool = False) -> float | None:
    if value is None and unknown:
        return None
    _require(type(value) in (int, float) and math.isfinite(value), code)
    if rate:
        _require(0 <= value <= 1, code)
    return float(value)


def _count(value: Any, code: str) -> int:
    _require(type(value) is int and value >= 0, code)
    return value


def _interval(value: Any, code: str) -> list[float] | None:
    if value is None:
        return None
    _require(isinstance(value, list) and len(value) == 2, code)
    lo, hi = (_number(x, code) for x in value)
    _require(lo <= hi, code)
    return [lo, hi]


def _arm_labels(arm: str) -> dict[str, str]:
    _require(arm in ARM_IDS, "UNREGISTERED_ARM")
    trigger, context = arm.split("__")
    return {"id": arm, "trigger": trigger, "context": context,
            "label_en": TRIGGERS[trigger][1], "label_zh": TRIGGERS[trigger][2],
            "context_en": CONTEXTS[context][0], "context_zh": CONTEXTS[context][1]}


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)


def _project(spec_raw: bytes, spec: dict, report_raw: bytes, report: dict, receipt: dict) -> dict:
    _require(spec.get("schema") == "prophet.entry_regime_mechanism_spec/v1", "SPEC_SCHEMA")
    _require(report.get("schema") == "prophet.entry_regime_mechanism_report/v1", "REPORT_SCHEMA")
    _require(receipt.get("schema") == "prophet.entry_regime_arithmetic_verification/v1", "RECEIPT_SCHEMA")
    _require(report.get("status") == "RETROSPECTIVE_MECHANISM_PILOT_NOT_PROMOTION_BEARING", "REPORT_STATUS")
    _require(receipt.get("status") == "PASS_WITH_DECLARED_SCOPE", "RECEIPT_STATUS")
    _require(spec.get("promotion_eligible") is False and report.get("promotion_eligible") is False
             and receipt.get("promotion_eligible") is False, "RESEARCH_AUTHORITY_CONTRACT")
    report_sha, spec_sha = _digest(report_raw), _digest(spec_raw)
    _require(receipt.get("report_sha256") == report_sha, "REPORT_RECEIPT_DIGEST")
    _require(report.get("spec_sha256") == spec_sha == receipt.get("spec_sha256"), "SPEC_DIGEST")
    source = spec.get("source_base", "")
    _require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source) is not None, "SOURCE_COMMIT")
    native = receipt.get("native_source", {})
    _require(isinstance(native, dict), "NATIVE_RECEIPT_OBJECT")
    _require(report.get("source_base") == source == native.get("source_base")
             and native.get("native_source_matches_spec") is True, "SOURCE_BINDING")
    _require(spec.get("survivorship_biased") is True and report.get("survivorship_biased") is True,
             "POPULATION_LIMITATION_REQUIRED")
    _require(spec.get("fill_basis") == report.get("fill_basis") == "next_session_close", "FILL_BASIS")
    _require(spec.get("primary_horizon") == 21 and spec.get("secondary_horizon") == 63, "HORIZON_CONTRACT")
    _require(spec.get("triggers") == list(TRIGGERS) and spec.get("contexts") == list(CONTEXTS), "REGISTERED_MECHANISMS")
    _require(spec.get("primary_metric") == report.get("primary_metric")
             == "equal_decision_date_mean_net_excess_vs_same_window_SPY", "PRIMARY_METRIC")
    cost = _number(spec.get("primary_round_trip_cost_bps"), "COST_BASIS")
    _require(cost == report.get("primary_round_trip_cost_bps") and 0 <= cost < 10000, "COST_BASIS")
    window = report.get("window")
    _require(isinstance(window, list) and len(window) == 2 and window == [spec.get("start"), spec.get("end")],
             "WINDOW_CONTRACT")
    _require(date.fromisoformat(window[0]) < date.fromisoformat(window[1]), "WINDOW_ORDER")
    generated = report.get("generated_at")
    _require(isinstance(generated, str), "REPORT_CLOCK")
    generated_date = datetime.fromisoformat(generated.replace("Z", "+00:00")).date().isoformat()
    names = spec.get("universe")
    _require(isinstance(names, list) and len(names) == len(set(names)) and 0 < len(names) <= 100
             and all(isinstance(n, str) and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", n) for n in names),
             "UNIVERSE_CONTRACT")
    summaries = report.get("arm_summaries")
    _require(isinstance(summaries, list) and len(summaries) == 24, "SUMMARY_CENSUS")
    index: dict[tuple[str, int], dict] = {}
    groups = {21: [], 63: []}
    for summary in summaries:
        _require(isinstance(summary, dict), "SUMMARY_OBJECT")
        arm, horizon = summary.get("arm"), summary.get("horizon")
        _require(arm in ARM_IDS and type(horizon) is int and horizon in (21, 63), "SUMMARY_IDENTITY")
        _require((arm, horizon) not in index, "DUPLICATE_SUMMARY")
        _require(summary.get("promotion_eligible") is False, "SUMMARY_AUTHORITY")
        events = _count(summary.get("events"), "EVENT_COUNT")
        dates = _count(summary.get("decision_dates"), "DATE_COUNT")
        episodes = _count(summary.get("nonoverlapping_name_episodes"), "EPISODE_COUNT")
        _require(dates <= events and episodes <= events, "DEPENDENCE_COUNT_CONTRACT")
        row = {**_arm_labels(arm), "horizon": horizon, "events": events, "dates": dates,
               "episodes": episodes,
               "net_return": _number(summary.get("net_return"), "NET_RETURN", unknown=True),
               "net_excess": _number(summary.get("net_excess"), "NET_EXCESS", unknown=True),
               "positive_net_rate": _number(summary.get("net_positive_rate_date_weighted"), "NET_POSITIVE_RATE", unknown=True, rate=True),
               "retention": _number(summary.get("signal_retention"), "RETENTION", unknown=True, rate=True),
               "winner_retention": _number(summary.get("winner_retention"), "WINNER_RETENTION", unknown=True, rate=True)}
        if not events:
            _require(row["net_return"] is None and row["net_excess"] is None and row["positive_net_rate"] is None,
                     "EMPTY_ARM_IS_UNKNOWN")
        else:
            _require(all(row[k] is not None for k in ["net_return", "net_excess", "positive_net_rate", "retention"]),
                     "OBSERVED_ARM_METRIC_MISSING")
        index[(arm, horizon)] = row
        groups[horizon].append(row)
    _require(set(index) == {(a, h) for a in ARM_IDS for h in (21, 63)}, "COMPLETE_SUMMARY_GRID")
    order = {f"{t}__{c}": i for i, (t, c) in enumerate((t, c) for t in TRIGGERS for c in CONTEXTS)}
    for rows in groups.values():
        rows.sort(key=lambda x: order[x["id"]])
        for row in rows:
            base = index[(f"{row['trigger']}__unfiltered", row["horizon"])]
            expected_retention = row["events"] / base["events"] if base["events"] else None
            _require(row["events"] <= base["events"] and row["dates"] <= base["dates"]
                     and _close(row["retention"], expected_retention), "RETENTION_CENSUS")
    declared = spec.get("primary_comparisons")
    count = _count(spec.get("integer_primary_comparison_count"), "COMPARISON_BUDGET")
    _require(isinstance(declared, list) and len(declared) == count == 11
             and all(isinstance(x, list) and len(x) == 2 and all(a in ARM_IDS for a in x) for x in declared),
             "COMPARISON_BUDGET")
    _require(report.get("integer_primary_comparison_count") == count, "REPORT_COMPARISON_BUDGET")
    comparisons = report.get("primary_comparisons")
    _require(isinstance(comparisons, list) and len(comparisons) == count, "CONTRAST_CENSUS")
    seen, contrast_rows = set(), []
    for comparison in comparisons:
        _require(isinstance(comparison, dict), "CONTRAST_OBJECT")
        pair = (comparison.get("left"), comparison.get("right"))
        _require(pair in {tuple(x) for x in declared} and pair not in seen, "CONTRAST_IDENTITY")
        _require(comparison.get("promotion_eligible") is False and comparison.get("horizon") == 21,
                 "CONTRAST_AUTHORITY_OR_HORIZON")
        seen.add(pair)
        a, b = index[(pair[0], 21)], index[(pair[1], 21)]
        expected = a["net_excess"] - b["net_excess"] if a["net_excess"] is not None and b["net_excess"] is not None else None
        delta = _number(comparison.get("delta"), "CONTRAST_DELTA", unknown=True)
        _require(_close(delta, expected), "CONTRAST_ARITHMETIC")
        family = _interval(comparison.get("familywise_ci"), "ADJUSTED_INTERVAL")
        unadjusted = _interval(comparison.get("ci95"), "UNADJUSTED_INTERVAL")
        floor = comparison.get("honest_n_floor_met")
        _require(type(floor) is bool, "SAMPLE_FLOOR_TYPE")
        contrast_rows.append({"left": _arm_labels(pair[0]), "right": _arm_labels(pair[1]),
                              "delta": delta, "adjusted_ci": family, "unadjusted_ci": unadjusted,
                              "sample_floor_met": floor,
                              "interval_excludes_zero": family is not None and (family[0] > 0 or family[1] < 0)})
    strata = report.get("technical_core_strata_descriptive", [])
    _require(isinstance(strata, list), "PROVISIONAL_STRATA")
    provisional_count, strata_count = 0, 0
    for row in strata:
        _require(isinstance(row, dict), "PROVISIONAL_STRATUM_OBJECT")
        _require(row.get("tier") in ("T1", "T2") and type(row.get("provisional")) is bool,
                 "PROVISIONAL_STRATUM_IDENTITY")
        n = _count(row.get("events"), "PROVISIONAL_COUNT")
        strata_count += n
        if row["provisional"]:
            provisional_count += n
    base_events = index[("technical_core_t12__unfiltered", 21)]["events"]
    _require(strata_count == base_events, "PROVISIONAL_CENSUS")
    row_proof = receipt.get("row_verification")
    summary_proof = receipt.get("summary_verification")
    _require(isinstance(row_proof, dict) and isinstance(summary_proof, dict), "VERIFICATION_OBJECTS")
    _require(row_proof.get("all_price_fill_cost_and_context_checks") is True
             and summary_proof.get("arm_summaries_verified") == 24
             and summary_proof.get("contrast_point_estimates_verified") == 11, "VERIFICATION_SCOPE")
    verified_rows = _count(row_proof.get("events_verified"), "VERIFIED_ROW_COUNT")
    unique_events = sum(index[(f"{t}__unfiltered", 21)]["events"] for t in TRIGGERS)
    _require(verified_rows == sum(index[(f"{t}__unfiltered", h)]["events"] for t in TRIGGERS for h in (21, 63)),
             "VERIFIED_EVENT_CENSUS")
    return {"available": True, "state": "research_evidence", "reason_code": None,
            "promotion_eligible": False, "generated_date": generated_date,
            "source_commit": source, "report_sha256": report_sha, "spec_sha256": spec_sha,
            "window_start": window[0], "window_end": window[1], "universe": names,
            "universe_count": len(names), "unique_events": unique_events, "verified_rows": verified_rows,
            "primary_horizon": 21, "secondary_horizon": 63, "cost_bps": cost,
            "arm_count": 12, "comparison_count": count, "rows_by_horizon": groups,
            "comparisons": contrast_rows,
            "adjusted_intervals_excluding_zero": sum(x["interval_excludes_zero"] for x in contrast_rows),
            "t12_events": base_events, "t12_provisional_events": provisional_count,
            "auxiliary_available": False, "auxiliary_rows": [], "auxiliary_reason_code": None}


def _auxiliary(root: Path, payload: dict) -> None:
    _, auxiliary = _read(root, STUDY_DIR / "timing_attribution.json")
    _require(auxiliary.get("schema") == "prophet.entry_timing_attribution/v1"
             and auxiliary.get("status") == "AUXILIARY_DESCRIPTIVE_ONLY", "AUXILIARY_SCHEMA")
    _require(auxiliary.get("primary_report_sha256") == payload["report_sha256"]
             and auxiliary.get("spec_sha256") == payload["spec_sha256"], "AUXILIARY_BINDING")
    _require(auxiliary.get("promotion_eligible") is False and auxiliary.get("primary_protocol_unchanged") is True
             and auxiliary.get("statistical_inference") is None, "AUXILIARY_AUTHORITY")
    summaries = auxiliary.get("summaries")
    _require(isinstance(summaries, list) and len(summaries) == 24, "AUXILIARY_CENSUS")
    seen, rows = set(), []
    for row in summaries:
        _require(isinstance(row, dict), "AUXILIARY_ROW_OBJECT")
        arm, horizon = row.get("arm"), row.get("horizon")
        _require(arm in ARM_IDS and horizon in (21, 63) and (arm, horizon) not in seen, "AUXILIARY_IDENTITY")
        seen.add((arm, horizon))
        _require(row.get("promotion_eligible") is False, "AUXILIARY_ROW_AUTHORITY")
        if horizon != 21 or not arm.endswith("__unfiltered"):
            continue
        event = _number(row.get("event_net_excess"), "AUXILIARY_EVENT", unknown=True)
        control = _number(row.get("same_asset_month_control_net_excess"), "AUXILIARY_CONTROL", unknown=True)
        residual = _number(row.get("timing_residual_net_excess"), "AUXILIARY_RESIDUAL", unknown=True)
        _require(_close(residual, event - control if event is not None and control is not None else None),
                 "AUXILIARY_ARITHMETIC")
        primary = next(x for x in payload["rows_by_horizon"][21] if x["id"] == arm)
        _require(_close(event, primary["net_excess"]), "AUXILIARY_PRIMARY_VALUE")
        rows.append({**_arm_labels(arm), "event_excess": event, "control_excess": control,
                     "timing_residual": residual})
    _require(len(rows) == 4 and seen == {(arm, h) for arm in ARM_IDS for h in (21, 63)},
             "AUXILIARY_UNFILTERED_CENSUS")
    rows.sort(key=lambda x: list(TRIGGERS).index(x["trigger"]))
    payload.update(auxiliary_available=True, auxiliary_rows=rows)


DIRECTIONS = [
    ("BOTH_FALLING", "Both falling", "两者下降"),
    ("BOTH_RISING", "Both rising", "两者上升"),
    ("VIX_FALLING_VVIX_RISING", "VIX falling · VVIX rising", "VIX下降 · VVIX上升"),
    ("VIX_RISING_VVIX_FALLING", "VIX rising · VVIX falling", "VIX上升 · VVIX下降"),
    ("FLAT_OR_MIXED", "Flat or mixed", "持平或混合"),
    ("UNAVAILABLE", "Context unavailable", "背景数据不可用"),
]
JOIN_STATES = {"JOINED_DATE_PROXY_ONLY", "CONTEXT_WINDOW_INCOMPLETE",
               "DECLARED_DATE_UNAVAILABLE", "INVALID_DECLARED_SESSION",
               "CONTEXT_SESSION_UNAVAILABLE"}


def load_cohort_evidence(root: Path = ROOT) -> dict:
    """Only original aggregate coverage; no outcome or event-level source access."""
    try:
        raw, report = _read(root, COHORT_DIR / "context_report.json")
        receipt_raw, receipt = _read(root, COHORT_DIR / "metadata_receipt.json")
        _require(report.get("schema") == "prophet.recovered_screen_context/v1"
                 and receipt.get("schema") == "prophet.recovered_screen_metadata/v1",
                 "COHORT_SCHEMA")
        _require(report.get("authority") == "RESEARCH_DIAGNOSTIC_ONLY"
                 and report.get("promotion_eligible") is False
                 and report.get("registered_experiment_executed") is False
                 and report.get("outcomes_decoded") is False
                 and report.get("holdout_rows_materialized_in_export") is False,
                 "COHORT_AUTHORITY")
        _require(report.get("export_receipt_sha256") == _digest(receipt_raw)
                 and report.get("source_manifest_sha256") == receipt.get("source_manifest_sha256")
                 and report.get("source_counts") == receipt.get("counts"), "COHORT_BINDING")
        counts = report["source_counts"]
        values = {k: _count(counts.get(k), "COHORT_COUNT") for k in
                  ["screen_retained", "primary_analytic", "primary_any", "primary_none", "outside_primary_analytic"]}
        _require(values["primary_any"] + values["primary_none"] == values["primary_analytic"]
                 and values["primary_analytic"] + values["outside_primary_analytic"]
                 == values["screen_retained"], "COHORT_PARTITION")
        def statuses(value, expected):
            _require(isinstance(value, dict) and set(value).issubset(JOIN_STATES), "COHORT_JOIN_STATES")
            result = {key: _count(n, "COHORT_JOIN_COUNT") for key, n in value.items()}
            _require(sum(result.values()) == expected, "COHORT_JOIN_CENSUS")
            return result
        all_status = statuses(report["join_status_counts"], values["screen_retained"])
        statuses(report["primary_join_status_counts"], values["primary_analytic"])
        directions = report["primary_direction_counts"]
        _require(isinstance(directions, dict) and set(directions) == {"ANY", "A4"}, "COHORT_DIRECTION_GROUPS")
        for key, n in [("ANY", values["primary_any"]), ("A4", values["primary_none"])]:
            group = directions[key]
            _require(isinstance(group, dict) and set(group).issubset({x[0] for x in DIRECTIONS}),
                     "COHORT_DIRECTION_STATES")
            _require(sum(_count(v, "COHORT_DIRECTION_COUNT") for v in group.values()) == n,
                     "COHORT_DIRECTION_CENSUS")
        grades = {"survivor-biased": 0, "usable": 0}
        primary_total = 0
        for row in report["source_grade_breakdown"]:
            _require(isinstance(row, dict) and row.get("source_coverage_grade") in grades
                     and type(row.get("primary_analytic")) is bool, "COHORT_GRADE")
            n = _count(row.get("events"), "COHORT_GRADE_COUNT")
            statuses(row["join_status_counts"], n)
            grades[row["source_coverage_grade"]] += n
            primary_total += n if row["primary_analytic"] else 0
        _require(sum(grades.values()) == values["screen_retained"]
                 and primary_total == values["primary_analytic"], "COHORT_GRADE_CENSUS")
        joined = all_status.get("JOINED_DATE_PROXY_ONLY", 0)
        return {"available": True, "promotion_eligible": False, **values,
                "joined": joined, "unavailable": values["screen_retained"] - joined,
                "survivor_biased_events": grades["survivor-biased"], "usable_source_events": grades["usable"],
                "report_sha256": _digest(raw),
                "directions": [{"label_en": en, "label_zh": zh,
                                "any": directions["ANY"].get(key, 0), "none": directions["A4"].get(key, 0)}
                               for key, en, zh in DIRECTIONS]}
    except (EvidenceRefusal, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, EvidenceRefusal) else type(exc).__name__
        return {"available": False, "promotion_eligible": False, "reason_code": reason}


def load_entry_evidence(root: Path = ROOT) -> dict:
    """Fail closed for this panel only; other Technical Lab consumers keep working."""
    cohort = load_cohort_evidence(root)
    try:
        spec_raw, spec = _read(root, SPEC_PATH)
        report_raw, report = _read(root, STUDY_DIR / "report.json")
        _, receipt = _read(root, STUDY_DIR / "verification.json")
        payload = _project(spec_raw, spec, report_raw, report, receipt)
    except (EvidenceRefusal, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        # Do not publish local paths, raw source text or stack traces in the page.
        reason = str(exc) if isinstance(exc, EvidenceRefusal) else type(exc).__name__
        return {"available": False, "state": "evidence_unavailable", "reason_code": reason,
                "promotion_eligible": False, "auxiliary_available": False, "auxiliary_rows": [], "cohort": cohort}
    payload["cohort"] = cohort
    try:
        _auxiliary(root, payload)
    except (EvidenceRefusal, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        payload["auxiliary_reason_code"] = str(exc) if isinstance(exc, EvidenceRefusal) else type(exc).__name__
    return payload
