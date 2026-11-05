#!/usr/bin/env python3
"""Source-only v3 count-authoritative fixture packets. Never writes applied inputs."""
from __future__ import annotations
import copy, hashlib, html, json, re
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction
from pathlib import Path

getcontext().prec = 50
HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]
OUT = HERE / 'effective'
OUT.mkdir(parents=True, exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    return sha(path.read_bytes())
def q(x, places=2):
    d=Decimal(x.numerator)/Decimal(x.denominator) if isinstance(x,Fraction) else Decimal(str(x))
    return format(d.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP),f'.{places}f')
def signed(x, places=2): return ('+' if x>0 else '') + q(x,places)
def stats(n,d,p,eligible=None):
    cur=Fraction(n*100,d); prior=Fraction(p*100,d); delta=cur-prior
    return {'current_above':n,'prior_above':p,'covered':d,'eligible':eligible or d,
            'current_percent_fraction':str(cur),'prior_percent_fraction':str(prior),
            'delta_pp_fraction':str(delta),'current_percent_1dp':q(cur,1),
            'current_percent_2dp':q(cur),'prior_percent_2dp':q(prior),
            'delta_pp_2dp':signed(delta),'delta_bps_0dp':signed(delta*100,0),
            'relative_percent_2dp':signed(Fraction((n-p)*100,p)) if p else None}

SECTORS=[
 ('technology','Technology','科技',286,207,201,'42'),
 ('industrials','Industrials','工业',267,189,185,'65'),
 ('financials','Financials','金融',500,346,343,'52'),
 ('communication_services','Communication services','通信服务',177,118,116,'21'),
 ('consumer_discretionary','Consumer discretionary','非必需消费',375,238,241,'47'),
 ('health_care','Health care','医疗保健',54,33,33,'54'),
 ('utilities','Utilities','公用事业',333,194,198,'28'),
 ('energy','Energy','能源',0,None,None,None),
 ('consumer_staples','Consumer staples','必需消费',250,139,138,'36'),
 ('materials','Materials','原材料',500,261,264,'23'),
]
HISTORY=[657,663,None,679,673,687,697,709]
DATES=['21 Oct','22 Oct','23 Oct','26 Oct','27 Oct','28 Oct','29 Oct','30 Oct']
RATES=[Fraction(n*100,1063) if n is not None else None for n in HISTORY]
U=stats(709,1063,697)
CORE={'information_technology':stats(742,1000,721,1006),'utilities':stats(132,250,133)}
macro={s[0]:stats(s[4],s[3],s[5]) for s in SECTORS if s[3]}
energy={'current_above':None,'prior_above':None,'covered':0,'eligible':82,
        'current_percent':None,'prior_percent':None,'delta_pp':None,'availability':'unavailable'}
contract={
 'schema':'f02.synthetic-participation-fixture.v3','status':'SOURCE_PREPARED_NATIVE_APPLICATION_PENDING',
 'authority':'Current proposed native participation fixture inputs only; synthetic, not a product API/data contract.',
 'namespace':'f02.fixture.v3/macro',
 'identity_policy':'Board/step keys and entity slugs remain stable. Only the versioned Macro fixture namespace advances v2 to v3; Company and Options v2 identities remain unchanged.',
 'historical_boundary':'Original applied packets, pattern-lab.html, old static sheets and frozen review evidence remain immutable historical v2 evidence. These v3 inputs do not imply product implementation or runtime behavior.',
 'calculation':{
  'rate_percent':'100 * above_count / covered_valid_count; calculate from integer counts, then round for display',
  'delta_pp':'100 * (current_above/current_covered - prior_above/prior_covered); never subtract rounded labels',
  'delta_bps':'10000 * (current_above/current_covered - prior_above/prior_covered); round this raw result, not rounded pp * 100',
  'relative_percent':'100 * (current_rate / prior_rate - 1); unavailable if prior rate is zero or unknown',
  'coverage':'covered_valid_count / eligible_count; numerator for rate is a separate above_count',
  'rounding':'decimal ROUND_HALF_UP after exact rational calculation; table rate 1dp, pp delta 2dp; core/evidence rate 2dp; bps 0dp',
  'sort':'current raw rate descending; missing rates last; stable entity tie-break; visible Above 50D downward arrow',
  'missing':'Energy 0/82 means no covered valid securities out of82eligible; above_count/rate/delta unavailable, never0%. Missing history point stays a gap.',
 },
 'cohorts':{
  'universe':{**U,'cohort':'Independent synthetic universe; not the aggregate of sector rows.',
      'source_identity':'f02.fixture.v3/macro/universe/share_above_50d/2026-10-30',
      'history':{'covered_per_available_session':1063,'above_counts':HISTORY,'dates':DATES,'available_sessions':7,'eligible_sessions':8,
                 'percent_2dp':[q(v) if v is not None else None for v in RATES]}},
  'core_component_sectors':{'cohort':'Component anatomy examples, independent of the Macro sector table.',**CORE,'energy':energy},
  'macro_sector_rows':{'cohort':'Independent synthetic sector sample rows, not a partition of the universe cohort.',
      'rows':macro|{'energy':energy},'sorted_entity_keys':[s[0] for s in SECTORS if s[0]!='energy']+['energy']},
 },
 'source_semantics':'Illustrative current/prior settled observations use the same valid cohort per row. No eligibility, provider, production count, market total, clock or entitlement semantics are inferred for real APIs.',
}
contract_hash=dump(HERE/'fixture-contract.json',contract)

