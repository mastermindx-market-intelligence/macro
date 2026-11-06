"""T11 prereg harness tests — episodes, merge, matching, metrics.

Each test carries a `# MUTATION:` line naming the single one-line source
change that makes it FAIL; every mutation was applied, run to FAIL, and
reverted (never committed).  Pure synthetic arrays only — no market data,
no I/O.  Prereg: research/LEADERSHIP_ROTATION_PREREG_V1.md (frozen
fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb) §5/§7; rulings ORCH-SCI R6–R8.
DEVELOPMENT HARNESS — no verdict authority.
"""

import math

import numpy as np
import pytest

from scripts.leadership_rotation_episodes import (
    AMPLITUDE,
    AMPLITUDE_SENSITIVITY,
    MATCH_WINDOW,
    UpPhase,
    classify_alarms,
    episode_metrics,
    lower_weighted_median,
    merge_within_pair,
    quiet_mask,
    zigzag,
)

# ---------------------------------------------------------------------------
# synthetic path builders (pure arrays)
# ---------------------------------------------------------------------------


def _hand_path():
    """flat 20 -> +0.10 rise over 50 -> -0.10 fall over 50 -> +0.05 rise 50."""
    R = [0.0] * 20
    R += [0.002 * k for k in range(1, 51)]          # idx 20..69, tops at 0.10
    R += [0.10 - 0.002 * k for k in range(1, 51)]   # idx 70..119, back to 0.0
    R += [0.001 * k for k in range(1, 51)]          # idx 120..169, tops at 0.05
    return R


def _min_up_path(m):
    """Single rise of log 0.08 over exactly m sessions, then a 40-session fall."""
    R = [0.0]
    R += [0.08 * i / m for i in range(1, m + 1)]
    R += [0.08 * (1 - k / 40) for k in range(1, 41)]
    return R


def _rise_only_path(top=0.10, n=50):
    R = [0.0]
    R += [top * i / n for i in range(1, n + 1)]
    return R


def _rise_fall_path(top=0.10, n=50):
    R = _rise_only_path(top, n)
    R += [top - top * k / n for k in range(1, n + 1)]
    return R


# ---------------------------------------------------------------------------
# 1-6: zig-zag episodes
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_episodes.py:25 AMPLITUDE = 0.08 -> AMPLITUDE = 0.05
def test_hand_path_single_qualifying_phase():
    phases = zigzag(_hand_path())
    # the +0.05 leg must NOT form a phase at A = 0.08 (only 0.05 of rise)
    assert len(phases) == 1
    ph = phases[0]
    assert (ph.T, ph.P) == (0, 69)
    assert ph.rise == pytest.approx(0.10, abs=1e-9)
    assert ph.qualifies is True
    assert ph.censored is False


# MUTATION: scripts/leadership_rotation_episodes.py:27 MIN_UP = 40 -> MIN_UP = 39
def test_min_up_boundary():
    short = zigzag(_min_up_path(39))
    assert len(short) == 1
    assert short[0].P - short[0].T == 39
    assert short[0].qualifies is False
    long = zigzag(_min_up_path(40))
    assert len(long) == 1
    assert long[0].P - long[0].T == 40
    assert long[0].qualifies is True


# MUTATION: scripts/leadership_rotation_episodes.py:114 if mode == 1: -> if False:
def test_censored_phase_at_series_end():
    phases = zigzag(_rise_only_path(0.10, 50))
    assert len(phases) == 1
    ph = phases[0]
    assert ph.censored is True
    assert (ph.T, ph.P) == (0, 50)
    assert ph.rise == pytest.approx(0.10, abs=1e-9)
    assert ph.qualifies is True  # 50 - 0 >= 40, censored qualifying counts


# MUTATION: scripts/leadership_rotation_episodes.py:84 continue -> x = 0.0
def test_nan_skip_preserves_turning_points():
    # floor 0.04: a zero-filled NaN would sit STRICTLY below the true trough,
    # so this path catches zero-fill / ffill mutations, not just compaction
    base = [0.04]
    base += [0.04 + 0.002 * i for i in range(1, 51)]      # rise to 0.14 at 50
    base += [0.14 - 0.002 * k for k in range(1, 51)]      # fall back to 0.04
    punched = list(base)
    # punches sit where a zero-fill would STEAL the trough (values > floor)
    punched[10:16] = [float("nan")] * 6   # inside the rise
    punched[60:66] = [float("nan")] * 6   # inside the fall
    a = zigzag(base)
    b = zigzag(punched)
    assert [(p.T, p.P, p.censored, p.qualifies) for p in a] == \
           [(p.T, p.P, p.censored, p.qualifies) for p in b]
    assert a[0].rise == pytest.approx(b[0].rise, abs=1e-12)
    # indices stayed calendar indices, not compacted
    assert (b[0].T, b[0].P) == (0, 50)


