"""Pure research reference: past-only support and shrinkage, not an accepted forecast.
No source acquisition, persistence, dispatch or production authority. Stored prior
forecasts must actually have been fixed before their outcomes; types cannot prove it.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import fsum, isfinite
from typing import Sequence


def _aware(t: datetime) -> bool:
    return t.tzinfo is not None and t.utcoffset() is not None


def _fraction(x: float) -> bool:
    return isfinite(x) and 0 <= x <= 1


@dataclass(frozen=True)
class PastForecast:
    query_id: str
    profile_id: str
    issued_at: datetime
    outcome_available_at: datetime
    baseline: float
    analogue: float
    actual: float
    nearest_rms_distance: float

    def __post_init__(self) -> None:
        if not self.query_id or not self.profile_id:
            raise ValueError('Exact supplied query and representation identities required')
        if not _aware(self.issued_at) or not _aware(self.outcome_available_at):
            raise ValueError('Timezone-aware information clocks required')
        if self.outcome_available_at <= self.issued_at:
            raise ValueError('This future-outcome experiment requires positive maturation time')
        if not all(_fraction(x) for x in [self.baseline,self.analogue,self.actual]):
            raise ValueError('Positive-participation fractions must be finite and within [0,1]')
        if not isfinite(self.nearest_rms_distance) or self.nearest_rms_distance < 0:
            raise ValueError('A finite nonnegative distance is required')


def linear_quantile(values: Sequence[float], q: float) -> float:
    if not values or not 0 <= q <= 1:
        raise ValueError('Nonempty sample and a quantile in [0,1] required')
    x=sorted(values)
    if any(not isfinite(v) for v in x):
        raise ValueError('Finite quantile sample required')
    position=(len(x)-1)*q
    lo=int(position)
    hi=min(lo+1,len(x)-1)
    return x[lo]+(position-lo)*(x[hi]-x[lo])


def past_only_forecast(*, profile_id: str, decision_at: datetime,
                       baseline: float, analogue: float | None,
                       nearest_rms_distance: float | None,
                       history: Sequence[PastForecast]) -> dict:
    """Fixed v1: >=60 matured unique queries, past q95 novelty, 20-pseudoquery shrink.
    All technically eligible historic raw analogue forecasts calibrate the method,
    including ones that a then-cold policy would not have acted on. Their predictions
    still must have been fixed ex ante; they are not re-fit on current outcomes.
    Baseline fallback is a research comparison, not permission to serve a forecast.
    """
    if not profile_id or not _aware(decision_at) or not _fraction(baseline):
        raise ValueError('Valid profile, decision timestamp and baseline required')
    if (analogue is None) != (nearest_rms_distance is None):
        raise ValueError('Missing analogue must have an explicit matching absence')
    if analogue is not None and (not _fraction(analogue) or not isfinite(nearest_rms_distance)
                                 or nearest_rms_distance < 0):
        raise ValueError('Invalid current analogue or distance')
    # Equal decision-time releases are conservatively excluded. Unmatured records
    # cannot contribute their distances or targets in this deliberately simple v1.
    past=[r for r in history if r.profile_id==profile_id and r.issued_at < decision_at
          and r.outcome_available_at < decision_at]
    keys=[r.query_id for r in past]
    if len(keys)!=len(set(keys)):
        raise ValueError('Duplicate historical queries would inflate support')
    base={'n_matured':len(past),'used_alpha':0.,'fitted_alpha':None,
          'distance_threshold':None,'forecast':baseline,
          'support_claim':'HEURISTIC_DISTANCE_SCREEN_NOT_CALIBRATED_CONFIDENCE'}
    if analogue is None:
        return base | {'reason':'NO_TECHNICAL_MATCH'}
    if len(past)<60:
        return base | {'reason':'COLD_START_BASELINE_ONLY'}
    threshold=linear_quantile([r.nearest_rms_distance for r in past],.95)
    deltas=[r.analogue-r.baseline for r in past]
    ss=fsum(d*d for d in deltas)
    numerator=fsum((r.actual-r.baseline)*d for r,d in zip(past,deltas))
    denom=ss*(1+20/len(past))
    alpha=0. if denom==0 else min(1.,max(0.,numerator/denom))
    base |= {'fitted_alpha':alpha,'distance_threshold':threshold}
    if nearest_rms_distance > threshold:
        return base | {'reason':'OUTSIDE_PAST_DISTANCE_SUPPORT'}
    return base | {'used_alpha':alpha,'forecast':baseline+alpha*(analogue-baseline),
                   'reason':'SUPPORTED_SHRUNK_RESEARCH_FORECAST' if alpha>0
                            else 'NO_POSITIVE_CALIBRATED_INCREMENT'}


def evaluation_table(outcomes: Sequence[float], baseline: Sequence[float],
                     candidate: Sequence[float | None]) -> dict:
    """Compare common queries AND the all-query fallback policy, no mask cherry-pick."""
    if not outcomes or len(outcomes)!=len(baseline) or len(outcomes)!=len(candidate):
        raise ValueError('Equal nonempty evaluation arrays required')
    if not all(_fraction(x) for x in list(outcomes)+list(baseline)):
        raise ValueError('Known finite outcome and baseline fractions required')
    if any(x is not None and not _fraction(x) for x in candidate):
        raise ValueError('Candidate must be a valid fraction or explicit abstention')
    covered=[i for i,x in enumerate(candidate) if x is not None]
    all_ids=range(len(outcomes))
    mse=lambda predictions,ids: fsum((outcomes[i]-predictions[i])**2 for i in ids)/len(ids)
    policy=[baseline[i] if candidate[i] is None else candidate[i] for i in all_ids]
    return {'n_queries':len(outcomes),'n_covered':len(covered),
            'coverage':len(covered)/len(outcomes),
            'baseline_all_mse':mse(baseline,all_ids),
            'candidate_same_covered_mse':mse(candidate,covered) if covered else None,
            'baseline_same_covered_mse':mse(baseline,covered) if covered else None,
            'full_fallback_policy_mse':mse(policy,all_ids)}
