"""Pure Early Leadership / Sector Rotation evidence compiler.

This module is deliberately downstream of existing owners:
- GMI owns theme_state/v1 and membership/peer evidence;
- Technical Opportunity / setup owners own setup state;
- B4/entry owners own current geometry and Availability;
- Evaluation owns whether these observations improve selection.

It creates no ThemeState, candidate episode, score, rank, entry verdict, plan, or
trade authority.  Its job is to bind source-qualified observations into a
comparable research feature envelope for B10/H1-style evaluation.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from typing import Any, Mapping

SCHEMA = "prophet.early_leadership_evidence/v1"
PEER_SCHEMA = "prophet.peer_ex_candidate/v1"
CANDIDATE_SCHEMA = "prophet.stock_window_observation/v1"
EXPOSURE_SCHEMA = "prophet.economic_exposure_read/v1"
SETUP_SCHEMA = "prophet.owner_setup_observation/v1"
GEOMETRY_SCHEMA = "prophet.owner_entry_geometry_read/v1"

_SETUP_STATES = frozenset({
    "FORMING", "ARMED", "TRIGGERED", "CONFIRMED", "FAILED", "EXTENDED", "UNKNOWN"
})
_EXPOSURE_STATES = frozenset({
    "CONFIRMED_DIRECT", "CONFIRMED_INDIRECT", "MEMBERSHIP_ONLY", "UNAVAILABLE"
})
_AUTHORITY = {
    "can_rank": False,
    "can_gate_candidate_admission": False,
    "can_compute_b4_availability": False,
    "can_originate_plan": False,
    "can_change_entry_open": False,
    "can_size": False,
    "can_publish_trade_instruction": False,
    "can_execute": False,
    "can_trade": False,
}
_PROHIBITED_INPUTS = frozenset({
    "board_rank", "score_rank", "display_rank", "featured", "manual_action",
    "plan_status", "future_return", "fwd_return", "outcome", "hit_target",
})


class EarlyLeadershipEvidenceError(ValueError):
    """The source observations cannot be combined without changing their meaning."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EarlyLeadershipEvidenceError(name)
    return value.strip()


def _num(value: Any, name: str) -> float:
    if value is None or isinstance(value, bool):
        raise EarlyLeadershipEvidenceError(name)
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EarlyLeadershipEvidenceError(name) from exc
    if not isfinite(out):
        raise EarlyLeadershipEvidenceError(name)
    return out


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise EarlyLeadershipEvidenceError(name)
    return value


