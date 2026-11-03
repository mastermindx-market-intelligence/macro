"""A4 observation-window calculator (Wave 3 lane W3_X4_observation).

Implements the clock and window arithmetic of the frozen A4 design packet
``designs/A4_transfer_obs/A4_transfer_obs.md`` section 4.7 (``observation_window.v1``:
two modes and the cutoff, the six delayed-entry test arms, measurement windows,
coincident-events ambiguity) and its Appendix C clock worked arithmetic, under
mastermindx-market-intelligence/macro MASTERPLAN.md section 9 (two observation
modes: at-origin uses only data available before the decision; a later landmark
may use data up to the landmark and starts its outcome window afterward) and
the Phase 0 freeze (DEC:NEWS-IMPACT-PHASE0-FREEZE; identity is ``cik:`` + 10
digits passed through untouched, no confidence / probability / score /
price_target / fair_value / sentiment / contagion field anywhere — standing
kills KILL-LLM-CONFIDENCE, DNR:KILL-STALENESS-ALPHA).  The emitted record
validates against the frozen ``observation_window.v1.schema.json``
(contracts_w3, never edited here).

Seat-accepted defaults that bind (design section 7, adopted per W3-R1):
- Q7: the at-origin reference is the LAST COMPLETED bar whose close is at or
  before the cutoff; a bar that closes exactly at the cutoff counts, and the
  decision bar's own close is not a feature for ``at_origin``.
- Q3: the residual factor set is exactly ``{market, documented_peer_residual}``
  (sector / mag7 / gpu_theme are recorded as unused collinear absences).
- Q4: ``next_rth_open_plus_one_session`` is kept and tagged
  ``stale_news_treatment`` — a test arm, never a staleness feature.

Interpretations of the design text, chosen because the worked cases pin them
or because the text names the same stamp twice (recorded in the lane return):
- ``same_session_close_1600_et``: 16:00 America/New_York of the session
  containing T0 when T0 < that 16:00 stamp (case 5.7); otherwise the next
  16:00 America/New_York stamp on a calendar session date strictly after T0
  (calendar-anchored: a Saturday wall-clock 16:00 is not a market landmark).
  On an early-close session the stamp is still 16:00 ET — the policy is named
  for 16:00, and the design text says "16:00 America/New_York" both times.
- ``next_rth_open_plus_one_session``: RTH open of the session after the
  session containing T0; when no session contains T0 (pre-market, overnight,
  weekend, holiday) the anchor is the upcoming session.  For an in-session T0
  this equals ``next_rth_open`` — the two arms are genuinely distinct only for
  an out-of-session T0; that degeneracy is what the design text says.
- matched window: counted in trading sessions of the injected calendar
  (DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS, amendment X4), never in calendar
  days.  The anchor is the session containing the information cutoff
  (inclusive) or the next session when the cutoff is outside regular hours;
  both outcome endpoints shift back by the same whole number of sessions so
  the matched end lands in the k-th session strictly before the anchor
  (``matched_window_sessions_back``, default 1, an int in ``[1, 10]``).
  Each endpoint keeps its ET wall-clock time on the shifted session date
  (a DST change is absorbed); a candidate counts only when both endpoints
  fall inside their shifted sessions and its UTC duration equals the
  outcome's — otherwise the search steps one session further back (early
  closes, holidays, DST spans), raising ``MATCHED_WINDOW_NO_SESSION`` after
  10 candidates.  ``matched_window_end <= information_cutoff`` holds by
  construction; ``MATCHED_WINDOW_AFTER_CUTOFF`` stays as a defensive
  invariant.
- coincident classification follows the ``W_obs_coincident_ambiguous`` fixture
  rule (lane law), which is the acceptance fixture: an event sharing the
  target (or a documented-exposure peer) with ``observed_at`` inside
  ``[first_admissible_feed_receipt, outcome_end]`` is coincident.  The design
  4.7(h) text says ``[information_cutoff, outcome_end]``, which would EXCLUDE
  the fixture's own 13:40Z event (cutoff 13:47:14Z); the fixture wins per
  W3-R1 and the disagreement is recorded in the lane return.
- mode is derived from the policy as in the worked cases: feed_receipt /
  plus_60s / plus_900s are ``at_origin``; next_rth_open /
  same_session_close_1600_et / next_rth_open_plus_one_session are
  ``landmark``.

Determinism: no clock reads, no randomness, no network, no module-level I/O;
the calendar and bars are INJECTED data (never derived here, never read from
``data/``); every emitted stamp is UTC ``YYYY-MM-DDTHH:MM:SSZ`` computed via
stdlib ``zoneinfo`` America/New_York only; iteration over sets/dicts is
sorted; ``observation_id`` is content-derived (sha256 of the canonical
geometry seed), so two runs on permuted input order give byte-identical
canonical JSON.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

__all__ = [
    "OBSERVATION_VERSION",
    "DELAYED_ENTRY_POLICIES",
    "TEST_PURPOSE_FOR_POLICY",
    "MODE_FOR_POLICY",
    "RESIDUAL_FACTOR_SET",
    "UNUSED_COLLINEAR_FACTORS",
    "FORBIDDEN_KEYS",
    "MATCHED_WINDOW_SESSIONS_BACK_DEFAULT",
    "CODES",
    "ObservationError",
    "Bar",
    "Session",
    "TradingCalendar",
    "WindowGeometry",
    "WindowBuild",
    "parse_utc",
    "to_utc_stamp",
    "to_ny_local",
    "canonical_json",
    "strip_forbidden_keys",
    "classify_coincident_events",
    "compute_window_geometry",
    "build_observation_window",
    "validate_record",
]

OBSERVATION_VERSION = "ni-observation-1"

#: The six delayed-entry test arms, design 4.7(f). Order is schema-enum order.
DELAYED_ENTRY_POLICIES: tuple[str, ...] = (
    "feed_receipt",
    "plus_60s",
    "plus_900s",
    "next_rth_open",
    "same_session_close_1600_et",
    "next_rth_open_plus_one_session",
)

TEST_PURPOSE_FOR_POLICY: Mapping[str, str] = {
    "feed_receipt": "none",
    "plus_60s": "source_delay",
    "plus_900s": "research_time",
    "next_rth_open": "gap_open",
    "same_session_close_1600_et": "session_close_landmark",
    "next_rth_open_plus_one_session": "stale_news_treatment",
}

MODE_FOR_POLICY: Mapping[str, str] = {
    "feed_receipt": "at_origin",
    "plus_60s": "at_origin",
    "plus_900s": "at_origin",
    "next_rth_open": "landmark",
    "same_session_close_1600_et": "landmark",
    "next_rth_open_plus_one_session": "landmark",
}

#: Design 4.7(g) / seat default Q3: the only legal residual legs in v1.
RESIDUAL_FACTOR_SET: frozenset[str] = frozenset({"market", "documented_peer_residual"})

#: Design S5 / F16: collinear terms recorded as unused absences, never subtracted.
UNUSED_COLLINEAR_FACTORS: tuple[str, ...] = ("sector", "mag7", "gpu_theme")

#: W3-R3: keys stripped at ingest from every injected structure and recorded
#: in ``WindowBuild.stripped_fields``. Never present in any emitted record.
FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "confidence",
        "probability",
        "score",
        "price_target",
        "fair_value",
        "sentiment",
        "contagion",
    }
)

#: Matched-window sessions back: the matched end lands in the k-th session
#: strictly before the anchor (the cutoff's session); see module docstring.
MATCHED_WINDOW_SESSIONS_BACK_DEFAULT = 1

_NY = ZoneInfo("America/New_York")
_UTC = timezone.utc
_STAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

# --- error handling (W3-R5: closed code strings, one module exception) --------

BAD_TIMESTAMP = "BAD_TIMESTAMP"
BAD_BAR = "BAD_BAR"
BAR_OUT_OF_ORDER = "BAR_OUT_OF_ORDER"
CALENDAR_BAD_SHAPE = "CALENDAR_BAD_SHAPE"
CALENDAR_EMPTY = "CALENDAR_EMPTY"
CALENDAR_BAD_SESSION = "CALENDAR_BAD_SESSION"
UNKNOWN_POLICY = "UNKNOWN_POLICY"
NO_NEXT_SESSION = "NO_NEXT_SESSION"
DECISION_OUTSIDE_SESSION = "DECISION_OUTSIDE_SESSION"
DECISION_BEFORE_CUTOFF = "DECISION_BEFORE_CUTOFF"
WINDOW_USES_FULL_SESSION = "WINDOW_USES_FULL_SESSION"
REFERENCE_BAR_MISSING = "REFERENCE_BAR_MISSING"
MATCHED_WINDOW_AFTER_CUTOFF = "MATCHED_WINDOW_AFTER_CUTOFF"
BAD_MATCHED_WINDOW_SESSIONS = "BAD_MATCHED_WINDOW_SESSIONS"
MATCHED_WINDOW_NO_SESSION = "MATCHED_WINDOW_NO_SESSION"
CUTOFF_VIOLATION = "CUTOFF_VIOLATION"
RESPONSE_WINDOW_MISMATCH = "RESPONSE_WINDOW_MISMATCH"
BAD_RESIDUAL_FIT = "BAD_RESIDUAL_FIT"
FIT_END_AFTER_CUTOFF = "FIT_END_AFTER_CUTOFF"
BAD_PEER_SET = "BAD_PEER_SET"
BAD_COINCIDENT_EVENT = "BAD_COINCIDENT_EVENT"
RECORD_SCHEMA_INVALID = "RECORD_SCHEMA_INVALID"

CODES: frozenset[str] = frozenset(
    {
        BAD_TIMESTAMP,
        BAD_BAR,
        BAR_OUT_OF_ORDER,
        CALENDAR_BAD_SHAPE,
        CALENDAR_EMPTY,
        CALENDAR_BAD_SESSION,
        UNKNOWN_POLICY,
        NO_NEXT_SESSION,
        DECISION_OUTSIDE_SESSION,
        DECISION_BEFORE_CUTOFF,
        WINDOW_USES_FULL_SESSION,
        REFERENCE_BAR_MISSING,
        MATCHED_WINDOW_AFTER_CUTOFF,
        BAD_MATCHED_WINDOW_SESSIONS,
        MATCHED_WINDOW_NO_SESSION,
        CUTOFF_VIOLATION,
        RESPONSE_WINDOW_MISMATCH,
        BAD_RESIDUAL_FIT,
        FIT_END_AFTER_CUTOFF,
        BAD_PEER_SET,
        BAD_COINCIDENT_EVENT,
        RECORD_SCHEMA_INVALID,
    }
)


class ObservationError(Exception):
    """Observation-window fault carrying one closed code from :data:`CODES`."""

    code: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- stamps --------------------------------------------------------------------


def parse_utc(value: str | datetime) -> datetime:
    """Parse a UTC ``...Z`` stamp (or accept a tz-aware datetime) to UTC.

    Naive datetimes and any other shape raise :class:`ObservationError` with
    code ``BAD_TIMESTAMP``: every stamp crossing this module's boundary is
    either an explicit UTC string or an aware datetime.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ObservationError(BAD_TIMESTAMP, f"naive datetime not admitted: {value!r}")
        return value.astimezone(_UTC)
    if isinstance(value, str) and _STAMP_RE.match(value):
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:  # e.g. month 13
            raise ObservationError(BAD_TIMESTAMP, f"unparseable stamp {value!r}: {exc}") from exc
        return parsed.replace(tzinfo=_UTC)
    raise ObservationError(BAD_TIMESTAMP, f"not a UTC ...Z stamp or aware datetime: {value!r}")


