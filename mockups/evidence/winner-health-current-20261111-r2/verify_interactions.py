from pathlib import Path
import os, sys, json, hashlib, importlib.util, threading, http.server, socketserver, functools, datetime, subprocess
import argparse
parser=argparse.ArgumentParser(description='Verify Winner Health interactions against explicit synthetic fixtures.')
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
W=args.root.resolve();P=args.output_dir.resolve();P.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(W))
import engine.i18n
from scripts import build_winner_health_page as bwh
from playwright.sync_api import sync_playwright
spec=importlib.util.spec_from_file_location('wh_page_tests',W/'tests/test_winner_health_page.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
healthy=[]
for i in range(80):
 r=m._row(ticker=f'T{i:03d}',legs=[]);r.update(name=f'Running {i:03d}',state='extended_healthy');healthy.append(r)
watch=[]
for i in range(9):
 r=m._row(ticker=f'N{i:02d}');r.update(name=f'Name {i:02d}',name_zh=f'名称{i:02d}');watch.append(r)
ctx=m._ctx({'extended_healthy':healthy,'extended_watch':watch})
fixture=P/'interaction-fixture.json';fixture.write_text(json.dumps(ctx,ensure_ascii=False,indent=2)+'\n')
html=bwh.render(W,fixture=fixture)
target=W/'site/__proof_winner_health_interaction.html';target.write_text(html)
out=P/'interaction-observation';out.mkdir(exist_ok=True)
checks=[];cases=[]
def check(case,name,ok,actual=None):
 checks.append({'case':case,'check':name,'pass':bool(ok),'actual':actual})
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=socketserver.ThreadingTCPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(W/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{server.server_address[1]}/__proof_winner_health_interaction.html'
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width in [1440,390]:
   for theme in ['dark','light']:
    case=f'{width}-{theme}';errors=[];responses=[]
    context=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=1)
    context.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.removeItem('themeAuto');localStorage.setItem('lang','en');")
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:responses.append({'status':r.status,'url':r.url}) if r.status>=400 else None)
    page.goto(url,wait_until='networkidle')
    functions=page.evaluate("() => ({theme:typeof window.setTheme,lang:typeof window.setLang})")
    check(case,'real_theme_and_language_functions',functions=={'theme':'function','lang':'function'},functions)
    page.evaluate("(s)=>{window.setTheme(s.theme);window.setLang('en');}",{'theme':theme});page.wait_for_timeout(1250)
    run=page.locator('#g-running');group=page.locator('#g-wear');button=group.locator('.wh-more');query=page.locator('#wh-find-q');null=page.locator('#wh-find-null')
    check(case,'healthy_rollup_count_only',run.locator('.row').count()==0 and run.locator('.wh-more').count()==0 and '80' in run.inner_text(),run.inner_text())
    check(case,'initial_eight_visible',group.locator('.row:visible').count()==8,group.locator('.row:visible').count())
    check(case,'initial_collapsed_aria',button.get_attribute('aria-expanded')=='false',button.get_attribute('aria-expanded'))
    button.click();check(case,'expand_nine',group.locator('.row:visible').count()==9 and button.get_attribute('aria-expanded')=='true',{'visible':group.locator('.row:visible').count(),'aria':button.get_attribute('aria-expanded')})
    button.click();check(case,'collapse_eight',group.locator('.row:visible').count()==8 and button.get_attribute('aria-expanded')=='false')
    button.scroll_into_view_if_needed();button.evaluate('(e)=>e.blur()');page.mouse.move(1,1);page.wait_for_timeout(150)
    rest=button.evaluate('(e)=>getComputedStyle(e).backgroundColor')
    button.hover();page.wait_for_timeout(150);hover=button.evaluate('(e)=>getComputedStyle(e).backgroundColor')
    check(case,'hover_paint_changes',rest!=hover,{'rest':rest,'hover':hover})
    page.mouse.move(1,1);button.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
    focus=button.evaluate("(e)=>({active:document.activeElement===e,visible:e.matches(':focus-visible'),width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle,color:getComputedStyle(e).outlineColor})")
    check(case,'real_tab_button_focus',focus['active'] and focus['visible'] and focus['width']>=2 and focus['style']=='solid',focus)
    group.screenshot(path=str(out/f'group-focus-{case}.png'))
    query.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
    qfocus=query.evaluate("(e)=>({active:document.activeElement===e,visible:e.matches(':focus-visible'),width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle})")
    check(case,'real_tab_search_focus',qfocus['active'] and qfocus['visible'] and qfocus['width']>=2 and qfocus['style']=='solid',qfocus)
    query.fill('T079')
    message=null.inner_text()
    check(case,'rollup_only_search_honest_null',null.is_visible() and 'No individually listed name matches' in message and 'counts only' in message and "isn't tracked" not in message,message)
    query.fill('N08')
    visible=group.locator('.row:visible .tk').all_text_contents()
    more=button.evaluate("(e)=>({hidden:e.hidden,display:getComputedStyle(e).display,rects:e.getClientRects().length})")
    check(case,'ninth_name_found',visible==['N08'] and not null.is_visible(),visible)
    check(case,'search_hides_more_visually',not button.is_visible(),more)
    query.fill('  n08  ')
    check(case,'trimmed_casefold_search',group.locator('.row:visible .tk').all_text_contents()==['N08'])
    page.evaluate("window.setLang('zh')")
    page.wait_for_function("document.querySelector('#wh-find-q').placeholder==='代码或名称'")
    check(case,'locale_search_chrome',query.get_attribute('placeholder')=='代码或名称' and query.get_attribute('aria-label')=='查找代码',{'placeholder':query.get_attribute('placeholder'),'aria':query.get_attribute('aria-label')})
    query.fill('名称08')
    check(case,'chinese_name_search',group.locator('.row:visible .tk').all_text_contents()==['N08'])
    query.fill('T079');message_zh=null.inner_text()
    check(case,'chinese_rollup_qualified_null','逐只列出的标的中' in message_zh and '只显示数量' in message_zh,message_zh)
    null.screenshot(path=str(out/f'search-null-zh-{case}.png'))
    query.fill('')
    check(case,'clear_restores_cap_rollup',group.locator('.row:visible').count()==8 and button.is_visible() and button.get_attribute('aria-expanded')=='false' and run.is_visible() and not null.is_visible())
    check(case,'no_document_overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    check(case,'no_page_errors',not errors,errors)
    check(case,'no_failed_responses',not responses,responses)
    cases.append({'case':case,'page_errors':errors,'failed_responses':responses})
    context.close()
  browser.close()
finally:
 server.shutdown();server.server_close()
report={'schema':'macro.winner_health.interaction_observation.v1','source':subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'SYNTHETIC_FIXTURE_REPLAY','fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'html_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_template_blob':subprocess.check_output(['git','-C',str(W),'hash-object','templates/winner_health.html.j2'],text=True).strip(),'checks':checks,'cases':cases,'result':'PASS' if all(c['pass'] for c in checks) else 'FAIL'}
(out/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'result':report['result'],'checks':len(checks),'failures':[x for x in checks if not x['pass']],'receipt':str(out/'receipt.json')},ensure_ascii=False))
sys.exit(0 if report['result']=='PASS' else 1)
