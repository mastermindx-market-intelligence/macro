"""engine.group_breadth_history — within-group breadth and breadth CHANGE, one code path.

Pure functions. A closes matrix (sessions x tickers) and a membership map go in;
per group per session come out. The same functions build the reconstructed
history (``scripts/build_group_breadth_history.py``) and tonight's member rows
(``engine/member_breadth_ledger.py`` via ``collectors/breadth.py``), so the
history and the nightly record cannot drift apart (Historical Reconstruction
Protocol §4.2).

What is measured (no thresholds are tuned anywhere in this module):

* level, per group per session — members counted (a close that session), members
  with 50 and with 200 sessions of history, members above each average, and the
  share above each average in percent (0-100, the convention of
  ``data/breadth/sector_breadth.parquet``).
* plain level change over 5/20/63/126 sessions — today's share minus the share k
  sessions earlier, each on whatever membership was in force on its own date
  (column prefix ``lvl_chg_``). Membership reassignment moves this number by itself.
* like-for-like (fixed-set) change over the same horizons — take the members of
  the group at t; keep those with w sessions of history at BOTH t and t-k; their
  share above their own average at t minus the share of the SAME names at t-k
  (prefix ``fix_chg_``). This is the change the rotation programme ruled on.
* weekly fixed-set change (``weekly_fixed_set``) — last session of each calendar
  week, k = 13 and 26 weeks, 200-session average, exactly per the COO addendum.
* cross-sectional rank of every change across the groups valid on that session
  (1 = largest increase; ties share the lower rank), and ``n_ranked``.
* state from the sign of every change: ``improving`` (> 0), ``deteriorating``
  (< 0), ``flat`` (exactly 0), missing when the change is missing; and
  ``*_run``: how many consecutive rows that state has held, counting today.

Fixed rules, all ruled not tuned:
* A moving average for a session uses that session and earlier closes only
  (``rolling(w, min_periods=w)`` — identical to ``collectors/breadth.py``), so a
  value never uses data dated after its own row.
* ``MIN_MEMBERS = 10`` (COO addendum 2026-11-12 01:13Z): a share, and any change
  built from it, is missing — never zero — when fewer than 10 members qualify.
* Shares are computed as ``100.0 * count / denominator`` in one rounding step, so
  two equal ratios are equal floats and an exactly-unchanged share is exactly 0.

Membership map: a DataFrame with columns ``ticker``, ``group`` and optional
``start_date`` / ``end_date``. A row makes the ticker a member of the group on
sessions ``start_date <= d < end_date`` (a missing start is open to the past, a
missing end is open to the future). Today's-membership bases simply pass rows
without dates. A ticker may hold several non-overlapping rows; if rows overlap,
the LAST row in the frame wins on the overlapping sessions.

Nothing here reads files, the network or the clock.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

WINDOWS: tuple[int, int] = (50, 200)
HORIZONS: tuple[int, ...] = (5, 20, 63, 126)
WEEKLY_HORIZONS: tuple[int, ...] = (13, 26)
MIN_MEMBERS = 10
# COO addendum 2026-11-12 01:13Z: the headline is the WEEKLY fixed-set change,
# k = 13 weeks (weekly_fixed_set). The daily 63-session columns stay as specified.
HEADLINE = "fix_chg_pct_above_200_13w"

STATE_IMPROVING = "improving"
STATE_DETERIORATING = "deteriorating"
STATE_FLAT = "flat"

_NOT_MEMBER = -1


# --------------------------------------------------------------------------- inputs
def member_flags(closes: pd.DataFrame, window: int) -> tuple[np.ndarray, np.ndarray]:
    """(has_history, above) boolean matrices for one moving-average window.

    ``has_history[t, i]`` — ticker i has a defined ``window``-session average at t.
    ``above[t, i]``       — its close at t is strictly above that average.
    Causal: row t uses closes on rows <= t only.

    The average is taken over the ticker's OWN last ``window`` closes, so a row
    where it has no close (a halt, a stray vendor row) does not erase its average
    for the next ``window`` rows. On a matrix without interior gaps this equals
    ``closes.rolling(window, min_periods=window).mean()`` exactly (the collector's
    form). A ticker has no flag on a row where it has no close.
    """
    ma = closes.apply(lambda s: s.dropna().rolling(window, min_periods=window).mean()
                      .reindex(s.index))
    has = ma.notna().to_numpy()
    above = (closes > ma).to_numpy() & has
    return has, above


def assign_groups(index: pd.DatetimeIndex, tickers: Sequence[str],
                  membership: pd.DataFrame,
                  groups: Sequence[str] | None = None) -> tuple[np.ndarray, list[str]]:
    """Membership map -> int16 code matrix (sessions x tickers), -1 = not a member.

    Returns ``(codes, groups)`` where ``codes[t, i] == j`` means ticker i belongs
    to ``groups[j]`` on session t. Rows whose ticker is not in ``tickers`` or whose
    group is missing are ignored.
    """
    mem = membership.dropna(subset=["group"])
    if groups is None:
        groups = sorted(mem["group"].astype(str).unique())
    groups = list(groups)
    gpos = {g: j for j, g in enumerate(groups)}
    tpos = {t: i for i, t in enumerate(tickers)}
    idx = pd.DatetimeIndex(index)
    codes = np.full((len(idx), len(tickers)), _NOT_MEMBER, dtype=np.int16)
    has_start = "start_date" in mem.columns
    has_end = "end_date" in mem.columns
    for row in mem.itertuples(index=False):
        i = tpos.get(getattr(row, "ticker"))
        j = gpos.get(str(getattr(row, "group")))
        if i is None or j is None:
            continue
        lo = 0
        hi = len(idx)
        if has_start:
            s = getattr(row, "start_date")
            if pd.notna(s):
                lo = int(idx.searchsorted(pd.Timestamp(s), side="left"))
        if has_end:
            e = getattr(row, "end_date")
            if pd.notna(e):
                hi = int(idx.searchsorted(pd.Timestamp(e), side="left"))
        if hi > lo:
            codes[lo:hi, i] = j
    return codes, groups


# --------------------------------------------------------------------------- arithmetic
def _share(count: np.ndarray, denom: np.ndarray, min_members: int) -> np.ndarray:
    out = np.full(count.shape, np.nan)
    ok = denom >= min_members
    out[ok] = (100.0 * count[ok]) / denom[ok]
    return out


def _shift_rows(a: np.ndarray, k: int, fill) -> np.ndarray:
    """Row t of the result holds row t-k of ``a``; the first k rows hold ``fill``."""
    out = np.empty_like(a)
    out[:k] = fill
    out[k:] = a[:-k] if k else a
    return out


def group_levels(codes: np.ndarray, closes_valid: np.ndarray,
                 flags: dict[int, tuple[np.ndarray, np.ndarray]],
                 n_groups: int, min_members: int = MIN_MEMBERS) -> dict[str, np.ndarray]:
    """Per-group level matrices (sessions x groups).

    ``flags`` maps window -> (has_history, above) from ``member_flags``.
    """
    T = codes.shape[0]
    out: dict[str, np.ndarray] = {"n_members": np.zeros((T, n_groups), dtype=np.int32)}
    for w in flags:
        out[f"n_has_{w}"] = np.zeros((T, n_groups), dtype=np.int32)
        out[f"n_above_{w}"] = np.zeros((T, n_groups), dtype=np.int32)
    for j in range(n_groups):
        m = codes == j
        out["n_members"][:, j] = (m & closes_valid).sum(axis=1)
        for w, (has, above) in flags.items():
            out[f"n_has_{w}"][:, j] = (m & has).sum(axis=1)
            out[f"n_above_{w}"][:, j] = (m & above).sum(axis=1)
    for w in flags:
        out[f"pct_above_{w}"] = _share(out[f"n_above_{w}"], out[f"n_has_{w}"], min_members)
    return out


def level_change(level: np.ndarray, k: int) -> np.ndarray:
    """Plain difference of levels: level[t] - level[t-k] (missing if either is)."""
    return level - _shift_rows(level, k, np.nan)


def fixed_set_change(codes: np.ndarray, has: np.ndarray, above: np.ndarray,
                     k: int, n_groups: int,
                     min_members: int = MIN_MEMBERS) -> tuple[np.ndarray, np.ndarray]:
    """Like-for-like change over k rows on the members of each group at t.

    Eligible at t: member of g at t, with a defined average at t AND at t-k.
    Returns ``(change, n_eligible)``; change is missing when n_eligible < min_members.
    """
    has_k = _shift_rows(has, k, False)
    above_k = _shift_rows(above, k, False)
    elig_any = has & has_k
    T = codes.shape[0]
    chg = np.full((T, n_groups), np.nan)
    n = np.zeros((T, n_groups), dtype=np.int32)
    for j in range(n_groups):
        e = (codes == j) & elig_any
        ne = e.sum(axis=1)
        now = (e & above).sum(axis=1)
        then = (e & above_k).sum(axis=1)
        n[:, j] = ne
        chg[:, j] = _share(now, ne, min_members) - _share(then, ne, min_members)
    return chg, n


def cross_rank(change: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rank across groups per row: 1 = largest change; ties take the lower rank
    (``min``); missing stays missing. Returns ``(rank, n_ranked)``."""
    df = pd.DataFrame(change)
    rank = df.rank(axis=1, method="min", ascending=False).to_numpy()
    n_ranked = df.notna().sum(axis=1).to_numpy().astype(np.int32)
    return rank, n_ranked


