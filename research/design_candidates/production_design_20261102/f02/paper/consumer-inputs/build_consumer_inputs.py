#!/usr/bin/env python3
"""Native Paper construction inputs. Does not call Paper or render a browser.

Each step is one editable visual group. Parent IDs are symbolic construction
references for the operator to resolve from actual Paper returns.
"""
from pathlib import Path
from html import escape
import ast, hashlib, json, re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB = (ROOT / 'pattern-lab.html').read_text()
FIXTURE = json.loads((ROOT / 'fixtures/company-history.json').read_text())
MACRO = ast.literal_eval(re.search(r'const macroRows\s*=\s*(\[.*?\]);', LAB, re.S).group(1).replace('null', 'None'))
PREMIUM = [825000, 612000, 540000, 455000, 425000, 390000, 312000, 280000, 245000, 195000, 145000, 120000]
BASE = 'font-family:Inter,Noto Sans SC,sans-serif;font-size:13px;line-height:20px;'

def palette(theme):
    prefix = ':root' if theme == 'dark' else 'html[data-theme=light]'
    css = re.search(re.escape(prefix) + r'\{([^}]+)', LAB).group(1)
    p = {k:v.strip() for k,v in re.findall(r'--([\w-]+):([^;]+)', css)}
    if theme == 'dark':
        p.update(dict(bg='var(--noir-canvas)', rail='var(--noir-sidebar)', panel='var(--noir-panel)', raised='var(--noir-raised)', selected='var(--noir-selected)', ink='var(--noir-text-primary)', secondary='var(--noir-text-secondary)', muted='var(--noir-text-tertiary)', accent='var(--noir-champagne)'))
    return p

def div(name, style='', inner=''):
    # Avoid flex squeezing within the initially fixed scene; the operator must
    # switch the final artboard height to fit-content after construction.
    if 'flex-shrink:' not in style: style = 'flex-shrink:0;' + style
    return f'<div layer-name="{escape(name,quote=True)}" style="{style}">{inner}</div>'

def text(label, p, size=13, role='ink', weight=400, extra='', name=None):
    return div(name or label, f'font-family:Inter,Noto Sans SC,sans-serif;font-size:{size}px;line-height:{round(size*1.5)}px;font-weight:{weight};color:{p[role]};{extra}', escape(str(label)))

def button(label,p,width=120,primary=False):
    return div(label, BASE+f'display:flex;align-items:center;justify-content:center;width:{width}px;flex-shrink:0;height:36px;padding:0 10px;border-radius:7px;border:1px solid {p["control-line"]};background:{p["ink"] if primary else p["panel"]};color:{p["bg"] if primary else p["ink"]};font-weight:{600 if primary else 400};',escape(label))

def cell(label,p,width,align='left',role='ink',weight=400,size=13,extra=''):
    return text(label,p,size,role,weight,f'width:{width}px;flex-shrink:0;padding:0 10px;text-align:{align};white-space:nowrap;font-variant-numeric:tabular-nums;{extra}')

