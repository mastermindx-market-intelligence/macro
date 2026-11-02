"""Render real dashboard templates with incumbent synthetic host fixtures.

These are integration-fixture proofs, NOT full producer builds or production
acceptance. The brief JSONs are real committed artifacts with their old dates.
Only fixture URLs are intercepted; assets come from the owning local site tree.
"""
from __future__ import annotations

import functools
import http.server
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def render_hosts():
    from jinja2 import Environment, FileSystemLoader, ChainableUndefined
    from engine import i18n
    from engine.china_tier1 import hero_clause, posture_lane, posture_tone, reason_faces
    from engine.hk_tier1 import cycle_lane
    from tests.test_dashboard_template_render import _env, _base_vm
    from tests.test_hk_board_ui import _vm
    from tests.test_china_delayed_board_disclosure import _Loose

    read = lambda name: json.loads((ROOT / 'site' / name).read_text())
    macro_vm = _base_vm()
    macro_vm['master_brief'] = read('master_brief.json')
    macro = _env().get_template('dashboard.html.j2').render(**macro_vm, mode='macro')
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=False,
                      undefined=ChainableUndefined)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t, t_pctile=i18n.t_pctile,
                      posture_lane=posture_lane, posture_tone=posture_tone,
                      reason_faces=reason_faces, hero_clause=hero_clause, cycle_lane=cycle_lane)
    hk_vm = _vm(None, 'macro')
    hk_vm['china_brief'] = read('china_brief.json')
    hk = env.get_template('hk.html.j2').render(**hk_vm)
    china = env.get_template('china.html.j2').render(
        mode='macro', board_staleness=None,
        latest=_Loose(date='2026-08-06', quad_name='Goldilocks'),
        market_state=_Loose(color='yellow'), sectors=[], china_brief=read('china_brief.json'))
    return {'macro': macro, 'china': china, 'hk': hk}


def main() -> int:
    from playwright.sync_api import sync_playwright
    hosts = render_hosts()
    out = ROOT / 'mockups/evidence/aibrief-abx3/host-fixtures'
    out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'site'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    report = {'scope': 'real full templates + incumbent synthetic host view-model fixtures + committed dated briefs; NOT production or full producer builds', 'states': []}
    ids = {'macro': ('mx5', 'dlg-aibrief'), 'china': ('cnx', 'cnx-dlg-aibrief'), 'hk': ('hkx', 'hkx-dlg-aibrief')}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for host, html in hosts.items():
                    prefix, dialog_id = ids[host]
                    for width in (1440, 390):
                        for theme in ('dark', 'light'):
                            for language in ('en', 'zh'):
                                context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                                context.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(language)});")
                                errors = []
                                def route(request):
                                    url = request.request.url
                                    if url == origin + '/abx3-host-fixture.html':
                                        request.fulfill(status=200, content_type='text/html', body=html)
                                    elif url.startswith(origin + '/'):
                                        request.continue_()
                                    else:
                                        request.abort()
                                context.route('**/*', route)
                                page = context.new_page()
                                page.on('pageerror', lambda error: errors.append(str(error)))
                                page.goto(origin + '/abx3-host-fixture.html', wait_until='domcontentloaded')
                                page.wait_for_function("document.querySelector('[data-aib-freshness]')?.dataset.state")
                                opener = page.locator('[onclick="' + prefix + "OpenDlg('" + dialog_id + "')\"]").first
                                dialog = page.locator('#' + dialog_id)
                                if host == 'macro':
                                    # The local fixture has no real login. Verify the anonymous
                                    # guard, then supply a clearly synthetic registered-reader
                                    # response to the existing display gate. This grants no
                                    # service entitlement and is never production auth proof.
                                    page.evaluate("window.MMXAccessPreview={isAnon:()=>true,openSignin:()=>{window.__abxAuthPrompt=true;}};window.MMXSharedShell={openAuth:()=>{window.__abxAuthPrompt=true;}}")
                                    opener.click(timeout=15000)
                                    assert not dialog.is_visible()
                                    assert page.evaluate('window.__abxAuthPrompt === true')
                                    page.evaluate('window.MMXAccessPreview.isAnon=()=>false')
                                opener.click(timeout=15000)
                                dialog.wait_for(state='visible')
                                page.wait_for_timeout(400)
                                assert dialog.locator('[data-aib-freshness]').get_attribute('data-state') == 'old'
                                # This measures the actual open dialog, not unrelated synthetic page content.
                                geometry = dialog.locator('.' + prefix + '-dlg-panel').evaluate('(n) => {const r=n.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,viewport:innerWidth,scroll:n.scrollWidth,client:n.clientWidth};}')
                                assert geometry['left'] >= -1 and geometry['right'] <= geometry['viewport'] + 1, geometry
                                assert geometry['scroll'] <= geometry['client'] + 1, geometry
                                assert dialog.locator('div,p,section,header,details,summary,li,dl,dt,dd,article').evaluate_all("nodes => nodes.every(n => {const s=getComputedStyle(n);return s.borderLeftWidth===s.borderRightWidth && (parseFloat(s.borderLeftWidth)===0 || s.borderLeftColor===s.borderRightColor);})"), 'Asymmetric container edge in the actual dialog'
                                file = f'{host}-{width}-{theme}-{language}.png'
                                page.screenshot(path=out / file)
                                summary = dialog.locator('.aib2-details summary').first
                                summary.focus()
                                page.keyboard.press('Enter')
                                assert summary.locator('..').get_attribute('open') is not None
                                page.keyboard.press('Escape')
                                page.wait_for_function('(id)=>!document.getElementById(id).classList.contains("open")', arg=dialog_id)
                                report['states'].append({'host': host, 'width': width, 'theme': theme, 'language': language,
                                    'passed': True, 'file': file, 'geometry': geometry, 'page_errors': errors})
                                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'states': len(report['states']), 'passed': sum(s['passed'] for s in report['states']), 'report': str(out / 'report.json')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