def to_utc_stamp(value: str | datetime) -> str:
    """Render a UTC stamp as ``YYYY-MM-DDTHH:MM:SSZ`` (schema ``iso_datetime``)."""
    return parse_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_ny_local(value: str | datetime) -> str:
    """Render a stamp in America/New_York local time (display only)."""
    return parse_utc(value).astimezone(_NY).strftime("%Y-%m-%d %H:%M:%S")


def canonical_json(obj: Any) -> str:
    """Canonical JSON (W3-R2): sorted keys, compact separators, no ascii folding."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _ny_to_utc(day: date, hhmmss: str) -> datetime:
    parts = hhmmss.split(":")
    if len(parts) not in (2, 3) or not all(p.isdigit() and len(p) == 2 for p in parts):
        raise ObservationError(CALENDAR_BAD_SESSION, f"bad session time {hhmmss!r} on {day}")
    hh, mm = int(parts[0]), int(parts[1])
    ss = int(parts[2]) if len(parts) == 3 else 0
    try:
        local = datetime.combine(day, time(hh, mm, ss), tzinfo=_NY)
    except ValueError as exc:
        raise ObservationError(CALENDAR_BAD_SESSION, f"bad session time {hhmmss!r} on {day}: {exc}") from exc
    return local.astimezone(_UTC)


# --- bars ----------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """One injected bar as a UTC half-open interval ``[start_utc, end_utc]``.

    Prices are NOT carried here: returns are measured upstream and injected
    into the record; this module computes window geometry only.
    """

    start_utc: datetime
    end_utc: datetime

    def __post_init__(self) -> None:
        if parse_utc(self.start_utc) >= parse_utc(self.end_utc):
            raise ObservationError(BAD_BAR, f"bar end must be after start: {self}")

    def to_dict(self) -> dict:
        return {"start": to_utc_stamp(self.start_utc), "end": to_utc_stamp(self.end_utc)}


def bars_from_mappings(bars: Iterable[Mapping[str, Any] | Bar] | None) -> tuple[Bar, ...]:
    """Ingest bars as mappings ``{"start": ..., "end": ...}`` or :class:`Bar`.

    Returns bars sorted by ``(end, start)`` (deterministic under input
    permutation); duplicate bars raise ``BAR_OUT_OF_ORDER``.
    """
    if bars is None:
        return ()
    out: list[Bar] = []
    for raw in bars:
        if isinstance(raw, Bar):
            out.append(raw)
            continue
        if not isinstance(raw, Mapping) or "start" not in raw or "end" not in raw:
            raise ObservationError(BAD_BAR, f"bar mapping needs start/end: {raw!r}")
        out.append(Bar(parse_utc(raw["start"]), parse_utc(raw["end"])))
    out.sort(key=lambda b: (b.end_utc, b.start_utc))
    for i in range(1, len(out)):
        if out[i] == out[i - 1]:
            raise ObservationError(BAR_OUT_OF_ORDER, f"duplicate bar {out[i].to_dict()}")
    return tuple(out)


# --- calendar ------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    """One regular-trading-hours session with UTC bounds (early closes included)."""

    date: date
    open_utc: datetime
    close_utc: datetime

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "open": to_utc_stamp(self.open_utc),
            "close": to_utc_stamp(self.close_utc),
        }


@dataclass(frozen=True)
class TradingCalendar:
    """Injected session calendar (design P5/A5): dates with ET open/close times.

    Built from ``{"sessions": {"YYYY-MM-DD": {"open": "HH:MM[:SS]", "close": "HH:MM[:SS]"}}}``.
    Holidays are simply absent dates; early closes are dates whose close is
    earlier than 16:00. Holidays are NEVER derived here.
    """

    sessions: tuple[Session, ...]

    def __post_init__(self) -> None:
        if not self.sessions:
            raise ObservationError(CALENDAR_EMPTY, "calendar has no sessions")
        for i in range(1, len(self.sessions)):
            if self.sessions[i].open_utc <= self.sessions[i - 1].open_utc:
                raise ObservationError(
                    CALENDAR_BAD_SESSION,
                    f"sessions must be unique and sorted by open: {self.sessions[i - 1].to_dict()} then {self.sessions[i].to_dict()}",
                )

    @staticmethod
    def from_mapping(mapping: Mapping[str, Any] | "TradingCalendar") -> "TradingCalendar":
        """Build from the injected dict shape (pass-through for a calendar)."""
        if isinstance(mapping, TradingCalendar):
            return mapping
        if not isinstance(mapping, Mapping) or not isinstance(mapping.get("sessions"), Mapping):
            raise ObservationError(CALENDAR_BAD_SHAPE, f"calendar must be a mapping with a 'sessions' mapping: {mapping!r}")
        sessions: list[Session] = []
        for key in sorted(mapping["sessions"]):
            raw = mapping["sessions"][key]
            if not isinstance(raw, Mapping) or "open" not in raw or "close" not in raw:
                raise ObservationError(CALENDAR_BAD_SESSION, f"session {key!r} needs open/close: {raw!r}")
            try:
                day = date.fromisoformat(key)
            except ValueError as exc:
                raise ObservationError(CALENDAR_BAD_SESSION, f"session date {key!r}: {exc}") from exc
            open_utc = _ny_to_utc(day, str(raw["open"]))
            close_utc = _ny_to_utc(day, str(raw["close"]))
            if open_utc >= close_utc:
                raise ObservationError(
                    CALENDAR_BAD_SESSION,
                    f"session {key!r} open {raw['open']!r} must precede close {raw['close']!r}",
                )
            sessions.append(Session(day, open_utc, close_utc))
        sessions.sort(key=lambda s: (s.open_utc, s.date))
        return TradingCalendar(tuple(sessions))

    def session_containing(self, ts: str | datetime) -> Session | None:
        """The session whose ``[open, close]`` contains ``ts`` (inclusive bounds)."""
        t = parse_utc(ts)
        for s in self.sessions:
            if s.open_utc <= t <= s.close_utc:
                return s
            if s.open_utc > t:
                break
        return None

    def upcoming_session(self, ts: str | datetime) -> Session:
        """First session whose open is strictly after ``ts`` (``next_rth_open`` law)."""
        t = parse_utc(ts)
        for s in self.sessions:
            if s.open_utc > t:
                return s
        raise ObservationError(NO_NEXT_SESSION, f"no session opens strictly after {to_utc_stamp(t)}")

    def session_after(self, session: Session) -> Session:
        """The next session after ``session`` in calendar order."""
        for s in self.sessions:
            if s.open_utc > session.open_utc:
                return s
        raise ObservationError(NO_NEXT_SESSION, f"no session after {session.to_dict()}")

    def landmark_1600et(self, ts: str | datetime) -> datetime:
        """``same_session_close_1600_et`` entry stamp (see module docstring)."""
        t = parse_utc(ts)
        containing = self.session_containing(t)
        if containing is not None:
            stamp = _ny_to_utc(containing.date, "16:00:00")
            if t < stamp:
                return stamp
        for s in self.sessions:
            stamp = _ny_to_utc(s.date, "16:00:00")
            if stamp > t:
                return stamp
        raise ObservationError(NO_NEXT_SESSION, f"no 16:00 ET session stamp after {to_utc_stamp(t)}")


# --- geometry ------------------------------------------------------------------


@dataclass(frozen=True)
class WindowGeometry:
    """The computed window boundaries and reference objects (design 4.7/App C).

    ``at_origin_reference_bar`` is the last completed bar whose close is at or
    before the cutoff (seat default Q7; a bar closing exactly at the cutoff
    counts).  ``first_outcome_bar`` is the first bar whose end is strictly
    after the cutoff — the first return bar (V_CUTOFF).  Neither has a schema
    field (``additionalProperties: false``); they are the leakage-free anchors
    the record's cutoff semantics encode.
    """

    policy: str
    mode: str
    test_purpose: str
    stale_news_treatment: bool
    t0: datetime
    entry_timestamp: datetime
    information_cutoff: datetime
    decision_timestamp: datetime
    outcome_start: datetime
    outcome_end: datetime
    matched_window_start: datetime
    matched_window_end: datetime
    next_rth_open_utc: datetime
    session_date: str | None
    at_origin_reference_bar: Bar | None = None
    first_outcome_bar: Bar | None = None
    residual_factor_ids: tuple[str, ...] = ("documented_peer_residual", "market")
    full_session_return_used: bool = False

    def __post_init__(self) -> None:
        if self.outcome_start < self.information_cutoff:
            raise ObservationError(
                CUTOFF_VIOLATION,
                f"outcome_start {to_utc_stamp(self.outcome_start)} before cutoff {to_utc_stamp(self.information_cutoff)}",
            )
        if self.outcome_end <= self.outcome_start:
            raise ObservationError(
                CUTOFF_VIOLATION,
                f"outcome_end {to_utc_stamp(self.outcome_end)} not after outcome_start {to_utc_stamp(self.outcome_start)}",
            )
        if self.matched_window_end > self.information_cutoff:
            raise ObservationError(
                MATCHED_WINDOW_AFTER_CUTOFF,
                f"matched_window_end {to_utc_stamp(self.matched_window_end)} after cutoff {to_utc_stamp(self.information_cutoff)}",
            )
        if (self.outcome_end - self.outcome_start) != (
            self.matched_window_end - self.matched_window_start
        ):
            raise ObservationError(
                CUTOFF_VIOLATION,
                "matched window duration must equal the outcome window duration",
            )
        if self.full_session_return_used:
            raise ObservationError(
                WINDOW_USES_FULL_SESSION,
                "full_session_return_used is false in v1 (both fixture modes carry false)",
            )

    def to_dict(self) -> dict:
        return {
            "policy": self.policy,
            "mode": self.mode,
            "test_purpose": self.test_purpose,
            "stale_news_treatment": self.stale_news_treatment,
            "first_admissible_feed_receipt": to_utc_stamp(self.t0),
            "entry_timestamp": to_utc_stamp(self.entry_timestamp),
            "information_cutoff": to_utc_stamp(self.information_cutoff),
            "decision_timestamp": to_utc_stamp(self.decision_timestamp),
            "outcome_start": to_utc_stamp(self.outcome_start),
            "outcome_end": to_utc_stamp(self.outcome_end),
            "matched_window_start": to_utc_stamp(self.matched_window_start),
            "matched_window_end": to_utc_stamp(self.matched_window_end),
            "next_rth_open_utc": to_utc_stamp(self.next_rth_open_utc),
            "session_date": self.session_date,
            "at_origin_reference_bar": self.at_origin_reference_bar.to_dict() if self.at_origin_reference_bar else None,
            "first_outcome_bar": self.first_outcome_bar.to_dict() if self.first_outcome_bar else None,
            "residual_factor_ids": list(self.residual_factor_ids),
            "full_session_return_used": self.full_session_return_used,
        }


def _matched_window(
    cal: TradingCalendar,
    cutoff: datetime,
    outcome_start: datetime,
    outcome_end: datetime,
    k: int,
) -> tuple[datetime, datetime]:
    """The matched control window, counted in trading sessions (amendment X4).

    The anchor is the session containing the cutoff (inclusive), or the next
    session when the cutoff is outside regular hours.  Both outcome endpoints
    shift back by the same whole number of sessions so the matched end lands
    in the k-th session strictly before the anchor, each endpoint keeping its
    ET wall-clock time on the shifted session date.  A candidate counts only
    when both endpoints fall inside their shifted sessions and its UTC
    duration equals the outcome's; the search steps one session further back
    (early closes, holidays, DST spans) and raises after 10 candidates.  Pure:
    no clock reads.
    """
    anchor = cal.session_containing(cutoff)
    if anchor is None:
        anchor = cal.upcoming_session(cutoff)
    anchor_idx = cal.sessions.index(anchor)

    def _session_index(ts: datetime) -> int:
        session = cal.session_containing(ts)
        if session is None:
            session = cal.upcoming_session(ts)
        return cal.sessions.index(session)

    i = _session_index(outcome_start)
    j = _session_index(outcome_end)
    n0 = j - (anchor_idx - k)  # >= 1: the matched END sits k sessions before the anchor
    for c in range(10):
        n = n0 + c
        if i - n < 0:
            raise ObservationError(
                MATCHED_WINDOW_NO_SESSION,
                f"no session {n} before the outcome-start session for k={k}",
            )
        s_start = cal.sessions[i - n]
        s_end = cal.sessions[j - n]
        m_start = datetime.combine(s_start.date, outcome_start.astimezone(_NY).time(), tzinfo=_NY).astimezone(_UTC)
        m_end = datetime.combine(s_end.date, outcome_end.astimezone(_NY).time(), tzinfo=_NY).astimezone(_UTC)
        if (
            s_start.open_utc <= m_start <= s_start.close_utc
            and s_end.open_utc <= m_end <= s_end.close_utc
            and (m_end - m_start) == (outcome_end - outcome_start)
        ):
            return m_start, m_end
    raise ObservationError(
        MATCHED_WINDOW_NO_SESSION,
        f"no admissible matched window within 10 sessions before the anchor for k={k}",
    )


def compute_window_geometry(
    t0: str | datetime,
    policy: str,
    calendar: Mapping[str, Any] | TradingCalendar,
    bars: Iterable[Mapping[str, Any] | Bar] | None = None,
    decision_timestamp: str | datetime | None = None,
    matched_window_sessions_back: int = MATCHED_WINDOW_SESSIONS_BACK_DEFAULT,
) -> WindowGeometry:
    """Compute the window geometry for one delayed-entry policy (pure).

    ``t0`` is ``first_admissible_feed_receipt``; ``decision_timestamp`` is the
    at-origin decision stamp (defaults to the entry stamp, as in case 5.5) and
    is ignored for landmark policies, whose decision IS the landmark entry.
    """
    if (
        isinstance(matched_window_sessions_back, bool)
        or not isinstance(matched_window_sessions_back, int)
        or not 1 <= matched_window_sessions_back <= 10
    ):
        raise ObservationError(
            BAD_MATCHED_WINDOW_SESSIONS,
            f"matched_window_sessions_back must be an int in [1, 10], not {matched_window_sessions_back!r}",
        )
    if policy not in TEST_PURPOSE_FOR_POLICY:
        raise ObservationError(UNKNOWN_POLICY, f"policy not in {list(DELAYED_ENTRY_POLICIES)}: {policy!r}")
    t0_dt = parse_utc(t0)
    cal = TradingCalendar.from_mapping(calendar)
    bar_tuple = bars_from_mappings(bars)

    if policy == "feed_receipt":
        entry = t0_dt
    elif policy == "plus_60s":
        entry = t0_dt + timedelta(seconds=60)
    elif policy == "plus_900s":
        entry = t0_dt + timedelta(seconds=900)
    elif policy == "next_rth_open":
        entry = cal.upcoming_session(t0_dt).open_utc
    elif policy == "same_session_close_1600_et":
        entry = cal.landmark_1600et(t0_dt)
    else:  # next_rth_open_plus_one_session
        anchor = cal.session_containing(t0_dt)
        if anchor is None:
            anchor = cal.upcoming_session(t0_dt)
        entry = cal.session_after(anchor).open_utc

    next_rth_open = cal.upcoming_session(t0_dt).open_utc
    mode = MODE_FOR_POLICY[policy]
    stale_arm = policy == "next_rth_open_plus_one_session"

    reference_bar: Bar | None = None
    first_outcome_bar: Bar | None = None
    for bar in bar_tuple:  # sorted by end; first end > cutoff is the first outcome bar
        if bar.end_utc > entry:
            first_outcome_bar = bar
            break

    if mode == "at_origin":
        cutoff = entry
        decision = parse_utc(decision_timestamp) if decision_timestamp is not None else entry
        if decision < cutoff:
            raise ObservationError(
                DECISION_BEFORE_CUTOFF,
                f"decision {to_utc_stamp(decision)} before cutoff {to_utc_stamp(cutoff)}",
            )
        session = cal.session_containing(decision)
        if session is None:
            raise ObservationError(
                DECISION_OUTSIDE_SESSION,
                f"at_origin decision {to_utc_stamp(decision)} is not inside an RTH session",
            )
        if decision == session.open_utc and session.open_utc > cutoff:
            # V_NO_FULL_DAY: an open-to-close window straddling the cutoff as a
            # 09:35-style decision's outcome (S7).
            raise ObservationError(
                WINDOW_USES_FULL_SESSION,
                f"at_origin window would start at the session open {to_utc_stamp(session.open_utc)}",
            )
        outcome_start = decision
        outcome_end = session.close_utc
        candidates = [b for b in bar_tuple if b.end_utc <= cutoff]
        if not candidates:
            raise ObservationError(
                REFERENCE_BAR_MISSING,
                f"no completed bar with end <= cutoff {to_utc_stamp(cutoff)}",
            )
        last_end = candidates[-1].end_utc
        refs = [b for b in candidates if b.end_utc == last_end]
        if len(refs) > 1:
            raise ObservationError(
                BAR_OUT_OF_ORDER,
                f"ambiguous at-origin reference bar at end {to_utc_stamp(last_end)}",
            )
        reference_bar = refs[0]
        session_date = session.date.isoformat()
    else:
        cutoff = entry
        decision = entry
        session = cal.session_containing(cutoff)
        if session is not None and cutoff == session.close_utc:
            nxt = cal.session_after(session)
            outcome_start = nxt.open_utc
            outcome_end = nxt.close_utc
        else:
            later = [b for b in bar_tuple if b.end_utc > cutoff]
            if later:
                outcome_start = later[0].end_utc
                if session is not None:
                    outcome_end = session.close_utc
                else:
                    # X4: when the cutoff sits outside regular hours (e.g. 16:00 ET
                    # on an early-close day) the outcome ends at the close of the
                    # session CONTAINING outcome_start, not the session after it.
                    containing = cal.session_containing(outcome_start)
                    if containing is not None:
                        outcome_end = containing.close_utc
                    else:
                        outcome_end = cal.upcoming_session(outcome_start).close_utc
            else:
                nxt = cal.upcoming_session(cutoff)
                outcome_start = nxt.open_utc
                outcome_end = nxt.close_utc
        session_date = session.date.isoformat() if session is not None else None

    matched_start, matched_end = _matched_window(
        cal, cutoff, outcome_start, outcome_end, matched_window_sessions_back
    )

    return WindowGeometry(
        policy=policy,
        mode=mode,
        test_purpose=TEST_PURPOSE_FOR_POLICY[policy],
        stale_news_treatment=stale_arm,
        t0=t0_dt,
        entry_timestamp=entry,
        information_cutoff=cutoff,
        decision_timestamp=decision,
        outcome_start=outcome_start,
        outcome_end=outcome_end,
        matched_window_start=matched_start,
        matched_window_end=matched_end,
        next_rth_open_utc=next_rth_open,
        session_date=session_date,
        at_origin_reference_bar=reference_bar,
        first_outcome_bar=first_outcome_bar,
    )


# --- ingest helpers (W3-R3 strip-and-record) ------------------------------------


def strip_forbidden_keys(value: Any, path: str = "") -> tuple[Any, list[str]]:
    """Recursively drop :data:`FORBIDDEN_KEYS` from an injected structure.

    Returns ``(clean, stripped)`` where ``stripped`` lists ``path.key`` for
    every removed key (sorted by the caller).  Forbidden keys never pass
    through to any emitted record (the schema's ``additionalProperties:false``
    would reject them anyway; stripping at ingest is the recorded law).
    """
    stripped: list[str] = []
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key in sorted(value):
            child = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_KEYS:
                stripped.append(child)
                continue
            clean[key], sub = strip_forbidden_keys(value[key], child)
            stripped.extend(sub)
        return clean, stripped
    if isinstance(value, (list, tuple)):
        items: list[Any] = []
        for i, item in enumerate(value):
            cleaned, sub = strip_forbidden_keys(item, f"{path}[{i}]")
            items.append(cleaned)
            stripped.extend(sub)
        return items, stripped
    return value, stripped


def _absence(subject: str, detail: str, reason: str = "not_stated") -> dict:
    """A ``field_absence.v1`` payload (freeze D13/D14 shape)."""
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": detail,
        "missing_fields": [],
    }


def classify_coincident_events(
    events: Iterable[Mapping[str, Any]],
    target_company_id: str,
    peer_member_ids: Iterable[str] = (),
    t0: str | datetime | None = None,
    outcome_end: str | datetime | None = None,
) -> tuple[dict, ...]:
    """Apply the ``W_obs_coincident_ambiguous`` fixture rule (frozen by lane law).

    An event is coincident when its ``company_id`` is the target or a peer-set
    member and its ``observed_at`` falls in ``[t0, outcome_end]`` (inclusive).
    The design 4.7(h) text would start that interval at the cutoff and so
    exclude the fixture's own 13:40Z event; the fixture wins (W3-R1).  Returns
    pass-through mappings sorted by ``(observed_at, fact_id)`` with forbidden
    keys stripped.
    """
    allowed = {target_company_id, *set(peer_member_ids)}
    t0_dt = parse_utc(t0) if t0 is not None else None
    end_dt = parse_utc(outcome_end) if outcome_end is not None else None
    kept: list[tuple[str, dict]] = []
    for raw in events:
        if not isinstance(raw, Mapping):
            raise ObservationError(BAD_COINCIDENT_EVENT, f"event must be a mapping: {raw!r}")
        for key in ("fact_id", "company_id", "observed_at"):
            if key not in raw:
                raise ObservationError(BAD_COINCIDENT_EVENT, f"event missing {key!r}: {raw!r}")
        cleaned, _ = strip_forbidden_keys(raw, "coincident_events")
        when = parse_utc(raw["observed_at"])
        if raw["company_id"] not in allowed:
            continue
        if t0_dt is not None and when < t0_dt:
            continue
        if end_dt is not None and when > end_dt:
            continue
        kept.append((to_utc_stamp(when), cleaned))
    kept.sort(key=lambda pair: (pair[0], pair[1].get("fact_id", "")))
    return tuple(dict(item) for _, item in kept)


# --- record assembly ------------------------------------------------------------


@dataclass(frozen=True)
class WindowBuild:
    """The emitted record plus its ingest report (stripped keys, geometry)."""

    record: dict
    geometry: WindowGeometry
    stripped_fields: tuple[str, ...] = ()
    observation_version: str = OBSERVATION_VERSION

    @property
    def canonical_json(self) -> str:
        return canonical_json(self.record)

    def to_dict(self) -> dict:
        return {
            "record": self.record,
            "geometry": self.geometry.to_dict(),
            "stripped_fields": list(self.stripped_fields),
            "observation_version": self.observation_version,
        }


def _checked_response(
    response: Mapping[str, Any] | None,
    subject: str,
    geometry: WindowGeometry,
    stripped: list[str],
) -> dict:
    """Ingest one response: default absence, strip, and window-leak guard."""
    if response is None:
        return {"form": "unmeasured", "absence": _absence(subject, f"no measured {subject} injected")}
    cleaned, sub = strip_forbidden_keys(response, subject)
    stripped.extend(sub)
    if cleaned.get("form") == "measured":
        for key, expected in (
            ("window_start", to_utc_stamp(geometry.outcome_start)),
            ("window_end", to_utc_stamp(geometry.outcome_end)),
        ):
            if key in cleaned and to_utc_stamp(cleaned[key]) != expected:
                raise ObservationError(
                    RESPONSE_WINDOW_MISMATCH,
                    f"{subject}.{key} {cleaned[key]!r} != computed {expected!r}",
                )
    return cleaned


def _checked_residual_fit(
    fit: Mapping[str, Any] | None, geometry: WindowGeometry, stripped: list[str]
) -> dict:
    """Ingest the residual fit: default absence, closed checks, V_FIT_CUTOFF."""
    if fit is None:
        return _absence(
            "residual_fit",
            "coefficients are fitted upstream (ols_trailing_pre_cutoff) and injected; none supplied",
        )
    cleaned, sub = strip_forbidden_keys(fit, "residual_fit")
    stripped.extend(sub)
    if cleaned.get("method") != "ols_trailing_pre_cutoff":
        raise ObservationError(
            BAD_RESIDUAL_FIT, f"residual_fit.method must be 'ols_trailing_pre_cutoff': {cleaned.get('method')!r}"
        )
    legs = cleaned.get("legs")
    if not isinstance(legs, list) or not legs:
        raise ObservationError(BAD_RESIDUAL_FIT, "residual_fit.legs must be a non-empty list")
    for leg in legs:
        if leg.get("factor_id") not in RESIDUAL_FACTOR_SET:
            raise ObservationError(
                BAD_RESIDUAL_FIT,
                f"residual_fit leg factor_id {leg.get('factor_id')!r} outside {sorted(RESIDUAL_FACTOR_SET)}",
            )
        bars_n = leg.get("window_bars")
        if not isinstance(bars_n, int) or not 2 <= bars_n <= 2520:
            raise ObservationError(BAD_RESIDUAL_FIT, f"residual_fit leg window_bars out of 2..2520: {bars_n!r}")
    fit_start = cleaned.get("fit_start")
    fit_end = cleaned.get("fit_end")
    if fit_start is None or fit_end is None:
        raise ObservationError(BAD_RESIDUAL_FIT, "residual_fit needs fit_start and fit_end")
    if parse_utc(fit_end) < parse_utc(fit_start):
        raise ObservationError(BAD_RESIDUAL_FIT, "residual_fit fit_end before fit_start")
    if parse_utc(fit_end) > geometry.information_cutoff:
        raise ObservationError(
            FIT_END_AFTER_CUTOFF,
            f"fit_end {to_utc_stamp(fit_end)} after cutoff {to_utc_stamp(geometry.information_cutoff)} (V_FIT_CUTOFF)",
        )
    if "unused_collinear_factors" not in cleaned:
        cleaned["unused_collinear_factors"] = [
            {
                "factor_id": factor,
                "absence": _absence(
                    f"residual_fit.{factor}",
                    "collinear with market plus documented-peer residual; not subtracted",
                ),
            }
            for factor in UNUSED_COLLINEAR_FACTORS
        ]
    return cleaned


def _checked_peer_set(
    peer_set: Mapping[str, Any] | None, target_company_id: str, stripped: list[str]
) -> dict:
    """Ingest the peer set: default absence or the documented-exposure checks (4.6)."""
    if peer_set is None:
        return _absence(
            "peer_set",
            "no documented-exposure peer set injected; selector would be illegal (V_PEER_SELECTOR)",
        )
    cleaned, sub = strip_forbidden_keys(peer_set, "peer_set")
    stripped.extend(sub)
    if cleaned.get("selection") != "documented_exposure":
        raise ObservationError(
            BAD_PEER_SET, f"peer_set.selection must be 'documented_exposure': {cleaned.get('selection')!r}"
        )
    members = cleaned.get("member_ids")
    if not isinstance(members, list) or not members:
        raise ObservationError(BAD_PEER_SET, "peer_set.member_ids must be a non-empty list")
    if len(set(members)) != len(members):
        raise ObservationError(BAD_PEER_SET, "peer_set.member_ids must be unique")
    if target_company_id in members:
        raise ObservationError(BAD_PEER_SET, "peer_set.member_ids must not contain the target (target_excluded)")
    if cleaned.get("excluded_target_id") != target_company_id:
        raise ObservationError(
            BAD_PEER_SET,
            f"peer_set.excluded_target_id {cleaned.get('excluded_target_id')!r} != target {target_company_id!r}",
        )
    return cleaned


def _default_display_summary(geometry: WindowGeometry, target_company_id: str) -> str:
    """Deterministic window-only display text (S17: no certainty verbs)."""
    if geometry.mode == "at_origin":
        return (
            f"From {to_ny_local(geometry.outcome_start)} to {to_ny_local(geometry.outcome_end)} "
            f"America/New_York, after policy {geometry.policy} from first feed receipt at "
            f"{to_ny_local(geometry.t0)}, the window return for {target_company_id} is recorded "
            f"over that window. The full-session move is not used."
        )
    return (
        f"At the {to_ny_local(geometry.entry_timestamp)} America/New_York landmark, data up to that "
        f"stamp may be used. The outcome window for {target_company_id} runs "
        f"{to_ny_local(geometry.outcome_start)} to {to_ny_local(geometry.outcome_end)} America/New_York."
    )


def build_observation_window(
    *,
    source_fact_id: str,
    target_company_id: str,
    first_admissible_feed_receipt: str | datetime,
    policy: str,
    calendar: Mapping[str, Any] | TradingCalendar,
    observed_at: str | datetime,
    bars: Iterable[Mapping[str, Any] | Bar] | None = None,
    decision_timestamp: str | datetime | None = None,
    absolute_response: Mapping[str, Any] | None = None,
    residual_response: Mapping[str, Any] | None = None,
    residual_fit: Mapping[str, Any] | None = None,
    peer_set: Mapping[str, Any] | None = None,
    coincident_events: Iterable[Mapping[str, Any]] = (),
    source_available_at: str | datetime | None = None,
    display_summary: str | None = None,
    matched_window_sessions_back: int = MATCHED_WINDOW_SESSIONS_BACK_DEFAULT,
) -> WindowBuild:
    """Compute the geometry and assemble one ``observation_window.v1`` record.

    All market data (calendar, bars, measured responses, fitted coefficients,
    peer set, coincident facts) is INJECTED (W3-R4); this function computes
    the clock arithmetic, applies the closed checks, strips forbidden keys at
    ingest (recorded in ``WindowBuild.stripped_fields``), derives
    ``attribution_state``, and mints a content-derived ``observation_id``.
    """
    geometry = compute_window_geometry(
        first_admissible_feed_receipt,
        policy,
        calendar,
        bars=bars,
        decision_timestamp=decision_timestamp,
        matched_window_sessions_back=matched_window_sessions_back,
    )
    stripped: list[str] = []

    absolute = _checked_response(absolute_response, "absolute_response", geometry, stripped)
    residual = _checked_response(residual_response, "residual_response", geometry, stripped)
    fit = _checked_residual_fit(residual_fit, geometry, stripped)
    peers = _checked_peer_set(peer_set, target_company_id, stripped)
    peer_members = peers.get("member_ids", [])

    cleaned_events: list[dict] = []
    for raw in coincident_events:
        if not isinstance(raw, Mapping):
            raise ObservationError(BAD_COINCIDENT_EVENT, f"event must be a mapping: {raw!r}")
        cleaned, sub = strip_forbidden_keys(raw, "coincident_events")
        stripped.extend(sub)
        cleaned_events.append(cleaned)
    coincident = classify_coincident_events(
        cleaned_events,
        target_company_id,
        peer_member_ids=peer_members,
        t0=geometry.t0,
        outcome_end=geometry.outcome_end,
    )

    if coincident:
        attribution = "ambiguous_coincident"
    elif absolute.get("form") == "measured" and residual.get("form") == "measured":
        attribution = "unambiguous_single_event"
    else:
        attribution = "unmeasured"

    seed = canonical_json(
        {
            "source_fact_id": source_fact_id,
            "target_company_id": target_company_id,
            "policy": geometry.policy,
            "t0": to_utc_stamp(geometry.t0),
            "entry_timestamp": to_utc_stamp(geometry.entry_timestamp),
            "decision_timestamp": to_utc_stamp(geometry.decision_timestamp),
            "outcome_start": to_utc_stamp(geometry.outcome_start),
            "outcome_end": to_utc_stamp(geometry.outcome_end),
            "matched_window_start": to_utc_stamp(geometry.matched_window_start),
            "matched_window_end": to_utc_stamp(geometry.matched_window_end),
            "coincident_fact_ids": sorted(str(e["fact_id"]) for e in coincident),
        }
    )
    observation_id = "obs_" + sha256(seed.encode("utf-8")).hexdigest()[:24]

    record = {
        "schema": "observation_window.v1",
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "unsolicited_instruction_detected": False,
        "observation_id": observation_id,
        "mode": geometry.mode,
        "source_fact_id": source_fact_id,
        "target_company_id": target_company_id,
        "first_admissible_feed_receipt": to_utc_stamp(geometry.t0),
        "delayed_entry_policy": geometry.policy,
        "test_purpose": geometry.test_purpose,
        "entry_timestamp": to_utc_stamp(geometry.entry_timestamp),
        "information_cutoff": to_utc_stamp(geometry.information_cutoff),
        "decision_timestamp": to_utc_stamp(geometry.decision_timestamp),
        "outcome_start": to_utc_stamp(geometry.outcome_start),
        "outcome_end": to_utc_stamp(geometry.outcome_end),
        "matched_window_start": to_utc_stamp(geometry.matched_window_start),
        "matched_window_end": to_utc_stamp(geometry.matched_window_end),
        "full_session_return_used": False,
        "absolute_response": absolute,
        "residual_response": residual,
        "residual_fit": fit,
        "peer_set": peers,
        "coincident_events": [dict(e) for e in coincident],
        "attribution_state": attribution,
        "observed_at": to_utc_stamp(observed_at),
        "source_available_at": to_utc_stamp(source_available_at if source_available_at is not None else geometry.t0),
        "display_summary": display_summary if display_summary is not None else _default_display_summary(geometry, target_company_id),
    }
    return WindowBuild(record=record, geometry=geometry, stripped_fields=tuple(sorted(stripped)))


def validate_record(
    record: Mapping[str, Any],
    schema_path: str | None = None,
) -> None:
    """Validate a record against the frozen ``observation_window.v1`` schema.

    The schema is read lazily (no module-level I/O); the default path resolves
    through the lane overlay's ``contracts`` link to the frozen contracts_w3
    file.  Raises :class:`ObservationError` with code ``RECORD_SCHEMA_INVALID``
    on the first validation failure message set (deterministically sorted).
    """
    from jsonschema import Draft202012Validator  # lazy: geometry stays dependency-free

    path = schema_path or str(
        Path(__file__).resolve().parents[2] / "contracts" / "news_impact" / "observation_window.v1.schema.json"
    )
    with open(path, "r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda e: [str(p) for p in e.absolute_path])
    if errors:
        messages = "; ".join(
            f"{('/'.join(str(p) for p in e.absolute_path) or '<root>')}: {e.message}" for e in errors[:5]
        )
        raise ObservationError(RECORD_SCHEMA_INVALID, messages)
