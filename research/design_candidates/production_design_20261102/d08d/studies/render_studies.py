"""Render D08D static design studies. No application imports, requests or replay engine.

All numbers and paths drawn as market content are illustrative. Geometry consumes
F01 candidate.4; the output is supporting evidence, not an editable Paper reference.
"""
from pathlib import Path
import html, json, math

ROOT = Path(__file__).resolve().parent
ROOT.mkdir(parents=True, exist_ok=True)
DARK = dict(bg='#080808',nav='#0c0c0c',panel='#121212',raised='#191919',selected='#292929',ink='#f3f3f3',muted='#b8b8b8',sub='#949494',line='#343434',boundary='#6f6f6f',accent='#c9b99b',buy='#70cbdc',sell='#d9a6ef',up='#b0d4b9',down='#efa6ad',warn='#e9be6a',link='#a7c9f1',focus='#c4d9f4')
LIGHT = dict(bg='#f6f6f3',nav='#efefec',panel='#ffffff',raised='#f0f0ed',selected='#e2e2dc',ink='#1a1c20',muted='#51555b',sub='#5f6368',line='#cbccc7',boundary='#85877f',accent='#66543b',buy='#18687c',sell='#7c3d9b',up='#256341',down='#a62d43',warn='#82550d',link='#235b8e',focus='#245c91')

class SVG:
    def __init__(self,w,h,light=False):
        self.w,self.h,self.c=w,h,LIGHT if light else DARK
        self.a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><pattern id="gap" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0 8 L8 0" stroke="{self.c["sub"]}" stroke-width="1" opacity=".5"/></pattern></defs>']
        self.rect(0,0,w,h,self.c['bg'])
    def rect(self,x,y,w,h,fill=None,stroke=None,r=0,opacity=None):
        s=f'<rect x="{x}" y="{y}" width="{max(0,w)}" height="{max(0,h)}" rx="{r}" fill="{fill or self.c["panel"]}"'
        if stroke:s+=f' stroke="{stroke}"'
        if opacity is not None:s+=f' opacity="{opacity}"'
        self.a.append(s+'/>')
    def line(self,x1,y1,x2,y2,color=None,width=1,dash=None):
        self.a.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or self.c["line"]}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def text(self,x,y,s,size=14,color=None,weight=400,anchor='start',mono=False):
        family='DejaVu Sans Mono' if mono else 'DejaVu Sans'
        self.a.append(f'<text x="{x}" y="{y}" fill="{color or self.c["ink"]}" font-family="{family}, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(s))}</text>')
    def para(self,x,y,s,w,size=13,color=None,line=20,maxlines=None):
        # Conservative line budgeting; native Paper typography remains a separate gate.
        budget=max(12,int(w/(size*.58)))
        lines=[]; cur=''
        for word in s.split():
            if len(cur)+len(word)+1>budget and cur:lines.append(cur);cur=word
            else:cur=(cur+' '+word).strip()
        if cur:lines.append(cur)
        if maxlines is not None:lines=lines[:maxlines]
        for i,s in enumerate(lines):self.text(x,y+i*line,s,size,color)
        return y+len(lines)*line
    def button(self,x,y,w,label,primary=False,h=44):
        self.rect(x,y,w,h,self.c['ink'] if primary else self.c['raised'],self.c['boundary'] if not primary else None,8)
        self.text(x+w/2,y+h/2+5,label,13,self.c['bg'] if primary else self.c['ink'],600,'middle')
    def pill(self,x,y,label,w=None):
        w=w or len(label)*7+20
        self.rect(x,y,w,26,self.c['selected'],None,13)
        self.text(x+w/2,y+18,label,12,self.c['ink'],500,'middle')
    def path(self,d,stroke,width=2,fill='none',opacity=None):
        self.a.append(f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}"'+(f' opacity="{opacity}"' if opacity is not None else '')+'/>')
    def circle(self,x,y,r,fill,stroke=None):
        self.a.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+'/>')
    def save(self,name):
        p=ROOT/(name+'.svg');p.write_text(''.join(self.a)+'</svg>');return p
    def review(self,name,viewport):
        d=ROOT.parent/'review-input';d.mkdir(exist_ok=True)
        raw=''.join(self.a)+'</svg>'
        raw=raw.replace(f'height="{self.h}" viewBox="0 0 {self.w} {self.h}"',f'height="{viewport}" viewBox="0 0 {self.w} {viewport}"',1)
        target=d/(name+'.svg')
        # A later added study must not be represented as an original critic input.
        if not (d/'first-pass-artifacts.json').exists() and not target.exists():target.write_text(raw)

def shell(s,w,h,section='Replay'):
    c=s.c;nav=224 if w>=1200 else 196 if w>860 else 0;head=64 if w>860 else 56;g=24 if w>=1200 else 20 if w>600 else 16
    if nav:
        s.rect(0,0,nav,h,c['nav']);s.line(nav,0,nav,h)
        s.text(24,36,'MASTERMIND',15,c['ink'],700)
        s.text(24,66,'RESEARCH WORKSPACE',10,c['sub'],600)
        for i,label in enumerate(['Today','Discover','Analysis','Monitor','Research','Portfolio']):
            y=110+i*48;s.text(24,y,label,14,c['muted'])
        s.line(20,398,nav-20,398);s.text(24,430,'MARKETS',10,c['sub'],600)
        for i,label in enumerate(['Market overview','Stocks','Options']):
            y=469+i*46
            if i==2:s.rect(12,y-25,nav-24,40,c['selected'],None,8)
            s.text(24,y,label,13,c['ink'] if i==2 else c['muted'],600 if i==2 else 400)
        s.text(24,h-50,'Sources & coverage',12,c['muted']);s.text(24,h-24,'Workspace settings',12,c['sub'])
    s.rect(nav,0,w-nav,head,c['nav']);s.line(nav,head,w,head)
    if nav:
        s.text(nav+g,38,'Analysis',14,c['ink'],600)
        sw=min(400,w-nav-280);sx=w-sw-110
        s.rect(sx,13,sw,38,c['raised'],c['line'],8);s.text(sx+14,37,'Search instrument or workspace',12,c['sub']);s.text(w-75,37,'EN',12,c['muted'])
    else:
        s.line(18,21,36,21,c['ink']);s.line(18,28,36,28,c['ink']);s.line(18,35,36,35,c['ink']);s.text(52,34,'MASTERMIND',13,c['ink'],700);s.text(w-28,34,'EN',12,c['muted'],'400','end')
    s.text(nav+g,head+28,'Options',13,c['muted']);s.text(nav+g+74,head+28,'/',13,c['sub']);s.text(nav+g+92,head+28,section,13,c['ink'],600);s.line(nav,head+44,w,head+44)
    return nav,g,head+44

