"""Lane 8 (v1.1) — per-head forecast capabilities + Evaluation / Portfolio contracts.

Observed Cycles facts are shown elsewhere in the record. This module only answers, for each of
the four remaining-opportunity heads, whether it may be shown on a record, and why not:

    remaining_return_distribution · adverse_tail · target_before_invalidation · transition_time

Each head is judged ALONE under the predeclared protocol
`research/sector_completion_20261021/B12_V11_HEADS_PROTOCOL.md`; its frozen research result is
`HEAD_RESEARCH` below (from `b12/v11_heads_result.json`). Passing one head qualifies none of its
siblings; withdrawing one removes only that head. The historical W4.2 4/6 verdict is not an input.

No head emits a number today. A research-qualified head still needs a live record whose turn
state is the protocol's (ZigZag v2, close_price, 14%, epoch `price_c4414dcb`) AND a wired live
estimator; neither exists, so every head is `withheld` with its own reason code.

The Evaluation / Portfolio part is a typed contract only (no UI, no runner): it fixes what a
Strategy-evaluation result and an exposure request must carry so that capture ratios, attribution
and selection claims cannot be faked. Wording law: raw relative strength is not estimated alpha;
positive selection contribution is not evidence of portfolio skill; historical duration is not
remaining upside. Nothing here ranks, gates, sizes, trades or escalates.
"""
from __future__ import annotations

from typing import Literal, Optional, TypedDict

FORECAST_HEADS_SCHEMA = "sector_cycles.forecast_heads.v1"
PROTOCOL_REF = "research/sector_completion_20261021/B12_V11_HEADS_PROTOCOL.md"
REPORT_REF = "research/sector_completion_20261021/b12/v11_heads_result.json"
RESULTS_REF = "research/sector_completion_20261021/B12_V11_HEADS_RESULTS.md"
PROTOCOL_EPOCH = "price_c4414dcb"        # ZigZag v2, close_price, pct 14 (onto.turn_epoch)
HORIZON_SESSIONS = 20                    # completed sessions after a t+1 close entry
AUTHORITY = {"may_rank": False, "may_gate": False, "may_size": False,
             "may_trade": False, "may_escalate": False}

HEADS = ("remaining_return_distribution", "adverse_tail",
         "target_before_invalidation", "transition_time")

TARGETS = {
    "remaining_return_distribution": (
        "quantiles 10/25/50/75/90 of the ETF's 20-session total return minus SPY's over the "
        "same closes, less a 10 bp round trip (percentage-point difference, not alpha)"),
    "adverse_tail": (
        "probability that the cumulative total return from entry falls to -1.5 x trailing "
        "20-session volatility within 20 sessions"),
    "target_before_invalidation": (
        "probability that the cumulative total return from entry reaches +1 x trailing "
        "20-session volatility before -1 x, within 20 sessions"),
    "transition_time": (
        "probability that the next turn becomes first-known (confirmed_at, not pivot date) "
        "within 20 sessions"),
}

# Frozen from b12/v11_heads_result.json (see B12_V11_HEADS_RESULTS.md for the full table).
# A change in the result file without a change here fails tests/test_sector_forecast_heads.py.
HEAD_RESEARCH: dict[str, dict] = {
    'remaining_return_distribution': {'disposition': 'WITHHELD_FAILED', 'reasons': ['skill_ci90_includes_or_below_zero', 'fails_bh_fdr_q0.10', 'skill_positive_in_under_60pct_of_years'], 'skill': -0.00062, 'ci90': [-0.00747, 0.00579], 'p_one_sided': 0.562, 'n_scored': 2300, 'coverage': 0.9922, 'n_dates': 430},
    'adverse_tail': {'disposition': 'QUALIFIED_RESEARCH', 'reasons': [], 'skill': 0.01018, 'ci90': [0.00218, 0.01922], 'p_one_sided': 0.018, 'n_scored': 2300, 'coverage': 0.9922, 'n_dates': 430},
    'target_before_invalidation': {'disposition': 'QUALIFIED_RESEARCH', 'reasons': [], 'skill': 0.02666, 'ci90': [0.00927, 0.04335], 'p_one_sided': 0.0035, 'n_scored': 2300, 'coverage': 0.9922, 'n_dates': 430},
    'transition_time': {'disposition': 'QUALIFIED_RESEARCH', 'reasons': [], 'skill': 0.10195, 'ci90': [0.06696, 0.14157], 'p_one_sided': 0.0, 'n_scored': 2300, 'coverage': 0.9922, 'n_dates': 430},
}

