#!/usr/bin/env python3
"""F02 native Paper construction input; does not contact or mutate Paper."""
import ast
import hashlib
import json
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = (ROOT / 'pattern-lab.html').read_text()
FIXTURE = json.loads((ROOT / 'fixtures/company-history.json').read_text())
MACRO = ast.literal_eval(re.search(r'const macroRows\s*=\s*(\[.*?\]);', SOURCE, re.S).group(1).replace('null', 'None'))
PALETTES = {}
for theme, prefix in [('dark', ':root'), ('light', 'html[data-theme=light]')]:
    css = re.search(re.escape(prefix) + r'\{([^}]+)', SOURCE).group(1)
    PALETTES[theme] = dict(re.findall(r'--([\w-]+):([^;]+)', css))
DARK_VARS = {'bg':'canvas','rail':'sidebar','panel':'panel','raised':'raised','selected':'selected','ink':'text-primary','secondary':'text-secondary','muted':'text-tertiary','accent':'champagne'}
for k,v in DARK_VARS.items():
    PALETTES['dark'][k] = 'var(--noir-' + v + ')'

def attr(s):
    return escape(str(s), quote=True)

def text(s, size=13, color='ink', weight=400, theme='dark', line=None, style='', lang='en'):
    c = PALETTES[theme].get(color,color)
    font = 'Noto Sans SC' if lang == 'zh' else 'Inter'
    return '<div style="font-family: '+font+';font-size: '+str(size)+'px;line-height: '+str(line or round(size*1.45))+'px;font-weight: '+str(weight)+';color: '+c+';'+style+'">'+escape(str(s))+'</div>'

def frame(name, inner='', style=''):
    return '<div layer-name="'+attr(name)+'" style="display: flex;flex-direction: column;flex-shrink: 0;'+style+'">'+inner+'</div>'

def row(name, inner='', style=''):
    return frame(name, inner, 'flex-direction: row;align-items: center;'+style)

def button(label, theme='dark', width=120, height=44, disabled=False, focus=False, lang='en', selected=False):
    p=PALETTES[theme]
    outline='outline: 2px solid '+p['focus']+';outline-offset: 2px;' if focus else ''
    return row(label+' control',text(label,12,'muted' if disabled else 'ink',500,theme,line=18,lang=lang),
        'justify-content: center;width: '+str(width)+'px;height: '+str(height)+'px;border: 1px solid '+p['control-line']+';border-radius: 6px;background-color: '+p['selected' if selected else 'panel']+';'+outline)

def board(key,name,page,width,height,theme,language='en'):
    return {'key':key,'name':name,'pageId':page,'width':width,'height':height,'theme':theme,'language':language,
      'artboardStyles':{'display':'flex','flexDirection':'column','backgroundColor':PALETTES[theme]['bg'],'overflow':'hidden'},'steps':[]}

def add(b,key,parent,html,note=None):
    x={'key':key,'parent':parent,'html':html}
    if note:x['verification_note']=note
    b['steps'].append(x)

def artifact(b, label):
    t=b['theme'];p=PALETTES[t]
    add(b,'artifact','board',row('F02 candidate provenance',text(label,11,'secondary',500,t,line=16),
      'width: 100%;height: 30px;padding: 0 16px;background-color: '+p['raised']+';'))

STATES = [
 ('Loading','Loading observations.','The source has not responded. No result count is available.','Loading…','Availability · loading; skeleton has no count.',True),
 ('Empty','No observations match this view.','The request completed with 0 matching records. Current filters remain visible.','Clear filter','Availability · complete, zero matching records.',False),
 ('Partial','Partial coverage.','7 of 8 observations are available. Missing values are not zero.','View coverage','Coverage · partial; preserve the seven observations.',False),
 ('Stale','Older observations retained.','Source: 30 Oct, 20:00 UTC. The expected update has not arrived.','Inspect source','Freshness · stale by the source owner’s policy.',False),
 ('Refresh error','Refresh failed.','The last successful view remains available with its original source date.','Retry refresh','Read error · a retry never sends a save.',False),
 ('Unsupported','This source is not supported.','No value has been inferred for this listing. Supported evidence remains reachable.','View coverage','Availability · unsupported is different from zero.',False),
 ('Guest','Sign in to save this view.','Public evidence remains available on this illustrative public-read route.','Sign in','Access · guest; bind the existing return URL.',False),
 ('Plan required','This source requires an eligible plan.','Available public data remains visible.','Check access','Access · server omits restricted data; existing plans only.',False),
 ('Expired before send','Your session expired.','Your view is retained. Sign in again before saving; no change has been sent.','Sign in again','Only with proof that the request was not sent.',False),
 ('First use','Choose a starting view.','Open an example or select an available instrument from the domain owner’s valid choices.','Open example','Availability · no arbitrary unsupported default.',False),
 ('Save pending','Saving…','This request is pending. You can continue reading the same dated observations.','Saving…','Mutation · pending; repeat submission disabled.',True),
 ('Saved','Saved. Breadth comparison is confirmed.','Open this view again from your saved views.','Open saved view','Only after the owner confirms the object and readback.',False),
 ('Save failed','Save failed.','A noncommit failure is confirmed. Your last saved view is unchanged; local edits remain.','Retry save','Mutation · failure; do not infer noncommit from silence.',False),
 ('Save uncertain','Save outcome unknown.','Check the existing request before retrying.','Check request status','Owner retains request identity; no duplicate write.',False),
 ('Corrected source','The source revised this observation.','View the correction and prior value, with the producer’s revision lineage.','Compare readings','Provenance · correction is not a new authority claim.',False),
 ('Loaded','Source: 30 Oct, 20:00 UTC.','Available observations have loaded. Their units, coverage and evidence remain visible.','Inspect source','Availability · loaded; no permanent success banner.',False),
]

