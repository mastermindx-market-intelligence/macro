"""Pure S2-P3 day-clustered diagnostic on declared BVC/quote comparisons.

This method is a descriptive source-independent scientific *prerequisite*.
It does not authenticate underlying tape, establish actual aggressor labels,
infer beneficial owners, fit a model, manufacture data or publish an alert.
Expected security-minute slots and research source cohorts are owner inputs.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict,dataclass,field
from decimal import Decimal,InvalidOperation,localcontext
import math
from typing import Iterable

import pressure as m
import quote_calibration as q
import quote_reference as tape_q

_ALLOWED_STATUS={
 "COMPARABLE_PROXY_DIAGNOSTIC",
 "QUOTE_COVERAGE_INSUFFICIENT",
 "GROSS_NOTIONAL_MISMATCH",
 "BVC_DIRECTION_UNAVAILABLE",
 "NO_ELIGIBLE_TAPE"
}


@dataclass(frozen=True)
class ExpectedSlot:
    security_id: str
    session_id: str
    phase: str
    start_utc_s: int
    end_utc_s: int

    def validate(self) -> None:
        m._text(self.security_id,"security_id")
        m._date(self.session_id)
        if self.phase not in ("PRE","RTH","AH"):
            raise ValueError("invalid_phase")
        m._integer(self.start_utc_s,"slot_start")
        m._integer(self.end_utc_s,"slot_end")
        if self.start_utc_s%60 or self.end_utc_s-self.start_utc_s!=60:
            raise ValueError("exact_one_minute_slot_required")
        if (m._et_clock(self.start_utc_s)[0]!=self.session_id or
            m._et_clock(self.end_utc_s-1)[0]!=self.session_id):
            raise ValueError("slot_clock_session_mismatch")


@dataclass(frozen=True)
class TaggedComparison:
    slot: ExpectedSlot
    comparison: q.MinuteComparison
    policy_ref: str
    population_ref: str
    mode: str


@dataclass(frozen=True)
class StudyPolicy:
    min_session_clusters: int=3

    def validate(self) -> None:
        if (type(self.min_session_clusters) is not int or
            not 3<=self.min_session_clusters<=252):
            raise ValueError("min_session_clusters_invalid")


@dataclass(frozen=True)
class StudyResult:
    status: str
    expected_minutes: int
    observed_minutes: int
    missing_minutes: int
    comparable_minutes: int
    not_comparable_minutes: int
    expected_session_clusters: int
    session_clusters_with_comparables: int
    per_day: tuple[tuple[str,int,int,float|None],...]
    status_counts: tuple[tuple[str,int],...]
    quote_eligible_gross_observed_usd: str
    quote_classified_gross_observed_usd: str
    quote_unknown_gross_observed_usd: str
    quote_classified_share_observed: str|None
    equal_day_mean_proxy_disagreement: float|None
    leave_one_day_out_low: float|None
    leave_one_day_out_high: float|None
    is_confidence_interval: bool
    is_statistical_accuracy_study: bool
    source_receipts_verified: bool
    rights_verified: bool
    market_pilot_admitted: bool
    customer_publishable: bool
    knowledge_class: str
    source_scope: str
    mode: str|None
    policy_ref: str|None
    population_ref: str|None
    input_digest: str
    authority: dict[str,bool]=field(default_factory=lambda:dict(tape_q.NO_AUTHORITY))


def _value(v: str,field: str, *, nonnegative: bool=False) -> Decimal:
    if not isinstance(v,str) or len(v)>512:
        raise ValueError(field+"_invalid")
    try:
        x=Decimal(v)
    except (InvalidOperation,ValueError):
        raise ValueError(field+"_invalid") from None
    if not x.is_finite() or (nonnegative and x<0):
        raise ValueError(field+"_invalid")
    return x


def _str(v: Decimal) -> str:
    return "0" if not v else format(v.normalize(),"f")


def assess_quote_study(expected_slots: Iterable[ExpectedSlot],
                       observations: Iterable[TaggedComparison], *,
                       cutoff_utc_s: int,
                       policy: StudyPolicy=StudyPolicy()) -> StudyResult:
    """Equal-weight day-cluster mean and leave-one-day-out stability envelope.

    A leave-one-day-out envelope is NOT a sampling-confidence interval. The
    comparator's ratio disagreement is NOT labelled exchange-truth accuracy.
    """
    if not isinstance(policy,StudyPolicy):
        raise ValueError("study_policy_required")
    policy.validate()
    m._integer(cutoff_utc_s,"cutoff")
    if cutoff_utc_s<=0:
        raise ValueError("invalid_cutoff")
    expected={}
    for slot in expected_slots:
        if not isinstance(slot,ExpectedSlot):
            raise ValueError("expected_slot_required")
        slot.validate()
        if slot.end_utc_s>cutoff_utc_s:
            raise ValueError("cutoff_before_expected_slot_end")
        key=(slot.session_id,slot.security_id,slot.start_utc_s)
        if key in expected:
            raise ValueError("duplicate_expected_slot")
        expected[key]=slot
    if not expected:
        raise ValueError("expected_population_required")
    seen={}
    policies=set();populations=set();modes=set()
    for t in observations:
        if not isinstance(t,TaggedComparison) or not isinstance(t.comparison,q.MinuteComparison):
            raise ValueError("tagged_comparison_required")
        if not isinstance(t.slot,ExpectedSlot):
            raise ValueError("comparison_slot_required")
        t.slot.validate()
        key=(t.slot.session_id,t.slot.security_id,t.slot.start_utc_s)
        if key not in expected:
            raise ValueError("unexpected_slot")
        if t.slot!=expected[key]:
            raise ValueError("slot_identity_mismatch")
        if key in seen:
            raise ValueError("duplicate_observation")
        c=t.comparison
        if (c.session_id!=t.slot.session_id or c.security_id!=t.slot.security_id
                or c.phase!=t.slot.phase or c.start_utc_s!=t.slot.start_utc_s
                or c.end_utc_s!=t.slot.end_utc_s):
            raise ValueError("comparison_clock_identity_mismatch")
        if (c.knowledge_class!="ESTIMATOR_COMPARISON_NOT_TAPE_TRUTH" or
            c.authority!=tape_q.NO_AUTHORITY or
            c.is_statistical_confidence_interval):
            raise ValueError("comparison_authority_or_class_invalid")
        if c.status not in _ALLOWED_STATUS:
            raise ValueError("comparison_status_not_supported")
        m._text(t.policy_ref,"policy_ref")
        m._text(t.population_ref,"population_ref")
        if t.mode not in ("as_observed","corrected_history"):
            raise ValueError("observation_mode_unknown")
        policies.add(t.policy_ref);populations.add(t.population_ref);modes.add(t.mode)
        if len(policies)>1:raise ValueError("mixed_policy")
        if len(populations)>1:raise ValueError("mixed_population")
        if len(modes)>1:raise ValueError("mixed_mode")
        seen[key]=t

    day_denominator=defaultdict(int)
    daily_means=defaultdict(list)
    counts=defaultdict(int)
    eligible=classified=unknown=Decimal(0)
    with localcontext() as ctx:
        ctx.prec=256
        for slot in expected.values():
            day_denominator[slot.session_id]+=1
        for key,t in seen.items():
            c=t.comparison
            counts[c.status]+=1
            qeligible=_value(c.quote_eligible_gross,"eligible",nonnegative=True)
            qclass=_value(c.quote_classified_gross,"classified",nonnegative=True)
            qunknown=_value(c.quote_unknown_gross,"unknown",nonnegative=True)
            if qeligible!=qclass+qunknown:
                raise ValueError("quote_notional_accounting_mismatch")
            eligible+=qeligible;classified+=qclass;unknown+=qunknown
            if c.status=="COMPARABLE_PROXY_DIAGNOSTIC":
                if (c.absolute_ratio_disagreement is None or c.bvc_ratio is None
                        or c.quote_covered_ratio is None):
                    raise ValueError("comparable_requires_ratios")
                a=_value(c.absolute_ratio_disagreement,"proxy_gap",nonnegative=True)
                br=_value(c.bvc_ratio,"bvc_ratio")
                qr=_value(c.quote_covered_ratio,"quote_ratio")
                if abs(br)>1 or abs(qr)>1 or a>2 or abs(br-qr)!=a:
                    raise ValueError("disagreement_accounting_mismatch")
                daily_means[t.slot.session_id].append(float(a))
            elif c.absolute_ratio_disagreement is not None:
                raise ValueError("withheld_disagreement_required")
        ratios=_str(classified/eligible) if eligible else None

    day_mean={}
    per_day=[]
    for day in sorted(day_denominator):
        vals=daily_means.get(day,[])
        mean=math.fsum(vals)/len(vals) if vals else None
        if mean is not None:
            day_mean[day]=mean
        per_day.append((day,len(vals),day_denominator[day],mean))
    clusters=len(day_mean)
    status=("DESCRIPTIVE_STABILITY_AVAILABLE"
            if clusters>=policy.min_session_clusters
            else "INSUFFICIENT_SESSION_CLUSTERS")
    aggregate=low=high=None
    if status=="DESCRIPTIVE_STABILITY_AVAILABLE":
        means=[day_mean[day] for day in sorted(day_mean)]
        aggregate=math.fsum(means)/len(means)
        loo=[math.fsum(means[:i]+means[i+1:])/(len(means)-1)
             for i in range(len(means))]
        low=min(loo);high=max(loo)
    records=[seen[key] for key in sorted(seen)]
    return StudyResult(
        status,len(expected),len(seen),len(expected)-len(seen),
        sum(len(x) for x in daily_means.values()),
        len(seen)-sum(len(x) for x in daily_means.values()),
        len(day_denominator),clusters,tuple(per_day),
        tuple(sorted(counts.items())),
        _str(eligible),_str(classified),_str(unknown),ratios,
        aggregate,low,high,False,False,False,False,False,False,
        "BAR_VS_QUOTE_PROXY_DISAGREEMENT_NOT_TAPE_TRUTH",
        "OWNER_SUPPLIED_EXPECTED_SLOTS_UNVERIFIED",
        next(iter(modes)) if modes else None,
        next(iter(policies)) if policies else None,
        next(iter(populations)) if populations else None,
        m.digest({"slots":[asdict(expected[k]) for k in sorted(expected)],
                  "observations":[asdict(x) for x in records],
                  "cutoff_utc_s":cutoff_utc_s,"policy":asdict(policy)}))