class Board:
    def __init__(self,key,theme,height,public=False):
        self.p=palette(theme);self.key=key;self.public=public
        self.b={'key':f'{key}-{theme}','name':f'F02 · {key.title()} · {theme.title()} · Candidate 2','pageId':'p-6-0','width':1440,'height':height,'theme':theme,'styles':{'backgroundColor':self.p['bg'],'display':'flex','flexDirection':'column','padding':'0px','gap':'0px','fontFamily':'Inter','color':self.p['ink']},'steps':[]}
        self.step('artifact','board',div('F02 candidate identity',BASE+f'display:flex;align-items:center;justify-content:space-between;width:1440px;height:32px;padding:0 24px;background:{self.p["raised"]};',text(f'F02 / {key.upper()} / {theme.upper()}',self.p,11,'secondary',600)+text('CANDIDATE 2 · ILLUSTRATIVE FIXTURE · REVIEW PENDING',self.p,11,'muted')))
        brand=div('Mastermind',f'display:flex;align-items:center;gap:12px;',div('M mark',f'display:flex;align-items:center;justify-content:center;width:28px;height:28px;background:{self.p["ink"]};border-radius:7px;color:{self.p["bg"]};font-family:Inter;font-size:16px;font-weight:700;','M')+text('MASTERMIND',self.p,12,'ink',700,'letter-spacing:0.1em;'))
        chrome = '研究 · 工具 · 学习' if public and theme=='light' else 'Research · Tools · Learn' if public else 'Workspace · Example view'
        self.step('header','board',div('Public header' if public else 'Shared header envelope',f'display:flex;align-items:center;justify-content:space-between;width:1440px;height:64px;padding:0 24px;background:{self.p["rail"]};border-bottom:1px solid {self.p["line"]};',brand+div('Chrome actions','display:flex;align-items:center;gap:24px;',text(chrome,self.p,12,'secondary')+text('EN / 中文',self.p,12,'ink',500))))
        if public:
            self.step('main','board',div('Public reading surface',f'display:flex;flex-direction:column;width:1440px;padding:32px 160px 40px;gap:0px;background:{self.p["bg"]};'))
        else:
            self.step('body','board',div('Investor workspace envelope',f'display:flex;flex-direction:row;align-items:stretch;width:1440px;background:{self.p["bg"]};'))
            self.step('rail','body',div('F01 provisional rail',f'display:flex;flex-direction:column;width:224px;flex-shrink:0;padding:24px 16px;gap:4px;background:{self.p["rail"]};border-right:1px solid {self.p["line"]};'))
            self.step('rail-label','rail',text('WORKSPACE',self.p,10,'muted',600,'padding:0 12px 8px;letter-spacing:0.1em;'))
            for i,label in enumerate(['Today','Discover','Analysis','Monitor','Research','Portfolio']):
                active=label=='Analysis'
                self.step(f'nav-{i}','rail',div(f'Navigation / {label}',f'display:flex;align-items:center;width:192px;height:42px;padding:0 12px;background:{self.p["selected"] if active else "transparent"};border-radius:8px;',text(label,self.p,14,'ink' if active else 'secondary',600 if active else 400)))
            self.step('rail-note','rail',text('F01 shell envelope. Navigation, history and compact-rail behavior retain their existing owner.',self.p,11,'muted',400,'width:192px;padding:24px 12px 0;white-space:normal;'))
            self.step('main','body',div('Primary workspace',f'display:flex;flex-direction:column;width:1216px;flex-shrink:0;padding:24px;gap:0px;background:{self.p["bg"]};'))

    def step(self,key,parent,html):
        assert parent=='board' or any(x['key']==parent for x in self.b['steps']),(self.key,parent)
        self.b['steps'].append({'key':key,'parent':parent,'html':html})

    def head(self,eyebrow,title,deck):
        p=self.p
        left=div('Question and source context','display:flex;flex-direction:column;gap:5px;width:990px;',text(eyebrow,p,11,'accent',600,'letter-spacing:0.07em;')+text(title,p,28,'ink',600,'letter-spacing:-0.025em;line-height:34px;')+text(deck,p,12,'secondary'))
        self.step('question','main',div('Workspace question','display:flex;align-items:center;justify-content:space-between;width:1168px;padding:0 0 18px;',left+button('Source details',p,132)))

    def note(self,key,parent,copy,padding='12px 0',size=12):
        self.step(key,parent,text(copy,self.p,size,'secondary',400,f'padding:{padding};white-space:normal;'))

    def footer(self,copy,details):
        p=self.p
        self.step('build-footer','main',div('Build contract / candidate limitations',f'display:flex;flex-direction:column;gap:7px;width:1168px;padding:18px 0 0;border-top:1px solid {p["line"]};',text('BUILD CONTRACT · F02-SYSTEM/1.0.0-candidate.2',p,11,'accent',600)+text(copy,p,12,'secondary')+text(details,p,11,'muted')))

def macro_chart(p):
    w,h=824,226;px=44;pw=758;py=16;ph=132
    parts=[]
    for v in [40,60,80]:
        yy=py+ph-(v-40)/40*ph
        parts.append(f'<line x1="{px}" y1="{yy}" x2="{px+pw}" y2="{yy}" stroke="{p["line"]}"/>')
        parts.append(f'<text x="31" y="{yy+4}" font-family="Inter" font-size="12" text-anchor="end" fill="{p["muted"]}">{v}</text>')
    vs=[61.8,62.4,None,63.9,63.3,64.6,65.57,66.7];last=None
    for i,v in enumerate(vs):
        x=px+i*pw/7
        if v is None:
            last=None;parts.append(f'<text x="{x}" y="106" font-family="Inter" font-size="12" text-anchor="middle" fill="{p["muted"]}">unavailable</text>');continue
        y=py+ph-(v-40)/40*ph
        if last:parts.append(f'<line x1="{last[0]}" y1="{last[1]}" x2="{x}" y2="{y}" stroke="{p["accent"]}" stroke-width="2.5"/>')
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{p["accent"]}"/>');last=(x,y)
    for i,label in enumerate(['21 Oct','22','23','26','27','28','29','30 Oct']):
        parts.append(f'<text x="{px+i*pw/7}" y="175" text-anchor="middle" fill="{p["muted"]}" font-family="Inter" font-size="12">{label}</text>')
    return div('Eight categorical sessions / gap preserved','display:flex;flex-direction:column;width:824px;',f'<svg width="{w}" height="190" viewBox="0 0 {w} 190" xmlns="http://www.w3.org/2000/svg">'+''.join(parts)+'</svg>'+text('Exact %: 61.8 · 62.4 · unavailable · 63.9 · 63.3 · 64.6 · 65.57 · 66.7',p,12,'secondary')+text('7 of 8 observations. This universe is independent of the sector fixtures.',p,11,'muted'))