def state_matrix():
    b=board('states-matrix','F02 · States & semantics · Dark / Light · Candidate 2','p-4-0',1440,2800,'dark')
    artifact(b,'F02 / STATE + SEMANTIC CONTRACT / ILLUSTRATIVE NATIVE SPECIMENS')
    add(b,'heading','board',frame('State contract heading',
      text('A state tells you what happened.',28,'ink',600,line=36)+text('Read across one outcome in both themes. Availability, coverage, freshness, access and save remain independent.',14,'secondary',line=22),
      'width: 1440px;padding: 24px 28px 20px;gap: 8px;'))
    headers=frame('State and condition header',text('STATE / CONDITION',11,'secondary',600,line=18),'width: 184px;padding: 12px;')
    headers+=frame('Dark specimen header',text('DARK · OBSERVED COPY + ACTION',11,'secondary',600,line=18),'width: 600px;padding: 12px;background-color: '+PALETTES['dark']['raised']+';')
    headers+=frame('Light specimen header',text('LIGHT · SAME OUTCOME',11,'secondary',600,'light',18),'width: 600px;padding: 12px;background-color: '+PALETTES['light']['raised']+';')
    add(b,'matrix','board',frame('State comparison matrix',row('Column labels',headers,'width: 1384px;align-items: stretch;'),'width: 1440px;padding: 0 28px;'))
    for i,(state,head,copy,action,note,disabled) in enumerate(STATES):
        key='state-'+str(i)
        cells=frame('State '+state,text(state,14,'ink',600,line=20)+text(note,11,'secondary',400,line=16),'width: 184px;padding: 12px;gap: 6px;border-bottom: 1px solid '+PALETTES['dark']['line']+';')
        for t in ['dark','light']:
            p=PALETTES[t]
            specimen=frame(t.title()+' outcome copy',text(head,15,'ink',600,t,22)+text(copy,13,'secondary',400,t,20),'width: 416px;gap: 4px;')
            specimen+='\n'+button(action,t,144,36,disabled)
            cells+='\n'+row(t.title()+' outcome cell',specimen,'width: 600px;min-height: 112px;padding: 12px;gap: 16px;background-color: '+p['panel']+';border-bottom: 1px solid '+p['line']+';')
        add(b,key,'matrix',row('State comparison · '+state,cells,'width: 1384px;min-height: 112px;align-items: stretch;'),
          'One aligned comparison row; native state label, copy and action appear in both themes. No rounded card, colored edge or executed request.')
        if i in [2,5,8,11,15]:
            b['steps'][-1]['checkpoint_after']=True
            b['steps'][-1]['checkpoint_target']=key
    add(b,'combined-heading','board',frame('Combined state introduction',
      text('One view can be stale, partially covered and saving.',21,'ink',600,line=30)+text('Read caveats survive every save transition. Signing in does not prove the earlier save failed.',14,'secondary',line=22),
      'width: 1440px;padding: 28px 28px 16px;gap: 6px;'))
    add(b,'combined','board',row('Combined read and mutation specimens','', 'padding: 0 28px;gap: 24px;align-items: stretch;'))
    for t,expired in [('dark',False),('light',True)]:
        p=PALETTES[t];head='Session expired while saving' if expired else 'Stale + partial + save pending'
        key='combined-'+t
        add(b,key,'combined',frame(head,'','width: 680px;padding: 20px;background-color: '+p['panel']+';border: 1px solid '+p['line']+';border-radius: 8px;gap: 10px;'))
        add(b,key+'-heading',key,frame('Combined state heading and receipt',text(head,18,'ink',600,t,26)+text('Older source: 30 Oct, 20:00 UTC · Partial coverage: 7 of 8',13,'warn',500,t,20),'gap: 10px;'))
        add(b,key+'-value',key,row('Retained observation',text('Participation',13,'secondary',400,t)+text('66.7%',26,'ink',500,t,34)+text('+1.13 pp',14,'up',500,t), 'gap: 20px;'))
        add(b,key+'-status',key,frame('Read caveat and save outcome',text('The expected update has not arrived. One observation is still missing.',13,'secondary',400,t,20)+text('The outcome is unknown. Check the existing request after signing in.' if expired else 'This request is pending. Reading and source inspection remain available.',13,'secondary',400,t,20),'gap: 10px;'))
        add(b,key+'-action',key,button('Sign in and check request' if expired else 'Saving…',t,224,40,not expired))
        add(b,key+'-note',key,text('Existing request identity stays with D23/current write owner. No new request is issued here.' if expired else 'After a confirmed save, the same stale and partial caveats remain.',12,'muted',400,t,18))
        b['steps'][-1]['checkpoint_after']=True
        b['steps'][-1]['checkpoint_target']=key
    add(b,'semantics-heading','board',frame('Semantic distinctions heading',text('The same sign does not imply the same meaning.',21,'ink',600,line=30),'padding: 28px 28px 16px;'))
    add(b,'semantics','board',row('Semantic distinctions','', 'padding: 0 28px;gap: 24px;align-items: flex-start;'))
    sem=[('Direction','+1.13 pp / −0.80 pp','Signs, units and prior-session baseline.','up'),('Options side','≈ Buy / ≈ Sell / Mixed','Execution-side estimate; intent unknown.','flow-buy'),('Exposure','+ Positive / − Negative','Signed quantity; retain domain units.','flow-sell')]
    for i,(head,val,note,col) in enumerate(sem):
        add(b,'meaning-'+str(i),'semantics',frame(head,text(head,13,'secondary',500)+text(val,18,col,600,line=26)+text(note,12,'muted',line=18),'width: 328px;gap: 8px;'))
    add(b,'selection-focus','semantics',frame('Selection and focus',text('Selection / keyboard focus',13,'secondary',500)+row('Selected and focused controls',button('Selected',width=126,height=36,selected=True)+button('Focus',width=110,height=36,focus=True),'gap: 16px;')+text('Quiet selected fill; independent visible focus outline.',12,'muted',line=18),'width: 328px;gap: 8px;'))
    add(b,'notes','board',frame('State implementation notes',text('Builder contract',13,'ink',600)+text('These are editable design specimens, not an executed state machine. Map each axis to the existing owner; preserve typed source identity, request generation, server access enforcement and D23 confirmation/readback.',13,'secondary',line=21)+text('F02-SYSTEM/1.0.0-candidate.2 · INTERACTION_STATES.md · Existing domain verdict, count and lifecycle meanings remain unchanged.',12,'muted',line=18),'width: 1440px;padding: 28px;gap: 8px;'))
    b['expected_geometry']={'matrix_rows':16,'state_column':184,'dark_cell':600,'light_cell':600,'matrix_usable_width':1384,'minimum_row_height':112,'row_separators':'quiet neutral; no rounded card containers','same_copy_in_both_themes':True}
    return b

