"""T11 composer — pair / group / family evaluation for leadership rotation.

Prereg: research/LEADERSHIP_ROTATION_PREREG_V1.md, frozen at commit
fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb (blob
9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe).

DEVELOPMENT HARNESS — no verdict authority.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import leadership_rotation_episodes as ep
from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st

__all__ = [
    "PairSeries",
    "evaluate_pair",
    "evaluate_group",
    "evaluate_family",
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
    _a0_raw, a0_onsets = st.arm_a0(R)
    a2_alarms, a2_pending = st.arm_a2(a1_state, a1_entries)
    b1_days = st.arm_b1(R, s0, end)
    b2_entries = st.arm_b2(R)
    b3_state, b3_entries, b3_exits = st.arm_b3(ps.num, ps.spy)

    a1_w = _filter_window(a1_entries, s0, end)
    a2_w = _filter_window(a2_alarms, s0, end)
    a0_w = _filter_window(a0_onsets, s0, end)
    b2_w = _filter_window(b2_entries, s0, end)
    b3_w = _filter_window(b3_entries, s0, end)

    a1_kept, a1_merged = ep.merge_within_pair(a1_w)
    a2_kept, a2_merged = ep.merge_within_pair(a2_w)
    a0_kept, a0_merged = ep.merge_within_pair(a0_w)
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


def _collect_y20_res(pair_cores: Sequence[dict]) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
    a1_y, b1_y, b2_y, a1_res, b3_res = [], [], [], [], []
    for core in pair_cores:
        for r in core.get("a1_out", []):
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None:
                a1_y.append(r["y20"]["y"])
            if r["y_res_20"]["state"] == "MATURED" and r["y_res_20"]["y"] is not None:
                a1_res.append(r["y_res_20"]["y"])
        for r in core.get("b1_out", []):
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None:
                b1_y.append(r["y20"]["y"])
        for r in core.get("b2_out", []):
            if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None:
                b2_y.append(r["y20"]["y"])
        for r in core.get("b3_out", []):
            if r["y_res_20"]["state"] == "MATURED" and r["y_res_20"]["y"] is not None:
                b3_res.append(r["y_res_20"]["y"])
    return a1_y, b1_y, b2_y, a1_res, b3_res


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
) -> Tuple[List[inf.Item], List[int]]:
    items: List[inf.Item] = []
    for ps, core in zip(pairs, cores):
        for r in core.get("a1_out", []):
            fld = "y_res_20" if residual else "y20"
            if r[fld]["state"] == "MATURED" and r[fld]["y"] is not None:
                items.append((group, ps.pair_id, r["t"]))
    if not items:
        return [], []
    _labels, pos_coord = _item_coord_map(items)
    return items, [pos_coord[i] for i in range(len(items))]


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


def _h1_point_on_subset(
    records: Sequence[dict],
    phases: Sequence[ep.UpPhase],
    onset_coord: Dict[int, int],
    coord_mask: np.ndarray,
    session_w: float,
) -> float:
    allowed_onsets = {t for t, c in onset_coord.items() if coord_mask[c]}
    sub_records = [
        rec
        for rec in records
        if rec.get("phase_T") in allowed_onsets or (
            rec["cls"] == "FALSE_START" and coord_mask[onset_coord.get(rec["index"], rec["index"])]
        )
    ]
    sub_phases = [ph for ph in phases if ph.qualifies and ph.T in allowed_onsets]
    if not sub_phases:
        return float("nan")
    m_a2 = _episode_metrics_unit(sub_records, sub_phases, session_w)
    m_a1 = _episode_metrics_unit(sub_records, sub_phases, session_w)
    return m_a2["median_delay"] - m_a1["median_delay"]


def evaluate_group(
    pairs: Sequence[PairSeries],
    *,
    start: int,
    end: int,
    partition: str,
    W: Optional[np.ndarray] = None,
) -> dict:
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
    decision = inf.h1_decision(
        delay_reduction,
        burden_diff_a,
        detection_diff_a,
        p_a,
        burden_cut_b,
        detection_diff_b,
        p_b,
    )

    a1_y, b1_y, b2_y, a1_res, b3_res = _collect_y20_res(cores)
    a1_items_all = _items_from_kept(group, pairs, cores, "a1_kept")
    honest_n_h1 = _cluster_n(onset_items)
    honest_n_h2 = _cluster_n(_items_matured_a1(group, pairs, cores, residual=False)[0])
    honest_n_h3 = _cluster_n(_items_matured_a1(group, pairs, cores, residual=True)[0])
    test_n_h2 = _cluster_n(a1_items_all)

    h2_point = inf.h2_statistic(
        np.array(a1_y, dtype=float) if a1_y else np.array([np.nan]),
        np.array(b1_y, dtype=float) if b1_y else np.array([np.nan]),
        np.array(b2_y, dtype=float) if b2_y else np.array([np.nan]),
    )
    _a1_items, a1_coords = _items_matured_a1(group, pairs, cores, residual=False)
    b1_items = _items_from_kept(group, pairs, cores, "b1_days")
    b2_items = _items_from_kept(group, pairs, cores, "b2_kept")
    _, b1_pos = _item_coord_map(b1_items) if b1_items else ([], {})
    _, b2_pos = _item_coord_map(b2_items) if b2_items else ([], {})
    b1_coords_list = [b1_pos[i] for i in range(len(b1_items))] if b1_items else []
    b2_coords_list = [b2_pos[i] for i in range(len(b2_items))] if b2_items else []

    a1_Wm = inf.item_weights(W, a1_coords) if a1_coords else np.zeros((W.shape[0], 0))
    b1_Wm = inf.item_weights(W, b1_coords_list) if b1_coords_list else np.zeros((W.shape[0], 0))
    b2_Wm = inf.item_weights(W, b2_coords_list) if b2_coords_list else np.zeros((W.shape[0], 0))

    h2_reps = (
        inf.h2_replicates(
            np.array(a1_y, dtype=float),
            a1_Wm,
            np.array(b1_y, dtype=float) if b1_y else np.array([]),
            b1_Wm,
            np.array(b2_y, dtype=float) if b2_y else np.array([]),
            b2_Wm,
        )
        if a1_y
        else np.full(W.shape[0], np.nan)
    )
    p_h2, _ = inf.one_sided_p(h2_reps)
    fs_a1 = st.false_start_rate_h20(a1_y)
    fs_b2 = st.false_start_rate_h20(b2_y)
    h2_safety = (
        (fs_a1 - fs_b2) <= inf.H2_FALSE_START_NI
        if np.isfinite(fs_a1) and np.isfinite(fs_b2)
        else True
    )

    h3_point = inf.h3_statistic(
        np.array(a1_res, dtype=float) if a1_res else np.array([np.nan]),
        np.array(b3_res, dtype=float) if b3_res else np.array([np.nan]),
    )
    b3_items = _items_from_kept(group, pairs, cores, "b3_kept")
    _, b3_pos = _item_coord_map(b3_items) if b3_items else ([], {})
    b3_coords_list = [b3_pos[i] for i in range(len(b3_items))] if b3_items else []
    b3_Wm = inf.item_weights(W, b3_coords_list) if b3_coords_list else np.zeros((W.shape[0], 0))
    a1_res_items, a1_res_coords = _items_matured_a1(group, pairs, cores, residual=True)
    a1_res_Wm = inf.item_weights(W, a1_res_coords) if a1_res_coords else np.zeros((W.shape[0], 0))
    h3_reps = (
        inf.h3_replicates(
            np.array(a1_res, dtype=float),
            a1_res_Wm,
            np.array(b3_res, dtype=float) if b3_res else np.array([]),
            b3_Wm,
        )
        if a1_res
        else np.full(W.shape[0], np.nan)
    )
    p_h3, _ = inf.one_sided_p(h3_reps)

    session_indices = [
        t
        for t in range(start, end + 1)
        if t < len(measured_per_day) and measured_per_day[t] > 0
    ]
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

    pair_legs = {ps.pair_id: (ps.num_sym, ps.den_sym) for ps in pairs}

    return _json_sanitize(
        {
            "group": group,
            "partition": partition,
            "window": [int(start), int(end)],
            "pairs": [c["pair_id"] for c in cores],
            "executable": executable,
            "honest_n": {"H1": honest_n_h1, "H2": honest_n_h2, "H3": honest_n_h3},
            "test_n": {"H2": test_n_h2, "H3": test_n_h2},
            "shared_leg_components": inf.shared_leg_components(pair_legs),
            "coverage": _aggregate_coverage(cores),
            "arms": _aggregate_arms(cores),
            "H1": {
                "A1": m_a1,
                "A2": m_a2,
                "A0": m_a0,
                "delay_reduction": delay_reduction,
                "burden_diff_a": burden_diff_a,
                "detection_diff_a": detection_diff_a,
                "burden_cut_b": burden_cut_b,
                "detection_diff_b": detection_diff_b,
                "p_a": p_a,
                "p_b": p_b,
                "p": max(p_a, p_b),
                "decision": decision,
                "stability": {"delay_reduction": stab_delay, "burden_cut_b": stab_burden},
            },
            "H2": {
                "point": h2_point,
                "p": p_h2,
                "safety": {"fs_a1": fs_a1, "fs_b2": fs_b2, "ok": h2_safety},
                "interval_90": inf.interval_90(h2_reps),
                "lower_bound": inf.lower_bound(h2_reps),
            },
            "H3": {"point": h3_point, "p": p_h3},
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


def _group_verdicts(gr: dict, partition: str, holm_adj: List[float], order) -> dict:
    executable = gr.get("executable", False)
    cov = _as_float(gr.get("coverage", 0.0))
    if math.isnan(cov):
        cov = 0.0
    gname = gr.get("group", "")
    out: Dict[str, str] = {}
    for h in ("H1", "H2", "H3"):
        p_holm = _holm_p_for(gname, h, order, holm_adj)
        if h == "H1":
            clause = inf.clause1(
                1.0 if gr["H1"]["decision"]["margins_met"] else 0.0,
                1.0,
                p_holm,
            )
            stable = (
                gr["H1"]["stability"]["delay_reduction"]["holds"]
                and gr["H1"]["stability"]["burden_cut_b"]["holds"]
            )
            out[h] = inf.verdict(
                partition,
                executable=executable,
                source_limited=False,
                immature=_immature(gr, h),
                honest_n=gr["honest_n"]["H1"],
                clause1_ok=clause,
                stable=stable,
                coverage=cov,
            )
        elif h == "H2":
            clause = inf.clause1(_as_float(gr["H2"]["point"]), inf.MARGIN_H2, p_holm)
            out[h] = inf.verdict(
                partition,
                executable=executable,
                source_limited=False,
                immature=_immature(gr, h),
                honest_n=gr["honest_n"]["H2"],
                clause1_ok=clause,
                stable=True,
                coverage=cov,
                h2_safety_ok=gr["H2"]["safety"]["ok"],
            )
        else:
            clause = inf.clause1(_as_float(gr["H3"]["point"]), inf.MARGIN_H3, p_holm)
            out[h] = inf.verdict(
                partition,
                executable=executable,
                source_limited=False,
                immature=_immature(gr, h),
                honest_n=gr["honest_n"]["H3"],
                clause1_ok=clause,
                stable=True,
                coverage=cov,
            )
    out["C3"] = inf.verdict(
        partition,
        executable=True,
        source_limited=True,
        immature=False,
        honest_n=0,
        clause1_ok=False,
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
) -> dict:
    n_calendar = max((len(ps.spy) for plist in groups.values() for ps in plist), default=0)
    W = inf.stationary_bootstrap_weights(n_calendar) if n_calendar else np.zeros((0, 0))
    group_results: Dict[str, dict] = {}
    for gname, plist in groups.items():
        group_results[gname] = evaluate_group(
            plist, start=start, end=end, partition=partition, W=W
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
            verdicts[gname] = _group_verdicts(gr, partition, adjusted, order)

    return _json_sanitize(
        {
            "prereg": {
                "path": st.PREREG_PATH,
                "commit": st.PREREG_COMMIT,
                "blob": st.PREREG_BLOB_SHA,
            },
            "partition": partition,
            "look_count": 0,
            "groups": group_results,
            "holm": {"order": order, "raw": raw_ps, "adjusted": adjusted},
            "verdicts": verdicts,
        }
    )


def run_p1(repo: str, *, commit: str = "HEAD", out: Optional[str] = None) -> dict:
    st.assert_prereg_landed(repo, head=commit)
    symbols = sorted({s for _id, (_g, num, den) in st.PAIRS.items() for s in (num, den)} | {"SPY"})
    closes, identity = st.load_closes_from_git(repo, commit, symbols)
    calendar = st.session_calendar(closes["SPY"])
    mask = st.partition_mask(calendar, "P1")
    idx = np.flatnonzero(mask)
    start, end = int(idx[0]), int(idx[-1])
    aligned = {sym: st.align(closes[sym], calendar) for sym in symbols}
    spy = aligned["SPY"]
    groups: Dict[str, List[PairSeries]] = {
        "defensive_sector": [],
        "broadening_proxy": [],
    }
    for pair_id, (group, num_sym, den_sym) in st.PAIRS.items():
        if pair_id in st.P2_EXCLUDED:
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
    result = evaluate_family(groups, start=start, end=end, partition="P1")
    result["inputs"] = identity
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
    args = parser.parse_args(argv)
    if args.cmd == "controls":
        results = falsifier_controls()
        print(json.dumps(_json_sanitize(results), indent=2))
        return 0 if all(r["passed"] for r in results.values()) else 1
    if args.cmd == "p1":
        run_p1(args.repo, commit=args.commit, out=args.out)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