def macro(theme):
    b=Board('macro',theme,1260);p=b.p
    b.head('MARKET / PARTICIPATION','Market breadth','Universe and sector observations · illustrative · observed 30 Oct 2026, 20:00 UTC')
    b.step('comparison-layout','main',div('824 data + 24 gap + 320 evidence','display:flex;align-items:flex-start;gap:24px;width:1168px;'))
    b.step('comparison','comparison-layout',div('Primary comparison','display:flex;flex-direction:column;width:824px;flex-shrink:0;'))
    b.step('evidence','comparison-layout',div('Docked evidence',f'display:flex;flex-direction:column;width:320px;flex-shrink:0;padding:16px;gap:0px;border:1px solid {p["line"]};background:{p["panel"]};border-radius:10px;'))
    items=[('Universe share above 50D','66.7%','+1.13 pp vs prior settled session','up',360),('Sector coverage','9 / 10','1 unavailable','muted',240),('Health care change','0.0 pp','Reported zero','secondary',224)]
    inner=''
    for lab,val,sub,col,width in items:
        value_row=div(lab+' value and comparison','display:flex;align-items:baseline;gap:12px;',text(val,p,28,'ink',500,'line-height:34px;')+text(sub,p,12,col))
        inner+=div(lab,f'display:flex;flex-direction:column;width:{width}px;flex-shrink:0;gap:4px;',text(lab,p,12,'secondary')+value_row)
    b.step('metrics','comparison',div('Unboxed summary',f'display:flex;width:824px;padding:10px 0;border-top:1px solid {p["line"]};border-bottom:1px solid {p["line"]};',inner))
    b.step('tabs','comparison',div('Local manual-activation tabs',f'display:flex;gap:8px;width:824px;padding:12px 0;border-bottom:1px solid {p["line"]};',div('Selected sector comparison',f'padding:8px 12px;background:{p["selected"]};border-radius:7px;',text('Sector comparison',p,13,'ink',600))+text('History values',p,13,'secondary',400,'padding:8px 12px;')))
    b.note('table-caption','comparison','Sector observations · change versus prior session · — means unavailable',padding='14px 0 10px')
    widths=[254,126,130,164,150]
    labels=['Sector','Above 50D','Change · pp','Covered / eligible','Source']
    b.step('table-header','comparison',div('Table header',f'display:flex;align-items:center;width:824px;height:36px;background:{p["raised"]};', ''.join(cell(v,p,widths[i],'left' if i in [0,4] else 'right','secondary',600,11) for i,v in enumerate(labels))))
    for i,r in enumerate(MACRO):
        delta='—' if r[3] is None else ('0.00' if r[3]==0 else f'{r[3]:+.2f}')
        vals=[r[0],'—' if r[2] is None else f'{r[2]:.1f}%',delta,r[4],'Evidence']
        inner=''.join(cell(v,p,widths[j],'left' if j in [0,4] else 'right','link' if j==4 else ('up' if r[3] and r[3]>0 else 'down' if r[3] and r[3]<0 else 'muted' if r[3] is None else 'ink') if j==2 else 'ink',600 if i==3 and j==0 else 400) for j,v in enumerate(vals))
        b.step(f'sector-{i+1}','comparison',div(f'Sector row / {r[0]}',f'display:flex;align-items:center;width:824px;height:40px;background:{p["selected"] if i==3 else p["panel"]};border-bottom:1px solid {p["line"]};',inner))
    b.note('table-behavior','comparison','10 / 10 sector fixtures · selected: Communication services. Raw numeric sorting; missing values last.',size=11)
    b.step('history-title','comparison',div('Universe history heading','display:flex;align-items:baseline;justify-content:space-between;width:824px;padding:20px 0 6px;',text('Universe sample · eight sessions',p,17,'ink',600)+text('View values',p,12,'link')))
    b.note('history-unit','comparison','Share above 50-day average · % · categorical session axis · scale 40–80',padding='0 0 8px')
    b.step('history-chart','comparison',macro_chart(p))
    b.step('evidence-head','evidence',div('Inspector header',f'display:flex;align-items:center;justify-content:space-between;padding:0 0 12px;border-bottom:1px solid {p["line"]};',text('Evidence',p,17,'ink',600)+button('Close',p,64)))
    b.step('evidence-entity','evidence',div('Selected sector identity','display:flex;flex-direction:column;gap:6px;padding:16px 0;',text('SELECTED SECTOR · ILLUSTRATIVE',p,10,'accent',600)+text('Communication services',p,16,'ink',600)))
    for i,(label,value,role) in enumerate([('Above 50D','66.7%','ink'),('Change vs prior session','+1.13 pp','up'),('Covered / eligible','21 / 21','ink')]):
        b.step(f'evidence-value-{i}','evidence',div(label,'display:flex;align-items:center;justify-content:space-between;padding:7px 0;',text(label,p,12,'secondary')+text(value,p,13,role,500)))
    for i,(label,value) in enumerate([('Source identity','macro / communication-services'),('Observed','2026-10-30 · 20:00 UTC'),('Published','2026-10-30 · 20:02 UTC'),('Retrieved','2026-10-30 · 20:03 UTC'),('Unit','Percent; delta in percentage points')]):
        b.step(f'evidence-field-{i}','evidence',div(label,'display:flex;flex-direction:column;gap:3px;padding:10px 0;',text(label,p,11,'muted')+text(value,p,12,'ink',400,'white-space:normal;')))
    b.note('evidence-caveat','evidence','A successful refresh does not establish source freshness. Observation, publication and retrieval retain separate clocks.',padding='12px 0')
    b.step('evidence-return','evidence',button('Return to comparison',p,286))
    b.note('evidence-focus','evidence','Docked: no focus trap. Close returns to the stable row trigger and restores table context.',padding='12px 0 0',size=11)
    b.footer('The selected row is quiet full-width fill, independently focusable. A 320px dock + 24px gap requires at least 640px primary width. Otherwise use the specified overlay.', 'Source: dashboard.html.j2 / theme.css; actual field mapping and all regime, risk, calendar and linked desks stay with D02. F01 joint shell freeze and browser proof remain open.')
    return b.b

