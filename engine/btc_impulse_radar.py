"""BTC forward IMPULSE-PRESSURE radar — DISPLAY-ONLY (P0).

The complaint this answers: the rest of Vector describes the *standing regime*
("bearish"), which persists by construction and never escalates — useless for
calling tops/bottoms/flushes. This module is the opposite: a FORWARD-pressure
gauge built ONLY from adversarially-verified LEADING precursors, that fires on a
threshold *cross*, escalates, and DECAYS back to quiet. It is distinct from the
regime read and NEVER sums with it.

Two separate 0-100 gauges (UP and DOWN). Each gauge's legs SUM to its headline
(house style of btc_leverage_cascade's one-sided gate, generalised). Each leg
contributes points only when its verified trigger condition is met, then decays
geometrically — so absent fresh crosses the gauge bleeds back to `quiet` within
a few days. That is the anti-"permanently-on" mechanism, in four parts:
  1. legs fire on a leak-free leading feature's threshold CROSS, never on the
     standing regime label (the regime is explicitly NOT a leg);
  2. the one "new-low" deepening bonus (D1/cbp) is BOUNDED — first 2 bars of a
     fresh cross only, and gated on a benign trailing return, so it cannot pin
     the gauge during a sustained selloff;
  3. every leg DECAYS the moment its condition stops being met;
  4. the radar lives in its own field, never added to the regime composite.

Legs (sized by 2024+ holdout lift x source independence, NOT by June-24
performance — every act leg below MISSED the 2026-06-24 options-calm flush, and
we deliberately do not penalise/reward that). Provenance: the radar builds its
OWN causal z-scores / trailing percentiles (.shift(1), no centering, no
full-sample fit) from raw series rather than trusting precomputed *_pctile/*_z
columns (research/VECTOR_IMPULSE_PREDICTION.md §4.5).

  DOWN gauge
    D2  dvol_range_z60 >= 2.0 (2nd close >=1.5 confirms)        act    40  (Deribit dvol)
    D3  sopr_z90 > 2.0 AND sopr > 1.02 AND 5d-up               act    30  (bgeo sopr)
    D1  cbp_z90 < -1.0 (>=2 of last 3) + bounded deepening      context 15  (coinbase_premium)
    FUEL  oi_pctile >= .70 AND vov_pctile >= .60 & rising       context 15  (coil spring)
    CASCADE  leverage cascade_risk in {elevated,high} OR        context 15  (btc_leverage_cascade)
             OI-only break (oi_pctile >= .80)
  UP gauge
    U1  sopr_z90 < -1.5 AND already down >=5%/5d               act    30  (bgeo sopr; reactive
             wash-out → leads the BOUNCE ~2d, NOT a pre-rally oracle)

cascade_risk verdicts and the honest lead/coincidence record live in
research/VECTOR_IMPULSE_PREDICTION.md. This module is wired into build_vector as
a context leg (`context_legs["impulse_radar"]`); it sizes nothing and emits no
alert yet (alerts/UI = P1, falsifier = P3).

Config (under `btc_impulse_radar:` in config.yml; all optional, in-code
defaults apply when absent):
  enabled: true
  horizon_days: 6        # decay lookback for a leg's most-recent fire
  cbp_z_w: 90 ; dvol_z_w: 60 ; sopr_z_w: 90 ; pctile_w: 252
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

# Ladder thresholds (score -> state). Shared by both gauges.
_LADDER = (("quiet", 0, 15), ("coiled", 15, 35), ("warning", 35, 60), ("trigger", 60, 101))


def _f(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _ladder(score: float, has_act: bool) -> str:
    """Ladder state. CONTEXT legs alone can only load the gauge to `coiled`;
    `warning`/`trigger` REQUIRE a live act-tier precursor cross. This is what
    keeps a chronically-elevated context backdrop (crowded OI + US selling) from
    masquerading as an acute impulse warning — the exact failure the user hit."""
    if score >= 60:
        return "trigger" if has_act else "coiled"
    if score >= 35:
        return "warning" if has_act else "coiled"
    if score >= 15:
        return "coiled"
    return "quiet"



def _evidence_date(value) -> date | None:
    """Parse one contract date without ever defaulting to the wall clock."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


