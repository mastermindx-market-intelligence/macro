#!/usr/bin/env python3
"""F02 local role evidence map and bounded native construction supplements.

No Paper/browser/network operations. Prepared inputs remain distinct from actual
native IDs, screenshot proof, executable behavior and authority review.
"""
from pathlib import Path
from html import escape
import hashlib,json,re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FILE='01M312VSDSZFVT45674GDVJVZN'
D={'bg':'var(--noir-canvas)','panel':'var(--noir-panel)','raised':'var(--noir-raised)','selected':'var(--noir-selected)','ink':'var(--noir-text-primary)','secondary':'var(--noir-text-secondary)','muted':'var(--noir-text-tertiary)','accent':'var(--noir-champagne)','line':'#343434','control':'#6f6f6f','up':'#b0d4b9','focus':'#c4d9f4'}
L={'bg':'#f6f6f3','panel':'#ffffff','raised':'#f0f0ed','selected':'#e2e2dc','ink':'#1a1c20','secondary':'#51555b','muted':'#5f6368','accent':'#66543b','line':'#cbccc7','control':'#85877f','up':'#256341','focus':'#245c91'}
ICON_SOURCE='https://github.com/mastermindx-market-intelligence/macro/blob/b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e/templates/_icons.html.j2'
ICON_BLOB='0ada914d14ffca25498ed186d681d1a7b7f82697'
# Paths copied verbatim from the inspected, pinned existing Macro icon owner.
ICON_PATHS={
 'search':'<circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.4" y1="15.4" x2="21" y2="21"/>',
 'arrow_up':'<line x1="12" y1="19.5" x2="12" y2="5"/><polyline points="6,11 12,5 18,11"/>',
 'swirl':'<path d="M20.4 12a8.4 8.4 0 1 0-8.4 8.4 4.6 4.6 0 0 0 4.6-4.6"/><polyline points="17.1,8.9 20.4,12 23,8.7"/>',
}

def frame(name,inner='',style='',direction='column'):
 return f'<div layer-name="{escape(name,quote=True)}" style="display:flex;flex-direction:{direction};flex-shrink:0;{style}">{inner}</div>'
def row(name,inner='',style=''):return frame(name,inner,style,'row')
def txt(s,p=D,size=13,role='ink',weight=400,style='',line=None):
 return frame(s,escape(s),f'font-family:Inter;font-size:{size}px;line-height:{line or round(size*1.5)}px;font-weight:{weight};color:{p[role]};{style}')
def svg(name,p=D,size=24,role='ink'):
 return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:{p[role]};" xmlns="http://www.w3.org/2000/svg">{ICON_PATHS[name]}</svg>'
def action(label,p=D,kind='secondary',width=204,icon=None,focus=False,disabled=False):
 bg=p['ink'] if kind=='primary' else p['panel'] if kind=='secondary' else 'transparent'
 color=p['bg'] if kind=='primary' else p['ink']
 if disabled:color=p['muted'];bg=p['raised']
 border=f'1px solid {p["control"]}' if kind=='secondary' else '0px solid transparent'
 glyph=svg(icon,{**p,'ink':color},20) if icon else ''
 style=f'width:{width}px;height:44px;align-items:center;justify-content:center;gap:10px;padding:0 14px;background-color:{bg};border:{border};border-radius:6px;'
 if focus:style+=f'outline:2px solid {p["focus"]};outline-offset:3px;'
 return row(label,glyph+txt(label,{**p,'ink':color},13,'ink',600 if kind=='primary' else 500),style)
def step(key,parent,html,variant,**extra):return {'key':key,'parent':parent,'html':html,'variant':variant,**extra}
def heading(title,copy):return frame(title,txt(title,size=21,weight=600,line=30)+txt(copy,role='secondary',style='width:1296px;',line=21),'width:1344px;gap:8px;')

