#!/usr/bin/env python3
"""Build the F03 review directory from immutable audit inputs; never edit a registry or Paper.

This generator produces audit metadata and a local review artifact only. The canonical
registry/exporter, Paper adapter, RIG and runtime retain their existing ownership.
"""
from __future__ import annotations
import argparse, collections, copy, csv, gzip, hashlib, html, json, re, shutil
from pathlib import Path
from page_observations import attach_page_observations

PACKAGE = '6e1862867193ec6486a22001a0e4fb515da20448'
PROCEDURE = 'c57adacb338fe837c7d585f1e372c64d9b0118ec'
MACRO = 'b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e'
TERMINAL = 'b79b1e136290978ff7675087de979bb1b42b3713'
BASE = 'https://github.com/mastermindx-market-intelligence/macro/blob/' + PACKAGE + '/research/design_candidates/production_design_20261102/'
ROLE = {
 'candidate/workspace; approval evidence not inferred':'candidate_unqualified',
 'held reference; not admitted for build':'held',
 'historical archive label; verify lineage before moving':'historical',
 'move/redirect notice; preserve successor linkage':'redirect',
 'reference; approval evidence not inferred':'reference_unqualified',
 'rejected reference; retain rejection rationale':'rejected',
 'source evidence; not automatically editable/approved':'source_only',
 'specification/reference; reconcile with current candidate':'specification',
}
ZH = {
 'P00':'Paper 访问与写入资格','F01':'共享外壳与导航','F02':'设计系统','F03':'设计目录与整合',
 'D01':'今日概览','D02':'宏观、风险与事件','D03':'美股与 Prophet','D04':'发现与热力图','D05':'板块与轮动',
 'D06':'终端与图表','D07':'公司、财报与预期','D08':'期权平台整合','D08A':'期权概览与资金流',
 'D08B':'期权敞口与波动率','D08C':'期权计划与复盘','D08D':'期货与股票回放','D09':'资金流与机构持仓',
 'D10':'新闻与简报','D11':'研究库与情报中心','D12':'市场记忆与策略证据','D13':'GMI 与市场本体',
 'D14':'Mastermind AI','D15':'债券与信用','D16':'外汇','D17':'商品与能源','D18':'加密资产',
 'D19':'中国市场','D20':'香港与加拿大','D21':'国际市场与国家周期','D22':'组合与配置',
 'D23':'监控、自选与提醒','D24':'专业与催化剂情报','D25':'账户与帮助','D26':'公共网站与学习','D27':'内部 OS 与管理','QA01':'独立复核',
}

def load(p): return json.loads(p.read_text())
def dump(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n')
def git_blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def md(s): return str(s).replace('|','\\|').replace('\n',' ')
def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(md(x) for x in row)+' |' for row in rows])+'\n'


RETURN_FIELDS = frozenset({
    'source_contract', 'source_contract_label', 'candidate_ref', 'rig_state',
    'rig_receipt', 'shell_version', 'system_version', 'status', 'next_action',
    'return_observation',
})

def apply_assignment_returns(sessions, curation):
    """Evidence-only overlay; never edits frozen identity, ownership or access."""
    by_id = {s['id']: s for s in sessions}
    returns = curation.get('assignment_returns', {})
    assert set(returns) <= set(by_id), 'return names an unknown assignment'
    assert {s['id'] for s in sessions if s.get('return_observation')} <= set(returns), 'omitted return requires an explicit withdrawal/retention observation'
    pending = []
    before = {sid: {k: v for k, v in s.items() if k not in RETURN_FIELDS}
              for sid, s in by_id.items()}
    for sid, row in returns.items():
        assert set(row) == RETURN_FIELDS, 'return requires the complete explicit evidence field set'
        obs = row['return_observation']
        head = obs['source_head']
        assert re.fullmatch(r'[0-9a-f]{40}', head), 'return requires immutable source'
        link = row['source_contract']
        assert re.fullmatch(r'https://github\.com/mastermindx-market-intelligence/macro/blob/[0-9a-f]{40}/[A-Za-z0-9_./-]+', link), 'invalid source URL'
        assert '/blob/' + head + '/' in link, 'source pin and link disagree'
        assert not any(part in ('.', '..') for part in link.split('/')), 'source path cannot normalize outside its immutable pin'
        assert row.get('rig_receipt') is None and row.get('rig_state') == 'draft', 'observation overlay cannot grant approval'
        candidate = row.get('candidate_ref')
        if candidate:
            expected = 'https://app.paper.design/file/' + obs['candidate_file_id'] + '/' + obs['candidate_page_id']
            assert candidate == expected, 'candidate identity/link mismatch'
        else:
            assert obs['candidate_file_id'] is None and obs['candidate_page_id'] is None, 'absent candidate must have absent native identity'
        for field in ('readme_url', 'retained_reference_url'):
            value = obs.get(field)
            assert value is None or re.fullmatch(r'https://app\.paper\.design/file/[A-Z0-9]+/p-[A-Za-z0-9-]+', value), 'invalid Paper evidence URL'
        if obs.get('readme_url'):
            assert obs['readme_url'] == 'https://app.paper.design/file/' + obs['readme_file_id'] + '/' + obs['readme_page_id'], 'Read me identity/link mismatch'
            assert obs.get('retained_reference_url') != obs['readme_url'], 'current Read me is not retained original evidence'
        else:
            assert all(obs.get(k) is None for k in ('readme_file_id', 'readme_page_id', 'readme_board_id')), 'absent Read me must have absent identity'
        pending.append((sid, copy.deepcopy(row)))
    for sid, row in pending:
        by_id[sid].update(row)
    assert before == {sid: {k: v for k, v in s.items() if k not in RETURN_FIELDS}
                      for sid, s in by_id.items()}, 'overlay changed frozen assignment fields'
    return sessions

