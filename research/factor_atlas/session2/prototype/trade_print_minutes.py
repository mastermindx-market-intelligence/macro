"""Pure S2 source-independent print-minute *candidate* geometry.

This is a deliberate SYNTHETIC_FIXTURE research kernel. It consumes the
incumbent quote_reference.TapeTrade shape, but NEVER authenticates its
trade conditions, corrections, source, venue, printed volume, identity,
session calendar, rights, knowledge vintage, or complete market coverage.

Does not read any tape or owner data, calculate BVC, emit m.Bar, select
revisions, replace engine.flow_signing, or enable production/trading.
A source-owner supplied actual dataset is deliberately NOT reduced here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from typing import Iterable

import pressure as m
import quote_reference as q
import source_preflight as sp

NANO=1_000_000_000
MINUTE_NS=60*NANO
SYNTHETIC="SYNTHETIC_FIXTURE"
UNVERIFIED="OWNER_UNVERIFIED"


@dataclass(frozen=True)
class PrintSelection:
    trade: q.TapeTrade
    updates_trade_ohlc: bool | None
    included_in_share_volume: bool | None


@dataclass(frozen=True)
class CandidatePrintMinute:
    security_id: str
    session_id: str
    phase: str
    start_utc_s: int
    end_utc_s: int
    prints_selected: int
    prints_withheld: int
    candidate_open: str | None
    candidate_high: str | None
    candidate_low: str | None
    candidate_close: str | None
    candidate_share_volume: str | None
    candidate_trade_gross_usd: str | None
    latest_known_at_ns: int | None
    refusals: tuple[str,...]
    prices_are_owner_admitted: bool=False
    consolidated_population_proven: bool=False


@dataclass(frozen=True)
class TradePrintMinuteReview:
    schema: str
    status: str
    mode: str
    input_class: str
    expected_cells: int
    observed_candidate_cells: int
    matched_print_cells: int
    only_withheld_cells: int
    absent_candidate_cells: int
    explicit_no_trade_cells: int
    minutes: tuple[CandidatePrintMinute,...]
    input_digest: str
    source_authenticated: bool=False
    canonical_pit_identity_admitted: bool=False
    share_volume_and_sale_conditions_admitted: bool=False
    pit_backtest_admitted: bool=False
    market_pilot_admitted: bool=False
    customer_publishable: bool=False
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _money(value: Decimal) -> str:
    return q._amount(value)


def reconstruct_print_minutes(
    selections: Iterable[PrintSelection], *,
    scope: sp.IntakeScope, mode: str="as_observed",
    input_class: str=SYNTHETIC
) -> TradePrintMinuteReview:
    """Reduce only synthetic owner-shaped, already selected eligible prints.

    This method is never a source owner or a real-market decoder. Even
    caller-asserted sale conditions and revision/rights IDs are UNVERIFIED.
    No missing print or unselected revision is converted into observed zero.
    """
    segments=sp._scope(scope)
    if mode not in ("as_observed","corrected_history"):
        raise ValueError("invalid_reconstruction_mode")
    if input_class not in (SYNTHETIC,UNVERIFIED):
        raise ValueError("input_class_not_admitted")
    expected=len(scope.securities)*sum(
        (seg.end_utc_s-seg.start_utc_s)//60 for seg in segments)
    if input_class!=SYNTHETIC:
        # Never consume an actual unadmitted tape or reflect its prices.
        return TradePrintMinuteReview(
            "factor_atlas.trade_print_minutes.research_v1",
            "SOURCE_UNVERIFIED_NOT_REDUCED",mode,input_class,
            expected,0,0,0,expected,0,(),
            m.digest({"scope":asdict(scope),"mode":mode,"input_class":input_class}))
    rows=tuple(selections)
    if len(rows)>100_000:
        raise ValueError("bounded_print_sample_required")
    bucket=defaultdict(list)
    seen=set()
    for rec in rows:
        if not isinstance(rec,PrintSelection):
            raise ValueError("original_selected_print_shape_required")
        if any(type(v) not in (bool,type(None)) for v in
               (rec.updates_trade_ohlc,rec.included_in_share_volume)):
            raise ValueError("eligibility_boolean_required")
        t=rec.trade
        if not isinstance(t,q.TapeTrade):
            raise ValueError("original_tape_trade_shape_required")
        q._integer(t.sip_ns,"trade_sip")
        if t.sip_ns>scope.cutoff_utc_ns:
            continue
        if mode=="as_observed" and t.available_ns is not None and t.available_ns>scope.cutoff_utc_ns:
            continue
        with localcontext() as ctx:
            ctx.prec=256
            price,size=q._trade(t,mode)
        if t.security_id not in scope.securities:
            raise ValueError("outside_owner_security_scope")
        minute_start_s=(t.sip_ns//MINUTE_NS)*60
        matching=next((s for s in segments
                        if s.start_utc_s<=minute_start_s
                        and minute_start_s+60<=s.end_utc_s
                        and s.session_id==t.session_id
                        and s.phase==t.phase),None)
        if matching is None:
            raise ValueError("outside_owner_calendar")
        key=(t.security_id,t.session_id,t.trade_id)
        if key in seen:
            raise ValueError("duplicate_trade_needs_original_selector")
        seen.add(key)
        bucket[(t.security_id,matching,minute_start_s)].append((rec,price,size))
    minutes=[]
    docs=[]
    for (security,seg,start),candidates in sorted(
            bucket.items(),key=lambda x:(x[0][0],x[0][2],x[0][1].phase)):
        candidates.sort(key=lambda item:(item[0].trade.sip_ns,item[0].trade.trade_id))
        docs.extend(asdict(item[0]) for item in candidates)
        selected=[]
        refusals=set()
        withheld=0
        for rec,price,size in candidates:
            t=rec.trade
            if rec.updates_trade_ohlc is None or rec.included_in_share_volume is None:
                refusals.add("OWNER_ELIGIBILITY_UNKNOWN")
            elif rec.updates_trade_ohlc is not True or rec.included_in_share_volume is not True:
                refusals.add("PRINT_NOT_IN_MATCHED_OHLC_VOLUME_POPULATION")
            elif t.condition_state!="ELIGIBLE":
                refusals.add("SALE_CONDITION_NOT_QUALIFIED")
            elif t.correction_state!="CURRENT":
                refusals.add("SOURCE_CORRECTION_NOT_SELECTED")
            elif t.venue!="LIT":
                refusals.add("TRF_ALIGNMENT_UNPROVEN")
            else:
                selected.append((t,price,size))
                continue
            withheld+=1
        if selected:
            prices=[p for _,p,_ in selected]
            total_shares=sum((z for _,_,z in selected),Decimal(0))
            total_gross=sum((p*z for _,p,z in selected),Decimal(0))
            earliest=selected[0][0].sip_ns
            latest=selected[-1][0].sip_ns
            opening={p for t,p,z in selected if t.sip_ns==earliest}
            closing={p for t,p,z in selected if t.sip_ns==latest}
            if len(opening)!=1 or len(closing)!=1:
                refusals.add("EVENT_ORDER_NOT_PROVEN")
            open_price=_money(next(iter(opening))) if len(opening)==1 else None
            close_price=_money(next(iter(closing))) if len(closing)==1 else None
            low=_money(min(prices))
            high=_money(max(prices))
            shares=_money(total_shares)
            gross=_money(total_gross)
            known=max(t.available_ns for t,p,z in selected) if mode=="as_observed" else None
        else:
            open_price=close_price=low=high=shares=gross=known=None
        minutes.append(CandidatePrintMinute(
            security,seg.session_id,seg.phase,start,start+60,
            len(selected),withheld,open_price,high,low,close_price,
            shares,gross,known,tuple(sorted(refusals))))
    return TradePrintMinuteReview(
        "factor_atlas.trade_print_minutes.research_v1",
        "SYNTHETIC_PRINT_SAMPLE_NOT_ADMITTED",mode,input_class,
        expected,len(minutes),
        sum(z.prints_selected>0 for z in minutes),
        sum(z.prints_selected==0 for z in minutes),
        expected-len(minutes),0,tuple(minutes),
        m.digest({"scope":asdict(scope),"mode":mode,"selected_source_shape":docs}))
