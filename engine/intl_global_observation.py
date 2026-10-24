"""Basis-explicit, four-clock, qualified-or-abstain global observation contract.

Every observation names its currency basis (local | usd_unhedged | usd_hedged)
and return basis (price | total-return gross/net), carries four ordered clocks
(observation, source_publication, ingestion, computation) and, for USD bases,
must satisfy the multiplicative return identity

    1 + r_USD = (1 + r_local) * (1 + r_FX)

to RETURN_IDENTITY_TOLERANCE in fraction units. A record is either qualified
or abstains with a closed vocabulary of reasons; nothing is silently coerced
into a value. Only local and price bases are supported today: hedged and
total-return bases abstain basis_unsupported until a real source exists.

This module is a contract, not a collector: it imports no intl module and no
pandas, and performs no I/O. The incumbent qualifier remains the authority;
adapters may keep or withhold a value, never upgrade one.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from datetime import datetime, timezone

CONTRACT_VERSION = "intl-global-observation-v1"
REQUIRED_CLOCKS = ("observation", "source_publication", "ingestion", "computation")
CLOCK_PRECISIONS = ("exact", "upper_bound", "session_date")
CURRENCY_BASES = ("local", "usd_unhedged", "usd_hedged")
SUPPORTED_CURRENCY_BASES = frozenset({"local", "usd_unhedged"})
RETURN_BASES = ("price", "total_return_gross", "total_return_net")
SUPPORTED_RETURN_BASES = frozenset({"price"})
FX_ORIENTATIONS = ("local_per_USD", "USD_per_local")
QUALIFICATION_STATES = ("qualified", "abstain")
ABSTAIN_REASONS = frozenset({
    "clock_missing",
    "clock_order_violation",
    "value_unavailable",
    "return_identity_violation",
    "identity_mismatch",
    "basis_unsupported",
    "rights_unconfirmed",
    "incumbent_qualification_withheld",
    "source_evidence_missing",
})
RETURN_IDENTITY_TOLERANCE = 1e-9  # fraction units
# Frozen: EZ is the euro-area aggregate id of the IM11 universe; this module
# does NOT import IM11 and never re-derives the mapping from configuration.
LEGACY_MARKET_TO_UNIVERSE_ID = {
    "JP": "JP", "KR": "KR", "TW": "TW", "IN": "IN",
    "AU": "AU", "GB": "GB", "EZ": "EZ",
}
IDENTITY_FIELDS = (
    "universe_id", "market_id", "index_id", "fx_id", "horizon",
    "currency_basis", "return_basis", "window_start", "window_end",
    "source_content_sha256",
)

_ORDERED_CLOCK_PAIRS = tuple(zip(REQUIRED_CLOCKS, REQUIRED_CLOCKS[1:]))


class ObservationError(ValueError):
    """Malformed observation request. The contract never guesses a basis."""


def _finite_number(value) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def fx_return_from_closes(fx_start: float, fx_end: float, orientation: str) -> float:
    """FX return in fraction units from two strictly positive closes.

    USD_per_local (e.g. GBPUSD): fx_end / fx_start - 1. local_per_USD
    (e.g. USDJPY, fx_invert): a higher pair is a weaker local currency, so
    the USD return inverts to fx_start / fx_end - 1.
    """
    if orientation not in FX_ORIENTATIONS:
        raise ObservationError("unknown_fx_orientation")
    for name, close in (("fx_start", fx_start), ("fx_end", fx_end)):
        if _finite_number(close) is None or close <= 0:
            raise ObservationError(f"invalid_fx_close:{name}")
    start, end = float(fx_start), float(fx_end)
    if orientation == "USD_per_local":
        return end / start - 1.0
    return start / end - 1.0


def return_identity_residual(r_local: float, r_fx: float, r_usd: float) -> float:
    """abs((1 + r_usd) - (1 + r_local)(1 + r_fx)), all inputs in fractions."""
    return abs((1.0 + r_usd) - (1.0 + r_local) * (1.0 + r_fx))


def decompose(local_pct: float, usd_pct: float, fx_pct: float) -> dict:
    """Percentage-point decomposition plus the identity residual diagnostic."""
    return {
        "local_pct": local_pct,
        "fx_pct": fx_pct,
        "usd_pct": usd_pct,
        "additive_fx_contribution_pp": usd_pct - local_pct,
        "interaction_pp": usd_pct - local_pct - fx_pct,
        "identity_residual": return_identity_residual(
            local_pct / 100.0, fx_pct / 100.0, usd_pct / 100.0),
    }


def _parse_clock_instant(text: str) -> datetime | None:
    """ISO-8601 instant as written (naive stays naive); None when unusable."""
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:  # a naive value is UTC
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _validated_clocks(clocks) -> dict | None:
    """Every required clock as {name: (datetime-as-written, precision)}, or None."""
    if not isinstance(clocks, dict):
        return None
    parsed = {}
    for name in REQUIRED_CLOCKS:
        entry = clocks.get(name)
        if not isinstance(entry, dict):
            return None
        precision = entry.get("precision")
        if precision not in CLOCK_PRECISIONS:
            return None
        at = entry.get("at")
        if type(at) is not str or not at.strip():
            return None
        moment = _parse_clock_instant(at)
        if moment is None:
            return None
        parsed[name] = (moment, precision)
    return parsed


def check_clocks(clocks: dict) -> str | None:
    """'clock_missing', 'clock_order_violation', or None when the four hold.

    observation <= source_publication <= ingestion <= computation. When either
    side of a pair is a session_date, only calendar dates compare; otherwise
    UTC instants (a naive value is UTC).
    """
    parsed = _validated_clocks(clocks)
    if parsed is None:
        return "clock_missing"
    for earlier, later in _ORDERED_CLOCK_PAIRS:
        left, left_precision = parsed[earlier]
        right, right_precision = parsed[later]
        if "session_date" in (left_precision, right_precision):
            if left.date() > right.date():
                return "clock_order_violation"
        elif _as_utc(left) > _as_utc(right):
            return "clock_order_violation"
    return None


def observation_id(identity: dict) -> str:
    """Content id over the identity alone; publication stamps never enter it."""
    encoded = json.dumps(identity, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return "obs:sha256:" + hashlib.sha256(encoded).hexdigest()


def build_observation(*, identity: dict, clocks: dict, values: dict,
                      rights: dict | None, incumbent: dict | None,
                      evidence_ref: str | None,
                      snapshot_published_at: str | None = None,
                      extra_reasons: tuple[str, ...] = ()) -> dict:
    """Qualify one observation or abstain with every applicable closed reason.

    The incumbent qualifier stays the authority: an observation is qualified
    only when the basis is supported, the clocks are present and ordered, the
    basis value is finite, the return identity holds where it applies, rights
    are confirmed, the incumbent receipt is qualified and source evidence is
    referenced — plus no adapter-supplied extra reasons.
    """
    if not isinstance(identity, dict) or set(identity) != set(IDENTITY_FIELDS):
        raise ObservationError("identity_fields")
    currency_basis = identity["currency_basis"]
    return_basis = identity["return_basis"]
    if currency_basis not in CURRENCY_BASES:
        raise ObservationError("currency_basis")
    if return_basis not in RETURN_BASES:
        raise ObservationError("return_basis")
    market_id = identity["market_id"]
    if market_id not in LEGACY_MARKET_TO_UNIVERSE_ID:
        raise ObservationError("market_id")
    if identity["universe_id"] != LEGACY_MARKET_TO_UNIVERSE_ID[market_id]:
        raise ObservationError("universe_id")
    if not isinstance(extra_reasons, tuple):
        extra_reasons = tuple(extra_reasons)
    for reason in extra_reasons:
        if reason not in ABSTAIN_REASONS:
            raise ObservationError("unknown_abstain_reason")

    reasons = set(extra_reasons)
    supported = (currency_basis in SUPPORTED_CURRENCY_BASES
                 and return_basis in SUPPORTED_RETURN_BASES)
    if not supported:
        reasons.add("basis_unsupported")
    clock_reason = check_clocks(clocks)
    if clock_reason is not None:
        reasons.add(clock_reason)

    supplied = values if isinstance(values, dict) else {}
    local_pct = _finite_number(supplied.get("local_pct"))
    usd_pct = _finite_number(supplied.get("usd_pct"))
    fx_pct = _finite_number(supplied.get("fx_pct"))

    # Diagnostic decomposition whenever all three legs are finite; it is
    # published only on a qualified observation.
    material = None
    residual = None
    if local_pct is not None and usd_pct is not None and fx_pct is not None:
        material = decompose(local_pct, usd_pct, fx_pct)
        residual = material["identity_residual"]

    basis_value = None
    if supported:
        basis_value = local_pct if currency_basis == "local" else usd_pct
        if basis_value is None:
            reasons.add("value_unavailable")
        if currency_basis == "usd_unhedged":
            # The USD basis requires the full decomposition: identity cannot
            # be attested from the USD leg alone.
            if local_pct is None or fx_pct is None:
                reasons.add("value_unavailable")
            elif residual is not None and residual > RETURN_IDENTITY_TOLERANCE:
                reasons.add("return_identity_violation")
        elif material is not None and residual > RETURN_IDENTITY_TOLERANCE:
            # Local basis: checked only when all three legs are supplied.
            reasons.add("return_identity_violation")

    if (not isinstance(rights, dict)
            or type(rights.get("decision_ref")) is not str
            or not rights["decision_ref"].strip()):
        reasons.add("rights_unconfirmed")
    if not isinstance(incumbent, dict) or incumbent.get("quality") != "qualified":
        reasons.add("incumbent_qualification_withheld")
    if type(evidence_ref) is not str or not evidence_ref.strip():
        reasons.add("source_evidence_missing")

    assert all(reason in ABSTAIN_REASONS for reason in reasons)
    state = "qualified" if not reasons else "abstain"
    return {
        "contract_version": CONTRACT_VERSION,
        "observation_id": observation_id(identity),
        "identity": deepcopy(identity),
        "clocks": deepcopy(clocks),
        "snapshot_published_at": snapshot_published_at,
        "state": state,
        "abstain_reasons": sorted(reasons),
        "value": ({"pct": basis_value, "unit": "percent"}
                  if state == "qualified" else None),
        "decomposition": deepcopy(material) if state == "qualified" else None,
        "identity_residual": residual,
        "incumbent": deepcopy(incumbent) if incumbent is not None else None,
        "rights": deepcopy(rights) if rights is not None else None,
        "evidence_ref": evidence_ref,
    }


def assert_single_basis(observations: list[dict]) -> None:
    """Reject any list mixing currency bases or return bases."""
    if not isinstance(observations, list):
        raise ObservationError("observations_must_be_a_list")
    currency_bases = set()
    return_bases = set()
    for observation in observations:
        identity = observation.get("identity") if isinstance(observation, dict) else None
        if not isinstance(identity, dict):
            raise ObservationError("observation_identity_missing")
        currency_bases.add(identity.get("currency_basis"))
        return_bases.add(identity.get("return_basis"))
    if len(currency_bases) > 1 or len(return_bases) > 1:
        raise ObservationError("mixed_observation_bases")
