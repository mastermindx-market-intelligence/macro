"""Editable, token-based R8 Prophet design source. Illustrative states, not market recommendations."""
from pathlib import Path
from html import escape
import argparse, json
from bs4 import BeautifulSoup

cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--output",type=Path,required=True)
args=cli.parse_args()
OUT=args.output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
STATUS_BAR="<div layer-name=\"Status bar\" style=\"display: flex; align-items: center; gap: 154px; padding: 21px 24px 19px;\">\n  <div layer-name=\"Time\" style=\"display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1;\">\n    <div style=\"color: white; font-family: system-ui; font-size: 17px; font-weight: 600; text-align: center; width: fit-content\">\n      9:41\n    </div>\n  </div>\n  <div layer-name=\"Icons\" style=\"display: flex; flex-direction: column; flex: 1; align-items: center; justify-content: center;\">\n    <svg width=\"82\" height=\"22\" viewBox=\"0 0 82 22\" style=\"flex-shrink: 0\" fill=\"white\">\n      <path d=\"M3.7 13H2.5a1 1 0 0 0-1 1v2.5a1 1 0 0 0 1 1h1.2a1 1 0 0 0 1-1V14a1 1 0 0 0-1-1m5.2-2.5H7.7a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h1.2a1 1 0 0 0 1-1v-5a1 1 0 0 0-1-1M14.1 8h-1.2a1 1 0 0 0-1 1v7.5a1 1 0 0 0 1 1h1.2a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1m5.2-2.5h-1.2a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h1.2a1 1 0 0 0 1-1v-10a1 1 0 0 0-1-1\" />\n      <path fill-rule=\"evenodd\" d=\"M36.57 7.8c2.49 0 4.88.92 6.68 2.58.14.13.36.12.49 0l1.3-1.27a.34.34 0 0 0 0-.5 12.55 12.55 0 0 0-16.93 0 .34.34 0 0 0 0 .5l1.3 1.26c.13.13.34.14.48 0a10 10 0 0 1 6.68-2.57m0 4.22a5.4 5.4 0 0 1 3.67 1.44c.14.13.35.13.48 0l1.3-1.33a.37.37 0 0 0-.01-.52 7.9 7.9 0 0 0-10.88 0 .37.37 0 0 0 0 .52l1.29 1.32c.13.14.34.14.48 0 1-.92 2.31-1.43 3.67-1.43m2.52 2.8q0 .15-.1.28l-2.18 2.45a.3.3 0 0 1-.24.11.3.3 0 0 1-.24-.1l-2.18-2.46a.43.43 0 0 1 .01-.56 3.44 3.44 0 0 1 4.82 0 .4.4 0 0 1 .11.28\" clip-rule=\"evenodd\" />\n      <path fill-rule=\"evenodd\" d=\"M70.5 5c2.05 0 3.08 0 3.88.34a4.3 4.3 0 0 1 2.28 2.28c.34.8.34 1.83.34 3.88s0 3.08-.34 3.88a4.3 4.3 0 0 1-2.28 2.28c-.8.34-1.83.34-3.88.34h-12c-2.05 0-3.08 0-3.88-.34a4.3 4.3 0 0 1-2.28-2.28c-.34-.8-.34-1.83-.34-3.88s0-3.08.34-3.88a4.3 4.3 0 0 1 2.28-2.28C55.42 5 56.45 5 58.5 5zM58.28 6c-1.85 0-2.77 0-3.48.36a3.3 3.3 0 0 0-1.44 1.44C53 8.5 53 9.43 53 11.28v.44c0 1.85 0 2.77.36 3.48a3.3 3.3 0 0 0 1.44 1.44c.7.36 1.63.36 3.48.36h12.44c1.85 0 2.77 0 3.48-.36a3.3 3.3 0 0 0 1.44-1.44c.36-.7.36-1.63.36-3.48v-.44c0-1.85 0-2.77-.36-3.48a3.3 3.3 0 0 0-1.44-1.44C73.5 6 72.57 6 70.72 6z\" clip-rule=\"evenodd\" style=\"opacity: .35\" />\n      <path d=\"M54 11c0-1.4 0-2.1.27-2.63a2.5 2.5 0 0 1 1.1-1.1C55.9 7 56.6 7 58 7h13c1.4 0 2.1 0 2.64.27q.72.37 1.09 1.1C75 8.9 75 9.6 75 11v1c0 1.4 0 2.1-.27 2.64a2.5 2.5 0 0 1-1.1 1.09C73.1 16 72.4 16 71 16H58c-1.4 0-2.1 0-2.63-.27a2.5 2.5 0 0 1-1.1-1.1C54 14.1 54 13.4 54 12z\" />\n      <path d=\"M78 9.5v4.08a2.2 2.2 0 0 0 1.33-2.04A2.2 2.2 0 0 0 78 9.5\" style=\"opacity: .35\" />\n    </svg>\n  </div>\n</div>"
TOKENS={
"light":{"bg":"#F7F8FA","panel":"#FFFFFF","panel2":"#EEF1F6","text":"#1C2430","muted":"#5D6B7E","line":"#C9CCD1","line-quiet":"#E2E6EC","ink-up":"#1E6D47","ink-down":"#B23C3D","ink-warn":"#7D5922","info":"#285FFF","link":"#285FFF","up":"#1F9A55","down":"#CF4040","warn":"#B9791A"},
"dark":{"bg":"#0F1115","panel":"#181B21","panel2":"#1E222A","text":"#D7DCE3","muted":"#8B93A1","line":"#3A4150","line-quiet":"#272C35","ink-up":"#45B873","ink-down":"#E06464","ink-warn":"#E0A030","info":"#5B9BF0","link":"#7AA7E0","up":"#45B873","down":"#E06464","warn":"#E0A030"}}
# Existing Paper tokens; dark semantic ink aliases use their existing family token.
def v(theme,key):
    if theme=="dark" and key.startswith("ink-"):key=key[4:]
    return "var(--mx-"+theme+"-"+key+")"