# MUTATION: scripts/leadership_rotation_episodes.py:86 x < run_min[0] -> x <= run_min[0]
def test_ties_keep_earliest_trough_index():
    R = [0.0, 0.03, 0.0]                          # two equal minima: idx 0 and 2
    R += [0.0025 * j for j in range(1, 49)]       # rise to 0.12 at idx 50
    R += [0.12 - 0.0025 * k for k in range(1, 49)]
    phases = zigzag(R)
    assert len(phases) == 1
    assert phases[0].T == 0  # the EARLIER minimum, never the later tie


# MUTATION: scripts/leadership_rotation_episodes.py:58 amplitude: float = AMPLITUDE -> amplitude: float = AMPLITUDE_SENSITIVITY
def test_amplitude_sensitivity_is_not_a_phase():
    R = _rise_fall_path(0.10, 50)  # a 0.10 log rise
    at_default = zigzag(R)
    assert len(at_default) == 1
    assert AMPLITUDE == 0.08
    at_sensitive = zigzag(R, amplitude=AMPLITUDE_SENSITIVITY)
    assert at_sensitive == []  # 0.10 < 0.12: no phase at the sensitivity A


# ---------------------------------------------------------------------------
# 7: anchor-based within-pair merge (ORCH-SCI R6)
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_episodes.py:146 merged.append(a) -> merged.append(a); anchor = a
def test_anchor_merge_keeps_from_last_kept():
    kept, merged = merge_within_pair([0, 10, 19, 28, 37, 46])
    assert kept == [0, 28]
    assert merged == [10, 19, 37, 46]
    kept2, merged2 = merge_within_pair([0, 20, 40])
    assert kept2 == [0, 20, 40]  # gap exactly 20 keeps
    assert merged2 == []
    assert merge_within_pair([]) == ([], [])


# ---------------------------------------------------------------------------
# 8: alarm matching precedence (ORCH-SCI R7)
# ---------------------------------------------------------------------------


def _match_phases():
    return [
        UpPhase(T=0, P=30, rise=0.09, censored=False, qualifies=False),
        UpPhase(T=100, P=160, rise=0.10, censored=False, qualifies=True),
    ]


# MUTATION: scripts/leadership_rotation_episodes.py:174 a <= host.T + window -> a < host.T + window
def test_classify_matching_precedence():
    phases = _match_phases()
    assert MATCH_WINDOW == 40
    # boundary: T and T+40 are both MATCHED when they are the phase's first alarm
    one = classify_alarms([100], phases)
    assert one[0]["cls"] == "MATCHED" and one[0]["delay"] == 0
    edge = classify_alarms([140], phases)
    assert edge[0]["cls"] == "MATCHED" and edge[0]["delay"] == 40
    # second alarm inside the window -> REPEATED
    two = classify_alarms([100, 120], phases)
    assert [r["cls"] for r in two] == ["MATCHED", "REPEATED"]
    assert two[1]["phase_T"] == 100
    # just past the window, phase unmatched -> LATE
    late = classify_alarms([141], phases)
    assert late[0]["cls"] == "LATE" and late[0]["delay"] == 41
    # a later in-phase alarm after a MATCHED -> REPEATED (never LATE)
    after = classify_alarms([100, 150], phases)
    assert [r["cls"] for r in after] == ["MATCHED", "REPEATED"]
    # LATE then REPEATED once the phase holds a LATE
    seq = classify_alarms([150, 155], phases)
    assert [r["cls"] for r in seq] == ["LATE", "REPEATED"]
    # alarm in no phase at all -> FALSE_START
    assert classify_alarms([200], phases)[0]["cls"] == "FALSE_START"
    # alarm inside a NON-qualifying phase -> FALSE_START
    assert classify_alarms([15], phases)[0]["cls"] == "FALSE_START"
    # FALSE_START subtypes via off_index (state arms A1/A2/B3)
    exp = classify_alarms([200], phases, off_index={200: 230})
    assert exp[0]["subtype"] == "EXPIRES"          # off - a = 30 <= 40
    per = classify_alarms([200], phases, off_index={200: 241})
    assert per[0]["subtype"] == "PERSISTENT"       # off - a = 41 > 40
    still = classify_alarms([200], phases, off_index={200: None})
    assert still[0]["subtype"] == "PERSISTENT"     # still ON at series end
    unmapped = classify_alarms([200, 210], phases, off_index={200: 230})
    assert unmapped[0]["subtype"] == "EXPIRES"
    assert unmapped[1]["subtype"] == "PERSISTENT"  # no off recorded
    # event arms (A0/B2): off_index=None -> subtype NONE
    none = classify_alarms([200], phases)
    assert none[0]["subtype"] == "NONE"
    # non-FALSE_START records carry subtype None
    assert one[0]["subtype"] is None


