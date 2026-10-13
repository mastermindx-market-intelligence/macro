"""RESEARCH REFERENCE — NOT WIRED. Asynchronous-session covariance qualification (Q18).

Study outcome, numbers and limitations live in one place only:
research/quant_assessment_2026_10/Q18_asynchronous_covariance/VERDICT.md (frozen
preregistration PREREG.md, amendment PREREG_AMENDMENT.md). This module is the
reference implementation that study exercised. It is imported by nothing,
registers nothing, schedules nothing and gates nothing
(``RESEARCH_ONLY = True``). Its outputs are context-only measurement records:
no lead/lag here is a causal direction, and promotion would need a separate
admitted decision by the covariance context owner.

Resolution contract. Inputs are daily session closes, so every estimate is a
daily-interval (or coarser block) quantity. No function returns an intraday
variance, an intraday lag, or a sub-day timing estimate; ``lag_aligned`` takes
an integer number of sessions only, and ``classify_pair_clock``'s
``lag_seconds`` is declared close-clock metadata, not an estimated lead.

Problem. Daily closes of exchanges on different clocks (SSE 15:00 Asia/Shanghai,
HKEX 16:00 Asia/Hong_Kong, NYSE 16:00 America/New_York) cover different 24-hour
windows. Joining them on the calendar-date label ("naive same-date") pairs an
Asia return that ended before the US session with a US return that has not yet
been incorporated in Asia, which attenuates the measured correlation (the Epps /
nonsynchronous-trading effect). A fixed one-day lag fixes part of it but drops
the same-label overlap and mis-handles multi-session holiday gaps.

What this module provides (pure functions, bounded inputs, no I/O at import):

* an explicit UTC interval map per return (start/end close timestamp, DST
  offset change, early-close and skipped-session holiday flags);
* the Hayashi–Yoshida (HY) estimator over declared close timestamps, which uses
  every overlapping interval pair and is identified only when the close clocks
  are declared (missing timestamps -> ``UNKNOWN``, never a guessed lag);
* the declared competitors only (naive same-label, a fixed lag, bucket sums);
  no lag search on outcomes;
* distinct non-identification states — a measured zero return is ``MEASURED``,
  a missing observation is never zero-filled;
* moving-block bootstrap and Newey–West uncertainty with honest block counts;
* a PSD coherence report that never repairs (repair/shrinkage belongs to Q08).

Correlations are realized (uncentered) unless ``centered=True`` is requested.
|corr| > 1 is flagged, never clipped.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

RESEARCH_ONLY = True

MAX_OBS = 200_000  # hard input bound for every public function

# Interval / estimate states. A measured zero is MEASURED; absence is never zero.
MEASURED = "MEASURED"
NO_OVERLAP = "NO_OVERLAP"
UNKNOWN = "UNKNOWN"          # clock / timestamp not declared -> unidentified
INVALID = "INVALID"          # nonpositive / non-finite price or degenerate variance
EXCLUDED = "EXCLUDED"        # removed by an explicit declared exclusion
PENDING = "PENDING"          # interval not yet closed (end beyond the as-of bound)
INSUFFICIENT = "INSUFFICIENT"  # fewer pairs / observations than the declared minimum
STATES = (MEASURED, NO_OVERLAP, UNKNOWN, INVALID, EXCLUDED, PENDING, INSUFFICIENT)

# Pair clock classes
SIMULTANEOUS = "SIMULTANEOUS"
NONSYNCHRONOUS = "NONSYNCHRONOUS"
DST_VARYING = "DST_VARYING"
UNIDENTIFIED = "UNIDENTIFIED"


@dataclass(frozen=True)
class SessionSpec:
    """Declared session clock: IANA zone + regular local close ``HH:MM``."""

    name: str
    tz: str | None
    close_local: str | None

    def declared(self) -> bool:
        return bool(self.tz) and bool(self.close_local)


SSE = SessionSpec("SSE", "Asia/Shanghai", "15:00")
HKEX_INDEX = SessionSpec("HKEX_INDEX", "Asia/Hong_Kong", "16:10")
NYSE = SessionSpec("NYSE", "America/New_York", "16:00")


def _check_len(n: int, what: str = "input") -> None:
    if n > MAX_OBS:
        raise ValueError(f"{what} length {n} exceeds MAX_OBS={MAX_OBS}")


def _parse_hhmm(s: str) -> pd.Timedelta:
    hh, mm = s.split(":")
    h, m = int(hh), int(mm)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"bad HH:MM {s!r}")
    return pd.Timedelta(hours=h, minutes=m)


def close_timestamps_utc(dates: Iterable, spec: SessionSpec,
                         early_closes: Mapping | None = None) -> pd.DataFrame:
    """Map session date labels to UTC close instants.

    Returns a frame with ``end_utc`` (int64 epoch seconds), ``utc_offset_min``
    and ``early_close`` (bool). An undeclared spec yields ``state=UNKNOWN`` rows
    with no timestamps — callers must not substitute a guessed clock.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize()
    _check_len(len(idx), "dates")
    if not spec.declared():
        return pd.DataFrame({"date": idx, "end_utc": pd.array([pd.NA] * len(idx), dtype="Int64"),
                             "utc_offset_min": pd.array([pd.NA] * len(idx), dtype="Int64"),
                             "early_close": False, "state": UNKNOWN})
    reg = _parse_hhmm(spec.close_local)
    offs = pd.TimedeltaIndex([reg] * len(idx))
    early = np.zeros(len(idx), dtype=bool)
    if early_closes:
        ec = {pd.Timestamp(k).normalize(): _parse_hhmm(v) for k, v in early_closes.items()}
        vals = list(offs)
        for i, d in enumerate(idx):
            if d in ec:
                vals[i] = ec[d]
                early[i] = True
        offs = pd.TimedeltaIndex(vals)
    local = (idx + offs).tz_localize(spec.tz, ambiguous="raise", nonexistent="raise")
    utc = local.tz_convert("UTC")
    # asi8 is in the index's own unit; normalise to epoch seconds
    unit = np.datetime_data(utc.tz_localize(None).values.dtype)[0]
    scale = {"ns": 1_000_000_000, "us": 1_000_000, "ms": 1_000, "s": 1}[unit]
    end = (utc.asi8 // scale).astype(np.int64)
    off_min = np.array([int(t.utcoffset().total_seconds() // 60) for t in local], dtype=np.int64)
    return pd.DataFrame({"date": idx, "end_utc": end, "utc_offset_min": off_min,
                         "early_close": early, "state": MEASURED})


def return_intervals(dates: Sequence, closes: Sequence[float], spec: SessionSpec,
                     early_closes: Mapping | None = None,
                     exclude_dates: Iterable | None = None,
                     asof_utc: int | None = None) -> pd.DataFrame:
    """Close-to-close log returns with an explicit UTC interval map.

    Invalid prices (non-finite or <= 0) are removed and the following return is
    BRIDGED over the longer interval (``bridged_invalid``) — never zero-filled.
    Explicitly excluded dates are bridged the same way and counted. Rows carry
    ``holiday_gap`` (weekday sessions skipped between the two closes),
    ``dst_shift`` (UTC offset changed inside the interval), ``early_close`` and
    ``zero_return`` (a MEASURED zero, kept). Intervals ending after ``asof_utc``
    are ``PENDING``.
    """
    n = len(dates)
    _check_len(n, "dates")
    if len(closes) != n:
        raise ValueError("dates and closes differ in length")
    px = np.asarray(closes, dtype=float)
    ts = close_timestamps_utc(dates, spec, early_closes)
    excl = set()
    if exclude_dates is not None:
        excl = {pd.Timestamp(d).normalize() for d in exclude_dates}
    valid = np.isfinite(px) & (px > 0)
    is_excl = ts["date"].isin(excl).to_numpy() if excl else np.zeros(n, dtype=bool)
    keep = valid & ~is_excl
    order = np.argsort(ts["date"].to_numpy(), kind="stable")
    pos = np.empty(n, dtype=np.int64)
    pos[order] = np.arange(n)
    if n and ts["date"].duplicated().any():
        raise ValueError("duplicate session dates")
    keep_idx = [int(i) for i in order if keep[i]]
    rows = []
    for k in range(1, len(keep_idx)):
        i0, i1 = keep_idx[k - 1], keep_idx[k]
        skipped_raw = [int(j) for j in order[pos[i0] + 1:pos[i1]]]
        d0, d1 = ts["date"].iloc[i0], ts["date"].iloc[i1]
        wk = int(np.busday_count(d0.date(), d1.date())) - 1
        rows.append({
            "date": d1, "prev_date": d0,
            "start_utc": ts["end_utc"].iloc[i0], "end_utc": ts["end_utc"].iloc[i1],
            "ret": math.log(px[i1] / px[i0]),
            "holiday_gap": wk > 0, "skipped_weekdays": max(wk, 0),
            "dst_shift": (spec.declared() and int(ts["utc_offset_min"].iloc[i0]) != int(ts["utc_offset_min"].iloc[i1])),
            "early_close": bool(ts["early_close"].iloc[i1]),
            "bridged_invalid": any(not valid[j] for j in skipped_raw),
            "bridged_excluded": any(is_excl[j] for j in skipped_raw),
            "state": ts["state"].iloc[i1],
        })
    out = pd.DataFrame(rows, columns=["date", "prev_date", "start_utc", "end_utc", "ret",
                                      "holiday_gap", "skipped_weekdays", "dst_shift",
                                      "early_close", "bridged_invalid", "bridged_excluded",
                                      "state"])
    out["zero_return"] = out["ret"] == 0.0
    if asof_utc is not None and spec.declared() and len(out):
        out.loc[out["end_utc"].astype("int64") > int(asof_utc), "state"] = PENDING
    out.attrs["n_invalid_prices"] = int((~valid).sum())
    out.attrs["n_excluded_dates"] = int(is_excl.sum())
    out.attrs["n_rows_in"] = int(n)
    return out


def overlap_pairs(a_start, a_end, b_start, b_end) -> tuple[np.ndarray, np.ndarray]:
    """Index pairs (i, j) whose half-open intervals (start, end] overlap with
    positive length. Both series must be sorted and internally non-overlapping.
    Two-pointer sweep, O(n + m)."""
    as_, ae = np.asarray(a_start, dtype=np.int64), np.asarray(a_end, dtype=np.int64)
    bs, be = np.asarray(b_start, dtype=np.int64), np.asarray(b_end, dtype=np.int64)
    _check_len(len(as_), "a"), _check_len(len(bs), "b")
    if np.any(ae <= as_) or np.any(be <= bs):
        raise ValueError("intervals must have end > start")
    if np.any(as_[1:] < ae[:-1]) or np.any(bs[1:] < be[:-1]):
        raise ValueError("intervals must be sorted and non-overlapping")
    ia, ib = [], []
    i = j = 0
    n, m = len(as_), len(bs)
    while i < n and j < m:
        if max(as_[i], bs[j]) < min(ae[i], be[j]):
            ia.append(i)
            ib.append(j)
        if ae[i] < be[j]:
            i += 1
        elif be[j] < ae[i]:
            j += 1
        else:
            i += 1
            j += 1
    return np.asarray(ia, dtype=np.int64), np.asarray(ib, dtype=np.int64)


def hayashi_yoshida(ra, a_start, a_end, rb, b_start, b_end, min_pairs: int = 2) -> dict:
    """Hayashi–Yoshida covariance/correlation over declared intervals.

    Variances are the realized sums of squares over intervals that take part in
    at least one overlap pair. Missing timestamps -> ``UNKNOWN`` (no estimate);
    no overlap -> ``NO_OVERLAP``; fewer than ``min_pairs`` -> ``INSUFFICIENT``;
    zero or non-finite variance -> ``INVALID``. |corr| > 1 is flagged only.
    """
    ra, rb = np.asarray(ra, dtype=float), np.asarray(rb, dtype=float)
    _check_len(len(ra), "ra"), _check_len(len(rb), "rb")
    base = {"cov": None, "var_a": None, "var_b": None, "corr": None, "n_pairs": 0,
            "n_a_used": 0, "n_b_used": 0, "corr_out_of_bounds": False}
    try:
        sa = np.asarray(a_start, dtype=float)
        ea = np.asarray(a_end, dtype=float)
        sb = np.asarray(b_start, dtype=float)
        eb = np.asarray(b_end, dtype=float)
    except (TypeError, ValueError):
        return {**base, "state": UNKNOWN}
    if not (len(sa) == len(ea) == len(ra) and len(sb) == len(eb) == len(rb)):
        raise ValueError("returns and interval arrays differ in length")
    if (not np.all(np.isfinite(sa)) or not np.all(np.isfinite(ea))
            or not np.all(np.isfinite(sb)) or not np.all(np.isfinite(eb))):
        return {**base, "state": UNKNOWN}
    if not (np.all(np.isfinite(ra)) and np.all(np.isfinite(rb))):
        return {**base, "state": INVALID}
    if len(ra) == 0 or len(rb) == 0:
        return {**base, "state": NO_OVERLAP}
    ia, ib = overlap_pairs(sa.astype(np.int64), ea.astype(np.int64),
                           sb.astype(np.int64), eb.astype(np.int64))
    if len(ia) == 0:
        return {**base, "state": NO_OVERLAP}
    ua, ub = np.unique(ia), np.unique(ib)
    cov = float(np.sum(ra[ia] * rb[ib]))
    va, vb = float(np.sum(ra[ua] ** 2)), float(np.sum(rb[ub] ** 2))
    out = {**base, "cov": cov, "var_a": va, "var_b": vb, "n_pairs": int(len(ia)),
           "n_a_used": int(len(ua)), "n_b_used": int(len(ub))}
    if len(ia) < min_pairs:
        return {**out, "state": INSUFFICIENT}
    if not (va > 0 and vb > 0):
        return {**out, "state": INVALID}
    corr = cov / math.sqrt(va * vb)
    return {**out, "corr": corr, "corr_out_of_bounds": abs(corr) > 1.0, "state": MEASURED}


def realized_corr(x, y, centered: bool = False) -> float | None:
    """Realized (uncentered by default) correlation on already paired arrays."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    _check_len(len(x), "x")
    if len(x) != len(y) or len(x) < 2:
        return None
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        return None
    if centered:
        x, y = x - x.mean(), y - y.mean()
    den = math.sqrt(float(np.sum(x * x)) * float(np.sum(y * y)))
    if den <= 0:
        return None
    return float(np.sum(x * y)) / den


def naive_same_label(labels_a, ra, labels_b, rb, centered: bool = False) -> dict:
    """Incumbent-style complete-case join on the date label (E0)."""
    a = pd.Series(np.asarray(ra, dtype=float), index=pd.DatetimeIndex(labels_a))
    b = pd.Series(np.asarray(rb, dtype=float), index=pd.DatetimeIndex(labels_b))
    _check_len(len(a), "a"), _check_len(len(b), "b")
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    c = realized_corr(j["a"].to_numpy(), j["b"].to_numpy(), centered=centered)
    return {"corr": c, "n_matched": int(len(j)),
            "state": MEASURED if c is not None else INSUFFICIENT}


def lag_aligned(labels_a, ra, labels_b, rb, lag: int = 1, centered: bool = False) -> dict:
    """Pair each A return dated t with the B return ``lag`` B-sessions earlier
    (lag=1: the last B return dated strictly before t; lag=0: same label only).
    Declared competitor (E1); never chosen by searching outcomes.

    ``lag`` must be a non-negative integer count of sessions: daily closes carry
    no sub-session timing, so a fractional, boolean or vector lag is refused
    (``TypeError``) rather than silently implying intraday precision."""
    if isinstance(lag, (bool, np.bool_)) or not isinstance(lag, (int, np.integer)):
        raise TypeError("lag must be an integer number of sessions")
    if lag < 0:
        raise ValueError("lag must be >= 0")
    la = pd.DatetimeIndex(labels_a)
    lb = pd.DatetimeIndex(labels_b)
    _check_len(len(la), "a"), _check_len(len(lb), "b")
    ra, rb = np.asarray(ra, dtype=float), np.asarray(rb, dtype=float)
    if lag == 0:
        return naive_same_label(la, ra, lb, rb, centered=centered)
    order = np.argsort(lb.values, kind="stable")
    lbs, rbs = lb.values[order], rb[order]
    pos = np.searchsorted(lbs, la.values, side="left") - lag
    ok = pos >= 0
    x, y = ra[ok], rbs[pos[ok]]
    fin = np.isfinite(x) & np.isfinite(y)
    c = realized_corr(x[fin], y[fin], centered=centered)
    return {"corr": c, "n_matched": int(fin.sum()),
            "state": MEASURED if c is not None else INSUFFICIENT}


def bucket_sum_corr(buckets_a, ra, buckets_b, rb, centered: bool = False) -> dict:
    """Aggregate both series to integer buckets (e.g. weeks) by summing log
    returns, join buckets present in both, and correlate (E3)."""
    a = pd.Series(np.asarray(ra, dtype=float)).groupby(np.asarray(buckets_a)).sum()
    b = pd.Series(np.asarray(rb, dtype=float)).groupby(np.asarray(buckets_b)).sum()
    _check_len(len(ra), "a"), _check_len(len(rb), "b")
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    c = realized_corr(j["a"].to_numpy(), j["b"].to_numpy(), centered=centered)
    return {"corr": c, "n_buckets": int(len(j)),
            "state": MEASURED if c is not None else INSUFFICIENT}


def classify_pair_clock(spec_a: SessionSpec, spec_b: SessionSpec, dates: Iterable) -> dict:
    """Classify the close-clock relation over the given session dates."""
    d = list(dates)
    _check_len(len(d), "dates")
    if not (spec_a.declared() and spec_b.declared()):
        return {"clock": UNIDENTIFIED, "lag_seconds": None}
    ta = close_timestamps_utc(d, spec_a)["end_utc"].to_numpy(dtype=np.int64)
    tb = close_timestamps_utc(d, spec_b)["end_utc"].to_numpy(dtype=np.int64)
    diff = np.unique(tb - ta)
    if len(diff) == 1 and diff[0] == 0:
        clock = SIMULTANEOUS
    elif len(diff) == 1:
        clock = NONSYNCHRONOUS
    else:
        clock = DST_VARYING
    return {"clock": clock, "lag_seconds": sorted(int(x) for x in diff)}


def qualify_pair(iv_a: pd.DataFrame, iv_b: pd.DataFrame, min_pairs: int = 40) -> dict:
    """Interval-qualified HY record for two ``return_intervals`` frames.

    Only ``MEASURED`` intervals enter the estimator; all other states are
    counted in the support/attrition block (never zero-filled)."""
    _check_len(len(iv_a), "iv_a"), _check_len(len(iv_b), "iv_b")
    sup = {}
    for tag, iv in (("a", iv_a), ("b", iv_b)):
        st = iv["state"].value_counts().to_dict() if len(iv) else {}
        sup[tag] = {
            "n_intervals": int(len(iv)),
            "states": {k: int(v) for k, v in st.items()},
            "n_holiday_gap": int(iv["holiday_gap"].sum()) if len(iv) else 0,
            "n_dst_shift": int(iv["dst_shift"].sum()) if len(iv) else 0,
            "n_early_close": int(iv["early_close"].sum()) if len(iv) else 0,
            "n_zero_return": int(iv["zero_return"].sum()) if len(iv) else 0,
            "n_bridged_invalid": int(iv["bridged_invalid"].sum()) if len(iv) else 0,
            "n_invalid_prices": int(iv.attrs.get("n_invalid_prices", 0)),
        }
    if (len(iv_a) and (iv_a["state"] == UNKNOWN).any()) or (len(iv_b) and (iv_b["state"] == UNKNOWN).any()):
        return {"state": UNKNOWN, "hy": None, "support": sup}
    ma = iv_a[iv_a["state"] == MEASURED]
    mb = iv_b[iv_b["state"] == MEASURED]
    hy = hayashi_yoshida(ma["ret"].to_numpy(), ma["start_utc"].to_numpy(np.int64),
                         ma["end_utc"].to_numpy(np.int64), mb["ret"].to_numpy(),
                         mb["start_utc"].to_numpy(np.int64), mb["end_utc"].to_numpy(np.int64),
                         min_pairs=min_pairs)
    return {"state": hy["state"], "hy": hy, "support": sup}


def simulate_async_pair(n_days: int, rho: float, close_a_frac: float, close_b_frac: float,
                        steps_per_day: int = 48, vol_a: float = 0.01, vol_b: float = 0.01,
                        seed: int = 0, drop_days_a: Iterable[int] | None = None) -> dict:
    """Synthetic pair with known integrated correlation ``rho``.

    Two correlated Brownian log-prices on an integer step grid; A is observed at
    step ``day*steps + round(close_a_frac*steps)``, B likewise. ``drop_days_a``
    removes A observations (holidays) so the next A return spans several days.
    Returns integer-time intervals and log returns for both series.
    """
    if not (1 <= n_days <= MAX_OBS // max(1, steps_per_day)):
        raise ValueError("n_days out of bounds")
    if not (-1.0 <= rho <= 1.0) or not (0 <= close_a_frac < 1) or not (0 <= close_b_frac < 1):
        raise ValueError("bad rho / close fraction")
    rng = np.random.default_rng(seed)
    T = (n_days + 1) * steps_per_day
    z1 = rng.standard_normal(T)
    z2 = rho * z1 + math.sqrt(max(0.0, 1 - rho * rho)) * rng.standard_normal(T)
    s = 1.0 / math.sqrt(steps_per_day)
    pa = np.concatenate([[0.0], np.cumsum(vol_a * s * z1)])
    pb = np.concatenate([[0.0], np.cumsum(vol_b * s * z2)])
    oa = int(round(close_a_frac * steps_per_day))
    ob = int(round(close_b_frac * steps_per_day))
    drop = set(int(x) for x in (drop_days_a or ()))
    days_a = [d for d in range(n_days + 1) if d not in drop]
    days_b = list(range(n_days + 1))
    ta = np.array([d * steps_per_day + oa for d in days_a], dtype=np.int64)
    tb = np.array([d * steps_per_day + ob for d in days_b], dtype=np.int64)
    out = {}
    for tag, t, p, days in (("a", ta, pa, days_a), ("b", tb, pb, days_b)):
        out[tag] = {"day": np.asarray(days[1:], dtype=np.int64), "start": t[:-1], "end": t[1:],
                    "ret": np.diff(p[t])}
    out["rho"] = rho
    return out


def moving_block_bootstrap_mean(x, block_len: int, n_boot: int = 2000, seed: int = 0,
                                alpha: float = 0.05) -> dict:
    """Moving-block bootstrap of the mean of all finite entries of ``x``.

    ``x`` is (T,) or (T, P): rows are time blocks, columns are pairs; rows are
    resampled jointly so cross-pair dependence inside a time block is kept.
    Honest N is the number of distinct time rows with any finite entry.
    """
    a = np.asarray(x, dtype=float)
    if a.ndim == 1:
        a = a[:, None]
    if a.ndim != 2:
        raise ValueError("x must be 1-D or 2-D")
    _check_len(a.shape[0], "x")
    rows = np.isfinite(a).any(axis=1)
    a = a[rows]
    T = a.shape[0]
    if T < 2 or not (1 <= block_len <= T) or not (1 <= n_boot <= 100_000):
        return {"mean": float(np.nanmean(a)) if T else None, "ci_lo": None, "ci_hi": None,
                "se": None, "n_time_blocks": int(T), "state": INSUFFICIENT}
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block_len))
    starts_all = rng.integers(0, T - block_len + 1, size=(n_boot, nb))
    offs = np.arange(block_len)
    stats = np.empty(n_boot)
    for k in range(n_boot):
        ix = (starts_all[k][:, None] + offs[None, :]).ravel()[:T]
        stats[k] = np.nanmean(a[ix])
    lo, hi = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(np.nanmean(a)), "ci_lo": float(lo), "ci_hi": float(hi),
            "se": float(np.std(stats, ddof=1)), "n_time_blocks": int(T),
            "block_len": int(block_len), "n_boot": int(n_boot), "state": MEASURED}


def newey_west_se(x, lags: int) -> dict:
    """Newey–West (Bartlett) standard error of the mean of a 1-D series."""
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)]
    _check_len(len(v), "x")
    n = len(v)
    if n < 3 or lags < 0 or lags >= n:
        return {"mean": float(v.mean()) if n else None, "se": None, "n": n, "state": INSUFFICIENT}
    e = v - v.mean()
    s = float(np.dot(e, e)) / n
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        s += 2.0 * w * float(np.dot(e[l:], e[:-l])) / n
    s = max(s, 0.0)
    return {"mean": float(v.mean()), "se": math.sqrt(s / n), "n": n, "lags": int(lags),
            "state": MEASURED}


def psd_report(matrix, tol: float = 1e-10) -> dict:
    """Report PSD coherence of a correlation/covariance matrix. Never repairs."""
    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("square matrix required")
    _check_len(m.shape[0] * m.shape[0], "matrix cells")
    if not np.all(np.isfinite(m)):
        return {"state": INVALID, "min_eig": None, "is_psd": None, "symmetric": None,
                "n": int(m.shape[0]), "repaired": False}
    sym = bool(np.allclose(m, m.T, atol=1e-12))
    ev = np.linalg.eigvalsh((m + m.T) / 2.0)
    return {"state": MEASURED, "min_eig": float(ev[0]), "is_psd": bool(ev[0] >= -tol),
            "symmetric": sym, "n": int(m.shape[0]), "repaired": False}