def core_supplement():
 icons=[];controls=[]
 icons.append(step('core-icon-heading','board',heading('Use the existing icon anatomy.','24 × 24 viewBox · 1.8 stroke · currentColor · named controls. These are the existing search, arrow_up and swirl paths, not new brand assets.'),'Icon/anatomy'))
 for key,name,label,description in [
  ('evidence','search','Inspect source','Evidence action: visible text names the action; the implementation accessible name also identifies its row.'),
  ('recovery','swirl','Retry refresh','Recovery action: a read retry belongs to the existing source owner. This mark never implies save confirmation.'),
 ]:
  pair=''
  for theme,p in [('Dark',D),('Light',L)]:
   pair+=frame(f'{theme} {key}',txt(theme,p,11,'muted',600)+action(label,p,width=220,icon=name,focus=key=='recovery')+txt(description,p,12,'secondary',style='width:596px;',line=19),'width:656px;padding:20px;gap:12px;background-color:'+p['bg']+';')
  icons.append(step('core-icon-'+key,'board',row(key+' theme pair',pair,'width:1344px;gap:32px;align-items:flex-start;'),'Icon/'+key,checkpoint_after=True))
 directions=''
 for theme,p in [('Dark',D),('Light',L)]:
  valid=row('Known direction',svg('arrow_up',p,24,'up')+txt('Increase · +1.13 pp',p,17,'up',600),'align-items:center;gap:12px;height:44px;')
  unknown=row('Unknown direction',frame('Reserved 24px icon slot','','width:24px;height:24px;')+txt('— Change unavailable',p,17,'ink',500),'align-items:center;gap:12px;height:44px;')
  directions+=frame(theme+' direction',txt(theme,p,11,'muted',600)+valid+unknown+txt('Noninteractive marker. Sign, unit and wording carry meaning; unknown has no invented arrow or trend.',p,12,'secondary',style='width:596px;',line=19),'width:656px;padding:20px;gap:8px;background-color:'+p['bg']+';')
 icons.append(step('core-icon-direction','board',row('Direction and absence',directions,'width:1344px;gap:32px;'),'Icon/direction',checkpoint_after=True))
 sizes=''
 for size in [16,20,24]:
  sizes+=frame(str(size)+'px optical sample',txt(f'{size}px rendered mark',size=12,role='secondary')+row('44px labeled target',frame('44px icon target',svg('search',D,size),'width:44px;height:44px;align-items:center;justify-content:center;')+txt('Inspect source',size=13),'align-items:center;gap:8px;')+txt('Same 24-unit path; inspect at actual scale.',size=12,role='muted'),'width:432px;gap:8px;')
 icons.append(step('core-icon-sizes','board',row('Optical sizes with labeled hitboxes',sizes,'width:1344px;gap:24px;'),'Icon/16-20-24-and-44-target'))
 icons.append(step('core-icon-reuse-contract','board',frame('Icon source and accessibility contract',txt('REUSE THE ACTUAL SOURCE OWNER',size=12,role='accent',weight=600)+txt('Macro: templates/_icons.html.j2 → icon(search), icon(arrow_up), icon(swirl). Existing Terminal inline SVG ownership remains separate.',size=13,role='secondary')+txt('In the browser, decorative SVG is aria-hidden and not focusable; the named control owns its accessible label. Preserve currentColor and stroke, then qualify optical size, forced colors and real focus behavior. Paper does not prove those semantics.',size=13,role='secondary',style='width:1296px;',line=21),'width:1344px;padding:20px 24px;gap:8px;background-color:'+D['panel']+';'),'Icon/source-contract'))

 controls.append(step('core-action-heading','board',heading('Give each action a clear priority.','Primary confirms the domain action; secondary inspects or supports; quiet opens optional detail. A visual hierarchy does not grant write permission.'),'Action/hierarchy'))
 for theme,p in [('dark',D),('light',L)]:
  groups=''
  for kind,label,copy in [('primary','Save view','Primary · D23/current owner confirms the write.'),('secondary','Inspect source','Secondary · read evidence without a mutation.'),('quiet','More details','Quiet · optional disclosure; no silent save.')]:
   groups+=frame(kind+' action',txt(kind.title(),p,12,'secondary',600)+action(label,p,kind,220)+txt(copy,p,12,'secondary',style='width:400px;',line=19),'width:416px;gap:12px;')
  controls.append(step('core-action-hierarchy-'+theme,'board',row(theme+' action hierarchy',groups,'width:1344px;padding:20px;gap:24px;background-color:'+p['bg']+';'),'Action/'+theme+'-primary-secondary-quiet',checkpoint_after=True))
 controls.append(step('core-action-disabled','board',row('Pending primary with reading available',action('Saving…',D,'primary',220,disabled=True)+action('Inspect source',D,'secondary',220)+txt('Pending disables repeat submission. Read and evidence actions remain available. A disabled appearance is not a server lock.',size=13,role='secondary',style='width:816px;',line=21),'width:1344px;align-items:center;gap:24px;padding:16px 0;'),'Action/pending-primary'))

 controls.append(step('core-disclosure-heading','board',heading('Disclose the method without hiding the answer.','The comparison and its coverage remain outside this optional region. Collapsed, expanded and failed-detail states keep the same explicit summary.'),'DetailDisclosure/states'))
 def summary(p,width,state):
  label='Show method +' if state=='collapsed' else 'Hide method −'
  return row('Method disclosure summary / '+state,txt('How participation is calculated',p,16,'ink',600,style=f'width:{width-180}px;')+txt(label,p,13,'secondary',500,style='width:180px;text-align:right;'),f'width:{width}px;min-height:44px;align-items:center;')
 controls.append(step('core-disclosure-collapsed','board',frame('Collapsed method disclosure',summary(D,1296,'collapsed'),'width:1344px;padding:12px 24px;border-top:1px solid '+D['line']+';border-bottom:1px solid '+D['line']+';'),'DetailDisclosure/collapsed-desktop'))
 controls.append(step('core-disclosure-expanded','board',frame('Expanded method disclosure','','width:1344px;padding:20px 24px;gap:12px;border-top:1px solid '+D['line']+';border-bottom:1px solid '+D['line']+';'),'DetailDisclosure/expanded-container'))
 controls.append(step('core-disclosure-expanded-summary','core-disclosure-expanded',summary(D,1296,'expanded'),'DetailDisclosure/expanded-summary'))
 controls.append(step('core-disclosure-expanded-body','core-disclosure-expanded',txt('Illustrative method: count covered securities with a valid close above their valid 50-day average. Divide by the covered securities with both observations. Show eligible-population coverage separately; missing securities are not classified as below average.',size=14,role='secondary',style='width:1296px;',line=22),'DetailDisclosure/expanded-body',checkpoint_after=True))
 controls.append(step('core-disclosure-error','board',frame('Failed method detail retains summary','','width:1344px;padding:20px 24px;gap:12px;background-color:'+D['panel']+';'),'DetailDisclosure/error-container'))
 controls.append(step('core-disclosure-error-summary','core-disclosure-error',summary(D,1296,'expanded'),'DetailDisclosure/error-summary'))
 controls.append(step('core-disclosure-error-copy','core-disclosure-error',frame('Detail error',txt('Method details could not be loaded.',size=16,weight=600)+txt('The comparison remains visible with its original source and coverage. No method has been inferred. Retry only this existing read; do not resend a save.',size=14,role='secondary',style='width:1296px;',line=22),'width:1296px;gap:6px;'),'DetailDisclosure/error-copy'))
 controls.append(step('core-disclosure-error-action','core-disclosure-error',action('Retry details',D,'secondary',180,icon='swirl'),'DetailDisclosure/error-recovery',checkpoint_after=True))
 controls.append(step('core-disclosure-mobile','board',frame('320px disclosure companion','','width:320px;padding:16px;gap:12px;background-color:'+L['bg']+';'),'DetailDisclosure/mobile-container'))
 controls.append(step('core-disclosure-mobile-label','core-disclosure-mobile',txt('320px / optional method / three states',L,12,'muted',600,style='width:288px;'),'DetailDisclosure/mobile-label'))
 def mobile_summary(state):
  return row('Mobile summary / '+state,txt('How participation is calculated',L,14,'ink',600,style='width:208px;',line=20)+txt('Show +' if state=='collapsed' else 'Hide −',L,12,'secondary',500,style='width:64px;text-align:right;'), 'width:288px;min-height:56px;align-items:center;gap:16px;')
 controls.append(step('core-disclosure-mobile-collapsed','core-disclosure-mobile',frame('Mobile collapsed',txt('COLLAPSED',L,10,'muted',600)+mobile_summary('collapsed'),'width:288px;padding:12px 0;border-bottom:1px solid '+L['line']+';gap:4px;'),'DetailDisclosure/collapsed-320'))
 controls.append(step('core-disclosure-mobile-expanded','core-disclosure-mobile',frame('Mobile expanded','','width:288px;padding:12px 0;border-bottom:1px solid '+L['line']+';gap:8px;'),'DetailDisclosure/expanded-320-container'))
 controls.append(step('core-disclosure-mobile-expanded-summary','core-disclosure-mobile-expanded',frame('Mobile expanded header',txt('EXPANDED',L,10,'muted',600)+mobile_summary('expanded'),'width:288px;gap:4px;'),'DetailDisclosure/expanded-320-summary'))
 controls.append(step('core-disclosure-mobile-expanded-body','core-disclosure-mobile-expanded',txt('Count covered securities above their valid 50-day average. Divide by those with both observations. Show coverage separately; missing is not below average.',L,14,'secondary',style='width:288px;',line=22),'DetailDisclosure/expanded-320-body'))
 controls.append(step('core-disclosure-mobile-error','core-disclosure-mobile',frame('Mobile detail error','','width:288px;padding:12px 0;gap:8px;'),'DetailDisclosure/error-320-container'))
 controls.append(step('core-disclosure-mobile-error-summary','core-disclosure-mobile-error',frame('Mobile error header',txt('DETAIL ERROR',L,10,'muted',600)+mobile_summary('expanded'),'width:288px;gap:4px;'),'DetailDisclosure/error-320-summary'))
 controls.append(step('core-disclosure-mobile-error-copy','core-disclosure-mobile-error',txt('Method unavailable. The comparison keeps its dated source and coverage; no method is inferred.',L,14,'secondary',style='width:288px;',line=22),'DetailDisclosure/error-320-copy'))
 controls.append(step('core-disclosure-mobile-error-action','core-disclosure-mobile-error',action('Retry details',L,'secondary',288,icon='swirl'),'DetailDisclosure/error-320-recovery',checkpoint_after=True))
 controls.append(step('core-disclosure-contract','board',frame('Disclosure behavior and source boundary',txt('BROWSER CONTRACT · NOT AN EXECUTED INPUT TEST',size=12,role='accent',weight=600)+txt('One native disclosure summary controls one identified region. Enter / Space or touch toggles it; aria-expanded and panel identity stay synchronized. Keep focus on the summary, preserve URL/sort/scroll, and never save on open or close. Important controls remain at least 44px.',size=13,role='secondary',style='width:1296px;',line=21)+txt('This is a shared failure treatment, not a new method endpoint. The host owner supplies any existing detail read/retry callback. Source: existing MX/Detail Disclosure references 2GG-0 / 2LX-0 and SOURCE_AND_DATA_CONTRACT.md §5; real browser behavior and host wiring remain unverified.',size=13,role='secondary',style='width:1296px;',line=21),'width:1344px;padding:20px 24px;gap:8px;background-color:'+D['panel']+';'),'DetailDisclosure/source-contract'))
 return {'schema':'f02.paper.core-role-supplement.v1','status':'PREPARED_NOT_APPLIED','file_id':FILE,'system_version':'F02-SYSTEM/1.0.0-candidate.2','source_icon':{'url':ICON_SOURCE,'blob_sha':ICON_BLOB,'names':['search','arrow_up','swirl'],'path_bytes_reused':True,'stroke':1.8,'viewBox':'0 0 24 24','color':'currentColor'},'append_to_existing':[{'target_board_key':'foundations','target_packet':'foundation-inputs/boards.json','steps':icons},{'target_board_key':'controls','target_packet':'foundation-inputs/boards.json','steps':controls}],'paper_calls':0,'browser_calls':0,'native_id_binding':'Parent resolves actual board and step IDs before application. No native IDs asserted.'}

