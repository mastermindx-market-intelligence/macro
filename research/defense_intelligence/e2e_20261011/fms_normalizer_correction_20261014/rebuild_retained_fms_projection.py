"""Offline explicit normalizer correction via incumbent live collector projector.
CLI live acquire has no projection-only command and MUST NOT be called here.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
ROOT=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');P=Path(__file__).parent;sys.path.insert(0,str(ROOT))
from collectors import fms_notifications_live as live
D=P/'retained-correction-current-availability';OUTPUT=D/'projection';OUTPUT.mkdir()
raw=(ROOT/'data/government_revenue/fms_case_graph.json').read_bytes();old=json.loads(raw);(OUTPUT/'original_fms_case_graph.json').write_bytes(raw)
original=[json.loads(x) for x in (ROOT/'data/government_revenue/fms_observations.jsonl').read_text().splitlines() if x];corrected=[json.loads(x) for x in (D/'fms_observations.jsonl').read_text().splitlines() if x]
fr=old['coverage']['sources']['federal_register'];state=old['coverage']['sources']['state_pm_bureau'];dsca=old['coverage']['sources']['dsca_press'];scope=old['scope']
denominator=sorted({r['fields']['transmittal_number'] for r in original if r['source_surface']=='federal_register' and r['kind']=='fr_raw_text' and r['fields'].get('classification')=='original' and scope['delivered_from']<=r['fields'].get('official_notification_date','')<=scope['delivered_through']})
assert len(denominator)==fr['originals']
kwargs=dict(as_of=old['as_of'],scope_delivered_from=scope['delivered_from'],scope_delivered_through=scope['delivered_through'],fr_publication_from=fr['publication_window'][0],fr_publication_through=fr['publication_window'][1],fr_denominator_transmittals=denominator,fr_docs_scanned=fr['docs_scanned'],fr_amendments_excluded=fr['amendments_excluded'],fr_corrections=fr['corrections'],fr_out_of_scope_originals=fr['out_of_scope_originals'],fr_status=fr['status'],state_listing_pages=state['listing_pages'],state_qualifying_articles=state['qualifying_articles'],state_articles_succeeded=state['articles_succeeded'],state_articles_failed=state['articles_failed'],state_status=state['status'],dsca_articles_staged=dsca['articles_staged'],dsca_status=dsca['status'],history_disclosure=old['coverage']['history_disclosure'])
baseline=live.fms_cases.build_fms_case_graph(observations=original,generated_at=old['generated_at'],**kwargs);assert baseline==old,'incumbent_baseline_replay_mismatch'
now=datetime.now(timezone.utc).isoformat();candidate=live.fms_cases.build_fms_case_graph(observations=corrected,generated_at=now,**kwargs)
assert candidate['coverage']==old['coverage'] and candidate['scope']==old['scope']
a={c['case_key']:c for c in old['cases']};b={c['case_key']:c for c in candidate['cases']};assert a.keys()==b.keys();changed=[k for k in a if a[k]!=b[k]];assert changed==['fms:transmittal:25-104'];fields=[k for k in a[changed[0]] if a[changed[0]][k]!=b[changed[0]][k]];assert fields==['contractors','observations'] or set(fields)=={'contractors','observations'}
projection_state=json.loads((ROOT/'data/government_revenue/fms_projection_state.json').read_text());projection_state.update(observation_count=len(corrected),generated_at=now);assert projection_state['receipt_count']==len(original)
for name,value in [('fms_case_graph.json',candidate),('fms_projection_state.json',projection_state)]:live._atomic_write_text(OUTPUT/name,json.dumps(value,sort_keys=True,separators=(',',':')))
receipt={'schema':'defense.fms_normalizer_projection_replay.v1','incumbent_invocation':'collectors.fms_notifications_live.fms_cases.build_fms_case_graph retained originalcoverage kwargs; no acquire','baseline_exact_graph_replay':True,'changed_cases':changed,'changed_case_fields':fields,'source_coverage_scope_unchanged':True,'old_graph_sha256':hashlib.sha256(raw).hexdigest(),'new_graph_sha256':hashlib.sha256((OUTPUT/'fms_case_graph.json').read_bytes()).hexdigest(),'new_graph_known_at':candidate['known_at'],'new_graph_generated_at':candidate['generated_at'],'new_source_receipts':0,'upstream_private_shared_writes':False}
(OUTPUT/'PROJECTION_REPLAY_RECEIPT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
