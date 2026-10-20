"""C19 WP31 evaluator — SOURCES module (prereg §1–§3: episodes, cutoff, K, label, A0, leaks).

Governing documents
-------------------
- Preregistration: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``
  (merged as commit ``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c``).  The prereg wins
  any conflict with the build spec; never redesign, never widen.
- Frozen build spec: ``WP31_BUILD_SPEC.md`` (seat stage), sections
  "Shared episode dict" and "Sources (prereg §1–§3)", sha256
  ``5485384ad1f08a0211f634045d23d623d7e4d961924d5b9f5911ea6081149ef1``.

This module implements the SOURCES part of the WP31 evaluator.  The episode
dict produced by :func:`enumerate_episodes` and shaped by :func:`k_from_surface`,
:func:`label_and_a0_from_companyfacts` and :func:`apply_leak_rules` is the sole
interface to the sibling STATS and GATES modules; nothing is imported from them
(lane law R6).

Wave 2 adds the S leg — the event-workspace revision-chain reader
(:func:`parse_fiscal_q`, :func:`previous_fiscal_q`, :func:`s_event_ids`,
:func:`resolve_company_id`, :func:`s_from_revisions`, :func:`s_from_workspace`,
:func:`collect_s_legs`), the EX-99.1 manifest enrichment
(:func:`enrich_exhibits`) and the prior-filings helper
(:func:`prior_filings_from_submissions`).  Every production dependency
(identity registry, revision-chain reader, SGML manifest parser) is imported
lazily inside the function that uses it and is injectable as a parameter, so
importing this module stays light and no test ever touches the production
readers.

Sources mirrored or wrapped, with their repo lines (lane laws R2–R4):
- ``lib/exchange_holidays.py:273 early_close(market, day) -> time | None`` and
  ``lib/us_cash_calendar.py:29 is_session(day)`` (holiday predicate path: announced
  slate with ``lib/nyse_calendar`` fallback for unannounced years) — cutoff law R2.
  The US regular close 16:00 America/New_York mirrors
  ``lib/market_session.py:125`` ``return [(time(9, 30), close or time(16))]``.
- ``collectors/edgar_earnings_8k.py:407 _extract_8k_rows`` — the exact 8-K row keys
  (ticker, cik, accession, form, filing_date, acceptance_datetime, report_date,
  items).  The Item-2.02 exact-token filter mirrors
  ``collectors/edgar_earnings_8k.py:128 tokenize_items`` / ``:151 has_item_202``
  (``ITEM_202 = "2.02"`` at ``:113``); the EX-99.1 type match mirrors
  ``scripts/refresh_event_workspaces.py:99``
  ``_EX99_TYPE = re.compile(r"^EX-99\\.1(?:\\b|$)", re.I)``.
- ``scripts/refresh_event_workspaces.py:1023 fiscal_period_for_report_date`` is
  imported and used directly when the import is clean (verified at BASE); on an
  import failure the helper below is mirrored from ``:998 _fiscal_quarter_end_before``
  and ``:1023 fiscal_period_for_report_date`` verbatim (lane law R3).
- ``engine/k3e_expectation_surface.py:218 inspect_expectation_surface`` (wrapped by
  :func:`k_from_surface`; its refusal type ``QueryRefusal`` at ``:42`` carries
  ``.reason``), called the way ``scripts/query_k3e_expectation_surface.py:150-155``
  calls it.  The default ``CURRENT`` reading of a row's own expectation state
  mirrors ``engine/k3e_expectation_surface.py:499``.

All times are America/New_York via ``zoneinfo``; every returned clock is an
aware UTC datetime or an ISO-8601 UTC string ending in ``Z``.  No I/O at import
time; standard library + numpy/pandas plus the repo libs above only.  No real
EPS / price / return / estimate / consensus / label value for any universe
issuer is read or printed by this module (lane law R1).
"""
from __future__ import annotations

import calendar
import math
import re
from collections import namedtuple
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import pandas as pd

from lib.exchange_holidays import early_close
from lib.us_cash_calendar import is_session
from engine.k3e_expectation_surface import QueryRefusal, inspect_expectation_surface

# --------------------------------------------------------------------------
# Frozen constants (prereg §1 universe; PREREG_COMMIT time per the build spec)
# --------------------------------------------------------------------------

#: issuer -> (cluster key, fiscal-year-end month) — prereg §1 frozen universe.
UNIVERSE: dict[str, tuple[str, int]] = {
    "AAPL": ("AAPL", 9),
    "DHI": ("HOMEBUILDERS", 9),
    "PHM": ("HOMEBUILDERS", 12),
    "KBH": ("HOMEBUILDERS", 11),
    "TOL": ("HOMEBUILDERS", 10),
}

#: Committer time of PREREG_COMMIT (spec "Sources" bullet 2; prereg §1
#: "Eligibility": t_rel strictly after this instant; == False at the instant).
PREREG_COMMIT_TIME: datetime = datetime(2026, 10, 17, 12, 1, 44, tzinfo=timezone.utc)

_ET = ZoneInfo("America/New_York")
#: Regular-session close mirrors ``lib/market_session.py:125`` (`close or time(16)`).
_REGULAR_CLOSE = time(16)
#: Same 30-day walk bound as ``lib/us_cash_calendar.py:36 last_session_on_or_before``.
_MAX_LOOKBACK_DAYS = 30

# K surface query dimensions (prereg §3.1).
_K_METRIC = "EPS"
_K_HORIZON = "0q"
_K_PROVIDER = "yfinance"
_K_RECORD_CLASS = "earnings_estimate"
_K_PERIOD_WINDOW_DAYS = 7

# Label/A0 XBRL reading (prereg §3.2, §3.3, §4 A0 row).
_EPS_CONCEPT = "EarningsPerShareDiluted"
_EPS_UNIT = "USD/shares"
_ORIGINAL_FORMS = frozenset({"10-Q", "10-K"})  # never an amendment (no "/A")
_DURATION_MIN_DAYS = 84
_DURATION_MAX_DAYS = 98
#: q-4 / p-4 comparative window: 4 fiscal quarters (52 weeks = 364 days) +/- 1 week.
_COMPARATIVE_MIN_DAYS = 350
_COMPARATIVE_MAX_DAYS = 378

_EX991_TYPE = re.compile(r"^EX-99\.1(?:\b|$)", re.I)  # mirrored (see docstring)
_ITEM_202 = "2.02"  # collectors/edgar_earnings_8k.py:113

#: Lifecycle states in which a revision's ``source_sha256`` is release-bearing
#: (wave-2 spec §1.4).  Mirrors the vocabulary of
#: ``engine/company_intelligence/events.py`` ``EVENT_STATES`` (lines 43-55
#: there): "complete", "corrected", "derived_ready" and "distributed" carry a
#: published source; "completed_partial" deliberately does not (prereg §2.5: a
#: partial is never silent backing), and neither do "discovered", "scheduled",
#: "rescheduled", "started", "superseded" or "cancelled".
RELEASE_STATES: frozenset[str] = frozenset(
    {"complete", "corrected", "derived_ready", "distributed"}
)

#: Exact fiscal-quarter label law (wave-2 spec §1.2): four digits, uppercase Q.
_FISCAL_Q_RE = re.compile(r"^(\d{4})Q([1-4])$")

# --------------------------------------------------------------------------
# Fiscal-period helper: import the repo one, mirror it if the import fails (R3)
# --------------------------------------------------------------------------

_FiscalPeriod = namedtuple("_FiscalPeriod", "year quarter calendar_end")


