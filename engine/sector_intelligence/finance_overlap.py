"""Deterministic, pure overlap and basket-state context arithmetic for the Finance
Sector Intelligence lane (Finance T3).

display/context only — never a score, never a membership signal

The functions in this module describe *overlap* between two slices (securities,
business lines, macro drivers, market factors and ownership hierarchy) and the
*basket-state context* of a candidate slice (incumbent baskets, candidate
membership posture, and per-candidate HELD_* missing-property gaps).

They NEVER compute a score, rank, gate, size, trade, or attractiveness signal —
the authority block emitted by ``overlap_report`` and ``basket_state_context``
makes that literal-false contract explicit, and the helpers produce only
plain JSON-serializable values. Every function is pure: no I/O, no randomness,
no time reads, no pandas. Missing states are first-class (None / empty lists /
"HELD_*" tokens) rather than coerced to zero.

The five overlap dimensions (SECURITY, BUSINESS_LINE, MACRO_DRIVER,
MARKET_FACTOR, OWNERSHIP_HIERARCHY), the five weighting families, and the
twelve membership states are defined verbatim by the frozen research carrier
``research/finance/FINANCE_R11_SUBTHEME_ATLAS_V0_1_2026-09-23.json`` on branch
``sol/finance-sector-research-20260923`` (procedure
``Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157``); this module mirrors
those enumerations as closed vocabularies rather than re-deriving them.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping, Sequence


# ---------------------------------------------------------------------------
# Frozen closed vocabularies (mirror FINANCE_R11_SUBTHEME_ATLAS_V0_1).
# ---------------------------------------------------------------------------

# Five overlap dimensions — verbatim from FINANCE_R11_SUBTHEME_ATLAS_V0_1_2026-09-23.json
# ``overlap_dimensions``.
OVERLAP_DIMENSIONS: tuple[str, ...] = (
    "SECURITY",
    "BUSINESS_LINE",
    "MACRO_DRIVER",
    "MARKET_FACTOR",
    "OWNERSHIP_HIERARCHY",
)

# Five weighting families — verbatim from FINANCE_R11_SUBTHEME_ATLAS_V0_1_2026-09-23.json
# ``weighting_families``. The module is weight-agnostic (it normalizes whatever
# weights it is handed) but exposes this tuple for callers who wish to keep the
# canonical enumeration close at hand.
WEIGHTING_FAMILIES: tuple[str, ...] = (
    "EQUAL_WEIGHT",
    "FLOAT_CAP_CONTEXT",
    "EXPOSURE_WEIGHT",
    "EXPOSURE_CAPPED_WEIGHT",
    "STRATIFIED_EQUAL_WEIGHT",
)

# Closed macro-driver vocabulary (per FINANCE R11-9 audit). Anything outside
# this set raises ValueError naming the offending token.
MACRO_DRIVER_VOCAB: tuple[str, ...] = (
    "policy_rates",
    "yield_curve",
    "deposit_funding",
    "credit_growth",
    "losses_defaults",
    "housing",
    "equity_levels",
    "volatility",
    "issuance_ma",
    "catastrophe_reinsurance",
    "regulation_capital",
    "fx",
    "liquidity",
)

_MACRO_DRIVER_SET = frozenset(MACRO_DRIVER_VOCAB)

# Closed entity-role vocabulary.
_ENTITY_ROLES: tuple[str, ...] = ("MANAGER", "VEHICLE", "OPERATING_COMPANY")
_ENTITY_ROLE_SET = frozenset(_ENTITY_ROLES)

# Whitespace collapse regex (business-line label normalization).
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Small normalization helpers (private).
# ---------------------------------------------------------------------------

def _normalize_security_id(token: Any) -> str | None:
    """Normalize a security-id token. Returns None for empty/whitespace inputs."""
    if token is None:
        return None
    s = str(token).strip()
    if not s:
        return None
    return s.upper()


def _normalize_business_line(token: Any) -> str | None:
    if token is None:
        return None
    s = str(token).strip().lower()
    if not s:
        return None
    return _WS_RE.sub(" ", s)


def _normalize_member_security_id(member: Mapping[str, Any]) -> str | None:
    return _normalize_security_id(member.get("security_id"))


# ---------------------------------------------------------------------------
# Security overlap
# ---------------------------------------------------------------------------

def security_jaccard(
    a: Iterable[str], b: Iterable[str]
) -> float | None:
    """|A∩B| / |A∪B| over normalized security ids.

    Each input is iterated once, stripped, upper-cased and deduped. Empty
    tokens are skipped. If both sides are empty the function returns ``None``
    — NOT 0.0 — so callers can distinguish "no securities recorded" from "no
    overlap". Identical non-empty sets return 1.0; disjoint sets return 0.0.
    """
    set_a = {_normalize_security_id(x) for x in a}
    set_b = {_normalize_security_id(x) for x in b}
    set_a.discard(None)
    set_b.discard(None)
    if not set_a and not set_b:
        return None
    union = set_a | set_b
    if not union:
        return None
    inter = set_a & set_b
    return len(inter) / len(union)


def weighted_overlap(
    a: Mapping[str, float], b: Mapping[str, float]
) -> float | None:
    """Σ min(w_a, w_b) over the union of keys, after each side is normalized to sum 1.0.

    Each side is independently normalized to total 1.0 (sum of all positive
    weights). A side whose normalized total is zero or negative returns
    ``None``. A negative weight anywhere raises ``ValueError`` naming the key.

    The result is symmetric and lies in [0, 1] for non-negative inputs.
    """
    if a is None or b is None:  # type: ignore[unreachable]
        return None

    # Reject negatives up front (both sides).
    for key, val in a.items():
        if val is None:
            continue
        f = float(val)
        if f < 0:
            raise ValueError(f"negative weight: {key!r}={f}")
    for key, val in b.items():
        if val is None:
            continue
        f = float(val)
        if f < 0:
            raise ValueError(f"negative weight: {key!r}={f}")

    pos_a = {k: float(v) for k, v in a.items() if v is not None and float(v) > 0}
    pos_b = {k: float(v) for k, v in b.items() if v is not None and float(v) > 0}

    total_a = sum(pos_a.values())
    total_b = sum(pos_b.values())

    if total_a <= 0 or total_b <= 0:
        return None

    norm_a = {k: v / total_a for k, v in pos_a.items()}
    norm_b = {k: v / total_b for k, v in pos_b.items()}

    keys = set(norm_a) | set(norm_b)
    if not keys:
        return None
    return sum(min(norm_a.get(k, 0.0), norm_b.get(k, 0.0)) for k in keys)


# ---------------------------------------------------------------------------
# Business-line overlap
# ---------------------------------------------------------------------------

def business_line_overlap(
    a: Iterable[str], b: Iterable[str]
) -> float | None:
    """Jaccard over normalized business-line labels (lower-case, collapsed whitespace)."""
    set_a = {_normalize_business_line(x) for x in a}
    set_b = {_normalize_business_line(x) for x in b}
    set_a.discard(None)
    set_b.discard(None)
    if not set_a and not set_b:
        return None
    union = set_a | set_b
    if not union:
        return None
    return len(set_a & set_b) / len(union)


# ---------------------------------------------------------------------------
# Macro-driver overlap
# ---------------------------------------------------------------------------

def macro_driver_overlap(
    a: Iterable[str], b: Iterable[str]
) -> float | None:
    """Jaccard over the closed driver vocabulary.

    Tokens outside ``MACRO_DRIVER_VOCAB`` raise ``ValueError`` naming the
    offending token. Both sides empty ⇒ ``None``. Disjoint valid sets ⇒ 0.0.
    """
    set_a = {_norm_macro_driver(x, side="a") for x in a}
    set_b = {_norm_macro_driver(x, side="b") for x in b}
    set_a.discard(None)
    set_b.discard(None)
    if not set_a and not set_b:
        return None
    union = set_a | set_b
    if not union:
        return None
    return len(set_a & set_b) / len(union)


def _norm_macro_driver(token: Any, *, side: str) -> str | None:
    if token is None:
        return None
    s = str(token).strip()
    if not s:
        return None
    if s not in _MACRO_DRIVER_SET:
        raise ValueError(f"unknown macro_driver token ({side}): {s!r}")
    return s


# ---------------------------------------------------------------------------
# Market-factor cosine overlap
# ---------------------------------------------------------------------------

def market_factor_overlap(
    a: Mapping[str, float], b: Mapping[str, float]
) -> float | None:
    """Cosine similarity over factor loadings keyed by factor name.

    Returns ``None`` when either side is a zero vector (no direction signal).
    Missing keys contribute 0.0 to both sides so the union defines the inner
    product space.
    """
    if a is None or b is None:  # type: ignore[unreachable]
        return None
    keys = set(a) | set(b)
    norm_a = math.sqrt(sum(float(v) ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(float(v) ** 2 for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    dot = sum(float(a.get(k, 0.0)) * float(b.get(k, 0.0)) for k in keys)
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Ownership hierarchy
# ---------------------------------------------------------------------------

def ownership_hierarchy_report(
    members_a: Sequence[Mapping[str, Any]],
    members_b: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Expose manager↔vehicle relationships across two slices without merging them.

    Each member mapping must carry ``security_id`` and ``entity_role`` (one of
    ``MANAGER`` / ``VEHICLE`` / ``OPERATING_COMPANY``) and an optional
    ``parent_security_id``. A manager and its vehicle are NEVER treated as the
    same security: the SECURITY-jaccard helper explicitly excludes them by
    design (they have distinct security ids); this helper exposes the
    relationship separately so the caller can surface it to readers.

    Returns:

    ``manager_vehicle_pairs`` — every distinct (manager, vehicle) pair that
    appears in *either* side. ``in_a`` / ``in_b`` are true on whichever side
    EITHER the manager id OR the vehicle id appears as a member — the
    relationship is "observed on that side" if either endpoint of the pair is
    observable there.

    ``shared_managers`` — manager security ids that appear on **both** sides.

    ``shared_vehicles`` — vehicle security ids that appear on **both** sides.

    ``note`` — a literal reminder that manager and vehicle economics are never
    merged.
    """
    pairs: dict[tuple[str, str], dict[str, bool]] = {}
    managers_a: set[str] = set()
    managers_b: set[str] = set()
    vehicles_a: set[str] = set()
    vehicles_b: set[str] = set()

    def _record(side: str, members: Sequence[Mapping[str, Any]]) -> None:
        for m in members or ():
            sid = _normalize_member_security_id(m)
            if sid is None:
                continue
            role = m.get("entity_role")
            if role not in _ENTITY_ROLE_SET:
                # Skip silently — caller decides whether to validate.
                continue
            parent = m.get("parent_security_id")
            parent_sid = (
                _normalize_security_id(parent) if parent is not None else None
            )
            if role == "MANAGER":
                if side == "a":
                    managers_a.add(sid)
                else:
                    managers_b.add(sid)
            elif role == "VEHICLE":
                if side == "a":
                    vehicles_a.add(sid)
                else:
                    vehicles_b.add(sid)
            # Record a (parent, child) pair whenever a member's
            # parent_security_id is observable, regardless of role labels
            # (parent/child is the structural contract).
            if parent_sid:
                key = (parent_sid, sid)
                entry = pairs.setdefault(key, {"in_a": False, "in_b": False})
                entry["in_a" if side == "a" else "in_b"] = True

    _record("a", members_a)
    _record("b", members_b)

    # Promote in_a / in_b flags to "either endpoint observable on this side".
    # That makes the cross-slice relationship readable: if the manager SYN_MGR
    # is on side A and its BDC vehicle SYN_BDC is on side B, the pair shows
    # in_a=True AND in_b=True so the reader sees the relationship spans both
    # slices rather than appearing to belong to only one.
    pair_list = []
    for (mgr, veh), flags in pairs.items():
        in_a = bool(flags["in_a"]) or (mgr in managers_a) or (veh in vehicles_a)
        in_b = bool(flags["in_b"]) or (mgr in managers_b) or (veh in vehicles_b)
        pair_list.append({
            "manager": mgr,
            "vehicle": veh,
            "in_a": in_a,
            "in_b": in_b,
        })
    pair_list.sort(key=lambda d: (d["manager"], d["vehicle"]))

    return {
        "manager_vehicle_pairs": pair_list,
        "shared_managers": sorted(managers_a & managers_b),
        "shared_vehicles": sorted(vehicles_a & vehicles_b),
        "note": "manager and vehicle economics are never merged",
    }


