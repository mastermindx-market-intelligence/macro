"""Pre-registered leadership-rotation study harness (T11 part 1).

Measurement primitives for research/LEADERSHIP_ROTATION_PREREG_V1.md, frozen at
commit ``fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb`` (blob
``9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe``; NOT yet on origin/main).

DEVELOPMENT HARNESS -- no verdict authority. Every number this module produces
on P1 data is DEVELOPMENT-labelled (prereg section 6); the binding verdict
classes (SUPPORTED / CONSISTENT / NOT_SUPPORTED) belong to P2/P3, which are
seat acts and are NEVER executable here (``partition_mask`` raises
``PartitionSealed`` for them). Computing any outcome on real prices before the
prereg lands on main voids the study (prereg section 12, invalidator 6), so the
only I/O in this module is the git-object source loader and the prereg guard;
every measurement function is pure and runs on synthetic arrays in tests.

Conventions (prereg section 3 + ORCH-SCI rulings):
- R_t = log(P_num) - log(P_den) on total-return closes; indices are integer
  positions on the SPY session calendar (R1).
- A present close that is non-finite or <= 0 is SOURCE_INVALID; a missing row
  is UNMEASURED; neither is ever zero- or forward-filled (R2).
- All arms are past-only: the value at index t uses indices <= t only.
- Outcome states MATURED / IMMATURE / UNPRICEABLE / SOURCE_INVALID are kept
  distinct and never dropped from denominators; means are over MATURED only.
"""

from __future__ import annotations

import io
import subprocess

import numpy as np
import pandas as pd
from engine.leadership_rotation_context import pair_interpretation

__all__ = [
    "PREREG_PATH",
    "PREREG_COMMIT",
    "PREREG_BLOB_SHA",
    "SEED",
    "H_PRIMARY",
    "H_SECONDARY",
    "C",
    "WARMUP",
    "Z_LOOKBACK",
    "SIGMA_CHANGES",
    "Z_ENTER",
    "Z_EXIT",
    "A0_QUIET",
    "B2_LOOKBACK",
    "BETA_WINDOW",
    "B5_LOOKBACKS",
    "MARGIN_H2",
    "MARGIN_H3",
    "P1_START",
    "P1_END",
    "P2_EXCLUDED",
    "PAIRS",
    "OUTCOME_STATES",
    "SourceInvalid",
    "PartitionSealed",
    "PreregNotLanded",
    "PreregChanged",
    "load_closes_from_git",
    "session_calendar",
    "align",
    "source_flags",
    "log_ratio",
    "log_rel_to_spy",
    "first_eligible",
    "zscore",
    "hysteresis",
    "arm_a1",
    "arm_a2",
    "arm_a0",
    "arm_b1",
    "arm_b2",
    "arm_b3",
    "rolling_beta",
    "arm_b5_table",
    "arm_b6_carry",
    "arm_b7",
    "outcome",
    "policy_outcome",
    "cost_of_delay",
    "residual_outcome",
    "summarize_outcomes",
    "false_start_rate_h20",
    "all_event_coverage",
    "partition_mask",
    "assert_prereg_landed",
    "entry_context",
]

# ---------------------------------------------------------------------------
# Frozen prereg constants (LEADERSHIP_ROTATION_PREREG_V1.md sections 2-7)
# ---------------------------------------------------------------------------

