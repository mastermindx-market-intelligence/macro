"""Offline Forex source diagnostics subordinate to the Tiingo research reader.

Only explicitly labelled diagnostic aggregation is allowed. No correction
selection, calendar admission, publication or watch evaluation occurs here.
Even dense, valid vendor rows yield no eligible
final-4H observations. A timestamp delta is an observation, not proof of lost data.
"""
from __future__ import annotations

import math
import re
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from collectors.tiingo_archive import DEFAULT_ARCHIVE, validate_request
from lib.dataos.tiingo_reader import TiingoView, TiingoViewRefusal, read_research_view

SCHEMA = "mastermind.tiingo.forex_watch_source.v1"
QUALIFICATION_GAPS = (
    "spot_identity_not_admitted",
    "historical_ohlc_basis_unqualified",
    "vendor_timestamp_start_end_unqualified",
    "4h_calendar_and_completeness_unqualified",
    "finalization_and_correction_contract_unqualified",
    "historical_availability_unverified",
    "live_feed_and_freshness_not_admitted",
)
OHLC = ("open", "high", "low", "close")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_ROWS = 20_000
MAX_RECONCILIATION_NATIVE_ROWS = 128
MAX_RECONCILIATION_ROW_REFERENCES = 100_000
MINUTE_NS = 60_000_000_000
INTERVAL_RECONCILIATION_SCHEMA = "mastermind.tiingo.forex_interval_reconciliation.v1"
PRODUCT_USE_APPROVAL_REFERENCE = "Macro PR #9996 comment 6331071428"
INTERVAL_HYPOTHESES = (
    ("start_label_half_open", 0),
    ("end_label_half_open", -240),
    ("end_label_inclusive_minute", -239),
    ("start_label_exclusive_minute", 1),
)


def _clock(value: Any) -> pd.Timestamp | None:
    # Parse only lossless, aware ISO clock forms. pandas can discard comma
    # fractions, excess precision, or nanoseconds in lowercase compact times.
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2}|\d{8})[Tt ]"
        r"(?P<time>\d{2}:\d{2}:\d{2}|\d{6})"
        r"(?P<fraction>\.\d{1,9})?(?P<zone>[Zz]|[+-](?:[01]\d|2[0-3]):?[0-5]\d)",
        value,
    )
    if match is None:
        return None
    day = match["date"].replace("-", "")
    clock = match["time"].replace(":", "")
    zone = match["zone"]
    zone = "+00:00" if zone in ("Z", "z") else zone
    if len(zone) == 5:
        zone = zone[:3] + ":" + zone[3:]
    canonical = (
        f"{day[:4]}-{day[4:6]}-{day[6:]}T"
        f"{clock[:2]}:{clock[2:4]}:{clock[4:]}{match['fraction'] or ''}{zone}"
    )
    try:
        stamp = pd.Timestamp(canonical)
        if pd.isna(stamp) or stamp.tzinfo is None:
            return None
        stamp = stamp.tz_convert("UTC")
        _ = stamp.value  # Require representable nanoseconds; never silently truncate.
        return stamp
    except (ValueError, TypeError, OverflowError):
        return None


def _price_issue(value: Any) -> str | None:
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "boolean"
    if not isinstance(value, (int, float)):
        return "not_numeric"
    try:
        if not math.isfinite(value):
            return "nonfinite"
    except OverflowError:
        return "nonfinite"
    return "nonpositive" if value <= 0 else None


def _evidence_value(value: Any) -> Any:
    # The verified reader already rejects malformed/nonfinite source numbers.
    # Direct pure-function diagnostics still serialize strictly and retain why
    # a value is unusable. Immutable source bytes remain the full raw evidence.
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return {"unusable_source_value": repr(value)[:256], "python_type": type(value).__name__}


def diagnose_forex_view(view: TiingoView, *, expected_pair: str,
                        receipt_id: str) -> dict[str, Any]:
    """Project an already-verified view without granting stronger authority.

    Use read_forex_watch_source at the file boundary. This pure function cannot
    prove bytes on disk; it checks the supplied lineage and preserves all rows.
    """
    if (not isinstance(view, TiingoView) or view.source != "forex-bars"
            or view.purpose != "INSPECTION"
            or view.authority != "RESEARCH_ONLY_VENDOR_SOURCE"
            or view.pit_backtest_eligible is not False
            or view.redistribution_admitted is not False):
        raise TiingoViewRefusal("Forex diagnostics require the inspection-only research reader")
    if (not isinstance(expected_pair, str) or not re.fullmatch(r"[A-Z]{6}", expected_pair)
            or not isinstance(receipt_id, str) or not SHA.fullmatch(receipt_id)
            or not isinstance(view.source_sha256, str) or not SHA.fullmatch(view.source_sha256)
            or _clock(view.source_observed_at_utc) is None):
        raise TiingoViewRefusal("Forex diagnostics require exact pair, receipt and capture context")
    validate_request("forex-bars", expected_pair.lower(), view.source_request_path)
    if len(view.rows) > MAX_ROWS:
        raise TiingoViewRefusal("Forex diagnostic row cap exceeded; no silent truncation")
    candidates, clocks, by_instant = [], [], defaultdict(list)
    issue_counts: Counter[str] = Counter()
    frequencies = set()
    reasons = set(QUALIFICATION_GAPS)
    for ordinal, row in enumerate(view.rows):
        if (not isinstance(row, dict)
                or row.get("ticker_vendor") != expected_pair.lower()
                or row.get("source_receipt_id") != receipt_id
                or row.get("source_sha256") != view.source_sha256
                or row.get("source_observed_at_utc") != view.source_observed_at_utc
                or row.get("source_vendor") != "tiingo"
                or row.get("dataset_source") != "forex-bars"
                or any(row.get(k) is not False for k in (
                    "source_rights_admitted", "dataos_identity_admitted",
                    "pit_backtest_eligible", "canonical_price_basis_admitted"))):
            raise TiingoViewRefusal("Forex diagnostic row identity or lineage mismatch")
        prices = {key: row.get("vendor_" + key) for key in OHLC}
        issues = {key: issue for key, value in prices.items() if (issue := _price_issue(value))}
        for issue in issues.values():
            issue_counts[issue] += 1
        if not issues and not prices["low"] <= min(prices["open"], prices["close"]) <= max(prices["open"], prices["close"]) <= prices["high"]:
            issues["ohlc_bounds"] = "inconsistent"
            issue_counts["inconsistent_bounds"] += 1
        stamp = _clock(row.get("bar_at_vendor"))
        if stamp is None:
            issues["vendor_timestamp"] = "invalid_or_naive"
            issue_counts["invalid_timestamp"] += 1
        else:
            clocks.append(stamp.value)
            if stamp.second or stamp.microsecond or stamp.nanosecond:
                issue_counts["subminute_timestamp"] += 1
            # Every original row remains in candidates. This grouping only
            # diagnoses repeated instants; it never selects a correction winner.
            by_instant[stamp.value].append(tuple(
                prices[k] if _price_issue(prices[k]) is None else ("invalid", repr(prices[k]))
                for k in OHLC))
        frequency = row.get("requested_resample_frequency")
        frequencies.add(str(frequency))
        candidates.append({
            "source_row_ordinal": ordinal,
            "bar_at_vendor": _evidence_value(row.get("bar_at_vendor")),
            "vendor_ohlc": {k: _evidence_value(v) for k, v in prices.items()},
            "requested_resample_frequency": _evidence_value(frequency),
            "source_projection_version": row.get("projection_version"),
            "issues": issues,
        })
    duplicate_rows = sum(len(v) - 1 for v in by_instant.values())
    conflicting_instants = sum(len(set(v)) > 1 for v in by_instant.values())
    ordered = sorted(by_instant)
    steps = [(b - a) / 1_000_000_000 for a, b in zip(ordered, ordered[1:])]
    backwards = sum(b < a for a, b in zip(clocks, clocks[1:]))
    minute_reference = frequencies == {"1min"}
    if not candidates:
        reasons.add("empty_vendor_view")
    if duplicate_rows:
        reasons.add("duplicate_vendor_instants")
    if conflicting_instants:
        reasons.add("conflicting_vendor_observations")
    if backwards:
        reasons.add("vendor_rows_out_of_order")
    if issue_counts:
        reasons.add("vendor_observations_require_diagnosis")
    if minute_reference and any(step > 60 for step in steps):
        reasons.add("observed_timestamp_spacing_exceeds_requested_minute")
    return {
        "schema": SCHEMA, "authority": "RESEARCH_ONLY_VENDOR_SOURCE",
        "source_state": "empty" if not candidates else "diagnostic_candidates",
        "pair_candidate": expected_pair,
        "source": {**view.metadata(), "source_receipt_id": receipt_id,
                   "source_request_path": view.source_request_path},
        "dataos_identity_admitted": False, "pit_backtest_eligible": False,
        "redistribution_admitted": False, "monitoring_admitted": False,
        "product_use_approval": {
            "state": "COMPLETE", "authority": "Chairman attestation",
            "reference": PRODUCT_USE_APPROVAL_REFERENCE,
            "scope": "R26 Tiingo Forex product use; technical source admission remains separate",
        },
        "candidate_observations": candidates,
        "eligible_observations": [],  # No local flag or apparently perfect data can admit a feed.
        "withheld_reasons": sorted(reasons),
        "diagnostics": {
            "rows": len(candidates), "unique_valid_timestamp_instants": len(ordered),
            "duplicate_instant_rows": duplicate_rows,
            "conflicting_ohlc_instants": conflicting_instants,
            "out_of_order_valid_timestamp_steps": backwards,
            "requested_resample_frequencies": sorted(frequencies),
            "cadence_reference_seconds": 60 if minute_reference else None,
            "observed_timestamp_steps_gt_reference": sum(step > 60 for step in steps) if minute_reference else None,
            "maximum_observed_timestamp_step_seconds": max(steps, default=None),
            "timestamp_spacing_proves_missing_data": False,
            "first_vendor_instant_utc": pd.Timestamp(ordered[0], tz="UTC").isoformat() if ordered else None,
            "last_vendor_instant_utc": pd.Timestamp(ordered[-1], tz="UTC").isoformat() if ordered else None,
            "value_issue_counts": dict(sorted(issue_counts.items())),
        },
    }