def chart(s,x,y,w,h,equity=False,footprint=False,mobile=False):
    c=s.c;s.rect(x,y,w,h,c['panel'],c['line'],10)
    s.text(x+14,y+24,'Observed IEX book' if equity else ('Executed footprint' if footprint else 'Depth & captured price'),13,c['ink'],600)
    if not mobile:s.text(x+w-16,y+24,'Chart data / table',12,c['link'],500,'end')
    if equity:
        s.rect(x+14,y+35,9,9,c['sell']);s.text(x+28,y+44,'Ask book',10,c['muted'])
        s.rect(x+105,y+35,9,9,c['buy']);s.text(x+119,y+44,'Bid book',10,c['muted'])
        s.text(x+14,y+61,'Log intensity · max of displayed books',10,c['sub'])
    elif footprint:
        s.text(x+14,y+44,'Sell | Buy · contracts · 1 min / 1 tick',10,c['muted'])
        s.circle(x+18,y+56,3,c['warn']);s.text(x+28,y+61,'Unknown side · outlined column = selected',10,c['sub'])
    else:
        for j,(col,lab) in enumerate([('#4869cc','<180'),('#4fd3dd','180–259'),('#c2a347','≥260')]):
            xx=x+14+j*(84 if mobile else 104);s.rect(xx,y+35,9,9,col);s.text(xx+14,y+44,lab,10,c['muted'])
        s.text(x+14,y+61,'Mean bid + ask depth · contracts' if mobile else 'Mean bid + ask depth · contracts · hatch = incomplete coverage · dot = selected frame',10,c['sub'])
    left=x+12;right=x+w-(52 if mobile and not equity else 58);top=y+76;bottom=y+h-40;pw=right-left;ph=bottom-top
    for i in range(5):
        yy=top+i*ph/4;s.line(left,yy,right,yy,c['line'])
        lab=f'{182.8-i*.2:.2f}' if equity else f'{6104-i*2:,.0f}'
        s.text(right+6,yy+4,lab,10 if mobile else 11,c['sub'])
    count=60 if equity else (2 if mobile else 7) if footprint else 15
    illustrative_max=max(round(50+1200*(math.sin(n*.43+j*1.31)+1)/2) for n in range(count) for j in range(9))
    cw=pw/count
    for n in range(count):
        xx=left+n*cw
        gap=n in ([17,18] if equity else [7])
        if gap:s.rect(xx,top,cw,ph,'url(#gap)');continue
        if footprint:
            for j in range(7):
                yy=top+17+j*(ph-24)/7
                if j in [2,3,4]:s.rect(xx+2,yy-11,cw-4,20,c['raised'],None,3)
                s.text(xx+cw*.43,yy+3,str((n*31+j*17)%180+20),11,c['sell'],600,'end')
                s.text(xx+cw*.57,yy+3,str((n*23+j*41)%190+25),11,c['buy'],600)
                if j==3:s.circle(xx+cw*.5,yy-8,2.5,c['warn'])
        else:
            for j in range(9):
                v=(math.sin(n*.43+j*1.31)+1)/2
                if v>.25:
                    yy=top+j*ph/9
                    if equity:
                        col=c['buy'] if j>4 else c['sell'];quantity=round(50+1200*v);op=.25+.75*math.log1p(quantity)/math.log1p(illustrative_max)
                    else:
                        quantity=100+v*280;col='#c2a347' if quantity>=260 else '#4fd3dd' if quantity>=180 else '#4869cc';op=.28+v*.48
                    s.rect(xx+.4,yy,cw-.8,ph/9-1,col,None,1,op)
            if not equity:
                center=.60-.25*math.sin(n*.54);yy=top+center*ph;up=n%3!=0
                s.line(xx+cw*.5,yy-22,xx+cw*.5,yy+23,c['up'] if up else c['down'],1.5)
                s.rect(xx+cw*.5-3,yy-10,6,19,c['up'] if up else c['down'],None,1)
    selx=right-cw*.5
    if footprint:s.rect(right-cw+1,top-3,cw-2,ph+6,'none',c['accent'],3)
    else:s.line(selx,top,selx,bottom,c['accent'],1.5,'4 3')
    s.circle(selx,bottom+7,3,c['accent'])
    s.text(left,bottom+25,'#78' if equity else '13:44' if footprint and mobile else '13:30',10,c['sub']);s.text(left+pw/2,bottom+25,'Snapshot order' if equity else 'UTC',10,c['sub'],400,'middle');s.text(right,bottom+25,'#137' if equity else '13:45',10,c['ink'],500,'end')

def annotations(s,y,items,w):
    c=s.c;s.rect(0,y,w,s.h-y,c['raised']);s.line(0,y,w,y,c['line'])
    s.text(20,y+28,'D08D · ILLUSTRATIVE DESIGN STUDY',11,c['ink'],700)
    s.text(20,y+48,'No market-data or production-proof claim.',11,c['sub'])
    if w>800:
        col=(w-48)/len(items)
        for i,(title,copy) in enumerate(items):
            xx=20+i*col;s.text(xx,y+78,f'{i+1:02}  {title}',12,c['ink'],600);s.para(xx,y+100,copy,col-20,12,c['muted'],18)
    else:
        yy=y+74
        for i,(title,copy) in enumerate(items):
            s.text(20,yy,f'{i+1:02}  {title}',12,c['ink'],600);yy=s.para(20,yy+20,copy,w-40,12,c['muted'],18)+12

