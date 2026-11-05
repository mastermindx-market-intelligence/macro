"""Actual admin code + synthetic evidence only, bound to localhost.
No production records, credentials, jobs, clock writes or account actions.
Open /fixture-session once; it sets an ephemeral synthetic signed session without
printing the cookie. Eight-cell capture must label every artifact SYNTHETIC.
"""
import sys,os,json,threading
from pathlib import Path
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from http.cookies import SimpleCookie
from unittest.mock import patch
TREE=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/eval-os-a1-preflight-20260922-f75c61cdabe6f12c')
OUT=Path(__file__).parent
sys.path.insert(0,str(TREE))
# All identity/auth values here are disposable local fixture values, not saved credentials.
os.environ.update(ADMIN_SESSION_SECRET='synthetic-local-evaluation-fixture',ADMIN_PASSWORD='unused-synthetic-fixture')
from admin import server,auth,intelligence_os as IOS
NOW='2026-10-12T20:00:00+00:00'
cells=[];outputs=[];providers={}
for name,lifecycle,klass,state,reason in [
 ('synthetic-immature','phase0','predictive','healthy',None),
 ('synthetic-supported-scope-unknown','validated','ranking','healthy',None),
 ('synthetic-retired','retired','predictive','healthy',None),
 ('synthetic-partial','validated','classification_state',None,'partial'),
 ('synthetic-falsified','falsified','detection_event','healthy',None),
 ('synthetic-descriptive','phase0','descriptive','healthy',None),
 ('synthetic-unclassified','phase0',None,'healthy',None)]:
 eid='engine/'+name+'.py::synthetic-fixture'
 cells.append({'engine_id':eid,'producer':'engine/'+name+'.py','owner_program':'SYNTHETIC — no market outcomes','output_class':klass,'authority':'display','ledger':'none','graded_by_design':'no — descriptive' if klass=='descriptive' else 'no — not yet','graded_by_design_source':'synthetic display fixture','declared_horizon':{'horizon_d':[126]},'validation_state':lifecycle,'validation_state_evidence':{'bound_species':[{'species_id':'SYNTHETIC-V1','validation_status':lifecycle,'owner_scope':{'version':'fixture-v1','market_scope':['US']}}],'reason':'synthetic fixture only'},'evidence_ref':['synthetic:fixture-v1']})
 outputs.append({'engine_id':eid,'artifact_id':name,'state':state,'assessment_status':reason or 'complete','observed_at':NOW,'source_asof':NOW,'freshness_sla_hours':24,'age_hours':0,'path':'synthetic/'+name+'.json','storage':'synthetic','decided_by':'content_watermark' if state else None,'output_class':klass,'authority':'display','dependency_bound':'exact','required_inputs':[],'optional_inputs':[],'reason_codes':[],'reader_observation':None,'self_health':None})
 if name=='synthetic-immature':
  cells[-1]['evidence_ref']=['synthetic:fixture-v1','research/PREREG_P0D_MATCHED_CONTROL_CONTRACT.md']
  providers[eid]={'kind':'qledger','binding':'direct:qledger:synthetic','family':'synthetic','read_status':'ok','clock_start':{'declared_horizon_d':126,'horizon_unit':'trading_days'},'readiness':{'63':{'n_dates':0,'needed':25,'ready':False,'clock_basis':'explicit_unit_v1:trading_days:US','evidence_basis':'matched_control','wilson_ci_low':None,'control_coverage':0,'n_cohort_dates':10,'n_controlled_dates':0,'n_cohort_rows':10,'n_controlled_rows':0,'n_control_refused_rows':10,'benchmark_baseline_hit_rate':0,'benchmark_baseline_excess_mean':None,'benchmark_baseline_mean_abs_excess':0,'benchmark_baseline_excess_basis':'magnitude_only','benchmark_baseline_excess_mean_by_direction':{'1':0.01,'-1':-0.01},'reason':'SYNTHETIC fixture; not empirical outcomes'}}}