def sign_state(change: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """State from the sign of the change and how many consecutive rows it held.

    Returns ``(state, run)``: state is an object array of improving /
    deteriorating / flat / None; run counts consecutive rows with the same
    state including the current row (NaN where the state is missing).
    """
    state = np.full(change.shape, None, dtype=object)
    state[change > 0] = STATE_IMPROVING
    state[change < 0] = STATE_DETERIORATING
    state[change == 0] = STATE_FLAT
    run = np.full(change.shape, np.nan)
    T = change.shape[0]
    for t in range(T):
        cur = state[t]
        ok = cur != None  # noqa: E711 — elementwise on an object array
        if t == 0:
            run[t, ok] = 1.0
            continue
        same = ok & (state[t - 1] == cur)
        prev = np.nan_to_num(run[t - 1], nan=0.0)
        run[t, ok] = 1.0
        run[t, same] = prev[same] + 1.0
    return state, run


# --------------------------------------------------------------------------- assemblers
def _long(index: pd.DatetimeIndex, groups: Sequence[str],
          cols: dict[str, np.ndarray]) -> pd.DataFrame:
    T, G = len(index), len(groups)
    base = pd.DataFrame({
        "date": np.repeat(np.asarray(index), G),
        "group": np.tile(np.asarray(groups, dtype=object), T),
    })
    for name, mat in cols.items():
        flat = mat.reshape(T * G)
        # state columns: one fixed dtype whatever the values (all-missing or not),
        # so a prefix run and a full run produce the same schema
        base[name] = pd.Series(flat, dtype=object) if flat.dtype == object else flat
    return base


def _change_block(cols: dict[str, np.ndarray], name: str, chg: np.ndarray) -> None:
    rank, n_ranked = cross_rank(chg)
    state, run = sign_state(chg)
    cols[name] = chg
    cols[f"rank_{name}"] = rank
    cols[f"n_ranked_{name}"] = np.repeat(n_ranked[:, None], chg.shape[1], axis=1)
    cols[f"state_{name}"] = state
    cols[f"run_{name}"] = run


def daily_group_breadth(closes: pd.DataFrame, membership: pd.DataFrame,
                        groups: Sequence[str] | None = None,
                        windows: Iterable[int] = WINDOWS,
                        horizons: Iterable[int] = HORIZONS,
                        min_members: int = MIN_MEMBERS) -> pd.DataFrame:
    """Long frame (date, group) of levels, plain and fixed-set changes, ranks, states.

    ``closes`` must be sorted by date with one column per ticker; NaN = no close.
    Rows are emitted for every session x group; a group with too few qualifying
    members carries missing shares on that session.
    """
    closes = closes.sort_index()
    codes, groups = assign_groups(closes.index, list(closes.columns), membership, groups)
    flags = {w: member_flags(closes, w) for w in windows}
    G = len(groups)
    lv = group_levels(codes, closes.notna().to_numpy(), flags, G, min_members)
    cols: dict[str, np.ndarray] = dict(lv)
    for w, (has, above) in flags.items():
        for k in horizons:
            _change_block(cols, f"lvl_chg_pct_above_{w}_{k}", level_change(lv[f"pct_above_{w}"], k))
            fchg, nfix = fixed_set_change(codes, has, above, k, G, min_members)
            _change_block(cols, f"fix_chg_pct_above_{w}_{k}", fchg)
            cols[f"n_fixed_{w}_{k}"] = nfix
    return _long(closes.index, groups, cols)


def week_end_rows(index: pd.DatetimeIndex) -> np.ndarray:
    """Integer positions of the last session of each calendar week (Mon-Sun)."""
    idx = pd.DatetimeIndex(index)
    week = idx.to_period("W-SUN")
    s = pd.Series(np.arange(len(idx)), index=week)
    return s.groupby(level=0).max().to_numpy()


def weekly_fixed_set(closes: pd.DataFrame, membership: pd.DataFrame,
                     groups: Sequence[str] | None = None,
                     window: int = 200,
                     horizons_weeks: Iterable[int] = WEEKLY_HORIZONS,
                     min_members: int = MIN_MEMBERS,
                     include_last_partial_week: bool = True) -> pd.DataFrame:
    """Weekly fixed-set change of the share above the ``window``-session average.

    Sampled at the last session of each calendar week; k counted in weeks. The
    averages are computed on the full daily matrix first, then sampled, so each
    weekly value is the daily value of its own session. Also carries the plain
    difference of weekly levels as ``lvl_diff_pct_above_{w}_{k}w`` (membership
    reassignment moves that one; it is kept for comparison, not as the measure).

    ``include_last_partial_week=False`` drops the final week when its last
    session is Monday-Wednesday (a week still in progress). A final week
    ending Thursday is kept, so a holiday-shortened week is not lost; the cost
    is that a normal week cut on Thursday is kept too.
    """
    closes = closes.sort_index()
    codes, groups = assign_groups(closes.index, list(closes.columns), membership, groups)
    has, above = member_flags(closes, window)
    rows = week_end_rows(closes.index)
    if not include_last_partial_week and len(rows):
        last = closes.index[rows[-1]]
        # in progress = the week's Friday has not passed yet in the data. A
        # holiday-shortened week ending Thursday is complete only if a later
        # date exists; at the end of the data we cannot tell, so Thursday is
        # kept (Good Friday / July 4) and Monday-Wednesday ends are dropped.
        if last.dayofweek < 3:
            rows = rows[:-1]
    idx = closes.index[rows]
    c_w, h_w, a_w = codes[rows], has[rows], above[rows]
    G = len(groups)
    lv = group_levels(c_w, closes.notna().to_numpy()[rows], {window: (h_w, a_w)}, G, min_members)
    cols: dict[str, np.ndarray] = {
        "n_members": lv["n_members"],
        f"n_has_{window}": lv[f"n_has_{window}"],
        f"pct_above_{window}": lv[f"pct_above_{window}"],
    }
    for k in horizons_weeks:
        fchg, nfix = fixed_set_change(c_w, h_w, a_w, k, G, min_members)
        _change_block(cols, f"fix_chg_pct_above_{window}_{k}w", fchg)
        cols[f"n_fixed_{window}_{k}w"] = nfix
        cols[f"lvl_diff_pct_above_{window}_{k}w"] = level_change(lv[f"pct_above_{window}"], k)
    return _long(idx, groups, cols)


def through_last_complete_row(closes: pd.DataFrame, frac: float = 0.8,
                              lookback: int = 20) -> pd.DataFrame:
    """``closes`` cut after its last complete row (trailing; no look-ahead).

    A row priced for under ``frac`` of the trailing ``lookback``-row maximum of
    priced names is an in-progress day (the collector's own rule). Empty when
    no row is complete.
    """
    n = closes.notna().sum(axis=1)
    full = n >= n.rolling(lookback, min_periods=1).max() * frac
    return closes.loc[:full[full].index.max()] if full.any() else closes.iloc[:0]


def member_rows(closes: pd.DataFrame, membership: pd.DataFrame,
                window: int = 200, asof: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per member ticker for a single session — the nightly ledger rows.

    Columns: ``date, ticker, group, has_200_sessions, above_200, source_asof``
    (the two flag names carry ``window``). ``date`` is ``asof`` (default: the last
    session in ``closes``); ``source_asof`` is the ticker's own latest close on or
    before ``date`` (missing if it has none). Uses ``member_flags`` and
    ``assign_groups`` — the same functions as the history.
    """
    closes = closes.sort_index()
    if asof is not None:
        closes = closes[closes.index <= pd.Timestamp(asof)]
    if closes.empty:
        return pd.DataFrame(columns=["date", "ticker", "group", f"has_{window}_sessions",
                                     f"above_{window}", "source_asof"])
    tickers = list(closes.columns)
    codes, groups = assign_groups(closes.index, tickers, membership)
    has, above = member_flags(closes, window)
    t = len(closes.index) - 1
    d = closes.index[t]
    last_valid = closes.apply(pd.Series.last_valid_index)
    out = []
    for i, tk in enumerate(tickers):
        j = codes[t, i]
        if j == _NOT_MEMBER:
            continue
        lv = last_valid.get(tk)
        out.append({
            "date": d.date().isoformat(),
            "ticker": tk,
            "group": groups[j],
            f"has_{window}_sessions": bool(has[t, i]),
            f"above_{window}": bool(above[t, i]),
            "source_asof": None if lv is None or pd.isna(lv) else pd.Timestamp(lv).date().isoformat(),
        })
    return pd.DataFrame(out, columns=["date", "ticker", "group", f"has_{window}_sessions",
                                      f"above_{window}", "source_asof"])