def company_history(p):
    w,h=1168,213;px=42;pw=1102;py=12;ph=140
    cols=[p['accent'],p['link'],p['up'],p['flow-sell'],p['down']];parts=[]
    for v in [0,30,60]:
        y=py+ph-v/60*ph;parts.append(f'<line x1="{px}" y1="{y}" x2="{px+pw}" y2="{y}" stroke="{p["line"]}"/><text x="30" y="{y+4}" font-family="Inter" font-size="12" fill="{p["muted"]}" text-anchor="end">{v}</text>')
    group=pw/17;bar=(group-14)/5
    for k,year in enumerate(FIXTURE['periods']):
        for i,ser in enumerate(FIXTURE['series']):
            value=ser['values'][k];bh=value/60*ph;x=px+k*group+7+i*bar
            parts.append(f'<rect x="{x:.2f}" y="{py+ph-bh:.2f}" width="{bar-1:.2f}" height="{bh:.2f}" fill="{cols[i]}"/>')
        parts.append(f'<text x="{px+(k+.5)*group:.2f}" y="177" text-anchor="middle" fill="{p["muted"]}" font-family="Inter" font-size="12">{year}</text>')
    return div('Five series × seventeen fiscal years','display:flex;flex-direction:column;width:1168px;',f'<svg width="{w}" height="190" viewBox="0 0 {w} 190" xmlns="http://www.w3.org/2000/svg">'+''.join(parts)+'</svg>'+text('Five bars per year follow the numbered legend. Definitions are consistent within this illustrative history only.',p,11,'secondary'))

