"""Exercise actual compiled stock-entry disclosure, including explicit error fixtures.

No live feeds, price collection, authority changes or source-page mutation. Every
real-page byte digest is retained. The extra runtime fixture is visibly labeled.
"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from itertools import product
import argparse, hashlib, json, mimetypes, sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from engine import basket_score
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    root=ROOT/'site';records=[]
    paths=['basket/ai_semiconductors.html','basket_china/cn_semis.html','basket_hk/hk_banks.html']
    paths += [str(next(iter(sorted((root/d).glob('*.html')))).relative_to(root)) for d in ['basket_canada','basket_intl']]
    # The non-market fixture exercises missing assessment + actual theme veto.
    fixture_members=[{'symbol':'REVIEW_A','conviction':None},
                     {'symbol':'REVIEW_B','conviction':{'score':68,'cycle_blocked':False,'entry':{'status':'buy_now'},'verdict':'Constructive','entry_pct':.7}}]
    fixture=basket_score.act_now_stocks(fixture_members,{'label':'fading','reco':'trim','textures':{'bull_age':{'in_bull':True}}})
    assert fixture['entry_checks'][0]['code']=='assessment_unavailable'
    assert fixture['entry_checks'][1]['code']=='theme_blocked'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for theme,lang,width in product(['dark','light'],['en','zh'],[1440,390]):
            context=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844},device_scale_factor=1)
            context.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
            def route(req):
                u=urlsplit(req.request.url);p=(root/unquote(u.path).lstrip('/')).resolve()
                if u.hostname!='proof.local' or u.path.startswith(('/live/','/api/')) or not p.is_relative_to(root.resolve()) or not p.is_file():
                    req.fulfill(status=404,body='Unavailable in compiled-page proof');return
                req.fulfill(status=200,content_type=mimetypes.guess_type(str(p))[0] or 'application/octet-stream',body=p.read_bytes())
            context.route('**/*',route)
            for n,path in enumerate(paths):
                scenarios=['real_compiled']+(['validation_failure','theme_blocked_missing_fixture'] if n==0 else [])
                for scenario in scenarios:
                    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                    page.goto('http://proof.local/'+path,wait_until='networkidle');page.wait_for_selector('[data-stock-entry-link]')
                    if scenario=='validation_failure':
                        page.evaluate('DETAIL.act_now.entry_summary.qualified += 1; render();')
                    elif scenario=='theme_blocked_missing_fixture':
                        page.evaluate('(x)=>{DETAIL.act_now=x.act;DETAIL.members=x.members;render();}',{'act':fixture,'members':fixture_members})
                    link=page.locator('[data-stock-entry-link]');assert link.bounding_box()['height']>=40
                    link.focus();page.keyboard.press('Enter');detail=page.locator('#stock-entry-checks')
                    source=page.evaluate('DETAIL');rows=source['act_now']['entry_checks']
                    if scenario=='validation_failure':
                        assert detail.get_attribute('role')=='status'
                        assert detail.locator('table').count()==0
                    else:
                        assert detail.evaluate('e=>e.open')
                        assert detail.locator('tbody tr').count()==len(rows)
                        for r in rows: assert r['reason_'+lang] in detail.inner_text()
                    before=detail.inner_text();page.evaluate('render()');detail=page.locator('#stock-entry-checks')
                    assert detail.inner_text()==before
                    assert page.evaluate('document.activeElement===(document.querySelector("#stock-entry-checks > summary")||document.querySelector("#stock-entry-checks"))')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2')
                    if scenario!='validation_failure':
                        assert detail.evaluate('e=>e.open')
                        hrefs=detail.locator('tbody a').evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))')
                        assert len(hrefs)==len(rows) and all(h.startswith(source['stock_base']) for h in hrefs)
                    else:hrefs=[]
                    panel=detail.locator('xpath=..')
                    if scenario!='real_compiled':
                        label='SYNTHETIC REVIEW FIXTURE — NOT MARKET DATA' if lang=='en' else '合成审核情景 — 非市场数据'
                        panel.evaluate('(el,text)=>{const p=document.createElement("p");p.className="muted sm";p.textContent=text;el.prepend(p);}',label)
                    materials=panel.evaluate('el=>{const s=getComputedStyle(el);return {background:s.backgroundColor,backgroundImage:s.backgroundImage,border:s.borderColor,text:s.color,font:s.fontFamily};}')
                    assert not errors
                    png=f'{n}-{scenario}-{theme}-{lang}-{width}.png';panel.screenshot(path=str(out/png))
                    records.append({'path':path,'scenario':scenario,'theme':theme,'lang':lang,'width':width,'as_of':source['as_of'],
                        'members':len(rows),'hrefs':hrefs,'source_sha256':hashlib.sha256((root/path).read_bytes()).hexdigest(),
                        'screenshot':png,'screenshot_sha256':hashlib.sha256((out/png).read_bytes()).hexdigest(),'materials':materials,
                        'visible_panel_text':panel.inner_text(),'page_errors':errors,'keyboard_open_or_error_focus':True,
                        'refresh_preserves_focus':True,'viewport_overflow':False,'synthetic':scenario!='real_compiled'})
                    page.close()
            context.close()
        browser.close()
    payload={'compiled_file_tests':True,'production':False,'live_feeds':'unavailable_by_fixture',
             'template_sha256':hashlib.sha256((ROOT/'templates/basket_detail.html.j2').read_bytes()).hexdigest(),
             'engine_sha256':hashlib.sha256((ROOT/'engine/basket_score.py').read_bytes()).hexdigest(),
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'records':records,
             'limitations':['Local compiled-file evidence only; no production, authentication or live-feed proof.',
                            'Synthetic review states are visibly labeled; they do not describe market observations.']}
    (out/'results.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'states':len(records),'real':sum(not r['synthetic'] for r in records),'synthetic':sum(r['synthetic'] for r in records),
                      'all_axes_per_route':8,'page_errors':sum(bool(r['page_errors']) for r in records),'page_overflow':sum(r['viewport_overflow'] for r in records)}))

if __name__=='__main__':main()