def read_forex_watch_source(day: str, receipt_id: str, *, expected_pair: str,
                            root: Path = DEFAULT_ARCHIVE, receipt_path: Path | None = None,
                            max_rows: int = MAX_ROWS, check_mount: bool = True) -> dict[str, Any]:
    """Select an exact immutable research receipt; integrity failures propagate."""
    if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
        raise TiingoViewRefusal("invalid Forex diagnostic row cap")
    view = read_research_view("forex-bars", day, receipt_id, root=root,
                             purpose="INSPECTION", max_rows=max_rows,
                             receipt_path=receipt_path, check_mount=check_mount)
    return diagnose_forex_view(view, expected_pair=expected_pair, receipt_id=receipt_id)


def reconcile_forex_intervals(
    minute_view: TiingoView, four_hour_view: TiingoView, *, expected_pair: str,
    minute_receipt_id: str, four_hour_receipt_id: str,
) -> dict[str, Any]:
    """Compare four interval hypotheses using exact inspection receipt views.

    Obtain both views through read_research_view at the file boundary. This pure
    diagnostic preserves input order and original row ordinals, but aggregates
    valid observed rows in timestamp order. It never selects a correction, fills
    a slot, infers availability, selects a hypothesis or emits admitted bars.
    Equality is of normalized view values, not arbitrary-precision raw JSON.
    """
    from urllib.parse import parse_qs, urlsplit

    inputs = {}
    for name, view, receipt, frequency in (
        ("minute", minute_view, minute_receipt_id, "1min"),
        ("four_hour", four_hour_view, four_hour_receipt_id, "4hour"),
    ):
        diagnostic = diagnose_forex_view(
            view, expected_pair=expected_pair, receipt_id=receipt
        )
        query = parse_qs(urlsplit(view.source_request_path).query,
                         keep_blank_values=True)
        if (query.get("resampleFreq") != [frequency]
                or any(row["requested_resample_frequency"] != frequency
                       for row in diagnostic["candidate_observations"])):
            raise TiingoViewRefusal(
                "Interval reconciliation requires exact 1min and 4hour requests"
            )
        inputs[name] = diagnostic

    if len(four_hour_view.rows) > MAX_RECONCILIATION_NATIVE_ROWS:
        raise TiingoViewRefusal("Interval reconciliation native row cap exceeded; no truncation")

    def prepare(diagnostic):
        entries, groups, unplaced = [], defaultdict(list), []
        for candidate in diagnostic["candidate_observations"]:
            ordinal = candidate["source_row_ordinal"]
            stamp = _clock(candidate["bar_at_vendor"])
            issues = sorted(candidate["issues"])
            if stamp is None:
                unplaced.append(ordinal)
            else:
                if stamp.value % MINUTE_NS:
                    issues.append("timestamp_not_minute_aligned")
                groups[stamp.value].append(ordinal)
            entries.append({"ordinal": ordinal, "stamp": stamp,
                            "ohlc": candidate["vendor_ohlc"], "issues": issues})
        for ordinals in groups.values():
            if len(ordinals) > 1:
                for ordinal in ordinals:
                    entries[ordinal]["issues"].append("duplicate_vendor_instant")
        return entries, groups, unplaced

    minutes, minute_groups, unplaced = prepare(inputs["minute"])
    natives, _, _ = prepare(inputs["four_hour"])
    ordered = sorted((row for row in minutes if row["stamp"] is not None),
                     key=lambda row: row["stamp"].value)
    instants = [row["stamp"].value for row in ordered]
    minute_clock = _clock(minute_view.source_observed_at_utc)
    native_clock = _clock(four_hour_view.source_observed_at_utc)
    separation = native_clock.value - minute_clock.value

    def iso(instant):
        return pd.Timestamp(instant, tz="UTC").isoformat()

    def missing_ranges(missing):
        # Compress consecutive expected slots; these are unobserved slots,
        # never a claim of missing vendor data or authority to fill them.
        runs = []
        for instant in missing:
            if runs and instant == runs[-1][1] + MINUTE_NS:
                runs[-1][1] = instant
            else:
                runs.append([instant, instant])
        return [{"first_utc": iso(first), "last_utc": iso(last),
                 "slots": (last - first) // MINUTE_NS + 1}
                for first, last in runs]

    hypotheses, row_references = [], 0
    for name, shift in INTERVAL_HYPOTHESES:
        windows = []
        for native in natives:
            row_references += 1  # Native ordinal is emitted even for an invalid window.
            if row_references > MAX_RECONCILIATION_ROW_REFERENCES:
                raise TiingoViewRefusal(
                    "Interval reconciliation row reference cap exceeded; no truncation"
                )
            window = {
                "native_source_row_ordinal": native["ordinal"],
                "native_vendor_ohlc": dict(native["ohlc"]),
                "native_issues": list(native["issues"]),
                "interval_start_utc": None, "interval_end_utc": None,
                "coverage": None, "edge_rows": None,
                "observed_minute_ohlc": None,
                "equal_fields": {field: None for field in OHLC},
                "all_ohlc_equal": None, "close_equal": None,
                "blocked_reasons": [],
            }
            windows.append(window)
            if native["stamp"] is None:
                window["blocked_reasons"] = ["invalid_native_timestamp"]
                continue
            start = native["stamp"].value + shift * MINUTE_NS
            end = start + 240 * MINUTE_NS
            try:
                window["interval_start_utc"] = iso(start)
                window["interval_end_utc"] = iso(end)
            except (ValueError, TypeError, OverflowError):
                window["blocked_reasons"] = ["interval_clock_out_of_range"]
                continue

            left, right = bisect_left(instants, start), bisect_left(instants, end)
            edges = {
                "at_interval_start": minute_groups.get(start, ()),
                "at_interval_end": minute_groups.get(end, ()),
                "last_before_start": minute_groups.get(instants[left - 1], ()) if left else (),
                "first_at_or_after_end": minute_groups.get(instants[right], ()) if right < len(instants) else (),
            }
            # Bound every ordinal reference copied into window output, including
            # unplaced rows and boundary witnesses outside the selected interval.
            cost = right - left + len(unplaced) + sum(map(len, edges.values()))
            if row_references + cost > MAX_RECONCILIATION_ROW_REFERENCES:
                raise TiingoViewRefusal(
                    "Interval reconciliation row reference cap exceeded; no truncation"
                )
            selected = ordered[left:right]
            invalid = [row["ordinal"] for row in selected if row["issues"]]
            cost += len(invalid)
            if row_references + cost > MAX_RECONCILIATION_ROW_REFERENCES:
                raise TiingoViewRefusal(
                    "Interval reconciliation row reference cap exceeded; no truncation"
                )
            row_references += cost
            observed = {row["stamp"].value for row in selected}
            expected = [start + n * MINUTE_NS for n in range(240)]
            missing = [instant for instant in expected if instant not in observed]
            unexpected = sorted(observed.difference(expected))
            occupied = [n for n, instant in enumerate(expected) if instant in observed]
            duplicates = len(selected) - len(observed)
            dense = (len(selected) == 240 and not missing and not unexpected
                     and not duplicates and not unplaced
                     and native["stamp"].value % MINUTE_NS == 0)
            window["coverage"] = {
                "observed_minute_rows": len(selected),
                "observed_unique_instants": len(observed),
                "observed_source_row_ordinals": [row["ordinal"] for row in selected],
                "expected_minute_slots": 240,
                "missing_expected_minute_slots": len(missing),
                "missing_expected_minute_ranges": missing_ranges(missing),
                "unexpected_minute_instants_utc": [iso(instant) for instant in unexpected],
                "unplaced_minute_source_row_ordinals": list(unplaced),
                "duplicate_instant_rows": duplicates,
                "leading_unobserved_slots": occupied[0] if occupied else None,
                "trailing_unobserved_slots": 239 - occupied[-1] if occupied else None,
                "internal_unobserved_slots": (
                    sum(occupied[0] < n < occupied[-1] for n, instant in enumerate(expected)
                        if instant not in observed) if occupied else None
                ),
                "dense_240_minute_grid": dense,
                "observed_grid_state": "dense" if dense else "sparse" if selected else "empty",
                "first_observed_minute_utc": iso(min(observed)) if observed else None,
                "last_observed_minute_utc": iso(max(observed)) if observed else None,
                "missing_slots_prove_missing_vendor_data": False,
                "interval_end_after_minute_receipt_observed": end > minute_clock.value,
                "interval_end_after_four_hour_receipt_observed": end > native_clock.value,
            }
            window["edge_rows"] = {key: list(refs) for key, refs in edges.items()}
            blocked = []
            if native["issues"]:
                blocked.append("invalid_or_duplicate_native_row")
            if unplaced:
                blocked.append("unplaced_minute_timestamps")
            if invalid:
                blocked.append("invalid_or_duplicate_minute_rows")
            if not selected:
                blocked.append("no_observed_minute_rows")
            window["invalid_minute_source_row_ordinals"] = invalid
            window["blocked_reasons"] = blocked
            if blocked:
                continue

            aggregate = {
                "open": selected[0]["ohlc"]["open"],
                "high": max(row["ohlc"]["high"] for row in selected),
                "low": min(row["ohlc"]["low"] for row in selected),
                "close": selected[-1]["ohlc"]["close"],
            }
            equal = {field: aggregate[field] == native["ohlc"][field] for field in OHLC}
            window.update(observed_minute_ohlc=aggregate, equal_fields=equal,
                          all_ohlc_equal=all(equal.values()), close_equal=equal["close"])

        hypotheses.append({
            "name": name, "start_offset_minutes_from_native_label": shift,
            "interval_convention": "[start, end)", "windows": windows,
            "summary": {
                "native_rows": len(windows),
                "compared_windows": sum(w["all_ohlc_equal"] is not None for w in windows),
                "all_ohlc_equal_windows": sum(w["all_ohlc_equal"] is True for w in windows),
                "close_equal_windows": sum(w["close_equal"] is True for w in windows),
                "dense_equal_windows": sum(w["all_ohlc_equal"] is True
                                          and w["coverage"]["dense_240_minute_grid"] for w in windows),
                "sparse_equal_windows": sum(w["all_ohlc_equal"] is True
                                           and not w["coverage"]["dense_240_minute_grid"] for w in windows),
            },
        })

    return {
        "schema": INTERVAL_RECONCILIATION_SCHEMA,
        "authority": "RESEARCH_ONLY_VENDOR_SOURCE", "pair_candidate": expected_pair,
        "inputs": inputs, "hypotheses": hypotheses, "eligible_observations": [],
        "monitoring_admitted": False, "dataos_identity_admitted": False,
        "pit_backtest_eligible": False, "redistribution_admitted": False,
        "comparison_semantics": {
            "equality": "exact equality of normalized TiingoView numeric values",
            "raw_arbitrary_precision_equality_proven": False,
            "aggregation": "observed rows in timestamp order; original row ordinals retained",
            "gap_filling": False, "correction_selection": False,
            "hypothesis_selection": False, "vendor_finality_proven": False,
        },
        "receipt_observation_clocks": {
            "minute_source_observed_at_utc": minute_view.source_observed_at_utc,
            "four_hour_source_observed_at_utc": four_hour_view.source_observed_at_utc,
            "four_hour_minus_minute_nanoseconds": separation,
            "absolute_separation_seconds": abs(separation) / 1_000_000_000,
            "meaning": "original response/receipt observation clocks; not durable availability or a fresh recheck",
        },
        "row_issues": {
            name: [{"source_row_ordinal": row["ordinal"], "issues": list(row["issues"])}
                   for row in rows if row["issues"]]
            for name, rows in (("minute", minutes), ("four_hour", natives))
        },
    }


# Existing version exports preserve explicit historical v1 calls.
CANDIDATE_POLICY_VERSION = "tiingo-forex-local-close-candidate/1"
CANDIDATE_POLICY_SCHEMA = "mastermind.tiingo.forex_source_candidate_assessment.v1"
CURRENT_CANDIDATE_POLICY_VERSION = "tiingo-forex-local-close-candidate/2"
CURRENT_CANDIDATE_POLICY_SCHEMA = "mastermind.tiingo.forex_source_candidate_assessment.v2"
CANDIDATE_PAIRS = (
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
    "USDMXN", "USDCNH", "USDBRL",
)
MAX_CANDIDATE_NATIVE_VINTAGES = 8


def _forex_clock_policy(version: str, family: str) -> bool:
    """Dispatch only explicit historical/current versions; omission defaults current."""
    versions = {
        "candidate": (CANDIDATE_POLICY_VERSION, CURRENT_CANDIDATE_POLICY_VERSION),
        "batch": (BATCH_CANDIDATE_POLICY_VERSION, CURRENT_BATCH_CANDIDATE_POLICY_VERSION),
    }
    historical, current = versions[family]
    if type(version) is not str or version not in (historical, current):
        raise TiingoViewRefusal("Unknown Forex " + family + " policy version")
    return version == current


def _slot_clock_contract_qualification(
    inventory: dict[str, dict[str, Any]], start: pd.Timestamp | None, end: pd.Timestamp | None,
    required_receipts: tuple[str | None, ...],
) -> dict[str, Any]:
    """Keep relevant unknown-clock vintages even when their clock claims they are open."""
    from collectors.tiingo_archive import (
        RESPONSE_OBSERVATION_CLOCK_CONTRACT, TiingoArchiveError,
        parse_observation_clock_contract,
    )

    required = {receipt for receipt in required_receipts if receipt is not None}
    present = all(receipt is not None and receipt in inventory for receipt in required_receipts)
    records = []
    for receipt, item in sorted(inventory.items()):
        diagnostic = item["diagnostic"]
        relevant = receipt in required
        if not relevant:
            for row in diagnostic["candidate_observations"]:
                stamp = _clock(row["bar_at_vendor"])
                if (stamp is None or start is None or end is None
                        or (item["frequency"] == "4hour" and stamp.value % (240 * MINUTE_NS))):
                    relevant = True  # Unplaceable evidence cannot be excluded by its clock.
                    break
                if ((item["frequency"] == "1min" and start <= stamp < end)
                        or (item["frequency"] == "4hour" and stamp == start)):
                    relevant = True
                    break
        if not relevant:
            continue
        try:
            contract = parse_observation_clock_contract(
                diagnostic["source"].get("source_observation_clock_contract"))
        except TiingoArchiveError as exc:
            raise TiingoViewRefusal("Invalid source observation clock contract") from exc
        qualified = contract == RESPONSE_OBSERVATION_CLOCK_CONTRACT
        records.append({
            "source_receipt_id": receipt, "frequency": item["frequency"],
            "role": "selected" if receipt in required else "competing",
            "declared_contract": contract,
            "state": "recognized" if qualified else "unrecorded" if contract is None else "unsupported",
            "qualified": qualified,
        })
    unqualified = [item["source_receipt_id"] for item in records if not item["qualified"]]
    return {
        "required_contract": RESPONSE_OBSERVATION_CLOCK_CONTRACT,
        "selected_receipts_present": present, "relevant_receipts": records,
        "unqualified_receipt_ids": unqualified,
        "all_relevant_contracts_qualified": present and bool(records) and not unqualified,
        "producer_declaration_only": True, "producer_execution_independently_attested": False,
    }


def assess_forex_source_candidate(
    minute_view: TiingoView, four_hour_view: TiingoView, *, expected_pair: str,
    minute_receipt_id: str, four_hour_receipt_id: str,
    policy_version: str = CURRENT_CANDIDATE_POLICY_VERSION,
    verified_at_utc: str, assessed_at_utc: str,
    known_native_vintages: tuple[tuple[TiingoView, str], ...] = (),
) -> dict[str, Any]:
    """Execute the nominated research policy without admitting a source.

    Default v2 requires recognized original-receipt clock declarations; explicit
    v1 retains historical unknown-clock semantics. Neither version admits bars.

    Both primary views and optional native vintages must come from the existing
    verified reader. This pure boundary cannot authenticate bytes on disk or
    attest the caller's readback clock. It examines only the explicitly supplied
    native inventory; minute-vintage/correction coverage remains unqualified.
    Passing checks is not finality, an eligible observation or a feed binding.
    """
    from urllib.parse import parse_qs, urlsplit

    strict_clock = _forex_clock_policy(policy_version, "candidate")
    if expected_pair not in CANDIDATE_PAIRS:
        raise TiingoViewRefusal("Unknown Forex candidate policy or pair scope")
    verified, assessed = _clock(verified_at_utc), _clock(assessed_at_utc)
    if verified is None or assessed is None or assessed < verified:
        raise TiingoViewRefusal("Candidate assessment requires ordered explicit UTC clocks")
    if (not isinstance(known_native_vintages, (tuple, list))
            or len(known_native_vintages) > MAX_CANDIDATE_NATIVE_VINTAGES):
        raise TiingoViewRefusal("Candidate native vintage cap exceeded; no truncation")

    reconciliation = reconcile_forex_intervals(
        minute_view, four_hour_view, expected_pair=expected_pair,
        minute_receipt_id=minute_receipt_id, four_hour_receipt_id=four_hour_receipt_id,
    )
    primary = reconciliation["inputs"]
    inventory = {four_hour_receipt_id: primary["four_hour"]}
    for item in known_native_vintages:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TiingoViewRefusal("Candidate native vintage requires an exact view/receipt pair")
        view, receipt = item
        if not isinstance(view, TiingoView) or len(view.rows) > MAX_RECONCILIATION_NATIVE_ROWS:
            raise TiingoViewRefusal("Candidate native vintage row cap or view refused")
        diagnostic = diagnose_forex_view(view, expected_pair=expected_pair, receipt_id=receipt)
        query = parse_qs(urlsplit(view.source_request_path).query, keep_blank_values=True)
        if (query.get("resampleFreq") != ["4hour"]
                or any(row["requested_resample_frequency"] != "4hour"
                       for row in diagnostic["candidate_observations"])):
            raise TiingoViewRefusal("Candidate vintage must be an exact native 4hour request")
        if receipt in inventory and inventory[receipt] != diagnostic:
            raise TiingoViewRefusal("Conflicting supplied content for one native receipt identity")
        inventory[receipt] = diagnostic

    clocks = [_clock(primary["minute"]["source"]["source_observed_at_utc"])]
    clocks.extend(_clock(d["source"]["source_observed_at_utc"]) for d in inventory.values())
    if any(clock > verified for clock in clocks):
        raise TiingoViewRefusal("Candidate verification precedes a supplied response observation")

    # Index every supplied native row. Duplicate or unplaceable closed-vintage
    # evidence is a failure, never an instruction to pick the newest row.
    interval_ns = 240 * MINUTE_NS
    groups = {}
    unplaced = {}
    for receipt, diagnostic in sorted(inventory.items()):
        slots = defaultdict(list)
        bad = []
        for row in diagnostic["candidate_observations"]:
            stamp = _clock(row["bar_at_vendor"])
            if stamp is None or stamp.value % interval_ns:
                bad.append(row["source_row_ordinal"])
            else:
                slots[stamp.value].append(row)
        groups[receipt], unplaced[receipt] = slots, bad

    clock_inventory = {}
    if strict_clock:
        if minute_receipt_id in inventory:
            raise TiingoViewRefusal("Conflicting frequencies for one clock receipt identity")
        clock_inventory = {
            receipt: {"diagnostic": diagnostic, "frequency": "4hour"}
            for receipt, diagnostic in inventory.items()
        }
        clock_inventory[minute_receipt_id] = {"diagnostic": primary["minute"], "frequency": "1min"}

    windows = []
    for source_window in reconciliation["hypotheses"][0]["windows"]:
        start = _clock(source_window["interval_start_utc"])
        end = _clock(source_window["interval_end_utc"])
        try:
            expires = pd.Timestamp(end.value + interval_ns, tz="UTC") if end is not None else None
        except (ValueError, OverflowError):
            expires = None
        coverage = source_window["coverage"] or {}
        comparable, open_vintages, conflicts, invalid = [], [], [], []
        if start is not None and end is not None:
            for receipt, diagnostic in sorted(inventory.items()):
                observed = _clock(diagnostic["source"]["source_observed_at_utc"])
                rows = groups[receipt].get(start.value, [])
                if observed < end:
                    if rows:
                        open_vintages.append(receipt)
                    continue
                if unplaced[receipt]:
                    invalid.append(receipt)
                if not rows:
                    continue
                comparable.append(receipt)
                if len(rows) != 1 or rows[0]["issues"]:
                    invalid.append(receipt)
                elif rows[0]["vendor_ohlc"] != source_window["native_vendor_ohlc"]:
                    conflicts.append(receipt)
        checks = {
            "utc_four_hour_slot": start is not None and start.value % interval_ns == 0,
            "valid_comparison": not source_window["blocked_reasons"],
            "dense_minute_grid": coverage.get("dense_240_minute_grid") is True,
            "normalized_ohlc_agreement": source_window["all_ohlc_equal"] is True,
            "both_responses_observed_after_interval_end": (
                bool(coverage)
                and coverage["interval_end_after_minute_receipt_observed"] is False
                and coverage["interval_end_after_four_hour_receipt_observed"] is False
            ),
            "interval_ended_before_verification": end is not None and end <= verified,
            "verification_before_candidate_expiry": expires is not None and verified < expires,
            "assessment_before_candidate_expiry": expires is not None and assessed < expires,
            "supplied_closed_native_vintages_consistent": bool(comparable) and not conflicts and not invalid,
        }
        clock_evidence = None
        if strict_clock:
            clock_evidence = _slot_clock_contract_qualification(
                clock_inventory, start, end, (minute_receipt_id, four_hour_receipt_id))
            checks["response_observation_clock_contracts_qualified"] = (
                clock_evidence["all_relevant_contracts_qualified"])
        satisfied = all(checks.values())
        windows.append({
            "native_source_row_ordinal": source_window["native_source_row_ordinal"],
            "candidate_checks_satisfied": satisfied,
            "assessment_state": "checks_satisfied_policy_unadopted" if satisfied else "checks_failed",
            "checks": checks,
            "failed_checks": [name for name, passed in checks.items() if not passed],
            "comparison_blocked_reasons": list(source_window["blocked_reasons"]),
            "candidate_projection": {
                "literal_pair": expected_pair,
                "quote_units_per_base_unit": expected_pair[3:] + " per " + expected_pair[:3],
                "interval_start_utc": source_window["interval_start_utc"],
                "interval_end_utc": source_window["interval_end_utc"],
                "utc_slot_index": start.value // interval_ns if start is not None else None,
                "native_reported_close": source_window["native_vendor_ohlc"]["close"],
                "candidate_expires_at_utc": expires.isoformat() if expires is not None else None,
            },
            "native_vintage_check": {
                "compared_closed_receipt_ids": comparable,
                "open_receipt_ids_not_compared_as_corrections": open_vintages,
                "conflicting_closed_receipt_ids": conflicts,
                "invalid_closed_receipt_ids": sorted(set(invalid)),
                "all_possible_corrections_examined": False,
                "minute_vintage_inventory_examined": False,
            },
            **({"clock_contract_qualification": clock_evidence} if strict_clock else {}),
        })

    return {
        "schema": CURRENT_CANDIDATE_POLICY_SCHEMA if strict_clock else CANDIDATE_POLICY_SCHEMA,
        "policy_version": policy_version,
        "policy_state": "CANDIDATE_NOT_ADOPTED",
        "authority": "RESEARCH_ONLY_VENDOR_SOURCE",
        "pair_candidate": expected_pair, "requested_pair_inventory": list(CANDIDATE_PAIRS),
        "source_state": "empty_native_view" if not windows else "candidate_assessments",
        "selected_candidate_hypothesis": "start_label_half_open",
        "inputs": {name: diagnostic["source"] for name, diagnostic in primary.items()},
        "native_vintage_inventory": [inventory[key]["source"] for key in sorted(inventory)],
        "inventory_scope": "only supplied exact native receipts; not an archive-wide or minute-vintage census",
        "clocks": {
            "verified_at_utc": verified_at_utc, "assessed_at_utc": assessed_at_utc,
            "meaning": "explicit caller readback/assessment clocks; no I/O or independent time attestation",
            "original_response_clocks": reconciliation["receipt_observation_clocks"],
            "reread_extends_freshness": False,
        },
        "windows": windows,
        "comparison_semantics": {
            "equality": reconciliation["comparison_semantics"]["equality"],
            "raw_arbitrary_precision_equality_proven": False,
            "vendor_immutability_proven": False, "correction_selection": False,
            "global_inventory_completeness_proven": False,
        },
        "owner_decisions_required": [
            "adopt_exact_pair_identity_and_supported_calendar_scope",
            "adopt_reported_close_and_normalized_numeric_comparison",
            "adopt_durable_readback_availability_and_freshness_policy",
            "qualify_vintage_inventory_and_observation_revision_contract",
            "explicit_account_feed_binding_through_normal_rule_revision",
        ],
        "product_use_approval": dict(primary["minute"]["product_use_approval"]),
        "eligible_observations": [], "monitoring_admitted": False,
        "dataos_identity_admitted": False, "pit_backtest_eligible": False,
        "redistribution_admitted": False,
    }


BATCH_CANDIDATE_POLICY_VERSION = "tiingo-forex-local-close-batch-candidate/1"
BATCH_CANDIDATE_POLICY_SCHEMA = "mastermind.tiingo.forex_source_batch_candidate.v1"
CURRENT_BATCH_CANDIDATE_POLICY_VERSION = "tiingo-forex-local-close-batch-candidate/2"
CURRENT_BATCH_CANDIDATE_POLICY_SCHEMA = "mastermind.tiingo.forex_source_batch_candidate.v2"
BATCH_INVENTORY_SCHEMA = "mastermind.tiingo.forex_batch_inventory_evidence.v1"
MAX_BATCH_MINUTE_VINTAGES = 9
MAX_BATCH_NATIVE_VINTAGES = MAX_CANDIDATE_NATIVE_VINTAGES + 1
MAX_BATCH_INPUT_ROWS = 100_000
MAX_BATCH_IDENTITY_BYTES = 64 * 1024 * 1024
MAX_BATCH_INVENTORY_ENTRIES = 256
BATCH_SUPPORTING_CHECKS = (
    "utc_four_hour_slot",
    "valid_comparison",
    "dense_minute_grid",
    "normalized_ohlc_agreement",
    "both_responses_observed_after_interval_end",
    "interval_ended_before_verification",
    "supplied_closed_native_vintages_consistent",
)


def _batch_view_identity(view: TiingoView, budget: dict[str, int]) -> str:
    """Fingerprint full view content; absent additive metadata keeps historical identity."""
    import hashlib
    import json
    from dataclasses import fields

    def typed(value: Any, depth: int = 0) -> Any:
        budget["nodes"] += 1
        if depth > 16 or budget["nodes"] > 10_000_000:
            raise TiingoViewRefusal("Batch identity structure budget exceeded")
        if value is None:
            return ["none"]
        if type(value) is bool:
            return ["bool", value]
        if type(value) is int:
            return ["int", str(value)]
        if type(value) is float:
            return ["float", value.hex()]
        if type(value) is str:
            return ["str", value]
        if type(value) in (list, tuple):
            return [type(value).__name__, [typed(item, depth + 1) for item in value]]
        if type(value) is dict and all(type(key) is str for key in value):
            return ["dict", [[key, typed(value[key], depth + 1)] for key in sorted(value)]]
        raise TiingoViewRefusal("Batch identity contains unsupported source value types")

    values = {field.name: getattr(view, field.name) for field in fields(TiingoView)}
    # An absent additive contract preserves historical v1 view fingerprints.
    if view.source_observation_clock_contract is None:
        values.pop("source_observation_clock_contract")
    content = typed(values)
    digest = hashlib.sha256()
    for part in json.JSONEncoder(ensure_ascii=True, separators=(",", ":")).iterencode(content):
        encoded = part.encode("utf-8")
        budget["bytes"] += len(encoded)
        if budget["bytes"] > MAX_BATCH_IDENTITY_BYTES:
            raise TiingoViewRefusal("Batch full-content identity byte budget exceeded")
        digest.update(encoded)
    return digest.hexdigest()


def _batch_inventory_declaration(
    evidence: dict[str, Any] | None, inventory: dict[str, dict[str, Any]],
    verified: pd.Timestamp,
) -> dict[str, Any]:
    """Validate correspondence of a supplied declaration, never attest a census."""
    result = {
        "state": "not_supplied",
        "inventory_selection_consistent": None,
        "two_scan_identity_sets_equal": None,
        "atomic_census_proven": False,
        "global_inventory_completeness_proven": False,
    }
    if evidence is None:
        return result
    if (not isinstance(evidence, dict)
            or evidence.get("schema") != BATCH_INVENTORY_SCHEMA
            or set(evidence) - {"schema", "scans", "selected_receipt_ids", "owner_quiescence_reference"}):
        raise TiingoViewRefusal("Batch inventory declaration schema refused")

    def identities(value: Any) -> list[str]:
        if (not isinstance(value, (list, tuple))
                or len(value) > MAX_BATCH_INVENTORY_ENTRIES
                or any(not isinstance(item, str) or not SHA.fullmatch(item) for item in value)
                or len(set(value)) != len(value)):
            raise TiingoViewRefusal("Batch inventory requires bounded unique exact receipt identities")
        return sorted(value)

    selected = evidence.get("selected_receipt_ids")
    if not isinstance(selected, dict) or set(selected) != {"1min", "4hour"}:
        raise TiingoViewRefusal("Batch inventory requires selected identities by frequency")
    selected = {frequency: identities(selected[frequency]) for frequency in ("1min", "4hour")}
    actual = {frequency: sorted(key for key, item in inventory.items()
                               if item["frequency"] == frequency)
              for frequency in ("1min", "4hour")}
    if selected != actual:
        raise TiingoViewRefusal("Batch supplied views do not match declared selected inventory")
    scans = evidence.get("scans")
    if not isinstance(scans, (list, tuple)) or len(scans) != 2:
        raise TiingoViewRefusal("Batch inventory requires exactly two explicit scan declarations")
    normalized, previous = [], None
    for scan in scans:
        if not isinstance(scan, dict) or set(scan) != {"started_at_utc", "completed_at_utc", "receipt_ids"}:
            raise TiingoViewRefusal("Batch scan declaration fields refused")
        started, completed = _clock(scan["started_at_utc"]), _clock(scan["completed_at_utc"])
        if (started is None or completed is None or completed < started
                or completed > verified or (previous is not None and started < previous)):
            raise TiingoViewRefusal("Batch scan declarations require ordered bounded clocks")
        ids = identities(scan["receipt_ids"])
        if not set(inventory) <= set(ids):
            raise TiingoViewRefusal("A supplied selected receipt is absent from a declared scan")
        if any(_clock(item["view"].source_observed_at_utc) > completed for item in inventory.values()):
            raise TiingoViewRefusal("A declared scan precedes a selected response observation")
        normalized.append({"started_at_utc": scan["started_at_utc"],
                           "completed_at_utc": scan["completed_at_utc"], "receipt_ids": ids})
        previous = completed
    quiescence = evidence.get("owner_quiescence_reference")
    if quiescence is not None and (not isinstance(quiescence, str) or len(quiescence) > 2048):
        raise TiingoViewRefusal("Owner quiescence evidence must be a bounded reference, not an authority flag")
    return {
        **result, "schema": BATCH_INVENTORY_SCHEMA, "state": "supplied_declaration_only",
        "inventory_selection_consistent": True,
        "two_scan_identity_sets_equal": normalized[0]["receipt_ids"] == normalized[1]["receipt_ids"],
        "selected_receipt_ids": selected, "scans": normalized,
        "owner_quiescence_reference": quiescence,
        "owner_quiescence_independently_verified": False,
    }


def _batch_minute_slot(
    minute_inventory: dict[str, dict[str, Any]], start: pd.Timestamp, end: pd.Timestamp,
) -> tuple[dict[str, Any], str | None]:
    """Compare all supplied closed overlapping minutes without stitching grids."""
    grids, invalid, opened = {}, [], []
    for receipt, item in sorted(minute_inventory.items()):
        diagnostic = item["diagnostic"]
        if _clock(item["view"].source_observed_at_utc) < end:
            opened.append(receipt)
            continue
        values, bad = {}, False
        for row in diagnostic["candidate_observations"]:
            stamp = _clock(row["bar_at_vendor"])
            if stamp is None:
                bad = True  # An unplaceable instant cannot be excluded from this slot.
                continue
            if not start <= stamp < end:
                continue
            if stamp.value % MINUTE_NS or stamp.value in values or row["issues"]:
                bad = True
            values.setdefault(stamp.value, row["vendor_ohlc"])
        grids[receipt] = values
        if bad:
            invalid.append(receipt)
    required = set(range(start.value, end.value, MINUTE_NS))
    complete = [receipt for receipt in sorted(grids)
                if receipt not in invalid and set(grids[receipt]) == required]
    partial = [receipt for receipt in sorted(grids) if set(grids[receipt]) != required]
    reference = complete[0] if complete else None
    conflicts = []
    if reference is not None:
        baseline = grids[reference]
        for receipt, values in sorted(grids.items()):
            if any(stamp not in baseline or ohlc != baseline[stamp] for stamp, ohlc in values.items()):
                conflicts.append(receipt)
    return {
        "complete_reference_receipt_ids": complete,
        "selected_complete_reference_receipt_id": reference,
        "compared_closed_receipt_ids": sorted(grids),
        "open_receipt_ids_not_compared_as_corrections": opened,
        "partial_closed_receipt_ids": partial,
        "conflicting_closed_receipt_ids": conflicts,
        "invalid_closed_receipt_ids": invalid,
        "closed_overlapping_minute_counts": {receipt: len(values) for receipt, values in sorted(grids.items())},
        "supplied_closed_minute_values_consistent": bool(reference) and not conflicts and not invalid,
        "partial_matching_receipts_do_not_establish_completeness": True,
        "all_possible_corrections_examined": False,
    }, reference


def assess_forex_source_batch_candidate(
    minute_vintages: tuple[tuple[TiingoView, str], ...],
    four_hour_vintages: tuple[tuple[TiingoView, str], ...], *,
    expected_pair: str, consecutive: int,
    policy_version: str = CURRENT_BATCH_CANDIDATE_POLICY_VERSION,
    verified_at_utc: str, assessed_at_utc: str,
    inventory_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess the exact current adjacent slots as unadopted research evidence.

    Default v2 also qualifies every relevant supplied receipt clock; explicit
    v1 preserves the historical policy without that additional provenance gate.

    Older supporting slots retain the individual policy's expired verdict while
    using the existing evaluator's current-decision availability semantics. Only
    the newest slot must remain within its fixed expiry. One complete minute
    view must witness each slot; partial views are compared, never stitched.

    This pure function authenticates neither disk bytes nor caller clocks or an
    archive census. Equal supplied scan declarations are not an atomic snapshot.
    No result admits a feed, account binding, historical availability or bars.
    """
    from urllib.parse import parse_qs, urlsplit

    strict_clock = _forex_clock_policy(policy_version, "batch")
    if (expected_pair not in CANDIDATE_PAIRS
            or type(consecutive) is not int or not 1 <= consecutive <= 10):
        raise TiingoViewRefusal("Unknown Forex batch policy, pair or consecutive-close bound")
    verified, assessed = _clock(verified_at_utc), _clock(assessed_at_utc)
    if verified is None or assessed is None or assessed < verified:
        raise TiingoViewRefusal("Batch assessment requires ordered explicit UTC clocks")
    supplied = (("1min", minute_vintages, MAX_BATCH_MINUTE_VINTAGES),
                ("4hour", four_hour_vintages, MAX_BATCH_NATIVE_VINTAGES))
    for _frequency, views, limit in supplied:
        if not isinstance(views, (list, tuple)) or len(views) > limit:
            raise TiingoViewRefusal("Batch input-reference cap exceeded before deduplication")
    inventory, duplicates = {}, Counter()
    budget = {"rows": 0, "nodes": 0, "bytes": 0}
    for frequency, views, _limit in supplied:
        for item in views:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise TiingoViewRefusal("Batch inputs require exact view/receipt pairs")
            view, receipt = item
            if not isinstance(view, TiingoView) or not isinstance(view.rows, tuple):
                raise TiingoViewRefusal("Batch inputs require exact reader views with ordered tuple rows")
            budget["rows"] += len(view.rows)
            if (budget["rows"] > MAX_BATCH_INPUT_ROWS
                    or (frequency == "4hour" and len(view.rows) > MAX_RECONCILIATION_NATIVE_ROWS)):
                raise TiingoViewRefusal("Batch row-reference budget exceeded; no truncation")
            diagnostic = diagnose_forex_view(view, expected_pair=expected_pair, receipt_id=receipt)
            query = parse_qs(urlsplit(view.source_request_path).query, keep_blank_values=True)
            if (query.get("resampleFreq") != [frequency]
                    or any(row["requested_resample_frequency"] != frequency
                           for row in diagnostic["candidate_observations"])):
                raise TiingoViewRefusal("Batch view frequency does not match its exact request")
            if _clock(view.source_observed_at_utc) > verified:
                raise TiingoViewRefusal("Batch verification precedes a supplied response observation")
            fingerprint = _batch_view_identity(view, budget)
            if receipt in inventory:
                if (inventory[receipt]["fingerprint"] != fingerprint
                        or inventory[receipt]["frequency"] != frequency):
                    raise TiingoViewRefusal("Conflicting full content for one batch receipt identity")
                duplicates[receipt] += 1
                continue
            inventory[receipt] = {"view": view, "diagnostic": diagnostic,
                                  "frequency": frequency, "fingerprint": fingerprint}
    inventory = dict(sorted(inventory.items()))
    declaration = _batch_inventory_declaration(inventory_evidence, inventory, verified)
    minutes = {key: item for key, item in inventory.items() if item["frequency"] == "1min"}
    natives = {key: item for key, item in inventory.items() if item["frequency"] == "4hour"}
    interval_ns = 240 * MINUTE_NS
    try:
        latest_end_ns = (assessed.value // interval_ns) * interval_ns
        ends = [pd.Timestamp(latest_end_ns - interval_ns * offset, tz="UTC")
                for offset in reversed(range(consecutive))]
        starts = [pd.Timestamp(end.value - interval_ns, tz="UTC") for end in ends]
        expiries = [pd.Timestamp(end.value + interval_ns, tz="UTC") for end in ends]
    except (ValueError, OverflowError):
        raise TiingoViewRefusal("Batch target sequence exceeds supported nanosecond clock bounds") from None

    supporting_checks = BATCH_SUPPORTING_CHECKS + (
        ("response_observation_clock_contracts_qualified",) if strict_clock else ())
    cache, slots = {}, []
    for index, (start, end, expiry) in enumerate(zip(starts, ends, expiries)):
        minute_check, minute_receipt = _batch_minute_slot(minutes, start, end)
        native_choices = []
        for receipt, item in natives.items():
            rows = [row for row in item["diagnostic"]["candidate_observations"]
                    if (stamp := _clock(row["bar_at_vendor"])) is not None and stamp == start]
            if rows:
                preferred = (_clock(item["view"].source_observed_at_utc) >= end
                             and len(rows) == 1 and not rows[0]["issues"])
                native_choices.append((not preferred, receipt))
        native_receipt = min(native_choices)[1] if native_choices else None
        candidate = None
        if minute_receipt is not None and native_receipt is not None:
            key = (minute_receipt, native_receipt)
            if key not in cache:
                # At most one deterministic pair per required slot (ten total),
                # not a retained Cartesian product of all supplied receipts.
                cache[key] = assess_forex_source_candidate(
                    minutes[minute_receipt]["view"], natives[native_receipt]["view"],
                    expected_pair=expected_pair, minute_receipt_id=minute_receipt,
                    four_hour_receipt_id=native_receipt,
                    policy_version=(CURRENT_CANDIDATE_POLICY_VERSION if strict_clock
                                    else CANDIDATE_POLICY_VERSION),
                    verified_at_utc=verified_at_utc, assessed_at_utc=assessed_at_utc,
                    known_native_vintages=tuple((item["view"], receipt) for receipt, item in natives.items()
                                               if receipt != native_receipt),
                )
            matches = [window for window in cache[key]["windows"]
                       if _clock(window["candidate_projection"]["interval_start_utc"]) == start]
            candidate = matches[0] if matches else None
        supporting = (candidate is not None
                      and all(candidate["checks"][name] for name in supporting_checks)
                      and minute_check["supplied_closed_minute_values_consistent"])
        clock_evidence = None
        if strict_clock:
            clock_evidence = _slot_clock_contract_qualification(
                inventory, start, end, (minute_receipt, native_receipt))
            supporting = supporting and clock_evidence["all_relevant_contracts_qualified"]
        latest = index == consecutive - 1
        fresh = (candidate is not None
                 and candidate["checks"]["verification_before_candidate_expiry"]
                 and candidate["checks"]["assessment_before_candidate_expiry"])
        projection = (dict(candidate["candidate_projection"]) if candidate is not None else {
            "literal_pair": expected_pair,
            "quote_units_per_base_unit": expected_pair[3:] + " per " + expected_pair[:3],
            "interval_start_utc": start.isoformat(), "interval_end_utc": end.isoformat(),
            "utc_slot_index": start.value // interval_ns,
            "native_reported_close": None, "candidate_expires_at_utc": expiry.isoformat(),
        })
        projection["candidate_available_at_utc"] = verified_at_utc
        slots.append({
            "role": "latest" if latest else "supporting",
            "candidate_assessment": candidate,
            "selected_minute_receipt_id": minute_receipt,
            "selected_native_receipt_id": native_receipt,
            "supporting_checks_satisfied": bool(supporting),
            "latest_freshness_required": latest,
            "latest_freshness_satisfied": bool(fresh) if latest else None,
            "minute_vintage_check": minute_check, "candidate_projection": projection,
            "slot_checks_satisfied": bool(supporting and (not latest or fresh)),
            **({"clock_contract_qualification": clock_evidence} if strict_clock else {}),
        })
    checks = {
        "all_required_adjacent_slots_supported": all(slot["supporting_checks_satisfied"] for slot in slots),
        "latest_slot_within_fixed_expiry": slots[-1]["latest_freshness_satisfied"],
        "supplied_two_scan_identity_sets_equal": declaration["two_scan_identity_sets_equal"],
    }
    if strict_clock:
        checks["all_relevant_observation_clock_contracts_qualified"] = all(
            slot["clock_contract_qualification"]["all_relevant_contracts_qualified"] for slot in slots)
    satisfied = all(slot["slot_checks_satisfied"] for slot in slots) and declaration["two_scan_identity_sets_equal"] is not False
    return {
        "schema": CURRENT_BATCH_CANDIDATE_POLICY_SCHEMA if strict_clock else BATCH_CANDIDATE_POLICY_SCHEMA,
        "policy_version": policy_version,
        "policy_state": "CANDIDATE_NOT_ADOPTED", "authority": "RESEARCH_ONLY_VENDOR_SOURCE",
        "pair_candidate": expected_pair, "requested_pair_inventory": list(CANDIDATE_PAIRS),
        "consecutive": consecutive, "required_interval_ends_utc": [end.isoformat() for end in ends],
        "clocks": {
            "verified_at_utc": verified_at_utc, "assessed_at_utc": assessed_at_utc,
            "meaning": "caller-supplied readback completion and assessment; no independent attestation",
            "latest_anchor_from": "assessment UTC four-hour boundary; no older-window fallback",
            "supporting_availability": "current decision only; not historical availability",
            "reread_extends_newest_freshness": False,
        },
        "input_inventory": [
            {"source": item["diagnostic"]["source"], "frequency": item["frequency"],
             "full_view_identity_sha256": item["fingerprint"]}
            for item in inventory.values()
        ],
        "duplicate_supplied_references": dict(sorted(duplicates.items())),
        "inventory_evidence": declaration,
        "inventory_scope": "only supplied views and declarations; neither an authenticated nor atomic archive census",
        "slots": slots, "checks": checks,
        "batch_checks_satisfied": bool(satisfied),
        "assessment_state": "checks_satisfied_policy_unadopted" if satisfied else "checks_failed",
        "failed_checks": [key for key, passed in checks.items() if passed is False],
        "comparison_semantics": {
            "normalized_ohlc_equality_only": True,
            "raw_arbitrary_precision_equality_proven": False,
            "vendor_immutability_proven": False, "correction_selection": False,
            "global_inventory_completeness_proven": False,
            "atomic_census_proven": False,
        },
        "owner_decisions_required": [
            "adopt_exact_pair_identity_and_supported_calendar_scope",
            "adopt_reported_close_and_normalized_numeric_comparison",
            "qualify_actual_readback_clock_and_inventory_concurrency_boundary",
            "adopt_supporting_history_and_newest_slot_freshness_policy",
            "qualify_observation_revision_and_explicit_account_feed_binding",
        ],
        "product_use_approval": {
            "state": "COMPLETE", "authority": "Chairman attestation",
            "reference": PRODUCT_USE_APPROVAL_REFERENCE,
            "scope": "R26 Tiingo Forex product use; technical source admission remains separate",
        },
        "eligible_observations": [], "monitoring_admitted": False,
        "dataos_identity_admitted": False, "pit_backtest_eligible": False,
        "redistribution_admitted": False,
    }


BATCH_CENSUS_SCHEMA = "mastermind.tiingo.forex_batch_observed_census.v1"


def _census_now_utc() -> str:
    """Actual invocation clock; tests may replace this private clock only."""
    return pd.Timestamp.now(tz="UTC").isoformat()


def _census_clock() -> tuple[str, pd.Timestamp]:
    value = _census_now_utc()
    stamp = _clock(value)
    if stamp is None:
        raise TiingoViewRefusal("Census clock is not an aware bounded UTC instant")
    return value, stamp


def _scan_forex_receipts(context: Any, dates: tuple[str, ...], expected_pair: str,
                        evidence: dict[str, Any]) -> dict[str, Any]:
    """Observe bounded leaf entries before selecting a pair or frequency."""
    import hashlib
    import json
    import os
    import stat
    from urllib.parse import parse_qs, urlsplit
    from collectors.tiingo_archive import capture_day, validate_receipt

    started, start = _census_clock()
    scan = {"started_at_utc": started, "completed_at_utc": None,
            "directories": [], "entry_count_before_filter": 0, "entries": []}
    evidence["scans"].append(scan)
    entries = []
    for day in dates:
        relative = ("receipts", "forex-bars", day)
        directory = {"path": "/".join(relative), "state": "observing", "entries": 0}
        scan["directories"].append(directory)
        try:
            with context.directory(relative) as fd:
                with os.scandir(fd) as listing:
                    for entry in listing:
                        scan["entry_count_before_filter"] += 1
                        directory["entries"] += 1
                        if scan["entry_count_before_filter"] > MAX_BATCH_INVENTORY_ENTRIES:
                            raise TiingoViewRefusal("Census entry cap exceeded before filtering or deduplication")
                        # No glob or type/extension/pair filter can hide an entry.
                        entries.append((day, entry.name, entry.stat(follow_symlinks=False).st_mode))
                directory["state"] = "observed"
        except FileNotFoundError:
            # Only an absent leaf directory counts as absence. A file vanishing
            # after enumeration is an unstable acquisition, not an empty leaf.
            if directory["entries"]:
                raise TiingoViewRefusal("Census entry disappeared during enumeration") from None
            directory["state"] = "absent"
    for day, name, mode in sorted(entries):
        relative = ("receipts", "forex-bars", day, name)
        item = {"path": "/".join(relative), "state": "unverified"}
        scan["entries"].append(item)
        if (not stat.S_ISREG(mode)
                or not re.fullmatch(r"[0-9a-f]{16}-[0-9a-f]{24}\.json", name)):
            raise TiingoViewRefusal("Census contains an unexpected temporary, nonregular or named receipt entry")
        record = context.read_metadata(relative)
        if (record.get("schema") != "mastermind.tiingo.raw_receipt.v1"
                or record.get("source") != "forex-bars" or record.get("vendor") != "tiingo"
                or not isinstance(record.get("symbol"), str)
                or not re.fullmatch(r"[a-z]{6}", record["symbol"])
                or not isinstance(record.get("raw_sha256"), str)
                or not SHA.fullmatch(record["raw_sha256"])
                or any(type(record.get(key)) is not int or record[key] < 0
                       for key in ("raw_bytes", "compressed_bytes"))):
            raise TiingoViewRefusal("Census receipt metadata cannot be safely placed or selected")
        identity = validate_receipt(record)
        observed = _clock(record.get("observed_at_utc"))
        if (record.get("receipt_id") != identity or observed is None
                or capture_day(record["observed_at_utc"]) != day):
            raise TiingoViewRefusal("Census receipt identity or UTC capture partition mismatch")
        request_hash = hashlib.sha256(record["request_path"].encode()).hexdigest()[:16]
        stem = request_hash + "-" + record["raw_sha256"][:24]
        expected_raw = "/".join(("raw", "forex-bars", day, record["symbol"], stem + ".raw.gz"))
        if name != stem + ".json" or record.get("raw_path") != expected_raw:
            raise TiingoViewRefusal("Census receipt path does not bind its exact original request and raw context")
        query = parse_qs(urlsplit(record["request_path"]).query, keep_blank_values=True)
        frequencies = query.get("resampleFreq", [])
        frequency = frequencies[0] if len(frequencies) == 1 else None
        if frequency is None:
            raise TiingoViewRefusal("Census Forex receipt lacks one exact requested frequency")
        selected = record["symbol"] == expected_pair.lower() and frequency in ("1min", "4hour")
        item.update(
            state="metadata_verified", receipt_id=identity,
            receipt_metadata_sha256=hashlib.sha256(json.dumps(record, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
            capture_day=day, pair=record["symbol"].upper(), frequency=frequency,
            source_observed_at_utc=record["observed_at_utc"], raw_sha256=record["raw_sha256"],
            raw_bytes=record["raw_bytes"], compressed_bytes=record["compressed_bytes"],
            selection="selected" if selected else "other_literal_pair_or_frequency",
        )
    completed, end = _census_clock()
    scan["completed_at_utc"] = completed
    if end < start or any(_clock(item["source_observed_at_utc"]) > end for item in scan["entries"]):
        raise TiingoViewRefusal("Census clocks precede a receipt observation or run backwards")
    snapshot = {"directories": scan["directories"], "entries": scan["entries"]}
    scan["snapshot_sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return scan


def read_forex_source_batch_candidate(
    *, expected_pair: str, consecutive: int,
    policy_version: str = CURRENT_BATCH_CANDIDATE_POLICY_VERSION,
    root: Path = DEFAULT_ARCHIVE, check_mount: bool = True,
) -> dict[str, Any]:
    """Read a bounded observed census through the selected candidate policy version.

    Two scans and exact retained byte reads are observations, not a lock or an
    atomic/global inventory guarantee. No captures, materialization, correction
    choice, historical knowability, source admission or account effects occur.
    A refusal carries its compact partial observations as census_evidence.
    """
    from collectors.tiingo_archive import TiingoArchiveError
    from scripts.tiingo_materialize import BoundedTiingoRead

    strict_clock = _forex_clock_policy(policy_version, "batch")
    if (expected_pair not in CANDIDATE_PAIRS
            or type(consecutive) is not int or not 1 <= consecutive <= 10):
        raise TiingoViewRefusal("Unknown Forex census policy, pair or consecutive-close bound")
    started_at, started = _census_clock()
    interval_ns = 240 * MINUTE_NS
    latest_end_ns = (started.value // interval_ns) * interval_ns
    try:
        earliest = pd.Timestamp(latest_end_ns - interval_ns * (consecutive - 1), tz="UTC")
        dates = tuple(day.date().isoformat() for day in pd.date_range(
            earliest.normalize(), started.normalize(), freq="D"))
    except (ValueError, OverflowError):
        raise TiingoViewRefusal("Census target sequence exceeds supported clock bounds") from None
    if not 1 <= len(dates) <= 3:
        raise TiingoViewRefusal("Census capture-date bound exceeded")
    evidence = {
        "schema": BATCH_CENSUS_SCHEMA, "state": "acquiring", "policy_version": policy_version,
        "pair_candidate": expected_pair, "consecutive": consecutive,
        "capture_dates": list(dates), "started_at_utc": started_at,
        "fixed_latest_interval_end_utc": pd.Timestamp(latest_end_ns, tz="UTC").isoformat(),
        "scans": [], "selected_views": [], "byte_reads": {}, "selected_row_references": 0,
        "observed_scans_equal": None, "assessment": None,
        "atomic_census_proven": False, "global_inventory_completeness_proven": False,
        "owner_quiescence_independently_verified": False,
        "historical_availability_proven": False, "eligible_observations": [],
        "monitoring_admitted": False, "dataos_identity_admitted": False,
        "pit_backtest_eligible": False, "redistribution_admitted": False,
        "product_use_approval": {"state": "COMPLETE", "authority": "Chairman attestation",
                                 "reference": PRODUCT_USE_APPROVAL_REFERENCE},
        "bounds": {"entries_before_filter_per_scan": MAX_BATCH_INVENTORY_ENTRIES,
                   "capture_dates": 3, "metadata_bytes": 16 * 1024 * 1024,
                   "decompressed_raw_bytes": 64 * 1024 * 1024,
                   "compressed_raw_bytes": 64 * 1024 * 1024,
                   "encoded_normalized_bytes": 64 * 1024 * 1024,
                   "total_process_memory_bound_claimed": False,
                   "minute_references": MAX_BATCH_MINUTE_VINTAGES,
                   "native_references": MAX_BATCH_NATIVE_VINTAGES,
                   "selected_row_references": MAX_BATCH_INPUT_ROWS},
    }
    context = None
    try:
        with BoundedTiingoRead(root, check_mount=check_mount) as context:
            first = _scan_forex_receipts(context, dates, expected_pair, evidence)
            selected = [item for item in first["entries"] if item["selection"] == "selected"]
            for frequency, limit in (("1min", MAX_BATCH_MINUTE_VINTAGES),
                                     ("4hour", MAX_BATCH_NATIVE_VINTAGES)):
                if sum(item["frequency"] == frequency for item in selected) > limit:
                    raise TiingoViewRefusal("Census selected-reference cap exceeded before deduplication")
            views = {"1min": [], "4hour": []}
            for item in selected:
                acquired = {"path": item["path"], "receipt_id": item["receipt_id"],
                            "frequency": item["frequency"], "state": "acquiring"}
                evidence["selected_views"].append(acquired)
                remaining = MAX_BATCH_INPUT_ROWS - evidence["selected_row_references"]
                if remaining < 1:
                    raise TiingoViewRefusal("Census selected row-reference budget exhausted")
                limit = MAX_ROWS if item["frequency"] == "1min" else MAX_RECONCILIATION_NATIVE_ROWS
                try:
                    view = read_research_view(
                        "forex-bars", item["capture_day"], item["receipt_id"], root=root,
                        purpose="INSPECTION", receipt_path=Path(root) / item["path"],
                        max_rows=min(limit, remaining), check_mount=check_mount, read_context=context,
                    )
                except TiingoViewRefusal as exc:
                    if str(exc) != "source view lacks artifact-bound evidence":
                        raise
                    acquired.update(state="materialized_view_unavailable", empty_payload_proven=False)
                    continue
                if len(view.rows) > min(limit, remaining):
                    raise TiingoViewRefusal(
                        "Census exact-reader result exceeds its row-reference allowance"
                    )
                evidence["selected_row_references"] += len(view.rows)
                acquired.update(state="exact_view_verified", rows=len(view.rows),
                                raw_sha256=view.source_sha256)
                if strict_clock:
                    acquired["source_observation_clock_contract"] = view.source_observation_clock_contract
                views[item["frequency"]].append((view, item["receipt_id"]))
            second = _scan_forex_receipts(context, dates, expected_pair, evidence)
            evidence["observed_scans_equal"] = first["snapshot_sha256"] == second["snapshot_sha256"]
            context.verify_bindings()
            verified_at, verified = _census_clock()
            assessed_at, assessed = _census_clock()
            evidence.update(verified_at_utc=verified_at, assessed_at_utc=assessed_at,
                            byte_reads=context.used)
            if (verified < _clock(second["completed_at_utc"]) or assessed < verified
                    or _clock(first["started_at_utc"]) < started
                    or _clock(second["started_at_utc"]) < _clock(first["completed_at_utc"])):
                raise TiingoViewRefusal("Census readback/assessment clocks are not ordered")
            reasons = []
            if not evidence["observed_scans_equal"]:
                reasons.append("observed_receipt_inventory_changed")
            if assessed.value // interval_ns * interval_ns != latest_end_ns:
                reasons.append("assessment_crossed_fixed_four_hour_boundary")
            if any(item["state"] != "exact_view_verified" for item in evidence["selected_views"]):
                reasons.append("selected_materialized_view_unavailable")
            if reasons:
                evidence.update(state="withheld", withheld_reasons=reasons)
                return evidence
            declaration = {
                "schema": BATCH_INVENTORY_SCHEMA,
                "selected_receipt_ids": {frequency: sorted({identity for _view, identity in items})
                                         for frequency, items in views.items()},
                "scans": [{"started_at_utc": scan["started_at_utc"],
                           "completed_at_utc": scan["completed_at_utc"],
                           "receipt_ids": sorted({item["receipt_id"] for item in scan["entries"]})}
                          for scan in (first, second)],
            }
            evidence["assessment"] = assess_forex_source_batch_candidate(
                tuple(views["1min"]), tuple(views["4hour"]), expected_pair=expected_pair,
                consecutive=consecutive, policy_version=policy_version,
                verified_at_utc=verified_at, assessed_at_utc=assessed_at,
                inventory_evidence=declaration,
            )
            evidence["state"] = "observed_census_complete_policy_unadopted"
            return evidence
    except (TiingoViewRefusal, TiingoArchiveError, OSError, ValueError, TypeError, KeyError) as exc:
        evidence.update(state="refused", refusal_type=type(exc).__name__, refusal_reason=str(exc))
        if context is not None:
            evidence["byte_reads"] = context.used
        refusal = TiingoViewRefusal("Forex observed census refused: " + str(exc))
        refusal.census_evidence = evidence
        raise refusal from exc