def small_chart(theme,lang,width=358):
    p=PALETTES[theme];zh=lang=='zh';points=[61.8,62.4,None,63.9,63.3,64.6,65.57,66.7]
    plot_width=width-64
    def xy(i,v):return 44+i*plot_width/7,20+(80-v)/40*140
    els=[]
    for y in [20,90,160]:els.append('<line x1="44" x2="'+str(width-20)+'" y1="'+str(y)+'" y2="'+str(y)+'" stroke="'+p['line']+'"/>')
    last=None
    for i,v in enumerate(points):
        if v is None:last=None;continue
        x,y=xy(i,v)
        if last:els.append('<line x1="'+str(last[0])+'" y1="'+str(last[1])+'" x2="'+str(x)+'" y2="'+str(y)+'" stroke="'+p['accent']+'" stroke-width="2.5"/>')
        els.append('<circle cx="'+str(x)+'" cy="'+str(y)+'" r="3.5" fill="'+p['accent']+'"/>');last=(x,y)
    svg='<svg width="'+str(width)+'" height="200" viewBox="0 0 '+str(width)+' 200" xmlns="http://www.w3.org/2000/svg">'+''.join(els)+'</svg>'
    labels=''
    for v,y in [(80,12),(60,82),(40,152)]:labels+=text(v,12,'muted',400,theme,18,'position: absolute;left: 8px;top: '+str(y)+'px;width: 26px;text-align: right;')
    for i,s in [(0,'10/21'),(2,'10/23'),(4,'10/27'),(7,'10/30')]:labels+=text(s,11,'muted',400,theme,16,'position: absolute;left: '+str(24+i*plot_width/7)+'px;top: 177px;width: 40px;text-align: center;')
    labels+=text('缺失' if zh else 'Missing',12,'muted',400,theme,18,'position: absolute;left: '+str(15+2*plot_width/7)+'px;top: 110px;width: 58px;text-align: center;',lang)
    return frame('Eight sessions with an explicit gap',svg+labels,'position: relative;width: '+str(width)+'px;height: 210px;')

