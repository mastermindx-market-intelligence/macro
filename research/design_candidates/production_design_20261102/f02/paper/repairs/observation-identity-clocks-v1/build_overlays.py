#!/usr/bin/env python3
"""Prepare bounded source overlays; no Paper/browser/GitHub operations."""
import copy,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]
BASE=PAPER/'repairs/fixture-coherence-v1'
OUT=HERE/'effective';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n');return sha(p.read_bytes())

SHORT='f02.fixture.v3/macro/sector/communication_services'
FULL=SHORT+'/share_above_50d/2026-10-30'
FIXTURE=PAPER.parent/'fixtures/company-history.json'
fixture=json.loads(FIXTURE.read_text())
assert fixture['observed_period']=='Fiscal years 2010–2026; fiscal label is not a calendar observation timestamp'
assert fixture['publication']=='2026-10-30T20:02:00Z' and fixture['retrieval']=='2026-10-30T20:03:00Z'

changes={
 ('macro-dark','evidence-field-0'):(SHORT,FULL),
 ('macro-light','evidence-field-0'):(SHORT,FULL),
 ('fault-compositions','empty-table-context'):(
  'Requested periods: FY 2025–2026 · Display currency: USD · Source observed 30 Oct 2026, 20:00 UTC.',
  'Observation basis: FY 2025–2026 · Display currency: USD · Fixture published 30 Oct 2026, 20:02 UTC · Retrieved 30 Oct 2026, 20:03 UTC.'),
 ('fault-compositions','retained-table-context'):(
  'Requested periods: FY 2025–2026 · Display currency: USD · Original source 30 Oct 2026, 20:00 UTC · last successful retrieval 20:03 UTC.',
  'Observation basis: FY 2025–2026 · Display currency: USD · Fixture published 30 Oct 2026, 20:02 UTC · Last successful retrieval 30 Oct 2026, 20:03 UTC.'),
 ('fault-compositions','tabs-empty-panel'):(
  'Source request: annual statement metrics · observation time 30 Oct 2026, 20:00 UTC',
  'Source request: annual statement metrics · Fiscal basis: FY 2025–2026 · Fixture published 30 Oct 2026, 20:02 UTC · Retrieved 20:03 UTC'),
 ('fault-compositions','retained-table-error'):(
  'The last successful view remains associated with EXM and its original source date. Retry reads the same view; it does not change filters, erase rows or send a save.',
  'The last successful view remains associated with EXM, its original fiscal periods and publication clock. Retry reads the same view; it does not change filters, erase rows or send a save.'),
}
inputs={};outputs={};overrides=[];counts={};preserved=[]
for filename in ['consumer-boards.json','fault-composition-inputs.json']:
 p=BASE/'effective-spaced'/filename;raw=p.read_bytes();o=json.loads(raw);n=copy.deepcopy(o);inputs[str(p)]=sha(raw)
 for oldboard,board in zip(o['boards'],n['boards']):
  for oldstep,step in zip(oldboard['steps'],board['steps']):
   ident=(board['key'],step['key'])
   if ident not in changes:
    assert step==oldstep;preserved.append({'packet':filename,'board':ident[0],'step':ident[1]});continue
   old,new=changes[ident];oldhtml=step['html']
   assert old in oldhtml,(ident,old)
   # Exact replacement may update an identical layer label as well as visible text.
   step['html']=oldhtml.replace(old,new)
   assert step['key']==oldstep['key'] and step['parent']==oldstep['parent']
   assert re.findall(r'</?[^>\s]+',oldhtml)==re.findall(r'</?[^>\s]+',step['html'])
   overrides.append({'packet':filename,'board_key':ident[0],'step_key':ident[1],
    'base_packet_sha256':sha(raw),'base_step_html_sha256':sha(oldhtml.encode()),
    'replacement_html_sha256':sha(step['html'].encode()),'expected_before_text':old,'after_text':new,
    'replacement_html':step['html'],'native_status':'PREPARED_NOT_APPLIED_BY_THIS_TASK'})
   counts[ident]=1
 n['observation_identity_clock_override']={
  'version':'f02.observation-identity-clocks.v1','status':'PREPARED_NOT_APPLIED',
  'base_packet':str(p.relative_to(PAPER)),'base_packet_sha256':sha(raw),
  'company_fixture_path':'fixtures/company-history.json','company_fixture_sha256':sha(FIXTURE.read_bytes()),
  'scope':'Two Macro source-identity fields and four Company fault-copy steps only; board/step/entity keys and all numeric inputs remain stable.',
  'precedence':'Apply after fixture-coherence-v1/effective-spaced. Compose independently with latest Company annual-growth/caveat overlays. Never replay already-applied groups.'}
 digest=dump(OUT/filename,n);outputs[filename]={'path':str((OUT/filename).relative_to(HERE)),'sha256':digest}
