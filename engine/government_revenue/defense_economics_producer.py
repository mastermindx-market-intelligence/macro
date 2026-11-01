"""Pure derived reader of the incumbent persisted Event Workspace generation.

The refresh producer owns acquisition, release binding and byte replay. This
reader verifies the owner manifest/files, closes fact projection, and composes
an entitled read model without network calls or publication effects.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from hashlib import sha256
import json
from engine.company_intelligence.contracts import canonical_json_bytes
from engine.company_intelligence.event_workspace import (
    validate_workspace_manifest, validate_event_workspace, validate_generation_clocks,
    select_current_event_from_aliases, WorkspaceError,
)
from engine.company_intelligence.defense_profiles import DEFENSE_TICKERS, SEGMENTS, METRICS, defense_issuer
from engine.earnings_release.figures import parse_numeric
from engine.company_intelligence.defense_cash_profiles import financial_fact_rules
from engine.company_intelligence.rms_segment_profile import numeric_rules as rms_numeric_rules
from engine.government_revenue.defense_economics import compose_defense_economics
from engine.government_revenue.defense_interpretation import build_defense_interpretation
from engine.government_revenue.defense_government_context import load_government_context_inputs,qualify_government_context
from engine.government_revenue.defense_participation_context import qualify_participation_context
from engine.government_revenue.defense_market_context import (
    load_defense_market_inputs, compose_defense_market_context,
)

# Existing accepted enterprise derived-display rights owner. This trusted
# producer reference is not a request flag; changed bytes require requalification.
_MARKET_RIGHTS_REF={
    "path":"research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
    "sha256":"82ad971b46d4159739117d3defe19a25a2a24ede45e5e8d28494c5849e757891",
    "derived_display_qualified":True,"debrand_required":True,
}

_SUPPLEMENT_METRICS={'msl_preferred_payout_terms','msl_qipo_conversion_terms','msl_nonipo_redemption_terms','space_business_sale_pending_terms','space_business_sale_pending_accounting','space_business_sale_completed_terms','space_business_sale_retained_scope'}
_SUPPLEMENT_METRICS.update(rms_numeric_rules())
_F2_NUMERIC={
 'defense_segment_prior_margin':('reported_segment_margin','percent','issuer_reported_segment:Defense Systems:reported','prior'),
 'siaw_unfavorable_eac':('reported_eac','USD_million','issuer_reported_program_cost_estimate:SiAW:unfavorable_EAC','current'),
 'sentinel_prior_favorable_eac':('reported_eac','USD_million','issuer_reported_program_cost_estimate:Sentinel:prior_favorable_EAC','prior'),
}

_FACT_CLASSES=dict(zip(METRICS,('reported_segment_sales','reported_segment_operating_profit','reported_segment_margin')))

def _instant(value):
    result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('clock_requires_timezone')
    return result


def load_defense_owner_snapshot(root):
    """Read verified local mirror of the existing owner prefix; never fetch."""
    nest=Path(root)/'data/company_intelligence/event_workspaces'
    marker=nest/'manifest.json'
    if not marker.is_file():return None
    raw=marker.read_bytes();manifest=json.loads(raw);validate_workspace_manifest(manifest)
    generation=str(manifest['generation_id'])
    immutable=nest/'generations'/generation
    if (immutable/'manifest.json').read_bytes()!=raw:raise ValueError('owner_marker_immutable_mismatch')
    rows={}
    for relative,receipt in manifest['files'].items():
        digest=receipt['sha256']
        path=(immutable/relative).resolve()
        if not path.is_relative_to(immutable.resolve()):raise ValueError('owner_path_outside_generation')
        body=path.read_bytes()
        if sha256(body).hexdigest()!=digest:raise ValueError('owner_workspace_hash_mismatch')
        row=json.loads(body);validate_event_workspace(row)
        if row['generation_id']!=generation:raise ValueError('owner_generation_mismatch')
        if row['event_id'] in rows:raise ValueError('duplicate_owner_event')
        rows[row['event_id']]={'workspace':row,'sha256':digest}
    validate_generation_clocks(manifest,{k:v['workspace'] for k,v in rows.items()})
    return {'manifest':manifest,'manifest_sha256':sha256(raw).hexdigest(),'rows':rows}


def _project_fact(fact, workspace, source, *, owner_ref):
    metric=fact.get('metric')
    if fact.get('typed_absence'):return None
    supplement=source.get('kind')=='issuer_supplement'
    ticker=next(t for t in DEFENSE_TICKERS if defense_issuer(t).company_id==workspace['issuer']['company_id'])
    financial_rules=financial_fact_rules(ticker,workspace['fiscal_period']['year'],workspace['fiscal_period']['quarter'])
    if isinstance(metric,str) and metric.startswith('issuer_') and metric not in financial_rules:
        raise ValueError('financial_profile_subject_period_unqualified')
    if metric not in _FACT_CLASSES and metric not in _F2_NUMERIC and metric not in financial_rules and not supplement:return None
    if fact.get('schema')!='event_fact.v1' or fact.get('event_id')!=workspace['event_id'] or fact.get('fact_id')!=workspace['event_id']+':'+metric:raise ValueError('fact_event_mismatch')
    ticker=next(t for t in DEFENSE_TICKERS if defense_issuer(t).company_id==workspace['issuer']['company_id'])
    period=f"{workspace['fiscal_period']['year']}Q{workspace['fiscal_period']['quarter']}"
    expected_unit='percent' if metric.endswith('margin') else 'USD_million'
    basis='issuer_reported_segment:'+SEGMENTS[ticker]+':reported'
    fact_class=_FACT_CLASSES.get(metric)
    if metric in _F2_NUMERIC:
        if ticker!='NOC':raise ValueError('F2_adverse_subject_or_period_unqualified')
        fact_class,expected_unit,basis,period_relation=_F2_NUMERIC[metric]
        year=workspace['fiscal_period']['year']-(1 if period_relation=='prior' else 0)
        period=f"{year}Q{workspace['fiscal_period']['quarter']}"
    if metric in financial_rules:
        fact_class,expected_unit,basis,period=financial_rules[metric]
    numeric_supplement=False
    if supplement:
        from engine.company_intelligence.issuer_supplements import _rules,validate_supplement_source
        validate_supplement_source(source,event_id=workspace['event_id'])
        if source['supplement_profile']=='LMT_RMS':
            if ticker!='LMT':raise ValueError('supplement_fact_subject_mismatch')
            if (workspace['fiscal_period']['year'],workspace['fiscal_period']['quarter'])!=(2026,2):
                raise ValueError('RMS_workspace_fiscal_period_mismatch')
            rules=rms_numeric_rules()
            if metric not in rules:return None
            fact_class,expected_unit,basis,period=rules[metric]
            numeric_supplement=True
            if fact.get('fact_class')!=fact_class:raise ValueError('RMS_fact_class_mismatch')
        else:
            if ticker!='LHX':raise ValueError('supplement_fact_subject_mismatch')
            rules={v[0]:v for v in _rules(source['supplement_profile'])}
            if metric not in rules:return None
            _,phrase,second,fact_class,basis=rules[metric]
            expected_unit='source_reported_terms'
            period=source['source_document']['presented_fiscal_label']
    if fact.get('period')!=period or fact.get('unit')!=expected_unit or fact.get('basis')!=basis:raise ValueError('fact_basis_period_unit_mismatch')
    span=fact.get('source_span') or {};receipt=span.get('receipt') or {}
    if span.get('schema')!='source_span.v1' or span.get('receipt_state')!='byte_replayed' or span.get('rights_profile')!='rp_public_primary_v1':raise ValueError('fact_receipt_or_rights_unqualified')
    if span.get('document_id')!=source['document_id'] or receipt.get('source_sha256')!=source['source_sha256'] or receipt.get('segment_sha256')!=source['source_sha256']:raise ValueError('fact_source_document_mismatch')
    excerpt=span.get('display_excerpt')
    if supplement and not numeric_supplement:
        from engine.fundamental_forensics.disclosure_diff import normalize_filing
        normalized=normalize_filing({'content':excerpt,'accession':source['document_id']})
        blocks=[b for b in normalized.blocks if not b.table and b.text==fact.get('value') and phrase in b.text and (second is None or second in b.text)]
        if len(blocks)!=1 or fact.get('fact_class')!=fact_class:raise ValueError('supplement_value_not_owner_clause')
    else:
        if numeric_supplement:
            from engine.company_intelligence.rms_segment_profile import receipt_value
            parsed_value=receipt_value(excerpt,metric)
            if parsed_value!=fact.get('value'):raise ValueError('fact_value_not_owner_literal')
        else:
            parsed=parse_numeric(excerpt) if isinstance(excerpt,str) else None
            if parsed is None or parsed[0]!=fact.get('value'):raise ValueError('fact_value_not_owner_literal')
    excerpt_hash=sha256(excerpt.encode()).hexdigest()
    if span.get('text_sha256')!=excerpt_hash or receipt.get('text_sha256')!=excerpt_hash:raise ValueError('fact_text_hash_mismatch')
    start,end=receipt.get('span_start_byte'),receipt.get('span_end_byte')
    if isinstance(start,bool) or isinstance(end,bool) or not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=receipt.get('segment_bytes',-1) or end-start!=len(excerpt.encode()):raise ValueError('fact_byte_bounds_invalid')
    locator=span.get('locator') or {}
    if locator.get('span_start_byte')!=start or locator.get('span_end_byte')!=end:raise ValueError('fact_locator_mismatch')
    return {'fact_id':fact['fact_id'],'value':fact['value'],'unit':expected_unit,'period':period,
            'accounting_basis':basis,'fact_class':fact_class,'owner_ref':owner_ref,
            'source_span':dict(receipt_state='byte_replayed',text_sha256=excerpt_hash,document_id=source['document_id'],span_id=span['span_id'],source_url=source['url'])}


def build_defense_economics_payload(root, *, generated_at=None, as_of=None, owner_inputs=None,
                                    require_market_owner=False, government_inputs=None, participation_inputs=None):
    """Compose from a verified local owner mirror, or explicit owner snapshot.

    Explicit inputs have the exact same owner manifest+row receipt shape; this
    is a producer seam, never an HTTP input. Missing mirrors produce typed
    owner absences for offline fixtures. Live production requires the complete
    qualified local market and financial mirrors. A present market receipt is
    consumed in ordinary local builds too; this reader never hydrates or fetches.
    Invalid or contradictory owner receipts fail closed before publication.
    """
    clock=generated_at or as_of
    if clock is None:raise ValueError('generated_at_or_as_of_required')
    cutoff=_instant(as_of or clock)
    if owner_inputs is not None and not isinstance(owner_inputs,dict):raise ValueError('owner_snapshot_must_be_mapping')
    if cutoff>_instant(clock):raise ValueError('cutoff_after_generation')
    if not isinstance(require_market_owner,bool):raise ValueError('require_market_owner_must_be_boolean')
    market_receipt=Path(root)/'data/massive_stock_day/.defense_read/read_receipt.json'
    use_market=require_market_owner or market_receipt.exists() or market_receipt.is_symlink()
    snapshot=load_defense_owner_snapshot(root) if owner_inputs is None else owner_inputs
    inputs={};bindings={}
    if snapshot is None:
        if use_market:raise ValueError('required_financial_owner_mirror_missing')
        return compose_defense_economics(inputs,generated_at=clock,source_bindings=bindings)
    manifest=snapshot['manifest'];validate_workspace_manifest(manifest)
    if sha256(canonical_json_bytes(manifest)).hexdigest()!=snapshot.get('manifest_sha256'):
        raise ValueError('owner_manifest_hash_mismatch')
    expected_files={'workspaces/'+event_id+'.json' for event_id in snapshot['rows']}
    if expected_files!=set(manifest['files']):raise ValueError('owner_snapshot_incomplete')
    for event_id,held in snapshot['rows'].items():
        row=held['workspace'];validate_event_workspace(row)
        if row['event_id']!=event_id:raise ValueError('owner_event_key_mismatch')
        receipt=manifest['files'].get('workspaces/'+event_id+'.json')
        if receipt is None or receipt['sha256']!=held['sha256'] or sha256(canonical_json_bytes(row)).hexdigest()!=held['sha256'] or row.get('generation_id')!=manifest['generation_id']:
            raise ValueError('owner_manifest_receipt_mismatch')
    if any(event_id not in snapshot['rows'] for event_id in manifest['aliases'].values()):raise ValueError('owner_alias_target_missing')
    validate_generation_clocks(manifest,{k:v['workspace'] for k,v in snapshot['rows'].items()})
    for ticker in DEFENSE_TICKERS:
        try:selected=select_current_event_from_aliases(ticker,manifest['aliases'])
        except WorkspaceError as exc:
            if 'does not cover' in str(exc):continue
            raise
        event_id=selected.event_id
        held=snapshot['rows'][event_id];workspace=held['workspace'];validate_event_workspace(workspace)
        issuer=defense_issuer(ticker);subject=workspace['issuer']
        if subject['company_id']!=issuer.company_id:raise ValueError('owner_subject_mismatch')
        listings=[v for v in subject['listings'] if v['ticker']==ticker and v['mic']=='XNYS']
        if len(listings)!=1:raise ValueError('owner_listing_unqualified')
        security=listings[0]['security_id']
        lifecycle=workspace['lifecycle'];observed=lifecycle['observed_at'];available=lifecycle['source_available_at']
        if _instant(observed)>cutoff or _instant(available)>cutoff:continue
        sources=[s for s in workspace['sources'] if s.get('kind')=='issuer_release']
        if len(sources)!=1:raise ValueError('issuer_release_missing_or_ambiguous')
        source=sources[0]
        if source.get('filing_key',{}).get('cik')!=issuer.cik or source.get('receipt_state')!='byte_replayed':raise ValueError('owner_filing_identity_unqualified')
        ref='event_workspace:'+manifest['generation_id']+':'+event_id
        bindings[ref]={'sha256':held['sha256'],'content_id':manifest['generation_id'],'contract':'event_workspace.v1','owner_family':'company_intelligence','issuer_id':issuer.company_id,'security_id':security,'periods':[f"{workspace['fiscal_period']['year']}Q{workspace['fiscal_period']['quarter']}"],'observed_at':observed,'source_available_at':available,'owner_admission_ref':ref}
        facts=[]
        source_by_document={s.get('document_id'):s for s in workspace['sources'] if s.get('receipt_state')=='byte_replayed'}
        for fact in workspace['facts']:
            fact_source=source_by_document.get((fact.get('source_span') or {}).get('document_id'))
            if fact_source is None:
                if fact.get('metric') in _FACT_CLASSES or fact.get('metric') in _F2_NUMERIC or fact.get('metric') in _SUPPLEMENT_METRICS or str(fact.get('metric','')).startswith('issuer_'):
                    if not fact.get('typed_absence'):raise ValueError('financial_fact_source_document_unbound')
                continue
            fact_ref=ref
            if fact_source.get('kind')=='issuer_supplement':
                from engine.company_intelligence.issuer_supplements import validate_supplement_source
                doc_observed,doc_available=validate_supplement_source(fact_source,event_id=event_id)
                if doc_observed>cutoff or doc_available>cutoff:continue
                fact_ref=ref+':'+fact_source['document_id']
                bindings[fact_ref]={**bindings[ref],'observed_at':fact_source['source_clock']['observed_at'],
                    'source_available_at':fact_source['source_clock']['available_at'],
                    'periods':[fact_source['source_document']['presented_fiscal_label']],
                    'owner_admission_ref':fact_ref}
            projected=_project_fact(fact,workspace,fact_source,owner_ref=fact_ref)
            if projected is not None:
                if projected['period'] not in bindings[fact_ref]['periods']:
                    bindings[fact_ref]['periods'].append(projected['period'])
                facts.append(projected)
        if len({v['fact_id'] for v in facts})!=len(facts):raise ValueError('duplicate_financial_fact')
        core_count=sum(v['fact_id'].rsplit(':',1)[-1] in METRICS for v in facts)
        state='supported' if core_count==3 else 'partial'
        observed=max((bindings[f['owner_ref']]['observed_at'] for f in facts),key=_instant,default=observed)
        period=bindings[ref]['periods'][0]
        inputs[ticker]={'identity':{'identity_mode':'current','issuer_binding':{'issuer_id':issuer.company_id},'security_id':security},'identity_owner_ref':ref,'name':subject['display_name'],
            'axes':{'economics':{'state':state,'summary_en':f'{SEGMENTS[ticker]}: {period} reported segment context.','summary_zh':f'{SEGMENTS[ticker]}：{period} 报告分部资料。','owner_ref':ref,'evidence_refs':[ref],'observed_at':observed,'fiscal_period':period,'reason_code':'reported_segment_context','facts':facts,'limitations':['segment_not_program_workshare','shareholder_capture_not_asserted','historical_pit_not_admitted']+(['reported_operating_profit_unavailable'] if core_count<3 else []),'display_scope':'government_revenue_entitled'}},
            'contrary_case':'Segment sales and margin do not establish program workshare or shareholder capture.',
            'contrary_case_zh':'分部销售额及利润率不能证明项目份额或股东获益。',
            'next_condition_zh':'核实公司的合约范围及利润率证据，关注下一份公司报告，并独立查看已观察到的市场反应。',
            'invalidation_zh':'来源修订、发行人或证券不匹配，或字节凭据核验失败，均使引用数值失效。',
            'next_condition':'Confirm contract scope and margin evidence; watch the next company report; review observed market response separately.',
            'invalidation':'Source revision, issuer/security mismatch, or a failed byte receipt invalidates the quoted fact.'}
    if 'NOC' in inputs and any(f['fact_id'].endswith(':siaw_unfavorable_eac') for f in inputs['NOC']['axes']['economics']['facts']):
        index={f['fact_id'].rsplit(':',1)[-1]:f for f in inputs['NOC']['axes']['economics']['facts']}
        adverse=index.get('siaw_unfavorable_eac');prior=index.get('sentinel_prior_favorable_eac')
        if adverse is not None and prior is not None:
            inputs['NOC']['contrary_case']=f"The issuer reports a ${format(adverse['value'],',g')} million unfavorable SiAW EAC adjustment in {adverse['period'][4:]} {adverse['period'][:4]}; the ${format(prior['value'],',g')} million favorable Sentinel comparison belongs to {prior['period'][4:]} {prior['period'][:4]}."
            inputs['NOC']['contrary_case_zh']=f"发行人报告{adverse['period']}SiAW有{format(adverse['value'],',g')}百万美元不利EAC调整；{format(prior['value'],',g')}百万美元有利Sentinel调整属于{prior['period']}对比期。"
    if 'LHX' in inputs and any(f['fact_id'].endswith(':space_business_sale_completed_terms') for f in inputs['LHX']['axes']['economics']['facts']):
        inputs['LHX']['contrary_case']='Preferred payout and conditional conversion terms affect common-shareholder transmission. The completed space-business sale has a different scope and value basis from the prior pending transaction.'
        inputs['LHX']['contrary_case_zh']='优先股支付及有条件转换条款影响普通股股东获益路径。已完成航天业务出售的范围及价值口径，与此前待完成交易分别记录。'
    government=qualify_government_context(
        load_government_context_inputs(root) if government_inputs is None else government_inputs,
        inputs,generated_at=clock,
    )
    if set(bindings).intersection(government['source_bindings']):raise ValueError('government_owner_binding_collision')
    bindings.update(government['source_bindings'])
    for ticker,axes in government['axes_by_ticker'].items():
        inputs[ticker]['axes'].update(axes)
    participation=qualify_participation_context(participation_inputs,inputs,generated_at=clock)
    if set(bindings).intersection(participation['source_bindings']):raise ValueError('participation_owner_binding_collision')
    bindings.update(participation['source_bindings'])
    for ticker,axes in participation['axes_by_ticker'].items():
        inputs[ticker]['axes'].update(axes)
    for ticker,data in inputs.items():
        interpretation=build_defense_interpretation(ticker,data['axes']['economics']['facts'])
        if interpretation is None:continue
        data['interpretation']=interpretation
        data['invalidation']=interpretation['scenarios'][0]['invalidation_en']+' A source or identity correction also requires requalification.'
        data['invalidation_zh']=interpretation['scenarios'][0]['invalidation_zh']+' 来源或身份更正也需要重新核验。'
        if ticker=='NOC':
            data['next_condition']='Watch new EAC revisions and reported margin; qualify delivery, cost recovery and cash evidence separately.'
            data['next_condition_zh']='关注新的EAC修订及已披露利润率；分别核验交付、成本回收及现金证据。'
        elif ticker=='LHX':
            data['next_condition']='Watch the contractual QIPO, milestone and redemption conditions, retained business scope and subsequent cash disclosures.'
            data['next_condition_zh']='关注合约QIPO、里程碑及赎回条件、保留业务范围，以及后续现金披露。'
        else:
            data['next_condition']='Confirm contract scope and delivery, then review reported margin and cash conversion; evaluate observed market context separately.'
            data['next_condition_zh']='先核实合约范围及交付，再检视已披露利润率及现金转化；独立评估已观察到的市场背景。'
    if use_market:
        # Reuse the verified financial snapshot and its selected subject inputs.
        # A missing/cutoff-excluded quartet cannot admit a price-only profile.
        if any(ticker not in inputs for ticker in DEFENSE_TICKERS):
            raise ValueError('required_market_financial_subject_missing')
        prices,reference=load_defense_market_inputs(root,rights_ref=_MARKET_RIGHTS_REF)
        market=compose_defense_market_context(
            prices,snapshot,reference,_MARKET_RIGHTS_REF,generated_at=clock,
        )
        for ticker in DEFENSE_TICKERS:
            axis=market['recognition_by_ticker'][ticker]
            binding=market['source_bindings'][axis['owner_ref']]
            identity=inputs[ticker]['identity']
            if (binding['issuer_id']!=identity['issuer_binding']['issuer_id']
                    or binding['security_id']!=identity['security_id']
                    or axis['price_response']['security_id']!=identity['security_id']):
                raise ValueError('market_financial_subject_mismatch')
        if set(bindings).intersection(market['source_bindings']):
            raise ValueError('market_owner_binding_collision')
        bindings.update(market['source_bindings'])
        for ticker in DEFENSE_TICKERS:
            inputs[ticker]['axes']['recognition']=market['recognition_by_ticker'][ticker]
        # Raw envelopes remain local proof; only closed derived legs are composed.
    return compose_defense_economics(inputs,generated_at=clock,source_bindings=bindings)