TERMINAL_PIN='b79b1e136290978ff7675087de979bb1b42b3713'
TERMINAL_BASE='https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/'+TERMINAL_PIN+'/terminal/'

def portable_gaps(core):
 metrics=[]
 metrics.append(step('core-metric-exceptions-heading','board',heading('Keep the unit and the clock honest.','These are portable formatting and missing-clock states. They do not change the observed data or timestamps on any consumer board.'),'MetricValue/portable-exceptions'))
 pair=''
 for theme,p in [('Dark',D),('Light',L)]:
  pair+=frame(theme+' basis-point comparison',txt('BASIS-POINT EXPRESSION · SAME COMPARISON',p,11,'muted',600)+txt('+113 bps',p,32,'up',600,line=40)+txt('65.57% → 66.70%',p,16,'ink',500)+txt('+1.13 percentage points × 100 = +113 basis points. This is a unit conversion of the illustrative comparison, not a new published statistic.',p,13,'secondary',style='width:608px;',line=21),'width:656px;padding:24px;gap:10px;background-color:'+p['bg']+';')
 metrics.append(step('core-metric-bps','board',row('Explicit basis points in both themes',pair,'width:1344px;gap:32px;'),'ChangeValue/bps',checkpoint_after=True))
 pair=''
 for theme,p in [('Dark',D),('Light',L)]:
  pair+=frame(theme+' unknown source age',txt('MISSING-CLOCK STATE FIXTURE',p,11,'muted',600)+txt('Participation · 66.70%',p,24,'ink',600,line=32)+txt('Source age unavailable.',p,16,'ink',600)+txt('Source observation time was not supplied. Publication time was not supplied.',p,13,'secondary',style='width:608px;',line=21)+txt('Retrieved 30 Oct 2026 · 20:03 UTC',p,13,'secondary')+txt('A completed retrieval cannot establish freshness. Keep the unknown source clock visible beside the value.',p,13,'secondary',style='width:608px;',line=21),'width:656px;padding:24px;gap:10px;background-color:'+p['bg']+';')
 metrics.append(step('core-metric-unknown-age','board',row('Unknown age in both themes',pair,'width:1344px;gap:32px;'),'FreshnessReceipt/unknown-source-age',checkpoint_after=True))
 core['append_to_existing'].append({'target_board_key':'metrics','target_packet':'foundation-inputs/boards.json','steps':metrics})

 controls=next(g['steps'] for g in core['append_to_existing'] if g['target_board_key']=='controls')
 controls.append(step('core-tier-heading','board',heading('Keep the Options access result specific.','Pinned source: /options renders its access gate before the live workspace. A denial and an unavailable entitlement check require different messages and actions.'),'TierGate/resource-specific'))
 controls.append(step('core-tier-denied-row','board',row('Options denied / theme pair','','width:1344px;gap:32px;align-items:flex-start;'),'TierGate/denied-pair'))
 for theme,p in [('dark',D),('light',L)]:
  parent='core-tier-denied-'+theme
  controls.append(step(parent,'core-tier-denied-row',frame('Options denied / '+theme,'','width:656px;padding:24px;gap:16px;background-color:'+p['panel']+';border:1px solid '+p['line']+';border-radius:8px;'),'TierGate/denied-'+theme+'-container'))
  copy=txt('OPTIONS · ACCESS REQUIRED',p,11,'muted',600)+txt('Unlock the Options desk',p,24,'ink',600,line=32)+txt('Live options flow, chains, exposure (GEX) and unusual activity. Access requires an Essential or Pro plan — sign up to start the free 7-day trial.',p,14,'secondary',style='width:606px;',line=22)
  features=frame('Existing resource description',''.join(txt(x,p,13,'ink') for x in ['Live order-flow tape','Option chains & greeks','Gamma exposure (GEX)','Unusual & sweep detection']),'width:606px;gap:6px;')
  controls.append(step(parent+'-copy',parent,frame('Existing Options gate copy',copy+features,'width:606px;gap:12px;'),'TierGate/denied-'+theme+'-resource-and-requirement'))
  controls.append(step(parent+'-action',parent,frame('Existing onboarding entry',action('Start 7-day free trial',p,'primary',606)+txt('Essential & Pro · cancel anytime',p,12,'secondary'),'width:606px;gap:10px;'),'TierGate/denied-'+theme+'-existing-action',source_callback="onboarding.open('signup', { plan: 'essential' })",checkpoint_after=True))
 controls.append(step('core-tier-unavailable-row','board',row('Options entitlement unavailable / theme pair','','width:1344px;gap:32px;align-items:flex-start;'),'TierGate/unavailable-pair'))
 for theme,p in [('dark',D),('light',L)]:
  parent='core-tier-unavailable-'+theme
  copy=txt('OPTIONS · ACCESS CHECK UNAVAILABLE',p,11,'muted',600)+txt('Options is temporarily unavailable',p,22,'ink',600,line=30)+txt("We couldn't verify Options access right now. This does not mean your subscription changed. Please retry.",p,14,'secondary',style='width:606px;',line=22)
  controls.append(step(parent,'core-tier-unavailable-row',frame('Existing Options outage copy / '+theme,copy,'width:656px;padding:24px;gap:12px;background-color:'+p['panel']+';border:1px solid '+p['line']+';border-radius:8px;'),'TierGate/unavailable-'+theme+'-resource'))
  controls.append(step(parent+'-actions',parent,row('Existing read recovery and route',action('Try again',p,'primary',220)+action('Go to chart',p,'quiet',220),'width:606px;gap:16px;'),'TierGate/unavailable-'+theme+'-existing-actions',source_callbacks=['window.location.reload()','href=/terminal'],checkpoint_after=True))
 controls.append(step('core-tier-contract','board',frame('Pinned Options resource and access owner',txt('SOURCE BINDING · NOT AN ACCESS TEST OR CURRENT OFFER VERIFICATION',size=12,role='accent',weight=600)+txt('Source pin b79b1e1: getLiveOptionsAccess returns allowed / denied / unavailable. Denied → OptionsPaywall; unavailable → OptionsServiceUnavailable; only allowed mounts OptionsWorkspaceMount. No tape, zero-result count or paid payload is shown in either gate.',size=13,role='secondary',style='width:1296px;',line=21)+txt('Actual authority: optionsReadAccess requires terminal_live_options or the exact existing unlimited exception. A paid-plan label alone never grants access. Existing paywall copy and onboarding callback are reused as pinned references; the billing owner must verify the offer before release. Outage retry reloads the current route; the existing chart link is /terminal.',size=13,role='secondary',style='width:1296px;',line=21)+txt('This resource boundary does not revoke public evidence on unrelated routes. The generic public-read state specimen is a different host policy. Host auth return context, payload omission and callback effects remain unverified.',size=13,role='secondary',style='width:1296px;',line=21),'width:1344px;padding:20px 24px;gap:8px;background-color:'+D['panel']+';'),'TierGate/source-contract'))
 core['source_access']={'pin':TERMINAL_PIN,'route':'/options','resource':'Live Options','results':{'allowed':'OptionsWorkspaceMount','denied':'OptionsPaywall','unavailable':'OptionsServiceUnavailable'},'authority':'optionsReadAccess: terminal_live_options feature or exact existing unlimited exception','source_urls':[TERMINAL_BASE+x for x in ['app/(shell)/options/page.tsx','components/OptionsPaywall.tsx','components/OptionsServiceUnavailable.tsx','lib/entitlement.ts','lib/optionsAccess.ts','lib/i18n.tsx']],'copy_scope':'Exact relevant English paywall and unavailable copy at the pinned revision; no claim that trial terms are currently valid. Host owner must verify at release.'}
 controls_group=next(g for g in core['append_to_existing'] if g['target_board_key']=='controls')
 core['append_to_existing'].remove(controls_group)
 variant_header=frame('Core control variants provenance and heading',txt('F02 · CANDIDATE 2 · EDITABLE ROLE VARIANTS',size=11,role='secondary',weight=600)+txt('Actions, disclosures and access',size=28,weight=600,line=36)+txt('Companion to the existing controls board. These source-bound examples preserve the real host owners; native geometry and behavior require their own review.',size=14,role='secondary',style='width:1296px;',line=22),'width:1344px;gap:8px;')
 variants={'key':'controls-variants','name':'F02 · Actions, disclosure & access variants · Candidate 2','pageId':'p-4-0','width':1440,'height':900,'theme':'dark','language':'en','artboardStyles':{'display':'flex','flexDirection':'column','width':'1440px','height':'fit-content','padding':'48px','gap':'24px','backgroundColor':D['bg'],'fontFamily':'Inter','color':D['ink']},'steps':[step('artifact-header','board',variant_header,'Controls/provenance-and-directory')]+controls_group['steps'],'construction_note':'Create a separate fit-content companion artboard. No parent step depends on the original controls board. Original controls receives only its separately prepared hover comparison.'}
 core['boards']=[variants,options_phone()]
 return core