def evidence(s,x,y,w,h,equity=False):
    c=s.c;s.rect(x,y,w,h,c['panel'],c['line'],10)
    s.text(x+20,y+30,'Observation evidence',17,c['ink'],600)
    s.text(x+20,y+55,'Historical · selected observation',12,c['sub'])
    s.line(x+20,y+72,x+w-20,y+72)
    fields=[('Instrument','NVDA · IEX · shares' if equity else 'ESZ6 · ES / SPX · contracts'),('Market time','13:45:00.123456789 UTC' if equity else '13:45:00 UTC'),('Market date / source session','2026-10-12'),('Selection','137 / 480 retained samples' if equity else 'Requested 13:45:30 UTC'),('Coverage','Partial capture · discrete books' if equity else 'Partial captured window'),('Availability','Archive acquired 13 Oct 2026' if equity else 'Loaded 13:30–13:45 UTC')]
    yy=y+100
    for k,v in fields:s.text(x+20,yy,k,11,c['sub']);s.text(x+20,yy+22,v,12,c['ink'],500);yy+=49
    s.line(x+20,yy-8,x+w-20,yy-8)
    yy=s.para(x+20,yy+17,'Acquired later. This archive does not establish what was known at market time.' if equity else 'Gamma unavailable for this frame. Valid futures observations remain visible.',w-40,12,c['muted'],18)
    s.button(x+20,yy+10,w-40,'Exact source fields  ↓')
    s.text(x+20,y+h-24,'View only · no save has occurred',11,c['sub'])

def desktop(name,equity=False,light=False,w=1440,footprint=False,modal=False):
    vh=900;ann=200;s=SVG(w,vh+ann,light);c=s.c;nav,g,top=shell(s,w,vh)
    x=nav+g;usable=w-nav-2*g;dock=usable>=984 and not modal;pw=usable-344 if dock else usable
    s.text(x,top+30,'← NVDA chart · 5 min · 12 Oct selection' if equity else '← Options · SPX · 0DTE · selected view',13,c['link'],500)
    s.text(x,top+75,'Equity replay' if equity else 'Futures replay',28,c['ink'],600)
    s.pill(x+(235 if equity else 250),top+54,'Historical')
    s.text(x,top+103,'NVDA · IEX only · shares · partial archive' if equity else 'ESZ6 · ES / SPX · contracts · source session 2026-10-12',13,c['muted'])
    s.text(w-g,top+75,'ILLUSTRATIVE DATA',10,c['sub'],500,'end')
    ty=top+126
    labels=[('NVDA  ▾' if equity else 'ES / SPX  ▾',116),('Depth',100),('Executions' if equity else 'Footprint',118),('Display & layers  ▾',160),('Refresh source',140)]
    xx=x
    for lab,bw in labels:
        s.button(xx,ty,bw,lab,primary=(lab=='Depth' and not footprint) or (lab=='Footprint' and footprint));xx+=bw+8
    if not dock:s.button(x+usable-108,ty,108,'Evidence')
    cy=ty+64;s.rect(x,cy,pw,119,c['panel'],c['line'],10)
    s.text(x+16,cy+25,'OBSERVATION 137 / 480' if equity else 'SELECTED PUBLISHED FRAME',11,c['sub'],600)
    s.text(x+16,cy+50,'2026-10-12 · 13:45:00.123456789 UTC' if equity else '2026-10-12 · 13:45:00 UTC',18,c['ink'],600)
    s.text(x+16,cy+73,'Archive acquired 13 Oct 2026 · later-acquired record' if equity else 'Requested 13:45:30 UTC · selected at or before request',12,c['muted'])
    s.text(x+16,cy+100,'Latest retained  →' if equity else 'Loaded 13:30–13:45 UTC',11,c['link'] if equity else c['sub'])
    pickw=156;s.button(x+pw-pickw-124,cy+64,44,'←');s.button(x+pw-pickw-72,cy+64,pickw,'Choose observation' if equity else 'Choose frame');s.button(x+pw-64,cy+64,44,'→')
    my=cy+135;metrics=[('Observed bid shares','24,100'),('Observed ask shares','19,800'),('Executions through selection','58,720')] if equity else [('Captured contracts','12,940'),('Known-side delta','+842'),('Unknown-side contracts','318')]
    for i,(label,val) in enumerate(metrics):
        mx=x+i*pw/3;s.text(mx+2,my+14,label,11,c['sub']);s.text(mx+2,my+45,val,26,c['ink'],500)
    py=my+65;chart(s,x,py,pw,255,equity,footprint)
    fy=py+274
    if equity:
        s.rect(x,fy,pw,70,c['panel'],c['line'],10);s.text(x+16,fy+24,'60 shown from selected prefix · hatch = gap · dashed marker = selection',12,c['muted'])
        s.text(x+16,fy+47,'Captured executions: 2,140 unknown-side shares; corrections may be incomplete.',12,c['sub'])
    else:
        s.rect(x,fy,pw,70,c['panel'],c['line'],10);s.text(x+16,fy+23,'Known-side CVD',12,c['muted'])
        pts=[(x+150+i*(pw-220)/14,fy+45-18*math.sin(i*.4)) for i in range(15)]
        s.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a,b in pts),c['accent'],1.5)
        s.text(x+pw-18,fy+28,'+842',13,c['ink'],500,'end');s.text(x+16,fy+55,'Full CVD —',11,c['sub'])
    s.text(x,vh-36,'Price window: near observed top ±1% · totals keep all observed orders' if equity else '1-minute intervals · 1 tick / row · GEX withheld · CVD on · Weekly positioning  ↓',12,c['muted'])
    s.text(x,vh-15,'Historical observations · exact source and coverage remain available in Evidence',11,c['sub'])
    if dock:evidence(s,x+pw+24,cy,320,vh-cy-62,equity)
    if modal:
        s.rect(nav,64,w-nav,vh-64,'#000000',None,0,.4)
        mw=440;mx=w-mw;my=64;s.rect(mx,my,mw,vh-my,c['panel']);s.line(mx,my,mx,vh,c['line'])
        s.text(mx+24,my+38,'Observation evidence',21,c['ink'],600);s.button(w-70,my+14,46,'×')
        s.text(mx+24,my+69,'NVDA · IEX · historical archive',13,c['muted']);s.line(mx+24,my+90,w-24,my+90)
        entries=[('Selected market observation','12 Oct 2026 · 13:45:00.123456789 UTC'),('Position / retained coverage','137 of 480 · partial, discrete books'),('Observed resting shares','Bid 24,100 · Ask 19,800'),('Executions through selection','58,720 shares · 2,140 unknown side'),('Correction qualification','Net of observed breaks; completeness unknown'),('Archive acquired','13 Oct 2026 · 08:12:00 UTC'),('Retained depth','32 levels per side · further levels omitted')]
        yy=my+125
        for k,v in entries:s.text(mx+24,yy,k,12,c['sub']);s.text(mx+24,yy+23,v,12,c['ink'],500);yy+=60
        s.para(mx+24,yy,'Later acquisition does not establish what was known at market time.',mw-48,13,c['muted'],20)
        s.button(mx+24,yy+55,mw-48,'Exact artifact / source / sequence  ↓')
        s.button(mx+24,vh-132,mw-48,'Back to replay',primary=True)
        s.button(mx+24,vh-76,mw-48,'Return to NVDA chart · 5 min')
    s.review(name,vh)
    annotations(s,vh,[('Identity & time','Historical scope stays next to the instrument and selection. No live label.'),('Native selection','Futures cutoff and IEX sample identity remain different. No shared clock conversion.'),('One evidence surface','320px dock only when primary content remains ≥640px; 440px modal at 1024.'),('Preserved depth','Advanced display, source, gaps, execution accounting and exact return remain reachable.')],w)
    s.save(name)

