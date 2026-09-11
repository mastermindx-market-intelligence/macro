"""Risk Radar — forward-outcome log + deterministic grading (Phase B).

Every daily risk_radar snapshot is APPENDED to data/risk_radar/forward_log.jsonl (idempotent
by as-of date; every writer self-gates on ledger_lane_armed(), so off-lane renders are
read-only). Once an entry's horizon matures, it is GRADED deterministically against the
realized SPY path: did a >= threshold drawdown actually occur within H business days? Each
alert is then a true-positive or a false-positive. The rolling scorecard (realized precision /
recall / false-positive rate per state-band and per scare-type and per horizon) is what the
dashboard surfaces and what the Opus self-correction loop (engine/risk_radar_review.py) reads
to rethink wrong calls and retune the calibration. Self-auditing by construction.

Pure-ish + never raises into the build.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

HORIZONS = {"h5": 5, "h10": 10, "h21": 21}        # business-day forward windows
DD_THRESHOLDS = (0.05, 0.08)                       # a >=5% pullback = a "drawdown"; 8% = a bigger one
PRIMARY_DD = 0.05
ALERT_STATES = ("elevated", "risk-off")            # which states count as a loud alert for precision

# Display vocabulary for the publication-change read model.  The canonical ledger stores
# stable machine keys; this map translates only the compact user-facing explanation. Unknown
# future legs remain exact in machine fields, while user copy uses a neutral localized fallback.
_LEG_DISPLAY = {
    "credit_oas_roc": ("HY credit spreads widening", "高收益利差走阔"),
    "credit_hyg_tlt": ("HY bonds lagging Treasuries", "高收益债跑输国债"),
    "rates_move": ("Bond-market volatility (MOVE)", "债市波动率（MOVE）"),
    "rates_realrate": ("Real yields jumping", "实际利率跳升"),
    "bubble_ext": ("S&P trend extension vs 200-day", "标普相对200日线趋势延伸"),
    "bubble_leadership": ("Narrow leadership (semis)", "领涨过窄（半导体）"),
    "growth_defensives": ("Defensives outperforming", "防御股跑赢"),
    "growth_cyc_def": ("Cyclicals fading vs defensives", "周期股弱于防御"),
    "vol_term": ("VIX term-structure stress", "VIX 期限结构紧张"),
    "vol_putcall": ("Put/call skew", "认沽/认购偏斜"),
    "vol_gex": ("Dealer gamma (GEX)", "做市商 Gamma"),
    "corr_floor_break": ("Stocks moving together", "个股联动上升"),
    "global_breadth": ("Global breadth breakdown", "全球广度破位"),
    "jpy_carry": ("Yen carry stress", "日元套利压力"),
    "nh_contraction": ("New-high participation contracting", "创新高参与度收缩"),
    "ai_breadth_divergence": ("AI breadth divergence", "AI 广度背离"),
}
_STATE_DISPLAY = {
    "calm": ("Calm", "平静"),
    "watch": ("Watch", "观察"),
    "caution": ("Caution", "警戒"),
    "elevated": ("Elevated", "升高"),
    "risk-off": ("Risk-off", "避险"),
}
_SCARE_DISPLAY = {
    "credit": ("Credit stress", "信用压力"),
    "rates": ("Rates / inflation shock", "利率/通胀冲击"),
    "bubble": ("Bubble risk", "泡沫风险"),
    "growth": ("Growth scare / defensive rotation", "增长恐慌/防御轮动"),
    "vol": ("Volatility event", "波动率事件"),
    "global": ("Global breadth breakdown", "全球广度破位"),
    "internals": ("Breadth internals deterioration", "内部广度恶化"),
}


def ledger_lane_armed() -> bool:
    """True only on a ledger-advancing collect lane (COLLECT_LANE=nightly, legacy
    alias US_LANE). House law: nightly is the SOLE advancer of data/ forward
    ledgers — this log's only advancing lane is daily.yml's engine job (job-level
    COLLECT_LANE=nightly; verified via git log on data/risk_radar/forward_log.jsonl:
    every advancing commit is that job's "engine: regime update"). engine/run.py
    also runs on closing-bell (whose contract, closing-bell.yml, is that every
    ledger writer self-gates on COLLECT_LANE) and the engine-render/render
    re-render lanes; there the radar still renders and snapshot_and_grade degrades
    to a pure scorecard read, but log/grade must not advance — appends are
    idempotent-by-asof with FIRST-WRITER-WINS, so a mid-session off-lane append
    would permanently displace the nightly row. Canonical gate:
    engine/risk_radar_intl_audit.ledger_lane_armed (#2684); ignition sibling
    engine/ignition_audit.ledger_lane_armed (#2693)."""
    import os
    lane = os.environ.get("COLLECT_LANE", "") or os.environ.get("US_LANE", "")
    return lane.lower() == "nightly"


def _path(root=None) -> Path:
    base = config.data_dir() if root is None else (Path(root) / "data")
    p = base / "risk_radar" / "forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return rows


def _write(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, separators=(",", ":"), default=str) for r in rows) + "\n")


def _entry_from_snapshot(snap: dict) -> dict | None:
    """Slim a risk_radar.compute() snapshot to the loggable fields (no recompute)."""
    if not snap or not snap.get("asof") or snap.get("state") is None:
        return None
    # CONTEXT-GATE EVIDENCE (audit 2026-07-29). Only the GATED state was ever logged, so the
    # context gate's promotion-grade false-positive claim (H21 banner precision 0.085 -> 0.249,
    # fire-rate 80% -> 17%) could never be falsified on THIS engine's own ledger: every day the
    # gate clamped elevated+ down to 'caution' was recorded as a caution day, the alert count
    # stayed 0 for life, and the counterfactual the gate is justified by left no trace. Logging
    # the UN-gated state beside the gated one makes the clamped days gradeable as the alerts they
    # would have been — the gate itself is untouched, this is pure accounting.
    gate = snap.get("context_gate") or {}
    authority = snap.get("authority") or {}
    ungated = snap.get("state_ungated")
    return {
        "asof": str(snap["asof"]),
        "state": snap.get("state"),
        "alert": bool(snap.get("alert")),
        # what the radar read BEFORE the context gate clamped it, plus the gate's own legs
        "state_ungated": ungated,
        "alert_ungated": (None if ungated is None
                          else bool(ungated in ALERT_STATES)),
        "gate_clamped": (None if ungated is None else bool(ungated != snap.get("state"))),
        "context_gate": {"met": gate.get("met"),
                         "spy_below_200dma": gate.get("spy_below_200dma"),
                         "breadth_weak": gate.get("breadth_weak")},
        "dominant_scare": snap.get("dominant_scare"),
        "top_score": snap.get("top_score"),
        # Authority provenance is part of the forward claim. Without it, a future review cannot
        # distinguish a visible advisory from a day that actually overrode Market State, nor
        # reconstruct which evidence had passed the confirmation/validation gate at the time.
        "can_force": bool(snap.get("can_force")),
        "authority_tier": authority.get("tier"),
        "authority_reason": authority.get("reason"),
        "confirmed_validated_legs": list(authority.get("confirmed_validated_legs") or []),
        "conjunction_n": (snap.get("drawdown_prob") or {}).get("conjunction_n"),
        "scares": {s["scare"]: {
                       "score": s.get("score"), "band": s.get("band"),
                       "firing_legs": [
                           {"leg": leg.get("leg"), "pctile": leg.get("pctile"),
                            "confirmed": bool(leg.get("confirmed")),
                            "era_robust": bool(leg.get("era_robust")),
                            "lift_2020": leg.get("lift_2020")}
                           for leg in (s.get("firing_legs") or [])
                       ],
                   }
                   for s in (snap.get("scares") or [])},
        "drawdown_prob": snap.get("drawdown_prob"),
        # de-escalation trajectory (engine/risk_radar.trajectory) — slim record so a future
        # recovery audit can grade whether "peaking/receding" actually preceded a rebound.
        "traj_phase": (snap.get("trajectory") or {}).get("phase"),
        "traj_intensity": (snap.get("trajectory") or {}).get("intensity"),
        "traj_off_peak": (snap.get("trajectory") or {}).get("off_peak"),
        "traj_odds_now": (snap.get("trajectory") or {}).get("odds_now"),
        # W1-S3 enabling fields (§8 ruling 2026-07-04): the DE-ESCALATION verdict and
        # dislocation switch were never logged, so S3's retro-derivation had a ZERO-day
        # overlap window for its pre-registered reconstruction check (→ moved to W3+).
        # Logging them from today makes the check possible when the window matures.
        "deescalation_eligible": (snap.get("deescalation") or {}).get("eligible"),
        "deescalation_reason": (snap.get("deescalation") or {}).get("reason"),
        "dislocation_active": snap.get("dislocation_active"),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": None,
    }


def log_snapshot(snap: dict, root=None) -> bool:
    """Append today's snapshot to the forward log (idempotent by as-of). Returns True if added.
    Ledger-advancing lanes only (ledger_lane_armed): off-lane calls no-op, returning False."""
    try:
        if not ledger_lane_armed():
            log.debug("risk_radar_audit log skipped: lane not armed")
            return False
        entry = _entry_from_snapshot(snap)
        if entry is None:
            return False
        p = _path(root)
        rows = _read(p)
        if any(r.get("asof") == entry["asof"] for r in rows):
            return False
        rows.append(entry)
        _write(p, rows)
        return True
    except Exception as e:  # noqa: BLE001 — never fatal
        log.warning("risk_radar_audit log failed: %s", e)
        return False


def _spy():
    df = store.read("yahoo", "SPY")
    if df is None or "close" not in df:
        return None
    s = df["close"].dropna()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def _grade_entry(entry: dict, spy: pd.Series) -> dict | None:
    """Realized forward max-drawdown per horizon from the as-of date; mark hit + outcome.
    Returns the 'graded' dict, or None if the longest horizon hasn't matured yet."""
    asof = pd.Timestamp(entry["asof"])
    loc = spy.index.searchsorted(asof, side="right")     # first bar strictly after as-of
    maxH = max(HORIZONS.values())
    if loc + maxH > len(spy):
        return None                                       # not matured
    base_loc = max(0, loc - 1)
    base_px = float(spy.iloc[base_loc])
    fwd_dd, hit = {}, {}
    for hk, hd in HORIZONS.items():
        w = spy.iloc[loc: loc + hd]
        dd = float(w.min() / base_px - 1.0) if len(w) else None
        fwd_dd[hk] = None if dd is None else round(dd, 4)
        hit[hk] = {f"dd{int(t*100)}": (dd is not None and dd <= -t) for t in DD_THRESHOLDS}
    any_primary = any(fwd_dd[hk] is not None and fwd_dd[hk] <= -PRIMARY_DD for hk in HORIZONS)
    is_alert = entry.get("state") in ALERT_STATES
    outcome = None
    if is_alert:
        outcome = "true_positive" if any_primary else "false_positive"
    elif entry.get("state") in ("watch", "caution"):
        outcome = "tp_watch" if any_primary else "tn_watch"
    else:
        outcome = "calm_dd" if any_primary else "calm_quiet"
    # COUNTERFACTUAL grade for the UN-gated state (audit 2026-07-29): on a clamped day the
    # gated row grades as a caution, so the alert the gate suppressed is never scored either
    # way. Grading it separately is what makes the gate's own FP claim falsifiable. None on
    # rows logged before state_ungated existed — never imputed from the gated state.
    ung = entry.get("state_ungated")
    outcome_ungated = None
    if ung:
        if ung in ALERT_STATES:
            outcome_ungated = "true_positive" if any_primary else "false_positive"
        elif ung in ("watch", "caution"):
            outcome_ungated = "tp_watch" if any_primary else "tn_watch"
        else:
            outcome_ungated = "calm_dd" if any_primary else "calm_quiet"
    return {"base_px": round(base_px, 2), "fwd_dd": fwd_dd, "hit": hit,
            "outcome": outcome, "any_dd5_within_h21": bool(any_primary),
            "outcome_ungated": outcome_ungated,
            "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def grade_log(root=None) -> int:
    """Grade every matured, ungraded entry against the realized SPY path. Returns # newly graded.

    Ledger-advancing lanes only (ledger_lane_armed): grades are keep-first-permanent,
    so an off-lane grade computed from a mid-session store would stick — no-op, 0.
    """
    try:
        if not ledger_lane_armed():
            log.debug("risk_radar_audit grade skipped: lane not armed")
            return 0
        p = _path(root)
        rows = _read(p)
        if not rows:
            return 0
        spy = _spy()
        if spy is None:
            return 0
        n = 0
        for r in rows:
            if r.get("graded"):
                continue
            g = _grade_entry(r, spy)
            if g is not None:
                r["graded"] = g
                n += 1
        if n:
            _write(p, rows)
        return n
    except Exception as e:  # noqa: BLE001
        log.warning("risk_radar_audit grade failed: %s", e)
        return 0


def scorecard(root=None) -> dict:
    """Rolling realized-accuracy scorecard from the graded log: overall alert precision, per-state
    hit-rate, per-dominant-scare precision, and recent mistakes (FPs + missed drawdowns). What the
    dashboard shows + the Opus review reads. Never raises."""
    try:
        rows = [r for r in _read(_path(root)) if r.get("graded")]
    except Exception:  # noqa: BLE001
        rows = []
    if not rows:
        return {"n_graded": 0, "note": "no matured entries yet"}
    alerts = [r for r in rows if r.get("alert")]
    tp = [r for r in alerts if r["graded"]["outcome"] == "true_positive"]
    fp = [r for r in alerts if r["graded"]["outcome"] == "false_positive"]
    # recall: of all matured days that PRECEDED a >=5%/h21 drawdown, how many were alerted?
    pre = [r for r in rows if r["graded"].get("any_dd5_within_h21")]
    pre_alerted = [r for r in pre if r.get("alert")]
    by_state = {}
    for r in rows:
        st = r.get("state")
        d = by_state.setdefault(st, {"n": 0, "dd": 0})
        d["n"] += 1
        d["dd"] += int(bool(r["graded"].get("any_dd5_within_h21")))
    by_state = {k: {"n": v["n"], "hit_rate": round(v["dd"] / v["n"], 3) if v["n"] else None}
                for k, v in by_state.items()}
    mistakes = [{"asof": r["asof"], "state": r["state"], "dominant_scare": r.get("dominant_scare"),
                 "scares": r.get("scares"), "kind": r["graded"]["outcome"],
                 "fwd_dd_h21": r["graded"]["fwd_dd"].get("h21")}
                for r in rows
                if r["graded"]["outcome"] in ("false_positive",)
                or (not r.get("alert") and r["graded"].get("any_dd5_within_h21"))]  # FPs + misses
    # CONTEXT-GATE COUNTERFACTUAL (audit 2026-07-29). `n_alerts` has been 0 for the life of this
    # ledger because the gate clamps every elevated+ read down to 'caution' before it is logged —
    # so the gate's measured false-positive reduction has never been checkable HERE. This block
    # scores the un-gated state on the same realized paths: how many clamped days would have been
    # alerts, and how many of those would have been false. Rows logged before state_ungated
    # existed are excluded from the denominators rather than imputed.
    ung_rows = [r for r in rows if (r["graded"] or {}).get("outcome_ungated")]
    ung_alerts = [r for r in ung_rows if r.get("alert_ungated")]
    ung_tp = [r for r in ung_alerts if r["graded"]["outcome_ungated"] == "true_positive"]
    ung_fp = [r for r in ung_alerts if r["graded"]["outcome_ungated"] == "false_positive"]
    clamped = [r for r in ung_rows if r.get("gate_clamped")]
    gate_cf = {
        "n_rows_with_ungated": len(ung_rows),
        "n_clamped_by_gate": len(clamped),
        "n_alerts_ungated": len(ung_alerts),
        "n_true_pos_ungated": len(ung_tp), "n_false_pos_ungated": len(ung_fp),
        "alert_precision_ungated": (round(len(ung_tp) / len(ung_alerts), 3)
                                    if ung_alerts else None),
        "note": ("Counterfactual: the state BEFORE the context gate clamped it, graded on the "
                 "same realized SPY paths. Rows logged before state_ungated was recorded are "
                 "excluded, so an empty block means 'not yet measurable', not 'no false alarms'."),
    }
    return {
        "n_graded": len(rows),
        "alert_precision": round(len(tp) / len(alerts), 3) if alerts else None,
        "n_alerts": len(alerts), "n_true_pos": len(tp), "n_false_pos": len(fp),
        "recall_dd5_h21": round(len(pre_alerted) / len(pre), 3) if pre else None,
        "by_state": by_state,
        "context_gate_counterfactual": gate_cf,
        "recent_mistakes": sorted(mistakes, key=lambda m: m["asof"], reverse=True)[:25],
        "asof_range": [rows[0]["asof"], rows[-1]["asof"]],
    }



def _change_num(value) -> float | None:
    """Finite one-decimal score for display/comparison; typed absence otherwise."""
    if isinstance(value, (bool, np.bool_)):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return round(out, 1) if np.isfinite(out) else None


def _scare_map(payload: dict) -> dict[str, dict]:
    """Normalize live list-shaped scares and ledger dict-shaped scares."""
    raw = (payload or {}).get("scares") or {}
    if isinstance(raw, dict):
        return {str(k): (v if isinstance(v, dict) else {}) for k, v in raw.items()}
    out: dict[str, dict] = {}
    for row in raw if isinstance(raw, list) else []:
        if isinstance(row, dict) and row.get("scare"):
            out[str(row["scare"])] = row
    return out


def _leg_ids(scare: dict) -> list[str]:
    rows = (scare or {}).get("firing_legs")
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        key = row.get("leg") if isinstance(row, dict) else None
        if key and key not in out:
            out.append(str(key))
    return out


def _leg_label(key: str, language: str) -> str:
    pair = _LEG_DISPLAY.get(key)
    if pair:
        return pair[0 if language == "en" else 1]
    return key.replace("_", " ") if language == "en" else "未分类信号"


def _publication_day(value) -> pd.Timestamp | None:
    """Normalize a canonical ISO as-of to its timezone-free publication date."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) < 10 or (len(text) > 10 and text[10] not in ("T", " ")):
        return None
    try:
        day = datetime.strptime(text[:10], "%Y-%m-%d").date()
        ts = pd.Timestamp(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(ts):
        return None
    return pd.Timestamp(day)


def _state_label(state, language: str) -> str:
    key = str(state or "")
    pair = _STATE_DISPLAY.get(key)
    if pair:
        return pair[0 if language == "en" else 1]
    return key.replace("_", " ").title() if language == "en" else key


def _scare_label(scare, language: str) -> str | None:
    key = str(scare or "")
    pair = _SCARE_DISPLAY.get(key)
    if pair:
        return pair[0 if language == "en" else 1]
    if language == "en" and key:
        return key.replace("_", " ").title()
    return None


def _compact_labels(keys: list[str], language: str, limit: int = 2) -> str:
    labels = [_leg_label(k, language) for k in keys[:limit]]
    if len(keys) > limit:
        labels.append(f"+{len(keys) - limit}")
    return (", ".join(labels) if language == "en" else "、".join(labels))


def publication_change(snap: dict, root=None) -> dict:
    """Compare ``snap`` with earlier canonical Risk-Radar publications.

    This is a READ MODEL over ``forward_log.jsonl`` — never a second history store.  The
    comparator is deliberately the latest row with ``asof < current_asof`` because the nightly
    lane appends today's row before this function runs.  Selecting the ledger tail would therefore
    manufacture a zero delta on the very lane that owns the publication.
    """
    snap = snap if isinstance(snap, dict) else {}
    current_asof = str(snap.get("asof") or "")
    current_score = _change_num(snap.get("top_score"))
    base = {
        "available": False,
        "basis": "prior_publication",
        "null_reason": None,
        "current_asof": current_asof or None,
        "prior_asof": None,
        "score": {"current": current_score, "prior": None,
                  "delta": None, "direction": None},
        "state": None,
        "scares": [],
        "week": {"available": False, "null_reason": "NO_WEEK_REFERENCE"},
        "summary_en": "",
        "summary_zh": "",
    }
    if not current_asof:
        return {**base, "null_reason": "CURRENT_ASOF_MISSING"}

    try:
        current_ts = _publication_day(current_asof)
        if current_ts is None:
            return {**base, "null_reason": "CURRENT_ASOF_INVALID"}
        # Keep the first publication for each date: the ledger's own contract is
        # FIRST-WRITER-WINS, and comparison must preserve that identity even if equivalent
        # date/timestamp spellings appear in malformed historical data.
        by_day: dict[str, tuple[pd.Timestamp, dict]] = {}
        for row in _read(_path(root)):
            if not isinstance(row, dict):
                continue
            raw_asof = row.get("asof")
            ts = _publication_day(raw_asof)
            if ts is None:
                continue
            day_key = ts.date().isoformat()
            if day_key in by_day:
                continue
            by_day[day_key] = (ts, row)
        ordered = sorted(by_day.values(), key=lambda item: item[0])
        earlier = [(ts, row) for ts, row in ordered if ts < current_ts]
        if not earlier:
            return {**base, "null_reason": "NO_EARLIER_PUBLICATION"}

        prior_ts, prior = earlier[-1]
        prior_score = _change_num(prior.get("top_score"))
        delta = (round(current_score - prior_score, 1)
                 if current_score is not None and prior_score is not None else None)
        direction = (None if delta is None else
                     "rising" if delta > 0 else "easing" if delta < 0 else "flat")

        current_state, prior_state = snap.get("state"), prior.get("state")
        current_scares, prior_scares = _scare_map(snap), _scare_map(prior)
        scare_changes: list[dict] = []
        for key in sorted(set(current_scares) | set(prior_scares)):
            cur = current_scares.get(key, {})
            old = prior_scares.get(key, {})
            cur_score, old_score = _change_num(cur.get("score")), _change_num(old.get("score"))
            scare_delta = (round(cur_score - old_score, 1)
                           if cur_score is not None and old_score is not None else None)
            cur_legs, old_legs = _leg_ids(cur), _leg_ids(old)
            old_set, cur_set = set(old_legs), set(cur_legs)
            added = [leg for leg in cur_legs if leg not in old_set]
            cleared = [leg for leg in old_legs if leg not in cur_set]
            label_en = (cur.get("label_en") or old.get("label_en") or
                        _scare_label(key, "en") or "Unclassified risk")
            label_zh = (cur.get("label_zh") or old.get("label_zh") or
                        _scare_label(key, "zh") or "未分类风险")
            scare_changes.append({
                "scare": key,
                "label_en": label_en,
                "label_zh": label_zh,
                "prior": old_score,
                "current": cur_score,
                "delta": scare_delta,
                "prior_band": old.get("band"),
                "current_band": cur.get("band"),
                "band_changed": bool(old.get("band") is not None and
                                     cur.get("band") is not None and
                                     old.get("band") != cur.get("band")),
                "added_legs": added,
                "cleared_legs": cleared,
                "added_labels_en": [_leg_label(k, "en") for k in added],
                "added_labels_zh": [_leg_label(k, "zh") for k in added],
                "cleared_labels_en": [_leg_label(k, "en") for k in cleared],
                "cleared_labels_zh": [_leg_label(k, "zh") for k in cleared],
            })
        scare_changes.sort(key=lambda row: (
            -(abs(row["delta"]) if row["delta"] is not None else -1.0), row["scare"]
        ))

        week_candidates = [(ts, row) for ts, row in earlier
                           if ts <= current_ts - pd.Timedelta(days=7)]
        if week_candidates:
            week_ts, week_row = week_candidates[-1]
            week_score = _change_num(week_row.get("top_score"))
            week_delta = (round(current_score - week_score, 1)
                          if current_score is not None and week_score is not None else None)
            if week_score is None:
                week = {"available": False, "null_reason": "WEEK_SCORE_MISSING",
                        "asof": str(week_row.get("asof")), "score": None, "delta": None}
            else:
                week = {"available": True, "asof": str(week_row.get("asof")),
                        "score": week_score, "delta": week_delta}
        else:
            week = {"available": False, "null_reason": "NO_WEEK_REFERENCE"}

        dominant = str(snap.get("dominant_scare") or "")
        dominant_change = next((row for row in scare_changes if row["scare"] == dominant), None)
        subject = dominant_change
        if subject and subject["prior"] is not None and subject["current"] is not None:
            lead_en = f"{subject['label_en']} {subject['prior']:.1f}→{subject['current']:.1f}"
            lead_zh = f"{subject['label_zh']} {subject['prior']:.1f}→{subject['current']:.1f}"
        elif prior_score is not None and current_score is not None:
            lead_en = f"Radar {prior_score:.1f}→{current_score:.1f}"
            lead_zh = f"雷达 {prior_score:.1f}→{current_score:.1f}"
        else:
            lead_en, lead_zh = "Risk Radar changed", "风险雷达发生变化"
        summary_en, summary_zh = [lead_en], [lead_zh]
        state_changed = bool(prior_state in _STATE_DISPLAY and
                             current_state in _STATE_DISPLAY and
                             prior_state != current_state)
        if state_changed:
            summary_en.append(f"{_state_label(prior_state, 'en')}→{_state_label(current_state, 'en')}")
            summary_zh.append(f"{_state_label(prior_state, 'zh')}→{_state_label(current_state, 'zh')}")
        prior_dominant = prior.get("dominant_scare")
        current_dominant = snap.get("dominant_scare")
        if prior_dominant and current_dominant and prior_dominant != current_dominant:
            prior_label_en = prior.get("dominant_label_en") or _scare_label(prior_dominant, "en")
            prior_label_zh = prior.get("dominant_label_zh") or _scare_label(prior_dominant, "zh")
            current_label_en = (snap.get("dominant_label_en") or
                                _scare_label(current_dominant, "en"))
            current_label_zh = (snap.get("dominant_label_zh") or
                                _scare_label(current_dominant, "zh"))
            if all((prior_label_en, prior_label_zh, current_label_en, current_label_zh)):
                summary_en.append(f"Lead {prior_label_en}→{current_label_en}")
                summary_zh.append(f"主导 {prior_label_zh}→{current_label_zh}")
        if subject:
            if subject["cleared_legs"]:
                summary_en.append(f"{_compact_labels(subject['cleared_legs'], 'en')} cleared")
                summary_zh.append(f"{_compact_labels(subject['cleared_legs'], 'zh')}解除")
            if subject["added_legs"]:
                summary_en.append(f"{_compact_labels(subject['added_legs'], 'en')} added")
                summary_zh.append(f"{_compact_labels(subject['added_legs'], 'zh')}新增")

        return {
            **base,
            "available": True,
            "null_reason": None,
            "prior_asof": str(prior.get("asof")),
            "score": {"current": current_score, "prior": prior_score,
                      "delta": delta, "direction": direction},
            "state": {"current": current_state, "prior": prior_state,
                      "changed": state_changed},
            "scares": scare_changes,
            "week": week,
            "summary_en": " · ".join(summary_en),
            "summary_zh": " · ".join(summary_zh),
        }
    except Exception as exc:  # noqa: BLE001 — display read model must never break a build
        log.warning("risk_radar publication-change read failed: %s", exc)
        return {**base, "null_reason": "COMPARISON_ERROR"}


def snapshot_and_grade(snap: dict, root=None) -> dict:
    """Convenience for run.py: log today's snapshot, grade matured entries, return the scorecard
    (which the engine attaches to latest['risk_radar']['forward_log']).

    Off-lane (ledger_lane_armed() False) the log/grade legs no-op and this is a
    pure scorecard read — the display payload stays populated on the
    closing-bell / engine-render / render lanes without advancing the ledger."""
    log_snapshot(snap, root=root)
    grade_log(root=root)
    out = dict(scorecard(root=root))
    out["publication_change"] = publication_change(snap, root=root)
    return out