def _permission_result(identity: str, evaluation: date | None, *, reason: str,
                       permitted: bool = False, direction: str | None = None,
                       validation_asof: date | None = None,
                       validation_age_days: int | None = None,
                       gate_read_state: str = "unknown", gate_path: str | None = None,
                       gate_status: str = "unknown", stats: list[dict] | None = None,
                       target: dict | None = None, model_version=None) -> dict:
    """Always-same permission shape; refusal is data, never an exception."""
    return {
        "identity": identity,
        "permitted": bool(permitted),
        "reason": reason,
        "direction": direction,
        "evaluation_date": evaluation.isoformat() if evaluation else None,
        "validation_asof": validation_asof.isoformat() if validation_asof else None,
        "validation_age_days": validation_age_days,
        "validation_state": (
            "current" if reason in {"eligible", "demoted", "insufficient_n", "no_data",
                                     "unknown_status", "inconsistent_verdict",
                                     "leg_contract_mismatch", "leg_evidence_malformed",
                                     "leg_malformed", "leg_missing",
                                     "legs_contract_mismatch"}
            else reason
        ),
        "gate_read_state": gate_read_state,
        "gate_path": gate_path,
        "gate_status": gate_status,
        "stats": stats or [],
        "target": target or {},
        "model_version": model_version,
        "version_state": "present" if model_version not in (None, "") else "absent",
    }


