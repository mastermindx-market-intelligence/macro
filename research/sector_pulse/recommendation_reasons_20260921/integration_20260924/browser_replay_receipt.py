"""Local browser acceptance of actual #7669 integrated files; no live/protected data."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hashlib, json, mimetypes, subprocess
from playwright.sync_api import sync_playwright
ROOT=Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/theme-recommendation-reasons-20260921-sol')
OUT=Path('/tmp/mmx-leadership-resume-20260924/integration/browser');OUT.mkdir(exist_ok=True)
HEAD='ef10b39a9e56cf912e6ae2be98ad0937c4716616'
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==HEAD
proof=json.loads((OUT.parent/'proof.json').read_text())
selected=['site/basket/ai_semiconductors.html','site/basket_china/cn_semis.html',
          'site/basket_hk/hk_tech_hardware.html','site/basket_canada/ca_tech.html',
          'site/basket_intl/intl_semis.html']
expected={r['path']:r for r in proof['rows'] if r['path'] in selected}
for relative in selected:
    assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected[relative]['output_sha256']
records=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    for relative in selected:
      for theme in ('dark','light'):
       for lang in ('en','zh'):
        for width in (1440,390):
            ctx=browser.new_context(viewport={'width':width,'height':1000},device_scale_factor=1)
            ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
            denied=[]
            def serve(route):
                u=urlsplit(route.request.url)
                if u.hostname!='integration.local':route.fulfill(status=204,body='');return
                path=unquote(u.path)
                if path.startswith(('/live/','/api/','/premiumdata/')):
                    denied.append(path);route.fulfill(status=401,content_type='application/json',body='{"error":"not_part_of_local_proof"}');return
                target=(ROOT/'site'/path.lstrip('/')).resolve()
                if target.is_relative_to((ROOT/'site').resolve()) and target.is_file():
                    route.fulfill(status=200,content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream',body=target.read_bytes())
                else:route.fulfill(status=404,body='Unavailable in integrated-source proof')
            ctx.route('**/*',serve)
            page=ctx.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            page.goto('http://integration.local/'+relative.removeprefix('site/'),wait_until='networkidle')
            link=page.locator('[data-stock-entry-link]');link.wait_for(state='visible')
            applied=page.evaluate('({theme:document.documentElement.dataset.theme,language:document.documentElement.dataset.lang})')
            assert applied=={'theme':theme,'language':lang},applied
            link.focus();page.keyboard.press('Enter')
            panel=page.locator('#stock-entry-checks')
            assert panel.evaluate('(e)=>e.open')
            assert panel.locator('summary').evaluate('(e)=>e===document.activeElement')
            data=page.evaluate('({asof:DETAIL.as_of,members:DETAIL.members.length,checks:DETAIL.act_now.entry_checks,stockBase:DETAIL.stock_base})')
            assert data['asof']==expected[relative]['as_of']
            assert data['members']==len(data['checks'])==expected[relative]['members']
            table=panel.locator('tbody tr');assert table.count()==data['members']
            for index,row in enumerate(data['checks']):
                text=table.nth(index).inner_text()
                assert row['symbol'] in text and row['reason_'+lang] in text,(relative,row['symbol'])
                href=table.nth(index).locator('a').first.get_attribute('href')
                assert href and row['symbol'] in href,(row['symbol'],href)
            page.evaluate('render()')
            assert panel.evaluate('(e)=>e.open')
            assert panel.locator('summary').evaluate('(e)=>e===document.activeElement')
            geometry=page.evaluate('({scroll:document.documentElement.scrollWidth,viewport:innerWidth})')
            assert geometry['scroll']<=geometry['viewport']+1,(relative,geometry)
            panel.scroll_into_view_if_needed()
            filename=relative.replace('/','_').replace('.html','')+'-'+theme+'-'+lang+'-'+str(width)+'.png'
            panel.screenshot(path=str(OUT/filename))
            assert not errors,(relative,errors)
            records.append({'path':relative,'theme':theme,'language':lang,'width':width,
                            'as_of':data['asof'],'members':data['members'],'all_reasons_present_in_dom':True,
                            'keyboard_open_and_refresh_focus':True,'stock_links_checked':True,
                            'page_errors':errors,'page_overflow':False,'unavailable_live_requests':sorted(set(denied)),
                            'screenshot':filename,'sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest()})
            ctx.close()
      print('VERIFIED',relative,len(records),flush=True)
    browser.close()
result={'source_head':HEAD,'main_input':proof['base'],'captures':len(records),'records':records,
        'production':False,'limitations':['Dated main-branch input, not new quotes or decisions.',
        'Local Chromium, not Safari/iOS or authenticated production acceptance.',
        'Optional live/protected requests explicitly unavailable; no credential or alias used.']}
(OUT/'receipt.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'captures':len(records),'page_errors':sum(len(r['page_errors']) for r in records),
                  'all_keyboard_and_refresh_checks':all(r['keyboard_open_and_refresh_focus'] for r in records)}),flush=True)
