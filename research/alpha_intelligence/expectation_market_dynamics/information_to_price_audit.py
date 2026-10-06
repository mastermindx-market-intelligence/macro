"""Read-only structural audit of SRC-A1's existing declared snapshot.

This diagnostic is not an expectation store, PIT certification, rights decision,
admission authority, or predictive evaluation. Core audit() uses only stdlib;
pandas is imported lazily only to decode explicit CLI parquet input.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from numbers import Real
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

OBSERVATION_COLUMNS = (
    "observation_id collection_session_id attempt_id provider provider_record_class "
    "provider_payload_hash ticker_compat issuer_ref security_ref metric horizon_label_raw "
    "period_end fiscal_period fiscal_year observation_type value unit currency basis "
    "aggregation_level contributor_id source_effective_at source_published_at "
    "provider_observed_at system_observed_at market_session missingness_reason "
    "correction_state supersedes_observation_id rights_class provenance_note"
).split()
ATTEMPT_COLUMNS = (
    "attempt_id collection_session_id provider ticker_compat attempted_at completed_at "
    "status http_status latency_ms response_payload_hash safe_error_class "
    "safe_error_detail observation_count"
).split()
OBSERVATION_TYPES = {
    "average", "median", "high", "low", "covering_analyst_count", "growth", "year_ago"
}
ATTEMPT_STATUSES = {
    "success", "partial", "null", "http_401", "http_403", "http_429", "malformed", "error"
}
MISSINGNESS = {"UNESTIMABLE", "UNAVAILABLE", "RIGHTS_BLOCKED", "NOT_APPLICABLE", "MALFORMED"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _missing(value):
    # Nullish parquet scalars in metadata are absent; nonfinite measurements
    # are explicitly invalid in _measurement rather than silently made null.
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            return math.isnan(value)
        except (TypeError, ValueError, OverflowError):
            pass
    return type(value).__name__ in {"NAType", "NaTType"}


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _stable(value):
    """JSON-safe fingerprint form; preserve null vs bool vs nonfinite differences."""
    if isinstance(value, Mapping):
        return {str(k): _stable(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_stable(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            if not math.isfinite(value):
                return {"nonfinite": str(value)}
        except (TypeError, ValueError, OverflowError):
            return {"invalid_number": str(value)}
        return value if isinstance(value, (int, float)) else float(value)
    if value is None or isinstance(value, (str, bool)):
        return value
    return {"scalar_type": type(value).__name__, "representation": str(value)}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _clock(value):
    if _missing(value):
        return None
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return None
        return stamp.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def _measurement(value):
    if value is None or type(value).__name__ in {"NAType", "NaTType"}:
        return "missing"
    if isinstance(value, bool) or not isinstance(value, Real):
        return "invalid"
    try:
        return "valid" if math.isfinite(value) else "invalid"
    except (TypeError, ValueError, OverflowError):
        return "invalid"


def _valid_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except (ValueError, TypeError):
        return False


def audit(observations: Sequence[Mapping], attempts: Sequence[Mapping], as_of: str):
    """Return deterministic diagnostics; every supplied row remains in a population.

    Reasons are nonexclusive row counts by table and dimension. Populations are
    mutually exclusive per named partition. Samples expose at most five owner
    IDs (or input row ordinals for missing IDs), not a large list of row IDs.
    """
    cutoff = _clock(as_of)
    if cutoff is None or not isinstance(as_of, str):
        raise ValueError("as_of must be an ISO timezone-aware datetime string")
    for name, rows in (("observations", observations), ("attempts", attempts)):
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, Mapping)):
            raise TypeError(name + " must be a sequence of mappings")

    reasons = {}
    row_flags = {"observations": [set() for _ in observations],
                 "attempts": [set() for _ in attempts]}
    dimension_flags = {"observations": [set() for _ in observations],
                       "attempts": [set() for _ in attempts]}
    clock_bounds = defaultdict(list)

    def mark(table, index, dimension, reason):
        key = (table, dimension, reason)
        if reason in row_flags[table][index]:
            return
        row_flags[table][index].add(reason)
        dimension_flags[table][index].add(dimension)
        row = (observations if table == "observations" else attempts)[index]
        identity = row.get("observation_id" if table == "observations" else "attempt_id") if isinstance(row, Mapping) else None
        sample = _text(identity) or "row:" + str(index)
        item = reasons.setdefault(key, {"count": 0, "samples": []})
        item["count"] += 1
        item["samples"] = sorted(set(item["samples"] + [sample]))[:5]

    groups = {}
    for table, rows, columns, id_field in (
        ("attempts", attempts, ATTEMPT_COLUMNS, "attempt_id"),
        ("observations", observations, OBSERVATION_COLUMNS, "observation_id"),
    ):
        grouped = defaultdict(list)
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                mark(table, index, "integrity", "invalid_row_type")
                continue
            absent = sorted(set(columns) - set(row))
            if absent:
                mark(table, index, "integrity", "missing_schema_columns")
            for field in columns:
                if field not in row:
                    mark(table, index, "schema", "missing_column:" + field)
            identity = _text(row.get(id_field))
            if identity is None:
                mark(table, index, "integrity", "missing_owner_id")
            else:
                grouped[identity].append(index)
            for field in ("collection_session_id", "provider", "ticker_compat"):
                if _text(row.get(field)) is None:
                    mark(table, index, "integrity", "missing_binding:" + field)
            if row.get("provider") != "yfinance":
                mark(table, index, "integrity", "unsupported_source_provider")
            clocks = ("attempted_at", "completed_at") if table == "attempts" else (
                "provider_observed_at", "system_observed_at", "source_published_at", "source_effective_at"
            )
            for field in clocks:
                value = row.get(field)
                parsed = _clock(value)
                optional = field.startswith("source_")
                if parsed is None:
                    if not optional or not _missing(value):
                        mark(table, index, "temporal", "invalid_or_missing_clock:" + field)
                    elif optional:
                        mark(table, index, "public_information", "missing_public_clock:" + field)
                else:
                    clock_bounds[table + "." + field].append(parsed)
                    if parsed > cutoff and field != "source_effective_at":
                        mark(table, index, "temporal", "clock_after_as_of:" + field)
        groups[table] = grouped
        for identity, indices in grouped.items():
            if len(indices) > 1:
                fingerprints = {_hash(_stable(rows[i])) for i in indices}
                reason = "duplicate_owner_id_exact" if len(fingerprints) == 1 else "duplicate_owner_id_conflicting"
                for index in indices:
                    mark(table, index, "integrity", reason)

    observed_by_attempt = defaultdict(list)
    for index, row in enumerate(observations):
        if isinstance(row, Mapping) and _text(row.get("attempt_id")):
            observed_by_attempt[row["attempt_id"]].append(index)

    for index, row in enumerate(attempts):
        if not isinstance(row, Mapping):
            continue
        status = row.get("status")
        if not isinstance(status, str) or status not in ATTEMPT_STATUSES:
            mark("attempts", index, "integrity", "invalid_attempt_status")
        count = row.get("observation_count")
        count_valid = _measurement(count) == "valid" and count >= 0 and int(count) == count
        if not count_valid:
            mark("attempts", index, "integrity", "invalid_observation_count")
        elif _text(row.get("attempt_id")):
            attached = observed_by_attempt.get(row["attempt_id"], [])
            # Owner counts produced immutable rows, not duplicate input occurrences.
            identities = {observations[i].get("observation_id") for i in attached
                          if _text(observations[i].get("observation_id"))}
            if len(identities) != count:
                mark("attempts", index, "integrity", "observation_count_mismatch")
        payload = row.get("response_payload_hash")
        if not _missing(payload) and (not isinstance(payload, str) or not SHA256.fullmatch(payload)):
            mark("attempts", index, "integrity", "invalid_response_payload_hash")
        if (all(_text(row.get(f)) for f in ("collection_session_id", "provider", "ticker_compat"))
                and (_missing(payload) or (isinstance(payload, str) and SHA256.fullmatch(payload)))):
            owner_hash = _hash((row["collection_session_id"], row["provider"], row["ticker_compat"],
                                None if _missing(payload) else payload))
            if row.get("attempt_id") != owner_hash:
                mark("attempts", index, "integrity", "owner_id_hash_mismatch")
        start, end = _clock(row.get("attempted_at")), _clock(row.get("completed_at"))
        if start and end and start > end:
            mark("attempts", index, "temporal", "attempt_clock_order")
        latency = row.get("latency_ms")
        if not _missing(latency) and (_measurement(latency) != "valid" or latency < 0):
            mark("attempts", index, "integrity", "invalid_latency")
        if not observed_by_attempt.get(_text(row.get("attempt_id"))):
            mark("attempts", index, "coverage", "attempt_without_observations")

    roles = Counter()
    measurement = Counter()
    missingness = Counter()
    for index, row in enumerate(observations):
        if not isinstance(row, Mapping):
            measurement["invalid_row"] += 1
            roles["invalid_row"] += 1
            continue
        value_state = _measurement(row.get("value"))
        measurement[value_state] += 1
        reason = row.get("missingness_reason")
        missingness[_text(reason) or "<NULL>"] += 1
        if value_state == "invalid":
            mark("observations", index, "measurement", "invalid_measurement")
        elif value_state == "missing":
            mark("observations", index, "measurement", "missing_measurement")
            if not isinstance(reason, str) or reason not in MISSINGNESS:
                mark("observations", index, "integrity", "missing_value_without_typed_missingness")
        elif not _missing(reason):
            mark("observations", index, "integrity", "present_value_with_missingness")
        if not _missing(reason) and (not isinstance(reason, str) or reason not in MISSINGNESS):
            mark("observations", index, "integrity", "invalid_missingness")
        kind = row.get("observation_type")
        role = {"average": "central_expectation", "median": "central_expectation",
                "high": "range_bound", "low": "range_bound",
                "covering_analyst_count": "coverage_count", "growth": "growth",
                "year_ago": "historical_comparator"}.get(_text(kind), "invalid_type")
        roles[role] += 1
        if not isinstance(kind, str) or kind not in OBSERVATION_TYPES:
            mark("observations", index, "integrity", "invalid_observation_type")
        metric = row.get("metric")
        expected_class = {"EPS": "earnings_estimate", "revenue": "revenue_estimate"}.get(_text(metric))
        if expected_class is None:
            mark("observations", index, "integrity", "invalid_metric")
        elif row.get("provider_record_class") != expected_class:
            mark("observations", index, "integrity", "metric_record_class_mismatch")
        for field in ("attempt_id", "horizon_label_raw", "provider_payload_hash", "provider_record_class"):
            if _text(row.get(field)) is None:
                mark("observations", index, "integrity", "missing_binding:" + field)
        payload = row.get("provider_payload_hash")
        if not isinstance(payload, str) or not SHA256.fullmatch(payload):
            mark("observations", index, "integrity", "invalid_provider_payload_hash")
        identity_fields = ("collection_session_id", "provider", "provider_record_class", "provider_payload_hash",
                           "ticker_compat", "metric", "horizon_label_raw", "observation_type")
        if all(_text(row.get(f)) for f in identity_fields):
            if row.get("observation_id") != _hash(tuple(row[f] for f in identity_fields)):
                mark("observations", index, "integrity", "owner_id_hash_mismatch")
        if row.get("aggregation_level") != "consensus_snapshot" or not _missing(row.get("contributor_id")):
            mark("observations", index, "integrity", "unsupported_aggregation")
        provider_clock, system_clock = _clock(row.get("provider_observed_at")), _clock(row.get("system_observed_at"))
        if provider_clock and system_clock and provider_clock > system_clock:
            mark("observations", index, "temporal", "provider_after_system")
        publication = _clock(row.get("source_published_at"))
        if publication and provider_clock and publication > provider_clock:
            mark("observations", index, "temporal", "publication_after_capture")
        # Effective time is a separate source fact: never equate it to publication.
        matches = groups["attempts"].get(_text(row.get("attempt_id")), [])
        if not matches:
            mark("observations", index, "integrity", "orphan_attempt_reference")
        elif len(matches) != 1:
            mark("observations", index, "integrity", "ambiguous_attempt_reference")
        else:
            attempt_index = matches[0]
            attempt = attempts[attempt_index]
            for field, attempt_field in (("collection_session_id", "collection_session_id"),
                                         ("provider", "provider"), ("ticker_compat", "ticker_compat"),
                                         ("provider_payload_hash", "response_payload_hash")):
                if row.get(field) != attempt.get(attempt_field):
                    mark("observations", index, "integrity", "attempt_binding_mismatch:" + field)
            if "integrity" in dimension_flags["attempts"][attempt_index]:
                mark("observations", index, "integrity", "referenced_attempt_integrity_error")
            if "temporal" in dimension_flags["attempts"][attempt_index]:
                mark("observations", index, "temporal", "referenced_attempt_temporal_error")
            start, end = _clock(attempt.get("attempted_at")), _clock(attempt.get("completed_at"))
            if start and provider_clock and provider_clock < start:
                mark("observations", index, "temporal", "capture_before_attempt")
            if end and system_clock and system_clock > end:
                mark("observations", index, "temporal", "system_after_attempt_completion")
            if _text(attempt.get("status")) not in {"success", "partial", "malformed"}:
                mark("observations", index, "integrity", "observations_from_nondata_attempt")
        for field in ("unit", "currency", "basis"):
            if _text(row.get(field)) is None:
                mark("observations", index, "economic_basis", "missing_economic_basis:" + field)
        for field in ("issuer_ref", "security_ref"):
            if _text(row.get(field)) is None:
                mark("observations", index, "canonical_identity", "missing_canonical_identity:" + field)
        for field in ("period_end",):
            if _missing(row.get(field)):
                mark("observations", index, "mapped_period", "missing_period_mapping:" + field)
        if not _missing(row.get("period_end")) and not _valid_date(row.get("period_end")):
            mark("observations", index, "mapped_period", "invalid_period_end")
        # A label or caller-added permission field is never an authorization.
        rights = _text(row.get("rights_class"))
        if rights is None or rights == "UNKNOWN":
            mark("observations", index, "rights", "rights_unknown")
        elif rights in {"UNLICENSED", "RIGHTS_BLOCKED", "UNAVAILABLE"}:
            mark("observations", index, "rights", "rights_declared_blocked")
        else:
            mark("observations", index, "rights", "rights_label_unverified")
        if row.get("correction_state") == "missing" and value_state == "valid":
            mark("observations", index, "integrity", "missing_correction_with_present_value")
        supersedes = _text(row.get("supersedes_observation_id"))
        if _text(row.get("correction_state")) not in {"original", "missing", "unchanged", "supersedes"}:
            mark("observations", index, "integrity", "unknown_correction_state")
        if supersedes:
            if row.get("correction_state") != "supersedes":
                mark("observations", index, "integrity", "correction_reference_inconsistent")
            lineage = groups["observations"].get(supersedes, [])
            if not lineage:
                mark("observations", index, "integrity", "orphan_supersedes_reference")
            elif len(lineage) != 1:
                mark("observations", index, "integrity", "ambiguous_supersedes_reference")
            elif supersedes == row.get("observation_id"):
                mark("observations", index, "integrity", "self_supersedes_reference")
            else:
                prior = observations[lineage[0]]
                for field in ("provider", "provider_record_class", "ticker_compat", "metric", "horizon_label_raw", "observation_type"):
                    if row.get(field) != prior.get(field):
                        mark("observations", index, "integrity", "supersedes_grain_mismatch:" + field)
                if (_text(prior.get("period_end")) and _text(row.get("period_end"))
                        and prior.get("period_end") != row.get("period_end")):
                    mark("observations", index, "integrity", "supersedes_fiscal_rollover")
                if _measurement(prior.get("value")) != "valid":
                    mark("observations", index, "integrity", "supersedes_nonpresent_prior")
                if all(_stable(prior.get(f)) == _stable(row.get(f)) for f in ("value", "unit", "currency", "basis")):
                    mark("observations", index, "integrity", "supersedes_unchanged_value_basis")
                prior_clock = _clock(prior.get("system_observed_at"))
                if prior_clock and system_clock and prior_clock > system_clock:
                    mark("observations", index, "temporal", "supersedes_later_knowledge")
        elif row.get("correction_state") == "supersedes":
            mark("observations", index, "integrity", "missing_supersedes_reference")

    # Source owner forces non-count fields to typed missingness when the
    # provider's companion analyst count is unavailable or zero. Audit the
    # retained cross-row shape rather than infer a count from other fields.
    source_groups = defaultdict(list)
    group_fields = ("attempt_id", "provider", "provider_record_class", "ticker_compat", "metric", "horizon_label_raw")
    for index, row in enumerate(observations):
        if isinstance(row, Mapping) and all(_text(row.get(f)) for f in group_fields):
            source_groups[tuple(row[f] for f in group_fields)].append(index)
    for indices in source_groups.values():
        companions = [i for i in indices if observations[i].get("observation_type") == "covering_analyst_count"]
        if len(companions) != 1:
            reason = "missing_covering_count_companion" if not companions else "ambiguous_covering_count_companion"
            for index in indices:
                if observations[index].get("observation_type") != "covering_analyst_count":
                    mark("observations", index, "source_consistency", reason)
            continue
        companion_index = companions[0]
        companion = observations[companion_index]
        state = _measurement(companion.get("value"))
        number = companion.get("value")
        valid_count = state == "valid" and number >= 0 and int(number) == number
        if state == "valid" and not valid_count:
            mark("observations", companion_index, "integrity", "invalid_covering_analyst_count")
        nonestimable = state == "missing" or (state == "valid" and number <= 0)
        uninterpretable = state == "invalid" or not valid_count and not nonestimable
        inconsistent_count = state == "valid" and not _missing(companion.get("missingness_reason"))
        for index in indices:
            row = observations[index]
            if row.get("observation_type") == "covering_analyst_count":
                continue
            if nonestimable and _measurement(row.get("value")) == "valid":
                mark("observations", index, "integrity", "present_measurement_in_nonestimable_group")
            elif uninterpretable or inconsistent_count:
                mark("observations", index, "source_consistency", "uninterpretable_covering_count_companion")

    def frequencies(rows, field):
        counter = Counter()
        for row in rows:
            if isinstance(row, Mapping):
                counter[_text(row.get(field)) or "<NULL_OR_INVALID>"] += 1
            else:
                counter["<INVALID_ROW>"] += 1
        return dict(sorted(counter.items()))

    def dimensions(table):
        counter = Counter(d for flags in dimension_flags[table] for d in flags)
        return dict(sorted(counter.items()))

    lineage_counts = Counter()
    semantic_groups = defaultdict(list)
    semantic_key = ("provider", "provider_record_class", "ticker_compat", "metric", "horizon_label_raw", "observation_type")
    for index, row in enumerate(observations):
        if not isinstance(row, Mapping):
            continue
        lineage_counts["declared_state:" + (_text(row.get("correction_state")) or "<NULL>")] += 1
        if _text(row.get("supersedes_observation_id")):
            lineage_counts["declared_supersedes_references"] += 1
        if (_measurement(row.get("value")) == "valid" and _clock(row.get("system_observed_at"))
                and all(_text(row.get(f)) for f in semantic_key)
                and len(groups["observations"].get(_text(row.get("observation_id")), [])) == 1):
            semantic_groups[tuple(row[f] for f in semantic_key)].append(row)
    for rows in semantic_groups.values():
        rows.sort(key=lambda r: (_clock(r["system_observed_at"]), r["observation_id"]))
        times = Counter(_clock(row["system_observed_at"]) for row in rows)
        for row in rows:
            if times[_clock(row["system_observed_at"])] > 1:
                index = groups["observations"][row["observation_id"]][0]
                mark("observations", index, "source_consistency", "retained_lineage_order_ambiguous")
        for prior, current in zip(rows, rows[1:]):
            current_index = groups["observations"][current["observation_id"]][0]
            if (times[_clock(prior["system_observed_at"])] > 1
                    or _clock(prior["system_observed_at"]) == _clock(current["system_observed_at"])):
                mark("observations", current_index, "source_consistency", "retained_lineage_order_ambiguous")
            elif current.get("correction_state") == "supersedes":
                if current.get("supersedes_observation_id") != prior["observation_id"]:
                    mark("observations", current_index, "integrity", "supersedes_not_latest_retained_present")
            if current.get("correction_state") == "unchanged" and times[_clock(prior["system_observed_at"])] == 1:
                same_basis = all(_stable(prior.get(f)) == _stable(current.get(f))
                                 for f in ("value", "unit", "currency", "basis"))
                p_anchor, c_anchor = _text(prior.get("period_end")), _text(current.get("period_end"))
                if not same_basis or (p_anchor and c_anchor and p_anchor != c_anchor):
                    mark("observations", current_index, "integrity", "unchanged_contradicts_retained_predecessor")
            lineage_counts["retained_adjacent_present_pairs"] += 1
            p, c = _text(prior.get("period_end")), _text(current.get("period_end"))
            if p and c and p != c:
                lineage_counts["declared_period_end_rollover_pairs"] += 1
            else:
                lineage_counts["anchor_missing_pairs" if not p or not c else "same_declared_anchor_pairs"] += 1
                fields = ("value", "unit", "currency", "basis")
                equal = all(_stable(prior.get(f)) == _stable(current.get(f)) for f in fields)
                lineage_counts["unchanged_value_basis_pairs" if equal else "changed_value_basis_pairs"] += 1
    # Coverage is a dependency: a malformed, misbound, late or ambiguous
    # companion cannot qualify its siblings even when its literal value is >0.
    for indices in source_groups.values():
        companions = [i for i in indices if observations[i].get("observation_type") == "covering_analyst_count"]
        if len(companions) == 1 and dimension_flags["observations"][companions[0]].intersection(
                {"integrity", "temporal", "measurement", "source_consistency"}):
            for index in indices:
                if observations[index].get("observation_type") != "covering_analyst_count":
                    mark("observations", index, "source_consistency", "unverifiable_covering_count_companion")
    eligible = 0
    central = 0
    for index, row in enumerate(observations):
        if isinstance(row, Mapping) and _measurement(row.get("value")) == "valid":
            if not dimension_flags["observations"][index].intersection({"integrity", "temporal", "measurement", "source_consistency"}):
                eligible += 1
                if row.get("observation_type") in {"average", "median"}:
                    central += 1
    report = {
        "audit_version": 1,
        "scope": "structural_on_declared_clocks_only",
        "as_of": cutoff.isoformat().replace("+00:00", "Z"),
        "historical_availability_verified": False,
        "predictive_validation": False,
        "financial_authority": {key: False for key in (
            "admission", "rights_authorization", "execution", "position_sizing",
            "ranking", "publication", "residual_computation")},
        "public_information_reconstruction": "UNKNOWN",
        "canonical_identity_validation": "DECLARED_PRESENCE_ONLY",
        "period_mapping_validation": "DECLARED_PRESENCE_ONLY",
        "economic_basis_validation": "DECLARED_PRESENCE_ONLY",
        "readiness": "EMPTY_INPUT" if not observations else "DIAGNOSTIC_ONLY",
        "populations": {
            "semantics": "Each named partition is mutually exclusive; partitions are not additive.",
            "observations": {"rows": len(observations),
                             "mapping_rows": sum(isinstance(r, Mapping) for r in observations),
                             "invalid_row_type": sum(not isinstance(r, Mapping) for r in observations)},
            "attempts": {"rows": len(attempts),
                         "mapping_rows": sum(isinstance(r, Mapping) for r in attempts),
                         "invalid_row_type": sum(not isinstance(r, Mapping) for r in attempts)},
            "measurement_partition": dict(sorted(measurement.items())),
            "observation_role_partition": dict(sorted(roles.items())),
            "declared_capture_comparison_partition": {
                "structurally_eligible_rows": eligible, "excluded_rows": len(observations) - eligible},
            "central_expectation_rows_with_declared_capture_support": central,
        },
        "dimensions": {"semantics": "Nonexclusive affected row counts; never sum across dimensions.",
                       "observations": dimensions("observations"), "attempts": dimensions("attempts")},
        "reasons": [{"table": t, "dimension": d, "reason": r, **value}
                    for (t, d, r), value in sorted(reasons.items())],
        "lineage": {"semantics": "Descriptive retained-row adjacency and declared correction states; nonexclusive, not proof of full history or overwrite safety.",
                    "counts": dict(sorted(lineage_counts.items()))},
        "counts": {
            "unique_collection_sessions": len({_text(r.get("collection_session_id")) for r in observations if isinstance(r, Mapping) and _text(r.get("collection_session_id"))}),
            "unique_attempt_collection_sessions": len({_text(r.get("collection_session_id")) for r in attempts if isinstance(r, Mapping) and _text(r.get("collection_session_id"))}),
            "linked_observation_rows": sum(len(indices) for key, indices in observed_by_attempt.items() if key in groups["attempts"]),
            "declared_attempt_observation_count_sum": sum(int(r["observation_count"]) for r in attempts if isinstance(r, Mapping) and _measurement(r.get("observation_count")) == "valid" and r["observation_count"] >= 0 and int(r["observation_count"]) == r["observation_count"]),
            "unique_metrics": len({_text(r.get("metric")) for r in observations if isinstance(r, Mapping) and _text(r.get("metric"))}),
            "unique_horizons": len({_text(r.get("horizon_label_raw")) for r in observations if isinstance(r, Mapping) and _text(r.get("horizon_label_raw"))}),
            "unique_observation_ids": len(groups["observations"]),
            "unique_attempt_ids": len(groups["attempts"]),
            "unique_observation_tickers": len({_text(r.get("ticker_compat")) for r in observations
                                              if isinstance(r, Mapping) and _text(r.get("ticker_compat"))}),
            "unique_attempt_tickers": len({_text(r.get("ticker_compat")) for r in attempts
                                          if isinstance(r, Mapping) and _text(r.get("ticker_compat"))}),
            "ticker_rows": frequencies(observations, "ticker_compat"),
            "metric_rows": frequencies(observations, "metric"),
            "horizon_rows": frequencies(observations, "horizon_label_raw"),
            "observation_type_rows": frequencies(observations, "observation_type"),
            "attempt_status_rows": frequencies(attempts, "status"),
            "rights_class_rows": frequencies(observations, "rights_class"),
            "missingness_rows": dict(sorted(missingness.items())),
        },
        "clock_bounds": {name: {"min": min(values).isoformat().replace("+00:00", "Z"),
                               "max": max(values).isoformat().replace("+00:00", "Z"),
                               "valid_clock_rows": len(values)}
                         for name, values in sorted(clock_bounds.items())},
        "limitations": [
            "Declared capture clocks and IDs are checked, not independently attested.",
            "Source effective time is economic time, not a knowledge cutoff; publication and capture clocks remain distinct.",
            "Companion analyst-count consistency is checked at source grain; absent companions are unverified.",
            "Missing public clocks permit declared capture comparisons, not public-information replay.",
            "Relative horizons do not establish fiscal periods.",
            "Identity, fiscal mapping, currency and basis are never inferred or joined to current owners.",
            "Rights labels and any caller permission fields confer no authority.",
            "Average/median, bounds, coverage counts, growth and year-ago fields have distinct roles.",
            "No event, actual-result, tradability, price or residual joins are supplied by these two inputs.",
            "No future returns, independent issuer episodes, episode eligibility or predictive qualification are computed.",
            "Raw rows are long-form fields and horizons, not independent estimates or events.",
            "Fiscal labels remain optional; a supplied period_end is only a declared anchor.",
            "Retained snapshot lineage cannot prove full history or overwrite safety.",
        ],
    }
    return report


def _git(repo, *arguments):
    import os
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-C", str(repo), *arguments], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return result.stdout


def _git_path(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or any(p in {"", ".", ".."} for p in value.split("/"))
            or ":" in value or "\x00" in value or "\\" in value):
        raise ValueError("git input paths must be explicit safe repository-relative paths")
    return value


def load_inputs(*, observations_path=None, attempts_path=None, repo=None, revision=None,
                git_observations_path=None, git_attempts_path=None):
    """Read exactly one complete pair; no fallback, provider, writes or lazy Git fetch."""
    local = observations_path is not None or attempts_path is not None
    git = any(v is not None for v in (repo, revision, git_observations_path, git_attempts_path))
    if local == git:
        raise ValueError("supply one complete local or exact Git input pair, mutually exclusive")
    provenance = {"mode": "local_parquet" if local else "git_exact_revision", "inputs": {}}
    blobs = {}
    if local:
        if observations_path is None or attempts_path is None:
            raise ValueError("both local parquet paths are required")
        paths = {"observations": Path(observations_path).resolve(strict=True),
                 "attempts": Path(attempts_path).resolve(strict=True)}
        if paths["observations"] == paths["attempts"] or any(not p.is_file() for p in paths.values()):
            raise ValueError("input pair must contain two distinct regular files")
        before = {name: p.stat() for name, p in paths.items()}
        for name, path in paths.items():
            blobs[name] = path.read_bytes()
            provenance["inputs"][name] = {"path": str(path), "git_blob_id": None}
        after = {name: p.stat() for name, p in paths.items()}
        for name in paths:
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if signature(before[name]) != signature(after[name]):
                raise ValueError("input changed during paired read")
        provenance["source_revision"] = None
        provenance["pairing"] = "both explicitly supplied; stable during read; shared historical origin unverified"
    else:
        if any(v is None for v in (repo, revision, git_observations_path, git_attempts_path)):
            raise ValueError("repo, full revision, and both Git parquet paths are required")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("revision must be a full lowercase 40hex commit ID")
        paths = {"observations": _git_path(git_observations_path),
                 "attempts": _git_path(git_attempts_path)}
        if paths["observations"] == paths["attempts"]:
            raise ValueError("Git input paths must be distinct")
        if _git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip() != revision:
            raise ValueError("revision must identify the exact commit")
        for name, path in paths.items():
            spec = revision + ":" + path
            if _git(repo, "cat-file", "-t", spec).decode().strip() != "blob":
                raise ValueError("Git input must be a blob")
            blobs[name] = _git(repo, "show", spec)
            provenance["inputs"][name] = {
                "path": path, "git_blob_id": _git(repo, "rev-parse", "--verify", spec).decode().strip()}
        provenance["source_revision"] = revision
        provenance["pairing"] = "two blobs at one exact commit"
    for name, blob in blobs.items():
        if not blob.startswith(b"PAR1") or not blob.endswith(b"PAR1"):
            raise ValueError(name + " input is not a parquet byte stream (LFS pointers are not data)")
        provenance["inputs"][name].update({"sha256": hashlib.sha256(blob).hexdigest(),
                                           "byte_count": len(blob)})
    import pandas as pd
    # Arrow nullable decoding preserves parquet NULL separately from IEEE NaN.
    # A default float frame would turn both into NaN and misclassify missing rows.
    decoded = {name: pd.read_parquet(io.BytesIO(blob), dtype_backend="pyarrow").to_dict("records") for name, blob in blobs.items()}
    return decoded["observations"], decoded["attempts"], provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--observations-path")
    parser.add_argument("--attempts-path")
    parser.add_argument("--repo")
    parser.add_argument("--revision")
    parser.add_argument("--git-observations-path")
    parser.add_argument("--git-attempts-path")
    args = parser.parse_args(argv)
    try:
        if _clock(args.as_of) is None:
            raise ValueError("as_of must be an ISO timezone-aware datetime")
        observations, attempts, provenance = load_inputs(
            observations_path=args.observations_path, attempts_path=args.attempts_path,
            repo=args.repo, revision=args.revision,
            git_observations_path=args.git_observations_path, git_attempts_path=args.git_attempts_path)
        report = audit(observations, attempts, args.as_of)
        report["input_provenance"] = provenance
        print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    except (ValueError, TypeError, OSError, subprocess.SubprocessError, ImportError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
