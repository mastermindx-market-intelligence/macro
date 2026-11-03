#!/usr/bin/env python3
"""Prepare bounded F02 fault compositions locally. Never contacts Paper/browser."""
from pathlib import Path
import hashlib, json, re, xml.etree.ElementTree as ET
from build_role_evidence_inputs import D,L,txt,action

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
CORE_SHA='2f70a6d233b4ff2612494e02155409473d17e4e08930f1441e062dd83c223d83'
FILE='01M312VSDSZFVT45674GDVJVZN'
FIXTURE=json.loads((ROOT/'fixtures/company-history.json').read_text())

def frame(name,inner='',style='',direction='column'):
 from html import escape
 return f'<div layer-name="{escape(name,quote=True)}" style="display:flex;flex-direction:{direction};flex-shrink:0;box-sizing:border-box;{style}">{inner}</div>'
def row(name,inner='',style=''):return frame(name,inner,style,'row')
def body(s,p=D,width=1296,size=13,role='secondary',weight=400,line=21):return txt(s,p,size,role,weight,style=f'width:{width}px;overflow-wrap:anywhere;',line=line)
def label(s,p=D,width=1296):return body(s,p,width,11,'muted',600,17)
def two_values(items,p,width=608):
 col=(width-24)//2
 return row('Two original values',''.join(frame(k,body(k,p,col,12,'secondary',500,18)+body(v,p,col,26,'ink',600,34),'width:'+str(col)+'px;gap:5px;')for k,v in items),f'width:{width}px;gap:24px;')
def table_cells(vals,p,header=False):
 widths=[320,160,160,220,220,216]
 cells=''
 for i,(value,w) in enumerate(zip(vals,widths)):
  if i==5 and not header:
   cells+=frame('Evidence cell',action('Evidence',p,'secondary',140),'width:216px;align-items:flex-end;padding-right:12px;')
  else:
   if i in [1,2,3]:
    content=txt(value,p,12 if header else 13,'secondary' if header else 'ink',600 if header else 400,style=f'width:{w-24}px;align-items:flex-end;text-align:right;',line=19 if header else 20)
   else:
    content=body(value,p,w-24,12 if header else 13,'secondary' if header else 'ink',600 if header else 400,19 if header else 20)
   cells+=frame(str(value),content,f'width:{w}px;padding:8px 12px;align-items:'+('flex-end;' if i in [1,2,3] else 'flex-start;'))
 return row('Column headers' if header else 'Financial metric row',cells,'width:1296px;min-height:'+('40' if header else '52')+'px;align-items:center;background-color:'+p['raised' if header else 'panel']+';border-bottom:1px solid '+p['line']+';')
def table_context(case,p,filter_text,count,source):
 title=row(case+' heading',body('EXM · Annual statement comparison',p,1048,21,'ink',600,29)+action('Source details',p,'secondary',224),'width:1296px;gap:24px;align-items:center;')
 scope=body('Requested periods: FY 2025–2026 · Display currency: USD · '+source,p)
 filters=row('Retained table filter',body('Label filter: '+filter_text,p,960,13,'ink',500)+body(count,p,312,12,'secondary',500),'width:1296px;gap:24px;align-items:center;')
 headers=table_cells(['Metric','FY 2025','FY 2026','Change','Unit','Source'],p,True)
 return frame(case+' composed table',label('ILLUSTRATIVE INPUT · '+case.upper(),p)+title+scope+filters+headers,'width:1344px;padding:24px;gap:12px;background-color:'+p['bg']+';')
def state_message(title,copy,button,p,width=1296,disabled=False):
 return frame(title,body(title,p,width,18,'ink',600,26)+body(copy,p,width,14,'secondary',400,22)+action(button,p,'secondary',220,disabled=disabled),f'width:{width}px;padding:20px 0;gap:12px;')

