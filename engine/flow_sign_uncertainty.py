"""RESEARCH REFERENCE — NOT WIRED. Options trade-sign uncertainty and measurement-error calibration (Q04).

VERDICT (Q04, 2026-10 quant assessment): INSUFFICIENT_DATA for calibrated
aggressor probabilities and for signer accuracy. Retained local data holds NO
independent aggressor label. The missing input is a per-print, independently
sourced aggressor-side label joined to the same prints' NBBO, for example the
vendor tcbbo ``side`` field of the absent raw cache
``data/options_flow/_dbento_sample.parquet``. Every local "agreement" figure is
quote-rule self-consistency. This module therefore REFUSES to emit a calibrated
buy probability from quote-derived labels. What it does provide is a measured
edge-location-conditional report: which prints carry a sign under the
maintained edge-sign assumption below, and the bounds on net signed premium
that follow from it.

Maintained edge-sign assumption (``EDGE_SIGN_ASSUMPTION``)
----------------------------------------------------------
Every "identified" sign, bound and share here is CONDITIONAL on one maintained,
untested assumption: a print at the ask was buyer-initiated and a print at the
bid was seller-initiated. That is the quote rule's own premise, and with no
independent aggressor label it cannot be tested on retained data. The
``identified_*`` / ``net_identified`` / ``unidentified`` names are kept for
API stability and mean "under that assumption". Consequences:

* The bounds [N - U, N + U] are edge-location-conditional bounds. They are not
  sharp identified-set bounds without the assumption, and they are too narrow
  if any edge print is mis-signed (for example a seller lifting a stale ask or
  a complex/hedge leg printing at an edge).
* The unidentified share U is a LOWER BOUND on the true unidentified share:
  relaxing the assumption can only move edge premium into the ambiguous pool.

Scope and laws
--------------
* Research-only (``RESEARCH_ONLY = True``). Nothing imports this module. It
  registers nothing, schedules nothing, gates nothing, and reads no files or
  clocks at import.
* At-ask / at-bid are EXECUTION LOCATIONS, not buyers or sellers. They are
  mapped to a sign only under ``EDGE_SIGN_ASSUMPTION``.
* Agreement between two quote-derived signers is self-consistency, never
  aggressor accuracy (Lee & Ready 1991).
* Inside-spread, outside-spread, midpoint-tie, locked, crossed, stale,
  future-quote, no-quote and corrected/cancelled prints each get an explicit
  outcome. Where location does not identify the sign, the sign is ``None``,
  never a silent zero.
* No universal quote/trade time-lag constant exists here. The legacy
  Lee-Ready lag and the staleness limit are REQUIRED keyword arguments with
  no default.
* Production signing (``engine/flow_signing.py``) and its gate are untouched.
  The sidecar annotates a production sign and never changes it. The negative
  delta-adjustment evidence is preserved in
  ``DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE``.
* Honest N for correlated prints = distinct blocks (sessions), never rows.
"""
from __future__ import annotations

import math
from types import MappingProxyType
from typing import Iterable, Mapping, NamedTuple, Sequence

import numpy as np

RESEARCH_ONLY = True
VERDICT = "INSUFFICIENT_DATA"
EDGE_SIGN_ASSUMPTION = (
    "maintained, untested: at-ask print = buyer-initiated, at-bid print = seller-initiated "
    "(the quote rule's own premise); all identified signs/bounds are conditional on it, the "
    "bounds are too narrow if edge prints are mis-signed, and U is a lower bound on the true "
    "unidentified share"
)
MISSING_INPUT = (
    "independent per-print aggressor-side label for US option prints joined to "
    "the same prints' NBBO (e.g. vendor tcbbo `side` in "
    "data/options_flow/_dbento_sample.parquet, absent)"
)

# ── print outcomes ────────────────────────────────────────────────────────────
AT_ASK = "at_ask"
AT_BID = "at_bid"
INSIDE_ABOVE_MID = "inside_above_mid"
INSIDE_BELOW_MID = "inside_below_mid"
MIDPOINT_TIE = "midpoint_tie"
OUTSIDE_ABOVE = "outside_above"
OUTSIDE_BELOW = "outside_below"
LOCKED = "locked"
CROSSED = "crossed"
STALE_QUOTE = "stale_quote"
FUTURE_QUOTE = "future_quote"
NO_QUOTE = "no_quote"
CORRECTED = "corrected_or_cancelled"
INVALID_PRINT = "invalid_print"

