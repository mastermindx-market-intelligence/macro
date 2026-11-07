"""R4 RESEARCH-ONLY cohort/label semantics, never a production admission owner.

These pure functions test proposed rules against curated audit cases. They do not
acquire sources, mint canonical identities, fit a forecast, choose investments or
persist state. Calendar-day views do not prove intraday availability. Source rights,
identity, first-disclosure search coverage and source correction adjudication remain
with incumbent owners. The intentionally exposed historical sample is not unbiased.
"""
from calendar import monthrange
import hashlib
import json
from typing import Any, Mapping, Sequence

from resources_catalyst_r1_reference import nonnegative
from resources_catalyst_r3_capital import _day, _unique

_ENROLLMENT_FIELDS = frozenset({
    'observation_key','project_key','issuer_key','claim_key','source_ref','known_on',
    'effective_lower','effective_upper','listing_venue','primary_product',
    'stage_kind','prior_stage_entry',
})
_STRATA = {
    'FINANCING_ATTEMPT':'financing_attempt',
    'BUILD_APPROVED':'construction_decision',
    'BUILD_CONDITIONAL':'conditional_build',
    'EARLY_WORKS':'preparatory_observation',
    'CONTINUED_CONSTRUCTION':'prevalent_build_observation',
}
_EVENT_FIELDS = frozenset({
    'id','project_key','source_ref','target','kind','lower','upper','known_on','recorded_on',
})


def _text(value: Any) -> str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError('nonempty_text_required')
    return value


def screen_observation(row: Mapping[str,Any]) -> dict[str,Any]:
    """Scope screen for a proposed 2018-2022 TSX/TSXV gold disclosure study.

    A match is an observed landmark, NOT proof of first incident entry. Unknowns
    remain explicit. There is no outcome, future price or optional-options argument.
    The fixed column allowlist is a test seam, not a new corporate source schema.
    """
    if set(row)!=_ENROLLMENT_FIELDS: raise ValueError('enrollment_field_boundary')
    for key in ('observation_key','project_key','issuer_key','claim_key','source_ref'):
        _text(row[key])
    kind=row['stage_kind']
    if kind not in _STRATA: raise ValueError('unrecognized_stage')
    prior=row['prior_stage_entry']
    if prior is not None and type(prior) is not bool: raise ValueError('prior_entry_boolean')
    known,lo,hi=map(_day,(row['known_on'],row['effective_lower'],row['effective_upper']))
    if lo>hi: raise ValueError('inverted_date_interval')
    venue=row['listing_venue']; product=row['primary_product']
    for v in (venue,product):
        if v is not None: _text(v)
    start,end=_day('2018-01-01'),_day('2022-12-31')
    scope='MATCHED_OBSERVATION';reason='within_observed_scope'
    if hi<start or lo>end or known<start or known>end:
        scope,reason='OUT_OF_SCOPE','outside_occurrence_or_publication_window'
    elif venue is not None and venue not in {'TSX','TSXV'}:
        scope,reason='OUT_OF_SCOPE','different_listing_venue'
    elif product is not None and product!='gold':
        scope,reason='OUT_OF_SCOPE','different_primary_product'
    elif venue is None or product is None:
        scope,reason='UNRESOLVED','listing_or_product_unknown'
    elif lo<start or hi>end or hi>known:
        scope,reason='UNRESOLVED','date_scope_or_observation_not_qualified'
    incident='UNVERIFIED' if prior is None else ('PREVALENT' if prior else 'CANDIDATE_INCIDENT')
    return dict(scope=scope,stratum=_STRATA[kind],incident=incident,reason=reason,
                production_admission=False)


