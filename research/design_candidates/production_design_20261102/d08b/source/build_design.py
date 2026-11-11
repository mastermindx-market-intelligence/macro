"""D08B editable Paper composition payloads; design fixtures, never market output."""
from pathlib import Path
import json, math, html

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'source'
D={'bg':'#0F1115','panel':'#181B21','raised':'#1E222A','text':'#D7DCE3','muted':'#A5ACB8','line':'#3A4150','blue':'#7AA7E0','pos':'#65CCD2','neg':'#D1A1E4','gold':'#E6BE68'}
L={'bg':'#F7F8FA','panel':'#FFFFFF','raised':'#EEF1F6','text':'#1C2430','muted':'#5D6B7E','line':'#C9CCD1','blue':'#2758E6','pos':'#14676E','neg':'#794A91','gold':'#865D13'}
strikes=[775,770,765,760,755,750,745,740,735]
expiries=['2026-11-06','2026-11-13','2026-11-20','2026-11-27','2026-12-04','2026-12-18']
matrix=[[25,18,12,6,4,3],[34,20,13,8,5,4],[65,42,24,16,10,8],[128,57,36,28,20,12],[94,27,15,25,14,12],[268,74,52,61,33,37],[-201,-58,-39,-47,-26,-29],[-121,-37,-27,-33,-19,-18],[-71,-23,-18,-17,-12,-14]]
net=sum(map(sum,matrix))
fixture={'kind':'illustrative_design_fixture','sourceNamespace':'D08B:fixture','securityId':'FIXTURE:US-ARCX-SPY','root':'SPY','spot':752.10,'spotAt':'2026-11-02T16:00:02-05:00','sourceSession':'2026-11-02','oiPositionSession':'2026-10-30','oiReportDate':'2026-11-02','availableAt':'2026-11-03T03:52:00-05:00','builtAt':'2026-11-03T04:10:00-05:00','unit':'USD per +1% spot','displayScale':1000000,'definitionKey':'fixture-call-plus-put-minus-v1','expiries':expiries,'strikes':strikes,'netGammaMillions':matrix,'knownNetGammaSubtotalMillions':net,'population':{'reported':112,'qualified':108,'excluded':4,'marketCoverage':None},'selection':{'strike':750,'expiry':'2026-11-06','right':'aggregate:call+put','callGammaMillions':400,'putGammaMillions':-132,'priorCallGammaMillions':380,'priorPutGammaMillions':-156},'volatility':{'expiryDays':[4,11,18,25,32,46],'atmIvPercent':[14.8,None,17.2,18.0,18.4,19.1],'selectedExpiry':'2026-11-20','smileStrikes':[730,740,750,760,770],'callIvPercent':[22.8,19.1,17.6,None,18.4],'putIvPercent':[23.5,19.8,17.8,18.1,19.0]}}
(OUT/'illustrative-fixture.json').write_text(json.dumps(fixture,indent=2))

def tx(s,size=14,color=None,weight=400,style=''):
 return f'<div style="font-size:{size}px;font-weight:{weight};'+(f'color:{color};' if color else '')+f'{style}">{html.escape(str(s))}</div>'
def box(name,x,y,w,h,content='',t=D,extra=''):
 return f'<div layer-name="{name}" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;display:flex;flex-direction:column;font-family:Inter;color:{t["text"]};{extra}">{content}</div>'
def row(content,gap=12,extra=''):
 return f'<div style="display:flex;align-items:center;gap:{gap}px;{extra}">{content}</div>'
def col(content,gap=8,extra=''):
 return f'<div style="display:flex;flex-direction:column;gap:{gap}px;{extra}">{content}</div>'
def button(s,t=D,primary=False,width=None):
 return '<div style="display:flex;align-items:center;justify-content:center;min-height:44px;padding:0 14px;border-radius:8px;'+(f'width:{width}px;' if width else '')+f'background:{t["text"] if primary else t["raised"]};color:{t["bg"] if primary else t["text"]};font-size:13px;font-weight:500;">{html.escape(s)}</div>'
def panel(name,x,y,w,h,content,t=D):
 return box(name,x,y,w,h,content,t,f'padding:20px;border:1px solid {t["line"]};border-radius:14px;background:{t["panel"]};gap:16px;')
def shell(t=D,w=1440,h=1050,lang='EN'):
 nav=224 if w>=1200 else (196 if w>860 else 0)
 ops=[]
 if w>860:
  ops.append({'name':'header','html':box('Shell header',0,0,w,64,row(tx('MASTERMIND',14,weight=700,style='letter-spacing:2px;width:200px')+button('Search companies or tools     ⌘ K',t,width=410)+tx(('Light' if t==L else 'Dark')+'     '+lang+'     Open chart ↗',13,t['muted']),24,'justify-content:space-between'),t,f'padding:12px 24px;background:{t["panel"]};border-bottom:1px solid {t["line"]};')})
  ops.append({'name':'rail','html':box('Shell navigation',0,64,nav,h-64,'',t,f'padding:24px 16px;background:{t["panel"]};border-right:1px solid {t["line"]};gap:4px;')})
  labels=['Today','Discover','Analysis','Monitor','Research','Portfolio','Markets','United States','China','Hong Kong','Canada','International','All tools']
  for i,label in enumerate(labels):
   ops.append({'name':f'nav-{i}','target':'Shell navigation','html':f'<div style="display:flex;align-items:center;height:{32 if label=="Markets" else 44}px;padding:0 14px;border-radius:8px;font-size:{11 if label=="Markets" else 14}px;color:{t["muted"] if label=="Markets" else t["text"]};background:{t["raised"] if label=="All tools" else "transparent"}">{label}</div>'})
 else:
  ops.append({'name':'header','html':box('Mobile shell header',0,0,w,56,row(tx('☰',18)+tx('MASTERMIND',12,weight=700,style='letter-spacing:1.5px')+tx(lang,12,t['muted']),12,'justify-content:space-between'),t,f'padding:0 16px;justify-content:center;background:{t["panel"]};border-bottom:1px solid {t["line"]};')})
 return ops

