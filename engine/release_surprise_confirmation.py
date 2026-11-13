"""MRI-owned, point-in-time macro surprise evidence; never a trading signal.

Official facts remain release_actual.v1. Economist polls are a separate typed
baseline, never a median of model forecasts and prediction-market observations.
All clocks are explicit UTC instants. This module performs no network or writes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from engine.rates_command_basis import RIGHTS_VALUES
from engine.release_actuals import canonical_actual, receipt_integrity_errors

SCHEMA = "release_surprise_confirmation.v1"
CONSENSUS_SCHEMA = "release_consensus.v1"
CONTEXT_SCHEMA = "release_surprise_context.v1"
ACTUALS_PATH = "data/release_forecast/official_actuals.jsonl"
CONSENSUS_PATH = "data/release_forecast/consensus_snapshots.jsonl"
DEFECTS_PATH = "data/release_forecast/official_actual_defects.json"
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_INPUT_ROWS = 100_000
PAIR_DEFINITIONS = (
    ("cpi_headline_ppi_headline", "cpi_headline", "ppi_finaldemand"),
    ("cpi_core_ppi_headline", "cpi_core", "ppi_finaldemand"),
)
CONSUMERS = frozenset({"prophet", "sector_intelligence", "event_windows", "release_radar"})
_USE_SCOPES = frozenset({"internal_research", "display_derived", "display_raw"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT = re.compile(r"^consensus:[0-9a-f]{24}$")
_INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


class EvidenceError(ValueError):
    """A named data-contract failure, not permission to repair an upstream fact."""


def authority() -> dict[str, bool]:
    return {name: False for name in ("can_score", "can_rank", "can_gate", "can_size", "can_trade")}


def valid_authority(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == set(authority()) and all(v is False for v in value.values())


def validate_pair_projection(pair: Any) -> None:
    if not isinstance(pair, dict) or not valid_authority(pair.get("authority")) or pair.get("display_derived_allowed") is not True:
        raise EvidenceError("pair_authority_or_rights_violation")
    if pair.get("pair_id") not in {p[0] for p in PAIR_DEFINITIONS}:
        raise EvidenceError("unknown_pair_definition")
    cpi, ppi = finite(pair.get("cpi_surprise")), finite(pair.get("ppi_surprise"))
    directions = tuple("hot" if x > 0 else "cold" if x < 0 else "neutral" for x in (cpi, ppi))
    expected = "neutral_or_mixed_neutral" if "neutral" in directions else "cpi_" + directions[0] + "_ppi_" + directions[1]
    agreement = None if "neutral" in directions else directions[0] == directions[1]
    if pair.get("quadrant") != expected or pair.get("agreement") is not agreement:
        raise EvidenceError("inconsistent_pair_semantics")
    if instant(pair.get("known_at")) != max(instant(pair.get("cpi_known_at")), instant(pair.get("ppi_known_at"))):
        raise EvidenceError("pair_clock_not_second_report")


def instant(value: Any) -> datetime:
    if not isinstance(value, str) or not _INSTANT.fullmatch(value):
        raise EvidenceError("timestamp_requires_explicit_offset_and_seconds")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid_timestamp") from exc
    if result.utcoffset() is None:
        raise EvidenceError("naive_timestamp")
    return result.astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EvidenceError("finite_number_required")
    return float(value)


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seal(value: dict) -> dict:
    value["evidence_digest"] = digest({k: v for k, v in value.items() if k != "evidence_digest"})
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise EvidenceError("invalid_" + name)
    return value


def normalize_consensus(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one immutable poll snapshot; a rights field is evidence, not a grant.

    The ingestion owner must set recorded_at itself. Backfilled estimates with a
    post-release recorded_at are retained for disclosure but never used as if the
    system possessed them before the release. A future separately qualified
    vendor-vintage research mode must not silently weaken this contract.
    """
    if not isinstance(raw, Mapping) or raw.get("schema") != CONSENSUS_SCHEMA:
        raise EvidenceError("consensus_schema_mismatch")
    if raw.get("baseline_kind") != "economist_consensus":
        raise EvidenceError("not_economist_consensus")
    result: dict[str, Any] = {"schema": CONSENSUS_SCHEMA, "baseline_kind": "economist_consensus"}
    for key in ("release", "period", "exact_target_id", "unit", "source_id", "source_url"):
        result[key] = _text(raw.get(key), key)
    if result["unit"] not in {"percent", "thousands"}:
        raise EvidenceError("unsupported_consensus_unit")
    try:
        stamp = result["period"]
        if len(stamp) == 7:
            datetime.strptime(stamp, "%Y-%m")
        elif len(stamp) == 10:
            datetime.strptime(stamp, "%Y-%m-%d")
        else:
            raise ValueError
    except ValueError as exc:
        raise EvidenceError("invalid_reference_period") from exc
    url = urlsplit(result["source_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise EvidenceError("invalid_source_url")
    source_hash = raw.get("source_sha256")
    if not isinstance(source_hash, str) or not _HEX64.fullmatch(source_hash):
        raise EvidenceError("invalid_source_sha256")
    result["source_sha256"] = source_hash
    result["value"] = finite(raw.get("value"))
    times = {key: instant(raw.get(key)) for key in
             ("forecast_at", "observed_at", "recorded_at", "release_at")}
    if not times["forecast_at"] <= times["observed_at"] <= times["recorded_at"]:
        raise EvidenceError("consensus_clock_order_invalid")
    # Late records can be retained, but select_consensus below refuses them.
    if times["forecast_at"] >= times["release_at"]:
        raise EvidenceError("forecast_not_pre_release")
    result.update({key: iso(value) for key, value in times.items()})
    rights = raw.get("rights", "unknown")
    if rights not in RIGHTS_VALUES:
        raise EvidenceError("unknown_rights_vocabulary")
    scopes = raw.get("use_scopes", [])
    if not isinstance(scopes, list) or any(not isinstance(x, str) or x not in _USE_SCOPES for x in scopes):
        raise EvidenceError("invalid_use_scopes")
    if rights == "display_only" and "internal_research" in scopes:
        raise EvidenceError("display_only_rights_block_research")
    result["rights"] = rights
    result["use_scopes"] = sorted(set(scopes))
    result["rights_ref"] = raw.get("rights_ref")
    if rights != "unknown":
        _text(result["rights_ref"], "rights_ref")
    if rights == "unknown" and scopes:
        raise EvidenceError("unknown_rights_cannot_authorize_use")
    supersedes = raw.get("supersedes_receipt_id")
    if supersedes is not None:
        if not isinstance(supersedes, str) or not _RECEIPT.fullmatch(supersedes):
            raise EvidenceError("invalid_supersedes_receipt")
        result["supersedes_receipt_id"] = supersedes
    receipt = "consensus:" + digest(result)[:24]
    if raw.get("receipt_id") not in (None, receipt):
        raise EvidenceError("consensus_receipt_hash_mismatch")
    result["receipt_id"] = receipt
    return result


def _target(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(key) for key in ("release", "period", "exact_target_id", "unit"))


def _actual_known(row: Mapping[str, Any]) -> datetime:
    return max(instant(row.get(key)) for key in ("source_released_at", "observed_at", "verified_at"))


def _select_consensus(rows: list[dict], actual: dict, *, source_id: str | None) -> tuple[dict | None, str | None]:
    publication = instant(actual.get("source_released_at"))
    matches = [r for r in rows if _target(r) == _target(actual)]
    if source_id is not None:
        matches = [r for r in matches if r["source_id"] == source_id]
    if not matches:
        return None, "matching_economist_consensus_missing"
    eligible = [r for r in matches
                if instant(r["release_at"]) == publication
                and instant(r["recorded_at"]) < publication
                and r["rights"] != "unknown"
                and "internal_research" in r["use_scopes"]]
    if not eligible:
        return None, "consensus_not_pit_or_rights_qualified"
    if len({r["source_id"] for r in eligible}) != 1:
        return None, "ambiguous_consensus_sources"
    latest_at = max(instant(r["forecast_at"]) for r in eligible)
    latest = [r for r in eligible if instant(r["forecast_at"]) == latest_at]
    ids = {r["receipt_id"]: r for r in eligible}
    for row in latest:
        prior_id = row.get("supersedes_receipt_id")
        if prior_id is not None:
            prior = ids.get(prior_id)
            if prior is None or _target(prior) != _target(row) or instant(prior["recorded_at"]) >= instant(row["recorded_at"]):
                return None, "invalid_consensus_correction_lineage"
    superseded = {r["supersedes_receipt_id"] for r in latest if r.get("supersedes_receipt_id")}
    latest = [r for r in latest if r["receipt_id"] not in superseded]
    if len({r["value"] for r in latest}) != 1:
        return None, "conflicting_consensus_snapshot"
    return max(latest, key=lambda r: (instant(r["recorded_at"]), r["receipt_id"])), None


def build_surprise_history(
    actuals: Iterable[dict], consensus: Iterable[dict], *, asof: str,
    defects_path: str | Path, consensus_source_id: str | None = None,
    min_history: int = 12, max_history: int = 60, max_capture_lag_hours: float = 24.0,
) -> dict[str, Any]:
    """Join canonical first prints to pre-release polls, then lag-normalize.

    Normalization uses only earlier *available* observations of the same release,
    target, unit and poll source. Neither the current print nor future data fit it.
    """
    cutoff = instant(asof)
    if not (2 <= min_history <= max_history <= 240):
        raise EvidenceError("invalid_normalization_window")
    lag = finite(max_capture_lag_hours)
    if not 0 < lag <= 168:
        raise EvidenceError("invalid_capture_lag")
    reasons: Counter[str] = Counter()
    snapshots: dict[str, dict] = {}
    quarantined_targets: set[tuple] = set()
    actual_rows = list(actuals)
    consensus_rows = list(consensus)
    for raw in consensus_rows:
        try:
            row = normalize_consensus(raw)
            if instant(row["recorded_at"]) > cutoff:
                reasons["consensus_future_at_cutoff"] += 1
                continue
            snapshots[row["receipt_id"]] = row
        except (EvidenceError, TypeError, ValueError) as exc:
            reasons["consensus_invalid:" + str(exc)] += 1
            if isinstance(raw, Mapping):
                try:
                    if instant(raw.get("recorded_at")) > cutoff:
                        continue
                except EvidenceError:
                    pass
                target = _target(raw)
                if all(isinstance(v, str) for v in target):
                    quarantined_targets.add(target)
    eligible_actuals: list[dict] = []
    for row in actual_rows:
        try:
            errors = receipt_integrity_errors(row, defects_path=defects_path)
        except (ValueError, TypeError, KeyError):
            errors = ["malformed_actual_contract"]
        if errors:
            reasons["actual_invalid:" + errors[0]] += 1
            continue
        try:
            finite(row.get("actual"))
            known = _actual_known(row)
            published = instant(row["source_released_at"])
        except EvidenceError:
            reasons["actual_publication_clock_unknown"] += 1
            continue
        if known > cutoff:
            reasons["actual_future_at_cutoff"] += 1
        elif known - published > timedelta(hours=lag):
            reasons["actual_capture_too_late"] += 1
        else:
            eligible_actuals.append(row)
    by_actual: dict[tuple, list] = defaultdict(list)
    by_poll: dict[tuple, list] = defaultdict(list)
    for row in eligible_actuals:
        by_actual[(row["release"], row["period"])].append(row)
    for row in snapshots.values():
        by_poll[_target(row)].append(row)
    keys = sorted(by_actual)
    events: list[dict] = []
    for release, period in keys:
        candidates = by_actual[(release, period)]
        if len({(r["actual"], r["exact_target_id"], r["unit"]) for r in candidates}) != 1:
            reasons["conflicting_first_prints"] += 1
            continue
        actual = canonical_actual(candidates, release, period, defects_path=defects_path)
        if actual is None:
            reasons["canonical_actual_unavailable"] += 1
            continue
        if _target(actual) in quarantined_targets:
            reasons["consensus_target_quarantined"] += 1
            continue
        poll, reason = _select_consensus(by_poll.get(_target(actual), []), actual, source_id=consensus_source_id)
        if poll is None:
            reasons[reason or "consensus_unavailable"] += 1
            continue
        # Published decimal surprises: no floating-point epsilon invents a sign.
        from decimal import Decimal
        surprise = float(Decimal(str(actual["actual"])) - Decimal(str(poll["value"])))
        state = "hot" if surprise > 0 else "cold" if surprise < 0 else "neutral"
        known_at = iso(_actual_known(actual))
        event_id = "macro_surprise:" + digest([actual["receipt_id"], poll["receipt_id"]])[:24]
        events.append({
            "event_id": event_id, "release": release, "period": period,
            "exact_target_id": actual["exact_target_id"], "unit": actual["unit"],
            "actual": actual["actual"], "consensus": poll["value"], "surprise": surprise,
            "surprise_unit": "percentage_points" if actual["unit"] == "percent" else actual["unit"],
            "direction": state, "release_at": iso(instant(actual["source_released_at"])),
            "known_at": known_at, "actual_receipt_id": actual["receipt_id"],
            "consensus_receipt_id": poll["receipt_id"], "consensus_source_id": poll["source_id"],
            "source_refs": [actual["source_url"], poll["source_url"]],
            "display_derived_allowed": "display_derived" in poll["use_scopes"],
            "display_raw_allowed": "display_raw" in poll["use_scopes"],
            "rights": poll["rights"], "rights_ref": poll["rights_ref"],
            "authority": authority(),
        })
    events.sort(key=lambda row: (instant(row["known_at"]), row["event_id"]))
    normalization_history: dict[tuple, list] = defaultdict(list)
    for event in events:
        history_key = (event["release"], event["exact_target_id"], event["unit"], event["consensus_source_id"])
        prior = [r for r in normalization_history[history_key]
                 if r["release"] == event["release"]
                 and r["exact_target_id"] == event["exact_target_id"]
                 and r["unit"] == event["unit"]
                 and r["consensus_source_id"] == event["consensus_source_id"]
                 and instant(r["known_at"]) < instant(event["release_at"])][-max_history:]
        normalization_history[history_key].append(event)
        # Bounded past buffer; delayed arrivals still require the clock filter.
        normalization_history[history_key] = normalization_history[history_key][-max_history-2:]
        values = [r["surprise"] for r in prior]
        sd = stdev(values) if len(values) >= min_history else None
        event["normalization"] = {
            "n_prior": len(values), "window_max": max_history, "min_history": min_history,
            "mean_prior": mean(values) if values else None, "sd_prior": sd,
            "scaled_surprise": event["surprise"] / sd if sd and sd > 0 else None,
            "zscore": (event["surprise"] - mean(values)) / sd if sd and sd > 0 else None,
            "status": "available" if sd and sd > 0 else "insufficient_or_zero_variance_history",
            "basis": "same_target_and_poll_source_known_before_release",
            "display_derived_allowed": all(r["display_derived_allowed"] for r in prior),
        }
    return {"events": events, "reason_counts": dict(sorted(reasons.items())),
            "input_counts": {"actual_rows": len(actual_rows), "consensus_rows": len(consensus_rows)},
            "eligible_event_count": len(events), "asof": iso(cutoff),
            "latest_inflation_period": max((r["period"] for r in eligible_actuals
                if r["release"] in {"cpi_headline", "cpi_core", "ppi_finaldemand"}), default=None)}


def build_confirmation_pairs(events: Iterable[dict]) -> list[dict]:
    """Same reference period, explicit headline/core variant; second clock wins."""
    indexed = {}
    for event in events:
        key = (event["release"], event["period"])
        if key in indexed:
            raise EvidenceError("duplicate_release_period")
        indexed[key] = event
    periods = sorted({period for _, period in indexed if len(period) == 7})
    pairs: list[dict] = []
    for pair_id, cpi_release, ppi_release in PAIR_DEFINITIONS:
        for period in periods:
            cpi, ppi = indexed.get((cpi_release, period)), indexed.get((ppi_release, period))
            if cpi is None or ppi is None:
                continue
            directions = (cpi["direction"], ppi["direction"])
            if "neutral" in directions:
                quadrant, agreement = "neutral_or_mixed_neutral", None
            else:
                quadrant = "cpi_" + directions[0] + "_ppi_" + directions[1]
                agreement = directions[0] == directions[1]
            known_at = iso(max(instant(cpi["known_at"]), instant(ppi["known_at"])))
            pairs.append({
                "event_id": "macro_pair:" + digest([pair_id, cpi["event_id"], ppi["event_id"]])[:24],
                "pair_id": pair_id, "period": period, "known_at": known_at,
                "cpi_event_id": cpi["event_id"], "ppi_event_id": ppi["event_id"],
                "cpi_release": cpi_release, "ppi_release": ppi_release,
                "cpi_surprise": cpi["surprise"], "ppi_surprise": ppi["surprise"],
                "cpi_zscore": cpi["normalization"]["zscore"],
                "ppi_zscore": ppi["normalization"]["zscore"],
                "display_zscore_allowed": cpi["normalization"]["display_derived_allowed"] and ppi["normalization"]["display_derived_allowed"],
                "quadrant": quadrant, "agreement": agreement,
                "cpi_known_at": cpi["known_at"], "ppi_known_at": ppi["known_at"],
                "display_derived_allowed": cpi["display_derived_allowed"] and ppi["display_derived_allowed"],
                "source_refs": sorted(set(cpi["source_refs"] + ppi["source_refs"])),
                "authority": authority(),
            })
    return sorted(pairs, key=lambda row: (instant(row["known_at"]), row["pair_id"]))


def read_jsonl(path: Path) -> tuple[list[dict], dict]:
    """Missing, empty, malformed and oversized are different observed states."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
    except FileNotFoundError:
        return [], {"status": "missing", "sha256": None, "rows": 0}
    except OSError:
        return [], {"status": "unreadable", "sha256": None, "rows": 0}
    if len(raw) > MAX_INPUT_BYTES:
        return [], {"status": "oversized", "sha256": None, "rows": 0}
    signature = hashlib.sha256(raw).hexdigest()
    try:
        def bad_constant(_: str) -> None:
            raise EvidenceError("nonfinite_json")
        rows = []
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line, parse_constant=bad_constant)
            if not isinstance(row, dict) or len(rows) >= MAX_INPUT_ROWS:
                raise EvidenceError("invalid_jsonl_row_or_limit")
            rows.append(row)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        return [], {"status": "invalid", "sha256": signature, "rows": 0}
    return rows, {"status": "ready" if rows else "empty", "sha256": signature, "rows": len(rows)}


def unavailable(reason: str, *, asof: str, status: str = "unavailable") -> dict:
    return seal({"schema": SCHEMA, "asof": iso(instant(asof)), "status": status,
            "display_only": True, "authority": authority(), "reason_codes": [reason],
            "latest_pairs": [], "latest_releases": [], "research_status": "not_validated",
            "trade_recommendation": None})


def build_confirmation_artifact(root: str | Path, *, asof: str, consensus_source_id: str | None = None) -> dict:
    root = Path(root)
    instant(asof)
    actuals, actual_meta = read_jsonl(root / ACTUALS_PATH)
    polls, poll_meta = read_jsonl(root / CONSENSUS_PATH)
    input_meta = {"official_actuals": actual_meta, "economist_consensus": poll_meta}
    bad = {"invalid", "unreadable", "oversized"}
    if any(meta["status"] in bad for meta in input_meta.values()):
        result = unavailable("input_integrity_failure", asof=asof, status="input_invalid")
        result["inputs"] = input_meta
        return seal(result)
    history = build_surprise_history(actuals, polls, asof=asof, defects_path=root / DEFECTS_PATH,
                                     consensus_source_id=consensus_source_id)
    all_pairs = build_confirmation_pairs(history["events"])
    display_pairs = [p for p in all_pairs if p["display_derived_allowed"]]
    latest_pairs = []
    for pair_id, _, _ in PAIR_DEFINITIONS:
        candidates = [p for p in display_pairs if p["pair_id"] == pair_id]
        if candidates:
            latest = dict(candidates[-1])
            if not latest["display_zscore_allowed"]:
                latest["cpi_zscore"] = latest["ppi_zscore"] = None
            latest["freshness"] = "stale" if instant(asof) - instant(latest["known_at"]) > timedelta(days=45) else "current"
            if history["latest_inflation_period"] and latest["period"] < history["latest_inflation_period"]:
                latest["freshness"] = "superseded_by_incomplete_period"
            latest_pairs.append(latest)
    display_events = []
    for event in history["events"][-16:]:
        if not event["display_derived_allowed"]:
            continue
        projected = dict(event)
        if not event["normalization"]["display_derived_allowed"]:
            projected["normalization"] = {"status": "derived_display_rights_unavailable", "zscore": None}
        if not event["display_raw_allowed"]:
            projected.pop("actual", None)
            projected.pop("consensus", None)
        display_events.append(projected)
    reasons = list(history["reason_counts"])
    if poll_meta["status"] in {"missing", "empty"}:
        reasons.insert(0, "economist_consensus_history_unavailable")
    if not all_pairs:
        reasons.append("paired_release_history_unavailable")
    elif not display_pairs:
        reasons.append("derived_display_rights_unavailable")
    result = unavailable(reasons[0] if reasons else "research_not_validated", asof=asof)
    result.update({
        "status": "available_descriptive" if latest_pairs else "partial" if display_events else "unavailable",
        "inputs": input_meta, "reason_codes": sorted(set(reasons)),
        "reason_counts": history["reason_counts"], "eligible_event_count": history["eligible_event_count"],
        "paired_period_count": len({p["period"] for p in all_pairs}),
        "latest_inflation_period": history["latest_inflation_period"],
        "latest_pairs": latest_pairs, "latest_releases": display_events,
        "methodology": {"baseline_kind": "economist_consensus", "actual_basis": "official_first_print",
                        "entry_rule": "first_session_close_strictly_after_signal_known_at",
                        "neutral_policy": "separate_not_hot_or_cold", "consensus_source_id": consensus_source_id,
                        "core_ppi": "not_supported_by_current_official_actual_owner",
                        "accuracy_claim": "withheld_until_independently_validated_forward_evidence"},
    })
    if latest_pairs and not any(p["freshness"] == "current" for p in latest_pairs):
        result["status"] = "historical_context_only"
        result["reason_codes"].append("no_current_complete_pair")
    return seal(result)


def read_consumer_context(root: str | Path, *, consumer: str, asof: str, max_age_hours: float = 72.0) -> dict:
    """Existing MRI artifact -> descriptive consumer; no recalc or second writer."""
    if consumer not in CONSUMERS:
        raise EvidenceError("unknown_consumer")
    cutoff = instant(asof)
    if not 0 < finite(max_age_hours) <= 168:
        raise EvidenceError("invalid_max_age_hours")
    result = {"schema": CONTEXT_SCHEMA, "consumer": consumer, "asof": iso(cutoff),
              "status": "unavailable", "display_only": True, "authority": authority(),
              "latest_pairs": [], "reason_codes": [], "research_status": "not_validated"}
    root = Path(root)
    primary = root / "data/release_forecast/latest.json"
    path = primary if primary.exists() else root / "site/macrodata/release_forecast.json"
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise EvidenceError("artifact_oversized")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise EvidenceError("release_forecast_invalid")
        evidence = payload.get("surprise_confirmation")
        if payload.get("schema") != "release_forecast.v2" or not isinstance(evidence, dict) or evidence.get("schema") != SCHEMA:
            raise EvidenceError("confirmation_artifact_unavailable")
        if not valid_authority(evidence.get("authority")) or evidence.get("display_only") is not True:
            raise EvidenceError("authority_ceiling_violation")
        if evidence.get("status") not in {"unavailable", "input_invalid", "partial", "available_descriptive", "historical_context_only"}:
            raise EvidenceError("unknown_confirmation_status")
        produced = instant(evidence.get("asof"))
        if produced > cutoff or cutoff - produced > timedelta(hours=max_age_hours):
            raise EvidenceError("artifact_stale_or_future")
        if evidence.get("evidence_digest") != digest({k: v for k, v in evidence.items() if k != "evidence_digest"}):
            raise EvidenceError("evidence_digest_mismatch")
        pairs = evidence.get("latest_pairs")
        if not isinstance(pairs, list):
            raise EvidenceError("invalid_pair_projection")
        for pair in pairs:
            validate_pair_projection(pair)
            if instant(pair.get("known_at")) > cutoff:
                raise EvidenceError("future_pair")
            if cutoff - instant(pair["known_at"]) > timedelta(days=45):
                pair["freshness"] = "stale"
        result.update({"status": evidence["status"], "source_asof": evidence["asof"],
                       "source_digest": evidence["evidence_digest"], "latest_pairs": pairs,
                       "reason_codes": evidence.get("reason_codes", []),
                       "paired_period_count": evidence.get("paired_period_count", 0)})
        if pairs and not any(p.get("freshness") == "current" for p in pairs):
            result["status"] = "historical_context_only"
    except FileNotFoundError:
        result["reason_codes"] = ["release_forecast_missing"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result["reason_codes"] = [str(exc) if isinstance(exc, EvidenceError) else "release_forecast_invalid"]
    return result
