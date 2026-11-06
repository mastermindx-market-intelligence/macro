"""Browser-check actual isolated builder outputs, not a direct-mapper substitute."""
from __future__ import annotations
import hashlib
import json
import mimetypes
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright, expect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INPUT=HERE/'rru_intl_build_20260910_candidate-v2'
OUT=HERE/'rru_intl_built_browser_20260910'
PIN='eb9e91961ddc4f3043d0dad358602525e66eccda'
SOURCE=json.loads((INPUT/'receipt.json').read_text())

def sha(raw): return hashlib.sha256(raw).hexdigest()

EXTRA_ASSETS={'fonts/Inter-400.woff2','fonts/Inter-600.woff2',
              'fonts/Inter-700.woff2','fonts/Inter-800.woff2'}

def main():
    assert not SOURCE['failures'] and SOURCE['full_builder']
    OUT.mkdir(exist_ok=False)
    cached={}; served={}; blocked=set(); records=[]; screenshots=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context()
        cases={r['case'] for r in SOURCE['cases']}
        def route_request(route):
            request=route.request; url=urlsplit(request.url)
            if request.method!='GET' or url.hostname!='rru-synthetic.invalid':
                blocked.add(request.url); route.abort(); return
            parts=unquote(url.path).lstrip('/').split('/')
            if len(parts)<3 or parts[0] not in cases or parts[1]!='site':
                blocked.add(request.url); route.abort(); return
            rel='/'.join(parts[2:]); target=(INPUT/parts[0]/'site'/rel).resolve()
            if not target.is_relative_to(INPUT.resolve()):
                route.abort(); return
            if target.is_file():
                body=target.read_bytes()
            elif rel in EXTRA_ASSETS:
                if rel not in cached:
                    raw=subprocess.run(['git','show',f'{PIN}:templates/{rel}'],cwd=ROOT,
                        check=True,capture_output=True,timeout=30).stdout
                    cached[rel]=raw
                body=cached[rel]
            else:
                blocked.add(request.url); route.abort(); return
            served[rel]=sha(body)
            route.fulfill(status=200,body=body,content_type=mimetypes.guess_type(rel)[0] or 'text/plain')
        context.route('**/*',route_request)
        page=context.new_page(); page.set_default_timeout(10000)
        errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        for row in SOURCE['cases']:
            file=INPUT/row['case']/'site'/row['route']
            assert sha(file.read_bytes())==row['html_sha256']
            for width in (1440,390):
                page.set_viewport_size({'width':width,'height':1000})
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        errors.clear()
                        page.goto(f"https://rru-synthetic.invalid/{row['case']}/site/{row['route']}",wait_until='load')
                        page.evaluate("([t,l])=>{document.documentElement.setAttribute('data-theme',t);document.documentElement.setAttribute('data-lang',l)}",[theme,lang])
                        page.evaluate('document.fonts.ready')
                        modern=row['case'] not in ('legacy','absent')
                        expected_count=0 if row['case']=='absent' else 1
                        checks={'card_count':page.locator('.rrx').count()==expected_count,
                            'page_no_overflow':page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')}
                        trigger=page.locator("button[data-dialog='dlg-risk']")
                        trigger.click()
                        dialog=page.locator('#dlg-risk'); panel=dialog.locator('.imd-panel')
                        expect(dialog).to_have_attribute('aria-hidden','false')
                        expect(panel).to_be_in_viewport(ratio=.95)
                        page.wait_for_function("""() => {
                            const p=document.querySelector('#dlg-risk .imd-panel');
                            const r=p.getBoundingClientRect();
                            return r.width>0 && r.top>=-1 && r.bottom<=innerHeight+1 &&
                              p.getAnimations().every(a=>a.playState!=='running');
                        }""")
                        text=dialog.inner_text(); bounds=panel.bounding_box()
                        checks.update(panel_settled=bounds is not None and bounds['y']>=-1,
                            forecast_copy=('Forecast not available' if lang=='en' else '预测暂不可用') in text if modern else True,
                            old_odds_hidden='42.0%' not in text if modern else True,
                            no_page_error=not errors)
                        if row['cc']=='JP' and row['case'] in ('complete','partial','unavailable','legacy'):
                            name=f"{row['case']}-{theme}-{lang}-{width}-settled.png"
                            page.screenshot(path=str(OUT/name))
                            screenshots.append(dict(path=name,sha256=sha((OUT/name).read_bytes()),
                                panel_bounds=bounds,case=row['case'],theme=theme,lang=lang,width=width))
                        page.keyboard.press('Escape')
                        expect(dialog).not_to_be_visible()
                        expect(trigger).to_be_focused()
                        checks['focus_returned']=trigger.evaluate('e=>e===document.activeElement')
                        records.append(dict(cc=row['cc'],case=row['case'],theme=theme,lang=lang,
                                            width=width,checks=checks,panel_bounds=bounds,errors=list(errors)))
        context.close(); browser.close()
    failures=[r for r in records if not all(r['checks'].values())]
    unchanged=all(sha((INPUT/r['case']/'site'/r['route']).read_bytes())==r['html_sha256'] for r in SOURCE['cases'])
    receipt=dict(kind='actual_isolated_builder_to_settled_browser',cases=records,
        screenshot_records=screenshots,all_checks_pass=not failures,failures=failures,
        source_inputs_unchanged=unchanged,builder_receipt_sha256=sha((INPUT/'receipt.json').read_bytes()),
        served_asset_hashes=served,blocked_requests=sorted(blocked),
        fonts_shared=False,authenticated=False,production=False,synthetic_only=True)
    (OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(cases=len(records),failures=failures,screenshots=len(screenshots),
        source_inputs_unchanged=unchanged,font_assets_served=sorted(EXTRA_ASSETS.intersection(served)),production=False)))
    return 0 if not failures and unchanged else 1

if __name__=='__main__':
    raise SystemExit(main())