view={'outputs':outputs,'summary':{'reason_codes':{}},'generated':{'observed_at':NOW,'root_mode':'SYNTHETIC fixture'}}
registry={'engines':cells,'excluded':[]}
# Isolated synthetic inputs exercise the actual source readers; source tree stays untouched.
FIXTURE_INPUT_ROOT=OUT/'synthetic-combined-inputs'
findings_path=FIXTURE_INPUT_ROOT/'data/neuralweb/confluence_graph.json'
findings_path.parent.mkdir(parents=True,exist_ok=True)
findings_path.write_bytes((OUT.parent/'experience/fixture-proposals/findings-artifact.json').read_bytes())
ALL_REJECTED_ROOT=OUT/'synthetic-all-rejected-inputs'
all_path=ALL_REJECTED_ROOT/'data/neuralweb/confluence_graph.json'
all_path.parent.mkdir(parents=True,exist_ok=True)
all_document=json.loads(findings_path.read_bytes())
all_document['contradiction_records'][0]['kind']='SYNTHETIC-unsupported-owner-kind'
all_document['contradiction_records']=all_document['contradiction_records'][:1]
all_path.write_text(json.dumps(all_document))
_request_state=threading.local()
owner_path=FIXTURE_INPUT_ROOT/'site/qledger/track_record.json'
owner_path.parent.mkdir(parents=True,exist_ok=True)
owner_rows=providers[cells[0]['engine_id']]['readiness']
owner_path.write_text(json.dumps({'promotion_readiness':{'synthetic':owner_rows},'promotion_readiness_at':'2026-10-11T18:00:00+00:00'}))
def derive_synthetic(root,force):
 snapshot=IOS._read_owner_readiness_snapshot(FIXTURE_INPUT_ROOT)
 provider={**providers[cells[0]['engine_id']],'readiness':snapshot['readiness'].get('synthetic',{}),'recorded_snapshot':{**snapshot['context'],'family_present':True},'read_status':'partial'}
 findings_root=ALL_REJECTED_ROOT if getattr(_request_state,'case','default')=='all-rejected' else FIXTURE_INPUT_ROOT
 derived_view={**view,'typed_findings':IOS.load_findings(findings_root,outputs)}
 return derived_view,registry,{**providers,cells[0]['engine_id']:provider},0.,'miss'
IOS._derive=derive_synthetic
server.settings.auth_enabled=lambda:True
server.settings.deployed=lambda:False
class FixtureHandler(server.Handler):
 def do_GET(self):
  path=urlparse(self.path).path
  cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
  case=cookie.get('synthetic-findings-case')
  _request_state.case='all-rejected' if case and case.value=='all-rejected' else 'default'
  if path=='/fixture-session':
   requested=parse_qs(urlparse(self.path).query).get('case',['default'])[0]
   _request_state.case='all-rejected' if requested=='all-rejected' else 'default'
   self.send_response(302)
   for cookie in self._set_cookies(auth.mint_session(),auth.new_csrf()):self.send_header('Set-Cookie',cookie)
   self.send_header('Set-Cookie','synthetic-findings-case='+_request_state.case+'; Path=/; SameSite=Lax; HttpOnly')
   self.send_header('Location','/#/page/intelligence_os');self.send_header('Cache-Control','no-store');self.end_headers();return
  if path.startswith('/api/') and path not in ['/api/intelligence_os','/api/intelligence_os/engine','/api/session']:
   if not self._authed():return self._json({'error':'authentication required'},401)
   if path=='/api/summary':return self._json({'meta':{'repo':'SYNTHETIC fixture','deployed':False},'health':{'healthy':False,'available':False},'services':{'available':False},'git':{'config_dirty':False}})
   return self._json({'ok':True,'available':False,'items':[],'lobes':[],'count':0,'synthetic':True})
  return super().do_GET()
 def do_POST(self):return self._json({'ok':False,'error':'synthetic fixture is read-only'},405)
h=ThreadingHTTPServer(('127.0.0.1',0),FixtureHandler)
receipt={'scope':'SYNTHETIC local actual admin renderer/handler; not production/user acceptance','url':f'http://127.0.0.1:{h.server_address[1]}/fixture-session','pid':os.getpid(),'source_tree':str(TREE),'fixture_time':NOW,'owner_recorded_at':'2026-10-11T18:00:00+00:00','findings_source_as_of':'2026-10-11','fixture_input_root':str(FIXTURE_INPUT_ROOT),'engine_ids':[c['engine_id'] for c in cells]}
(OUT/'synthetic-server.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
try:h.serve_forever()
finally:h.server_close()
