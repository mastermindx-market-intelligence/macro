"""Render the real News partial and real shared mx5 host into an isolated fixture.

Synthetic representative data, explicit fixture auth, no production session.
The full production build is independently gated by CI.
"""
from pathlib import Path
import json, re, base64
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.qa'
OUT.mkdir(exist_ok=True)
env = Environment(loader=FileSystemLoader(ROOT/'templates'))
alerts = [
 dict(rule='gex_flip',tier='watch',severity='warn',plain_en='Options “gravity” flipped — bigger swings more likely',plain_zh='期权“重力”翻转 — 波动可能加剧',message='GEX: spot crossed the gamma flip (net −71bn, spot vs flip +0.3%) — measured across 4 sessions; no chain snapshots for Oct 27–29, so the crossing point is unobserved.',message_zh='GEX：现货穿越 gamma 翻转位（净值 −710 亿，现货较翻转位 +0.3%）— 跨 4 个交易日观测；10 月 27–29 日无期权链快照，具体穿越时点不可见。',edge_en='Changes the volatility backdrop, not the direction.',edge_zh='改变波动背景，并不代表方向。',what_en='Dealer gamma measures how options hedging pushes the market around. Positive gamma dampens moves; negative gamma amplifies them in both directions.',what_zh='交易商 gamma 衡量期权对冲对市场的影响。正 gamma 抑制波动；负 gamma 会放大双向波动。'),
 dict(rule='event_risk',tier='context',severity='warn',plain_en='A major event is on deck',plain_zh='重大事件临近',message='Event-risk window: Jobs report (nonfarm payrolls) in 5 days — two-sided volatility expected.',message_zh='事件风险窗口：就业报告（非农就业）将在 5 天后发布 — 预计双向波动。',edge_en='A volatility window, not a direction call.',edge_zh='波动窗口，并非方向判断。',what_en='CPI, FOMC and jobs reports can move markets. Check the calendar for the event, scheduled date and official release status.',what_zh='CPI、FOMC 与就业报告可能影响市场。请核查事件日历、预定日期及官方发布状态。'),
 dict(rule='passive_flow',tier='context',plain_en='A sector ETF is overweighting a stock beyond its price move',plain_zh='行业 ETF 增持幅度超过股价变化',message='XLV: LLY weight +1.19pp beyond price (≈+$579M estimated rebalance flow), Oct 22–29.',message_zh='XLV：LLY 权重超出价格解释部分 +1.19 个百分点（约 +5.79 亿美元估计再平衡流量），10 月 22–29 日。',edge_en='Passive index flow, not discretionary conviction.',edge_zh='被动指数资金流，并非主动投资信念。',what_en='Separate market drift from the residual weight change. The residual can include index reconstitution and float changes, so it is context rather than a buy signal.'),
 dict(rule='sector_leader',tier='context',plain_en='A sector broke into leadership',plain_zh='行业进入领先区间',message='XLB relative strength versus SPY crossed the 90th percentile of its 90-day range (now 92).',message_zh='XLB 相对 SPY 强度突破 90 天区间第 90 百分位（当前 92）。',edge_en='Descriptive rotation, not a timing signal.',edge_zh='描述性轮动，并非择时信号。',what_en='Review sector heat and its trigger before acting.'),
 dict(rule='fund_move',tier='context',plain_en='A fund manager made a notable move',plain_zh='基金经理出现显著调仓',message='ARKK: manager cut GOOG by 31% of position (Oct 14–30, flow-normalized).',message_zh='ARKK：经理减持 GOOG 31%（10 月 14–30 日，已按资金流标准化）。',edge_en='What a manager did, not a recommendation to copy.',edge_zh='反映经理行为，不构成跟随建议。',what_en='Mechanical fund-flow effects are stripped out; disclosure windows still differ from live trading activity.')
]
headlines=[dict(title='Treasury yields move as investors reassess the rate outlook',title_zh='投资者重估利率前景，美债收益率变化',source='Example financial wire',url='https://example.org/report/1',seendate='2026-11-01T14:20:00Z',summary='Representative fixture report for layout and source-link testing. This is not a current market fact.',summary_zh='用于布局及来源链接测试的示例报道，并非当前市场事实。'),dict(title='Earnings and economic releases shape the week ahead',title_zh='企业业绩与经济数据影响未来一周',source='Example news desk',url='https://example.org/report/2',seendate='2026-10-31T10:00:00Z')]
source=(ROOT/'templates/dashboard.html.j2').read_text()
host=source.split('{# ── mx5OpenDlg dialog system')[1].split('<script>',1)[1].split('</script>',1)[0]
# Keep the genuine modal lifecycle and deep-link owner, before unrelated dashboard code.
style=source[source.index('body.mx5-dlg-open{'):source.index('/* Extra-narrow (320px)')]
lock='html.mx5-dlg-lock{overflow:hidden}html.mx5-dlg-lock body{position:fixed;width:100%;overflow:hidden}'
body=env.get_template('_macro_news_intelligence.html.j2').render(alerts=alerts,macro_news={'headlines':headlines},latest={})
theme=(ROOT/'templates/theme.css').read_text()
# Assets are not part of this isolated source fixture; font fallback is explicit.
theme=re.sub(r'@import[^;]+;','',theme)
theme=re.sub(r'@font-face\s*\{[^}]+\}','',theme)
font=OUT/'NotoSansCJKsc-Regular.otf'
if font.exists():
    theme += '@font-face{font-family:"Noto Sans CJK SC";font-weight:400;unicode-range:U+2E80-9FFF,U+F900-FAFF,U+FF00-FFEF,U+20000-2FFFF;src:url(data:font/otf;base64,' + base64.b64encode(font.read_bytes()).decode() + ') format("opentype");}'