def text(s,size=14,weight=400,color=None,extra=""):
    return '<div style="font-family:Inter;font-size:'+str(size)+'px;font-weight:'+str(weight)+';line-height:'+str(round(size*1.45))+'px;'+("color:"+color+";" if color else "")+extra+'">'+s+'</div>'
def row(contents,gap=12,extra=""):
    return '<div style="display:flex;align-items:center;gap:'+str(gap)+'px;'+extra+'">'+contents+'</div>'
def svg(name,color,size=18):
    paths={
      "search":'<circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/>',
      "arrow":'<path d="M5 12h14m-5-5 5 5-5 5"/>',
      "chevron":'<path d="m8 10 4 4 4-4"/>',
      "settings":'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
      "menu":'<path d="M4 6h16M4 12h16M4 18h16"/>',
      "spark":'<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/>',
      "external":'<path d="M14 4h6v6m0-6-9 9M9 4H4v16h16v-5"/>',
      "info":'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
      "clock":'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
      "check":'<path d="m5 12 4 4L19 6"/>',
    }
    return '<svg width="'+str(size)+'" height="'+str(size)+'" viewBox="0 0 24 24" fill="none" stroke="'+color+'" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+paths[name]+'</svg>'
def pill(label,theme,tone="muted"):
    return '<div style="display:flex;align-items:center;padding:4px 8px;border:1px solid '+v(theme,"line-quiet")+';border-radius:6px;background:'+v(theme,"panel2")+';">'+text(escape(label),11,600,v(theme,tone))+'</div>'
def button(label,theme,primary=False,icon=None):
    return '<div style="display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 13px;min-height:40px;border-radius:8px;border:1px solid '+(v(theme,"info") if primary else v(theme,"line"))+';background:'+(v(theme,"info") if primary else v(theme,"panel"))+';color:'+("#FFFFFF" if primary and theme=="light" else v(theme,"text"))+';">'+(svg(icon,"#FFFFFF" if primary and theme=="light" else v(theme,"text"),16) if icon else "")+text(escape(label),13,600)+'</div>'
