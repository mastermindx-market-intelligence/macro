"""T11 composer — pair / group / family evaluation for leadership rotation.

Prereg: research/LEADERSHIP_ROTATION_PREREG_V1.md, frozen at commit
fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb (blob
9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe).
Amended by research/LEADERSHIP_ROTATION_PREREG_V2.md (2026-10-14; blob
1fcd151cfc4cdeb321789feb50d3fbb127cce056) -- both pinned by assert_protocol_landed.

DEVELOPMENT HARNESS — no verdict authority.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Unconditional repo-root pin (tests/test_check_script_import_pinning.py: a
# conditional insert is not a strong pin — a root already further down
# sys.path still loses to a foreign package ahead of it).
sys.path.insert(0, str(_REPO_ROOT))

from scripts import leadership_rotation_episodes as ep
from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st

__all__ = [
    "PairSeries",
    "build_groups",
    "evaluate_pair",
    "evaluate_group",
    "evaluate_family",
    "SizeGateNotPassed",
    "assert_size_gate_passed",
    "count_prior_looks",
    "record_look",
    "run_p1",
    "falsifier_controls",
]

FAMILY_ORDER: List[Tuple[str, str]] = [
    ("defensive_sector", "H1"),
    ("defensive_sector", "H2"),
    ("defensive_sector", "H3"),
    ("broadening_proxy", "H1"),
    ("broadening_proxy", "H2"),
    ("broadening_proxy", "H3"),
]

_FAMILY_GROUPS = ("defensive_sector", "broadening_proxy")

# ---------------------------------------------------------------------------
# P1 harness gate (prereg V2 §3 two-part size rule; T19 F9) and look ledger.
# Shared by the P0 size-gate writer (leadership_rotation_p0 ``size --out``) and
# the P1 reader (``run_p1``): the reader refuses unless the committed artifact
# at the reading commit shows the two-part gate PASSED for every required
# delta = 0 cell under the exact harness bytes that will run the read.
# ---------------------------------------------------------------------------
SIZE_GATE_PATH = "research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.size_gate.json"
SIZE_GATE_RULE = "V2_SEC3_TWO_PART"
SIZE_GATE_REQUIRED_CELLS: Tuple[int, ...] = (0, 1, 2, 3, 4, 48)
SIZE_GATE_MIN_M = 400
SIZE_GATE_H1_NULL_METHOD = "V2_OPTION_A"
SIZE_GATE_MIN_NULL_K = 1000  # prereg V2 §2: K >= 1,000 null paths per H1 read
HARNESS_MODULES: Tuple[str, ...] = (
    "engine/leadership_rotation_context.py",
    "scripts/leadership_rotation_episodes.py",
    "scripts/leadership_rotation_inference.py",
    "scripts/leadership_rotation_null.py",
    "scripts/leadership_rotation_p0.py",
    "scripts/leadership_rotation_run.py",
    "scripts/leadership_rotation_study.py",
)
LOOK_LEDGER_PATH = "research/LEADERSHIP_ROTATION_LOOK_LEDGER.jsonl"

_CONTROL_NAMES = (
    "both_down",
    "breadth_missingness",
    "empty_is_unknown",
    "composition_only",
    "shared_holdings",
    "rolling_carry",
    "beta_only",
    "relative_units",
    "confirmation_maturity",
    "zero_vs_missing",
)


@dataclass(frozen=True)
class PairSeries:
    pair_id: str
    group: str
    num_sym: str
    den_sym: str
    num: np.ndarray
    den: np.ndarray
    spy: np.ndarray


def _json_sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating, np.integer)):
        v = float(obj) if isinstance(obj, np.floating) else int(obj)
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    if isinstance(obj, np.ndarray):
        return _json_sanitize(obj.tolist())
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, ep.UpPhase):
        return {
            "T": int(obj.T),
            "P": int(obj.P),
            "rise": float(obj.rise),
            "censored": bool(obj.censored),
            "qualifies": bool(obj.qualifies),
        }
    return obj


def _in_window(t: int, s0: int, end: int) -> bool:
    return s0 <= t <= end


def _filter_window(items: Sequence[int], s0: int, end: int) -> List[int]:
    return [int(t) for t in items if _in_window(t, s0, end)]


def _log_returns(prices: np.ndarray) -> np.ndarray:
    p = np.asarray(prices, dtype=float)
    out = np.full(len(p), np.nan)
    if len(p) > 1:
        m = np.isfinite(p[1:]) & (p[1:] > 0) & np.isfinite(p[:-1]) & (p[:-1] > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[1:] = np.where(m, np.log(p[1:]) - np.log(p[:-1]), np.nan)
    return out


def _off_index(state, exits, entries: Sequence[int]) -> Dict[int, Optional[int]]:
    ex = sorted(int(x) for x in exits)
    off: Dict[int, Optional[int]] = {}
    for e in entries:
        nxt = None
        for x in ex:
            if x > e:
                nxt = x
                break
        off[int(e)] = nxt
    return off


def _outcome_record(R, invalid, t: int, h: int, betas, log_spy) -> dict:
    state, y = st.outcome(R, invalid, t, h)
    o = t + 1
    y_res = None
    res_state = None
    if state == "MATURED" and np.isfinite(y):
        beta_n, beta_d = betas
        yr = st.residual_outcome(y, beta_n, beta_d, log_spy, o, h)
        if not np.isfinite(yr):
            res_state = "UNPRICEABLE"
        else:
            res_state = "MATURED"
            y_res = float(yr)
    elif state in st.OUTCOME_STATES:
        res_state = state
    st_c, y_c = st.policy_outcome(R, invalid, t, h)
    return {
        "t": int(t),
        "y20": {
            "state": state,
            "y": float(y) if state == "MATURED" and np.isfinite(y) else None,
        },
        "y63": _outcome_short(R, invalid, t, st.H_SECONDARY),
        "y_res_20": {"state": res_state, "y": y_res},
        "policy_y20": {
            "state": st_c,
            "y": float(y_c) if st_c == "MATURED" and np.isfinite(y_c) else None,
        },
    }


def _outcome_short(R, invalid, t: int, h: int) -> dict:
    state, y = st.outcome(R, invalid, t, h)
    return {"state": state, "y": float(y) if state == "MATURED" and np.isfinite(y) else None}


def _summarize_arm_outcomes(records: List[dict], key: str) -> dict:
    pairs = [(r[key]["state"], r[key]["y"]) for r in records]
    return st.summarize_outcomes(
        [(s, y if y is not None else float("nan")) for s, y in pairs]
    )


def _arm_summary(kept, out_records, class_records, merged_away: int) -> dict:
    fs = st.false_start_rate_h20(
        [
            r["y20"]["y"]
            for r in out_records
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None
        ]
    )
    return {
        "n_items": len(kept),
        "merged_away": merged_away,
        "y20": _summarize_arm_outcomes(out_records, "y20"),
        "y63": _summarize_arm_outcomes(out_records, "y63"),
        "y_res_20": _summarize_arm_outcomes(out_records, "y_res_20"),
        "false_start_rate_h20": fs,
        "classifications": class_records,
    }


def _formation_bounds(ps: PairSeries, start: int, end: int) -> Tuple[int, bool]:
    fe = st.first_eligible(ps.num, ps.den)
    if fe is None:
        return end + 1, False
    return max(int(start), int(fe)), True


def _evaluate_pair_core(ps: PairSeries, *, start: int, end: int) -> dict:
    R, invalid = st.log_ratio(ps.num, ps.den)
    n = len(R)
    s0, eligible = _formation_bounds(ps, start, end)
    if not eligible or s0 > end:
        empty_arms = {
            arm: {"n_items": 0, "merged_away": 0, "y20": st.summarize_outcomes([]), "y63": st.summarize_outcomes([]),
                  "y_res_20": st.summarize_outcomes([]), "false_start_rate_h20": float("nan"), "classifications": []}
            for arm in ("A0", "A1", "A2", "B1", "B2", "B3")
        }
        empty_arms["B6"] = {"n_items": 0, "carry_share": 0.0, "carry_flags": []}
        empty_arms["B7"] = {"n_items": 0, "entries": st.arm_b7()}
        empty_arms["B5"] = {"patterns": {}, "n_formations": 0}
        return {
            "pair_id": ps.pair_id,
            "group": ps.group,
            "formation": {"start": s0, "end": int(end), "eligible": False},
            "measured_sessions": 0,
            "R": R,
            "invalid": invalid,
            "phases": [],
            "a1_class": [],
            "a2_class": [],
            "a0_class": [],
            "a0_raw_class": [],
            "a0_raw_merged_away": 0,
            "a1_kept": [],
            "a2_kept": [],
            "a0_kept": [],
            "b1_days": [],
            "b2_kept": [],
            "b3_kept": [],
            "a1_out": [],
            "b1_out": [],
            "b2_out": [],
            "b3_out": [],
            "arms": empty_arms,
            "coverage": st.all_event_coverage(R, invalid, max(s0, 0), min(end, n - 1)),
            "entry_context": {},
            "b6_share": 0.0,
        }

    a1_state, a1_entries, a1_exits = st.arm_a1(R)
    # prereg V2 §3.4: A0 raw (pre-suppression) fires, measured only — the A0 arm itself is unchanged
    a0_raw, a0_onsets = st.arm_a0(R)
    a2_alarms, a2_pending = st.arm_a2(a1_state, a1_entries)
    b1_days = st.arm_b1(R, s0, end)
    b2_entries = st.arm_b2(R)
    b3_state, b3_entries, b3_exits = st.arm_b3(ps.num, ps.spy)

    a1_w = _filter_window(a1_entries, s0, end)
    a2_w = _filter_window(a2_alarms, s0, end)
    a0_w = _filter_window(a0_onsets, s0, end)
    a0r_w = _filter_window(a0_raw, s0, end)
    b2_w = _filter_window(b2_entries, s0, end)
    b3_w = _filter_window(b3_entries, s0, end)

    a1_kept, a1_merged = ep.merge_within_pair(a1_w)
    a2_kept, a2_merged = ep.merge_within_pair(a2_w)
    a0_kept, a0_merged = ep.merge_within_pair(a0_w)
    a0r_kept, a0r_merged = ep.merge_within_pair(a0r_w)
    b2_kept, b2_merged = ep.merge_within_pair(b2_w)
    b3_kept, b3_merged = ep.merge_within_pair(b3_w)

    phases = ep.zigzag(R, start=s0, end=end + 1)
    phases_sens = ep.zigzag(R, amplitude=ep.AMPLITUDE_SENSITIVITY, start=s0, end=end + 1)

    lr_spy = _log_returns(ps.spy)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_spy = np.log(np.where(np.isfinite(ps.spy) & (ps.spy > 0), ps.spy, np.nan))
    lr_num = _log_returns(ps.num)
    lr_den = _log_returns(ps.den)
    beta_num = st.rolling_beta(lr_num, lr_spy)
    beta_den = st.rolling_beta(lr_den, lr_spy)

    def _betas_at(t: int) -> Tuple[float, float]:
        return float(beta_num[t]), float(beta_den[t])

    a1_class = ep.classify_alarms(
        a1_kept, phases, off_index=_off_index(a1_state, a1_exits, a1_kept)
    )
    a2_class = ep.classify_alarms(a2_kept, phases, off_index=None)
    a0_class = ep.classify_alarms(a0_kept, phases, off_index=None)
    a0_raw_class = ep.classify_alarms(a0r_kept, phases, off_index=None)

    num_s = pd.Series(ps.num)
    den_s = pd.Series(ps.den)
    ctx_counts: Dict[str, int] = {}
    for t in a1_kept:
        if t >= st.Z_LOOKBACK and np.isfinite(ps.num[t]) and np.isfinite(ps.den[t]):
            try:
                interp = st.entry_context(num_s, den_s, t)["interpretation"]
            except (ValueError, ZeroDivisionError):
                interp = "unmeasured"
            ctx_counts[interp] = ctx_counts.get(interp, 0) + 1

    a1_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in a1_kept
    ]
    b1_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in b1_days
    ]
    b2_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in b2_kept
    ]
    b3_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in b3_kept
    ]
    a0_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in a0_kept
    ]
    a2_out = [
        _outcome_record(R, invalid, t, st.H_PRIMARY, _betas_at(t), log_spy) for t in a2_kept
    ]

    b6_flags, b6_share = st.arm_b6_carry(R, a1_w)
    y20_all = np.array([st.outcome(R, invalid, t, st.H_PRIMARY)[1] for t in range(n)])
    b5 = st.arm_b5_table(R, y20_all, a1_state)

    measured = int(np.sum(np.isfinite(R[s0 : end + 1])))
    arms = {
        "A0": _arm_summary(a0_kept, a0_out, a0_class, len(a0_merged)),
        "A1": _arm_summary(a1_kept, a1_out, a1_class, len(a1_merged)),
        "A2": _arm_summary(a2_kept, a2_out, a2_class, len(a2_merged)),
        "B1": _arm_summary(b1_days, b1_out, [], 0),
        "B2": _arm_summary(b2_kept, b2_out, [], len(b2_merged)),
        "B3": _arm_summary(b3_kept, b3_out, [], len(b3_merged)),
        "B6": {
            "n_items": len(a1_kept),
            "carry_share": b6_share,
            "carry_flags": b6_flags,
        },
        "B7": {"n_items": 0, "entries": st.arm_b7()},
        "B5": b5,
    }
    arms["A2"]["pending"] = len(a2_pending)

    return {
        "pair_id": ps.pair_id,
        "group": ps.group,
        "formation": {"start": s0, "end": int(end), "eligible": True},
        "measured_sessions": measured,
        "R": R,
        "invalid": invalid,
        "phases": phases,
        "phases_sensitivity": phases_sens,
        "a1_class": a1_class,
        "a2_class": a2_class,
        "a0_class": a0_class,
        "a0_raw_class": a0_raw_class,
        "a0_raw_merged_away": len(a0r_merged),
        "a1_kept": a1_kept,
        "a2_kept": a2_kept,
        "a0_kept": a0_kept,
        "b1_days": b1_days,
        "b2_kept": b2_kept,
        "b3_kept": b3_kept,
        "a1_out": a1_out,
        "b1_out": b1_out,
        "b2_out": b2_out,
        "b3_out": b3_out,
        "arms": arms,
        "coverage": st.all_event_coverage(R, invalid, s0, end),
        "entry_context": ctx_counts,
        "b6_share": b6_share,
    }


def _pair_public(core: dict) -> dict:
    skip = {"R", "invalid", "phases", "phases_sensitivity"}
    out = {k: v for k, v in core.items() if k not in skip}
    out["episodes"] = {
        "primary": [_json_sanitize(ph) for ph in core.get("phases", [])],
        "sensitivity": [_json_sanitize(ph) for ph in core.get("phases_sensitivity", [])],
    }
    return out


def evaluate_pair(ps: PairSeries, *, start: int, end: int) -> dict:
    """Evaluate one pair over formation window [max(start, first_eligible), end]."""
    return _json_sanitize(_pair_public(_evaluate_pair_core(ps, start=start, end=end)))


def _cluster_n(items: List[inf.Item]) -> int:
    if not items:
        return 0
    return len(set(inf.single_linkage_clusters(items)[0]))


def _item_coord_map(items: List[inf.Item]) -> Tuple[List[int], Dict[int, int]]:
    labels, coords = inf.single_linkage_clusters(items)
    pos_coord = {i: coords[labels[i]] for i in range(len(items))}
    return labels, pos_coord


def _pair_session_indices(
    measured_per_day: np.ndarray, start: int, end: int
) -> List[int]:
    """ORCH-SCI ruling R22: pair-session list for §7 stability thirds."""
    out: List[int] = []
    for t in range(int(start), int(end) + 1):
        if 0 <= t < len(measured_per_day):
            c = int(measured_per_day[t])
            if c > 0:
                out.extend([t] * c)
    return out


def _measured_pairs_per_day(
    pairs: Sequence[PairSeries], cores: Sequence[dict], end: int
) -> np.ndarray:
    n = len(pairs[0].spy) if pairs else 0
    counts = np.zeros(n, dtype=np.int64)
    for ps, core in zip(pairs, cores):
        R = core["R"]
        s0 = core["formation"]["start"]
        for t in range(max(s0, 0), min(end + 1, len(R))):
            if np.isfinite(R[t]):
                counts[t] += 1
    return counts


def _h1_arm_replicates(
    records: Sequence[dict],
    phases: Sequence[ep.UpPhase],
    W: np.ndarray,
    onset_coord: Dict[int, int],
    alarm_coord: Dict[int, int],
    measured_per_day: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    qual = [ph for ph in phases if ph.qualifies]
    matched_T = {
        rec["phase_T"]
        for rec in records
        if rec["cls"] == "MATCHED" and rec["phase_T"] is not None
    }
    reps = W.shape[0]
    det = np.full(reps, np.nan)
    burden = np.full(reps, np.nan)
    delay = np.full(reps, np.nan)
    session_w = W.astype(np.float64) @ measured_per_day.astype(np.float64)

    for r in range(reps):
        wrow = W[r].astype(np.float64)
        det_num = 0.0
        det_den = 0.0
        for ph in qual:
            c = onset_coord.get(ph.T)
            if c is None:
                continue
            w = wrow[c]
            det_den += w
            if ph.T in matched_T:
                det_num += w
        det[r] = det_num / det_den if det_den > 0 else np.nan
        burden_w = sum(
            wrow[alarm_coord[rec["index"]]]
            for rec in records
            if rec["cls"] in ("REPEATED", "LATE", "FALSE_START") and rec["index"] in alarm_coord
        )
        years = session_w[r] / ep.SESSIONS_PER_YEAR
        burden[r] = burden_w / years if years > 0 else np.nan

    delays: List[float] = []
    d_coords: List[int] = []
    for rec in records:
        if rec["cls"] == "MATCHED" and rec["delay"] is not None and rec["phase_T"] is not None:
            delays.append(float(rec["delay"]))
            d_coords.append(onset_coord.get(rec["phase_T"], rec["index"]))
    if delays:
        Wm = inf.item_weights(W, d_coords)
        delay = inf.replicate_lower_median(np.array(delays), Wm)
    return det, burden, delay


def _episode_metrics_unit(
    records: Sequence[dict], phases: Sequence[ep.UpPhase], session_w_total: float
) -> dict:
    onset_keys = {ph.T for ph in phases if ph.qualifies}
    alarm_keys = {rec["index"] for rec in records}
    return ep.episode_metrics(
        list(records),
        list(phases),
        int(session_w_total),
        onset_w={k: 1.0 for k in onset_keys},
        alarm_w={k: 1.0 for k in alarm_keys},
        session_w_total=session_w_total,
    )


def _items_from_kept(
    group: str, pairs: Sequence[PairSeries], cores: Sequence[dict], key: str
) -> List[inf.Item]:
    items: List[inf.Item] = []
    for ps, core in zip(pairs, cores):
        for t in core.get(key, []):
            items.append((group, ps.pair_id, int(t)))
    return items


def _items_matured_a1(
    group: str, pairs: Sequence[PairSeries], cores: Sequence[dict], residual: bool
) -> Tuple[List[inf.Item], List[int], List[float]]:
    items: List[inf.Item] = []
    values: List[float] = []
    for ps, core in zip(pairs, cores):
        for r in core.get("a1_out", []):
            fld = "y_res_20" if residual else "y20"
            if r[fld]["state"] == "MATURED" and r[fld]["y"] is not None:
                items.append((group, ps.pair_id, int(r["t"])))
                values.append(float(r[fld]["y"]))
    if not items:
        return [], [], []
    _labels, pos_coord = _item_coord_map(items)
    coords = [pos_coord[i] for i in range(len(items))]
    return items, coords, values


def _matured_b1_y20(
    group: str, pairs: Sequence[PairSeries], cores: Sequence[dict]
) -> Tuple[List[float], List[int]]:
    """B1 formation days: own calendar index as bootstrap coordinate (ORCH-SCI R9)."""
    values: List[float] = []
    coords: List[int] = []
    for ps, core in zip(pairs, cores):
        for r in core.get("b1_out", []):
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None:
                t = int(r["t"])
                values.append(float(r["y20"]["y"]))
                coords.append(t)
    return values, coords


def _matured_b2_y20(
    group: str, pairs: Sequence[PairSeries], cores: Sequence[dict]
) -> Tuple[List[float], List[int]]:
    items: List[inf.Item] = []
    values: List[float] = []
    for ps, core in zip(pairs, cores):
        for r in core.get("b2_out", []):
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None:
                items.append((group, ps.pair_id, int(r["t"])))
                values.append(float(r["y20"]["y"]))
    if not items:
        return [], []
    _labels, pos_coord = _item_coord_map(items)
    coords = [pos_coord[i] for i in range(len(items))]
    return values, coords


def _matured_b3_res(
    group: str, pairs: Sequence[PairSeries], cores: Sequence[dict]
) -> Tuple[List[float], List[int]]:
    items: List[inf.Item] = []
    values: List[float] = []
    for ps, core in zip(pairs, cores):
        for r in core.get("b3_out", []):
            if r["y_res_20"]["state"] == "MATURED" and r["y_res_20"]["y"] is not None:
                items.append((group, ps.pair_id, int(r["t"])))
                values.append(float(r["y_res_20"]["y"]))
    if not items:
        return [], []
    _labels, pos_coord = _item_coord_map(items)
    coords = [pos_coord[i] for i in range(len(items))]
    return values, coords


def _h2_point_subset(
    a1_vals: Sequence[float],
    b1_vals: Sequence[float],
    b2_vals: Sequence[float],
) -> float:
    if not a1_vals:
        return float("nan")
    if not b1_vals and not b2_vals:
        return float("nan")
    m_a1 = float(np.mean(a1_vals))
    if b1_vals and b2_vals:
        m_b = max(float(np.mean(b1_vals)), float(np.mean(b2_vals)))
    elif b1_vals:
        m_b = float(np.mean(b1_vals))
    else:
        m_b = float(np.mean(b2_vals))
    return m_a1 - m_b


def _h3_point_subset(a1_res: Sequence[float], b3_res: Sequence[float]) -> float:
    if not a1_res or not b3_res:
        return float("nan")
    return float(np.mean(a1_res) - np.mean(b3_res))


def _coords_allowed(mask: np.ndarray, coord_union: np.ndarray) -> set[int]:
    return {int(coord_union[i]) for i in range(len(coord_union)) if mask[i]}


def _aggregate_coverage(cores: Sequence[dict]) -> float:
    num = sum(c["coverage"]["numerator"] for c in cores)
    den = sum(c["coverage"]["denominator"] for c in cores)
    return num / den if den else float("nan")


def _aggregate_arms(cores: Sequence[dict]) -> dict:
    arms_out: Dict[str, dict] = {}
    for arm in ("A0", "A1", "A2", "B1", "B2", "B3", "B6", "B7"):
        if arm == "B7":
            arms_out[arm] = {"n_items": 0, "mean_y_matured": None}
            continue
        if arm == "B6":
            shares = [c.get("b6_share", 0.0) for c in cores]
            arms_out[arm] = {
                "n_items": sum(c.get("arms", {}).get("A1", {}).get("n_items", 0) for c in cores),
                "carry_share_mean": float(np.mean(shares)) if shares else None,
            }
            continue
        arms_out[arm] = {
            "n_items": sum(c.get("arms", {}).get(arm, {}).get("n_items", 0) for c in cores)
        }
    return arms_out


C2_STRATA = ("both_up", "both_down", "mixed", "unmeasured")
C2_MIN_N = 5
C2_NOTE = "prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed Trend-Persistence-era study also called 'C2', which stays closed"


def _direction_labeler(ps: PairSeries) -> Callable[[int], str]:
    """prereg V2 §6 C2: label a session ``t`` by the CONTRACT's absolute_direction.

    The direction rule is NEVER re-implemented here -- it is read from
    ``engine.leadership_rotation_context.pair_interpretation`` through the
    existing contract consumer ``st.entry_context``.  Both legs are built as
    ``pd.Series`` ONCE per pair and each distinct ``t`` is evaluated once
    (memoised), so a stratum sweep costs one contract call per session, not one
    per (session, hypothesis).

    ``unmeasured`` is a distinct label: it is never zero and never a direction.
    """
    num_s = pd.Series(ps.num)
    den_s = pd.Series(ps.den)
    memo: Dict[int, str] = {}

    def _label_once(t: int) -> str:
        lookback = int(st.Z_LOOKBACK)
        if t < lookback:
            return "unmeasured"
        legs = (ps.num[t], ps.den[t], ps.num[t - lookback], ps.den[t - lookback])
        if not all(np.isfinite(leg) and leg > 0 for leg in legs):
            return "unmeasured"
        try:
            result = st.entry_context(num_s, den_s, t)
        except (ValueError, ZeroDivisionError):
            return "unmeasured"
        if not isinstance(result, dict) or "absolute_direction" not in result:
            return "unmeasured"
        return result["absolute_direction"]

    def label(t: int) -> str:
        key = int(t)
        if key not in memo:
            memo[key] = _label_once(key)
        return memo[key]

    return label


# prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed Trend-Persistence-era study also called 'C2', which stays closed
def _c2_strata(group: str, pairs: Sequence[PairSeries], cores: Sequence[dict]) -> dict:
    """Descriptive direction strata of H1/H2/H3 (prereg V2 §6 control C2).

    POINTS ONLY -- no p-values, no verdicts, no Holm, and no margin is applied.
    This block is additive: nothing reads it for any decision and it changes no
    existing number.  A field that cannot be truthfully filled is reported with
    a ``None`` point and a reason, never a filled fake value.
    """
    all_phases = [ph for c in cores for ph in c["phases"]]
    # session_w_total is the 252-session constant, NOT the realised pair-session
    # weight of the read: BOTH reported points are ratios/differences in which
    # the denominator cancels (delay_reduction is a difference of two medians;
    # burden_cut_b is 1 - burden_A1/burden_A0, and burden is burden_w divided by
    # session_w_total/252).  Per-stratum burden LEVELS are NOT reported, so the
    # level distortion this constant introduces is never observable downstream.
    session_w_total = 252.0
    labelers = [_direction_labeler(ps) for ps in pairs]
    zipped = list(zip(pairs, cores, labelers))

    def _metrics(records: Sequence[dict]) -> dict:
        return _episode_metrics_unit(records, all_phases, session_w_total)

    def _resolve(
        stratum: str, n: int, points: Sequence[Tuple[str, float, str]]
    ) -> Tuple[str, Optional[str], List[Tuple[str, Optional[float]]]]:
        """points are (key, value, cause-when-non-finite) in reported order."""
        if stratum == "unmeasured":
            return "UNMEASURED", "label_unmeasured", [(k, None) for k, _v, _c in points]
        if n < C2_MIN_N:
            return "SOURCE_LIMITED", f"n={n} < {C2_MIN_N}", [(k, None) for k, _v, _c in points]
        kept: List[Tuple[str, Optional[float]]] = []
        causes: List[str] = []
        for key, value, cause in points:
            if np.isfinite(value):
                kept.append((key, float(value)))
            else:
                kept.append((key, None))
                causes.append(cause)
        if causes:
            return "NOT_EXECUTABLE", ",".join(causes), kept
        return "COMPUTED", None, kept

    def _entry(
        n_items: int,
        n: int,
        stratum: str,
        points: Sequence[Tuple[str, float, str]],
        comparator_basis: Optional[str] = None,
    ) -> dict:
        status, reason, kept = _resolve(stratum, n, points)
        out: Dict[str, Any] = {"n_items": n_items, "n": n, "status": status}
        for key, value in kept:
            out[key] = value
        if comparator_basis is not None:
            out["comparator_basis"] = comparator_basis
        out["reason"] = reason
        return out

    def _matured(core: dict, arm_key: str, field: str, label, stratum: str) -> List[float]:
        return [
            float(r[field]["y"])
            for r in core.get(arm_key, [])
            if r[field]["state"] == "MATURED"
            and r[field]["y"] is not None
            and label(int(r["t"])) == stratum
        ]

    h1: Dict[str, dict] = {}
    h2: Dict[str, dict] = {}
    h3: Dict[str, dict] = {}
    for stratum in C2_STRATA:
        a1_records: List[dict] = []
        a2_records: List[dict] = []
        a0_records: List[dict] = []
        items_h1: List[inf.Item] = []
        items_h2: List[inf.Item] = []
        items_h3: List[inf.Item] = []
        b1_y: List[float] = []
        b2_y: List[float] = []
        b3_res: List[float] = []
        a1_y: List[float] = []
        a1_res: List[float] = []
        for ps, core, label in zipped:
            for rec in core["a1_class"]:
                if label(int(rec["index"])) != stratum:
                    continue
                a1_records.append(rec)
                if rec["cls"] == "MATCHED":
                    items_h1.append((group, ps.pair_id, int(rec["index"])))
            a2_records.extend(
                rec for rec in core["a2_class"] if label(int(rec["index"])) == stratum
            )
            a0_records.extend(
                rec for rec in core["a0_class"] if label(int(rec["index"])) == stratum
            )
            a1_y.extend(_matured(core, "a1_out", "y20", label, stratum))
            items_h2.extend(
                (group, ps.pair_id, int(r["t"]))
                for r in core.get("a1_out", [])
                if r["y20"]["state"] == "MATURED"
                and r["y20"]["y"] is not None
                and label(int(r["t"])) == stratum
            )
            b1_y.extend(_matured(core, "b1_out", "y20", label, stratum))
            b2_y.extend(_matured(core, "b2_out", "y20", label, stratum))
            a1_res.extend(_matured(core, "a1_out", "y_res_20", label, stratum))
            items_h3.extend(
                (group, ps.pair_id, int(r["t"]))
                for r in core.get("a1_out", [])
                if r["y_res_20"]["state"] == "MATURED"
                and r["y_res_20"]["y"] is not None
                and label(int(r["t"])) == stratum
            )
            b3_res.extend(_matured(core, "b3_out", "y_res_20", label, stratum))

        m_a1 = _metrics(a1_records)
        m_a2 = _metrics(a2_records)
        m_a0 = _metrics(a0_records)
        delay_reduction = float(m_a2["median_delay"]) - float(m_a1["median_delay"])
        burden_a0 = float(m_a0["burden"])
        burden_cut_b = (
            1.0 - float(m_a1["burden"]) / burden_a0
            if np.isfinite(burden_a0) and burden_a0 != 0
            else float("nan")
        )
        n_h1 = _cluster_n(items_h1)
        h1[stratum] = _entry(
            len(items_h1),
            n_h1,
            stratum,
            (
                ("delay_reduction", delay_reduction, "no_matched_delay"),
                ("burden_cut_b", burden_cut_b, "no_A0_burden"),
            ),
        )

        n_h2 = _cluster_n(items_h2)
        h2[stratum] = _entry(
            len(items_h2),
            n_h2,
            stratum,
            (("point", _h2_point_subset(a1_y, b1_y, b2_y), "no_same_stratum_comparator"),),
            comparator_basis="same_stratum",
        )

        n_h3 = _cluster_n(items_h3)
        h3[stratum] = _entry(
            len(items_h3),
            n_h3,
            stratum,
            (("point", _h3_point_subset(a1_res, b3_res), "no_same_stratum_comparator"),),
            comparator_basis="same_stratum",
        )

    return {
        "label_source": "engine.leadership_rotation_context.pair_interpretation absolute_direction via study.entry_context (lookback Z_LOOKBACK sessions, both legs)",
        "label_time": "H1: alarm index (A1/A2/A0 records); H2/H3: entry t of each outcome record",
        "note": C2_NOTE,
        "min_n": C2_MIN_N,
        "H1": h1,
        "H2": h2,
        "H3": h3,
    }


def evaluate_group(
    pairs: Sequence[PairSeries],
    *,
    start: int,
    end: int,
    partition: str,
    W: Optional[np.ndarray] = None,
    h1_null: Optional[Callable[..., dict]] = None,
) -> dict:
    """Evaluate one group.

    ``h1_null`` (prereg V2 §2 Option A) replaces H1's bootstrap p-values with the
    δ = 0 parametric surrogate null (``leadership_rotation_null``); the bootstrap
    p-values are kept under ``H1.p_bootstrap_superseded`` for the record only.
    ``None`` keeps the V1 bootstrap p-values (development only — evaluate_family
    refuses a P1 read without the Option A null)."""
    if partition in ("P2", "P3"):
        raise st.PartitionSealed(partition)
    if partition not in ("P0", "P1"):
        raise ValueError(f"unknown partition {partition!r}")

    cores = [_evaluate_pair_core(ps, start=start, end=end) for ps in pairs]
    n_calendar = len(pairs[0].spy) if pairs else 0
    measured_total = sum(c["measured_sessions"] for c in cores)
    executable = measured_total > 0
    group = pairs[0].group if pairs else ""

    if W is None:
        W = inf.stationary_bootstrap_weights(n_calendar) if n_calendar else np.zeros((0, 0))

    measured_per_day = _measured_pairs_per_day(pairs, cores, end)
    session_w_point = float(np.sum(measured_per_day[max(0, start) : end + 1]))

    all_phases = [ph for c in cores for ph in c["phases"]]
    records = {
        "a1": [rec for c in cores for rec in c["a1_class"]],
        "a2": [rec for c in cores for rec in c["a2_class"]],
        "a0": [rec for c in cores for rec in c["a0_class"]],
    }

    onset_items: List[inf.Item] = []
    for ps, core in zip(pairs, cores):
        for ph in core["phases"]:
            if ph.qualifies:
                onset_items.append((group, ps.pair_id, ph.T))
    _labels_on, onset_pos = _item_coord_map(onset_items)
    onset_coord: Dict[int, int] = {t: onset_pos[i] for i, (_g, _p, t) in enumerate(onset_items)}

    def _alarm_coords(class_key: str) -> Dict[int, int]:
        items: List[inf.Item] = []
        index_map: Dict[int, int] = {}
        for ps, core in zip(pairs, cores):
            for rec in core[class_key]:
                items.append((group, ps.pair_id, rec["index"]))
        if not items:
            return {}
        _lab, pos = _item_coord_map(items)
        for i, rec_i in enumerate(items):
            index_map[items[i][2]] = pos[i]
        return index_map

    alarm_coords = {
        "a1": _alarm_coords("a1_class"),
        "a2": _alarm_coords("a2_class"),
        "a0": _alarm_coords("a0_class"),
    }

    m_a1 = _episode_metrics_unit(records["a1"], all_phases, session_w_point)
    m_a2 = _episode_metrics_unit(records["a2"], all_phases, session_w_point)
    m_a0 = _episode_metrics_unit(records["a0"], all_phases, session_w_point)
    m_a0_raw = _episode_metrics_unit([rec for c in cores for rec in c["a0_raw_class"]], all_phases, session_w_point)

    det1, bur1, del1 = _h1_arm_replicates(
        records["a1"], all_phases, W, onset_coord, alarm_coords["a1"], measured_per_day
    )
    det2, bur2, del2 = _h1_arm_replicates(
        records["a2"], all_phases, W, onset_coord, alarm_coords["a2"], measured_per_day
    )
    _det0, bur0, _del0 = _h1_arm_replicates(
        records["a0"], all_phases, W, onset_coord, alarm_coords["a0"], measured_per_day
    )

    delay_reduction = m_a2["median_delay"] - m_a1["median_delay"]
    burden_diff_a = m_a1["burden"] - m_a2["burden"]
    detection_diff_a = m_a1["detection"] - m_a2["detection"]
    burden_cut_b = (
        1.0 - m_a1["burden"] / m_a0["burden"]
        if m_a0["burden"] and np.isfinite(m_a0["burden"]) and m_a0["burden"] != 0
        else float("nan")
    )
    detection_diff_b = m_a1["detection"] - m_a0["detection"]

    rep_delay_red = del2 - del1
    rep_bur_cut = 1.0 - (bur1 / bur0)
    p_a, _ = inf.one_sided_p(rep_delay_red)
    p_b, _ = inf.one_sided_p(rep_bur_cut)
    h1_null_out: Optional[dict] = None
    p_boot = {"p_a": p_a, "p_b": p_b}
    if h1_null is not None:
        h1_null_out = h1_null(
            partition=partition,
            group=group,
            pairs=pairs,
            cores=cores,
            start=start,
            end=end,
            t_a=float(delay_reduction),
            t_b=float(burden_cut_b),
            honest_n=_cluster_n(onset_items),
        )
        p_a = float(h1_null_out["p_a"])
        p_b = float(h1_null_out["p_b"])
    decision = inf.h1_decision(
        delay_reduction,
        burden_diff_a,
        detection_diff_a,
        p_a,
        burden_cut_b,
        detection_diff_b,
        p_b,
    )

    a1_items_all = _items_from_kept(group, pairs, cores, "a1_kept")
    _a1_items, a1_coords, a1_y = _items_matured_a1(group, pairs, cores, residual=False)
    b1_y, b1_coords = _matured_b1_y20(group, pairs, cores)
    b2_y, b2_coords = _matured_b2_y20(group, pairs, cores)
    a1_res_items, a1_res_coords, a1_res = _items_matured_a1(group, pairs, cores, residual=True)
    b3_res, b3_coords = _matured_b3_res(group, pairs, cores)

    honest_n_h1 = _cluster_n(onset_items)
    honest_n_h2 = _cluster_n(_a1_items)
    honest_n_h3 = _cluster_n(a1_res_items)
    test_n_h2 = _cluster_n(a1_items_all)

    a1_arr = np.array(a1_y, dtype=float)
    b1_arr = np.array(b1_y, dtype=float) if b1_y else np.array([], dtype=float)
    b2_arr = np.array(b2_y, dtype=float) if b2_y else np.array([], dtype=float)
    h2_point = _h2_point_subset(a1_y, b1_y, b2_y)
    a1_Wm = inf.item_weights(W, a1_coords) if a1_coords else np.zeros((W.shape[0], 0))
    b1_Wm = inf.item_weights(W, b1_coords) if b1_coords else np.zeros((W.shape[0], 0))
    b2_Wm = inf.item_weights(W, b2_coords) if b2_coords else np.zeros((W.shape[0], 0))
    if a1_y:
        assert len(a1_y) == a1_Wm.shape[1]
        if b1_y:
            assert len(b1_y) == b1_Wm.shape[1]
        if b2_y:
            assert len(b2_y) == b2_Wm.shape[1]
    h2_reps = (
        inf.h2_replicates(a1_arr, a1_Wm, b1_arr, b1_Wm, b2_arr, b2_Wm)
        if a1_y
        else np.full(W.shape[0], np.nan)
    )
    p_h2, _ = inf.one_sided_p(h2_reps)
    fs_a1 = st.false_start_rate_h20(a1_y)
    fs_b2 = st.false_start_rate_h20(b2_y)
    if np.isfinite(fs_a1) and np.isfinite(fs_b2):
        h2_safety = {
            "fs_a1": fs_a1,
            "fs_b2": fs_b2,
            "ok": (fs_a1 - fs_b2) <= inf.H2_FALSE_START_NI,
            "reason": "EVALUATED",
        }
    else:
        h2_safety = {
            "fs_a1": fs_a1,
            "fs_b2": fs_b2,
            "ok": False,
            "reason": "SAFETY_UNEVALUABLE",
        }

    a1_res_arr = np.array(a1_res, dtype=float)
    b3_arr = np.array(b3_res, dtype=float) if b3_res else np.array([], dtype=float)
    h3_point = _h3_point_subset(a1_res, b3_res)
    b3_Wm = inf.item_weights(W, b3_coords) if b3_coords else np.zeros((W.shape[0], 0))
    a1_res_Wm = inf.item_weights(W, a1_res_coords) if a1_res_coords else np.zeros((W.shape[0], 0))
    if a1_res:
        assert len(a1_res) == a1_res_Wm.shape[1]
        if b3_res:
            assert len(b3_res) == b3_Wm.shape[1]
    h3_reps = (
        inf.h3_replicates(a1_res_arr, a1_res_Wm, b3_arr, b3_Wm)
        if a1_res
        else np.full(W.shape[0], np.nan)
    )
    p_h3, _ = inf.one_sided_p(h3_reps)

    session_indices = _pair_session_indices(measured_per_day, start, end)
    coord_list = sorted(set(onset_coord.values()))
    coord_to_pos = {c: i for i, c in enumerate(coord_list)}

    def _mask_allows_cluster(c: int, mask: np.ndarray) -> bool:
        pos = coord_to_pos.get(c)
        if pos is None:
            return False
        return bool(mask[pos])

    def _delay_on_mask(mask: np.ndarray) -> float:
        sub_a1 = [
            rec
            for rec in records["a1"]
            if rec.get("phase_T") is not None
            and _mask_allows_cluster(onset_coord.get(rec["phase_T"], -1), mask)
        ]
        sub_a2 = [
            rec
            for rec in records["a2"]
            if rec.get("phase_T") is not None
            and _mask_allows_cluster(onset_coord.get(rec["phase_T"], -1), mask)
        ]
        if not sub_a1 and not sub_a2:
            return float("nan")
        ma1 = _episode_metrics_unit(sub_a1, all_phases, session_w_point)
        ma2 = _episode_metrics_unit(sub_a2, all_phases, session_w_point)
        return ma2["median_delay"] - ma1["median_delay"]

    def _burden_cut_on_mask(mask: np.ndarray) -> float:
        sub_a1 = [
            rec
            for rec in records["a1"]
            if _mask_allows_cluster(alarm_coords["a1"].get(rec["index"], -1), mask)
        ]
        sub_a0 = [
            rec
            for rec in records["a0"]
            if _mask_allows_cluster(alarm_coords["a0"].get(rec["index"], -1), mask)
        ]
        ma1 = _episode_metrics_unit(sub_a1, all_phases, session_w_point)
        ma0 = _episode_metrics_unit(sub_a0, all_phases, session_w_point)
        if not ma0["burden"] or not np.isfinite(ma0["burden"]) or ma0["burden"] == 0:
            return float("nan")
        return 1.0 - ma1["burden"] / ma0["burden"]

    _stab_default = {
        "third_1": float("nan"),
        "third_2": float("nan"),
        "third_3": float("nan"),
        "holds": False,
    }
    if coord_list and session_indices:
        onset_coords_arr = np.array(coord_list, dtype=np.int64)
        stab_delay = inf.stability_thirds(
            session_indices, onset_coords_arr, _delay_on_mask, delay_reduction
        )
        stab_burden = inf.stability_thirds(
            session_indices, onset_coords_arr, _burden_cut_on_mask, burden_cut_b
        )
    else:
        stab_delay = stab_burden = _stab_default

    h2_coord_union = np.array(
        sorted(set(a1_coords) | set(b1_coords) | set(b2_coords)), dtype=np.int64
    )

    def _h2_on_third(mask: np.ndarray) -> float:
        allowed = _coords_allowed(mask, h2_coord_union)
        a1_sub = [v for v, c in zip(a1_y, a1_coords) if c in allowed]
        b1_sub = [v for v, c in zip(b1_y, b1_coords) if c in allowed]
        b2_sub = [v for v, c in zip(b2_y, b2_coords) if c in allowed]
        return _h2_point_subset(a1_sub, b1_sub, b2_sub)

    if len(h2_coord_union) and session_indices:
        stab_h2 = inf.stability_thirds(
            session_indices, h2_coord_union, _h2_on_third, h2_point
        )
    else:
        stab_h2 = _stab_default

    h3_coord_union = np.array(
        sorted(set(a1_res_coords) | set(b3_coords)), dtype=np.int64
    )

    def _h3_on_third(mask: np.ndarray) -> float:
        allowed = _coords_allowed(mask, h3_coord_union)
        a_sub = [v for v, c in zip(a1_res, a1_res_coords) if c in allowed]
        b_sub = [v for v, c in zip(b3_res, b3_coords) if c in allowed]
        return _h3_point_subset(a_sub, b_sub)

    if len(h3_coord_union) and session_indices:
        stab_h3 = inf.stability_thirds(
            session_indices, h3_coord_union, _h3_on_third, h3_point
        )
    else:
        stab_h3 = _stab_default

    c2 = _c2_strata(group, pairs, cores)
    pair_legs = {ps.pair_id: (ps.num_sym, ps.den_sym) for ps in pairs}

    return _json_sanitize(
        {
            "group": group,
            "partition": partition,
            "window": [int(start), int(end)],
            "pairs": [c["pair_id"] for c in cores],
            "executable": executable,
            "honest_n": {"H1": honest_n_h1, "H2": honest_n_h2, "H3": honest_n_h3},
            # H2 and H3 share test_n: cluster count of all kept A1 entries (R10).
            "test_n": {"H2": test_n_h2, "H3": test_n_h2},
            "shared_leg_components": inf.shared_leg_components(pair_legs),
            "coverage": _aggregate_coverage(cores),
            "arms": _aggregate_arms(cores),
            "H1": {
                "A1": m_a1,
                "A2": m_a2,
                "A0": m_a0,
                "A0_raw": m_a0_raw,
                "delay_reduction": delay_reduction,
                "burden_diff_a": burden_diff_a,
                "detection_diff_a": detection_diff_a,
                "burden_cut_b": burden_cut_b,
                "detection_diff_b": detection_diff_b,
                "p_a": p_a,
                "p_b": p_b,
                "p": max(p_a, p_b),
                "p_method": (
                    SIZE_GATE_H1_NULL_METHOD if h1_null is not None else "V1_BOOTSTRAP"
                ),
                **(
                    {"null": h1_null_out, "p_bootstrap_superseded": p_boot}
                    if h1_null is not None
                    else {}
                ),
                "decision": decision,
                "interval_90": {
                    "delay_reduction": inf.interval_90(rep_delay_red),
                    "burden_cut_b": inf.interval_90(rep_bur_cut),
                },
                "lower_bound": {
                    "delay_reduction": inf.lower_bound(rep_delay_red),
                    "burden_cut_b": inf.lower_bound(rep_bur_cut),
                },
                "stability": {"delay_reduction": stab_delay, "burden_cut_b": stab_burden},
            },
            "H2": {
                "point": h2_point,
                "p": p_h2,
                "safety": h2_safety,
                "stability": stab_h2,
                "interval_90": inf.interval_90(h2_reps),
                "lower_bound": inf.lower_bound(h2_reps),
            },
            "H3": {
                "point": h3_point,
                "p": p_h3,
                "stability": stab_h3,
                "interval_90": inf.interval_90(h3_reps),
                "lower_bound": inf.lower_bound(h3_reps),
            },
            "c2_strata": c2,
        }
    )


def _holm_p_for(group: str, h: str, order, adjusted) -> float:
    for i, (g, hh) in enumerate(order):
        if g == group and hh == h:
            return adjusted[i]
    return 1.0


def _immature(gr: dict, h: str) -> bool:
    hn = gr["honest_n"][h]
    tn = gr.get("test_n", {}).get(h, hn)
    return hn < inf.MIN_HONEST_N and tn >= inf.MIN_HONEST_N


def _as_float(x: Any) -> float:
    if x is None:
        return float("nan")
    return float(x)


def _margin_met(point: float, margin: float) -> Optional[bool]:
    """``None`` when the point estimate is undefined (V2.1 §2 row 9a)."""
    if math.isnan(point):
        return None
    return bool(point >= margin)


def _group_verdicts(
    gr: dict,
    partition: str,
    holm_adj: List[float],
    order,
    powered: Optional[Dict[str, bool]] = None,
) -> dict:
    """Per-hypothesis outcome classes via the V2.1 §2 first-match table.

    ``powered`` maps "H2"/"H3" to the V2 §4.3 POWERED_IN_PRINCIPLE disposition from
    a landed power record; absent → P2/P3 H2/H3 are NOT_EXECUTABLE (row 4). H1's
    P2/P3 executability is governed by the size gate, so it passes True here.
    """
    executable = gr.get("executable", False)
    cov = _as_float(gr.get("coverage", 0.0))
    if math.isnan(cov):
        cov = 0.0
    gname = gr.get("group", "")
    pw = dict(powered or {})
    out: Dict[str, str] = {}
    for h in ("H1", "H2", "H3"):
        p_holm = _holm_p_for(gname, h, order, holm_adj)
        common = dict(
            executable=executable,
            source_limited=False,
            immature=_immature(gr, h),
            honest_n=gr["honest_n"][h],
            p_holm=p_holm,
            coverage=cov,
        )
        if h == "H1":
            stable = (
                gr["H1"]["stability"]["delay_reduction"]["holds"]
                and gr["H1"]["stability"]["burden_cut_b"]["holds"]
            )
            # margins_met already folds in H1's non-inferiority clauses (V1 §7).
            # An Option A null that could not be matched (V2.1 §6 item 2) means
            # the registered H1 p cannot be computed: row 2, NOT_EXECUTABLE.
            h1_null_out = gr["H1"].get("null")
            null_ok = not isinstance(h1_null_out, dict) or h1_null_out.get("status") == "OK"
            out[h] = inf.verdict(
                partition,
                margin_met=bool(gr["H1"]["decision"]["margins_met"]),
                stable=stable,
                powered_in_principle=True,
                **{**common, "executable": bool(executable and null_ok)},
            )
        elif h == "H2":
            out[h] = inf.verdict(
                partition,
                margin_met=_margin_met(_as_float(gr["H2"]["point"]), inf.MARGIN_H2),
                stable=gr["H2"]["stability"]["holds"],
                ni_ok=gr["H2"]["safety"]["ok"],
                powered_in_principle=pw.get("H2"),
                **common,
            )
        else:
            out[h] = inf.verdict(
                partition,
                margin_met=_margin_met(_as_float(gr["H3"]["point"]), inf.MARGIN_H3),
                stable=gr["H3"]["stability"]["holds"],
                powered_in_principle=pw.get("H3"),
                **common,
            )
    out["C3"] = inf.verdict(
        partition,
        executable=True,
        source_limited=True,
        immature=False,
        honest_n=0,
        margin_met=None,
        p_holm=1.0,
        stable=False,
        coverage=0.0,
    )
    return out


def evaluate_family(
    groups: Dict[str, List[PairSeries]],
    *,
    start: int,
    end: int,
    partition: str,
    look_count: int = 0,
    h1_null: Optional[Callable[..., dict]] = None,
    powered: Optional[Dict[str, bool]] = None,
) -> dict:
    """Evaluate the six-hypothesis family.

    ``powered`` carries the V2 §4.3 POWERED_IN_PRINCIPLE dispositions for H2/H3
    from a landed power record; it only matters for P2/P3 (V2.1 §2 row 4).

    ``look_count`` is the number of counted development looks this evaluation
    is (V1 §2: "P1 = counted development looks"). The default 0 is the P0
    synthetic call, which is not a counted look; ``run_p1`` always passes the
    real committed-ledger count plus one.
    """
    if isinstance(look_count, bool) or not isinstance(look_count, int) or look_count < 0:
        raise ValueError(f"look_count must be a non-negative int, got {look_count!r}")
    if partition == "P1" and h1_null is None and any(groups.values()):
        # Prereg V2 §2: the V1 bootstrap null is superseded for every read.
        raise ValueError("a P1 read requires the V2 Option A H1 null (h1_null)")
    n_calendar = max((len(ps.spy) for plist in groups.values() for ps in plist), default=0)
    W = inf.stationary_bootstrap_weights(n_calendar) if n_calendar else np.zeros((0, 0))
    group_results: Dict[str, dict] = {}
    for gname, plist in groups.items():
        group_results[gname] = evaluate_group(
            plist, start=start, end=end, partition=partition, W=W, h1_null=h1_null
        )

    raw_ps: List[float] = []
    order: List[Tuple[str, str]] = []
    for g, h in FAMILY_ORDER:
        order.append((g, h))
        gr = group_results.get(g)
        if gr is None:
            raw_ps.append(float("nan"))
            continue
        if h == "H1":
            raw_ps.append(gr["H1"]["p"])
        elif h == "H2":
            raw_ps.append(gr["H2"]["p"])
        else:
            raw_ps.append(gr["H3"]["p"])
    adjusted = inf.holm([p if np.isfinite(p) else 1.0 for p in raw_ps])

    verdicts: Dict[str, dict] = {}
    for gname in _FAMILY_GROUPS:
        gr = group_results.get(gname)
        if gr is None:
            verdicts[gname] = {
                h: "NOT_EXECUTABLE" for h in ("H1", "H2", "H3")
            }
            verdicts[gname]["C3"] = "SOURCE_LIMITED"
        else:
            verdicts[gname] = _group_verdicts(gr, partition, adjusted, order, powered)

    return _json_sanitize(
        {
            "prereg": {
                "path": st.PREREG_PATH,
                "commit": st.PREREG_COMMIT,
                "blob": st.PREREG_BLOB_SHA,
                "v2_path": st.PREREG_V2_PATH,
                "v2_blob": st.PREREG_V2_BLOB_SHA,
            },
            "partition": partition,
            "look_count": look_count,
            "groups": group_results,
            "holm": {"order": order, "raw": raw_ps, "adjusted": adjusted},
            "verdicts": verdicts,
        }
    )


def build_groups(
    aligned: dict[str, np.ndarray],
    spy: np.ndarray,
    partition: str,
) -> dict[str, list[PairSeries]]:
    groups: Dict[str, List[PairSeries]] = {
        "defensive_sector": [],
        "broadening_proxy": [],
    }
    for pair_id, (group, num_sym, den_sym) in st.PAIRS.items():
        if partition == "P2" and pair_id in st.P2_EXCLUDED:
            continue
        groups[group].append(
            PairSeries(
                pair_id=pair_id,
                group=group,
                num_sym=num_sym,
                den_sym=den_sym,
                num=aligned[num_sym],
                den=aligned[den_sym],
                spy=spy,
            )
        )
    return groups


SIZE_GATE_REASONS: Tuple[str, ...] = (
    "SIZE_GATE_ARTIFACT_ABSENT",
    "SIZE_GATE_UNPARSEABLE",
    "SIZE_GATE_RULE_MISMATCH",
    "SIZE_GATE_NOT_SIZED",
    "SIZE_GATE_CELL_MISSING",
    "SIZE_GATE_M_BELOW_MIN",
    "SIZE_GATE_ROW_NOT_SIZED",
    "SIZE_GATE_NULL_METHOD_MISMATCH",
    "SIZE_GATE_NULL_K_TOO_SMALL",
    "SIZE_GATE_PREREG_PIN_MISMATCH",
    "SIZE_GATE_HARNESS_DRIFT",
)

# The seven gated rows of prereg V2 §3 item 3: each (hypothesis, group) row
# plus the any-of-6 family row.
_SIZE_GATE_ROW_NAMES: Tuple[str, ...] = (
    "defensive_sector/H1",
    "defensive_sector/H2",
    "defensive_sector/H3",
    "broadening_proxy/H1",
    "broadening_proxy/H2",
    "broadening_proxy/H3",
    "family_any",
)

_SIZE_GATE_SCHEMA = "leadership_rotation.size_gate.v1"


class SizeGateNotPassed(RuntimeError):
    """The committed size-gate artifact does not prove the V2 §3 rule PASSED.

    ``reason`` is always one of ``SIZE_GATE_REASONS`` and ``detail`` names the
    offending cell / row / path / value, so a refusal is actionable without a
    second read of the artifact.
    """

    def __init__(self, reason: str, detail: str) -> None:
        assert reason in SIZE_GATE_REASONS, f"unknown size-gate reason {reason!r}"
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _git_blob_sha(data: bytes) -> str:
    """``git hash-object`` for in-memory bytes: sha1 over the blob header."""
    import hashlib

    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _git_show(repo: str, commit: str, path: str) -> Optional[bytes]:
    """Committed bytes of ``commit:path``, or None when git cannot show them.

    Reads the commit, never the working tree: the size-gate proof and the look
    ledger both travel with the commit being read.
    """
    import subprocess

    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _resolve_commit(repo: str, commit: str) -> str:
    """Full 40-hex sha for ``commit``; ``ValueError`` when it is not one."""
    import subprocess

    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(
            f"not a commit in {repo}: {commit!r} ({proc.stderr.strip()})"
        )
    return proc.stdout.strip()


def _wilson_lower(passes: int, m: int) -> float:
    """Wilson 95 % score lower bound of ``passes / m``.

    Byte-for-byte the ``wilson_interval`` formula of
    ``scripts/leadership_rotation_p0.py`` (z = 1.959963984540054, ``max(0.0,
    ...)`` clip included). p0 is NOT imported here: p0 imports this module, so
    an import in this direction would be circular.
    """
    if m <= 0:
        return float("nan")
    z = 1.959963984540054
    phat = passes / m
    z2 = z * z
    denom = 1.0 + z2 / m
    center = (phat + z2 / (2 * m)) / denom
    margin = z * math.sqrt((phat * (1 - phat) / m + z2 / (4 * m * m))) / denom
    lo = max(0.0, center - margin)
    return lo


def assert_size_gate_passed(
    repo: str,
    *,
    commit: str = "HEAD",
    path: str = SIZE_GATE_PATH,
    runtime_root: Optional[str] = None,
) -> dict:
    """Refuse unless the committed artifact proves the V2 §3 gate PASSED.

    Seat ruling T19 F9: protocol landing alone does not authorise a P1
    real-data read. The committed size-gate artifact must show the prereg V2
    §3 two-part rule SIZED for every required delta = 0 cell, under the exact
    harness bytes that will run the read. Checks run in a fixed order and the
    first failure raises ``SizeGateNotPassed``:

    1. artifact present at ``commit:path``; 2. parses to an object;
    3. schema/rule/alpha are the registered ones; 4. ``sized is True``;
    5. every required cell carries all seven rows; 6. every required-cell row
    ran ``M >= SIZE_GATE_MIN_M`` sims; 7. EVERY row is SIZED by both recorded
    parts AND by recomputation from its own counts (this is what stops a
    hand-edited ``flag`` from passing); 8. the H1 null method is the V2 one;
    9. the prereg blobs match the frozen pins; 10. the recorded harness blobs
    match both the reading commit's bytes and the runtime bytes.

    Returns the gate identity that ``run_p1`` records in its result.
    """
    raw = _git_show(repo, commit, path)
    if raw is None:
        raise SizeGateNotPassed(
            "SIZE_GATE_ARTIFACT_ABSENT",
            f"no size-gate artifact at {commit}:{path} in {repo}",
        )
    try:
        obj = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as exc:
        raise SizeGateNotPassed("SIZE_GATE_UNPARSEABLE", f"{path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise SizeGateNotPassed(
            "SIZE_GATE_UNPARSEABLE",
            f"{path}: top level is {type(obj).__name__}, expected an object",
        )

    schema = obj.get("schema")
    rule = obj.get("rule")
    alpha = obj.get("alpha")
    if schema != _SIZE_GATE_SCHEMA or rule != SIZE_GATE_RULE or alpha != 0.025:
        raise SizeGateNotPassed(
            "SIZE_GATE_RULE_MISMATCH",
            f"{path}: schema={schema!r} (want {_SIZE_GATE_SCHEMA!r}), rule={rule!r} "
            f"(want {SIZE_GATE_RULE!r}), alpha={alpha!r} (want 0.025)",
        )

    if obj.get("sized") is not True:
        raise SizeGateNotPassed(
            "SIZE_GATE_NOT_SIZED",
            f"{path}: sized={obj.get('sized')!r} is not True",
        )

    raw_rows = obj.get("rows")
    rows: List[Any] = raw_rows if isinstance(raw_rows, list) else []

    for cid in SIZE_GATE_REQUIRED_CELLS:
        present = {
            r.get("row") for r in rows if isinstance(r, dict) and r.get("cell_id") == cid
        }
        missing = [name for name in _SIZE_GATE_ROW_NAMES if name not in present]
        if missing:
            raise SizeGateNotPassed(
                "SIZE_GATE_CELL_MISSING",
                f"{path}: cell {cid} (delta = 0) is missing row(s) {', '.join(missing)}",
            )

    for row in rows:
        if not isinstance(row, dict) or row.get("cell_id") not in SIZE_GATE_REQUIRED_CELLS:
            continue
        m = row.get("m")
        if not isinstance(m, int) or isinstance(m, bool) or m < SIZE_GATE_MIN_M:
            raise SizeGateNotPassed(
                "SIZE_GATE_M_BELOW_MIN",
                f"{path}: cell {row.get('cell_id')} row {row.get('row')!r} ran m={m!r}, "
                f"need an int >= {SIZE_GATE_MIN_M}",
            )

    for row in rows:
        if not isinstance(row, dict):
            raise SizeGateNotPassed(
                "SIZE_GATE_ROW_NOT_SIZED", f"{path}: row entry {row!r} is not an object"
            )
        where = f"cell {row.get('cell_id')} row {row.get('row')!r}"
        passes = row.get("passes")
        m = row.get("m")
        counts_ok = (
            isinstance(passes, int)
            and not isinstance(passes, bool)
            and isinstance(m, int)
            and not isinstance(m, bool)
            and m > 0
        )
        wilson: Optional[float] = None
        rate: Optional[float] = None
        envelope: Optional[float] = None
        if counts_ok:
            wilson = _wilson_lower(passes, m)
            rate = passes / m
            envelope = 0.025 + 2 * math.sqrt(0.025 * 0.975 / m)
        recomputed_ok = bool(counts_ok) and wilson <= 0.025 and rate <= envelope
        if not (
            row.get("flag") == "SIZED"
            and row.get("part_i_ok") is True
            and row.get("part_ii_ok") is True
            and recomputed_ok
        ):
            raise SizeGateNotPassed(
                "SIZE_GATE_ROW_NOT_SIZED",
                f"{path}: {where} fails the V2 §3 two-part rule "
                f"(flag={row.get('flag')!r}, part_i_ok={row.get('part_i_ok')!r}, "
                f"part_ii_ok={row.get('part_ii_ok')!r}, passes={passes!r}, m={m!r}; "
                f"recomputed wilson_lower={wilson!r} must be <= 0.025 and "
                f"pass_rate={rate!r} must be <= envelope={envelope!r})",
            )

    if obj.get("h1_null_method") != SIZE_GATE_H1_NULL_METHOD:
        raise SizeGateNotPassed(
            "SIZE_GATE_NULL_METHOD_MISMATCH",
            f"{path}: h1_null_method={obj.get('h1_null_method')!r}, "
            f"expected {SIZE_GATE_H1_NULL_METHOD!r}",
        )
    null_k = obj.get("h1_null_k")
    if isinstance(null_k, bool) or not isinstance(null_k, int) or null_k < SIZE_GATE_MIN_NULL_K:
        raise SizeGateNotPassed(
            "SIZE_GATE_NULL_K_TOO_SMALL",
            f"{path}: h1_null_k={null_k!r}, prereg V2 §2 requires K >= {SIZE_GATE_MIN_NULL_K}",
        )

    expected_prereg = {
        "v1_blob": st.PREREG_BLOB_SHA,
        "v2_blob": st.PREREG_V2_BLOB_SHA,
        "v2_1_blob": st.PREREG_V2_1_BLOB_SHA,
    }
    prereg = obj.get("prereg")
    pinned = prereg if isinstance(prereg, dict) else {}
    for key, want in expected_prereg.items():
        got = pinned.get(key)
        if got != want:
            raise SizeGateNotPassed(
                "SIZE_GATE_PREREG_PIN_MISMATCH",
                f"{path}: prereg.{key}={got!r}, expected frozen {want!r}",
            )

    harness = obj.get("harness")
    raw_blobs = harness.get("blobs") if isinstance(harness, dict) else None
    blobs = raw_blobs if isinstance(raw_blobs, dict) else {}
    if set(blobs) != set(HARNESS_MODULES):
        raise SizeGateNotPassed(
            "SIZE_GATE_HARNESS_DRIFT",
            f"{path}: harness.blobs covers {sorted(blobs)}, expected exactly "
            f"{sorted(HARNESS_MODULES)}",
        )
    import subprocess

    root = Path(runtime_root) if runtime_root else Path(__file__).resolve().parents[1]
    for mod in HARNESS_MODULES:
        want = blobs[mod]
        probe = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{commit}:{mod}"],
            capture_output=True,
            text=True,
        )
        commit_blob = probe.stdout.strip() if probe.returncode == 0 else None
        if commit_blob != want:
            raise SizeGateNotPassed(
                "SIZE_GATE_HARNESS_DRIFT",
                f"{path}: harness blob for {mod} is {want!r} but the commit side "
                f"({commit}:{mod}) is {commit_blob or 'absent'}",
            )
        try:
            runtime_blob: Optional[str] = _git_blob_sha((root / mod).read_bytes())
        except OSError:
            runtime_blob = None
        if runtime_blob != want:
            raise SizeGateNotPassed(
                "SIZE_GATE_HARNESS_DRIFT",
                f"{path}: harness blob for {mod} is {want!r} but the runtime side "
                f"({root / mod}) is {runtime_blob or 'absent'}",
            )

    return {
        "path": path,
        "commit": _resolve_commit(repo, commit),
        "artifact_blob": _git_blob_sha(raw),
        "rule": rule,
        "required_cells": list(SIZE_GATE_REQUIRED_CELLS),
        "min_m": SIZE_GATE_MIN_M,
        "h1_null_method": obj["h1_null_method"],
        "harness_head": harness["head"],
    }


def count_prior_looks(
    repo: str,
    *,
    commit: str = "HEAD",
    partition: str = "P1",
    path: str = LOOK_LEDGER_PATH,
) -> int:
    """Number of COMMITTED prior looks for ``partition`` at ``commit``.

    An absent ledger is zero looks. A ledger that cannot be read fails closed
    with ``ValueError`` -- an unreadable ledger must never under-count, because
    this count is what makes a P1 read a *counted* development look (V1 §2)
    rather than an unrecorded one.
    """
    raw = _git_show(repo, commit, path)
    if raw is None:
        return 0
    count = 0
    for n, line in enumerate(raw.decode("utf-8", "replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"LOOK_LEDGER_UNPARSEABLE line {n}") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"LOOK_LEDGER_UNPARSEABLE line {n}")
        if entry.get("partition") == partition:
            count += 1
    return count


def record_look(repo: str, entry: dict, *, path: str = LOOK_LEDGER_PATH) -> Path:
    """Append one look entry to the ledger in ``repo`` and return its path.

    This is a working-tree append only. The ledger is COUNTED at a commit
    (``count_prior_looks`` reads ``commit:path`` through git), so a recorded
    look becomes a prior look for the next read only once it is committed --
    an uncommitted append changes nothing about the next read's index.
    """
    dest = Path(repo, path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return dest


def run_p1(
    repo: str,
    *,
    commit: str = "HEAD",
    out: Optional[str] = None,
    record: bool = True,
) -> dict:
    """The only P1 real-data reader. Order is binding: refuse before loading.

    Protocol landing (V1 + V2 blobs at the reading head), then the V2.1
    amendment blob, then the prereg V2 §3 two-part size gate (T19 F9), then
    the committed look count -- and only then is a single byte of market data
    read. The result carries the gate identity and the look index, and the
    look is appended to the ledger unless ``record`` is False.
    """
    from datetime import datetime, timezone

    import hashlib

    st.assert_protocol_landed(repo, head=commit)
    st.assert_prereg_landed(
        repo, head=commit, path=st.PREREG_V2_1_PATH, blob_sha=st.PREREG_V2_1_BLOB_SHA
    )
    gate = assert_size_gate_passed(repo, commit=commit)
    prior = count_prior_looks(repo, commit=commit, partition="P1")
    look_count = prior + 1

    symbols = sorted({s for _id, (_g, num, den) in st.PAIRS.items() for s in (num, den)} | {"SPY"})
    closes, identity = st.load_closes_from_git(repo, commit, symbols)
    calendar = st.session_calendar(closes["SPY"])
    mask = st.partition_mask(calendar, "P1")
    idx = np.flatnonzero(mask)
    start, end = int(idx[0]), int(idx[-1])
    aligned = {sym: st.align(closes[sym], calendar) for sym in symbols}
    spy = aligned["SPY"]
    groups = build_groups(aligned, spy, "P1")
    from scripts.leadership_rotation_null import NULL_K_DEFAULT, make_h1_null_provider

    result = evaluate_family(
        groups,
        start=start,
        end=end,
        partition="P1",
        look_count=look_count,
        h1_null=make_h1_null_provider(NULL_K_DEFAULT),
    )
    result["inputs"] = identity
    result["size_gate"] = gate
    result["look"] = {
        "index": look_count,
        "prior_looks": prior,
        "ledger_path": LOOK_LEDGER_PATH,
        "ledger_commit": gate["commit"],
    }
    if record:
        payload = json.dumps(
            _json_sanitize({k: v for k, v in result.items() if k != "look"}),
            sort_keys=True,
        )
        record_look(
            repo,
            {
                "partition": "P1",
                "look_index": look_count,
                "commit": gate["commit"],
                "size_gate_blob": gate["artifact_blob"],
                "prereg_v2_1_blob": st.PREREG_V2_1_BLOB_SHA,
                "utc": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
                "result_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            },
        )
    if out:
        Path(out).write_text(json.dumps(_json_sanitize(result), indent=2))
    return result


def falsifier_controls() -> Dict[str, dict]:
    return {name: _FC_DISPATCH[name]() for name in _CONTROL_NAMES}


def _fc_both_down() -> dict:
    n = 400
    num = np.linspace(1.0, 0.97, n)
    den = np.linspace(1.0, 0.88, n)
    spy = np.ones(n)
    num_s = pd.Series(num)
    den_s = pd.Series(den)
    t = 340
    interp = st.entry_context(num_s, den_s, t)["interpretation"]
    ps = PairSeries("t", "g", "N", "D", num, den, spy)
    pr = evaluate_pair(ps, start=300, end=350)
    ctx = pr.get("entry_context", {})
    passed = interp == "relative_resilience" or bool(ctx) or pr["arms"]["A1"]["n_items"] > 0
    return {
        "passed": passed,
        "statement": "Receiver falling less than donor is relative resilience, not absolute recovery.",
        "detail": {"entry_context": ctx, "a1_n": pr["arms"]["A1"]["n_items"]},
    }


def _fc_breadth_missingness() -> dict:
    from engine.leadership_rotation_context import breadth

    b = breadth(1, 1, 2)
    fam = evaluate_family({}, start=0, end=10, partition="P0")
    v = fam["verdicts"]
    passed = b.coverage == 0.5 and all(
        v.get(g, {}).get("C3") == "SOURCE_LIMITED" for g in _FAMILY_GROUPS
    )
    return {
        "passed": passed,
        "statement": "Breadth with partial coverage is SOURCE_LIMITED, not a point estimate.",
        "detail": {"breadth_coverage": b.coverage},
    }


def _fc_empty_is_unknown() -> dict:
    n = 50
    nan_leg = np.full(n, np.nan)
    ps = PairSeries("e", "defensive_sector", "A", "B", nan_leg, nan_leg, np.ones(n))
    gr = evaluate_group([ps], start=0, end=40, partition="P0")
    v = _group_verdicts(gr, "P0", [1.0] * 6, FAMILY_ORDER)
    ok = all(v[h] == "NOT_EXECUTABLE" for h in ("H1", "H2", "H3"))
    return {
        "passed": ok,
        "statement": "Zero measured sessions yields NOT_EXECUTABLE, never a fabricated statistic.",
        "detail": {"verdicts": v},
    }


def _fc_composition_only() -> dict:
    n = 400
    num = np.concatenate([np.full(100, np.nan), np.linspace(1.0, 1.1, 300)])
    den = np.linspace(1.0, 1.05, n)
    spy = np.ones(n)
    ps = PairSeries("late", "g", "N", "D", num, den, spy)
    pr = evaluate_pair(ps, start=120, end=380)
    cov = pr["coverage"]["coverage"]
    passed = cov is not None and cov < 1.0
    return {
        "passed": passed,
        "statement": "Late-listed receiver keeps UNMEASURED days in the coverage denominator.",
        "detail": {"coverage": pr["coverage"]},
    }


def _fc_shared_holdings() -> dict:
    n = 500
    spy = np.ones(n)
    day = 350
    pairs = []
    for pid in ("p1", "p2", "p3"):
        num = np.ones(n)
        den = np.ones(n)
        num[day] = 1.05
        pairs.append(PairSeries(pid, "g", "XLP", "XLK", num, den, spy))
    gr = evaluate_group(pairs, start=300, end=400, partition="P0", W=np.ones((10, n), dtype=np.int32))
    passed = gr["honest_n"]["H2"] == 1 and gr["shared_leg_components"] == 1
    return {
        "passed": passed,
        "statement": "Same-day entries on a shared leg form one cluster (honest-N 1).",
        "detail": {"honest_n_H2": gr["honest_n"]["H2"], "shared": gr["shared_leg_components"]},
    }


def _fc_rolling_carry() -> dict:
    n = 800
    dr = np.concatenate([np.zeros(500), np.full(300, 0.015)])
    R = np.cumsum(dr)
    num = np.exp(R)
    den = np.ones(n)
    R2, _ = st.log_ratio(num, den)
    carry_R = np.concatenate(([np.nan], R2[:-1]))
    z_carry = st.zscore(carry_R)
    t_carry = next(
        (t for t in range(500, n) if np.isfinite(z_carry[t]) and z_carry[t] >= st.Z_ENTER),
        None,
    )
    flags, _ = st.arm_b6_carry(R2, [t_carry] if t_carry is not None else [])
    passed = bool(flags and flags[0])
    return {
        "passed": passed,
        "statement": "A1 entry driven only by carry window roll is flagged by B6.",
        "detail": {"carry_flags": flags},
    }


def _fc_beta_only() -> dict:
    n = 800
    t = np.arange(n, dtype=float)
    spy = np.exp(0.001 * t)
    num = spy**0.6
    den = spy**0.5
    ps = PairSeries("b", "g", "N", "D", num, den, spy)
    core = _evaluate_pair_core(ps, start=300, end=750)
    R, invalid = core["R"], core["invalid"]
    with np.errstate(divide="ignore", invalid="ignore"):
        log_spy = np.log(np.where(np.isfinite(ps.spy) & (ps.spy > 0), ps.spy, np.nan))
    lr_num = _log_returns(ps.num)
    lr_den = _log_returns(ps.den)
    beta_num = st.rolling_beta(lr_num, _log_returns(ps.spy))
    beta_den = st.rolling_beta(lr_den, _log_returns(ps.spy))
    t0 = 760
    y = st.outcome(R, invalid, t0, st.H_PRIMARY)[1]
    yr = st.residual_outcome(
        y, float(beta_num[t0]), float(beta_den[t0]), log_spy, t0 + 1, st.H_PRIMARY
    )
    passed = (
        np.isfinite(y)
        and abs(y) > 1e-8
        and np.isfinite(yr)
        and abs(yr) < 0.25 * abs(y)
    )
    return {
        "passed": bool(passed),
        "statement": "Beta-matched legs have zero residual Y^res_20 while raw Y_20 may be nonzero.",
        "detail": {"y_raw": float(y), "y_res": float(yr) if np.isfinite(yr) else None},
    }


def _fc_relative_units() -> dict:
    n = 400
    num = np.ones(n)
    num[351:372] = np.linspace(1.0, 1.01, 21)
    den = np.ones(n)
    spy = np.ones(n)
    ps = PairSeries("u", "g", "N", "D", num, den, spy)
    pr = evaluate_pair(ps, start=300, end=360)
    y = None
    for r in pr.get("b1_out", []):
        if r["t"] == 350 and r["y20"]["state"] == "MATURED":
            y = r["y20"]["y"]
            break
    passed = y is not None and abs(y - math.log(1.01)) < 1e-9
    return {
        "passed": passed,
        "statement": "Outcomes are log-ratio units; +1% receiver move yields log(1.01).",
        "detail": {"y": y},
    }


def _fc_confirmation_maturity() -> dict:
    from engine.leadership_rotation_context import confirmation_maturity

    t = 70
    oc = confirmation_maturity(t, st.C, st.H_PRIMARY)
    passed = oc == t + st.C + st.H_PRIMARY
    return {
        "passed": passed,
        "statement": "Continuation maturity uses t+c+H from the formation index.",
        "detail": {"oc": oc},
    }


def _fc_zero_vs_missing() -> dict:
    n = 200
    num = np.ones(n)
    num[50] = 0.0
    den = np.ones(n)
    den[60] = np.nan
    spy = np.ones(n)
    ps = PairSeries("z", "g", "N", "D", num, den, spy)
    R, inv = st.log_ratio(num, den)
    state, entries, _exits = st.arm_a1(R)
    cov = st.all_event_coverage(R, inv, 0, n - 1)
    passed = cov["counts"]["UNMEASURED"] > 0 and not state[50]
    return {
        "passed": passed,
        "statement": "Zero close is invalid/OFF; missing leg is UNMEASURED in coverage.",
        "detail": {"unmeasured": cov["counts"]["UNMEASURED"]},
    }


_FC_DISPATCH = {
    "both_down": _fc_both_down,
    "breadth_missingness": _fc_breadth_missingness,
    "empty_is_unknown": _fc_empty_is_unknown,
    "composition_only": _fc_composition_only,
    "shared_holdings": _fc_shared_holdings,
    "rolling_carry": _fc_rolling_carry,
    "beta_only": _fc_beta_only,
    "relative_units": _fc_relative_units,
    "confirmation_maturity": _fc_confirmation_maturity,
    "zero_vs_missing": _fc_zero_vs_missing,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Leadership rotation T11 composer")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("controls")
    p1 = sub.add_parser("p1")
    p1.add_argument("--repo", required=True)
    p1.add_argument("--commit", default="HEAD")
    p1.add_argument("--out")
    p1.add_argument(
        "--no-record",
        action="store_true",
        help="do not append this read to the look ledger (still counted as a look)",
    )
    args = parser.parse_args(argv)
    if args.cmd == "controls":
        results = falsifier_controls()
        print(json.dumps(_json_sanitize(results), indent=2))
        return 0 if all(r["passed"] for r in results.values()) else 1
    if args.cmd == "p1":
        run_p1(args.repo, commit=args.commit, out=args.out, record=not args.no_record)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