def company(theme):
    b=Board('company',theme,1190);p=b.p
    b.head('ANALYSIS / EXM · EXAMPLE INDUSTRIES','Financial statements','Illustrative issuer · statement currency USD · filing retrieved 30 Oct 2026, 20:03 UTC')
    inner=''
    for label,width,active in [('Income statement',160,True),('Balance sheet',140,False),('Cash flow',120,False),('Annual',78,True),('Quarterly',100,False)]:
        inner+=div(label,f'display:flex;align-items:center;justify-content:center;width:{width}px;height:36px;flex-shrink:0;background:{p["selected"] if active else "transparent"};border-radius:7px;',text(label,p,13,'ink' if active else 'secondary',600 if active else 400))
    b.step('statement-tabs','main',div('Statement and period controls',f'display:flex;align-items:center;gap:8px;width:1168px;padding:0 0 14px;border-bottom:1px solid {p["line"]};',inner+text('Transcripts →',p,13,'link',400,'padding-left:190px;')))
    b.step('history-heading','main',div('Company history heading','display:flex;align-items:baseline;justify-content:space-between;width:1168px;padding:18px 0 10px;',text('Income statement · 17 fiscal years',p,17,'ink',600)+text('USD bn · zero baseline · 0–60',p,12,'secondary')+text('View all 17 years as data →',p,12,'link')))
    cols=[p['accent'],p['link'],p['up'],p['flow-sell'],p['down']];legend=''
    for i,ser in enumerate(FIXTURE['series']):
        legend+=div(ser['en'],f'display:flex;align-items:center;gap:8px;width:233px;flex-shrink:0;',div(f'Series {i+1}',f'display:flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:3px;background:{cols[i]};font-family:Inter;font-size:11px;font-weight:600;color:{p["bg"]};',str(i+1))+text(ser['en'],p,12,'ink'))
    b.step('history-legend','main',div('Numbered series legend','display:flex;width:1168px;padding:0 0 8px;',legend))
    b.step('history-chart','main',company_history(p))
    b.step('statement-caption','main',div('Statement comparison caption','display:flex;justify-content:space-between;width:1168px;padding:20px 0 10px;',text('EXM · annual statements · USD bn unless labeled',p,12,'secondary')+text('← Earlier periods     FY 2022–2026',p,12,'link')))
    widths=[250,125,125,125,125,125,165,128]
    labels=['Reported metric','FY 2022','FY 2023','FY 2024','FY 2025','FY 2026','FY26 / FY25 change','Source']
    b.step('statement-header','main',div('Statement header',f'display:flex;align-items:center;width:1168px;height:38px;background:{p["raised"]};',''.join(cell(v,p,widths[i],'left' if i in [0,7] else 'right','secondary',600,11) for i,v in enumerate(labels))))
    for i,r in enumerate(FIXTURE['rows']):
        label='Diluted earnings per share' if r[0]=='Diluted EPS' else r[0]
        unit='%' if r[8]=='percent' else r[8]
        first=div(label,'display:flex;flex-direction:column;justify-content:center;width:250px;flex-shrink:0;padding:0 10px;',text(label,p,13,'ink',600 if i==0 else 400)+text(unit,p,10,'muted'))
        inner=first+''.join(cell(r[j+2] if r[j+2] is not None else '—',p,125,'right','ink' if r[j+2] is not None else 'muted') for j in range(5))
        delta=r[7] or '—';inner+=cell(delta,p,165,'right','up' if delta.startswith('+') else 'ink' if delta.startswith('0') else 'muted')+cell('Evidence',p,128,'left','link')
        b.step(f'statement-row-{i+1}','main',div(f'Statement / {r[0]}',f'display:flex;align-items:center;width:1168px;height:46px;background:{p["panel"]};border-bottom:1px solid {p["line"]};',inner))
    b.note('statement-caveat','main','— Current diluted EPS field is missing. Dividend change is absolute USD/share; relative growth from a zero base is undefined.',padding='12px 0 18px')
    b.footer('Evidence binds EXM / metric / fiscal period / USD; opening and closing preserves selection and scroll. Manual tabs preserve annual/quarterly and historical navigation through D07.', 'Source: AnalysisWorkspace.tsx + existing getFund/getBars/intel/quote reads; EvidenceRail.tsx owns citation anatomy. The five-series illustration does not qualify real historical definitions, filing data or complete Company integration.')
    b.b['fixture_counts']={'periods':17,'series':5,'plotted_values':85,'recent_periods':5,'statement_rows':9}
    return b.b

def expiry_chart(p):
    parts=[]
    for y,label,v in [(12,'20 Nov 2026',2.857),(56,'18 Dec 2026',1.687)]:
        parts.append(f'<text x="0" y="{y+18}" font-family="Inter" font-size="13" fill="{p["secondary"]}">{label}</text><rect x="138" y="{y}" width="{400*v/3:.2f}" height="24" fill="{p["accent"]}"/><text x="{150+400*v/3:.2f}" y="{y+18}" font-family="Inter" font-size="13" fill="{p["ink"]}">{v:.3f}</text>')
    parts.append(f'<line x1="138" y1="95" x2="538" y2="95" stroke="{p["line"]}"/><text x="138" y="117" font-family="Inter" font-size="12" fill="{p["muted"]}">0</text><text x="538" y="117" font-family="Inter" font-size="12" text-anchor="end" fill="{p["muted"]}">3.0 USD m</text>')
    return '<svg width="650" height="128" viewBox="0 0 650 128" xmlns="http://www.w3.org/2000/svg">'+''.join(parts)+'</svg>'

