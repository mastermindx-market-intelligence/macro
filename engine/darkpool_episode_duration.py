"""RESEARCH REFERENCE — NOT WIRED. Q11 off-exchange activity episode-duration filter.

Verdict (Q11 quant assessment, 2026-10): KEEP as a research reference only (pre-registered
H1-H3 all met on semi-synthetic held-out injections, at about half the streak's untouched
alarm rate). It stays unwired; promotion would be a separate, gated decision. See
``research/quant_assessment_2026_10/Q11_offexchange_episode_duration/VERDICT.md``.

What it is
----------
A two-regime (Normal / Elevated) explicit-duration (hidden semi-Markov) forward filter on a
causally robust-standardized daily activity series (e.g. FINRA-facility off-exchange volume ÷
consolidated volume). It has Student-t emissions and a negative-binomial Elevated-sojourn
distribution. At every session it emits:

* ``p_elevated``: the filtered probability of the Elevated regime;
* the posterior duration of the Elevated regime (mean, sd, P(duration ≥ k));
* ``surprise``: the negative log one-step predictive density.

An alarm layer turns ``p_elevated`` into episodes with hysteresis. Each episode's DETECTION
index (the first session at which it was knowable) is kept separate from its RETROSPECTIVE
ONSET estimate. ``update_detection_records`` is an append-only, as-of record builder: a later
data vintage can never move an already-recorded detection earlier.

What it is NOT
--------------
* Not wired. Nothing imports it, it writes no file, emits no alert, and registers no event.
  It mints no event identity: records live only in the caller's memory.
* Not a direction, accumulation, distribution or intent read. A statistical activity regime is
  a venue/reporting-category activity state. FINRA short volume is not short interest or net
  buying, and ATS/non-ATS is a reporting category, not owner intent.
* Not a change to PSS-AF1 (DNR:HOLD-PSS-AF1-FINRA), the darkpool context labels, the forward
  ledger or any alert owner.
* Not tuned to returns: no price or return series is an input anywhere in this module.

Missing sessions are explicit NaN on a session calendar. A missing session is a
prediction-only step: it carries no likelihood and adds no observed evidence. Across a gap the
filtered probability only drifts toward its stationary level at the duration hazards; an
elevated probability is therefore non-increasing across the gap but decays slowly (mean
Elevated duration 20 sessions), so an open episode can span a gap of up to ``max_gap``
sessions. Only a gap longer than ``max_gap`` resets the filter and closes any open episode.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

RESEARCH_ONLY = True

# Module contract: what this module may do. The no-silent-activation test pins it.
CONTRACT: dict = {
    "wired": False,
    "consumers": (),
    "writes_files": False,
    "emits_alerts": False,
    "persists_records": False,
    "uses_returns_or_prices": False,
    "modifies_owners": (),  # darkpool_signals / darkpool_context / PSS-AF1 / alerts: unchanged
}

MAX_SERIES_LEN = 20_000
MAD_SCALE = 1.4826
_LOG_2PI = math.log(2.0 * math.pi)


# ---------------------------------------------------------------------------
# input standardization (causal)
# ---------------------------------------------------------------------------

def robust_activity_z(values: Sequence[float] | np.ndarray, *, window: int = 60,
                      min_hist: int = 20, mad_floor: float = 1e-3) -> np.ndarray:
    """Causal robust z of log activity on an explicit session calendar.

    ``values`` is aligned to the calendar, with NaN (or non-positive) for missing sessions.
    For each observed session t, the baseline is the median/MAD (×1.4826) of log values
    over the previous ``window`` OBSERVED sessions. The current value is excluded, and so are
    missing sessions: they are never interpolated. The output is NaN where the session is
    missing or fewer than ``min_hist`` prior observations exist.
    """
    v = np.asarray(values, dtype="float64")
    if v.ndim != 1:
        raise ValueError("values must be 1-D")
    if len(v) > MAX_SERIES_LEN:
        raise ValueError(f"series longer than {MAX_SERIES_LEN}")
    if window < 5 or min_hist < 5 or min_hist > window:
        raise ValueError("need 5 <= min_hist <= window")
    out = np.full(len(v), np.nan)
    obs_idx = np.flatnonzero(np.isfinite(v) & (v > 0))
    if len(obs_idx) <= min_hist:
        return out
    lv = np.log(v[obs_idx])
    n = len(lv)
    med = np.full(n, np.nan)
    mad = np.full(n, np.nan)
    # partial windows (fewer than `window` priors)
    for j in range(min_hist, min(window, n)):
        h = lv[:j]
        m = np.median(h)
        med[j], mad[j] = m, np.median(np.abs(h - m))
    if n > window:
        win = np.lib.stride_tricks.sliding_window_view(lv[:-1], window)  # win[i] = lv[i:i+window]
        m = np.median(win, axis=1)
        med[window:] = m
        mad[window:] = np.median(np.abs(win - m[:, None]), axis=1)
    scale = np.maximum(MAD_SCALE * mad, mad_floor)
    z = (lv - med) / scale
    out[obs_idx] = z
    return out


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DurationFilterParams:
    """Frozen filter parameters. Only ``nu`` and ``scale`` are fit (training data only)."""

    nu: float = 4.0                 # Student-t degrees of freedom (both regimes)
    scale: float = 1.0              # Student-t scale (both regimes)
    mu_elevated_sd: float = 1.0     # Elevated location, in units of ``scale``
    enter_hazard: float = 1.0 / 250.0
    mean_duration: float = 20.0     # Elevated sojourn mean (sessions)
    duration_shape: int = 2         # negative-binomial shape r (r=1 → geometric)
    max_duration: int = 120         # duration state cap; the last bin is absorbing
    max_gap: int = 5                # consecutive missing sessions tolerated before a reset

    def validate(self) -> None:
        if not (2.0 < self.nu <= 1e6):
            raise ValueError("nu must be > 2")
        if not (self.scale > 0):
            raise ValueError("scale must be > 0")
        if not (0 < self.enter_hazard < 1):
            raise ValueError("enter_hazard in (0,1)")
        if not (self.mean_duration > 1):
            raise ValueError("mean_duration > 1")
        if self.duration_shape < 1 or self.max_duration < 10 or self.max_duration > 2000:
            raise ValueError("bad duration settings")
        if self.max_gap < 0:
            raise ValueError("max_gap >= 0")


def exit_hazards(params: DurationFilterParams) -> np.ndarray:
    """h[d-1] = P(Elevated ends after d sessions | lasted d), for d = 1..max_duration.

    duration = 1 + K with K ~ NegBin(r, p) and mean 1 + r(1-p)/p = ``mean_duration``.
    """
    r = params.duration_shape
    p = r / (r + params.mean_duration - 1.0)
    D = params.max_duration
    k = np.arange(D + 1, dtype="float64")
    logpmf = (np.array([math.lgamma(r + kk) - math.lgamma(r) - math.lgamma(kk + 1) for kk in k])
              + r * math.log(p) + k * math.log1p(-p))
    pmf = np.exp(logpmf)
    surv = 1.0 - np.concatenate([[0.0], np.cumsum(pmf)[:-1]])  # P(K >= k)
    surv = np.maximum(surv, 1e-300)
    h = np.clip(pmf[:D] / surv[:D], 1e-12, 1.0 - 1e-12)
    return h


def _t_logpdf(x: float, loc: float, scale: float, nu: float) -> float:
    z = (x - loc) / scale
    return (math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2) - 0.5 * math.log(nu * math.pi)
            - math.log(scale) - (nu + 1) / 2 * math.log1p(z * z / nu))


@dataclass
class FilterPath:
    p_elevated: np.ndarray
    exp_duration: np.ndarray        # E[duration | Elevated], sessions (NaN-safe)
    sd_duration: np.ndarray
    p_duration_ge5: np.ndarray      # P(duration >= 5 | Elevated)
    surprise: np.ndarray            # -log predictive density (NaN on missing sessions)
    observed: np.ndarray            # bool
    gap_reset: np.ndarray           # bool: filter reset at this session after a long gap


def filter_path(x: Sequence[float] | np.ndarray, params: DurationFilterParams | None = None) -> FilterPath:
    """Forward (causal) filter. The output at t depends only on x[: t + 1]."""
    params = params or DurationFilterParams()
    params.validate()
    x = np.asarray(x, dtype="float64")
    if x.ndim != 1 or len(x) > MAX_SERIES_LEN:
        raise ValueError("x must be 1-D and bounded")
    n = len(x)
    D = params.max_duration
    h = exit_hazards(params)
    d_idx = np.arange(1, D + 1, dtype="float64")
    mu = params.mu_elevated_sd * params.scale
    hin = params.enter_hazard
    pN, pE = 1.0, np.zeros(D)
    out_p = np.zeros(n)
    out_m = np.full(n, np.nan)
    out_s = np.full(n, np.nan)
    out_g5 = np.full(n, np.nan)
    out_sur = np.full(n, np.nan)
    obs = np.isfinite(x)
    reset = np.zeros(n, dtype=bool)
    gap = 0
    for t in range(n):
        if not obs[t]:
            gap += 1
        if obs[t] and gap > params.max_gap:
            pN, pE = 1.0, np.zeros(D)
            reset[t] = True
        if obs[t]:
            gap = 0
        # predict
        stay = pE * (1.0 - h)
        newE = np.empty(D)
        newE[0] = pN * hin
        newE[1:] = stay[:-1]
        newE[-1] += stay[-1]
        newN = pN * (1.0 - hin) + float((pE * h).sum())
        if obs[t]:
            lN = _t_logpdf(x[t], 0.0, params.scale, params.nu)
            lE = _t_logpdf(x[t], mu, params.scale, params.nu)
            mx = max(lN, lE)
            wN, wE = math.exp(lN - mx), math.exp(lE - mx)
            sE = float(newE.sum())
            pred = newN * wN + sE * wE
            out_sur[t] = -(math.log(pred) + mx)
            newN *= wN
            newE = newE * wE
            tot = newN + float(newE.sum())
            newN /= tot
            newE /= tot
        pN, pE = newN, newE
        sE = float(pE.sum())
        out_p[t] = sE
        if sE > 1e-12:
            w = pE / sE
            m = float((w * d_idx).sum())
            out_m[t] = m
            out_s[t] = math.sqrt(max(float((w * d_idx * d_idx).sum()) - m * m, 0.0))
            out_g5[t] = float(w[4:].sum())
    return FilterPath(out_p, out_m, out_s, out_g5, out_sur, obs, reset)


# ---------------------------------------------------------------------------
# alarm layer: detection time vs retrospective onset
# ---------------------------------------------------------------------------

@dataclass
class Episode:
    detected_at: int                 # first session index at which the episode was knowable
    retro_onset_at_detection: int    # onset estimate made AT detection (<= detected_at)
    end_at: int | None = None        # first index at which the alarm switched off (None = open)
    n_observed: int = 0              # observed sessions inside the episode (missing excluded)
    closed_by: str | None = None     # "hysteresis" | "gap_reset" | None


def episodes_from_path(path: FilterPath, *, tau_on: float, tau_off: float | None = None) -> list[Episode]:
    """Hysteresis alarm on p_elevated. An episode can only open on an observed session."""
    if not (0 < tau_on < 1):
        raise ValueError("tau_on in (0,1)")
    tau_off = tau_on / 2.0 if tau_off is None else tau_off
    if not (0 <= tau_off <= tau_on):
        raise ValueError("0 <= tau_off <= tau_on")
    eps: list[Episode] = []
    cur: Episode | None = None
    for t in range(len(path.p_elevated)):
        if cur is not None and path.gap_reset[t]:
            cur.end_at, cur.closed_by = t, "gap_reset"
            cur = None
        p = path.p_elevated[t]
        if cur is None:
            if path.observed[t] and p >= tau_on:
                m = path.exp_duration[t]
                back = int(round(m)) - 1 if np.isfinite(m) else 0
                cur = Episode(detected_at=t, retro_onset_at_detection=max(t - max(back, 0), 0), n_observed=1)
                eps.append(cur)
        else:
            if p < tau_off:
                cur.end_at, cur.closed_by = t, "hysteresis"
                cur = None
            elif path.observed[t]:
                cur.n_observed += 1
    return eps


def onset_indicator(episodes: Iterable[Episode], n: int) -> np.ndarray:
    """Boolean array: True at each episode's DETECTION index (never at its retro onset)."""
    a = np.zeros(n, dtype=bool)
    for e in episodes:
        a[e.detected_at] = True
    return a


