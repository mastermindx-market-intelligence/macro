"""D03 T46: actual shadow builder/render pipeline in network-isolated Chromium.

All candidate/context inputs and publication paths are temporary synthetic
fixtures. Actual template, write_page, shared-shell assets and theme are used.
No production URL, live input, live ledger, auth change or deployment is used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import mimetypes
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


MEASURE = """el => {
  const s = getComputedStyle(el), b = el.getBoundingClientRect();
  const cv=document.createElement('canvas');cv.width=cv.height=1;
  const cx=cv.getContext('2d',{willReadFrequently:true});
  function lum(color){cx.clearRect(0,0,1,1);cx.fillStyle=color;cx.fillRect(0,0,1,1);
    return [...cx.getImageData(0,0,1,1).data].slice(0,3)
      .map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;})
      .reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);}
  const bg=lum(s.backgroundColor);
  const text=['.source-label','h2','.source-description','.source-clock','summary']
    .map(sel=>{const e=el.querySelector(sel),c=getComputedStyle(e),r=e.getBoundingClientRect();
      const fg=lum(c.color);return {selector:sel,text:e.innerText,fontSize:parseFloat(c.fontSize),
        contrast:(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05),
        width:r.width,height:r.height,overflow:e.scrollWidth>e.clientWidth+1};});
  return {sourceState:el.dataset.sourceState,x:b.x,right:b.right,width:b.width,height:b.height,
    viewport:innerWidth,pageScrollWidth:document.documentElement.scrollWidth,
    scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,background:s.backgroundColor,
    borderWidths:[s.borderTopWidth,s.borderRightWidth,s.borderBottomWidth,s.borderLeftWidth],
    borderColors:[s.borderTopColor,s.borderRightColor,s.borderBottomColor,s.borderLeftColor],text};
}"""


class FixtureClock(datetime):
    @classmethod
    def now(cls, tz=None):
        value=cls(2026,11,4,6,0,tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    root,out=args.repo.resolve(),args.out.resolve()
    assert out.is_dir() and not list(out.iterdir()), 'Use a new empty evidence directory'
    sys.path.insert(0,str(root))
    import engine.group_context as gcmod
    from scripts import build_stock_board_v2 as v2

    spec=importlib.util.spec_from_file_location('t46_fixture',root/'tests/test_stock_board_v2_availability.py')
    fixtures=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    source_paths=['scripts/build_stock_board_v2.py','templates/us_stocks_v2.html.j2',
                  'tests/test_stock_board_v2_availability.py','templates/theme.css',
                  'templates/shared_shell.css','templates/shared_shell_bridge.js',
                  'templates/data_base.js','lib/pages.py','lib/shared_shell.py']
    hashes={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in source_paths}
    cases={}
    for name in ('unavailable','malformed','partial','empty','populated','mixed','unknown','future'):
        case_root=out/'fixtures'/name
        site=case_root/'site'
        (site/'factordata').mkdir(parents=True)
        (case_root/'templates').mkdir()
        for asset in ('us_stocks_v2.html.j2','data_base.js'):
            shutil.copy2(root/'templates'/asset,case_root/'templates'/asset)
        for asset in ('theme.css','data_base.js'):
            shutil.copy2(root/'templates'/asset,site/asset)
        rows=[] if name=='empty' else [fixtures._rich('AAA',0.8),fixtures._rich('CCC',0.6,'T4')]
        std,setups=fixtures._inputs(rows)
        if name=='mixed': setups['as_of']='2026-11-01'
        if name=='unknown': std.pop('as_of')
        if name=='future': setups['as_of']='2030-01-01'
        if name=='malformed':
            for source in (v2._STD,v2._SETUPS): (site/'factordata'/source).write_text('{')
        elif name not in ('unavailable',):
            fixtures._write(site,v2._STD,std)
            if name!='partial': fixtures._write(site,v2._SETUPS,setups)
        before={p.name:p.read_bytes() for p in (site/'factordata').iterdir()}
        with patch.object(v2.config,'ROOT',case_root),patch.object(gcmod,'_ROOT',case_root),patch.object(v2,'datetime',FixtureClock):
            payload=v2.build(write=True,site=site)
        assert all((site/'factordata'/p).read_bytes()==b for p,b in before.items())
        assert (site/'us_stocks_v2.html').is_file()
        assert payload['shadow'] is True
        cases[name]={'root':case_root,'site':site,'payload':payload}
    print(json.dumps({'phase':'actual_builder_fixtures_complete','cases':list(cases),'out':str(out)}),flush=True)

    blocked=set()
    def route_request(route):
        parsed=urlparse(route.request.url)
        parts=unquote(parsed.path).strip('/').split('/',2)
        if parsed.hostname=='127.0.0.1' and len(parts)==3 and parts[0]=='case' and parts[1] in cases:
            site=cases[parts[1]]['site']
            candidate=(site/parts[2]).resolve()
            if candidate.is_relative_to(site) and candidate.is_file():
                route.fulfill(status=200,content_type=mimetypes.guess_type(candidate)[0] or 'application/octet-stream',body=candidate.read_bytes())
                return
            asset=(root/'templates'/parts[2]).resolve()
            if asset.is_relative_to(root/'templates') and asset.is_file() and asset.suffix in {'.css','.js','.woff2','.woff','.svg','.png'}:
                route.fulfill(status=200,content_type=mimetypes.guess_type(asset)[0] or 'application/octet-stream',body=asset.read_bytes())
                return
        blocked.add((parsed.hostname or '')+parsed.path)
        route.abort()

    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        version=browser.version
        for width in (320,390,1440):
            for theme in ('light','dark'):
                for lang in ('en','zh'):
                    context=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=1,has_touch=width<=390)
                    context.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});")
                    context.route('**/*',route_request)
                    page=context.new_page()
                    page.set_default_timeout(5000)
                    errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    for name,case in cases.items():
                        if width!=390 and name in ('malformed','mixed','unknown','future'): continue
                        page.goto(f'http://127.0.0.1/case/{name}/us_stocks_v2.html',wait_until='load')
                        page.evaluate('document.fonts.ready')
                        panel=page.locator('.source-coverage')
                        measured=panel.evaluate(MEASURE)
                        expected={'unavailable':'unavailable','malformed':'unavailable','partial':'partial'}.get(name,'complete')
                        assert case['payload']['source_coverage']['state']==expected
                        expected_observation={'empty':'shared','populated':'shared','mixed':'mixed','future':'future'}.get(name,'unknown')
                        assert case['payload']['source_coverage']['observation_state']==expected_observation
                        expected_date='2026-11-02' if expected_observation=='shared' else None
                        assert case['payload']['as_of']==expected_date
                        assert measured['sourceState']==expected
                        assert measured['x']>=-1 and measured['right']<=width+1
                        assert measured['pageScrollWidth']<=width+1,(name,width,theme,lang,measured)
                        assert measured['scrollWidth']<=measured['clientWidth']+1
                        assert len(set(measured['borderWidths']))==1 and len(set(measured['borderColors']))==1
                        for item in measured['text']:
                            assert not item['overflow'],(name,item)
                            assert item['contrast']>=4.5,(name,theme,lang,item)
                            assert item['fontSize']>=12
                        assert measured['text'][2]['fontSize']>=14
                        assert measured['text'][4]['height']>=44
                        expected_heading={'en':{'unavailable':'Sources unavailable','partial':'Partial coverage','complete':'Both inputs readable'},
                                          'zh':{'unavailable':'数据源暂不可用','partial':'覆盖不完整','complete':'两个输入均可读取'}}[lang][expected]
                        assert measured['text'][1]['text']==expected_heading
                        clock_copy={
                            'en':{'shared':'Shared source observation: 2026-11-02. Build time does not establish freshness.',
                                  'mixed':'Shared observation unavailable — source dates differ. Inspect each date below.',
                                  'future':'Shared observation unavailable — a supplied date is in the future and is unverified.',
                                  'unknown':'Shared observation unavailable. Build time is not a source observation.'},
                            'zh':{'shared':'共同来源观察日期: 2026-11-02. 构建时间不能证明数据新鲜度。',
                                  'mixed':'共同观察日期暂不可用——来源日期不同，请查看下方各自日期。',
                                  'future':'共同观察日期暂不可用——存在尚未核实的未来日期。',
                                  'unknown':'共同观察日期暂不可用。构建时间不等于来源观察时间。'},
                        }[lang][expected_observation]
                        assert ' '.join(panel.locator('.source-clock').inner_text().split())==clock_copy
                        assert page.locator('.strip .stat b').first.inner_text()==(expected_date or '—')
                        assert '2026-11-04 06:00 UTC' in page.locator('.foot').inner_text()
                        assert page.locator('meta[name="robots"]').get_attribute('content')=='noindex'
                        assert not errors,errors
                        screenshot=f'{name}-{width}-{theme}-{lang}.png'
                        panel.screenshot(path=str(out/screenshot),animations='disabled')
                        details=page.locator('.source-receipts')
                        summary=details.locator('summary')
                        summary.focus()
                        page.keyboard.press('Enter')
                        assert details.get_attribute('open') is not None
                        assert page.locator('.source-receipt').count()==2
                        assert page.locator('.source-receipt dt code').all_text_contents()==['us_standouts.json','setups.json']
                        receipt_dates={'unavailable':[[],[]],'malformed':[[],[]],
                                       'partial':[['2026-11-02'],[]],'unknown':[[],['2026-11-02']],
                                       'mixed':[['2026-11-02'],['2026-11-01']],
                                       'future':[['2026-11-02'],['2030-01-01']]}.get(name,[['2026-11-02'],['2026-11-02']])
                        for index,dates in enumerate(receipt_dates):
                            assert page.locator('.source-receipt').nth(index).locator('time').all_text_contents()==dates
                        if name=='future':
                            assert ('Future date — unverified' if lang=='en' else '未来日期——未核实') in page.locator('.source-receipt').nth(1).inner_text()
                        assert summary.evaluate('e=>parseFloat(getComputedStyle(e).outlineWidth)')>=2
                        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
                        source_dates=panel.locator('.source-date').evaluate_all('''els=>els.map(e=>({
                            text:e.textContent, height:e.getBoundingClientRect().height,
                            lineHeight:parseFloat(getComputedStyle(e).lineHeight),
                            whiteSpace:getComputedStyle(e).whiteSpace
                        }))''')
                        assert all(d['whiteSpace']=='nowrap' and d['height']<=d['lineHeight']+1 for d in source_dates)
                        if width==390 and lang=='en':
                            panel.screenshot(path=str(out/f'details-{name}-{theme}.png'),animations='disabled')
                        page.keyboard.press('Enter')
                        assert details.get_attribute('open') is None
                        if width==320:
                            summary.tap()
                            assert details.get_attribute('open') is not None
                            summary.tap()
                            assert details.get_attribute('open') is None
                        links=page.locator('.v2-card').evaluate_all('els=>els.map(e=>e.getAttribute("href"))')
                        assert len(links)==sum(case['payload']['counts'][key] for key in ('entry_open','setting_up'))
                        if links:
                            summary.focus()
                            page.keyboard.press('Tab')
                            assert page.evaluate('document.activeElement.classList.contains("v2-card")')
                            assert links==['stock.html?t=AAA','stock.html?t=CCC']
                        if expected=='unavailable':
                            assert page.locator('.conc').count()==0
                            assert page.locator('.strip .stat b').all_text_contents()[:4]==['—']*4
                        page.emulate_media(reduced_motion='reduce')
                        if links: assert page.locator('.v2-card').first.evaluate('e=>getComputedStyle(e).transitionDuration')=='0s'
                        page.emulate_media(reduced_motion='no-preference')
                        if (name,width,theme,lang) in {('populated',320,'dark','en'),('partial',390,'light','en'),('unavailable',1440,'dark','zh')}:
                            page.screenshot(path=str(out/f'page-{name}-{width}-{theme}-{lang}.png'),full_page=True,animations='disabled')
                        results.append({'case':name,'viewport':width,'theme':theme,'language':lang,'screenshot':screenshot,
                                        'status':case['payload']['status'],'as_of':case['payload']['as_of'],
                                        'observation_state':case['payload']['source_coverage']['observation_state'],
                                        'keyboard_details':True,'touch_details':width==320,'candidate_links':links,
                                        'reduced_motion_media_exercised':True,'card_reduced_motion_verified':bool(links),
                                        'clock_copy_verified':True,'receipt_dates':receipt_dates,
                                        'unbroken_source_dates':source_dates,**measured})
                    context.close()
        browser.close()
    assert len(results)==64,len(results)
    assert not blocked,sorted(blocked)
    assert hashes=={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in source_paths}
    proof={'kind':'synthetic actual-builder browser proof; not deployment or live-market acceptance',
           'chromium':version,'fixture_build_clock':'2026-11-04T06:00:00Z','source_sha256':hashes,
           'case_count':len(results),'js_errors':[],'blocked_requests':sorted(blocked),
           'minimum_source_text_contrast':min(t['contrast'] for r in results for t in r['text']),
           'results':results}
    (out/'browser-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'phase':'pass','cases':len(results),'chromium':version,
                      'min_contrast':proof['minimum_source_text_contrast'],'blocked_requests':sorted(blocked)}),flush=True)


if __name__=='__main__':
    main()