def chart(theme,kind):
    points={"rise":"0,64 12,59 24,61 36,47 48,51 60,49 72,38 84,44 96,34 108,40 120,25 132,30 144,23 156,29 168,17 180,20 192,10 204,16 216,9 228,12 240,4",
            "near":"0,52 12,49 24,51 36,55 48,49 60,54 72,51 84,46 96,52 108,42 120,46 132,41 144,47 156,36 168,39 180,30 192,34 204,25 216,29 228,22 240,25",
            "wait":"0,68 12,66 24,61 36,62 48,53 60,58 72,50 84,49 96,37 108,42 120,34 132,40 144,25 156,31 168,20 180,28 192,16 204,19 216,8 228,14 240,9",
            "stale":"0,59 12,56 24,63 36,50 48,58 60,46 72,52 84,42 96,49 108,36 120,43 132,31 144,40 156,28 168,34 180,22 192,28 204,16 216,22 228,17 240,19"}
    color=v(theme,"muted" if kind=="stale" else "ink-up")
    zone_top={"rise":0,"near":34,"wait":20,"stale":20}[kind]
    return '<svg width="100%" height="82" viewBox="0 0 240 82" preserveAspectRatio="none"><path d="M0 70H240M0 35H240" stroke="'+v(theme,"line-quiet")+'" stroke-width="1"/><rect x="176" y="'+str(zone_top)+'" width="64" height="20" fill="'+v(theme,"panel2")+'"/><path d="M176 '+str(zone_top)+'H240M176 '+str(zone_top+20)+'H240" stroke="'+v(theme,"info")+'" stroke-width="1" stroke-dasharray="4 4"/><polyline points="'+points[kind]+'" fill="none" stroke="'+color+'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'