def update_detection_records(records: Sequence[dict], *, asof: int, x_asof: Sequence[float],
                             params: DurationFilterParams, tau_on: float,
                             tau_off: float | None = None) -> list[dict]:
    """Append-only as-of record builder (in memory; persists nothing, mints no global id).

    ``x_asof`` is the full series as known at as-of index ``asof`` (len == asof + 1), so it
    may include restated history. Existing records are returned unchanged, as a copy-prefix.
    A new ``detected`` record is stamped ``detected_at = asof``, the session at which this
    run first observed the open episode, even if the restated data would have alarmed
    earlier. The onset estimate is stored separately and never replaces ``detected_at``.

    If a record is open but the live episode was first detected after that record's
    ``detected_at`` (the old episode ended and a new one began between two runs), a ``closed``
    record for the old episode and a new ``detected`` record are both stamped at ``asof``.
    A revision that only moves the backfilled index of the same episode, not past the open
    record's ``detected_at``, appends nothing.
    """
    if len(x_asof) != asof + 1:
        raise ValueError("x_asof must cover sessions 0..asof exactly")
    out = [dict(r) for r in records]
    open_rec = None
    for r in out:
        if r["event"] == "detected":
            open_rec = r
        elif r["event"] == "closed":
            open_rec = None
    path = filter_path(x_asof, params)
    eps = episodes_from_path(path, tau_on=tau_on, tau_off=tau_off)
    live = eps[-1] if eps and eps[-1].end_at is None else None
    seq = sum(1 for r in out if r["event"] == "detected")

    def _detected() -> dict:
        return {"event": "detected", "episode_seq": seq + 1, "detected_at": asof,
                "retro_onset_estimate": min(live.retro_onset_at_detection, asof),
                "p_elevated": round(float(path.p_elevated[asof]), 6),
                "backfilled_detection_index": live.detected_at}

    if open_rec is None and live is not None:
        out.append(_detected())
    elif open_rec is not None and live is None:
        out.append({"event": "closed", "episode_seq": open_rec["episode_seq"], "closed_at": asof})
    elif open_rec is not None and live is not None and live.detected_at > open_rec["detected_at"]:
        # The open record's episode was live at its stamping session, so a live episode first
        # detected AFTER that session is a different, newer one: the old one closed between
        # runs. Close the old record and stamp the new episode at this as-of session.
        out.append({"event": "closed", "episode_seq": open_rec["episode_seq"], "closed_at": asof})
        out.append(_detected())
    return out