def product_nav(x,y,w,active,t=D):
 labels=['Desk','Flow','Exposure','Structure','Volatility','Statistics','Prophet']
 return box('Options local navigation',x,y,w,44,row(''.join(button(s,t,s==active) for s in labels),8)+tx('Illustrative fixture',11,t['muted']),t,'justify-content:space-between;flex-direction:row;align-items:center;')

def heatmap_svg(w=784,h=350,t=D,phone=False):
 # Signed exposure matrix with explicit units and a shared square-root color scale.
 n=1 if phone else 6;left=45;right=74 if phone else 86;top=36;cw=(w-left-right)/n;rh=(h-top-20)/9
 a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
 def text(x,y,s,sz=11,fill=None,anchor='middle'):
  return f'<text x="{x}" y="{y}" fill="{fill or t["muted"]}" font-family="Inter" font-size="{sz}" text-anchor="{anchor}">{html.escape(str(s))}</text>'
 a.append(text(0,16,'Strike',11,anchor='start'))
 for j,e in enumerate(expiries[:n]):a.append(text(left+j*cw+cw/2,16,e[5:].replace('-','/')))
 a.append(text(w-2,16,'All 6 exp.',10,anchor='end'))
 for i,(k,vals) in enumerate(zip(strikes,matrix)):
  y=top+i*rh;a.append(text(0,y+rh*.65,k,12,t['text'],'start'))
  for j,v in enumerate(vals[:n]):
   opacity=.12+.65*math.sqrt(abs(v)/268)
   color=t['pos'] if v>=0 else t['neg']
   a.append(f'<rect x="{left+j*cw+2}" y="{y+2}" width="{cw-4}" height="{rh-4}" rx="4" fill="{color}" fill-opacity="{opacity:.3f}"'+(f' stroke="{t["text"]}" stroke-width="2"' if k==750 and j==0 else '')+'/>')
   rgb=lambda s:[int(s[k:k+2],16)/255 for k in (1,3,5)]
   bg=[a*opacity+b*(1-opacity) for a,b in zip(rgb(color),rgb(t['panel']))]
   lum=lambda cs:sum(c*v for c,v in zip([.2126,.7152,.0722],[(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4) for x in cs]))
   contrast=lambda fg:(max(lum(rgb(fg)),lum(bg))+.05)/(min(lum(rgb(fg)),lum(bg))+.05)
   cell_text=max(['#FFFFFF','#000000'],key=contrast)
   a.append(text(left+j*cw+cw/2,y+rh*.65,f'{v:+d}',12,cell_text))
  a.append(text(w-3,y+rh*.65,f'{sum(vals):+d}',12,t['pos'] if sum(vals)>0 else t['neg'],'end'))
  if k==755:
   yy=y+rh
   a.append(f'<line x1="0" y1="{yy}" x2="{w}" y2="{yy}" stroke="{t["gold"]}" stroke-width="1" stroke-dasharray="4 3"/>')
 a.append('</svg>');return ''.join(a)

boards=[]
ops=shell()
# Existing header already written in Paper; dispatcher skips header once for B01.
ops += [
 {'name':'localnav','html':product_nav(248,76,1168,'Exposure')},
 {'name':'identity','html':box('Exposure identity',248,138,1168,68,row(col(tx('SPY / Exposure',28,weight=600)+tx('US · ARCX · SPY    Book Nov 2, 2026    Spot 752.10 · 16:00:02 ET',12,D['muted']),8)+button('Source & coverage',D)+button('Session · Nov 2 ▾',D),18,'justify-content:space-between'))},
 {'name':'summary','html':box('Qualified exposure summary',248,222,1168,90,row(col(tx('KNOWN GAMMA SUBTOTAL',11,D['muted'],500)+tx(f'{net:+,}M',36,D['pos'],600)+tx('USD per +1% spot · qualified rows',12,D['muted']))+col(tx('LARGEST STRIKE IN THIS BOOK',11,D['muted'])+tx('750   +525M',25,weight=600)+tx('6 expiries · both rights',12,D['muted']))+col(tx('SOURCE ROWS',11,D['muted'])+tx('108 / 112',25,weight=600)+tx('4 excluded · complete total unavailable',12,D['muted'])),44,'justify-content:space-between'),extra=f'border-bottom:1px solid {D["line"]};')},
 {'name':'matrix','html':panel('Exposure matrix',248,336,824,514,col(row(tx('Strike × expiry',16,weight=600)+tx('$M per +1% spot',12,D['muted']),12,'justify-content:space-between')+row(button('Gamma ▾')+button('Net ▾')+button('All 6 expiries ▾')+button('Range ▾')+button('More views ▾'),8)+heatmap_svg()+row(tx('− Negative',11,D['neg'])+tx('0',11,D['muted'])+tx('+ Positive',11,D['pos'])+tx('Spot 752.10 ┄   Square-root scale',11,D['muted']),16),12))},
 {'name':'inspector','html':panel('Selected node inspector',1096,336,320,514,col(row(tx('SELECTED NODE',11,D['muted'])+tx('01 / 54',11,D['muted']),10,'justify-content:space-between')+tx('750 · Nov 06',25,weight=600)+tx('+268M',38,D['pos'],600)+tx('USD per +1% spot · net',12,D['muted'])+tx('Call +400M     Put −132M',14)+tx('Aggregate · 2 qualified contracts',12,D['muted'])+row(tx('Distance to spot',12,D['muted'])+tx('−0.28%',13),8,'justify-content:space-between')+row(tx('Matched change',12,D['muted'])+tx('+44M',15,D['pos']),8,'justify-content:space-between')+tx('Oct 30 → Nov 2 · same 2 contracts',12,D['muted'])+button('Inspect 2 contracts',D,True)+button('Compare these sessions')+row(tx('Volatility ↗',13,D['blue'])+tx('Open chart ↗',13,D['blue']),20),14))},
 {'name':'access','html':box('Exposure secondary controls',248,874,1168,44,row(button('Matrix')+button('By strike')+button('By expiry')+button('Price context')+button('3D / exact 2D')+button('Positioning & levels'),8))},
 {'name':'timeline','html':panel('Dated book timeline',248,938,1168,78,row(col(tx('BOOK HISTORY',11,D['muted'])+tx('Oct 30  →  Nov 2 selected',13),6)+button('Compare sessions')+button('Replay reference ↗'),22,'justify-content:space-between'))}
]
boards.append({'key':'B01','name':'B01 · Exposure + node · 1440 · Dark EN · R1','width':1440,'height':1050,'theme':'dark','locale':'EN','ops':ops})

