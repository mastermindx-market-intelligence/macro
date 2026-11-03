#!/usr/bin/env python3
"""Draw original F02 vector specifications and matching static PNG plates.

This is a geometry/type drawing program, NOT an HTML renderer or browser test.
No remote assets, browser automation, Paper writes, or product code are used.
The SVGs are editable source illustrations; they are not Paper references.
"""
from __future__ import annotations
import ast, contextlib, hashlib, json, math, re
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HTML = (ROOT / 'pattern-lab.html').read_text()
FONTS = Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/share/fonts/truetype')
REGULAR = FONTS / 'NotoSans-Regular.ttf'
BOLD = FONTS / 'NotoSans-Bold.ttf'
SCALE = 2
MANIFEST = []

def colors(theme):
    prefix = ':root' if theme == 'dark' else 'html[data-theme=light]'
    css = re.search(re.escape(prefix) + r'\{([^}]+)', HTML).group(1)
    return {k: v for k, v in re.findall(r'--([\w-]+):([^;]+)', css)}

PALETTES = {t: colors(t) for t in ['dark', 'light']}
PALETTES['dark']['control'] = '#6f6f6f'
PALETTES['light']['control'] = '#85877f'
MACRO = ast.literal_eval(re.search(r'const macroRows=(\[.*?\]);', HTML).group(1).replace('null', 'None'))
COMPANY = ast.literal_eval(re.search(r'const companyRows=(\[.*?\]);', HTML).group(1).replace('null', 'None'))
PREMIUM = [825000, 612000, 540000, 455000, 425000, 390000, 312000, 280000, 245000, 195000, 145000, 120000]

class Sheet:
    def __init__(self, width, height, theme='dark', title='', lang='en', raster=True):
        self.w, self.h, self.p, self.theme = width, height, PALETTES[theme], theme
        self.title, self.lang, self.raster = title, lang, raster
        self.im = Image.new('RGBA', (width*SCALE, height*SCALE), self.p['bg'])
        self.draw = ImageDraw.Draw(self.im)
        self.parts = []
        self.fonts = {}
        self.clip_id = 0
        self.overflows = []
        self.rect(0, 0, width, height, 'bg')

    def col(self, key):
        return self.p.get(key, key)

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = ImageFont.truetype(str(BOLD if bold else REGULAR), round(size*SCALE))
        return self.fonts[key]

    def measure(self, text, size=14, bold=False):
        return self.font(size,bold).getlength(str(text))/SCALE

    def rect(self, x, y, w, h, fill='panel', radius=0, stroke=None, sw=1):
        f, st = self.col(fill), self.col(stroke) if stroke else None
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{f}"'+(f' stroke="{st}" stroke-width="{sw}"' if st else '')+'/>')
        box = tuple(round(v*SCALE) for v in (x,y,x+w,y+h))
        if radius:
            self.draw.rounded_rectangle(box, radius=round(radius*SCALE), fill=None if f=='none' else f, outline=st, width=round(sw*SCALE))
        else:
            self.draw.rectangle(box, fill=None if f=='none' else f, outline=st, width=round(sw*SCALE))

    def line(self,x1,y1,x2,y2,color='line',width=1,dash=None):
        c=self.col(color)
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
        if dash:
            # The only dashed marks are horizontal, non-data guides.
            step=float(dash.split()[0]); xx=x1
            while xx<x2:
                self.draw.line((xx*SCALE,y1*SCALE,min(x2,xx+step)*SCALE,y2*SCALE),fill=c,width=round(width*SCALE));xx+=step*2
        else:
            self.draw.line(tuple(v*SCALE for v in (x1,y1,x2,y2)),fill=c,width=max(1,round(width*SCALE)))

    def circle(self,x,y,r,color='accent',stroke=None,sw=1):
        c=self.col(color);st=self.col(stroke) if stroke else None
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"'+(f' stroke="{st}" stroke-width="{sw}"' if st else '')+'/>')
        self.draw.ellipse(((x-r)*SCALE,(y-r)*SCALE,(x+r)*SCALE,(y+r)*SCALE),fill=c,outline=st,width=round(sw*SCALE))

    def text(self,x,y,text,size=14,color='ink',bold=False,anchor='start',spacing=None):
        text=str(text);c=self.col(color)
        fam='Noto Sans SC, PingFang SC, sans-serif' if self.lang=='zh' else 'Noto Sans, DejaVu Sans, Arial, sans-serif'
        self.parts.append(f'<text x="{x}" y="{y}" fill="{c}" font-size="{size}" font-weight="{650 if bold else 400}" text-anchor="{anchor}" font-family="{fam}"'+(f' letter-spacing="{spacing}"' if spacing else '')+'>'+escape(text)+'</text>')
        if self.raster:
            anc={'start':'ls','end':'rs','middle':'ms'}[anchor]
            font=self.font(size,bold)
            if any(ch in text for ch in '→↗≈≥'):
                font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',round(size*SCALE))
            self.draw.text((round(x*SCALE),round(y*SCALE)),text,font=font,fill=c,anchor=anc,stroke_width=0)
        width=self.measure(text,size,bold)
        left=x if anchor=='start' else x-width if anchor=='end' else x-width/2
        if left < -0.5 or left+width > self.w+0.5 or y>self.h:
            self.overflows.append({'text':text,'x':x,'y':y,'width':width})

    def wrap(self,text,width,size=14,bold=False):
        words=str(text).split(); lines=[];cur=''
        for word in words:
            test=(cur+' '+word).strip()
            if cur and self.measure(test,size,bold)>width:
                lines.append(cur);cur=word
            else:cur=test
        if cur:lines.append(cur)
        return lines

    def paragraph(self,x,y,text,width,size=14,color='secondary',leading=None,bold=False):
        leading=leading or size*1.6
        for line in self.wrap(text,width,size,bold):
            self.text(x,y,line,size,color,bold);y+=leading
        return y

    def button(self,x,y,label,width=None,primary=False,focus=False,small=False,disabled=False):
        fs=12 if small else 13;h=44 if self.w<=390 else 32 if small else 36
        width=width or self.measure(label,fs,primary)+24
        self.rect(x,y,width,h,'ink' if primary else 'panel',7,None if primary else 'control')
        if focus:self.rect(x-3,y-3,width+6,h+6,'none',10,'focus',2)
        self.text(x+width/2,y+h/2+4,label,fs,'muted' if disabled else 'bg' if primary else 'ink',primary,'middle')
        return width

    @contextlib.contextmanager
    def clip(self,x,y,w,h):
        self.clip_id+=1;cid=f'clip-{self.clip_id}'
        self.parts.append(f'<defs><clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs><g clip-path="url(#{cid})">')
        old_im,old_draw=self.im,self.draw
        self.im=Image.new('RGBA',old_im.size,(0,0,0,0));self.draw=ImageDraw.Draw(self.im)
        yield
        box=tuple(round(v*SCALE) for v in (x,y,x+w,y+h));crop=self.im.crop(box)
        old_im.alpha_composite(crop,(round(x*SCALE),round(y*SCALE)))
        self.im,self.draw=old_im,old_draw
        self.parts.append('</g>')

    def save(self,name,notes,css_width=None):
        desc='Original static vector design composition. Illustrative data. Not a browser screenshot, editable Paper reference, accessibility test, or approved reference.'
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="title desc" lang="{self.lang}"><title id="title">{escape(self.title)}</title><desc id="desc">{desc}</desc>'+''.join(self.parts)+'</svg>'
        (HERE/f'{name}.svg').write_text(svg)
        if self.raster:self.im.convert('RGB').resize((self.w,self.h),Image.Resampling.LANCZOS).save(HERE/f'{name}.png',optimize=True)
        MANIFEST.append({'id':name,'title':self.title,'kind':'static_vector_composition','theme':self.theme,'language':self.lang,'width':self.w,'height':self.h,'intended_css_width':css_width or self.w,'svg':f'{name}.svg','png':f'{name}.png' if self.raster else None,'raster_font':'Noto Sans / installed fallback for the specified Inter-first UI' if self.raster else 'unrendered: no CJK font present','browser_verified':False,'paper_applied':False,'notes':notes,'off_canvas_text':self.overflows})

