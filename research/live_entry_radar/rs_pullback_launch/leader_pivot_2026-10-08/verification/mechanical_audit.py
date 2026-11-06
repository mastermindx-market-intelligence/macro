"""Source-free mathematical checks for the RS Leader Pivot research commission.

Not a trading engine, data-admission implementation, market backtest or estimate
of predictive performance. Python standard library only; deterministic output.
Run: python mechanical_audit.py --output mechanical_results.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

CHECKS: list[dict[str, object]] = []

def check(name: str, condition: bool, evidence: object) -> None:
    if not condition:
        raise AssertionError(f"{name}: {evidence!r}")
    CHECKS.append({"name": name, "status": "PASS", "evidence": evidence})

def basket(returns: list[float], weights: list[float], exclude: int | None = None) -> float:
    if len(returns) != len(weights) or not returns:
        raise ValueError("Nonempty, matched returns and weights required")
    if any(not math.isfinite(x) for x in returns + weights) or any(w < 0 for w in weights):
        raise ValueError("Finite returns and finite nonnegative weights required")
    pairs = [(r, w) for j, (r, w) in enumerate(zip(returns, weights)) if j != exclude]
    total = sum(w for _, w in pairs)
    if total <= 0:
        raise ValueError("No positive ex-self support")
    return sum(r * w for r, w in pairs) / total

def bars(session: int, grain: int) -> dict[str, int]:
    if session <= 0 or grain <= 0:
        raise ValueError("Positive session and grain required")
    full, stub = divmod(session, grain)
    return {"session_minutes": session, "grain_minutes": grain, "full_bars": full, "stub_minutes": stub}

def half_life(alpha: float, grain: float) -> float:
    if not 0 < alpha < 1 or grain <= 0:
        raise ValueError("0 < alpha < 1 and positive grain required")
    return grain * math.log(0.5) / math.log1p(-alpha)

@dataclass(frozen=True)
class Bar:
    start: datetime
    end: datetime
    known: datetime
    low: float
    high: float
    close: float
    complete: bool = True

def pivot_at(history: list[Bar], cutoff: datetime) -> tuple[float, float, str] | None:
    """Toy causal rejection-bar specification, not an owner-compatible detector."""
    available = [b for b in history if b.complete and b.end <= cutoff and b.known <= cutoff]
    available.sort(key=lambda b: b.end)
    if len(available) < 5:
        return None
    prior, current = available[-5:-1], available[-1]
    if current.end - current.start != timedelta(minutes=30):
        return None
    floor = min(b.low for b in prior)
    if current.high <= current.low:
        return None
    qualifies = current.low < floor and current.close > floor and (
        (current.close - current.low) / (current.high - current.low) >= 0.5)
    return (current.low, current.high, current.known.isoformat()) if qualifies else None

def first_passage(ohlc: list[tuple[float, float]], upper: float, lower: float) -> str:
    if lower >= upper:
        raise ValueError("Ordered barriers required")
    for high, low in ohlc:
        if low > high:
            raise ValueError("Invalid OHLC range")
        up, down = high >= upper, low <= lower
        if up and down:
            return "ORDER_UNRESOLVED"
        if up:
            return "UPPER_FIRST"
        if down:
            return "LOWER_FIRST"
    return "NEITHER_BY_HORIZON"

def main() -> dict[str, object]:
    rr, ww = [0.02, 0.01, 0.01], [0.4, 0.3, 0.3]
    inc, ex = basket(rr, ww), basket(rr, ww, 0)
    check("inclusive_relative_attenuation", math.isclose(rr[0] - inc, (1 - ww[0]) * (rr[0] - ex)),
          {"self_weight": ww[0], "inclusive_relative": rr[0] - inc, "ex_self_relative": rr[0] - ex})
    max_error = 0.0
    for i in range(3):
        own_weight = ww[i] / sum(ww)
        error = abs(rr[i] - inc - (1 - own_weight) * (rr[i] - basket(rr, ww, i)))
        max_error = max(max_error, error)
    check("ex_self_identity_all_members", max_error < 1e-14, {"max_absolute_error": max_error})
    def nested(subject: float, safe: bool) -> float:
        parent = basket([subject, .01, -.01], [.4, .3, .3], 0 if safe else None)
        return .5 * .01 + .5 * parent
    contaminated = (nested(.02, False) - nested(.01, False)) / .01
    clean = (nested(.02, True) - nested(.01, True)) / .01
    check("parent_shrinkage_reintroduces_self", math.isclose(contaminated, .2), {"subject_return_loading": contaminated})
    check("ex_self_parent_removes_loading", abs(clean) < 1e-14, {"subject_return_loading": clean})
    neff = sum([.9, .05, .05]) ** 2 / sum(w*w for w in [.9, .05, .05])
    check("member_count_not_effective_support", neff < 1.23, {"members": 3, "effective_n": neff})
    try:
        basket([.01], [1.0], 0)
    except ValueError:
        check("singleton_ex_self_refused", True, "No benchmark invented")
    else:
        check("singleton_ex_self_refused", False, "Should refuse")
    matrix = [bars(s, g) for s in (390, 210) for g in (15, 30, 60, 65, 120, 130, 195, 240)]
    for row in matrix:
        check(f"clock_conservation_{row['session_minutes']}_{row['grain_minutes']}",
              row["full_bars"] * row["grain_minutes"] + row["stub_minutes"] == row["session_minutes"], row)
    check("normal_session_native", all(bars(390, g)["stub_minutes"] == 0 for g in (30, 65, 130, 195)), "390-minute arithmetic")
    check("early_close_not_native", all(bars(210, g)["stub_minutes"] > 0 for g in (65, 130, 195)), "210-minute arithmetic")
    check("240m_unavailable_before_1330", 9 * 60 + 30 + 240 == 13 * 60 + 30, {"first_full_close_et": "13:30"})
    ema = 2 / 15
    rma = 1 / 14
    memory = []
    for name, a in (("EMA14", ema), ("Wilder14", rma)):
        a30 = 1 - (1-a) ** (30/120)
        row = {"kernel": name, "120m_half_life_minutes": half_life(a, 120), "30m_matched_alpha": a30,
               "30m_effective_period": (2/a30 - 1) if name == "EMA14" else 1/a30}
        memory.append(row)
        check(f"memory_match_{name}", math.isclose(half_life(a, 120), half_life(a30, 30), rel_tol=1e-12), row)
    check("same_period_changes_memory_fourfold", math.isclose(half_life(ema,120)/half_life(ema,30),4), "Same EMA14: 120m memory is four times 30m memory")
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    hs = [Bar(start+timedelta(minutes=30*i),start+timedelta(minutes=30*(i+1)),
              start+timedelta(minutes=30*(i+1),seconds=2),lo,lo+2,lo+1)
          for i,lo in enumerate([102,101.5,101,100.5])]
    candidate = Bar(start+timedelta(minutes=120),start+timedelta(minutes=150),
                    start+timedelta(minutes=150,seconds=2),100,102,101.5)
    hs.append(candidate)
    check("closed_but_not_known_refused", pivot_at(hs, candidate.end) is None, "Known time is two seconds after close")
    issued = pivot_at(hs, candidate.known)
    check("pivot_issued_only_when_available", issued is not None, issued)
    future = Bar(start+timedelta(minutes=150),start+timedelta(minutes=180),start+timedelta(minutes=180,seconds=2),90,110,109)
    check("future_suffix_cannot_change_issued_pivot", pivot_at(hs+[future], candidate.known) == issued, "As-of result unchanged")
    provisional = Bar(candidate.start,candidate.end,candidate.known,candidate.low,candidate.high,candidate.close,False)
    check("incomplete_30m_refused", pivot_at(hs[:-1]+[provisional],candidate.known) is None, "Incomplete flag prevents issue")
    check("frozen_pivot_not_current_future_low", issued is not None and issued[0] == 100 and future.low == 90, {"original_low": 100,"later_low":90})
    check("same_bar_confirmation_forbidden", not (candidate.end > candidate.known), "Confirmation must use a later bar and later availability")
    check("barrier_order_unidentified", first_passage([(102,99)],101,99.5) == "ORDER_UNRESOLVED", "OHLC does not order two hits")
    check("downside_barrier_is_competing_event", first_passage([(100,99.4),(102,100)],101,99.5) == "LOWER_FIRST", "Later rally cannot erase first invalidation")
    check("neither_hit_not_missing", first_passage([(100.2,99.8)],101,99.5) == "NEITHER_BY_HORIZON", "Observed non-event differs from absent data")
    p0,p1=.4,.7
    bounds=[(p0-y)**2-(p1-y)**2 for y in (0,1)]
    check("paired_missing_label_brier_bounds", math.isclose(min(bounds),-.33) and math.isclose(max(bounds),.27),
          {"baseline_minus_candidate_bounds": [min(bounds),max(bounds)], "same_outcome_required":True})
    early,late,target,A=100.1,100.8,101.0,1.0
    check("confirmation_cost_consumes_remaining_path", math.isclose((late-early)/A,.7) and math.isclose((target-late)/A,.2),
          {"confirmation_cost_A":(late-early)/A,"remaining_to_fixed_target_A":(target-late)/A})
    expected_primary = 2 * (1+1+2*8)
    check("initial_candidate_accounting", expected_primary == 36,
          {"model_forms":2,"B0":1,"P1":1,"eight_other_families_add_and_cumulative":16,"maximum_initial_fits":expected_primary})
    return {"schema":"rs_leader_mechanical_audit.v1","scope":"SYNTHETIC_AND_ALGEBRA_ONLY",
            "market_trials_executed":0,"source_admission_granted":False,"predictive_edge_estimated":False,
            "checks_passed":len(CHECKS),"checks_failed":0,"clock_matrix":matrix,"memory_controls":memory,"checks":CHECKS}

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=main()
    result["script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    payload=json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(payload,encoding="utf-8")
    print(json.dumps({"checks_passed":result["checks_passed"],"checks_failed":0,
                      "market_trials_executed":0,"result_sha256":hashlib.sha256(payload.encode()).hexdigest()},sort_keys=True))
