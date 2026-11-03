#!/usr/bin/env python3
"""Versioned native companion inputs; no Paper/browser/network operations."""
from pathlib import Path
from decimal import Decimal
from html import escape
import hashlib, importlib.util, json, math, re, xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]
F02=PAPER.parent
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rowrepair=module('company_growth_repair',PAPER/'repairs/company-annual-growth-v2/build_company_row_repairs.py')
consumer=rowrepair.consumer;native=rowrepair.native
FIXTURE=rowrepair.FIXTURE
ORIGINAL=json.loads((PAPER/'consumer-inputs/consumer-boards.json').read_text())
PROGRESS=json.loads((PAPER/'native-progress.json').read_text())
ROWS=json.loads((PAPER/'repairs/company-annual-growth-v2/company-row-replacements.v2.json').read_text())
FILE='01M312VSDSZFVT45674GDVJVZN'
VERSION='F02-consumer-evidence-reading-density-companions/1.0.0'
SOURCE_BOARD={b['key']:b for b in ORIGINAL['boards']}
ACTUAL={b['key']:b for b in PROGRESS['boards']}
ART={s['key']:s for s in SOURCE_BOARD['editorial-dark']['steps']}
def sha(v):return hashlib.sha256(v if isinstance(v,bytes)else v.encode()).hexdigest()
def frame(name,inner='',style='',horizontal=False):return f'<div layer-name="{escape(name,quote=True)}" style="display:flex;flex-direction:{"row"if horizontal else"column"};flex-shrink:0;box-sizing:border-box;{style}">{inner}</div>'
def text(s,p,width,size=13,role='ink',weight=400,line=None,extra=''):
 return f'<div style="font-family:Inter;font-size:{size}px;line-height:{line or round(size*1.5)}px;font-weight:{weight};color:{p[role]};width:{width}px;flex-shrink:0;overflow-wrap:anywhere;{extra}">{escape(str(s))}</div>'
def number(s,p,width,size=14,role='ink',weight=400):return text(s,p,width,size,role,weight,22,'font-variant-numeric:tabular-nums;font-feature-settings:\'tnum\';text-align:right;')
def button(s,p,width,focus=False):
 outline='outline:2px solid '+p['focus']+';outline-offset:2px;'if focus else''
 return frame(s,text(s,p,width-24,13,'ink',500,20,'text-align:center;'),'width:'+str(width)+'px;min-height:44px;padding:10px 12px;justify-content:center;align-items:center;border:1px solid '+p['control-line']+';border-radius:6px;background-color:'+p['panel']+';'+outline)
def link(s,url,p,width):return f'<a layer-name="{escape(s,quote=True)}" href="{escape(url,quote=True)}" style="display:flex;align-items:center;width:{width}px;min-height:44px;font-family:Inter;font-size:14px;line-height:22px;color:{p["link"]};text-decoration:underline;overflow-wrap:anywhere;">{escape(s)}</a>'
def board(key,name,page,width,theme,pad=0,gap=0):
 p=consumer.palette(theme)
 return {'key':key,'name':name,'pageId':page,'width':width,'height':900,'theme':theme,'language':{'body':'en','chrome':'en'},'artboardStyles':{'display':'flex','flexDirection':'column','width':f'{width}px','height':'fit-content','padding':f'{pad}px','gap':f'{gap}px','backgroundColor':p['bg'],'fontFamily':'Inter','color':p['ink']},'steps':[]}
def add(b,key,parent,html,variant,**meta):b['steps'].append({'key':key,'parent':parent,'html':html,'variant':variant,**meta})
def artifact(b,label):
 p=consumer.palette(b['theme']);w=b['width']
 add(b,'artifact','board',frame('Candidate source identity',text(label,p,w-40,10,'secondary',500,15),'width:'+str(w)+'px;padding:9px 20px;background-color:'+p['raised']+';'),'Provenance/versioned-companion')
def dialog_header(b,title):
 p=consumer.palette(b['theme']);w=b['width'];inner=w-40
 add(b,'dialog-header','board',frame('Evidence header / Close starts focus',text(title,p,inner-92,20,'ink',600,28)+button('Close',p,76,True),'width:'+str(w)+'px;min-height:64px;padding:10px 20px;gap:16px;align-items:center;background-color:'+p['panel']+';border-bottom:1px solid '+p['line']+';',True),'EvidenceInspector/close-44')
