"""Offline component fixture using shipped Jinja chrome, CSS and JS owners.

Only library responses, logo enhancement and the external navigation/access
boundaries are synthetic. No customer session, credential, live data or network.
The same fixture is used by browser regression tests and the canonical capture
tool; it is explicitly not production acceptance.
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]


def source(name: str) -> str:
    root = Path(os.environ.get("MMX_POLISH_SOURCE_ROOT", ROOT))
    return (root / "templates" / name).read_text(encoding="utf-8")


def function(text: str, name: str) -> str:
    # These shipped functions have balanced braces, including their strings.
    start = text.index("function " + name + "(")
    depth = 0
    for index in range(text.index("{", start), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError("Unclosed shipped function: " + name)


def rows(market: str = "us", count: int = 26) -> list[dict]:
    if market != "us":
        return []
    return [
        {"t": f"A{i:03}", "n": f"Alpha Company {i}", "z": f"示例公司{i}",
         "v": 10000 - i, "st": "TURN SIGNALED"}
        for i in range(1, count + 1)
    ]


def assets(*, view: str = "rest") -> dict[str, tuple[str, str]]:
    theme = source("theme.js")
    dashboard = source("dashboard.html.j2")
    nav = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    chrome = nav.get_template("_site_nav.html.j2").render(
        t=lambda en, zh="": Markup(
            '<span class="l-en">' + html.escape(en) + '</span>'
            '<span class="l-zh">' + html.escape(zh) + "</span>"
        )
    )
    base_start = dashboard.index("<style>") + len("<style>")
    base_end = dashboard.index('{% include "_risk_radar_card.css.j2" %}', base_start)
    base_css = dashboard[base_start:base_end]
    mobile_css = theme[theme.index("  var NAV_MOBILE_CSS ="):theme.index("  function initMobileNav()")]
    market_constants = theme[theme.index("  var STOCK_MARKETS ="):theme.index("  function initNavDrills()")]
    search = function(theme, "initNavSearch")
    search_boot = """
var _mmSharedAssetRoot = '';
function curLang(){ return document.documentElement.getAttribute('data-lang') || 'en'; }
function ensureNavSearchCss(){ return true; }
function ensureNavLogoAssets(){}
function mmTerminalOn(){ return false; }
var TERMINAL_PAGES = {};
window.__navigations = [];
window.MMXSharedShell = {navigate:function(url, mode){ window.__navigations.push({url:url, mode:mode}); }};
window.MMXAccessPreview = {isAnon:function(){ return false; }};
window.setLang = function(lang){
  document.documentElement.setAttribute('data-lang', lang);
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.dispatchEvent(new CustomEvent('langchange', {detail:lang}));
};
window.setTheme = function(theme){ document.documentElement.setAttribute('data-theme',theme); };
""" + market_constants + mobile_css + function(theme, "initMobileNav") + function(theme, "initAdaptiveNav") + search + """
initMobileNav(); initAdaptiveNav(); initNavSearch();
"""
    # Exercise the real mx5 owner without the page's unrelated data integrations.
    script_marker = dashboard.index("  {# ── mx5OpenDlg dialog system")
    start = dashboard.index("<script>", script_marker) + len("<script>")
    end = dashboard.index("</script>", start)
    dialog_js = dashboard[start:end]
    css_start = dashboard.index("/* Scroll-lock while dialog open */")
    css_end = dashboard.index("/* ── S2: Dialog interior components", css_start)
    dialog_css = dashboard[css_start:css_end]
    link = re.search(r'<a class="wnx-card" href="#dlg-events"[^>]+>', dashboard)
    assert link, "Authored Week Ahead link must remain available"
    detail_rows = "".join(
        '<section class="panel"><h2><span class="l-en">Event ' + str(i) +
        '</span><span class="l-zh">日程 ' + str(i) +
        '</span></h2><p><span class="l-en">Synthetic fixture. Details are ready when the panel opens.</span>'
        '<span class="l-zh">交互测试示例。面板打开后即可阅读完整详情。</span></p>'
        '<button type="button" class="gbtn"><span class="l-en">Read details</span>'
        '<span class="l-zh">查看详情</span></button></section>' for i in range(1, 13)
    )
    auto = ""
    if view == "search":
        auto = """document.querySelector('.search-trigger').click();
document.querySelector('.ticker-input').value='a';
document.querySelector('.ticker-input').dispatchEvent(new Event('input',{bubbles:true}));"""
    elif view == "dialog":
        auto = "document.getElementById('fixture-dialog-open').click();"
    page = """<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Macro interaction fixture — synthetic content</title>
<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="dashboard-base.css">
<link rel="stylesheet" href="navigation-refresh.css">
<link rel="stylesheet" href="product-nav-icons.css"><link rel="stylesheet" href="dialog.css">
</head><body class="page-macro"><div class="wrap">""" + chrome + """
<main><section class="panel"><h1><span class="l-en">Macro interaction fixture</span>
<span class="l-zh">宏观面板交互测试</span></h1>
<p><span class="l-en">Synthetic content · shipped interface components</span>
<span class="l-zh">示例内容 · 实际界面组件</span></p>
<button id="fixture-dialog-open" class="gbtn" onclick="mx5OpenDlg('dlg-events')">
<span class="l-en">Open week ahead</span><span class="l-zh">查看本周日历</span></button>
""" + link.group(0).replace('class="wnx-card"', 'id="fixture-native-link" class="gbtn"') + """
<span class="l-en">Week ahead link</span><span class="l-zh">本周日历链接</span></a>
<button class="gbtn" id="outside">Outside control</button></section>
<div aria-hidden="true" style="height:1200px"></div></main></div>
<div class="mx5-dlg" id="dlg-events" role="dialog" aria-labelledby="fixture-title" tabindex="-1">
<div class="mx5-dlg-backdrop"></div><div class="mx5-dlg-panel">
<div class="mx5-dlg-header"><span class="mx5-dlg-title" id="fixture-title">
<span class="l-en">Week ahead</span><span class="l-zh">未来一周</span></span>
<button class="mx5-dlg-close" type="button" onclick="mx5CloseDlg()" aria-label="Close">×</button></div>
<div class="mx5-dlg-body">""" + detail_rows + """</div></div></div>
<script src="interaction.js"></script><script src="dialog.js"></script>
<script>""" + auto + """</script></body></html>"""
    return {
        "macro.html": (page, "text/html"),
        "theme.css": (source("theme.css"), "text/css"),
        "dashboard-base.css": (base_css, "text/css"),
        "navigation-refresh.css": (source("navigation-refresh.css"), "text/css"),
        "product-nav-icons.css": (source("product-nav-icons.css"), "text/css"),
        "dialog.css": (dialog_css, "text/css"),
        "interaction.js": (search_boot, "text/javascript"),
        "dialog.js": (dialog_js, "text/javascript"),
    }
