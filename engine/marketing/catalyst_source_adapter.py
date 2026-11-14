"""Reader half of the Catalyst SEC source cycle (A3-R).

Turns the writer's published ``marketing.catalyst_sec_cycle_index/v1`` snapshot
into the five read callables ``catalyst_admission.read_qualified_event_context``
consumes.  Fail closed everywhere: no stored SEC document bytes are ever
re-read or persisted (D4) — every observation is built from the index record
alone; every identity claim is re-checked against the pilot universe (F4); the
snapshot must be structurally sound and younger than ten minutes; and a missing
or broken store yields an empty state that is cached for the TTL so a down
store is not hammered per request.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Sequence

from engine.marketing.catalyst_admission import AdmittedEdgarSource
from engine.marketing.catalyst_packets import (
    FIGURE_OUTCOMES,
    PublicSourceGrant,
    VerifiedDocumentObservation,
    VerifiedEarningsFigure,
)
from engine.marketing.catalyst_scan import SourceCoverageReceipt
from engine.marketing.catalyst_source_store import INDEX_SCHEMA

OBSERVATION_OWNER_REF = "marketing.catalyst_source_cycle"
COVERAGE_OWNER_REF = "marketing.catalyst_source_adapter"
GRANT_OWNER_REF = (
    "marketing.catalyst_source_adapter@SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS-20261101"
)
CACHE_TTL_SECONDS = 60
MAX_SNAPSHOT_AGE = timedelta(minutes=10)
EVENT_LIMIT = 20
GRANT_MAX_LIFETIME = timedelta(days=7)
GRANT_MAX_AHEAD = timedelta(hours=24)

# Default universe the lazy path loads (writer-owned file, writer loader).
UNIVERSE_PATH = "config/catalyst_pilot_universe.json"
_WINDOW = timedelta(days=7)

_SOURCE_URL_RE = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/([A-Za-z0-9._-]+)$")
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_INDEX_PAGE_SUFFIXES = ("-index.htm", "-index.html", "-index-headers.html")
_FILING_KEY_RE = re.compile(r"^\d{10}:\d{10}-\d{2}-\d{6}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_CLOCK_FMT = "%Y-%m-%dT%H:%M:%SZ"
_FIGURE_KEYS = frozenset(
    {("eps_actual", "gaap"), ("eps_actual", "adjusted"), ("rev_actual", "reported")})
_MAX_FIGURES = 24


def _parse_clock(value: object) -> datetime | None:
    """Strict 'YYYY-MM-DDTHH:MM:SSZ' -> aware UTC, else None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, _CLOCK_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _events_in(state: object, start: datetime, end: datetime) -> list:
    """Served events with acceptance in [start, min(end, t_start)], newest first."""
    upper = min(end, state.t_start)
    return [event for accepted, event in state.events if start <= accepted <= upper]


def _f4_identity_ok(record: Mapping, universe_row: object) -> bool:
    """F4: a public grant may only cite an issuer's own EX-99.1 8-K exhibit.

    (a) the exhibit type is exactly ``EX-99.1`` as taken from the parsed filing
    index Type column (never inferred from a file name); (b) the archive URL is
    a canonical sec.gov Archives path whose CIK directory is the universe CIK
    for this TICKER and whose accession directory matches the accession without
    dashes; (c) the form is an 8-K / 8-K/A carrying Item 2.02.
    """
    if not isinstance(record, Mapping):
        return False
    exhibit = record.get("exhibit")
    if not isinstance(exhibit, Mapping) or exhibit.get("exhibit_type") != "EX-99.1":
        return False
    accession = record.get("accession")
    if not isinstance(accession, str) or not _ACCESSION_RE.match(accession):
        return False
    url = exhibit.get("source_url")
    match = _SOURCE_URL_RE.match(url) if isinstance(url, str) else None
    if match is None:
        return False
    cik = getattr(universe_row, "cik", None)
    if isinstance(cik, bool) or not isinstance(cik, int) or cik <= 0:
        return False
    if match.group(1) != str(cik) or match.group(2) != accession.replace("-", ""):
        return False
    filename = match.group(3)
    if (filename.startswith(".") or filename.lower().endswith(_INDEX_PAGE_SUFFIXES)
            or filename == accession + ".txt"):
        # Dot paths, the filing index pages and the full submission text
        # are never the issuer's EX-99.1 document.
        return False
    if record.get("form") not in ("8-K", "8-K/A"):
        return False
    items = record.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return False
    return "2.02" in items


