from pathlib import Path
from hashlib import sha256
import json
from playwright.sync_api import sync_playwright
ROOT=Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/sector-cycle-p1-member-observation-20260917-sol')
SITE=Path('/tmp/mmx-sector-p1-proof/site')
OUT=Path('/tmp/mmx-sector-p1-units-browser')
OUT.mkdir(exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    try:
        for lang in ['en','zh']:
            for theme in ['dark','light']:
                for width in [1440,390]:
                    context=browser.new_context(viewport={'width':width,'height':1000})
                    page=context.new_page()
                    errors=[]
                    page.on('pageerror',lambda exc:errors.append(str(exc)))
                    page.add_init_script('localStorage.setItem("lang",'+json.dumps(lang)+');localStorage.setItem("theme",'+json.dumps(theme)+');')
                    page.goto((SITE/'basket/ai_infra.html').as_uri(),wait_until='load',timeout=20000)
                    page.locator('#mo-metric').wait_for(timeout=10000)
                    original=page.evaluate('JSON.stringify(DETAIL.member_observations)')
                    assert page.locator('html').get_attribute('data-lang')==lang
                    assert page.locator('html').get_attribute('data-theme')==theme
                    page.select_option('#mo-metric','raw_daily_change')
                    raw=page.locator('#mo-rows tr').first.inner_text()
                    assert '%' in raw,raw
                    page.select_option('#mo-metric','benchmark_relative_daily_change')
                    relative=page.locator('#mo-rows tr').first.inner_text()
                    expected='pp' if lang=='en' else '个百分点'
                    assert expected in relative and '%' not in relative,relative
                    page.select_option('#mo-metric','strict_trend_200')
                    assert page.locator('#mo-rows tr').count()==24
                    page.select_option('#mo-filter','unavailable')
                    assert page.locator('#mo-rows tr').count()==1
                    missing=page.locator('#mo-rows').inner_text()
                    assert 'CBRS' in missing,missing
                    assert ('Unavailable' if lang=='en' else '不可用') in missing,missing
                    page.select_option('#mo-filter','all')
                    page.fill('#mo-search','CBRS')
                    assert page.locator('#mo-rows tr').count()==1
                    assert page.evaluate('JSON.stringify(DETAIL.member_observations)')==original
                    page.fill('#mo-search','')
                    page.select_option('#mo-metric','benchmark_relative_daily_change')
                    band=page.locator('.mo-band')
                    band.scroll_into_view_if_needed()
                    box=band.bounding_box()
                    assert box is not None and box['width']<=width,box
                    assert not errors,errors
                    result={'lang':lang,'theme':theme,'viewport':width,'raw':raw,'relative':relative,
                            'catalogue':24,'strict_200_observed':23,'strict_200_unavailable':1,
                            'missing_member':'CBRS','source_data_unchanged':True,'script_errors':errors,
                            'section_width':box['width']}
                    if (lang,theme,width) in [('en','dark',1440),('zh','light',390)]:
                        image=OUT/f'member-evidence-{lang}-{theme}-{width}.png'
                        band.screenshot(path=str(image))
                        result['screenshot']=image.name
                        result['screenshot_sha256']=sha256(image.read_bytes()).hexdigest()
                    results.append(result)
                    print(json.dumps(result,ensure_ascii=False),flush=True)
                    context.close()
    finally:
        browser.close()
receipt={'scope':'local real-input rendered page; not deployed or authenticated production proof',
         'template_sha256':sha256((ROOT/'templates/basket_detail.html.j2').read_bytes()).hexdigest(),
         'observation_digest':json.loads((SITE/'basketdata/member_observations.json').read_text())['projection_digest'],
         'states':results}
(OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print('BROWSER_STATES_PASSED',len(results),flush=True)
