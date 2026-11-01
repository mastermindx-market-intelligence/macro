"""Catalyst SEC source cycle WRITER: the scheduled off-render EDGAR sweep.

Reads SEC EDGAR submissions for a fixed pilot universe, finds 8-K / 8-K/A
filings carrying Item 2.02 inside the last 7 days, retrieves each issuer's
EX-99.1 earnings release IN MEMORY, hashes it and projects its figures with
the incumbent Earnings Release binder, then publishes exactly ONE canonical
index JSON (no document bytes) as an immutable source_sync snapshot inside the
``marketing/catalyst-sec-source/v1/`` namespace.

D4 retention (rights decision): SEC document bytes are never persisted — no
store object, no file, no log.  Only URL, sha256, projected figures, filing
clocks and the first-retrieval receipt id survive.  The writer therefore never
calls any incumbent SEC-byte persistence function (archive/manifest/receipt
writers stay with their owners); the ONLY store write is the index snapshot
produced by ``sync_source_roots`` through the namespaced wrapper.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

from collectors.edgar_forensics import SecRequestPacer, endpoint_url
from engine.fundamental_forensics.sec_document_spine import (
    ARCHIVE_ORIGIN,
    FilingManifestError,
    archive_document_url,
    build_filing_manifests,
)
from engine.fundamental_forensics.source_sync import sync_source_roots
from engine.marketing.catalyst_packets import FIGURE_OUTCOMES, bound_figure_outcome
from engine.marketing.catalyst_source_store import (
    INDEX_RELATIVE_PATH,
    INDEX_SCHEMA,
    NAMESPACE_PREFIX,
    CatalystSourceUnavailable,
    NamespacedSourceStore,
    read_latest_index,
    validate_index,
)
from engine.news_impact.edgar_body import (
    _HREF_RE,
    _TD_RE,
    _TH_RE,
    _TR_RE,
    _cell_text,
    _find_index_table,
    index_url,
    parse_filing_index,
)
from engine.research_vault.r2_store import StrictConditionalWriteStore

UNIVERSE_SCHEMA = "marketing.catalyst_pilot_universe/v1"
MAX_UNIVERSE = 100
MAX_REQUEST_BUDGET = 150
MIN_INTERVAL_SECONDS = 0.2
WINDOW = timedelta(days=7)

_SUBMISSIONS_CAP = 16 * 1024 * 1024
_INDEX_CAP = 2 * 1024 * 1024
_DOCUMENT_CAP = 8 * 1024 * 1024
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_RETRYABLE_ITEM_FORMS = frozenset({"8-K", "8-K/A"})
_MAX_USER_AGENT = 256
_UA_EMAIL_RE = re.compile(
    r"^[<(]?[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}[>)]?$")


class RequestBudgetExhausted(RuntimeError):
    """The cycle's SEC GET budget is spent; no further request may be made."""


class SecGetRefused(RuntimeError):
    """One bounded SEC GET was refused (status, redirect, size or shape)."""


class SecAccessHalted(RuntimeError):
    """SEC refused access (403) or kept rate-limiting (429): stop the cycle.

    Fair access: once SEC says stop, the cycle makes no further request.
    """


def _user_agent_ok(value: object) -> bool:
    """SEC fair-access User-Agent: a declared name plus a contact email.

    Printable ASCII only (no CR/LF header injection), bounded length, one
    token shaped like an email address and at least one other token naming
    the requester.
    """
    if not isinstance(value, str) or not 1 <= len(value) <= _MAX_USER_AGENT:
        return False
    if any(not 0x20 <= ord(char) <= 0x7E for char in value):
        return False
    tokens = value.split()
    emails = [token for token in tokens if _UA_EMAIL_RE.match(token)]
    names = [token for token in tokens
             if not _UA_EMAIL_RE.match(token) and any(c.isalpha() for c in token)]
    return bool(emails) and bool(names)


def _finite(value: object) -> float | None:
    """Private copy of the producer's finite-number gate (catalyst_packets)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    import math

    return number if math.isfinite(number) else None


def _fmt(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now() -> datetime:
    """The CLI's default clock (aware UTC)."""
    return datetime.now(timezone.utc)