def observe_directory_progress(data, out):
    """Current effects come from the existing native log, never from curation."""
    meta = data['metadata']
    native_path = out / 'paper' / 'native-progress.json'
    if native_path.exists():
        native = load(native_path)
        operation_ids = [op['operation_id'] for op in native['operations']]
        assert len(operation_ids) == len(set(operation_ids)), 'duplicate native operation IDs'
        unresolved = [op['operation_id'] for op in native['operations'] if op['state'] == 'EFFECT_UNKNOWN']
        recorded_unresolved = [op['operation_id'] for op in native['unresolved_effects']]
        assert len(recorded_unresolved) == len(set(recorded_unresolved)), 'duplicate unresolved operation IDs'
        assert set(unresolved) == set(recorded_unresolved), 'native unresolved-effect ledger mismatch'
        applied = sum(op['state'] == 'APPLIED_RESPONSE_OBSERVED' for op in native['operations'])
        meta['directory']['paper_mutations'] = applied
        meta['directory']['paper_unresolved_effects'] = len(unresolved)
        meta['directory']['paper_unresolved_operation_ids'] = unresolved
        meta['paper_application'] = ('PARTIAL_NATIVE_EFFECT_UNKNOWN__RESOURCE_ACTIONS_NOT_DISPATCHED' if unresolved
                                     else 'DIRECTORY_EDITS_OBSERVED__RESOURCE_ACTIONS_NOT_DISPATCHED' if applied
                                     else 'NOT_APPLIED_TO_PAPER')
        meta['native_effect_evidence'] = 'paper/native-progress.json'
        meta['continuation_procedure_sha'] = native.get('continuation_protected_procedure', native.get('protected_procedure'))
        meta['native_effect_observed_at'] = native['observed_at']
    meta['assignment_return_observations'] = [
        {'id': s['id'], 'observed_at_utc': s['return_observation']['observed_at_utc'],
         'source_head': s['return_observation']['source_head']}
        for s in data['sessions'] if s.get('return_observation')]
    meta['baseline_scope_note'] = 'Original 299 listed pages + two observations and 2450 boards remain frozen; later returns are separate observations, not a recensus.'
    f03 = next(s for s in data['sessions'] if s['id'] == 'F03')
    f03['source_contract_label'] = 'F03 organization contract'
    if meta['directory']['paper_mutations']:
        f03['candidate_ref'] = 'https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1P-0'
        f03['status'] = 'Directory refinements observed; all 301 cross-file organization actions NOT_DISPATCHED; reference approval absent'
        f03['next_action'] = 'Continue safe source/design work with self-QA; formal RIG/release gates are separate. Resource actions require supported-operation qualification and preservation evidence.'
        if meta['directory'].get('paper_unresolved_effects'):
            f03['status'] = 'PARTIAL: ' + str(meta['directory']['paper_unresolved_effects']) + ' native operation outcome unconfirmed; ' + f03['status']
            f03['next_action'] = 'Reconcile the exact original-carrier pending operation before further Paper writes. Continue independent source work; do not replay, change carrier or infer acceptance.'