def resolve_leg_permission(gate_snapshot, identity: str, evaluation_date) -> dict:
    """Resolve current permission for one exact BTC impulse identity.

    This is the sole authority resolver.  It consumes the validator's existing
    artifact contract; it does not invent a schema/version and it never consults
    ``all_pass``.  Raw causal fire history remains independent of this decision.
    Validation age 0 or 1 UTC days is current; every unreadable, malformed,
    future, stale, contradictory, or non-leading state fails closed.
    """
    evaluation = _evidence_date(evaluation_date)
    directions = {"d2": "down", "d3": "down", "u1": "up", "d2+d3": "down"}
    if identity not in directions:
        return _permission_result(identity, evaluation, reason="unknown_identity")
    direction = directions[identity]
    if evaluation is None:
        return _permission_result(identity, None, reason="evaluation_time_invalid",
                                  direction=direction)

    read_state, artifact, gate_path = "ok", gate_snapshot, None
    if isinstance(gate_snapshot, dict) and "read_state" in gate_snapshot:
        read_state = str(gate_snapshot.get("read_state") or "unknown")
        artifact = gate_snapshot.get("artifact")
        gate_path = gate_snapshot.get("path")
    if read_state == "missing":
        return _permission_result(identity, evaluation, reason="gate_missing",
                                  direction=direction, gate_read_state=read_state,
                                  gate_path=gate_path)
    if read_state == "corrupt" or not isinstance(artifact, dict):
        return _permission_result(identity, evaluation, reason="gate_corrupt",
                                  direction=direction, gate_read_state=read_state,
                                  gate_path=gate_path)
    if read_state != "ok" or not artifact or artifact.get("ok") is not True:
        return _permission_result(identity, evaluation, reason="gate_unavailable",
                                  direction=direction, gate_read_state=read_state,
                                  gate_path=gate_path)

    # Import at call time: the evaluator imports this module for raw conditions.
    from engine import btc_impulse_radar_backtest as evaluator

    target_label = f"fwd({evaluator.LABEL_H}d) +-{int(evaluator.LABEL_THR * 100)}%"
    target = {
        "label": target_label,
        "bars": evaluator.LABEL_H,
        "calendar": "BTC_24_7",
        "window": f"(t,t+{evaluator.LABEL_H}d]",
        "down_threshold": -evaluator.LABEL_THR,
        "up_threshold": evaluator.LABEL_THR,
    }
    model_version = (artifact.get("model_version") or artifact.get("rule_version")
                     or artifact.get("schema_version"))
    if artifact.get("label") != target_label:
        return _permission_result(identity, evaluation, reason="target_mismatch",
                                  direction=direction, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)

    validation = _evidence_date(artifact.get("asof"))
    if validation is None:
        return _permission_result(identity, evaluation, reason="validation_time_invalid",
                                  direction=direction, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)
    age = (evaluation - validation).days
    if age < 0:
        return _permission_result(identity, evaluation, reason="future_validation",
                                  direction=direction, validation_asof=validation,
                                  validation_age_days=age, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)
    if age >= 2:
        return _permission_result(identity, evaluation, reason="stale_validation",
                                  direction=direction, validation_asof=validation,
                                  validation_age_days=age, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)

    legs = artifact.get("legs")
    if not isinstance(legs, dict):
        return _permission_result(identity, evaluation, reason="legs_contract_mismatch",
                                  direction=direction, validation_asof=validation,
                                  validation_age_days=age, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)
    known = set(evaluator.LEGS)
    if any(key not in known for key in legs):
        return _permission_result(identity, evaluation, reason="legs_contract_mismatch",
                                  direction=direction, validation_asof=validation,
                                  validation_age_days=age, gate_read_state=read_state,
                                  gate_path=gate_path, target=target,
                                  model_version=model_version)

    requested = ["d2", "d3"] if identity == "d2+d3" else [identity]
    stats: list[dict] = []
    statuses: list[str] = []
    for key in requested:
        if key not in legs:
            return _permission_result(identity, evaluation, reason="leg_missing",
                                      direction=direction, validation_asof=validation,
                                      validation_age_days=age, gate_read_state=read_state,
                                      gate_path=gate_path, target=target,
                                      model_version=model_version)
        row = legs[key]
        if not isinstance(row, dict):
            return _permission_result(identity, evaluation, reason="leg_malformed",
                                      direction=direction, validation_asof=validation,
                                      validation_age_days=age, gate_read_state=read_state,
                                      gate_path=gate_path, target=target,
                                      model_version=model_version)
        status = row.get("status")
        if status not in {"leading", "demoted", "insufficient_n", "no_data"}:
            return _permission_result(identity, evaluation, reason="unknown_status",
                                      direction=direction, validation_asof=validation,
                                      validation_age_days=age, gate_read_state=read_state,
                                      gate_path=gate_path, target=target,
                                      model_version=model_version)
        statuses.append(status)
        expected = evaluator.LEGS[key]
        if status != "no_data":
            actual_direction = row.get("dir")
            if "direction" in row and row.get("direction") != actual_direction:
                return _permission_result(identity, evaluation,
                                          reason="leg_contract_mismatch",
                                          direction=direction, validation_asof=validation,
                                          validation_age_days=age,
                                          gate_read_state=read_state, gate_path=gate_path,
                                          target=target, model_version=model_version)
            contract_ok = (
                actual_direction == expected["dir"]
                and row.get("label") == expected["label"]
                and row.get("floor") == expected["floor"]
                and row.get("min_holdout_n") == evaluator.MIN_HOLDOUT_N
            )
            if not contract_ok:
                return _permission_result(identity, evaluation,
                                          reason="leg_contract_mismatch",
                                          direction=direction, validation_asof=validation,
                                          validation_age_days=age,
                                          gate_read_state=read_state, gate_path=gate_path,
                                          target=target, model_version=model_version)
            expected_pass = status == "leading"
            if row.get("pass") is not expected_pass:
                return _permission_result(identity, evaluation,
                                          reason="inconsistent_verdict",
                                          direction=direction, validation_asof=validation,
                                          validation_age_days=age,
                                          gate_read_state=read_state, gate_path=gate_path,
                                          target=target, model_version=model_version)
            # A refusal status already fails closed and should remain explicit even
            # when old artifacts omit its diagnostic measurements.  Only a row that
            # seeks current ``leading`` authority must prove the measurements that
            # earned that label; never let status/pass labels self-authorize.
            if status == "leading":
                n_holdout = row.get("n_fires_holdout")
                lift_holdout = row.get("lift_holdout")
                perm_p = row.get("perm_p")
                count_valid = (
                    isinstance(n_holdout, (int, np.integer))
                    and not isinstance(n_holdout, (bool, np.bool_))
                    and int(n_holdout) >= 0
                )
                lift_valid = (
                    isinstance(lift_holdout, (int, float, np.integer, np.floating))
                    and not isinstance(lift_holdout, (bool, np.bool_))
                    and np.isfinite(float(lift_holdout))
                )
                p_valid = (
                    isinstance(perm_p, (int, float, np.integer, np.floating))
                    and not isinstance(perm_p, (bool, np.bool_))
                    and np.isfinite(float(perm_p))
                    and 0.0 <= float(perm_p) <= 1.0
                )
                if not count_valid or not lift_valid or not p_valid:
                    return _permission_result(identity, evaluation,
                                              reason="leg_evidence_malformed",
                                              direction=direction, validation_asof=validation,
                                              validation_age_days=age,
                                              gate_read_state=read_state, gate_path=gate_path,
                                              target=target, model_version=model_version)
                measured_leading = (
                    int(n_holdout) >= int(evaluator.MIN_HOLDOUT_N)
                    and float(lift_holdout) >= float(expected["floor"])
                    and float(perm_p) <= float(evaluator.P_MAX)
                )
                if not measured_leading:
                    return _permission_result(identity, evaluation,
                                              reason="inconsistent_verdict",
                                              direction=direction, validation_asof=validation,
                                              validation_age_days=age,
                                              gate_read_state=read_state, gate_path=gate_path,
                                              target=target, model_version=model_version)
        elif row.get("pass") not in (None, False):
            return _permission_result(identity, evaluation,
                                      reason="inconsistent_verdict",
                                      direction=direction, validation_asof=validation,
                                      validation_age_days=age, gate_read_state=read_state,
                                      gate_path=gate_path, target=target,
                                      model_version=model_version)
        stats.append({
            "leg": key,
            "status": status,
            "direction": expected["dir"],
            "label": expected["label"],
            "floor": expected["floor"],
            "min_holdout_n": evaluator.MIN_HOLDOUT_N,
            "lift_full": row.get("lift_full"),
            "lift_holdout": row.get("lift_holdout"),
            "perm_p": row.get("perm_p"),
            "n_fires_full": row.get("n_fires_full"),
            "n_fires_holdout": row.get("n_fires_holdout"),
        })

    if "demoted" in statuses:
        reason = "demoted"
    elif "insufficient_n" in statuses:
        reason = "insufficient_n"
    elif "no_data" in statuses:
        reason = "no_data"
    else:
        reason = "eligible"
    return _permission_result(
        identity, evaluation, reason=reason, permitted=reason == "eligible",
        direction=direction, validation_asof=validation, validation_age_days=age,
        gate_read_state=read_state, gate_path=gate_path, gate_status=reason,
        stats=stats, target=target, model_version=model_version,
    )