Disposition = Literal["QUALIFIED_RESEARCH", "WITHHELD_FAILED", "WITHHELD_UNDERPOWERED",
                      "NOT_EVALUATED"]

_RECONSTRUCTED_KINDS = frozenset({"basket"})   # amalgam families use kind=<ns>


def _head(head: str, *, status: str, reason: str) -> dict:
    res = HEAD_RESEARCH.get(head) or {"disposition": "NOT_EVALUATED", "reasons": []}
    return {
        "status": status,                     # always "withheld" today
        "reason_code": reason,
        "research_disposition": res["disposition"],
        "research_reasons": list(res.get("reasons") or []),
        # Pointer only: the protocol says "nothing numeric yet" on a record, so research
        # statistics stay in the report, never on the live payload (independent review M2).
        "evidence": {"protocol": PROTOCOL_REF, "report_ref": REPORT_REF,
                     "results_doc": RESULTS_REF},
        "target": TARGETS[head],
        "horizon_sessions": HORIZON_SESSIONS,
        "market": "US",
    }


def head_capabilities(*, record_kind: str, turn_epoch: Optional[str],
                      market: str = "US", live_estimator_wired: bool = False) -> dict:
    """Per-head capability block for one Cycles record.

    Reason precedence per head (first that applies):
      membership_not_point_in_time  — basket / amalgam records (today's roster back-projected)
      record_kind_not_evaluated     — any other non-sector record kind
      market_not_evaluated          — any non-US record
      research_withheld_failed / research_withheld_underpowered / research_not_evaluated
      live_state_not_protocol_epoch — the record's turn state is not the protocol's epoch
      live_estimator_not_wired      — no live estimator emits this head yet
    """
    out = {}
    for head in HEADS:
        disp = (HEAD_RESEARCH.get(head) or {}).get("disposition", "NOT_EVALUATED")
        if record_kind in _RECONSTRUCTED_KINDS:
            reason = "membership_not_point_in_time"
        elif record_kind != "sector":
            reason = "record_kind_not_evaluated"
        elif market != "US":
            reason = "market_not_evaluated"
        elif disp != "QUALIFIED_RESEARCH":
            reason = {"WITHHELD_FAILED": "research_withheld_failed",
                      "WITHHELD_UNDERPOWERED": "research_withheld_underpowered"
                      }.get(disp, "research_not_evaluated")
        elif turn_epoch != PROTOCOL_EPOCH:
            reason = "live_state_not_protocol_epoch"
        elif not live_estimator_wired:
            reason = "live_estimator_not_wired"
        else:   # unreachable today: every branch above withholds
            reason = "live_estimator_not_wired"
        out[head] = _head(head, status="withheld", reason=reason)
    return {"schema": FORECAST_HEADS_SCHEMA, "observed_cycles": "shown",
            "protocol": PROTOCOL_REF, "report_ref": REPORT_REF, "heads": out, **AUTHORITY}


def withdraw(block: dict, head: str, reason: str) -> dict:
    """Withdraw ONE head (SP10): only that head changes; siblings are untouched."""
    if head not in HEADS:
        raise KeyError(head)
    new = {**block, "heads": dict(block["heads"])}
    new["heads"][head] = {**block["heads"][head], "status": "withheld", "reason_code": reason}
    return new


# ── Evaluation / Portfolio typed contracts (no UI, no runner) ────────────────

COMPARATOR_IDS = ("C1_passive_market", "C2_simple_participation", "C3_sector_allocation_only",
                  "C4_member_selection_only", "C5_joint_sector_and_name",
                  "C6_exact_incumbent_prophet", "C7_independent_emergence")

CLAIMS = ("observed_relative_performance", "estimated_exposure_residual",
          "participation_attribution", "incremental_selection_value")

CAPTURE_MIN_DENOMINATOR = 0.01           # |sum of benchmark returns| below this → unavailable


class ComparatorResult(TypedDict, total=False):
    id: str                               # one of COMPARATOR_IDS
    status: Literal["evaluated", "unavailable"]
    reason: Optional[str]                 # required when unavailable
    ann_return: float
    ann_excess_over_cash: float
    beta_vs_market: float
    tracking_error: float
    upside_capture: Optional[float]       # None when the denominator is near zero
    downside_capture: Optional[float]
    mean_invested: float
    annual_turnover: float
    costs_paid_total: float
    no_entry_periods: int
    no_fill_signals: int


