"""ONE coverage object for the options family (OIP R8).

THE PROBLEM.  Four builders in this family each answer "how much of the universe did we
actually see?" in a different, non-comparable shape:

  build_options_command   covered / universe / coverage_pct / quality_en / quality_zh
  build_gex_board         {group: {covered, total}} + a "__all__" roll-up
  build_options_screener  n_names / n_young / n_mature / n_skew / n_ivspread / n_relvol
  build_flow_desk         a STRING — "353 names · EOD · direction approx"

So no surface can put two of them side by side, no audit can compare them, and the
flow desk's number cannot be read by a machine at all.  R8 defines the shape once.

CONTRACT
  * ADDITIVE ONLY.  Emitted under the key ``coverage_v1`` ALONGSIDE every existing
    field.  Nothing is removed or renamed — the four builders' current keys are load-
    bearing for pages that ship today, and no surface consumes this object yet.
    Surfaces adopt it in later OIP waves.
  * DISPLAY-TIER.  A coverage count never ranks, sizes, or gates anything.
  * PLAIN WORDS, BILINGUAL.  Every name is an EN/ZH pair of ordinary words — no store
    paths, no slugs, no enums, no "n=".  ``key`` is machine-only and must never be
    rendered; surfaces render ``name_en`` / ``name_zh``.
  * HONEST NULLS.  An uncountable universe is ``n: None``, never 0, and
    ``coverage_pct`` is None rather than a fabricated 100%.  ``sessions_behind`` is
    computed from the exchange calendar (``lib.nyse_calendar``), never wall-clock days,
    so a Monday morning does not report every store as a session staler than it is.

SHAPE (schema ``options_coverage.v1``)

    {
      "schema": "options_coverage.v1",
      "universe": {"name_en": "US options universe", "name_zh": "美股期权范围",
                   "n": 403},
      "covered": 370,
      "coverage_pct": 91.8,          # None when either side is unknown
      "asof": "2026-07-28",          # the session this coverage was counted at
      "sessions_behind": 1,          # of `asof`, from the NYSE calendar; None if unknown
      "sources": [                   # per-source freshness, one row per input store
        {"key": "flow_desk", "name_en": "Options tape", "name_zh": "期权成交",
         "asof": "2026-07-28", "n": 353, "sessions_behind": 1}
      ]
    }
"""
from __future__ import annotations

from datetime import timedelta

SCHEMA = "options_coverage.v1"


def _as_asof(v) -> str | None:
    """A date string, or None.  `str(pd.NaT)` is the literal "NaT" and `str(nan)` is
    "nan" — publishing either as an as-of stamp is worse than publishing nothing."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nat", "nan", "none", "<na>"):
        return None
    return s


def _sessions_behind(asof, expected_session=None) -> int | None:
    """Completed sessions missing behind ``asof``, or None when it cannot be judged.

    Calendar-derived, never a wall-clock day count — a store holding Friday's close is
    0 sessions behind on Saturday, Sunday AND Monday morning.
    """
    if not asof:
        return None
    try:
        import pandas as pd

        from lib import nyse_calendar

        actual = pd.Timestamp(str(asof)).date()
        if expected_session is not None:
            expected = pd.Timestamp(str(expected_session)).date()
            return len(nyse_calendar.sessions_between(actual + timedelta(days=1), expected))
        return int(nyse_calendar.sessions_behind(actual))
    except Exception:  # noqa: BLE001
        return None


def _status(asof, expected_session=None) -> str:
    stamp = _as_asof(asof)
    if not stamp:
        return "unavailable"
    if expected_session is not None:
        try:
            import pandas as pd
            if pd.Timestamp(stamp).date() > pd.Timestamp(str(expected_session)).date():
                return "conflict"
        except Exception:  # noqa: BLE001 — unreadable dates are unavailable, never current
            return "unavailable"
    behind = _sessions_behind(asof, expected_session)
    if behind is None:
        return "unavailable"
    return "stale" if behind else "current"


def _as_int(v) -> int | None:
    """int(v) or None.  NEVER raises — `int(float("nan"))` raises ValueError, which would
    break this module's "never raises" contract the first time a count arrived as NaN from
    a pandas aggregation (minor 4, review 2026-07-29).  Booleans are rejected because
    `isinstance(True, int)` is True and a flag is not a count."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):   # NaN / +-inf
        return None
    return int(f)


def source(key: str, name_en: str, name_zh: str, *,
           asof=None, n: int | None = None, expected_session=None) -> dict:
    """One input store's freshness row.

    ``key`` is machine-only (never rendered).  ``name_en`` / ``name_zh`` are the plain
    words a surface prints.  ``asof`` is the store's own session stamp; ``n`` the number
    of names it covered.  Both may be None — an unknown is printed as unknown.
    """
    behind = _sessions_behind(asof, expected_session)
    status = _status(asof, expected_session)
    return {
        "key": str(key),
        "name_en": str(name_en),
        "name_zh": str(name_zh),
        "asof": _as_asof(asof),
        "n": _as_int(n),
        "expected_session": _as_asof(expected_session),
        "sessions_behind": behind,
        "status": status,
    }