def mobile_macro(theme,lang):
    zh=lang=='zh';p=PALETTES[theme]
    b=board('macro-'+theme+'-'+lang+'-390','F02 · Macro comparison · '+('中文' if zh else 'EN')+' · '+theme.title()+' · 390','p-5-0',390,1510,theme,lang)
    artifact(b,'F02 / 390 CSS px / '+('中文 / 设计候选' if zh else 'EN / DESIGN CANDIDATE'))
    menu='<svg width="20" height="20" viewBox="0 0 24 24"><path d="M4 6H20M4 12H20M4 18H20" stroke="'+p['ink']+'" stroke-width="1.8" fill="none"/></svg>'
    add(b,'app-header','board',row('Compact application header',text('MASTERMIND',13,'ink',600,theme,20,'flex-grow: 1;letter-spacing: 0.06em;')+button('中文' if zh else 'EN',theme,52,44,lang=lang)+row('Menu control',menu,'width: 44px;height: 44px;justify-content: center;'), 'width: 390px;height: 56px;padding: 0 16px;gap: 12px;background-color: '+p['rail']+';border-bottom: 1px solid '+p['line']+';'))
    add(b,'body','board',frame('390px analytical content','', 'width: 390px;padding: 0 16px;background-color: '+p['bg']+';'))
    title=text('市场 / 参与度' if zh else 'MARKET / PARTICIPATION',11,'accent',600,theme,18,lang=lang)
    title+='\n'+row('Page heading and source',text('市场广度' if zh else 'Market breadth',26,'ink',600,theme,32,'width: 264px;',lang)+button('来源' if zh else 'Source',theme,78,44,lang=lang),'width: 358px;justify-content: space-between;')
    title+='\n'+text('示例总体 · 2026年10月30日20:00 UTC' if zh else 'Universe sample · 30 Oct 2026, 20:00 UTC',12,'secondary',400,theme,18,lang=lang)
    add(b,'title','body',frame('Market breadth question and source',title,'width: 358px;height: 108px;padding-top: 12px;padding-bottom: 8px;gap: 4px;'))
    metric=row('Principal observation',text('66.7%',26,'ink',500,theme,30)+text('高于50日均线' if zh else 'above 50-day average',12,'secondary',400,theme,18,lang=lang),'gap: 16px;')
    metric+='\n'+text('+1.13 pp 较上一交易日' if zh else '+1.13 pp vs prior settled session',12,'up',500,theme,18,lang=lang)
    metric+='\n'+text('9/10行业 · 医疗保健0.00 pp · — 不可用' if zh else '9/10 sectors · Health care 0.00 pp · — unavailable',12,'secondary',400,theme,18,lang=lang)
    add(b,'metric','body',frame('Participation with coverage and comparator',metric,'width: 358px;height: 72px;padding-top: 4px;padding-bottom: 2px;gap: 0px;'))
    add(b,'section-toolbar','body',row('Sector comparison toolbar',text('行业对比' if zh else 'Sector comparison',15,'ink',600,theme,22,'flex-grow: 1;',lang)+button('查看图表' if zh else 'View chart',theme,104,44,lang=lang),'width: 358px;height: 44px;'))
    add(b,'scroll-cue','body',frame('Pre-table local overflow cue',text('横向滚动查看覆盖率和全部列 →' if zh else 'Scroll → for coverage and all columns',12,'secondary',400,theme,18,lang=lang),'width: 358px;height: 19px;'))
    cells=text('行业 / 证据' if zh else 'Sector / source',12,'secondary',500,theme,18,'width: 164px;flex-shrink: 0;',lang)
    cells+=text('高于50D' if zh else 'Above 50D',12,'secondary',500,theme,18,'width: 88px;flex-shrink: 0;text-align: right;padding-right: 12px;',lang)
    cells+=text('变动 · pp' if zh else 'Change · pp',12,'secondary',500,theme,18,'width: 96px;flex-shrink: 0;text-align: right;padding-right: 12px;',lang)
    cells+=text('覆盖范围' if zh else 'Coverage',12,'secondary',500,theme,18,'width: 130px;flex-shrink: 0;padding-left: 12px;',lang)
    cells+=text('定义' if zh else 'Definition',12,'secondary',500,theme,18,'width: 160px;flex-shrink: 0;',lang)
    add(b,'table','body',frame('Named sector comparison scroll region',row('Column headings',cells,'width: 650px;height: 36px;padding-left: 12px;background-color: '+p['raised']+';'), 'width: 358px;height: 596px;overflow: hidden;'), 'Viewport 358px; native rows remain 650px. Only this region scrolls in implementation; it is intentionally clipped on the design canvas.')
    for i,r in enumerate(MACRO):
        name=r[1] if zh else r[0];val='—' if r[2] is None else f'{r[2]:.1f}%';delta='—' if r[3] is None else f'{r[3]:+.2f}' if r[3] else '0.00'
        col='muted' if r[3] is None else 'up' if r[3]>0 else 'down' if r[3]<0 else 'ink'
        c=text(name,13,'ink',600 if i==3 else 400,theme,18,'width: 120px;flex-shrink: 0;padding-right: 8px;',lang)
        c+=button('证据' if zh else 'Source',theme,44,44,focus=i==3,lang=lang)
        c+=text(val,13,'ink',400,theme,20,'width: 88px;flex-shrink: 0;text-align: right;padding-right: 12px;font-variant-numeric: tabular-nums;')
        c+=text(delta,13,col,400,theme,20,'width: 96px;flex-shrink: 0;text-align: right;padding-right: 12px;font-variant-numeric: tabular-nums;')
        c+=text(r[4] if r[4]!='—' else ('未量化' if zh else 'Not quantified'),13,'secondary',400,theme,20,'width: 130px;flex-shrink: 0;padding-left: 12px;',lang)
        c+=text('高于50日均线' if zh else 'Above 50-day average',12,'secondary',400,theme,18,'width: 160px;flex-shrink: 0;',lang)
        add(b,'sector-'+str(i),'table',row('Sector '+r[0],c,'width: 650px;height: 56px;padding-left: 12px;background-color: '+p['selected' if i==3 else 'panel']+';border-bottom: 1px solid '+p['line']+';'),
          'Evidence trigger is 44×44px. Stable sector identity, not row position; selected row and focused trigger remain separate.')
        if i in [2,5,9]:b['steps'][-1]['checkpoint_after']=True
    add(b,'post-table','body',frame('Table coverage reminder',text('10行 · 横向滚动查看覆盖率和全部列 →' if zh else '10 rows · scroll for coverage and all columns →',12,'secondary',400,theme,18,lang=lang),'width: 358px;height: 40px;padding-top: 12px;'))
    add(b,'chart-heading','body',frame('Supporting history heading',text('示例总体 · 八个交易日' if zh else 'Universe sample · eight sessions',16,'ink',600,theme,24,lang=lang)+text('高于50日均线的比例 · % · 刻度40–80' if zh else 'Above 50-day average · % · scale 40–80',12,'secondary',400,theme,18,lang=lang),'width: 358px;height: 46px;gap: 4px;'))
    add(b,'chart','body',small_chart(theme,lang),'Seven points, two independent line segments; 23 Oct missing. Numeric coordinates derive from the explicit fixture, not a production feed.')
    add(b,'chart-footer','body',frame('Chart coverage and exact-value action',frame('Gap and coverage',text('8次观测中7次可用 · 不插值' if zh else '7 of 8 observations · no interpolation',12,'secondary',400,theme,18,lang=lang),'width: 358px;height: 24px;')+button('查看准确数值' if zh else 'View exact values',theme,170,44,lang=lang),'width: 358px;'))
    annotation='构建说明：44px重要触控目标；完整行业证据无需悬停。选中状态与焦点独立。按Escape关闭覆盖层后返回相同实体、来源和滚动位置。此画布不证明键盘、触控或400%缩放行为。' if zh else 'Build contract: important controls are 44px. Full-row evidence requires no hover. Selection and focus stay independent. Close/Escape restores the same entity, source and scroll context. Canvas geometry does not prove keyboard, touch or 400% zoom behavior.'
    add(b,'build-note','body',frame('Adjacent mobile build contract',text('构建说明 / F02 candidate 2' if zh else 'Build contract / F02 candidate 2',12,'ink',600,theme,18,lang=lang)+text(annotation,12,'secondary',400,theme,19,lang=lang)+text('F01外壳联合冻结待完成 · 数据均为示例' if zh else 'F01 joint shell freeze remains open · all values illustrative',11,'muted',400,theme,17,lang=lang),'width: 358px;padding-top: 24px;padding-bottom: 24px;gap: 8px;border-top: 1px solid '+p['line']+';'))
    b['expected_geometry']={'table_top':329,'first_row_top':365,'first_row_text_baseline_approx':398,'table_viewport_width':358,'table_intrinsic_width':650,'row_height':56,'control':44,'viewport_kind':'mobile web; no fabricated OS status bar'}
    return b

