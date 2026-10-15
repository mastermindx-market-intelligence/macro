"""Options Matrix identity composition over captured existing Data OS inputs.

Kept separate from the shared entity consumer so unrelated workspace consumers do
not acquire Matrix retention dependencies. This module grants no rights or Save.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from engine.options_matrix_retention import (
    HistoricalUnavailable,
    SnapshotReference,
    verify_snapshot,
)
from lib.dataos.identity import IdentityError, _aware_utc

from .entity import (
    IdentityArtifactRead,
    IdentityResolutionError,
    OptionUnderlyingIdentity,
    _identity_read,
    resolve_option_underlying_security,
)


@dataclass(frozen=True)
class OptionMatrixIdentity:
    """Exact Matrix reference joined to a captured canonical underlying.

    This is neither a source-use decision nor Saved Research admission. Selection
    membership and current principal/snapshot/action rights remain separate.
    """

    snapshot: "SnapshotReference"
    underlying: OptionUnderlyingIdentity
    available_at: datetime


def resolve_option_matrix_security(
    ref: "SnapshotReference", matrix: IdentityArtifactRead, *, vendor: str,
    decision_at: datetime | str, aliases: IdentityArtifactRead,
    security_master: IdentityArtifactRead, root_evidence: IdentityArtifactRead,
) -> OptionMatrixIdentity | None:
    """Use the verified Matrix root and source session, never caller substitutes.

    The admitted reader supplies the vendor namespace and exact artifact reads.
    Their hashes and clocks are consistency checks, not capture authentication.
    No bucket read, mutable-head fallback, alias publication or implicit clock.
    """
    try:
        cutoff = _aware_utc(decision_at, "decision_at")
        matrix_at = _identity_read(matrix, cutoff)
        verify_snapshot(ref, matrix.body)
        if ref.session is None:
            raise IdentityResolutionError("matrix source session unavailable")
        on = date.fromisoformat(ref.session)
        if on > matrix_at.date():
            raise IdentityResolutionError("matrix source session is after captured read")
        underlying = resolve_option_underlying_security(
            vendor, ref.root, on, decision_at=cutoff, aliases=aliases,
            security_master=security_master, root_evidence=root_evidence,
        )
        if underlying is None:
            return None
        return OptionMatrixIdentity(ref, underlying, max(matrix_at, underlying.available_at))
    except (IdentityError, HistoricalUnavailable) as exc:
        raise IdentityResolutionError(f"matrix identity contract invalid: {exc}") from exc