def artifact_bar(s,label):
    s.rect(0,0,s.w,36,'raised')
    s.text(24,23,'F02 / '+label,11,'secondary',True)
    s.text(s.w-24,23,'ILLUSTRATIVE · STATIC COMPOSITION · NOT PAPER',10,'muted',False,'end')

def brand(s,x,y):
    s.rect(x,y-21,28,28,'ink',7);s.text(x+14,y,'M',16,'bg',True,'middle')
    s.text(x+40,y,'MASTERMIND',12,'ink',True,spacing='1.2')

def shell(s,consumer,public=False):
    artifact_bar(s,consumer.upper()+' / '+s.theme.upper()+' / 1440')
    s.rect(0,36,s.w,64,'rail');s.line(0,100,s.w,100)
    brand(s,24,75)
    s.text(s.w-24,74,'Research · Tools · Learn' if public else 'Workspace · Example view',12,'muted',False,'end')
    if not public:
        s.rect(0,100,224,s.h-100,'rail');s.line(224,100,224,s.h)
        s.text(28,138,'WORKSPACE',10,'muted',True,spacing='1.1')
        for i,label in enumerate(['Today','Discover','Analysis','Monitor','Research','Portfolio']):
            y=157+i*46
            if label=='Analysis':s.rect(16,y,192,42,'selected',8)
            s.text(28,y+27,label,14,'ink' if label=='Analysis' else 'secondary',label=='Analysis')
        s.paragraph(28,465,'Observed shell envelope. F01 retains navigation and composition ownership.',164,11,'muted',18)

def foot(s,top,line1,line2):
    s.line(248 if s.w==1440 else 24,top,s.w-24,top)
    x=248 if s.w==1440 else 24
    s.text(x,top+24,line1,11,'secondary')
    s.text(x,top+45,line2,11,'muted')

def title(s,eyebrow,head,deck,right='Source details'):
    s.text(248,139,eyebrow,11,'accent',True,spacing='1')
    s.text(248,182,head,28,'ink',True)
    s.text(248,211,deck,14,'secondary')
    s.text(248,239,'Filing retrieved  30 Oct 2026 · 20:03 UTC' if head=='Financial statements' else 'Source  30 Oct 2026 · 20:00 UTC',12,'secondary')
    s.text(610 if head=='Financial statements' else 570,239,'Annual fiscal periods · illustrative' if head=='Financial statements' else 'Illustrative settled observation',12,'muted')
    s.button(1284,154,right,132)

def metric(s,x,y,label,value,unit,change,note,w=260,color='secondary'):
    s.text(x,y,label,12,'secondary')
    s.text(x,y+43,value,32,'ink')
    xx=x+s.measure(value,32)+10
    s.text(xx,y+41,unit,16,'secondary')
    s.text(x,y+68,change,12,color)
    s.text(x,y+89,note,11,'muted')

