"""LEADERSHIP-ROTATION T11 harness — zig-zag episodes, merge, matching, burden.

Prereg: research/LEADERSHIP_ROTATION_PREREG_V1.md, frozen at commit
fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb (blob
9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe) — §5 (transition dating & event
accounting, D5), §7 (H1 margins, D7), §8 (honest-N / uncertainty, D8).

DEVELOPMENT HARNESS — no verdict authority.  This module is a pure
numpy/stdlib estimator library: no I/O, no market data, no engine imports.
It computes, for synthetic or later study lanes (T12–T14), the zig-zag
episode decomposition of a log series, anchor-based within-pair alarm
merging, alarm-to-onset matching, and the burden / detection / delay
metrics that H1 consumes.

Binding orchestrator rulings cited inline: ORCH-SCI R6 (anchor merge),
R7 (matching precedence), R8 (burden / detection / lower median).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

AMPLITUDE = 0.08
AMPLITUDE_SENSITIVITY = 0.12
MIN_UP = 40
MATCH_WINDOW = 40
MERGE_GAP = 20
SESSIONS_PER_YEAR = 252


@dataclass(frozen=True)
class UpPhase:
    """One zig-zag up-phase on calendar indices (ORCH-SCI R1)."""

    T: int
    P: int
    rise: float
    censored: bool
    qualifies: bool


def _extreme(seg_lo: int, seg_hi: int, R: np.ndarray, want_max: bool):
    """Return (value, calendar_idx) of the strict max/min over [seg_lo, seg_hi).

    NaN entries are skipped entirely (indices stay calendar indices).  numpy
    argmax/argmin return the FIRST occurrence, which is the earliest index on
    ties — exactly the strict-update tie rule.
    """
    seg = R[seg_lo:seg_hi]
    finite = np.flatnonzero(np.isfinite(seg))
    vals = seg[finite]
    j = int(np.argmax(vals) if want_max else np.argmin(vals))
    return float(vals[j]), seg_lo + int(finite[j])


def zigzag(R, amplitude: float = AMPLITUDE, min_up: int = MIN_UP,
           start: int = 0, end=None) -> list[UpPhase]:
    """Zig-zag up-phases of the log series R over calendar indices [start, end).

    A is a LOG amplitude.  NaN entries neither form nor break turning points.
    Mode None tracks the running min and running max (strict updates, so ties
    keep the EARLIEST index).  In mode None a value >= running_min + A confirms
    trough T = running_min.idx -> mode UP; a value <= running_max - A confirms
    an initial peak -> mode DOWN.  In UP a value <= run_max - A confirms peak
    P = run_max.idx and records the phase; in DOWN a value >= run_min + A
    confirms the next trough.  A phase still UP at `end` is recorded with
    P = run_max.idx, censored=True, and qualifies by the same P - T rule
    (censored qualifying phases are included; their count is printed by
    callers).  Onset of a qualifying phase = T.
    """
    R = np.asarray(R, dtype=float)
    if end is None:
        end = int(R.shape[0])
    phases: list[UpPhase] = []
    mode = 0  # 0 = None, 1 = UP, -1 = DOWN
    run_min = None
    run_max = None
    trough = None
    for i in range(start, end):
        x = R[i]
        if not np.isfinite(x):
            continue  # NaN skip: neither forms nor breaks a turning point
        if mode == 0:
            if run_min is None or x < run_min[0]:
                run_min = (x, i)
            if run_max is None or x > run_max[0]:
                run_max = (x, i)
            if x >= run_min[0] + amplitude:
                trough = run_min[1]
                mode = 1
                run_max = _extreme(trough + 1, i + 1, R, want_max=True)
            elif x <= run_max[0] - amplitude:
                peak0 = run_max[1]
                mode = -1
                run_min = _extreme(peak0 + 1, i + 1, R, want_max=False)
        elif mode == 1:
            if x > run_max[0]:
                run_max = (x, i)
            elif x <= run_max[0] - amplitude:
                peak = run_max[1]
                phases.append(UpPhase(trough, peak, float(R[peak] - R[trough]),
                                      False, (peak - trough) >= min_up))
                mode = -1
                run_min = _extreme(peak + 1, i + 1, R, want_max=False)
        else:
            if x < run_min[0]:
                run_min = (x, i)
            elif x >= run_min[0] + amplitude:
                trough = run_min[1]
                mode = 1
                run_max = _extreme(trough + 1, i + 1, R, want_max=True)
    if mode == 1:
        peak = run_max[1]
        phases.append(UpPhase(trough, peak, float(R[peak] - R[trough]),
                              True, (peak - trough) >= min_up))
    return phases


def quiet_mask(n: int, phases) -> np.ndarray:
    """True for indices in NO qualifying [T, P]."""
    quiet = np.ones(n, dtype=bool)
    for ph in phases:
        if ph.qualifies:
            quiet[ph.T:ph.P + 1] = False
    return quiet


def merge_within_pair(alarms, gap: int = MERGE_GAP):
    """Anchor-based within-pair merge (ORCH-SCI ruling R6).

    Sort alarms; keep the first; keep a later alarm iff it is >= `gap`
    sessions after the last KEPT alarm.  Returns (kept, merged_away);
    merged-away alarms are REPEATED and never enter burden.
    """
    ordered = sorted(int(a) for a in alarms)
    kept: list[int] = []
    merged: list[int] = []
    anchor = None
    for a in ordered:
        if anchor is None or a - anchor >= gap:
            kept.append(a)
            anchor = a
        else:
            merged.append(a)
    return kept, merged


def classify_alarms(kept, phases, window: int = MATCH_WINDOW,
                    off_index=None) -> list[dict]:
    """Match kept alarms against QUALIFYING phases (ORCH-SCI ruling R7).

    Each record is {"index", "cls", "subtype", "phase_T", "delay"} with
    cls in {MATCHED, LATE, REPEATED, FALSE_START}.  `off_index` maps an
    alarm index -> the index where the arm's state turned OFF (a value of
    None, or a missing key, means still ON at the end of the calendar):
    a FALSE_START subtype is EXPIRES iff off - a <= window, else
    PERSISTENT.  `off_index=None` (event arms A0/B2) gives subtype NONE.
    """
    qual = [ph for ph in phases if ph.qualifies]
    matched_taken = {ph.T: False for ph in qual}
    # phase already holds a MATCHED or LATE alarm
    engaged = {ph.T: False for ph in qual}
    records: list[dict] = []
    for a in sorted(int(x) for x in kept):
        rec = {"index": a, "cls": None, "subtype": None,
               "phase_T": None, "delay": None}
        host = None
        for ph in qual:
            if ph.T <= a <= ph.P:
                host = ph
                break
        if host is not None and a <= host.T + window:
            if not matched_taken[host.T]:
                rec["cls"] = "MATCHED"
                rec["phase_T"] = host.T
                rec["delay"] = a - host.T
                matched_taken[host.T] = True
                engaged[host.T] = True
            else:
                rec["cls"] = "REPEATED"
                rec["phase_T"] = host.T
                rec["delay"] = a - host.T
        elif host is not None:
            if engaged[host.T]:
                rec["cls"] = "REPEATED"
            else:
                rec["cls"] = "LATE"
                engaged[host.T] = True
            rec["phase_T"] = host.T
            rec["delay"] = a - host.T
        else:
            rec["cls"] = "FALSE_START"
            if off_index is None:
                rec["subtype"] = "NONE"
            else:
                off = off_index.get(a)
                rec["subtype"] = ("EXPIRES"
                                  if off is not None and off - a <= window
                                  else "PERSISTENT")
        records.append(rec)
    return records


def lower_weighted_median(values, weights=None) -> float:
    """Smallest value whose cumulative weight >= half the total weight.

    Unweighted (all weights 1) an even count returns the LOWER middle.
    NaN for empty or zero-weight input.  Used identically for point
    estimates and bootstrap replicates (ORCH-SCI ruling R8).
    """
    vals = [float(v) for v in values]
    if not vals:
        return float("nan")
    if weights is None:
        wts = [1.0] * len(vals)
    else:
        wts = [float(w) for w in weights]
    total = float(sum(wts))
    if not (total > 0.0):
        return float("nan")
    half = total / 2.0
    cum = 0.0
    for i in sorted(range(len(vals)), key=lambda j: vals[j]):
        cum += wts[i]
        if cum >= half:
            return vals[i]
    return vals[sorted(range(len(vals)), key=lambda j: vals[j])[-1]]


def episode_metrics(records, phases, measured_sessions: int, merged_away: int = 0,
                    onset_w=None, alarm_w=None, session_w_total=None,
                    quiet_sessions=None) -> dict:
    """Episode metrics for one arm (ORCH-SCI ruling R8).

    detection = sum(w matched onsets) / sum(w qualifying onsets), misses
    included in the denominator.  burden = sum(w REPEATED + LATE +
    FALSE_START among KEPT records) / (session_w_total / 252) — merged-away
    alarms are printed beside burden via `merged_away` and never enter it.
    median_delay is the lower weighted median of MATCHED delays weighted by
    their onset weight.  quiet_rate is computed only when the caller passes
    `quiet_sessions` (the count of quiet MEASURED sessions).
    """
    onset_w = onset_w if onset_w is not None else {}
    alarm_w = alarm_w if alarm_w is not None else {}
    if session_w_total is None:
        session_w_total = measured_sessions
    qual = [ph for ph in phases if ph.qualifies]
    matched_T = set()
    cls_counts = {"MATCHED": 0, "LATE": 0, "REPEATED": 0, "FALSE_START": 0}
    sub_counts = {"EXPIRES": 0, "PERSISTENT": 0, "NONE": 0}
    burden_w = 0.0
    for rec in records:
        cls_counts[rec["cls"]] += 1
        if rec["cls"] == "MATCHED":
            matched_T.add(rec["phase_T"])
        elif rec["cls"] == "FALSE_START":
            sub_counts[rec["subtype"]] += 1
        if rec["cls"] in ("REPEATED", "LATE", "FALSE_START"):
            burden_w += float(alarm_w.get(rec["index"], 1.0))
    det_num = 0.0
    det_den = 0.0
    for ph in qual:
        w_on = float(onset_w.get(ph.T, 1.0))
        det_den += w_on
        if ph.T in matched_T:
            det_num += w_on
    detection = det_num / det_den if det_den > 0.0 else float("nan")
    delay_pairs = [(rec["delay"], float(onset_w.get(rec["phase_T"], 1.0)))
                   for rec in records if rec["cls"] == "MATCHED"]
    median_delay = (lower_weighted_median([d for d, _ in delay_pairs],
                                          [w for _, w in delay_pairs])
                    if delay_pairs else float("nan"))
    burden_years = float(session_w_total) / SESSIONS_PER_YEAR
    burden = burden_w / burden_years if burden_years > 0.0 else float("nan")
    metrics = {
        "n_qualifying": len(qual),
        "n_censored_qualifying": sum(1 for ph in qual if ph.censored),
        "n_matched": cls_counts["MATCHED"],
        "n_miss": sum(1 for ph in qual if ph.T not in matched_T),
        "detection": detection,
        "median_delay": median_delay,
        "n_late": cls_counts["LATE"],
        "n_repeated": cls_counts["REPEATED"],
        "n_false_start": cls_counts["FALSE_START"],
        "n_fs_expires": sub_counts["EXPIRES"],
        "n_fs_persistent": sub_counts["PERSISTENT"],
        "n_fs_none": sub_counts["NONE"],
        "burden": burden,
        "merged_away": merged_away,
        "quiet_rate": None,
    }
    if quiet_sessions is not None:
        span = max([rec["index"] for rec in records] + [ph.P for ph in qual] + [0])
        qmask = quiet_mask(span + 1, phases)
        quiet_w = sum(float(alarm_w.get(rec["index"], 1.0))
                      for rec in records if qmask[rec["index"]])
        quiet_years = float(quiet_sessions) / SESSIONS_PER_YEAR
        metrics["quiet_rate"] = (quiet_w / quiet_years
                                 if quiet_years > 0.0 else float("nan"))
    return metrics
