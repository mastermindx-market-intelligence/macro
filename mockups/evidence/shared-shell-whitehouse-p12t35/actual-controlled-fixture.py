"""P12.T35 actual renderer, retained rows; isolated file fixture, no network."""
import hashlib,json,re,subprocess,sys,html as htmllib
from pathlib import Path
from unittest.mock import patch,Mock
from urllib.parse import urlsplit
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright,expect
E=Path(__file__).parent/'source-349e12c9';E.mkdir(exist_ok=True)
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/claude/cd8f6fc4b43f4cb4/whitehouse-source-label-p12t34-f5f6d0725551ccde')
sys.path.insert(0,str(ROOT));from scripts import build_whitehouse as b
assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)==''
REV=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def git(p):return subprocess.check_output(['git','show',REV+':'+p],cwd=ROOT)
ledger=Mock();ledger.exists.return_value=True;ledger.read_text.return_value=git('data/whitehouse/alerts.jsonl').decode()
with patch.object(b,'_ledger_path',return_value=ledger):rows=b._load_ledger(ROOT)
original_hash=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
selected=next(x for x in rows if 'finland' in str(x.get('source_url')))
other=next(x for x in rows if x.get('section')=='treasury')
archived=next(x for x in rows if x.get('section')!='treasury' and x.get('published','').startswith('2026-10-17'))
full=b._render_page(ROOT,rows,b._load_treasury_watch(ROOT/'site'))
full_ids=re.findall(r'<section class="wh-card(?: live)?" id="([^"]+)"',full)
assert full_ids==[x['id'] for x in rows]
assert sum(x.startswith('wh-') for x in full_ids)==63 and sum(x.startswith('tw-') for x in full_ids)==14
source_hrefs=[htmllib.unescape(x) for x in re.findall(r'<p class="wh-src"><a href="([^"]+)"',full)]
assert source_hrefs==[x['source_url'] for x in rows if x.get('source_url')]
assert hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()==original_hash
view=b._render_page(ROOT,[selected,other],b._load_treasury_watch(ROOT/'site'))
missing=dict(selected,id='wh-synthetic-missing',published=None,generated_at=None,analysis=None,sectors=[],tickers=[],source_url=None,banner_days=0)
views={'reader':view,'empty':b._render_page(ROOT,[]),'missing':b._render_page(ROOT,[missing]),'archived':b._render_page(ROOT,[archived]),'treasury':b._render_page(ROOT,[],b._load_treasury_watch(ROOT/'site'))}
site=E/'site';site.mkdir(exist_ok=True)
for name,value in views.items():(site/(name+'.html')).write_text(value)
# Copy exact local preimages for all generated refs and their CSS dependencies.
queue=[]
for value in views.values():queue+=re.findall(r'<(?:script|link)\b[^>]*(?:src|href)="([^"]+)"',value)
seen=set()
while queue:
 href=queue.pop();u=urlsplit(href)
 if u.scheme or u.netloc or not u.path or u.path.startswith('/'):continue
 rel=Path(u.path)
 if '..' in rel.parts or rel.as_posix() in seen:continue
 seen.add(rel.as_posix());src=ROOT/'site'/rel
 if not src.is_file():continue
 raw=src.read_bytes();dst=site/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
 if rel.suffix=='.css':
  for path in re.findall(r'url\([\'\"]?([^\'\")]+)',raw.decode(errors='replace')):
   if not urlsplit(path).scheme:
    fullpath=(src.parent/urlsplit(path).path).resolve()
    try:queue.append(fullpath.relative_to(ROOT/'site').as_posix())
    except ValueError:pass
