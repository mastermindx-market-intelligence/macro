"""Native source composition for the existing nominal-policy-point comparator.

The normal publisher supplies its actual reads and adopted decisions. No fetch,
Saved identity, historical fill or alternative arithmetic is introduced here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math

from engine.intl_inputs import admit_ecb_deposit_field
from engine.intl_rates import compare_policy_points
from lib.intl_boe_publication import admit_boe_policy_field

METHOD = 'intl-ecb-boe-nominal-policy-point-v1'
MAPPING_POLICY = 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-ecb-boe-policy-comparison'
INSTRUMENTS = {'EZ': 'deposit_facility', 'GB': 'bank_rate'}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _qualified_row(metric, economy, date, qualification):
    if (type(metric) is not dict or metric.get('quality') not in {'qualified', 'stale'}
            or metric.get('metadata') != 'allowed' or metric.get('value_permission') != 'allowed'
            or metric.get('instrument') != {'kind': 'official_policy', 'id': INSTRUMENTS[economy], 'market_id': economy}
            or metric.get('unit') != 'percent' or type(metric.get('value')) not in {int, float}
            or not math.isfinite(metric['value']) or metric.get('observation_at') != date
            or type(metric.get('source_reference')) is not str or not metric['source_reference']):
        return None
    return {'economy': economy, 'instrument_id': INSTRUMENTS[economy],
            'instrument_kind': 'nominal_policy_point', 'observation_at': date,
            'unit': 'percent', 'value': metric['value'], 'quality': 'qualified',
            'metadata': 'allowed', 'value_permission': 'allowed',
            'source_reference': metric['source_reference'], 'qualification_ref': qualification}


def compare_native_policy_points(intent, *, ecb_materialized, ecb_decision,
                                 boe_materialized, boe_decision, evaluated_at, mapping_decision=None,
                                 ecb_policy_materialized=None):
    """Invoke the unchanged engine on four exact admitted native endpoints.

    Historical dates are explicit latest-vintage reads. The same materialization
    may have a stale current display while its authenticated historical dates
    remain available; a missing exact row is never replaced with a nearby one.
    The caller supplies its actual identity/generation; this function mints none.
    """
    observations = dict.fromkeys(('a_start', 'a_end', 'b_start', 'b_end'))
    validated = compare_policy_points(intent, observations, None)
    if validated['state'] == 'invalid':
        return validated
    mapping = {'status': 'qualified', 'method_version': METHOD,
               'instruments': {side: {'economy': intent['economy_' + side],
                                     'instrument_id': INSTRUMENTS.get(intent['economy_' + side], 'unsupported'),
                                     'instrument_kind': 'nominal_policy_point'}
                               for side in ('a', 'b')}}
    if (intent['method_version'] != METHOD or {intent['economy_a'], intent['economy_b']} != {'EZ', 'GB'}
            or intent['period']['mode'] != 'fixed_dates' or intent['vintage_policy'] != 'latest_vintage'):
        mapping['status'] = 'unsupported'
        return compare_policy_points(intent, observations, mapping)
    expected_mapping = {
        'owner_ref': 'scripts/build_intl.py', 'policy_ref': MAPPING_POLICY,
        'method_version': METHOD, 'metadata': 'allowed', 'value_permission': 'allowed',
        'binding': {'economy_a': intent['economy_a'], 'economy_b': intent['economy_b'],
                    'period': intent['period'],
                    'ecb_identity': ecb_materialized.get('materialized_identity') if type(ecb_materialized) is dict else None,
                    'boe_receipt_sha256': boe_materialized.get('receipt_sha256') if type(boe_materialized) is dict else None}}
    try:
        from lib.intl_investigation_projection import _plain_json
        permitted_mapping = (_plain_json(mapping_decision) and type(mapping_decision) is dict
                             and mapping_decision == expected_mapping
                             and expected_mapping['binding']['ecb_identity'] is not None
                             and expected_mapping['binding']['boe_receipt_sha256'] is not None)
    except (TypeError, ValueError, RecursionError):
        permitted_mapping = False
    if not permitted_mapping:
        mapping['status'] = 'unqualified'
        return compare_policy_points(intent, observations, mapping)
    generation = intent['identity']['source_generation']
    if (type(generation) is not str or not generation
            or type(ecb_decision) is not dict or type(boe_decision) is not dict
            or ecb_decision.get('decision_ref') != generation + ':EZ.policy_rate'
            or boe_decision.get('decision_ref') != generation + ':GB.policy_rate'):
        return compare_policy_points(intent, observations, mapping)
    evaluated = None
    try:
        evaluated = datetime.fromisoformat(evaluated_at.replace('Z', '+00:00'))
        requested = datetime.fromisoformat(ecb_materialized['provenance']['requested_at'].replace('Z', '+00:00'))
        if (evaluated.tzinfo is None or requested.tzinfo is None
                or requested.astimezone(timezone.utc) > evaluated.astimezone(timezone.utc)):
            raise ValueError('invalid ECB source chronology')
        current_ecb = admit_ecb_deposit_field(
            ecb_materialized['series'], provenance=ecb_materialized['provenance'],
            materialized_identity=ecb_materialized['materialized_identity'],
            evaluated_at=evaluated_at, publication_decision=ecb_decision)
    except (KeyError, TypeError, ValueError, OverflowError):
        current_ecb = None
    original_ecb_rows = {}
    try:
        from lib.intl_ecb_policy_publication import _receipt as validate_ecb_receipt, _json, _sha, _parse
        evidence = ecb_policy_materialized
        if type(evidence) is not dict or evidence.get('status') != 'ready':
            raise ValueError('original ECB row evidence unavailable')
        receipt = evidence['receipt']; validate_ecb_receipt(receipt)
        raw = evidence.get('source_bytes')
        if (type(raw) is not bytes or _sha(raw) != receipt['source_sha256']
                or _sha(_json(receipt)) != evidence['receipt_sha256']
                or receipt['artifact_sha256'] != ecb_materialized['materialized_identity']['artifact_sha256']
                or datetime.fromisoformat(receipt['committed_at'].replace('Z','+00:00')) > evaluated):
            raise ValueError('ECB original source/store binding differs')
        original_ecb_rows = {row['date']: row for row in _parse(raw)['observations']}
    except (KeyError,TypeError,ValueError,OverflowError):
        # Historical dates need their original observed status, never merely
        # a cached numeric row or the current display's stale/qualified state.
        original_ecb_rows = {}
    for slot in observations:
        economy = intent['economy_' + slot[0]]
        date = intent['period'][slot.split('_')[1]]
        decision = ecb_decision if economy == 'EZ' else boe_decision
        try:
            if economy == 'GB':
                metric = admit_boe_policy_field(boe_materialized, evaluated_at=evaluated_at,
                    publication_decision=boe_decision, observation_date=date)
            else:
                # A validated series-level publication decision and exact
                # authenticated series membership authorize this historical
                # point. A current-display age is not a historical cutoff.
                if (type(current_ecb) is not dict or current_ecb.get('quality') not in {'qualified', 'stale'}
                        or current_ecb.get('metadata') != 'allowed' or current_ecb.get('value_permission') != 'allowed'):
                    continue
                original = original_ecb_rows.get(date)
                if original is None or original['status'] != 'observed':
                    continue
                series = ecb_materialized['series']
                selected = series.loc[date]
                if hasattr(selected, 'item'):
                    selected = selected.item()
                if type(selected) not in {int,float} or selected != original['value']:
                    continue
                metric = {**current_ecb, 'value': selected, 'observation_at': date}
            qualification = 'intl-policy-endpoint:sha256:' + _digest({
                'method': METHOD, 'mapping': mapping_decision, 'date': date, 'economy': economy,
                'decision': {k: v for k, v in decision.items() if k != 'decision_ref'},
                'value': metric.get('value'), 'unit': metric.get('unit'),
                'source_receipt': evidence['receipt_sha256'] if economy == 'EZ' and original_ecb_rows else boe_materialized.get('receipt_sha256')})
            observations[slot] = _qualified_row(metric, economy, date, qualification)
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            # The engine withholds every comparison number/reference when any
            # endpoint is unavailable. No partial result or cached fallback.
            continue
    return compare_policy_points(intent, observations, mapping)


POINTS_SCHEMA = 'intl.policy_points.v1'
POINTS_MAX_BYTES = 4 * 1024 * 1024
_POINT_REF_KEYS = {'artifact_name','artifact_sha256','artifact_bytes','mapping_identity','qualification_identity'}

def validate_policy_points_reference(ref, generation):
    """Only the same-generation, content-addressed flat feed can be named."""
    import re
    if type(ref) is not dict or set(ref) != _POINT_REF_KEYS:
        raise ValueError('invalid policy point reference')
    for key in ('artifact_sha256','mapping_identity','qualification_identity'):
        if type(ref[key]) is not str or not re.fullmatch('[0-9a-f]{64}',ref[key]):
            raise ValueError('invalid policy point identity')
    if (type(ref['artifact_bytes']) is not int or not 0<ref['artifact_bytes']<=POINTS_MAX_BYTES
            or ref['artifact_name'] != 'intl_policy_points_'+generation.split(':',1)[1]+'_'+ref['artifact_sha256']+'.json'):
        raise ValueError('invalid policy point artifact')
    return ref


def build_policy_points(*, generation, ecb, boe, policies, mapping_policy, mapping_document_sha256, evaluated_at):
    """Project original native rows after both actual stores and rights qualify.

    The artifact carries latest-vintage daily points, never a date-pair grid,
    a user query, or a historical original-known claim.
    """
    from lib.intl_generation_publication import _generation, _digest as digest_check
    from lib.intl_boe_publication import _utc
    _generation(generation);digest_check('mapping policy revision',mapping_document_sha256)
    expected={'status':'confirmed','policy_ref':MAPPING_POLICY,'metadata':'allowed','value_permission':'allowed'}
    if mapping_policy != expected or ecb.get('status')!='ready' or boe.get('status')!='ready':
        return None
    for sid in ('EZ.policy_rate','GB.policy_rate'):
        p=policies.get(sid)
        if (type(p)is not dict or p.get('metadata')!='allowed' or p.get('value_permission')!='allowed'
                or not p.get('policy_identity')):return None
    mapping={'owner_ref':'scripts/build_intl.py','policy_ref':MAPPING_POLICY,'method_version':METHOD,
        'metadata':'allowed','value_permission':'allowed','policy_document_sha256':mapping_document_sha256,
        'instruments':{e:{'instrument_id':i,'instrument_ref':e+'.policy_rate','unit':'percent'}for e,i in INSTRUMENTS.items()}}
    mapping_identity=_digest({'domain':'intl-policy-mapping-v1','mapping':mapping,
                              'series_policies':{sid:policies[sid]for sid in ('EZ.policy_rate','GB.policy_rate')}})
    series={}
    for economy,source in [('EZ',ecb),('GB',boe)]:
        receipt=source['receipt'];digest_check('source receipt',source['receipt_sha256'])
        clocks={key:receipt[key]for key in ('requested_at','response_received_at','input_verified_at','committed_at','provider_published_at','revision_vintage')}
        if not (_utc(clocks['requested_at'])<=_utc(clocks['response_received_at'])<=_utc(clocks['input_verified_at'])<=_utc(clocks['committed_at'])<=_utc(evaluated_at)):
            raise ValueError('invalid policy source chronology')
        rows=source['parsed']['observations'] if economy=='EZ' else receipt['rows']
        series[economy]={'instrument_id':INSTRUMENTS[economy],'instrument_ref':economy+'.policy_rate',
            'unit':'percent','receipt_sha256':source['receipt_sha256'],'source_reference':receipt['source_url'],
            'clocks':clocks,'rows':rows}
    qualification=_digest({'domain':'intl-policy-source-qualification-v1','mapping_identity':mapping_identity,
                           'receipts':{e:s['receipt_sha256']for e,s in series.items()}})
    return {'schema':POINTS_SCHEMA,'asof':None,'generation':generation,'mapping':mapping,
            'mapping_identity':mapping_identity,'qualification_identity':qualification,'series':series}


def publish_policy_points(*,data_root,contract):
    from lib.intl_generation_publication import _canonical_json,_generations_dir,_write_immutable
    payload=_canonical_json(contract).encode();digest=hashlib.sha256(payload).hexdigest()
    ref={'artifact_name':'intl_policy_points_'+contract['generation'].split(':',1)[1]+'_'+digest+'.json',
         'artifact_sha256':digest,'artifact_bytes':len(payload),'mapping_identity':contract['mapping_identity'],
         'qualification_identity':contract['qualification_identity']}
    validate_policy_points_reference(ref,contract['generation'])
    directory=_generations_dir(data_root,create=True)
    _write_immutable(directory/ref['artifact_name'],payload,POINTS_MAX_BYTES)
    return ref


def _published_intent(settings,generation):
    return {key:settings.get(key)for key in ('economy_a','economy_b','lens','definition','method_version','period')} | {
        'vintage_policy':settings.get('revision_policy'),
        'identity':{'principal_partition':None,'saved_id':None,'saved_revision':None,'source_generation':generation}}


def preview_published_policy_points(*,feed_base,source_generation,artifact_sha256,settings,evaluated_at):
    """Read an exact public pin with fresh current policy, then use owner math.

    The route authenticates first. This reader has no credentials, stale cache,
    account state, filesystem fallback, or request-selected origin/path.
    """
    from lib.intl_generation_publication import (_generation,_digest as digest_check,
        _parse_json,_validate_contract,_validate_descriptor,MAX_ARTIFACT_BYTES,MAX_DESCRIPTOR_BYTES)
    from lib.intl_feed_reader import FixedFeedReader, FeedReadError
    intent=_published_intent(settings,source_generation) if type(settings)is dict else {}
    observations=dict.fromkeys(('a_start','a_end','b_start','b_end'))
    result=compare_policy_points(intent,observations,None)
    envelope={'schema':'intl.policy_preview.v1','state':result['state'],'source_generation':source_generation,
        'artifact_sha256':artifact_sha256,'mapping_identity':None,'qualification_identity':None,'result':result}
    if result['state']=='invalid':return envelope
    try:
        _generation(source_generation);digest_check('generation fingerprint',artifact_sha256)
        reader=FixedFeedReader(feed_base)
        current_raw=reader.read('intl_generation_current.json',max_bytes=MAX_DESCRIPTOR_BYTES)
        current=_validate_descriptor(_parse_json(current_raw))
        if current['state']!='ready':return envelope
        witness='intl_generation_descriptor_'+hashlib.sha256(current_raw).hexdigest()+'.json'
        if reader.read(witness,max_bytes=MAX_DESCRIPTOR_BYTES)!=current_raw:return envelope
        name='intl_generation_'+source_generation.split(':',1)[1]+'_'+artifact_sha256+'.json'
        raw=reader.read(name,max_bytes=MAX_ARTIFACT_BYTES)
        if hashlib.sha256(raw).hexdigest()!=artifact_sha256:return envelope
        generation=_validate_contract(_parse_json(raw))
        if generation['generation']!=source_generation:return envelope
        ref=generation.get('policy_points_ref')
        if ref is None:return envelope
        validate_policy_points_reference(ref,source_generation)
        # Fresh policy, not merely the permission frozen into an old pin.
        for sid in ('EZ.policy_rate','GB.policy_rate'):
            p=current['current_policies'].get(sid);old=generation['policies'].get(sid)
            if (type(p)is not dict or p.get('metadata')!='allowed' or p.get('value_permission')!='allowed'
                    or p!=old):return envelope
        cp=current.get('current_policy_points')
        if (type(cp)is not dict or cp.get('metadata')!='allowed' or cp.get('value_permission')!='allowed'
                or cp.get('mapping_identity')!=ref['mapping_identity']):return envelope
        point_raw=reader.read(ref['artifact_name'],max_bytes=POINTS_MAX_BYTES)
        if len(point_raw)!=ref['artifact_bytes'] or hashlib.sha256(point_raw).hexdigest()!=ref['artifact_sha256']:return envelope
        points=_parse_json(point_raw)
        if (type(points)is not dict or set(points)!={'schema','asof','generation','mapping','mapping_identity','qualification_identity','series'}
                or points['schema']!=POINTS_SCHEMA or points['asof']is not None
                or points['generation']!=source_generation or points['mapping_identity']!=ref['mapping_identity']
                or points['qualification_identity']!=ref['qualification_identity']):return envelope
        mapping=points['mapping'];series=points['series']
        if (mapping.get('owner_ref')!='scripts/build_intl.py' or mapping.get('policy_ref')!=MAPPING_POLICY
                or mapping.get('method_version')!=METHOD or mapping.get('metadata')!='allowed'
                or mapping.get('value_permission')!='allowed' or type(series)is not dict or set(series)!={'EZ','GB'}):return envelope
        expected_mapping=_digest({'domain':'intl-policy-mapping-v1','mapping':mapping,
                'series_policies':{sid:generation['policies'][sid]for sid in ('EZ.policy_rate','GB.policy_rate')}})
        qualification=_digest({'domain':'intl-policy-source-qualification-v1','mapping_identity':expected_mapping,
                'receipts':{e:s['receipt_sha256']for e,s in series.items()}})
        if expected_mapping!=ref['mapping_identity'] or qualification!=ref['qualification_identity']:return envelope
        if ({settings['economy_a'],settings['economy_b']}!={'EZ','GB'} or settings['method_version']!=METHOD
                or settings['revision_policy']!='latest_vintage' or settings['period']['mode']!='fixed_dates'):
            return envelope
        for side in ('a','b'):
            economy=settings['economy_'+side]
            if settings['instrument_'+side+'_ref'] is not None and settings['instrument_'+side+'_ref']!=economy+'.policy_rate':return envelope
        for slot in observations:
            economy=settings['economy_'+slot[0]];source=series[economy]
            if source['instrument_ref']!=economy+'.policy_rate' or source['instrument_id']!=INSTRUMENTS[economy] or source['unit']!='percent':return envelope
            date=settings['period'][slot.split('_')[1]]
            matches=[row for row in source['rows']if row['date']==date]
            if len(matches)!=1 or matches[0]['status']!='observed':continue
            row=matches[0]
            if type(row['value'])not in {int,float} or not math.isfinite(row['value']):continue
            observations[slot]={'economy':economy,'instrument_id':INSTRUMENTS[economy],
                'instrument_kind':'nominal_policy_point','observation_at':date,'unit':'percent','value':row['value'],
                'quality':'qualified','metadata':'allowed','value_permission':'allowed',
                'source_reference':source['source_reference'],
                'qualification_ref':'intl-policy-endpoint:sha256:'+_digest({'qualification':qualification,'economy':economy,'date':date,'value':row['value']})}
        receipt={'status':'qualified','method_version':METHOD,'instruments':{side:{'economy':settings['economy_'+side],
            'instrument_id':INSTRUMENTS[settings['economy_'+side]],'instrument_kind':'nominal_policy_point'}for side in ('a','b')}}
        result=compare_policy_points(intent,observations,receipt)
        if reader.read('intl_generation_current.json',max_bytes=MAX_DESCRIPTOR_BYTES)!=current_raw:return envelope
        return {**envelope,'state':result['state'],'mapping_identity':expected_mapping,'qualification_identity':qualification,'result':result}
    except (FeedReadError,OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError):
        return envelope