def macro_chart(s,x,y,w,mobile=False):
    s.text(x,y,'Participation over eight sessions',17 if not mobile else 15,'ink',True)
    s.text(x,y+24,'Share above 50-day average · % · scale 40–80',12 if not mobile else 10,'secondary')
    if not mobile:s.text(x+w,y,'View values',12,'link',False,'end')
    px=x+40;pw=w-62;py=y+48;ph=150 if not mobile else 140
    val=[61.8,62.4,None,63.9,63.3,64.6,65.57,66.7]
    for a in [40,60,80]:
        yy=py+ph-(a-40)/40*ph;s.line(px,yy,px+pw,yy);s.text(px-12,yy+4,str(a),11,'muted',False,'end')
    points=[]
    for i,v in enumerate(val):
        xx=px+i*pw/7
        if v is None:
            points=[];s.text(xx,py+ph*.66,'gap',10,'muted',False,'middle');continue
        yy=py+ph-(v-40)/40*ph
        if points:s.line(points[-1][0],points[-1][1],xx,yy,'accent',2.5)
        points.append((xx,yy));s.circle(xx,yy,3.5)
    for i,label in [(0,'21 Oct'),(2,'23'),(4,'27'),(7,'30 Oct')] if mobile else list(enumerate(['21 Oct','22','23','26','27','28','29','30 Oct'])):
        s.text(px+i*pw/7,py+ph+24,label,10 if mobile else 11,'muted',False,'middle')
    s.text(x,py+ph+52,'7 of 8 observations. No interpolation across the missing session.' if not mobile else '7 of 8 observations · no interpolation',11,'secondary')

def tabs(s,x,y,w,labels=('Comparison','Chart data')):
    h=44 if s.w<=390 else 36
    s.rect(x,y,115,h,'selected',7);s.text(x+14,y+h/2+6,labels[0],13,'ink',True)
    s.text(x+134,y+h/2+6,labels[1],13,'secondary');s.line(x,y+h+10,x+w,y+h+10)

def evidence(s,x,y,w=320,kind='macro'):
    s.rect(x,y,w,655,'panel',10,'line')
    s.text(x+18,y+31,'Evidence',17,'ink',True);s.button(x+w-52,y+9,'×',36)
    s.line(x,y+51,x+w,y+51)
    s.text(x+18,y+80,'ILLUSTRATIVE SOURCE',10,'accent',True)
    s.text(x+18,y+113,'Communication services',16,'ink',True)
    s.text(x+18,y+149,'Above 50D',12,'secondary');s.text(x+w-18,y+149,'66.7%',14,'ink',False,'end')
    s.text(x+18,y+180,'Change vs prior session',12,'secondary');s.text(x+w-18,y+180,'+1.13 pp',14,'up',False,'end')
    s.text(x+18,y+211,'Covered / eligible',12,'secondary');s.text(x+w-18,y+211,'21 / 21',14,'ink',False,'end')
    s.line(x+18,y+231,x+w-18,y+231)
    fields=[('Source identity','f02.fixture.v1 / macro-3'),('Observed period','2026-10-30 · 20:00 UTC'),('Publication','2026-10-30 · 20:02 UTC'),('Retrieved','2026-10-30 · 20:03 UTC'),('Unit','Percent; delta in percentage points')]
    yy=y+258
    for lab,val in fields:s.text(x+18,yy,lab,11,'muted');s.text(x+18,yy+21,val,12,'ink');yy+=57
    s.paragraph(x+18,y+550,'A successful refresh does not prove that a source is current. The observation keeps its own clock.',w-36,12,'secondary',19)
    s.button(x+18,y+605,'Return to comparison',w-36)

def macro_sheet(theme):
    s=Sheet(1440,1240,theme,'Macro comparison and evidence · F02 static specimen')
    shell(s,'Macro');title(s,'MARKET / PARTICIPATION','Market breadth','Compare participation by sector, then inspect the observation and its source.')
    x,y,w=248,267,824
    s.line(x,y,x+w,y);s.line(x,y+134,x+w,y+134)
    metric(s,x,y+25,'Above 50-day average','66.7','%','+1.13 pp vs prior session','Illustrative share · 8-session series',color='up')
    metric(s,x+292,y+25,'Sectors with data','9','/ 10','1 unavailable','Missing does not mean zero')
    metric(s,x+566,y+25,'Health care change','0.0','pp','Reported zero','Not a placeholder')
    macro_chart(s,x,433,w)
    tabs(s,x,713,w)
    s.text(x,786,'Sector comparison · illustrative subset · change versus prior session',12,'secondary')
    cols=[x,x+255,x+382,x+517,x+680,x+w]
    s.rect(x,804,w,36,'raised')
    for xx,lab in [(x+12,'Sector'),(cols[2]-12,'Above 50D'),(cols[3]-12,'Change · pp'),(cols[4]-12,'Covered / eligible')]:s.text(xx,827,lab,11,'secondary',True,'start' if xx==x+12 else 'end')
    s.text(cols[4]+12,827,'Source',11,'secondary',True)
    # All ten rows remain in the source fixture; this bounded pane shows eight and gives its count.
    for i,r in enumerate(MACRO[:8]):
        yy=840+i*37;s.rect(x,yy,w,37,'panel');s.line(x,yy+37,x+w,yy+37)
        s.text(x+12,yy+24,r[0],12,'ink',i==3)
        s.text(cols[2]-12,yy+24,'—' if r[2] is None else f'{r[2]:.1f}%',13,'ink',False,'end')
        delta='—' if r[3] is None else f'{r[3]:+.2f}' if r[3]!=0 else '0.00'
        s.text(cols[3]-12,yy+24,delta,13,'up' if r[3] and r[3]>0 else 'down' if r[3] and r[3]<0 else 'muted' if r[3] is None else 'ink',False,'end')
        s.text(cols[4]-12,yy+24,r[4],13,'ink',False,'end');s.text(cols[4]+12,yy+24,'Evidence',12,'link')
    s.text(x,1163,'8 of 10 rows in this bounded view · 2 more below · source opens the complete row',11,'muted')
    evidence(s,1096,267)
    foot(s,1180,'F02 pattern slice: 224 rail + 48 padding + 824 content + 24 gap + 320 evidence = 1440.',
         'Retain Macro regime, risk, calendar, linked desks and domain semantics in D02 composition. No route or capability is removed here.')
    s.save(f'macro-{theme}-1440', ['Docked inspector is exactly 320px; primary data width is 824px.','This is the breadth pattern slice, not a replacement for the Macro workspace.','The viewport intentionally bounds table rows with a visible continuation count.'])