ops=shell(D,390,1110)
ops += [
 {'name':'context','html':box('Phone context',16,72,358,108,col(row(tx('Options / Exposure',14,weight=600)+button('Views ▾',D),8,'justify-content:space-between')+row(tx('SPY',30,weight=600)+button('Nov 2 ▾'),12,'justify-content:space-between')+tx('Dated book · 2026 · illustrative fixture',12,D['muted']),8))},
 {'name':'metrics','html':box('Phone readable summaries',16,198,358,102,row(col(tx('Known gamma subtotal',12,D['muted'])+tx(f'{net:+,}M',29,D['pos'],600)+tx('$ per +1% spot',11,D['muted']),6,'width:170px')+col(tx('Largest strike',12,D['muted'])+tx('750',29,weight=600)+tx('+525M · all 6 expiries',11,D['muted']),6),18),extra=f'padding:14px 0;border-top:1px solid {D["line"]};border-bottom:1px solid {D["line"]};')},
 {'name':'qualification','html':box('Phone visible source qualification',16,314,358,82,col(tx('Spot Nov 2 · 16:00:02 ET   |   OI Oct 30',12,D['muted'])+tx('OI reported Nov 2 · 108/112 rows · 4 excluded',12,D['muted'])+tx('Complete total unavailable · market coverage unknown',12,D['muted'],style='line-height:18px'),8))},
 {'name':'filters','html':box('Phone matrix controls',16,412,358,100,col(row(button('Gamma ▾')+button('Net ▾')+button('Research ▾'),8)+row(tx('Selected expiry',12,D['muted'])+button('Nov 06 ▾'),10,'justify-content:space-between'),10))},
 {'name':'precise-selection','html':box('Phone immediate exact selection',16,528,358,44,button('Select a node in Exact values',D,True))},
 {'name':'matrix','html':panel('Phone expiry slice',16,588,358,390,col(row(tx('Overview · Nov 06',15,weight=600)+tx('$M',12,D['muted']),8,'justify-content:space-between')+heatmap_svg(318,296,D,True)+tx('Spot 752.10 · 16:00:02 ET  ┄',12,D['gold']),10))},
 {'name':'selection','html':panel('Phone selected node',16,994,358,148,col(row(tx('750 · Nov 06',19,weight=600)+tx('+268M',24,D['pos'],600),12,'justify-content:space-between')+tx('2 contracts · net · $ per +1% spot',12,D['muted'])+button('Inspect selected node',D,True),10))},
 {'name':'footer','html':box('Phone further access',16,1158,358,92,col(row(button('Full matrix')+button('Exact values'),12)+tx('108/112 source rows · Source & coverage ↗',12,D['muted']),14))}
]
boards.append({'key':'B02','name':'B02 · Exposure slice · 390 · Dark EN · R1','width':390,'height':1284,'theme':'dark','locale':'EN','ops':ops})

ops=shell(L,320,1230,'ZH')
ops += [
 {'name':'close','html':box('Node return and close',16,72,288,44,row(tx('← 返回敞口矩阵',15,weight=600)+button('关闭',L),8,'justify-content:space-between'),L)},
 {'name':'title','html':box('Node identity ZH',16,138,288,122,col(tx('SPY · 750 · 2026-11-06',21,weight=600)+tx('合并节点 · 看涨与看跌',13,L['muted'])+tx('+268M',38,L['pos'],600)+tx('美元 / 标的上涨 1% · 示例数据',12,L['muted']),8),L)},
 {'name':'source','html':panel('Node source clocks ZH',16,282,288,304,col(tx('数据与范围',17,weight=600)+tx('标的参考价 752.10 美元',14)+tx('报价 11月2日 16:00:02 ET',12,L['muted'])+tx('持仓所属交易日 10月30日',14)+tx('持仓报告日期 11月2日',12,L['muted'])+tx('此节点 2 个有效合约',14)+tx('108 / 112 行有效 · 4 行排除',12,L['muted'])+tx('可用时间：11月3日 03:52 ET',12,L['muted'])+tx('完整总量不可用；全市场覆盖未知',12,L['muted']),10),L)},
 {'name':'compare','html':panel('Node matched change ZH',16,602,288,154,col(tx('相同合约的两次观测',16,weight=600)+row(tx('+44M',30,L['pos'],600)+tx('10月30日 → 11月2日',12,L['muted']),12)+tx('不代表资金流向或新增持仓',13,L['muted']),14),L)},
 {'name':'contracts','html':panel('Exact contract choices ZH',16,772,288,220,col(tx('选择实际合约',17,weight=600)+button('SPY · 11月6日 · 750 看涨',L)+button('SPY · 11月6日 · 750 看跌',L)+tx('合约乘数与交割条款在详情中核验',12,L['muted']),14),L)},
 {'name':'research','html':box('Node research actions ZH',16,1008,288,198,col(button('查看波动率',L,True)+button('比较观测日期',L)+button('查看来源与计算',L),14),L)},
 {'name':'foot','html':box('No implicit plan ZH',16,1230,288,52,tx('切换视图保留节点；选择合约后才可交给计划工作区。',12,L['muted'],style='line-height:20px'),L)}
]
boards.append({'key':'B03','name':'B03 · Exact node · 320 · Light ZH · R1','width':320,'height':1310,'theme':'light','locale':'ZH','ops':ops})

