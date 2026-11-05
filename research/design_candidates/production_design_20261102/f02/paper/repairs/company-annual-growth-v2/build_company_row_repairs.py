#!/usr/bin/env python3
"""Versioned Company row repair inputs; no Paper/browser calls or frozen edits."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import hashlib, importlib.util, json, re, xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]
F02=PAPER.parent
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
native=module('existing_native_parser',PAPER/'repairs/build_numeric_alignment_native_patch.py')
consumer=module('existing_consumer_inputs',PAPER/'consumer-inputs/build_consumer_inputs.py')
FIXTURE=json.loads((F02/'fixtures/company-history.json').read_text())
SOURCE=json.loads((PAPER/'consumer-inputs/consumer-boards.json').read_text())
PROGRESS=json.loads((PAPER/'native-progress.json').read_text())
NUMERIC=json.loads((PAPER/'repairs/numeric-alignment-source-input-override.json').read_text())
FILE='01M312VSDSZFVT45674GDVJVZN'
VERSION='F02-company-annual-growth-repair/2.0.0'
WIDTHS=[250,125,125,125,125,125,165,128]
PERIODS=FIXTURE['statement_periods']
def sha(v):return hashlib.sha256(v if isinstance(v,bytes)else v.encode()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def d(s):return Decimal(str(s).rstrip('%')) if s is not None else None
def signed(n,places=1):
 q=n.quantize(Decimal('1').scaleb(-places),rounding=ROUND_HALF_UP)
 return ('+' if q>0 else '−' if q<0 else '')+format(abs(q),f'.{places}f')
SERIES={x['en']:x for x in FIXTURE['series']}
PERIOD_INDEX={yr:i for i,yr in enumerate(FIXTURE['periods'])}
def series_value(name,year):
 return Decimal(str(SERIES[name]['values'][PERIOD_INDEX[year]]))
def margin_raw(year):
 income=series_value('Operating income',year);revenue=series_value('Revenue',year)
 return income/revenue*100,{'operating_income_usd_bn':str(income),'revenue_usd_bn':str(revenue)}
def changes(row):
 out=[]
 for j,period in enumerate(PERIODS):
  current=d(row[j+2]);prior=None if j==0 else d(row[j+1]);prior_period=None if j==0 else PERIODS[j-1]
  baseline_source='adjacent displayed statement value'if j else'not supplied'
  raw_sources=None
  if row[0]=='Operating margin':
   current,current_inputs=margin_raw(period);prior,prior_inputs=margin_raw(period-1);prior_period=period-1
   baseline_source='explicit consistent-definition operating income / revenue series'
   raw_sources={'current':current_inputs,'prior':prior_inputs}
  elif j==0 and row[0]in SERIES:
   prior=series_value(row[0],period-1);prior_period=period-1
   assert current==series_value(row[0],period),'Statement and history do not agree'
   baseline_source='FY2021 value in the existing17-year matching series'
  if j==0 and prior is None:
   label='Prior unavailable';kind='prior_not_supplied';amount=None;unit=None
  elif current is None or prior is None:
   label='Unavailable';kind='missing_current_or_prior';amount=None;unit=None
  elif row[0]=='Operating margin':
   amount=current-prior;unit='pp';label=signed(amount)+' pp';kind='absolute_percentage_points_from_raw_ratios'
  elif row[0]=='Dividend per share':
   amount=current-prior;unit='USD/share';label=signed(amount,2)+' USD/share';kind='absolute_currency_per_share'
  elif prior==0:
   label='Unavailable';kind='zero_relative_baseline';amount=None;unit=None
  else:
   amount=(current/prior-1)*100;unit='percent';label=signed(amount)+'%';kind='relative_percent'
  out.append({'period':period,'prior_period':prior_period,'raw_value':row[j+2],'raw_prior':str(prior)if prior is not None else None,'raw_current_for_formula':str(current)if current is not None else None,'change_label':label,'change_type':kind,'unrounded_change':str(amount)if amount is not None else None,'change_unit':unit,'comparator':baseline_source,'raw_ratio_inputs':raw_sources})
 return out

def frame(name,inner,style):return f'<div layer-name="{escape(name,quote=True)}" style="display:flex;flex-shrink:0;box-sizing:border-box;{style}">{inner}</div>'
def text(s,p,size=13,role='ink',weight=400,line=20):
 return f'<div style="font-family:Inter;font-size:{size}px;line-height:{line}px;font-weight:{weight};color:{p[role]};font-variant-numeric:tabular-nums;font-feature-settings:\'tnum\';white-space:nowrap;width:max-content;flex-shrink:0;">{escape(str(s))}</div>'
def row_html(row,i,theme,audit):
 p=consumer.palette(theme)
 label='Diluted earnings per share' if row[0]=='Diluted EPS' else row[0]
 unit='%' if row[8]=='percent'else row[8]
 first=frame(label,text(label,p,13,'ink',600 if i==0 else 400)+text(unit,p,12,'secondary',400,18),'flex-direction:column;justify-content:center;gap:2px;width:250px;padding:0 10px;')
 cells=''
 for a in audit:
  value='—' if a['raw_value']is None else a['raw_value']
  change=a['change_label'];role='up'if change.startswith('+')else'down'if change.startswith('−')else'secondary'
  cells+=frame(f'{label} / FY {a["period"]} / value and annual change',text(value,p,13,'muted'if value=='—'else'ink')+text(change,p,12,role,400,18),'flex-direction:column;align-items:flex-end;justify-content:center;gap:2px;width:125px;padding:0 10px;text-align:right;')
 delta=row[7]if row[7]is not None else'Unavailable'
 role='up'if delta.startswith('+')else'down'if delta.startswith('−')else'muted'if delta=='Unavailable'else'ink'
 cells+=frame('Latest change / FY 2026 versus FY 2025',text(delta,p,13,role),'flex-direction:column;align-items:flex-end;justify-content:center;width:165px;padding:0 10px;text-align:right;')
 cells+=frame(f'Evidence / {label}',text('Evidence',p,13,'link'),'flex-direction:column;align-items:flex-start;justify-content:center;width:128px;height:44px;padding:0 10px;')
 return frame('Statement / '+row[0]+' / annual changes',first+cells,'flex-direction:row;align-items:center;width:1168px;height:52px;background-color:'+p['panel']+';border-bottom:1px solid '+p['line']+';')

def main():
 sources={b['key']:b for b in SOURCE['boards']};actual={b['key']:b for b in PROGRESS['boards']}
 n_overrides={(x['board_key'],x['step_key']):x for x in NUMERIC['overrides']}
 prior_overrides={(x['board_key'],x['step_key']):x for x in json.loads((PAPER/'repairs/company-annual-growth-v1/company-source-overrides.v1.json').read_text())['overrides']}
 frozen=[PAPER/'consumer-inputs/consumer-boards.json',F02/'fixtures/company-history.json',PAPER/'reviews/product-native-first-pass.md',PAPER/'reviews/taste-native-first-pass.md']
 frozen += [PAPER/'consumer-inputs'/f'company-{theme}.json'for theme in ['dark','light']]
 frozen += [PAPER/'exports'/f'company-{theme}.jsx'for theme in ['dark','light']]
 hashes={str(p):sha(p.read_bytes())for p in frozen}
 ops=[];overrides=[];boardinfo=[];audit=[]
 for i,row in enumerate(FIXTURE['rows']):audit.append({'metric':row[0],'unit':row[8],'values':changes(row)})
 for theme in ['dark','light']:
  key='company-'+theme;b=actual[key];source_steps={s['key']:s for s in sources[key]['steps']}
  export_path=PAPER/'exports'/f'{key}.jsx';export=export_path.read_text();root,index=native.parse_jsx(export)
  assert root['attrs']['id']==b['id'] and b['pageId']=='p-6-0'
  header=index[b['steps']['statement-header']]
  assert [c['style']['width']for c in header['children']]==[str(w)+'px'for w in WIDTHS]
  for i,row in enumerate(FIXTURE['rows']):
   sk=f'statement-row-{i+1}';old_id=b['steps'][sk];old=index[old_id];src=source_steps[sk];source_row=native.Parser(src['html']).roots[0]
   assert old['parent_id']==b['steps']['main']
   assert len(old['children'])==8 and [c['style']['width']for c in old['children']]==[str(w)+'px'for w in WIDTHS]
   assert native.all_text(old)==native.all_text(source_row),(key,sk,'frozen export/source text mismatch')
   html=row_html(row,i,theme,audit[i]['values']);new=ET.fromstring(html)
   assert len(new)==8 and [re.search(r'width:(\d+)px',c.attrib['style']).group(1)for c in new]==list(map(str,WIDTHS))
   for j,cell in enumerate(list(new)[1:6]):
    assert 'align-items:flex-end' in cell.attrib['style'] and 'flex-direction:column' in cell.attrib['style']
    assert list(cell)[0].text==('—'if row[j+2]is None else row[j+2])
    assert list(cell)[1].text==audit[i]['values'][j]['change_label']
   assert 'font-size:12px' in list(list(new)[0])[1].attrib['style']
   old_desc=[n['attrs']['id']for n in native.walk(old)if'id'in n['attrs']]
   old_numeric=[c['attrs']['id']for c in old['children'][1:7]]
   override={'board_key':key,'step_key':sk,'original_source_html_sha256':sha(src['html']),'accepted_before_overlay_html_sha256':list(dict.fromkeys([sha(src['html']),n_overrides[(key,sk)]['replacement_html_sha256'],prior_overrides[(key,sk)]['replacement_html_sha256']])),'replacement_html_sha256':sha(html),'replacement_html':html,'repair_version':VERSION}
   overrides.append(override)
   ops.append({'board_key':key,'board_id':b['id'],'page_id':b['pageId'],'step_key':sk,'operation':'replace_owned_row_subtree','target_row_id':old_id,'expected_parent_id':old['parent_id'],'expected_old_row_text':native.all_text(old),'expected_cell_widths':WIDTHS,'source_export':str(export_path),'source_export_sha256':sha(export),'source_step_html_sha256':sha(src['html']),'html':html,'html_sha256':sha(html),'old_descendant_ids_invalid_after_success':old_desc,'old_numeric_frame_ids_invalid_after_success':old_numeric,'new_root_id':None,'new_cell_ids':None,'cell_binding_intent':[{'column':j+1,'period':PERIODS[j],'field':row[0],'value':row[j+2],'change':audit[i]['values'][j]['change_label']}for j in range(5)],'guard':'Writer must re-read this actual owned row and match entity/metric/raw values, parent and widths. Existing style-only alignment may differ from frozen export and is already built into replacement. Stop if identity/data/row root changed.'})
  boardinfo.append({'board_key':key,'board_id':b['id'],'main_id':b['steps']['main'],'header_id':b['steps']['statement-header'],'history_chart_id':b['steps']['history-chart'],'preserve_history':True,'row_count':9,'old_row_height':46,'new_row_height':52,'row_stack_height_increase':54,'fit_instruction':'Keep artboard/main flow at fit-content; inspect the full footer after the 54px increase. Do not scale the chart or shrink the new row text.'})
 assert len(ops)==len(overrides)==18
 assert audit[6]['values'][3]['change_label']=='+72.5%'
 assert audit[6]['values'][4]['change_label']=='Unavailable'
 assert [x['values'][0]['change_label']for x in audit]==['+33.3%','+30.4%','+25.0%','−1.1 pp','+26.7%','+33.3%','Prior unavailable','Prior unavailable','Prior unavailable']
 assert all(x['change_label']=='0.00 USD/share'for x in audit[7]['values'][1:])
 assert [x['change_label']for x in audit[3]['values'][1:]]==['+0.8 pp','+2.5 pp','+3.3 pp','+1.2 pp']
 for a,row in zip(audit,FIXTURE['rows']):
  if row[7]is not None:assert a['values'][-1]['change_label']==row[7],(row[0],a['values'][-1]['change_label'],row[7])
 for p,h in hashes.items():assert sha(Path(p).read_bytes())==h
 result={'schema':'f02.paper.company-annual-growth-row-repair.v2','version':VERSION,'status':'PREPARED_NOT_APPLIED','supersedes':'company-annual-growth-v1; v1 remains preserved and was confirmed unapplied by the sole writer','target_file_id':FILE,'scope':'Eighteen existing Company row roots only; no chart/history/source fixture mutation. Preserve all five raw annual values and latest-change column.','boards':boardinfo,'operations':ops,'arithmetic_policy':{'normal':'(current/prior - 1) × 100; one decimal, ROUND_HALF_UP','operating_margin':'current and prior raw operating-income/revenue ratios ×100, then subtract; pp, one decimal','dividend':'current minus prior; absolute USD/share, two decimals; relative growth from zero remains undefined','fy2022':'Use supplied FY2021 matching series for Revenue/Gross profit/Operating income/Pretax income/Net income and raw income/revenue ratios for margin. Only EPS/dividend/FCF lack supplied FY2021 priors.','missing':'Unavailable when current or comparator is missing; raw missing remains an em dash'},'stale_patch_notice':'After any row replacement, that row’s old numeric frame IDs and descendant IDs are stale. Do not replay the original Company BODY alignment targets. The unchanged Company header may retain its separately verified alignment repair; Macro and Options patches are unaffected. Bind all replacement IDs from actual Paper returns.','writer_sequence':['Re-read the exact board and target row via the sole authorized writer. Match the local binding against current row identity/values/width/parent.','Replace one complete row visual group at a time in its existing position, preserving original row order. Never append duplicate rows.','Capture actual returned new root/descendant IDs and update step mappings immediately. If a mutation response is unknown, reconcile before any retry.','Verify numeric frame flex-column/end alignment, all five amounts and five changes, 12px units, 52px row, preserved source action.','Read back and capture both full Company boards. Confirm 17×5 history and raw amounts unchanged; inspect footer and header alignment.'], 'frozen_inputs_unchanged_sha256':hashes,'paper_calls':0,'browser_calls':0,'rendered_verified':False}
 dump(HERE/'company-row-replacements.v2.json',result)
 dump(HERE/'company-source-overrides.v2.json',{'schema':'f02.paper.company-annual-growth-source-overrides.v2','version':VERSION,'source_packet':str(PAPER/'consumer-inputs/consumer-boards.json'),'source_packet_sha256':sha((PAPER/'consumer-inputs/consumer-boards.json').read_bytes()),'composition_order':'Apply original hash-guarded numeric style override first if needed, then these complete-row overrides. Do not edit frozen applied inputs. These row replacements include alignment themselves.','overrides':overrides})
 dump(HERE/'company-growth-arithmetic.v2.json',{'schema':'f02.company.annual-change-arithmetic.v2','fixture_sha256':sha((F02/'fixtures/company-history.json').read_bytes()),'periods':PERIODS,'rows':audit})
 dump(HERE/'company-row-validation.v2.json',{'schema':'f02.paper.company-row-repair-validation.v2','status':'PASS_LOCAL_BINDING_ARITHMETIC_HTML_ONLY','rows_per_theme':9,'themes':2,'annual_values_per_theme':45,'annual_change_labels_per_theme':45,'fy2022_prior_unavailable':3,'fy2022_supplied_prior':6,'eps_fy2025_growth':'+72.5%','eps_fy2026':'Unavailable','dividend_zero_change':'0.00 USD/share','unit_font_px':12,'amount_font_px':13,'change_font_px':12,'row_height_px':52,'column_widths':WIDTHS,'row_width_px':sum(WIDTHS),'all_raw_values_preserved':True,'all_histories_untouched':True,'all_actual_row_ids_resolve':True,'frozen_sources_unchanged':True,'native_application':False,'native_render_review':False,'browser_review':False})
 lines=['# Company annual-change row repair v2','','Prepared source inputs only. The two frozen independent reviews identify missing per-year change companions, small units and failed numeric alignment. This packet replaces nine existing row groups per theme while retaining every raw amount, the final change column, and the untouched 17×5 history.','','## Writer instructions','','1. Use `company-row-replacements.v2.json`. Re-read each target row’s actual identity, parent, widths and raw values. Style-only alignment differences are expected if the prior patch was applied.','2. Replace each owned row subtree in place, one visual group per call; bind returned new IDs. Do not append duplicate rows.','3. After replacement, the old Company body numeric-frame IDs are stale. Do not replay them. Header, Macro and Options alignment targets are independent.','4. New rows are 52px (previously46px): allow the board to grow54px in total and inspect its footer. Do not scale typography or chart marks.','5. Capture actual JSX and full boards after both themes; then update native evidence maps. Local arithmetic/HTML checks are not native review.','','## Arithmetic','','FY2022 uses the existing FY2021 history for five matching metrics and raw income/revenue ratios for margin. Only EPS, dividend and free cash flow say “Prior unavailable”. FY2023 onward uses adjacent supplied values; margin always uses the explicit raw ratios. Standard metrics use relative percent; Operating margin uses pp from raw income/revenue ratios; Dividend per share uses absolute USD/share, including explicit zero. FY2026 EPS remains unknown and its change says “Unavailable”. FY2025 EPS is2.07 versus FY2024 1.20, giving+72.5%.','','| Row | Dark target | Light target |','| --- | --- | --- |']
 for i,r in enumerate(FIXTURE['rows']):lines.append('| '+r[0]+' | '+ops[i]['target_row_id']+' | '+ops[9+i]['target_row_id']+' |')
 lines += ['','`company-source-overrides.v2.json` is for later versioned effective packet composition; it accepts the original row hash, prior numeric-alignment source override hash, or the superseded v1 Company row hash. Frozen original packets, exports, reviews and fixture remain unchanged.','']
 (HERE/'WRITER_README.md').write_text('\n'.join(lines).replace('previously46px','previously 46px').replace('grow54px','grow 54px').replace('is2.07','is 2.07').replace('giving+72.5%','giving +72.5%'))
 print(json.dumps({'rows':len(ops),'packet':str(HERE/'company-row-replacements.v2.json'),'sha256':sha((HERE/'company-row-replacements.v2.json').read_bytes()),'override_sha256':sha((HERE/'company-source-overrides.v2.json').read_bytes()),'frozen_unchanged':True},indent=2))

if __name__=='__main__':main()