def bar_chart(s,x,y,w,values,labels,title_,unit,maxvalue):
    s.text(x,y,title_,17,'ink',True);s.text(x,y+25,unit,12,'secondary');s.text(x+w,y,'View values',12,'link',False,'end')
    px=x+44;pw=w-72;py=y+50;ph=145
    for tick in [0,maxvalue/2,maxvalue]:
        yy=py+ph-tick/maxvalue*ph;s.line(px,yy,px+pw,yy);s.text(px-12,yy+4,f'{tick:g}',11,'muted',False,'end')
    bw=min(82,pw/(len(values)*2.1))
    for i,(value,label) in enumerate(zip(values,labels)):
        cx=px+pw*(i+.5)/len(values);bh=value/maxvalue*ph
        s.rect(cx-bw/2,py+ph-bh,bw,bh,'accent',2);s.text(cx,py+ph-bh-8,f'{value:g}',12,'ink',False,'middle');s.text(cx,py+ph+25,label,11,'muted',False,'middle')

def company_sheet(theme):
    s=Sheet(1440,1216,theme,'Company statement pattern · F02 static specimen')
    shell(s,'Company');title(s,'ANALYSIS / EXM · EXAMPLE INDUSTRIES','Financial statements','Compare reported periods with definitions and statement currency kept in view.')
    s.line(248,267,1416,267);s.line(248,401,1416,401)
    metric(s,248,292,'Revenue · FY 2026','48.00','USD bn','+33.3% vs FY 2025','Statement currency: USD',color='up')
    metric(s,656,292,'Operating margin','24.5','%','+1.2 pp vs FY 2025','Reported basis; no currency conversion',color='up')
    metric(s,1057,292,'Diluted EPS','—','USD / share','Not available','Current filing field is missing')
    bar_chart(s,248,435,1168,[12,16,24,36,48],['FY 2022','2023','2024','2025','2026'],'Reported annual revenue','USD bn · fiscal years · zero baseline',60)
    s.text(248,683,'Fiscal years are not calendar years. Earlier definitions remain explicitly non-comparable where the source says so.',12,'secondary')
    tabs(s,248,708,1168,('Statements','Chart data'))
    for xx,label,active in [(248,'Income statement',True),(418,'Balance sheet',False),(566,'Cash flow',False),(702,'Annual',True),(790,'Quarterly',False)]:
        if active:s.rect(xx,770,154 if xx==248 else 76,32,'selected',6)
        s.text(xx+10,792,label,12,'ink' if active else 'secondary',active)
    s.text(1416,792,'17-year history remains reachable →',12,'link',False,'end')
    s.text(248,826,'EXM · Example Industries · annual statements · USD bn unless labeled',12,'secondary')
    cols=[248,550,714,878,1042,1235,1416]
    s.rect(248,842,1168,36,'raised')
    for i,l in enumerate(['Reported metric','FY 2024','FY 2025','FY 2026','Change · FY26 / FY25','Source']):
        s.text(cols[i]+12 if i in [0,5] else cols[i+1]-12,866,l,11,'secondary',True,'start' if i in [0,5] else 'end')
    for i,r in enumerate(COMPANY):
        yy=878+i*33;s.rect(248,yy,1168,33,'panel');s.line(248,yy+33,1416,yy+33)
        s.text(260,yy+22,r[0],12,'ink',i==0)
        s.text(536,yy+22,{'USD bn':'USD bn','percent':'%','USD / share':'USD/share'}[r[6]],10,'muted',False,'end')
        for j in range(3):s.text(cols[j+2]-12,yy+22,r[j+2] or '—',13,'ink' if r[j+2] else 'muted',False,'end')
        delta=r[5] or '—'
        if i==6:delta='0.00 USD/share'
        s.text(cols[5]-12,yy+22,delta,12,'up' if delta.startswith('+') else 'ink' if i==6 else 'muted',False,'end')
        s.text(cols[5]+12,yy+22,'Evidence',12,'link')
    foot(s,1154,'F02 pattern slice: source definitions, statement currency, fiscal basis and explicit missing fields stay attached.',
         'Retain Company tabs, annual/quarterly controls, transcripts, evidence precision and historical paging in D07 composition.')
    s.save(f'company-{theme}-1440',['Statement comparison includes zero dividend, unavailable EPS, percentage-point margin change and currency values.','Earlier-period and transcript capabilities remain with the existing Company composition; controls shown are static.'])