def labeled(label,value,p,width=350):return frame(label,text(label,p,width,12,'secondary',500,18)+text(value,p,width,13,'ink',400,20),'width:'+str(width)+'px;gap:4px;')
def article_text(key):return native.all_text(native.Parser(ART[key]['html']).roots[0])

def company_historical():
 b=board('company-fy2025-eps-evidence-390','F02 · Company historical EPS evidence & return · 390 · Repair v1','p-5-0',390,'dark');p=consumer.palette('dark')
 artifact(b,'F02 · ILLUSTRATIVE HISTORICAL CELL · REPAIR v1');dialog_header(b,'Company evidence')
 add(b,'body','board',frame('Historical EPS inspector','','width:390px;padding:20px;gap:16px;'),'EvidenceInspector/historical-body')
 add(b,'identity','body',frame('Selected field and period',text('EXM · Example Industries',p,350,17,'ink',600,25)+text('Diluted earnings per share',p,350,22,'ink',600,30)+text('Selected observation: FY 2025 · USD/share',p,350,13,'secondary',500,20),'width:350px;gap:6px;'),'EvidenceInspector/field-period-identity')
 add(b,'selected-value','body',frame('FY 2025 reported value',text('2.07 USD/share',p,350,30,'ink',600,38)+text('+72.5% versus FY 2024',p,350,16,'up',500,24),'width:350px;gap:6px;'),'MetricValue/known-historical-cell')
 add(b,'comparison','body',frame('Exact adjacent annual comparison',labeled('Comparator · FY 2024','1.20 USD/share',p)+text('(2.07 / 1.20 − 1) × 100 = +72.5%',p,350,14,'ink',500,22)+text('Relative change between the two stated fiscal years. Currency and per-share definition are unchanged within this illustrative fixture.',p,350,13,'secondary',400,20),'width:350px;gap:12px;'),'ChangeValue/historical-relative-percent')
 source='f02.fixture.v2/company/EXM/diluted_eps/FY2022-FY2026'
 add(b,'source-identity','body',frame('Exact fixture source scope',labeled('Source identity',source,p)+labeled('Record scope / selected observation','FY 2022–FY 2026 / FY 2025',p)+labeled('Raw field','company-history.json · rows[6][5] = 2.07',p),'width:350px;gap:12px;'),'EvidenceInspector/historical-source-binding')
 add(b,'clocks','body',frame('Fiscal period and document clocks',labeled('Observed period','Fiscal year 2025; no calendar timestamp inferred',p)+labeled('Published','30 Oct 2026 · 20:02 UTC',p)+labeled('Retrieved','30 Oct 2026 · 20:03 UTC',p),'width:350px;gap:12px;'),'FreshnessReceipt/fiscal-period-and-clocks')
 add(b,'limitation','body',frame('Historical evidence caveat',text('FY 2026 remains unavailable.',p,350,15,'ink',600,22)+text('The missing current field does not erase the supplied FY 2025 value. These are illustrative statement inputs, not a real filing or producer receipt.',p,350,13,'secondary',400,20),'width:350px;padding:14px 0;gap:6px;border-top:1px solid '+p['line']+';'),'Callout/historical-known-current-unknown')
 add(b,'return-action','body',button('Return to FY 2025 EPS',p,350),'EvidenceInspector/historical-return',return_binding={'board_keys':['company-dark','company-light'],'step_key':'statement-row-7','column_index':4,'field':'diluted_eps','period':2025,'value':'2.07','new_native_id':None})
 add(b,'return-state-heading','board',frame('Explicit companion return state',text('RETURN STATE · SAME FY 2025 CELL',p,350,11,'secondary',600,17)+text('Diluted EPS · USD/share · FY 2025',p,350,13,'ink',500,20),'width:390px;padding:20px 20px 12px;gap:6px;background-color:'+p['raised']+';'),'EvidenceInspector/returned-cell-context')
 source_op=next(x for x in ROWS['operations']if x['board_key']=='company-dark'and x['step_key']=='statement-row-7')
 cell=ET.fromstring(source_op['html'])[4]
 cell.set('style',cell.attrib['style']+'min-height:52px;background-color:'+p['selected']+';outline:2px solid '+p['focus']+';outline-offset:2px;')
 add(b,'returned-historical-cell','board',frame('Restored historical cell focus',text('FY 2025 selected',p,225,13,'secondary',500)+ET.tostring(cell,encoding='unicode'),'width:390px;padding:0 20px 20px;align-items:center;background-color:'+p['raised']+';',True),'DataRow/historical-cell-return',source_replacement_hash=source_op['html_sha256'])
 add(b,'build-contract','board',frame('Historical inspector source and interaction contract',text('BUILD CONTRACT · NOT A COMPLETED INTERACTION',p,350,10,'secondary',600,15)+text('The source record retains the existing five-year identity; selection adds FY 2025 context without inventing a producer ID. Restore the same field/period cell after closing, by stable identity, and make it visible. The normal row replacement must supply its new native IDs first; old Company descendant IDs are stale.',p,350,12,'secondary',400,18)+text('Modal focus containment, Escape, touch, scroll preservation, real caller/receipt mapping and keyboard activation of a historical cell still need browser and D07 integration proof.',p,350,12,'secondary',400,18),'width:390px;padding:20px;gap:8px;border-top:1px solid '+p['line']+';'),'Build/historical-evidence-boundary')
 b['fixture_binding']={'entity':'EXM','field':'diluted_eps','source_identity':source,'selected_period':2025,'selected_value':'2.07','selected_unit':'USD/share','prior_period':2024,'prior_value':'1.20','relative_change_percent':'72.5','source_json_path':'rows[6][5]','comparison_json_path':'rows[6][4]','record_identity_unchanged':True,'return_native_binding':'Resolve the current statement-row-7 replacement root and FY2025 cell; no old descendant may be reused.'}
 return b

