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

from PIL import Image
states=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 try:
  for width in (1440,390):
   for theme in ('dark','light'):
    for lang in ('en','zh'):
     c=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844},offline=True,service_workers='block',reduced_motion='reduce',color_scheme=theme)
     c.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('themeAuto','0');localStorage.setItem('lang','{lang}');")
     errors=[];blocked=[]
     def route(r):
      u=urlsplit(r.request.url);path=unquote(u.path).lstrip('/')
      if u.hostname=='fixture.invalid' and path=='macro_business_activity.html':raw=(E/'candidate-healthy.html').read_bytes();ct='text/html'
      elif u.hostname=='fixture.invalid' and Path(path).suffix in ['.js','.css','.svg','.png','.woff2','.ico'] and (found:=asset(path)):raw,source=found;ct=mimetypes.guess_type(path)[0] or 'application/octet-stream'
      else:blocked.append({'origin':u.hostname,'path':u.path});r.abort();return
      r.fulfill(status=200,body=raw,content_type=ct)
     c.route('**/*',route);p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.goto('https://fixture.invalid/macro_business_activity.html#current',wait_until='load')
     expect(p.locator('html')).to_have_attribute('data-lang',lang);expect(p.locator('html')).to_have_attribute('data-theme',theme)
     applied={'theme':p.locator('html').get_attribute('data-theme'),'locale':p.locator('html').get_attribute('data-lang')}
     def shot(kind,forced=None):
      dest=E/f'settled-{width}-{theme}-{lang}-{kind}.png';p.screenshot(path=str(dest));raw=dest.read_bytes();dimensions=Image.open(dest).size
      states.append({'viewport':'desktop' if width==1440 else 'mobile','viewport_width':width,'viewport_height':900 if width==1440 else 844,'theme':theme,'locale':lang,'access':'controlled-retained-local','force_state':forced,'captured':True,'file':dest.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'width':dimensions[0],'height':dimensions[1],'applied_theme':applied['theme'],'applied_locale':applied['locale'],'applied_force_state':forced,'errors':list(errors),'networkBlocked':list(blocked)})
     shot('entry');metric=p.locator('.mq-metric').first;metric.locator('summary').focus();p.keyboard.press('Enter');metric.evaluate('(e)=>{e.scrollIntoView({block:"start"});window.scrollBy(0,-210)}');assert metric.locator('summary').bounding_box()['height']==44;shot('depth','metric-depth')
     if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
      p.locator('.mq-evidence-button').click();expect(p.locator('#mq-close-evidence')).to_be_focused();shot('drawer','source-drawer')
     assert not errors;c.close()
 finally:browser.close()
tool=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
manifest={'schema':'mastermind.p0_evidence.v2','tool':{'module_ref':str(Path(__file__)),'module_sha256':tool,'version':'P12.T40 bounded offline native-renderer capture'},'target':{'route':'/macro_business_activity.html','baseline':HEAD,'source':json.loads((E/'source-qualification.json').read_text())['candidateSource'],'kind':'controlled standalone native-renderer retained snapshot; not served/inShell/current-economic acceptance'},'axes':{'force_states':[{'name':'metric-depth','kind':'native-disclosure'},{'name':'source-drawer','kind':'native-dialog'}]},'pages':[{'page_id':'macro:macro_business_activity','route':'/macro_business_activity.html','states':states}]}
(E/'capture-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'rest':sum(x['force_state'] is None for x in states),'depth':sum(x['force_state']=='metric-depth' for x in states),'drawer':sum(x['force_state']=='source-drawer' for x in states),'errors':sum(len(x['errors']) for x in states)}))