def builder_entry(s):
    """Source return and native/reference approval are intentionally independent."""
    obs = s.get('return_observation') or {}
    candidate = ('[Observed candidate / directory](' + s['candidate_ref'] + ')'
                 if s.get('candidate_ref') else 'New native candidate not admitted or not established by this return.')
    contract = s.get('source_contract')
    if contract == 'CONTRACT.md': contract = '../CONTRACT.md'
    contract_text = ('[' + s.get('source_contract_label', 'Returned source/build package') + '](' + contract + ')'
                     if contract else 'Not returned; the original assignment is requirements, not a completed build contract.')
    text = '**Candidate:** ' + candidate + '\n\n'
    if obs.get('candidate_file_id'):
        text += '**Candidate identity:** `' + obs['candidate_file_id'] + ' / ' + obs['candidate_page_id'] + '`.\n\n'
    if obs.get('readme_url'):
        text += '[Read me / candidate entry](' + obs['readme_url'] + ')\n\n'
        text += '**Read me identity:** `' + ' / '.join(x for x in (obs['readme_file_id'], obs['readme_page_id'], obs.get('readme_board_id')) if x) + '`.\n\n'
    if obs.get('retained_reference_url'):
        text += '[Retained original reference](' + obs['retained_reference_url'] + ') — not promoted to an approved candidate.\n\n'
    text += '**Returned contract / package:** ' + contract_text + '\n\n'
    text += '**Approval:** No approved candidate established in the inspected package. RIG receipt not observed; state: ' + (s.get('rig_state') or 'unobserved') + '. A displayed assignment is not live writer custody.\n\n'
    text += '**Shell/system:** ' + (s.get('shell_version') or 'F01 final release not observed') + ' / ' + (s.get('system_version') or 'F02 final release not observed') + '.\n\n'
    text += '**Status:** ' + s['status'] + '\n\n'
    if obs:
        text += '**Return observation:** ' + obs['observed_at_utc'] + '; immutable source `' + obs['source_head'] + '`. This does not refresh the original inventory or certify contract completeness.\n\n'
    text += '**Next action:** ' + s['next_action'] + '\n\n'
    return text

