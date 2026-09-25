from pathlib import Path
from copy import deepcopy
from urllib.parse import urlsplit, unquote
import hashlib, json, mimetypes

from playwright.sync_api import sync_playwright

ROOT = Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/theme-recommendation-reasons-20260921-sol')
SITE = ROOT/'site'
OUT = Path('/tmp/mmx-7669-continuation-repair/browser')
PAGES = Path('/tmp/mmx-7669-continuation-repair/browser-pages')
OUT.mkdir(parents=True, exist_ok=True); PAGES.mkdir(parents=True, exist_ok=True)

source = SITE/'basket_china/cn_pharma_cxo.html'
html = source.read_text()
prefix, tail = html.split('const DETAIL = ', 1)
base, end = json.JSONDecoder().raw_decode(tail)

def page_for(name, mutator):
    d = deepcopy(base); mutator(d)
    raw = json.dumps(d, separators=(',',':'), ensure_ascii=False, allow_nan=False).replace('</','<\\/')
    text = prefix + 'const DETAIL = ' + raw + tail[end:]
    path = PAGES/(name+'.html'); path.write_text(text)
    return path, d

scenarios = {}
scenarios['continuation_zero_qualified'] = page_for('continuation_zero_qualified', lambda d: None)

def fresh_initial(d):
    d['theme'].setdefault('textures',{}).setdefault('clean_entry',{})['flag'] = True
    d['theme']['reco'] = 'accumulate'; d['theme']['reco_en']='ACCUMULATE'; d['theme']['reco_zh']='加仓'
    d['theme']['reco_reason_code']='entry_checks_clear'
    d['theme']['reco_why_en']='Entry checks clear.'
    d['theme']['reco_why_zh']='入场条件已满足。'
scenarios['fresh_initial'] = page_for('fresh_initial', fresh_initial)

def demoted(d):
    d['theme']['reco']='hold'; d['theme']['reco_en']='HOLD'; d['theme']['reco_zh']='持有'
    d['theme']['reco_reason_code']='regime_safeguard'
    d['theme']['reco_why_en']='Risk safeguard is active.'
    d['theme']['reco_why_zh']='风险保护已启用。'
scenarios['final_demoted'] = page_for('final_demoted', demoted)

def stale_missing(d):
    d['as_of']='2026-09-20'
    d['theme']['reco']='accumulate'; d['theme']['reco_en']='ACCUMULATE'; d['theme']['reco_zh']='加仓'
    d['theme'].setdefault('textures',{}).pop('clean_entry',None)
    d['theme']['reco_reason_code']='entry_read_unavailable'
    d['theme']['reco_why_en']='Entry information unavailable.'
    d['theme']['reco_why_zh']='入场信息暂缺。'
scenarios['stale_missing_entry'] = page_for('stale_missing_entry', stale_missing)

expected = {
 'continuation_zero_qualified': {'rating_en':'ACCUMULATE','rating_zh':'加仓','initial':True,'qualified':0,'stale':True},
 'fresh_initial': {'rating_en':'ACCUMULATE','rating_zh':'加仓','initial':False,'qualified':0,'stale':True},
 'final_demoted': {'rating_en':'HOLD','rating_zh':'持有','initial':False,'qualified':0,'stale':True},
 'stale_missing_entry': {'rating_en':'ACCUMULATE','rating_zh':'加仓','initial':True,'qualified':0,'stale':True},
}

records=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    for scenario,(scenario_path,data) in scenarios.items():
      for theme in ('dark','light'):
       for lang in ('en','zh'):
        for width in (1440,390):
            ctx=browser.new_context(viewport={'width':width,'height':1000},device_scale_factor=1)
            ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
            errors=[]; denied=[]
            def serve(route):
                u=urlsplit(route.request.url)
                if u.hostname!='continuation.local':
                    route.fulfill(status=204,body=''); return
                path=unquote(u.path)
                if path==f'/basket_china/{scenario}.html':
                    route.fulfill(status=200,content_type='text/html',body=scenario_path.read_bytes()); return
                if path.startswith(('/live/','/api/','/premiumdata/')):
                    denied.append(path); route.fulfill(status=401,content_type='application/json',body='{"error":"not_part_of_local_proof"}'); return
                target=(SITE/path.lstrip('/')).resolve()
                if target.is_relative_to(SITE.resolve()) and target.is_file():
                    route.fulfill(status=200,content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream',body=target.read_bytes())
                else:
                    route.fulfill(status=404,body='Unavailable in local proof')
            ctx.route('**/*',serve)
            page=ctx.new_page(); page.on('pageerror',lambda err: errors.append(str(err)))
            page.goto(f'http://continuation.local/basket_china/{scenario}.html',wait_until='networkidle')
            applied=page.evaluate('({theme:document.documentElement.dataset.theme,language:document.documentElement.dataset.lang})')
            assert applied=={'theme':theme,'language':lang}, applied
            hero=page.locator('.panel.hero')
            hero_text=hero.inner_text()
            rating=expected[scenario]['rating_en'] if lang=='en' else expected[scenario]['rating_zh']
            assert rating in hero_text, (scenario,lang,hero_text)
            assert 'WAIT FOR ENTRY' not in hero_text and '等待入场' not in hero_text
            initial_visible=('Initial entry context:' in hero_text) if lang=='en' else ('初始入场条件：' in hero_text)
            assert initial_visible is expected[scenario]['initial'], (scenario,lang,hero_text)
            link=page.locator('[data-stock-entry-link]'); assert link.count()==1
            link.focus(); page.keyboard.press('Enter')
            panel=page.locator('#stock-entry-checks'); assert panel.evaluate('(e)=>e.open')
            summary=panel.inner_text()
            if scenario=='continuation_zero_qualified':
                assert ('0 qualified' in summary) if lang=='en' else ('0 只通过' in summary)
            stale=page.locator('.ftr-stale-banner')
            assert (stale.count()>0) is expected[scenario]['stale']
            if scenario=='stale_missing_entry':
                assert ('Entry information unavailable.' in hero_text) if lang=='en' else ('入场信息暂缺。' in hero_text)
            geometry=page.evaluate('({scroll:document.documentElement.scrollWidth,viewport:innerWidth})')
            assert geometry['scroll']<=geometry['viewport']+1, (scenario,theme,lang,width,geometry)
            hero.scroll_into_view_if_needed()
            filename=f'{scenario}-{theme}-{lang}-{width}.png'
            hero.screenshot(path=str(OUT/filename))
            assert not errors,(scenario,errors)
            records.append({
                'scenario':scenario,'theme':theme,'language':lang,'width':width,
                'rating_visible':True,'wait_instruction_absent':True,
                'initial_context_visible':initial_visible,'stock_checks_opened':True,
                'page_errors':errors,'page_overflow':False,'unavailable_live_requests':sorted(set(denied)),
                'screenshot':filename,'sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest()
            })
            ctx.close()
      print('VERIFIED',scenario,len(records),flush=True)
    browser.close()

receipt={'source_page':source.relative_to(ROOT).as_posix(),
         'source_page_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'captures':len(records),'records':records,'production':False,
         'limitations':['Synthetic controls modify only DETAIL data inside the compiled current source page.',
                        'No new market data, action-card decision, score, or trade permission is created.',
                        'Local Chromium proof only; production/authenticated proof remains separate.']}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'captures':len(records),'errors':sum(len(x['page_errors']) for x in records),
                  'all_no_wait':all(x['wait_instruction_absent'] for x in records)},indent=2))
