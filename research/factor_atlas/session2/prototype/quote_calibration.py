"""Pure one-minute comparison of BVC and quote-reference estimators.

Not a tape-truth oracle, source qualifier, historical replay owner or predictor.
Matched covered-dollar disagreement is a descriptive sensitivity calculation;
source/admission/tape eligibility remains with incumbent owners.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, localcontext
import math
import pressure as m
import quote_reference as q


@dataclass(frozen=True)
class ComparisonPolicy:
    min_quote_coverage: float = .9
    max_notional_gap: float = .05

    def validate(self) -> None:
        for name, value in (("min_quote_coverage",self.min_quote_coverage),
                            ("max_notional_gap",self.max_notional_gap)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError(name+"_invalid")
        if not 0 < self.min_quote_coverage <= 1 or not 0 <= self.max_notional_gap <= 1:
            raise ValueError("comparison_policy_out_of_bounds")


@dataclass(frozen=True)
class MinuteComparison:
    status: str
    security_id: str
    session_id: str
    phase: str
    start_utc_s: int
    end_utc_s: int
    matched_eligible_prints: int
    matched_quote_classified_prints: int
    bvc_gross_usd: str
    bvc_net_usd: str | None
    quote_eligible_gross: str
    quote_classified_gross: str
    quote_unknown_gross: str
    quote_coverage: str | None
    relative_gross_gap: str | None
    bvc_ratio: str | None
    quote_covered_ratio: str | None
    absolute_ratio_disagreement: str | None
    possible_quote_net_min: str
    possible_quote_net_max: str
    is_statistical_confidence_interval: bool
    input_digest: str
    knowledge_class: str = "ESTIMATOR_COMPARISON_NOT_TAPE_TRUTH"
    authority: dict[str,bool] = field(default_factory=lambda: dict(q.NO_AUTHORITY))


def _number(v: str,name: str) -> Decimal:
    if not isinstance(v,str) or len(v)>512:
        raise ValueError(name+"_invalid_numeric_encoding")
    try:
        d=Decimal(v)
    except (ValueError,InvalidOperation):
        raise ValueError(name+"_invalid_numeric_encoding") from None
    if not d.is_finite():
        raise ValueError(name+"_nonfinite")
    return d


def _s(d: Decimal) -> str:
    return "0" if not d else format(d.normalize(),"f")


def compare_minute(point: m.PressurePoint, tape: q.TapeResult, *, cutoff_ns: int,
                   policy: ComparisonPolicy=ComparisonPolicy()) -> MinuteComparison:
    """Match by complete true UTC minute, identity, phase and information cutoff.

    The notional tolerance detects obvious incompatible universes; passing it
    is NOT proof of aggregate-trade sale-condition or source rights parity.
    """
    if not isinstance(policy,ComparisonPolicy): raise ValueError("comparison_policy_required")
    policy.validate()
    if type(cutoff_ns) is not int or cutoff_ns<=0: raise ValueError("cutoff_invalid")
    m._validate_point(point)
    if not isinstance(tape,q.TapeResult):
        raise ValueError("quote_tape_result_required")
    if point.mode!=tape.mode: raise ValueError("mode_mismatch")
    if point.authority!=m.AUTHORITY or tape.authority!=q.NO_AUTHORITY:
        raise ValueError("authority_violation")
    if tape.knowledge_class!="QUOTE_REFERENCE_INFERRED_AGGRESSOR":
        raise ValueError("unrecognized_quote_reference")
    bar=point.bar
    if bar.end_utc_s*1_000_000_000>cutoff_ns:
        raise ValueError("late_bvc_bar")
    if (point.mode=="as_observed" and (bar.available_at_utc_s is None
            or bar.available_at_utc_s*1_000_000_000>cutoff_ns)):
        raise ValueError("late_bvc_availability")

    with localcontext() as ctx:
        ctx.prec=256
        observed=buy=sell=unknown=excluded=Decimal(0)
        selected=[]
        for d in tape.details:
            if not isinstance(d,q.TapeDetail):
                raise ValueError("invalid_tape_detail")
            gross=_number(d.trade_gross,"detail_gross")
            if gross<=0: raise ValueError("invalid_trade_gross")
            observed+=gross
            if d.sign is not None and (type(d.sign) is not int or d.sign not in (-1,1)):
                raise ValueError("invalid_quote_sign")
            if d.state in ("CANCELLED_PRINT","UNQUALIFIED_PRINT"):
                if d.sign is not None: raise ValueError("invalid_excluded_sign")
                excluded+=gross
            elif d.sign==1:
                if d.state not in ("QUOTE_BUY","MIDPOINT_TICK_BUY"):
                    raise ValueError("inconsistent_quote_sign")
                buy+=gross
            elif d.sign==-1:
                if d.state not in ("QUOTE_SELL","MIDPOINT_TICK_SELL"):
                    raise ValueError("inconsistent_quote_sign")
                sell+=gross
            else:
                unknown+=gross
            if (d.security_id==bar.security_id and
                d.session_id==bar.segment.session_id and
                d.phase==bar.segment.phase and
                bar.start_utc_s*1_000_000_000<=d.trade_event_ns<
                bar.end_utc_s*1_000_000_000):
                if d.monetary_basis != bar.basis_id:
                    raise ValueError("monetary_basis_mismatch")
                if d.trade_event_ns>cutoff_ns or (point.mode=="as_observed" and
                    (d.known_at_ns is None or d.known_at_ns>cutoff_ns)):
                    raise ValueError("late_tape_observation")
                selected.append((d,gross))
        eligible=buy+sell+unknown
        totals={"observed_gross":observed,"total_gross":eligible,
                "buyer_gross":buy,"seller_gross":sell,
                "unknown_gross":unknown,
                "excluded_or_unqualified_gross":excluded,
                "net_covered":buy-sell,
                "possible_full_net_min":buy-sell-unknown,
                "possible_full_net_max":buy-sell+unknown}
        if any(_number(getattr(tape,key),key)!=value for key,value in totals.items()):
            raise ValueError("tape_accounting_mismatch")
        if tape.coverage_fraction is not None:
            if eligible==0 or _number(tape.coverage_fraction,"coverage")!=(buy+sell)/eligible:
                raise ValueError("tape_accounting_coverage_mismatch")
        elif eligible>0:
            raise ValueError("tape_accounting_coverage_missing")

        b=s=u=Decimal(0)
        n=0
        for d,gross in selected:
            if d.state in ("CANCELLED_PRINT","UNQUALIFIED_PRINT"): continue
            n+=1
            if d.sign==1:b+=gross
            elif d.sign==-1:s+=gross
            else:u+=gross
        full=b+s+u
        classified=b+s
        base=Decimal(str(point.gross_usd))
        if base<0: raise ValueError("bvc_negative_gross")
        coverage=(classified/full) if full else None
        relative_gap=(abs(base-full)/max(base,full)) if max(base,full)>0 else None
        bvc_ratio=(Decimal(str(point.net_usd))/base) if (point.net_usd is not None and
                   point.directionally_usable and base>0) else None
        quote_ratio=((b-s)/classified) if classified else None
        status="COMPARABLE_PROXY_DIAGNOSTIC"
        if full==0:
            status="NO_ELIGIBLE_TAPE"
        elif coverage<Decimal(str(policy.min_quote_coverage)):
            status="QUOTE_COVERAGE_INSUFFICIENT"
        elif relative_gap is None or relative_gap>Decimal(str(policy.max_notional_gap)):
            status="GROSS_NOTIONAL_MISMATCH"
        elif bvc_ratio is None:
            status="BVC_DIRECTION_UNAVAILABLE"
        gap=abs(bvc_ratio-quote_ratio) if status=="COMPARABLE_PROXY_DIAGNOSTIC" else None
        return MinuteComparison(status,bar.security_id,bar.segment.session_id,
            bar.segment.phase,bar.start_utc_s,bar.end_utc_s,
            n,sum(d.sign is not None for d,g in selected
                  if d.state not in ("CANCELLED_PRINT","UNQUALIFIED_PRINT")),
            _s(base),_s(Decimal(str(point.net_usd))) if point.net_usd is not None else None,
            _s(full),_s(classified),_s(u),_s(coverage) if coverage is not None else None,
            _s(relative_gap) if relative_gap is not None else None,
            _s(bvc_ratio) if bvc_ratio is not None else None,
            _s(quote_ratio) if quote_ratio is not None else None,
            _s(gap) if gap is not None else None,
            _s(b-s-u),_s(b-s+u),False,
            m.digest({"point":asdict(point),
                      "matched_tape": [asdict(d) for d,g in selected],
                      "tape_mode":tape.mode,"tape_method":tape.knowledge_class,
                      "policy":asdict(policy),"cutoff_ns":cutoff_ns}))