PREREG_PATH = "research/LEADERSHIP_ROTATION_PREREG_V1.md"
PREREG_COMMIT = "fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb"
PREREG_BLOB_SHA = "9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe"
# V2 amendment (research/LEADERSHIP_ROTATION_PREREG_V2.md, 2026-10-14): H1 null
# reference, two-part size rule, G2 positive control, R13, C2. V1 stays frozen
# and is still required unchanged at every reading head (V2 section 0).
PREREG_V2_PATH = "research/LEADERSHIP_ROTATION_PREREG_V2.md"
PREREG_V2_BLOB_SHA = "1fcd151cfc4cdeb321789feb50d3fbb127cce056"
# V2.1 amendment (research/LEADERSHIP_ROTATION_PREREG_V2_1.md, 2026-10-14): VOIDED verdict
# class, clause->outcome-class table, alarm first-match precedence, Option A
# matching precision. Required landed and unchanged before any P1 read (run_p1).
PREREG_V2_1_PATH = "research/LEADERSHIP_ROTATION_PREREG_V2_1.md"
PREREG_V2_1_BLOB_SHA = "8f48509b65c70f7f3786402cba9b21940a907e83"
SEED = 20261014
H_PRIMARY = 20
H_SECONDARY = 63
C = 5  # delayed-confirmation sessions (prereg section 3)
WARMUP = 252  # pair warm-up sessions before the first formation date
Z_LOOKBACK = 20  # sessions in the A1/B3 z numerator
SIGMA_CHANGES = 63  # daily dR changes in the A1/B3 sigma window
Z_ENTER = 1.0
Z_EXIT = 0.0
A0_QUIET = 5  # consecutive non-positive sessions that suppress an A0 onset
B2_LOOKBACK = 63  # trailing sessions in the B2 momentum crossing
BETA_WINDOW = 252  # past-only OLS window (arm B4)
B5_LOOKBACKS = (1, 5, 20, 63)  # fixed multihorizon signs (arm B5)
MARGIN_H2 = 0.0050  # H2 practical margin, log-ratio units (+0.50 points)
MARGIN_H3 = 0.0025  # H3 residual margin, log-ratio units (+0.25 points)
P1_START = "2015-01-02"
P1_END = "2026-10-12"
P2_EXCLUDED = frozenset({"xlp_vs_smh"})

# Registered confirmatory cohort (prereg section 2, data/oracle/ratio_pairs.json
# v1.0 keyed by id): id -> (group, receiver/num, donor/den). Groups are NEVER
# pooled; every verdict is per group.
PAIRS = {
    "xlp_vs_xlk": ("defensive_sector", "XLP", "XLK"),
    "xlu_vs_xlk": ("defensive_sector", "XLU", "XLK"),
    "xlv_vs_xlk": ("defensive_sector", "XLV", "XLK"),
    "xlp_vs_smh": ("defensive_sector", "XLP", "SMH"),
    "dia_vs_qqq": ("broadening_proxy", "DIA", "QQQ"),
    "iwm_vs_qqq": ("broadening_proxy", "IWM", "QQQ"),
    "rsp_vs_qqq": ("broadening_proxy", "RSP", "QQQ"),
}

OUTCOME_STATES = ("MATURED", "IMMATURE", "UNPRICEABLE", "SOURCE_INVALID")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SourceInvalid(ValueError):
    """A committed source series is absent or unusable (loader only)."""


class PartitionSealed(RuntimeError):
    """P2/P3 are sealed: the look is a seat act, never executable here."""


class PreregNotLanded(RuntimeError):
    """The prereg document is not an ancestor of the reading head."""


class PreregChanged(RuntimeError):
    """The prereg blob at the reading head differs from the frozen blob."""


# ---------------------------------------------------------------------------
# Source (the only real I/O in the module)
# ---------------------------------------------------------------------------


def _git(repo: str, *args: str, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
    )


