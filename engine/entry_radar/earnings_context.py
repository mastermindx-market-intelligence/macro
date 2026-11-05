"""Optional post-commit retrospective earnings context on the ordinary payload.

No detection, lifecycle, quote-use attribution, ledger/spool writes or case store.
The script supplies the already committed native rows; failures affect context only.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from engine.company_intelligence.opportunity_context import compose_earnings_candidate_case
from engine.company_intelligence.opportunity_qualification import _identity, _instant
from engine.company_intelligence.research_generation import read_pinned_generation, validate_generation_pointer
from engine.entry_radar.quote_context import restore_pack_identity
from engine.entry_radar.live_ledger import LiveEpisode, EPISODE_FIELDS, compute_episode_id
from engine.entry_radar import detectors
from lib import evidence_foundation as ef
from lib.opportunity_case import validate_case

SCHEMA='entry_radar.research_context/v1'
MAX_CANDIDATES=8
RESEARCH_IDENTITY_VENDOR='polygon'
LIMITATIONS=['whole_workspace_rights_unknown','freshness_policy_unknown','native_quote_use_not_established',
             'owner_span_receipt_not_locally_replayed','no_surprise_calibration_or_entry_authority']


def _now():return datetime.now(timezone.utc)


def _candidate(raw):
    row=LiveEpisode.from_dict({k:raw[k] for k in EPISODE_FIELDS if k in raw})
    spec=detectors.get_spec(row.detector_id)
    if (row.state!='CANDIDATE' or row.terminal or row.candidate_at is None
            or row.detector_version!=spec.version or row.detector_spec_hash!=spec.spec_hash
            or row.episode_id!=compute_episode_id(ticker=row.ticker,detector_id=row.detector_id,
                variant=row.variant,first_armed_at=row.first_armed_at)):
        raise ValueError('native_candidate_invalid')
    return row


def _research_identity(row,read):
    # Explicit existing research lookup namespace. This NEVER describes the
    # candidate's historical quote vendor and never falls back to another one.
    return RESEARCH_IDENTITY_VENDOR,_identity(row,read,RESEARCH_IDENTITY_VENDOR)


def _closed_binding(binding):
    from lib.dataos.identity import ReferenceReadReceipt
    keys={'schema','episode_id','episode_canonical_sha256','candidate_at','ticker','identity',
          'workspace_native_identity','workspace_reference_id','workspace_semantic_sha256','scope',
          'candidate_quote_security_join','sha256'}
    identity_keys={'vendor','vendor_symbol','security_id','issuer_id','cik','alias_revision_id',
                   'alias_known_at_utc_ns','identity_read_receipt','identity_snapshot_sha256','identity_scope'}
    if (type(binding) is not dict or set(binding)!=keys or binding['schema']!='earnings.ler_context_binding.v1'
            or type(binding['identity']) is not dict or set(binding['identity'])!=identity_keys
            or set(binding['workspace_native_identity'])!={'event_id','generation_id'}
            or binding['identity']['identity_scope']!='as_known_in_observation_bound_snapshot'):
        raise ValueError('retrospective_context_binding_invalid')
    identity=binding['identity']
    for key in ('vendor','vendor_symbol','security_id','issuer_id','cik','alias_revision_id',
                'alias_known_at_utc_ns','identity_snapshot_sha256','identity_scope'):
        if type(identity[key]) is not str or not 0<len(identity[key])<=256:
            raise ValueError('retrospective_context_binding_invalid')
    if (not re.fullmatch(r'[0-9]{10}',identity['cik'])
            or not re.fullmatch(r'[0-9]+',identity['alias_known_at_utc_ns'])
            or not re.fullmatch(r'[a-f0-9]{64}',identity['identity_snapshot_sha256'])
            or not re.fullmatch(r'[a-f0-9]{64}',binding['workspace_semantic_sha256'])):
        raise ValueError('retrospective_context_binding_invalid')
    receipt=ReferenceReadReceipt.from_record(binding['identity']['identity_read_receipt']).as_record()
    if (receipt!=binding['identity']['identity_read_receipt']
            or receipt['receipt_sha256']!=identity['identity_snapshot_sha256']):
        raise ValueError('retrospective_context_binding_invalid')
    return json.loads(ef.canonical_json_bytes(binding))


def project_context(envelope: dict, row: LiveEpisode, pointer: dict) -> dict:
    """Closed descriptive projection; no arbitrary owner bodies or K3 controls."""
    case=validate_case(envelope['case']);binding=_closed_binding(envelope['candidate_context_binding'])
    pointer=validate_generation_pointer(pointer)
    canonical=sha256(row.canonical.encode()).hexdigest()
    refs=case['inputs']['references'];rid,ref=next(iter(refs.items()))
    slot=case['inputs']['vector']['slots'][0];link=slot['earnings_context']
    expected={'event_id':link['event_id'],'generation_id':pointer['generation_id']}
    if (envelope['schema']!='earnings.candidate_research.v1' or envelope['live_projection_eligible'] is not False
            or envelope['limitations']!=LIMITATIONS or len(refs)!=1
            or binding['episode_id']!=row.episode_id or binding['episode_canonical_sha256']!=canonical
            or binding['candidate_at']!=row.candidate_at or binding['ticker']!=row.ticker
            or binding['scope']!='episode_symbol_context' or binding['candidate_quote_security_join']!='not_established'
            or binding['workspace_native_identity']!=expected or ref['native_identity']!=expected
            or binding['workspace_reference_id']!=rid or binding['identity']['cik']!=link['cik']
            or ref['owner_store']!='earnings.workspace_generation'
            or case['asof']['value']!=row.candidate_at or case['asof']['t0_mode']!='retrospective_research'
            or case['asof']['t0_source']!='earnings_workspace_context'
            or case['subject']['subject_type']!='earnings_cik'
            or case['research_state']!='partial' or case['permitted_consumers']!=['research_session']
            or _instant(pointer['captured_at'])>_instant(row.candidate_at)):
        raise ValueError('retrospective_context_binding_invalid')
    if binding['sha256']!=sha256(ef.canonical_json_bytes({k:v for k,v in binding.items() if k!='sha256'})).hexdigest():
        raise ValueError('retrospective_context_binding_invalid')
    evidence_keys=('reference_id','owner_store','native_digest','clocks','rights','freshness','provenance')
    result={'schema':SCHEMA,'projection_kind':'retrospective_earnings_context','episode_id':row.episode_id,
            'episode_binding':{'episode_id':row.episode_id,'candidate_at':row.candidate_at,'canonical_sha256':canonical},
            'candidate_context_binding':binding,
            'case_ref':{'schema':case['schema'],'case_id':case['case_id'],'sha256':case['content_sha256']},
            'native_earnings_identity':expected,'research_subject':{'key_type':'cik','key':link['cik']},
            'fiscal_period':dict(link['fiscal_period']),
            'composed_at':case['generated_at'],'evidence_cutoff':row.candidate_at,
            'source_generation':pointer,'research_state':'partial',
            'evidence_binding_state':case['evidence_binding']['state'],
            'company_context':{'state':'partial'},
            'observation':{'metric':'revenue',**dict(link['observation'])},
            'transmission':{'state':'unavailable'},
            'evidence_refs':[{k:ref[k] for k in evidence_keys}],
            'denominators':case['denominators'],'dominant_degradation':case['dominant_degradation'],
            'candidate_quote_security_join':'not_established','live_projection_eligible':False,
            'limitations':list(LIMITATIONS),'authority':dict(ef.ALL_FALSE_AUTHORITY)}
    if len(ef.canonical_json_bytes(result))>64*1024:raise ValueError('retrospective_context_bound')
    result['sha256']=sha256(ef.canonical_json_bytes(result)).hexdigest()
    return result


def attach_retrospective_earnings_context(payload: dict, *, pack, identity_directory,
                                         committed: bool, budget_seconds: float = 16,
                                         ledger=None, journal=None) -> dict:
    """Script hook AFTER commit/save and BEFORE normal publish; bounded to 8.

    Fresh owner I/O only verifies the exact retained pointers. This does not
    collect data, scan predecessors, manufacture missing prior reads or attest
    that a quote was consumed. Never propagates optional failure to the pass.
    """
    from engine.neuralweb import company_intelligence_reader as owner
    try:
        with owner.bounded_read_budget(budget_seconds):
            return _attach(payload, pack=pack, identity_directory=identity_directory, committed=committed,
                           ledger=ledger, journal=journal)
    except owner.CompanyIntelligenceReadBudgetExceeded:
        return {'state':'unavailable','selected':0,'attached':0,'refusals':{'optional_resource_budget':1}}


def _attach(payload, *, pack, identity_directory, committed, ledger=None, journal=None):
    from engine.neuralweb import company_intelligence_reader as owner
    report={'state':'unavailable','selected':0,'attached':0,'refusals':{}}
    def refuse(code):report['refusals'][code]=report['refusals'].get(code,0)+1
    if committed is not True:
        refuse('ledger_not_committed');return report
    try:
        owner.check_read_budget()
        rows=payload.get('episodes')
        if type(rows) is not list or len(rows)>8192:raise ValueError()
        candidates=[r for r in rows if isinstance(r,dict) and r.get('state')=='CANDIDATE']
        ids=[r.get('episode_id') for r in candidates]
        if any(type(i) is not str for i in ids) or len(ids)!=len(set(ids)):raise ValueError()
        choices=sorted(candidates,key=lambda r:r['episode_id'])[:MAX_CANDIDATES]
        report['selected']=len(choices)
        if not choices:report['state']='empty';return report
        from engine.entry_radar.replay.identity_observation_snapshot import read_identity_snapshot
        read=restore_pack_identity(pack,read_identity_snapshot(identity_directory))
    except owner.CompanyIntelligenceReadBudgetExceeded:
        refuse('optional_resource_budget');return report
    except Exception:
        refuse('native_preparation_unavailable');return report
    try:
        pointer = validate_generation_pointer(pack.earnings_generation)
    except Exception:
        pointer = None
    quote_report = None
    if ledger is not None and journal is not None:
        quote_report = {'attached':0, 'refusals':{}}
        report['quote_candidate_provenance'] = quote_report
    prepared=[]
    for raw in choices:
        try:
            owner.check_read_budget()
            row=_candidate(raw)
            vendor,identity=_research_identity(row,read)
            if quote_report is not None:
                try:
                    from engine.entry_radar.candidate_provenance import compose_candidate_quote_provenance
                    if (re.fullmatch(r'[A-Z0-9.^=-]{1,32}', row.ticker) is None
                            or ledger.get(row.episode_id) is None
                            or ledger.get(row.episode_id).canonical != row.canonical):
                        raise ValueError()
                    record = journal.read(row.market_session,row.ticker)
                    if record is None or record.pack_hash != pack.pack_hash:
                        raise ValueError()
                    provenance = compose_candidate_quote_provenance(row.to_dict(),
                        record=record, identity_read=read,
                        origin=ledger.candidate_origin(row.episode_id), composed_at=_now().isoformat())
                    if any(provenance['identity'][key] != identity[key]
                           for key in ('security_id','issuer_id','cik','identity_snapshot_sha256')):
                        raise ValueError()
                    owner.check_read_budget()
                    raw['quote_candidate_provenance'] = provenance
                    quote_report['attached'] += 1
                except owner.CompanyIntelligenceReadBudgetExceeded:
                    raise
                except Exception:
                    key = 'native_quote_provenance_unqualified'
                    quote_report['refusals'][key] = quote_report['refusals'].get(key,0)+1
            if pointer is None or _instant(pointer['captured_at'])>_instant(row.candidate_at):
                raise ValueError()
            prepared.append((raw,row,vendor,identity))
        except owner.CompanyIntelligenceReadBudgetExceeded:
            refuse('optional_resource_budget');return report
        except Exception:refuse('candidate_context_unqualified')
    if not prepared:
        return report
    try:
        companies=sorted({'cik:'+identity['cik'] for _,_,_,identity in prepared})
        events=read_pinned_generation(pointer,companies)
    except owner.CompanyIntelligenceReadBudgetExceeded:
        refuse('optional_resource_budget');return report
    except Exception:
        refuse('earnings_generation_unavailable');return report
    for raw,row,vendor,identity in prepared:
        try:
            owner.check_read_budget()
            native=events.get('cik:'+identity['cik'])
            if native is None:raise ValueError()
            composed=_now().isoformat().replace('+00:00','Z')
            envelope=compose_earnings_candidate_case(episode=row.to_dict(),identity_read=read,vendor=vendor,
                composed_at=composed,event_id=native['event_id'],revisions=native['revisions'])
            projection=project_context(envelope,row,pointer)
            owner.check_read_budget()
            raw['research_context']=projection
            # The optional link names this exact accepted research projection;
            # neither its retrospective mode nor its eligibility/rights changes.
            if 'quote_candidate_provenance' in raw:
                provenance = dict(raw['quote_candidate_provenance'])
                provenance['research_context_ref'] = {'case_ref':dict(projection['case_ref']),
                    'context_sha256':projection['sha256']}
                provenance.pop('sha256')
                provenance['sha256'] = sha256(ef.canonical_json_bytes(provenance)).hexdigest()
                raw['quote_candidate_provenance'] = provenance
            report['attached']+=1
        except owner.CompanyIntelligenceReadBudgetExceeded:
            refuse('optional_resource_budget');break
        except Exception:refuse('earnings_context_unqualified')
    report['state']='partial' if report['attached'] else 'unavailable'
    return report
