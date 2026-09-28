"""Semantic and geometry checks on actual generated Crypto fixture routes."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

OUT=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/crypto_h5_actual')
BASE='http://127.0.0.1:8766'
states=['happy','zero','unavailable','stale','breakdown','zero-gap','malformed']
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    for state in states:
        for width,height in [(1440,1000),(768,1024),(390,844),(320,844)]:
            for theme in ['dark','light']:
                for lang in ['en','zh']:
                    page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
                    errors=[]; failed=[]
                    page.on('pageerror',lambda e,errors=errors: errors.append(str(e)))
                    page.on('requestfailed',lambda r,failed=failed: failed.append(r.url))
                    page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                    resp=page.goto(f'{BASE}/crypto-{state}.html',wait_until='networkidle',timeout=30000)
                    page.wait_for_timeout(350)
                    h5=page.locator('[data-shelf="H5"]')
                    h5txt=h5.inner_text()
                    exposure=h5.locator('.exposure-big').inner_text()
                    geometry=h5.evaluate("""e => { const outer=e.getBoundingClientRect();
                      return [...e.querySelectorAll('.alloc-main,.alloc-side,.alloc-top,.source-line,.alloc-key')]
                        .map(n => { const r=n.getBoundingClientRect(); return {class:n.className,sw:n.scrollWidth,cw:n.clientWidth,x:r.x,right:r.right}; })
                        .filter(n => n.sw>n.cw+2 || n.x<outer.x-2 || n.right>outer.right+2); }""")
                    expected='available' if state in ('happy','zero','zero-gap') else ('breakdown-unavailable' if state=='breakdown' else 'unavailable')
                    row={'state':state,'width':width,'theme':theme,'lang':lang,'http':resp.status if resp else None,
                         'overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),
                         'h5Count':h5.count(),'h6Count':page.locator('[data-shelf="H6"]').count(),
                         'renderedState':h5.get_attribute('data-allocation-state'),
                         'expectedState':expected,'exposure':exposure,'h5GeometryFailures':geometry,
                         'minimumReadingFont':h5.locator('.alloc-top p,.alloc-note').evaluate_all("es=>Math.min(...es.map(e=>parseFloat(getComputedStyle(e).fontSize)))"),
                         'allocBar':h5.locator('.alloc-bar').count(),'allocLegend':h5.locator('.alloc-legend').count(),
                         'canonicalReceipt':'btc.decision/v1' in h5txt,'rawSignalText':'alloc_optimal' in h5txt,
                         'pageErrors':errors,'requestFailures':[u for u in failed if not u.endswith('favicon.ico')]}
                    if state=='happy':
                        good='60%' in exposure and row['allocBar']==1 and row['allocLegend']==1
                    elif state in ('zero','zero-gap'):
                        good=exposure.strip().startswith('0%') and '100%' in h5txt and row['allocBar']==1 and row['allocLegend']==1
                    elif state=='breakdown':
                        good='60%' in exposure and '40%' in h5txt and row['allocBar']==0 and row['allocLegend']==0
                        good=good and ('Breakdown unavailable' in h5txt if lang=='en' else '类别明细暂不可用' in h5txt)
                    else:
                        good=exposure.strip().startswith('—') and row['allocBar']==0 and row['allocLegend']==0
                        good=good and ('Allocation unavailable' in h5txt if lang=='en' else '配置暂不可用' in h5txt)
                        if state=='stale':
                            good=good and ('different snapshot' in h5txt if lang=='en' else '快照日期不一致' in h5txt) and '60%' not in h5txt
                    row['semanticPass']=good and row['renderedState']==expected and row['canonicalReceipt']
                    if state in ('breakdown','zero-gap','stale') and ((width==1440 and theme=='dark' and lang=='en') or (width==320 and theme=='light' and lang=='zh')):
                        h5.screenshot(path=str(OUT/f'h5-{state}-{width}-{theme}-{lang}.png'))
                    rows.append(row)
                    page.close()
        print('Checked',state,flush=True)
    browser.close()
(OUT/'browser_matrix.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
bad=[r for r in rows if r['http']!=200 or r['overflow'] or r['h5Count']!=1 or r['h6Count']!=1 or r['pageErrors'] or not r['semanticPass'] or r['rawSignalText'] or r['h5GeometryFailures'] or r['minimumReadingFont']<14]
print(json.dumps({'cells':len(rows),'passed':len(rows)-len(bad),'failures':bad},indent=2,ensure_ascii=False))
assert not bad