def _record_ok(record: object, issuer: Mapping, universe_row: object,
               window_start: datetime, t_start: datetime, t_complete: datetime,
               filing_key_counts: Mapping[str, int]) -> bool:
    """R2 validation of one index event record; any failure fails its issuer."""
    if not isinstance(record, Mapping):
        return False
    ticker, cik = record.get("ticker"), record.get("cik")
    if ticker != issuer.get("ticker") or cik != issuer.get("cik"):
        return False
    if isinstance(cik, bool) or not isinstance(cik, int) or cik <= 0:
        return False
    accession = record.get("accession")
    if not isinstance(accession, str) or not _ACCESSION_RE.match(accession):
        return False
    filing_key = record.get("filing_key")
    if not isinstance(filing_key, str) or filing_key != "%010d:%s" % (cik, accession):
        return False
    if filing_key_counts.get(filing_key, 0) != 1:
        return False
    if not _f4_identity_ok(record, universe_row):
        return False
    exhibit = record.get("exhibit")
    document_sha256 = exhibit.get("document_sha256")
    if not isinstance(document_sha256, str) or not _HEX64_RE.match(document_sha256):
        return False
    retention = record.get("retention")
    if not isinstance(retention, Mapping):
        return False
    receipt_id = retention.get("first_retained_receipt_id")
    if (not isinstance(receipt_id, str)
            or not 1 <= len(receipt_id) <= 128):
        return False
    accepted = _parse_clock(record.get("acceptance_datetime"))
    first = _parse_clock(retention.get("first_retained_at"))
    last = _parse_clock(retention.get("last_verified_at"))
    if accepted is None or first is None or last is None:
        return False
    if not window_start <= accepted <= t_start:
        return False
    if not accepted <= first <= last:
        return False
    if not t_start <= last <= t_complete:
        return False
    figures = record.get("figures")
    if not isinstance(figures, list) or len(figures) > _MAX_FIGURES:
        return False
    for figure in figures:
        if not isinstance(figure, Mapping):
            return False
        if (figure.get("field"), figure.get("basis")) not in _FIGURE_KEYS:
            return False
        if _finite_number(figure.get("value")) is None:
            return False
        span = figure.get("span_sha256")
        if not isinstance(span, str) or not _HEX64_RE.match(span):
            return False
    if figures and record.get("parse_status") != "parsed":
        return False
    lineage = record.get("lineage")
    if not isinstance(lineage, Mapping):
        return False
    amends = lineage.get("amends_filing_key")
    generation = lineage.get("correction_generation")
    if isinstance(generation, bool) or not isinstance(generation, int):
        return False
    form = record.get("form")
    if form == "8-K":
        if amends != "" or generation != 0:
            return False
    elif form == "8-K/A":
        if (not isinstance(amends, str) or not _FILING_KEY_RE.match(amends)
                or not amends.startswith("%010d:" % cik)
                or amends == filing_key or generation != 1):
            return False
    else:
        return False
    return True


def _unique_figure(figures: Sequence[Mapping], field: str, basis: str):
    """The UNIQUE (field, basis) figure's value, else None."""
    matches = [figure for figure in figures
               if figure.get("field") == field and figure.get("basis") == basis]
    if len(matches) != 1:
        return None
    return _finite_number(matches[0].get("value"))