def _mirrored_fiscal_quarter_end_before(anchor: date, fiscal_year_end_month: int) -> date:
    """Mirror of ``scripts/refresh_event_workspaces.py:998 _fiscal_quarter_end_before``.

    Quoted source (lines 1013-1020 there)::

        quarter_end_months = sorted({(fiscal_year_end_month - 3 * i - 1) % 12 + 1 for i in range(4)})
        candidates: list[date] = []
        for year in (anchor.year - 1, anchor.year, anchor.year + 1):
            for month in quarter_end_months:
                last_day = calendar.monthrange(year, month)[1]
                candidates.append(date(year, month, last_day))
        before = [candidate for candidate in candidates if candidate < anchor]
    """
    quarter_end_months = sorted(
        {(fiscal_year_end_month - 3 * i - 1) % 12 + 1 for i in range(4)}
    )
    candidates: list[date] = []
    for year in (anchor.year - 1, anchor.year, anchor.year + 1):
        for month in quarter_end_months:
            last_day = calendar.monthrange(year, month)[1]
            candidates.append(date(year, month, last_day))
    before = [candidate for candidate in candidates if candidate < anchor]
    if not before:
        raise ValueError(
            f"no fiscal quarter end precedes anchor date {anchor.isoformat()}"
        )
    return max(before)


def _mirrored_fiscal_period_for_report_date(
    report_date: str, fiscal_year_end_month: int
) -> _FiscalPeriod:
    """Mirror of ``scripts/refresh_event_workspaces.py:1023 fiscal_period_for_report_date``.

    Quoted source (lines 1041-1047 there)::

        anchor = date.fromisoformat(str(report_date))
        quarter_end = _fiscal_quarter_end_before(anchor, fiscal_year_end_month)
        fy_start_month = (fiscal_year_end_month % 12) + 1
        months_elapsed = (quarter_end.month - fy_start_month) % 12
        quarter = months_elapsed // 3 + 1
        fiscal_year = quarter_end.year if quarter_end.month <= fiscal_year_end_month else quarter_end.year + 1
        return FiscalPeriod(year=fiscal_year, quarter=quarter, calendar_end=quarter_end)
    """
    anchor = date.fromisoformat(str(report_date))
    quarter_end = _mirrored_fiscal_quarter_end_before(anchor, fiscal_year_end_month)
    fy_start_month = (fiscal_year_end_month % 12) + 1
    months_elapsed = (quarter_end.month - fy_start_month) % 12
    quarter = months_elapsed // 3 + 1
    fiscal_year = (
        quarter_end.year
        if quarter_end.month <= fiscal_year_end_month
        else quarter_end.year + 1
    )
    return _FiscalPeriod(year=fiscal_year, quarter=quarter, calendar_end=quarter_end)


try:  # pragma: no cover - exercised through whichever branch the host admits
    from scripts.refresh_event_workspaces import (
        fiscal_period_for_report_date as _fiscal_period_for_report_date,
    )

    FISCAL_HELPER_SOURCE = (
        "scripts/refresh_event_workspaces.py:1023 fiscal_period_for_report_date (imported)"
    )
except Exception:  # noqa: BLE001 - any import-time failure flips to the mirror
    _fiscal_period_for_report_date = _mirrored_fiscal_period_for_report_date  # type: assignment[function]
    FISCAL_HELPER_SOURCE = (
        "mirrored from scripts/refresh_event_workspaces.py:998,1023 (import failed)"
    )


# --------------------------------------------------------------------------
# Clock helpers
# --------------------------------------------------------------------------


def _iso_utc(moment: datetime) -> str:
    """ISO-8601 UTC string with an explicit ``Z`` suffix."""
    if moment.tzinfo is None:
        raise ValueError("naive datetime has no UTC representation")
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _aware_utc(moment: datetime, *, label: str) -> datetime:
    if not isinstance(moment, datetime):
        raise TypeError(f"{label} must be a datetime, got {type(moment).__name__}")
    if moment.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware (naive datetimes are refused)")
    return moment.astimezone(timezone.utc)