def coverage_object(*, universe_name_en: str, universe_name_zh: str,
                    universe_n: int | None, covered_n: int | None,
                    asof=None, sources: list[dict] | None = None,
                    expected_session=None) -> dict:
    """Build the shared coverage object.  Never raises; unknowns stay None.

    ``covered_n`` is clamped to ``universe_n`` when both are known — a coverage share
    above 100% is a counting bug, and publishing it as ">100%" is worse than clamping
    and letting the two raw counts stand for inspection.
    """
    uni = _as_int(universe_n)
    cov = _as_int(covered_n)
    pct = None
    if uni is not None and cov is not None and uni > 0:
        pct = round(min(cov, uni) / uni * 100.0, 1)
    return {
        "schema": SCHEMA,
        "universe": {
            "name_en": str(universe_name_en),
            "name_zh": str(universe_name_zh),
            "n": uni,
        },
        "covered": cov,
        "coverage_pct": pct,
        "asof": _as_asof(asof),
        "expected_session": _as_asof(expected_session),
        "sessions_behind": _sessions_behind(asof, expected_session),
        "status": _status(asof, expected_session),
        "sources": list(sources or []),
    }


def _source_session_date(value):
    """Parse a published session DATE, never guess an instant's market date."""
    import re
    from datetime import date, datetime

    import pandas as pd
    from lib import nyse_calendar

    if not pd.api.types.is_scalar(value):
        return "invalid", None
    if value is None or pd.isna(value):
        return "missing", None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in {"nat", "nan", "none", "<na>"}:
            return "missing", None
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return "invalid", None
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return "invalid", None
    if isinstance(value, datetime):
        # Parquet may store a session DATE as a naive midnight timestamp. An
        # aware or non-midnight value is an instant requiring an explicit owner
        # conversion, never a reason to guess a date here.
        if value.tzinfo is not None or any((value.hour, value.minute, value.second,
                                           value.microsecond, getattr(value, "nanosecond", 0))):
            return "invalid", None
        value = value.date()
    if not isinstance(value, date):
        return "invalid", None
    if not nyse_calendar.is_session(value):
        return "invalid", None
    return "dated", value


def source_session_coverage(frame, *, comparison_session, date_columns) -> dict:
    """Count source-date alignment per UNIQUE ticker in an existing state table.

    Additive audit metadata only. A matching date does not certify provider SLA
    freshness, optionability, complete chains, Greek validity, or feature quality.
    Duplicate identical observations collapse; differing dates (including a null
    beside a dated row) stay conflicts, never latest-row-wins. No input is changed.
    """
    import pandas as pd

    kind, comparison = _source_session_date(comparison_session)
    if kind != "dated":
        raise ValueError("comparison_session must be a valid exchange-session date")
    if (not isinstance(date_columns, (tuple, list)) or not date_columns
            or any(not isinstance(c, str) or not c.startswith("src_")
                   or not c.endswith("_asof") for c in date_columns)
            or len(set(date_columns)) != len(date_columns)):
        raise ValueError("date_columns must name distinct explicit source-date columns")
    report = {
        "basis": "source_session_alignment_only",
        "comparison_session": comparison.isoformat(),
        "status": "unavailable",
        "n_rows": None, "n_tickers": None, "n_invalid_ticker_rows": None,
        "n_duplicate_tickers": None, "n_all_source_dates_matching": None,
        "qualified_ticker_count": None,
        "sources": {},
        "note": "Source dates are reported independently; matching dates do not qualify data. "
                "Older dates are relative to the comparison session, not a provider SLA verdict.",
    }
    if not isinstance(frame, pd.DataFrame) or "ticker" not in frame.columns:
        report["reason"] = "state_or_ticker_column_unavailable"
        return report
    if not frame.columns.is_unique:
        report["reason"] = "ambiguous_columns"
        return report

    groups: dict[str, list[dict]] = {}
    invalid = 0
    # No symbol alias conversion: class-share punctuation remains part of identity.
    for row in frame.to_dict(orient="records"):
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or not ticker.strip():
            invalid += 1
            continue
        groups.setdefault(ticker.strip().upper(), []).append(row)
    report.update(status="measured", n_rows=len(frame), n_tickers=len(groups),
                  n_invalid_ticker_rows=invalid,
                  n_duplicate_tickers=sum(len(rows) > 1 for rows in groups.values()))
    all_matching = set(groups)
    statuses = ("matching_session", "older_session", "future_session", "missing", "invalid", "conflict")
    for column in date_columns:
        buckets: dict[str, list[str]] = {status: [] for status in statuses}
        for ticker in sorted(groups):
            dates = {_source_session_date(row.get(column)) for row in groups[ticker]}
            if len(dates) != 1:
                status = "conflict"
            else:
                kind, value = next(iter(dates))
                status = kind
                if kind == "dated":
                    status = ("matching_session" if value == comparison else
                              "older_session" if value < comparison else "future_session")
            buckets[status].append(ticker)
        all_matching.intersection_update(buckets["matching_session"])
        report["sources"][column] = {
            "column_present": column in frame.columns,
            "counts": {status: len(tickers) for status, tickers in buckets.items()},
            "tickers_by_status": buckets,
        }
    report["n_all_source_dates_matching"] = len(all_matching)
    return report