def line_chart(t,w,h,kind,selected_x=None):
 a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
 def txt(x,y,s,color=None,anchor='middle',sz=11):return f'<text x="{x}" y="{y}" fill="{color or t["muted"]}" font-family="Inter" font-size="{sz}" text-anchor="{anchor}">{s}</text>'
 left=36;right=w-20;top=24;bottom=h-32
 for v in [12,16,20,24]:
  y=bottom-(v-12)/12*(bottom-top);a.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="{t["line"]}"/>');a.append(txt(0,y+4,f'{v}%',anchor='start'))
 if kind=='term':
  xs=fixture['volatility']['expiryDays']; ys=fixture['volatility']['atmIvPercent']; cs=[t['blue']];series=[ys];lo=0;hi=46;labels=['Nov06','Nov13','Nov20','Nov27','Dec04','Dec18']
 else:
  xs=[730,740,750,760,770];series=[fixture['volatility']['callIvPercent'],fixture['volatility']['putIvPercent']];cs=[t['blue'],t['gold']];lo=730;hi=770;labels=[str(s) for s in xs]
 selected_x=(18 if kind=='term' else 750) if selected_x is None else selected_x
 sx=left+(selected_x-lo)/(hi-lo)*(right-left)
 a.append(f'<line x1="{sx}" y1="{top}" x2="{sx}" y2="{bottom}" stroke="{t["muted"]}" stroke-dasharray="3 4"/>')
 for series_index,(vals,color) in enumerate(zip(series,cs)):
  prev=None
  for j,(xv,yv) in enumerate(zip(xs,vals)):
   x=left+(xv-lo)/(hi-lo)*(right-left)
   if yv is None:
    prev=None;continue
   y=bottom-(yv-12)/12*(bottom-top)
   if prev:a.append(f'<line x1="{prev[0]}" y1="{prev[1]}" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="5 3"' if series_index==1 else '')+'/>')
   a.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>' if series_index==0 else f'<path d="M{x} {y-5} L{x+5} {y} L{x} {y+5} L{x-5} {y} Z" fill="{color}"/>');prev=(x,y)
   if xv==selected_x and series_index==0:a.append(f'<circle cx="{x}" cy="{y}" r="8" fill="none" stroke="{t["text"]}" stroke-width="1.5"/>')
 for xv,label in zip(xs,labels):a.append(txt(left+(xv-lo)/(hi-lo)*(right-left),h-5,label))
 a.append('</svg>');return ''.join(a)

ops=shell(L)
ops += [
 {'name':'localnav','html':product_nav(248,76,1168,'Volatility',L)},
 {'name':'identity','html':box('Volatility identity',248,138,1168,72,row(col(tx('SPY / Volatility',28,weight=600)+tx('Book Nov 2, 2026 · reported IV · illustrative fixture',12,L['muted']),8)+button('Source & method',L)+button('Session · Nov 2 ▾',L),18,'justify-content:space-between'),L)},
 {'name':'selected','html':box('Selected expiry summary',248,226,1168,88,row(col(tx('SELECTED EXPIRY',11,L['muted'])+tx('Nov 20 · 18 days',28,weight=600),8)+col(tx('REPORTED ATM IV',11,L['muted'])+tx('17.2%',36,L['blue'],600),8)+button('Choose expiry ▾',L),24,'justify-content:space-between'),L,f'border-bottom:1px solid {L["line"]};')},
 {'name':'term','html':panel('Term structure',248,338,824,294,col(row(tx('IV by expiry',17,weight=600)+tx('5 of 6 supplied',12,L['muted']),12,'justify-content:space-between')+line_chart(L,784,192,'term')+tx('Nov 13 is missing · no curve is fitted across the gap',12,L['muted']),12),L)},
 {'name':'smile','html':panel('Exact expiry smile',248,652,824,294,col(row(tx('Smile · Nov 20',17,weight=600)+row(tx('● Calls —',12,L['blue'])+tx('◆ Puts - -',12,L['gold']),12),12,'justify-content:space-between')+line_chart(L,784,192,'smile')+tx('Strike 750 · Call 17.6% · Put 17.8% · Call 760 not supplied',12,L['muted']),12),L)},
 {'name':'inspector','html':panel('Volatility expiry inspector',1096,338,320,474,col(tx('NOV 20, 2026',12,L['muted'])+tx('750 strike',28,weight=600)+tx('Call 17.6% / Put 17.8%',19,L['blue'],500)+tx('Reported IV · not a modeled surface',12,L['muted'])+button('Inspect exact contracts',L,True)+button('Source values',L)+tx('REFERENCE CONTEXT',11,L['muted'])+tx('20-return realized vol 16.8%',14)+tx('Different horizon · no cheap/rich verdict',12,L['muted'])+tx('Quote inputs and IV method: not supplied',12,L['muted']),18),L)},
 {'name':'retained','html':panel('Volatility retained controls',1096,832,320,114,col(tx('Continue research',14,weight=600)+row(tx('History ↗',13,L['blue'])+tx('Rank windows ↗',13,L['blue']),18)+tx('Back to selected exposure node ↗',13,L['blue']),12),L)},
 {'name':'footer','html':box('Volatility full access',248,970,1168,44,row(button('Term structure',L)+button('Smile / skew',L)+button('IV–RV history',L)+button('Rank & percentile',L)+button('3D / exact 2D',L),10),L)}
]
boards.append({'key':'B04','name':'B04 · Expiry-led volatility · 1440 · Light EN · R1','width':1440,'height':1050,'theme':'light','locale':'EN','ops':ops})