def _parse_utc(value: Any) -> datetime | None:
    """Parse an ISO clock as UTC; None when absent/malformed (fail closed).

    Generic parser: offset-less strings/datetimes are read as UTC, explicit
    offsets are honoured, unparseable values return None and the caller drops
    or refuses the record — never a guessed clock.  It does NOT correct the
    EDGAR submissions-JSON ``acceptanceDateTime``, whose "…Z" suffix is not true
    UTC (``collectors/edgar_earnings_8k.py`` stores that raw value under an
    "ISO-UTC" label); release times go through
    :func:`_edgar_json_acceptance_utc` (prereg §10 A2).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _edgar_json_acceptance_utc(value: Any) -> datetime | None:
    """True UTC from an EDGAR submissions-JSON ``acceptanceDateTime`` (prereg §10 A2).

    The JSON clock J runs ahead of the true acceptance instant U by the
    America/New_York offset (verified on non-universe MSFT/JPM filings against
    the filing header's ET ``ACCEPTANCE-DATETIME``).  With o = -NY offset at J,
    U = J - o, and the result is kept only when -NY offset at U equals o;
    otherwise the clock is unresolvable and None is returned (fail closed —
    the caller drops the row and prereg §10 A3 applies).  The two offsets can
    disagree only within hours of a DST transition (a weekend night).
    """
    j = _parse_utc(value)
    if j is None:
        return None
    offset = -j.astimezone(_ET).utcoffset()
    u = j - offset
    if -u.astimezone(_ET).utcoffset() != offset:
        return None
    return u


def _parse_day(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


# --------------------------------------------------------------------------
# Cutoff + eligibility (prereg §1 Eligibility, §2 Cutoff)
# --------------------------------------------------------------------------


def cutoff_for(t_rel: datetime) -> datetime:
    """C(e): scheduled close of the last NYSE session ending strictly before t_rel.

    Prereg §2: "the scheduled close (regular or early close, NYSE calendar) of
    the last NYSE session that ends strictly before ``t_rel(e)``".  Sessions and
    full-day closures come from ``lib.us_cash_calendar.is_session`` (announced
    slate + historical fallback); the early-close time comes from
    ``lib.exchange_holidays.early_close("US", day)`` (13:00 local on published
    half days); the regular close is 16:00 local (``lib/market_session.py:125``).
    Local times are converted through ``zoneinfo.ZoneInfo("America/New_York")``
    so the result is correct across the DST boundary.  A release at exactly the
    close instant belongs to the PREVIOUS session's close (strict inequality).
    """
    rel = _aware_utc(t_rel, label="t_rel")
    day = rel.astimezone(_ET).date()
    for _ in range(_MAX_LOOKBACK_DAYS + 1):
        if is_session(day):
            close_local = early_close("US", day) or _REGULAR_CLOSE
            close_utc = datetime.combine(day, close_local, _ET).astimezone(
                timezone.utc
            )
            if close_utc < rel:
                return close_utc
        day -= timedelta(days=1)
    raise ValueError(
        f"no US cash session close strictly before {rel.isoformat()} within "
        f"{_MAX_LOOKBACK_DAYS + 1} days"
    )


def is_eligible(t_rel: datetime) -> bool:
    """True iff t_rel is strictly after PREREG_COMMIT_TIME (prereg §1)."""
    rel = _aware_utc(t_rel, label="t_rel")
    return rel > PREREG_COMMIT_TIME


# --------------------------------------------------------------------------
# Episode enumeration (prereg §1 unit; spec "Sources" bullet 3)
# --------------------------------------------------------------------------


def _has_item_202(raw: str | None) -> bool:
    """Mirror of ``collectors/edgar_earnings_8k.py:151 has_item_202``.

    Exact comma-split token membership of ``"2.02"`` (``:128 tokenize_items``),
    never substring matching, so "12.02" / "2.020" do not match.
    """
    if not raw:
        return False
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    return _ITEM_202 in tokens


def _has_ex991(row: Mapping[str, Any]) -> bool:
    """True iff the row proves an EX-99.1 exhibit is attached.

    ``_extract_8k_rows`` itself carries no exhibit list (the exhibit body is
    only resolvable through the SGML document map, a network read), so
    enumerate_episodes consumes rows enriched with an ``exhibits`` list (of
    type strings or ``{"type": ...}`` mappings) or a boolean ``has_ex_99_1``
    marker; a row without exhibit proof is dropped — fail closed, never a
    silent admit.  The type match mirrors ``scripts/refresh_event_workspaces.py:99``.
    """
    marker = row.get("has_ex_99_1")
    if isinstance(marker, bool):
        return marker
    value = row.get("exhibits")
    if value is None:
        value = row.get("exhibit_types")
    if value is None:
        return False
    if isinstance(value, str):
        candidates: list[Any] = [value]
    elif isinstance(value, (list, tuple)):
        candidates = list(value)
    else:
        return False
    for item in candidates:
        if isinstance(item, Mapping):
            kind = item.get("type") or item.get("name") or ""
        else:
            kind = str(item or "")
        if _EX991_TYPE.match(str(kind).strip()):
            return True
    return False


def _empty_k() -> dict[str, Any]:
    return {
        "average": None,
        "year_ago": None,
        "observed_at": None,
        "expectation_state": None,
        "identity_status": None,
        "rights_class": None,
        "attempt_status": None,
        "period_end": None,
        "abstain_reason": None,
        "record_ids": [],
    }


def _empty_s() -> dict[str, Any]:
    """The empty S leg; every wave-2 key is always present (spec §1.4)."""
    return {
        "q_minus_1_resolved": False,
        "source_sha256": None,
        "generation_id": None,
        "generated_at": None,
        "observed_at": None,
        "lifecycle_state": None,
        "record_ids": [],
        "pit_unrecoverable": False,
        "q_release_before_cutoff": False,
        "reason": None,
    }


def _empty_a0() -> dict[str, Any]:
    return {"sign": None, "period": None, "accession": None, "accepted_at": None}


def enumerate_episodes(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build the skeleton episode dicts for the frozen universe (prereg §1).

    ``rows`` are 8-K dicts shaped like
    ``collectors/edgar_earnings_8k.py:407 _extract_8k_rows`` output
    (keys ticker, cik, accession, form, filing_date, acceptance_datetime,
    report_date, items) plus EX-99.1 exhibit proof (see :func:`_has_ex991` —
    the collector itself carries no exhibit list, so exhibit-less rows are
    dropped fail-closed).  Kept per row: issuer in UNIVERSE, Item 2.02 exact
    token, an EX-99.1 exhibit, a resolvable acceptance clock and a report_date
    anchor.  The clock is the EDGAR submissions-JSON ``acceptanceDateTime``
    corrected to true UTC by :func:`_edgar_json_acceptance_utc` (prereg §10 A2).
    ``(issuer, q, period_end)`` come from the repo fiscal helper
    (``FISCAL_HELPER_SOURCE`` records which path is live).  The FIRST
    qualifying filing per (issuer, q) is kept by acceptance time (prereg §1
    "unit" — first filing carrying the release).  ``status`` is "ELIGIBLE"
    when :func:`is_eligible` (t_rel strictly after the prereg commit instant)
    else "EXPOSED" (smoke-test plumbing only, never counted — prereg §0).

    prereg §10 A3: an in-universe Form 8-K Item 2.02 row for the same
    (issuer, q) that was dropped only for a missing EX-99.1 or an unresolvable
    clock, and that is earlier than the kept filing (or cannot be ordered
    against it), means the kept filing may not be the first release.  An
    ELIGIBLE episode in that position becomes NOT_EVALUABLE with reason
    ``earlier_release_filing_dropped`` — never shifted to a later filing.  A
    dropped row with the kept filing's own accession is the same filing and is
    ignored.  Limits: a key with only dropped rows mints no episode, and a row
    without a report_date cannot be attributed to a quarter.

    Output is ordered by (t_rel, issuer, q); every key of the shared episode
    dict is initialized (``returns`` stays absent — it is written by the
    cost-descriptive stage).
    """
    best: dict[tuple[str, str], dict[str, Any]] = {}
    shadows: dict[tuple[str, str], list[tuple[str, datetime | None]]] = {}
    for row in rows or ():
        if not isinstance(row, Mapping):
            continue
        issuer = str(row.get("ticker") or "").strip().upper()
        if issuer not in UNIVERSE:
            continue
        form = str(row.get("form") or "").strip()
        # prereg §2 names "Form 8-K"; an 8-K/A amendment is not the first release.
        if form != "8-K":
            continue
        if not _has_item_202(row.get("items")):
            continue
        report_date = str(row.get("report_date") or "").strip()
        if not report_date:
            continue
        cluster, fye_month = UNIVERSE[issuer]
        try:
            fiscal = _fiscal_period_for_report_date(report_date, fye_month)
        except Exception:  # noqa: BLE001 - an unanchored row cannot mint an episode
            continue
        q = f"{fiscal.year}Q{fiscal.quarter}"
        period_end = fiscal.calendar_end.isoformat()
        key = (issuer, q)
        accession = str(row.get("accession") or "").strip()
        t_rel = _edgar_json_acceptance_utc(row.get("acceptance_datetime"))
        if t_rel is None or not _has_ex991(row):
            # dropped, but it may be the true first release (prereg §10 A3)
            shadows.setdefault(key, []).append((accession, t_rel))
            continue
        current = best.get(key)
        if current is not None and current["_t_rel"] <= t_rel:
            continue  # keep the FIRST qualifying filing by acceptance time
        best[key] = {
            "issuer": issuer,
            "cluster": cluster,
            "q": q,
            "period_end": period_end,
            "t_rel": _iso_utc(t_rel),
            "cutoff": _iso_utc(cutoff_for(t_rel)),
            "status": "ELIGIBLE" if is_eligible(t_rel) else "EXPOSED",
            "not_evaluable_reason": None,
            "label": None,
            "k": _empty_k(),
            "s": _empty_s(),
            "a0": _empty_a0(),
            "_t_rel": t_rel,
            "_accession": accession,
        }
    for key, episode in best.items():
        if episode["status"] != "ELIGIBLE":
            continue  # EXPOSED is never counted; its status stays as is
        for accession, moment in shadows.get(key, ()):
            if accession and accession == episode["_accession"]:
                continue  # the kept filing itself
            if moment is None or moment <= episode["_t_rel"]:
                episode["status"] = "NOT_EVALUABLE"
                episode["not_evaluable_reason"] = "earlier_release_filing_dropped"
                break
    episodes = sorted(
        best.values(), key=lambda e: (e["_t_rel"], e["issuer"], e["q"])
    )
    for episode in episodes:
        episode.pop("_t_rel")
        episode.pop("_accession")
    return list(episodes)


# --------------------------------------------------------------------------
# K from the expectation surface (prereg §3.1; spec "Sources" bullet 5)
# --------------------------------------------------------------------------


def _as_record_rows(value: Any) -> list[dict[str, Any]]:
    """DataFrame or row mappings -> list of plain dict rows (nulls restored)."""
    if value is None:
        return []
    if isinstance(value, pd.DataFrame):
        # Same nan->None discipline as scripts/query_k3e_expectation_surface.py:81.
        return (
            value.astype(object).where(pd.notna(value), None).to_dict("records")
        )
    if isinstance(value, (list, tuple)):
        return [dict(row) for row in value if isinstance(row, Mapping)]
    if isinstance(value, Mapping):
        return [dict(value)]
    return []


def k_from_surface(
    observations: Any,
    attempts: Any,
    *,
    cutoff: datetime,
    period_end: Any,
    **provenance: Any,
) -> dict[str, Any]:
    """Read the episode ``k`` sub-dict from the k3e expectation surface.

    Wraps ``engine.k3e_expectation_surface.py:218 inspect_expectation_surface``
    (called the way ``scripts/query_k3e_expectation_surface.py`` calls it) with
    metric "EPS", horizon_label_raw "0q", provider "yfinance",
    provider_record_class "earnings_estimate" (prereg §3.1).

    Keyword-only provenance (all forwarded through the wrapped engine):
      - ``source_provenance``: the full engine envelope
        ``{"source_revision": "<40hex>", "inputs": {<observations path>:
        {"sha256": "<64hex>", "git_blob_id": "<40hex>"}, <attempts path>: ...}}``;
        if omitted, the remaining kwargs are treated as that mapping.
      - ``identity_aliases``: optional alias rows (else the engine reports
        identity gate status "NOT_CHECKED").
      - ``ticker``: optional issuer; otherwise derived from the single distinct
        ``ticker_compat`` of matching EPS/0q/yfinance rows (empty -> the engine
        refuses INVALID_QUERY_DIMENSIONS, mirrored as an abstain reason).

    Selection (prereg §2.1, §3.1, fail-closed): only rows with
    ``system_observed_at <= cutoff`` are ever read (a record observed after
    cutoff is never a feature; rows after cutoff are ignored); among them the
    newest ``provider_payload_hash`` group (max system_observed_at) wins; an
    equal-clock tie abstains (no value is consumed).  The group's ``period_end``
    must sit within 7 calendar days of the episode quarter end — a null or
    different period end is ``abstain_reason="period_mismatch"`` and no value
    is emitted.  A ``QueryRefusal`` from the engine (or its refusal type) is
    reported as ``abstain_reason="query_refusal:<code>"``.  When no qualifying
    group exists, every value is None with ``abstain_reason=None`` — the STATS
    lane then ABSTAINs "k_missing" (never a silent partial, prereg §2.5).
    ``expectation_state`` comes from the engine's cutoff-visible public state
    when the chosen group is also the engine's latest captured snapshot,
    otherwise from the chosen "average" row's own state field (default
    "CURRENT", mirroring ``engine/k3e_expectation_surface.py:499``).
    ``record_ids`` are the observation ids actually consumed (average, year_ago)
    — the STATS lane's manifest.  ``rights_class`` labels BOTH consumed rows
    (prereg §10 A1): each row's label is upper-cased with None/empty read as
    "UNKNOWN" (the producer's labeled absence); one shared label is returned
    as is, two different labels as ``"MIXED:<a>,<b>"`` (sorted), which the
    stats allow-list blocks.  With neither row present it is None — A1 then
    cannot emit, so the K-backed gate is already closed.
    """
    k = _empty_k()
    cutoff_utc = _aware_utc(cutoff, label="cutoff")
    rest = dict(provenance)
    aliases = rest.pop("identity_aliases", None)
    forced_ticker = rest.pop("ticker", None)
    source_provenance = rest.pop("source_provenance", None)
    if source_provenance is None:
        source_provenance = rest

    obs = _as_record_rows(observations)
    att = _as_record_rows(attempts)

    matching = {
        row.get("ticker_compat")
        for row in obs
        if row.get("metric") == _K_METRIC
        and row.get("horizon_label_raw") == _K_HORIZON
        and row.get("provider") == _K_PROVIDER
    }
    matching.discard(None)
    if isinstance(forced_ticker, str) and forced_ticker:
        ticker: str = forced_ticker
    elif len(matching) == 1:
        ticker = str(next(iter(matching)))
    else:
        ticker = ""  # engine refuses -> query_refusal:INVALID_QUERY_DIMENSIONS

    try:
        result = inspect_expectation_surface(
            obs,
            att,
            source_provenance=source_provenance,
            ticker=ticker,
            metric=_K_METRIC,
            horizon=_K_HORIZON,
            as_of=_iso_utc(cutoff_utc),
            provider=_K_PROVIDER,
            identity_aliases=aliases,
        )
    except QueryRefusal as refusal:
        k["abstain_reason"] = f"query_refusal:{refusal.reason}"
        return k

    payload = result.get("semantic_payload") or {}
    gate = payload.get("identity_gate") or {}
    k["identity_status"] = gate.get("status")

    groups: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}
    for row in obs:
        if row.get("provider") != _K_PROVIDER:
            continue
        if row.get("ticker_compat") != ticker:
            continue
        if row.get("metric") != _K_METRIC:
            continue
        if row.get("horizon_label_raw") != _K_HORIZON:
            continue
        if row.get("provider_record_class") != _K_RECORD_CLASS:
            continue
        clock = _parse_utc(row.get("system_observed_at"))
        if clock is None or clock > cutoff_utc:
            continue  # PIT law: never read a record observed after cutoff
        group_hash = row.get("provider_payload_hash")
        if not isinstance(group_hash, str) or not group_hash:
            continue
        groups.setdefault(group_hash, []).append((clock, row))
    if not groups:
        return k  # all-None, no reason -> STATS ABSTAIN("k_missing")

    group_clock = {
        group_hash: max(clock for clock, _ in members)
        for group_hash, members in groups.items()
    }
    newest = max(group_clock.values())
    tied = [
        group_hash for group_hash, clock in group_clock.items() if clock == newest
    ]
    if len(tied) != 1:
        return k  # equal-clock tie fails closed, consuming nothing
    group_hash = tied[0]
    rows = [row for _clock, row in groups[group_hash]]
    k["observed_at"] = _iso_utc(newest)

    by_type: dict[str, dict[str, Any]] = {}
    for row in rows:
        observation_type = str(row.get("observation_type") or "")
        if observation_type in ("average", "year_ago"):
            by_type.setdefault(observation_type, row)

    period_row = by_type.get("average") or by_type.get("year_ago") or rows[0]
    group_period = _parse_day(period_row.get("period_end"))
    episode_period = _parse_day(period_end)
    k["period_end"] = group_period.isoformat() if group_period else None
    if (
        group_period is None
        or episode_period is None
        or abs((group_period - episode_period).days) > _K_PERIOD_WINDOW_DAYS
    ):
        k["abstain_reason"] = "period_mismatch"
        return k  # fail closed: no value is consumed for a mismatched quarter

    for field, observation_type in (("average", "average"), ("year_ago", "year_ago")):
        row = by_type.get(observation_type)
        if row is not None and _number(row.get("value")) and row.get(
            "missingness_reason"
        ) is None:
            k[field] = float(row["value"])
        if row is not None and row.get("observation_id"):
            k["record_ids"].append(str(row["observation_id"]))

    consumed = [
        row for row in (by_type.get("average"), by_type.get("year_ago")) if row is not None
    ]
    labels = sorted(
        {
            str(row.get("rights_class") or "UNKNOWN").strip().upper() or "UNKNOWN"
            for row in consumed
        }
    )
    if not labels:
        k["rights_class"] = None
    elif len(labels) == 1:
        k["rights_class"] = labels[0]
    else:
        k["rights_class"] = "MIXED:" + ",".join(labels)

    latest = payload.get("latest_captured_snapshot") or {}
    latest_snapshot = latest.get("snapshot") if latest.get("status") == "AVAILABLE" else None
    latest_identity = (latest_snapshot or {}).get("identity") or {}
    if latest_identity.get("provider_payload_hash") == group_hash:
        k["expectation_state"] = (latest_snapshot or {}).get("expectation_state")
        k["attempt_status"] = (latest_snapshot or {}).get("attempt_status")
    else:
        k["expectation_state"] = (
            (average_row.get("expectation_state") or "CURRENT")
            if average_row is not None
            else None
        )
        attempt_ids = {row.get("attempt_id") for row in rows}
        attempt_ids.discard(None)
        attempt_status = None
        if len(attempt_ids) == 1:
            linked = [
                row for row in att if row.get("attempt_id") in attempt_ids
            ]
            if len(linked) == 1:
                attempt_status = linked[0].get("status")
        k["attempt_status"] = attempt_status
    return k


