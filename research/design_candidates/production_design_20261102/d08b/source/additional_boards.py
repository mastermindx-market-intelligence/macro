"""Additional source-qualified retention compositions; execute to build the full set."""
import json, math
from pathlib import Path
import build_design as d
from build_design import tx,box,row,col,button,panel,shell,D,L

ops=[{'name':'title','html':box('Interaction annotations title',32,28,1376,88,col(tx('D08B / Control and transition annotations',30,weight=600)+tx('Read beside B01–B14 · implementation obligations, not runtime proof',14,D['muted']),14))}]
notes=[
('B01 · Matrix and inspector','Arrow keys move cell focus; Enter selects. Selection binds exact root, snapshot, ISO expiry, strike, lens, metric and unit.','Scope changes preserve the node if present. Otherwise show the original dated node and ask for a new selection. No nearest-node substitution.'),
('B02 / B10 · Phone controls','Views opens workspace destinations. Research opens range, breakdown, price context, compare, history/replay and source controls.','A menu uses modal focus containment, Esc/Close, and returns focus to its trigger. Changing view neither saves nor changes the selected observation.'),
('B03 · Exact contract handoff','A matrix cell may aggregate both rights. Inspect actual source members; choose the precise root, expiry, strike and right.','C validates accepted shortlist shapes, stale policy and terms. Missing multiplier/deliverable or ambiguous series cannot create an invented tradable instrument.'),
('B04 / B08 · Volatility','Expiry is a date identity, not a nearest-tenor guess. Missing selected expiry stays selected. Do not connect a line through an unavailable point.','IV/RV are percent numbers; adapter converts once if required. Published VRP remains verbatim. RR25 methods with opposite subtraction orders stay separate.'),
('B05 / B06 / B11 · Equal access','3D and exact 2D share the qualified projection and selection. Window, cap, mode, unit and full-lens normalization stay unchanged.','Gamma Surface is discrete. Phone exact rows are 48px; zero and missing are distinct. Every admitted row remains reachable after rendering limits or WebGL failure.'),
('B07 · Comparison basis','Compare only equal identity/scope/definition and advancing source sessions with both observations available at the cutoff.','Intersect finite actual contract members. Show set additions/deletions and qualification gained/lost separately. Net, gross and magnitude changes have different labels.'),
('B09 · Failure and access','Clear data immediately on root change. A refresh failure may keep only same-root authorized prior evidence with its original date.','Access unknown is not plan-required. Retry is explicit for reads. Durable save stays with the admitted owner and requires readback; unknown effects are not resubmitted.'),
('B13 / B14 · Strong incumbents','Research Lab mirrors side for separation; hollow marks encode negative ΔOI. Expiry depth is ordinal. Exact rows include zero/null and values beyond the draw cap.','Level labels may move to avoid collisions; price ticks never move. Null regime remains Unknown. Brightness is a source score, not a probability.')]
for i,(title,body,detail) in enumerate(notes):
 ops.append({'name':f'note-{i}','html':panel(title,32+(i%2)*704,136+(i//2)*254,680,230,col(tx(title,20,weight=600)+tx(body,14,style='line-height:23px')+tx(detail,12,D['muted'],style='line-height:20px'),16))})
d.boards.append({'key':'B12','name':'B12 · Interaction and state annotations · R1','width':1440,'height':1170,'theme':'dark','locale':'EN','ops':ops})

chain=[]
for ei,exp in enumerate(['2026-11-06','2026-11-20','2026-12-18']):
 for ki,k in enumerate([740,745,750,755,760]):
  for si,side in enumerate(['C','P']):
   value=(ei+1)*65+(ki+1)*83+si*47
   doi=-320 if (ei,ki,si)==(0,2,0) else (-value if (ei+ki+si)%3==0 else value)
   if (ei,ki,si)==(2,0,0):doi=0
   if (ei,ki,si)==(2,0,1):doi=None
   chain.append({'root':'SPY','expiry':exp,'strike':k,'side':side,'volume':value*9,'oi':value*25,'doi':doi})
fullmax=max(abs(r['doi']) for r in chain if r['doi'] is not None)
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="784" height="386" viewBox="0 0 784 386">']
for e in range(3):
 x=392+e*30;y=332-e*23
 svg.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-240}" stroke="{D["line"]}"/>')
 svg.append(f'<text x="{x+8}" y="{y+18}" fill="{D["muted"]}" font-family="Inter" font-size="11">{["Nov06","Nov20","Dec18"][e]}</text>')
for r in chain:
 if r['doi'] in [0,None]:continue
 e=['2026-11-06','2026-11-20','2026-12-18'].index(r['expiry']);x=392+(1 if r['side']=='C' else -1)*abs(r['doi'])/fullmax*230+e*30;y=332-(r['strike']-740)/20*240-e*23
 radius=max(1,min(17,math.sqrt(abs(r['doi'])/fullmax)*17));color=D['blue'] if r['side']=='C' else D['neg'];fill='none' if r['doi']<0 else color
 svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="{color}" stroke-width="2"/>')
 if r['expiry']=='2026-11-06' and r['strike']==750 and r['side']=='C':
  svg.append(f'<circle cx="{x}" cy="{y}" r="{radius+5}" fill="none" stroke="{D["text"]}" stroke-width="2"/>')
for k in [740,750,760]:svg.append(f'<text x="12" y="{332-(k-740)/20*240}" fill="{D["muted"]}" font-family="Inter" font-size="12">{k}</text>')
svg.append(f'<text x="110" y="30" fill="{D["neg"]}" font-family="Inter" font-size="13">Puts ← magnitude</text><text x="510" y="30" fill="{D["blue"]}" font-family="Inter" font-size="13">magnitude → Calls</text>')
# Absolute magnitude calibration is referenced to the front expiry's zero spine.
svg.append(f'<line x1="162" y1="364" x2="622" y2="364" stroke="{D["muted"]}"/>')
for sign in [-1,1]:
 for v in [0,250,500,657]:
  if sign==-1 and v==0:continue
  xx=392+sign*v/fullmax*230
  svg.append(f'<line x1="{xx}" y1="360" x2="{xx}" y2="368" stroke="{D["muted"]}"/><text x="{xx}" y="381" text-anchor="middle" fill="{D["muted"]}" font-family="Inter" font-size="10">{v}</text>')
svg.append(f'<text x="8" y="380" fill="{D["muted"]}" font-family="Inter" font-size="11">|ΔOI| · contracts</text><text x="678" y="142" fill="{D["muted"]}" font-family="Inter" font-size="11">Marker area</text>')
for v,yy in [(100,176),(320,230),(657,284)]:
 radius=max(1,min(17,math.sqrt(v/fullmax)*17))
 svg.append(f'<circle cx="716" cy="{yy}" r="{radius}" fill="none" stroke="{D["text"]}" stroke-width="1.5"/><text x="742" y="{yy+4}" fill="{D["muted"]}" font-family="Inter" font-size="11">{v}</text>')
svg.append('</svg>')
ops=shell(D,1440,1220)
ops += [
 {'name':'title','html':box('Chain lab identity',248,88,1168,88,col(row(tx('SPY / Chain investigation',28,weight=600)+button('Back to exposure'),18,'justify-content:space-between')+tx('Published-coordinate study · Nov 2, 2026 · illustrative fixture',12,D['muted']),14))},
 {'name':'controls','html':box('Chain lab research controls',248,196,1168,44,row(button('3D + exact table',D,True)+button('Volume / OI / ΔOI ▾')+button('Both sides ▾')+button('All 3 expiries ▾')+button('Camera ▾'),10))},
 {'name':'cloud','html':panel('Published coordinate point cloud',248,264,824,520,col(row(tx('ΔOI by strike, side and expiry',16,weight=600)+tx('28 / 30 marks',12,D['muted']),12,'justify-content:space-between')+''.join(svg)+tx('Hollow = negative ΔOI · X distance from each expiry zero = |ΔOI| · depth is ordinal',12,D['muted'])+tx('Marker area ∝ |ΔOI| · 2px minimum / 34px cap in this view · full-book scale',12,D['muted']),12))},
 {'name':'inspector','html':panel('Chain source coordinate inspector',1096,264,320,520,col(tx('SELECTED COORDINATE',11,D['muted'])+tx('750 · Nov 06 · Call',23,weight=600)+tx('−320 contracts',30,D['neg'],600)+tx('Published ΔOI · hollow marker',13,D['muted'])+tx('Instrument identity unverified',14)+tx('OI reference session: not supplied',12,D['muted'])+tx('Availability time: not supplied',12,D['muted'])+button('Inspect source coordinate',D,True)+button('Compare · 1 of 3 selected')+tx('Plan requires resolved actual contract terms.',12,D['muted'],style='line-height:20px'),18))},
 {'name':'table','html':panel('Chain exact row table',248,808,1168,264,col(row(tx('Exact rows · includes zero and missing',17,weight=600)+tx('50 rows/page · 30 admitted',12,D['muted']),16,'justify-content:space-between')+row(tx('Expiry / strike / side',12,D['muted'],style='width:320px')+tx('ΔOI',12,D['muted'],style='width:150px')+tx('OI',12,D['muted'],style='width:170px')+tx('State / action',12,D['muted']),20)+row(tx('Nov 06 / 750 / Call',15,style='width:320px')+tx('−320',18,D['neg'],style='width:150px')+tx('7,850',17,style='width:170px')+tx('Selected · Inspect',14),20,'height:48px')+row(tx('Dec 18 / 740 / Call',15,style='width:320px')+tx('0',18,style='width:150px')+tx('6,950',17,style='width:170px')+tx('Measured zero · Inspect',14),20,'height:48px')+row(tx('Dec 18 / 740 / Put',15,style='width:320px')+tx('—',18,style='width:150px')+tx('8,125',17,style='width:170px')+tx('ΔOI not supplied · Inspect',14),20,'height:48px'),12))},
 {'name':'footer','html':box('Chain additional access',248,1096,1168,92,col(row(button('Exact table only')+button('Reset / front / top')+button('Source & exclusions')+button('Volatility for matching session'),12)+tx('Draw cap: 20,000 nonzero marks. Exact table retains all admitted rows. No fitted IV surface or automatic saved investigation.',12,D['muted']),18))}
]
d.boards.append({'key':'B13','name':'B13 · Published chain 3D + table · 1440 · Dark EN · R1','width':1440,'height':1220,'theme':'dark','locale':'EN','ops':ops})

levels=[('Call wall',800),('Flip',769.5),('Anchor',768),('Cluster',760),('Cluster',750),('Put wall',740),('Trapdoor',735)]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="784" height="452" viewBox="0 0 784 452">']
def yy(p):return 420-(p-730)/75*382
svg.append(f'<line x1="320" y1="26" x2="320" y2="426" stroke="{L["line"]}" stroke-width="2"/>')
for title,price in levels:
 y=yy(price);label_y=y+(-14 if price==769.5 else 12 if price==768 else 0);sel=price==750;color=L['blue'] if price>=752.1 else L['gold'];r=8 if sel else 5
 svg.append(f'<circle cx="320" cy="{y}" r="{r}" fill="{color}"/><line x1="{325+r}" y1="{y}" x2="410" y2="{label_y}" stroke="{L["line"]}"/><text x="270" y="{label_y+5}" text-anchor="end" fill="{L["text"]}" font-family="Inter" font-size="14">{price:g}</text><text x="426" y="{label_y+5}" fill="{L["text"]}" font-family="Inter" font-size="15">{title}{" · selected" if sel else ""}</text>')
y=yy(752.1);svg.append(f'<line x1="24" y1="{y}" x2="760" y2="{y}" stroke="{L["gold"]}" stroke-dasharray="5 4"/><text x="24" y="{y-10}" fill="{L["gold"]}" font-family="Inter" font-size="13">Spot 752.10</text>');svg.append('</svg>')
ops=shell(L,1440,1120)
ops += [
 {'name':'title','html':box('Levels identity',248,88,1168,90,col(row(tx('SPY / Positioning & levels',28,weight=600)+button('Back to selected node',L),18,'justify-content:space-between')+tx('Dated model context · Nov 2, 2026 · illustrative fixture',12,L['muted']),14),L)},
 {'name':'controls','html':box('Levels controls',248,200,1168,44,row(button('Price map',L,True)+button('Positioning',L)+button('Blue / orange palette',L)+button('Source convention',L),10),L)},
 {'name':'map','html':panel('Exact-price level map',248,268,824,558,col(row(tx('Price levels and confluence',17,weight=600)+tx('USD · model-derived',12,L['muted']),12,'justify-content:space-between')+''.join(svg)+tx('Label collision handling may move text; price ticks and leader anchors remain exact.',12,L['muted']),12),L)},
 {'name':'inspector','html':panel('Level source inspector',1096,268,320,558,col(tx('SELECTED LEVEL',11,L['muted'])+tx('750 · Cluster',27,weight=600)+tx('Exact source price',14)+tx('Regime: Unknown',20,weight=600)+tx('The source has not supplied a regime.',12,L['muted'],style='line-height:20px')+tx('Source score: display context only',13,L['muted'])+tx('Spot timestamp and model as-of remain separate.',13,L['muted'],style='line-height:20px')+button('View source notes',L,True)+button('Inspect related exposure',L)+tx('No price probability follows from brightness or label placement.',12,L['muted'],style='line-height:20px'),20),L)},
 {'name':'related','html':panel('Positioning retained investigation',248,850,1168,178,col(row(tx('Continue positioning research',18,weight=600)+button('Positioning workspace ↗',L),16,'justify-content:space-between')+row(button('Observed change',L)+button('Expiry structure',L)+button('Flow context',L)+button('Volatility context',L)+button('Source clocks & coverage',L),10)+tx('Keep scenario, hedge-pressure model and observed flow definitions distinct. Preserved metrics remain subject to each source contract.',12,L['muted']),16),L)}
]
d.boards.append({'key':'B14','name':'B14 · Levels and positioning context · 1440 · Light EN · R1','width':1440,'height':1120,'theme':'light','locale':'EN','ops':ops})
for b in d.boards:
 if b['key'] in ['B13','B14']:
  nav=''.join(o['html'] for o in b['ops'] if o.get('target')=='Shell navigation')
  for o in b['ops']:
   if o['name']=='rail':o['html']=o['html'][:-6]+nav+'</div>'
  b['ops']=[o for o in b['ops'] if o.get('target')!='Shell navigation']
(d.OUT/'chain-illustrative-fixture.json').write_text(json.dumps({'kind':'illustrative_design_fixture','sourceNamespace':'D08B:fixture-chain','sourceSession':'2026-11-02','oiPositionSession':None,'availableAt':None,'scaleBasis':'full-admitted-snapshot','rows':chain},indent=2))
(d.OUT/'paper-compositions.json').write_text(json.dumps(d.boards,ensure_ascii=False,indent=2))
print(json.dumps({'boards':len(d.boards),'operations':sum(len(x['ops']) for x in d.boards)}))