def options_sheet(theme):
    s=Sheet(1440,1250,theme,'Options tape pattern · F02 static specimen')
    shell(s,'Options');title(s,'OPTIONS / FLOW','Options tape','Read the observed prints. Trade side is not a prediction of price direction.')
    s.rect(248,259,1168,37,'raised',7);s.text(262,283,'Connected',12,'ink',True);s.text(372,283,'Market closed · last session',12,'secondary');s.text(627,283,'Source 30 Oct · 20:00 UTC',12,'secondary');s.text(913,283,'Transport and source clocks remain separate',12,'muted')
    s.line(248,316,1416,316);s.line(248,445,1416,445)
    metric(s,248,340,'Observed premium','4.54','USD m','12 example prints','Fixture window; not a market total')
    metric(s,656,340,'Classified near ask','4','/ 12','Estimated buy side','Classification does not establish intent')
    metric(s,1057,340,'Unknown moneyness','1','/ 12','Shown without inference','No underlying snapshot')
    s.text(248,478,'Premium by expiry',17,'ink',True);s.text(248,502,'USD m · exact fixture totals · zero baseline',12,'secondary')
    # Compact two-bar comparison preserves space for the analytical table.
    for yy,label,value in [(527,'20 Nov 2026',2.857),(564,'18 Dec 2026',1.687)]:
        s.text(248,yy+16,label,12,'secondary');s.rect(379,yy,440*value/3,22,'accent',2);s.text(379+440*value/3+12,yy+16,f'{value:.3f}',12,'ink')
    s.line(379,592,819,592);s.text(379,611,'0',10,'muted');s.text(819,611,'3.0 USD m',10,'muted',False,'end')
    s.paragraph(922,493,'Side is estimated from execution context. Opening or closing intent and signed exposure are separate fields.',450,13,'secondary',21)
    s.text(922,578,'≈ Buy',14,'flow-buy',True);s.text(1014,578,'≈ Sell',14,'flow-sell',True);s.text(1105,578,'Mixed',14,'secondary',True)
    s.text(922,606,'These colors do not flip with language or market direction.',11,'muted')
    x=248
    for label,width in [('All presets',113),('Premium ≥ USD 100K',180),('DTE 0–60',106),('All moneyness',138),('Symbol',110)]:s.button(x,638,label,width);x+=width+8
    s.button(1158,638,'Share',74);s.button(1240,638,'Export',78);s.button(1326,638,'Save',90)
    s.text(248,705,'12 illustrative prints · all values in this fixture are observed examples, not live market data',12,'secondary')
    widths=[93,89,119,70,104,103,129,103,55,109,97,97]
    cols=[248]
    for w in widths:cols.append(cols[-1]+w)
    assert sum(widths)==1168
    labels=['Instrument','Time · ET','Expiry','Type','Strike · USD','Est. side','Premium · USD','Contracts','DTE','Moneyness','Flags','Source']
    s.rect(248,722,1168,37,'raised')
    for i,label in enumerate(labels):s.text(cols[i]+10,746,label,10,'secondary',True)
    for i,p in enumerate(PREMIUM):
        y=759+i*31;s.rect(248,y,1168,31,'panel');s.line(248,y+31,1416,y+31)
        side=['≈ Buy','≈ Sell','Mixed'][i%3]
        row=[['EXM','NOVA','ALFA'][i%3],f'15:{58-i:02}:{42-i:02}','2026-11-20' if i<5 else '2026-12-18','Put' if i%3==1 else 'Call',['120.00','85.00','42.50'][i%3],side,f'{p:,}',f'{1500-i*70:,}','21' if i<5 else '49','Unknown' if i==7 else 'OTM' if i%2 else 'ITM','Sweep' if i%4==0 else '—','Evidence']
        for j,value in enumerate(row):
            color='flow-buy' if j==5 and i%3==0 else 'flow-sell' if j==5 and i%3==1 else 'link' if j==11 else 'muted' if value=='Unknown' else 'ink'
            s.text(cols[j+1]-10 if j in [4,6,7,8] else cols[j]+10,y+21,value,11,color,j==0,'end' if j in [4,6,7,8] else 'start')
    s.text(248,1155,'12 / 12 fixture rows · source inspection retains the complete contract identity and classification caveats',11,'muted')
    foot(s,1190,'F02 pattern slice: keep call/put, estimated side, moneyness, expiry, DTE, contracts, flags and currency distinct.',
         'Retain all Options workspaces, presets, saved screens, filters, sharing and the actual export scope in D08 composition.')
    s.save(f'options-{theme}-1440',['The table uses all 12 fixture rows with 12 columns.','Production supports additional filters/workspaces and a different export window; this specimen does not remove or redefine them.','Chart totals reconcile to USD 4,544,000; buy-side estimate is 4/12; unknown moneyness is 1/12.'])