def _event_dict(record: Mapping) -> dict:
    """The edgar_earnings_wire.build_event shape, replayed from the record."""
    figures = [figure for figure in (record.get("figures") or [])
               if isinstance(figure, Mapping)]
    eps_actual = _unique_figure(figures, "eps_actual", "gaap")
    eps_basis = "gaap" if eps_actual is not None else None
    if eps_actual is None:
        eps_actual = _unique_figure(figures, "eps_actual", "adjusted")
        eps_basis = "adjusted" if eps_actual is not None else None
    rev_actual = _unique_figure(figures, "rev_actual", "reported")
    if record.get("form") == "8-K/A":
        revision_status, generation, supersedes, reason = (
            "corrected", 1, 0, "official_amendment")
    else:
        revision_status, generation, supersedes, reason = "active", 0, None, None
    retention = record.get("retention") or {}
    first = _parse_clock(retention.get("first_retained_at"))
    when = first.strftime("%Y-%m-%dT%H:%M:%S") if first is not None else ""
    return {
        "id": "%s-%s" % (record.get("ticker"), record.get("accession")),
        "ticker": record.get("ticker"),
        "when": when,
        "when_semantics": "processing_wall_clock",
        "eps_actual": eps_actual,
        "eps_est": None,
        "rev_actual": rev_actual,
        "rev_est": None,
        "quarter": None,
        "source": "edgar_8k_202",
        "cik": record.get("cik"),
        "accession": record.get("accession"),
        "filing_key": record.get("filing_key"),
        "form": record.get("form"),
        "filing_date": record.get("filing_date") or "",
        "acceptance_datetime": record.get("acceptance_datetime"),
        "acceptance_datetime_source": "sec_submissions.acceptanceDateTime",
        "source_url": (record.get("exhibit") or {}).get("source_url"),
        "_session": None,
        "_revenue_label": None,
        "_eps_label": None,
        "_eps_basis": eps_basis,
        "_eps_gaap": eps_actual if eps_basis == "gaap" else None,
        "revision_status": revision_status,
        "correction_generation": generation,
        "supersedes_generation": supersedes,
        "correction_reason": reason,
    }


class _Snapshot:
    """Immutable derived view of one loaded index (or an empty fail-closed view)."""

    __slots__ = ("empty", "snapshot_id", "t_start", "t_complete", "window_start",
                 "rows", "events", "records", "sources", "ok_tickers",
                 "in_window_count", "index_truncated", "index_outcome")

    def __init__(self, *, empty: bool = True, snapshot_id: str = "",
                 t_start: datetime | None = None,
                 t_complete: datetime | None = None,
                 window_start: datetime | None = None,
                 rows: Mapping[str, dict] | None = None,
                 events: Sequence[tuple[datetime, dict]] = (),
                 records: Mapping | None = None,
                 sources: Mapping | None = None,
                 ok_tickers: frozenset[str] = frozenset(),
                 in_window_count: int = 0,
                 index_truncated: object = None,
                 index_outcome: object = None):
        self.empty = empty
        self.snapshot_id = snapshot_id
        self.t_start = t_start
        self.t_complete = t_complete
        self.window_start = window_start
        self.rows = dict(rows or {})
        self.events = tuple(events)
        self.records = dict(records or {})
        self.sources = dict(sources or {})
        self.ok_tickers = ok_tickers
        self.in_window_count = in_window_count
        self.index_truncated = index_truncated
        self.index_outcome = index_outcome

    def fresh(self, now: datetime) -> bool:
        """Freshness evaluated on EVERY call, against that call's `now`."""
        if self.empty or self.t_start is None or self.t_complete is None:
            return False
        if self.t_start > now or self.t_complete > now:
            return False
        if (now - self.t_complete) > MAX_SNAPSHOT_AGE:
            return False
        if (now - self.t_start) > MAX_SNAPSHOT_AGE:
            return False
        return True