assert set(counts)==set(changes)

fault=json.loads((OUT/'fault-composition-inputs.json').read_text())
basefault=json.loads((BASE/'effective-spaced/fault-composition-inputs.json').read_text())
fm={s['key']:s for s in fault['boards'][0]['steps']};bm={s['key']:s for s in basefault['boards'][0]['steps']}
protected=['unavailable-table-context','unavailable-table-state','tabs-loading-panel',
 'unavailable-inspector-summary','not-yet-published-state','unquantified-coverage-state','combined-confirmed-saved']
for key in protected:assert fm[key]==bm[key],key
for key in ['empty-table-context','retained-table-context','tabs-empty-panel']:
 assert '20:00' not in fm[key]['html'] and '20:02' in fm[key]['html'] and '20:03' in fm[key]['html']
 assert 'FY 2025–2026' in fm[key]['html']
assert 'original fiscal periods and publication clock' in fm['retained-table-error']['html']
assert 'Observed 30 Oct 2026, 20:00 UTC' in fm['unavailable-inspector-summary']['html']
for filename,board_key,step_key in [
 ('mobile-state-boards.json','macro-docked-1280','dock-source-0'),
 ('supplemental-boards.json','macro-zh-evidence-return-390','source-identity'),
 ('supplemental-boards.json','width-768-overlay','overlay-source'),
 ('supplemental-boards.json','width-1024-overlay','overlay-source'),
 ('supplemental-boards.json','width-1600-docked','dock-source-0')]:
 packet=json.loads((BASE/'effective-spaced'/filename).read_text())
 step=next(s for b in packet['boards'] if b['key']==board_key for s in b['steps'] if s['key']==step_key)
 assert FULL in step['html'],(board_key,step_key)

base_native=BASE/'native-patch-candidates.spaced.json';native=json.loads(base_native.read_text());inputs[str(base_native)]=sha(base_native.read_bytes())
minimal=[]
for g in native['text_groups']:
 if g['board_key'] not in ['macro-dark','macro-light'] or g['step_key']!='evidence-field-0':continue
 assert len(g['updates'])==1
 u=g['updates'][0];assert u['after_text']==SHORT
 expected_id='4XH-0' if g['board_key']=='macro-dark' else '4Z5-0'
 assert u['nodeId']==expected_id
 assert u['expected_before_text']=='macro / communication-services'
 u['html']=FULL;u['after_text']=FULL
 u['accepted_observed_before_texts']=['macro / communication-services',SHORT]
 u['already_satisfied_text']=FULL
 g['argument_shape']['updates']=[{'nodeId':expected_id,'html':FULL}]
 ov=next(x for x in overrides if x['board_key']==g['board_key'] and x['step_key']==g['step_key'])
 g['previous_effective_html_sha256']=g['effective_html_sha256'];g['effective_html_sha256']=ov['replacement_html_sha256']
 g['observation_identity_override']='Full metric/date identity supersedes incomplete v3 prefix only; no numeric or entity-key change.'
 minimal.append({'board_key':g['board_key'],'board_id':g['board_id'],'step_key':g['step_key'],
  'step_node_id':g['target_node_id'],'text_node_id':expected_id,
  'accepted_observed_before_texts':['macro / communication-services',SHORT],
  'after_text':FULL,'already_satisfied_text':FULL,
  'arguments':{'fileId':native['file_id'],'updates':[{'nodeId':expected_id,'html':FULL}]},
  'guard':'Fresh-read this exact Text node. Apply only if its observed text exactly matches one listed before-state. If full identity is already present, record satisfied and do not replay; any other value needs reconciliation.'})