# ---------------------------------------------------------------------------
# training-only parameter fit (no returns, no evaluation data)
# ---------------------------------------------------------------------------

def fit_emission_params(x_train: Sequence[float] | np.ndarray, *, max_n: int = 200_000) -> tuple[float, float]:
    """MLE of Student-t (nu, scale) with location fixed at 0 on pooled TRAINING z values.

    A deterministic stride subsample bounds the cost. Returns (nu, scale), with nu clipped to [2.1, 50].
    """
    from scipy import stats  # local import: no scipy cost at module import

    x = np.asarray(x_train, dtype="float64")
    x = x[np.isfinite(x)]
    if len(x) < 200:
        raise ValueError("need >= 200 finite training values")
    if len(x) > max_n:
        x = x[:: int(math.ceil(len(x) / max_n))]
    nu, _loc, scale = stats.t.fit(x, floc=0.0)
    return float(min(max(nu, 2.1), 50.0)), float(scale)


def activation_status() -> dict:
    """Self-description used by the no-silent-activation test."""
    return {"research_only": RESEARCH_ONLY, **CONTRACT}


__all__ = [
    "RESEARCH_ONLY", "CONTRACT", "DurationFilterParams", "FilterPath", "Episode",
    "robust_activity_z", "exit_hazards", "filter_path", "episodes_from_path", "onset_indicator",
    "update_detection_records", "fit_emission_params", "activation_status",
]