def build():
 b={'key':'fault-compositions','name':'F02 · Fault compositions & saved read continuity · Candidate 2','pageId':'p-4-0','width':1440,'height':900,'theme':'mixed','language':'en','artboardStyles':{'display':'flex','flexDirection':'column','width':'1440px','height':'fit-content','padding':'48px','gap':'24px','backgroundColor':D['bg'],'fontFamily':'Inter','color':D['ink']},'steps':[]}
 def add(key,parent,html,variants,**extra):
  b['steps'].append({'key':key,'parent':parent,'html':html,'variants':variants,**extra})

 add('artifact-header','board',frame('Fault composition provenance',label('F02 · CANDIDATE 2 · PORTABLE FAULT-STATE FIXTURES')+body('Keep the comparison intact when a result is unavailable.',D,1296,28,'ink',600,36)+body('Each state below is an explicit illustrative input. Definition/currency and response failures are counterfactual examples, separate from the normal consumer fixtures. No real filing, access decision or save result is asserted.',D,1296,14),'width:1344px;gap:8px;'),['Provenance/independent-fault-fixtures'])

 pair=''
 for theme,p in [('Dark',D),('Light',L)]:
  title=row('Missing-period section heading',body('Annual financials',p,446,22,'ink',600,30)+action('Inspect source',p,'secondary',146),'width:608px;gap:16px;align-items:center;')
  pair+=frame(theme+' missing period header',label('EXM · MISSING-PERIOD INPUT',p,608)+title+body('Observation period not supplied.',p,608,15,'ink',500,22)+body('Statement currency: USD · source period unknown',p,608)+body('Retrieved 30 Oct 2026, 20:03 UTC. Retrieval does not identify the observation period.',p,608,12,'secondary',400,19),'width:656px;padding:24px;gap:10px;background-color:'+p['bg']+';')
 add('missing-period-headers','board',row('Missing observation period / both themes',pair,'width:1344px;gap:32px;align-items:flex-start;'),['SectionHeader/missing-period-dark','SectionHeader/missing-period-light'],checkpoint_after=True)

 definition=frame('Changed definition comparison',label('ILLUSTRATIVE INPUT · DEFINITION CHANGED',D,608)+body('EXM · Operating margin',D,608,21,'ink',600,29)+two_values([('FY 2025 · all operations','23.3%'),('FY 2026 · continuing operations','24.5%')],D)+body('— Comparison not available',D,608,17,'ink',600,25)+body('The definitions differ. No comparable restatement was supplied; a numerical change would misstate the comparison.',D,608)+action('Inspect definitions',D,'secondary',220),'width:656px;padding:24px;gap:12px;background-color:'+D['panel']+';')
 currency=frame('Mixed currency comparison',label('ILLUSTRATIVE INPUT · CURRENCY MISMATCH',L,608)+body('EXM · Revenue',L,608,21,'ink',600,29)+two_values([('FY 2025 · statement currency','36.00 USD bn'),('FY 2026 · statement currency','48.00 EUR bn')],L)+body('— Comparison not available',L,608,17,'ink',600,25)+body('Currencies differ. No authorized conversion rate or common-currency restatement was supplied; no percent change is calculated.',L,608)+action('Inspect currencies',L,'secondary',220),'width:656px;padding:24px;gap:12px;background-color:'+L['panel']+';')
 add('withheld-comparisons','board',row('Two reasons to withhold a comparison',definition+currency,'width:1344px;gap:32px;align-items:flex-start;'),['ChangeValue/definition-mismatch','ChangeValue/currency-mismatch'],checkpoint_after=True)

 add('empty-table-context','board',table_context('Completed empty query',L,'ZZZ','0 matches / 9 source metrics','Source observed 30 Oct 2026, 20:00 UTC.'),['TableFrame/empty-container'])
 add('empty-table-state','empty-table-context',state_message('No metrics match “ZZZ”.','The query completed with 0 matching records. The source contains nine metrics; this result does not mean there was no financial activity. The entity, periods and filter remain visible.','Clear filter',L),['TableFrame/empty-query-composed'],checkpoint_after=True)
 add('unavailable-table-context','board',table_context('Source response unavailable',D,'All metrics','Result count unavailable','Source observation time unavailable · read attempted 30 Oct 2026, 20:03 UTC.'),['TableFrame/unavailable-container'])
 add('unavailable-table-state','unavailable-table-context',state_message('The statement source is unavailable.','No response records or result count were supplied. Values remain unavailable; no zero, empty query result or access denial has been inferred. The requested entity and periods are retained.','View coverage',D),['TableFrame/source-unavailable-composed'],checkpoint_after=True)
 add('retained-table-context','board',table_context('Refresh error / retained rows',L,'income','3 retained matches / 9 source metrics','Original source 30 Oct 2026, 20:00 UTC · last successful retrieval 20:03 UTC.'),['TableFrame/retained-error-container'])
 retained=[]
 for key,index in [('operating-income',2),('pretax-income',4),('net-income',5)]:
  a=FIXTURE['rows'][index]
  vals=[a[0],a[5],a[6],a[7],a[8],'Evidence']
  identity_key=re.sub(r'[^a-z0-9]+','_',a[0].lower()).strip('_')
  add('retained-'+key,'retained-table-context',table_cells(vals,L),['DataRow/retained-'+key],source_row={'fixture':'fixtures/company-history.json','row_index':index,'periods':[2025,2026],'evidence_key':'company-'+str(index),'source_identity':'f02.fixture.v2/company/EXM/'+identity_key+'/FY2022-FY2026'})
  retained.append({'step':'retained-'+key,'fixture_row_index':index,'values':vals})
 add('retained-table-error','retained-table-context',state_message('Refresh failed. These rows are retained.','The last successful view remains associated with EXM and its original source date. Retry reads the same view; it does not change filters, erase rows or send a save.','Retry refresh',L),['TableFrame/retained-error-composed'],checkpoint_after=True)

 charthead=row('Unavailable chart heading',body('EXM · Revenue history',D,1048,21,'ink',600,29)+action('Exact values unavailable',D,'secondary',224,disabled=True),'width:1296px;gap:24px;align-items:center;')
 add('unavailable-chart-context','board',frame('Unavailable ChartFrame',label('ILLUSTRATIVE INPUT · SERIES UNAVAILABLE')+charthead+body('Unit: USD bn · requested fiscal years 2010–2026 · scale unavailable until observations are returned')+body('Source observation time unavailable · read attempted 30 Oct 2026, 20:03 UTC',D,1296,12),'width:1344px;padding:24px;gap:12px;background-color:'+D['panel']+';'),['ChartFrame/unavailable-container'])
 plot=frame('Typed unavailable plot region',body('Revenue history is unavailable.',D,1248,19,'ink',600,27)+body('No observations were supplied for this series. Other available statement evidence remains accessible.',D,1248,14),'width:1296px;min-height:160px;padding:24px;gap:10px;justify-content:center;background-color:'+D['raised']+';')
 add('unavailable-chart-state','unavailable-chart-context',frame('Unavailable chart with recovery',plot+action('View coverage',D,'secondary',220),'width:1296px;gap:16px;'),['ChartFrame/source-unavailable-composed'],checkpoint_after=True)

 add('tabs-comparison','board',row('Same active tab / loading and completed empty','','width:1344px;gap:32px;align-items:flex-start;'),['Tabs/availability-comparison'])
 def tab_state(p,busy):
  tabs=''
  for title,w in [('Overview',160),('Table',160),('Sources',160)]:
   selected=title=='Table'
   tabs+=row(title+' tab',body(title,p,w-24,13,'ink' if selected else 'secondary',600 if selected else 400),f'width:{w}px;height:44px;padding:0 12px;align-items:center;background-color:'+p['selected' if selected else 'bg']+';border-radius:6px;')
  panel=frame('Selected Table panel',body('Annual statement table',p,608,18,'ink',600,26)+body('Loading observations.' if busy else 'No metrics match “ZZZ”.',p,608,15,'ink',600,22)+body('The request is pending. No result count is available yet.' if busy else 'The request completed with 0 matching records. The same filter and requested periods are retained.',p,608)+action('Loading…' if busy else 'Clear filter',p,'secondary',220,disabled=busy),'width:608px;gap:10px;')
  return frame('Busy tab panel' if busy else 'Empty tab panel',label('ILLUSTRATIVE INPUT · '+('LOADING' if busy else 'COMPLETED EMPTY'),p,608)+body('EXM · FY 2025–2026 · Label filter: ZZZ',p,608,13,'ink',500)+row('Local tablist',tabs,'width:608px;gap:8px;')+panel+body('Source request: annual statement metrics · observation time '+('not returned' if busy else '30 Oct 2026, 20:00 UTC'),p,608,12),'width:656px;padding:24px;gap:16px;background-color:'+p['bg']+';')
 add('tabs-loading-panel','tabs-comparison',tab_state(D,True),['Tabs/busy-active-panel'],selected_tab='Table',requested_context={'entity':'EXM','periods':[2025,2026],'filter':'ZZZ'},result_count=None,panel_contract='One stable labeled Table panel; loading aria-busy is an implementation requirement.')
 add('tabs-empty-panel','tabs-comparison',tab_state(L,False),['Tabs/empty-active-panel'],selected_tab='Table',requested_context={'entity':'EXM','periods':[2025,2026],'filter':'ZZZ'},result_count=0,checkpoint_after=True)

 inspectorhead=row('Source evidence header',body('Source evidence',L,508,21,'ink',600,29)+action('Close',L,'secondary',76,focus=True),'width:608px;gap:24px;align-items:center;')
 add('unavailable-inspector-context','board',frame('Entity-bound unavailable inspector',label('ILLUSTRATIVE INPUT · SUPPORTING SOURCE UNAVAILABLE',L,608)+inspectorhead,'width:656px;padding:24px;gap:16px;background-color:'+L['panel']+';'),['EvidenceInspector/unavailable-container'])
 identity='f02.fixture.v2/macro/sector/communication_services/share_above_50d/2026-10-30'
 summary=body('Communication services',L,608,22,'ink',600,30)+body('Share above 50D · retained row summary',L,608,13,'secondary',500)+two_values([('Observation','66.70%'),('Change vs prior session','+1.13 pp')],L)+body('Coverage: 21 / 21 securities · baseline 65.57%',L,608,13,'ink',500)+body(identity,L,608,12,'secondary',400,19)+body('Observed 30 Oct 2026, 20:00 UTC · published 20:02 UTC · summary retrieved 20:03 UTC',L,608,12,'secondary',400,19)
 add('unavailable-inspector-summary','unavailable-inspector-context',frame('Retained matched source summary',summary,'width:608px;gap:10px;'),['EvidenceInspector/unavailable-retained-summary'])
 err=body('Supporting source unavailable.',L,608,17,'ink',600,25)+body('The matched row summary is retained. Supporting citation detail could not be retrieved; no new evidence or correction has been inferred.',L,608)+action('View coverage',L,'secondary',220)
 add('unavailable-inspector-source-error','unavailable-inspector-context',frame('Unavailable source with typed recovery',err,'width:608px;padding:16px 0;gap:12px;border-top:1px solid '+L['line']+';border-bottom:1px solid '+L['line']+';'),['EvidenceInspector/unavailable-recovery'])
 add('unavailable-inspector-return','unavailable-inspector-context',action('Return to Communication services',L,'secondary',608),['EvidenceInspector/unavailable-return'],return_target='macro-3',source_identity=identity,checkpoint_after=True)

 no_pub=label('ILLUSTRATIVE INPUT · PUBLICATION STATUS = NOT PUBLISHED',L)+body('Example universe · Share above 50D',L,1296,21,'ink',600,29)+body('No observation has been published for 3 Nov 2026.',L,1296,18,'ink',600,26)+body('The requested period is retained. No new value or zero is shown. The last published fixture observation remains dated 30 Oct 2026, 20:00 UTC.',L)+body('Requested period: 3 Nov 2026 · current publication: not published · source age is not replaced by the request time',L,1296,12)+action('Inspect last observation',L,'secondary',260)
 add('not-yet-published-state','board',frame('No publication yet with calendar and source context',no_pub,'width:1344px;padding:24px;gap:12px;background-color:'+L['bg']+';'),['StatePanel/no-publication-yet'],publication_status='not_published',requested_period='2026-11-03',observation=None,last_observation_key='chart:macro:7',checkpoint_after=True)
 unknown=label('ILLUSTRATIVE INPUT · COVERAGE DENOMINATOR NOT SUPPLIED')+body('Example source batch · Participation readings',D,1296,21,'ink',600,29)+body('Coverage not quantified.',D,1296,18,'ink',600,26)+two_values([('Available observations','7'),('Eligible total','— Not supplied')],D,1296)+body('Seven records are available. The producer did not supply the eligible total; no fraction, completeness claim or coverage percentage is calculated.')+body('Batch observed 30 Oct 2026, 20:00 UTC · retrieved 20:03 UTC · separate coverage-state fixture',D,1296,12)+action('View coverage',D,'secondary',220)
 add('unquantified-coverage-state','board',frame('Known available count with unknown denominator',unknown,'width:1344px;padding:24px;gap:12px;background-color:'+D['panel']+';'),['StatePanel/coverage-unknown'],coverage={'available':7,'eligible':None,'status':'unknown'},checkpoint_after=True)

 metric=frame('Same saved read metric',body('Participation',D,300,12,'secondary',500)+body('66.7%',D,300,32,'ink',600,40)+body('+1.13 pp',D,300,16,'up',600,24),'width:300px;gap:6px;')
 read=frame('Same stale and partial read caveats',body('Older source: 30 Oct, 20:00 UTC',D,472,14,'ink',600,22)+body('Partial coverage: 7 of 8',D,472,14,'ink',600,22)+body('The expected update has not arrived. One observation is still missing.',D,472),'width:472px;gap:8px;')
 saved=frame('Owner-confirmed fixture result',body('Saved. Breadth comparison is confirmed.',D,476,17,'ink',600,25)+body('Illustrative owner confirmation and readback · saved object: Breadth comparison · request: fixture-save-01',D,476,12,'secondary',400,19)+action('Open saved view',D,'secondary',220),'width:476px;gap:10px;')
 add('combined-confirmed-saved','board',frame('Stale + partial + confirmed saved',label('ILLUSTRATIVE OWNER-CONFIRMED RESULT · SAME READ SNAPSHOT')+row('Saved result preserves the read axes',metric+read+saved,'width:1296px;gap:24px;align-items:flex-start;'),'width:1344px;padding:24px;gap:16px;background-color:'+D['panel']+';'),['SaveFeedback/confirmed-saved-with-stale-partial','MetricValue/retained-read-after-save'],read_snapshot={'value':66.7,'unit':'percent','change':1.13,'change_unit':'pp','available':7,'eligible':8,'observed':'2026-10-30T20:00:00Z','freshness':'stale','coverage':'partial'},write_snapshot={'status':'saved','object':'Breadth comparison','request':'fixture-save-01','confirmation':'illustrative_owner_confirmed_readback'},matched_input={'packet':'mobile-inputs/mobile-state-boards.json','board':'states-matrix','steps':['combined-dark-heading','combined-dark-value','combined-dark-status']},parent_reported_native_reference={'pending':'6YA-0','uncertain':'6YU-0','scope':'Parent-provided predecessor IDs only; not newly inspected by this generator.'},checkpoint_after=True)

 add('build-contract','board',frame('Fault composition implementation boundary',label('BUILD CONTRACT · OUTSIDE THE PRODUCT')+body('These are portable presentation fixtures, not new domain data, schemas, billing decisions or endpoints. The source-bound retained table rows and Macro summary keep their original values and identities. Counterfactual definition/currency inputs are explicitly separate from the normal Company fixture.')+body('Bind filter clearing, coverage inspection, retry reads, evidence return and saved-object opening to the existing host owner. Error does not erase valid retained rows; source unavailability is not access denial; unknown counts and periods do not become zero. A confirmed save changes the write axis only.')+body('Native application/readback, exact geometry, screenshots, keyboard/ARIA, focus/scroll return, real source integration and actual write readback remain unverified. VirtualizedDataInspector, CountLadder, LifecycleRail and DecisionRow / VerdictHero remain retained and unqualified.'),'width:1344px;padding:20px 24px;gap:8px;background-color:'+D['raised']+';'),['Build/source-and-verification-boundary'])
 assert len(b['steps'])==25,len(b['steps'])
 return {'schema':'f02.paper.fault-compositions.v1','status':'PREPARED_NOT_APPLIED','file_id':FILE,'system_version':'F02-SYSTEM/1.0.0-candidate.2','boards':[b],'append_to_existing':[],
  'fixture_policy':'Every fault state is an explicit illustrative input. Counterfactual definition/currency/publication/availability states do not overwrite normal consumer facts or establish real domain authority.',
  'source_references':[{'path':'SYSTEM_CONTRACT.md','sections':['4. Component anatomy, variants and failure treatment','4.1 Density and truncation','4.2 Chart grammar']},{'path':'INTERACTION_STATES.md','sections':['Copy and recovery matrix','Independent state axes','Control/action contracts']},{'path':'SOURCE_AND_DATA_CONTRACT.md','sections':['4.1 Numeric and unit rules','4.2 Time and freshness rules','5.1 Table, chart and overlay behavior','11.3 Closed-form criteria for the open consumer integration gap']}],
  'fixture_bindings':{'retained_table_rows':retained,'retained_macro_source_identity':identity,'counterfactual_definition':{'prior_value':23.3,'prior_basis':'all operations','current_value':24.5,'current_basis':'continuing operations','unit':'percent','comparable_restatement':None,'change':None},'counterfactual_currency':{'prior_value':36.0,'prior_currency':'USD','current_value':48.0,'current_currency':'EUR','scale':'bn','authorized_fx':None,'change':None}},
  'unchanged_core_packet':{'path':'core-supplement-inputs.json','sha256':CORE_SHA},'paper_calls':0,'browser_calls':0,'native_binding':'Parent must bind actual native IDs and review actual renders. No native construction is asserted.'}

