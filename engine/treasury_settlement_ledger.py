"""Source-input contract for the existing private settlement math and H3 data gate.

Pure, outcome-blind functions. This module neither certifies sources nor acquires
or publishes data. An independently accepted source owner supplies the inventory,
cash basis, economic identities and literal release/receipt clocks. The module
checks that supplied contract; an opaque certificate reference is not acceptance.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Optional, Sequence

from engine.treasury_auction_primitives import (
    CashComponent, CashKind, InputRole, Observation, SecurityClass, settlement_cash,
)

METHOD = "settlement_cohort_input_gate.v1"
CHANNELS = ("BILL_CMB", "COUPON")
SERIES_UNITS = {"TGCR": "PERCENT", "SOFR": "PERCENT", "IORB": "PERCENT",
                "RESERVES": "USD", "ON_RRP": "USD",
                "DEALER_INVENTORY": "USD", "GOVERNMENT_MMF_AUM": "USD"}


def _clock(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name}: aware datetime required")
    return value.astimezone(timezone.utc)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty string required")
    return value


def _digest(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name}: SHA-256 required")
    return value


def _day(value, name):
    if type(value) is not date:
        raise ValueError(f"{name}: date required")
    return value


@dataclass(frozen=True)
class SettlementClaim:
    """Normalized evidence supplied by an existing qualified source owner.

    economic_claim_keys identify payments, not merely rows/CUSIPs. A funded
    buyback already included in redemptions must carry the same payment key.
    Empty keys are allowed only for a source-qualified category-wide zero.
    source_digest/locator bind the extraction, not a fresh source certificate.
    """
    component: CashComponent
    security_class: SecurityClass
    source_digest: str
    source_locator: str
    economic_claim_keys: tuple[str, ...]
    cash_basis: str = "CASH_USD"
    holder_scope: str = "PRIVATE_MARKETABLE_EX_SOMA"
    soma_treatment: str = "ALREADY_EXCLUDED_BY_SOURCE"
    sourced_category_zero: bool = False

    @property
    def channel(self):
        return "BILL_CMB" if self.security_class in (SecurityClass.BILL, SecurityClass.CMB) else "COUPON"


def inventory_digest(claims: Sequence[SettlementClaim]) -> str:
    """Bind every imported claim and value, not just its administrative ID."""
    rows = []
    for c in claims:
        a = c.component.amount
        rows.append({"id": c.component.component_id, "kind": c.component.kind.value,
            "cohort_id": c.component.cohort_id, "settlement_date": c.component.settlement_date.isoformat(),
            "class": c.security_class.value, "source_digest": c.source_digest,
            "source_locator": c.source_locator, "economic_claim_keys": sorted(c.economic_claim_keys),
            "cash_basis": c.cash_basis, "holder_scope": c.holder_scope,
            "soma_treatment": c.soma_treatment, "sourced_category_zero": c.sourced_category_zero,
            "amount": None if a is None else {"value": None if a.value is None else str(a.value),
                "unit": a.unit, "currency": a.currency,
                "known_at": None if a.known_at is None else _clock(a.known_at, "known_at").isoformat(),
                "as_of": None if a.as_of is None else _clock(a.as_of, "as_of").isoformat(),
                "source_ref": a.source_ref, "input_method": a.input_method, "role": a.role.value}})
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r: (r["id"], r["source_digest"])),
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CohortInventory:
    """Imported upstream inventory; no constructor or string grants acceptance."""
    cohort_id: str
    settlement_date: date
    expected_component_ids: tuple[str, ...]
    claims_digest: str
    known_at: datetime
    source_ref: str
    independent_acceptance_ref: Optional[str]
    complete_private_universe: bool = False
    funded_buybacks_excluded_from_redemptions: bool = False


def qualify_settlement_cohort(*, cohort_id: str, settlement_date: date,
        decision_at: datetime, claims: Sequence[SettlementClaim],
        inventory: Optional[CohortInventory] = None) -> dict:
    """Check source-supplied accounting contract before invoking accepted math.

    Even a satisfied imported contract is SOURCE_CONTRACT_SATISFIED, not empirical
    qualification or evidence that a certificate was actually accepted. Actual
    research admission still owes independent raw-source/PIT review and a freeze.
    """
    _text(cohort_id, "cohort_id"); _day(settlement_date, "settlement_date")
    at = _clock(decision_at, "decision_at")
    if len(claims) > 2048:
        raise ValueError("cohort exceeds bounded claim inventory")
    reasons, seen_ids, seen_payments, grouped = [], set(), set(), {}
    for channel in CHANNELS:
        grouped[channel] = {kind: [] for kind in CashKind}
    for c in claims:
        if not isinstance(c, SettlementClaim) or not isinstance(c.component, CashComponent):
            raise ValueError("SettlementClaim with CashComponent required")
        if not isinstance(c.security_class, SecurityClass) or not isinstance(c.component.kind, CashKind):
            raise ValueError("explicit security class and cash kind required")
        x = c.component
        _text(x.component_id, "component_id"); _digest(c.source_digest, "source_digest")
        _text(c.source_locator, "source_locator")
        if x.component_id in seen_ids:
            reasons.append("duplicate_component_id")
        seen_ids.add(x.component_id)
        if x.cohort_id != cohort_id or x.settlement_date != settlement_date:
            reasons.append("cohort_or_settlement_mismatch")
        if c.cash_basis != "CASH_USD" or c.holder_scope != "PRIVATE_MARKETABLE_EX_SOMA":
            reasons.append("unqualified_cash_basis_or_private_scope")
        if c.soma_treatment != "ALREADY_EXCLUDED_BY_SOURCE":
            reasons.append("unqualified_soma_treatment")
        if type(c.sourced_category_zero) is not bool or not isinstance(c.economic_claim_keys, tuple):
            raise ValueError("explicit zero flag and tuple of payment keys required")
        a = x.amount
        if a is not None and not isinstance(a, Observation):
            raise ValueError("Observation required")
        if a is None or a.value is None:
            reasons.append("missing_cash_amount")
        else:
            if not isinstance(a, Observation):
                raise ValueError("Observation required")
            if a.role != InputRole.QUALIFIED:
                reasons.append("cash_input_not_externally_qualified")
            if a.unit != "USD" or a.currency != "USD":
                reasons.append("cash_unit_or_currency_mismatch")
            _text(a.source_ref, "amount.source_ref"); _text(a.input_method, "amount.input_method")
            if isinstance(a.value, bool) or not isinstance(a.value, (int, float, Decimal)):
                raise ValueError("finite numeric cash magnitude required")
            value = Decimal(str(a.value))
            if not value.is_finite() or value < 0:
                raise ValueError("nonnegative finite cash magnitude required")
            if a.known_at is None or a.as_of is None:
                reasons.append("missing_cash_clock")
            else:
                known, economic = _clock(a.known_at, "cash.known_at"), _clock(a.as_of, "cash.as_of")
                if economic > known or known > at:
                    reasons.append("cash_not_eligible_at_cutoff")
            if c.sourced_category_zero:
                if value != 0 or c.economic_claim_keys:
                    reasons.append("invalid_category_zero")
            elif not c.economic_claim_keys:
                reasons.append("missing_economic_payment_identity")
        for key in c.economic_claim_keys:
            _text(key, "economic_claim_key")
            if key in seen_payments:
                reasons.append("overlapping_economic_payment")
            seen_payments.add(key)
        grouped[c.channel][x.kind].append(x)
    # A category-wide zero cannot be combined with nonzero/detail entries for
    # that same channel and kind, including entries with different source IDs.
    for channel in CHANNELS:
        for kind in CashKind:
            subset = [c for c in claims if c.channel == channel and c.component.kind == kind]
            if not subset:
                reasons.append(f"missing_inventory:{channel}:{kind.value}")
            if any(c.sourced_category_zero for c in subset) and len(subset) != 1:
                reasons.append("category_zero_conflicts_with_detail")
    digest = inventory_digest(claims)
    if inventory is None:
        reasons.append("missing_accepted_inventory")
    else:
        if not isinstance(inventory, CohortInventory):
            raise ValueError("CohortInventory required")
        _text(inventory.source_ref, "inventory.source_ref"); _digest(inventory.claims_digest, "inventory.claims_digest")
        if inventory.cohort_id != cohort_id or inventory.settlement_date != settlement_date:
            reasons.append("inventory_cohort_mismatch")
        if type(inventory.complete_private_universe) is not bool or type(inventory.funded_buybacks_excluded_from_redemptions) is not bool:
            raise ValueError("inventory certification flags must be bool")
        if not isinstance(inventory.expected_component_ids, tuple):
            raise ValueError("inventory component IDs must be tuple")
        for identity in inventory.expected_component_ids:
            _text(identity, "inventory.component_id")
        if not inventory.complete_private_universe or not inventory.funded_buybacks_excluded_from_redemptions:
            reasons.append("inventory_completeness_or_nonoverlap_unaccepted")
        if inventory.independent_acceptance_ref is None:
            reasons.append("missing_independent_source_acceptance")
        else:
            _text(inventory.independent_acceptance_ref, "independent_acceptance_ref")
        inventory_at = _clock(inventory.known_at, "inventory.known_at")
        if inventory_at > at:
            reasons.append("inventory_not_known_at_cutoff")
        if any(c.component.amount is not None and c.component.amount.known_at is not None
                and _clock(c.component.amount.known_at, "cash.known_at") > inventory_at for c in claims):
            reasons.append("inventory_precedes_claim_availability")
        if len(set(inventory.expected_component_ids)) != len(inventory.expected_component_ids):
            reasons.append("duplicate_inventory_id")
        if set(inventory.expected_component_ids) != seen_ids or inventory.claims_digest != digest:
            reasons.append("inventory_does_not_bind_exact_claims")
    reasons = sorted(set(reasons))
    channels = {}
    for channel, groups in grouped.items():
        # Do not pass malformed/mismatched inputs to the math leaf or expose a
        # partial category total as if it were a complete net cash quantity.
        channels[channel] = (None if reasons else settlement_cash(cohort_id=cohort_id,
            settlement_date=settlement_date, currency="USD", decision_at=at,
            proceeds=groups[CashKind.PRIVATE_PROCEEDS_EX_SOMA],
            redemptions=groups[CashKind.PRIVATE_MARKETABLE_REDEMPTION],
            buybacks=groups[CashKind.FUNDED_BUYBACK_OUTLAY], completeness_certified=True))
    return {"method_version": METHOD, "cohort_id": cohort_id,
        "settlement_date": settlement_date.isoformat(), "decision_cutoff_utc": at.isoformat(),
        "input_contract_status": "INSUFFICIENT_PIT" if reasons else "SOURCE_CONTRACT_SATISFIED",
        "null_reasons": reasons, "inventory_digest": digest, "channels": channels,
        "net_private_cash_usd": None,  # Channel values must not erase opposing bill/coupon effects.
        "reserve_pressure": None, "probabilities": None, "is_context_only": True,
        "research_admission": "REQUIRES_INDEPENDENT_SOURCE_PIT_REVIEW_AND_DATASET_FREEZE"}


@dataclass(frozen=True)
class FinancingVintage:
    series: str
    effective_date: date
    observation: Observation
    release_at: Optional[datetime]
    body_received_at: Optional[datetime]
    source_digest: str
    vintage_id: str
    revision: bool = False
    interpolated: bool = False
    release_clock_basis: str = "VERIFIED_OFFICIAL_TIMESTAMP"


def financing_baseline_at(vintages: Sequence[FinancingVintage], decision_at: datetime) -> dict:
    """Select latest eligible economic date and released vintage per series.

    A qualified official body receipt may instead supply a conservative release
    availability bound, explicitly selected without inventing publication time.
    No weekly interpolation, effective-date backdating, release-rule imputation,
    future revisions, synthetic fixture data or result-role inputs are admitted.
    This selector does not calculate outcomes or replace canonical liquidity.
    """
    at = _clock(decision_at, "decision_at")
    if len(vintages) > 4096:
        raise ValueError("baseline exceeds bounded vintage inventory")
    eligible, excluded = {}, []
    for v in vintages:
        if not isinstance(v, FinancingVintage) or v.series not in SERIES_UNITS:
            raise ValueError("supported FinancingVintage required")
        _day(v.effective_date, "effective_date"); _digest(v.source_digest, "source_digest")
        _text(v.vintage_id, "vintage_id")
        if type(v.revision) is not bool or type(v.interpolated) is not bool:
            raise ValueError("vintage revision/interpolation flags must be bool")
        a = v.observation
        if not isinstance(a, Observation):
            raise ValueError("Observation required")
        reasons = []
        if a.role != InputRole.QUALIFIED or v.interpolated:
            reasons.append("unqualified_or_interpolated_baseline")
        if a.unit != SERIES_UNITS[v.series] or a.currency != ("USD" if a.unit == "USD" else None):
            reasons.append("baseline_unit_mismatch")
        _text(a.source_ref, "source_ref"); _text(a.input_method, "input_method")
        if a.value is None:
            reasons.append("missing_baseline_value")
        elif isinstance(a.value, bool) or not isinstance(a.value, (int, float, Decimal)) or not Decimal(str(a.value)).is_finite():
            raise ValueError("finite baseline value required")
        if v.release_clock_basis not in ("VERIFIED_OFFICIAL_TIMESTAMP", "QUALIFIED_OFFICIAL_BODY_AVAILABILITY_BOUND"):
            raise ValueError("explicit supported release clock basis required")
        needs_exact = v.release_clock_basis == "VERIFIED_OFFICIAL_TIMESTAMP"
        clocks = (v.body_received_at, a.known_at, a.as_of)
        if any(clock is None for clock in clocks) or (needs_exact and v.release_at is None):
            reasons.append("missing_literal_release_or_receipt_clock")
        else:
            body, known, economic = [_clock(clock, "baseline_clock") for clock in clocks]
            released = _clock(v.release_at, "release_at") if v.release_at is not None else body
            if released > body or body > known or economic > known:
                reasons.append("baseline_clock_order_invalid")
            if economic.date() != v.effective_date:
                reasons.append("baseline_effective_date_mismatch")
            if any(clock > at for clock in (released, body, known, economic)) or v.effective_date > at.date():
                reasons.append("baseline_not_known_at_cutoff")
        if reasons:
            excluded.append({"series": v.series, "vintage_id": v.vintage_id, "reasons": reasons})
        else:
            eligible.setdefault(v.series, []).append(v)
    selected, conflicts = {}, []
    for series, rows in sorted(eligible.items()):
        # One immutable source/vintage identity cannot acquire a different
        # economic date, value or provenance on a repeat fetch. Receipt and
        # knowledge clocks may advance; the source facts may not.
        facts = {}
        for v in rows:
            identity = (v.vintage_id, v.source_digest)
            a = v.observation
            signature = (v.effective_date, Decimal(str(a.value)), a.unit, a.currency,
                _clock(a.as_of, "as_of"), a.source_ref, a.input_method, a.role,
                v.release_at, v.release_clock_basis, v.revision)
            facts.setdefault(identity, set()).add(signature)
        if any(len(versions) != 1 for versions in facts.values()):
            conflicts.append({"series": series, "reason": "immutable_vintage_metadata_conflict"})
            continue
        # Re-fetching one immutable vintage cannot advance its first observed
        # availability or create a new revision. Keep the earliest eligible copy.
        unique = {}
        for v in rows:
            key = (v.vintage_id, v.source_digest, str(v.observation.value), v.release_at, v.release_clock_basis)
            if key not in unique or _clock(v.observation.known_at, "known_at") < _clock(unique[key].observation.known_at, "known_at"):
                unique[key] = v
        rows = list(unique.values())
        newest_date = max(v.effective_date for v in rows)
        newest = [v for v in rows if v.effective_date == newest_date]
        if len({v.release_clock_basis for v in newest}) > 1:
            # A body-availability upper bound is not an exact release time.
            # A later fetch of an old print cannot outrank a real revision.
            conflicts.append({"series": series,
                "reason": "mixed_release_clock_bases_cannot_order_revisions"})
            continue
        rank = lambda v: (v.effective_date, _clock(v.release_at or v.body_received_at, "release_available_by"))
        best = max(map(rank, rows))
        tied = [v for v in rows if rank(v) == best]
        if len({(str(v.observation.value), v.source_digest, v.vintage_id) for v in tied}) != 1:
            conflicts.append({"series": series, "reason": "same_release_conflicting_vintages"})
            continue
        v = min(tied, key=lambda x: _clock(x.observation.known_at, "known_at"))
        selected[series] = {"effective_date": v.effective_date.isoformat(),
            "value": str(v.observation.value), "unit": v.observation.unit,
            "release_at": _clock(v.release_at, "release_at").isoformat() if v.release_at else None,
            "release_clock_basis": v.release_clock_basis,
            "release_available_by": _clock(v.release_at or v.body_received_at, "release_available_by").isoformat(),
            "known_at": _clock(v.observation.known_at, "known_at").isoformat(),
            "body_received_at": _clock(v.body_received_at, "body_received_at").isoformat(),
            "as_of": _clock(v.observation.as_of, "as_of").isoformat(),
            "source_ref": v.observation.source_ref, "input_method": v.observation.input_method,
            "source_digest": v.source_digest, "vintage_id": v.vintage_id, "revision": v.revision}
    missing = sorted(set(SERIES_UNITS) - set(selected))
    return {"method_version": "financing_vintage_selection.v1", "decision_cutoff_utc": at.isoformat(),
        "selected": selected, "excluded": excluded, "conflicts": conflicts,
        "missing_series": missing, "status": "INSUFFICIENT_PIT" if missing or conflicts else "SOURCE_CONTRACT_SATISFIED",
        "canonical_liquidity_baseline": "EXTERNAL_OWNER_REQUIRED", "probabilities": None,
        "selection_policy": "latest_eligible_effective_date_then_qualified_release_availability; original_vintages_not_refreshed"}