def calc_row(period,ret,balance,p,width=350,height=44):
 widths=[92,120,138];values=[period,ret,balance];inside=''
 for i,(value,w)in enumerate(zip(values,widths)):
  role='up'if ret=='+50%'and i==1 else'down'if ret=='−50%'and i==1 else'secondary'if ret=='Not applicable'and i==1 else'ink'
  content=text(value,p,w-16,14,role,400,22,'font-variant-numeric:tabular-nums;white-space:nowrap;text-align:'+('left'if i==0 else'right')+';'+('display:flex;flex-direction:column;align-items:flex-end;'if i in [1,2]else''))
  inside+=frame(value,content,f'width:{w}px;padding:0 8px;align-items:'+('flex-start;'if i==0 else'flex-end;')+'justify-content:center;')
 return frame(period,inside,f'width:{width}px;height:{height}px;align-items:center;background-color:'+p['panel']+';border-bottom:1px solid '+p['line']+';',True)
def calc_header(p):
 out=''
 for i,(value,w)in enumerate(zip(['Period','Return','Balance · USD'],[92,120,138])):
  out+=frame(value,text(value,p,w-16,12,'secondary',600,18,'text-align:'+('left'if i==0 else'right')+';'+('display:flex;flex-direction:column;align-items:flex-end;'if i in [1,2]else'')),f'width:{w}px;padding:0 8px;align-items:'+('flex-start;'if i==0 else'flex-end;'))
 return frame('Calculation column headers',out,'width:350px;height:40px;align-items:center;background-color:'+p['raised']+';',True)