def _parse_clock(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def new_session():
    """Build the cycle's SEC session (module-level so tests can intercept)."""
    import requests

    return requests.Session()


@dataclass(frozen=True)
class UniverseIssuer:
    """One fixed pilot-universe member."""

    ticker: str
    cik: int
    name: str


@dataclass(frozen=True)
class CycleResult:
    """The cycle's terminal fact sheet (never carries SEC bytes)."""

    outcome: str
    exit_code: int
    requests_used: int
    events: tuple
    issuers_ok: int
    issuers_incomplete: int
    issuers_failed: int
    issuers_not_checked: int
    snapshot_id: str | None
    reason: str | None


def load_universe(path: object) -> tuple[UniverseIssuer, ...]:
    """Load and validate ``marketing.catalyst_pilot_universe/v1``.

    Enforces 1..100 rows, exact ticker shape, positive int CIKs (never bools),
    non-empty names and unique tickers and CIKs.  Any violation is a
    ``ValueError``.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != UNIVERSE_SCHEMA:
        raise ValueError("universe schema must be marketing.catalyst_pilot_universe/v1")
    rows = raw.get("issuers")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_UNIVERSE:
        raise ValueError("universe must carry 1..100 issuers")
    issuers: list[UniverseIssuer] = []
    seen_tickers: set[str] = set()
    seen_ciks: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("universe row must be an object")
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or not _TICKER_RE.fullmatch(ticker):
            raise ValueError("universe ticker is invalid")
        cik = row.get("cik")
        if isinstance(cik, bool) or not isinstance(cik, int) or cik <= 0:
            raise ValueError("universe cik must be a positive int")
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("universe name must be a non-empty string")
        if ticker in seen_tickers:
            raise ValueError("universe ticker is duplicated")
        if cik in seen_ciks:
            raise ValueError("universe cik is duplicated")
        seen_tickers.add(ticker)
        seen_ciks.add(cik)
        issuers.append(UniverseIssuer(ticker=ticker, cik=cik, name=name))
    return tuple(issuers)


def project_release_figures(
    *,
    cik: int,
    accession: str,
    body_bytes: bytes,
    manifest: Mapping,
    exhibit_url: str,
    document_sha256: str,
) -> tuple[str, tuple[dict, ...], str]:
    """Project an EX-99.1 body's figures exactly as the public packet does.

    Mirrors the bind block of ``engine/marketing/catalyst_packets.py``: bind
    with the incumbent Earnings Release binder, map eps_diluted / revenue
    candidates, replay every span receipt against the exact bytes and drop
    non-finite amounts.  Returns ``(status, figures, figure_outcome)`` where
    status is ``parsed``, ``no_figures``, ``parse_failed`` or
    ``binding_digest_mismatch`` and figure_outcome is one of
    ``FIGURE_OUTCOMES`` (empty on a digest mismatch), so a release with no
    projectable figures never reads like a binder failure.
    """
    from engine.earnings_release.binding import bind_release_document
    from engine.earnings_release.receipts import replay_receipt

    try:
        body = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return ("parse_failed", (), "document_not_utf8")
    try:
        bound = bind_release_document(
            cik=cik,
            accession=accession,
            body=body,
            form=manifest["filing"]["form"],
            filing_date=manifest["clocks"]["filed_on"],
            acceptance_datetime=manifest["clocks"]["accepted_at"],
            report_date=manifest["filing"]["report_date"],
            exhibit_url=exhibit_url,
        )
    except Exception:  # noqa: BLE001 - a binding failure is never fatal to D4.
        return ("parse_failed", (), "binder_exception")
    if bound.revision.source_sha256 != document_sha256:
        # Checked OUTSIDE the generic except so it can never be swallowed.
        return ("binding_digest_mismatch", (), "")
    figures: list[dict] = []
    try:
        for f in bound.figures.figures:
            candidate: tuple[str, str, float] | None = None
            if (f.concept == "eps_diluted" and f.units == "per_share"
                    and f.currency == "USD" and f.scale_factor == 1.0
                    and f.basis in ("gaap", "non_gaap")):
                candidate = (
                    "eps_actual",
                    "gaap" if f.basis == "gaap" else "adjusted",
                    f.value,
                )
            elif (f.concept == "revenue" and f.currency == "USD"
                  and f.basis == "gaap"
                  and f.scale_factor is not None
                  and f.scale_factor > 0):
                candidate = ("rev_actual", "reported", f.value * f.scale_factor)
            if candidate is None:
                continue
            replay_receipt(f.receipt, source=body)
            field, basis, amount = candidate
            if _finite(amount) is None:
                continue
            figures.append({
                "field": field,
                "basis": basis,
                "value": float(amount),
                "span_sha256": f.receipt.span_sha256,
            })
    except Exception:  # noqa: BLE001 - unreadable attachment, no facts admitted.
        return ("parse_failed", (), "replay_failed")
    outcome = bound_figure_outcome(bound.figures.outcome, len(figures))
    return (FIGURE_OUTCOMES[outcome], tuple(figures), outcome)


class _Cycle:
    """One bounded cycle run; the only SEC client is ``_bounded_get``."""

    def __init__(self, *, store, session, user_agent, clock, sleep, max_requests,
                 min_interval_seconds) -> None:
        self._store = store
        self._session = session
        self._user_agent = user_agent
        self._clock = clock
        self._sleep = sleep
        self._max_requests = max_requests
        self._pacer = SecRequestPacer(min_interval_seconds=min_interval_seconds)
        self.requests_used = 0
        self.budget_exhausted = False
        self.halt_reason: str | None = None

    def _clock_now(self) -> datetime:
        return self._clock()

    def _bounded_get(self, url: str, cap: int) -> bytes | None:
        """The ONE SEC GET path: paced, budgeted, bounded, no redirects."""
        attempt = 0
        while True:
            attempt += 1
            if self.halt_reason is not None:
                raise SecAccessHalted(self.halt_reason)
            if self.requests_used >= self._max_requests:
                self.budget_exhausted = True
                raise RequestBudgetExhausted("sec request budget exhausted")
            self._pacer.acquire()
            self.requests_used += 1
            response = self._session.get(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
                timeout=30,
                stream=True,
                allow_redirects=False,
            )
            try:
                status = getattr(response, "status_code", None)
                if isinstance(status, int) and 300 <= status < 400:
                    raise SecGetRefused("redirect_refused")
                if status == 404:
                    return None
                if status == 403:
                    self.halt_reason = "sec_access_refused"
                    raise SecAccessHalted(self.halt_reason)
                if status != 200 and status in _RETRY_STATUSES and attempt < _MAX_ATTEMPTS:
                    self._sleep(min(2 ** attempt, 8))
                    continue
                if status == 429:
                    self.halt_reason = "sec_rate_limited"
                    raise SecAccessHalted(self.halt_reason)
                if status != 200:
                    raise SecGetRefused("status_refused")
                if getattr(response, "url", None) != url:
                    raise SecGetRefused("response_url_mismatch")
                headers = getattr(response, "headers", None) or {}
                declared = headers.get("Content-Length")
                if declared is not None:
                    try:
                        declared_length = int(str(declared).strip())
                    except ValueError:
                        raise SecGetRefused("content_length_invalid") from None
                    if declared_length > cap:
                        raise SecGetRefused("content_length_over_cap")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=65536):
                    if not isinstance(chunk, bytes):
                        raise SecGetRefused("chunk_not_bytes")
                    total += len(chunk)
                    if total > cap:
                        raise SecGetRefused("body_over_cap")
                    chunks.append(chunk)
                return b"".join(chunks)
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()


def _row_items_tokens(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


def _reduced_payload(payload: dict, keep: list[int]) -> dict:
    recent = payload["filings"]["recent"]
    return {
        "cik": payload.get("cik"),
        "name": payload.get("name"),
        "tickers": payload.get("tickers"),
        "filings": {
            "recent": {
                field: [values[index] for index in keep]
                for field, values in recent.items()
            },
        },
    }


def run_cycle(
    *,
    store,
    universe,
    user_agent,
    clock,
    session=None,
    sleep=time.sleep,
    max_requests=150,
    min_interval_seconds=0.2,
    work_root=None,
) -> CycleResult:
    """Run one catalyst SEC source cycle and publish the canonical index.

    Refusals (exit 2) make zero session calls and publish nothing.  A cycle
    ends COMPLETE (0), TRUNCATED (3), PARTIAL (4) or PUBLISH_FAILED (5).  A
    cycle in which no issuer was swept ok or incomplete, or in which no issuer
    was verified (swept ok, or a prior event definitively withdrawn), ends
    FAILED (6) and publishes nothing, leaving the prior pointer unchanged; this
    includes a budget/403/429 halt before anything was verified.  The reader
    serves that pointer only while it is younger than its freshness bound
    (``MAX_SNAPSHOT_AGE`` in catalyst_source_adapter, 10 minutes), so repeated
    FAILED cycles take the catalyst surface dark.  A 403, or a
    429 that outlasts the retries, otherwise halts the cycle (TRUNCATED): no
    further SEC request is made and every unswept issuer carries its prior
    events.
    """
    if not _user_agent_ok(user_agent):
        return _refused("user_agent_invalid")
    if not isinstance(universe, (tuple, list)) or not 1 <= len(universe) <= MAX_UNIVERSE:
        return _refused("universe_out_of_range")
    if (isinstance(max_requests, bool) or not isinstance(max_requests, int)
            or not 1 <= max_requests <= MAX_REQUEST_BUDGET):
        return _refused("max_requests_invalid")
    if (isinstance(min_interval_seconds, bool)
            or not isinstance(min_interval_seconds, (int, float))
            or min_interval_seconds < MIN_INTERVAL_SECONDS):
        return _refused("min_interval_seconds_invalid")
    if not isinstance(store, StrictConditionalWriteStore):
        return _refused("store_not_conditional_write")
    if not isinstance(store, NamespacedSourceStore) or store.prefix != NAMESPACE_PREFIX:
        return _refused("store_not_catalyst_namespace")
    try:
        prior = read_latest_index(store)
    except CatalystSourceUnavailable:
        return _refused("prior_index_unreadable")

    cycle = _Cycle(
        store=store, session=session if session is not None else new_session(),
        user_agent=user_agent, clock=clock, sleep=sleep, max_requests=max_requests,
        min_interval_seconds=min_interval_seconds,
    )

    started = clock()
    window_start = started - WINDOW
    window_end = started
    issuer_rows: list[dict] = []
    events: list[dict] = []
    skipped: list[dict] = []
    truncated = False
    prior_events_by_ticker: dict[str, dict[str, dict]] = {}
    if prior is not None:
        for event in prior.index.get("events", []):
            prior_events_by_ticker.setdefault(str(event["ticker"]), {})[
                str(event["filing_key"])] = event

    stop_reason: str | None = None
    verified_issuers = 0
    for issuer in universe:
        prior_for_issuer = prior_events_by_ticker.get(issuer.ticker, {})
        if stop_reason is not None:
            issuer_rows.append(_issuer_row(issuer, "not_checked", stop_reason))
            events.extend(_carry_prior_events(prior_for_issuer, window_start, window_end))
            continue
        try:
            status, reason, issuer_events, issuer_skipped, verified = _process_issuer(
                cycle, issuer, started, window_start, window_end, prior_for_issuer,
            )
        except (RequestBudgetExhausted, SecAccessHalted):
            status, reason, issuer_events, issuer_skipped, verified = None, None, [], [], False
        if cycle.budget_exhausted or cycle.halt_reason is not None:
            # The interrupted issuer's in-flight work is discarded; it and
            # every later issuer are not_checked with prior in-window events
            # carried unchanged so first-retrieval identity survives.
            truncated = True
            stop_reason = cycle.halt_reason or "budget_exhausted"
            issuer_rows.append(_issuer_row(issuer, "not_checked", stop_reason))
            events.extend(_carry_prior_events(prior_for_issuer, window_start, window_end))
            continue
        if status in ("not_checked", "failed"):
            # A failed sweep proves nothing new: keep the prior in-window
            # events (and their ORIGINAL receipts) instead of dropping them.
            events.extend(_carry_prior_events(prior_for_issuer, window_start, window_end))
        else:
            events.extend(issuer_events)
        skipped.extend(issuer_skipped)
        issuer_rows.append(_issuer_row(issuer, status, reason))
        if verified:
            verified_issuers += 1

    counts = {status: sum(1 for row in issuer_rows if row["status"] == status)
              for status in ("ok", "incomplete", "failed", "not_checked")}
    if counts["ok"] + counts["incomplete"] == 0 or verified_issuers == 0:
        # Nothing was swept, or every swept issuer only deferred transient
        # failures: publishing would only replace the prior pointer with an
        # index that proves less.  Keep the prior snapshot serving.
        swept = counts["ok"] + counts["incomplete"]
        return CycleResult(
            outcome="FAILED", exit_code=6, requests_used=cycle.requests_used,
            events=(), issuers_ok=counts["ok"],
            issuers_incomplete=counts["incomplete"],
            issuers_failed=counts["failed"],
            issuers_not_checked=counts["not_checked"], snapshot_id=None,
            reason=stop_reason or ("no_issuer_verified" if swept else "no_issuer_swept"),
        )
    if truncated:
        outcome, exit_code = "TRUNCATED", 3
    elif counts["ok"] != len(issuer_rows):
        outcome, exit_code = "PARTIAL", 4
    else:
        outcome, exit_code = "COMPLETE", 0

    completed = cycle._clock_now()
    index = {
        "schema": INDEX_SCHEMA,
        "cycle_started_at": _fmt(started),
        "cycle_completed_at": _fmt(completed),
        "window_start": _fmt(window_start),
        "window_end": _fmt(window_end),
        "requests_used": cycle.requests_used,
        "request_budget": max_requests,
        "outcome": outcome,
        "truncated": truncated,
        "issuers": issuer_rows,
        "events": _sorted_events(events),
        "skipped": skipped,
    }

    work_dir = None
    try:
        if work_root is not None:
            Path(work_root).mkdir(parents=True, exist_ok=True)
        work_dir = Path(tempfile.mkdtemp(dir=work_root))
        raw_root = work_dir / "raw"
        archive_root = work_dir / "archive"
        (raw_root / "catalyst").mkdir(parents=True)
        archive_root.mkdir()
        index_bytes = json.dumps(
            index, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        (raw_root / INDEX_RELATIVE_PATH).write_bytes(index_bytes)
        validate_index(index)
        snapshot = sync_source_roots(
            raw_root=raw_root,
            archive_root=archive_root,
            store=store,
            snapshot_at=completed,
            publish_latest=True,
            skip_objects_in_latest_manifest=True,
        )
        return CycleResult(
            outcome=outcome, exit_code=exit_code, requests_used=cycle.requests_used,
            events=tuple(index["events"]), issuers_ok=counts["ok"],
            issuers_incomplete=counts["incomplete"], issuers_failed=counts["failed"],
            issuers_not_checked=counts["not_checked"],
            snapshot_id=snapshot.snapshot_id, reason=stop_reason,
        )
    except Exception as exc:  # noqa: BLE001 - publish failure keeps prior pointer.
        return CycleResult(
            outcome="PUBLISH_FAILED", exit_code=5, requests_used=cycle.requests_used,
            events=tuple(index["events"]), issuers_ok=counts["ok"],
            issuers_incomplete=counts["incomplete"], issuers_failed=counts["failed"],
            issuers_not_checked=counts["not_checked"], snapshot_id=None,
            reason=type(exc).__name__,
        )
    finally:
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)


def _refused(reason: str) -> CycleResult:
    return CycleResult(
        outcome="REFUSED", exit_code=2, requests_used=0, events=(),
        issuers_ok=0, issuers_incomplete=0, issuers_failed=0,
        issuers_not_checked=0, snapshot_id=None, reason=reason,
    )


def _issuer_row(issuer: UniverseIssuer, status: str, reason: str | None) -> dict:
    return {
        "ticker": issuer.ticker,
        "cik": issuer.cik,
        "name": issuer.name,
        "issuer_id": f"cik:{issuer.cik:010d}",
        "status": status,
        "reason": reason,
    }


def _sorted_events(events: list[dict]) -> list[dict]:
    by_filing = sorted(events, key=lambda event: event["filing_key"])
    by_acceptance = sorted(
        by_filing, key=lambda event: event["acceptance_datetime"], reverse=True)
    return by_acceptance


def _carry_prior_events(prior: dict[str, dict], window_start: datetime,
                        window_end: datetime) -> list[dict]:
    """Copy a failed/not_checked issuer's in-window prior events unchanged.

    The reader serves only ``ok`` issuers, so a carried event is never shown
    from this cycle; it exists so the next sweep re-verifies it under its
    original first-retrieval receipt instead of minting a new one.
    """
    carried: list[dict] = []
    for event in prior.values():
        accepted = _parse_clock(event.get("acceptance_datetime"))
        if accepted is None or not window_start <= accepted <= window_end:
            continue
        carried.append(dict(event))
    return carried


def _process_issuer(cycle: _Cycle, issuer: UniverseIssuer, started: datetime,
                    window_start: datetime, window_end: datetime,
                    prior_by_key: dict[str, dict]):
    """Sweep one issuer; returns (status, reason, events, skipped, verified).

    ``verified`` is False when the issuer failed, or when every in-window
    filing raised a transient error: such an issuer proves nothing new and
    never by itself justifies replacing the prior index pointer.
    """
    try:
        body = cycle._bounded_get(endpoint_url(issuer.cik, "submissions"), _SUBMISSIONS_CAP)
    except (RequestBudgetExhausted, SecAccessHalted):
        raise
    except Exception as exc:  # noqa: BLE001 - submissions failure fails the issuer.
        return "failed", type(exc).__name__, [], [], False
    if body is None:
        return "failed", "submissions_missing", [], [], False
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - undecodable submissions fail the issuer.
        return "failed", type(exc).__name__, [], [], False

    try:
        if int(payload["cik"]) != issuer.cik:
            return "failed", "identity_mismatch", [], [], False
        tickers = [str(t).upper() for t in (payload.get("tickers") or [])]
        if issuer.ticker not in tickers:
            return "failed", "identity_mismatch", [], [], False
    except Exception as exc:  # noqa: BLE001 - malformed identity fails the issuer.
        return "failed", type(exc).__name__, [], [], False

    filings = payload.get("filings")
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return "failed", "submissions_shape", [], [], False
    if recent:
        lengths = {len(values) if isinstance(values, list) else None
                   for values in recent.values()}
        if None in lengths or len(lengths) > 1:
            return "failed", "submissions_shape", [], [], False

    files = filings.get("files") if isinstance(filings, dict) else None
    if files is None:
        files = []
    if not isinstance(files, list):
        return "failed", "submissions_shape", [], [], False
    if files:
        raw_acceptances = recent.get("acceptanceDateTime")
        acceptances = [
            _parse_clock(value) for value in raw_acceptances
            if isinstance(raw_acceptances, list) and isinstance(value, str)
        ]
        acceptances = [value for value in acceptances if value is not None]
        if not acceptances or min(acceptances) >= window_start:
            return "failed", "pagination_unproven", [], [], False

    forms = recent.get("form") or []
    items = recent.get("items") or []
    raw_acceptances = recent.get("acceptanceDateTime") or []
    accession_numbers = recent.get("accessionNumber") or []
    keep: list[int] = []
    for index in range(len(accession_numbers)):
        form = forms[index] if index < len(forms) else None
        if form not in _RETRYABLE_ITEM_FORMS:
            continue
        if "2.02" not in _row_items_tokens(items[index] if index < len(items) else None):
            continue
        accepted = _parse_clock(
            raw_acceptances[index] if index < len(raw_acceptances) else None)
        if accepted is None or not window_start <= accepted <= window_end:
            continue
        keep.append(index)

    try:
        manifests = build_filing_manifests(
            _reduced_payload(payload, keep),
            cik=issuer.cik,
            ticker=issuer.ticker,
            recorded_at=started,
        )
    except FilingManifestError:
        return "failed", "manifest_error", [], [], False
    except Exception as exc:  # noqa: BLE001 - any manifest failure fails the issuer.
        return "failed", type(exc).__name__, [], [], False

    events: list[dict] = []
    skipped: list[dict] = []
    incomplete = False
    withdrawn = 0
    for manifest in manifests:
        accepted = _parse_clock(manifest["clocks"]["accepted_at"])
        if accepted is None or not window_start <= accepted <= window_end:
            continue
        filing_key = f"{issuer.cik:010d}:{manifest['filing']['accession']}"
        prior_event = prior_by_key.get(filing_key)
        try:
            if prior_event is not None:
                event = _carry_filing(cycle, issuer, manifest, accepted, prior_event, skipped)
            else:
                event = _new_filing(cycle, issuer, manifest, accepted, skipped)
        except (RequestBudgetExhausted, SecAccessHalted):
            raise
        except Exception as exc:  # noqa: BLE001 - per-filing failure skips the filing.
            if prior_event is not None:
                # A transient re-verify failure is not evidence the document
                # changed: keep the prior event (original receipt, prior
                # last_verified_at) and mark the issuer incomplete.
                events.append(dict(prior_event))
                skipped.append({
                    "ticker": issuer.ticker,
                    "accession": manifest["filing"]["accession"],
                    "reason": "reverify_deferred",
                })
                incomplete = True
                continue
            skipped.append({
                "ticker": issuer.ticker,
                "accession": manifest["filing"]["accession"],
                "reason": type(exc).__name__,
            })
            incomplete = True
            continue
        if event is None:
            incomplete = True
            if prior_event is not None:
                # A definitive withdrawal (integrity mismatch / document
                # missing) changes what the reader serves, so it counts as
                # verified work; an unattested or unparseable new filing does not.
                withdrawn += 1
            continue
        events.append(event)
    status = "incomplete" if incomplete or skipped else "ok"
    reason = skipped[0]["reason"] if (incomplete and skipped) else None
    return status, reason, events, skipped, status == "ok" or withdrawn > 0


def _lineage_for(issuer: UniverseIssuer, manifest: dict) -> tuple[str, int] | None:
    """Attested 8-K/A lineage, or None when the amendment is unattested."""
    if manifest["filing"]["form"] != "8-K/A":
        return ("", 0)
    lineage = manifest["lineage"]
    if lineage.get("relationship") != "observed_accession":
        return None
    amends = lineage.get("amends_accession")
    if (not isinstance(amends, str)
            or not amends.startswith(f"{issuer.cik:010d}-")
            or amends == manifest["filing"]["accession"]):
        return None
    return (f"{issuer.cik:010d}:{amends}", 1)


def _carry_filing(cycle: _Cycle, issuer: UniverseIssuer, manifest: dict,
                  accepted: datetime, prior_event: dict, skipped: list[dict]) -> dict | None:
    """Re-verify one prior-index filing by document sha; never re-parses it."""
    if (prior_event.get("form") != manifest["filing"]["form"]
            or prior_event.get("acceptance_datetime") != _fmt(accepted)):
        skipped.append({
            "ticker": issuer.ticker,
            "accession": manifest["filing"]["accession"],
            "reason": "integrity_mismatch",
        })
        return None
    body = cycle._bounded_get(prior_event["exhibit"]["source_url"], _DOCUMENT_CAP)
    if body is None:
        skipped.append({
            "ticker": issuer.ticker,
            "accession": manifest["filing"]["accession"],
            "reason": "document_missing",
        })
        return None
    digest = hashlib.sha256(body).hexdigest()
    del body
    if digest != prior_event["exhibit"]["document_sha256"]:
        skipped.append({
            "ticker": issuer.ticker,
            "accession": manifest["filing"]["accession"],
            "reason": "integrity_mismatch",
        })
        return None
    carried = dict(prior_event)
    carried["retention"] = {
        **prior_event["retention"],
        "last_verified_at": _fmt(cycle._clock_now()),
    }
    return carried


def _ex99_1_row_hrefs(html: str) -> list[str]:
    """Raw hrefs of the filing-index rows whose Type cell is exactly EX-99.1.

    The CIK/accession check binds to the matched row's own link, never to
    any link elsewhere on the page.
    """
    table = _find_index_table(html)
    if table is None:
        return []
    hrefs: list[str] = []
    for row in _TR_RE.findall(table):
        if _TH_RE.search(row):
            continue
        cells = _TD_RE.findall(row)
        if len(cells) < 4 or _cell_text(cells[3]) != "EX-99.1":
            continue
        links = _HREF_RE.findall(cells[2])
        hrefs.append(links[0] if len(links) == 1 else "")
    return hrefs


def _new_filing(cycle: _Cycle, issuer: UniverseIssuer, manifest: dict,
                accepted: datetime, skipped: list[dict]) -> dict | None:
    """Retrieve, hash, project and drop one NEW EX-99.1 in memory (D4)."""
    accession = manifest["filing"]["accession"]
    lineage = _lineage_for(issuer, manifest)
    if lineage is None:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "unattested_amendment",
        })
        return None
    amends_filing_key, correction_generation = lineage

    filing_date = manifest["clocks"].get("filed_on")
    if not isinstance(filing_date, str) or not filing_date:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "manifest_error",
        })
        return None

    index_body = cycle._bounded_get(
        index_url(f"{issuer.cik:010d}", accession), _INDEX_CAP)
    if index_body is None:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "index_missing",
        })
        return None
    try:
        html = index_body.decode("utf-8")
    except UnicodeDecodeError:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "UnicodeDecodeError",
        })
        return None
    del index_body
    documents = parse_filing_index(html)
    matches = [doc for doc in documents if doc.doc_type.strip() == "EX-99.1"]
    if not matches:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "no_ex99_1",
        })
        return None
    if len(matches) > 1:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "ambiguous_ex99_1",
        })
        return None
    filename = matches[0].filename
    acc_nodash = accession.replace("-", "")
    direct_href = f"/Archives/edgar/data/{issuer.cik}/{acc_nodash}/{filename}"
    row_hrefs = _ex99_1_row_hrefs(html)
    url = archive_document_url(issuer.cik, accession, filename)
    if (len(row_hrefs) != 1 or row_hrefs[0] not in (direct_href, "/ix?doc=" + direct_href)
            or not url.startswith(f"{ARCHIVE_ORIGIN}/{issuer.cik}/{acc_nodash}/")):
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "exhibit_cik_mismatch",
        })
        return None

    body = cycle._bounded_get(url, _DOCUMENT_CAP)
    if body is None:
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "document_missing",
        })
        return None
    try:
        document_sha256 = hashlib.sha256(body).hexdigest()
        retrieved_at = cycle._clock_now()
        retrieved_at_text = _fmt(retrieved_at)
        receipt_id = "catsec-" + hashlib.sha256(
            f"{url}\n{document_sha256}\n{retrieved_at_text}".encode("utf-8"),
        ).hexdigest()[:40]
        parse_status, figures, figure_outcome = project_release_figures(
            cik=issuer.cik, accession=accession, body_bytes=body,
            manifest=manifest, exhibit_url=url, document_sha256=document_sha256,
        )
        byte_length = len(body)
    finally:
        # D4: SEC document bytes live only inside this frame, never on disk.
        del body
    if parse_status == "binding_digest_mismatch":
        skipped.append({
            "ticker": issuer.ticker, "accession": accession,
            "reason": "binding_digest_mismatch",
        })
        return None
    return {
        "ticker": issuer.ticker,
        "cik": issuer.cik,
        "accession": accession,
        "filing_key": f"{issuer.cik:010d}:{accession}",
        "form": manifest["filing"]["form"],
        "items": _row_items_tokens(manifest["filing"].get("items")),
        "filing_date": filing_date,
        "report_date": manifest["filing"].get("report_date"),
        "acceptance_datetime": _fmt(accepted),
        "exhibit": {
            "exhibit_type": "EX-99.1",
            "source_url": url,
            "document_sha256": document_sha256,
            "byte_length": byte_length,
        },
        "retention": {
            "first_retained_at": retrieved_at_text,
            "first_retained_receipt_id": receipt_id,
            "last_verified_at": retrieved_at_text,
        },
        "figures": [dict(figure) for figure in figures],
        "lineage": {
            "amends_filing_key": amends_filing_key,
            "correction_generation": correction_generation,
        },
        "parse_status": parse_status,
        "figure_outcome": figure_outcome,
    }
