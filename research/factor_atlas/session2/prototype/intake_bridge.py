"""Research-only S2-P2 bridge from source-shaped metadata to existing BVC/window math.

Only SYNTHETIC_FIXTURE records can enter the arithmetic preview. Any owner-
unverified market-shaped inputs return preflight evidence only, even if their
self-asserted source hashes/entitlement/basis labels look complete.

No I/O, provider/reader capture, entitlement lookup, revision selection, source
admission, membership registry, signed tape, customer output or trading actions.
Real admitted cohorts still require an incumbent-owner caller/receiver contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

import pressure as m
import source_preflight as sp
import window_pressure as wp

NANO=1_000_000_000
_SYNTHETIC="SYNTHETIC_FIXTURE"
_UNVERIFIED="OWNER_UNVERIFIED"


@dataclass(frozen=True)
class MinuteEnvelope:
    claim: sp.MinuteClaim
    close: float
    volume: float
    vwap: float | None


@dataclass(frozen=True)
class IntakePreview:
    status: str
    stage: str
    source_quality: str
    input_class: str
    preflight: sp.Preflight
    normalized_bar_count: int
    earliest_bar_available_utc_s: int | None
    latest_bar_available_utc_s: int | None
    window: wp.WindowPressure | None
    source_authenticated: bool
    source_rights_verified: bool
    market_pilot_admitted: bool
    may_execute_market_pilot: bool
    customer_publishable: bool
    knowledge_class: str
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _unadmitted(stage: str, observed: sp.Preflight,
                input_class: str, inputs_digest: str) -> IntakePreview:
    return IntakePreview(
        "NOT_ADMITTED",stage,"NOT_ADMITTED",input_class,
        observed,0,None,None,None,False,False,False,False,False,
        "SYNTHETIC_SOURCE_SHAPED_PREVIEW_NOT_MARKET_MEASUREMENT",
        inputs_digest)


def preview_intake(scope: sp.IntakeScope, records: Iterable[MinuteEnvelope],
                   memberships: Sequence[m.Membership], *,
                   config: m.BVCConfig, start_utc_s: int, end_utc_s: int,
                   cutoff_utc_ns: int,
                   input_class: str = _SYNTHETIC) -> IntakePreview:
    """Preview only fabricated geometry after complete metadata checks.

    The owner must authenticate actual retained bytes, licensing, basis and
    availability separately; no untrusted string can switch source admission.
    """
    if input_class not in (_SYNTHETIC,_UNVERIFIED):
        raise ValueError("input_class_not_admitted")
    if not isinstance(scope,sp.IntakeScope):
        raise ValueError("owner_scope_required")
    if not isinstance(config,m.BVCConfig):
        raise ValueError("bvc_config_required")
    config.validate()
    sp._timestamp(cutoff_utc_ns,"cutoff")
    m._integer(start_utc_s,"start")
    m._integer(end_utc_s,"end")
    if not start_utc_s<end_utc_s:
        raise ValueError("invalid_window")
    if not isinstance(memberships,(tuple,list)) or not memberships:
        raise ValueError("memberships_required")
    for group in memberships:
        if not isinstance(group,m.Membership):
            raise ValueError("membership_required")
        if group.basis!="point_in_time":
            raise ValueError("membership_requires_point_in_time")
        if any(s not in scope.securities for s in group.member_ids):
            raise ValueError("member_outside_intake")
    items=tuple(records)
    if any(not isinstance(x,MinuteEnvelope) for x in items):
        raise ValueError("minute_envelope_required")
    if any(not isinstance(x.claim,sp.MinuteClaim) for x in items):
        raise ValueError("owner_claim_required")
    checked_scope=replace(scope,cutoff_utc_ns=cutoff_utc_ns)
    pre=sp.preflight(checked_scope,(x.claim for x in items))
    stamp={"scope":asdict(checked_scope),"preflight_digest":pre.input_digest,
           "input_class":input_class,"start":start_utc_s,"end":end_utc_s,
           "cutoff":cutoff_utc_ns,"membership":[asdict(g) for g in
                   sorted(memberships,key=lambda g:g.factor_id)],
           "estimator":config.identity}
    if input_class!=_SYNTHETIC:
        return _unadmitted("OWNER_ADMISSION_REQUIRED",pre,input_class,m.digest(stamp))
    if not pre.metadata_complete:
        return _unadmitted("INCOMPLETE_OR_UNPROVEN_INTAKE",pre,input_class,m.digest(stamp))

    max_end=max(s.end_utc_s for s in scope.segments)
    inside=[x for x in items if x.claim.start_utc_s<max_end]
    cutoff_s=cutoff_utc_ns//NANO
    ordered=sorted(inside,key=lambda x:(x.claim.security_id,x.claim.start_utc_s))
    bars=[]
    for record in ordered:
        c=record.claim
        if type(record.volume) not in (int,float) or type(record.close) not in (int,float):
            raise ValueError("bar_numeric_required")
        if c.value_state=="PRESENT" and record.volume==0:
            raise ValueError("present_zero_requires_explicit_zero_state")
        if c.value_state=="EXPLICIT_ZERO_VOLUME" and record.volume!=0:
            raise ValueError("explicit_zero_state_mismatch")
        known_ns=max(c.source_receipt_utc_ns,c.reader_completed_utc_ns)
        known_s=(known_ns+NANO-1)//NANO
        native=m.Bar(c.security_id,c.segment,c.start_utc_s,c.end_utc_s,
                     known_s,record.close,record.volume,record.vwap,
                     c.basis_id,c.source_revision_ref,c.rights_ref)
        m._validate_bar(native)
        bars.append(native)
    stamp["synthetic_bars"]=[asdict(x) for x in bars]
    fingerprint=m.digest(stamp)
    if any(x.available_at_utc_s>cutoff_s for x in bars):
        return _unadmitted("CUTOFF_PRECISION_WITHHELD",pre,input_class,fingerprint)
    result=wp.measure_windows(bars,memberships,scope.segments,
                               start_utc_s=start_utc_s,end_utc_s=end_utc_s,
                               cutoff_utc_s=cutoff_s,config=config,
                               mode="as_observed")
    if result.authority!=m.AUTHORITY:
        raise ValueError("window_authority_mismatch")
    return IntakePreview(
        "NOT_ADMITTED","SYNTHETIC_WINDOW_PREVIEW","NOT_ADMITTED",input_class,
        pre,len(bars),min((b.available_at_utc_s for b in bars),default=None),
        max((b.available_at_utc_s for b in bars),default=None),
        result,False,False,False,False,False,
        "SYNTHETIC_SOURCE_SHAPED_PREVIEW_NOT_MARKET_MEASUREMENT",
        fingerprint)