def load_closes_from_git(
    repo: str,
    commit: str,
    symbols,
    path_fmt: str = "data/yahoo/{sym}.parquet",
    column: str = "close",
):
    """Read each symbol's closes from COMMITTED git bytes only.

    Mirrors ``lib.store.read`` (parquet -> to_datetime index -> sorted) but
    reads ``<commit>:<path>`` through ``git cat-file`` -- never the working
    tree, never a write. Returns ``(closes, identity)`` where ``closes`` maps
    symbol -> float ``column`` Series and ``identity`` maps symbol ->
    ``{"path", "blob_sha", "commit"}``. Raises ``SourceInvalid`` naming the
    symbol and reason when the path is absent at the commit, the column is
    missing, or dates are duplicated.
    """
    closes: dict = {}
    identity: dict = {}
    for sym in symbols:
        path = path_fmt.format(sym=sym)
        probe = _git(repo, "rev-parse", f"{commit}:{path}")
        if probe.returncode != 0:
            raise SourceInvalid(
                f"{sym}: path absent at commit {commit}: {path} "
                f"({probe.stderr.strip()})"
            )
        blob = probe.stdout.strip()
        raw = _git(repo, "cat-file", "blob", blob, binary=True)
        if raw.returncode != 0:
            raise SourceInvalid(f"{sym}: blob {blob} unreadable at {path}")
        try:
            frame = pd.read_parquet(io.BytesIO(raw.stdout))
        except Exception as exc:  # noqa: BLE001 - surfaced as a source defect
            raise SourceInvalid(f"{sym}: parquet unreadable at {path}: {exc}") from exc
        if column not in frame.columns:
            raise SourceInvalid(f"{sym}: missing column {column!r} at {path}")
        index = pd.DatetimeIndex(pd.to_datetime(frame.index))
        if index.has_duplicates:
            raise SourceInvalid(f"{sym}: duplicate dates at {path}")
        try:
            values = frame[column].to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise SourceInvalid(f"{sym}: non-numeric {column!r} at {path}: {exc}") from exc
        closes[sym] = pd.Series(values, index=index, name=sym).sort_index()
        identity[sym] = {"path": path, "blob_sha": blob, "commit": commit}
    return closes, identity


# ---------------------------------------------------------------------------
# Calendar and measurement (pure; rulings R1/R2)
# ---------------------------------------------------------------------------


def session_calendar(spy_close) -> pd.DatetimeIndex:
    """NYSE session calendar = SPY dates with a non-NaN close (R1)."""
    return pd.DatetimeIndex(spy_close.dropna().index)


def align(close, calendar) -> np.ndarray:
    """Reindex a close series onto the calendar, no fill (R2)."""
    return close.reindex(pd.DatetimeIndex(calendar)).to_numpy(dtype=float)


def source_flags(aligned) -> tuple:
    """(measured, invalid) per R2: measured = finite and > 0; a present close
    that is non-finite or <= 0 is SOURCE_INVALID."""
    arr = np.asarray(aligned, dtype=float)
    measured = np.isfinite(arr) & (arr > 0.0)
    invalid = ~np.isnan(arr) & ~measured
    return measured, invalid


def log_ratio(num, den) -> tuple:
    """(R, invalid): R = log(num) - log(den) where BOTH legs are measured
    (else NaN); invalid = num_invalid | den_invalid (R2)."""
    num_measured, num_invalid = source_flags(num)
    den_measured, den_invalid = source_flags(den)
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where(num_measured & den_measured, np.log(num) - np.log(den), np.nan)
    return R, num_invalid | den_invalid


def log_rel_to_spy(num, spy) -> tuple:
    """Receiver-vs-SPY log ratio, same construction as ``log_ratio`` (B3)."""
    return log_ratio(num, spy)


def first_eligible(num, den):
    """First index t with >= WARMUP indices below t where BOTH legs are
    measured (prereg section 2 warm-up); None when never reached."""
    num_measured, _ = source_flags(num)
    den_measured, _ = source_flags(den)
    both = num_measured & den_measured
    running = np.cumsum(both)
    for t in range(1, len(both)):
        if running[t - 1] >= WARMUP:
            return t
    return None


# ---------------------------------------------------------------------------
# Arms (all past-only: the value at t uses indices <= t only)
# ---------------------------------------------------------------------------


