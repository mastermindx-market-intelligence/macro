"""Guarded, read-only P2 ingress for one U.S. thematic basket.

Consumes outputs ALREADY produced by existing owner adapters:
- basket_membership_pit.members_asof
- theme_graph identity/rights qualification
- existing known-at market price/benchmark readers

No data collection, store, scheduler, owner qualification, network or filesystem.
A syntactically coherent packet is NOT an authenticated vendor receipt, rights
grant or market-vintage proof. Every successful output is research-preview-only;
downstream publishing, rankings, alerts, sizing and predictions remain blocked.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any
import math

from engine.sector_theme_factor_intelligence import HORIZONS, MA_BASES, project_factor_frame
from engine.sector_theme_regime_fingerprint import compose_regime_fingerprint
from engine.sector_theme_regime_explain import explain_regime_preview

SCHEMA = "sector_theme_owner_preview/v1"
PURPOSE = "sector_theme_factor_research"
MARKET_ORIGINS = frozenset(("synthetic_fixture", "owner_reported"))
MEMBERSHIP_MODES = frozenset(("PIT_AS_KNOWN", "CURRENT_ROSTER"))


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        v = value
    elif isinstance(value, str):
        try:
            v = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, OverflowError):
            return None
    else:
        return None
    if v.tzinfo is None or v.utcoffset() is None:
        return None
    return v.astimezone(timezone.utc)


def _day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        d = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return d if value == d.isoformat() else None


def _number(value: object) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        v = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return v if math.isfinite(v) else None


def _name(value: object) -> str | None:
    return value if isinstance(value, str) and bool(value.strip()) and value == value.strip() else None


def _held(*reasons: str) -> dict:
    return {
        "schema": SCHEMA,
        "status": "HELD",
        "hold_reasons": sorted(set(reasons)),
        "frame": None,
        "fingerprint": None,
        "eligible_for_customer_publication": False,
        "eligible_for_historical_prediction": False,
        "trading_or_alert_authority": False,
    }


def _reference_return(
    raw: object, *, horizon: str, end: datetime, decision: datetime,
    price_basis: str,
) -> tuple[float | None, str | None]:
    if not isinstance(raw, Mapping):
        return None, "missing_reference"
    if raw.get("horizon") != horizon or raw.get("price_basis") != price_basis:
        return None, "reference_horizon_or_basis_mismatch"
    if _timestamp(raw.get("period_end")) != end:
        return None, "reference_endpoint_mismatch"
    observed, available = _timestamp(raw.get("observed_at")), _timestamp(raw.get("available_at"))
    if observed is None or available is None:
        return None, "missing_reference_known_at"
    if not end <= observed <= available <= decision:
        return None, "future_or_noncausal_reference"
    value = _number(raw.get("return_frac"))
    if value is None or value < -1.0:
        return None, "invalid_reference_return"
    return value, None


def preview_us_theme_packet(packet: object) -> dict:
    """Consume owner-shaped packet, never authenticate its origin.

    Owner permissions are not supplied by this helper. An actual product
    publisher must independently obtain and verify the genuine source/rights/
    known-at receipts through their incumbents. The returned flags never
    become true even for syntactically correct or owner-reported packets.
    """
    if not isinstance(packet, Mapping):
        return _held("missing_owner_packet")
    market, membership, identities = (
        packet.get("market"), packet.get("membership_asof"),
        packet.get("member_identities"),
    )
    if not isinstance(market, Mapping) or not isinstance(membership, Mapping):
        return _held("missing_membership_or_market")
    if not isinstance(identities, Mapping):
        return _held("missing_identity_owner")
    group_id = _name(packet.get("group_id"))
    cohort_id = _name(packet.get("cohort_id"))
    revision = _name(packet.get("membership_revision"))
    if not all((group_id, cohort_id, revision)):
        return _held("missing_canonical_group_or_revision")
    if packet.get("group_kind") not in ("theme", "sector", "industry"):
        # No direct subtheme/microtheme security edges exist at this boundary.
        return _held("subtheme_membership_not_qualified")
    if packet.get("membership_mode") not in MEMBERSHIP_MODES:
        return _held("missing_membership_basis")
    mode = packet["membership_mode"]
    origin = market.get("origin")
    if origin not in MARKET_ORIGINS:
        return _held("unknown_source_origin")
    rights = packet.get("use_verdict")
    if origin == "owner_reported":
        # This is a claimed receipt shape, never a rights assertion by us.
        if (not isinstance(rights, Mapping) or rights.get("verdict") != "ALLOWED"
                or rights.get("purpose") != PURPOSE
                or not _name(rights.get("registry_revision"))
                or not _name(rights.get("source_ref"))):
            return _held("research_source_use_not_granted")
    else:
        if rights is not None:
            return _held("synthetic_packet_carries_live_rights_claim")
    if membership.get("suite") != "baskets":
        return _held("wrong_membership_suite")
    if membership.get("basket_id") != group_id:
        return _held("membership_group_mismatch")
    pit = membership.get("pit")
    basis = membership.get("basis")
    if mode == "PIT_AS_KNOWN" and (pit is not True or basis != "pit_snapshot"):
        return _held("current_roster_not_pit")
    if mode == "CURRENT_ROSTER" and not (
        (pit is True and basis == "pit_snapshot")
        or (pit is False and basis == "current_membership")
    ):
        return _held("unknown_roster_basis")
    if membership.get("source_shape") not in ("membership", None):
        return _held("unqualified_member_source_shape")
    if mode == "PIT_AS_KNOWN" and membership.get("source_shape") != "membership":
        return _held("unqualified_member_source_shape")
    members = membership.get("members")
    if not isinstance(members, list) or not members or any(
        not _name(x) for x in members
    ) or len(set(members)) != len(members):
        return _held("invalid_native_members")
    horizon = market.get("horizon")
    ma_basis = market.get("ma_basis")
    price_basis = market.get("price_basis")
    if horizon not in HORIZONS or ma_basis not in MA_BASES or (
        price_basis not in ("split_adjusted", "total_return_adjusted", "unadjusted")
    ):
        return _held("invalid_timeframe_or_price_basis")
    end = _timestamp(market.get("period_end"))
    decision = _timestamp(market.get("decision_at"))
    known = _timestamp(packet.get("membership_known_at"))
    if end is None or decision is None or known is None:
        return _held("missing_original_membership_or_market_clock")
    if end > decision or known > decision:
        return _held("future_market_or_membership_known_at")
    if mode == "PIT_AS_KNOWN" and known > end:
        return _held("future_membership_knowledge_for_pit")
    date_asof, snap = _day(membership.get("asof")), _day(membership.get("snapshot_date"))
    if date_asof is None or date_asof > end.date():
        return _held("invalid_native_asof_date")
    if pit is True and (snap is None or snap > date_asof):
        return _held("invalid_native_snapshot_date")
    if pit is False and snap is not None and mode == "CURRENT_ROSTER":
        # Avoid presenting some other historical snapshot as this current list.
        return _held("current_roster_with_foreign_snapshot")
    if pit is True and snap is not None and known.date() < snap:
        return _held("membership_known_at_predates_native_snapshot")
    # Dated snapshots alone are NOT proof of their first availability.
    if origin == "owner_reported" and not isinstance(
        packet.get("original_membership_receipt"), Mapping
    ):
        return _held("original_membership_receipt_not_authenticated_here")
    identity_ids: dict[str, str] = {}
    for ticker in members:
        record = identities.get(ticker)
        if (not isinstance(record, Mapping)
                or record.get("resolution_state") != "RESOLVED"
                or not _name(record.get("security_id"))
                or not _name(record.get("issuer_id"))):
            return _held("unresolved_canonical_member_identity")
        identity_clock = _timestamp(record.get("available_at"))
        if identity_clock is None or identity_clock > decision:
            return _held("missing_or_future_identity_availability")
        if mode == "PIT_AS_KNOWN" and identity_clock > end:
            return _held("future_identity_for_pit")
        identity_ids[ticker] = record["security_id"]
    if len(set(identity_ids.values())) != len(members):
        return _held("duplicate_canonical_security")
    rows = market.get("member_rows")
    if not isinstance(rows, Mapping) or any(ticker not in members for ticker in rows):
        return _held("invalid_member_row_population")
    for ticker, raw in rows.items():
        if not isinstance(raw, Mapping) or raw.get("price_basis") != price_basis:
            return _held("member_price_basis_mismatch")
    benchmark, reason = _reference_return(
        market.get("benchmark"), horizon=horizon,
        end=end, decision=decision, price_basis=price_basis)
    if reason is not None:
        return _held("benchmark_"+reason)
    parent = None
    if market.get("parent") is not None:
        parent, reason = _reference_return(
            market["parent"], horizon=horizon,
            end=end, decision=decision, price_basis=price_basis)
        if reason is not None:
            return _held("parent_"+reason)
    elif packet.get("group_kind") != "sector":
        # Real parent-relative analysis needs an aligned parent, not a zero.
        return _held("missing_parent_reference")
    canonical_rows = {
        identity_ids[ticker]: dict(rows[ticker])
        for ticker in members if ticker in rows
    }
    try:
        frame = project_factor_frame(
            group_id=group_id,
            cohort_id=cohort_id,
            member_ids=list(identity_ids.values()),
            measurements=canonical_rows,
            horizon=horizon,
            period_end=end,
            decision_at=decision,
            membership_revision=revision,
            membership_known_at=known,
            membership_mode=mode,
            # An owner-shaped packet does not prove immutable ORIGINAL observation
            # receipts; keep it reconstructed until incumbent custody verifies.
            evidence_mode=(
                "synthetic_fixture" if origin == "synthetic_fixture"
                else "reconstructed_price_history"
            ),
            ma_basis=ma_basis,
            benchmark_return=benchmark,
            parent_return=parent,
        )
        fp = compose_regime_fingerprint({horizon: frame})
    except (ValueError, TypeError, OverflowError):
        # Not a permissive partial fallback: malformed contracts are held.
        return _held("invalid_factor_projection_input")
    return {
        "schema": SCHEMA,
        "status": "RESEARCH_PREVIEW_ONLY",
        "hold_reasons": [
            "owner_custody_source_rights_and_original_receipts_not_authenticated"
        ],
        "basis": mode,
        "source_origin": origin,
        "known_member_tickers": len(members),
        "expected_security_ids": list(sorted(identity_ids.values())),
        "frame": frame,
        "fingerprint": fp,
        "explanation": explain_regime_preview(fp),
        "group_flow_context": project_owner_group_flow_context(
            fp, packet.get("group_flow_reading"), packet.get("group_flow_binding")
        ),
        "eligible_for_customer_publication": False,
        "eligible_for_historical_prediction": False,
        "trading_or_alert_authority": False,
    }


# P2b: CONSUME incumbent group_flow.fingerprint_at, never reproduce its flow
# score or stage decision, and never fold owner-reported values into a new rank.
FLOW_SCHEMA = "sector_theme_group_flow_context/v1"
FLOW_SOURCE = "engine.group_flow.fingerprint_at"
FLOW_WINDOWS = ("rs_window_d", "breadth_ma_d", "corr_window_d",
                "persist_window_d", "z_lookback_d")


def _flow_held(reason: str) -> dict:
    return {
        "schema": FLOW_SCHEMA, "status": "HELD",
        "reason": reason, "observations": {},
        "eligible_for_customer_publication": False,
        "ranking_or_trading_authority": False,
    }


def _flow_metric(raw: Mapping, key: str, low: float | None = None,
                 high: float | None = None) -> dict:
    n = _number(raw.get(key))
    if n is None:
        return {"status": "unmeasured", "reason": "missing_or_invalid_owner_field"}
    if (low is not None and n < low) or (high is not None and n > high):
        return {"status": "unmeasured", "reason": "owner_field_out_of_range"}
    return {"status": "owner_reported_unqualified", "value": n,
            "unit": "z_score" if key in ("accel_z", "broadening_z") else "fraction"}


def project_owner_group_flow_context(
    fingerprint: object, owner_reading: object, binding: object,
) -> dict:
    """Project a separately labeled group_flow read without pretending source admission.

    Group_flow's stage and flow_score are NOT forecast probabilities, capital
    rankings, transaction flow measurements or independently validated alpha.
    This interface binds the owner observation to a specific already-composed
    group, complete security population, decision clock and 20-session basis.
    An actual source/rights/identity owner must still authenticate the binding.
    """
    if not isinstance(fingerprint, Mapping) or (
        fingerprint.get("schema") != "sector_theme_regime_fingerprint/v1"
    ):
        return _flow_held("missing_current_factor_fingerprint")
    if not isinstance(owner_reading, Mapping) or not isinstance(binding, Mapping):
        return _flow_held("missing_owner_group_flow")
    if fingerprint.get("authority", {}).get("eligible_for_customer_publication") is not False:
        return _flow_held("fingerprint_claims_publication_rights")
    if (fingerprint.get("authority", {}).get("predictive_promoted") is not False
            or fingerprint.get("authority", {}).get("ranking_authority") is not False):
        return _flow_held("fingerprint_claims_prediction_or_ranking")
    group = fingerprint.get("group")
    horizons = fingerprint.get("horizons")
    if not isinstance(group, Mapping) or not isinstance(horizons, Mapping):
        return _flow_held("missing_group_or_horizons")
    if (binding.get("source_function") != FLOW_SOURCE
            or not _name(binding.get("source_revision"))):
        return _flow_held("unknown_group_flow_source_definition")
    if binding.get("group_id") != group.get("group_id") or (
        binding.get("cohort_id") != group.get("cohort_id")
    ):
        return _flow_held("owner_flow_group_or_cohort_mismatch")
    ids = binding.get("member_ids")
    group_ids = group.get("member_ids")
    if (not isinstance(ids, list) or not isinstance(group_ids, list)
            or any(not _name(x) for x in ids)
            or sorted(ids) != sorted(group_ids)
            or len(set(ids)) != len(ids)):
        return _flow_held("owner_flow_population_mismatch")
    if binding.get("horizon") != "20d" or "20d" not in horizons:
        return _flow_held("group_flow_requires_20d_factor_frame")
    v = horizons["20d"]
    if not isinstance(v, Mapping) or v.get("moving_average_basis") != "daily_sessions":
        return _flow_held("group_flow_requires_daily_session_ma_basis")
    config = binding.get("windows")
    if (not isinstance(config, Mapping)
            or any(type(config.get(k)) is not int or config[k] < 2 for k in FLOW_WINDOWS)
            or config["rs_window_d"] != 20):
        return _flow_held("unqualified_group_flow_window_definition")
    period_end, observed, available, decision = (
        _timestamp(binding.get("period_end")),
        _timestamp(binding.get("observed_at")),
        _timestamp(binding.get("available_at")),
        _timestamp(group.get("decision_at")),
    )
    if any(v is None for v in (period_end, observed, available, decision)):
        return _flow_held("missing_group_flow_original_clock")
    if period_end != _timestamp(v.get("period_end")):
        return _flow_held("group_flow_wrong_period_end")
    if not period_end <= observed <= available <= decision:
        return _flow_held("future_or_out_of_order_group_flow_receipt")
    source_origin = binding.get("origin")
    if source_origin == "owner_reported":
        rights = binding.get("use_verdict")
        if (not isinstance(rights, Mapping) or rights.get("verdict") != "ALLOWED"
                or rights.get("purpose") != PURPOSE
                or not _name(rights.get("registry_revision"))
                or not _name(rights.get("source_ref"))):
            return _flow_held("group_flow_research_use_not_admitted")
    elif source_origin != "synthetic_fixture" or binding.get("use_verdict") is not None:
        return _flow_held("group_flow_source_origin_or_rights_invalid")
    # Never use the incumbent score; it is weighted/renormalised under the
    # historical owner and has not demonstrated a future return edge.
    stage = owner_reading.get("stage")
    if stage is not None and stage not in ("emerging", "confirmed", "cooling", "quiet"):
        return _flow_held("unknown_owner_flow_stage_vocabulary")
    fields = {
        "relative_wealth_second_difference_z": _flow_metric(owner_reading, "accel_z"),
        "ma_breadth_broadening_z": _flow_metric(owner_reading, "broadening_z"),
        "ma_breadth_observed_sample": _flow_metric(owner_reading, "breadth", 0, 1),
        "member_return_cohesion": _flow_metric(owner_reading, "cohesion", -1, 1),
        "member_return_cohesion_change": _flow_metric(owner_reading, "cohesion_chg", -2, 2),
        "relative_strength_persistence": _flow_metric(owner_reading, "persistence", 0, 1),
        "relative_strength_percentile": _flow_metric(owner_reading, "rs_pctile", 0, 1),
    }
    if not any(v["status"] == "owner_reported_unqualified" for v in fields.values()):
        return _flow_held("all_owner_group_flow_fields_unmeasured")
    return {
        "schema": FLOW_SCHEMA,
        "status": "OWNER_REPORTED_RESEARCH_ONLY",
        "producer": FLOW_SOURCE,
        "producer_revision_claim": binding["source_revision"],
        "source_origin": source_origin,
        "cohort_id": group["cohort_id"],
        "horizon": "20d",
        "period_end": period_end.isoformat(),
        "available_at": available.isoformat(),
        "owner_windows": {key: config[key] for key in FLOW_WINDOWS},
        "owner_stage_descriptive_only": stage,
        "observations": fields,
        "breadth_denominator_status": "source_population_vintage_not_authenticated",
        "original_observation_and_use_receipts_verified": False,
        "eligible_for_customer_publication": False,
        "ranking_or_trading_authority": False,
    }
