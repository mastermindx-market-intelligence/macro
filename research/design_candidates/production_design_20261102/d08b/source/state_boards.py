"""Final review-state specimens. Run this entry point to generate all compositions."""
import json
import additional_boards as a
from build_design import tx,box,row,col,button,panel,shell,D,L
d=a.d

ops=[{'name':'title','html':box('Rendered states title',32,24,1376,100,col(tx('D08B / Rendered exposure states',30,weight=600)+tx('Same phone task and shell · illustrative state fixtures · source/access decisions stay with their owners',13,D['muted']),14))}]
states=[('Loading','SPY exposure','Loading book for Nov 2…','Loading the selected SPY book.','loading'),('Empty with reason','SPY exposure','No qualified observations','The dated response contains no qualified rows in this scope.','empty'),('First read failed','SPY exposure','Could not read exposure','No verified snapshot is available for this root.','error'),('Refresh failed','SPY exposure','Last available · Nov 2','Refresh failed. The observation below retains its original date.','stale'),('Access unresolved','SPY exposure','Access could not be verified','Protected values remain hidden while access is unresolved.','access'),('Verified plan requirement','SPY exposure','Access requires an eligible plan','Your current access does not include this resource.','plan')]
for i,(label,title,headline,body,kind) in enumerate(states):
 x=32+(i%3)*478;y=144+(i//3)*850
 inner=box('State shell '+kind,0,0,390,56,row(tx('☰',18)+tx('MASTERMIND',12,weight=700)+tx('EN',12,D['muted']),12,'justify-content:space-between'),D,f'padding:0 16px;justify-content:center;background:{D["panel"]};border-bottom:1px solid {D["line"]};')
 inner+=box('State context '+kind,16,76,358,100,col(row(tx(title,25,weight=600)+button('Views ▾'),10,'justify-content:space-between')+tx('Requested · SPY · Nov 2, 2026',12,D['muted'])+tx(label,12,D['gold']),12))
 inner+=box('State controls '+kind,16,194,358,44,row(button('Gamma ▾')+button('Net ▾')+button('Scope ▾'),10))
 if kind=='loading':
  content=col(tx(headline,23,weight=600)+tx(body,13,D['muted'],style='line-height:21px')+''.join(f'<div style="height:32px;width:{w}px;border-radius:6px;background:{D["raised"]};"></div>' for w in [180,318,318,250,318,280])+tx('Source date and coverage appear when ready.',12,D['muted']),18)
 elif kind=='stale':
  content=col(tx(headline,23,weight=600)+tx(body,13,D['muted'],style='line-height:21px')+tx('Known subtotal +500M',28,D['pos'],600)+tx('108/112 rows · 4 excluded',13,D['muted'])+tx('Full total unavailable · market coverage unknown',12,D['muted'],style='line-height:20px')+tx('Spot Nov 2 16:00:02 ET · OI Oct 30',12,D['muted'])+tx('OI reported Nov 2 · available Nov 3 03:52 ET',12,D['muted'])+row(tx('750 / Nov 06',18)+tx('+268M',22,D['pos']),14,'justify-content:space-between')+button('Inspect dated node',D,True)+button('Retry refresh'),14)
 else:
  action={'empty':'Change scope','error':'Retry read','access':'Retry access check','plan':'View access details'}[kind]
  content=col(tx(headline,26,weight=600)+tx(body,14,D['muted'],style='line-height:23px')+tx('The requested root, book and origin stay intact.',13,D['muted'],style='line-height:21px')+button(action,D,True)+button('Return to originating view'),22)
 inner+=panel('State body '+kind,16,262,358,484,content)
 inner+=box('State footer '+kind,16,764,358,30,tx('Source & status ↗',13,D['blue']))
 ops.append({'name':'state-'+kind,'html':box('Phone state '+kind,x,y,390,812,inner,D,f'border:1px solid {D["line"]};border-radius:16px;background:{D["bg"]};')})
d.boards.append({'key':'B15','name':'B15 · Rendered loading empty failure access · R1','width':1440,'height':1834,'theme':'dark','locale':'EN','ops':ops})

ops=shell(D,1440,1120)
ops += [
 {'name':'title','html':box('Nonzero cohort identity',248,88,1168,92,col(row(tx('SPY / Compare reported cohorts',28,weight=600)+button('Back to selected node'),18,'justify-content:space-between')+tx('Oct 30 → Nov 2 · same identity, scope and definition · illustrative comparison fixture',12,D['muted'])+tx('Knowledge cutoff: Nov 3, 2026 · 04:15 ET · current-knowledge comparison',12,D['muted']),8))},
 {'name':'summary','html':panel('Matched versus reported population',248,206,1168,142,row(col(tx('MATCHED COHORT ONLY',11,D['muted'])+tx('+44M',40,D['pos'],600)+tx('2 finite matched contracts · $ / +1% spot',12,D['muted']),10)+col(tx('OBSERVED ROWS',11,D['muted'])+tx('5 → 5',30,weight=600)+tx('4 qualified in each book',12,D['muted']),10)+col(tx('FULL-BOOK CHANGE',11,D['muted'])+tx('Unavailable',27,weight=600)+tx('Do not include nonmatching rows in this delta',12,D['muted']),10),40,'justify-content:space-between'))},
 {'name':'matched','html':panel('Finite matched contract rows',248,372,824,298,col(tx('Matched evidence',18,weight=600)+row(tx('Nov 06 / 750 Call',15,style='width:270px')+tx('+380M → +400M',19,style='width:250px')+tx('+20M',20,D['pos']),18,'height:56px')+row(tx('Nov 06 / 750 Put',15,style='width:270px')+tx('−156M → −132M',19,style='width:250px')+tx('+24M',20,D['pos']),18,'height:56px')+tx('Net +224M → +268M · gross 536M → 532M · gross change −4M',13,D['muted'])+tx('This is observed exposure change, not trade flow or economic entry/exit.',13,D['muted']),20))},
 {'name':'counts','html':panel('Nonzero membership and qualification',1096,372,320,298,col(tx('Excluded from matched delta',17,weight=600)+row(tx('Previous-only reported',13)+tx('1',21),12,'justify-content:space-between')+row(tx('Current-only reported',13)+tx('1',21),12,'justify-content:space-between')+row(tx('Qualification gained',13)+tx('1',21),12,'justify-content:space-between')+row(tx('Qualification lost',13)+tx('1',21),12,'justify-content:space-between')+tx('Set changes and qualification changes are distinct.',12,D['muted'],style='line-height:20px'),18))},
 {'name':'unmatched','html':panel('Excluded population evidence',248,694,1168,302,col(tx('What changed in the reported population',18,weight=600)+row(tx('Nov06 / 755 Call',14,style='width:270px')+tx('+10M → absent',16,style='width:270px')+tx('Previous-only reported',13,D['muted']),22,'height:44px')+row(tx('Nov06 / 765 Call',14,style='width:270px')+tx('Absent → +30M',16,style='width:270px')+tx('Current-only reported',13,D['muted']),22,'height:44px')+row(tx('Nov06 / 755 Put',14,style='width:270px')+tx('Unknown → −40M',16,style='width:270px')+tx('Qualification gained',13,D['muted']),22,'height:44px')+row(tx('Nov06 / 760 Call',14,style='width:270px')+tx('+20M → unknown',16,style='width:270px')+tx('Qualification lost',13,D['muted']),22,'height:44px'),12))},
 {'name':'actions','html':box('Cohort source actions',248,1020,1168,44,row(button('Inspect source populations',D,True)+button('Change comparison basis')+button('Return to node'),12))}
]
d.boards.append({'key':'B16','name':'B16 · Nonzero cohort differences · 1440 · Dark EN · R1','width':1440,'height':1120,'theme':'dark','locale':'EN','ops':ops})

ops=shell(L,390,1390)
ops += [
 {'name':'title','html':box('Exact contract detail identity',16,76,358,158,col(row(tx('← Back to node',15,weight=600)+button('Close',L),10,'justify-content:space-between')+tx('SPY · Nov 06 · 750 Call',25,weight=600)+tx('2026-11-06 · source-qualified example row',12,L['muted'])+tx('Illustrative contract fixture · no market order',12,L['muted']),16),L)},
 {'name':'identity','html':panel('Full source contract identity',16,254,358,232,col(tx('Exact source identity',18,weight=600)+tx('Namespace D08B:fixture',13)+tx('Root SPY · expiry 2026-11-06',14)+tx('Strike 750 USD · right Call',14)+tx('Source row fixture:SPY:20261106:750:C',12,L['muted'],style='line-height:20px')+tx('Source session Nov 2 · copied evidence retained',12,L['muted'],style='line-height:20px'),16),L)},
 {'name':'terms','html':panel('Contract terms',16,506,358,280,col(tx('Contract terms · example supplied values',16,weight=600)+row(tx('Multiplier',13,L['muted'])+tx('100',16),12,'justify-content:space-between')+row(tx('Deliverable',13,L['muted'])+tx('100 SPY shares',15),12,'justify-content:space-between')+row(tx('Exercise',13,L['muted'])+tx('American',15),12,'justify-content:space-between')+row(tx('Settlement',13,L['muted'])+tx('Physical',15),12,'justify-content:space-between')+tx('The source row and owning validator establish these terms; display ticker alone does not.',12,L['muted'],style='line-height:20px'),17),L)},
 {'name':'actions','html':box('Explicit contract handoff',16,806,358,126,col(button('Continue with this contract in Plan',L,True)+button('Return to 750 / Nov 06',L),14),L)},
 {'name':'ambiguous','html':panel('Ambiguous terms state specimen',16,952,358,302,col(tx('Alternative state · terms unresolved',17,weight=600)+tx('This source coordinate is not a qualified contract.',21,weight=600,style='line-height:29px')+tx('Adjusted root / multiplier / deliverable: not resolved',13,L['muted'],style='line-height:21px')+button('Inspect original source',L)+tx('Plan handoff unavailable · retain the original node and show the owner’s validation reason.',12,L['muted'],style='line-height:20px'),18),L)},
 {'name':'footer','html':box('Contract ownership note',16,1274,358,98,tx('C owns shortlist and Plan validation, user assumptions, save and readback. Navigating here does not create a plan, persist research or place an order.',12,L['muted'],style='line-height:20px'),L)}
]
d.boards.append({'key':'B17','name':'B17 · Exact contract and ambiguous terms · 390 · Light EN · R1','width':390,'height':1420,'theme':'light','locale':'EN','ops':ops})
for b in d.boards:
 if b['key']=='B16':
  nav=''.join(o['html'] for o in b['ops'] if o.get('target')=='Shell navigation')
  for o in b['ops']:
   if o['name']=='rail':o['html']=o['html'][:-6]+nav+'</div>'
  b['ops']=[o for o in b['ops'] if o.get('target')!='Shell navigation']
(d.OUT/'comparison-illustrative-fixture.json').write_text(json.dumps({'kind':'illustrative_design_fixture','scope':'five-reported-members','knowledgeCutoff':'2026-11-03T04:15:00-05:00','cutoffMode':'current_knowledge_fixture','previousAvailableAt':'2026-11-02T03:52:00-05:00','currentAvailableAt':'2026-11-03T03:52:00-05:00','previous':[{'expiry':'2026-11-06','strike':750,'right':'C','valueMillions':380},{'expiry':'2026-11-06','strike':750,'right':'P','valueMillions':-156},{'expiry':'2026-11-06','strike':755,'right':'C','valueMillions':10},{'expiry':'2026-11-06','strike':755,'right':'P','valueMillions':None},{'expiry':'2026-11-06','strike':760,'right':'C','valueMillions':20}],'current':[{'expiry':'2026-11-06','strike':750,'right':'C','valueMillions':400},{'expiry':'2026-11-06','strike':750,'right':'P','valueMillions':-132},{'expiry':'2026-11-06','strike':765,'right':'C','valueMillions':30},{'expiry':'2026-11-06','strike':755,'right':'P','valueMillions':-40},{'expiry':'2026-11-06','strike':760,'right':'C','valueMillions':None}]},indent=2))
for b in d.boards:
 if b['key']=='B00':
  b['height']=1060
  b['ops'].append({'name':'source-link','html':box('Canonical source and ownership',32,916,1376,116,col(tx('Owner D08B · Integrator D08 · F01/F02 candidate.4 unreleased · RIG draft',13,D['muted'])+tx('Candidate: Terminal / p-12-0 · Read me: p-14-0 · Board IDs and freeze digests in EVIDENCE_MANIFEST.json',12,D['muted'])+tx('https://github.com/mastermindx-market-intelligence/macro/blob/design/d08b-exposure-volatility-20261104-c3/research/design_candidates/production_design_20261102/d08b/SOURCE_BUILD_CONTRACT.md',11,D['blue'],style='line-height:18px'),12))})

(d.OUT/'paper-compositions.json').write_text(json.dumps(d.boards,ensure_ascii=False,indent=2))
print(json.dumps({'boards':len(d.boards),'operations':sum(len(x['ops']) for x in d.boards)}))