PRINT_OUTCOMES = (
    AT_ASK, AT_BID, INSIDE_ABOVE_MID, INSIDE_BELOW_MID, MIDPOINT_TIE,
    OUTSIDE_ABOVE, OUTSIDE_BELOW, LOCKED, CROSSED, STALE_QUOTE, FUTURE_QUOTE,
    NO_QUOTE, CORRECTED, INVALID_PRINT,
)
# Outcomes excluded from the premium denominator (record retained, counted).
EXCLUDED_OUTCOMES = frozenset({CORRECTED, INVALID_PRINT})

# Tick-rule outcomes.
UPTICK = "uptick"
DOWNTICK = "downtick"
ZERO_TICK_CARRY = "zero_tick_carry"
ZERO_TICK_NO_PRIOR = "zero_tick_no_prior"
NO_PRIOR_TRADE = "no_prior_trade"

# Label provenance. Only the independent kinds can support accuracy or calibration.
INDEPENDENT_PROVENANCES = frozenset({
    "exchange_aggressor_flag", "vendor_side_field", "matched_order_audit",
})
QUOTE_DERIVED_PROVENANCES = frozenset({
    "quote_rule", "tick_rule", "lee_ready", "quote_rule_self_consistency",
    "production_side", "delta_adjusted", "execution_location",
})

# Requirement 6: negative evidence preserved verbatim (scripts/calibrate_flow_signing.py).
DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE: Mapping[str, object] = MappingProxyType({
    "tick_minute_agreement": 0.556,
    "delta_adjusted_minute_agreement": 0.526,
    "improves_direction": False,
    "source": "scripts/calibrate_flow_signing.py delta_adjusted block (unchanged)",
})


class IndependentLabelsRequired(ValueError):
    """Raised when calibration or accuracy is requested without independent labels."""


class PrintOutcome(NamedTuple):
    outcome: str
    identified_sign: int | None   # edge-location sign, conditional on EDGE_SIGN_ASSUMPTION
    quote_rule_sign: int | None   # what a midpoint quote rule would assert
    reason: str


def _finite_pos(x: float | None) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def classify_print(
    price: float | None,
    bid: float | None,
    ask: float | None,
    *,
    quote_age_ms: float | None,
    max_quote_age_ms: float | None,
    corrected: bool = False,
    atol: float = 1e-9,
) -> PrintOutcome:
    """Classify one print against its causally prior NBBO into an explicit outcome.

    ``max_quote_age_ms`` is REQUIRED. Pass an explicit value from a declared
    source contract, or ``None`` to state that no staleness rule applies.
    There is no default constant.
    """
    if corrected:
        return PrintOutcome(CORRECTED, None, None, "correction/cancel: excluded, record retained")
    if not _finite_pos(price):
        return PrintOutcome(INVALID_PRINT, None, None, "non-finite or non-positive price")
    if not (_finite_pos(bid) and _finite_pos(ask)):
        return PrintOutcome(NO_QUOTE, None, None, "no two-sided quote")
    if quote_age_ms is None or not math.isfinite(quote_age_ms):
        return PrintOutcome(NO_QUOTE, None, None, "quote time unknown: causal order unproven")
    if quote_age_ms < 0:
        return PrintOutcome(FUTURE_QUOTE, None, None, "quote stamped after trade")
    if max_quote_age_ms is not None and quote_age_ms > max_quote_age_ms:
        return PrintOutcome(STALE_QUOTE, None, None, "quote older than declared limit")
    if abs(ask - bid) <= atol:
        return PrintOutcome(LOCKED, None, None, "locked market: ask == bid")
    if ask < bid:
        return PrintOutcome(CROSSED, None, None, "crossed market: ask < bid")
    mid = (ask + bid) / 2.0
    qr = 1 if price > mid + atol else (-1 if price < mid - atol else None)
    if abs(price - ask) <= atol:
        return PrintOutcome(AT_ASK, 1, 1, "printed at ask")
    if abs(price - bid) <= atol:
        return PrintOutcome(AT_BID, -1, -1, "printed at bid")
    if price > ask:
        return PrintOutcome(OUTSIDE_ABOVE, None, qr, "outside spread (stale/complex/late): unidentified")
    if price < bid:
        return PrintOutcome(OUTSIDE_BELOW, None, qr, "outside spread (stale/complex/late): unidentified")
    if qr is None:
        return PrintOutcome(MIDPOINT_TIE, None, None, "midpoint tie: quote rule silent")
    if qr > 0:
        return PrintOutcome(INSIDE_ABOVE_MID, None, 1, "inside spread above mid: unidentified")
    return PrintOutcome(INSIDE_BELOW_MID, None, -1, "inside spread below mid: unidentified")