def options(theme):
    b=Board('options',theme,1220);p=b.p
    b.head('OPTIONS / FLOW','Options tape','Illustrative prints · 30 Oct 2026, 15:47:31–15:58:42 ET · side estimates do not establish intent')
    b.step('transport-receipt','main',div('Transport, session and source clocks',f'display:flex;align-items:center;justify-content:space-between;width:1168px;height:34px;padding:0 12px;background:{p["raised"]};border-radius:6px;',text('Connected',p,12,'ink',600)+text('Market closed · last session',p,12,'secondary')+text('Snapshot 30 Oct · 20:00 UTC',p,12,'secondary')+text('12 prints · USD 4.54 m premium',p,12,'ink')))
    inner=''.join(button(label,p,width) for label,width in [('All presets',113),('Premium ≥ USD 100K',180),('DTE 0–60',106),('All moneyness',138),('Symbol',110)])
    inner+=div('View actions','display:flex;gap:8px;padding-left:223px;',button('Share',p,74)+button('Export',p,78)+button('Save',p,90))
    b.step('filters','main',div('Current filter and owner-action controls','display:flex;align-items:center;gap:8px;width:1168px;padding:14px 0 8px;',inner))
    b.note('tape-caption','main','12 / 12 fixture prints · ≈ estimated side · 1 unknown moneyness · not a market-wide total',padding='8px 0 10px')
    widths=[93,89,119,70,104,103,129,103,55,109,97,97]
    labels=['Instrument','Time · ET','Expiry','Type','Strike · USD','Est. side','Premium · USD','Contracts','DTE','Moneyness','Flags','Source']
    b.step('tape-header','main',div('Tape header',f'display:flex;align-items:center;width:1168px;height:38px;background:{p["raised"]};',''.join(cell(v,p,widths[i],'left','secondary',600,11) for i,v in enumerate(labels))))
    for i,premium in enumerate(PREMIUM):
        row=[['EXM','NOVA','ALFA'][i%3],f'15:{58-i:02}:{42-i:02}','2026-11-20' if i<5 else '2026-12-18','Put' if i%3==1 else 'Call',['120.00','85.00','42.50'][i%3],['≈ Buy','≈ Sell','Mixed'][i%3],f'{premium:,}',f'{1500-i*70:,}','21' if i<5 else '49','Unknown' if i==7 else 'OTM' if i%2 else 'ITM','Sweep' if i%4==0 else '—','Evidence']
        inner=''
        for j,v in enumerate(row):
            role='flow-buy' if j==5 and i%3==0 else 'flow-sell' if j==5 and i%3==1 else 'link' if j==11 else 'muted' if v=='Unknown' else 'ink'
            inner+=cell(v,p,widths[j],'right' if j in [4,6,7,8] else 'left',role,600 if j==0 else 400,13,extra=f'border-left:1px solid {p["line"]};' if j in [5,9] else '')
        b.step(f'print-{i+1:02}','main',div(f'Tape print {i+1:02}',f'display:flex;align-items:center;width:1168px;height:40px;background:{p["panel"]};border-bottom:1px solid {p["line"]};',inner))
    b.note('cohort-caption','main','Contributing cohort: these twelve prints. Full-row evidence preserves contract identity, observations, estimates and source fields.',padding='12px 0 18px',size=11)
    b.step('expiry-heading','main',div('Secondary expiry summary',f'display:flex;align-items:baseline;justify-content:space-between;width:1168px;padding:16px 0 6px;border-top:1px solid {p["line"]};',text('Premium by contract expiry',p,17,'ink',600)+text('USD m · observed 30 Oct 2026, 15:47:31–15:58:42 ET',p,12,'secondary')))
    b.step('expiry-summary','main',div('Expiry bars and interpretation','display:flex;align-items:flex-start;gap:38px;width:1168px;padding:8px 0 18px;',expiry_chart(p)+div('Semantic boundary','display:flex;flex-direction:column;gap:14px;width:480px;padding:10px 0;',text('Expiry is the grouping dimension. The observed trade window is separate. This is not a market/session total.',p,13,'secondary')+div('Side categories','display:flex;gap:22px;',text('≈ Buy',p,14,'flow-buy',600)+text('≈ Sell',p,14,'flow-sell',600)+text('Mixed',p,14,'secondary',600))+text('Intent, signed exposure and market direction remain independent meanings.',p,11,'muted'))))
    b.footer('Filters and the tape lead. Share, Export and Save use the existing owner; this visual does not invent a write API. Pending, saved, failed and uncertain outcomes are specified separately.', 'Source: OptionsWorkspaceMount / OptionsStatisticsView.tsx / flowStream.ts / flowFreshness.ts. D08 retains every view, preset, saved screen, coverage denominator, export scope and entitlement path; D23 retains save readback.')
    b.b['fixture_counts']={'prints':12,'columns':12,'premium_total_usd':sum(PREMIUM),'expiry_buckets':2}
    return b.b