def overlay(kind):
    theme='light';p=PALETTES[theme];eps=kind=='eps';r=FIXTURE['rows'][6 if eps else 7]
    field='diluted_eps' if eps else 'dividend_per_share'
    b=board('company-'+kind+'-overlay-320','F02 · Company evidence · '+('Unknown EPS' if eps else 'Actual zero dividend')+' · 320','p-5-0',320,1740,theme)
    artifact(b,'F02 / 320 CSS px / EVIDENCE OVERLAY')
    close='<svg width="20" height="20" viewBox="0 0 24 24"><path d="M6 6L18 18M18 6L6 18" stroke="'+p['ink']+'" stroke-width="1.8"/></svg>'
    close=row('Close evidence — initial focus',close,'width: 44px;height: 44px;justify-content: center;background-color: '+p['panel']+';border: 1px solid '+p['control-line']+';border-radius: 6px;outline: 2px solid '+p['focus']+';outline-offset: 2px;')
    add(b,'header','board',row('Evidence dialog header',text('Evidence',18,'ink',600,theme,26,'flex-grow: 1;')+close,'width: 320px;height: 64px;padding: 0 16px;gap: 16px;background-color: '+p['panel']+';border-bottom: 1px solid '+p['line']+';'))
    add(b,'body','board',frame('320px dialog body','', 'width: 320px;padding: 20px;background-color: '+p['bg']+';gap: 16px;'))
    heading=text('ILLUSTRATIVE FILING',11,'accent',600,theme,16)
    heading+='\n'+text('Diluted earnings per share' if eps else 'Dividend per share',24,'ink',600,theme,30)
    heading+='\n'+text('稀释每股收益' if eps else '每股股息',14,'secondary',500,theme,22,lang='zh')
    heading+='\n'+text('EXM · Example Industries',13,'secondary',400,theme,20)
    add(b,'title','body',frame('Exact financial field heading',heading,'width: 280px;gap: 6px;'))
    v='—' if eps else '0.00';message='FY2026 value not supplied. Unknown is not zero.' if eps else 'Reported zero in this illustrative fixture. Zero is a value.'
    add(b,'value','body',frame('Current value and absence semantics',row('Value with unit',text(v,38,'ink',500,theme,46)+text('USD/share',13,'secondary',400,theme,20),'gap: 12px;align-items: baseline;')+text(message,13,'secondary',400,theme,20),'width: 280px;padding: 16px;background-color: '+p['raised']+';gap: 8px;'))
    add(b,'history','body',frame('Five fiscal periods',text('All displayed annual periods',14,'ink',600,theme,20,'padding-bottom: 16px;'), 'width: 280px;'))
    for j,y in enumerate(FIXTURE['statement_periods']):
        val=r[j+2] if r[j+2] is not None else '—'
        c=text('FY '+str(y),13,'secondary',400,theme,20,'width: 140px;')+text(val,17,'ink',500,theme,24,'width: 140px;text-align: right;font-variant-numeric: tabular-nums;')
        add(b,'period-'+str(y),'history',row('FY '+str(y),c,'width: 280px;height: 40px;border-bottom: 1px solid '+p['line']+';'))
        if j==2:b['steps'][-1]['checkpoint_after']=True
    add(b,'comparison','body',frame('Comparison and baseline',text('FY2026 − FY2025',12,'secondary',500,theme,18)+text('Unavailable comparison' if eps else '0.00 USD/share',17,'ink',500,theme,24)+text('A missing current value cannot yield a change.' if eps else 'Percentage change is undefined because the prior value is zero.',13,'secondary',400,theme,20),'width: 280px;gap: 6px;'))
    fields=[('Source identity','f02.fixture.v2/company/EXM/'+field+'/FY2022-FY2026'),('Entity / field','EXM / '+field),('Observation basis','Fiscal years 2022–2026'),('Publication','30 Oct 2026 · 20:02 UTC'),('Retrieved','30 Oct 2026 · 20:03 UTC'),('Unit / currency','USD per diluted share' if eps else 'USD per share; statement currency USD')]
    for i,(label,value) in enumerate(fields):
        add(b,'source-'+str(i),'body',frame(label,text(label,12,'muted',500,theme,18)+text(value,13,'ink',400,theme,20,'width: 280px;overflow-wrap: anywhere;'),'width: 280px;gap: 4px;'))
    add(b,'limitation','body',frame('Field-specific source limitation',text('Source limitation',13,'ink',600,theme,20)+text('The source fixture contains no FY2026 diluted EPS. Earlier reported values remain visible. Do not derive EPS from an unrelated share count.' if eps else 'The fixture reports 0.00 in each displayed period. Do not replace these observations with dashes or calculate 0/0 as a percentage change.',13,'secondary',400,theme,21),'width: 280px;padding: 16px;background-color: '+p['raised']+';gap: 6px;'))
    add(b,'return','body',button('Return to comparison',theme,280,44))
    add(b,'contract','body',frame('Adjacent overlay interaction contract',text('Build contract',12,'ink',600,theme,18)+text('One named modal; background inert. Tab stays inside; Escape closes. Restore the source trigger by stable entity/field/period identity after sort. If removed, focus the named table heading and announce the change.',12,'secondary',400,theme,19)+text('Retain table scroll and draft state. No save is caused by open, close, navigation or language. Browser/keyboard/400% qualification remains open.',12,'secondary',400,theme,19),'width: 280px;padding-top: 16px;border-top: 1px solid '+p['line']+';gap: 8px;'))
    b['expected_geometry']={'viewport':320,'body_width':280,'close_target':44,'return_target':44,'evidence_key':'f02.fixture.v2/company/EXM/'+field+'/FY2022-FY2026','observation_kind':'fiscal periods; not market timestamps'}
    return b