def enrollment_fingerprint(rows: Sequence[Mapping[str,Any]]) -> str:
    """Digest only the bounded enrollment input, never a labels/performance sidecar.

    A hash checks byte/semantic continuity, not blindness, coverage or provenance.
    """
    if not rows: raise ValueError('empty_enrollment')
    for row in rows: screen_observation(row)
    keys=[r['observation_key'] for r in rows]
    if len(set(keys))!=len(keys): raise ValueError('duplicate_observation')
    payload=json.dumps(sorted(rows,key=lambda r:r['observation_key']),
                       sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def horizon_date(start: str, months: int) -> str:
    """Calendar-month anniversary; clamp invalid month-end to that month's last day."""
    day=_day(start)
    if type(months) is not int or months<1: raise ValueError('positive_integer_months')
    years,m=divmod(day.month-1+months,12);year=day.year+years;month=m+1
    if year>9999: raise ValueError('horizon_out_of_range')
    return day.replace(year=year,month=month,day=min(day.day,monthrange(year,month)[1])).isoformat()


def milestone_at_horizon(
    events: Sequence[Mapping[str,Any]], target: str, start: str, months: int,
    label_asof: str, *, project_key: str, mode: str='public_reconstruction',
) -> dict[str,Any]:
    """First-attainment label, not sustained operation or original-claim total return.

    Relevant owner-resolved sources must describe FIRST attainment or an exact
    'not yet attained' observation. Date intervals are retained, never midpointed.
    A later first-attainment report may establish a past label, but cannot become
    an earlier feature: label_asof is explicitly distinct from a forecast cutoff.
    Conflicting assertions require source-owner adjudication, not latest-wins.
    No-event absence alone gives UNKNOWN. Public reconstruction != system replay.
    """
    _text(project_key);_text(target)
    if mode not in {'public_reconstruction','system_replay'}: raise ValueError('unknown_time_mode')
    begin,cut,h=map(_day,(start,label_asof,horizon_date(start,months)))
    if cut<begin: raise ValueError('label_cutoff_before_entry')
    _unique(events)
    first=[];not_yet=[];refs=[]
    for e in events:
        if set(e)!=_EVENT_FIELDS: raise ValueError('event_field_boundary')
        for k in ('source_ref','target','project_key'): _text(e[k])
        if e['project_key']!=project_key: raise ValueError('different_project')
        if e['kind'] not in {'attained_first','not_yet'}: raise ValueError('unqualified_label_kind')
        lo,hi,known=map(_day,(e['lower'],e['upper'],e['known_on']))
        recorded=None if e['recorded_on'] is None else _day(e['recorded_on'])
        if lo>hi or hi>known: raise ValueError('invalid_observed_time_interval')
        if e['kind']=='not_yet' and lo!=hi: raise ValueError('exact_not_yet_date_required')
        if e['target']!=target or known>cut: continue
        if mode=='system_replay' and (recorded is None or recorded>cut): continue
        refs.append(e['source_ref'])
        (first if e['kind']=='attained_first' else not_yet).append((lo,hi))
    state='PENDING' if cut<h else 'UNKNOWN';value=None
    lower=upper=None
    if first:
        lower=max(x[0] for x in first);upper=min(x[1] for x in first)
        if not_yet:
            last_negative=max(x[0] for x in not_yet)
            from datetime import timedelta
            lower=max(lower,last_negative+timedelta(days=1))
        if lower>upper: state='CONFLICT'
        elif upper<=begin: state='PRE_ENTRY_ATTAINMENT'
        elif lower<=begin: state='AMBIGUOUS_ENTRY'
        elif upper<=h: state,value='ACHIEVED',True
        elif lower>h: state,value='NOT_ACHIEVED_BY_HORIZON',False
        else: state='INTERVAL_STRADDLES_HORIZON'
    elif not_yet and max(x[0] for x in not_yet)>=h:
        state,value='NOT_ACHIEVED_BY_HORIZON',False
    return dict(state=state,value=value,target=target,project_key=project_key,
                horizon=h.isoformat(),label_asof=cut.isoformat(),time_mode=mode,
                admissible_sources=sorted(set(refs)),
                first_interval=None if lower is None or lower>upper else [lower.isoformat(),upper.isoformat()],
                event_probability=None,expected_return=None,can_rank=False)


def settlement_value(ratio: Any, successor_price: Any, cash_per_old_share: Any,
                     cash_currency: str, price_currency: str) -> str|None:
    """Conditional gross value per old share, not historical P&L or fair value.

    Caller must separately prove completed settlement, whole-share units, actual
    currency/price date and rights. No FX, missing-price, fee, dividend or tax default
    is invented. A future forecast price does not become realized settlement value.
    """
    if _text(cash_currency)!=_text(price_currency): raise ValueError('unbound_fx')
    if ratio is None or cash_per_old_share is None: return None
    r,c=map(nonnegative,(ratio,cash_per_old_share))
    if successor_price is None: return str(c) if r==0 else None
    p=nonnegative(successor_price)
    return str(r*p+c)


def audit_summary(rows: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    """Describe this purposeful audit, never infer a universe success rate."""
    digest=enrollment_fingerprint(rows)
    return dict(observations=len(rows),projects=len({r['project_key'] for r in rows}),
                issuers=len({r['issuer_key'] for r in rows}),claims=len({r['claim_key'] for r in rows}),
                sources=len({r['source_ref'] for r in rows}),enrollment_sha256=digest,
                sampling_design='RETROSPECTIVE_PURPOSEFUL_AUDIT',
                population_success_rate=None,empirically_qualified=False,can_rank=False)