CARDS=[
 {"symbol":"NVDA","name":"NVIDIA","sector":"Semiconductors","price":"225.07","move":"+0.22%","status":"Buy","status_zh":"买入","tone":"ink-up","stage":"Ready","stage_zh":"就绪","chart":"rise","entry":"220.50–225.10","risk":"Close below 212.40","risk_zh":"收盘低于 212.40","reason":"Price is inside the stated zone.","reason_zh":"价格位于所列区间内。","lens":"Early leadership"},
 {"symbol":"ANET","name":"Arista Networks","sector":"Computer networking","price":"142.18","move":"−0.41%","status":"Near","status_zh":"临近","tone":"info","stage":"Turning","stage_zh":"转强","chart":"near","entry":"136.80–140.20","risk":"Close below 129.60","risk_zh":"收盘低于 129.60","reason":"Wait for the entry conditions.","reason_zh":"等待入场条件满足。","lens":"Early leadership"},
 {"symbol":"VKTX","name":"Viking Therapeutics","sector":"Biotechnology","price":"35.56","move":"−3.24%","status":"Wait","status_zh":"等待","tone":"ink-warn","stage":"Trend","stage_zh":"趋势","chart":"wait","entry":"30.20–32.40","risk":"Close below 27.90","risk_zh":"收盘低于 27.90","reason":"Extended. Wait for a pullback.","reason_zh":"已拉伸，等待回调。","lens":"Early leadership"},
 {"symbol":"CRDO","name":"Credo Technology","sector":"Semiconductors","price":"88.14","move":"Quote stale","status":"Entry unverified","status_zh":"入场未核实","tone":"muted","stage":"Needs refresh","stage_zh":"待刷新","chart":"stale","entry":"80.14–86.90","risk":"Close below 79.80","risk_zh":"收盘低于 79.80","reason":"A stale quote cannot confirm entry.","reason_zh":"过期报价无法确认入场。","lens":"Early leadership"}
]
def design(theme="light",mobile=False,zh=False):
    width=390 if mobile else 1440
    ops=[]
    def L(en,cn):return cn if zh else en
    def add(key,parent,inner="",style=""):
        html='<div layer-name="'+key+'" data-slot="'+key+'" style="display:flex;flex-direction:column;'+style+'">'+inner+'</div>'
        ops.append({"key":key,"parent":parent,"html":html})
    muted=v(theme,"muted");ink=v(theme,"text");line=v(theme,"line-quiet");panel=v(theme,"panel")
    if mobile:
        status=STATUS_BAR.replace("color: white", "color: "+ink).replace('fill="white"', 'fill="'+ink+'"')
        ops.append({"key":"Status bar","parent":"artboard","html":status})
    brand=row('<div style="display:flex;align-items:center;justify-content:center;width:25px;height:25px;border-radius:7px;background:'+v(theme,"info")+';color:#FFFFFF;">'+text("M",16,800)+'</div>'+text("MASTERMINDX",13,700,ink,"letter-spacing:0.08em;"),9)
    if mobile:
        nav=row(brand+row(svg("search",ink,20)+svg("menu",ink,20),20),10,"justify-content:space-between;width:100%;")
    else:
        items=row("".join(text(x,13,600 if i==0 else 400,ink if i==0 else muted) for i,x in enumerate(["United States","China","Hong Kong","Canada","International","Other Assets","Research"])),18)
        search=row(svg("search",muted,16)+text("Search tickers",13,400,muted),8,"width:150px;padding:10px 12px;border:1px solid "+line+";border-radius:8px;")
        nav=row(brand+items+row(search+button("Terminal",theme,False,"external")+svg("settings",ink,19),12,"padding-left:12px;"),28,"width:100%;justify-content:space-between;")
    add("R8 Global navigation","artboard",nav,"height:64px;justify-content:center;padding:0 "+("20" if mobile else "40")+"px;background:"+panel+";border-bottom:1px solid "+line+";")
    add("R8 Main","artboard","","padding:"+("24px 20px 32px" if mobile else "32px 40px 48px")+";gap:"+("16px" if mobile else "24px")+";")
    title=text(L("US EQUITY INTELLIGENCE","美股市场情报"),11,600,muted,"letter-spacing:0.12em;")+row(text("Prophet",28 if mobile else 38,700,ink,"letter-spacing:-0.04em;")+text(L("US stocks","美国股票"),15,400,muted),14)
    meta=text(L("Data through 30 Oct 2026","数据截至 2026年10月30日"),12,500,muted)+text(L("After the close · US","美股 · 盘后"),12,400,muted)
    heading=row('<div style="display:flex;flex-direction:column;gap:5px;">'+title+'</div>'+('<div style="display:flex;align-items:center;gap:20px;">'+meta+button(L("Ask Mastermind","问操盘大脑"),theme,False,"spark")+'</div>' if not mobile else button(L("Ask","提问"),theme,False,"spark")),12,"justify-content:space-between;align-items:center;")
    add("R8 Masthead","R8 Main",heading+(row(meta,12,"flex-wrap:wrap;") if mobile else ""),"gap:10px;")
    brief_left=row('<div style="width:8px;height:8px;border-radius:50%;background:'+v(theme,"warn")+';"></div>'+text(L("Mixed market","市场分化"),14,600,v(theme,"ink-warn"))+text(L("Keep positions smaller. Protect gains.","缩小仓位，保护收益。"),13,400,muted),10,"flex-wrap:wrap;")
    brief_right=row(pill(L("Reflation","再通胀"),theme)+pill(L("Defensive","防御姿态"),theme)+text(L("Risk radar →","风险雷达 →"),12,600,v(theme,"link")),10,"flex-wrap:wrap;")
    add("R8 Market brief","R8 Main",brief_left+brief_right,"flex-direction:"+("column" if mobile else "row")+";align-items:"+("flex-start" if mobile else "center")+";justify-content:space-between;gap:12px;padding:14px 16px;border:1px solid "+line+";border-radius:12px;background:"+panel+";")
    navlinks=[]
    for i,label in enumerate([L("Opportunities","机会"),L("Market context","市场背景"),L("Sector timing","板块择时"),L("Track record ↗","历史表现 ↗")]):
        navlinks.append('<div style="display:flex;align-items:center;min-height:36px;'+("width:calc(50% - 6px);" if mobile else "")+'padding:6px 10px;border-radius:7px;background:'+(v(theme,"panel2") if i==0 else "transparent")+';">'+text(label,12,600 if i==0 else 500,ink if i==0 else muted)+'</div>')
    add("R8 Section navigation","R8 Main","".join(navlinks),"flex-direction:row;flex-wrap:wrap;gap:4px 12px;")
    wsheading=row(text(L("Opportunity workspace","机会工作台"),19,600,ink,"letter-spacing:-0.02em;")+text(L("Open Screener →","打开筛选器 →"),12,600,v(theme,"link")),12,"justify-content:space-between;")
    tabs=row("".join('<div style="display:flex;justify-content:center;padding:9px '+("18" if mobile else "20")+'px;border-radius:7px;background:'+(panel if i==0 else "transparent")+';'+("flex:1;" if mobile else "")+'">'+text(label,13,600,ink if i==0 else muted)+'</div>' for i,label in enumerate([L("Today","今日"),L("Screener","筛选器"),L("Plans","计划") ])),4,"padding:4px;border:1px solid "+line+";border-radius:10px;background:"+v(theme,"panel2")+";"+("width:100%;" if mobile else ""))
    add("R8 Workspace header","R8 Main",wsheading+tabs,"gap:12px;"+("" if mobile else "flex-direction:row;align-items:center;justify-content:space-between;"))
    guidance=row(text(L("<b>3</b> ready · <b>7</b> developing · <b>6</b> unavailable","<b>3</b> 项就绪 · <b>7</b> 项酝酿中 · <b>6</b> 项不可用"),13,400,muted)+text(L("Review the current entry conditions.","仍需审视当前入场条件。"),12,400,muted),12,"justify-content:space-between;flex-wrap:wrap;")
    add("R8 Board guidance","R8 Main",guidance,"padding-bottom:2px;")
    add("R8 Opportunity grid","R8 Main","","flex-direction:"+("column" if mobile else "row")+";gap:16px;align-items:stretch;")
    for i,c in enumerate(CARDS):
        key="R8 Card "+c["symbol"]
        add(key,"R8 Opportunity grid","","width:"+("100%" if mobile else "328px")+";min-width:0;flex-shrink:0;gap:14px;padding:18px;border:1px solid "+line+";border-radius:12px;background:"+panel+";")
        moveTone="muted" if i==3 else ("ink-up" if c["move"].startswith("+") else "ink-down")
        identity='<div style="display:flex;flex-direction:column;gap:2px;">'+text(c["symbol"],18,700,ink)+text(c["name"],12,500,muted)+'</div>'
        price='<div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px;">'+text("$"+c["price"],22,600,ink,"letter-spacing:-0.035em;")+text(L(c["move"],"报价过期" if i==3 else c["move"]),12,500,v(theme,moveTone))+'</div>'
        add(key+" identity",key,row(identity+price,10,"justify-content:space-between;align-items:flex-start;")+text(L("Quote time unavailable","报价时间不可用"),10,400,muted),"gap:5px;")
        state=row(pill(L(c["status"],c["status_zh"]),theme,c["tone"])+text(L("Maturity · "+c["stage"]+" ↗","成熟度 · "+c["stage_zh"]+" ↗"),11,500,v(theme,"link")),8,"justify-content:space-between;")
        add(key+" status",key,state+text(L("Signal time unavailable","信号时间不可用"),10,400,muted),"gap:5px;")
        add(key+" chart",key,chart(theme,c["chart"])+row(text(L("Daily closes","日收盘价"),10,400,muted)+text(L("30 Oct 2026","2026-10-30"),10,400,muted),8,"justify-content:space-between;"),"gap:5px;")
        terms='<div style="display:flex;flex-direction:column;gap:8px;">'+row(text(L("Entry zone","入场区间"),11,500,muted)+text("$"+c["entry"],12,600,ink),8,"justify-content:space-between;")+row(text(L("Invalidation","失效条件"),11,500,muted)+text(L(c["risk"],c["risk_zh"]),11,500,ink),8,"justify-content:space-between;")+'</div>'
        add(key+" terms",key,terms+text(L("Terms date unavailable","条款日期不可用"),10,400,muted)+text(L(c["reason"],c["reason_zh"]),12,400,muted),"gap:8px;min-height:98px;padding-top:4px;")
        add(key+" actions",key,row(row('<div style="width:14px;height:14px;border:1px solid '+v(theme,"line")+';border-radius:3px;"></div>'+text(L("Compare","对比"),11,500,muted),6)+button(L("Open setup","打开形态"),theme,False,"arrow")+text(L("Sources","来源"),11,600,v(theme,"link")),8,"justify-content:space-between;"),"padding-top:2px;")
    add("R8 Complete board link","R8 Main",row(text(L("View all 16 candidates →","查看全部 16 个候选 →"),13,600,v(theme,"link"))+text(L("Priority describes readiness, not the probability of a win.","优先级描述形态准备程度，并非获胜概率。"),12,400,muted),16,"flex-wrap:wrap;justify-content:space-between;"),"padding-bottom:6px;")
    add("R8 Context heading","R8 Main",row(text(L("Market context","市场背景"),22,600,ink,"letter-spacing:-0.025em;")+text(L("The backdrop for your next decision","为下一步判断提供背景"),12,400,muted),14,"flex-wrap:wrap;"),"padding-top:10px;")
    add("R8 Context grid","R8 Main","","flex-direction:"+("column" if mobile else "row")+";gap:20px;align-items:stretch;")
    add("R8 Regime panel","R8 Context grid","","width:"+("100%" if mobile else "860px")+";gap:18px;padding:22px;border:1px solid "+line+";border-radius:12px;background:"+panel+";")
    add("R8 Regime heading","R8 Regime panel",row(text(L("Where the regime is headed","周期走向"),16,600,ink)+pill(L("Modeled","模型推演"),theme,"ink-warn"),12,"justify-content:space-between;"))
    add("R8 Regime readings","R8 Regime panel",row('<div style="display:flex;flex:1;flex-direction:column;gap:4px;">'+text(L("GROWTH","增长"),10,600,muted,"letter-spacing:0.08em;")+text("1.3% ↗",26,600,ink)+text(L("Accelerating · low base","加速 · 低基数"),12,400,muted)+'</div><div style="display:flex;flex:1;flex-direction:column;gap:4px;">'+text(L("INFLATION","通胀"),10,600,muted,"letter-spacing:0.08em;")+text("2.8% ↗",26,600,ink)+text(L("Accelerating · low base","加速 · 低基数"),12,400,muted)+'</div>',20))
    paths=[]
    for n,label in enumerate([L("Reflation","再通胀"),L("Goldilocks","金发姑娘"),L("Goldilocks","金发姑娘")]):
        paths.append('<div style="display:flex;flex:1;min-width:0;flex-direction:column;gap:5px;padding:10px 12px;border-radius:8px;background:'+v(theme,"panel2")+';">'+text("+"+str(n+1)+"Q",10,600,muted)+text(label,12,600,v(theme,"ink-warn" if n==0 else "ink-up"))+'</div>')
    add("R8 Regime path","R8 Regime panel",row("".join(paths),8)+text(L("Base effects describe a possible path. They are not a forecast guarantee.","基数效应描述一种可能路径，并非确定性预测。"),11,400,muted),"gap:10px;")
    add("R8 Breadth panel","R8 Context grid","","width:"+("100%" if mobile else "480px")+";gap:18px;padding:22px;border:1px solid "+line+";border-radius:12px;background:"+panel+";")
    add("R8 Breadth heading","R8 Breadth panel",row(text(L("Market participation","市场参与度"),16,600,ink)+text("S&P 1500",11,500,muted),12,"justify-content:space-between;"))
    add("R8 Breadth bar","R8 Breadth panel",row('<div style="display:flex;flex-direction:column;gap:2px;">'+text("571",28,600,v(theme,"ink-up"))+text(L("Advancing","上涨"),11,400,muted)+'</div><div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px;">'+text("923",28,600,v(theme,"ink-down"))+text(L("Declining","下跌"),11,400,muted)+'</div>',12,"justify-content:space-between;")+'<div style="display:flex;width:100%;height:6px;border-radius:3px;overflow:hidden;"><div style="width:38%;background:'+v(theme,"up")+';"></div><div style="width:62%;background:'+v(theme,"down")+';"></div></div>',"gap:10px;")
    add("R8 Breadth metrics","R8 Breadth panel",row('<div style="display:flex;flex:1;flex-direction:column;gap:3px;">'+text("55%",20,600,ink)+text(L("Above 50-day","高于50日均线"),11,400,muted)+'</div><div style="display:flex;flex:1;flex-direction:column;gap:3px;">'+text("54%",20,600,ink)+text(L("Above 200-day","高于200日均线"),11,400,muted)+'</div><div style="display:flex;flex:1;flex-direction:column;gap:3px;">'+text("+45",20,600,v(theme,"ink-up"))+text(L("Net new highs","净新高"),11,400,muted)+'</div>',12))
    add("R8 Theme heading","R8 Main",row(text(L("Theme action map","主题行动图"),18,600,ink)+text(L("38 groups · Sector Intelligence →","38 个分组 · 行业情报 →"),12,500,v(theme,"link")),12,"justify-content:space-between;flex-wrap:wrap;"),"padding-top:10px;")
    add("R8 Theme lanes","R8 Main","","flex-direction:"+("column" if mobile else "row")+";border:1px solid "+line+";border-radius:12px;background:"+panel+";overflow:hidden;")
    lanes=[("Buy now","可关注","3","ink-up",["Consumer Staples","Real Estate","Utilities"]),("Almost ready","接近就绪","1","info",["GLP-1 & Obesity"]),("Wait for a pullback","等待回调","7","ink-warn",["Regional Banks","Payments & Fintech"]),("Take profits","落袋为安","1","ink-warn",["Cybersecurity"]),("Stand aside","暂时观望","26","muted",["US Energy Complex","Big Pharma"])]
    zh_names={"Consumer Staples":"必需消费品","Real Estate":"房地产","Utilities":"公用事业","GLP-1 & Obesity":"GLP-1 与肥胖治疗","Regional Banks":"区域银行","Payments & Fintech":"支付与金融科技","Cybersecurity":"网络安全","US Energy Complex":"美国能源产业","Big Pharma":"大型制药","Financials":"金融","Technology":"信息技术","Energy":"能源","Health Care":"医疗保健","Materials":"原材料"}
    for idx,(en,cn,num,tone,names) in enumerate(lanes):
        add("R8 Theme lane "+str(idx),"R8 Theme lanes",row(text(L(en,cn),12,600,v(theme,tone))+text(num,12,600,muted),8,"justify-content:space-between;")+''.join(text(L(x,zh_names.get(x,x)),12,500,ink) for x in names)+text(L("View group →","查看分组 →"),11,500,v(theme,"link")),"width:"+("100%" if mobile else "272px")+";gap:13px;padding:18px;"+("border-top:1px solid "+line+";" if idx and mobile else ("border-left:1px solid "+line+";" if idx else "")))
    add("R8 Sector heading","R8 Main",row(text(L("Sector timing","板块择时"),22,600,ink,"letter-spacing:-0.025em;")+text(L("Short-term setups · Full board →","短线形态 · 完整看板 →"),12,500,v(theme,"link")),12,"justify-content:space-between;flex-wrap:wrap;"),"padding-top:12px;")
    add("R8 Sector table","R8 Main","","border:1px solid "+line+";border-radius:12px;background:"+panel+";overflow:hidden;")
    if not mobile:
        cols=[("Sector",290),("Current read",560),("Trend",260),("3mo vs market",170)]
        add("R8 Sector columns","R8 Sector table","".join('<div style="width:'+str(w)+'px;flex-shrink:0;">'+text(label,11,600,muted)+'</div>' for label,w in cols),"flex-direction:row;padding:12px 20px;background:"+v(theme,"panel2")+";")
    sectors=[("XLF","Financials","Setup","Approaching an up-cross","info","200d + 50d","−0.2%"),("XLK","Technology","Neutral","In trend; no fresh edge","muted","200d only","−2.1%"),("XLE","Energy","Extended","Late in the move; protect gains","ink-warn","200d + 50d","+22.5%"),("XLV","Health Care","Extended","Stretched and still rising","ink-warn","200d + 50d","+16.6%"),("XLP","Consumer Staples","Riding","Weekly cycle has turned up","info","200d + 50d","+7.3%"),("XLB","Materials","Extended","Wait for the next clean base","ink-warn","200d + 50d","+3.7%")]
    zh_details={"Setup":"酝酿","Neutral":"中性","Extended":"已拉伸","Riding":"顺势","Approaching an up-cross":"接近上穿","In trend; no fresh edge":"趋势中，暂无新优势","Late in the move; protect gains":"行情后段，保护收益","Stretched and still rising":"已拉伸，仍在上行","Weekly cycle has turned up":"周线周期已转强","Wait for the next clean base":"等待下一个清晰底部","200d + 50d":"200日 + 50日","200d only":"仅200日"}
    for idx,(symbol,name,state,detail,tone,trend,rs) in enumerate(sectors):
        name=L(name,zh_names.get(name,name));state=L(state,zh_details.get(state,state));detail=L(detail,zh_details.get(detail,detail));trend=L(trend,zh_details.get(trend,trend))
        a=row(text(symbol,13,600,v(theme,"link"))+text(name,12,500,ink),8)
        b=row(pill(state,theme,tone)+text(detail,12,400,muted),10,"flex-wrap:wrap;")
        if mobile:contents=row(a+pill(state,theme,tone),10,"justify-content:space-between;flex-wrap:wrap;")+text(detail,12,400,muted)+row(text(trend,11,500,muted)+text(rs+" "+L("vs market","对比市场"),12,600,v(theme,"ink-up" if rs.startswith("+") else "ink-down")),12,"justify-content:space-between;")
        else:contents=''.join('<div style="display:flex;align-items:center;width:'+str(w)+'px;flex-shrink:0;">'+content+'</div>' for w,content in [(290,a),(560,b),(260,text(trend,12,500,muted)),(170,text(rs,13,600,v(theme,"ink-up" if rs.startswith("+") else "ink-down")))])
        add("R8 Sector row "+symbol,"R8 Sector table",contents,"flex-direction:"+("column" if mobile else "row")+";gap:"+("10px" if mobile else "0")+";padding:16px 20px;border-top:1px solid "+line+";")
    add("R8 Turn setups","R8 Main",row(text(L("Turn setups","拐点形态"),18,600,ink)+pill(L("Unavailable","暂不可用"),theme),12,"justify-content:space-between;")+text(L("The nightly checklist could not load. This does not mean there are no qualifying stocks.","夜间检查表未能加载。这并不代表没有符合条件的股票。"),13,400,muted)+row(button(L("Try again","重试"),theme)+text(L("Early bottoming context · not a buy list","早期筑底参考 · 非买入清单"),11,400,muted),12,"flex-wrap:wrap;"),"gap:14px;padding:22px;border:1px solid "+line+";border-radius:12px;background:"+panel+";")
    add("R8 Research links","R8 Main",row(text(L("Continue your research","继续研究"),17,600,ink)+text(L("Market leaders →","市场领跑者 →"),12,500,v(theme,"link"))+text(L("Fresh triggers →","最新触发 →"),12,500,v(theme,"link"))+text(L("Real fund moves →","基金真实动作 →"),12,500,v(theme,"link"))+text(L("Pick Lab ↗","选股实验室 ↗"),12,500,v(theme,"link"))+text(L("Alerts ↗","提醒 ↗"),12,500,v(theme,"link")),20,"justify-content:space-between;flex-wrap:wrap;"),"padding:8px 0;")
    add("R8 Footer","R8 Main",row(text(L("Track record ↗","历史表现 ↗"),12,600,v(theme,"link"))+text(L("What changed today →","今日变化 →"),12,500,v(theme,"link")),20,"flex-wrap:wrap;")+text(L("Design illustration · sample data and state coverage, not current signals. System model plans are not your holdings or fills.","设计示例 · 数据和状态仅供设计审视，并非当前信号。系统模型计划并非你的持仓或成交。"),11,400,muted),"gap:14px;padding-top:22px;border-top:1px solid "+line+";")
    if zh:
        for op in ops:
            op["html"]=op["html"].replace("font-family:Inter;","font-family:PingFang SC;")
            for prefix in ("--mx-"+theme+"-ink-", "--mx-"+theme+"-"):
                op["html"]=op["html"].replace(prefix+"up)",prefix+"DIRECTIONTEMP)").replace(prefix+"down)",prefix+"up)").replace(prefix+"DIRECTIONTEMP)",prefix+"down)")
    return {"name":"R8 Full Prophet · "+str(width)+" · "+theme.title()+" · "+("ZH" if zh else "EN")+" · design illustration","width":width,"theme":theme,"locale":"zh" if zh else "en","operations":ops}