html='''<!doctype html><html lang="en" data-theme="light" data-lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>News popup — source fixture</title><style>'''+theme+style+lock+'''body{margin:0;background:var(--bg);font-family:var(--font-ui)}.fixture-bg{padding:40px;max-width:1100px;margin:auto;color:var(--muted)}.fixture-bg h1{font-size:30px;color:var(--text)}.fixture-tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.fixture-tiles>div{height:190px;border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:20px}</style><style>'''+(ROOT/'templates/macro_news_intelligence.css').read_text()+'''</style></head><body class="page-macro"><div class="fixture-bg"><p>DESIGN & INTERACTION FIXTURE · REPRESENTATIVE DATA</p><h1>Market dashboard</h1><button id="trigger" onclick="mx5OpenDlg('dlg-news')">Open News intelligence</button><div class="fixture-tiles"><div>Market conditions</div><div>Risk radar</div><div>Economic events</div></div></div><div class="mx5-dlg" id="dlg-news" role="dialog" aria-labelledby="ni-dialog-title" tabindex="-1"><div class="mx5-dlg-backdrop" onclick="mx5CloseDlg()"></div><div class="mx5-dlg-panel"><div class="mx5-dlg-header"><span class="mx5-dlg-title" id="ni-dialog-title"><span class="l-en">News — Market Intelligence</span><span class="l-zh">新闻 — 市场情报</span></span><button class="mx5-dlg-close" onclick="mx5CloseDlg()" aria-label="Close">×</button></div><div class="mx5-dlg-body">'''+body+'''</div></div></div><div class="mx5-dlg" id="dlg-events" role="dialog" tabindex="-1"><div class="mx5-dlg-panel"><button onclick="mx5CloseDlg()">Close events</button><div class="mx5-dlg-body">Event calendar fixture</div></div></div><script>window.MMXAccessPreview={isAnon:()=>false};window.fetch=()=>new Promise(()=>{});</script><script>'''+host+'''</script><script>'''+(ROOT/'templates/macro_news_intelligence.js').read_text()+'''</script><script>'''+(ROOT/'templates/release_publications_live.js').read_text()+'''</script></body></html>'''
(OUT/'news-fixture.html').write_text(html)
print(json.dumps({'fixture':str(OUT/'news-fixture.html'),'alerts':len(alerts),'headlines':len(headlines),'host':'actual shared mx5 source','font':'system fallback'}))
