"""Conservative ThetaData T2a signed-tape adapter for Flow Leaders.

One derived consumer of the existing data/tape_flow/daily/<ROOT>.parquet store.
No collection, vendor calls, copied Theta EOD store, schema migration, or writes.
The legacy Massive/Polygon summaries are NOT a valid fresh source.

Units: tape premiums are USD; the Flow Leaders science contract uses USD millions.
The signed value comes from Theta trade+NBBO quote-rule estimation, NOT EOD
volume or a directional oracle. Source-ready does not qualify a predictive edge.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from lib.nyse_calendar import is_session

log = logging.getLogger(__name__)
MIN_UNIVERSE_COVERAGE = 0.90

_REQUIRED = frozenset({
    "date", "root", "signing_source", "n_trades", "net_signed_premium",
    "gross_premium", "zerodte_share",
})
_EX_ZERO_DTE = (
    "dte_1_7d_net_premium", "dte_8_30d_net_premium",
    "dte_31_90d_net_premium", "dte_90p_net_premium",
)


@dataclass
class TapeCohort:
    summaries: dict[str, pd.DataFrame] = field(default_factory=dict)
    expected_roots: int = 0
    latest_session: str | None = None
    current_roots: int = 0

    @property
    def coverage_ratio(self) -> float:
        return self.current_roots / self.expected_roots if self.expected_roots else 0.0

    @property
    def coverage_ready(self) -> bool:
        return self.expected_roots > 0 and self.coverage_ratio >= MIN_UNIVERSE_COVERAGE


def _parse_root(path: Path, expected: set[str]) -> tuple[str, pd.DataFrame] | None:
    root = path.stem.upper()
    if root not in expected:
        return None
    try:
        raw = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 — an unreadable root is NOT valid coverage
        log.warning("flow_leaders: Theta tape %s unreadable: %s", root, exc)
        return None
    if raw.empty or not _REQUIRED.issubset(raw.columns):
        return None
    # No source fusion. Accept only the canonical tape writer's own source/identity.
    if not raw["root"].astype(str).str.upper().eq(root).all():
        log.warning("flow_leaders: Theta tape %s contains wrong-root records", root)
        return None
    if not raw["signing_source"].astype(str).eq("tape").all():
        log.warning("flow_leaders: Theta tape %s has mixed/unqualified signing", root)
        return None

    dates = raw["date"].astype("string")
    canonical = dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
    parsed = pd.to_datetime(dates.where(canonical), format="%Y-%m-%d", errors="coerce")
    net = pd.to_numeric(raw["net_signed_premium"], errors="coerce")
    gross = pd.to_numeric(raw["gross_premium"], errors="coerce")
    trades = pd.to_numeric(raw["n_trades"], errors="coerce")
    zshare = pd.to_numeric(raw["zerodte_share"], errors="coerce")
    today_utc = datetime.now(timezone.utc).date()
    session_ok = parsed.map(lambda d: bool(
        pd.notna(d) and d.date() <= today_utc and is_session(d.date())
    ))
    valid = (
        session_ok & trades.gt(0) & net.notna() & gross.gt(0)
        & (gross.add(0.0001) >= net.abs())
        & (zshare.isna() | zshare.between(0, 1))
    ).fillna(False)
    if not valid.any():
        return None
    df = raw.loc[valid].copy()
    dates_valid = parsed.loc[valid]
    if dates_valid.duplicated().any():
        # Do not silently choose a winner for conflicting root/session receipts.
        log.warning("flow_leaders: Theta tape %s has duplicate sessions", root)
        return None

    net = net.loc[valid].astype(float) / 1_000_000
    gross = gross.loc[valid].astype(float) / 1_000_000
    zshare = zshare.loc[valid].astype(float)
    ex0dte = pd.Series(float("nan"), index=df.index)
    if all(col in df.columns for col in _EX_ZERO_DTE):
        buckets = df.loc[:, list(_EX_ZERO_DTE)].apply(pd.to_numeric, errors="coerce")
        complete = buckets.notna().all(axis=1)
        ex0dte.loc[complete] = buckets.sum(axis=1).loc[complete] / 1_000_000

    result = pd.DataFrame(
        {
            "net_premium_mn": net.to_numpy(),
            "premium_mn": gross.to_numpy(),
            "zerodte_share": zshare.to_numpy(),
            "net_premium_ex0dte_mn": ex0dte.to_numpy(),
        },
        index=pd.DatetimeIndex(dates_valid.to_numpy(), name="session"),
    ).sort_index()
    return root, result


def load_tape_cohort(data_root: Path, expected_roots: Iterable[str]) -> TapeCohort:
    """Read actual T2a source receipts and compare the newest *common* session
    against the full configured universe. A single updated root is not a board.

    A partial store or denied source is fail-closed by the caller; NEVER
    fall through to a legacy archive and re-label it a fresh market session.
    """
    expected = {str(root).upper() for root in expected_roots}
    cohort = TapeCohort(expected_roots=len(expected))
    tape_root = data_root / "tape_flow" / "daily"
    if not tape_root.is_dir():
        return cohort

    for path in sorted(tape_root.glob("*.parquet")):
        rec = _parse_root(path, expected)
        if rec is None:
            continue
        ticker, summary = rec
        cohort.summaries[ticker] = summary

    if not cohort.summaries:
        return cohort
    dates_by_root = {ticker: df.index[-1].date().isoformat()
                     for ticker, df in cohort.summaries.items()}
    # Choose the most widely represented session, not a single early/late
    # outlier. Restrict eligible names to that session in the caller.
    session_counts: dict[str, int] = {}
    for session in dates_by_root.values():
        session_counts[session] = session_counts.get(session, 0) + 1
    latest, count = max(session_counts.items(), key=lambda item: (item[1], item[0]))
    cohort.latest_session = latest
    cohort.current_roots = count
    # Do not silently re-label the historical tail as part of the latest cohort.
    cohort.summaries = {
        ticker: df for ticker, df in cohort.summaries.items()
        if dates_by_root[ticker] == latest
    }
    return cohort