def options_phone():
 p=L
 b={'key':'options-full-row-evidence-320','name':'F02 · Options print-01 evidence · 320 · Candidate 2','pageId':'p-5-0','width':320,'height':1520,'theme':'light','language':'en','artboardStyles':{'display':'flex','flexDirection':'column','backgroundColor':p['bg'],'overflow':'hidden'},'steps':[]}
 ss=b['steps']
 def add(k,parent,html,v,**kw):ss.append(step(k,parent,html,v,**kw))
 add('artifact','board',frame('F02 Options evidence provenance',txt('F02 · CANDIDATE 2 · ILLUSTRATIVE',p,10,'secondary',500,line=15),'width:320px;padding:9px 16px;background-color:'+p['raised']+';'),'EvidenceInspector/provenance')
 add('dialog-header','board',row('Print evidence / close receives initial focus',txt('Print evidence',p,18,'ink',600,style='width:196px;',line=26)+action('Close',p,'secondary',76,focus=True),'width:320px;height:64px;padding:0 16px;gap:16px;background-color:'+p['panel']+';border-bottom:1px solid '+p['line']+';'),'EvidenceInspector/close-44',return_target='options-0')
 add('body','board',frame('Full Options row','','width:320px;padding:20px 16px;gap:18px;'),'EvidenceInspector/320-body')
 add('entity','body',frame('Exact print identity',txt('EXM · print-01',p,22,'ink',600,line=30)+txt('Observed option print',p,13,'secondary')+txt('Illustrative source · same first tape row',p,12,'muted'),'width:288px;gap:6px;'),'EvidenceInspector/identity')
 def field_group(name,fields):
  lines=''
  for label,value in fields:
   lines+=row(label,txt(label,p,12,'secondary',500,style='width:96px;',line=19)+txt(value,p,13,'ink',500,style='width:176px;overflow-wrap:anywhere;',line=20),'width:288px;min-height:36px;align-items:center;gap:16px;border-bottom:1px solid '+p['line']+';')
  return frame(name,lines,'width:288px;')
 add('contract-fields','body',field_group('Contract identity',[('Instrument','EXM'),('Expiry','2026-11-20'),('Type','Call'),('Strike','120.00 USD')]),'EvidenceInspector/full-row-contract-fields')
 add('print-fields','body',field_group('Observed print fields',[('Time · ET','15:58:42'),('Est. side','≈ Buy'),('Premium','825,000 USD'),('Contracts','1,500')]),'EvidenceInspector/full-row-print-fields')
 add('context-fields','body',field_group('Classification and flags',[('DTE','21 calendar days'),('Moneyness','ITM'),('Flags','Sweep')]),'EvidenceInspector/full-row-context-fields')
 identity='f02.fixture.v2/options/EXM/2026-11-20/Call/120.00/2026-10-30/print-01'
 add('source-identity','body',frame('Source field expanded',txt('Source · illustrative fixture',p,12,'secondary',600)+txt(identity,p,13,'ink',style='width:288px;overflow-wrap:anywhere;word-break:break-all;',line=20),'width:288px;gap:6px;'),'EvidenceInspector/full-row-source-field')
 clocks=frame('Print observation clock',txt('Observed print',p,12,'secondary',500)+txt('30 Oct 2026 · 15:58:42 ET',p,13,'ink')+txt('America/New_York',p,12,'muted'),'width:288px;gap:2px;')
 clocks+=frame('Fixture cohort observation window',txt('Twelve-print observation window',p,12,'secondary',500)+txt('30 Oct 2026 · 15:47:31–15:58:42 ET',p,13,'ink',style='width:288px;'),'width:288px;gap:2px;')
 clocks+=frame('Publication and retrieval separately',txt('Published · 30 Oct 2026, 20:02 UTC',p,13,'ink')+txt('Retrieved · 30 Oct 2026, 20:03 UTC',p,13,'ink'),'width:288px;gap:4px;')
 add('clocks','body',frame('Three clocks plus distinct cohort window',clocks,'width:288px;gap:12px;'),'EvidenceInspector/observation-publication-retrieval')
 add('limitation','body',frame('Interpretation and clock limits',txt('Estimated side is not intent.',p,14,'ink',600,line=21)+txt('≈ Buy does not identify opening or closing intent, a price forecast or signed exposure.',p,13,'secondary',style='width:288px;',line=20)+txt('Expiry describes the contract. The observed time and cohort window describe prints; they are not expiry clocks or a market-wide total.',p,13,'secondary',style='width:288px;',line=20),'width:288px;gap:6px;'),'EvidenceInspector/critical-limitation')
 add('return-action','body',action('Return to EXM · print-01',p,'secondary',288),'EvidenceInspector/return-44',return_target='options-0',checkpoint_after=True)
 add('build-contract','board',frame('Options evidence implementation boundary',txt('BUILD CONTRACT · OUTSIDE THE PRODUCT',p,10,'muted',600,line=15)+txt('Modal: close starts focus; trap Tab, allow Escape, make the background inert and keep scrolling inside this inspector. Restore the visible options-0 evidence trigger by stable print identity. If filtered away, use the named tape heading fallback.',p,12,'secondary',style='width:288px;',line=18)+txt('All 12 tape fields are preserved. Source key and row match the candidate-2 fixture; no live API, access check, focus test or completed browser path is claimed.',p,12,'secondary',style='width:288px;',line=18),'width:320px;padding:16px;gap:8px;background-color:'+p['raised']+';'),'EvidenceInspector/integration-contract')
 b['fixture_binding']={'source_file':'../../pattern-lab.html','source_function':'optionRows[0] and evidenceRecord(options-0)','consumer_board_keys':['options-dark','options-light'],'consumer_step_key':'print-01','row_key':'options-0','print_id':'print-01','source_identity':identity,'field_count':12,'field_values':{'Instrument':'EXM','Time · ET':'15:58:42','Expiry':'2026-11-20','Type':'Call','Strike · USD':'120.00','Est. side':'≈ Buy','Premium · USD':'825000','Contracts':'1500','DTE':'21','Moneyness':'ITM','Flags':'Sweep','Source':identity},'observation_date':'2026-10-30','cohort_window':'15:47:31–15:58:42 America/New_York','publication':'2026-10-30T20:02:00Z','retrieval':'2026-10-30T20:03:00Z'}
 return b

def main():
 core=portable_gaps(core_supplement())
 for group in core['append_to_existing']+core.get('boards',[]):
  keys={'board'}
  for s in group['steps']:
   assert s['parent'] in keys,(group.get('target_board_key',group.get('key')),s['key'],s['parent'])
   assert s['key'] not in keys;keys.add(s['key'])
   assert '<table' not in s['html'] and 'display:grid' not in s['html']
 (HERE/'core-supplement-inputs.json').write_text(json.dumps(core,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'core_groups':[{ 'board':g['target_board_key'],'steps':len(g['steps'])}for g in core['append_to_existing']],'boards':[{ 'board':g['key'],'steps':len(g['steps'])}for g in core['boards']]},indent=2))

if __name__=='__main__':main()