def mobile(name,equity=False,light=False,w=390):
    vh=844;ann=490;s=SVG(w,vh+ann,light);c=s.c;nav,g,top=shell(s,w,vh);x=g;cw=w-2*g
    s.rect(x,top+2,cw,44,'none',None,4)  # quiet 44px return interaction row
    s.text(x,top+22,'← NVDA chart · 5 min · 12 Oct selection' if equity else '← Options · SPX · selected 0DTE view',11,c['link'],500)
    s.text(x,top+54,'Equity replay' if equity else 'Futures replay',22,c['ink'],600)
    s.pill(w-g-86,top+36,'Historical',86)
    s.text(x,top+78,'NVDA · IEX · shares · partial archive' if equity else 'ESZ6 · ES / SPX · contracts',12,c['muted'])
    by=top+90;s.button(x,by,(cw-8)/2,'NVDA  ▾' if equity else 'ES / SPX  ▾');s.button(x+(cw+8)/2,by,(cw-8)/2,'Layers & data  ▾')
    cy=by+56;s.rect(x,cy,cw,128,c['panel'],c['line'],10)
    s.text(x+12,cy+19,'137 / 480 · 12 OCT 2026' if equity else 'SELECTED · 12 OCT 2026',10,c['sub'],600)
    s.text(x+12,cy+42,'13:45:00.123456789 UTC' if equity else '13:45:00 UTC',15,c['ink'],600)
    s.text(x+12,cy+62,'Archive acquired 13 Oct · later record' if equity else 'Requested 13:45:30 UTC · 1 min / 1 tick',10,c['muted'])
    s.button(x+12,cy+72,44,'←');s.button(x+64,cy+72,cw-128,'Choose observation' if equity else 'Choose frame');s.button(x+cw-56,cy+72,44,'→')
    ty=cy+140;bw=(cw-16)/3
    for i,label in enumerate(['Depth','Executions' if equity else 'Footprint','Evidence']):s.button(x+i*(bw+8),ty,bw,label,primary=i==0)
    my=ty+64
    metrics=[('Obs. bid shares','24,100'),('Obs. ask shares','19,800'),('Captured exec.','58,720')] if equity else [('Captured ctr.','12,940'),('Known-side Δ','+842'),('Unknown side','318')]
    for i,(lab,val) in enumerate(metrics):s.text(x+i*cw/3,my,lab,10,c['sub']);s.text(x+i*cw/3,my+24,val,20 if w>=390 else 18,c['ink'],500)
    s.text(x,my+41,'Through selection · unknown side 2,140 shares' if equity else 'Loaded-window totals · known CVD +842 · full —',10,c['muted'])
    py=my+54;chart(s,x,py,cw,310,equity,False,True)
    s.text(x,py+327,'±1% view · gap hatch · selection dot · Chart data →' if equity else 'Gap hatch · selection dot · GEX — · Chart data →',10,c['link'])
    s.review(name,vh)
    annotations(s,vh,[('Chart prominence','The 310px chart card contains a 194px plot. Full year, request and quantity scope remain above it.'),('Touch & keyboard','44px controls. Choose observation is a non-drag path; arrows step native samples. Chart data is also in Layers & data.'),('Advanced tools','Layers & data retains interval, rows, expiry, mapping, zoom, CVD and weekly positioning. See the opened sheet study.'),('Exact return','Named source selection is retained. Static views illustrate the contract; restored state still needs real browser proof.')],w)
    s.save(name)

def mobile_evidence():
    w=390;vh=844;s=SVG(w,1220,True);c=s.c
    s.rect(0,0,w,vh,c['panel']);s.text(20,38,'Observation evidence',21,c['ink'],600);s.button(326,14,44,'×')
    s.text(20,76,'NVDA · IEX · Historical',13,c['muted']);s.line(20,98,370,98)
    s.text(20,132,'13:45:00.123456789 UTC',19,c['ink'],600);s.text(20,158,'12 October 2026 · sample 137 of 480',13,c['muted'])
    s.rect(20,180,350,82,c['raised'],None,10);s.text(36,207,'Partial captured window',14,c['ink'],600);s.para(36,230,'Acquired later; does not establish what was known at market time.',318,12,c['muted'],18)
    fields=[('Observed resting shares','Bid 24,100 · Ask 19,800'),('Captured executions through selection','58,720 shares · unknown side 2,140'),('Retained depth levels','32 per side · further levels omitted'),('Archive acquired','13 Oct 2026 · 08:12:00 UTC'),('Correction qualification','Observed breaks applied; completeness unknown')]
    yy=290
    for k,v in fields:s.text(20,yy,k,12,c['sub']);s.text(20,yy+24,v,12,c['ink'],500);yy+=60
    s.button(20,610,350,'Exact artifact / source / sequence  ↓')
    s.text(20,685,'View only · no save has occurred',12,c['sub']);s.button(20,704,350,'Back to replay',primary=True);s.button(20,760,350,'Return to NVDA chart · 5 min')
    s.review('equity-evidence-390-light-en',vh)
    annotations(s,vh,[('One modal owner','Full-width sheet at ≤600px. Background inert; close returns to Evidence trigger.'),('Preserve identity','Native sequence, session, exact timestamp and artifact position stay attached to the selected observation.'),('No false save','Evidence inspection is read-only. D23 save appears only after its receipt/readback contract is admitted.')],w);s.save('equity-evidence-390-light-en')