plans=[]
for theme,mobile,zh in [("light",False,False),("dark",False,False),("light",True,False),("dark",True,True)]:
    plan=design(theme,mobile,zh);plans.append(plan)
    body=BeautifulSoup('<div data-slot="artboard" style="display:flex;flex-direction:column;width:'+str(plan["width"])+'px;background:'+v(theme,"bg")+';font-family:Inter,-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:'+v(theme,"text")+';"></div>',"html.parser")
    for op in plan["operations"]:
        parent=body.select_one('[data-slot="'+op["parent"]+'"]')
        assert parent is not None,op["parent"]
        parent.append(BeautifulSoup(op["html"],"html.parser"))
    variables="".join("--mx-"+t+"-"+key+":"+value+";" for t,values in TOKENS.items() for key,value in values.items())+"--font-ui:Inter;"
    html='<!doctype html><html lang="'+plan["locale"]+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(plan["name"])+'</title><style>:root{'+variables+'}*{box-sizing:border-box}body{margin:0;background:'+TOKENS[theme]["bg"]+'}svg{display:block;flex-shrink:0}button,input{font:inherit}</style><body>'+str(body)+'</body></html>'
    label=str(plan["width"])+"-"+theme+"-"+plan["locale"]
    (OUT/(label+".html")).write_text(html)
    (OUT/(label+".json")).write_text(json.dumps(plan,indent=2,ensure_ascii=False))
print(json.dumps({"output":str(OUT),"variants":len(plans),"operations":[len(x["operations"]) for x in plans],"paper_mutations":0}))
