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
        "eligible_for_customer_publication": False,
        "eligible_for_historical_prediction": False,
        "trading_or_alert_authority": False,
    }