def tick_outcome(price: float, prev_price: float | None, prior_sign: int | None) -> tuple[str, int | None]:
    """Tick rule with explicit tie handling. A zero tick carries the prior sign or stays unsigned."""
    if prev_price is None or not math.isfinite(prev_price):
        return NO_PRIOR_TRADE, None
    if price > prev_price:
        return UPTICK, 1
    if price < prev_price:
        return DOWNTICK, -1
    if prior_sign in (1, -1):
        return ZERO_TICK_CARRY, int(prior_sign)
    return ZERO_TICK_NO_PRIOR, None


def order_prints(records: Sequence[Mapping], *, receipt_cutoff: float) -> tuple[list[dict], int]:
    """Keep prints received at or before ``receipt_cutoff``, in historical trade order.

    Trade order is (trade_ts, seq), with a stable sort so that ties keep the
    input (feed) order. Receipt time filters prints and never reorders them.
    Returns (ordered, n_received_after_cutoff).
    """
    kept = [dict(r) for r in records if float(r["receipt_ts"]) <= receipt_cutoff]
    late = len(records) - len(kept)
    kept.sort(key=lambda r: (float(r["trade_ts"]), float(r.get("seq", 0))))
    return kept, late


def align_quote_asof(trade_ts: float, quote_ts: Sequence[float], *, quote_lag_ms: float) -> int:
    """Index of the latest quote with quote_ts <= trade_ts - quote_lag_ms, else -1.

    ``quote_lag_ms`` is REQUIRED, with no default. The legacy Lee-Ready
    5-second lag is never assumed. ``quote_ts`` must be ascending.
    """
    q = np.asarray(quote_ts, dtype=float)
    if q.size and np.any(np.diff(q) < 0):
        raise ValueError("quote_ts must be ascending (historical order)")
    idx = int(np.searchsorted(q, trade_ts - float(quote_lag_ms), side="right")) - 1
    return idx


# ── edge-location-conditional bounds (under EDGE_SIGN_ASSUMPTION) ────────────

def bounds_from_prints(outcomes: Sequence[PrintOutcome], premiums: Sequence[float]) -> dict:
    """Edge-location-conditional bounds on the net signed premium share.

    S_id = sum(v * s) over edge (at-ask/at-bid) prints, V_amb = sum(v) over
    all other non-excluded prints, G = edge gross + V_amb (excluded outcomes
    are left out of G). Net share is bounded by [(S_id - V_amb)/G, (S_id + V_amb)/G].

    These bounds hold only under ``EDGE_SIGN_ASSUMPTION``; they are not sharp
    without it and are too narrow if an edge print is mis-signed. The returned
    ``unidentified`` share is a lower bound on the true unidentified share.
    """
    s_id = 0.0
    v_id = 0.0
    v_amb = 0.0
    n_excluded = 0
    for o, v in zip(outcomes, premiums):
        v = float(v)
        if o.outcome in EXCLUDED_OUTCOMES or not math.isfinite(v) or v <= 0:
            n_excluded += 1
            continue
        if o.identified_sign is None:
            v_amb += v
        else:
            s_id += v * o.identified_sign
            v_id += v
    g = v_id + v_amb
    if g <= 0:
        return {"gross": 0.0, "net_identified": None, "unidentified": None,
                "lower": None, "upper": None, "n_excluded": n_excluded}
    return {
        "gross": g,
        "net_identified": s_id / g,
        "unidentified": v_amb / g,
        "lower": (s_id - v_amb) / g,
        "upper": (s_id + v_amb) / g,
        "n_excluded": n_excluded,
    }


def event_bounds(coverage, at_ask_share, at_bid_share) -> dict:
    """Bounds from retained event fields (each null counts as 0, i.e. unidentified, never a sign).

    Returns unidentified U = 1 - c(a+b), net N = c(a-b), lower = N-U, upper = N+U.
    Conditional on ``EDGE_SIGN_ASSUMPTION``: U is a lower bound on the true
    unidentified share and [N-U, N+U] is too narrow if edge prints are mis-signed.
    """
    def _f(x):
        try:
            x = float(x)
        except (TypeError, ValueError):
            return float("nan")
        return x

    c, a, b = _f(coverage), _f(at_ask_share), _f(at_bid_share)
    c = 0.0 if not math.isfinite(c) else min(max(c, 0.0), 1.0)
    a = 0.0 if not math.isfinite(a) else min(max(a, 0.0), 1.0)
    b = 0.0 if not math.isfinite(b) else min(max(b, 0.0), 1.0)
    u = min(max(1.0 - c * (a + b), 0.0), 1.0)
    n = c * (a - b)
    return {"unidentified": u, "net_identified": n, "lower": n - u, "upper": n + u}


