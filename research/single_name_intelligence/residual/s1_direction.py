"""s1_direction.py — the two frozen P01/P02 baselines (REG P01/P02, D6/D7).

Every decision-cutoff quantity here reads bars <= D(s) ONLY (D3). The day-s
move (close(D(s)) -> close(s)) is deliberately outside every input, and the
report discloses that.

Baseline (i) always-long: direction +1.
Baseline (ii) trailing-63 excess sign:
    sign( (P_subj(D)/P_subj(D63) - 1) - (P_bench(D)/P_bench(D63) - 1) )
where D = D(s) and D63 = 63 sessions before D on the subject's market calendar.
Both series must hold bars on D and D63 EXACTLY, else direction 0 (the unit
then abstains — listed, never a hit and never a miss).
"""
from __future__ import annotations

from datetime import date

from s1_manifest import last_session_before, session_n_back


def direction_always_long(s: date) -> int:
    return 1


def _leg_close(closes: dict[date, float], d: date) -> float | None:
    v = closes.get(d)
    if v is None or v == 0 or v != v:
        return None
    return v


def direction_trailing63(subj_closes: dict[date, float], bench_closes: dict[date, float],
                         s: date, is_session, n: int = 63) -> int:
    """Baseline (ii). Decision cutoff D(s); 0 when either endpoint is missing
    or the trailing excess is exactly 0 (ties abstain, listed)."""
    d = last_session_before(is_session, s)
    d63 = session_n_back(is_session, d, n)
    subj_d, subj_63 = _leg_close(subj_closes, d), _leg_close(subj_closes, d63)
    bench_d, bench_63 = _leg_close(bench_closes, d), _leg_close(bench_closes, d63)
    if None in (subj_d, subj_63, bench_d, bench_63):
        return 0
    trail = (subj_d / subj_63 - 1.0) - (bench_d / bench_63 - 1.0)
    if trail > 0:
        return 1
    if trail < 0:
        return -1
    return 0


def sign_of(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0
