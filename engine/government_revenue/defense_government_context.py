"""Bounded issuer context from the incumbent prime dossier/exact recipient owner.

No collector ticker, name, programme inference, amount allocation, score,
acquisition, store, ledger or effects. Current graph review is never backdated
into the retained source dossier. Source and attribution clocks are distinct.
"""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from urllib.parse import urlparse
import json,re
from engine.government_revenue.dossiers import is_valid_dossier_payload
from engine.government_revenue import entity_resolution as er
from engine.company_intelligence.defense_profiles import defense_issuer,DEFENSE_TICKERS


def _instant(value):
    value=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('government_context_clock_timezone_required')
    return value


def _canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def load_government_context_inputs(root):
    """Read incumbent files only. Absent offline mirrors remain typed absent."""
    base=Path(root)/'data/government_revenue';paths={'dossier':base/'dossiers.json','recipient_graph':base/'recipient_entity_graph.json'}
    if not all(p.is_file() for p in paths.values()):return None
    raw={k:p.read_bytes() for k,p in paths.items()}
    return {**{k:json.loads(v) for k,v in raw.items()},'raw_bytes':raw,'file_sha256':{k:sha256(v).hexdigest() for k,v in raw.items()}}


def _issuer_cik_proof(ticker,graph):
    """The reviewed issuer-company SEC evidence must match financial native CIK."""
    rows=[r for r in graph['companies'] if r['ticker']==ticker and r['company_id']=='central:'+ticker]
    if len(rows)!=1:return False
    evidence={r['evidence_id']:r for r in graph['evidence']};expected=int(defense_issuer(ticker).cik)
    for ref in rows[0]['evidence_refs']:
        item=evidence[ref];url=urlparse(item['url']);match=re.match(r'^/Archives/edgar/data/(\d+)/',url.path)
        if item['publisher']=='SEC' and url.scheme=='https' and url.hostname=='www.sec.gov' and match and int(match.group(1))==expected and 'public_company' in item['claim_scopes']:
            return True
    return False


