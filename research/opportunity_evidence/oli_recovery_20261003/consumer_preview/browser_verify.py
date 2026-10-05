"""Real Chromium proof of the synthetic preview, not a production browser receipt."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent

def run():
    receipts=[];screens=[];errors=[];requests=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto((ROOT/'preview.html').as_uri());page.wait_for_function('window.__previewView !== undefined')
        for width in (1440,768,390,320):
            page.set_viewport_size({'width':width,'height':1100})
            for theme in ('dark','light'):
                if page.locator('html').get_attribute('data-theme')!=theme:page.locator('#theme').click()
                for scenario in ('confirmed','expired_entry','mixed_generation','future_knowledge','missing_optional','transport_failure','correction','holding','rights','native_extended'):
                    page.select_option('#scenario',scenario)
                    for audience in ('public','private'):
                        page.locator('#'+audience).click()
                        view=page.evaluate('window.__previewView')
                        assert view['audience']==audience
                        expected=view['sources']['entry']['display_value']
                        if expected:assert expected['native_verdict'].replace('_',' ').lower() in page.locator('#entry').inner_text().lower()
                        else:assert 'withholds' in page.locator('#entry-reason').inner_text()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,theme,scenario,audience,'overflow')
                        assert all(x is False for x in view['authority'].values()) and view['forecasts'] is None
                        if audience=='public':assert view['plan']['status']=='PRIVATE_CONTEXT_NOT_JOINED' and 'ref' not in view['plan']
                        receipts.append({'width':width,'theme':theme,'scenario':scenario,'audience':audience,'result':'PASS'})
                # Capture one at-rest workflow per screen width/theme, not just a design picture.
                page.select_option('#scenario','confirmed');page.locator('#public').click()
                out=ROOT/f'preview_{width}_{theme}.png';page.screenshot(path=str(out),full_page=True)
                screens.append({'file':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#evidence').click();assert page.locator('#detail').evaluate('(e)=>e.open')
        assert page.locator('#dialog-body').inner_text().count('Known ')==7
        page.keyboard.press('Escape');assert page.evaluate('document.activeElement.id')=='evidence'
        page.locator('#machine').click();parsed=json.loads(page.locator('#dialog-body pre').inner_text());assert parsed==page.evaluate('window.__previewView')
        page.locator('#close').click();assert page.evaluate('document.activeElement.id')=='machine'
        page.select_option('#scenario','correction');page.locator('#evidence').click();assert 'Corrects fixture:contradiction:demo / fixture-generation-1' in page.locator('#dialog-body').inner_text();page.keyboard.press('Escape')
        page.evaluate("document.documentElement.style.fontSize='200%'")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'text stress overflow'
        assert not errors,errors
        assert all(url.startswith('file:') for url in requests),requests
        browser.close()
    result={'scope':'synthetic preview only; no real producer/gateway/authentication/data/production proof',
            'matrix_cases':len(receipts),'matrix_pass':len(receipts),'browser':'Chromium / local container / headless',
            'interaction_checks':['Escape returns evidence-button focus','machine dialog JSON equals rendered view','close returns machine-button focus','correction lineage shown','no remote requests','no console page errors','390px root-font 200% stress'],
            'screenshots':screens,'cases':receipts,'errors':errors,'requests':requests,
            'html_sha256':hashlib.sha256((ROOT/'preview.html').read_bytes()).hexdigest()}
    (ROOT/'browser_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('scope','matrix_cases','matrix_pass','interaction_checks','errors','html_sha256')},indent=2))

if __name__=='__main__':run()