_EMPTY_SNAPSHOT = _Snapshot()


def _build_snapshot(latest: object, universe_rows: Sequence) -> _Snapshot:
    """Derive a read view from a LatestIndex; never raises, never does I/O."""
    if latest is None:
        return _EMPTY_SNAPSHOT
    try:
        index = getattr(latest, "index", None)
        if not isinstance(index, Mapping) or index.get("schema") != INDEX_SCHEMA:
            return _EMPTY_SNAPSHOT
        t_start = _parse_clock(index.get("cycle_started_at"))
        t_complete = _parse_clock(index.get("cycle_completed_at"))
        window_start = _parse_clock(index.get("window_start"))
        window_end = _parse_clock(index.get("window_end"))
        if t_start is None or t_complete is None:
            return _EMPTY_SNAPSHOT
        if window_start is None or window_end is None:
            return _EMPTY_SNAPSHOT
        if window_end != t_start or window_start != t_start - _WINDOW:
            return _EMPTY_SNAPSHOT

        raw_events = index.get("events")
        if not isinstance(raw_events, list):
            raw_events = []
        filing_key_counts: dict[str, int] = {}
        for event in raw_events:
            key = event.get("filing_key") if isinstance(event, Mapping) else None
            if isinstance(key, str):
                filing_key_counts[key] = filing_key_counts.get(key, 0) + 1
        buckets: dict[tuple[object, object], list] = {}
        for event in raw_events:
            if not isinstance(event, Mapping):
                continue
            buckets.setdefault((event.get("ticker"), event.get("cik")), []).append(event)

        universe_by_ticker: dict[str, object] = {}
        for row in universe_rows or ():
            ticker = getattr(row, "ticker", None)
            if isinstance(ticker, str) and ticker not in universe_by_ticker:
                universe_by_ticker[ticker] = row

        rows: dict[str, dict] = {}
        ok_tickers: set[str] = set()
        accepted_pairs: list[tuple[datetime, dict]] = []
        records: dict[tuple[object, object, object], tuple[Mapping, object]] = {}
        sources: dict[str, tuple[Mapping, object]] = {}

        raw_issuers = index.get("issuers")
        if not isinstance(raw_issuers, list):
            raw_issuers = []
        for issuer in raw_issuers:
            if not isinstance(issuer, Mapping):
                continue
            ticker = issuer.get("ticker")
            universe_row = universe_by_ticker.get(ticker) if isinstance(ticker, str) else None
            if universe_row is None:
                # Absent from the universe: ignored, never exposed.
                continue
            rows[ticker] = {"ticker": ticker,
                            "issuer_id": issuer.get("issuer_id"),
                            "name": issuer.get("name"),
                            "supported": False}
            issuer_events = buckets.get((ticker, issuer.get("cik")), ())
            ok = (issuer.get("status") == "ok"
                  and issuer.get("cik") == getattr(universe_row, "cik", None)
                  and issuer.get("issuer_id")
                  == "cik:%010d" % issuer.get("cik", 0)
                  and all(_record_ok(record, issuer, universe_row, window_start,
                                     t_start, t_complete, filing_key_counts)
                          for record in issuer_events))
            if not ok:
                # One bad record poisons the whole issuer for this read;
                # never "skip and claim complete".
                continue
            ok_tickers.add(ticker)
            rows[ticker]["supported"] = True
            for record in issuer_events:
                event = _event_dict(record)
                accepted = _parse_clock(record.get("acceptance_datetime"))
                if accepted is None:
                    continue
                accepted_pairs.append((accepted, event))
                records[(event["filing_key"], event["source_url"], event["ticker"])] = (
                    record, universe_row)
                sources["sec:" + str(event["filing_key"])] = (record, universe_row)

        accepted_pairs.sort(key=lambda pair: (-pair[0].timestamp(),
                                              str(pair[1].get("filing_key") or "")))
        return _Snapshot(
            empty=False,
            snapshot_id=str(getattr(latest, "snapshot_id", "") or ""),
            t_start=t_start,
            t_complete=t_complete,
            window_start=window_start,
            rows=rows,
            events=accepted_pairs,
            records=records,
            sources=sources,
            ok_tickers=frozenset(ok_tickers),
            in_window_count=len(accepted_pairs),
            index_truncated=index.get("truncated"),
            index_outcome=index.get("outcome"),
        )
    except Exception:
        return _EMPTY_SNAPSHOT


