"""Pure prospective-claim outcome inspection; never an alpha trial or trading engine.

This accepts an existing research owner's predeclared claim contract and an
incumbent market-data owner's complete, authenticated bar window. It does not
capture posts, create case IDs, register trials, fetch quotes, store results,
choose cohorts, set thresholds, infer intra-bar order, estimate probabilities,
assess option fills, or originate/suggest orders.

A coverage failure is an abstention, NEVER a missed forecast. Owner callbacks
are application-injected and must verify original publication/vintage, rights,
calendar, data revisions and the exact complete window. Synthetic callbacks
in tests prove arithmetic only; no model or analyst may supply the callback.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Callable
import operator
import re

from engine.market_navigator import AUTHORITY, ContractError, HORIZONS, _clock, _number, _ref
from engine.market_navigator_price_confirmation import ClosedBar

SCHEMA = "market_navigator.outcome_inspection/v1"
_KINDS = frozenset({"level_touch", "terminal_close"})
_OPS = {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le}
_UNITS = frozenset({"USD", "index_points"})
_HEX = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class OutcomeCase:
    """An incumbent research owner's frozen prediction/assessment contract."""

    claim_id: str
    episode_id: str
    rule_ref: str
    subject: str
    horizon: str
    original_rule_available_at: str
    decision_at: str
    deadline: str
    kind: str
    operator: str
    threshold: float
    unit: str

    def __post_init__(self) -> None:
        if not all(isinstance(x, str) and _HEX.fullmatch(x)
                   for x in (self.claim_id, self.episode_id)):
            raise ContractError("canonical claim and episode hashes required")
        for value in (self.rule_ref, self.subject):
            _ref(value)
        if self.horizon not in HORIZONS or self.kind not in _KINDS:
            raise ContractError("unsupported market horizon or outcome")
        if self.operator not in _OPS or self.unit not in _UNITS:
            raise ContractError("supported positive level comparison required")
        if _number(self.threshold) <= 0:
            raise ContractError("level must be positive")
        availability = _clock(self.original_rule_available_at)
        decision = _clock(self.decision_at)
        deadline = _clock(self.deadline)
        if not availability <= decision < deadline:
            raise ContractError("original rule must be known before decision and deadline")


def inspect_case(
    *, case: OutcomeCase, as_known_at: str, bars: tuple[ClosedBar, ...],
    expected_first_sequence: int | None = None,
    expected_last_sequence: int | None = None,
    verify_owner: Callable[[OutcomeCase, tuple[ClosedBar, ...], int, int, datetime], bool] | None = None,
) -> dict:
    """Resolve only the literal math of one predeclared, fully observed case.

    Scores at/after original deadline to avoid cherry-picking early winners.
    Both expected sequence bounds must be signed off by the actual data/
    exchange calendar owner, not inferred from the provided bars themselves.
    No metric or score denominator is computed here: the existing research
    owner retains cohort selection, trial registration and statistical grading.
    """
    if not isinstance(case, OutcomeCase) or type(bars) is not tuple or len(bars) > 512:
        raise ContractError("bounded typed case and bar tuple required")
    if not all(isinstance(row, ClosedBar) for row in bars):
        raise ContractError("all bars must use the incumbent typed bar contract")
    asof = _clock(as_known_at)
    out = {
        "schema": SCHEMA,
        "claim_id": case.claim_id,
        "episode_id": case.episode_id,
        "subject_binding_sha256": sha256(case.subject.encode()).hexdigest(),
        "rule_binding_sha256": sha256(case.rule_ref.encode()).hexdigest(),
        "horizon": case.horizon,
        "kind": case.kind,
        "operator": case.operator,
        "unit": case.unit,
        "threshold": case.threshold,
        "decision_at": case.decision_at,
        "deadline": case.deadline,
        "as_known_at": asof.isoformat().replace("+00:00", "Z"),
        "status": "unresolved",
        "mathematical_outcome": None,
        "eligible_trial": False,
        "predictive_validation": False,
        "source_authenticity_proven": False,
        "recommendation": False,
        "probability": None,
        "authority": dict(AUTHORITY),
    }
    if asof < _clock(case.deadline):
        return out | {"status": "decision_window_open"}
    if expected_first_sequence is None or expected_last_sequence is None or not bars:
        return out | {"status": "coverage_not_attested"}
    if (type(expected_first_sequence) is not int or type(expected_last_sequence) is not int
            or expected_first_sequence < 0 or expected_last_sequence < expected_first_sequence
            or expected_last_sequence >= 1_000_000_000):
        raise ContractError("invalid source-owner calendar bounds")
    if (len(bars) != expected_last_sequence - expected_first_sequence + 1
            or bars[0].sequence != expected_first_sequence
            or bars[-1].sequence != expected_last_sequence):
        return out | {"status": "calendar_window_incomplete"}
    if (any(row.subject != case.subject or row.horizon != case.horizon or row.unit != case.unit
            for row in bars)):
        return out | {"status": "subject_or_horizon_mismatch"}
    generation = bars[0].generation_ref
    if any(row.generation_ref != generation for row in bars):
        return out | {"status": "mixed_generation"}
    if any(left.sequence + 1 != right.sequence or _clock(left.ends_at) > _clock(right.begins_at)
           for left, right in zip(bars, bars[1:])):
        return out | {"status": "calendar_sequence_inconsistent"}
    if (_clock(bars[0].begins_at) < _clock(case.decision_at)
            or _clock(bars[-1].ends_at) > _clock(case.deadline)):
        return out | {"status": "outside_predeclared_window"}
    if any(not row.completed for row in bars):
        return out | {"status": "unfinished_source_bar"}
    if any(_clock(row.available_at) > asof for row in bars):
        return out | {"status": "bar_not_yet_available"}
    if any(_clock(row.valid_until) <= asof for row in bars):
        return out | {"status": "expired_source_revision"}
    if not callable(verify_owner):
        return out | {"status": "source_owner_missing"}
    try:
        allowed = verify_owner(case, bars, expected_first_sequence, expected_last_sequence, asof)
    except (ValueError, TypeError, PermissionError, RuntimeError, OSError):
        allowed = False
    if allowed is not True:
        return out | {"status": "source_owner_refused"}
    # The contract's comparison operator is frozen BEFORE the decision,
    # not chosen for whichever side of a bar happened to trade.
    comparator = _OPS[case.operator]
    if case.kind == "terminal_close":
        observed = comparator(bars[-1].close, case.threshold)
    elif case.operator in {"gt", "gte"}:
        observed = any(comparator(row.high, case.threshold) for row in bars)
    else:
        observed = any(comparator(row.low, case.threshold) for row in bars)
    return out | {
        "status": "mathematically_resolved",
        "mathematical_outcome": bool(observed),
        "observed_bar_count": len(bars),
        "first_bar_end": bars[0].ends_at,
        "last_bar_end": bars[-1].ends_at,
        "generation_binding_sha256": sha256(generation.encode()).hexdigest(),
        "owner_callback_qualified": True,
    }