expected=[('72.4','+2.10'),('70.8','+1.50'),('69.2','+0.60'),('66.7','+1.13'),('63.5','-0.80'),('61.1','0.00'),('58.3','-1.20'),('55.6','+0.40'),('52.2','-0.60')]
actual=[(macro[s[0]]['current_percent_1dp'],macro[s[0]]['delta_pp_2dp']) for s in SECTORS if s[3]]
assert actual==expected,(actual,expected)
assert [U[k] for k in ['current_percent_2dp','prior_percent_2dp','delta_pp_2dp','delta_bps_0dp','relative_percent_2dp']]==['66.70','65.57','+1.13','+113','+1.72']
assert macro['communication_services']['current_percent_2dp']=='66.67'
assert macro['communication_services']['prior_percent_2dp']=='65.54'
assert CORE['information_technology']['delta_pp_2dp']=='+2.10'
assert CORE['utilities']['delta_pp_2dp']=='-0.40'
assert all(0<=s['current_above']<=s['covered']<=s['eligible'] for s in [U,*CORE.values(),*macro.values()])
arithmetic={'schema':'f02.fixture-arithmetic-proof.v1','method':'Independent Fraction arithmetic and Decimal ROUND_HALF_UP from integer source tuples; assertions bind expected labels.',
 'universe':U,'core':CORE,'macro':macro,'energy':energy,'history':[{'date':d,'above':n,'covered':1063 if n is not None else None,'rate_1dp':q(r,1) if r is not None else None,'rate_2dp':q(r) if r is not None else None} for d,n,r in zip(DATES,HISTORY,RATES)],
 'checks':{'numerator_le_covered_le_eligible':True,'displayed_sector_rates_and_deltas_match':True,'communication_not_universe':True,'energy_unavailable_not_zero':True,'one_history_gap_on_23_oct':True,'sector_denominators_sum':sum(s[3] for s in SECTORS),'independent_cohorts_explicit':True},
 'fixture_contract_sha256':contract_hash}
dump(HERE/'arithmetic-validation.json',arithmetic)

def walk_strings(obj, fn):
 if isinstance(obj,str):return fn(obj)
 if isinstance(obj,list):return [walk_strings(x,fn) for x in obj]
 if isinstance(obj,dict):return {k:walk_strings(v,fn) for k,v in obj.items()}
 return obj
def namespace(s):return s.replace('f02.fixture.v2/macro/','f02.fixture.v3/macro/')
def macro_counts(s):
 s=namespace(s)
 for _,_,_,d,n,p,old in SECTORS:
  if old and int(old)!=d:
   s=s.replace(f'{old} / {old}',f'{d} / {d}').replace(f'{old}/{old}',f'{d}/{d}')
 return s
def replace_visible(h,old,new):
 return h.replace('>'+old+'<','>'+html.escape(new,quote=False)+'<')