def surface_svg(w=744,h=400,t=D):
 # Discrete data columns; height is signed gamma, never a smooth inferred surface.
 a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
 def proj(i,j,z=0):return (90+i*39+j*40,160+i*12-j*17-z*.38)
 for j in range(7):
  x1,y1=proj(0,j);x2,y2=proj(8,j);a.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["line"]}"/>')
 for i in range(9):
  x1,y1=proj(i,0);x2,y2=proj(i,5);a.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["line"]}"/>')
 for j in range(5,-1,-1):
  for i in range(9):
   v=matrix[i][j];x,y=proj(i,j);xx,yy=proj(i,j,v);color=t['pos'] if v>=0 else t['neg']
   a.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{color}" stroke-opacity=".65" stroke-width="8"/>')
   a.append(f'<circle cx="{xx}" cy="{yy}" r="{7 if i==5 and j==0 else 3.5}" fill="{color}"'+(f' stroke="{t["text"]}" stroke-width="2"' if i==5 and j==0 else '')+'/>')
 # Calibrated references use the same projection and linear height scale as the data.
 a.append(f'<line x1="55" y1="46" x2="55" y2="236" stroke="{t["muted"]}"/>')
 a.append(f'<line x1="55" y1="160" x2="90" y2="160" stroke="{t["muted"]}" stroke-dasharray="3 3"/>')
 for v in [-200,-100,0,100,200,300]:
  yy=160-v*.38;a.append(f'<line x1="51" y1="{yy}" x2="59" y2="{yy}" stroke="{t["muted"]}"/><text x="44" y="{yy+3}" text-anchor="end" fill="{t["muted"]}" font-family="Inter" font-size="10">{v:+d}</text>')
 for i in [0,2,4,5,6,8]:
  x,y=proj(i,0);a.append(f'<line x1="{x}" y1="{y+4}" x2="{x}" y2="{y+10}" stroke="{t["muted"]}"/><text x="{x-9}" y="{y+25}" text-anchor="end" fill="{t["text"] if i==5 else t["muted"]}" font-family="Inter" font-size="11">{strikes[i]}</text>')
 for j,e in enumerate(expiries):
  x,y=proj(8,j);a.append(f'<line x1="{x+4}" y1="{y}" x2="{x+10}" y2="{y}" stroke="{t["muted"]}"/><text x="{x+16}" y="{y+4}" fill="{t["text"] if j==0 else t["muted"]}" font-family="Inter" font-size="11">{e[5:].replace("-","/")}</text>')
 x,y=proj(5,0,268);a.append(f'<line x1="{x+8}" y1="{y-5}" x2="{x+34}" y2="{y-32}" stroke="{t["text"]}"/><text x="{x+40}" y="{y-35}" fill="{t["text"]}" font-family="Inter" font-size="12">750 · 11/06 · +268M</text>')
 a.append(f'<text x="38" y="340" fill="{t["muted"]}" font-family="Inter" font-size="12">Strike 775 → 735</text>')
 a.append(f'<text x="470" y="58" fill="{t["muted"]}" font-family="Inter" font-size="12">Expiry Nov 06 → Dec 18</text>')
 a.append(f'<text x="38" y="365" fill="{t["muted"]}" font-family="Inter" font-size="12">Height: linear signed $M / +1% spot · zero plane = 0</text>')
 a.append('</svg>');return ''.join(a)

ops=shell(D,1024,1060)
ops += [
 {'name':'title','html':box('3D title',216,84,788,92,col(row(tx('SPY / 3D investigation',27,weight=600)+button('Views ▾'),16,'justify-content:space-between')+tx('Gamma · Nov 2, 2026 · illustrative fixture',12,D['muted']),14))},
 {'name':'controls','html':box('3D controls',216,190,788,44,row(button('3D',D,True)+button('2D matrix')+button('Exact values')+button('Gamma ▾')+button('Net ▾')+button('Scope ▾')+button('Camera ▾'),8))},
 {'name':'scene','html':panel('3D discrete exposure',216,256,788,500,col(row(tx('Strike × expiry × signed gamma',16,weight=600)+tx('54 known nodes',12,D['muted']),12,'justify-content:space-between')+surface_svg(748,398)+tx('Static view · no auto-orbit · choose a node or an exact row',12,D['muted']),12))},
 {'name':'slice','html':panel('3D exact companion slice',216,780,788,204,col(row(tx('Selected · 750 / Nov 06',18,weight=600)+tx('+268M',28,D['pos'],600),12,'justify-content:space-between')+row(tx('Call +400M',16,D['pos'])+tx('Put −132M',16,D['neg']),30)+row(button('Inspect node',D,True)+button('Exact contracts')+button('Compare sessions'),12)+tx('Switching 2D/3D preserves dataset, snapshot, coordinate, unit and lens.',12,D['muted']),18))}
]
boards.append({'key':'B05','name':'B05 · 3D + exact slice · 1024 · Dark EN · R1','width':1024,'height':1060,'theme':'dark','locale':'EN','ops':ops})

