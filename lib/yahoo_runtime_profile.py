"""Inactive ownership profile and explicit binding for the Sector Yahoo cohort.

The existing runtime publisher verifies and selects a snapshot. This module does
neither: it only carries that verified selection through one computation and
fences legacy writers after an explicitly configured transfer.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterator

SECTOR_CLOSE_TICKERS = (
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
    "XLU", "XLV", "XLY", "SPY", "QQQ", "IWM",
)
PROFILE_SCHEMA = "yahoo.sector_runtime_profile.v1"
COHORT = "sector_close_14.v1"
SNAPSHOT_SCHEMA = "yahoo.close_cohort.v1"
MIN_SECTOR_HISTORY_SESSIONS = 1000


class YahooRuntimeProfileError(ValueError):
    """A declared ownership profile is not understood."""


class YahooRuntimeOwnershipError(RuntimeError):
    """A legacy writer attempted to modify runtime-owned history."""

    code = "YAHOO_RUNTIME_OWNER"

    def __init__(self) -> None:
        super().__init__(self.code)


class YahooRuntimeBindingError(RuntimeError):
    """The computation lacks a complete, compatible verified selection."""

    code = "YAHOO_RUNTIME_BINDING_REQUIRED"

    def __init__(self, code: str | None = None) -> None:
        self.code = code or type(self).code
        super().__init__(self.code)


@dataclass(frozen=True)
class YahooRuntimeProfile:
    mode: str = "legacy"
    schema: str = PROFILE_SCHEMA
    cohort: str = COHORT
    snapshot_schema: str = SNAPSHOT_SCHEMA
    declared: bool = False

    def __post_init__(self) -> None:
        if (self.mode not in ("legacy", "shadow", "runtime")
                or self.schema != PROFILE_SCHEMA or self.cohort != COHORT
                or self.snapshot_schema != SNAPSHOT_SCHEMA
                or not isinstance(self.declared, bool)):
            raise YahooRuntimeProfileError("Unsupported Sector runtime profile")


@dataclass(frozen=True)
class SymbolPartition:
    allowed: tuple[str, ...]
    excluded: tuple[str, ...]


def parse_profile(yahoo_config: Mapping[str, Any] | None) -> YahooRuntimeProfile:
    """Absent profile preserves pre-transfer compatibility; malformed fails."""
    if yahoo_config is None:
        yahoo_config = {}
    if not isinstance(yahoo_config, Mapping):
        raise YahooRuntimeProfileError("Yahoo configuration must be a mapping")
    if "sector_runtime" not in yahoo_config:
        return YahooRuntimeProfile()
    raw = yahoo_config["sector_runtime"]
    required = {"schema", "mode", "cohort", "snapshot_schema"}
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise YahooRuntimeProfileError("Invalid Sector runtime profile fields")
    if (raw["schema"] != PROFILE_SCHEMA or raw["cohort"] != COHORT
            or raw["snapshot_schema"] != SNAPSHOT_SCHEMA
            or raw["mode"] not in ("legacy", "shadow", "runtime")):
        raise YahooRuntimeProfileError("Unsupported Sector runtime profile")
    return YahooRuntimeProfile(mode=raw["mode"], declared=True)


def cohort_covers(*, group: str, symbol: str) -> bool:
    return (group == "yahoo" and isinstance(symbol, str)
            and symbol.strip().upper() in SECTOR_CLOSE_TICKERS)


def runtime_owns(profile: YahooRuntimeProfile, *, group: str, symbol: str) -> bool:
    return profile.mode == "runtime" and cohort_covers(group=group, symbol=symbol)


def partition_legacy_symbols(
    profile: YahooRuntimeProfile, symbols: Iterable[str]
) -> SymbolPartition:
    """Keep order and spelling; exclusions are not failed provider attempts."""
    if isinstance(symbols, (str, bytes)):
        raise TypeError("Expected a sequence of symbols")
    allowed: list[str] = []
    excluded: list[str] = []
    for symbol in symbols:
        if not isinstance(symbol, str):
            raise TypeError("Symbols must be strings")
        (excluded if (runtime_owns(profile, group="yahoo", symbol=symbol)
                      or bound_snapshot_for(group="yahoo", symbol=symbol) is not None)
         else allowed).append(symbol)
    return SymbolPartition(tuple(allowed), tuple(excluded))


def assert_legacy_write_allowed(
    profile: YahooRuntimeProfile, *, group: str, symbol: str
) -> None:
    if (runtime_owns(profile, group=group, symbol=symbol)
            or bound_snapshot_for(group=group, symbol=symbol) is not None):
        raise YahooRuntimeOwnershipError()


@dataclass(frozen=True)
class VerifiedYahooCohort:
    """Input supplied only after the existing publisher has verified its bytes.

    Frozen metadata does not make a DataFrame immutable. bind_snapshot takes
    private copies; consumers receive detached copies through frame().
    """
    generation_id: str
    source_session: str
    frames: Mapping[str, Any]
    schema: str = SNAPSHOT_SCHEMA
    cohort: str = COHORT


@dataclass(frozen=True)
class YahooSnapshot:
    generation_id: str
    source_session: str
    schema: str
    cohort: str
    _frames: Mapping[str, Any] = field(repr=False, compare=False)

    def frame(self, symbol: str) -> Any:
        key = symbol.strip().upper()
        if key not in self._frames:
            raise YahooRuntimeBindingError("YAHOO_RUNTIME_MEMBER_UNAVAILABLE")
        return self._frames[key].copy(deep=True)


_BOUND_SNAPSHOT: ContextVar[YahooSnapshot | None] = ContextVar(
    "sector_yahoo_verified_snapshot", default=None
)


def bound_snapshot_for(*, group: str, symbol: str) -> YahooSnapshot | None:
    """Observe only this calculation's existing binding, never resolve latest.

    An explicit verified binding may be used for a shadow calculation while
    global ownership remains legacy. It is a read-only scope for the cohort;
    it does not change the global transfer profile.
    """
    return _BOUND_SNAPSHOT.get() if cohort_covers(group=group, symbol=symbol) else None


def capture_sector_history(
    frame: Any, *, source_session: str | None = None,
    minimum_sessions: int = MIN_SECTOR_HISTORY_SESSIONS,
) -> Any:
    """Validate and detach one history; shared by acquisition and verified binding.

    This checks observed history, not provider completeness or publication identity.
    Acquisition supplies the completed target; the publisher-bound facade supplies
    its verified source session. Prior inputs may be shorter and require recovery.
    """
    import numpy as np
    import pandas as pd

    if (type(minimum_sessions) is not int or minimum_sessions < 1
            or not isinstance(frame, pd.DataFrame) or frame.empty
            or not isinstance(frame.index, pd.DatetimeIndex)
            or frame.index.hasnans or frame.index.has_duplicates
            or not frame.index.is_monotonic_increasing
            or frame.index.tz is not None
            or not frame.index.equals(frame.index.normalize())
            or not {"close", "close_price"}.issubset(frame.columns)
            or frame.columns.has_duplicates):
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_FRAME_INVALID")
    if source_session is not None:
        try:
            session = date.fromisoformat(source_session)
        except (TypeError, ValueError) as exc:
            raise YahooRuntimeBindingError("YAHOO_RUNTIME_SESSION_INVALID") from exc
        if session.isoformat() != source_session or frame.index[-1].date() != session:
            raise YahooRuntimeBindingError("YAHOO_RUNTIME_SESSION_INVALID")
    bases = frame[["close", "close_price"]]
    if any(not pd.api.types.is_numeric_dtype(bases[c])
           or pd.api.types.is_bool_dtype(bases[c])
           or pd.api.types.is_complex_dtype(bases[c]) for c in bases):
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_PRICE_BASIS_INVALID")
    try:
        values = bases.to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_PRICE_BASIS_INVALID") from exc
    if not np.isfinite(values).all() or not (values > 0).all():
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_PRICE_BASIS_INVALID")
    # Count actual scheduled US sessions, not arbitrary positive daily rows.
    # Historical years use this owner's existing calendar fallback; admission of
    # the current target separately requires published annual verification.
    from lib import market_session
    try:
        valid_sessions = all(market_session.is_session_date("US", stamp.date())
                             for stamp in frame.index)
    except Exception as exc:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_CALENDAR_UNAVAILABLE") from exc
    if not valid_sessions:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_HISTORY_SESSION_INVALID")
    if len(frame) < minimum_sessions:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_HISTORY_INSUFFICIENT")
    return frame.copy(deep=True)


def _capture(cohort: VerifiedYahooCohort) -> YahooSnapshot:
    if not isinstance(cohort, VerifiedYahooCohort):
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_SNAPSHOT_INVALID")
    try:
        session = date.fromisoformat(cohort.source_session)
    except (TypeError, ValueError) as exc:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_SESSION_INVALID") from exc
    if session.isoformat() != cohort.source_session:
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_SESSION_INVALID")
    if (not isinstance(cohort.generation_id, str) or not cohort.generation_id
            or len(cohort.generation_id) > 192 or cohort.schema != SNAPSHOT_SCHEMA
            or cohort.cohort != COHORT or not isinstance(cohort.frames, Mapping)
            or set(cohort.frames) != set(SECTOR_CLOSE_TICKERS)):
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_SNAPSHOT_INVALID")
    captured = {
        symbol: capture_sector_history(cohort.frames[symbol],
                                       source_session=cohort.source_session)
        for symbol in SECTOR_CLOSE_TICKERS
    }
    return YahooSnapshot(
        cohort.generation_id, cohort.source_session, cohort.schema,
        cohort.cohort, captured,
    )


@contextmanager
def bind_snapshot(
    profile: YahooRuntimeProfile, verified_cohort: VerifiedYahooCohort
) -> Iterator[YahooSnapshot]:
    """Pin one verified generation for the entire synchronous/async context."""
    if profile.mode not in ("shadow", "runtime"):
        raise YahooRuntimeBindingError("YAHOO_RUNTIME_PROFILE_NOT_ACTIVE")
    snapshot = _capture(verified_cohort)
    current = _BOUND_SNAPSHOT.get()
    if current is not None:
        same = (
            current.generation_id == snapshot.generation_id
            and current.source_session == snapshot.source_session
            and current.schema == snapshot.schema
            and current.cohort == snapshot.cohort
            and all(current._frames[s].equals(snapshot._frames[s])
                    for s in SECTOR_CLOSE_TICKERS)
        )
        if not same:
            raise YahooRuntimeBindingError("YAHOO_RUNTIME_BINDING_CONFLICT")
        yield current
        return
    token = _BOUND_SNAPSHOT.set(snapshot)
    try:
        yield snapshot
    finally:
        _BOUND_SNAPSHOT.reset(token)


def require_snapshot(profile: YahooRuntimeProfile) -> YahooSnapshot:
    """Never resolve latest, read a checkout or restart a provider as fallback."""
    snapshot = _BOUND_SNAPSHOT.get()
    if profile.mode not in ("shadow", "runtime") or snapshot is None:
        raise YahooRuntimeBindingError()
    return snapshot