def editorial_evidence():
 b=board('editorial-calculation-evidence-390','F02 · Editorial calculation evidence & return · 390 · Repair v1','p-5-0',390,'light');p=consumer.palette('light')
 artifact(b,'F02 · ILLUSTRATIVE CALCULATION EVIDENCE · v1');dialog_header(b,'Calculation evidence')
 add(b,'body','board',frame('Public calculation inspector','','width:390px;padding:20px;gap:16px;'),'EvidenceInspector/editorial-body')
 add(b,'identity','body',frame('Calculation identity',text('Compound-growth example',p,350,22,'ink',600,30)+text('Two annual periods · USD balances · no cash flows',p,350,13,'secondary',500,20),'width:350px;gap:6px;'),'EvidenceInspector/editorial-identity')
 add(b,'calculation-header','body',frame('Contiguous calculation table',calc_header(p),'width:350px;gap:0px;'),'TableFrame/calculation-header')
 for i,(period,ret,balance)in enumerate([('Start','Not applicable','10,000'),('Year 1','+50%','15,000'),('Year 2','−50%','7,500')]):add(b,'calculation-row-'+str(i),'calculation-header',calc_row(period,ret,balance,p),'DataRow/calculation-'+str(i))
 add(b,'total-return','body',frame('Exact total-return arithmetic',text('Total return · two years',p,350,15,'ink',600,22)+text('(7,500 / 10,000) − 1 = −25%',p,350,17,'ink',500,25),'width:350px;gap:6px;'),'MetricValue/total-return')
 add(b,'annualized-return','body',frame('Exact compound annual arithmetic',text('Compound annual return',p,350,15,'ink',600,22)+text('(7,500 / 10,000)^(1/2) − 1',p,350,16,'ink',500,24)+text('≈ −13.4% per year',p,350,19,'ink',600,27),'width:350px;gap:6px;'),'MetricValue/annualized-return')
 source='f02.fixture.v2/editorial/compound_growth/two_annual_periods'
 add(b,'source-and-dates','body',frame('Source and article calendar dates',labeled('Source identity',source,p)+labeled('Published','2026-07-20',p)+labeled('Example updated','2026-10-30',p)+text('These dates describe the document, not a live market observation.',p,350,12,'secondary',400,19),'width:350px;gap:12px;'),'EvidenceInspector/editorial-source-dates')
 add(b,'assumptions','body',frame('Calculation assumptions',text('What the example assumes',p,350,16,'ink',600,24)+text('No deposits, withdrawals, fees or taxes. Returns apply to changing balances. The arithmetic average is 0%; it is a different measure from total or compound annual return. This calculation is not a forecast.',p,350,13,'secondary',400,20),'width:350px;padding:14px 0;gap:8px;border-top:1px solid '+p['line']+';'),'Callout/calculation-limits')
 add(b,'return-action','body',button('Return to the calculation',p,350),'EvidenceInspector/editorial-return')
 add(b,'return-context','board',frame('Returned public calculation trigger',text('RETURN STATE · FOLLOW THE CALCULATION',p,350,11,'secondary',600,17)+button('Inspect the calculation →',p,350,True),'width:390px;padding:20px;gap:10px;background-color:'+p['raised']+';'),'EvidenceTrigger/editorial-restored-context')
 add(b,'build-contract','board',frame('Public evidence implementation boundary',text('BUILD CONTRACT · PUBLIC READING CONTEXT',p,350,10,'secondary',600,15)+text('Keep the article route, #arithmetic anchor and scroll. Close/Escape restores its calculation trigger; the public reading surface keeps its own shell. Modal trap, inert background, accessible name and actual focus return remain browser requirements.',p,350,12,'secondary',400,18),'width:390px;padding:20px;gap:8px;'),'Build/editorial-evidence')
 targets=[]
 for key in ['editorial-dark','editorial-light']:
  exp=PAPER/'exports'/f'{key}.jsx';_,index=native.parse_jsx(exp.read_text());node=ACTUAL[key]['steps']['calculation-evidence'];assert native.all_text(index[node])=='Inspect the calculation →'
  targets.append({'board_key':key,'board_id':ACTUAL[key]['id'],'step_key':'calculation-evidence','observed_node_id':node,'source_export_sha256':sha(exp.read_bytes()),'status':'Frozen observed return-target reference; writer/browser must resolve current target before use.'})
 b['fixture_binding']={'source_identity':source,'source_function':'pattern-lab.html evidenceRecord(article)','balances_usd':[10000,15000,7500],'returns_percent':[50,-50],'total_return_percent':-25,'annualized_return_percent':(math.sqrt(.75)-1)*100,'publication':'2026-07-20','example_updated':'2026-10-30','anchor':'#arithmetic','existing_return_targets':targets,'new_mobile_return_target':{'board_key':'editorial-reading-390','step_key':'calculation-evidence','native_id':None}}
 return b