# ---------------------------------------------------------------------------
# 9: metrics (ORCH-SCI R8)
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_episodes.py:227 if cum >= half: -> if cum > half:
def test_lower_median_returns_lower_middle():
    assert lower_weighted_median([2, 4, 6, 8]) == 4.0  # not 5
    assert lower_weighted_median([1, 2, 3]) == 2.0
    assert lower_weighted_median([1, 2], weights=[1, 3]) == 2.0
    assert lower_weighted_median([5, 1], weights=[3, 1]) == 5.0
    assert math.isnan(lower_weighted_median([]))
    assert math.isnan(lower_weighted_median([1.0], weights=[0.0]))


def _metric_phases():
    return [
        UpPhase(T=100, P=150, rise=0.10, censored=False, qualifies=True),
        UpPhase(T=300, P=350, rise=0.09, censored=False, qualifies=True),
    ]


# MUTATION: scripts/leadership_rotation_episodes.py:266 det_den += w_on -> det_den += 0.0
def test_detection_counts_misses_in_denominator():
    phases = _metric_phases()
    records = classify_alarms([110], phases)  # phase 100 matched, phase 300 missed
    m = episode_metrics(records, phases, measured_sessions=504)
    assert m["n_qualifying"] == 2
    assert m["n_matched"] == 1
    assert m["n_miss"] == 1
    assert m["detection"] == pytest.approx(0.5)  # 1 matched onset / 2 onsets
    assert m["median_delay"] == pytest.approx(10.0)
    assert m["n_censored_qualifying"] == 0


# MUTATION: scripts/leadership_rotation_episodes.py:275 / SESSIONS_PER_YEAR -> / (SESSIONS_PER_YEAR * 2)
def test_burden_excludes_matched_and_merged_is_per_year():
    phases = _metric_phases() + [
        UpPhase(T=500, P=520, rise=0.08, censored=True, qualifies=True)]
    records = classify_alarms([110, 130, 200, 250], phases)
    # 110 MATCHED (never burden), 130 REPEATED, 200/250 FALSE_START
    m = episode_metrics(records, phases, measured_sessions=504, merged_away=3)
    assert m["n_qualifying"] == 3
    assert m["n_censored_qualifying"] == 1
    assert m["n_repeated"] == 1
    assert m["n_false_start"] == 2
    assert m["merged_away"] == 3          # printed beside burden, never in it
    assert m["burden"] == pytest.approx(3 / (504 / 252))  # = 1.5 per pair-year


# MUTATION: scripts/leadership_rotation_episodes.py:265 w_on = float(onset_w.get(ph.T, 1.0)) -> w_on = 1.0
def test_weights_move_detection_and_burden():
    phases = _metric_phases()
    records = classify_alarms([110, 200], phases)
    m = episode_metrics(records, phases, measured_sessions=504,
                        onset_w={100: 3.0, 300: 1.0}, alarm_w={200: 2.0})
    assert m["detection"] == pytest.approx(3.0 / 4.0)   # weighted onsets
    assert m["burden"] == pytest.approx(2.0 / (504 / 252))  # alarm weight 2.0
    m_unweighted = episode_metrics(records, phases, measured_sessions=504)
    assert m_unweighted["detection"] == pytest.approx(0.5)
    assert m_unweighted["burden"] == pytest.approx(1.0 / (504 / 252))
    # session_w_total overrides measured_sessions in the burden denominator
    m_w = episode_metrics(records, phases, measured_sessions=504,
                          session_w_total=252)
    assert m_w["burden"] == pytest.approx(1.0 / 1.0)


