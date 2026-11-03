"""R4 guide-only browser proof. Uses the actual local source and existing interactions."""
from __future__ import annotations
import functools
import hashlib
import json
import re
import subprocess
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
import verify_browser as existing

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'mockups/refs/intraday-flow-upgrade/guide-r4'
BASELINE='703f3c9c230730cf9f0f5dbb99c7bd416b85859b'
checks=[]
captures=[]

def check(name,passed,**detail):
    record={'check':name,'passed':bool(passed),**detail}
    checks.append(record)
    assert passed,json.dumps(record,ensure_ascii=False)

def guide_region(text):
    start=text.index('<details class="ift-guide">')
    end=text.index('</details>',start)+len('</details>')
    return text[start:end],text[:start]+'<GUIDE_COPY>'+text[end:]

def source_proof():
    result={}
    for name in ['templates/intraday_flow.html.j2','site/intraday_flow.html']:
        old=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,text=True)
        new=(ROOT/name).read_text()
        old_guide,old_rest=guide_region(old)
        new_guide,new_rest=guide_region(new)
        scripts=lambda text:re.findall(r'<script\b[^>]*>.*?</script>',text,re.S|re.I)
        labels=lambda text:re.findall(r'<li><b>(.*?)</b>',text,re.S)
        check(name+'/outside-guide-identical',old_rest==new_rest)
        check(name+'/all-script-elements-identical',scripts(old)==scripts(new))
        check(name+'/six-bilingual-labels-and-markers-identical',labels(old_guide)==labels(new_guide) and len(labels(new_guide))==12)
        result[name]={'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
            'script_elements':len(scripts(new)),'outside_guide_identical':True}
    for name in ['templates/intraday-flow.css','site/intraday-flow.css','site/flowtracker/base.json']:
        old=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
        now=(ROOT/name).read_bytes()
        check(name+'/byte-identical',old==now)
        result[name]={'sha256':hashlib.sha256(now).hexdigest(),'byte_identical':True}
    return result

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def matrix(browser,url,width,theme,locale):
    key=f'{width}/{theme}/{locale}'
    context=existing.source_context(browser,theme,locale,width)
    page=context.new_page()
    errors=[];failed=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('response',lambda response:failed.append({'url':response.url,'status':response.status}) if response.status>=400 else None)
    page.goto(url,wait_until='domcontentloaded')
    existing.await_board(page)
    page.evaluate('document.fonts.ready')
    guide=page.locator('.ift-guide')
    summary=guide.locator(':scope > summary')
    check(key+'/native-guide-starts-closed',guide.get_attribute('open') is None)
    closed_height=guide.bounding_box()['height']
    page.locator('#ift-theme-menu > summary').click()
    page.locator('button[data-basket="mag7"]').click()
    ticker=page.locator('tr.lead-row:visible .expander').first.get_attribute('data-exp')
    page.locator('#ift-search').fill(ticker)
    expander=page.locator('tr.lead-row:visible .expander').first
    expander.press('Enter')
    check(key+'/selected-evidence-open',expander.get_attribute('aria-expanded')=='true' and page.locator('[data-detail="'+ticker+'"]').is_visible())
    def state():
        return page.evaluate("""() => ({
            query:document.getElementById('ift-search').value,
            basket:[...document.querySelectorAll('[data-basket][aria-pressed=true]')].map(e=>e.dataset.basket),
            stance:[...document.querySelectorAll('[data-stance][aria-pressed=true]')].map(e=>e.dataset.stance),
            selected:[...document.querySelectorAll('tr.lead-row.ift-selected')].map(e=>e.dataset.ticker),
            expanded:[...document.querySelectorAll('tr.lead-row .expander[aria-expanded=true]')].map(e=>e.dataset.exp),
            sort:document.querySelector('th[aria-sort=ascending],th[aria-sort=descending]')?.outerHTML,
            grouping:document.getElementById('ift-group-toggle')?.getAttribute('aria-pressed')
        })""")
    before=state()
    summary.focus();summary.press('Enter')
    check(key+'/enter-opens-native-guide',guide.get_attribute('open') is not None and summary.evaluate('(e)=>document.activeElement===e'))
    transitions=[]
    headers=guide.locator('.playbook-hd')
    for i in range(headers.count()):
        header=headers.nth(i)
        initially_open=header.get_attribute('aria-expanded')=='true'
        header.press('Space')
        toggled=header.get_attribute('aria-expanded')==str(not initially_open).lower()
        if header.get_attribute('aria-expanded')!='true':
            header.press('Enter')
        section=guide.locator('.playbook-section').nth(i)
        transitions.append({'index':i,'space_toggled':toggled,
            'expanded':header.get_attribute('aria-expanded')=='true',
            'body_visible':section.locator('.playbook-body').is_visible(),
            'focus_retained':header.evaluate('(e)=>document.activeElement===e')})
    check(key+'/all-four-subsections-keyboard-operable',len(transitions)==4 and all(all(v for k,v in t.items() if k!='index') for t in transitions),transitions=transitions)
    opposite='zh' if locale=='en' else 'en'
    check(key+'/only-requested-language-visible',
        guide.locator('.playbook-body > .l-'+locale+':visible').count()>0
        and guide.locator('.playbook-body > .l-'+opposite+':visible').count()==0)
    check(key+'/six-classifications-visible',guide.locator('ul.l-'+locale+' > li:visible').count()==6)
    geometry=guide.evaluate("""(el)=>{
        const box=el.getBoundingClientRect();
        const overflowing=[...el.querySelectorAll('*')].filter(e=>{
            const r=e.getBoundingClientRect();
            return r.width>0&&r.height>0&&(r.left < -0.5||r.right>innerWidth+0.5);
        }).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.trim().slice(0,90)}));
        return {viewport:innerWidth,document_width:document.documentElement.scrollWidth,
            guide_width:box.width,guide_scroll_width:el.scrollWidth,guide_client_width:el.clientWidth,
            left:box.left,right:box.right,overflowing};
    }""")
    check(key+'/opened-guide-wraps-without-horizontal-overflow',
        geometry['document_width']<=width and geometry['guide_scroll_width']<=geometry['guide_client_width']+1
        and not geometry['overflowing'],**geometry)
    path=OUT/f'guide-{width}-{theme}-{locale}.png'
    guide.screenshot(path=str(path))
    captures.append({'viewport':{'width':width,'height':900 if width>760 else 844},
        'theme':theme,'locale':locale,'state':'native guide and all four sections opened by keyboard',
        'capture_scope':'actual page guide element','source':'unmodified local feed files',
        'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    summary.focus();summary.press('Enter')
    check(key+'/enter-closes-and-retains-focus',guide.get_attribute('open') is None and summary.evaluate('(e)=>document.activeElement===e'))
    check(key+'/closed-guide-height-restored',abs(guide.bounding_box()['height']-closed_height)<0.1,
        initial_height=closed_height,final_height=guide.bounding_box()['height'])
    check(key+'/filters-selection-and-expanded-evidence-retained',state()==before,before=before,after=state())
    summary.press('Space')
    check(key+'/space-reopens-with-subsection-state-retained',
        guide.get_attribute('open') is not None and guide.locator('.playbook-hd[aria-expanded=true]').count()==4)
    check(key+'/no-page-errors-or-failed-responses',not errors and not failed,errors=errors,failed_responses=failed)
    print(key+': PASS',flush=True)
    context.close()

def main():
    assert not OUT.exists(),'Preserve existing evidence; use a new authorized output path for another material revision.'
    OUT.mkdir(parents=True)
    proof=source_proof()
    handler=functools.partial(QuietHandler,directory=str(ROOT/'site'))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            version=browser.version
            try:
                for width in [1440,390]:
                    for theme in ['light','dark']:
                        for locale in ['en','zh']:
                            matrix(browser,f'http://127.0.0.1:{server.server_port}/intraday_flow.html',width,theme,locale)
            finally:browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    report={'captured_at_utc':datetime.now(timezone.utc).isoformat(),
        'baseline_commit':BASELINE,
        'worktree_head_during_capture':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'capture_status':'R4 candidate source before its material commit; exact file hashes bind these observations',
        'independent_review':False,'production_acceptance':False,'browser':version,
        'source_identity':proof,'checks':checks,'check_count':len(checks),
        'passed':all(c['passed'] for c in checks),'captures':captures,
        'limits':['Static local page and existing local data only; no authenticated or production proof.',
                  'No startup diagnosis, new freshness policy, denied reviewer replay or denied Paper row batch.',
                  'R3 source/recovery/model proof retained through exact identity of all script elements.']}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'checks':len(checks),'captures':len(captures),
        'report':str((OUT/'verification.json').relative_to(ROOT))}),flush=True)

if __name__=='__main__':main()
