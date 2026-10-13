"""Derived Defense read model over inputs qualified by their existing owners.

This module does not acquire sources, admit data, resolve identities, calculate
financial values, or grant display rights. The trusted producer supplies owner
views after its owner schema/receipt/rights checks. HTTP input is not an owner
view. Structure checks here are additional safeguards, never authentication.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, date
from hashlib import sha256
import json
import math
import re
from lib import nyse_calendar
from engine.government_revenue.defense_interpretation import validate_defense_interpretation

CONTRACT = 'defense_economics.v1'
AXES = ('participation', 'demand', 'economics', 'recognition')
COHORT = ('LMT', 'RTX', 'NOC', 'LHX')
STATES = frozenset({'supported','partial','stale','missing_owner','unreviewed',
                    'contradictory','not_comparable','unavailable'})
AUTHORITY = dict(context_only=True, can_rank=False, can_size=False, can_gate=False,
                 can_originate_signal=False, can_escalate=False)
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _instant(value):
    if not isinstance(value, str):
        raise ValueError('clock must be an ISO instant')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('clock must include timezone')
    return result


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def _text(value):
    return value if isinstance(value, str) and len(value) <= 2000 else None


def _missing(reason, *, state='missing_owner'):
    return dict(state=state, summary_en='Required evidence is unavailable.',
                summary_zh='所需证据暂不可用。', owner_ref=None, evidence_refs=[],
                observed_at=None, fiscal_period=None, reason_code=reason,
                facts=[], limitations=[reason])


def _bound(ref, bindings):
    return isinstance(ref, str) and ref in bindings


def _fact(fact, bindings, subject):
    if not isinstance(fact, Mapping):
        raise ValueError('fact must be an owner-projected mapping')
    needed = ('fact_id','value','unit','period','accounting_basis','fact_class',
              'owner_ref','source_span')
    if any(fact.get(k) is None for k in needed) or not _bound(fact['owner_ref'], bindings):
        raise ValueError('financial fact lacks basis/period/unit/source binding')
    if any(not isinstance(fact[k],str) or not fact[k] or len(fact[k])>256 for k in ('fact_id','unit','period','accounting_basis','fact_class')):
        raise ValueError('fact_fields_invalid')
    if fact['fact_class'] not in {'reported_segment_sales','reported_segment_operating_profit','reported_segment_margin','reported_backlog','reported_guidance','reported_cashflow','reported_eac','reported_shareholder_terms','reported_financing','company_forward','derived_scenario'}:
        raise ValueError('fact_class_unsupported')
    span = fact['source_span']
    if not isinstance(span, Mapping) or span.get('receipt_state') != 'byte_replayed':
        raise ValueError('financial source span is not replayable')
    if not _SHA.fullmatch(str(span.get('text_sha256',''))) or not span.get('document_id'):
        raise ValueError('financial source span lacks document/hash')
    value = fact['value']
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('fact value is not a finite owner value')
    if isinstance(value, str) and len(value)>2000:
        raise ValueError('fact_value_too_long')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite financial value')
    binding = bindings[fact['owner_ref']]
    if any(binding.get(k) != subject.get(k) for k in ('issuer_id','security_id')) or fact['period'] not in binding.get('periods',[]):
        raise ValueError('fact_subject_or_period_mismatch')
    if binding.get('owner_family') != 'company_intelligence':
        raise ValueError('government money is not an issuer financial fact')
    if fact['fact_class'] == 'observed_market_expectation':
        raise ValueError('observed expectations require separate owner qualification')
    if fact.get('derived'):
        denominator = fact.get('denominator')
        numerator = fact.get('numerator')
        if not isinstance(numerator, Mapping) or not isinstance(denominator, Mapping) or any(
            denominator.get(k) != numerator.get(k) or numerator.get(k) is None
            for k in ('period','unit','accounting_basis')
        ) or any(not _bound(v.get('owner_ref'), bindings) for v in (numerator, denominator)):
            raise ValueError('derived figure lacks comparable owner denominator')
        for operand in (numerator,denominator):
            ref = bindings[operand['owner_ref']]
            operand_value=operand.get('value')
            if isinstance(operand_value,bool) or not isinstance(operand_value,(int,float)) or not math.isfinite(operand_value):
                raise ValueError('operand_value_invalid')
            if any(ref.get(k) != subject.get(k) for k in ('issuer_id','security_id')) or operand['period'] not in ref.get('periods',[]):
                raise ValueError('operand_subject_or_period_mismatch')
    fields = ('fact_id','value','unit','period','accounting_basis','fact_class',
              'owner_ref','derived','numerator','denominator')
    result = {k:deepcopy(fact[k]) for k in fields if k in fact and k not in ('numerator','denominator')}
    for name in ('numerator','denominator'):
        if name in fact:
            operand = fact[name]
            if not isinstance(operand, Mapping):
                raise ValueError('invalid_operand')
            result[name] = {k:deepcopy(operand[k]) for k in
                ('fact_id','value','unit','period','accounting_basis','owner_ref') if k in operand}
    result['source_span'] = {k:deepcopy(span[k]) for k in
        ('receipt_state','text_sha256','document_id','span_id','source_url') if k in span}
    return result


def _valid_binding_fields(ref):
    # These fields quote already-qualified owner receipt metadata; presence is
    # not source, identity, rights or market-calculation admission.
    if not isinstance(ref, Mapping) or not _SHA.fullmatch(str(ref.get('sha256', ''))):
        return False
    for key, value in ref.items():
        if key == 'periods':
            if not isinstance(value, list) or any(not isinstance(v, str) or len(v) > 128 for v in value):
                return False
        elif key == 'benchmark_window_sessions':
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                return False
        elif not isinstance(value, str) or len(value) > 512:
            return False
        if key in ('price_adjustment', 'benchmark', 'benchmark_price_adjustment') and (not value or len(value) > 128):
            return False
    return True


def _recognition_leg(value, bindings, generated, subject, *, scenario):
    missing = {'state':'missing_owner','owner_ref':None,'observed_at':None}
    if not isinstance(value, Mapping) or not _bound(value.get('owner_ref'),bindings):
        return missing
    binding = bindings[value['owner_ref']]
    if any(binding.get(k) != subject.get(k) for k in ('issuer_id','security_id')):
        return missing
    if value.get('state') not in ('supported','stale'):
        return missing
    try:
        if _instant(value.get('observed_at')) > generated:
            return missing
    except ValueError:
        return missing
    allowed = ('state','owner_ref','observed_at','security_id','price_adjustment',
               'price_vintage','window_sessions','return_pct','relative_return_pct','benchmark',
               'market_as_of','previous_session','sessions_behind')
    if scenario:
        if binding.get('owner_family') not in ('valuation_scenario','stock_library') or value.get('period') not in binding.get('periods',[]) or value.get('per_share') is None:
            return missing
        if value.get('schema') != 'valuation_scenario.v1' or value.get('kind') != 'algebraic_scenario':
            return missing
        allowed = ('state','owner_ref','observed_at','schema','kind','period','per_share','assumptions')
        assumptions = value.get('assumptions')
        if not isinstance(assumptions,Mapping) or set(assumptions) != {'sales_growth_pct','margin_delta_pp','earnings_multiple'}:
            return missing
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in assumptions.values()):
            return missing
    elif binding.get('owner_family') not in ('market','stock_library','group_reads') or any(value.get(k) is None for k in ('security_id','price_adjustment','price_vintage','window_sessions','return_pct','market_as_of','previous_session','sessions_behind')):
        return missing
    if not scenario and (value.get('security_id') != subject.get('security_id') or any(value.get(k) is not None and (not isinstance(value[k],str) or len(value[k])>128) for k in ('security_id','price_adjustment','price_vintage','benchmark'))):
        return missing
    if not scenario:
        # Quote the owner's declared basis rather than inferring it from a
        # column, ticker, adjustment flag or file modification time.
        adjustment = value.get('price_adjustment')
        if not adjustment or binding.get('price_adjustment') != adjustment:
            return missing
        if value.get('relative_return_pct') is not None:
            benchmark = value.get('benchmark')
            if (not isinstance(benchmark, str) or not benchmark
                    or benchmark != binding.get('benchmark')
                    or binding.get('benchmark_price_adjustment') != adjustment
                    or binding.get('benchmark_window_sessions') != value.get('window_sessions')):
                return missing
        window=value.get('window_sessions')
        if isinstance(window,bool) or not isinstance(window,int) or window<=0:
            return missing
        try:
            if _instant(value.get('price_vintage'))>generated: return missing
        except ValueError:
            return missing
        try:
            # Bar dates, archived-byte vintage and our read clock are distinct.
            bar_dates = [value[k] for k in ('previous_session','market_as_of')]
            if any(not isinstance(v,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',v) for v in bar_dates):
                return missing
            previous, market_as_of = map(date.fromisoformat, bar_dates)
            lag = value.get('sessions_behind')
            if (isinstance(lag,bool) or not isinstance(lag,int) or lag < 0
                    or previous >= market_as_of
                    or not all(nyse_calendar.is_session(d) for d in (previous,market_as_of))
                    or len(nyse_calendar.sessions_between(previous,market_as_of))-1 != window
                    or market_as_of > nyse_calendar.expected_last_session(generated)
                    or market_as_of > nyse_calendar.expected_last_session(_instant(value['price_vintage']))
                    or _instant(value['price_vintage']) > _instant(value['observed_at'])
                    or lag != nyse_calendar.sessions_behind(market_as_of,generated)
                    or (lag > 0 and value['state'] == 'supported')):
                return missing
        except (ValueError,TypeError):
            return missing
    result = {k:deepcopy(value[k]) for k in allowed if k in value}
    if scenario:
        result['assumptions'] = {k:value['assumptions'][k] for k in ('sales_growth_pct','margin_delta_pp','earnings_multiple')}
    if any(result.get(k) is not None and (isinstance(result[k],bool) or not isinstance(result[k],(int,float)) or not math.isfinite(result[k])) for k in ('return_pct','relative_return_pct','per_share','window_sessions')):
        return missing
    return result


def defense_economics_content_id(payload):
    semantic = {k:v for k,v in payload.items() if k not in ('generated_at','content_id')}
    return 'dfe1-' + sha256(_json(semantic).encode()).hexdigest()[:24]


def _axis(name, supplied, bindings, generated, subject):
    if not isinstance(supplied, Mapping):
        return _missing('owner_not_supplied')
    if supplied.get('display_scope') != 'government_revenue_entitled':
        return _missing('display_scope_not_qualified', state='unreviewed')
    state = supplied.get('state')
    if state not in STATES or not _bound(supplied.get('owner_ref'), bindings):
        return _missing('owner_reference_invalid', state='unreviewed')
    observed = supplied.get('observed_at')
    try:
        if observed is not None and _instant(observed) > generated:
            return _missing('observation_after_generation', state='contradictory')
    except ValueError:
        return _missing('observation_clock_invalid', state='unreviewed')
    if state in {'supported','partial'} and observed is None:
        return _missing('observation_clock_missing', state='unreviewed')
    if name in ('participation','demand') and state in ('supported','partial','stale'):
        refs=[supplied.get('owner_ref'),*supplied.get('evidence_refs',[])]
        if any(not _bound(ref,bindings) or any(bindings[ref].get(k)!=subject.get(k) for k in ('issuer_id','security_id')) for ref in refs):
            return _missing('government_context_subject_unqualified',state='unreviewed')
    if supplied.get('summary_lineage') == 'score_overlay':
        return _missing('score_overlay_not_financial_evidence', state='unreviewed')
    if supplied.get('claim_citations_pending') and name == 'economics':
        return _missing('financial_source_spans_pending', state='unreviewed')
    result = {k: deepcopy(supplied.get(k)) for k in
              ('state','owner_ref','observed_at','fiscal_period','reason_code')}
    result.update(summary_en=_text(supplied.get('summary_en')),
                  summary_zh=_text(supplied.get('summary_zh')),
                  evidence_refs=[v for v in supplied.get('evidence_refs',[]) if _bound(v,bindings)],
                  limitations=[v for v in supplied.get('limitations',[]) if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',v)], facts=[])
    if name == 'recognition' and supplied.get('expectations_kind') not in (None, 'not_observed'):
        return _missing('expectations_not_observed', state='unreviewed')
    if name == 'recognition':
        result['price_response'] = _recognition_leg(supplied.get('price_response'), bindings, generated, subject, scenario=False)
        result['valuation_scenario'] = _recognition_leg(supplied.get('valuation_scenario'), bindings, generated, subject, scenario=True)
        result['expectations_kind'] = 'not_observed'
        if state == 'supported' and result['price_response']['state'] not in ('supported','stale'):
            result['state'] = 'partial'
            result['limitations'].append('price_response_not_qualified')
    if state in {'supported','partial','stale'}:
        try:
            seen = set()
            for v in supplied.get('facts', []):
                quoted = _fact(v, bindings, subject)
                key = (quoted['fact_id'], quoted['owner_ref'], quoted['source_span']['text_sha256'])
                if key not in seen:
                    result['facts'].append(quoted)
                    seen.add(key)
        except ValueError as exc:
            return _missing('financial_fact_invalid', state='unreviewed')
    if name == 'economics' and state in {'supported','partial','stale'} and not result['facts']:
        return _missing('qualified_financial_facts_missing', state='unreviewed')
    return result


def compose_defense_economics(inputs, *, generated_at, source_bindings):
    """Quote owner facts; preserve missing optional axes and explicit unknowns.

    Source bindings are already-qualified immutable owner receipts. This is a
    pure view composition; no untrusted caller can use it to admit a source.
    """
    generated = _instant(generated_at)
    if not isinstance(inputs, Mapping) or not isinstance(source_bindings, Mapping):
        raise ValueError('inputs and source_bindings must be mappings')
    bindings = {key:{k:deepcopy(v) for k,v in ref.items() if k in
        ('sha256','content_id','contract','owner_family','observed_at','issuer_id','security_id','periods','source_available_at','owner_admission_ref','price_adjustment','benchmark','benchmark_price_adjustment','benchmark_window_sessions')}
        for key,ref in source_bindings.items() if isinstance(ref, Mapping)}
    if len(bindings) != len(source_bindings):
        raise ValueError('source binding must be a mapping')
    for key, ref in bindings.items():
        if not isinstance(key, str) or not _valid_binding_fields(ref):
            raise ValueError('source binding must include an immutable sha256')
    profiles = []
    for ticker in COHORT:
        data = inputs.get(ticker) or {}
        identity = data.get('identity') or {}
        issuer = identity.get('issuer_binding') or {}
        qualified_identity = (identity.get('identity_mode') == 'current'
                              and _bound(data.get('identity_owner_ref'), bindings)
                              and bindings[data['identity_owner_ref']].get('issuer_id') == issuer.get('issuer_id')
                              and bindings[data['identity_owner_ref']].get('security_id') == identity.get('security_id')
                              and isinstance(issuer.get('issuer_id'), str)
                              and isinstance(identity.get('security_id'), str))
        subject = {'issuer_id':issuer.get('issuer_id'), 'security_id':identity.get('security_id')}
        axes = {name: _axis(name, (data.get('axes') or {}).get(name), bindings, generated, subject)
                for name in AXES}
        axes['recognition'].setdefault('expectations_kind','not_observed')
        if not qualified_identity:
            axes['demand'] = _missing('issuer_identity_unqualified', state='unreviewed')
            axes['economics'] = _missing('issuer_identity_unqualified', state='unreviewed')
            axes['recognition'] = {**_missing('issuer_identity_unqualified', state='unreviewed'), 'expectations_kind':'not_observed'}
        complete = qualified_identity and all(axes[a]['state'] == 'supported' for a in AXES)
        interpretation=data.get('interpretation')
        validate_defense_interpretation(interpretation,ticker,axes['economics']['facts'])
        profiles.append(dict(
            issuer_id=issuer.get('issuer_id') if qualified_identity else None,
            security_id=identity.get('security_id') if qualified_identity else None,
            ticker_display=ticker, name=_text(data.get('name')) or ticker,
            identity_mode='current' if qualified_identity else None,
            identity_owner_ref=data.get('identity_owner_ref') if qualified_identity else None, axes=axes,
            interpretation=deepcopy(interpretation),
            program_workshare=None, program_workshare_state='not_disclosed',
            shareholder_capture={'state':'not_asserted','source_refs':[]},
            contrary_case=_text(data.get('contrary_case')),
            contrary_case_zh=_text(data.get('contrary_case_zh')),
            next_condition=_text(data.get('next_condition')),
            next_condition_zh=_text(data.get('next_condition_zh')),
            invalidation=_text(data.get('invalidation')),
            invalidation_zh=_text(data.get('invalidation_zh')),
            research_state='SOURCE_CONTEXT_COMPLETE' if complete else 'EVIDENCE_INSUFFICIENT',
            authority=deepcopy(AUTHORITY)))
    result = dict(contract=CONTRACT, schema_version='1.0.0', generated_at=generated_at,
                  source_bindings=bindings, profiles=profiles, authority=deepcopy(AUTHORITY))
    result['content_id'] = defense_economics_content_id(result)
    return result


def validate_defense_economics_payload(payload):
    """Strict read-time validation for the API/site-only canonical artifact."""
    if not isinstance(payload,Mapping) or set(payload) != {'contract','schema_version','content_id','generated_at','source_bindings','profiles','authority'}:
        raise ValueError('snapshot_fields_invalid')
    try:
        _json(payload)
    except (ValueError,TypeError): raise ValueError('snapshot_not_finite_json')
    if payload['contract'] != CONTRACT or payload['schema_version'] != '1.0.0' or payload['authority'] != AUTHORITY:
        raise ValueError('snapshot_contract_or_authority_invalid')
    generated = _instant(payload['generated_at'])
    bindings = payload['source_bindings']
    if not isinstance(bindings,Mapping): raise ValueError('bindings_invalid')
    allowed_binding = {'sha256','content_id','contract','owner_family','observed_at','issuer_id','security_id','periods','source_available_at','owner_admission_ref','price_adjustment','benchmark','benchmark_price_adjustment','benchmark_window_sessions'}
    for ref in bindings.values():
        if not _valid_binding_fields(ref) or set(ref)-allowed_binding:
            raise ValueError('binding_fields_invalid')
    profiles = payload['profiles']
    if not isinstance(profiles,list) or any(not isinstance(v,Mapping) for v in profiles) or [v.get('ticker_display') for v in profiles] != list(COHORT):
        raise ValueError('cohort_invalid')
    profile_keys = {'issuer_id','security_id','ticker_display','name','identity_mode','identity_owner_ref','axes','program_workshare','program_workshare_state','shareholder_capture','contrary_case','contrary_case_zh','next_condition','next_condition_zh','invalidation','invalidation_zh','research_state','authority'}
    axis_keys = {'state','summary_en','summary_zh','owner_ref','evidence_refs','observed_at','fiscal_period','reason_code','facts','limitations','price_response','valuation_scenario','expectations_kind'}
    for profile in profiles:
        if not (profile_keys <= set(profile) <= profile_keys | {'interpretation'}) or profile['authority'] != AUTHORITY or profile['program_workshare'] is not None or profile['program_workshare_state'] != 'not_disclosed' or profile['shareholder_capture'] != {'state':'not_asserted','source_refs':[]}:
            raise ValueError('profile_fields_or_authority_invalid')
        if profile['research_state'] not in ('SOURCE_CONTEXT_COMPLETE','EVIDENCE_INSUFFICIENT') or profile['identity_mode'] not in ('current',None):
            raise ValueError('profile_state_invalid')
        if any(v is not None and (not isinstance(v,str) or len(v)>2000) for v in [profile.get(k) for k in ('issuer_id','security_id','name','contrary_case','contrary_case_zh','next_condition','next_condition_zh','invalidation','invalidation_zh')]):
            raise ValueError('profile_text_invalid')
        subject = {k:profile[k] for k in ('issuer_id','security_id')}
        identity_ref=profile.get('identity_owner_ref')
        qualified_identity=(profile['identity_mode']=='current' and _bound(identity_ref,bindings) and all(bindings[identity_ref].get(k)==profile.get(k) and isinstance(profile.get(k),str) for k in ('issuer_id','security_id')))
        if not qualified_identity and any(profile.get(k) is not None for k in ('issuer_id','security_id','identity_owner_ref','identity_mode')):
            raise ValueError('identity_binding_invalid')
        if not isinstance(profile['axes'],Mapping) or set(profile['axes']) != set(AXES):
            raise ValueError('axes_invalid')
        for name,axis in profile['axes'].items():
            if not isinstance(axis,Mapping) or not {'state','summary_en','summary_zh','owner_ref','evidence_refs','observed_at','fiscal_period','reason_code','facts','limitations'} <= set(axis) or set(axis)-axis_keys or axis.get('state') not in STATES:
                raise ValueError('axis_fields_invalid')
            if any(v is not None and (not isinstance(v,str) or len(v)>2000) for v in [axis.get(k) for k in ('summary_en','summary_zh','owner_ref','observed_at','reason_code')]):
                raise ValueError('axis_text_invalid')
            if not isinstance(axis.get('facts'),list) or not isinstance(axis.get('evidence_refs'),list) or not isinstance(axis.get('limitations'),list) or any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',v) for v in axis['limitations']):
                raise ValueError('axis_lists_invalid')
            if axis.get('owner_ref') is not None and not _bound(axis['owner_ref'],bindings):
                raise ValueError('axis_owner_invalid')
            if axis.get('observed_at') is not None and _instant(axis['observed_at']) > generated:
                raise ValueError('axis_clock_invalid')
            if any(not _bound(v,bindings) for v in axis.get('evidence_refs',[])):
                raise ValueError('evidence_ref_invalid')
            if axis['state'] in ('supported','partial','stale') and axis.get('observed_at') is None:
                raise ValueError('supported_axis_observation_missing')
            if name in ('participation','demand') and axis['state'] in ('supported','partial','stale'):
                refs=[axis.get('owner_ref'),*axis['evidence_refs']]
                if not qualified_identity or any(not _bound(ref,bindings) or any(bindings[ref].get(k)!=subject.get(k) for k in ('issuer_id','security_id')) for ref in refs):
                    raise ValueError('government_context_subject_invalid')
            if name=='economics' and axis['state'] in ('supported','partial','stale') and (not qualified_identity or not axis.get('facts')):
                raise ValueError('supported_finance_missing_identity_or_facts')
            for fact in axis.get('facts',[]):
                if _fact(fact,bindings,subject) != fact: raise ValueError('fact_fields_invalid')
            if name == 'recognition':
                if not qualified_identity and axis['state'] in ('supported','partial','stale'):
                    raise ValueError('supported_recognition_missing_identity')
                for field,scenario in [('price_response',False),('valuation_scenario',True)]:
                    if field in axis and _recognition_leg(axis[field],bindings,generated,subject,scenario=scenario) != axis[field]:
                        raise ValueError('recognition_fields_invalid')
                if axis.get('expectations_kind') != 'not_observed': raise ValueError('expectations_invalid')
        validate_defense_interpretation(profile.get('interpretation'),profile['ticker_display'],profile['axes']['economics']['facts'])
        expected_state='SOURCE_CONTEXT_COMPLETE' if qualified_identity and all(profile['axes'][a]['state']=='supported' for a in AXES) else 'EVIDENCE_INSUFFICIENT'
        if profile['research_state'] != expected_state: raise ValueError('research_state_not_supported')
    if payload['content_id'] != defense_economics_content_id(payload): raise ValueError('content_id_mismatch')
    return True