def zscore(R) -> np.ndarray:
    """A1/B3 z: z_t = (R_t - R_{t-20}) / (sigma_t * sqrt(20)) where sigma_t is
    the ddof=1 stdev of the 63 daily changes dR_s = R_s - R_{s-1},
    s in [t-62, t]. NaN when any input is NaN, t is too early, or sigma_t = 0."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    z = np.full(n, np.nan)
    if n <= SIGMA_CHANGES:
        return z
    changes = np.diff(R)  # changes[j] = R_{j+1} - R_j
    scale = np.sqrt(H_PRIMARY)
    # Vectorized form of the original per-t loop (prereg V2 harness repair,
    # speed only): row i of ``win`` is changes[t-63:t] for t = 63 + i, i.e. dR
    # at s = t-62 .. t (ORCH-SCI window, R1). Each row is reduced on its own
    # contiguous copy with the same ``std(ddof=1)``, so the output is
    # bitwise-identical to the loop (pinned by
    # tests/test_leadership_rotation_study.py::test_zscore_vectorized_is_bitwise_identical_to_v1_loop).
    t = np.arange(SIGMA_CHANGES, n)
    win = np.ascontiguousarray(
        np.lib.stride_tricks.sliding_window_view(changes, SIGMA_CHANGES)[: n - SIGMA_CHANGES]
    )
    ok = ~(np.isnan(R[t]) | np.isnan(R[t - Z_LOOKBACK]) | np.isnan(win).any(axis=1))
    sigma = np.full(len(t), np.nan)
    if ok.any():
        sigma[ok] = win[ok].std(axis=1, ddof=1)
    good = ok & np.isfinite(sigma) & (sigma != 0.0)
    tg = t[good]
    z[tg] = (R[tg] - R[tg - Z_LOOKBACK]) / (sigma[good] * scale)
    return z


def hysteresis(z) -> tuple:
    """A1/B3 state machine (prereg section 4; NaN ruling R3).

    Enter when OFF and z >= +1.0; exit when ON and z <= 0.0; no re-entry while
    ON; a NaN z forces OFF with no exit recorded and no entry (the next entry
    needs z >= +1.0 again). Returns (state, entries, exits).
    """
    z = np.asarray(z, dtype=float)
    n = len(z)
    state = np.zeros(n, dtype=bool)
    entries: list = []
    exits: list = []
    on = False
    for t in range(n):
        zt = z[t]
        if np.isnan(zt):  # R3: forced OFF, no signal recorded either way
            on = False
            continue
        if not on:
            if zt >= Z_ENTER:
                on = True
                entries.append(t)
        elif zt <= Z_EXIT:
            on = False
            exits.append(t)
        state[t] = on
    return state, entries, exits


def arm_a1(R) -> tuple:
    """A1 challenger: ONE hysteresis setting, no grid (prereg section 4)."""
    return hysteresis(zscore(R))


def arm_a2(a1_state, a1_entries) -> tuple:
    """A2 delayed confirmation (R5): an entry at e is confirmed iff the A1
    state is ON at every index e+1..e+C; alarm date = e+C. When the calendar
    ends before e+C the entry is PENDING (counted, never an alarm)."""
    state = np.asarray(a1_state, dtype=bool)
    n = len(state)
    alarms: list = []
    pending: list = []
    for e in a1_entries:
        if e + C >= n:
            pending.append(e)
            continue
        if all(bool(state[e + i]) for i in range(1, C + 1)):
            alarms.append(e + C)
    return alarms, pending


def arm_a0(R) -> tuple:
    """A0 incumbent: raw = every t with R_t - R_{t-2} > 0 (both finite);
    onsets = raw t whose t-5..t-1 are all measured with R_s - R_{s-2} <= 0
    (>= 5 consecutive non-positive sessions; unmeasured day breaks the run,
    ruling R4)."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    diff2 = np.full(n, np.nan)
    if n > 2:
        diff2[2:] = R[2:] - R[:-2]
    raw: list = []
    onsets: list = []
    for t in range(2, n):
        if not (np.isfinite(R[t]) and np.isfinite(diff2[t]) and diff2[t] > 0.0):
            continue
        raw.append(t)
        quiet = True
        for s in range(t - A0_QUIET, t):  # t-5 .. t-1 (R4)
            if not (np.isfinite(R[s]) and np.isfinite(diff2[s]) and diff2[s] <= 0.0):
                quiet = False
                break
        if quiet:
            onsets.append(t)
    return raw, onsets