def _ratio(value: Any, name: str) -> float:
    out = _num(value, name)
    if not 0.0 <= out <= 1.0:
        raise EarlyLeadershipEvidenceError(name)
    return out


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise EarlyLeadershipEvidenceError(name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EarlyLeadershipEvidenceError(name) from exc
    if dt.tzinfo is None:
        raise EarlyLeadershipEvidenceError(name)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    """Canonical UTC text without discarding a material subsecond instant."""
    utc = dt.astimezone(timezone.utc)
    timespec = "microseconds" if utc.microsecond else "seconds"
    return utc.isoformat(timespec=timespec).replace("+00:00", "Z")


def _require_known(row: Mapping[str, Any], decision: datetime) -> str:
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if known > decision:
        raise EarlyLeadershipEvidenceError("future_evidence_not_allowed")
    return _iso(known)


def _closed(row: Mapping[str, Any], keys: set[str], name: str) -> None:
    if not isinstance(row, Mapping):
        raise EarlyLeadershipEvidenceError(f"{name}_not_object")
    extras = set(row) - keys
    if extras:
        if extras & _PROHIBITED_INPUTS:
            raise EarlyLeadershipEvidenceError(f"{name}_contains_prohibited_feedback_input")
        raise EarlyLeadershipEvidenceError(f"{name}_fields_not_closed")


def _source_ref(row: Mapping[str, Any]) -> str:
    return _text(row.get("source_ref"), "source_ref_missing_or_invalid")


_SETUP_LINEAGE_FIELDS = ("identity_epoch", "episode_id", "candidate_generation_id")


def _setup_lineage(row: Mapping[str, Any], owner: str) -> dict[str, str | None]:
    """Preserve an existing owner's complete binding; never allocate or infer it."""
    values = {field: row.get(field) for field in _SETUP_LINEAGE_FIELDS}
    if all(value is None for value in values.values()):
        return values
    if any(value is None for value in values.values()):
        raise EarlyLeadershipEvidenceError(f"{owner}_setup_lineage_incomplete")
    return {field: _text(value, f"{owner}_setup_lineage_invalid")
            for field, value in values.items()}


def _candidate(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {
        "schema", "issuer_id", "security_id", "ticker", "theme_id", "asof",
        "known_at", "return_window_sessions", "return_basis",
        "stock_return", "market_return", "market_id", "source_ref",
        *_SETUP_LINEAGE_FIELDS,
    }
    _closed(row, keys, "candidate")
    if row.get("schema") != CANDIDATE_SCHEMA:
        raise EarlyLeadershipEvidenceError("candidate_schema_invalid")
    window = _integer(row.get("return_window_sessions"), "candidate_window_invalid", minimum=1)
    asof = _utc(row.get("asof"), "candidate_asof_invalid")
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if asof > known or known > decision:
        raise EarlyLeadershipEvidenceError("candidate_clock_invalid")
    return {
        **_setup_lineage(row, "candidate"),
        "issuer_id": _text(row.get("issuer_id"), "candidate_issuer_invalid"),
        "security_id": _text(row.get("security_id"), "candidate_security_invalid"),
        "ticker": _text(row.get("ticker"), "candidate_ticker_invalid"),
        "theme_id": _text(row.get("theme_id"), "candidate_theme_invalid"),
        "asof": _iso(asof),
        "known_at": _iso(known),
        "return_window_sessions": window,
        "return_basis": _text(row.get("return_basis"), "candidate_return_basis_invalid"),
        "stock_return": _num(row.get("stock_return"), "candidate_stock_return_invalid"),
        "market_return": _num(row.get("market_return"), "candidate_market_return_invalid"),
        "market_id": _text(row.get("market_id"), "candidate_market_id_invalid"),
        "source_ref": _source_ref(row),
    }


def _peer(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {
        "schema", "candidate_issuer_id", "candidate_security_id", "theme_id",
        "asof", "known_at", "membership_vintage", "return_window_sessions",
        "return_basis", "candidate_excluded", "issuer_aliases_excluded",
        "peer_member_count", "priced_peer_count", "coverage",
        "equal_weight_return", "median_return", "positive_share", "source_ref",
    }
    _closed(row, keys, "peer")
    if row.get("schema") != PEER_SCHEMA:
        raise EarlyLeadershipEvidenceError("peer_schema_invalid")
    if row.get("candidate_excluded") is not True:
        raise EarlyLeadershipEvidenceError("candidate_must_be_excluded_from_peers")
    if row.get("issuer_aliases_excluded") is not True:
        raise EarlyLeadershipEvidenceError("issuer_aliases_must_be_excluded_from_peers")

    total = _integer(row.get("peer_member_count"), "peer_member_count_invalid")
    priced = _integer(row.get("priced_peer_count"), "priced_peer_count_invalid")
    if priced > total:
        raise EarlyLeadershipEvidenceError("priced_peer_count_exceeds_membership")
    coverage = _ratio(row.get("coverage"), "peer_coverage_invalid")
    expected_coverage = 0.0 if total == 0 else priced / total
    if abs(coverage - expected_coverage) > 1e-9:
        raise EarlyLeadershipEvidenceError("peer_coverage_count_mismatch")

    asof = _utc(row.get("asof"), "peer_asof_invalid")
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if asof > known or known > decision:
        raise EarlyLeadershipEvidenceError("peer_clock_invalid")

    if priced <= 1:
        state = "UNAVAILABLE_SINGLETON_OR_EMPTY"
        for key in ("equal_weight_return", "median_return", "positive_share"):
            if row.get(key) is not None:
                raise EarlyLeadershipEvidenceError("singleton_peer_metrics_must_be_null")
        ew = med = pos = None
    else:
        state = "MEASURED" if priced == total else "PARTIAL"
        ew = _num(row.get("equal_weight_return"), "peer_return_invalid")
        med = _num(row.get("median_return"), "peer_median_invalid")
        pos = _ratio(row.get("positive_share"), "peer_positive_share_invalid")

    return {
        "candidate_issuer_id": _text(row.get("candidate_issuer_id"), "peer_candidate_issuer_invalid"),
        "candidate_security_id": _text(row.get("candidate_security_id"), "peer_candidate_security_invalid"),
        "theme_id": _text(row.get("theme_id"), "peer_theme_invalid"),
        "asof": _iso(asof),
        "known_at": _iso(known),
        "membership_vintage": _text(row.get("membership_vintage"), "membership_vintage_invalid"),
        "return_window_sessions": _integer(row.get("return_window_sessions"), "peer_window_invalid", minimum=1),
        "return_basis": _text(row.get("return_basis"), "peer_return_basis_invalid"),
        "peer_member_count": total,
        "priced_peer_count": priced,
        "coverage": coverage,
        "equal_weight_return": ew,
        "median_return": med,
        "positive_share": pos,
        "measurement_state": state,
        "candidate_excluded": True,
        "issuer_aliases_excluded": True,
        "source_ref": _source_ref(row),
    }


def _theme(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {
        "schema", "theme_id", "asof", "known_at", "membership_vintage",
        "member_count", "priced_member_count", "coverage", "performance",
        "dynamics", "breadth", "diffusion", "authority", "rights_state", "receipts",
    }
    _closed(row, keys, "theme")
    if row.get("schema") != "theme_state/v1":
        raise EarlyLeadershipEvidenceError("theme_schema_invalid")
    member_count = _integer(row.get("member_count"), "theme_member_count_invalid")
    priced = _integer(row.get("priced_member_count"), "theme_priced_member_count_invalid")
    if priced > member_count:
        raise EarlyLeadershipEvidenceError("theme_priced_count_exceeds_membership")
    coverage = _ratio(row.get("coverage"), "theme_coverage_invalid")
    expected = 0.0 if member_count == 0 else priced / member_count
    if abs(coverage - expected) > 1e-6:
        raise EarlyLeadershipEvidenceError("theme_coverage_count_mismatch")

    performance = row.get("performance")
    dynamics = row.get("dynamics")
    breadth = row.get("breadth")
    diffusion = row.get("diffusion")
    for name, value in (
        ("performance", performance), ("dynamics", dynamics),
        ("breadth", breadth), ("diffusion", diffusion),
    ):
        if not isinstance(value, Mapping):
            raise EarlyLeadershipEvidenceError(f"theme_{name}_invalid")

    receipts = row.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise EarlyLeadershipEvidenceError("theme_receipts_required")
    receipts_out = sorted({_text(x, "theme_receipt_invalid") for x in receipts})
    asof = _utc(row.get("asof"), "theme_asof_invalid")
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if asof > known or known > decision:
        raise EarlyLeadershipEvidenceError("theme_clock_invalid")
    authority = _text(row.get("authority"), "theme_authority_invalid")
    if authority != "display":
        raise EarlyLeadershipEvidenceError("theme_authority_must_be_display")

    return {
        "theme_id": _text(row.get("theme_id"), "theme_id_invalid"),
        "asof": _iso(asof),
        "known_at": _iso(known),
        "membership_vintage": _text(row.get("membership_vintage"), "theme_membership_vintage_invalid"),
        "member_count": member_count,
        "priced_member_count": priced,
        "coverage": coverage,
        "performance": {
            "excess_5d_vs_spy": _num(performance.get("excess_5d_vs_spy"), "theme_excess_5d_invalid"),
            "excess_20d_vs_sector": _num(performance.get("excess_20d_vs_sector"), "theme_excess_20d_invalid"),
            "vol_normalized_10d": _num(performance.get("vol_normalized_10d"), "theme_volnorm_invalid"),
        },
        "dynamics": {
            "velocity": _num(dynamics.get("velocity"), "theme_velocity_invalid"),
            "acceleration": _num(dynamics.get("acceleration"), "theme_acceleration_invalid"),
            "persistence": _ratio(dynamics.get("persistence"), "theme_persistence_invalid"),
            "decay_risk": _ratio(dynamics.get("decay_risk"), "theme_decay_invalid"),
        },
        "breadth": {
            "positive_5d": _ratio(breadth.get("positive_5d"), "theme_positive_5d_invalid"),
            "rising_rs": _ratio(breadth.get("rising_rs"), "theme_rising_rs_invalid"),
            "early_event_share": _ratio(breadth.get("early_event_share"), "theme_early_event_share_invalid"),
            "entry_open_share": _ratio(breadth.get("entry_open_share"), "theme_entry_open_share_invalid"),
        },
        "diffusion": {
            "subthemes_participating": _integer(diffusion.get("subthemes_participating"), "subthemes_participating_invalid"),
            "leadership_entropy": _ratio(diffusion.get("leadership_entropy"), "leadership_entropy_invalid"),
            "leader_median_spread": _num(diffusion.get("leader_median_spread"), "leader_median_spread_invalid"),
        },
        "authority": authority,
        "rights_state": _text(row.get("rights_state"), "theme_rights_state_invalid"),
        "receipts": receipts_out,
    }


def _exposure(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {
        "schema", "issuer_id", "theme_id", "state", "known_at", "source_ref",
        "evidence_refs", "mapping_qualifier",
    }
    _closed(row, keys, "exposure")
    if row.get("schema") != EXPOSURE_SCHEMA:
        raise EarlyLeadershipEvidenceError("exposure_schema_invalid")
    state = _text(row.get("state"), "exposure_state_invalid")
    if state not in _EXPOSURE_STATES:
        raise EarlyLeadershipEvidenceError("exposure_state_unsupported")
    refs = row.get("evidence_refs")
    if not isinstance(refs, list):
        raise EarlyLeadershipEvidenceError("exposure_evidence_refs_invalid")
    refs_out = sorted({_text(x, "exposure_evidence_ref_invalid") for x in refs})
    if state in {"CONFIRMED_DIRECT", "CONFIRMED_INDIRECT"} and not refs_out:
        raise EarlyLeadershipEvidenceError("confirmed_exposure_requires_evidence")
    return {
        "issuer_id": _text(row.get("issuer_id"), "exposure_issuer_invalid"),
        "theme_id": _text(row.get("theme_id"), "exposure_theme_invalid"),
        "state": state,
        "known_at": _require_known(row, decision),
        "source_ref": _source_ref(row),
        "evidence_refs": refs_out,
        "mapping_qualifier": _text(row.get("mapping_qualifier"), "mapping_qualifier_invalid"),
        "economic_exposure_confirmed": state in {"CONFIRMED_DIRECT", "CONFIRMED_INDIRECT"},
    }


def _setup(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {"schema", "issuer_id", "security_id", "state", "observed_at",
            "known_at", "source_ref", "invalidation_ref", *_SETUP_LINEAGE_FIELDS}
    _closed(row, keys, "setup")
    if row.get("schema") != SETUP_SCHEMA:
        raise EarlyLeadershipEvidenceError("setup_schema_invalid")
    state = _text(row.get("state"), "setup_state_invalid")
    if state not in _SETUP_STATES:
        raise EarlyLeadershipEvidenceError("setup_state_unsupported")
    observed = _utc(row.get("observed_at"), "setup_observed_at_invalid")
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if observed > known or known > decision:
        raise EarlyLeadershipEvidenceError("setup_clock_invalid")
    invalidation = row.get("invalidation_ref")
    if invalidation is not None:
        invalidation = _text(invalidation, "setup_invalidation_ref_invalid")
    return {
        **_setup_lineage(row, "setup"),
        "issuer_id": _text(row.get("issuer_id"), "setup_issuer_invalid"),
        "security_id": _text(row.get("security_id"), "setup_security_invalid"),
        "state": state,
        "observed_at": _iso(observed),
        "known_at": _iso(known),
        "source_ref": _source_ref(row),
        "invalidation_ref": invalidation,
    }


def _geometry(row: Mapping[str, Any], decision: datetime) -> dict[str, Any]:
    keys = {
        "schema", "issuer_id", "security_id", "current_price", "invalidation_price", "chase_boundary",
        "target_price", "quote_asof", "known_at", "source_ref", *_SETUP_LINEAGE_FIELDS,
    }
    _closed(row, keys, "geometry")
    if row.get("schema") != GEOMETRY_SCHEMA:
        raise EarlyLeadershipEvidenceError("geometry_schema_invalid")
    current = _num(row.get("current_price"), "current_price_invalid")
    invalidation = _num(row.get("invalidation_price"), "invalidation_price_invalid")
    chase = _num(row.get("chase_boundary"), "chase_boundary_invalid")
    target_raw = row.get("target_price")
    target = None if target_raw is None else _num(target_raw, "target_price_invalid")
    if not (current > 0 and invalidation > 0 and chase > 0):
        raise EarlyLeadershipEvidenceError("geometry_prices_must_be_positive")
    if not invalidation < chase:
        raise EarlyLeadershipEvidenceError("geometry_invalidation_must_be_below_chase")
    if current <= invalidation:
        raise EarlyLeadershipEvidenceError("current_price_at_or_below_invalidation")
    if target is not None and target <= current:
        raise EarlyLeadershipEvidenceError("target_must_be_above_current_price")
    quote = _utc(row.get("quote_asof"), "quote_asof_invalid")
    known = _utc(row.get("known_at"), "known_at_missing_or_invalid")
    if quote > known or known > decision:
        raise EarlyLeadershipEvidenceError("geometry_clock_invalid")
    risk = current - invalidation
    return {
        **_setup_lineage(row, "geometry"),
        "issuer_id": _text(row.get("issuer_id"), "geometry_issuer_invalid"),
        "security_id": _text(row.get("security_id"), "geometry_security_invalid"),
        "current_price": current,
        "invalidation_price": invalidation,
        "chase_boundary": chase,
        "target_price": target,
        "quote_asof": _iso(quote),
        "known_at": _iso(known),
        "source_ref": _source_ref(row),
        "risk_to_invalidation_pct": risk / current,
        "room_to_chase_pct": (chase - current) / current,
        "target_room_pct": None if target is None else (target - current) / current,
        "gross_reward_risk": None if target is None else (target - current) / risk,
        "past_chase_boundary": current > chase,
        "availability_interpretation": "GEOMETRY_CONTEXT_ONLY_B4_REMAINS_OWNER",
    }


def build_early_leadership_evidence(
    *,
    decision_at: str,
    candidate: Mapping[str, Any],
    peer_ex_candidate: Mapping[str, Any],
    theme_state: Mapping[str, Any],
    economic_exposure: Mapping[str, Any],
    setup_observation: Mapping[str, Any],
    entry_geometry: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind independent owner facts into a B10-ready research envelope."""
    decision = _utc(decision_at, "decision_at_missing_or_invalid")
    cand = _candidate(candidate, decision)
    peer = _peer(peer_ex_candidate, decision)
    theme = _theme(theme_state, decision)
    exposure = _exposure(economic_exposure, decision)
    setup = _setup(setup_observation, decision)
    geometry = _geometry(entry_geometry, decision)

    for owner, name in ((setup, "setup"), (geometry, "geometry")):
        if owner["issuer_id"] != cand["issuer_id"]:
            raise EarlyLeadershipEvidenceError(f"{name}_issuer_mismatch")
        if owner["security_id"] != cand["security_id"]:
            raise EarlyLeadershipEvidenceError(f"{name}_security_mismatch")
    lineages = {tuple(owner[field] for field in _SETUP_LINEAGE_FIELDS)
                for owner in (cand, setup, geometry)}
    if len(lineages) != 1:
        raise EarlyLeadershipEvidenceError("setup_lineage_mismatch")
    lineage = {
        "state": "BOUND" if cand["episode_id"] is not None else "UNAVAILABLE",
        **{field: cand[field] for field in _SETUP_LINEAGE_FIELDS},
    }

    if peer["candidate_issuer_id"] != cand["issuer_id"]:
        raise EarlyLeadershipEvidenceError("peer_candidate_issuer_mismatch")
    if peer["candidate_security_id"] != cand["security_id"]:
        raise EarlyLeadershipEvidenceError("peer_candidate_security_mismatch")
    if exposure["issuer_id"] != cand["issuer_id"]:
        raise EarlyLeadershipEvidenceError("exposure_issuer_mismatch")
    if len({cand["theme_id"], peer["theme_id"], theme["theme_id"], exposure["theme_id"]}) != 1:
        raise EarlyLeadershipEvidenceError("theme_identity_mismatch")
    measurement_instants = (
        _utc(cand["asof"], "candidate_asof_invalid"),
        _utc(peer["asof"], "peer_asof_invalid"),
        _utc(theme["asof"], "theme_asof_invalid"),
    )
    if not (measurement_instants[0] == measurement_instants[1] == measurement_instants[2]):
        raise EarlyLeadershipEvidenceError("measurement_asof_mismatch")
    if peer["membership_vintage"] != theme["membership_vintage"]:
        raise EarlyLeadershipEvidenceError("membership_vintage_mismatch")
    if peer["return_window_sessions"] != cand["return_window_sessions"]:
        raise EarlyLeadershipEvidenceError("return_window_mismatch")
    if peer["return_basis"] != cand["return_basis"]:
        raise EarlyLeadershipEvidenceError("return_basis_mismatch")

    if peer["measurement_state"].startswith("UNAVAILABLE"):
        decomposition = {
            "state": "UNAVAILABLE",
            "stock_excess_market": cand["stock_return"] - cand["market_return"],
            "peer_excess_market": None,
            "stock_excess_peer": None,
            "identity_error": None,
        }
    else:
        peer_return = peer["equal_weight_return"]
        stock_excess_market = cand["stock_return"] - cand["market_return"]
        peer_excess_market = peer_return - cand["market_return"]
        stock_excess_peer = cand["stock_return"] - peer_return
        identity_error = stock_excess_market - (peer_excess_market + stock_excess_peer)
        if abs(identity_error) > 1e-12:
            raise AssertionError("return decomposition identity failed")
        decomposition = {
            "state": peer["measurement_state"],
            "stock_excess_market": stock_excess_market,
            "peer_excess_market": peer_excess_market,
            "stock_excess_peer": stock_excess_peer,
            "identity_error": identity_error,
        }

    mandatory_ready = (
        not peer["measurement_state"].startswith("UNAVAILABLE")
        and theme["rights_state"] not in {"RIGHTS_BLOCKED", "UNAVAILABLE"}
        and exposure["economic_exposure_confirmed"]
        and setup["state"] != "UNKNOWN"
        and lineage["state"] == "BOUND"
    )
    if mandatory_ready:
        research_state = "READY_FOR_RESEARCH_COMPARISON"
    elif (
        peer["measurement_state"].startswith("UNAVAILABLE")
        or theme["rights_state"] in {"RIGHTS_BLOCKED", "UNAVAILABLE"}
    ):
        research_state = "UNAVAILABLE"
    else:
        research_state = "ACCRUING"

    material = {
        "schema": SCHEMA,
        "decision_at": _iso(decision),
        "issuer_id": cand["issuer_id"],
        "security_id": cand["security_id"],
        "ticker": cand["ticker"],
        "theme_id": cand["theme_id"],
        "research_state": research_state,
        "setup_lineage": lineage,
        "candidate_measurement": cand,
        "peer_ex_candidate": peer,
        "theme_state_projection": theme,
        "economic_exposure": exposure,
        "setup_observation": setup,
        "entry_geometry": geometry,
        "return_decomposition": decomposition,
        "research_features": {
            "stock_excess_market": decomposition["stock_excess_market"],
            "peer_excess_market": decomposition["peer_excess_market"],
            "stock_excess_peer": decomposition["stock_excess_peer"],
            "peer_positive_share": peer["positive_share"],
            "peer_median_return": peer["median_return"],
            "peer_coverage": peer["coverage"],
            "theme_velocity": theme["dynamics"]["velocity"],
            "theme_acceleration": theme["dynamics"]["acceleration"],
            "theme_persistence": theme["dynamics"]["persistence"],
            "theme_decay_risk": theme["dynamics"]["decay_risk"],
            "theme_positive_5d": theme["breadth"]["positive_5d"],
            "theme_rising_rs": theme["breadth"]["rising_rs"],
            "theme_leadership_entropy": theme["diffusion"]["leadership_entropy"],
            "theme_leader_median_spread": theme["diffusion"]["leader_median_spread"],
            "economic_exposure_state": exposure["state"],
            "setup_state": setup["state"],
            "risk_to_invalidation_pct": geometry["risk_to_invalidation_pct"],
            "room_to_chase_pct": geometry["room_to_chase_pct"],
            "target_room_pct": geometry["target_room_pct"],
            "gross_reward_risk": geometry["gross_reward_risk"],
        },
        "interpretation": {
            "score": None,
            "probability": None,
            "rank": None,
            "recommendation": None,
            "availability": "DEFER_TO_B4",
            "peer_support": "LEAVE_ISSUER_OUT_OWNER_RECEIPT",
            "theme_state_owner": "GMI",
            "economic_exposure_membership_only_is_not_confirmed": True,
        },
        "authority": dict(_AUTHORITY),
    }
    material["evidence_id"] = "pele:" + sha256(_canonical(material).encode("utf-8")).hexdigest()
    return deepcopy(material)