ops=shell(L,768,1140,'ZH')
ops += [
 {'name':'title','html':box('2D alternative identity',20,80,728,90,col(row(tx('SPY / 精确数据',27,weight=600)+button('视图 ▾',L),16,'justify-content:space-between')+tx('2026-11-02 · Gamma · 与 3D 相同的数据 · 示例',13,L['muted']),16),L)},
 {'name':'toolbar','html':box('2D keyboard controls',20,194,728,100,col(row(button('二维矩阵',L)+button('精确数值',L,True)+button('返回 3D',L)+button('到期日 ▾',L),10)+tx('方向键移动 · Enter 选择 · Home/End 首末行 · Esc 关闭详情',12,L['muted']),18),L)},
 {'name':'table','html':panel('Exact values table',20,314,728,584,col(row(tx('行权价',13,L['muted'],style='width:100px')+tx('11月6日',13,L['muted'],style='width:160px')+tx('全部6个到期日',13,L['muted'],style='width:190px')+tx('状态',13,L['muted']),10)+''.join(row(tx(k,16,weight=600,style='width:100px')+tx(f'{vals[0]:+d}M',16,L['pos'] if vals[0]>=0 else L['neg'],style='width:160px')+tx(f'{sum(vals):+d}M',16,style='width:190px')+tx('已选择' if k==750 else '已提供',13,L['muted']),10,f'height:48px;padding:0 8px;border-radius:8px;background:{L["raised"] if k==750 else "transparent"};') for k,vals in zip(strikes,matrix))+tx('单位：美元 / 标的上涨1% · 以百万显示 · 正负号始终可见',12,L['muted']),8),L)},
 {'name':'selection','html':panel('2D selected node actions',20,920,728,166,col(row(tx('750 · 11月6日',24,weight=600)+tx('+268M',30,L['pos'],600),12,'justify-content:space-between')+tx('净值 · 合并节点 · 2个有效合约',13,L['muted'])+row(button('检查节点',L,True)+button('选择实际合约',L)+button('比较日期',L),12),16),L)}
]
boards.append({'key':'B06','name':'B06 · Exact 2D table · 768 · Light ZH · R1','width':768,'height':1140,'theme':'light','locale':'ZH','ops':ops})

ops=shell(D)
ops += [
 {'name':'localnav','html':product_nav(248,76,1168,'Exposure')},
 {'name':'title','html':box('Matched book comparison',248,138,1168,72,col(row(tx('SPY / Compare observations',28,weight=600)+button('Back to node'),18,'justify-content:space-between')+tx('Oct 30 → Nov 2, 2026 · same source and definition · illustrative fixture',12,D['muted']),12))},
 {'name':'change','html':panel('Comparison decision summary',248,230,1168,150,row(col(tx('MATCHED NODE CHANGE',11,D['muted'])+tx('+44M',42,D['pos'],600)+tx('Net gamma · $ per +1% spot',13,D['muted']),10)+col(tx('SAME 2 CONTRACTS',11,D['muted'])+tx('+224M → +268M',28,weight=600)+tx('750 · Nov 06 · both rights',13,D['muted']),10)+col(tx('GROSS EXPOSURE CHANGE',11,D['muted'])+tx('−4M',28,D['neg'],600)+tx('536M → 532M',13,D['muted']),10),46,'justify-content:space-between'))},
 {'name':'basis','html':panel('Comparison basis',248,404,824,354,col(tx('Same-contract evidence',18,weight=600)+row(tx('Contract',12,D['muted'],style='width:240px')+tx('Oct 30',12,D['muted'],style='width:130px')+tx('Nov 2',12,D['muted'],style='width:130px')+tx('Change',12,D['muted']),16)+row(tx('SPY Nov06 750 Call',15,style='width:240px')+tx('+380M',18,style='width:130px')+tx('+400M',18,style='width:130px')+tx('+20M',18,D['pos']),16,'height:64px')+row(tx('SPY Nov06 750 Put',15,style='width:240px')+tx('−156M',18,style='width:130px')+tx('−132M',18,style='width:130px')+tx('+24M',18,D['pos']),16,'height:64px')+tx('Changed exposure reflects observations and assumptions; it is not a trade tape.',13,D['muted'])+row(button('View each source')+button('Open current node',D,True),12),16))},
 {'name':'qualification','html':panel('Comparison qualification',1096,404,320,354,col(tx('Comparison basis',18,weight=600)+tx('2 finite matched contracts',15)+tx('0 current-only · 0 prior-only',13,D['muted'])+tx('0 gained · 0 lost qualification',13,D['muted'])+tx('Same root, scope, unit and method',13)+tx('Cutoff: Nov 3, 2026 · 04:15 ET',12,D['muted'])+tx('Current-knowledge comparison',12,D['muted'])+tx('Scope is this node, not the whole book',12,D['muted'])+button('Source & definitions'),15))},
 {'name':'positioning','html':panel('Positioning and level context',248,782,1168,182,col(row(tx('Keep context separate',18,weight=600)+button('Positioning & levels ↗'),16,'justify-content:space-between')+row(col(tx('LARGEST STRIKE',11,D['muted'])+tx('750 · +525M',23,weight=600)+tx('Current book · same declared scope',12,D['muted']),10)+col(tx('SPOT',11,D['muted'])+tx('752.10',23,weight=600)+tx('Nov 2 · 16:00:02 ET',12,D['muted']),10)+col(tx('INTERPRETATION',11,D['muted'])+tx('Observed change',23,weight=600)+tx('No directional-flow or win-probability claim',12,D['muted']),10),44),18))}
]
boards.append({'key':'B07','name':'B07 · Matched change · 1440 · Dark EN · R1','width':1440,'height':1050,'theme':'dark','locale':'EN','ops':ops})