def svg_for(width,height,low,high,theme='dark',left=44,right=20,top=20,bottom=30):
 ink='#1a1c20' if theme=='light' else 'var(--noir-text-primary)'
 line='#d8dadd' if theme=='light' else '#343434'
 pw=width-left-right;ph=height-top-bottom
 xy=lambda i,v:(left+i*pw/7,top+(high-float(v))/(high-low)*ph)
 parts=[]
 for tick in [low,(low+high)/2,high]:
  y=top+(high-tick)/(high-low)*ph;parts.append(f'<line x1="{left}" y1="{y:.4f}" x2="{width-right}" y2="{y:.4f}" stroke="{line}" stroke-width="1"/>')
 last=None
 for i,v in enumerate(RATES):
  if v is None:last=None;continue
  x,y=xy(i,v)
  if last:parts.append(f'<line x1="{last[0]:.4f}" y1="{last[1]:.4f}" x2="{x:.4f}" y2="{y:.4f}" stroke="{ink}" stroke-width="2"/>')
  parts.append(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="4" fill="{ink}"/>');last=(x,y)
 return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'+''.join(parts)+'</svg>'

def update_svg_data(svg, kind):
 """Keep original axes, labels, grid, colors and viewport; replace data marks only."""
 width=float(re.search(r'<svg[^>]*width="([0-9.]+)"',svg).group(1))
 if kind=='core':px,pw,py,ph,lo,hi,r,sw=80,1176,54,150,50,80,5,3
 elif kind=='consumer':px,pw,py,ph,lo,hi,r,sw=44,758,16,132,40,80,3.5,2.5
 else:px,pw,py,ph,lo,hi,r,sw=44,width-64,20,140,40,80,3.5,2.5
 fill=re.search(r'<circle\b[^>]*fill="([^"]+)"',svg).group(1)
 clean=re.sub(r'<circle\b[^>]*/>','',svg)
 clean=re.sub(r'<line\b(?=[^>]*stroke-width="(?:2(?:\.5)?|3)")[^>]*/>','',clean)
 parts=[];last=None
 for i,v in enumerate(RATES):
  if v is None:last=None;continue
  x=px+i*pw/7;y=py+(hi-float(v))/(hi-lo)*ph
  if last:parts.append(f'<line x1="{last[0]:.6f}" y1="{last[1]:.6f}" x2="{x:.6f}" y2="{y:.6f}" stroke="{fill}" stroke-width="{sw}"/>')
  parts.append(f'<circle cx="{x:.6f}" cy="{y:.6f}" r="{r}" fill="{fill}"/>');last=(x,y)
 return clean.replace('</svg>',''.join(parts)+'</svg>')

U_NOTE='Synthetic universe: 709/1063 × 100 = 66.70%; prior 697/1063 = 65.57%. Raw-count change +1.13 pp; relative +1.72%. Independent of sector examples; round only after calculation.'
C_NOTE='Communication sample: 118/177 × 100 = 66.67%; prior 116/177 = 65.54%; raw-count change +1.13 pp. Coverage177/177; independent of universe history7/8.'
C_ZH='通信示例：118/177 × 100 = 66.67%；上期116/177 = 65.54%；按原始计数计算差值+1.13个百分点。覆盖177/177；与总体历史7/8无关。'
CORE_NOTE='Core IT sample: 742/1000 × 100 = 74.20%; prior721/1000 = 72.10%; +2.10 pp. Coverage1000/1006, six missing. Separate from Macro sector samples.'
H_NOTE='Counts657,663,—,679,673,687,697,709 /1063. Seven of eight sessions; 23 Oct is missing. Independent universe cohort; no interpolation.'

sources=[
 ('mobile-inputs/mobile-state-boards.json','mobile-state-boards.json'),
 ('mobile-inputs/supplemental-boards.json','supplemental-boards.json'),
 ('core-supplement-inputs.json','core-supplement-inputs.json'),
 ('fault-composition-inputs.json','fault-composition-inputs.json'),
 ('foundation-inputs/boards.json','foundation-boards.json'),
 ('consumer-inputs/consumer-boards.json','consumer-boards.json'),
]
inventory=[];changes=[];source_before={}
for source_name,dest_name in sources:
 p=PAPER/source_name;raw=p.read_bytes();source_before[str(p)]=sha(raw);base=json.loads(raw);eff=copy.deepcopy(base)
 # Compose existing consumer alignment overrides before changing Macro fixture text.
 if dest_name=='consumer-boards.json':
  align=json.loads((PAPER/'repairs/numeric-alignment-source-input-override.json').read_text())
  for override in align['overrides']:
   if not override['board_key'].startswith('macro-'):continue
   st=next(s for b in eff['boards'] if b['key']==override['board_key'] for s in b['steps'] if s['key']==override['step_key'])
   assert sha(st['html'].encode())==override['source_step_html_sha256']
   st['html']=override['replacement_html']
 for b in eff.get('boards',[])+eff.get('append_to_existing',[]):
  key=b.get('key',b.get('target_board_key')); macro_board=key.startswith('macro-') or key.startswith('width-')
  core_board=key in ['metrics','controls','controls-variants','grammar']
  for st in b['steps']:
   k=st['key'];h=st['html'];old=h
   if macro_board: h=macro_counts(h)
   if core_board:
    h=h.replace('178 / 184','1000 / 1006').replace('178/184','1000/1006').replace('63 / 63','250 / 250')
   if macro_board and k in ['table','table-header']:
    h=replace_visible(h,'Above 50D','Above 50D ↓');h=replace_visible(h,'高于50D','高于50D ↓');h=replace_visible(h,'高于50日','高于50日 ↓');h=replace_visible(h,'高于50日均线','高于50日均线 ↓')
   # Energy is explicitly zero covered /82eligible; never zero rate.
   if macro_board and k.startswith('sector-') and ('>Energy<' in h or '>能源<' in h):
    h=replace_visible(h,'Not quantified','0 / 82');h=replace_visible(h,'未量化','0 / 82')
    # Rate and delta stay unavailable. The third em-dash text is the coverage cell.
    matches=list(re.finditer(r'>—<',h))
    if len(matches)>=3:
     m=matches[2];h=h[:m.start()]+'>0 / 82<'+h[m.end():]
   if macro_board:
    if k in ['evidence-value-0','value-0','overlay-values','dock-value']:
     h=replace_visible(h,'66.7%','66.67%')
    if k=='baseline':
     h=replace_visible(h,'上期65.57% → 本期66.70%；差值为+1.13个百分点，不是相对增长1.13%。',C_ZH)
    if k=='coverage-limit':
     h=h.replace('本行177/177与八期总体历史的7/8描述不同群体，不可合并。示例数值不代表实时生产者响应。','本行覆盖177/177；总体八期历史覆盖7/8，群体独立。示例不代表实时响应。')
    if k in ['overlay-limit','dock-footer']:
     for oldcopy in [
      'Row coverage177/177 and history coverage7/8 describe different populations. Do not combine their denominators or call this a market total.',
      'Row coverage 177/177 and history coverage 7/8 describe different populations. Do not combine their denominators or call this a market total.',
      'Row coverage 177/177 differs from universe-history coverage 7/8. The fixture is not a market total or a live source response.']:
      h=h.replace(oldcopy,C_NOTE)
    if k=='evidence-caveat':
     # Preserve wrapper/styles; replace its text leaf with exact selected-cohort calculation.
     h=re.sub(r'>([^<>]+)</div>\s*$',lambda m:'>'+html.escape(C_NOTE)+'</div>',h)
    if k=='evidence-field-0':h=h.replace('macro / communication-services','f02.fixture.v3/macro/sector/communication_services')
    if k=='table-behavior':h=h.replace('Raw numeric sorting; missing values last.','Above50D ↓; raw-rate descending; Energy unavailable last.')
    if k=='chart-footer':
     h=h.replace('Universe history is separate from the sector subset. Missing observations remain gaps; rows sort by raw values with explicit missing-last placement.',H_NOTE)
     h=h.replace('7 of 8 observations · no interpolation','709/1063 = 66.70% · history7/8')
     h=h.replace('8次观测中7次可用 · 不插值','709/1063 = 66.70% · 历史7/8')
    if k in ['metrics','metric']:
     h=h.replace('Universe share above 50D','Independent universe above50D')
     h=h.replace('above 50-day average','Universe709/1063 · above50D')
     h=h.replace('高于50日均线</div>','总体709/1063 · 高于50日</div>',1) if key.endswith('zh-390') else h
    if k in ['history-chart','chart'] and '<svg' in h:
     # Preserve accepted outer structure and native text labels; update point/line geometry from raw fractions.
     match=re.search(r'<svg[^>]*width="([0-9.]+)"[^>]*height="([0-9.]+)"[^>]*>.*?</svg>',h,re.S)
     if match:
      h=h[:match.start()]+update_svg_data(match.group(0),'consumer' if k=='history-chart' else 'mobile')+h[match.end():]
     h=h.replace('Exact %: 61.8 · 62.4 · unavailable · 63.9 · 63.3 · 64.6 · 65.57 · 66.7','Rounded %:61.8 ·62.4 ·— ·63.9 ·63.3 ·64.6 ·65.57 ·66.70')
     h=h.replace('7 of 8 observations. This universe is independent of the sector fixtures.',H_NOTE)
   if key=='metrics':
    if k=='metric-units':
     h=h.replace('65.57% → 66.70% is +1.13 percentage points. Relative change would be +1.72%, with a different label.',U_NOTE)
    if k=='table-caption':h=h.replace('Sector participation · illustrative settled observation','Component-sector samples · independent of Macro')
    if k=='source-receipt':
     h=h.replace('1000 / 1006 securities · partial coverage · illustrative fixture · connected transport is independent of source freshness.',CORE_NOTE+' Utilities:132/250 = 52.80%; prior133/250 = 53.20%; −0.40 pp; coverage250/250.')
    if k=='core-metric-bps':h=h.replace('+1.13 percentage points × 100 = +113 basis points. This is a unit conversion of the illustrative comparison, not a new published statistic.','Universe raw calculation: 10000 × (709−697)/1063 = 112.888… bps → +113 bps. Compute from counts; do not multiply a rounded pp label. Synthetic fixture only.')
    if k=='core-metric-unknown-age':h=h.replace('Participation · 66.70%','Universe709/1063 · 66.70%')
   if key=='controls' and k=='evidence-shell':
    h=h.replace('Missing securities are not counted as below-average observations.',CORE_NOTE)
   if key=='controls-variants':
    if k=='core-disclosure-heading':h=h.replace('The comparison and its coverage remain outside this optional region. Collapsed, expanded and failed-detail states keep the same explicit summary.',CORE_NOTE+' The summary stays visible in all three states.')
    if k=='core-disclosure-expanded-body':h=h.replace('Illustrative method: count covered securities with a valid close above their valid 50-day average. Divide by the covered securities with both observations. Show eligible-population coverage separately; missing securities are not classified as below average.',CORE_NOTE+' Count valid closes above valid50-day averages; missing securities are not below-average observations.')
    if k=='core-disclosure-mobile-label':h=h.replace('320px / optional method / three states','320px · Core IT74.20% · +2.10pp · coverage1000/1006')
    if k=='core-disclosure-mobile-expanded-body':h=h.replace('Count covered securities above their valid 50-day average. Divide by those with both observations. Show coverage separately; missing is not below average.','742/1000 ×100 =74.20%; prior721/1000 =72.10%; +2.10pp. Coverage1000/1006: six missing, never counted as below average. Component sample, separate from Macro.')
   if key=='fault-compositions':
    if k.startswith('unavailable-inspector'):
     h=macro_counts(h).replace('66.70%','66.67%').replace('65.57%','65.54%')
     h=h.replace('Coverage: 177 / 177 securities · baseline 65.54%','118/177 =66.67%; prior116/177 =65.54%; coverage177/177. Raw-count Δ+1.13pp.')
    if k=='combined-confirmed-saved':
     st['read_snapshot']['calculation']={'above':709,'covered':1063,'prior_above':697,'prior_covered':1063,'raw_rate_fraction':str(Fraction(70900,1063)),'display_rounding':'round after calculation'}
     h=h.replace('Participation</div>','Universe709/1063</div>')
     st['matched_input']['packet']='repairs/fixture-coherence-v1/effective/mobile-state-boards.json'
   if key=='states-matrix' and k in ['combined-dark-value','combined-light-value']:
    h=h.replace('Participation</div>','Universe709/1063</div>')
   if key=='grammar':
    if k=='chart-title':h=h.replace('Participation across eight settled sessions','Independent universe · eight settled sessions')
    if k=='chart':
     h=re.sub(r'<svg\b.*?</svg>',lambda m:update_svg_data(m.group(0),'core'),h,flags=re.S)
     h=h.replace('The line breaks at 26 Oct.','The line breaks at 23 Oct.')
     h=h.replace('26 Oct · —','26 Oct').replace('>23 Oct<','>23 Oct · —<')
    if k=='exact-values':
     # Eight stable date cells: regenerate only numeric leaf text, never the date labels.
     vals=iter(RATES)
     h=re.sub(r'>(?:[0-9]+\.[0-9]+%|—)<',lambda m:'>'+('—' if (v:=next(vals)) is None else q(v)+'%')+'<',h)
    if k=='chart-source':h=h.replace('Illustrative fixture, settled sessions, percent.',H_NOTE+' '+U_NOTE)
   st['html']=h
  if macro_board:
   rows=[s for s in b['steps'] if re.fullmatch(r'sector-\d+',s['key'])]
   if len(rows)==10:
    first=min(b['steps'].index(s) for s in rows)
    energy_step=next(s for s in rows if '>Energy<' in s['html'] or '>能源<' in s['html'])
    rows=[s for s in rows if s is not energy_step]+[energy_step]
    b['steps']=[s for s in b['steps'] if not re.fullmatch(r'sector-\d+',s['key'])]
    b['steps'][first:first]=rows
    b['fixture_sort']={'field':'share_above_50d','direction':'descending','missing':'last','entity_order':contract['cohorts']['macro_sector_rows']['sorted_entity_keys'],'step_key_order':[s['key'] for s in rows]}
 # Namespace metadata references advance only for Macro.
 eff=walk_strings(eff,namespace)
 eff['fixture_override']={'version':'f02.fixture.v3','contract':'../fixture-contract.json','contract_sha256':contract_hash,'original_packet':source_name,'original_packet_sha256':sha(raw),'status':'PREPARED_NOT_APPLIED','paper_calls':0,'note':'Full effective source packet. Preserve original applied bytes. Reconcile actual step IDs and fresh-read guards before native edits; do not reapply existing steps.'}
 if dest_name=='supplemental-boards.json':eff['base_packet_sha256']=sha((OUT/'mobile-state-boards.json').read_bytes())
 if dest_name=='fault-composition-inputs.json':
  eff['unchanged_core_packet']={'path':'repairs/fixture-coherence-v1/effective/core-supplement-inputs.json','sha256':sha((OUT/'core-supplement-inputs.json').read_bytes()),'meaning':'Core packet separately versioned; not applied by the fault packet.'}
 for oldb,newb in zip(base.get('boards',[])+base.get('append_to_existing',[]),eff.get('boards',[])+eff.get('append_to_existing',[])):
  bk=oldb.get('key',oldb.get('target_board_key')); oldmap={s['key']:s for s in oldb['steps']}
  assert set(oldmap)=={s['key'] for s in newb['steps']},bk
  for s in newb['steps']:
   old=oldmap[s['key']]
   if old!=s:changes.append({'packet':dest_name,'board_key':bk,'step_key':s['key'],'original_html_sha256':sha(old['html'].encode()),'effective_html_sha256':sha(s['html'].encode()),'effective_html':s['html']})
  if bk in ['company-eps-overlay-320','company-dividend-overlay-320','options-full-row-evidence-320']:
   assert oldb==newb,'Unrelated applied board must remain byte-equivalent as parsed: '+bk
 digest=dump(OUT/dest_name,eff)
 inventory.append({'original_packet':source_name,'original_sha256':sha(raw),'effective_packet':str((OUT/dest_name).relative_to(HERE)),'effective_sha256':digest,'boards':len(eff.get('boards',[])),'changed_steps':sum(c['packet']==dest_name for c in changes)})

for p,h in source_before.items():assert sha(Path(p).read_bytes())==h,'Original changed: '+p
dump(HERE/'step-overrides.json',{'schema':'f02.fixture-step-overrides.v1','status':'PREPARED_NOT_APPLIED','overrides':changes})
dump(HERE/'packet-manifest.json',{'schema':'f02.fixture-effective-packets.v1','status':'PREPARED_NOT_APPLIED','fixture_contract_sha256':contract_hash,'packets':inventory,'originals_unchanged':True,'company_and_options_original_subtrees_unchanged':True,'native_effects':0})
print(json.dumps({'packets':inventory,'changed_steps':len(changes),'contract_sha256':contract_hash,'originals_unchanged':True},indent=2))