class StrategyEvaluationResult(TypedDict, total=False):
    schema: str                           # "sector_intelligence.strategy_evaluation.v1"
    view: Literal["STRATEGY_EVALUATION_VIEW"]   # an adapter view, NOT a third Record population
    protocol_ref: str                     # predeclared protocol; results after it
    market: str
    benchmark: str
    costs_bp_per_side: float
    comparators: list                     # list[ComparatorResult], all seven ids present
    exposure_matched_reference: dict      # {"invested_fraction": w, "ann_excess_vs": {...ci90}}
    failed_leaders: dict                  # count + share held
    rebounds: dict                        # participation after drawdowns
    claims: dict                          # CLAIMS -> {"status", "basis"}


class ExposureRequest(TypedDict, total=False):
    schema: str                           # "sector_intelligence.portfolio_exposure_request.v1"
    account_ref: Optional[str]
    holdings_verified: bool               # Portfolio/Risk owner verified rights + holdings
    positions: Optional[list]             # [{"instrument", "weight"}] or None when unknown
    accounting_method: Optional[str]      # one named method + linking rule, or None


def capture_ratio(strategy_sum: float, benchmark_sum: float) -> Optional[float]:
    """Capture is unavailable (None) on a near-zero benchmark denominator (SP20)."""
    if benchmark_sum is None or abs(benchmark_sum) < CAPTURE_MIN_DENOMINATOR:
        return None
    return strategy_sum / benchmark_sum


def attribution(req: ExposureRequest) -> dict:
    """Participation attribution needs verified holdings and every weight. Unknown is
    unavailable, never zero (SP20)."""
    if not req.get("holdings_verified"):
        return {"status": "unavailable", "reason": "holdings_not_verified"}
    pos = req.get("positions")
    if pos is None:
        return {"status": "unavailable", "reason": "positions_unknown"}
    if any(p.get("weight") is None for p in pos):
        return {"status": "unavailable", "reason": "weights_missing"}
    if not req.get("accounting_method"):
        return {"status": "unavailable", "reason": "accounting_method_unnamed"}
    invested = sum(float(p["weight"]) for p in pos)
    return {"status": "computable", "invested_fraction": invested,
            "cash_fraction": 1.0 - invested, "method": req["accounting_method"]}


def selection_claim(diff_vs_exposure_matched_ci90: Optional[list]) -> dict:
    """Incremental selection value is never established by this lane (SP19/SP21). If the
    improvement is gone after the exposure match, say so; if not, it still needs Evaluation's
    out-of-sample acceptance."""
    if not diff_vs_exposure_matched_ci90:
        return {"status": "unavailable", "basis": "no_exposure_matched_comparison"}
    lo, _hi = diff_vs_exposure_matched_ci90
    if lo <= 0:
        return {"status": "not_established",
                "basis": "difference_vs_exposure_matched_reference_includes_zero_or_negative"}
    return {"status": "not_established",
            "basis": "positive_after_exposure_match_but_needs_evaluation_owner_acceptance"}


_FORBIDDEN_LABELS = ("alpha", "skill", "edge", "remaining_upside")


def validate_evaluation_result(res: StrategyEvaluationResult) -> list[str]:
    """Return the list of contract violations (empty = valid)."""
    errs: list[str] = []
    if res.get("view") != "STRATEGY_EVALUATION_VIEW":
        errs.append("view_must_be_strategy_evaluation_adapter")
    ids = [c.get("id") for c in res.get("comparators") or []]
    for cid in COMPARATOR_IDS:
        if cid not in ids:
            errs.append(f"missing_comparator:{cid}")
    for c in res.get("comparators") or []:
        if c.get("status") == "unavailable" and not c.get("reason"):
            errs.append(f"unavailable_without_reason:{c.get('id')}")
        if c.get("status") == "evaluated":
            for k in ("no_entry_periods", "no_fill_signals", "costs_paid_total",
                      "mean_invested"):
                if k not in c:
                    errs.append(f"missing_{k}:{c.get('id')}")
    for k in ("failed_leaders", "rebounds", "exposure_matched_reference"):
        if not res.get(k):
            errs.append(f"missing_{k}")
    claims = res.get("claims") or {}
    for k in CLAIMS:
        if k not in claims:
            errs.append(f"missing_claim:{k}")
    if (claims.get("incremental_selection_value") or {}).get("status") == "established":
        errs.append("selection_value_cannot_be_established_here")
    for key in _walk_keys(res):
        if any(b in key.lower() for b in _FORBIDDEN_LABELS):
            errs.append(f"forbidden_label:{key}")
    for flag, v in AUTHORITY.items():
        if res.get(flag):
            errs.append(f"authority_flag_true:{flag}")
    return errs


def _walk_keys(obj) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            out += _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _walk_keys(v)
    return out