ops=shell(L,390,1080)
ops += [
 {'name':'title','html':box('Phone volatility identity',16,76,358,100,col(row(tx('SPY / Volatility',23,weight=600)+button('Views ▾',L),8,'justify-content:space-between')+tx('Nov 2, 2026 · illustrative fixture',12,L['muted'])+tx('Selected expiry · Nov 13',16,weight=600),12),L)},
 {'name':'missing','html':panel('Missing selected expiry',16,202,358,190,col(tx('IV not supplied',27,weight=600)+tx('Your Nov 13 selection is preserved.',14,L['muted'])+tx('Other expiries remain available.',14,L['muted'])+button('Choose an available expiry',L,True),16),L)},
 {'name':'term','html':panel('Phone term structure',16,412,358,246,col(tx('IV by expiry',17,weight=600)+line_chart(L,318,150,'term',selected_x=11)+tx('The missing point stays a gap.',12,L['muted']),12),L)},
 {'name':'choices','html':panel('Phone expiry values',16,678,358,278,col(tx('Available observations',17,weight=600)+row(tx('Nov 06 · 4 days',14)+tx('14.8%',16,L['blue']),12,'justify-content:space-between;height:44px')+row(tx('Nov 20 · 18 days',14)+tx('17.2%',16,L['blue']),12,'justify-content:space-between;height:44px')+row(tx('Nov 27 · 25 days',14)+tx('18.0%',16,L['blue']),12,'justify-content:space-between;height:44px')+button('All expiries ▾',L),8),L)},
 {'name':'return','html':box('Phone volatility return',16,976,358,104,col(button('Source & method',L)+button('Back to exposure node',L),12),L)}
]
boards.append({'key':'B08','name':'B08 · Missing expiry · 390 · Light EN · R1','width':390,'height':1120,'theme':'light','locale':'EN','ops':ops})