def validate(packet):
 assert hashlib.sha256((HERE/'core-supplement-inputs.json').read_bytes()).hexdigest()==CORE_SHA,'Original 60-group packet changed.'
 b=packet['boards'][0];seen={'board'};variant_names=[]
 for s in b['steps']:
  assert s['key'] not in seen and s['parent'] in seen,(s['key'],s['parent']);seen.add(s['key'])
  root=ET.fromstring(s['html']);assert root.tag=='div'
  assert not re.search(r'<table|display\s*:\s*grid|(?:^|;)\s*margin(?:-|:)',s['html'])
  variant_names+=s['variants']
 assert len(b['steps'])==25 and b['width']==1440 and b['pageId']=='p-4-0'
 assert b['artboardStyles']['height']=='fit-content'
 steps={s['key']:s for s in b['steps']}
 for binding in packet['fixture_bindings']['retained_table_rows']:
  a=FIXTURE['rows'][binding['fixture_row_index']]
  assert binding['values']==[a[0],a[5],a[6],a[7],a[8],'Evidence']
  row_root=ET.fromstring(steps[binding['step']]['html'])
  for cell_index in [1,2,3]:
   child=row_root[cell_index][0]
   assert 'align-items:flex-end' in child.attrib['style'] and 'text-align:right' in child.attrib['style']
 assert steps['tabs-loading-panel']['result_count'] is None and steps['tabs-empty-panel']['result_count']==0
 assert steps['tabs-loading-panel']['requested_context']==steps['tabs-empty-panel']['requested_context']
 assert steps['unquantified-coverage-state']['coverage']=={'available':7,'eligible':None,'status':'unknown'}
 source=(ROOT/'pattern-lab.html').read_text()
 assert "['Communication services','通信服务',66.7,1.13,'21 / 21']" in source
 combined=steps['combined-confirmed-saved']
 assert combined['read_snapshot']=={'value':66.7,'unit':'percent','change':1.13,'change_unit':'pp','available':7,'eligible':8,'observed':'2026-10-30T20:00:00Z','freshness':'stale','coverage':'partial'}
 old=json.loads((HERE/'mobile-inputs/mobile-state-boards.json').read_text())
 pending={s['key']:s for board in old['boards'] if board['key']=='states-matrix' for s in board['steps']}
 actual=' '.join(ET.fromstring(combined['html']).itertext())
 for k in ['combined-dark-heading','combined-dark-value','combined-dark-status']:
  text=' '.join(ET.fromstring(pending[k]['html']).itertext())
  for phrase in ['66.7%','+1.13 pp','Older source: 30 Oct, 20:00 UTC','Partial coverage: 7 of 8','The expected update has not arrived. One observation is still missing.']:
   if phrase in text:assert phrase in actual,phrase
 return {'schema':'f02.paper.fault-composition-local-validation.v1','status':'PASS_LOCAL_INPUT_STRUCTURE_AND_FIXTURE_CONSISTENCY','steps':len(b['steps']),'variant_labels':variant_names,'single_roots':True,'parents_resolve_in_order':True,'core_packet_unchanged':True,'retained_financial_rows_match_fixture':3,'numeric_cells_have_fixed_width_and_end_alignment':True,'matched_loading_empty_context':True,'saved_read_caveats_preserved':True,'no_paper_or_browser_operations':True,'not_proved':['Native import/editability/fit','Actual keyboard, ARIA, focus, touch or scroll','Real source/entitlement/write integration','Independent native design review or formal RIG']}

if __name__=='__main__':
 packet=build();checks=validate(packet)
 out=HERE/'fault-composition-inputs.json';out.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
 (HERE/'fault-composition-validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'board':packet['boards'][0]['key'],'steps':len(packet['boards'][0]['steps']),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'core_unchanged':True},indent=2))