class _Reader:
    """Per-source state cache plus the five admitted read callables."""

    def __init__(self, store: object, *, universe=None, clock=None,
                 monotonic=None, loader=None):
        self._store = store
        self._universe_param = universe
        self._universe_rows: tuple | None = None
        self._clock: Callable[[], datetime] = clock or (
            lambda: datetime.now(timezone.utc))
        self._monotonic: Callable[[], float] = monotonic or time.monotonic
        if loader is None:
            from engine.marketing.catalyst_source_store import read_latest_index
            loader = read_latest_index
        self._loader = loader
        self._lock = threading.Lock()
        self._state: _Snapshot | None = None
        self._loaded_at: float | None = None
        self._local = threading.local()

    def _universe(self) -> tuple:
        if self._universe_rows is None:
            if self._universe_param is not None:
                self._universe_rows = tuple(self._universe_param)
            else:
                from engine.marketing.catalyst_source_cycle import load_universe
                self._universe_rows = load_universe(UNIVERSE_PATH)
        return self._universe_rows

    def _current_state(self) -> _Snapshot:
        mono = self._monotonic()
        with self._lock:
            if (self._state is None or self._loaded_at is None
                    or (mono - self._loaded_at) > CACHE_TTL_SECONDS):
                try:
                    latest = self._loader(self._store)
                    state = _build_snapshot(latest, self._universe())
                except Exception:
                    state = _EMPTY_SNAPSHOT
                self._state = state
                self._loaded_at = mono
            return self._state

    def _read_state(self, now: datetime) -> _Snapshot | None:
        """Pinned state when pinned <TTL ago (one read, one snapshot), else current."""
        pin = getattr(self._local, "pin", None)
        if pin is not None and (self._monotonic() - pin[0]) < CACHE_TTL_SECONDS:
            state = pin[1]
        else:
            state = self._current_state()
        return state if state.fresh(now) else None

    # --- the five admitted callables -------------------------------------

    def issuer_universe(self, now: datetime) -> dict:
        state = self._current_state()
        self._local.pin = (self._monotonic(), state)
        if not state.fresh(now):
            return {}
        return {ticker: dict(row) for ticker, row in state.rows.items()}

    def recent_events(self, start: datetime, end: datetime, limit: int) -> list:
        state = self._read_state(self._clock())
        if state is None or state.t_start is None:
            return []
        return _events_in(state, start, end)[:limit]

    def document_observation(self, event: Mapping, now: datetime):
        state = self._read_state(now)
        if state is None or not isinstance(event, Mapping):
            return None
        found = state.records.get(
            (event.get("filing_key"), event.get("source_url"), event.get("ticker")))
        if found is None:
            return None
        record, _universe_row = found
        exhibit = record.get("exhibit") or {}
        retention = record.get("retention") or {}
        lineage = record.get("lineage") or {}
        figures = tuple(
            VerifiedEarningsFigure(
                field=figure.get("field"),
                value=figure.get("value"),
                basis=figure.get("basis"),
                document_sha256=exhibit.get("document_sha256"),
                span_sha256=figure.get("span_sha256"))
            for figure in (record.get("figures") or [])
            if isinstance(figure, Mapping))
        # Passed through only when it agrees with the record's parse status.
        outcome = record.get("figure_outcome")
        if (not isinstance(outcome, str)
                or FIGURE_OUTCOMES.get(outcome) != record.get("parse_status")):
            outcome = ""
        return VerifiedDocumentObservation(
            source_id="sec:" + str(record.get("filing_key")),
            document_url=exhibit.get("source_url"),
            document_sha256=exhibit.get("document_sha256"),
            receipt_id=retention.get("first_retained_receipt_id"),
            owner_ref=OBSERVATION_OWNER_REF,
            first_verified_at_utc=_parse_clock(retention.get("first_retained_at")),
            checked_at_utc=_parse_clock(retention.get("last_verified_at")),
            source_snapshot_version=state.snapshot_id,
            filing_form=record.get("form"),
            amends_filing_key=lineage.get("amends_filing_key", ""),
            verified_figures=figures,
            figure_outcome=outcome,
        )

    def source_coverage(self, start: datetime, end: datetime, now: datetime):
        state = self._read_state(now)
        if state is None or state.window_start is None or state.t_start is None:
            return None
        if state.window_start > start:
            return None
        tickers = frozenset(state.ok_tickers)
        # Completeness is judged on the caller's own window (start .. t_start)
        # read from the state pinned at ``now``, not the wider writer window.
        window_events = _events_in(state, start, end)
        complete = (state.index_truncated is False
                    and state.index_outcome != "TRUNCATED"
                    and len(window_events) <= EVENT_LIMIT)
        return SourceCoverageReceipt(
            source="edgar_8k_202",
            receipt_id="catcov-" + hashlib.sha256(
                state.snapshot_id.encode("utf-8")).hexdigest()[:40],
            owner_ref=COVERAGE_OWNER_REF,
            snapshot_version=state.snapshot_id,
            issuer_tickers=tickers if tickers else None,
            window_start_utc=start,
            window_end_utc=state.t_start,
            checked_at_utc=state.t_complete,
            outcome="COMPLETE" if complete else "TRUNCATED",
            pagination_exhausted=True,
            truncated=not complete,
            returned_events=min(len(window_events), EVENT_LIMIT),
            event_limit=EVENT_LIMIT,
        )

    def public_grant(self, source_id: str, now: datetime):
        state = self._read_state(now)
        if state is None or not isinstance(source_id, str):
            return None
        found = state.sources.get(source_id)
        if found is None:
            return None
        record, universe_row = found
        if not _f4_identity_ok(record, universe_row):
            return None
        retention = record.get("retention") or {}
        exhibit = record.get("exhibit") or {}
        first = _parse_clock(retention.get("first_retained_at"))
        if first is None or first > now:
            return None
        expires = min(first + GRANT_MAX_LIFETIME, now + GRANT_MAX_AHEAD)
        if expires <= now:
            return None
        return PublicSourceGrant(
            source_id=source_id,
            receipt_id=retention.get("first_retained_receipt_id"),
            owner_ref=GRANT_OWNER_REF,
            audience="public_anonymous",
            effective_at_utc=first,
            expires_at_utc=expires,
            display_link=True,
            display_title=True,
            display_facts=True,
            document_url=exhibit.get("source_url"),
            document_sha256=exhibit.get("document_sha256"),
        )


def build_admitted_source(store: object, *, universe=None, clock=None,
                          monotonic=None, loader=None) -> AdmittedEdgarSource:
    """Build the admitted read source over a namespaced source store.

    Performs NO I/O at construction time: the index is loaded lazily on the
    first read and then cached for ``CACHE_TTL_SECONDS``; a load that raises or
    returns None yields an empty fail-closed state cached for the same TTL.
    """
    reader = _Reader(store, universe=universe, clock=clock,
                     monotonic=monotonic, loader=loader)
    return AdmittedEdgarSource(
        issuer_universe=reader.issuer_universe,
        recent_events=reader.recent_events,
        public_grant=reader.public_grant,
        document_observation=reader.document_observation,
        source_coverage=reader.source_coverage,
    )