def editorial_reading():
 b=board('editorial-reading-390','F02 · Public editorial reading · 390 · Repair v1','p-5-0',390,'light');p=consumer.palette('light')
 artifact(b,'F02 · PUBLIC READING · 390 · CANDIDATE REPAIR v1')
 add(b,'public-header','board',frame('Public masthead',text('MASTERMIND',p,230,12,'ink',700,18,'letter-spacing:0.1em;')+text('EN / 中文',p,100,12,'secondary',500,18,'text-align:right;'),'width:390px;height:56px;padding:0 20px;gap:20px;align-items:center;background-color:'+p['rail']+';border-bottom:1px solid '+p['line']+';',True),'SectionHeader/public-masthead')
 nav=''.join(frame(x,text(x,p,100,13,'ink',500,20,'text-align:center;'),'width:110px;height:44px;align-items:center;justify-content:center;')for x in ['Research','Tools','Learn'])
 add(b,'public-navigation','board',frame('Existing public navigation labels',nav,'width:390px;padding:4px 20px;gap:10px;align-items:center;background-color:'+p['rail']+';',True),'Action/public-navigation')
 add(b,'main','board',frame('Narrow English reading surface','','width:390px;padding:24px 20px;gap:18px;'),'Editorial/390-reading-column')
 add(b,'article-title','main',frame('Article title and dek',text('FROM THE DESK',p,350,11,'accent',600,17)+text('Compound Growth for Traders',p,350,30,'ink',700,36)+text('Read the calculation, compare the measures, and keep the assumptions in view.',p,350,16,'secondary',400,25),'width:350px;gap:10px;'),'SectionHeader/narrow-article')
 add(b,'publication','main',frame('Article publication dates',text('Published 2026-07-20',p,350,12,'secondary',400,18)+text('Example updated 2026-10-30',p,350,12,'secondary',400,18)+text('Illustrative article excerpt · English body',p,350,12,'muted',400,18),'width:350px;gap:4px;'),'FreshnessReceipt/document-dates')
 add(b,'toc','main',frame('Visible narrow table of contents',text('ON THIS PAGE',p,350,11,'secondary',600,17),'width:350px;gap:0px;'),'Editorial/narrow-toc-container')
 for i,(label,anchor)in enumerate([('Follow the calculation','#arithmetic'),('Compare the averages','#difference'),('Where this example stops','#limits'),('Explore the assumptions','#next')]):add(b,'toc-'+str(i),'toc',link(label,anchor,p,350),'Action/editorial-anchor',destination=anchor)
 add(b,'lede','main',text(article_text('lede'),p,350,18,'ink',400,28),'Editorial/lede')
 for prefix,headingkey,copykey,anchor in [('calculation','calculation-heading','calculation-copy','arithmetic'),('averages','averages-heading','averages-copy','difference')]:
  add(b,prefix+'-heading','main',frame('Article heading '+anchor,text(article_text(headingkey),p,350,22,'ink',600,30),'width:350px;padding:8px 0 0;'),'SectionHeader/editorial-'+prefix,anchor_id=anchor)
  add(b,prefix+'-copy','main',text(article_text(copykey),p,350,16,'secondary',400,26),'Editorial/'+prefix+'-paragraph')
  if prefix=='calculation':
   add(b,'calculation-table','main',frame('Three-column calculation table',text('Illustrative calculation · currency USD',p,350,12,'secondary',400,18),'width:350px;gap:0px;'),'TableFrame/editorial-calculation-container')
   add(b,'calculation-header','calculation-table',calc_header(p),'TableFrame/editorial-calculation-header')
   for i,(period,ret,balance)in enumerate([('Start','Not applicable','10,000'),('Year 1','+50%','15,000'),('Year 2','−50%','7,500')]):add(b,'calculation-row-'+str(i),'calculation-table',calc_row(period,ret,balance,p),'DataRow/editorial-calculation-'+str(i))
   add(b,'calculation-evidence','main',button('Inspect the calculation →',p,350),'EvidenceTrigger/editorial-390',evidence_key='article',companion_board_key='editorial-calculation-evidence-390')
 add(b,'equations','main',frame('Exact return formulas',text('Total return',p,318,13,'ink',600,20)+text('(7,500 / 10,000) − 1 = −25%.',p,318,14,'ink',400,22)+text('CAGR',p,318,13,'ink',600,20)+text('(7,500 / 10,000)^(1/2) − 1 ≈ −13.4% per year.',p,318,14,'ink',400,22),'width:350px;padding:16px;gap:6px;background-color:'+p['raised']+';border-radius:8px;'),'MetricValue/editorial-equations')
 for prefix,headingkey,copykey,anchor in [('limits','limits-heading','limits-copy','limits'),('next','next-heading','next-copy','next')]:
  add(b,prefix+'-heading','main',frame('Article heading '+anchor,text(article_text(headingkey),p,350,22,'ink',600,30),'width:350px;padding:8px 0 0;'),'SectionHeader/editorial-'+prefix,anchor_id=anchor)
  add(b,prefix+'-copy','main',text(article_text(copykey),p,350,16,'secondary',400,26),'Editorial/'+prefix+'-paragraph')
 urls=SOURCE_BOARD['editorial-dark']['continuation_urls']
 add(b,'continuation-links','main',frame('Existing public continuation destinations',''.join(link(label,url,p,350)for label,url in zip(['CAGR calculator ↗','Compounding calculator ↗','Back to the desk ↗'],urls)),'width:350px;padding:12px 0 0;border-top:1px solid '+p['line']+';'),'Action/public-continuation',urls=urls)
 add(b,'build-contract','board',frame('Narrow reading implementation boundary',text('BUILD CONTRACT · NATIVE READING COMPOSITION',p,350,10,'secondary',600,15)+text('The existing English body, calculation, publication dates and continuation URLs remain. The TOC uses the supporting specimen’s #arithmetic, #difference, #limits and #next anchors. This is a candidate composition; bind the actual emitted article’s canonical route and original heading slugs through its public owner.',p,350,12,'secondary',400,18)+text('No investor rail. Public navigation destinations remain with seo_base.html.j2. Actual 390px/400% browser reflow, anchors, link behavior, focus and CJK chrome still need their own receipt.',p,350,12,'secondary',400,18),'width:390px;padding:20px;gap:8px;background-color:'+p['raised']+';'),'Build/public-reading-boundary')
 b['source_binding']={'source_consumer_board':'editorial-dark','body_copy_keys':['lede','calculation-copy','averages-copy','limits-copy','next-copy'],'source_body_unchanged':True,'source_anchors':['arithmetic','difference','limits','next'],'continuation_urls':urls,'canonical_route':'Existing public article owner; not invented by this companion','density':'Comfortable reading:16px/26 body,18px/28 lede,22px/30 sections,30px/36 title','column_width':350}
 return b

