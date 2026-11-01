"""Source-rights reader and typed hold for Fundamental Forensics (FIF Z0 A52).

The coverage contract (``config/fundamental_forensics/coverage/
five_issuer_v1.json``) declares a ``source_rights`` block: which provider a
capture reads, under which access policy, and which credentials, licences or
purchases it would require.  Masterplan D0/A52 makes those rights a RELEASE
control: a source whose rights are not established must hold only the
dependent pack/release while independent work proceeds.  Before this module
the control lived only in the contract bytes and one static guard — nothing
at runtime read it.

This is the smallest runtime form of that control.  ``read_source_rights``
turns the contract bytes into a ``SourceRights`` record without ever coercing
or defaulting (an unusable block is a typed ``SourceRightsError``), and
``rights_hold`` decides, from the record alone, whether THIS lane may run a
capture: any declared credential requirement, any accepted licence or
purchase, or an access policy outside the established set is a ``RightsHold``
naming ONLY the provider — never an issuer, a pack or a credential value.

No credential lookup happens here and none is implied: this lane never reads
env vars, keychains, secret-like files or the network; a rights hold is
decided from the contract bytes alone.  Deliberately a LEAF like the other
FIF vocabulary modules — no I/O, no clock, no collector or script imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

#: The one access policy established at BASE: the SEC fair-access declared
#: user agent the capture edge already resolves through the FIF-family
#: canonical helper.
DEFAULT_ALLOWED_ACCESS_POLICIES: frozenset[str] = frozenset(
    {"sec_fair_access_declared_user_agent"}
)


class SourceRightsError(ValueError):
    """A contract's ``source_rights`` block is unusable; ``code`` names why."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceRights:
    """The declared rights picture of ONE provider, read from the contract."""

    provider: str
    access_policy: str
    credentials_required: tuple[str, ...]
    licences_accepted: tuple[str, ...]
    purchases: tuple[str, ...]


@dataclass(frozen=True)
class RightsHold:
    """A per-provider release hold; carries no issuer, pack or credential value."""

    code: str
    provider: str
    reason: str


def _malformed(message: str) -> SourceRightsError:
    return SourceRightsError(message, code="source_rights_malformed")


def _string_list(block: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = block.get(field)
    if not isinstance(value, list):
        raise _malformed(f"source_rights.{field} must be a list of non-empty strings")
    for item in value:
        if not isinstance(item, str) or not item:
            raise _malformed(
                f"source_rights.{field} must be a list of non-empty strings"
            )
    return tuple(value)


def read_source_rights(contract: Mapping) -> SourceRights:
    """Read ONE contract's ``source_rights`` block; never coerce, never default.

    A missing block, a non-mapping block (or contract), a missing/empty
    ``provider`` or ``access_policy``, or any list field that is not a list
    of non-empty strings raises ``SourceRightsError`` with the fixed code
    ``source_rights_malformed`` — no field is defaulted, coerced or guessed.
    """
    if not isinstance(contract, Mapping):
        raise _malformed("coverage contract must be a mapping")
    block = contract.get("source_rights")
    if not isinstance(block, Mapping):
        raise _malformed("coverage contract carries no usable source_rights mapping")
    provider = block.get("provider")
    if not isinstance(provider, str) or not provider:
        raise _malformed("source_rights.provider must be a non-empty string")
    access_policy = block.get("access_policy")
    if not isinstance(access_policy, str) or not access_policy:
        raise _malformed("source_rights.access_policy must be a non-empty string")
    return SourceRights(
        provider=provider,
        access_policy=access_policy,
        credentials_required=_string_list(block, "credentials_required"),
        licences_accepted=_string_list(block, "licences_accepted"),
        purchases=_string_list(block, "purchases"),
    )


def rights_hold(
    rights: SourceRights,
    *,
    allowed_access_policies: frozenset[str] = DEFAULT_ALLOWED_ACCESS_POLICIES,
) -> RightsHold | None:
    """Decide from the rights record alone whether this lane may run a capture.

    Returns ``None`` when the rights are established (the frozen contract's
    current values).  Otherwise the first matching condition holds, in the
    order the A52 seat ruling froze: a declared credential requirement, an
    accepted licence or purchase, then an unestablished access policy.  The
    hold names ONLY the provider; reason strings carry counts, never
    credential names or values, issuer or pack identifiers.
    """
    if rights.credentials_required:
        return RightsHold(
            code="source_rights_credentials_undeclared",
            provider=rights.provider,
            reason=(
                f"contract requires {len(rights.credentials_required)} credential(s) "
                "this lane cannot establish"
            ),
        )
    if rights.licences_accepted or rights.purchases:
        return RightsHold(
            code="source_rights_licence_unestablished",
            provider=rights.provider,
            reason=(
                f"contract declares {len(rights.licences_accepted)} accepted "
                f"licence(s) and {len(rights.purchases)} purchase(s); no "
                "acceptance machinery exists at BASE"
            ),
        )
    if rights.access_policy not in allowed_access_policies:
        return RightsHold(
            code="source_rights_policy_unknown",
            provider=rights.provider,
            reason=(
                "source access policy is outside the established set of "
                f"{len(allowed_access_policies)} policy/policies"
            ),
        )
    return None
