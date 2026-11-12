"""Exact contract identity bridge for Options Alpha expression campaigns.

Deliberately narrow: it encodes one already-selected campaign group (exact
ticker, expiration, right, strike_key, strike) into the incumbent NBBO cohort
contract and reports whether a Theta list-contracts catalog holds that exact
identity.  Terms are never inferred from root, OCC symbol, catalog fields, or
policy; list-contracts supplies none, so terms stay explicitly unavailable.
No clock, I/O, or outcome/selection/rank/size/trading authority lives here.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from decimal import Decimal

from engine import options_nbbo_cohort as cohort

__all__ = ["IdentityUnavailable", "contract_from_group", "theta_contract_identity_evidence"]


class IdentityUnavailable(ValueError):
    """The exact contract identity cannot be established from the input."""


# The five identity members a campaign group must carry; any other members on
# the group are never consulted.  Groups spell the side C/P while the
# incumbent contract enum is the equivalent lowercase word.
_GROUP_KEYS = ("ticker", "expiration", "right", "strike_key", "strike")
_GROUP_RIGHTS = {"C": "call", "P": "put"}

# The documented Theta option list-contracts row supplies exactly these four
# fields and no terms; any other key marks the shape unsupported as source
# authority.  The catalog right may spell call/put or C/P.
_CATALOG_ROW_KEYS = frozenset({"symbol", "expiration", "strike", "right"})
_CATALOG_RIGHTS = {"call": "call", "c": "call", "put": "put", "p": "put"}


def _unavailable(exc: cohort.NbboCohortError) -> IdentityUnavailable:
    return IdentityUnavailable(f"contract identity unavailable: {exc}")


def _validated_contract(contract: Mapping[str, object]) -> dict[str, object]:
    """Return the incumbent-normalized contract for an already-selected identity."""
    try:
        return cohort.validate_contract(contract)
    except cohort.NbboCohortError as exc:
        raise _unavailable(exc) from exc


def _strike_millis(value: object, *, label: str) -> int:
    """Return integer millis for an exact numeric strike, with no rounding."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IdentityUnavailable(f"{label} must be an exact number")
    if isinstance(value, float) and not math.isfinite(value):
        raise IdentityUnavailable(f"{label} must be finite")
    strike = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if strike <= 0:
        raise IdentityUnavailable(f"{label} must be positive")
    millis = strike * 1000
    if millis != millis.to_integral_value():
        raise IdentityUnavailable(f"{label} is not exactly representable as integer millis")
    return int(millis)


def contract_from_group(group: Mapping[str, object]) -> dict[str, object]:
    """Encode one campaign group into the incumbent exact contract.

    The five identity members are used exactly as given: the root stays
    verbatim (no stripping or case conversion), the strike_key must already
    be canonical decimal text, and the numeric strike must agree with it
    exactly as positive integer millis.  The padded OCC symbol is the
    deterministic identity encoding; all six fields go to the incumbent
    ``validate_contract``.  Unknown identity fails instead of substituting.
    """
    if not isinstance(group, Mapping):
        raise IdentityUnavailable("campaign group must be an object")
    for key in _GROUP_KEYS:
        if key not in group:
            raise IdentityUnavailable(f"campaign group is missing {key!r}")
    for name in ("ticker", "expiration", "strike_key"):
        if not isinstance(group[name], str):
            raise IdentityUnavailable(f"campaign group {name} must be a string")
    right = group["right"]
    if not isinstance(right, str) or right not in _GROUP_RIGHTS:
        raise IdentityUnavailable("campaign group right must be exactly 'C' or 'P'")
    millis = _strike_millis(group["strike"], label="campaign group strike")
    try:
        return _validated_contract(
            {
                "root": group["ticker"],
                "expiration": group["expiration"],
                "right": _GROUP_RIGHTS[right],
                "strike": group["strike_key"],
                "strike_millis": millis,
                "occ_symbol": cohort.canonical_occ_symbol(
                    root=group["ticker"],
                    expiration=group["expiration"],
                    right=_GROUP_RIGHTS[right],
                    strike_millis=millis,
                ),
            }
        )
    except cohort.NbboCohortError as exc:
        raise _unavailable(exc) from exc


def _catalog_row(row: object) -> Mapping[str, object]:
    """Reject any row shape outside the documented list-contracts schema."""
    if not isinstance(row, Mapping) or set(row) != _CATALOG_ROW_KEYS:
        raise IdentityUnavailable("unsupported theta response shape")
    if not isinstance(row["symbol"], str) or not isinstance(row["expiration"], str):
        raise IdentityUnavailable("unsupported theta response shape")
    strike = row["strike"]
    if (
        isinstance(strike, bool)
        or not isinstance(strike, (int, float))
        or (isinstance(strike, float) and not math.isfinite(strike))
    ):
        raise IdentityUnavailable("unsupported theta response shape")
    if not isinstance(row["right"], str) or row["right"].lower() not in _CATALOG_RIGHTS:
        raise IdentityUnavailable("theta catalog right is not a call/put enum value")
    return row


def _row_matches(row: Mapping[str, object], contract: Mapping[str, object]) -> bool:
    """Return whether a catalog row equals the already-selected exact contract."""
    if row["symbol"] != contract["root"] and row["symbol"] != contract["occ_symbol"]:
        return False
    if _CATALOG_RIGHTS[row["right"].lower()] != contract["right"]:
        return False
    if row["expiration"] != contract["expiration"]:
        return False
    strike = row["strike"]
    row_millis = Decimal(repr(strike)) if isinstance(strike, float) else Decimal(strike)
    return row_millis * 1000 == Decimal(contract["strike_millis"])


def theta_contract_identity_evidence(
    raw_bytes: bytes, contract: Mapping[str, object]
) -> dict[str, object]:
    """Report whether the Theta list-contracts catalog holds the exact contract.

    ``raw_bytes`` must strictly parse (no duplicate keys, no non-finite
    numbers) as the documented flat JSON array of rows with exactly symbol,
    expiration, strike, and right.  A row matches only when all four identity
    fields equal the already-selected contract (right may spell call/put or
    C/P); zero or multiple exact matches both fail.  Returns identity
    observed, null unavailable terms, and the exact raw hash and count.
    """
    if not isinstance(raw_bytes, bytes):
        raise IdentityUnavailable("theta catalog payload must be raw bytes")
    validated = _validated_contract(contract)
    try:
        document = cohort.strict_json_value(raw_bytes, label="theta contract catalog")
    except cohort.NbboCohortError as exc:
        raise IdentityUnavailable(f"theta contract catalog rejected: {exc}") from exc
    if not isinstance(document, list):
        raise IdentityUnavailable("theta contract catalog must be a flat JSON array")
    matches = sum(1 for row in document if _row_matches(_catalog_row(row), validated))
    if matches == 0:
        raise IdentityUnavailable(
            "theta contract catalog does not contain the exact contract identity"
        )
    if matches > 1:
        raise IdentityUnavailable(
            "theta contract catalog contains a duplicate exact contract identity"
        )
    return {
        "identity_observed": True,
        "multiplier": None,
        "standard_deliverable": None,
        "terms_status": "unavailable",
        "terms_reason": "THETA_LIST_CONTRACTS_DOES_NOT_SUPPLY_TERMS",
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_bytes_count": len(raw_bytes),
    }