def density():
 b=board('density-40-52-comparison','F02 · Dense40 / Comfortable52 · Same three rows · Repair v1','p-4-0',1440,'dark',48,24);p=consumer.palette('dark')
 add(b,'artifact-header','board',frame('Density comparison provenance',text('F02 · ILLUSTRATIVE DENSITY COMPARISON · REPAIR v1',p,1344,11,'secondary',600,17)+text('Change spacing. Keep the data and the tasks.',p,1344,28,'ink',600,36)+text('The same three Company metrics, periods, units, changes and evidence actions appear in both modes. Font sizes and precision stay the same.',p,1344,14,'secondary',400,22),'width:1344px;gap:8px;'),'Density/same-data-comparison')
 add(b,'comparison','board',frame('Two density modes','','width:1344px;gap:32px;align-items:flex-start;',True),'Density/comparison-container')
 sample=[FIXTURE['rows'][i]for i in [2,4,5]]
 widths=[200,100,100,100,124]
 for mode,h in [('dense',40),('comfortable',52)]:
  add(b,mode,'comparison',frame(mode.title()+' table','','width:656px;padding:16px;gap:0px;background-color:'+p['panel']+';'),'TableFrame/'+mode+'-container')
  add(b,mode+'-heading',mode,frame(mode.title()+' context',text(mode.title()+f' · {h}px rows',p,624,21,'ink',600,29)+text('EXM · Annual income metrics · USD bn',p,624,12,'secondary',500,18)+text('FY 2025 / FY 2026 · 3 same rows · source 30 Oct 2026',p,624,12,'secondary',400,18),'width:624px;padding:0 0 16px;gap:6px;'),'Density/'+mode+'-label')
  header=''
  for i,(label,w)in enumerate(zip(['Metric','FY 2025','FY 2026','Change','Source'],widths)):
   header+=frame(label,text(label,p,w-16,12,'secondary',600,18,'text-align:'+('right'if i in [1,2,3]else'left')+';'+('display:flex;flex-direction:column;align-items:flex-end;'if i in [1,2,3]else'')),f'width:{w}px;padding:0 8px;align-items:'+('flex-end;'if i in [1,2,3]else'flex-start;'))
  add(b,mode+'-header',mode,frame(mode+' headers',header,'width:624px;height:40px;align-items:center;background-color:'+p['raised']+';',True),'TableFrame/'+mode+'-headers')
  for n,a in enumerate(sample):
   vals=[a[0],a[5],a[6],a[7],'Evidence'];inner=''
   for i,(val,w)in enumerate(zip(vals,widths)):
    role='link'if i==4 else'up'if i==3 else'ink'
    cell=text(val,p,w-16,13,role,400,20,'font-variant-numeric:tabular-nums;white-space:nowrap;text-align:'+('right'if i in [1,2,3]else'left')+';'+('display:flex;flex-direction:column;align-items:flex-end;'if i in [1,2,3]else''))
    inner+=frame(val,cell,f'width:{w}px;padding:0 8px;align-items:'+('flex-end;'if i in [1,2,3]else'flex-start;')+'justify-content:center;'+('height:'+str(32 if mode=='dense'else 44)+'px;'if i==4 else''))
   add(b,mode+'-row-'+str(n+1),mode,frame(mode+' / '+a[0],inner,f'width:624px;height:{h}px;align-items:center;border-bottom:1px solid '+p['line']+';background-color:'+p['selected'if n==1 else'panel']+';',True),'DataRow/'+mode,field_values=vals,row_height=h)
 add(b,'build-contract','board',frame('Density implementation boundary',text('BUILD CONTRACT · REAL NATIVE SPACING, NOT AN EXECUTED TOGGLE',p,1344,11,'secondary',600,17)+text('Each dense row is 40px; each comfortable row is 52px. Both keep the same 13px values, 12px headers/units, column widths, source actions and selected Pretax-income row. Only row/desktop hit-area spacing changes. Important phone controls retain the separate 44px policy.',p,1344,13,'secondary',400,21)+text('The host density preference and persistence remain source-owned. Apply the actual row token without removing fields, changes or evidence; browser switching, touch, focus and export scope remain unverified.',p,1344,13,'secondary',400,21),'width:1344px;padding:16px 0 0;gap:8px;border-top:1px solid '+p['line']+';'),'Build/density-boundary')
 b['density_binding']={'same_fixture_rows':[2,4,5],'column_widths':widths,'font_sizes':{'value':13,'header':12,'unit':12},'row_heights':{'dense':40,'comfortable':52},'selected_metric':'Pretax income','same_data':True}
 return b

