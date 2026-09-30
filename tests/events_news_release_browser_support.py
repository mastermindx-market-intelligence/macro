"""Controlled component fixture, NOT the production mx5 modal manager.

All data is a pinned historical test extract. The shell supplies only open/close;
production focus trapping, inertness, deployment and account effects stay unproved.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TOKENS = '''
:root{--font-ui:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;--font-mono:ui-monospace,monospace;--fs-h1:28px;--fs-num-lg:22px;--fs-h2:17px;--fs-md:15px;--fs-body:14px;--fs-sm:12.5px;--fs-label:11px;--fs-micro:10px;--r-card:12px;--bg:#0f1115;--panel:#181b21;--panel2:#1e222a;--text:#d7dce3;--muted:#8b93a1;--line:#3a4150;--warn:#e0a030;--act:#e05555;--ok:#3da564;--info:#5b9bf0;--link:#7aa7e0;--card-shadow:0 1px 0 rgba(255,255,255,.02);--popover-shadow:0 6px 18px rgba(0,0,0,.5)}
html[data-theme="light"]{--bg:#f7f8fa;--panel:#fff;--panel2:#eef1f6;--text:#1c2430;--muted:#5d6b7e;--line:#c9ccd1;--warn:#b9791a;--act:#c43d3d;--ok:#2f8a52;--info:#285fff;--link:#285fff;--card-shadow:0 1px 3px rgba(20,30,50,.07);--popover-shadow:0 4px 10px rgba(20,30,50,.06),0 12px 28px rgba(20,30,50,.14)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}a{color:var(--link)}
.l-zh{display:none}html[data-lang="zh"] .l-en{display:none}html[data-lang="zh"] .l-zh{display:inline}
.mx5-dlg{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:10}.mx5-dlg[hidden]{display:none}.mx5-dlg-backdrop{position:absolute;inset:0;background:var(--bg);opacity:.75}.mx5-dlg-panel{position:relative;z-index:1}
.fixture-label{position:fixed;bottom:2px;inset-inline:0;text-align:center;font:10px var(--font-ui);color:var(--muted);z-index:20;pointer-events:none}
'''
STUB = '''
window.mx5CloseDlg=function(){document.getElementById('dlg-news').hidden=true;document.getElementById('fixture-open').focus();};
window.mx5OpenDlg=function(id){if(id==='dlg-news'){var r=document.getElementById(id);r.hidden=false;r.focus();}};
'''


def fixture_page(data, theme='light', lang='en', include_js=True):
    """Render real candidate templates/assets inside an explicit fixture shell."""
    if theme not in ('light', 'dark') or lang not in ('en', 'zh'):
        raise ValueError('Unsupported fixture appearance')
    component = Environment(loader=FileSystemLoader(ROOT/'templates')).get_template(
        '_macro_events_news.html.j2').render(**data)
    css = (ROOT/'templates/macro-events-news.css').read_text()
    js = (ROOT/'templates/macro-events-news.js').read_text() if include_js else ''
    return f'''<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Events & News — historical result component</title><style>{TOKENS}\n{css}</style></head><body><button id="fixture-open" onclick="mx5OpenDlg('dlg-news')">Open component</button>{component}<div class="fixture-label">HISTORICAL TEST FIXTURE · NOT LIVE DATA · CONTROLLED MODAL HOST</div><script>{STUB}</script><script>{js}</script></body></html>'''