def refresh_returns(out):
    """Re-render the existing frozen audit bundle without re-running its census."""
    names = {'metadata':'provenance','sessions':'assignment-directory','pages':'paper-page-directory',
             'artboards':'paper-artboard-directory','routes':'route-assignment-projection',
             'source_deltas':'source-delta-projection','destinations':'proposed-destinations',
             'changes':'live-delta','inventory_gaps':'inventory-gaps'}
    data = {key: load(out/'data'/(name+'.json')) for key, name in names.items()}
    assert len(data['sessions']) == 36 and len(data['routes']) == 348
    assert len(data['source_deltas']) == 9 and all(x['canonical_registry_id'] is None for x in data['source_deltas'])
    assert len(data['pages']) == 301 and len(data['artboards']) == 2450
    ledger = load(out/'data/resource-action-ledger.json')
    assert len(ledger) == 301 and all(x['effect_status'] == 'NOT_DISPATCHED' and not x['applied'] for x in ledger)
    curation = load(Path(__file__).with_name('curation.json'))
    apply_assignment_returns(data['sessions'], curation)
    observe_directory_progress(data, out)
    attach_page_observations(data, out)
    dump(out/'data/assignment-directory.json', data['sessions'])
    dump(out/'data/provenance.json', data['metadata'])
    render_directory(out, data, set(curation.get('assignment_returns', {})) | {'F03'})
    print(json.dumps({'status':'RETURN_OBSERVATIONS_REFRESHED_NOT_APPROVED',
                      'assignments':len(data['sessions']), 'returns':len(curation.get('assignment_returns', {})),
                      'canonical_records':len(data['routes']), 'actions_not_dispatched':len(ledger)}))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--inputs',type=Path); ap.add_argument('--evidence',type=Path); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--refresh-returns',action='store_true'); args=ap.parse_args()
    if args.refresh_returns:
        refresh_returns(args.output)
        return
    if args.inputs is None or args.evidence is None:
        ap.error('--inputs and --evidence are required for a full baseline build')
    inp,ev,out=args.inputs,args.evidence,args.output; out.mkdir(parents=True,exist_ok=True)
    blob_map=load(inp/'source-blob-map.json')
    for name,sha in blob_map.items():
        assert git_blob((inp/name).read_bytes())==sha, 'source bytes do not match Git blob: '+name
    files=load(inp/'paper-files.json'); pbase=load(inp/'paper-pages.json'); boards=load(inp/'paper-artboards.json')
    raw_sessions=load(inp/'session-manifest.json'); routes=load(inp/'route-ownership.json')['rows']; deltas=load(inp/'source-delta.json')['rows']
    current=load(inp/'current-registry.json'); live=load(ev/'paper-live-deltas.json')
    inventory=load(ev/'generated-document-inventory.json') if (ev/'generated-document-inventory.json').exists() else json.loads(gzip.decompress((ev/'generated-document-inventory.json.gz').read_bytes()))
    native=load(ev/'native-source-inventory.json')
    assert len(routes)==len({r['page_id'] for r in routes})==348
    assert {r['page_id'] for r in routes}=={r['page_id'] for r in current['pages']}
    assert len(deltas)==9 and len(pbase)==193 and len(boards)==2450
    ids={s['id'] for s in raw_sessions}; assert len(ids)==36
    primary={(p['file_id'],p['page_id']):p for p in pbase}
    bmap=collections.defaultdict(list)
    for b in boards: bmap[(b['file_id'],b['page_id'])].append(b)
    pages=[]
    for f in files:
        for raw in f['pages']:
            key=(f['file_id'],raw['id']); p=primary.get(key); owned=bmap[key]
            pages.append({
              'paper_file_id':f['file_id'],'paper_page_id':raw['id'],'file_name':f['name'],'name':raw['name'],
              'url':'https://app.paper.design/file/'+f['file_id']+'/'+raw['id'],
              'page_custodian':p['primary_session'] if p else 'F03','content_owner':p['primary_session'] if p else None,
              'organization_steward':'F03','role':ROLE[p['observed_role']] if p else 'unexpanded',
              'role_evidence':p['observed_role'] if p else 'listed only; content classification and domain allocation not verified',
              'listed_in_package':True,'expanded_in_package':bool(p),'board_count':len(owned) if p else None,
              'proposed_folder':p['proposed_folder'] if p else None,'proposed_file':p['proposed_working_file'] if p else None,
              'actual_destination':None,'rig_state':None,'rig_receipt':None,'candidate_selection':None,
              'source_contract':None,'predecessor':None,'successor':None,
              'conditions':'Retain original until lineage, comments, annotations, assets, links and current writer overlap are verified.',
              'artboard_owners':sorted({b['primary_session'] for b in owned}),
              'observation':'package structural census; no full visual acceptance',
            })
    assert len(pages)==299
    changes=[]
    for row in live:
        p=row['page']; owner=row.get('assignment_from_existing_route') or row.get('proposed_product_owner')
        pages.append({'paper_file_id':row['file_id'],'paper_page_id':p['pageId'],'file_name':p['fileName'],'name':p['pageName'],
          'url':p['url'],'page_custodian':owner,'content_owner':owner,'organization_steward':'F03','role':'live_delta_unqualified',
          'role_evidence':row['classification'],'listed_in_package':False,'expanded_in_package':False,'board_count':p['artboardCount'],
          'proposed_folder':None,'proposed_file':None,'actual_destination':None,'rig_state':None,'rig_receipt':None,
          'candidate_selection':None,'source_contract':None,'predecessor':None,'successor':None,'conditions':'Do not move or rename; current writer unverified.',
          'artboard_owners':[],'observation':'explicit live read in F03; assignment is existing route owner or proposed family owner, not a live lease'})
        changes.append({'kind':'page_added' if row['file_id']=='01M2WGNCX9475G79JRKJTCM08P' else 'file_observed',
          'file_id':row['file_id'],'page_id':p['pageId'],'name':p['pageName'],'file_name':p['fileName'],'url':p['url'],
          'owner':owner,'owner_basis':'existing registry assignment' if row.get('canonical_route_id') else 'proposed from family; not confirmed custody',
          'board_count':p['artboardCount'],'effect':'OBSERVED_ONLY','next_action':'Domain owner confirms current writer/candidate; F03 preserves exact source location.'})
    assert len({(p['paper_file_id'],p['paper_page_id']) for p in pages})==len(pages)
    board_rows=[{'paper_file_id':b['file_id'],'paper_page_id':b['page_id'],'artboard_id':b['artboard_id'],'name':b['name'],
      'width':b['width'],'height':b['height'],'child_count':b['child_count'],'product_owner':b['primary_session'],
      'page_custodian':b['page_custodian'],'page_url':b['page_url'],'rig_state':None,'rig_receipt':None} for b in boards]
    route_rows=[]
    for r in routes:
        route_rows.append({'canonical_registry_id':r['page_id'],'repo':r['repo'],'route':r['route'],'route_kind':r['route_kind'],
          'primary_session':r['primary_session'],'delegated_slices':r['delegated_design_slices'],'consult_sessions':r['consult_sessions'],
          'source_template':r['source_template'],'builder':r['builder'],'source_evidence':r['source_evidence'],
          'access_shell':r['access_shell'],'payload_tier':r['payload_tier'],'lifecycle':r['lifecycle'],
          'scope_disposition':r['scope_disposition'],'shared_archetype_owner':r['shared_archetype_owner'],'governed_regions':r['governed_regions'],
          'candidate_ref':None,'retention_qualified':None,'rig_state':None,'rig_receipt':None,
          'source_contract_gap':r['source_contract_gap'],'query_alias_contract':'Resolve in owning source; no guessed query/view values',
          'family_inventory':'evidence/generated-document-inventory.json.gz' if r['repo']=='macro' and r['route_kind']=='family' else None})
    delta_rows=[dict(r,canonical_registry_id=None,identity_kind='source_delta_not_canonical_route',
      design_slice='D08D' if r['route']=='/options/equity-replay' else None,
      customer_navigation='excluded' if r['route']=='/dev/options-plan' else 'not admitted by this directory') for r in deltas]
    sessions=[]
    for s in raw_sessions:
        direct=[r for r in route_rows if r['primary_session']==s['id']]
        delegated=[r['canonical_registry_id'] for r in route_rows if s['id'] in r['delegated_slices']]
        refs=[p for p in pages if p['page_custodian']==s['id'] or s['id'] in p['artboard_owners']]
        sessions.append(dict(s,title_zh=ZH[s['id']],canonical_registry_ids=[r['canonical_registry_id'] for r in direct],
          delegated_registry_ids=delegated,source_deltas=[r['route'] for r in delta_rows if r['primary_session']==s['id'] or r['design_slice']==s['id']],
          paper_refs=[{'file_id':p['paper_file_id'],'page_id':p['paper_page_id']} for p in refs],
          handoff_url=BASE+s['handoff'],source_contract='CONTRACT.md' if s['id']=='F03' else None,
          candidate_ref=None,rig_state=None,rig_receipt=None,shell_version=None,system_version=None,
          status='F03 source directory delivered; Paper organization blocked' if s['id']=='F03' else 'Candidate and full contract not returned in inspected package',
          next_action='Consume P00 qualification and exact target overlap evidence' if s['id']=='F03' else 'Return source contract and frozen exact candidate through existing programme owner'))
    destinations=[]
    for s in raw_sessions:
        if s['id']=='P00':continue
        for name in s['proposed_files']:
            source_pages=[p for p in pages if p['proposed_file']==name]
            destinations.append({'name':name,'folder':s['folder'],'owner':s['id'],'actual_file_id':None,'actual_folder_id':None,
              'resolution':'PENDING_VERIFIED_REUSE_OR_CREATION','existing_page_refs':[{'file_id':p['paper_file_id'],'page_id':p['paper_page_id']} for p in source_pages],
              'allocation_gap':not bool(source_pages),'existing_artboards':sum(p['board_count'] or 0 for p in source_pages),
              'rule':'Qualify existing coherent file for reuse before creating a duplicate; do not copy history into working set.'})
    checks=['source_identity','successor_and_retention','comments','annotations','assets','source_links','backlinks_and_redirect',
            'rejection_and_hold_conditions','writer_overlap','destination_fidelity','readback']
    ledger=[]
    for p in pages:
        if p['role']=='redirect': intent='preserve original redirect in place; verify its successor link'
        elif p['role']=='unexpanded': intent='inspect and compare content; no archive or move decision yet'
        elif p['role']=='live_delta_unqualified': intent='record new target and resolve exact owner/writer; preserve in place'
        elif p['role'] in ('historical','rejected','held','source_only'): intent='retain role and conditions; archive only after qualified lineage and preserved evidence'
        else:intent='qualify current working set; reuse or supported lossless transfer to proposed family'
        ledger.append({'source_file_id':p['paper_file_id'],'source_page_id':p['paper_page_id'],
          'source_artboard_ids':[b['artboard_id'] for b in bmap[(p['paper_file_id'],p['paper_page_id'])]],'source_url':p['url'],
          'organization_actor':'F03','page_custodian':p['page_custodian'],'product_owners':p['artboard_owners'] or [p['content_owner']],
          'requested_organization_action':intent,'upstream_mutation_tool':None,
          'intended_destination_name':p['proposed_file'],'intended_folder_name':p['proposed_folder'],
          'actual_destination_file_id':None,'actual_destination_page_id':None,'actual_destination_artboard_map':None,
          'admission_receipt':None,'operation_id':None,'effect_status':'NOT_DISPATCHED','applied':False,
          'preservation_checks':{k:None for k in checks},'readback':None,'final_destination_url':None,
          'gate':'P00 qualification; supported operation; exact-target ownership and preservation evidence',
          'source_disposition':'PRESERVED_AT_ORIGINAL_LOCATION'})
    curation=load(Path(__file__).with_name('curation.json'))
    relationships=curation['relationships']
    for p in pages:
        key=(p['paper_file_id'],p['paper_page_id'])
        p['baseline_role']=p['role']
        if key==('01M2WGNCX9475G79JRKJTCM08P','p-7-1'):
            p['baseline_role_evidence']=p['role_evidence']
            p['role']='historical'
            p['role_evidence']='Explicit historical / not-for-build page notice in exact board 2TT5-0; evidence/china-hub-redirect.jsx'
            p['role_observation']='Exact board 2TT5-0 JSX says this page is archived / not for build; evidence/china-hub-redirect.jsx'
            for a in ledger:
                if (a['source_file_id'],a['source_page_id'])==key:a['requested_organization_action']='retain observed historical role and conditions; no archive transfer until lineage and preservation qualified'
        p['recorded_successors']=[r for r in relationships if (r['source_file_id'],r['source_page_id'])==key]
        p['recorded_predecessors']=[r for r in relationships if (r['target_file_id'],r['target_page_id'])==key]
        p['lineage_notes']=[r for r in curation['page_notes'] if (r['file_id'],r['page_id'])==key]
        p['current_writer']='UNVERIFIED'
        p['ownership_basis']='verified package assignment; not live custody' if p['expanded_in_package'] else 'organization stewardship; content owner unknown'
        if not p['listed_in_package']: p['ownership_basis']='existing route assignment; writer unverified' if p['paper_file_id']=='01M2WGNCX9475G79JRKJTCM08P' else 'proposed family allocation; custody not confirmed'
    for b in board_rows:
        name=b['name'].upper(); labels=[]
        for pattern,label in [(r'\b(?:HELD|HOLD)\b','held'),(r'\bARCHIV(?:E|ED)\b','historical'),(r'\bREJECTED\b','rejected'),(r'SOURCE ONLY','source_only'),(r'QA ONLY|CANARY','qa_only')]:
            if re.search(pattern,name):labels.append(label)
        b['observed_role_labels']=labels
        b['role_basis']='board title; not a review receipt'
    for p in pages:
        p['board_role_warnings']=sorted({label for b in board_rows if (b['paper_file_id'],b['paper_page_id'])==(p['paper_file_id'],p['paper_page_id']) for label in b['observed_role_labels']})
    for s in sessions:s['aliases']=curation['assignment_aliases'].get(s['id'],[])
    apply_assignment_returns(sessions, curation)
    current_by_id={r['page_id']:r for r in current['pages']}
    for r in route_rows:r['registry_source_owner']=current_by_id[r['canonical_registry_id']]['owner']
    # Derive member identity with the existing exporter's exact-before-family rule.
    exact={('/index.html' if r['route']=='/' else r['route']):r for r in route_rows if r['repo']=='macro' and r['route_kind']!='family'}
    families=[(re.compile('^'+'[^/]+(?:/[^/]+)*'.join(re.escape(x) for x in re.split(r'<[^>]+>',r['route']))+'$'),r) for r in route_rows if r['repo']=='macro' and r['route_kind']=='family']
    excluded={x['path']:x['reason'] for x in inventory['projection']['coverage']['excluded']}
    documents=set(inventory['document_paths']); legacy=set(inventory['projection']['legacyPaths']); members=[]
    for path in inventory['tracked_html']:
        matches=[exact[path]] if path in exact else [r for pat,r in families if pat.fullmatch(path)]
        assert len(matches)<=1,'ambiguous family '+path
        route=matches[0] if matches else None
        delta=next((d for d in delta_rows if d['repo']=='macro' and d['route']==path),None)
        members.append({'path':path,'is_full_document':path in documents,'export_disposition':'included_legacy' if path in legacy else excluded[path],
          'canonical_registry_id':route['canonical_registry_id'] if route else None,'design_assignment':route['primary_session'] if route else (delta['primary_session'] if delta else None),
          'registry_source_owner':route['registry_source_owner'] if route else None,'source_delta':bool(delta)})
    actual_family_counts=collections.Counter(x['canonical_registry_id'] for x in members if x['export_disposition']=='included_legacy')
    for rid,n in inventory['projection']['coverage']['familyMembers'].items():assert actual_family_counts[rid]==n,'family count differs from exporter '+rid
    inventory_gaps=[x for x in members if x['export_disposition']=='unregistered'];assert len(inventory_gaps)==7
    for r in route_rows:
        if r['repo']=='macro' and r['route_kind']=='family':r['family_inventory']='inventory.html#family='+r['canonical_registry_id'];r['inventory_member_count']=sum(x['canonical_registry_id']==r['canonical_registry_id'] for x in members)
    metadata={'kind':'F03_DERIVED_AUDIT_DIRECTORY_NOT_A_CANONICAL_REGISTRY','package_sha':PACKAGE,'procedure_sha':PROCEDURE,
      'macro_observation_sha':MACRO,'terminal_observation_sha':TERMINAL,'source_blob_map':blob_map,
      'baseline':{'files':29,'listed_pages':299,'expanded_pages':193,'artboards':2450,'canonical_records':348,'source_deltas':9},
      'live_delta':{'observed_additional_files':1,'observed_additional_pages':2,'full_live_team_census':False},
      'directory':{'assignments':36,'proposed_destinations':len(destinations),'page_records':len(pages),'new_reference_approvals':0,'paper_mutations':0},
      'status':'PARTIAL / BLOCKED_RETURN','paper_application':'NOT_APPLIED_TO_PAPER','rig_state':'draft','rig_receipt':None,
      'registry_generated_at':current['generated_at'],'fresh_macro_inventory':inventory['receipt'],'fresh_native_inventory':native['receipt'],
      'native_projection_warning':'17 native routes are inherited from the registry, not a fresh native-module census or route admission.',
      'source_rule':'Canonical registry fields retain literal unknown; null belongs only to unobserved F03 projection metadata.'}
    data={'metadata':metadata,'sessions':sessions,'pages':pages,'artboards':board_rows,'routes':route_rows,'source_deltas':delta_rows,'destinations':destinations,'changes':changes,'inventory_gaps':inventory_gaps}
    observe_directory_progress(data, out)
    attach_page_observations(data, out)
    for name,value in [('provenance',metadata),('assignment-directory',sessions),('paper-page-directory',pages),('paper-artboard-directory',board_rows),
      ('route-assignment-projection',route_rows),('source-delta-projection',delta_rows),('proposed-destinations',destinations),('resource-action-ledger',ledger),('live-delta',changes)]:dump(out/'data'/f'{name}.json',value)
    (out/'evidence').mkdir(exist_ok=True)
    for name in ['before-directory-shot.jpg','before-terminal-shot.jpg','before-directory.jsx','paper-observations.json','paper-live-deltas.json','generated-document-inventory.json.gz','native-source-inventory.json']+[p.name for p in ev.glob('*.jsx') if p.name!='before-directory.jsx']:
        shutil.copyfile(ev/name,out/'evidence'/name)
    dump(out/'evidence'/'inventory-receipt.json',inventory['receipt'])
    dump(out/'data'/'inventory-gaps.json',inventory_gaps)
    with (out/'data'/'generated-document-index.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(members[0]));w.writeheader();w.writerows(members)
    member_payload=json.dumps([[x[k] for k in ['path','is_full_document','export_disposition','canonical_registry_id','design_assignment','registry_source_owner','source_delta']] for x in members],ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (out/'inventory.html').write_text(Path(__file__).with_name('inventory.template.html').read_text().replace('__MEMBERS__',member_payload))
    with (out/'data'/'canonical-route-assignments.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['canonical_registry_id','repo','route','route_kind','primary_session','delegated_slices','access_shell','payload_tier','source_template'])
        for r in route_rows:w.writerow([r[k] if k!='delegated_slices' else ','.join(r[k]) for k in ['canonical_registry_id','repo','route','route_kind','primary_session','delegated_slices','access_shell','payload_tier','source_template']])
    render_directory(out, data)
    print(json.dumps({'status':'BUILT_NOT_APPROVED','assignments':len(sessions),'page_records':len(pages),'artboards':len(board_rows),
      'canonical_records':len(route_rows),'deltas':len(delta_rows),'destinations':len(destinations),'actions_not_dispatched':len(ledger),
      'output':str(out)},indent=2))

def render_directory(out, data, updated_ids=None):
    sessions,pages,board_rows,route_rows,delta_rows=(data[k] for k in ('sessions','pages','artboards','routes','source_deltas'))
    # Every assignment is a GitHub-readable stop, with exact source references in two choices.
    (out/'assignments').mkdir(exist_ok=True)
    for s in sessions:
        if updated_ids is not None and s['id'] not in updated_ids: continue
        refs=[p for p in pages if {'file_id':p['paper_file_id'],'page_id':p['paper_page_id']} in s['paper_refs']]
        rr=[r for r in route_rows if r['primary_session']==s['id'] or s['id'] in r['delegated_slices']]
        ds=[r for r in delta_rows if r['route'] in s['source_deltas']]
        text=f"# {s['id']} — {s['title']}\n\n[Directory](../DIRECTORY.md) · [Original assignment]({s['handoff_url']})\n\n{s['job']}\n\n"
        text+='## Builder entry\n\n'
        text+=builder_entry(s)
        if s['id']=='D08':
            text+='## Four separately owned design packages\n\nFour design packages are not four route records. Source-only returns retain null native candidates.\n\n'
            for child in sessions:
                if child['id'] in ('D08A','D08B','D08C','D08D'):
                    text+='### '+child['id']+' — '+child['title']+'\n\n'+builder_entry(child)

        text+=f"**Dependencies:** {s['dependencies']}. **Named collaborators:** {s['partners']}. **Implementation/served status:** not assessed as ready.\n\n"
        text+='## Proposed working families\n\n'+('\n'.join('- '+x for x in s['proposed_files']))+'\n\nNo destination ID is inferred from these names. Existing coherent files should be verified for reuse first.\n\n'
        text+='## Observed Paper references\n\n'
        text+='These are discovery links, not approvals. Source-only, rejected, held and redirect roles remain distinct.\n\n'
        text+=table(['Reference','Exact source','Role / custody','Boards'],[[f"[{p['file_name']} — {p['name']}]({p['url']})",f"`{p['paper_file_id']} / {p['paper_page_id']}`",f"{p['role']}; page {p['page_custodian']}; board owners {', '.join(p['artboard_owners']) or 'not expanded'}",p['board_count'] if p['board_count'] is not None else 'not expanded'] for p in refs]) if refs else 'No dedicated reference is allocated in the inspected census. This is an explicit design/reference gap.\n'
        text+='\n## Exact artboard references\n\n'
        own=[b for b in board_rows if b['product_owner']==s['id']]
        text+=table(['File / page','Artboard ID','Name','Geometry / children'],[[f"`{b['paper_file_id']} / {b['paper_page_id']}`",f"`{b['artboard_id']}`",b['name'],f"{b['width']} × {b['height']}; {b['child_count']} children"] for b in own]) if own else 'No expanded artboards allocated.\n'
        text+='\n## Canonical route responsibility\n\n'
        text+=table(['Registry ID','Repository / route','Primary / slice','Source / access'],[[f"`{r['canonical_registry_id']}`",f"{r['repo']} `{r['route']}`",f"{r['primary_session']} / {', '.join(r['delegated_slices']) or 'none'}",f"{r['source_template']}; {r['access_shell']} / {r['payload_tier']}"] for r in rr]) if rr else 'Foundation/review responsibility; no canonical route subset assigned.\n'
        text+='\n## Source deltas outside canonical registry\n\n'
        text+=table(['Route','Source','Disposition'],[[f"`{r['route']}`",r['source'],r['disposition']] for r in ds]) if ds else 'None assigned in the nine-row annex.\n'
        text+='\n## Recorded lineage and unresolved evidence\n\nRecorded history claims are not candidate approvals. [Detailed preservation and operation contract](../OPERATIONS.md).\n\n'
        if s['id'] == 'F03' and data.get('page_observations'):
            observations = data['page_observations']
            structural = data['metadata']['structural_observations']
            text+='### Later structural inspection of baseline listed-only pages\n\n'
            text+=f"{len(observations)} of {structural['baseline_listed_only_pages']} pages were read by exact identity; {structural['observed_artboards']} complete compound artboard identities are now searchable in the interactive directory. {structural['zero_artboard_pages']} pages returned zero artboards. The original page/artboard census, product ownership, lineage and 301 undispatched actions remain unchanged.\n\n"
            text+=f"[Exact read evidence and all board identities](../{structural['evidence']}) · [Interactive search](../directory.html#view=references&owner=F03&q=structural+observation)\n\n"
            text+='Metadata inspection is not full-content comparison or disposal approval. Paper reported a file-size/data-loss warning on one retained file; no mutation was attempted there. Two capped 100-board lists were completed through exact root summaries and 26 individual board reads.\n\n'
            text+=table(['Exact file / page','Observed name','Boards / initial list','Read completed (UTC)','Provider warning'],[[f"[{p['file_id']} / {p['page_id']}]({p['url']})",p['page_name'],f"{p['artboard_count']} / {p['initial_returned_artboards']}",p['completed_at_utc'],'; '.join(p['warnings']) or 'None returned'] for p in observations])
            text+='\n'
        for p in refs:
            for rel in p['recorded_successors']:
                text+=f"- {p['paper_file_id']} / {p['paper_page_id']} → [recorded destination](https://app.paper.design/file/{rel['target_file_id']}/{rel['target_page_id']}); [source](../{rel['evidence']}). {rel['qualification']}\n"
            for note in p['lineage_notes']:text+=f"- {p['paper_file_id']} / {p['paper_page_id']}: {note['statement']} Missing: {note['missing']} (owner {note['owner']}). [Source](../{note['evidence']}).\n"
        text+='\nPredecessor/successor approval relationships, rejection rationale receipts, full retention ledgers, source contracts and per-route exact candidate mappings are not established by titles or board counts. Preserve originals and obtain those records through the domain owner before archival or builder approval. A displayed assignment is not a live writer lease.\n'
        (out/'assignments'/f"{s['id']}.md").write_text(text)
    index='# Design programme directory\n\n**Source directory available · directory refinements observed where logged · 301 cross-file organization actions NOT_DISPATCHED · reference approvals not established.**\n\nChoose a family below. Its entry exposes the exact references and contract status; one further link opens the source or Paper page. A missing approved candidate is reported in the same place.\n\n[Interactive directory](directory.html) · [Organization contract](CONTRACT.md) · [Evidence and return](README.md) · [Fresh inventory](evidence/inventory-receipt.json)\n\n'
    index+=table(['Assignment','User task','Routes / deltas','Reference status'],[[f"[{s['id']} — {s['title']}](assignments/{s['id']}.md)",s['job'],f"{len(s['canonical_registry_ids'])} canonical / {len(s['source_deltas'])} delta; {len(s['delegated_registry_ids'])} delegated",'Approval not established; see entry'] for s in sessions])
    if data.get('page_observations'):
        structural = data['metadata']['structural_observations']
        index+=f"\n## Later structural coverage\n\nAll {structural['observed_pages']} formerly listed-only page targets were inspected by exact identity, exposing {structural['observed_artboards']} searchable artboard identities across retained files. [Observed pages, timestamps and preservation limits](assignments/F03.md#later-structural-inspection-of-baseline-listed-only-pages). Frozen baseline counts and ownership are unchanged; this is not physical organization or disposal approval.\n"
    (out/'DIRECTORY.md').write_text(index)
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=Path(__file__).with_name('directory.template.html').read_text()
    (out/'directory.html').write_text(template.replace('__F03_DATA__',payload).replace('__F03_SCRIPT__',Path(__file__).with_name('directory.js').read_text()))


if __name__=='__main__':main()
