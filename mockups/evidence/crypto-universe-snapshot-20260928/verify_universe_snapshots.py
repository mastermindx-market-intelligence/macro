"""Browser proof for the existing Market Board snapshot projection, no writes."""
import argparse, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--base-url', required=True)
a = ap.parse_args(); out = a.output.resolve()
receipt = json.loads((out / 'scenario_receipts.json').read_text())
rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    try:
        for scenario in receipt['routes']:
            mode = scenario['mode']; expected = scenario['universe_coverage']
            for width, height in [(320, 844), (390, 844), (768, 1024), (1440, 1000)]:
                for theme in ('dark', 'light'):
                    for lang in ('en', 'zh'):
                        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
                        errors = []; requests = []
                        page.on('pageerror', lambda e, es=errors: es.append(str(e)))
                        page.on('response', lambda r, rs=requests: rs.append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
                        page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');localStorage.removeItem('themeAuto');")
                        row = {'mode': mode, 'width': width, 'theme': theme, 'locale': lang}
                        try:
                            response = page.goto(a.base_url.rstrip('/') + '/' + scenario['file'], wait_until='domcontentloaded', timeout=30000)
                            page.wait_for_function('document.readyState === "complete"', timeout=30000)
                            page.evaluate('() => document.fonts.ready')
                            page.evaluate("v => { if(window.setTheme) window.setTheme(v.theme); if(window.setLang) window.setLang(v.lang); }", {'theme': theme, 'lang': lang})
                            # Existing theme owner removes its 1100ms sun/moon
                            # flourish. Observe settlement; never hide it via CSS.
                            page.wait_for_selector('.sky-fx', state='detached', timeout=4000)
                            snapshot = page.locator('#universe-snapshot')
                            snapshot.scroll_into_view_if_needed()
                            summary = snapshot.locator('summary')
                            before = snapshot.locator('details').evaluate('e=>e.open')
                            summary.focus(); page.keyboard.press('Enter')
                            opened = snapshot.locator('details').evaluate('e=>e.open')
                            text = snapshot.inner_text()
                            font = snapshot.evaluate('e=>({size:parseFloat(getComputedStyle(e).fontSize),family:getComputedStyle(e).fontFamily})')
                            geometry = snapshot.evaluate("e=>{ const b=e.getBoundingClientRect();return [...e.querySelectorAll('*')].filter(n=>getComputedStyle(n).display!=='none'&&n.getClientRects().length).map(n=>{const r=n.getBoundingClientRect();return {tag:n.tagName,cls:n.className,x:r.x,right:r.right,sw:n.scrollWidth,cw:n.clientWidth};}).filter(n=>n.x<b.x-2||n.right>b.right+2||n.sw>n.cw+2);}")
                            symbols = page.locator('#market-board .asset b').all_text_contents()
                            more = page.locator('#market-board .compact-asset>span:first-child').all_text_contents()
                            excluded = snapshot.locator('.excluded-observation').count()
                            row.update(http=response.status, shelf_count=page.locator('[data-shelf]').count(),
                                snapshot_date=snapshot.get_attribute('data-universe-as-of'),
                                ranked_rows=len(symbols)+len(more), excluded=excluded,
                                closed_initially=not before, keyboard_open=opened,
                                disclosure_target_height=summary.bounding_box()['height'],
                                font=font, geometry_failures=geometry,
                                document_overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),
                                h5_count=page.locator('[data-shelf="H5"]').count(),
                                peer_accessible=page.locator('[role="table"][aria-labelledby="crypto-market-title"]').count(),
                                js_errors=errors, failed_responses=requests,
                                fonts_loaded=page.evaluate('Array.from(document.fonts).filter(f=>f.status==="loaded").map(f=>({family:f.family,weight:f.weight}))'))
                            good = row['http']==200 and row['shelf_count']==8 and row['h5_count']==1
                            good &= row['ranked_rows']==expected['listed'] and excluded==len(expected['excluded'])
                            good &= row['snapshot_date']==(expected['as_of'] or '') and row['keyboard_open'] and row['closed_initially']
                            good &= not geometry and not row['document_overflow'] and font['size']>=14 and row['disclosure_target_height']>=44
                            good &= not errors and not any('/fonts/' in r['url'] for r in requests)
                            good &= not any(s in ('DARK','POLYDOGE') for s in symbols)
                            good &= not any('DARK' in s or 'POLYDOGE' in s for s in more)
                            if mode=='empty':
                                good &= ('No ranked snapshot available' in text if lang=='en' else '暂无可用的排名快照' in text)
                            else:
                                good &= 'DARK' in text and 'POLYDOGE' in text and '2026-09-01' in text
                                good &= '31531510' not in text and '763755' not in text
                            if mode=='returns-missing':
                                good &= expected['breadth']['eligible']==0 and not expected['breadth']['available']
                            if mode=='combined':
                                good &= row['peer_accessible']==1
                            # Switching the visible language must not close the native disclosure.
                            other = 'zh' if lang=='en' else 'en'
                            page.evaluate('v=>window.setLang ? window.setLang(v) : document.documentElement.setAttribute("data-lang",v)', other)
                            row['open_after_language_change'] = snapshot.locator('details').evaluate('e=>e.open')
                            good &= row['open_after_language_change']
                            page.evaluate('v=>window.setLang ? window.setLang(v) : document.documentElement.setAttribute("data-lang",v)', lang)
                            if (width==1440 and theme=='dark' and lang=='en') or (width==320 and theme=='light' and lang=='zh'):
                                snapshot.screenshot(path=str(out / f'snapshot-{mode}-{width}-{theme}-{lang}.png'))
                            row['passed'] = bool(good)
                        except Exception as exc:
                            row.update(passed=False, error=str(exc), js_errors=errors, failed_responses=requests)
                        finally:
                            rows.append(row); page.close()
            print('Checked', mode, flush=True)
    finally:
        browser.close()
(out / 'browser_matrix.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False))
bad = [r for r in rows if not r['passed']]
print(json.dumps({'cells':len(rows),'passed':len(rows)-len(bad),'failures':bad},indent=2,ensure_ascii=False), flush=True)
assert not bad
