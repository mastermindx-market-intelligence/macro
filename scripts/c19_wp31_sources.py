"""C19 WP31 evaluator — SOURCES module (prereg §1–§3: episodes, cutoff, K, label, A0, leaks).

Governing documents
-------------------
- Preregistration: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``
  (merged as commit ``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c``).  The prereg wins
  any conflict with the build spec; never redesign, never widen.
- Frozen build spec: ``WP31_BUILD_SPEC.md`` (seat stage), sections
  "Shared episode dict" and "Sources (prereg §1–§3)", sha256
  ``5485384ad1f08a0211f634045d23d623d7e4d961924d5b9f5911ea6081149ef1``.

This module implements ONLY the SOURCES part of the WP31 evaluator.  The episode
dict produced by :func:`enumerate_episodes` and shaped by :func:`k_from_surface`,
:func:`label_and_a0_from_companyfacts` and :func:`apply_leak_rules` is the sole
interface to the sibling STATS and GATES modules; nothing is imported from them
(they do not exist yet — lane law R6).

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
    """Parse an EDGAR-style UTC clock; None when absent/malformed (fail closed).

    ``collectors/edgar_earnings_8k.py`` stores ``acceptance_datetime`` as an
    ISO-UTC string ("…Z"); offset-less strings/datetimes are read as UTC per
    that convention, unparseable values return None and the caller drops or
    refuses the record — never a guessed clock.
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
    return {
        "q_minus_1_resolved": False,
        "source_sha256": None,
        "generation_id": None,
        "record_ids": [],
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
    token, an EX-99.1 exhibit, a parseable acceptance clock and a report_date
    anchor.  ``(issuer, q, period_end)`` come from the repo fiscal helper
    (``FISCAL_HELPER_SOURCE`` records which path is live).  The FIRST
    qualifying filing per (issuer, q) is kept by acceptance time (prereg §1
    "unit" — first filing carrying the release).  ``status`` is "ELIGIBLE"
    when :func:`is_eligible` (t_rel strictly after the prereg commit instant)
    else "EXPOSED" (smoke-test plumbing only, never counted — prereg §0).
    Output is ordered by (t_rel, issuer, q); every key of the shared episode
    dict is initialized (``returns`` stays absent — it is written by the
    cost-descriptive stage).
    """
    best: dict[tuple[str, str], dict[str, Any]] = {}
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
        if not _has_ex991(row):
            continue
        t_rel = _parse_utc(row.get("acceptance_datetime"))
        if t_rel is None:
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
        }
    episodes = sorted(
        best.values(), key=lambda e: (e["_t_rel"], e["issuer"], e["q"])
    )
    for episode in episodes:
        episode.pop("_t_rel")
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
    — the STATS lane's manifest.  ``rights_class`` is the average row's own
    label (None stays None: an unlabeled right fails the K-backed gate closed).
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

    average_row = by_type.get("average")
    k["rights_class"] = average_row.get("rights_class") if average_row else None

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
    (the STATS lane ABSTAINs "no_prior_filing").

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
    S leg's ``generated_at``/``observed_at`` when its reader supplies them
    (the S reader is seat wave 2; :func:`s_from_workspace` stubs it).
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
# S reader stub (NOT built in this wave — spec "Sources" final bullet)
# --------------------------------------------------------------------------


def s_from_workspace(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Not implemented in this wave: the event-workspace S reader is owner-bound.

    Prereg §3.2 names ``read_current_event_workspace`` as the S entry point,
    but the build spec freezes it out of this lane; the seat supplies it in
    wave 2.  Raises with the exact message the integration runner asserts.
    """
    raise NotImplementedError("S reader: owner-bound; seat wave 2")