assert len(minimal)==2
native['observation_identity_clock_override']={'version':'f02.observation-identity-clocks.v1',
 'base_native_patch_sha256':sha(base_native.read_bytes()),
 'scope':'Only the two Macro evidence-field-0 text targets change. Company fault steps use the separately guarded source overlay; no unavailable native IDs are fabricated.',
 'precedence':'Use these two corrected groups in place of the older candidate groups, OR use minimal-native-identity-patch.v1.json. Never apply both. Other cumulative groups are historical candidates; reconcile actual writer progress before any action.'}
native_before=json.loads(base_native.read_text())
for before,after in zip(native_before['text_groups'],native['text_groups']):
 if before['board_key'] in ['macro-dark','macro-light'] and before['step_key']=='evidence-field-0':continue
 assert before==after
for key in ['chart_step_replacements','row_reorders','numeric_alignment_carry','unbound_items']:
 assert native_before[key]==native[key]
nativehash=dump(HERE/'native-patch-candidates.cumulative.v2.json',native)
minhash=dump(HERE/'minimal-native-identity-patch.v1.json',{'schema':'f02.native-observation-identity-patch.v1','status':'PREPARED_NOT_APPLIED','updates':minimal,'paper_calls':0})
ovhash=dump(HERE/'source-overrides.v1.json',{'schema':'f02.source-observation-identity-clock-overrides.v1','status':'PREPARED_NOT_APPLIED',
 'precedence':'fixture-coherence-v1/effective-spaced → this six-step overlay. The latest Company annual-growth/caveat overlays remain separate and must be preserved.',
 'company_fixture_sha256':sha(FIXTURE.read_bytes()),'overrides':overrides,'cumulative_packets':outputs,'paper_calls':0})
for path,digest in inputs.items():assert sha(Path(path).read_bytes())==digest,path
validation={'schema':'f02.observation-identity-clocks-validation.v1','status':'SOURCE_CHECKS_PASS_NATIVE_APPLICATION_NOT_CLAIMED',
 'source_identity':{'full':FULL,'macro_dark_text_id':'4XH-0','macro_light_text_id':'4Z5-0','matches_existing_width_mobile_fault_identity':True},
 'company_clock_basis':{'observation':'Fiscal years; no calendar observation timestamp supplied','comparison_periods':[2025,2026],'publication':fixture['publication'],'retrieval':fixture['retrieval'],'authoritative_fixture_sha256':sha(FIXTURE.read_bytes())},
 'changed_steps':6,'unchanged_steps':len(preserved),'protected_steps_identical':protected,
 'macro_2000_clocks_unchanged':True,'all_existing_input_and_native_candidate_hashes_preserved':inputs,
 'numeric_values_and_raw_company_rows_unchanged':True,'board_step_parent_keys_and_html_tag_topology_unchanged':True,
 'minimal_native_patch_sha256':minhash,'cumulative_native_patch_sha256':nativehash,'source_overrides_sha256':ovhash,
 'cumulative_packets':outputs,'paper_calls':0,'browser_calls':0}
valhash=dump(HERE/'validation.json',validation)
print(json.dumps({'source_overrides_sha256':ovhash,'minimal_native_patch_sha256':minhash,'cumulative_native_patch_sha256':nativehash,'validation_sha256':valhash,'packets':outputs,'changed_steps':6,'unchanged_steps':len(preserved)},indent=2))