# ---------------------------------------------------------------------------
# 10: quiet-period rate
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_episodes.py:126 quiet[ph.T:ph.P + 1] = False -> pass
def test_quiet_mask_marks_only_qualifying_spans():
    phases = _match_phases()
    q = quiet_mask(200, phases)
    assert q.dtype == np.bool_
    assert q[:31].all()          # non-qualifying phase [0, 30] is still quiet
    assert not q[100:161].any()  # qualifying [100, 160] is not quiet
    assert q[161:].all()


# MUTATION: scripts/leadership_rotation_episodes.py:298 for rec in records if qmask[rec["index"]]) -> for rec in records)
def test_quiet_rate_counts_only_kept_alarms_in_quiet_sessions():
    phases = [UpPhase(T=100, P=160, rise=0.10, censored=False, qualifies=True)]
    records = classify_alarms([50, 110, 300], phases)
    m = episode_metrics(records, phases, measured_sessions=400,
                        quiet_sessions=339, alarm_w={50: 2.0})
    # quiet kept alarms: 50 (w=2) and 300 (w=1); 110 sits inside [100, 160]
    assert m["quiet_rate"] == pytest.approx(3.0 / (339 / 252))
    # without the kwarg the key is absent from the report, not zero
    m2 = episode_metrics(records, phases, measured_sessions=400)
    assert m2["quiet_rate"] is None


# ---------------------------------------------------------------------------
# Prereg V2.1 §4 (R3): V1 §5 alarm precedence as a first-match ordering
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_episodes.py:classify_alarms let "outside every [T, T+40]" outrank "inside an up-phase after T+40"
def test_r3_late_outranks_false_start_inside_the_up_phase():
    """V1 §5 bullets 3 and 4 both cover an alarm at T+41..P; V2.1 §4 rules the
    up-phase bullet (LATE) first, and the bracket is closed at both ends."""
    phases = _match_phases()  # qualifying phase T=100, P=160
    assert classify_alarms([95], phases)[0]["cls"] == "FALSE_START"   # before T
    assert classify_alarms([160], phases)[0]["cls"] == "LATE"         # the peak itself
    assert classify_alarms([161], phases)[0]["cls"] == "FALSE_START"  # past P
    assert [r["cls"] for r in classify_alarms([95, 160, 161], phases)] == [
        "FALSE_START", "LATE", "FALSE_START",
    ]


def _r3_oracle(alarms, phases, window=40):
    """V2.1 §4 written per phase rather than per alarm: inside a qualifying
    [T, P] the phase's FIRST alarm is MATCHED (delay ≤ window) or LATE, and every
    later alarm in it is REPEATED; an alarm in no qualifying [T, P] is a
    FALSE_START."""
    qual = [ph for ph in phases if ph.qualifies]
    seen = set()
    out = []
    for a in sorted(alarms):
        host = next((ph for ph in qual if ph.T <= a <= ph.P), None)
        if host is None:
            out.append(("FALSE_START", None))
        elif host.T in seen:
            out.append(("REPEATED", host.T))
        else:
            seen.add(host.T)
            out.append(("MATCHED" if a - host.T <= window else "LATE", host.T))
    return out


# MUTATION: scripts/leadership_rotation_episodes.py:classify_alarms mark a post-window alarm LATE even after the phase is MATCHED
def test_r3_first_match_ordering_equals_the_per_phase_oracle():
    rng = np.random.default_rng(20261014)
    phases = [
        UpPhase(T=0, P=30, rise=0.09, censored=False, qualifies=False),
        UpPhase(T=100, P=160, rise=0.10, censored=False, qualifies=True),
        UpPhase(T=161, P=260, rise=0.12, censored=False, qualifies=True),
        UpPhase(T=300, P=330, rise=0.08, censored=True, qualifies=True),
        UpPhase(T=400, P=420, rise=0.05, censored=False, qualifies=False),
    ]
    for _ in range(3000):
        k = int(rng.integers(1, 9))
        alarms = sorted(set(int(x) for x in rng.integers(0, 460, k)))
        got = [(r["cls"], r["phase_T"]) for r in classify_alarms(alarms, phases)]
        assert got == _r3_oracle(alarms, phases), alarms