def event_bounds_arrays(coverage, at_ask_share, at_bid_share) -> dict:
    """Vectorised ``event_bounds`` (same null semantics)."""
    c = np.asarray(coverage, dtype=float)
    a = np.asarray(at_ask_share, dtype=float)
    b = np.asarray(at_bid_share, dtype=float)
    c = np.clip(np.where(np.isfinite(c), c, 0.0), 0.0, 1.0)
    a = np.clip(np.where(np.isfinite(a), a, 0.0), 0.0, 1.0)
    b = np.clip(np.where(np.isfinite(b), b, 0.0), 0.0, 1.0)
    u = np.clip(1.0 - c * (a + b), 0.0, 1.0)
    n = c * (a - b)
    return {"unidentified": u, "net_identified": n, "lower": n - u, "upper": n + u}


def label_is_identified(side: str, lower: float, upper: float) -> bool | None:
    """Is a production direction label robust to the edge-location-conditional bounds?

    True means the label's sign holds over [lower, upper] UNDER
    ``EDGE_SIGN_ASSUMPTION``; it is not evidence that the label is correct.
    Returns None for ``mixed`` and for unknown labels.
    """
    if side == "~buy":
        return bool(lower > 0)
    if side == "~sell":
        return bool(upper < 0)
    return None


# ── self-consistency vs accuracy ─────────────────────────────────────────────

def _provenance_kind(label_provenance: str) -> str:
    if label_provenance in INDEPENDENT_PROVENANCES:
        return "independent"
    if label_provenance in QUOTE_DERIVED_PROVENANCES:
        return "quote_derived"
    raise ValueError(f"unknown label provenance: {label_provenance!r}")


def agreement_report(sign_a: Sequence, sign_b: Sequence, *, label_provenance: str) -> dict:
    """Agreement between two sign vectors, named honestly.

    Accuracy is claimed only when ``sign_b`` comes from an independent
    provenance. Otherwise the metric is self-consistency.
    """
    kind = _provenance_kind(label_provenance)
    a = np.asarray(sign_a, dtype=float)
    b = np.asarray(sign_b, dtype=float)
    both = np.isfinite(a) & np.isfinite(b) & (a != 0) & (b != 0)
    n = int(both.sum())
    agree = float((a[both] == b[both]).mean()) if n else None
    return {
        "n_both_signed": n,
        "agreement": agree,
        "metric_kind": "aggressor_accuracy" if kind == "independent" else "self_consistency",
        "is_aggressor_accuracy": kind == "independent",
        "label_provenance": label_provenance,
    }


def disagreement_error_floor(sign_a: Sequence, sign_b: Sequence) -> dict:
    """Error lower bounds implied by disagreement between two signers.

    Each disagreeing print has at least one wrong signer, so
    err_a + err_b >= d and max(err_a, err_b) >= d / 2. This is a LOWER BOUND
    on error, never an accuracy estimate.
    """
    a = np.asarray(sign_a, dtype=float)
    b = np.asarray(sign_b, dtype=float)
    both = np.isfinite(a) & np.isfinite(b) & (a != 0) & (b != 0)
    n = int(both.sum())
    if n == 0:
        return {"n_both_signed": 0, "disagreement": None,
                "error_sum_floor": None, "max_error_floor": None}
    d = float((a[both] != b[both]).mean())
    return {"n_both_signed": n, "disagreement": d,
            "error_sum_floor": d, "max_error_floor": d / 2.0}