# ---------------------------------------------------------------------------
# Full overlap report
# ---------------------------------------------------------------------------

_INDEPENDENT_AUTHORITY: dict[str, bool] = {
    "is_score": False,
    "is_membership_signal": False,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_trade": False,
}


def _normalize_security_iter(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    return list(value)


def _normalize_str_iter(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    return list(value)


def _normalize_factor_map(value: Any) -> dict[str, float]:
    if value is None:
        return {}
    out: dict[str, float] = {}
    for k, v in value.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def overlap_report(
    slice_a: Mapping[str, Any], slice_b: Mapping[str, Any]
) -> dict[str, Any]:
    """Compose the five-dimension overlap report between two slice mappings.

    Each slice mapping carries the same shape:

    ``slice_id`` (str), ``securities`` (iterable), ``weights`` (mapping or
    None), ``business_lines`` (iterable), ``macro_drivers`` (iterable),
    ``market_factors`` (mapping or None), ``members`` (sequence of member
    mappings as accepted by ``ownership_hierarchy_report``).

    The function never raises on empty inputs — every numeric field may be
    ``None``. The authority block is literal-false across every dimension.
    """
    sec_a = _normalize_security_iter(slice_a.get("securities"))
    sec_b = _normalize_security_iter(slice_b.get("securities"))

    weights_a_raw = slice_a.get("weights")
    weights_b_raw = slice_b.get("weights")
    weights_a = (
        _normalize_factor_map(weights_a_raw)
        if isinstance(weights_a_raw, Mapping)
        else None
    )
    weights_b = (
        _normalize_factor_map(weights_b_raw)
        if isinstance(weights_b_raw, Mapping)
        else None
    )

    j_security = security_jaccard(sec_a, sec_b)
    weighted_security = (
        weighted_overlap(weights_a, weights_b)
        if weights_a is not None and weights_b is not None
        else None
    )
    norm_a_set = {_normalize_security_id(x) for x in sec_a}
    norm_b_set = {_normalize_security_id(x) for x in sec_b}
    norm_a_set.discard(None)
    norm_b_set.discard(None)
    shared_security = sorted(norm_a_set & norm_b_set)

    bl_a = _normalize_str_iter(slice_a.get("business_lines"))
    bl_b = _normalize_str_iter(slice_b.get("business_lines"))
    j_business = business_line_overlap(bl_a, bl_b)
    shared_business = sorted(
        (
            {_normalize_business_line(x) for x in bl_a}
            & {_normalize_business_line(x) for x in bl_b}
        )
        - {None}
    )

    md_a = _normalize_str_iter(slice_a.get("macro_drivers"))
    md_b = _normalize_str_iter(slice_b.get("macro_drivers"))
    try:
        j_driver = macro_driver_overlap(md_a, md_b)
    except ValueError:
        # Let the caller see unknown-token errors via the underlying helper.
        raise
    shared_driver = sorted(
        (
            {_norm_macro_driver(x, side="a") for x in md_a}
            & {_norm_macro_driver(x, side="b") for x in md_b}
        )
        - {None}
    )

    mf_a_raw = slice_a.get("market_factors")
    mf_b_raw = slice_b.get("market_factors")
    mf_a = (
        _normalize_factor_map(mf_a_raw)
        if isinstance(mf_a_raw, Mapping)
        else None
    )
    mf_b = (
        _normalize_factor_map(mf_b_raw)
        if isinstance(mf_b_raw, Mapping)
        else None
    )
    cosine = market_factor_overlap(mf_a, mf_b) if mf_a is not None and mf_b is not None else None

    members_a_raw = slice_a.get("members") or []
    members_b_raw = slice_b.get("members") or []
    hierarchy = ownership_hierarchy_report(members_a_raw, members_b_raw)

    dimensions: dict[str, Any] = {
        "SECURITY": {
            "jaccard": j_security,
            "weighted": weighted_security,
            "shared": shared_security,
        },
        "BUSINESS_LINE": {
            "jaccard": j_business,
            "shared": shared_business,
        },
        "MACRO_DRIVER": {
            "jaccard": j_driver,
            "shared": shared_driver,
        },
        "MARKET_FACTOR": {
            "cosine": cosine,
        },
        "OWNERSHIP_HIERARCHY": hierarchy,
    }

    note = _classify_independence(j_security, j_driver, cosine)

    return {
        "slice_a": slice_a.get("slice_id"),
        "slice_b": slice_b.get("slice_id"),
        "dimensions": dimensions,
        "independence_note": note,
        "authority": dict(_INDEPENDENT_AUTHORITY),
    }


def _classify_independence(
    j_security: float | None,
    j_driver: float | None,
    cosine: float | None,
) -> str:
    """Map the (security, driver, factor) tuple onto the five-state independence note."""
    if j_security is None and j_driver is None and cosine is None:
        return "INSUFFICIENT_DATA"
    if j_security is not None and j_security > 0:
        return "SHARED_SECURITIES"
    if j_driver is not None and j_driver > 0:
        return "SHARED_DRIVERS_ONLY"
    if cosine is not None and cosine > 0.5:
        return "SHARED_FACTORS_ONLY"
    return "INDEPENDENT"


# ---------------------------------------------------------------------------
# Basket-state context
# ---------------------------------------------------------------------------

_BASKET_AUTHORITY: dict[str, bool] = {
    "may_admit": False,
    "may_mutate_existing_basket": False,
}


def _to_set(value: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for v in value or ():
        sid = _normalize_security_id(v)
        if sid is not None:
            out.add(sid)
    return out


def _basket_id_set(value: Iterable[str]) -> set[str]:
    """Normalize basket-id tokens: strip whitespace, preserve case, dedupe empties."""
    out: set[str] = set()
    for v in value or ():
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        out.add(s)
    return out


def _candidate_security_id(candidate: Mapping[str, Any]) -> str | None:
    sid = candidate.get("security_id")
    if sid is None:
        return None
    return _normalize_security_id(sid)


def basket_state_context(
    slice_id: str,
    *,
    incumbent_basket_ids: Iterable[str],
    candidate_members: Sequence[Mapping[str, Any]],
    pit_validated_ids: Iterable[str],
    identity_validated_ids: Iterable[str],
    exposure_measured_ids: Iterable[str],
) -> dict[str, Any]:
    """Compute the candidate-posture and per-candidate HELD_* missing-property gaps.

    The function NEVER returns ``ADMITTED`` — admission belongs to the basket
    owner. The four postures are SEMANTIC_ONLY, BROAD_CONTEXT_AVAILABLE,
    RESEARCH_CANDIDATE and CANDIDATE_READY_FOR_OWNER_REVIEW, ordered from
    cheapest (no candidates and no incumbents) to richest (every candidate is
    exposure-measured AND identity-validated AND PIT-validated).
    """
    incumbents = sorted(_basket_id_set(incumbent_basket_ids))
    has_incumbents = bool(incumbents)
    candidates = list(candidate_members or ())

    pit_set = _to_set(pit_validated_ids)
    id_set = _to_set(identity_validated_ids)
    exp_set = _to_set(exposure_measured_ids)

    held: list[dict[str, str]] = []
    valid_candidates: list[str] = []
    pit_count = 0
    ready_candidates = 0

    for c in candidates:
        sid = _candidate_security_id(c)
        if sid is None:
            # Candidates without a security_id are recorded as HELD for all
            # three properties in the exposure → identity → pit order.
            held.append({"security_id": "", "state": "HELD_MISSING_EXPOSURE"})
            held.append({"security_id": "", "state": "HELD_MISSING_IDENTITY"})
            held.append({"security_id": "", "state": "HELD_MISSING_PIT"})
            continue

        has_exp = sid in exp_set
        has_id = sid in id_set
        has_pit = sid in pit_set

        if has_exp and has_id and has_pit:
            ready_candidates += 1

        if has_pit:
            pit_count += 1

        if not has_exp:
            held.append({"security_id": sid, "state": "HELD_MISSING_EXPOSURE"})
        if not has_id:
            held.append({"security_id": sid, "state": "HELD_MISSING_IDENTITY"})
        if not has_pit:
            held.append({"security_id": sid, "state": "HELD_MISSING_PIT"})

        if has_exp and has_id and has_pit:
            valid_candidates.append(sid)

    # Decide posture + membership_state.
    if not candidates and not has_incumbents:
        posture = "SEMANTIC_ONLY"
        membership_state = "NONE"
    elif not candidates and has_incumbents:
        posture = "BROAD_CONTEXT_AVAILABLE"
        membership_state = "NONE"
    else:
        # Candidates are present — the posture is always RESEARCH_CANDIDATE
        # unless every candidate is fully validated.
        posture = "RESEARCH_CANDIDATE"
        if pit_count == 0:
            membership_state = "CURRENT_MEMBERSHIP_ONLY"
        elif pit_count == len(candidates):
            membership_state = "PIT_MEMBERSHIP_VALIDATED"
        else:
            membership_state = "PIT_MEMBERSHIP_INCOMPLETE"

        if ready_candidates == len(candidates) and len(candidates) > 0:
            posture = "CANDIDATE_READY_FOR_OWNER_REVIEW"
            # membership_state stays the same — readiness is orthogonal to PIT
            # coverage in the cached independent signal.
            membership_state = "PIT_MEMBERSHIP_VALIDATED"

    return {
        "slice_id": slice_id,
        "posture": posture,
        "incumbent_basket_ids": incumbents,
        "member_count": len(candidates),
        "membership_state": membership_state,
        "held": held,
        "authority": dict(_BASKET_AUTHORITY),
    }


__all__ = [
    "OVERLAP_DIMENSIONS",
    "WEIGHTING_FAMILIES",
    "MACRO_DRIVER_VOCAB",
    "security_jaccard",
    "weighted_overlap",
    "business_line_overlap",
    "macro_driver_overlap",
    "market_factor_overlap",
    "ownership_hierarchy_report",
    "overlap_report",
    "basket_state_context",
]