ops=[{'name':'title','html':box('State atlas title',32,28,1376,80,col(tx('D08B / State & interaction specimens',30,weight=600)+tx('Build requirements · candidate references · no live data or runtime behavior asserted',13,D['muted']),12))}]
states=[('Loading selected book','Loading NVDA exposure…','Clear former SPY values immediately. Preserve requested root and layout.','Identity-bound skeleton; late SPY response discarded.'),('Partial book','Known subtotal +123M','108/112 source rows qualify. Whole-market coverage is unknown.','Show excluded rows and scoped denominator; never fill with zero.'),('Last available','As of Nov 2 · refresh failed','Keep only this root’s dated, authorized observation.','One explicit Retry; success does not redate the source.'),('Unsupported Greek','Vanna is not computed','Gamma remains available for the selected book.','Disabled action with reason; never a premium upgrade suggestion.'),('Access unresolved','Access could not be verified','Keep the requested resource; hide protected values.','Sign-in, plan-required and service failure need owner evidence.'),('Comparison unavailable','Methods differ','Both books stay inspectable. No aggregate delta.','Preserve both selections; offer supported same-method basis.'),('Original node missing','This node is outside the new book','Keep the original selection as dated evidence.','Choose a new node explicitly; never substitute a neighbour.'),('Return & handoff','Back to filtered tape','Restore the originating observation, filters, focus and scroll.','C owns plans/save; D owns temporal replay. No implicit save.'),('Reduced motion / no WebGL','Use exact 2D values','Same dataset, scope, unit and selection; full filter and compare controls.','No rotation required; no feature loss on phone or keyboard.')]
for i,(name,title,body,rule) in enumerate(states):
 x=32+(i%3)*464;y=140+(i//3)*280
 ops.append({'name':f'state-{i}','html':panel(name,x,y,440,252,col(tx(name.upper(),11,D['muted'])+tx(title,22,weight=600)+tx(body,14,style='line-height:22px')+tx(rule,12,D['muted'],style='line-height:20px'),16))})
boards.append({'key':'B09','name':'B09 · State and interaction atlas · Dark EN · R1','width':1440,'height':1020,'theme':'dark','locale':'EN','ops':ops})

ops=[{'name':'title','html':box('Build notes title',32,32,1376,100,col(tx('D08B / Read me & build contract',34,weight=600)+tx('Exposure, volatility and 3D investigation · Candidate R1 · RIG draft',15,D['muted'])+tx('Primary user: an options researcher testing a dated observation before continuing a research plan.',14),12))}]
sections=[('01 · Complete task','Underlying → dated exposure book → selected strike/expiry → exact contracts → comparison or volatility → original selection.','D08B owns GEX, Surface, Positioning, Levels, Volatility and 3D presentation. D08 owns navigation. D08C owns plans and saved scenarios. D08D owns replay data, cursor, entitlement and distribution.'),('02 · Read the candidate','B01–B03/B10–B11 matrix and phone; B04/B08 volatility; B05/B06 gamma 3D/2D; B07/B16 comparison; B13 chain; B14 levels; B15 states; B17 contracts; B09/B12 annotations.','All figures are a labeled illustrative fixture with explicit semantics. No measured usability, live model or production acceptance is claimed.'),('03 · Identity and numerical truth','A node is an aggregate until exact source contracts are resolved. Carry root, snapshot, coordinate, metric, unit, lens, qualification and source clocks.','Call+/put− is the declared fixture convention. Comparison is matched observation change, never order flow. Spot, OI position day, OI report date and availability are distinct.'),('04 · Responsive and access','Useful width = viewport − actual rail − two gutters. Dock320+24 only if primary≥640; otherwise use modal/full-screen details.','320/390: complete Views and Research pickers; selected expiry chart; exact values. Keyboard, touch and reduced-motion must reach the same node and operations.'),('05 · Source and review','Parent: macro #10649 · D08-OPTIONS/1.0.0 at d0516e1. Programme package 6e186286. Source package: research/design_candidates/production_design_20261102/d08b/.','F01/F02 candidate.4 geometry is an input, not a released foundation. Reference acceptance requires independent product and taste findings and the existing RIG process.'),('06 · Builder acceptance','No cross-root stale result, null→zero conversion, substituted expiry, future-known comparison, false durable save or detached focus.','Preserve every existing analytical view. Lazy-mount3D, bound visible cells and requests, supply semantic exact values and source-limited exports. No product implementation or deployment in this commission.')]
for i,(title,body,small) in enumerate(sections):
 x=32+(i%2)*704;y=160+(i//2)*252
 ops.append({'name':f'notes-{i}','html':panel(title,x,y,680,226,col(tx(title,20,weight=600)+tx(body,14,style='line-height:23px')+tx(small,12,D['muted'],style='line-height:20px'),16))})
boards.append({'key':'B00','name':'B00 · Read me and build contract · R1','width':1440,'height':960,'theme':'dark','locale':'EN','ops':ops})

# Independently requested phone interaction and exact-value specimens.
ops=shell(D,390,1260)
ops += [
 {'name':'menu-header','html':box('Phone research menu context',16,76,358,120,col(row(tx('Research controls',24,weight=600)+button('Close'),12,'justify-content:space-between')+tx('SPY · Book Nov 2 · 750 / Nov 06',13,D['muted'])+tx('Gamma · Net · range 735–775',13,D['muted']),14))},
 {'name':'views','html':panel('Open Views destinations',16,214,358,338,col(tx('VIEWS',11,D['muted'])+button('Exposure matrix',D,True)+button('Positioning & levels')+button('Volatility')+button('Surface / Flow context')+button('3D / exact 2D'),12))},
 {'name':'research','html':panel('Open Research destinations',16,572,358,416,col(tx('RESEARCH',11,D['muted'])+button('Range · 735–775 ▾')+button('By strike / by expiry')+button('Price context')+button('Compare observations')+button('Book history / replay reference')+button('Source, coverage & calculations'),12))},
 {'name':'return','html':box('Phone menu return',16,1012,358,160,col(button('Return to selected node',D,True)+tx('Changing a view retains this root, session, node, lens and range. A new expiry or range outside this node asks for an explicit selection.',12,D['muted'],style='line-height:20px'),18))}
]
boards.append({'key':'B10','name':'B10 · Phone open research controls · 390 · Dark EN · R1','width':390,'height':1210,'theme':'dark','locale':'EN','ops':ops})
ops=shell(D,390,1340)
rows=''.join(row(tx(k,16,weight=600,style='width:62px')+tx(f'{vals[0]:+d}M',16,D['pos'] if vals[0]>=0 else D['neg'],style='width:108px')+tx('Selected' if k==750 else 'Inspect →',12,D['muted']),12,f'height:48px;min-height:48px;padding:0 10px;border-radius:8px;background:{D["raised"] if k==750 else "transparent"};{('outline:2px solid '+D['blue']+';outline-offset:2px;') if k==750 else ''}') for k,vals in zip(strikes,matrix))
ops += [
 {'name':'title','html':box('Phone exact values context',16,76,358,158,col(row(tx('Exact values',25,weight=600)+button('Close'),12,'justify-content:space-between')+tx('SPY · Nov 2, 2026 · illustrative fixture',12,D['muted'])+row(button('Nov 06 ▾')+button('Gamma / Net ▾'),12)+tx('Same data as 3D · $M per +1% spot',12,D['muted']),14))},
 {'name':'rows','html':panel('Phone exact selectable rows',16,256,358,558,col(row(tx('Strike',12,D['muted'],style='width:72px')+tx('Nov 06',12,D['muted'],style='width:108px')+tx('Action',12,D['muted']),12)+rows+tx('Each row is a 48px selection target.',12,D['muted']),6))},
 {'name':'states','html':panel('Zero and missing cell specimens',16,834,358,240,col(tx('Cell-state specimens',16,weight=600)+tx('Examples below are separate state variants.',12,D['muted'])+row(tx('0',23,weight=600,style='width:60px')+tx('Measured zero',14),16,'min-height:44px')+row(tx('—',23,weight=600,style='width:60px')+tx('Not supplied · excluded from totals',12,D['muted']),16,'min-height:44px')+tx('Unknown is never drawn or summed as zero.',12,D['muted']),12))},
 {'name':'selection','html':box('Phone table selection actions',16,1094,358,170,col(button('Inspect 750 / Nov 06',D,True)+button('Return to 3D with this node')+tx('108/112 rows · 4 excluded · full total unavailable',12,D['muted']),14))}
]
boards.append({'key':'B11','name':'B11 · Phone exact 2D and cell states · 390 · Dark EN · R1','width':390,'height':1310,'theme':'dark','locale':'EN','ops':ops})

for board in boards:
 if board['key'] in ['B05','B07']:
  nav=''.join(o['html'] for o in board['ops'] if o.get('target')=='Shell navigation')
  for o in board['ops']:
   if o['name']=='rail': o['html']=o['html'][:-6]+nav+'</div>'
  board['ops']=[o for o in board['ops'] if o.get('target')!='Shell navigation']

(OUT/'paper-compositions.json').write_text(json.dumps(boards,ensure_ascii=False,indent=2))
print(json.dumps({'boards':len(boards),'operations':sum(len(b['ops']) for b in boards),'netGammaMillions':net,'selectedNode':268,'selectedStrike':sum(matrix[5]),'matchedChange':44,'grossChange':-4}))