def arm_b1(R, start, end) -> list:
    """B1 unconditional drift: every measured formation day in [start, end]."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    lo = max(int(start), 0)
    hi = min(int(end), n - 1)
    return [t for t in range(lo, hi + 1) if np.isfinite(R[t])]


def arm_b2(R) -> list:
    """B2 trend: t where R_t - R_{t-63} > 0 and R_{t-1} - R_{t-64} <= 0 (the
    <= 0 -> > 0 crossing; all four values finite)."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    out: list = []
    for t in range(B2_LOOKBACK + 1, n):
        cur = R[t] - R[t - B2_LOOKBACK]
        prev = R[t - 1] - R[t - 1 - B2_LOOKBACK]
        if np.isfinite(cur) and np.isfinite(prev) and cur > 0.0 and prev <= 0.0:
            out.append(t)
    return out


def arm_b3(num, spy) -> tuple:
    """B3 receiver-vs-SPY leg momentum: same hysteresis form as A1 on
    log(num/SPY)."""
    rel, _invalid = log_rel_to_spy(num, spy)
    return hysteresis(zscore(rel))


def rolling_beta(x_logret, m_logret, window: int = BETA_WINDOW) -> np.ndarray:
    """Past-only OLS slope (with intercept) of x on m over s in [t-251, t].
    NaN when any of the window's pairs is non-finite or var(m) = 0."""
    x = np.asarray(x_logret, dtype=float)
    m = np.asarray(m_logret, dtype=float)
    n = len(x)
    beta = np.full(n, np.nan)
    finite = np.isfinite(x) & np.isfinite(m)
    xz = np.where(finite, x, 0.0)
    mz = np.where(finite, m, 0.0)
    cx = np.concatenate(([0.0], np.cumsum(xz)))
    cm = np.concatenate(([0.0], np.cumsum(mz)))
    cmm = np.concatenate(([0.0], np.cumsum(mz * mz)))
    cxm = np.concatenate(([0.0], np.cumsum(xz * mz)))
    cf = np.concatenate(([0], np.cumsum(finite.astype(np.int64))))
    for t in range(window - 1, n):
        lo = t - window + 1
        if int(cf[t + 1] - cf[lo]) != window:
            continue
        sx = cx[t + 1] - cx[lo]
        sm = cm[t + 1] - cm[lo]
        smm = cmm[t + 1] - cmm[lo]
        sxm = cxm[t + 1] - cxm[lo]
        var_m = smm - sm * sm / window
        if var_m == 0.0 or not np.isfinite(var_m):
            continue
        beta[t] = (sxm - sx * sm / window) / var_m
    return beta


def arm_b5_table(R, Y20, states) -> dict:
    """B5 descriptive table, NEVER an alarm list (prereg section 4): for each
    formation day whose four lookback differences are all finite, the sign
    pattern of R_t - R_{t-k} for k in B5_LOOKBACKS (4-char '+'/'-', 0 counts
    '-'); per pattern the count, the MATURED count and the mean MATURED Y_20."""
    R = np.asarray(R, dtype=float)
    Y20 = np.asarray(Y20, dtype=float)
    states = np.asarray(states, dtype=bool)
    table: dict = {}
    total = 0
    for t in range(max(B5_LOOKBACKS), len(R)):
        diffs = [R[t] - R[t - k] for k in B5_LOOKBACKS]
        if not all(np.isfinite(d) for d in diffs):
            continue
        pattern = "".join("+" if d > 0.0 else "-" for d in diffs)
        row = table.setdefault(pattern, {"count": 0, "matured": 0, "y20_sum": 0.0})
        row["count"] += 1
        total += 1
        if t < len(states) and bool(states[t]):
            row["matured"] += 1
            row["y20_sum"] += float(Y20[t])
    return {
        "patterns": {
            pattern: {
                "count": row["count"],
                "matured": row["matured"],
                "mean_y20_matured": (
                    row["y20_sum"] / row["matured"] if row["matured"] else None
                ),
            }
            for pattern, row in sorted(table.items())
        },
        "n_formations": total,
    }


