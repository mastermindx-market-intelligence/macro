"""Pure quote-reference research, not aggressor truth or a new market-data owner.

Consumes incumbent-owner qualified prints/quotes; no IO, entitlement, calendar,
revision resolution, source-capture or publication. SIP nanosecond clocks stay
integers. Previous engine.flow_signing is the production calibration owner.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from typing import Iterable
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
NO_AUTHORITY = dict(may_publish=False,may_trade=False,may_rank=False,may_alert=False,may_size=False)

@dataclass(frozen=True)
class TapeTrade:
    security_id: str
    trade_id: str
    session_id: str
    phase: str
    sip_ns: int
    available_ns: int | None
    price: str
    decimal_size: str
    condition_state: str
    revision_ref: str
    rights_ref: str
    basis: str
    venue: str
    correction_state: str

@dataclass(frozen=True)
class TapeQuote:
    security_id: str
    session_id: str
    phase: str
    sip_ns: int
    available_ns: int | None
    bid: str
    ask: str
    bid_size: str
    ask_size: str
    condition_state: str
    revision_ref: str
    rights_ref: str
    basis: str

@dataclass(frozen=True)
class QuotePolicy:
    max_age_ns: int = 1_000_000_000
    midpoint_policy: str = "unknown"

    def validate(self) -> None:
        if type(self.max_age_ns) is not int or not 0 < self.max_age_ns <= 60_000_000_000:
            raise ValueError("invalid_quote_age")
        if self.midpoint_policy not in ("unknown","tick"):
            raise ValueError("invalid_midpoint_policy")

@dataclass(frozen=True)
class TapeDetail:
    trade_id: str
    security_id: str
    session_id: str
    phase: str
    trade_event_ns: int
    trade_gross: str
    sign: int | None
    state: str
    quote_event_ns: int | None
    quote_age_ns: int | None
    known_at_ns: int | None
    source_trade_revision: str
    source_quote_revision: str | None

@dataclass(frozen=True)
class TapeResult:
    mode: str
    knowledge_class: str
    observed_gross: str
    total_gross: str
    buyer_gross: str
    seller_gross: str
    unknown_gross: str
    excluded_or_unqualified_gross: str
    net_covered: str
    possible_full_net_min: str
    possible_full_net_max: str
    coverage_fraction: str | None
    details: tuple[TapeDetail,...]
    authority: dict[str,bool] = field(default_factory=lambda: dict(NO_AUTHORITY))

def _integer(v: object,name: str) -> int:
    if type(v) is not int or v <= 0:
        raise ValueError(name + "_invalid_timestamp")
    return v

def _identity(v: object,name: str) -> str:
    if not isinstance(v,str) or not v or len(v)>256:
        raise ValueError(name+"_invalid_identity")
    return v

def _decimal(v: object,name: str) -> Decimal:
    if not isinstance(v,str) or len(v)>80:
        raise ValueError(name+"_decimal_string_required")
    try:
        d=Decimal(v)
    except (InvalidOperation,ValueError,OverflowError):
        raise ValueError(name+"_invalid_decimal") from None
    if not d.is_finite() or d<=0 or not -20 <= d.adjusted() <= 15:
        raise ValueError(name+"_invalid_decimal")
    return d

def _amount(v: Decimal) -> str:
    return "0" if not v else format(v.normalize(),"f")

def _common(v: TapeTrade|TapeQuote,mode: str) -> None:
    _identity(v.security_id,"security")
    _identity(v.revision_ref,"revision")
    _identity(v.rights_ref,"rights")
    _identity(v.session_id,"session")
    _integer(v.sip_ns,"sip")
    try:
        day=datetime.fromtimestamp(v.sip_ns//1_000_000_000,timezone.utc).astimezone(ET).date().isoformat()
    except (ValueError,OverflowError,OSError):
        raise ValueError("invalid_event_clock") from None
    if day!=v.session_id:
        raise ValueError("event_session_mismatch")
    if v.phase not in ("PRE","RTH","AH"):
        raise ValueError("invalid_phase")
    if v.basis!="unadjusted/USD" and not v.basis.startswith("unadjusted/USD/"):
        raise ValueError("unproven_monetary_basis")
    if v.available_ns is None:
        if mode=="as_observed": raise ValueError("first_known_unavailable")
    elif _integer(v.available_ns,"first_known")<v.sip_ns:
        raise ValueError("receipt_before_source_event")

def _trade(t: TapeTrade,mode: str) -> tuple[Decimal,Decimal]:
    _common(t,mode)
    _identity(t.trade_id,"trade_id")
    if t.condition_state not in ("ELIGIBLE","UNKNOWN","EXCLUDED"):
        raise ValueError("unresolved_trade_conditions")
    if t.correction_state not in ("CURRENT","CANCELLED","UNRESOLVED"):
        raise ValueError("unresolved_corrections")
    if t.venue not in ("LIT","TRF"):
        raise ValueError("unresolved_venue")
    return _decimal(t.price,"price"),_decimal(t.decimal_size,"decimal_size")

def _valid_quote(q: TapeQuote) -> tuple[bool,Decimal|None,Decimal|None]:
    if q.condition_state!="ELIGIBLE": return False,None,None
    try:
        bid=_decimal(q.bid,"bid"); ask=_decimal(q.ask,"ask")
        _decimal(q.bid_size,"bid_size"); _decimal(q.ask_size,"ask_size")
    except ValueError:
        return False,None,None
    return (bid<ask),bid,ask

def _classify_tape_impl(trades: Iterable[TapeTrade], quotes: Iterable[TapeQuote],
                        policy: QuotePolicy, *, cutoff_ns: int,
                        mode: str="as_observed") -> TapeResult:
    """Compare eligible transaction prices with strictly past SIP NBBO.

    Equal-timestamp quote/order ambiguity and missing data withhold direction.
    An estimated net-dollar bound covers only eligible observed prints.
    Source/right/condition declarations are caller claims, not attestation.
    """
    if not isinstance(policy,QuotePolicy): raise ValueError("quote_policy_required")
    policy.validate(); _integer(cutoff_ns,"cutoff")
    if mode not in ("as_observed","corrected_history"):
        raise ValueError("invalid_mode")
    book:dict[tuple,list[TapeQuote]]=defaultdict(list)
    seen_q=set()
    for q in quotes:
        if not isinstance(q,TapeQuote): raise ValueError("quote_record_required")
        _integer(q.sip_ns,"quote_sip")
        if q.sip_ns>cutoff_ns: continue
        if mode=="as_observed" and (q.available_ns is None or q.available_ns>cutoff_ns):
            continue
        _common(q,mode)
        key=(q.security_id,q.session_id,q.phase,q.basis)
        occurrence=key+(q.sip_ns,)
        if occurrence in seen_q: raise ValueError("duplicate_quote_needs_revision_selection")
        seen_q.add(occurrence)
        book[key].append(q)
    clocks={}
    for key,rows in book.items():
        rows.sort(key=lambda x:x.sip_ns)
        clocks[key]=[x.sip_ns for x in rows]
    selected=[]; seen_t=set()
    for t in trades:
        if not isinstance(t,TapeTrade): raise ValueError("trade_record_required")
        _integer(t.sip_ns,"trade_sip")
        if t.sip_ns>cutoff_ns: continue
        if mode=="as_observed" and t.available_ns is not None and t.available_ns>cutoff_ns:
            continue
        price,shares=_trade(t,mode)
        unique=(t.security_id,t.session_id,t.trade_id)
        if unique in seen_t: raise ValueError("duplicate_trade_needs_revision_selection")
        seen_t.add(unique)
        selected.append((t,price,shares))
    selected.sort(key=lambda p:(p[0].sip_ns,p[0].security_id,p[0].trade_id))
    buy=sell=unknown=excluded=observed=Decimal(0)
    previous:dict[tuple,tuple[int,Decimal]]={}
    details=[]
    for t,price,shares in selected:
        gross=price*shares
        observed+=gross
        state=""; sign=None; q=None; age=None
        known=t.available_ns if mode=="as_observed" else None
        if t.correction_state=="CANCELLED":
            state="CANCELLED_PRINT";excluded+=gross
        elif t.condition_state!="ELIGIBLE" or t.correction_state!="CURRENT":
            state="UNQUALIFIED_PRINT";excluded+=gross
        elif t.venue=="TRF":
            state="TRF_ALIGNMENT_UNPROVEN";unknown+=gross
        else:
            scope=(t.security_id,t.session_id,t.phase,t.basis)
            idx=bisect_right(clocks.get(scope,[]),t.sip_ns)-1
            if idx<0:
                state="NO_PRECEDING_QUOTE"
            else:
                q=book[scope][idx]
                age=t.sip_ns-q.sip_ns
                if mode=="as_observed":known=max(t.available_ns,q.available_ns)
                if age==0:
                    state="EQUAL_TIMESTAMP_AMBIGUOUS"
                elif age>policy.max_age_ns:
                    state="STALE_QUOTE"
                else:
                    valid,bid,ask=_valid_quote(q)
                    if not valid:
                        state="INVALID_QUOTE"
                    elif price>(bid+ask)/2:
                        state="QUOTE_BUY";sign=1
                    elif price<(bid+ask)/2:
                        state="QUOTE_SELL";sign=-1
                    elif policy.midpoint_policy=="tick":
                        prior=previous.get(scope)
                        if prior is None or prior[0]>=t.sip_ns or prior[1]==price:
                            state="MIDPOINT_NO_TICK"
                        else:
                            sign=1 if price>prior[1] else -1
                            state="MIDPOINT_TICK_BUY" if sign>0 else "MIDPOINT_TICK_SELL"
                    else:
                        state="AT_MIDPOINT_UNCLASSIFIED"
            if sign is None:unknown+=gross
            elif sign==1:buy+=gross
            else:sell+=gross
            previous[scope]=(t.sip_ns,price)
        details.append(TapeDetail(t.trade_id,t.security_id,t.session_id,t.phase,
                    t.sip_ns,_amount(gross),sign,state,
                    q.sip_ns if q else None,age,known,t.revision_ref,
                    q.revision_ref if q else None))
    eligible=buy+sell+unknown;net=buy-sell
    if observed!=eligible+excluded or abs(net)>eligible:
        raise ValueError("tape_accounting_invalid")
    return TapeResult(mode,"QUOTE_REFERENCE_INFERRED_AGGRESSOR",
                      _amount(observed),_amount(eligible),_amount(buy),
                      _amount(sell),_amount(unknown),_amount(excluded),
                      _amount(net),_amount(net-unknown),_amount(net+unknown),
                      _amount((buy+sell)/eligible) if eligible else None,
                      tuple(details))


def classify_tape(trades: Iterable[TapeTrade], quotes: Iterable[TapeQuote],
                  policy: QuotePolicy, *, cutoff_ns: int,
                  mode: str="as_observed") -> TapeResult:
    """Bound arithmetic so decimal-size and midpoint precision survive parsing.

    Input magnitude and length are checked by the pure kernel. Local precision
    avoids altering any shared/global DecimalContext used by incumbent engines.
    """
    with localcontext() as ctx:
        ctx.prec=256
        return _classify_tape_impl(trades,quotes,policy,cutoff_ns=cutoff_ns,mode=mode)