def calibrate_buy_probability(
    segments: Sequence[str],
    labels: Sequence[int] | None,
    *,
    label_provenance: str,
    shrinkage_k: float,
) -> dict:
    """Hierarchically shrunk P(aggressor = buyer) per segment, from INDEPENDENT labels only.

    ``labels`` holds 1 for a buyer aggressor and 0 for a seller. A
    quote-derived or missing label raises ``IndependentLabelsRequired``:
    fabricated calibrated buy probabilities are refused.
    """
    if labels is None or _provenance_kind(label_provenance) != "independent":
        raise IndependentLabelsRequired(
            "calibrated buy probabilities need independent aggressor labels; missing: " + MISSING_INPUT
        )
    seg = np.asarray(segments, dtype=object)
    y = np.asarray(labels, dtype=float)
    if seg.shape != y.shape or y.size == 0:
        raise ValueError("segments and labels must be non-empty and aligned")
    if not np.all((y == 0) | (y == 1)):
        raise ValueError("labels must be 0/1")
    k = float(shrinkage_k)
    if k < 0:
        raise ValueError("shrinkage_k must be >= 0")
    pooled = float(y.mean())
    out = {"pooled": pooled, "segments": {}}
    for s in sorted(set(seg.tolist())):
        m = seg == s
        n_s = int(m.sum())
        p = (float(y[m].sum()) + k * pooled) / (n_s + k)
        out["segments"][s] = {"n": n_s, "p_buy": p}
    return out


# ── preregistered split (requirement 4) ──────────────────────────────────────

def chronological_split(sessions, train_frac: float = 0.6) -> tuple[list, list]:
    """Earliest floor(train_frac * S) distinct sessions train; the later ones test."""
    uniq = sorted(set(np.asarray(sessions, dtype=object).tolist()))
    n_train = int(math.floor(train_frac * len(uniq)))
    return uniq[:n_train], uniq[n_train:]


def contract_disjoint_mask(train_keys: Iterable, test_keys: Sequence) -> np.ndarray:
    """True for test rows whose contract key never appears among training rows."""
    seen = set(train_keys)
    return np.array([k not in seen for k in test_keys], dtype=bool)


# ── segment shrinkage model for the unidentified share (H1) ──────────────────