def research_link_diagnostics(*, case: OutcomeCase, ruler: "ResearchRuler",
                              audited_claim: dict) -> dict:
    """Check typed original-claim/ruler alignment without trusting audit metadata.

    This is a diagnostic join onto existing Navigator research intake, NOT
    authority to admit a trial or a source. The app must obtain the row from
    its existing grounded extractor and the original owner must independently
    verify source-body/revision, time, rights, episode and trial registration.
    """
    from engine.market_navigator_research import ResearchRuler

    if not isinstance(case, OutcomeCase) or not isinstance(ruler, ResearchRuler):
        raise ContractError("typed existing research ruler and outcome case required")
    if type(audited_claim) is not dict:
        raise ContractError("bounded existing research audit row required")
    if audited_claim.get("claim_id") != case.claim_id or ruler.claim_id != case.claim_id:
        raise ContractError("source-bound claim identity mismatch")
    issues = []
    if audited_claim.get("status") != "ruler_fields_present_not_validated":
        issues.append("research_fields_not_complete")
    if audited_claim.get("annotation_status") != "externally_supplied_not_semantically_verified":
        issues.append("annotation_not_identified")
    original_gaps = audited_claim.get("gaps")
    if not isinstance(original_gaps, list) or original_gaps:
        issues.append("research_gaps_present")
    if ruler.outcome != case.kind:
        issues.append("outcome_type_mismatch")
    if ruler.subject != case.subject or ruler.horizon != case.horizon:
        issues.append("research_subject_or_horizon_mismatch")
    if ruler.decision_at is None or _clock(ruler.decision_at) != _clock(case.decision_at):
        issues.append("decision_cutoff_mismatch")
    if ruler.deadline is None or _clock(ruler.deadline) != _clock(case.deadline):
        issues.append("original_deadline_mismatch")
    if ruler.trigger_ref != case.rule_ref:
        issues.append("original_rule_reference_mismatch")
    if _clock(ruler.annotation_available_at) > _clock(case.decision_at):
        issues.append("annotation_not_known_at_decision")
    if ruler.conditional is None:
        issues.append("conditional_nature_unknown")
    return {
        "schema": "market_navigator.outcome_research_link/v1",
        "claim_id": case.claim_id,
        "episode_id": case.episode_id,
        "status": "aligned_fields_not_authenticated" if not issues else "unqualified",
        "issues": issues,
        "source_authenticity_proven": False,
        "trial_registered": False,
        "score_admitted": False,
        "authority": dict(AUTHORITY),
    }