def editorial_sheet(theme):
    s=Sheet(1440,1340,theme,'Public editorial reading pattern · F02 static specimen')
    shell(s,'Public editorial',True)
    s.text(160,139,'Home / Blog / Compound Growth for Traders',12,'secondary')
    s.text(160,180,'FROM THE DESK',11,'accent',True,spacing='1.2')
    s.text(160,239,'Compound Growth for Traders',42,'ink',True)
    s.paragraph(160,280,'Read the calculation, compare the measures, and keep the assumptions in view.',1000,18,'secondary',28)
    s.text(160,335,'Published 2026-07-20  ·  Illustrative article excerpt',12,'muted')
    tx,ax,aw=160,418,720
    s.text(tx,397,'ON THIS PAGE',10,'muted',True,spacing='1')
    for i,l in enumerate(['Follow the calculation','Compare the averages','Where this example stops','Explore the assumptions']):s.text(tx,433+i*41,l,12,'ink' if i==0 else 'secondary',i==0)
    y=s.paragraph(ax,396,'A gain of 50% followed by a loss of 50% leaves less than you started with. The second return acts on a different base.',aw,20,'ink',31)
    s.text(ax,y+25,'Follow the calculation',23,'ink',True)
    y=s.paragraph(ax,y+61,'Start with USD 10,000. The first period raises the balance to USD 15,000. Losing half of that balance in the next period leaves USD 7,500. There are no deposits, withdrawals, fees or taxes in this example.',aw,17,'secondary',28)
    s.text(ax,y+14,'Illustrative calculation · currency USD',12,'secondary');table_y=y+32
    s.rect(ax,table_y,aw,38,'raised')
    s.text(ax+14,table_y+25,'Period',12,'secondary',True);s.text(ax+452,table_y+25,'Return',12,'secondary',True,'end');s.text(ax+aw-14,table_y+25,'Balance · USD',12,'secondary',True,'end')
    for i,(period,ret,bal) in enumerate([('Start','Not applicable','10,000'),('Year 1','+50%','15,000'),('Year 2','−50%','7,500')]):
        yy=table_y+38+i*42;s.rect(ax,yy,aw,42,'panel');s.line(ax,yy+42,ax+aw,yy+42);s.text(ax+14,yy+28,period,14,'ink');s.text(ax+452,yy+28,ret,14,'up' if i==1 else 'down' if i==2 else 'muted',False,'end');s.text(ax+aw-14,yy+28,bal,14,'ink',False,'end')
    s.text(ax,table_y+195,'Inspect the calculation →',13,'link')
    y=table_y+246;s.text(ax,y,'Compare the averages',23,'ink',True)
    y=s.paragraph(ax,y+37,'The arithmetic average is 0%. The total return is −25% over two years. The compound annual return is about −13.4% per year. These measures answer different questions, so the period and unit stay beside the number.',aw,17,'secondary',28)
    y+=21;s.text(ax,y,'Where this example stops',23,'ink',True)
    y=s.paragraph(ax,y+37,'Reordering the same returns does not change the final balance when no cash enters or leaves. Contributions and withdrawals change that relationship. A fixed-rate calculator describes assumptions; it does not predict future returns.',aw,17,'secondary',28)
    s.text(ax,y+26,'Explore the assumptions',23,'ink',True)
    s.line(ax,y+52,ax+aw,y+52)
    s.text(ax,y+85,'CAGR calculator ↗',14,'link');s.text(ax+228,y+85,'Compounding calculator ↗',14,'link');s.text(ax+520,y+85,'Back to the desk ↗',14,'link')
    s.line(160,1273,1280,1273)
    s.text(160,1298,'F02 reading slice: anchored TOC, publication date, body, quantitative example, evidence and continuation links stay reachable.',11,'secondary')
    s.text(160,1319,'The existing body language remains English; EN/ZH chrome does not manufacture a translated article or a /zh/ route.',11,'muted')
    s.save(f'editorial-{theme}-1440',['Comfortable English body is a 720px column with 210px TOC and 48px gap.','This is an illustrative excerpt, not a rewrite of the authored production article.','Public chrome may translate; authored body language and canonical URL stay with the existing source owner.'])

def mobile_macro(theme='dark',lang='en'):
    s=Sheet(390,1420,theme,'390px Macro comparison · static composition',lang,raster=lang=='en')
    s.rect(0,0,390,30,'raised');s.text(16,20,'F02 / 390 / STATIC / NOT PAPER',9,'muted')
    s.rect(0,30,390,56,'rail');brand(s,16,65);s.text(374,65,'Example view',10,'muted',False,'end');s.line(0,86,390,86)
    zh=lang=='zh'
    s.text(16,119,'市场 / 参与度' if zh else 'MARKET / PARTICIPATION',10,'accent',True)
    s.text(16,158,'市场广度' if zh else 'Market breadth',26,'ink',True)
    if zh:
        s.text(16,188,'先比较行业参与度，再查看来源。',13,'secondary')
        s.text(16,217,'来源 2026年10月30日 · 20:00 UTC',11,'secondary')
    else:
        s.paragraph(16,187,'Compare participation, then inspect the observation and source.',358,13,'secondary',21)
        s.text(16,241,'Source  30 Oct 2026 · 20:00 UTC',11,'secondary')
    s.button(16,258,'来源详情' if zh else 'Source details',142)
    s.line(16,314,374,314)
    s.text(16,341,'高于50日均线' if zh else 'Above 50-day average',12,'secondary')
    s.text(16,391,'66.7',38,'ink');s.text(111,389,'%',17,'secondary')
    s.text(16,418,'+1.13 pp 较上一交易日' if zh else '+1.13 pp vs prior session',12,'up')
    s.text(16,450,'已覆盖行业' if zh else 'Sectors with data',11,'secondary');s.text(204,450,'持平示例' if zh else 'Unchanged example',11,'secondary')
    s.text(16,485,'9 / 10',25,'ink');s.text(204,485,'0.0 pp',25,'ink')
    s.text(16,511,'1个不可用' if zh else '1 unavailable',11,'muted');s.text(204,511,'已报告零值' if zh else 'Reported zero',11,'muted');s.line(16,536,374,536)
    if not zh:macro_chart(s,16,570,358,True)
    else:
        s.text(16,570,'八个交易日的参与度',15,'ink',True);s.text(16,595,'高于50日均线的比例 · % · 刻度40–80',10,'secondary')
        # All geometry remains language independent. CJK text is intentionally not rasterized.
        px,pw,py,ph=56,296,618,140;vs=[61.8,62.4,None,63.9,63.3,64.6,65.57,66.7];last=None
        for tick in [40,60,80]:yy=py+ph-(tick-40)/40*ph;s.line(px,yy,px+pw,yy);s.text(px-12,yy+4,str(tick),11,'muted',False,'end')
        for i,v in enumerate(vs):
            if v is None:last=None;continue
            p=(px+i*pw/7,py+ph-(v-40)/40*ph)
            if last:s.line(*last,*p,'accent',2.5)
            s.circle(*p,3.5);last=p
        for i,label in [(0,'10/21'),(2,'10/23'),(4,'10/27'),(7,'10/30')]:s.text(px+i*pw/7,py+ph+24,label,10,'muted',False,'middle')
        s.text(px+2*pw/7,py+ph*.66,'缺失',10,'muted',False,'middle')
        s.text(16,811,'8次观测中7次可用 · 不对缺失值插值',11,'secondary')
    s.button(16,843,'查看图表数值' if zh else 'View chart values',170)
    tabs(s,16,899,358,('对比','图表数据') if zh else ('Comparison','Chart data'))
    s.text(16,974,'横向滚动查看各列 →' if zh else 'Scroll the table for all columns →',12,'secondary')
    with s.clip(16,992,358,280):
        s.rect(16,992,650,40,'raised')
        s.text(28,1018,'行业' if zh else 'Sector',11,'secondary',True);s.text(245,1018,'高于50D' if zh else 'Above 50D',11,'secondary',True,'end');s.text(355,1018,'变动 · pp' if zh else 'Change · pp',11,'secondary',True,'end')
        for i,r in enumerate(MACRO[:3]):
            yy=1032+i*80;s.rect(16,yy,650,80,'panel');s.line(16,yy+80,666,yy+80)
            s.text(28,yy+25,r[1] if zh else r[0],12,'ink');s.text(245,yy+25,f'{r[2]:.1f}%',13,'ink',False,'end');s.text(355,yy+25,f'{r[3]:+.2f}',13,'up',False,'end')
            s.button(28,yy+31,'证据' if zh else 'Evidence',106)
    s.text(16,1290,'3 / 10 示例行 · 下方继续' if zh else '3 / 10 example rows · continue below',11,'muted')
    s.line(16,1311,374,1311)
    if zh:
        for i,tx in enumerate(['静态矢量排版；未在浏览器或Paper验证。','点击证据打开覆盖层；关闭后返回触发控件。','字体环境缺少CJK；不提供伪造的栅格证明。']):s.text(16,1336+i*24,tx,10,'muted')
    else:s.paragraph(16,1337,'Static composition. Table overflow stays local; complete-row evidence remains reachable. Important touch controls target 44px. No browser test is implied.',358,11,'muted',19)
    return s

