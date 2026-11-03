"""P12.T40 independent ephemeral/offline browser: actual native renderer/assets."""
import hashlib,json,mimetypes,subprocess
from pathlib import Path
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright,expect
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/today-business-activity-depth-20261103-a455e0785d7ea09e');E=Path(__file__).parent
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();view=json.loads((E/'view.json').read_text());cache={};result={'head':HEAD,'kind':'controlled standalone retained snapshot, actual native validator/view/template/client; ephemeral offline context; no inShell/served/current-economic claim','profiles':[],'failures':[]}
def asset(path):
 if path in cache:return cache[path]
 if '..' in Path(path).parts:return None
 for prefix in ['templates/','site/']:
  try:raw=subprocess.check_output(['git','show',HEAD+':'+prefix+path],cwd=ROOT,stderr=subprocess.DEVNULL);cache[path]=(raw,prefix+path);return cache[path]
  except subprocess.CalledProcessError:pass
 return None
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 try:
  for width,theme,lang in [(1440,'dark','en'),(390,'light','zh')]:
   case={'width':width,'theme':theme,'lang':lang,'requests':[],'blocked':[],'errors':[]};state={'page':'healthy'}
   c=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844},reduced_motion='reduce',color_scheme=theme,offline=True,service_workers='block')
   c.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('themeAuto','0');localStorage.setItem('lang','{lang}');")
   def route(r):
    u=urlsplit(r.request.url);path=unquote(u.path).lstrip('/')
    if u.hostname=='fixture.invalid' and path=='macro_business_activity.html':raw=(E/(state['page']+'.html')).read_bytes();source='native-render-'+state['page'];ct='text/html'
    elif u.hostname=='fixture.invalid' and Path(path).suffix in ['.js','.css','.svg','.png','.woff2','.ico'] and (found:=asset(path)):
     raw,source=found;ct=mimetypes.guess_type(path)[0] or 'application/octet-stream'
    else:case['blocked'].append({'path':u.path,'origin':u.hostname});r.abort();return
    case['requests'].append({'path':path,'source':source,'sha256':hashlib.sha256(raw).hexdigest()});r.fulfill(status=200,body=raw,content_type=ct)
   c.route('**/*',route);p=c.new_page();p.on('pageerror',lambda e:case['errors'].append(str(e)))
   try:
    url='https://fixture.invalid/macro_business_activity.html#current';p.goto(url,wait_until='load');expect(p.locator('#mq-panel-current')).to_be_visible();expect(p.locator('.mq-metric')).to_have_count(len(view['metrics']));p.screenshot(path=str(E/f'before-v2-{width}-{theme}-{lang}-entry.png'))
    metric=p.locator('.mq-metric').nth(0);expect(metric).to_contain_text(view['metrics'][0]['value'][lang]);metric.locator('summary').click();metric.evaluate('(e)=>e.scrollIntoView({block:"start"})');case['leadingDetails']=metric.inner_text();case['detailsSummaryBox']=metric.locator('summary').bounding_box();p.screenshot(path=str(E/f'before-v2-{width}-{theme}-{lang}-metric.png'))
    button=p.locator('.mq-evidence-button');button.scroll_into_view_if_needed();before={'url':p.url,'scroll':p.evaluate('scrollY')};button.click();drawer=p.locator('#mq-evidence-drawer');expect(drawer).to_be_visible();expect(p.locator('#mq-close-evidence')).to_be_focused();case['closeBox']=p.locator('#mq-close-evidence').bounding_box();source=drawer.locator('.mq-source').first;source.scroll_into_view_if_needed();case['sourceReceipt']=source.inner_text();case['allSources']=drawer.locator('.mq-source').all_inner_texts();p.screenshot(path=str(E/f'before-v2-{width}-{theme}-{lang}-source.png'));p.keyboard.press('Escape');expect(drawer).to_be_hidden();expect(button).to_be_focused();assert p.url==before['url'];assert metric.locator('details').evaluate('(e)=>e.open');case['returned']={'url':p.url,'scrollBefore':before['scroll'],'scrollAfter':p.evaluate('scrollY'),'openerFocused':True,'metricDetailsStillOpen':True};assert abs(case['returned']['scrollAfter']-before['scroll'])<=3
    p.locator('[data-mq-tab="history"]').click();expect(p.locator('#mq-panel-history')).to_be_visible();assert p.url.endswith('#history');p.reload(wait_until='load');expect(p.locator('#mq-panel-history')).to_be_visible();case['history']=p.locator('#mq-panel-history').inner_text();case['historyUrl']=p.url
    p.locator('[data-mq-tab="history"]').focus();p.keyboard.press('Home');expect(p.locator('#mq-panel-current')).to_be_visible();assert p.url.endswith('#current');case['healthyOverflow']=p.evaluate('document.documentElement.scrollWidth>innerWidth')
    state['page']='mismatch';p.reload(wait_until='load');expect(p.locator('.mq-metric-value')).to_have_count(0);case['refusal']=p.locator('main').inner_text();p.screenshot(path=str(E/f'before-v2-{width}-{theme}-{lang}-refusal.png'));assert not case['errors'];case['noEconomicFigureOnRefusal']=True
   except Exception as ex:
    case['failure']=str(ex);result['failures'].append({'width':width,'failure':str(ex)});p.screenshot(path=str(E/f'probe-v2-failure-{width}.png'))
   finally:result['profiles'].append(case);c.close()
 finally:browser.close()
(E/'before-v2-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'profiles':len(result['profiles']),'failures':result['failures'],'controls':[{'width':c['width'],'close':c.get('closeBox'),'details':c.get('detailsSummaryBox')} for c in result['profiles']]},ensure_ascii=False));assert not result['failures']
