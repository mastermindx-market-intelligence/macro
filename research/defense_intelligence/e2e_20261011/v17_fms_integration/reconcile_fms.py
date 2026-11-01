from pathlib import Path
from datetime import datetime,timezone
import sys,json,subprocess,hashlib
W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');D=Path(__file__).parent;sys.path.insert(0,str(W))
from collectors import fms_notifications_live as live
H='0e618fb80e5941e731fa559692a39efddd83b94d';M='b4e1d4c724a91a608448b468baf94d4558bf91e8'
def raw(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=W)
def doc(ref,path):return json.loads(raw(ref,path))
obs_path='data/government_revenue/fms_observations.jsonl';receipts='data/government_revenue/fms_collection_receipts.jsonl';graph_path='data/government_revenue/fms_case_graph.json'
original=[json.loads(x) for x in raw(M,obs_path).splitlines() if x];corrected=[json.loads(x) for x in raw(H,obs_path).splitlines() if x]
assert (W/obs_path).read_bytes()==raw(H,obs_path)
assert raw(H,receipts)==raw(M,receipts)==(W/receipts).read_bytes()
old=doc(M,graph_path);held=doc(H,graph_path);fr=old['coverage']['sources']['federal_register'];state=old['coverage']['sources']['state_pm_bureau'];dsca=old['coverage']['sources']['dsca_press'];scope=old['scope']
den=sorted({r['fields']['transmittal_number'] for r in original if r['source_surface']=='federal_register' and r['kind']=='fr_raw_text' and r['fields'].get('classification')=='original' and scope['delivered_from']<=r['fields'].get('official_notification_date','')<=scope['delivered_through']});assert len(den)==fr['originals']
kwargs=dict(as_of=old['as_of'],scope_delivered_from=scope['delivered_from'],scope_delivered_through=scope['delivered_through'],fr_publication_from=fr['publication_window'][0],fr_publication_through=fr['publication_window'][1],fr_denominator_transmittals=den,fr_docs_scanned=fr['docs_scanned'],fr_amendments_excluded=fr['amendments_excluded'],fr_corrections=fr['corrections'],fr_out_of_scope_originals=fr['out_of_scope_originals'],fr_status=fr['status'],state_listing_pages=state['listing_pages'],state_qualifying_articles=state['qualifying_articles'],state_articles_succeeded=state['articles_succeeded'],state_articles_failed=state['articles_failed'],state_status=state['status'],dsca_articles_staged=dsca['articles_staged'],dsca_status=dsca['status'],history_disclosure=old['coverage']['history_disclosure'])
assert live.fms_cases.build_fms_case_graph(observations=original,generated_at=old['generated_at'],**kwargs)==old
now=datetime.now(timezone.utc).isoformat();out=live.fms_cases.build_fms_case_graph(observations=corrected,generated_at=now,**kwargs)
assert out['cases']==held['cases'];assert out['coverage']==old['coverage'] and out['scope']==old['scope'] and out['as_of']==old['as_of'];assert out['known_at']==held['known_at']
assert len(original)==94 and len(corrected)==95 and len(out['cases'])==68
assert len(corrected)==doc(H,'data/government_revenue/fms_projection_state.json')['observation_count']
assert corrected[:len(original)]==original, 'append-only original observations changed'
rawout=json.dumps(out,sort_keys=True,separators=(',',':')).encode()
for rel in [graph_path,'site/government-revenue-data/fms-cases.json']:(W/rel).write_bytes(rawout)
# Projection retains the accepted append-only correction and truthfully reflects 95 observations.
statepath='data/government_revenue/fms_projection_state.json';projection_state=doc(M,statepath);projection_state.update(observation_count=len(corrected),generated_at=now);(W/statepath).write_text(json.dumps(projection_state,sort_keys=True,separators=(',',':')))
r={'head_before':H,'main_integrated':M,'upstream_graph_exact_replay':True,'corrected_68_cases_identical_to_accepted_head':True,'observation_count':95,'incumbent_observations_preserved':94,'receipts_byte_identical':True,'new_acquisition_coverage_preserved':True,'projection_state_matches_95_observations':True,'upstream_acquisition_clock':old['generated_at'],'corrected_known_at_preserved':out['known_at'],'actual_projection_generated_at':now,'content_id':out['content_id'],'graph_sha256':hashlib.sha256(rawout).hexdigest(),'network_acquisition':False,'upstream_write':False};(D/'FMS_RECONCILIATION.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