def editorial(theme):
    b=Board('editorial',theme,1640,public=True);p=b.p
    b.step('breadcrumb','main',text('首页 / 研究札记 / Compound Growth for Traders' if theme=='light' else 'Home / Blog / Compound Growth for Traders',p,12,'secondary','400','padding:0 0 22px;'))
    b.step('article-title','main',div('Article title and dek','display:flex;flex-direction:column;gap:12px;width:1120px;',text('FROM THE DESK',p,11,'accent',600,'letter-spacing:0.1em;')+text('Compound Growth for Traders',p,42,'ink',700,'letter-spacing:-0.025em;line-height:48px;width:960px;')+text('Read the calculation, compare the measures, and keep the assumptions in view.',p,18,'secondary',400,'line-height:28px;width:960px;')))
    b.step('publication','main',text('Published 2026-07-20 · Example updated 2026-10-30 · Illustrative article excerpt',p,12,'muted',400,'padding:18px 0 32px;'))
    b.step('article-layout','main',div('TOC and reading measure','display:flex;align-items:flex-start;gap:48px;width:978px;'))
    b.step('toc','article-layout',div('Anchored table of contents','display:flex;flex-direction:column;width:210px;flex-shrink:0;gap:4px;'))
    b.step('article','article-layout',div('English article body','display:flex;flex-direction:column;width:720px;flex-shrink:0;gap:0px;'))
    b.step('toc-label','toc',text('ON THIS PAGE',p,10,'muted',600,'letter-spacing:0.1em;padding:0 0 8px;'))
    for i,label in enumerate(['Follow the calculation','Compare the averages','Where this example stops','Explore the assumptions']):
        b.step(f'toc-{i}','toc',text(label,p,12,'ink' if i==0 else 'secondary',600 if i==0 else 400,'padding:10px 0;'))
    b.step('lede','article',text('A gain of 50% followed by a loss of 50% leaves less than you started with. The second return acts on a different base.',p,20,'ink',400,'line-height:31px;padding:0 0 24px;'))
    b.step('calculation-heading','article',text('Follow the calculation',p,23,'ink',600,'line-height:31px;padding:0 0 14px;'))
    b.step('calculation-copy','article',text('Start with USD 10,000. The first period raises the balance to USD 15,000. Losing half of that balance in the next period leaves USD 7,500. There are no deposits, withdrawals, fees or taxes in this example.',p,17,'secondary',400,'line-height:28px;padding:0 0 18px;'))
    b.step('calculation-caption','article',text('Illustrative calculation · currency USD',p,12,'secondary',400,'padding:0 0 8px;'))
    widths=[260,200,260]
    b.step('calculation-header','article',div('Calculation header',f'display:flex;align-items:center;width:720px;height:40px;background:{p["raised"]};',''.join(cell(v,p,widths[i],'left' if i==0 else 'right','secondary',600,12) for i,v in enumerate(['Period','Return','Balance · USD']))))
    for i,(period,ret,bal) in enumerate([('Start','Not applicable','10,000'),('Year 1','+50%','15,000'),('Year 2','−50%','7,500')]):
        b.step(f'calculation-row-{i}','article',div(period,f'display:flex;align-items:center;width:720px;height:44px;background:{p["panel"]};border-bottom:1px solid {p["line"]};',cell(period,p,260,size=14)+cell(ret,p,200,'right','up' if i==1 else 'down' if i==2 else 'muted',size=14)+cell(bal,p,260,'right',size=14)))
    b.step('calculation-evidence','article',text('Inspect the calculation →',p,13,'link',400,'padding:12px 0 26px;'))
    b.step('averages-heading','article',text('Compare the averages',p,23,'ink',600,'line-height:31px;padding:0 0 14px;'))
    b.step('averages-copy','article',text('The arithmetic average is 0%. The total return is −25% over two years. The compound annual return is about −13.4% per year. These measures answer different questions, so the period and unit stay beside the number.',p,17,'secondary',400,'line-height:28px;padding:0 0 16px;'))
    b.step('equations','article',div('Exact arithmetic',f'display:flex;flex-direction:column;gap:6px;padding:16px 18px;background:{p["raised"]};border-radius:8px;',text('Total return = (7,500 / 10,000) − 1 = −25%.',p,14,'ink')+text('CAGR = (7,500 / 10,000)^(1/2) − 1 ≈ −13.4% per year.',p,14,'ink')))
    b.step('limits-heading','article',text('Where this example stops',p,23,'ink',600,'line-height:31px;padding:26px 0 14px;'))
    b.step('limits-copy','article',text('Reordering the same returns does not change the final balance when no cash enters or leaves. Contributions and withdrawals change that relationship. A fixed-rate calculator describes assumptions; it does not predict future returns.',p,17,'secondary',400,'line-height:28px;padding:0 0 24px;'))
    b.step('next-heading','article',text('Explore the assumptions',p,23,'ink',600,'line-height:31px;padding:0 0 14px;'))
    b.step('next-copy','article',text('Use the existing tools to examine an annualized return or a contribution schedule. Keep the period, currency and cash-flow assumptions in view.',p,17,'secondary',400,'line-height:28px;padding:0 0 18px;'))
    b.step('related','article',div('Existing continuation links',f'display:flex;align-items:center;justify-content:space-between;width:720px;padding:20px 0;border-top:1px solid {p["line"]};',text('CAGR calculator ↗',p,14,'link')+text('Compounding calculator ↗',p,14,'link')+text('Back to the desk ↗',p,14,'link')))
    b.step('public-contract','main',div('Editorial build contract',f'display:flex;flex-direction:column;gap:8px;width:1120px;padding:24px 0 0;border-top:1px solid {p["line"]};',text('BUILD CONTRACT · F02-SYSTEM/1.0.0-candidate.2',p,11,'accent',600)+text('English body; EN/ZH public chrome. Canonical anchors and routes stay with seo_article.html.j2 / seo_base.html.j2. No investor rail or invented translated URL.',p,12,'secondary')+text('TOC uses actual anchors; evidence opens this calculation; continuation uses the existing CAGR, compounding and blog routes. Publication/update dates describe this document, not market data. Browser/keyboard/zoom verification remains separate.',p,11,'muted')))
    b.b['continuation_urls']=['https://www.mastermind-x.com/tools/calculators/cagr.html','https://www.mastermind-x.com/tools/calculators/compounding.html','https://www.mastermind-x.com/blog/index.html']
    b.b['language']={'body':'en','chrome':'zh' if theme=='light' else 'en'}
    return b.b