# --------------------------------------------------------------------------
# Label + A0 from companyfacts (prereg §3.2, §3.3, §4 A0; spec bullet 6)
# --------------------------------------------------------------------------


def _quarterly_eps_filings(facts_json: Any) -> dict[str, dict[date, float]]:
    """accn -> {period end: diluted EPS} over original-filing quarterly facts.

    Rows obey prereg §3.2/§3.3: concept us-gaap:EarningsPerShareDiluted, unit
    "USD/shares", duration 84-98 days inclusive, no segment/dimension, form in
    {"10-Q","10-K"} exactly (a "10-Q/A"/"10-K/A" amendment row is never an
    original filing).  A filing whose same period end carries more than one
    distinct value is ambiguous and is dropped fail-closed.
    """
    units = (
        ((facts_json or {}).get("facts") or {})
        .get("us-gaap", {})
        .get(_EPS_CONCEPT, {})
        .get("units", {})
        .get(_EPS_UNIT)
    )
    if not isinstance(units, list):
        return {}
    raw: dict[str, dict[date, set[float]]] = {}
    for row in units:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("form") or "") not in _ORIGINAL_FORMS:
            continue
        segment = row.get("segment")
        if segment not in (None, "", {}, []):
            continue  # dimensional contexts are never accepted (prereg §3.2)
        start = _parse_day(row.get("start"))
        end = _parse_day(row.get("end"))
        if start is None or end is None:
            continue
        duration_days = (end - start).days
        if not (_DURATION_MIN_DAYS <= duration_days <= _DURATION_MAX_DAYS):
            continue
        if not _number(row.get("val")):
            continue
        accession = str(row.get("accn") or "").strip()
        if not accession:
            continue
        raw.setdefault(accession, {}).setdefault(end, set()).add(float(row["val"]))
    filings: dict[str, dict[date, float]] = {}
    for accession, ends in raw.items():
        if any(len(values) != 1 for values in ends.values()):
            continue  # ambiguous duplicate context -> fail closed, drop the filing
        filings[accession] = {end: next(iter(values)) for end, values in ends.items()}
    return filings


