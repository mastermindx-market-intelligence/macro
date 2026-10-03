"""Bottom-calling ruler — pure grading functions (DISPLAY-TIER; 2026-07-22).

OPERATOR OBJECTIVE (charter 2026-07-22): "pinpoint bottom picks — that's the main
objective of Prophet." Nothing in the system measures bottom-calling today. This module is
the policy-free measurement primitive for that objective. It grades a flagged bar AS a bottom
CALL on four separable qualities, frozen once at maturity, with NO exit policy mixed in
(exits are policy; mixing policy into measurement is what produced the floating-mark mess).

DESIGN: research/signal_engine/BOTTOM_LEDGER_DESIGN.md (ratified on research PR #3182).
The grading arithmetic here replicates research/signal_engine/bottom_ruler_study.py EXACTLY
(the committed calibration baseline in calibration/bottom_ruler_baseline.json is produced by
that same arithmetic run over the panel). Any change to the math here changes the yardstick —
do not "improve" it without a new ratified design + regenerated baseline.

THE FOUR QUALITIES (all frozen at maturity, H=60 trading days):
  PROXIMITY   how close (%) was the signal-day close to the eventual trough low in
              the window [t-PRE, t+H]?  prox = close[t]/trough - 1; pinpoint = within 5%.
  DURABILITY  did the called floor (trailing-20d low F) HOLD after the call? undercut =
              max(0, 1 - min(forward low)/F); held <=0.5% / probed <=3% / deep probe <=10% /
              broke >10%. A probe that recovers is NOT a failed call — depth is graded, not touch.
  PATH        MAE60 before MFE60 (what a position must survive to harvest the call).
  PAYOFF      MFE60 and fwd60 close-basis (context; never a verdict alone).

ONE-GRADER LAW (SA-R14): a grade is computed ONCE when the row matures and is then FROZEN —
never recomputed. The forward advancer (scripts/grade_bottom_calls.py) stores the frozen dict
and never regrades a graded row. These functions are deterministic re-computations from price
history, so a matured horizon can never regress to null; that is what makes the freeze safe.

DISPLAY-TIER: this is measurement/learning infrastructure. It confers NO ranking, sizing, or
gate authority. Promotion of any signal to authority is a separate decision that reads the
matured ledger against a pre-registered gate (VETO_LEG_AUDIT.md) — never this module.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from engine.ledger_clock import ClockContractError, to_ledger_date, to_ledger_date_index

# --- frozen study constants (bottom_ruler_study.py lines 45-48) --------------- #
H = 60        # maturity window (trading days)
PRE = 10      # trough search may start this many days before the signal
FLOOR_WIN = 20  # trailing floor = rolling-20d low (min_periods=5, per the study)
FLOOR_MINP = 5

# undercut depth classes (fractions of the floor F) — held/probe/deep/broke
UNDERCUT_HELD = 0.005
UNDERCUT_PROBE = 0.03
UNDERCUT_DEEP = 0.10
PINPOINT_PROX = 0.05


def _undercut_class(undercut: float) -> str:
    """Map an undercut fraction to the frozen depth class.

    held (<=0.5%) / probed (<=3%) / deep (<=10%) / broke (>10%). A recovered probe is NOT a
    failed call — depth is graded, not touch (BOTTOM_LEDGER_DESIGN.md durability row).
    """
    if undercut <= UNDERCUT_HELD:
        return "held"
    if undercut <= UNDERCUT_PROBE:
        return "probed"
    if undercut <= UNDERCUT_DEEP:
        return "deep"
    return "broke"


def _align_to_ledger_index(series: Any, di: pd.DatetimeIndex) -> pd.Series | None:
    """Re-key an aligned high/low series onto the contract-normalized close index.

    ``high``/``low`` are documented as "aligned to ``close``'s index", so they are re-keyed
    positionally when lengths match (the normal case) and reindexed by ledger date otherwise.
    Returns None when the series is absent — the close_only basis path.
    """
    if series is None:
        return None
    s = pd.Series(series)
    if len(s) == len(di):
        return pd.Series(s.to_numpy(), index=di)
    try:
        s = pd.Series(s.to_numpy(), index=to_ledger_date_index(s.index, field="price index"))
    except ClockContractError:
        return None
    return s.reindex(di)


def grade_call(
    close: pd.Series,
    high: pd.Series | None,
    low: pd.Series | None,
    flag_date: Any,
    *,
    h: int = H,
    pre: int = PRE,
    floor_win: int = FLOOR_WIN,
) -> dict | None:
    """Grade one flagged bar as a bottom call, or return None if not gradeable yet.

    Replicates the per-event arithmetic of bottom_ruler_study.py::events_for (lines 106-140)
    for a single signal bar located at `flag_date` in the price series.

    Args:
        close: price close series, DatetimeIndex (ascending). The signal bar is the row at
            `flag_date`.
        high, low: intraday high/low series aligned to `close`'s index. When either is None
            (or all-NaN over the window) the grade falls back to close for both — basis is
            flagged "close_only" (BOTTOM_LEDGER_DESIGN.md: delisted / close-only names are
            graded, not dropped).
        flag_date: the signal date. Must be present in `close.index` (the caller aligns).
        h, pre, floor_win: study constants; overridable only for tests.

    Returns:
        The frozen grade dict, or None when:
          * `flag_date` is not in the index,
          * the window is not yet matured (fewer than h bars after the signal), or
          * data is insufficient (no valid trailing-20d floor / non-finite trough / bad fill).

        Grade dict keys:
          prox            signed close/trough - 1 (>=0 in the normal case: % above the low)
          t_off           days from signal to the trough (negative = trough already in)
          undercut        max(0, 1 - min(forward low)/F): depth the floor was undercut
          undercut_class  held | probed | deep | broke
          mfe60           max forward high / fill - 1 (payoff ceiling over the window)
          mae60           min forward low / fill - 1 (worst drawdown the position must survive)
          fwd60           close[t+h] / fill - 1 (point-to-point close payoff)
          basis           "ohlc" (real high/low) or "close_only" (high/low absent → close)
    """
    c = pd.Series(close).dropna()
    if len(c) == 0:
        return None
    # CLOCK CONTRACT (engine/ledger_clock.py): the signal bar is located by CIVIL DATE, so both
    # sides are coerced to the one ledger-date representation before they ever meet. Without
    # this, a tz-aware price index (or a tz-aware flag_date) matched nothing and this function
    # returned None *silently* — a row would then accrue forever and never mature, with no
    # error anywhere. Coercion is date resolution only: not one line of the grading arithmetic
    # below depends on it, so the frozen yardstick is unchanged.
    try:
        di = to_ledger_date_index(c.index, field="price index")
        ts = to_ledger_date(flag_date, field="flag_date")
    except ClockContractError:
        return None
    c = pd.Series(c.to_numpy(), index=di)
    hits = np.where(di == ts)[0]
    if len(hits) == 0:
        return None
    # a duplicated index keeps the last bar for that date (prior get_loc behaviour)
    i = int(hits[-1])

    n = len(c)
    # matured-only: need `pre` bars before and `h` bars after, or the window is partial.
    # (study: `if i + H >= n or i - PRE < 0: continue`)
    if i + h >= n or i - pre < 0:
        return None

    # basis: real OHLC when both present with signal over the window, else close_only.
    # high/low arrive keyed by the ORIGINAL index; re-key them to the contract dates so the
    # reindex below aligns (same rule, same order — positional identity is preserved).
    hi = _align_to_ledger_index(high, di)
    lo = _align_to_ledger_index(low, di)
    win_slice = slice(i - pre, i + h + 1)
    has_ohlc = (
        hi is not None
        and lo is not None
        and bool(hi.iloc[win_slice].notna().any())
        and bool(lo.iloc[win_slice].notna().any())
    )
    if has_ohlc:
        basis = "ohlc"
    else:
        # close_only fallback: grade with close for both high and low (flag it).
        basis = "close_only"
        hi = c
        lo = c

    # Floor = trailing-20d low at the signal bar (study: low20 = lo.rolling(20,min_periods=5).min()).
    low20 = lo.rolling(floor_win, min_periods=FLOOR_MINP).min()
    F = float(low20.iloc[i])
    if not np.isfinite(F) or F <= 0:
        return None

    # numpy arrays with NaN filled by close (study: hn = hi.fillna(c), ln = lo.fillna(c)).
    cn = c.to_numpy()
    hn = hi.fillna(c).to_numpy()
    ln = lo.fillna(c).to_numpy()

    f = i + 1              # next-close fill (study)
    fill = float(cn[f])
    if not np.isfinite(fill) or fill <= 0:
        return None

    # proximity: signal close vs eventual trough low in [i-pre, i+h].
    w_lo = ln[i - pre: i + h + 1]
    trough = float(np.nanmin(w_lo))
    if not np.isfinite(trough) or trough <= 0:
        return None
    t_off = int(np.nanargmin(w_lo)) - pre         # days vs signal day

    # durability: undercut of the floor by the forward low from fill onward.
    fwd_lo = ln[f: i + h + 1]
    undercut = max(0.0, 1.0 - float(np.nanmin(fwd_lo)) / F)

    # path + payoff (study slices high/low from f+1, fwd60 from close[i+h]).
    mfe = float(np.nanmax(hn[f + 1: i + h + 1]) / fill - 1.0)
    mae = float(np.nanmin(ln[f + 1: i + h + 1]) / fill - 1.0)
    prox = float(cn[i] / trough - 1.0)
    fwd60 = float(cn[i + h] / fill - 1.0)

    return {
        "prox": prox,
        "t_off": t_off,
        "undercut": undercut,
        "undercut_class": _undercut_class(undercut),
        "mfe60": mfe,
        "mae60": mae,
        "fwd60": fwd60,
        "basis": basis,
    }


def pinpoint(grade: dict) -> bool:
    """True when the call landed within 5% of the eventual trough (prox <= 0.05).

    `pin5` in the study/design. A None or prox-less grade is not a pinpoint.
    """
    if not grade:
        return False
    prox = grade.get("prox")
    return prox is not None and prox <= PINPOINT_PROX


def _median(vals: list[float]) -> float | None:
    v = [x for x in vals if x is not None and np.isfinite(x)]
    return float(np.median(v)) if v else None


def cohort_table(rows: list[dict], by: list[str]) -> list[dict]:
    """Aggregate graded rows into cohorts keyed by the `by` fields.

    Each input row is expected to carry the grade fields (prox, undercut, undercut_class,
    mfe60, fwd60) plus whatever grouping keys `by` names (e.g. source, lane, rung). Rows
    missing a grade (prox is None) are skipped — a cohort summarizes MATURED calls only.

    Returns one dict per cohort:
        {<by fields...>, n, prox_med, pin5, held_pct, broke_pct, mfe60_med, fwd60_med}
    where pin5/held_pct/broke_pct are fractions in [0,1]. Deterministic order: sorted by the
    `by` key tuple.
    """
    buckets: dict[tuple, list[dict]] = {}
    for r in rows:
        if r.get("prox") is None:      # ungraded / immature — not part of a cohort
            continue
        key = tuple(r.get(k) for k in by)
        buckets.setdefault(key, []).append(r)

    out: list[dict] = []
    for key in sorted(buckets, key=lambda k: tuple(("" if x is None else str(x)) for x in k)):
        grp = buckets[key]
        n = len(grp)
        proxes = [g.get("prox") for g in grp]
        undercuts = [g.get("undercut") for g in grp]
        # class-based held/broke fall back to undercut thresholds if class absent.
        held = sum(1 for g in grp if _is_held(g)) / n
        broke = sum(1 for g in grp if _is_broke(g)) / n
        pin5 = sum(1 for g in grp if pinpoint(g)) / n
        row = dict(zip(by, key))
        row.update({
            "n": n,
            "prox_med": _median(proxes),
            "pin5": pin5,
            "held_pct": held,
            "broke_pct": broke,
            "mfe60_med": _median([g.get("mfe60") for g in grp]),
            "fwd60_med": _median([g.get("fwd60") for g in grp]),
        })
        # keep undercut median available for callers that want it (cheap, deterministic)
        row["undercut_med"] = _median(undercuts)
        out.append(row)
    return out


def _is_held(g: dict) -> bool:
    cls = g.get("undercut_class")
    if cls is not None:
        return cls == "held"
    u = g.get("undercut")
    return u is not None and u <= UNDERCUT_HELD


def _is_broke(g: dict) -> bool:
    cls = g.get("undercut_class")
    if cls is not None:
        return cls == "broke"
    u = g.get("undercut")
    return u is not None and u > UNDERCUT_DEEP