def mobile_inspector():
    s=Sheet(320,1420,'light','320px evidence overlay · static composition')
    s.rect(0,0,320,30,'raised');s.text(16,20,'F02 / 320 / STATIC / NOT PAPER',9,'muted')
    s.rect(0,30,320,56,'panel');s.text(16,65,'Evidence',17,'ink',True)
    s.rect(260,36,44,44,'panel',7,'control');s.rect(257,33,50,50,'none',10,'focus',2);s.text(282,64,'×',22,'ink',False,'middle');s.line(0,86,320,86)
    s.text(20,121,'ILLUSTRATIVE SOURCE',10,'accent',True)
    s.text(20,156,'Operating margin',23,'ink',True)
    s.text(20,188,'EXM · Example Industries',12,'secondary')
    y=220
    for lab,val,col in [('FY 2024','20.0%','ink'),('FY 2025','23.3%','ink'),('FY 2026','24.5%','ink'),('FY26 − FY25','+1.2 pp','up')]:
        s.text(20,y,lab,13,'secondary');s.text(300,y,val,17,col,False,'end');y+=42
    s.line(20,377,300,377)
    fields=[('Source identity','f02.fixture.v1 / company-3'),('Observed basis','Fiscal years 2024, 2025, 2026'),('Publication clock','Illustrative filing record'),('Retrieved','2026-10-30 · 20:03 UTC'),('Unit','Percent; delta in percentage points'),('Currency','Not applicable to this ratio')]
    y=411
    for lab,val in fields:
        s.text(20,y,lab,11,'muted');y=s.paragraph(20,y+25,val,280,13,'ink',21)+26
    s.rect(20,886,280,130,'raised',8)
    s.paragraph(36,912,'Fiscal years are not calendar years. Earlier definitions remain non-comparable where the source says so.',248,13,'secondary',22)
    s.paragraph(20,1053,'Publication, retrieval and observation are separate clocks. A fresh fetch does not make an old filing current.',280,13,'secondary',22)
    s.rect(20,1171,280,44,'panel',7,'control');s.text(160,1199,'Return to comparison',13,'ink',False,'middle')
    s.line(20,1250,300,1250)
    s.paragraph(20,1280,'Static overlay composition. Close and Escape return focus to the source trigger. Underlying scroll and the complete row are retained by contract.',280,11,'muted',20)
    return s

def mobile_comparison():
    a,b=mobile_macro(),mobile_inspector()
    a.save('macro-dark-390',['390px intended content width 358px; local table overflow; evidence action stays in the first column.'],390)
    b.save('company-evidence-light-320',['320px overlay width; body measure 280px; 44px close target and legitimate focus outline.','Exact fiscal observation basis replaces a misleading single market-clock label.'],320)
    # Keep ten raster review files in total: combine the two mobile originals in one plate.
    plate=Sheet(782,1516,'dark','Mobile comparison plate · 390px and 320px static compositions')
    plate.text(24,32,'F02 / MOBILE PATTERNS',14,'ink',True)
    plate.text(24,57,'390px dense comparison',11,'secondary');plate.text(438,57,'320px evidence overlay',11,'secondary')
    for sub,x in [(a,24),(b,438)]:
        plate.im.alpha_composite(sub.im,(x*SCALE,72*SCALE))
        plate.parts.append(f'<g transform="translate({x},72)">'+''.join(sub.parts)+'</g>')
    plate.save('mobile-comparison', ['Original logical frames: macro-dark-390.svg and company-evidence-light-320.svg.','PNG plate is a static composite from two independently drawn vector frames.'],None)
    # Individual mobile PNGs are redundant with the review plate, and intentionally omitted.
    for name in ['macro-dark-390','company-evidence-light-320']:
        (HERE/f'{name}.png').unlink()
        for item in MANIFEST:
            if item['id']==name:item['png']=None;item['raster_in_plate']='mobile-comparison.png'
    zh=mobile_macro('light','zh')
    zh.save('macro-light-zh-390',['Editable SVG text and geometry only; NOT rasterized.','No CJK font is installed in the narrowly inspected local font locations.','Requires qualified native-font visual review and browser/Paper proof.'],390)