def qualify_government_context(inputs,financial_inputs,*,generated_at):
    """Use the existing strict graph owner and exact-ID resolver at current cut.

    The output is bounded dated prime-award presence, never a programme role or
    forward demand/cash estimate. Full dossiers are validated before selection.
    """
    if inputs is None:return {'axes_by_ticker':{},'source_bindings':{},'local_proof':{'state':'owner_absent'}}
    cutoff=_instant(generated_at);dossier=inputs['dossier'];graph=inputs['recipient_graph']
    if not is_valid_dossier_payload(dossier):raise ValueError('government_context_dossier_invalid')
    if _instant(dossier['known_at'])>cutoff:raise ValueError('government_context_dossier_after_cutoff')
    loaded=er.load_recipient_entity_graph(graph,as_of=generated_at)
    if loaded['status']!='ready':raise ValueError('government_context_graph_not_ready')
    graph_clock=graph['graph_known_at'];_instant(graph_clock)
    raw=inputs.get('raw_bytes') or {'dossier':_canonical(dossier),'recipient_graph':_canonical(graph)}
    if set(raw)!={'dossier','recipient_graph'} or any(not isinstance(v,bytes) or json.loads(v)!=inputs[k] for k,v in raw.items()):raise ValueError('government_context_owner_bytes_mismatch')
    digests={k:sha256(v).hexdigest() for k,v in raw.items()}
    if inputs.get('file_sha256') is not None and inputs['file_sha256']!=digests:raise ValueError('government_context_owner_receipt_invalid')
    wanted={t for t in DEFENSE_TICKERS if t in financial_inputs and _issuer_cik_proof(t,graph)}
    # Prefilter by declared reviewed exact identifiers, never collection bucket.
    ids={r['value'] for r in graph['identifiers'] if r['namespace']=='sam_uei'}
    selected={};proof={}
    awards=sorted(dossier['awards'],key=lambda a:(a['dates'].get('known_at') or '',a['dates'].get('effective_at') or '',a['award_key']),reverse=True)
    for award in awards:
        native=award['identity'].get('generated_award_id');uei=award['recipient'].get('uei')
        if not native or uei not in ids:continue
        known=award['dates']['known_at'];effective=award['dates']['effective_at']
        if not known or not effective:continue
        if _instant(known)>cutoff:continue
        record={'generated_unique_award_id':native,'recipient_uei':uei,'effective_at':effective,'known_at':known}
        # The normalized graph is produced by the strict owner above, at THIS
        # cutoff, within this pure call; no marker/capsule is forged or retained.
        resolution=er.resolve_recipient(record,loaded['graph'],as_of=generated_at)
        issuer=resolution.get('issuer') or {};ticker=issuer.get('ticker')
        if ticker not in wanted or ticker in selected or resolution['resolution_state'] not in ('confirmed','reviewed') or issuer.get('company_id')!='central:'+ticker:continue
        if not resolution['source_identity_stable'] or not resolution['ownership_path'] or any(p['relationship'] not in ('issuer_legal_entity','wholly_owned') for p in resolution['ownership_path']):continue
        selected[ticker]=(award,resolution);proof[ticker]={'award_key':award['award_key'],'native_award_id':native,'recipient_uei':uei,'record_known_at':known,'event_effective_at':effective,'current_graph_review_clock':graph_clock,'resolution':resolution}
        if set(selected)==wanted:break
    axes={};bindings={}
    for ticker,(award,resolution) in selected.items():
        identity=financial_inputs[ticker]['identity'];issuer=identity['issuer_binding']['issuer_id'];security=identity['security_id']
        expected=defense_issuer(ticker)
        if issuer!=expected.company_id or security not in expected.security_ids_at(cutoff.date()):raise ValueError('government_financial_issuer_mismatch')
        dref='government_dossier:'+dossier['content_id']+':'+ticker+':'+award['award_key']
        gref='recipient_graph:'+graph['graph_id']+':'+ticker
        observed=max((award['dates']['known_at'],graph_clock),key=_instant)
        binding={'owner_family':'government_revenue','issuer_id':issuer,'security_id':security,'periods':[]}
        bindings[dref]={**binding,'sha256':digests['dossier'],'content_id':dossier['content_id'],'contract':dossier['contract'],'observed_at':award['dates']['known_at'],'owner_admission_ref':resolution['record_key']}
        bindings[gref]={**binding,'sha256':digests['recipient_graph'],'content_id':graph['graph_id'],'contract':graph['contract'],'observed_at':graph_clock,'owner_admission_ref':resolution['recipient_entity_id']}
        # A retained source cutoff before this analysis is visibly dated. It
        # cannot acquire freshness from the newer attribution-review clock.
        stale=_instant(award['dates']['known_at']).date()<cutoff.astimezone(timezone.utc).date()
        state='stale' if stale else 'partial'
        source_observed_at=award['dates']['known_at']
        shared={'display_scope':'government_revenue_entitled','state':state,'owner_ref':dref,'evidence_refs':[dref,gref],'observed_at':observed,'fiscal_period':None,'facts':[],
            'limitations':['dated_prime_observation','program_role_not_qualified','program_workshare_not_disclosed','government_amount_not_revenue','common_shareholder_capture_unknown','current_graph_review_not_historical_admission']}
        # Native signed actions are observable procurement history, not new
        # company orders. This classification uses only this exact award's
        # admitted action keys; it never uses a ticker collection bucket.
        action_keys=set(award['action_keys'])
        deobligation=any(a['action_key'] in action_keys and isinstance(a.get('obligation'),(int,float)) and not isinstance(a.get('obligation'),bool) and a['obligation']<0 for a in dossier['actions'])
        detail_en=' A signed negative obligation (deobligation) is present on this exact award.' if deobligation else ' Award presence alone is not a new-order observation.'
        detail_zh=' 该精确合约含有负数义务额（撤减义务）的已存行动。' if deobligation else ' 合约存在本身并非新增订单观测。'
        proof[ticker]['has_native_signed_deobligation']=deobligation
        axes[ticker]={
            'demand':{**shared,'summary_en':f'Reviewed exact recipient paths connect stored federal prime-award observations to the issuer group; selected-program role and workshare remain unknown. These are procurement context, not new orders, reported backlog or forecast revenue/cash. Period extensions change timing; deobligations reduce recorded obligations. Source observation {source_observed_at}; current attribution review is separate.'+detail_en,
                'summary_zh':f'已审核精确收款方路径将已存联邦主合约观测连接至发行人集团；所选项目角色及份额仍未知。它们属于采购背景，并非新增订单、已披露积压订单或收入／现金预测。期限延长改变时间，撤减义务降低已记义务额。来源观测时间{source_observed_at}；当前归属审核另列。'+detail_zh,'reason_code':'dated_award_presence_not_forward_demand'}}
    return {'axes_by_ticker':axes,'source_bindings':bindings,'local_proof':{'state':'qualified_bounded_prime_context','source_as_of':dossier['as_of'],'source_known_at':dossier['known_at'],'current_graph_review_clock':graph_clock,'analysis_cutoff':generated_at,'selected':proof,'did_use_collection_ticker':False,'did_use_materiality_or_score':False,'did_allocate_amounts':False}}