def _comparative(ends: dict[date, float], primary: date) -> date | None:
    """The q-4 / p-4 comparative end inside one filing, located by period end.

    The original 10-Q/10-K carries the current three-month context and the
    same-fiscal-quarter-last-year context; the comparative end is the one
    350-378 days (4 fiscal quarters ~ 52 weeks, +/- 1 week) before *primary*.
    """
    best: date | None = None
    best_gap: int | None = None
    for end in ends:
        if end >= primary:
            continue
        gap = (primary - end).days
        if _COMPARATIVE_MIN_DAYS <= gap <= _COMPARATIVE_MAX_DAYS:
            distance = abs(gap - 364)
            if best_gap is None or distance < best_gap:
                best, best_gap = end, distance
    return best


def _sign(difference: float) -> int | None:
    if difference > 0:
        return 1
    if difference < 0:
        return -1
    return 0  # exact tie — callers map it per the prereg rule


def label_and_a0_from_companyfacts(
    facts_json: Any,
    q_period_end: Any,
    q_accession: str,
    cutoff: datetime,
    prior_filings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Label Y(e) and arm A0 from the issuer's companyfacts JSON (prereg §3.3, §4).

    Locating prior quarters **by period end dates** (lane law R5): every
    quarterly fact end date seen in the original-filing rows orders the fiscal
    calendar.  ``q-4`` (label) and ``p-4`` (A0) are the comparative period in
    the SAME original filing, 350-378 days before the primary end.  For A0,
    ``q-1`` is the latest quarterly period end strictly before ``q_period_end``
    and ``q-2`` the next earlier one, among all end dates present; each
    candidate's ORIGINAL filing is the filing whose latest own end is that
    period (never an amendment, never ``q_accession``).

    Label = ``sign(EPS(q) - EPS(q-4))`` with BOTH values taken from q's own
    original filing (accn == ``q_accession``); equal -> ``label=None`` +
    ``not_evaluable_reason="label_tie"`` (prereg §3.3); an absent value ->
    ``label=None`` with ``not_evaluable_reason=None`` (the caller decides
    ``label_unavailable`` after 120 days).

    A0 = the same sign rule for the most recent ``p`` in {q-1, q-2} whose
    original filing (BOTH contexts present) was accepted <= ``cutoff``
    (prereg §2.1 point-in-time: acceptance timestamps come from
    ``prior_filings``, rows ``{"accession", "accepted_at", ...}``; an unknown
    accession or timestamp fails closed).  None available -> ``a0["sign"]=None``
    (the STATS lane ABSTAINs "no_prior_filing").  ``accepted_at`` is read as
    given (:func:`_parse_utc`), deliberately NOT through the EDGAR-JSON
    correction (prereg §10 A2): a raw submissions-JSON value runs late by the
    NY offset, which can only exclude a filing accepted within those hours
    before ``cutoff`` — never admit one accepted after it.

    All clocks are aware UTC; ``cutoff`` refuses naive datetimes.
    """
    cutoff_utc = _aware_utc(cutoff, label="cutoff")
    episode_end = _parse_day(q_period_end)
    q_accession = str(q_accession or "").strip()
    filings = _quarterly_eps_filings(facts_json)

    label: int | None = None
    not_evaluable_reason: str | None = None
    q_filing = filings.get(q_accession) or {}
    if episode_end is not None and q_filing:
        current_value = q_filing.get(episode_end)
        comparative_end = _comparative(q_filing, episode_end)
        if current_value is not None and comparative_end is not None:
            prior_value = q_filing[comparative_end]
            direction = _sign(current_value - prior_value)
            if direction == 0:
                not_evaluable_reason = "label_tie"
            else:
                label = direction

    accepted_at: dict[str, datetime] = {}
    for entry in prior_filings or ():
        if not isinstance(entry, Mapping):
            continue
        accession = str(entry.get("accession") or "").strip()
        moment = _parse_utc(entry.get("accepted_at"))
        if accession and moment is not None:
            accepted_at.setdefault(accession, moment)

    prior_ends = sorted(
        {
            end
            for filing in filings.values()
            for end in filing
            if episode_end is None or end < episode_end
        },
        reverse=True,
    )
    candidates = prior_ends[:2]  # q-1, q-2 located by period end date

    a0 = _empty_a0()
    for candidate_end in candidates:
        for accession, filing in filings.items():
            if accession == q_accession or max(filing) != candidate_end:
                continue  # not the ORIGINAL filing for that period
            current_value = filing.get(candidate_end)
            comparative_end = _comparative(filing, candidate_end)
            if current_value is None or comparative_end is None:
                continue  # both contexts are required (prereg §4 A0 row)
            moment = accepted_at.get(accession)
            if moment is None or moment > cutoff_utc:
                continue  # PIT fail-closed: accepted after cutoff or unknowable
            direction = _sign(current_value - filing[comparative_end])
            if direction == 0:
                continue  # an equal-prior tie emits nothing for A0
            a0 = {
                "sign": direction,
                "period": candidate_end.isoformat(),
                "accession": accession,
                "accepted_at": _iso_utc(moment),
            }
            break
        if a0["sign"] is not None:
            break  # most recent qualifying p wins; else fall through to None
    return {"label": label, "not_evaluable_reason": not_evaluable_reason, "a0": a0}


# --------------------------------------------------------------------------
# Leakage rules (prereg §2.1-§2.3; spec "Sources" leak bullet)
# --------------------------------------------------------------------------


def apply_leak_rules(ep: dict[str, Any]) -> dict[str, Any]:
    """Enforce the fail-closed leakage rules over one episode (returns a copy).

    Prereg §2.1 (point-in-time reads only): any K or S record whose
    observed/accepted clock is after the episode cutoff marks the episode
    ``NOT_EVALUABLE`` with reason ``"pre_cutoff_leak"`` — the K record clock is
    ``k["observed_at"]``, the SEC-leg clocks are ``a0["accepted_at"]`` and the
    S leg's ``generated_at``/``observed_at``, both supplied by the wave-2
    reader :func:`s_from_revisions`.
    Prereg §2.2/§2.4 (the q release is never a feature; pre-cutoff disclosure):
    an S leg with ``s["q_release_before_cutoff"] is True`` — some release-bearing
    ``q`` revision disclosed at or before the cutoff — is likewise a
    ``pre_cutoff_leak``.  The check runs with the other pre-cutoff checks,
    before ``pit_unrecoverable``.
    Prereg §2.3 (unrecoverable history is not guessed): a caller that cannot
    reconstruct the version that existed at the cutoff marks the episode by
    setting ``ep["pit_unrecoverable"] = True`` (top level or inside ``s``) and
    this function maps it to ``NOT_EVALUABLE`` with reason
    ``"pit_unrecoverable"``.  ``pre_cutoff_leak`` is checked first.  Episodes
    that are not ELIGIBLE (EXPOSED smoke rows, already-NOT_EVALUABLE rows)
    are returned unchanged — a leak never upgrades a status.
    """
    out = dict(ep)
    if out.get("status") != "ELIGIBLE":
        return out
    cutoff = _parse_utc(out.get("cutoff"))

    def _after_cutoff(value: Any) -> bool:
        moment = _parse_utc(value)
        return moment is not None and cutoff is not None and moment > cutoff

    k_leg = out.get("k") or {}
    s_leg = out.get("s") or {}
    a0_leg = out.get("a0") or {}
    if (
        _after_cutoff(k_leg.get("observed_at"))
        or _after_cutoff(a0_leg.get("accepted_at"))
        or _after_cutoff(s_leg.get("generated_at"))
        or _after_cutoff(s_leg.get("observed_at"))
        or s_leg.get("q_release_before_cutoff") is True
    ):
        out["status"] = "NOT_EVALUABLE"
        out["not_evaluable_reason"] = "pre_cutoff_leak"
        return out
    if out.get("pit_unrecoverable") or s_leg.get("pit_unrecoverable"):
        out["status"] = "NOT_EVALUABLE"
        out["not_evaluable_reason"] = "pit_unrecoverable"
        return out
    return out


# --------------------------------------------------------------------------
# S reader — fiscal-quarter helpers (wave-2 spec §1.2)
# --------------------------------------------------------------------------


def parse_fiscal_q(q: str) -> tuple[int, int]:
    """``"2026Q3"`` -> ``(2026, 3)``; anything else raises ``ValueError``.

    Exact ``^(\\d{4})Q([1-4])$`` on the upper-cased-``Q`` label — the same
    fiscal label the episode dict carries (``enumerate_episodes`` writes
    ``f"{fiscal.year}Q{fiscal.quarter}"``).  Lowercase ``q``, a missing quarter
    ("2026FY"), a 5th quarter or a non-string all refuse.
    """
    match = _FISCAL_Q_RE.fullmatch(q) if isinstance(q, str) else None
    if match is None:
        raise ValueError(f"not a fiscal quarter label: {q!r}")
    return int(match.group(1)), int(match.group(2))


def previous_fiscal_q(q: str) -> str:
    """The fiscal quarter immediately before ``q``: "2026Q1" -> "2025Q4"."""
    year, quarter = parse_fiscal_q(q)
    if quarter == 1:
        return f"{year - 1}Q4"
    return f"{year}Q{quarter - 1}"


def s_event_ids(company_id: str, q: str) -> tuple[str, str]:
    """``(q-1 event id, q event id)`` for one episode's SEC legs.

    Each id is ``canonical_event_id(company_id, FiscalPeriod(year=Y,
    quarter=N))`` with the default ``event_type="earnings_results"``
    (``engine/company_intelligence/events.py:182``; lazily imported so this
    module stays light).  ``calendar_end`` is not part of the canonical id and
    is deliberately left unset.  A malformed ``q`` raises ``ValueError``.
    """
    from engine.company_intelligence.events import FiscalPeriod, canonical_event_id

    q_year, q_quarter = parse_fiscal_q(q)
    qm1_year, qm1_quarter = parse_fiscal_q(previous_fiscal_q(q))
    qm1_id = canonical_event_id(
        company_id, FiscalPeriod(year=qm1_year, quarter=qm1_quarter)
    )
    q_id = canonical_event_id(company_id, FiscalPeriod(year=q_year, quarter=q_quarter))
    return qm1_id, q_id


# --------------------------------------------------------------------------
# S reader — identity (wave-2 spec §1.3)
# --------------------------------------------------------------------------


def resolve_company_id(
    issuer: str, cutoff: datetime, *, resolve_ticker: Any = None
) -> str | None:
    """The issuer's ``company_id`` as of the cutoff, or ``None`` (fail closed).

    The default resolver is bound lazily as
    ``production_registry().resolve_ticker``
    (``engine/company_intelligence/event_workspace.py:228``); the call is
    ``resolve_ticker(issuer, asof=cutoff_utc.date())`` and a truthy
    ``result.company_id`` is returned as a str.  ``None`` — the registry's
    typed absence — an ``IdentityError`` (or any other exception: a resolver
    bug must never crash the read) all map to ``None``.
    """
    if resolve_ticker is None:
        from engine.company_intelligence.event_workspace import production_registry

        resolve_ticker = production_registry().resolve_ticker
    cutoff_utc = _aware_utc(cutoff, label="cutoff")
    try:
        result = resolve_ticker(issuer, asof=cutoff_utc.date())
    except Exception:  # noqa: BLE001 - fail closed, never crash the read
        return None
    if result is None:
        return None
    company_id = getattr(result, "company_id", None)
    if not isinstance(company_id, str) or not company_id:
        return None
    return company_id


# --------------------------------------------------------------------------
# S reader — the pure selection function (wave-2 spec §1.4)
# --------------------------------------------------------------------------


def _revision_clock(rev: Mapping[str, Any]) -> tuple[datetime | None, datetime | None]:
    """(generated_at, observed_at) parsed as UTC; (None, None) when unshaped.

    ``workspace.generated_at`` is the system clock of the workspace version;
    ``observed_at`` is the revision's own system observation clock.  Both are
    true UTC (prereg §2.1's clocks) and are parsed with :func:`_parse_utc` —
    they are NOT submissions-JSON values and never go through the A2
    correction.
    """
    if not isinstance(rev, Mapping):
        return None, None
    workspace = rev.get("workspace")
    generated_at = (
        _parse_utc(workspace.get("generated_at"))
        if isinstance(workspace, Mapping)
        else None
    )
    return generated_at, _parse_utc(rev.get("observed_at"))


def _release_bearing(rev: Mapping[str, Any]) -> bool:
    """A non-empty str ``source_sha256`` AND ``lifecycle_state`` release-bearing."""
    sha = rev.get("source_sha256")
    if not isinstance(sha, str) or not sha:
        return False
    return rev.get("lifecycle_state") in RELEASE_STATES


def s_from_revisions(
    qm1_revisions: Any, q_revisions: Any, cutoff: datetime
) -> dict[str, Any]:
    """The S leg from the verified revision chains (prereg §2.1, §2.3, §2.2).

    ``qm1_revisions`` / ``q_revisions`` are the oldest-first revision lists
    ``read_all_event_source_revisions`` returns for the q-1 and q events (each
    receipt: ``generation_id``, ``source_sha256``, ``source_available_at``,
    ``observed_at``, ``lifecycle_state``, ``workspace_receipt`` =
    ``{"sha256", "bytes"}``, and a ``workspace`` body carrying
    ``generated_at``).  ``cutoff`` must be aware UTC.

    q-1 selection (prereg §2.1/§2.3):
      1. Every q-1 revision's ``workspace.generated_at`` and ``observed_at``
         are parsed.  ANY unparseable ``generated_at`` (any revision, not only
         release-bearing ones) means the chain cannot be ordered against
         ``C(e)``: ``pit_unrecoverable=True``, reason
         ``"revision_time_unparseable"``, and the selection stops — the
         version that existed at the cutoff is not guessed (prereg §2.3).
      2. Candidates are revisions with ``generated_at <= C``; a revision with
         a parseable ``observed_at > C`` is excluded (observed too late to be
         a feature input); a missing ``observed_at`` does not disqualify —
         ``generated_at`` is the prereg's clock.
      3. No candidates -> ABSTAIN, reason ``"qm1_not_published_by_cutoff"``,
         ``pit_unrecoverable=False``: the chain was walked to its root, so the
         absence is real absence.
      4. The newest candidate (last in oldest-first order) is the version that
         existed at ``C``.  The reader dedupes carry-forward hops and keeps the
         generation that introduced each ``source_sha256``, so the
         newest-candidate IS the as-of-C view and a correction introduced
         after ``C`` is never selected — prereg §2.1's last sentence.
      5. A non-release-bearing newest candidate abstains — reason
         ``"qm1_sha_missing"`` when its ``source_sha256`` is empty or not a
         str, else ``"qm1_not_released"`` (a ``completed_partial`` partial is
         never silent backing, prereg §2.5) — with NO fallback to an older
         candidate: an older version is not the as-of-C view.
      6. Otherwise resolved: sha, generation, lifecycle state, ISO-UTC clocks
         (``observed_at`` may be None) and
         ``record_ids=[workspace_receipt.sha256]`` (else ``[]``).

    q-release check (prereg §2.2/§2.4), computed over ``q_revisions``
    regardless of the q-1 outcome: a release-bearing q revision is a
    pre-cutoff disclosure when ANY of its ``workspace.generated_at``, its
    ``observed_at``, or its corrected source clock
    :func:`_edgar_json_acceptance_utc` (the submissions-JSON
    ``acceptanceDateTime``, stored unconverted — prereg §10 A2) is
    ``<= C``; any such revision sets ``q_release_before_cutoff=True``.  A
    release-bearing q revision whose source clock is missing, unparseable or
    uncorrectable and that no system clock already flagged sets
    ``pit_unrecoverable=True`` with reason ``"q_release_time_unresolved"`` —
    unless a q-1 reason was set first; the first reason wins.
    NOTHING else is copied from the q revisions: the q release is never a
    feature (prereg §2.2).
    """
    cutoff_utc = _aware_utc(cutoff, label="cutoff")
    s = _empty_s()

    # --- q-1 selection -----------------------------------------------------
    qm1_parsed: list[tuple[datetime, datetime | None, Mapping[str, Any]]] = []
    time_unparseable = False
    for rev in qm1_revisions or ():
        generated_at, observed_at = _revision_clock(rev)
        if generated_at is None:
            time_unparseable = True
            break
        qm1_parsed.append((generated_at, observed_at, rev))  # type: ignore[arg-type]
    if time_unparseable:
        s["pit_unrecoverable"] = True
        s["reason"] = "revision_time_unparseable"
    else:
        candidates = [
            (generated_at, observed_at, rev)
            for generated_at, observed_at, rev in qm1_parsed
            if generated_at <= cutoff_utc
            and (observed_at is None or observed_at <= cutoff_utc)
        ]
        if not candidates:
            s["reason"] = "qm1_not_published_by_cutoff"
        else:
            generated_at, observed_at, selected = candidates[-1]
            if not _release_bearing(selected):
                sha = selected.get("source_sha256")
                if not isinstance(sha, str) or not sha:
                    s["reason"] = "qm1_sha_missing"
                else:
                    s["reason"] = "qm1_not_released"
            else:
                receipt = selected.get("workspace_receipt")
                receipt_sha = (
                    receipt.get("sha256") if isinstance(receipt, Mapping) else None
                )
                s.update(
                    {
                        "q_minus_1_resolved": True,
                        "source_sha256": selected.get("source_sha256"),
                        "generation_id": (
                            selected.get("generation_id")
                            if isinstance(selected.get("generation_id"), str)
                            else None
                        ),
                        "lifecycle_state": selected.get("lifecycle_state"),
                        "generated_at": _iso_utc(generated_at),
                        "observed_at": (
                            _iso_utc(observed_at) if observed_at is not None else None
                        ),
                        "record_ids": (
                            [receipt_sha]
                            if isinstance(receipt_sha, str) and receipt_sha
                            else []
                        ),
                        "reason": None,
                    }
                )

    # --- q-release check (prereg §2.2/§2.4) — always computed --------------
    for rev in q_revisions or ():
        if not isinstance(rev, Mapping) or not _release_bearing(rev):
            continue
        generated_at, observed_at = _revision_clock(rev)
        source_at = _edgar_json_acceptance_utc(rev.get("source_available_at"))
        if (
            (generated_at is not None and generated_at <= cutoff_utc)
            or (observed_at is not None and observed_at <= cutoff_utc)
            or (source_at is not None and source_at <= cutoff_utc)
        ):
            s["q_release_before_cutoff"] = True
        elif source_at is None:
            s["pit_unrecoverable"] = True
            if s["reason"] is None:  # the first reason wins (spec §1.4)
                s["reason"] = "q_release_time_unresolved"
    return s


# --------------------------------------------------------------------------
# S reader — the reading wrapper (wave-2 spec §1.5)
# --------------------------------------------------------------------------


def s_from_workspace(
    issuer: str,
    q: str,
    cutoff: datetime,
    *,
    resolve_ticker: Any = None,
    revisions_reader: Any = None,
    revisions: Any = None,
    max_hops: int = 500,
) -> dict[str, Any]:
    """One episode's S leg, read through the verified predecessor chain.

    WHY THE CHAIN, NOT ``read_current_event_workspace``: prereg §2.1 reads
    "event-workspace versions with ``generated_at <= C(e)``" and §2.3 makes a
    version that "cannot be recovered (overwritten without history)"
    ``pit_unrecoverable``.  ``read_current_event_workspace`` returns only the
    newest version.  By evaluation time that version has been generated from
    the ``q`` release, which lands after ``C(e)``.  The verified predecessor
    chain IS the history §2.3 refers to, so the evaluator recovers the version
    as of ``C(e)`` from ``read_all_event_source_revisions``.  This is how
    §2.1/§2.3 are carried out; it is not a change to the S source.

    Steps: identity (§1.3; ``None`` -> ``pit_unrecoverable``,
    ``"identity_unresolved"``) -> event ids (a malformed ``q`` ->
    ``"fiscal_q_unparseable"``) -> revisions (an injected ``revisions`` mapping
    event_id -> list is used as given, skipping the reader; otherwise ONE
    ``revisions_reader([qm1_id, q_id], max_hops=max_hops)`` call, the reader
    bound lazily as ``read_all_event_source_revisions``; ANY exception —
    ``WorkspaceChainIntegrityError``, ``WorkspaceChainNotPublished``, the
    hop-bound refusal, anything else — -> ``"chain_unreadable"``) ->
    :func:`s_from_revisions`.  Every failure is an unrecoverable dict:
    ``_empty_s()`` plus ``pit_unrecoverable=True`` and the named reason.
    """
    company_id = resolve_company_id(issuer, cutoff, resolve_ticker=resolve_ticker)
    if company_id is None:
        s = _empty_s()
        s["pit_unrecoverable"] = True
        s["reason"] = "identity_unresolved"
        return s
    try:
        qm1_id, q_id = s_event_ids(company_id, q)
    except ValueError:
        s = _empty_s()
        s["pit_unrecoverable"] = True
        s["reason"] = "fiscal_q_unparseable"
        return s
    if revisions is None:
        if revisions_reader is None:
            from engine.neuralweb.company_intelligence_reader import (
                read_all_event_source_revisions,
            )

            revisions_reader = read_all_event_source_revisions
        try:
            revisions = revisions_reader([qm1_id, q_id], max_hops=max_hops)
        except Exception:  # noqa: BLE001 - any chain failure refuses the leg
            s = _empty_s()
            s["pit_unrecoverable"] = True
            s["reason"] = "chain_unreadable"
            return s
    return s_from_revisions(revisions.get(qm1_id, []), revisions.get(q_id, []), cutoff)


# --------------------------------------------------------------------------
# S reader — the batched reader (wave-2 spec §1.6)
# --------------------------------------------------------------------------


def _unrecoverable_s(reason: str) -> dict[str, Any]:
    s = _empty_s()
    s["pit_unrecoverable"] = True
    s["reason"] = reason
    return s


def collect_s_legs(
    episodes: Any,
    *,
    resolve_ticker: Any = None,
    revisions_reader: Any = None,
    max_hops: int = 500,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Every episode's S leg from EXACTLY ONE revisions-reader call.

    Keyed ``(issuer, q)``.  Identity is resolved for every episode first, then
    ONE ``revisions_reader(all_ids, max_hops=max_hops)`` call covers the union
    of every episode's two event ids.  The chain walk is O(hops) per call and
    measured ~153 s in production (reader docstring, 2026-08-23), so one call
    per episode is forbidden.  Each leg is then built through
    :func:`s_from_workspace` with the shared revision map, so identity
    failures (``"identity_unresolved"``) and a reader exception (every episode
    that needed the map becomes ``"chain_unreadable"``) map exactly as in
    :func:`s_from_workspace`.  Episodes whose status is not ELIGIBLE still get
    a leg — their manifest stays honest — but they never trigger a second
    reader call.
    """
    keys: list[tuple[str, str]] = []
    cutoffs: dict[tuple[str, str], datetime | None] = {}
    companies: dict[tuple[str, str], str | None] = {}
    wanted_ids: dict[str, None] = {}
    broken: dict[tuple[str, str], str] = {}
    for ep in episodes or ():
        if not isinstance(ep, Mapping):
            continue
        key = (str(ep.get("issuer") or ""), str(ep.get("q") or ""))
        if key in companies:
            continue
        keys.append(key)
        cutoff_dt = _parse_utc(ep.get("cutoff"))
        cutoffs[key] = cutoff_dt
        company_id = (
            resolve_company_id(key[0], cutoff_dt, resolve_ticker=resolve_ticker)
            if cutoff_dt is not None
            else None
        )
        if cutoff_dt is None or company_id is None:
            companies[key] = None
            broken[key] = "identity_unresolved"
            continue
        companies[key] = company_id
        try:
            qm1_id, q_id = s_event_ids(company_id, key[1])
        except ValueError:
            broken[key] = "fiscal_q_unparseable"
            continue
        wanted_ids.setdefault(qm1_id, None)
        wanted_ids.setdefault(q_id, None)

    revision_map: dict[str, list[dict[str, Any]]] | None = None
    reader_failed = False
    if wanted_ids:
        if revisions_reader is None:
            from engine.neuralweb.company_intelligence_reader import (
                read_all_event_source_revisions,
            )

            revisions_reader = read_all_event_source_revisions
        try:
            revision_map = revisions_reader(list(wanted_ids), max_hops=max_hops)
        except Exception:  # noqa: BLE001 - one refusal refuses every needy leg
            reader_failed = True

    legs: dict[tuple[str, str], dict[str, Any]] = {}
    for key in keys:
        if key in broken:
            legs[key] = _unrecoverable_s(broken[key])
        elif reader_failed or revision_map is None:
            legs[key] = _unrecoverable_s("chain_unreadable")
        else:
            legs[key] = s_from_workspace(
                key[0],
                key[1],
                cutoffs[key],
                resolve_ticker=resolve_ticker,
                revisions=revision_map,
            )
    return legs


# --------------------------------------------------------------------------
# EX-99.1 manifest enrichment (wave-2 spec §2)
# --------------------------------------------------------------------------


def enrich_exhibits(
    rows: Any, *, fetch_index_headers: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Set ``exhibits`` (types only) and ``has_ex_99_1`` from the SGML headers.

    Every input row reappears in order as a copy.  Only rows that are exactly
    Form ``"8-K"``, carry the Item 2.02 exact token (:func:`_has_item_202`)
    and whose uppercased ticker is in ``UNIVERSE`` are enriched; the rest pass
    through untouched and the fetcher is never called for them.  For an
    enriched row, ``fetch_index_headers(cik, accession)`` returns the filing's
    ``-index-headers.html`` text (the URL is the wave-3 fetcher's business);
    the text is parsed with ``_parse_sgml_manifest``, lazily imported from
    ``scripts.refresh_event_workspaces`` (it html-unescapes first, so escaped
    SGML parses), and the row gets ``exhibits=[{"type": T}, ...]`` — TYPES
    ONLY, filenames dropped — plus ``has_ex_99_1`` from the existing matcher
    :func:`_has_ex991`.  An empty manifest gives ``exhibits=[]`` and
    ``has_ex_99_1=False``.  A fetcher raise or a non-str return enriches
    nothing and appends ``{"ticker", "accession",
    "reason": "index_headers_unavailable"}`` to ``failures``: the row then
    carries no exhibit proof and :func:`enumerate_episodes` drops it (fail
    closed); if that row was the first release, prereg §10 A3's
    ``earlier_release_filing_dropped`` covers the episode.  No exhibit BODY is
    ever fetched or read — only the SGML header manifest (label-exposure law).
    """
    from scripts.refresh_event_workspaces import _parse_sgml_manifest

    enriched: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows or ():
        out = dict(row) if isinstance(row, Mapping) else row
        if not isinstance(out, dict):
            enriched.append(out)
            continue
        issuer = str(out.get("ticker") or "").strip().upper()
        if (
            str(out.get("form") or "").strip() == "8-K"
            and _has_item_202(out.get("items"))
            and issuer in UNIVERSE
        ):
            try:
                text = fetch_index_headers(out.get("cik"), out.get("accession"))
            except Exception:  # noqa: BLE001 - a failed fetch drops the row
                text = None
            if isinstance(text, str):
                manifest = _parse_sgml_manifest(text)
                out["exhibits"] = [{"type": kind} for kind, _name in manifest]
                out["has_ex_99_1"] = _has_ex991({"exhibits": out["exhibits"]})
            else:
                failures.append(
                    {
                        "ticker": issuer,
                        "accession": out.get("accession"),
                        "reason": "index_headers_unavailable",
                    }
                )
        enriched.append(out)
    return enriched, failures


# --------------------------------------------------------------------------
# Prior filings from EDGAR submissions pages (wave-2 spec §3; prereg §10 A2)
# --------------------------------------------------------------------------


def prior_filings_from_submissions(*pages: Any) -> list[dict[str, str]]:
    """10-Q/10-K ``{"accession", "accepted_at", "form"}`` rows from submissions.

    Each page is either an EDGAR submissions JSON (arrays under
    ``filings.recent``) or an older-filings page (arrays at the top level);
    the arrays are ``accessionNumber``, ``acceptanceDateTime`` and ``form``.
    Only forms exactly ``"10-Q"`` or ``"10-K"`` are emitted (the original
    filings A0 reads).  ``accepted_at`` is copied as given, UNCORRECTED: per
    prereg §10 A2 ("A0 history") the submissions-JSON clock runs 4-5 hours
    late, so the ``<= C(e)`` test can only exclude a filing that was in fact
    available, never admit one that was not — the error is conservative, and
    correcting it here would be a redesign of the registered rule.  Rows with
    an empty accession or empty acceptance are skipped; unequal arrays zip to
    the shortest; the first row wins on a duplicate accession; a malformed
    page (not a Mapping, arrays not lists) contributes nothing and never
    raises.
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in pages:
        if not isinstance(page, Mapping):
            continue
        filings = page.get("filings")
        source = page
        if isinstance(filings, Mapping):
            recent = filings.get("recent")
            source = recent if isinstance(recent, Mapping) else None
        if source is None:
            continue
        accessions = source.get("accessionNumber")
        acceptances = source.get("acceptanceDateTime")
        forms = source.get("form")
        if not (
            isinstance(accessions, list)
            and isinstance(acceptances, list)
            and isinstance(forms, list)
        ):
            continue
        for accession, accepted_at, form in zip(accessions, acceptances, forms):
            acc = accession.strip() if isinstance(accession, str) else ""
            accepted = accepted_at.strip() if isinstance(accepted_at, str) else ""
            kind = form.strip() if isinstance(form, str) else ""
            if not acc or not accepted or kind not in ("10-Q", "10-K"):
                continue
            if acc in seen:
                continue
            seen.add(acc)
            out.append({"accession": acc, "accepted_at": accepted, "form": kind})
    return out