def states():
    s=Sheet(1440,1220,'dark','Shared state and semantic distinctions · static specimen matrix')
    artifact_bar(s,'STATE / SEMANTICS / VARIANT MATRIX')
    s.text(28,90,'A state should tell you what happened.',28,'ink',True)
    s.text(28,124,'Separate availability, coverage, freshness, access and save outcome. None of these meanings requires a colored container edge.',14,'secondary')
    entries=[
      ('Loading','Loading observations','The source has not responded. No result count is available.','Loading…','dark'),
      ('Empty','No observations match','Request complete: 0 matching records. Clear the filter to continue.','Clear filter','light'),
      ('Partial','Coverage is incomplete','7 of 8 observations are available. Missing is not zero.','View coverage','dark'),
      ('Stale','Older observations retained','Source 30 Oct, 20:00 UTC. The expected update has not arrived.','Inspect source','light'),
      ('Refresh error','Last good view retained','Refresh failed. Existing observations remain visible with their own date.','Retry refresh','light'),
      ('Unsupported','Source not supported','No value is inferred for this listing. Other supported evidence remains reachable.','View coverage','dark'),
      ('Guest','Reading is available','Sign in to save. Public evidence remains readable here.','Sign in','light'),
      ('Plan required','Source access restricted','Available data stays visible. Restricted payload is not sent to the client.','Check access','dark'),
      ('Expired session','Sign in before saving','The current view is retained. No new change has been sent.','Sign in again','dark'),
      ('First use','Choose a starting view','Open an example to learn the comparison and source-inspection path.','Open example','light'),
      ('Save pending','Saving…','One request is pending. Do not submit a duplicate while it is unresolved.','Saving…','dark'),
      ('Saved','Readback confirmed','The owner confirmed the request and returned the saved object generation.','View saved object','light'),
      ('Save failed','Previous saved view remains','Failure is confirmed. Local edits are retained for an intentional retry.','Retry save','light'),
      ('Save uncertain','Outcome is unknown','Reconcile the existing request before retrying. Do not assert failure.','Check request','dark'),
      ('Corrected','A source revised its value','Show the revision and its retained predecessor. Do not silently rewrite history.','Compare revision','light'),
      ('Success','Refresh completed','The request succeeded. Source freshness and coverage are still independent.','Inspect source','dark')]
    for i,(state,head,copy,action,theme) in enumerate(entries):
        x=28+(i%4)*352;y=160+(i//4)*202;w=328;h=181;old=s.p;s.p=PALETTES[theme]
        s.rect(x,y,w,h,'panel',9,'line');s.text(x+16,y+26,state.upper(),10,'muted',True,spacing='.7')
        s.text(x+16,y+56,head,15,'ink',True);s.paragraph(x+16,y+81,copy,w-32,12,'secondary',18)
        s.button(x+16,y+132,action,small=True,disabled=state in ['Loading','Save pending'])
        s.p=old
    s.line(28,999,1412,999)
    s.text(28,1030,'The same sign does not imply the same meaning.',17,'ink',True)
    sem=[('Price direction','+1.13 pp / −0.80 pp','Signs + comparator period','up'),('Trade side','≈ Buy / ≈ Sell / Mixed','Execution estimate; intent unknown','flow-buy'),('Exposure','Positive / Negative','Signed quantity; domain units','flow-sell'),('Selection / focus','Selected / keyboard focus','Quiet fill / accessible outline','ink')]
    for i,(head,val,note,col) in enumerate(sem):
        x=28+i*352;s.text(x,1062,head,12,'secondary')
        if i==0:
            s.text(x,1092,'+1.13 pp',17,'up',True);s.text(x+105,1092,'/',17,'muted');s.text(x+123,1092,'−0.80 pp',17,'down',True)
        elif i==1:
            s.text(x,1092,'≈ Buy',17,'flow-buy',True);s.text(x+95,1092,'≈ Sell',17,'flow-sell',True);s.text(x+191,1092,'Mixed',17,'secondary',True)
        elif i==2:
            s.text(x,1092,'+ Positive',17,'#4cc6cc',True);s.text(x+139,1092,'− Negative',17,'#d896f0',True)
        else:
            s.rect(x,1070,100,34,'selected',6);s.text(x+50,1092,'Selected',13,'ink',True,'middle');s.button(x+116,1069,'Focus',116,focus=True)
        s.text(x,1118,note,11,'muted')
    s.text(28,1170,'Review matrix only. State boxes are isolated specimens, not a proposed page layout. Colors are supplementary to labels, signs and units.',11,'secondary')
    s.text(28,1194,'All responses and identities here are illustrative. No source access, server mutation, readback, browser interaction or Paper qualification is asserted.',11,'muted')
    s.save('states-and-semantics',['Sixteen distinct state treatments; access/availability/coverage/freshness/mutation are orthogonal.','Colors and neutral borders use the local pattern-lab token candidates.','Corrected and success are diagrammed contract extensions; they are not new backend status enums.'])

def main():
    for theme in ['dark','light']:
        macro_sheet(theme);company_sheet(theme);options_sheet(theme);editorial_sheet(theme)
    mobile_comparison();states()
    document={'artifact_kind':'original_static_design_sheets','generator':'draw_sheets.py','input_pattern_lab_sha256':hashlib.sha256(HTML.encode()).hexdigest(),'fonts':{'raster':'Noto Sans Regular / Bold','svg_english':'Noto Sans, Arial, sans-serif','svg_chinese':'Noto Sans SC, PingFang SC, sans-serif; CJK visual proof pending'},'browser_renderer_used':False,'paper_mutations':0,'frames':MANIFEST}
    (HERE/'manifest.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'frames':len(MANIFEST),'pngs':len(list(HERE.glob('*.png'))),'svgs':len(list(HERE.glob('*.svg'))),'off_canvas':sum(len(x['off_canvas_text']) for x in MANIFEST)},indent=2))

if __name__=='__main__':main()