def _causal_z(s: pd.Series, w: int) -> pd.Series:
    """Trailing z-score, leak-free: mean/std use a window ending at t-1."""
    mu = s.rolling(w).mean().shift(1)
    sd = s.rolling(w).std().shift(1)
    return (s - mu) / sd.replace(0.0, np.nan)


def _causal_pctile(s: pd.Series, w: int) -> pd.Series:
    """Trailing percentile of the CURRENT value within the last w bars (incl.
    current, no future). 0..1. Leak-free (uses only data up to t)."""
    return s.rolling(w, min_periods=max(20, w // 4)).rank(pct=True)


def _leg_points(cond: pd.Series, max_pts: float, decay: float, horizon: int) -> dict:
    """Points for a leg evaluated at the LAST bar, given its fire-condition
    boolean series. Full points on a fresh fire, decayed by `decay`**days_since
    for older fires, zero beyond `horizon` days. This is the decay that prevents
    a permanently-on gauge."""
    c = cond.fillna(False)
    if c.empty:
        return {"points": 0.0, "fired_today": False, "days_since": None}
    recent = c.iloc[-(horizon + 1):]
    trues = [i for i, v in enumerate(recent.to_numpy()) if v]
    if not trues:
        return {"points": 0.0, "fired_today": False, "days_since": None}
    days_since = (len(recent) - 1) - trues[-1]
    pts = max_pts * (decay ** days_since)
    if pts < 1.0:
        pts = 0.0
    return {"points": round(float(pts), 1), "fired_today": days_since == 0,
            "days_since": int(days_since)}


def _leg(key, label, tier, pts_info, max_pts, honesty) -> dict:
    evidence = pts_info.get("evidence") or {}
    demoted = bool(pts_info.get("demoted"))
    if demoted:
        status = str(evidence.get("status") or "denied").upper()
        honesty = honesty + f" · [EVIDENCE: {status} — act points zeroed]"
    return {"key": key, "label": label, "tier": tier, "max": max_pts,
            "points": pts_info["points"], "fired_today": pts_info["fired_today"],
            "days_since": pts_info["days_since"], "honesty": honesty,
            "demoted": demoted, "evidence": evidence}


# Act-tier leg fire conditions — the alert-relevant crosses. Shared by compute()
# (tail eval + decay) and fire_series() (alert transitions) so a bell can never
# drift from the gauge. Each returns a per-bar boolean Series on `index`.
def _d2_cond(rng: pd.Series, dvol_w: int, index) -> pd.Series:
    z = _causal_z(rng, dvol_w).reindex(index)
    return (z >= 2.0) | ((z >= 1.5) & (z.shift(1) >= 1.5))      # 2.0, or 2nd-confirm >=1.5


def _d3_cond(sopr: pd.Series, sopr_w: int, p5: pd.Series, index) -> pd.Series:
    sz = _causal_z(sopr, sopr_w).reindex(index)
    return (sz > 2.0) & (sopr.reindex(index) > 1.02) & (p5 > 0)  # leading top-exhaustion


def _u1_cond(sopr: pd.Series, sopr_w: int, p5: pd.Series, index) -> pd.Series:
    sz = _causal_z(sopr, sopr_w).reindex(index)
    return (sz < -1.5) & (p5 <= -0.05)                          # reactive wash-out bounce


def fire_series(sig_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-day act-tier leg fire booleans over FULL history (d2/d3 DOWN, u1 UP).
    Drives the alert engine's transition detection. Returns an empty frame on any
    failure / missing inputs (never raises). Columns present only when buildable."""
    try:
        cfg = config.load().get("btc_impulse_radar", {}) or {}
        dvol_w = int(cfg.get("dvol_z_w", 60))
        sopr_w = int(cfg.get("sopr_z_w", 90))
        if sig_df is None:
            sig_df = store.read("vector", "signals")
        if sig_df is None or sig_df.empty:
            return pd.DataFrame()
        df = sig_df.copy(); df.index = pd.to_datetime(df.index); df = df.sort_index()
        p5 = df["close"] / df["close"].shift(5) - 1.0
        out = {}
        try:
            dv = store.read("deribit", "dvol")
            if dv is not None and not dv.empty and {"dvol_high", "dvol_low", "dvol_close"} <= set(dv.columns):
                dv = dv.copy(); dv.index = pd.to_datetime(dv.index); dv = dv.sort_index()
                rng = (dv["dvol_high"] - dv["dvol_low"]) / dv["dvol_close"]
                if rng.dropna().shape[0] >= dvol_w:
                    out["d2"] = _d2_cond(rng, dvol_w, df.index).fillna(False)
        except Exception as e:  # noqa: BLE001
            log.debug("fire_series d2 skipped: %s", e)
        try:
            sp = store.read("bgeo", "sopr")
            if sp is not None and not sp.empty:
                sp = sp.copy(); sp.index = pd.to_datetime(sp.index)
                sopr = sp["sopr"].sort_index()
                if sopr.dropna().shape[0] >= sopr_w:
                    out["d3"] = _d3_cond(sopr, sopr_w, p5, df.index).fillna(False)
                    out["u1"] = _u1_cond(sopr, sopr_w, p5, df.index).fillna(False)
        except Exception as e:  # noqa: BLE001
            log.debug("fire_series sopr skipped: %s", e)
        return pd.DataFrame(out, index=df.index)
    except Exception as e:  # noqa: BLE001
        log.debug("fire_series failed: %s", e)
        return pd.DataFrame()


def compute(sig_df: pd.DataFrame | None = None, *, gate: dict | None = None,
            board_date=None) -> dict:
    """Build the forward impulse-pressure radar. Never raises."""
    try:
        cfg = config.load().get("btc_impulse_radar", {}) or {}
        if not cfg.get("enabled", True):
            return {"ok": False, "reason": "btc_impulse_radar disabled in config"}

        horizon = int(cfg.get("horizon_days", 6))
        cbp_w = int(cfg.get("cbp_z_w", 90))
        dvol_w = int(cfg.get("dvol_z_w", 60))
        sopr_w = int(cfg.get("sopr_z_w", 90))
        pct_w = int(cfg.get("pctile_w", 252))

        if sig_df is None:
            sig_df = store.read("vector", "signals")
        if sig_df is None or sig_df.empty:
            return {"ok": False, "reason": "signals.parquet not found"}
        df = sig_df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        close = df["close"]
        asof = str(df.index[-1].date())

        p3 = close / close.shift(3) - 1.0
        p5 = close / close.shift(5) - 1.0

        # Evidence gate: an act leg receives points only from an exact, current
        # passport. Read failure, version drift, future/stale validation, demotion,
        # underpowered samples, and expiry all fail closed.
        from engine import signal_evidence
        gate_receipt = signal_evidence.load_btc_gate() if gate is None else gate
        passport_date = board_date if board_date is not None else asof
        evidence = {
            key: signal_evidence.impulse_passport(
                key, event_at=asof, event_precision="date",
                board_date=passport_date, source_asof=asof, gate=gate_receipt,
            )
            for key in ("d2", "d3", "u1")
        }

        def _gate(key, pts):
            """Attach the receipt and zero every leg lacking current authority."""
            out = dict(pts)
            out["evidence"] = evidence[key]
            if not evidence[key]["claim_eligible"]:
                out.update({"points": 0.0, "fired_today": False,
                            "days_since": None, "demoted": True})
            return out

        down_legs: list[dict] = []
        up_legs: list[dict] = []

        # ---- D2: DVOL intraday-range jolt (act, 40) — Deribit dvol OHLC ---- #
        d2 = {"points": 0.0, "fired_today": False, "days_since": None}
        try:
            dv = store.read("deribit", "dvol")
            if dv is not None and not dv.empty and {"dvol_high", "dvol_low", "dvol_close"} <= set(dv.columns):
                dv = dv.copy(); dv.index = pd.to_datetime(dv.index); dv = dv.sort_index()
                rng = (dv["dvol_high"] - dv["dvol_low"]) / dv["dvol_close"]
                if rng.dropna().shape[0] >= dvol_w:
                    d2 = _leg_points(_d2_cond(rng, dvol_w, df.index), 40, 0.5, horizon)
        except Exception as e:  # noqa: BLE001 — leg is optional
            log.debug("D2 dvol leg skipped: %s", e)
        down_legs.append(_leg("d2_dvol", "Vol-of-vol jolt (DVOL range)", "act", _gate("d2", d2), 40,
                              "Observed DVOL-range condition; the current passport controls authority. Blind to slow/options-calm flushes."))

        # ---- SOPR legs: D3 (act down 30) + U1 (act up 30) — bgeo sopr ---- #
        d3 = {"points": 0.0, "fired_today": False, "days_since": None}
        u1 = {"points": 0.0, "fired_today": False, "days_since": None}
        try:
            sp = store.read("bgeo", "sopr")
            if sp is not None and not sp.empty:
                sp = sp.copy(); sp.index = pd.to_datetime(sp.index)
                sopr = sp["sopr"].sort_index()
                if sopr.dropna().shape[0] >= sopr_w:
                    d3 = _leg_points(_d3_cond(sopr, sopr_w, p5, df.index), 30, 0.5, horizon)
                    u1 = _leg_points(_u1_cond(sopr, sopr_w, p5, df.index), 30, 0.5, horizon)
        except Exception as e:  # noqa: BLE001
            log.debug("SOPR legs skipped: %s", e)
        down_legs.append(_leg("d3_sopr", "SOPR profit-take spike", "act", _gate("d3", d3), 30,
                              "Observed SOPR profit-take condition; the current passport controls authority. Blind when SOPR stays neutral."))
        up_legs.append(_leg("u1_sopr", "SOPR capitulation (wash-out)", "act", _gate("u1", u1), 30,
                            "Reactive wash-out observation after a deep drop; current passport controls authority. Not a pre-rally oracle."))

        # ---- D1: coinbase-premium z (context 15) + BOUNDED deepening ---- #
        d1 = {"points": 0.0, "fired_today": False, "days_since": None}
        deepen = 0.0
        if "coinbase_premium" in df.columns and df["coinbase_premium"].dropna().shape[0] >= cbp_w:
            cz = _causal_z(df["coinbase_premium"], cbp_w)
            d1_cond = ((cz < -1.0).rolling(3).sum() >= 2)
            d1 = _leg_points(d1_cond, 15, 0.6, horizon)
            # bounded deepening: only in the first 2 bars of a FRESH cross AND
            # only if the move had not yet started (trailing-3d ret >= -2% at onset).
            cc = d1_cond.fillna(False)
            if d1["fired_today"]:
                onset_pos = None
                arr = cc.to_numpy()
                for i in range(len(arr) - 1, max(len(arr) - 4, 0) - 1, -1):
                    if i > 0 and arr[i] and not arr[i - 1]:
                        onset_pos = i; break
                if onset_pos is not None:
                    bars_since_onset = (len(arr) - 1) - onset_pos
                    onset_p3 = _f(p3.iloc[onset_pos])
                    if bars_since_onset <= 1 and onset_p3 is not None and onset_p3 >= -0.02:
                        deepen = 8.0
        d1["points"] = round(min(d1["points"] + deepen, 15 + 8), 1)
        down_legs.append(_leg("d1_cbp", "US spot selling (Coinbase premium)", "context", d1, 15,
                              "Context-only: lift ~0.8 full / 1.12 holdout, largely COINCIDENT (fires when already falling). Deepening bonus bounded."))

        # ---- FUEL: OI x vov coincidence (context 15, coil spring) ---- #
        oi_pctile = vov_pctile = None
        fuel_lit = False
        fuel = {"points": 0.0, "fired_today": False, "days_since": None}
        if "oi_mcap_ratio" in df.columns and "vol_of_vol" in df.columns:
            oip = _causal_pctile(df["oi_mcap_ratio"], pct_w)
            vovp = _causal_pctile(df["vol_of_vol"], pct_w)
            vov_rising = df["vol_of_vol"] > df["vol_of_vol"].shift(5)
            fuel_cond = (oip >= 0.70) & (vovp >= 0.60) & vov_rising
            fuel = _leg_points(fuel_cond, 15, 0.7, horizon)
            oi_pctile = _f(oip.iloc[-1]); vov_pctile = _f(vovp.iloc[-1])
            fuel_lit = bool(fuel_cond.fillna(False).iloc[-1])
        down_legs.append(_leg("fuel", "Fuel: OI crowding x vol-of-vol rising", "context", fuel, 15,
                              "Coil-spring context (loading, not firing). OI percentile is anti-predictive standalone — never an act-call."))

        # ---- CASCADE: leverage gate (context 15, step) + OI-only break ---- #
        casc = {"points": 0.0, "fired_today": False, "days_since": None}
        cascade_risk = "low"; oi_only = "low"
        try:
            from engine import btc_leverage_cascade
            lev = btc_leverage_cascade.compute(df)
            if lev.get("ok"):
                cascade_risk = lev.get("cascade_risk", "low")
                # OI-only de-risk break (prior suggestion #1): the cascade module's
                # funding-independent OI-crowding flag — crowded OI warns on its own.
                oi_only = lev.get("oi_only_risk", "low")
                lit = cascade_risk in ("elevated", "high") or oi_only in ("elevated", "high")
                if lit:
                    casc = {"points": 15.0, "fired_today": cascade_risk == "high",
                            "days_since": 0}
        except Exception as e:  # noqa: BLE001
            log.debug("cascade leg skipped: %s", e)
        down_legs.append(_leg("cascade", "Leverage cascade / OI-only de-risk", "context", casc, 15,
                              "De-risk context. OI-only break lets crowded-but-not-euphoric OI warn (low-conviction, never an act crash-call)."))

        # ---- aggregate ---- #
        down_score = min(round(sum(l["points"] for l in down_legs)), 100)
        up_score = min(round(sum(l["points"] for l in up_legs)), 100)
        down_act = any(l["tier"] == "act" and l["points"] > 0 for l in down_legs)
        up_act = any(l["tier"] == "act" and l["points"] > 0 for l in up_legs)

        # ---- staleness (prior suggestion #4) ---------------------------------- #
        # TRUTHFUL signal = freshness of the committed INTRADAY DATA, not the flash
        # sentinel's heartbeat. The sentinel commits flash_state.json ONLY on a
        # state CHANGE (sentinel.yml: "no heartbeat spam"), so its last_eval lags
        # by design and would cry wolf. What actually matters for catching a flush
        # is: how old is the freshest hourly candle? If the intraday feed is >1d
        # behind the daily close, an intraday flush would be unseen.
        intraday_asof = None; stale = False; last_flash_change = None
        try:
            h = store.read("coinbase", "btc_hourly")
            if h is not None and not h.empty:
                last_h = pd.to_datetime(h.index).max()
                intraday_asof = str(last_h)
                stale = (pd.Timestamp(asof).normalize() - pd.Timestamp(last_h).normalize()).days > 1
        except Exception as e:  # noqa: BLE001
            log.debug("staleness (hourly) check skipped: %s", e)
        try:  # surfaced for transparency only — does NOT drive `stale`
            fs = config.data_dir() / "vector" / "flash_state.json"
            if fs.exists():
                last_flash_change = json.loads(fs.read_text()).get("last_eval")
        except Exception as e:  # noqa: BLE001
            log.debug("flash_state read skipped: %s", e)

        return {
            "ok": True, "display_only": True, "asof": asof,
            "evidence": evidence,
            "down": {
                "score": int(down_score), "ladder": _ladder(down_score, down_act),
                "act_live": down_act,
                "fired_today": any(l["fired_today"] and l["tier"] == "act" for l in down_legs),
                "legs": down_legs, "lead_window_days": [1, 3],
            },
            "up": {
                "score": int(up_score), "ladder": _ladder(up_score, up_act),
                "validated": evidence["u1"]["claim_eligible"],
                "act_live": up_act,
                "fired_today": any(l["fired_today"] and l["tier"] == "act" for l in up_legs),
                "legs": up_legs,
                "note": ("U1 is a reactive wash-out observation after a deep drop. "
                         "Its current evidence passport decides whether any action claim is permitted."),
            },
            "fuel_gauge": {
                "oi_pctile": round(oi_pctile, 3) if oi_pctile is not None else None,
                "vov_pctile": round(vov_pctile, 3) if vov_pctile is not None else None,
                "lit": fuel_lit,
                "state": "loading" if fuel_lit else "quiet",
            },
            "cascade": {"cascade_risk": cascade_risk, "oi_only_risk": oi_only},
            "staleness": {"daily_asof": asof, "intraday_asof": intraday_asof,
                          "stale": bool(stale), "last_flash_change": last_flash_change},
            "note": ("Forward impulse observations, not the standing regime. Exact current "
                     "evidence passports govern act points; every denied or unreadable state zeros "
                     "authority. Legs still decay to quiet, and this display sizes nothing."),
        }
    except Exception as e:  # noqa: BLE001 — radar is additive, never fatal
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