def arm_b6_carry(R, a1_entries) -> tuple:
    """B6 carry / zero-new-return placebo (R12): z'_t is A1's z with R_t
    replaced by R_{t-1} (so dR'_t = 0 both in the numerator and inside the
    63-change sigma window); an A1 entry at t is a carry entry iff
    z'_t >= +1.0. Returns (flags, share)."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    if n == 0:
        return [False for _ in a1_entries], 0.0
    carry_R = np.concatenate(([np.nan], R[:-1]))
    z_carry = zscore(carry_R)
    flags = [bool(z_carry[t] >= Z_ENTER) for t in a1_entries]
    share = float(np.mean(flags)) if flags else 0.0
    return flags, share


def arm_b7() -> list:
    """B7 abstention: no alarms, ever (prereg section 4)."""
    return []


# ---------------------------------------------------------------------------
# Outcomes (prereg section 3; o = t+1)
# ---------------------------------------------------------------------------


def outcome(R, invalid, t: int, h: int, origin_offset: int = 1) -> tuple:
    """(state, y) for a formation day t with horizon h, origin o = t+offset.

    Precedence: an EXISTING endpoint flagged invalid -> SOURCE_INVALID; else an
    existing endpoint with NaN R -> UNPRICEABLE; else an endpoint beyond the
    calendar end -> IMMATURE; else MATURED with y = R_{o+h} - R_o. y is NaN
    unless MATURED. States are never dropped from denominators (section 3).
    """
    R = np.asarray(R, dtype=float)
    invalid = np.asarray(invalid, dtype=bool)
    n = len(R)
    o = t + origin_offset
    end = o + h
    for idx in (o, end):
        if 0 <= idx < n and invalid[idx]:
            return "SOURCE_INVALID", np.nan
    for idx in (o, end):
        if 0 <= idx < n and np.isnan(R[idx]):
            return "UNPRICEABLE", np.nan
    if o < 0 or o >= n or end >= n:
        return "IMMATURE", np.nan
    return "MATURED", float(R[end] - R[o])


def policy_outcome(R, invalid, t: int, h: int) -> tuple:
    """A2 policy path: origin o_c = t + c + 1 (prereg section 3; no free
    earlier execution)."""
    return outcome(R, invalid, t, h, origin_offset=1 + C)


def cost_of_delay(R, invalid, entries, h: int) -> dict:
    """A1 at the common origin o vs the policy origin o_c (prereg section 7).

    mean_y_o / mean_y_oc are means over each path's own MATURED entries;
    ``difference`` is the mean of y_o - y_oc over entries MATURED on BOTH
    paths; every per-state count is printed beside the means.
    """
    states_o = {s: 0 for s in OUTCOME_STATES}
    states_oc = {s: 0 for s in OUTCOME_STATES}
    path_o: dict = {}
    path_oc: dict = {}
    for t in entries:
        st_o, y_o = outcome(R, invalid, t, h, origin_offset=1)
        st_c, y_c = outcome(R, invalid, t, h, origin_offset=1 + C)
        states_o[st_o] += 1
        states_oc[st_c] += 1
        path_o[t] = (st_o, y_o)
        path_oc[t] = (st_c, y_c)

    def _mean(values):
        return float(np.mean(values)) if values else None

    both = [
        t
        for t in entries
        if path_o[t][0] == "MATURED" and path_oc[t][0] == "MATURED"
    ]
    return {
        "mean_y_o": _mean([y for st, y in path_o.values() if st == "MATURED"]),
        "mean_y_oc": _mean([y for st, y in path_oc.values() if st == "MATURED"]),
        "difference": _mean([path_o[t][1] - path_oc[t][1] for t in both]),
        "n_both": len(both),
        "states_o": states_o,
        "states_oc": states_oc,
    }


def residual_outcome(y, beta_num, beta_den, log_spy, o: int, h: int) -> float:
    """B4 residual target y_res = y - (beta_num - beta_den) * (log_spy[o+h] -
    log_spy[o]). The CALLER passes betas taken at index t = o - 1 (past-only);
    a NaN beta makes the residual NaN and the caller marks UNPRICEABLE with
    reason BETA_UNMEASURED."""
    if y is None or not np.isfinite(y):
        return float("nan")
    if not np.isfinite(beta_num) or not np.isfinite(beta_den):
        return float("nan")
    spy_o = float(log_spy[o])
    spy_h = float(log_spy[o + h])
    if not np.isfinite(spy_o) or not np.isfinite(spy_h):
        return float("nan")
    return float(y - (float(beta_num) - float(beta_den)) * (spy_h - spy_o))


def summarize_outcomes(results) -> dict:
    """MATURED mean (over MATURED only) plus printed counts of every other
    state -- never a mean over non-MATURED outcomes (prereg section 3)."""
    counts = {s: 0 for s in OUTCOME_STATES}
    ys: list = []
    total = 0
    for state, y in results:
        total += 1
        counts[state] = counts.get(state, 0) + 1
        if state == "MATURED" and np.isfinite(y):
            ys.append(float(y))
    return {
        "n": total,
        "counts": counts,
        "mean_y_matured": float(np.mean(ys)) if ys else None,
    }


def false_start_rate_h20(ys_matured) -> float:
    """Share of MATURED Y_20 <= 0 -- the section 7 H2 safety endpoint, distinct
    from the section 5 FALSE_START class. NaN when nothing has matured (never
    a fabricated 0.0)."""
    ys = np.asarray([v for v in ys_matured if np.isfinite(v)], dtype=float)
    if ys.size == 0:
        return float("nan")
    return float(np.mean(ys <= 0.0))


def all_event_coverage(R, invalid, first_eligible_idx, last_formation, h: int = H_PRIMARY) -> dict:
    """Section 7 clause 3 all-event coverage (prereg section 7).

    Denominator = every calendar index in [first_eligible, last_formation];
    each day is classed UNMEASURED (R_t NaN) or by ``outcome``; numerator =
    MATURED with finite y. UNMEASURED days stay in the denominator, never
    reclassified as zero (section 3).
    """
    R = np.asarray(R, dtype=float)
    invalid = np.asarray(invalid, dtype=bool)
    counts = {"UNMEASURED": 0, **{s: 0 for s in OUTCOME_STATES}}
    denominator = 0
    numerator = 0
    for t in range(first_eligible_idx, last_formation + 1):
        denominator += 1
        if np.isnan(R[t]):
            counts["UNMEASURED"] += 1
            continue
        state, y = outcome(R, invalid, t, h)
        counts[state] += 1
        if state == "MATURED" and np.isfinite(y):
            numerator += 1
    return {
        "coverage": (numerator / denominator) if denominator else float("nan"),
        "denominator": denominator,
        "numerator": numerator,
        "counts": counts,
    }


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def partition_mask(calendar, partition: str) -> np.ndarray:
    """Boolean calendar mask for a partition (prereg section 6).

    "P1" -> dates in [P1_START, P1_END] inclusive. "P0" has no calendar mask
    (synthetic is drawn, never masked) -> ValueError. "P2"/"P3" are sealed:
    the holdout/prospective look is a seat act, never executable here ->
    PartitionSealed.
    """
    idx = pd.DatetimeIndex(calendar)
    if partition == "P1":
        start = pd.Timestamp(P1_START)
        end = pd.Timestamp(P1_END)
        return np.asarray((idx >= start) & (idx <= end), dtype=bool)
    if partition == "P0":
        raise ValueError("P0 is synthetic: it has no calendar mask to apply")
    if partition in ("P2", "P3"):
        raise PartitionSealed(
            f"{partition} is sealed: opening that look is a seat act, never "
            "executable in this harness"
        )
    raise ValueError(f"unknown partition {partition!r}")


def assert_prereg_landed(
    repo: str,
    head: str = "HEAD",
    main_ref: str = "origin/main",
    path: str = PREREG_PATH,
    blob_sha: str = PREREG_BLOB_SHA,
) -> dict:
    """The prereg must already be on main and unchanged at the reading head.

    ``add`` is the OLDEST commit of ``git log --diff-filter=A`` on main_ref
    (a squash merge of the prereg PR makes ``add`` the squash commit -- that
    is intended). No such commit, or ``add`` not an ancestor of head, raises
    PreregNotLanded; a head blob differing from the frozen blob raises
    PreregChanged.
    """
    log = _git(repo, "log", "--diff-filter=A", "--format=%H", main_ref, "--", path)
    adds = [line.strip() for line in log.stdout.splitlines() if line.strip()]
    if log.returncode != 0 or not adds:
        raise PreregNotLanded(f"no commit on {main_ref} adds {path}")
    add = adds[-1]  # git log prints newest-first; the oldest add is the landing
    ancestry = _git(repo, "merge-base", "--is-ancestor", add, head)
    if ancestry.returncode != 0:
        raise PreregNotLanded(
            f"prereg add commit {add} is not an ancestor of {head}"
        )
    blob = _git(repo, "rev-parse", f"{head}:{path}")
    found = blob.stdout.strip()
    if blob.returncode != 0 or found != blob_sha:
        raise PreregChanged(
            f"{path} at {head} is {found or 'absent'}, expected frozen {blob_sha}"
        )
    return {"add_commit": add, "blob_sha": blob_sha, "head": head}


def assert_protocol_landed(
    repo: str,
    head: str = "HEAD",
    main_ref: str = "origin/main",
) -> dict:
    """V1 AND V2 must both be on main and unchanged at the reading head.

    V2 section 6: the protocol identity for every read after the amendment is
    the V2 landing commit; V1's blob must also be untouched (V1 section 12.7).
    Raises PreregNotLanded / PreregChanged exactly as assert_prereg_landed.
    """
    v1 = assert_prereg_landed(
        repo, head=head, main_ref=main_ref, path=PREREG_PATH, blob_sha=PREREG_BLOB_SHA
    )
    v2 = assert_prereg_landed(
        repo, head=head, main_ref=main_ref, path=PREREG_V2_PATH, blob_sha=PREREG_V2_BLOB_SHA
    )
    return {"v1": v1, "v2": v2, "head": head}


# ---------------------------------------------------------------------------
# Contract consumer (read-only import; engine module is never edited here)
# ---------------------------------------------------------------------------


def entry_context(num, den, t: int, lookback: int = Z_LOOKBACK) -> dict:
    """Interpret a pair at t through the measured-product contract: simple
    returns of each leg over [t - lookback, t] feed
    ``pair_interpretation(r_receiver=num_ret, r_donor=den_ret)``; its result
    (including an ``Unmeasured``) is returned unchanged."""
    num_ret = float(num.iloc[t] / num.iloc[t - lookback] - 1.0)
    den_ret = float(den.iloc[t] / den.iloc[t - lookback] - 1.0)
    return pair_interpretation(r_receiver=num_ret, r_donor=den_ret)