def main():
 originals=[PAPER/'consumer-inputs/consumer-boards.json',F02/'fixtures/company-history.json',PAPER/'reviews/product-native-first-pass.md',PAPER/'reviews/taste-native-first-pass.md',PAPER/'repairs/company-annual-growth-v2/company-row-replacements.v2.json']
 hashes={str(p):sha(p.read_bytes())for p in originals}
 boards=[company_historical(),editorial_evidence(),editorial_reading(),density()]
 checks=[]
 for b in boards:
  seen={'board'}
  for s in b['steps']:
   assert s['parent']in seen and s['key']not in seen,(b['key'],s['key']);seen.add(s['key'])
   ET.fromstring(s['html'])
   assert not re.search(r'<table|display\s*:\s*grid|(?:^|;)\s*margin(?:-|:)',s['html'])
  checks.append({'board':b['key'],'steps':len(b['steps']),'sequential_parents':True,'valid_single_root_html':True,'fit_content':True})
 assert (Decimal('2.07')/Decimal('1.20')-1)*100==Decimal('72.5')
 assert 10000*1.5*.5==7500 and (7500/10000-1)*100==-25
 density_board=boards[3];ss={s['key']:s for s in density_board['steps']}
 for i in [1,2,3]:
  assert ss['dense-row-'+str(i)]['field_values']==ss['comfortable-row-'+str(i)]['field_values']
  assert ss['dense-row-'+str(i)]['row_height']==40 and ss['comfortable-row-'+str(i)]['row_height']==52
 ed=boards[2];edsteps={s['key']:s for s in ed['steps']}
 for key in ed['source_binding']['body_copy_keys']:
  assert ''.join(ET.fromstring(edsteps[key]['html']).itertext())==article_text(key)
 # A fixed-width text wrapper needs its own end alignment: Paper may create an
 # intrinsic-width native Text child inside it. Text alignment alone is not proof.
 def style(e):return dict(x.split(':',1)for x in e.attrib.get('style','').split(';')if ':'in x)
 numeric_pairs=0;row_width_checks=0
 def check_numeric_row(root,columns,expected_width):
  nonlocal numeric_pairs,row_width_checks
  assert sum(int(style(e)['width'][:-2])for e in root)==expected_width
  assert style(root)['width']==str(expected_width)+'px';row_width_checks+=1
  for column in columns:
   cell=root[column];wrapper=cell[0]
   for e in [cell,wrapper]:
    css=style(e)
    assert css['display']=='flex'and css['flex-direction']=='column'and css['align-items']=='flex-end'
   assert style(wrapper)['text-align']=='right';numeric_pairs+=1
 for b in boards[1:3]:
  steps={s['key']:s for s in b['steps']}
  header=ET.fromstring(steps['calculation-header']['html'])
  if b['key']=='editorial-calculation-evidence-390':header=header[0]
  check_numeric_row(header,[1,2],350)
  for i in range(3):check_numeric_row(ET.fromstring(steps['calculation-row-'+str(i)]['html']),[1,2],350)
 for mode in ['dense','comfortable']:
  check_numeric_row(ET.fromstring(ss[mode+'-header']['html']),[1,2,3],624)
  for i in range(1,4):check_numeric_row(ET.fromstring(ss[mode+'-row-'+str(i)]['html']),[1,2,3],624)
 assert numeric_pairs==40 and row_width_checks==16
 for p,h in hashes.items():assert sha(Path(p).read_bytes())==h
 packet={'schema':'f02.paper.consumer-companions.v1','version':VERSION,'status':'PREPARED_NOT_APPLIED','target_file_id':FILE,'boards':boards,'append_to_existing':[],'source_hashes':hashes,'dependent_row_patch':{'path':'../company-annual-growth-v2/company-row-replacements.v2.json','sha256':hashes[str(PAPER/'repairs/company-annual-growth-v2/company-row-replacements.v2.json')],'return_binding':'Historical FY2025 cell resolves through the newly replaced Company row; old descendants must not be used.'},'native_ids':'New boards/steps intentionally unbound; existing editorial return IDs are frozen observations only.','paper_calls':0,'browser_calls':0}
 out=HERE/'consumer-companion-inputs.v1.json';out.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
 validation={'schema':'f02.paper.consumer-companion-validation.v1','status':'PASS_LOCAL_SOURCE_ARITHMETIC_HTML_ONLY','boards':checks,'historical_eps_change_percent':'72.5','calculation':{'balances':[10000,15000,7500],'total_percent':-25,'cagr_percent_unrounded':(math.sqrt(.75)-1)*100,'cagr_display_percent':-13.4},'editorial_body_paragraphs_preserved':5,'density_same_rows':3,'numeric_frame_and_child_wrapper_end_alignment_pairs':numeric_pairs,'fixed_width_row_sums_checked':row_width_checks,'originals_unchanged':True,'source_hashes':hashes,'native_applied':False,'native_fit_reviewed':False,'browser_verified':False,'limits':['Actual import/editability/geometry and all new native IDs require the sole writer.','Historical-cell and article focus/scroll return are proposed behavior, not browser proof.','No real Company filing, article publication pipeline or source/mutation authority is qualified.']}
 (HERE/'consumer-companion-validation.v1.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 notes=['# Consumer evidence, reading and density companions v1','','Source-only prepared inputs. Apply through the sole writer; new IDs are unbound. Frozen consumer inputs, fixtures, reviews and Company row repair v2 remain unchanged.','','| Board key | Page / width | Groups |','| --- | --- | --- |']
 notes += ['| '+b['key']+' | '+b['pageId']+' / '+str(b['width'])+' | '+str(len(b['steps']))+' |'for b in boards]
 notes += ['','## Writer instructions','','- Create each new owned board as fit-content, then apply each meaningful group in order. Use the actual returned parent IDs; no inferred IDs.','- Company historical return depends on the new `statement-row-7` replacement and its FY2025 cell (column index4). Resolve the returned new cell ID; do not reuse the old Company descendant. The original five-year source record stays unchanged; FY2025 is explicit selected observation context.','- The editorial inspector records frozen observed wide triggers `6MH-0` and `6O7-0`; read current targets before binding. Its new390px trigger comes from `editorial-reading-390/calculation-evidence` and needs the returned ID.','- The390px reading board preserves the English body, calculation, source calendar dates, four specimen anchors and existing continuation URLs. It has public navigation and no investor rail.','- Density comparison physically uses40px and52px rows on the same three financial rows, with the same 13px data, 12px unit/header text and columns. It does not claim a tested density toggle.','- Numeric cell frames AND their fixed-width text wrappers use flex column/end alignment, guarding the actual native max-content text issue found in frozen review. Local validation checks 40 such pairs and 16 complete column-width sums; native export/visual inspection still must verify the resulting alignment.','- Capture/inspect historical selected-cell return, calculation source/assumptions, mobile table/TOC/formula/continuation fit, and both density tables. Browser/ARIA/focus/scroll and real source integration remain separate.','']
 (HERE/'WRITER_README.md').write_text('\n'.join(notes).replace('index4','index 4').replace('new390px','new 390px').replace('The390px','The 390px').replace('uses40px','uses 40px').replace('and52px','and 52px').replace('same 13px','same 13px').replace(', 12px',', 12px'))
 print(json.dumps({'packet':str(out),'sha256':sha(out.read_bytes()),'boards':checks},indent=2))

if __name__=='__main__':main()
