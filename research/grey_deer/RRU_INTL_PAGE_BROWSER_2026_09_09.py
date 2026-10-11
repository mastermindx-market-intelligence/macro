"""Full owning page and real risk-dialog controls, with qualified mapping supplied.

This deliberately isolates presentation. The original adapter and machine view are
NOT repaired or replaced; their separate failing journey suite remains authoritative.
The real page writer writes only under this new local synthetic fixture directory.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch
import hashlib
import json
from playwright.sync_api import sync_playwright
import RRU_INTL_JOURNEY_TESTS_2026_09_09 as j
from lib import pages,config

OUT=Path(__file__).parent/'rru_intl_page_browser_20260909'
OUT.mkdir(exist_ok=False)
SITE=OUT/'site'; SITE.mkdir()
TEMPLATES=OUT/'templates'; TEMPLATES.mkdir()
j.a.apply_bundle(j.candidate.bundle)
assets={name:j.pinned('templates/'+name) for name in
        ('theme.css','product-nav-icons.css','theme.js','data_base.js')}
for name,text in assets.items():
    (TEMPLATES/name).write_text(text)
    (SITE/name).write_text(text)
fixtures={}
writer_ids={}
for cc in j.dashboard.REGIONS:
    for case in ('complete','partial','unavailable','legacy'):
        snap=j.snapshot(j.a.radar.PROFILES[cc.lower()],case)
        if case=='legacy': snap=dict(state='caution',drawdown_prob=dict(h21=.42))
        rec=j.record(cc,snap)
        view,rd,html=j.render(rec,force_direct=True)
        note='<p class="imd-method" data-fixture="synthetic"><span class="l-en">Synthetic presentation test. Adapter and machine-view repair remain open.</span><span class="l-zh">合成展示测试。适配器与机器视图仍待修复。</span></p>'
        html=html.replace('<main class="imd-shell">','<main class="imd-shell">'+note,1)
        name=f'{cc}-{case}.html'
        with patch.object(config,'ROOT',OUT.resolve()), \
             patch.object(config,'load',return_value={'storage':{'site_dir':str(SITE.resolve())}}), \
             patch.object(pages,'_shim_checked',False):
            pages.write_page(SITE/name,html,encoding='utf-8')
        fixtures[name]=dict(cc=cc,case=case,rd=rd)
        writer_ids[name]=hashlib.sha256((SITE/name).read_bytes()).hexdigest()

blocked=[]
def route_request(route):
    parsed=urlparse(route.request.url)
    name=parsed.path.lstrip('/')
    if route.request.method!='GET' or parsed.hostname!='rru-fixture.invalid' or '/' in name:
        blocked.append(route.request.url);route.abort();return
    target=SITE/name
    if target.is_file():
        kind='text/html' if name.endswith('.html') else ('text/css' if name.endswith('.css') else 'application/javascript')
        route.fulfill(status=200,content_type=kind+'; charset=utf-8',body=target.read_bytes())
    else:
        blocked.append(route.request.url);route.abort()
records=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    for width in (1440,390):
        for theme in ('dark','light'):
            for lang in ('en','zh'):
                context=browser.new_context(viewport=dict(width=width,height=1000))
                context.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                context.route('**/*',route_request)
                page=context.new_page();page.set_default_timeout(10000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                for name,fixture in fixtures.items():
                    errors.clear()
                    response=page.goto('https://rru-fixture.invalid/'+name,wait_until='load')
                    page.locator('.imd-radar').scroll_into_view_if_needed()
                    card=page.locator('.imd-radar').inner_text()
                    trigger=page.locator('[data-dialog="dlg-risk"]')
                    trigger.focus();page.keyboard.press('Enter')
                    page.wait_for_function("document.querySelector('#dlg-risk').getAttribute('aria-hidden')==='false'")
                    dialog=page.locator('#dlg-risk');text=dialog.inner_text()
                    modern=fixture['case']!='legacy'
                    expect='Forecast not available' if lang=='en' else '预测暂不可用'
                    coverage='Input coverage' if lang=='en' else '输入覆盖'
                    checks=dict(one_radar=page.locator('.rrx').count()==1,
                        qualified_dialog=(expect in text) if modern else ('42.0%' in text),
                        qualified_trigger=(coverage in trigger.inner_text()) if modern else True,
                        no_false_odds=('42.0%' not in text) if modern else True,
                        page_no_overflow=not page.evaluate('document.documentElement.scrollWidth>innerWidth'),
                        no_page_errors=not errors,
                        dialog_open=dialog.get_attribute('aria-hidden')=='false')
                    shot=None
                    if fixture['cc']=='JP':
                        shot=f"{fixture['case']}-{theme}-{lang}-{width}-dialog.png"
                        page.screenshot(path=str(OUT/shot),full_page=False)
                    page.keyboard.press('Escape')
                    page.wait_for_function("!document.querySelector('#dlg-risk').classList.contains('open')")
                    checks['focus_returned']=trigger.evaluate('e=>e===document.activeElement')
                    checks['dialog_closed']=dialog.get_attribute('aria-hidden')=='true'
                    records.append(dict(cc=fixture['cc'],case=fixture['case'],theme=theme,
                        lang=lang,width=width,checks=checks,errors=list(errors),
                        screenshot=shot,screenshot_sha256=hashlib.sha256((OUT/shot).read_bytes()).hexdigest() if shot else None,
                        html_sha256=writer_ids[name],background=page.evaluate('getComputedStyle(document.body).backgroundColor')))
                context.close()
    browser.close()
result=dict(kind='complete_template_synthetic_fixture',production=False,
    original_adapter_bypassed_only_in_fixture=True,machine_view_unrepaired=True,
    canonical_writer='lib.pages.write_page',cases=records,
    all_checks_pass=all(all(r['checks'].values()) for r in records),
    blocked_requests=sorted(set(blocked)),template_sources=j.READ_SOURCES,
    written_pages=writer_ids)
(OUT/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(cases=len(records),all_checks_pass=result['all_checks_pass'],
    failures=[r for r in records if not all(r['checks'].values())],screenshots=sum(r['screenshot'] is not None for r in records))))
raise SystemExit(0 if result['all_checks_pass'] else 1)