def states():
    w=1440;vh=1372;s=SVG(w,1592,True);c=s.c
    s.text(32,48,'Replay states',30,c['ink'],600);s.text(32,78,'Illustrative access and recovery views · retain the requested instrument and observation',14,c['muted'])
    cards=[('01 · Guest','Sign in to open historical replay.','Sign in','Your selected observation will be kept.'),('02 · Plan required','Your current plan does not include this replay view.','View plans','A plan change does not guarantee this archive.'),('03 · Access unverified','Replay access could not be confirmed. Check your session and try again.','Check access','Protected values are not displayed.'),('04 · Distribution withheld','This source is not cleared for subscriber display.','Source details','Changing plan cannot clear this source restriction.'),('05 · Missing publication','No replay archive has been published for NVDA here.','Refresh source','No replacement market data is shown.'),('06 · Missing window','No retained observation covers this selection.','Choose observation','Available: 13:30–13:40 UTC in this example.'),('07 · Loading','Reading the published archive…','Reading…','Your request is kept while the source loads.'),('08 · Book gap','Order-chain coverage is incomplete. The book is withheld.','View evidence','Observed bid — · ask — · no inferred book'),('09 · Return fallback','Your NVDA 5-minute chart selection could not be restored.','Open Options','You can still inspect this replay.'),('10 · Unsupported dataset','This listing is not supported by the selected replay dataset.','Choose instrument','600519.SS · no proxy instrument substituted'),('11 · Load failed','Replay could not load. Your selection is kept.','Retry','Check the source again for this same selection.'),('12 · Latest source stale','The latest source is out of date. Current market values are withheld.','Refresh source','Source 12 Oct 13:45 UTC · checked 13:46 UTC')]
    cw=(w-96)/3;ch=292
    for i,(head,copy,act,detail) in enumerate(cards):
        x=32+(i%3)*(cw+16);y=108+(i//3)*(ch+18);s.rect(x,y,cw,ch,c['panel'],c['line'],12)
        s.text(x+20,y+30,head,17,c['ink'],600)
        s.text(x+20,y+57,'ESZ6 · ES / SPX · latest request' if i==11 else '600519.SS · requested listing' if i==9 else 'NVDA · IEX · 12 Oct 2026',12,c['ink'],500)
        s.text(x+20,y+80,'Fresh until 12 Oct 2026 13:45:05 UTC' if i==11 else 'Requested 13:45:00 UTC · historical',11,c['sub'])
        s.para(x+20,y+113,copy,cw-40,14,c['muted'],21)
        s.para(x+20,y+188,detail,cw-40,11,c['sub'],17)
        if act=='Reading…':s.text(x+20,y+254,act,13,c['sub'])
        else:s.button(x+20,y+227,min(190,cw-150),act)
        s.text(x+cw-20,y+254,'Back to replay' if i==8 else 'Options',12,c['link'],500,'end')
    s.review('state-atlas-1440-light-en',vh)
    annotations(s,vh,[('Source-established copy','Guest, plan, unverified access, missing data and distribution are distinct only when established.'),('No historical substitution','Missing windows and gaps never become synthetic prices, zero books or the next available observation.'),('Safe recovery','Retry remains scoped to the original selection; unknown save effects reconcile with their owner.')],w);s.save('state-atlas-1440-light-en')

def field(s,x,y,w,label,value):
    s.text(x,y,label,12,s.c['sub']);s.rect(x,y+12,w,44,s.c['raised'],s.c['boundary'],8)
    s.text(x+12,y+40,value,13,s.c['ink'],500);s.text(x+w-12,y+40,'▾',13,s.c['sub'],400,'end')

def advanced():
    w=1440;vh=1336;s=SVG(w,vh+220,False);c=s.c
    s.text(32,48,'Advanced replay · opened states',28,c['ink'],600)
    s.text(32,78,'Illustrative retained capabilities · controls stage changes until Apply',14,c['muted'])
    x=32;y=110;cw=436;s.rect(x,y,cw,670,c['panel'],c['line'],12)
    s.text(x+24,y+38,'Futures · Display & layers',21,c['ink'],600);s.text(x+24,y+65,'ESZ6 · ES / SPX · 12 Oct 2026',12,c['muted'])
    for j,(lab,val) in enumerate([('Completed interval','1 minute  /  5 minutes'),('Price rows','1 tick  /  4 ticks  /  8 ticks'),('Expiry lens · includes a source-date choice','All  /  Source-session 0DTE  /  Ex-0DTE'),('Mapping','Ratio  /  Basis'),('Price zoom','1×  /  2×')]):field(s,x+24,y+98+j*83,cw-48,lab,val)
    s.text(x+24,y+535,'✓ Mapped index GEX    ✓ Known-side CVD',13,c['ink'],500)
    s.text(x+24,y+563,'POC and all-expiry key levels remain reachable.',12,c['muted'])
    s.button(x+24,y+594,176,'Cancel');s.button(x+212,y+594,200,'Apply',primary=True)
    x=492;cw=916;s.rect(x,y,cw,346,c['panel'],c['line'],12)
    s.text(x+24,y+38,'Exposure layer · available-state specimen',20,c['ink'],600)
    s.text(x+24,y+65,'SPX exposure mapped to ESZ6 · ratio mapping · selected expiry: all',13,c['muted'])
    s.text(x+24,y+91,'USD millions per 1% index move · estimate, not native futures gamma',12,c['sub'])
    for j,(price,label,val) in enumerate([('6,102.00','Call wall · all expiries',8.4),('6,100.25','POC · captured window',None),('6,099.25','Gamma flip · all expiries',-3.1),('6,096.50','Put wall · all expiries',-6.2)]):
        yy=y+130+j*43;s.text(x+24,yy,price,13,c['ink'],500);s.text(x+130,yy,label,13,c['muted'])
        if val is not None:s.rect(x+480,yy-14,abs(val)*26,16,c['buy'] if val>0 else c['sell'],None,3,.75);s.text(x+750,yy,f'{val:+.1f}M',13,c['ink'],500)
        else:s.text(x+480,yy,'Observed volume peak; lower-price tie rule',12,c['sub'])
    s.text(x+24,y+321,'Source values stay unchanged as visible-range symbol size changes. Labels use a separate gutter.',12,c['sub'])
    yy=480;s.rect(x,yy,cw,300,c['panel'],c['line'],12);s.text(x+24,yy+38,'Weekly positioning · outside replay',20,c['ink'],600)
    s.text(x+24,yy+65,'CFTC TFF · futures only · ES code 13874A',13,c['muted']);s.text(x+24,yy+91,'Report date 6 Oct 2026 · retrieved 9 Oct 2026 · illustrative report',12,c['sub'])
    for j,(lab,longs,shorts,change) in enumerate([('Dealer / intermediary','120,000','144,000','−3,200'),('Asset manager','240,000','82,000','+5,400'),('Leveraged funds','95,000','171,000','—'),('Other reportables','41,000','28,000','+900')]):
        ry=yy+132+j*34;s.text(x+24,ry,lab,13,c['ink']);s.text(x+350,ry,longs+' long',12,c['muted']);s.text(x+500,ry,shorts+' short',12,c['muted']);s.text(x+685,ry,'Δ '+change,12,c['muted'])
    s.text(x+24,yy+277,'OI 612,000 · Δ net position vs prior report · unavailable — · outside replay',12,c['sub'])
    yy=812;s.rect(32,yy,1376,480,c['panel'],c['line'],12);s.text(56,yy+38,'Equity · display controls and captured executions',21,c['ink'],600)
    field(s,56,yy+76,352,'Price window','Near observed top ±1%  /  All retained')
    s.text(56,yy+160,'The price window changes the picture only.',13,c['muted']);s.para(56,yy+185,'Resting share totals retain all observed orders. The depth chart uses up to the last 60 selected-prefix samples. Sample count and ordinal bounds remain visible.',352,13,c['sub'],21)
    s.button(56,yy+290,352,'Chart data / accessible table')
    s.button(56,yy+350,164,'Cancel');s.button(232,yy+350,176,'Apply',primary=True)
    tx=448;tw=932;s.text(tx,yy+80,'NVDA · IEX · sample 137 / 480 · 12 Oct 2026 13:45:00.123456789 UTC',13,c['ink'],500)
    s.text(tx,yy+110,'Net of observed trade breaks through this sequence · correction completeness unknown',12,c['muted'])
    cols=[('Price',0),('Sell shares',210),('Buy shares',400),('Unknown shares',590)]
    for label,dx in cols:s.text(tx+dx,yy+153,label,12,c['sub'])
    for j,(p,sell,buy,unk) in enumerate([('182.4000','3,420','4,180','240'),('182.4100','2,100','5,600','150'),('182.4200','3,800','3,050','820'),('182.4300','2,740','4,620','310'),('182.4400','4,100','2,900','620')]):
        ry=yy+192+j*40;s.line(tx,ry+14,tx+tw,ry+14)
        for value,dx in zip([p,sell,buy,unk],[0,210,400,590]):s.text(tx+dx,ry,value,14,c['ink'],500)
    s.text(tx,yy+414,'Example rows shown · total 58,720 captured shares · unknown side 2,140',13,c['ink'],500)
    s.text(tx,yy+442,'First 64 price rows if capped; totals include every captured execution through selection.',12,c['sub'])
    annotations(s,vh,[('Preserved controls','Closed query choices stay closed. No freeform speed, archive date fetch or automatic playback.'),('Separate time bases','Weekly CFTC report and retrieval dates never inherit the intraday replay clock.'),('Accounting','Execution rows reuse native correction rules. Unknown side remains a quantity, not a forced classification.'),('Review limits','Values are illustrative and no source receipt is implied. Native Paper and browser behavior remain required.')],w);s.save('advanced-replay-1440-dark-en')

def mobile_controls():
    w=390;vh=1060;s=SVG(w,vh+340,False);c=s.c
    s.rect(0,0,w,vh,c['panel']);s.text(20,38,'Layers & data',22,c['ink'],600);s.button(326,14,44,'×')
    s.text(20,80,'ESZ6 · ES / SPX · Historical',13,c['muted']);s.text(20,104,'12 Oct 2026 · selected 13:45:00 UTC',12,c['sub'])
    for j,(lab,val) in enumerate([('Completed interval','1 minute'),('Price rows','1 tick'),('Expiry lens','All expiries'),('Mapping','Ratio'),('Price zoom','1×')]):field(s,20,150+j*84,350,lab,val)
    s.text(20,590,'✓ Known-side CVD',14,c['ink'],500);s.text(20,618,'Full CVD is unavailable while side is unknown.',12,c['muted'])
    s.text(20,654,'GEX layer · withheld for this frame',14,c['muted']);s.para(20,681,'Captured futures remain visible. Evidence explains the exposure source qualification.',350,12,c['sub'],19)
    s.button(20,738,350,'Chart data / accessible table')
    s.button(20,794,350,'Weekly positioning · separate report')
    s.text(20,876,'Changes remain local until Apply.',13,c['muted']);s.para(20,901,'Cancel restores the active view. Applying query controls preserves the originating selection.',350,12,c['sub'],20)
    s.button(20,984,160,'Cancel');s.button(192,984,178,'Apply',primary=True)
    annotations(s,vh,[('Scroll and actions','Controls sheet owns its vertical scroll. Apply/Cancel remain reachable above the safe-area inset.'),('No feature removal','Every existing interval, row, expiry, mapping, zoom, CVD and exposure control retains a named destination.'),('Proof due','This is a tall content capture, not an assertion that 1,060 CSS px fit an 844px viewport.')],w);s.save('futures-controls-390-dark-en')

def futures_mobile_evidence():
    w=390;vh=1000;s=SVG(w,vh+320,False);c=s.c;s.rect(0,0,w,vh,c['panel'])
    s.text(20,38,'Observation evidence',21,c['ink'],600);s.button(326,14,44,'×');s.text(20,80,'ESZ6 · ES / SPX · contracts',13,c['muted'])
    s.text(20,124,'12 Oct 2026 · 13:45:00 UTC',18,c['ink'],600);s.text(20,152,'Requested 13:45:30 UTC · Historical',12,c['sub'])
    fields=[('Source trading session','2026-10-12 · source session zone unavailable'),('Loaded observation window','13:30–13:45 UTC · partial capture'),('Published frame availability','13:30, 13:35, 13:40, 13:45 UTC'),('Quantity and coverage','12,940 captured contracts · unknown side 318'),('Known-side CVD / full CVD','+842 through loaded window / —'),('Source observation / publication','13:45:00 UTC / 13:45:02 UTC'),('Fresh until (source value)','13:45:05 UTC · does not change selected time'),('GEX qualification','Withheld · captured futures remain available')]
    yy=206
    for k,v in fields:s.text(20,yy,k,12,c['sub']);s.para(20,yy+24,v,350,12,c['ink'],18);yy+=70
    s.button(20,786,350,'Exact source / definition / digest  ↓');s.text(20,862,'View only · no save has occurred',12,c['sub'])
    s.button(20,888,350,'Back to replay',primary=True);s.button(20,944,350,'Return to Options · selected SPX view')
    annotations(s,vh,[('Three windows','Request, available publication cutoffs and loaded observation window remain distinct.'),('Market clocks','No exchange timezone is invented from the session date. UTC is an explicit display fallback until qualified.'),('Independent freshness','Publication/freshness qualify the source. They do not relabel the selected historical observation as live.')],w);s.save('futures-evidence-390-dark-en')

def source_detail():
    w=1024;vh=1130;s=SVG(w,vh+230,True);c=s.c
    s.text(32,48,'Exact source · selected IEX observation',25,c['ink'],600);s.text(32,78,'Illustrative identity specimen · these example identifiers are not a market receipt',13,c['muted'])
    s.rect(32,106,960,960,c['panel'],c['line'],12);x=56
    from datetime import datetime, timezone
    ns=str(int(datetime(2026,10,12,13,45,tzinfo=timezone.utc).timestamp())*10**9+123456789)
    acquired=str(int(datetime(2026,10,13,8,12,tzinfo=timezone.utc).timestamp())*10**9)
    fields=[('Instrument / venue / units','NVDA · IEX · shares · priceInt scale 10000'),('Selected artifact ordinal','137 of 480 retained samples · source-native fields cross-checked'),('Market timestamp (decimal nanoseconds)',ns),('Archive acquired / available time (decimal nanoseconds)',acquired),('Native source session','20261012.8004.00000001.0000002a'),('Native source sequence','982341'),('Artifact SHA-256 · illustrative example only','0123456789abcdef'*4),('Underlying archive source SHA-256 · different identity','fedcba9876543210'*4),('Capture and book limits','Partial capture · 32 retained levels/side · earlier snapshots omitted'),('Correction qualification','Observed trade breaks applied through this sequence; complete correction history unknown')]
    yy=140
    for lab,val in fields:
        s.text(x,yy,lab,12,c['sub']);s.text(x,yy+26,val,13,c['ink'],500,mono='SHA-256' in lab or 'nanoseconds' in lab);yy+=70
    s.para(x,yy+5,'A later archive acquisition does not establish what was known at market time. Artifact identity, native session/sequence and ordinal travel together; timestamp alone is not an exact reconstruction key.',900,14,c['muted'],22)
    s.text(x,yy+89,'Observed-break example: 100 captured shares removed from the selected-prefix execution total.',13,c['ink'],500)
    s.text(x,yy+117,'An unmatched break remains a qualification; it does not invent a missing execution or zero book.',12,c['sub'])
    s.button(56,1000,440,'Back to observation evidence',primary=True);s.button(512,1000,456,'Return to NVDA chart · 5 min')
    annotations(s,vh,[('Identity','Full example digests remain visible. A production view must display the actual admitted response identity and served time.'),('No invented certainty','Complete correction coverage is unknown unless the existing source explicitly proves it.'),('Exact reconstruction','Changed artifact or missing native cross-check gives an honest unavailable state; never silently remap to a nearby sample.')],w);s.save('equity-source-1024-light-en')

def journey():
    w=1440;vh=1210;s=SVG(w,vh+220,True);c=s.c
    s.text(32,48,'From research context to evidence — and back',28,c['ink'],600)
    s.text(32,78,'Interaction study · matched state is specified here; actual restoration still requires browser proof',14,c['muted'])
    for n,(title,rows) in enumerate([
        ('Origin · NVDA chart',[('Instrument','NVDA · original listing retained'),('Chart view','5-minute bars · 12 Oct 2026'),('Selected observation','13:45:00 UTC'),('Research context','Original filters, scroll and focused trigger'),('Action','Open equity replay')]),
        ('Replay · chosen observation',[('Dataset','IEX equity shares · historical'),('Selection','137 / 480 · 13:45:00.123456789 UTC'),('Acquisition','13 Oct 2026 · later-acquired record'),('Evidence','Source, coverage, quantities and corrections'),('Action','Return to NVDA chart · 5 min')]),
        ('Restored origin · expected state',[('Instrument','Same NVDA listing'),('Chart view','Same 5-minute bars · 12 Oct 2026'),('Selected observation','Same 13:45:00 UTC selection'),('Research context','Same validated filters, scroll and focus'),('Fallback','Named Options destination if unavailable')])]):
        x=32+n*464;y=110;cw=448;s.rect(x,y,cw,420,c['panel'],c['line'],12);s.text(x+20,y+36,title,18,c['ink'],600)
        for j,(lab,val) in enumerate(rows):s.text(x+20,y+80+j*62,lab,11,c['sub']);s.para(x+20,y+103+j*62,val,cw-40,13,c['ink'],18)
    x=32;y=558;s.rect(x,y,896,600,c['panel'],c['line'],12);s.text(x+24,y+40,'Choose observation',24,c['ink'],600)
    s.text(x+24,y+71,'NVDA · IEX · source session 20261012.8004.00000001.0000002a',13,c['muted'])
    s.text(x+24,y+99,'480 retained samples · select within this archive; no date archive is fetched',12,c['sub'])
    field(s,x+24,y+134,400,'Observation number','137 of 480');field(s,x+448,y+134,424,'Find within loaded observations','12 Oct 2026 · 13:45:00 UTC')
    s.text(x+24,y+231,'Sample',12,c['sub']);s.text(x+130,y+231,'Market time (UTC)',12,c['sub']);s.text(x+535,y+231,'Coverage',12,c['sub'])
    for j,(num,t,qual) in enumerate([('135','13:44:50.106421780','Observed book'),('136','13:44:55.451221100','Book withheld · source gap'),('137','13:45:00.123456789','Observed · 32 retained levels'),('138','13:45:05.003451900','Observed book')]):
        yy=y+256+j*52
        if num=='137':s.rect(x+16,yy-8,864,48,c['selected'],None,7)
        s.text(x+24,yy+21,num,14,c['ink'],600 if num=='137' else 400);s.text(x+130,yy+21,t,14,c['ink']);s.text(x+535,yy+21,qual,13,c['muted'])
    s.text(x+24,y+489,'A timestamp match lists native samples; it does not choose a later one silently.',12,c['sub'])
    s.button(x+24,y+526,400,'Cancel');s.button(x+448,y+526,424,'Select observation 137',primary=True)
    x=952;cw=456;s.rect(x,y,cw,600,c['panel'],c['line'],12);s.text(x+24,y+40,'After another selection',21,c['ink'],600)
    s.text(x+24,y+82,'Sample 136 / 480',17,c['ink'],600);s.text(x+24,y+111,'12 Oct 2026 · 13:44:55.451221100 UTC',12,c['muted'])
    s.para(x+24,y+154,'The selected book is withheld because the order chain is incomplete. No depth or zero-liquidity inference is drawn.',cw-48,15,c['muted'],24)
    s.text(x+24,y+257,'Observed bid —        Observed ask —',14,c['ink'],500)
    s.para(x+24,y+300,'Captured executions remain independently qualified. Evidence follows sample 136; the original chart context remains unchanged.',cw-48,14,c['muted'],22)
    s.button(x+24,y+420,cw-48,'Evidence for sample 136')
    s.button(x+24,y+478,cw-48,'Return to NVDA chart · 5 min')
    s.text(x+24,y+560,'Back/close restores the chooser trigger.',12,c['sub'])
    annotations(s,vh,[('Origin custody','D06/D08 extend their owned navigation mechanism; framework history fields are preserved.'),('No query expansion','Symbol and futures query grammars stay closed. Return context is validated transient state, never protected payload.'),('Selection','Loaded native observations only. Adjacent, direct-number and table selection share the same committed cursor.'),('Acceptance due','A matched real entry/evidence/return capture is required. This diagram is not an executed journey.')],w);s.save('journey-chooser-return-1440-light-en')

desktop('futures-1440-dark-en')
desktop('futures-footprint-1440-light-en',light=True,footprint=True)
desktop('equity-1440-dark-en',equity=True)
desktop('equity-evidence-1024-light-en',equity=True,light=True,w=1024,modal=True)
mobile('futures-390-dark-en')
mobile('equity-390-light-en',equity=True,light=True)
mobile('futures-320-dark-en',w=320)
mobile_evidence();states()
advanced();mobile_controls();futures_mobile_evidence();source_detail();journey()

names=[p.stem for p in sorted(ROOT.glob('*.svg'))]
gallery='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>D08D Replay — supporting design studies</title><style>body{margin:0;background:#f6f6f3;color:#1a1c20;font:16px/1.6 system-ui,sans-serif}header,main{max-width:1500px;margin:auto;padding:32px}h1{font-size:32px;line-height:1.2}p{max-width:85ch}article{margin:32px 0;padding:24px;background:white;border:1px solid #cbccc7;border-radius:12px}img{max-width:100%;height:auto;display:block}a{color:#235b8e}code{overflow-wrap:anywhere}h2{font-size:20px}footer{padding:32px} @media(max-width:600px){header,main{padding:16px}article{padding:12px}}</style><header><h1>D08D · Futures & equity replay</h1><p>Supporting static design studies. All market numbers are illustrative. These are source diagrams, not Paper compositions, implemented controls, measured usability or production proof. The full contract and gates are in the adjacent Markdown package.</p><p>中文：这些是辅助静态设计研究，所有行情数值均为示意。它们不代表 Paper 定稿、可运行产品、可用历史数据或生产验收。完整交互、状态与中文文案见规格文件。</p><p><a href="../README.md">Package overview</a> · <a href="../RESPONSIVE_SPEC.md">Responsive and bilingual specification</a></p></header><main>'''
for n in names:gallery+=f'<article><h2>{html.escape(n)}</h2><p><a href="{n}.svg">Vector source</a> · <a href="{n}.png">Full capture</a></p><img src="{n}.png" alt="D08D {html.escape(n)} illustrative supporting composition with annotations"></article>'
gallery+='</main><footer>Paper file/page/artboard IDs: not created. Native composition, foundation release and formal review remain gates.</footer></html>'
(ROOT/'index.html').write_text(gallery)
(ROOT/'study-manifest.json').write_text(json.dumps({'kind':'supporting static studies; not Paper or product proof','data':'illustrative only','renderer':'SVG; PNG rendered with local sharp/librsvg','font':'DejaVu Sans fallback for study captures; final Paper uses qualified F02 font stack','locale':'EN raster studies; ZH copy and construction specified, native glyph/layout proof outstanding','files':names},indent=2)+'\n')
print(json.dumps({'studies':len(names),'names':names}))