def liquidity_edges(train_values) -> tuple[float, float]:
    """Tercile cut points fitted on TRAINING values only (non-finite values ignored)."""
    v = np.asarray(train_values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 3:
        raise ValueError("need >= 3 finite training values for terciles")
    q1, q2 = np.quantile(v, [1 / 3, 2 / 3])
    return float(q1), float(q2)


def assign_liquidity(values, edges: tuple[float, float]) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    out = np.full(v.shape, "liq_unknown", dtype=object)
    fin = np.isfinite(v)
    out[fin & (v <= edges[0])] = "liq_t1_tight"
    out[fin & (v > edges[0]) & (v <= edges[1])] = "liq_t2"
    out[fin & (v > edges[1])] = "liq_t3_wide"
    return out


def time_segment(minute_of_day) -> np.ndarray:
    """Wall-clock minute-of-day -> open [570,630), mid [630,870), late [870,975], else other."""
    m = np.asarray(minute_of_day, dtype=float)
    out = np.full(m.shape, "other", dtype=object)
    fin = np.isfinite(m)
    out[fin & (m >= 570) & (m < 630)] = "open"
    out[fin & (m >= 630) & (m < 870)] = "mid"
    out[fin & (m >= 870) & (m <= 975)] = "late"
    return out


def fit_cell_means(y, cells, k: float) -> dict:
    y = np.asarray(y, dtype=float)
    cells = np.asarray(cells, dtype=object)
    pooled = float(y.mean())
    means = {}
    for c in set(cells.tolist()):
        m = cells == c
        n_c = int(m.sum())
        means[c] = (float(y[m].sum()) + k * pooled) / (n_c + k) if (n_c + k) > 0 else pooled
    return {"pooled": pooled, "k": float(k), "means": means}


def predict_cells(model: Mapping, cells) -> np.ndarray:
    cells = np.asarray(cells, dtype=object)
    return np.array([model["means"].get(c, model["pooled"]) for c in cells.tolist()], dtype=float)


def choose_k_loso(y, cells, sessions, k_grid: Iterable[float]) -> tuple[float, dict]:
    """Choose shrinkage k by leave-one-session-out CV inside TRAINING; ties go to the larger k."""
    y = np.asarray(y, dtype=float)
    cells = np.asarray(cells, dtype=object)
    sessions = np.asarray(sessions, dtype=object)
    uniq = sorted(set(sessions.tolist()))
    if len(uniq) < 2:
        raise ValueError("need >= 2 training sessions for LOSO")
    scores = {}
    for k in sorted(set(float(x) for x in k_grid)):
        sse = 0.0
        for s in uniq:
            tr = sessions != s
            model = fit_cell_means(y[tr], cells[tr], k)
            pred = predict_cells(model, cells[~tr])
            sse += float(((y[~tr] - pred) ** 2).sum())
        scores[k] = sse / y.size
    best = min(scores.values())
    chosen = max(k for k, v in scores.items() if v <= best + 1e-15)
    return chosen, scores


def session_block_bootstrap_skill(
    sessions, sq_err_model, sq_err_base, *, n_boot: int, seed: int,
) -> dict:
    """Skill = 1 - SSE_model/SSE_base, with a session-block bootstrap percentile 95% CI.

    Sessions are resampled with replacement, so honest N = number of distinct sessions.
    """
    sessions = np.asarray(sessions, dtype=object)
    em = np.asarray(sq_err_model, dtype=float)
    eb = np.asarray(sq_err_base, dtype=float)
    uniq = sorted(set(sessions.tolist()))
    per_m = np.array([em[sessions == s].sum() for s in uniq], dtype=float)
    per_b = np.array([eb[sessions == s].sum() for s in uniq], dtype=float)
    point = 1.0 - per_m.sum() / per_b.sum() if per_b.sum() > 0 else float("nan")
    rng = np.random.default_rng(seed)
    nb = len(uniq)
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        j = rng.integers(0, nb, size=nb)
        den = per_b[j].sum()
        boots[i] = 1.0 - per_m[j].sum() / den if den > 0 else np.nan
    boots = boots[np.isfinite(boots)]
    lo, hi = (np.quantile(boots, [0.025, 0.975]).tolist() if boots.size else [float("nan")] * 2)
    return {"skill": float(point), "ci_lo": float(lo), "ci_hi": float(hi),
            "n_blocks": nb, "n_rows": int(em.size), "n_boot": int(n_boot)}


def session_block_bootstrap_mean(sessions, values, weights=None, *, n_boot: int, seed: int) -> dict:
    """Weighted mean with a session-block bootstrap 95% CI (honest N = sessions)."""
    sessions = np.asarray(sessions, dtype=object)
    v = np.asarray(values, dtype=float)
    w = np.ones_like(v) if weights is None else np.asarray(weights, dtype=float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    sessions, v, w = sessions[ok], v[ok], w[ok]
    uniq = sorted(set(sessions.tolist()))
    if not uniq:
        return {"mean": None, "ci_lo": None, "ci_hi": None, "n_blocks": 0, "n_rows": 0}
    num = np.array([(v * w)[sessions == s].sum() for s in uniq])
    den = np.array([w[sessions == s].sum() for s in uniq])
    rng = np.random.default_rng(seed)
    nb = len(uniq)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        j = rng.integers(0, nb, size=nb)
        boots[i] = num[j].sum() / den[j].sum()
    lo, hi = np.quantile(boots, [0.025, 0.975]).tolist()
    return {"mean": float(num.sum() / den.sum()), "ci_lo": float(lo), "ci_hi": float(hi),
            "n_blocks": nb, "n_rows": int(v.size)}


def effective_n(blocks) -> int:
    """Honest N for correlated prints: the number of distinct blocks."""
    return len(set(np.asarray(blocks, dtype=object).tolist()))


# ── preservation (requirement 6) ─────────────────────────────────────────────

def delta_adjustment_recommended() -> bool:
    """The preserved evidence says delta adjustment did not beat the tick rule."""
    return bool(DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE["improves_direction"])


def annotate_production_sign(production_sign, bounds: Mapping) -> dict:
    """Attach an uncertainty sidecar to a production sign WITHOUT altering it."""
    return {
        "production_sign": production_sign,
        "sidecar_unidentified_share": bounds.get("unidentified"),
        "sidecar_lower": bounds.get("lower"),
        "sidecar_upper": bounds.get("upper"),
        "sidecar_is_aggressor_accuracy": False,
    }


__all__ = [
    "RESEARCH_ONLY", "VERDICT", "MISSING_INPUT", "EDGE_SIGN_ASSUMPTION", "PRINT_OUTCOMES", "PrintOutcome",
    "IndependentLabelsRequired", "classify_print", "tick_outcome", "order_prints",
    "align_quote_asof", "bounds_from_prints", "event_bounds", "event_bounds_arrays",
    "label_is_identified", "chronological_split", "contract_disjoint_mask", "agreement_report", "disagreement_error_floor",
    "calibrate_buy_probability", "liquidity_edges", "assign_liquidity", "time_segment",
    "fit_cell_means", "predict_cells", "choose_k_loso", "session_block_bootstrap_skill",
    "session_block_bootstrap_mean", "effective_n", "DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE",
    "delta_adjustment_recommended", "annotate_production_sign",
]