def dock_stress():
    t='dark';p=PALETTES[t]
    b=board('macro-docked-1280','F02 · Macro with evidence dock · 1280 stress · Provisional shell','p-5-0',1280,1300,t)
    artifact(b,'F02 / 1280 CSS px / PROVISIONAL F01 SHELL + F02 DOCK STRESS')
    add(b,'header','board',row('Global header',text('MASTERMIND',14,'ink',600,line=22,style='flex-grow: 1;letter-spacing: 0.06em;')+text('Workspace · Example view',13,'secondary',line=20), 'width: 1280px;height: 64px;padding: 0 24px;background-color: '+p['rail']+';border-bottom: 1px solid '+p['line']+';'))
    add(b,'workspace','board',row('Shell and main area','', 'width: 1280px;align-items: stretch;'))
    add(b,'rail','workspace',frame('224px expanded navigation','', 'width: 224px;padding: 24px 16px;background-color: '+p['rail']+';gap: 8px;border-right: 1px solid '+p['line']+';'))
    add(b,'rail-label','rail',text('WORKSPACE',11,'muted',600,line=18,style='padding: 0 12px 12px;'))
    for i,label in enumerate(['Today','Discover','Analysis','Monitor','Research','Portfolio']):
        add(b,'nav-'+str(i),'rail',row(label,text(label,14,'ink' if label=='Analysis' else 'secondary',600 if label=='Analysis' else 400,line=22), 'width: 192px;height: 44px;padding: 0 12px;border-radius: 6px;background-color: '+p['selected' if label=='Analysis' else 'rail']+';'))
    add(b,'rail-note','rail',frame('Shell ownership note',text('F01 owns navigation and shell release. This stress frame uses the observed baseline only.',12,'muted',line=19),'width: 192px;padding: 24px 12px 0;'))
    add(b,'main','workspace',frame('1008px usable content','', 'width: 1056px;padding: 24px;gap: 20px;'))
    add(b,'title','main',frame('Market breadth heading',text('MARKET / PARTICIPATION',11,'accent',600,line=18)+text('Market breadth',28,'ink',600,line=36)+text('Illustrative sector observations · 30 Oct 2026, 20:00 UTC',13,'secondary',line=20),'width: 1008px;gap: 6px;'))
    add(b,'split','main',row('Primary comparison and dock','', 'width: 1008px;gap: 24px;align-items: flex-start;'))
    add(b,'primary','split',frame('664px comparison area','', 'width: 664px;gap: 12px;'))
    add(b,'dock','split',frame('320px complementary evidence dock','', 'width: 320px;padding: 20px;background-color: '+p['panel']+';border: 1px solid '+p['line']+';border-radius: 8px;gap: 14px;'))
    add(b,'comparison-heading','primary',row('Comparison context',text('Sector comparison',17,'ink',600,line=24,style='flex-grow: 1;')+text('9 / 10 sectors available',12,'secondary',line=18),'width: 664px;height: 34px;'))
    cols=[('Sector',228,False),('Above 50D',104,True),('Δ pp',92,True),('Coverage',128,True),('Evidence',88,False)]
    head=''.join(text(l,12,'secondary',500,line=18,style='width: '+str(w)+'px;flex-shrink: 0;'+('text-align: right;padding-right: 16px;' if right else '')) for l,w,right in cols)
    add(b,'table','primary',frame('Dense sector comparison',row('Column headings',head,'width: 664px;height: 40px;padding: 0 12px;background-color: '+p['raised']+';'), 'width: 664px;'))
    for i,r in enumerate(MACRO):
        val='—' if r[2] is None else f'{r[2]:.1f}%';delta='—' if r[3] is None else f'{r[3]:+.2f}' if r[3] else '0.00'
        color='muted' if r[3] is None else 'up' if r[3]>0 else 'down' if r[3]<0 else 'ink'
        c=text(r[0],13,'ink',600 if i==3 else 400,line=20,style='width: 228px;flex-shrink: 0;')
        for v,w,col in [(val,104,'ink'),(delta,92,color),(r[4],128,'secondary')]:
            c+=text(v,13,col,400,line=20,style='width: '+str(w)+'px;flex-shrink: 0;text-align: right;padding-right: 16px;font-variant-numeric: tabular-nums;')
        c+=button('Source',width=76,height=32,focus=i==3)
        add(b,'sector-'+str(i),'table',row('Sector '+r[0],c,'width: 664px;height: 40px;padding: 0 12px;background-color: '+p['selected' if i==3 else 'panel']+';border-bottom: 1px solid '+p['line']+';'))
        if i in [2,5,9]:b['steps'][-1]['checkpoint_after']=True
    add(b,'history-heading','primary',frame('Supporting history',text('Universe sample · eight sessions',17,'ink',600,line=24)+text('Above 50-day average · % · scale 40–80 · 7 of 8 observations',12,'secondary',line=18),'width: 664px;padding-top: 12px;gap: 4px;'))
    add(b,'chart','primary',small_chart(t,'en',664))
    add(b,'chart-footer','primary',frame('Exact-value action and history scope',button('View exact values',width=170,height=36)+text('Universe history is separate from the sector subset. Missing observations remain gaps; rows sort by raw values with explicit missing-last placement.',12,'secondary',line=19),'width: 664px;gap: 12px;'))
    add(b,'dock-heading','dock',row('Evidence dock heading',text('Evidence',17,'ink',600,line=24,style='flex-grow: 1;')+button('Close',width=60,height=36),'width: 278px;'))
    add(b,'dock-entity','dock',frame('Selected sector identity',text('ILLUSTRATIVE SOURCE',11,'accent',600,line=18)+text('Communication services',22,'ink',600,line=28)+text('Share above the 50-day moving average',13,'secondary',line=20),'width: 278px;gap: 6px;'))
    add(b,'dock-value','dock',frame('Selected observation',text('66.7%',32,'ink',500,line=40)+text('+1.13 pp vs prior settled session',13,'up',500,line=20)+text('Covered / eligible: 21 / 21',13,'secondary',line=20),'width: 278px;gap: 6px;'))
    facts=[('Source identity','f02.fixture.v2/macro/sector/communication_services/share_above_50d/2026-10-30'),('Observation','30 Oct 2026 · settled 20:00 UTC'),('Publication','30 Oct 2026 · 20:02 UTC'),('Retrieved','30 Oct 2026 · 20:03 UTC'),('Units','Share in percent; change in percentage points')]
    for i,(label,value) in enumerate(facts):
        add(b,'dock-source-'+str(i),'dock',frame(label,text(label,12,'muted',500,line=18)+text(value,13,'ink',line=20,style='width: 278px;overflow-wrap: anywhere;'),'width: 278px;gap: 4px;'))
    add(b,'dock-footer','dock',frame('Evidence limitation and return action',text('Row coverage 21/21 and history coverage 7/8 describe different populations. Do not combine their denominators or call this a market total.',12,'secondary',line=19)+button('Return to comparison',width=278,height=36),'width: 278px;gap: 14px;'))
    add(b,'dock-contract','dock',frame('Adjacent dock interaction contract',text('Dock behavior',12,'ink',600,line=18)+text('Complementary region; no focus trap. Escape/Close returns to the same source trigger and scroll. If that row disappears, focus the named comparison heading.',12,'secondary',line=19),'width: 278px;padding-top: 12px;border-top: 1px solid '+p['line']+';gap: 6px;'))
    add(b,'width-contract','main',frame('Provisional width acceptance',text('1280 − 224 rail − 48 padding = 1008px usable',15,'ink',600,line=22)+text('1008 − 320 dock − 24 gap = 664px primary; exceeds the candidate 640px minimum.',13,'secondary',line=21)+text('Below the minimum, use the single evidence overlay; do not automatically collapse F01’s navigation. F01 joint release and real browser/keyboard/400% proof remain open.',12,'muted',line=19),'width: 1008px;padding-top: 20px;border-top: 1px solid '+p['line']+';gap: 6px;'))
    b['expected_geometry']={'viewport_width':1280,'rail':224,'header':64,'main_padding':24,'main_usable':1008,'dock':320,'gap':24,'primary':664,'primary_minimum':640,'shell_release':'PROVISIONAL; F01 joint freeze open'}
    return b

def main():
    boards=[state_matrix(),mobile_macro('dark','en'),mobile_macro('light','zh'),overlay('eps'),overlay('dividend'),dock_stress()]
    data={'schema':'f02.paper.native-construction.v1','status':'PREPARED_NOT_APPLIED','system_version':'F02-SYSTEM/1.0.0-candidate.2','file_id':'01M312VSDSZFVT45674GDVJVZN','source_pattern_sha256':hashlib.sha256(SOURCE.encode()).hexdigest(),'source_fixture_sha256':hashlib.sha256((ROOT/'fixtures/company-history.json').read_bytes()).hexdigest(),'boards':boards}
    out=HERE/'mobile-state-boards.json';out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'path':str(out),'boards':len(boards),'steps':sum(len(b['steps']) for b in boards),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'board_summaries':[{k:b[k] for k in ['key','pageId','width','height','theme','language']}|{'steps':len(b['steps'])} for b in boards]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