def validate(boards):
    results=[]
    forbidden=[r'display\s*:\s*grid',r'<table\b',r'\bmargin(?:-[a-z]+)?\s*:',r'<img\b',r'paper-gen://']
    for b in boards:
        known={'board'};seen=set()
        for s in b['steps']:
            assert s['parent'] in known,(b['key'],s['key'],s['parent'])
            assert s['key'] not in seen
            assert not any(re.search(p,s['html'],re.I) for p in forbidden),(b['key'],s['key'],'unsupported CSS/content')
            assert s['html'].startswith('<div ') and s['html'].endswith('</div>'),(b['key'],s['key'])
            known.add(s['key']);seen.add(s['key'])
        results.append({'board':b['key'],'steps':len(b['steps']),'native_html_groups':len(b['steps']),'svg_groups':sum('<svg' in s['html'] for s in b['steps']),'max_step_chars':max(len(s['html']) for s in b['steps'])})
    return results

def main():
    boards=[factory(theme) for factory in [macro,company,options,editorial] for theme in ['dark','light']]
    checks=validate(boards)
    packet={'schema':'f02.paper.native-construction-inputs.v1','status':'INPUTS_ONLY_NOT_PAPER_EFFECT','system_version':'F02-SYSTEM/1.0.0-candidate.2','target_file_id':'01M312VSDSZFVT45674GDVJVZN','source_artifact_commit':'d68d5ecfbcd7e29094f59af3f44e7ae2a0f7f940','shell':'observed 224px rail / 64px header / 24px main padding; F01 joint freeze pending','instructions':['Resolve symbolic parent keys only from returned IDs.','Create each artboard first; insert each visual-group step incrementally.','Inspect actual screenshot and editable structure after meaningful groups.','Use fit-content for final artboard height if content exceeds the initial scene.','Never call these inputs Paper applied until actual guarded effect and readback.'],'boards':boards}
    (HERE/'consumer-boards.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
    for b in boards:(HERE/(b['key']+'.json')).write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
    manifest={'schema':'f02.paper.native-input-check.v1','checks':checks,'data_counts':{'macro_sectors':len(MACRO),'company_periods':len(FIXTURE['periods']),'company_series':len(FIXTURE['series']),'company_values':sum(len(x['values']) for x in FIXTURE['series']),'company_recent_periods':len(FIXTURE['statement_periods']),'company_rows':len(FIXTURE['rows']),'option_prints':len(PREMIUM),'option_premium_total':sum(PREMIUM)},'paper_verified':False,'browser_verified':False}
    (HERE/'input-checks.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'boards':len(boards),'steps':sum(len(x['steps']) for x in boards),'checks':checks},indent=2))

if __name__=='__main__':main()