owned=['scripts/build_whitehouse.py','templates/whitehouse.html.j2','tests/test_whitehouse_build.py','research/migration_packets/MP-P12-T35-whitehouse-editorial-reader.md']
result={'head':REV,'kind':'standalone actual-renderer retained-input fixture, NOT inShell/serving/primarybody/rights/science','sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in owned},'treasury_source_sha256':hashlib.sha256((ROOT/'site/whdata/treasury_watch.json').read_bytes()).hexdigest(),'full_records':len(rows),'full_original_anchor_order_equal':True,'all_source_urls_equal':True,'input_hash_unchanged':original_hash,'new_js_bytes':len((ROOT/'templates/whitehouse.html.j2').read_text().split('{% block body_scripts %}')[1]),'selected_source_id':selected['id'],'profiles':[],'states':[],'failures':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True)
 try:
  for width in (1440,390):
   for theme in ('dark','light'):
    for lang in ('en','zh'):
     case={'width':width,'theme':theme,'lang':lang};c=browser.new_context(viewport={'width':width,'height':900},color_scheme=theme)
     network=[];c.route(re.compile('^https?://'),lambda r:(network.append(r.request.url),r.abort()))
     c.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('themeAuto','0');localStorage.setItem('lang','{lang}');")
     p=c.new_page();errors=[];p.on('pageerror',lambda err:errors.append(str(err)))
     try:
      base=(site/'reader.html').as_uri()+'#'+selected['id'];p.goto(base,wait_until='load');card=p.locator('#'+selected['id']);expect(card).to_be_visible()
      outline=card.locator('[data-wh-outline]');expect(outline).to_have_js_property('open',width>820)
      if lang=='zh':
       assert 'news' not in card.locator('.row1').inner_text() and 'medium' not in card.locator('.row1').inner_text()
      case['metrics']=card.evaluate('(e)=>({cardWidth:e.getBoundingClientRect().width,bodyWidth:e.querySelector(".wh-body").getBoundingClientRect().width,railWidth:e.querySelector("aside").getBoundingClientRect().width,border:getComputedStyle(e).borderColor,background:getComputedStyle(e).backgroundColor,shadow:getComputedStyle(e).boxShadow,up:getComputedStyle(e.querySelector(".wh-chg.up")||e.querySelector(".wh-dir.benefit")).color})')
      assert case['metrics']['bodyWidth']<700
      assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
      p.screenshot(path=str(E/f'reader-{width}-{theme}-{lang}.png'))
      if width==390:outline.locator('summary').focus();outline.locator('summary').press('Enter');expect(outline).to_have_js_property('open',True)
      link=outline.locator('a[href$="-source"]');link.focus();link.press('Enter')
      target=card.locator('h3[id$="-source"]');expect(target).to_be_focused();expect(link).to_have_attribute('aria-current','location')
      case['hit_targets']={sel:card.locator(sel).first.evaluate('(e)=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})') for sel in ['.wh-src a','.wh-sym']}
      assert all(v['width']>=40 and v['height']>=40 for v in case['hit_targets'].values())
      case['focused_target']=p.evaluate('document.activeElement.id');case['target_url']=p.url
      original=card.locator('.wh-src a');expect(original).to_have_attribute('href',selected['source_url']);original.focus();expect(original).to_be_focused()
      p.screenshot(path=str(E/f'source-{width}-{theme}-{lang}.png'))
      p.go_back(wait_until='domcontentloaded');expect(p).to_have_url(base)
      p.go_forward(wait_until='domcontentloaded');expect(p).to_have_url(case['target_url'])
      p.reload(wait_until='load');expect(link).to_have_attribute('aria-current','location')
      expect(target).to_be_visible();case['back_forward_reload']='PASS';case['page_errors']=errors;case['http_attempts']=network
      assert not errors and not network
     except Exception as exc:case['failure']=str(exc);result['failures'].append(case);p.screenshot(path=str(E/f'failure-{width}-{theme}-{lang}.png'))
     finally:result['profiles'].append(case);c.close()
  for state,width,theme,lang in [('empty',390,'light','zh'),('missing',390,'dark','en'),('archived',1440,'light','en'),('treasury',1440,'dark','en'),('treasury',390,'light','zh')]:
   c=browser.new_context(viewport={'width':width,'height':900},color_scheme=theme);requests=[];c.route(re.compile('^https?://'),lambda r:(requests.append(r.request.url),r.abort()))
   c.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('themeAuto','0');localStorage.setItem('lang','{lang}');")
   p=c.new_page();p.goto((site/(state+'.html')).as_uri(),wait_until='load')
   if state=='empty':expect(p.locator('.wh-empty')).to_be_visible()
   if state=='missing':
    expect(p.locator('.wh-src')).to_contain_text('Primary-source link unavailable.');assert p.locator('.wh-src a').count()==0
    p.locator('.wh-reading').scroll_into_view_if_needed()
   if state=='treasury':
    p.locator('#treasury-watch').scroll_into_view_if_needed()
    if lang=='zh':
     assert 'neutral_hollow' not in p.locator('#treasury-watch').inner_text() and '耗尽' in p.locator('#treasury-watch').inner_text()
   if state=='archived':assert p.locator('.wh-card .wh-badge.live').count()==0;expect(p.locator('.wh-card')).to_contain_text('Oct 17, 2026')
   assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
   p.screenshot(path=str(E/f'state-{state}-{width}-{theme}-{lang}.png'));result['states'].append({'state':state,'width':width,'theme':theme,'lang':lang,'http_attempts':requests});c.close()
 finally:browser.close();(E/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)==''
print(json.dumps({'head':REV,'profiles':len(result['profiles']),'states':len(result['states']),'failures':result['failures']},indent=2))
if result['failures']:sys.exit(1)
