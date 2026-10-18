"""Options Matrix identity composition over captured existing Data OS inputs.

Kept separate from the shared entity consumer so unrelated workspace consumers do
not acquire Matrix retention dependencies. This module grants no rights or Save.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from engine.options_matrix_retention import (
    HistoricalUnavailable,
    SnapshotReference,
    matrix_coordinate_tokens,
    matrix_observed_side_tokens,
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


# --- Retained selection membership (pure consumer composition) -----------------
#
# The closed candidate structural contract below is a shape contract only. It is
# validated by hand with the standard library: no jsonschema runtime dependency,
# no coercion, no defaults and no inferred fields. Validating it grants no
# rights, no Save, no persistence and no metric availability.

_SELECTION_MAX_BYTES = 2048
_SELECTION_SCHEMA = "options_matrix_selection.v1"
_SELECTION_ROOT_KEYS = frozenset({"schema", "primary", "comparisons", "view"})
_SELECTION_COORDINATE_KEYS = frozenset({"expiry", "side", "strike"})
_SELECTION_VIEW_KEYS = frozenset(
    {"lens", "metric", "side", "expiry", "display_mode"}
)
_SELECTION_LENS = "chain"
_SELECTION_METRICS = frozenset({"volume", "openInterest", "deltaOi"})
_SELECTION_VIEWS = frozenset({"3d", "table"})
_SELECTION_SIDES = frozenset({"call", "put"})
_SELECTION_VIEW_SIDES = frozenset({"all", "call", "put"})
_SELECTION_ALL = "all"
_SELECTION_MAX_COMPARISONS = 3
# maxLength 21 of the contract: 12 integral digits, the separator and 8 fractional.
_SELECTION_STRIKE_MAX_LENGTH = 21
_SELECTION_DATE_PATTERN = re.compile(r"(?!0000)[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SELECTION_STRIKE_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{0,7}[1-9])?")


@dataclass(frozen=True)
class OptionCoordinate:
    """One retained chain coordinate exactly as selected and stored."""

    expiry: str
    strike: str
    side: str


@dataclass(frozen=True)
class OptionSelectionView:
    """Stored view filters, syntax only.

    ``side`` and ``expiry`` are the only filters that drive hidden flags. ``metric``
    is recorded and never attested as available.
    """

    lens: str
    metric: str
    side: str
    expiry: str
    display_mode: str


@dataclass(frozen=True)
class OptionMatrixSelectionIdentity:
    """Exact retained Options Matrix selection joined to its captured identity.

    Membership says only that the stored coordinates were observed in this exact
    snapshot with the stored view filters recorded. It is not metric availability,
    option-contract identity, source rights, Save admission, I/O, original source
    authentication or persistence.
    """

    matrix: OptionMatrixIdentity
    primary: OptionCoordinate
    comparisons: tuple[OptionCoordinate, ...]
    view: OptionSelectionView
    primary_hidden: bool
    comparisons_hidden: tuple[bool, ...]


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """Object hook that refuses duplicate keys anywhere in the document."""
    unique: dict = {}
    for key, value in pairs:
        if key in unique:
            raise ValueError(f"duplicate JSON key: {key!r}")
        unique[key] = value
    return unique


def _reject_nonfinite_constant(name: str) -> float:
    raise ValueError(f"nonfinite JSON constant: {name}")


def _finite_number(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"nonfinite JSON number: {text}")
    return value


def _parse_selection_document(selection: bytes) -> dict:
    """Exact bytes in, parsed object out. No text, transport or file input."""
    if not isinstance(selection, bytes):
        raise IdentityResolutionError("matrix selection must be exact bytes")
    raw = bytes(selection)
    if len(raw) > _SELECTION_MAX_BYTES:
        raise IdentityResolutionError(
            f"matrix selection exceeds {_SELECTION_MAX_BYTES} bytes"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IdentityResolutionError(f"matrix selection is not UTF-8: {exc}") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
            parse_float=_finite_number,
        )
    except (ValueError, RecursionError) as exc:
        raise IdentityResolutionError(f"matrix selection is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise IdentityResolutionError("matrix selection must be a JSON object")
    return document


def _selection_object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise IdentityResolutionError(f"matrix selection {label} must be an object")
    return value


def _selection_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise IdentityResolutionError(f"matrix selection {label} must be a string")
    return value


def _selection_member(container: dict, key: str, label: str) -> object:
    if key not in container:
        raise IdentityResolutionError(f"matrix selection {label} is missing {key}")
    return container[key]


def _selection_unknown_keys(value: dict, allowed: frozenset, label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise IdentityResolutionError(
            f"matrix selection {label} has unknown keys: {sorted(unknown)}"
        )


def _selection_date(value: object, label: str) -> str:
    text = _selection_string(value, label)
    if len(text) != 10 or _SELECTION_DATE_PATTERN.fullmatch(text) is None:
        raise IdentityResolutionError(f"matrix selection {label} is not YYYY-MM-DD")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise IdentityResolutionError(
            f"matrix selection {label} is not a real Gregorian date: {exc}"
        ) from exc
    return text


def _selection_strike(value: object, label: str) -> str:
    """Canonical decimal string, kept exact. Never rounded or re-rendered."""
    text = _selection_string(value, label)
    if (
        len(text) > _SELECTION_STRIKE_MAX_LENGTH
        or _SELECTION_STRIKE_PATTERN.fullmatch(text) is None
    ):
        raise IdentityResolutionError(
            f"matrix selection {label} strike is not a canonical decimal string"
        )
    try:
        exact = Decimal(text)
    except ArithmeticError as exc:
        raise IdentityResolutionError(
            f"matrix selection {label} strike is not decimal exact: {exc}"
        ) from exc
    if exact <= 0:
        raise IdentityResolutionError(f"matrix selection {label} strike must be positive")
    return text


def _selection_side(value: object, label: str) -> str:
    text = _selection_string(value, label)
    if text not in _SELECTION_SIDES:
        raise IdentityResolutionError(f"matrix selection {label} side must be call or put")
    return text


def _selection_coordinate(value: object, label: str) -> tuple[str, str, str]:
    """Validated coordinate as an (expiry, strike, side) retention token."""
    coordinate = _selection_object(value, label)
    _selection_unknown_keys(coordinate, _SELECTION_COORDINATE_KEYS, label)
    return (
        _selection_date(_selection_member(coordinate, "expiry", label), f"{label} expiry"),
        _selection_strike(_selection_member(coordinate, "strike", label), f"{label}"),
        _selection_side(_selection_member(coordinate, "side", label), f"{label}"),
    )


def _selection_view(value: object) -> OptionSelectionView:
    view = _selection_object(value, "view")
    _selection_unknown_keys(view, _SELECTION_VIEW_KEYS, "view")
    lens = _selection_string(_selection_member(view, "lens", "view"), "view lens")
    if lens != _SELECTION_LENS:
        raise IdentityResolutionError(f"matrix selection view lens must be {_SELECTION_LENS}")
    metric = _selection_string(_selection_member(view, "metric", "view"), "view metric")
    if metric not in _SELECTION_METRICS:
        raise IdentityResolutionError("matrix selection view metric is not a stored metric")
    side = _selection_string(_selection_member(view, "side", "view"), "view side")
    if side not in _SELECTION_VIEW_SIDES:
        raise IdentityResolutionError("matrix selection view side is not a stored filter")
    expiry_value = _selection_member(view, "expiry", "view")
    expiry = (
        _SELECTION_ALL
        if isinstance(expiry_value, str) and expiry_value == _SELECTION_ALL
        else _selection_date(expiry_value, "view expiry")
    )
    display_mode = _selection_string(
        _selection_member(view, "display_mode", "view"), "view display_mode"
    )
    if display_mode not in _SELECTION_VIEWS:
        raise IdentityResolutionError("matrix selection view display_mode is not stored")
    return OptionSelectionView(lens, metric, side, expiry, display_mode)


def _selection_documents(
    document: dict,
) -> tuple[tuple[str, str, str], tuple[tuple[str, str, str], ...], OptionSelectionView]:
    """Closed schema check. Required fields only, in stored order."""
    _selection_unknown_keys(document, _SELECTION_ROOT_KEYS, "document")
    schema = _selection_string(_selection_member(document, "schema", ""), "schema")
    if schema != _SELECTION_SCHEMA:
        raise IdentityResolutionError(
            f"matrix selection schema must be {_SELECTION_SCHEMA}"
        )
    primary = _selection_coordinate(_selection_member(document, "primary", ""), "primary")
    raw_comparisons = _selection_member(document, "comparisons", "")
    if not isinstance(raw_comparisons, list):
        raise IdentityResolutionError("matrix selection comparisons must be an array")
    if len(raw_comparisons) > _SELECTION_MAX_COMPARISONS:
        raise IdentityResolutionError(
            f"matrix selection comparisons exceed {_SELECTION_MAX_COMPARISONS}"
        )
    comparisons = tuple(
        _selection_coordinate(item, f"comparisons[{index}]")
        for index, item in enumerate(raw_comparisons)
    )
    if len(set(comparisons)) != len(comparisons):
        # Value keyed, so repeated coordinates refuse regardless of JSON key order.
        raise IdentityResolutionError("matrix selection comparisons repeat a coordinate")
    view = _selection_view(_selection_member(document, "view", ""))
    return primary, comparisons, view


def _retained_memberships(
    ref: "SnapshotReference", body: bytes
) -> tuple[frozenset, frozenset]:
    """Own-side observed coordinates and the full snapshot expiry set."""
    try:
        observed = matrix_observed_side_tokens(ref, body)
        full = matrix_coordinate_tokens(ref, body)
    except HistoricalUnavailable as exc:
        raise IdentityResolutionError(f"matrix retention unavailable: {exc}") from exc
    try:
        side_members = frozenset(
            (expiry, Decimal(strike), side) for expiry, strike, side in observed
        )
        expiries = frozenset(expiry for expiry, _ in full)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise IdentityResolutionError(f"matrix retention coordinates invalid: {exc}") from exc
    return side_members, expiries


def _selection_hidden(expiry: str, side: str, view: OptionSelectionView) -> bool:
    """Stored side/expiry filters only. Hidden pins stay retained."""
    if view.side != _SELECTION_ALL and side != view.side:
        return True
    if view.expiry != _SELECTION_ALL and expiry != view.expiry:
        return True
    return False


def resolve_option_matrix_selection(
    ref: "SnapshotReference",
    matrix: IdentityArtifactRead,
    selection: bytes,
    *,
    vendor: str,
    decision_at: datetime | str,
    aliases: IdentityArtifactRead,
    security_master: IdentityArtifactRead,
    root_evidence: IdentityArtifactRead,
) -> OptionMatrixSelectionIdentity:
    """Join an exact retained selection to its captured Matrix identity.

    The same ref/matrix and supplied captures resolve the underlying through the
    unchanged :func:`resolve_option_matrix_security`; an unresolved root refuses
    instead of returning None. Membership comes from the retained snapshot's own
    observed side witnesses and full coordinate set. This establishes membership in the supplied bytes and
    stored view only, never metric availability, contract identity, source rights,
    Save admission, I/O, source authentication or persistence.
    """
    identity = resolve_option_matrix_security(
        ref, matrix, vendor=vendor, decision_at=decision_at, aliases=aliases,
        security_master=security_master, root_evidence=root_evidence,
    )
    if identity is None:
        raise IdentityResolutionError(
            "matrix underlying identity unresolved for selection"
        )
    try:
        primary, comparisons, view = _selection_documents(
            _parse_selection_document(selection)
        )
        side_members, expiries = _retained_memberships(ref, matrix.body)
        if view.expiry != _SELECTION_ALL and view.expiry not in expiries:
            raise IdentityResolutionError(
                f"matrix selection view expiry {view.expiry} is not retained"
            )
        for expiry, strike, side in (primary, *comparisons):
            if (expiry, Decimal(strike), side) not in side_members:
                raise IdentityResolutionError(
                    f"matrix selection coordinate {expiry} {strike} {side} "
                    "is not retained in the snapshot"
                )
    except HistoricalUnavailable as exc:
        raise IdentityResolutionError(f"matrix retention unavailable: {exc}") from exc
    except IdentityResolutionError:
        raise
    except (ValueError, TypeError, KeyError, ArithmeticError, RecursionError) as exc:
        raise IdentityResolutionError(f"matrix selection contract invalid: {exc}") from exc
    return OptionMatrixSelectionIdentity(
        matrix=identity,
        primary=OptionCoordinate(primary[0], primary[1], primary[2]),
        comparisons=tuple(OptionCoordinate(*coordinate) for coordinate in comparisons),
        view=view,
        primary_hidden=_selection_hidden(primary[0], primary[2], view),
        comparisons_hidden=tuple(
            _selection_hidden(coordinate[0], coordinate[2], view)
            for coordinate in comparisons
        ),
    )
