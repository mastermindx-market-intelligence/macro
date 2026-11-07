"""Non-browser verification of an offline design study. No DOM simulation or URL access."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib, json, re, subprocess
ROOT = Path(__file__).resolve().parent
HTML = ROOT / 'materials_dossier_review.html'
text = HTML.read_text()
script = text.split('<script>')[1].split('</script>')[0]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.remote=[]; self.i18n=[]; self.meta={}; self.tabs=[]; self.aria_keys=[]; self.elements=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); self.elements.append((tag,a))
        if 'data-i18n-aria' in a: self.aria_keys.append(a['data-i18n-aria'])
        if 'id' in a: self.ids.append(a['id'])
        if 'data-i18n' in a: self.i18n.append(a['data-i18n'])
        if 'data-tab' in a: self.tabs.append(a['data-tab'])
        for k in ('src','href','action','poster'):
            if a.get(k,'').startswith(('http:','https:','//')): self.remote.append((tag,k,a[k]))
        if tag=='meta': self.meta[a.get('http-equiv',a.get('name',''))]=a.get('content')
page=Page();page.feed(text)
runner="""const fs=require('node:fs'),vm=require('node:vm');const s=fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0];const c=vm.createContext({});vm.runInContext(s.slice(0,s.indexOf('const $=')),c,{timeout:1000});process.stdout.write(vm.runInContext('JSON.stringify({words,cases})',c));"""
r=subprocess.run(['node','-e',runner,str(HTML)],check=True,text=True,capture_output=True)
data=json.loads(r.stdout);w=data['words'];cases=data['cases'];results=[]
def check(name, passed): results.append({'check':name,'passed':bool(passed)})
check('no duplicate static HTML ids',len(page.ids)==len(set(page.ids)))
check('three task-tab identifiers',page.tabs==['understand','compare','verify'])
check('English and Chinese have identical copy keys',set(w['en'])==set(w['zh']))
check('static translated elements have both language keys',all(k in w['en'] and k in w['zh'] for k in page.i18n))
check('ten family labels in each language',all(len(w[l]['familyNames'])==10 for l in w))
check('four required journey templates',set(c['id'] for c in cases)=={'nutrien','novonix','wheaton','weyerhaeuser'})
check('all journey text has paired language fields',all(set(c['en'])==set(c['zh']) for c in cases))
check('each journey has exactly three economic steps per language',all(len(c[l]['steps'])==3 for c in cases for l in w))
check('four inspectable disclosure sections per journey',all(all(isinstance(c[l].get(k),str) and c[l][k] for k in ('inputs','source','next','guard')) for c in cases for l in w))
check('family membership limited to declared labels',all(type(c['family'])==int and 0<=c['family']<10 for c in cases))
check('no external asset or navigation URLs in markup',not page.remote)
check('no script network or durable state calls',not re.search(r'\b(fetch|XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage|indexedDB)\b',script))
check('CSP explicitly blocks outgoing connections',"connect-src 'none'" in page.meta.get('Content-Security-Policy',''))
check('CSP blocks forms and remote defaults',all(x in page.meta.get('Content-Security-Policy','') for x in ("default-src 'none'","form-action 'none'")))
check('live-data disclaimer exists in both languages','No live data' in w['en']['notLive'] and bool(w['zh']['notLive']))
check('filter count uses actual visible and total lengths','journeyCountLabel(lang,visible.length,cases.length)' in script)
check('no common-score data field',all(not (set(c)&{'score','rank','weight','signal','target_price'}) for c in cases))
check('valid viewport declaration','width=device-width' in page.meta.get('viewport',''))
syn=subprocess.run(['node','--check'],input=script,text=True,capture_output=True)
check('complete inline JavaScript syntax',syn.returncode==0)
count_runner = """const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');const c=vm.createContext({});vm.runInContext(fs.readFileSync(0,'utf8'),c,{timeout:1000});assert.equal(vm.runInContext('typeof journeyCountLabel',c),'function');for(const [locale,n,label] of [['en',4,'4 of 4 journey templates'],['en',1,'1 of 4 journey templates'],['en',0,'0 of 4 journey templates'],['zh',4,'4 / 4 个案例模板'],['zh',1,'1 / 4 个案例模板'],['zh',0,'0 / 4 个案例模板']])assert.equal(vm.runInContext(`journeyCountLabel(${JSON.stringify(locale)},${n},4)`,c),label);console.log('PASS: 6 pure visible/total count cases; no DOM/browser execution');"""
count=subprocess.run(['node','-e',count_runner],input=script[:script.index('const $=')],text=True,capture_output=True)
check('six pure visible-total copy cases',count.returncode==0)
# R27 source-contract checks are NOT DOM, assistive-technology or layout tests.
check('three localized accessibility names are declared',
      set(page.aria_keys)=={'reviewControlsLabel','shellContextLabel','taskListLabel'})
check('localized accessibility names have both language values',
      len(page.aria_keys)==3 and all(k in w['en'] and k in w['zh'] for k in page.aria_keys))
check('renderer wires localized accessibility attributes',
      "querySelectorAll('[data-i18n-aria]')" in script and
      "n.setAttribute('aria-label',t(n.dataset.i18nAria))" in script)
check('review controls declare a labelled group',
      any(a.get('role')=='group' and a.get('data-i18n-aria')=='reviewControlsLabel' for _,a in page.elements))
check('tab panel declares a keyboard focus target',
      any(a.get('id')=='panel' and a.get('tabindex')=='0' for _,a in page.elements))
check('announcement declares atomic status semantics',
      any(a.get('id')=='announcement' and a.get('role')=='status' and a.get('aria-atomic')=='true' for _,a in page.elements))
check('comparison renderer declares a native table and caption',
      all(v in script for v in ("node('table','comparison-table')", "node('caption','sr-only',t('compareIntro'))", "node('thead')", "node('tbody')")))
check('comparison renderer declares column and row header scopes',
      "heading.setAttribute('scope','col')" in script and "company.setAttribute('scope','row')" in script)
check('comparison declares a focusable in-container scroll region',
      "rows.setAttribute('role','region')" in script and "rows.tabIndex=0" in script and
      '.compare-list{overflow-x:auto;' in text)
check('mobile review and family controls declare larger targets',
      '.review-controls select,.review-controls .btn,.family{min-height:44px;font-size:14px}' in text)
check('tab changes append history rather than overwrite it',
      "history.pushState(null,'','#'+value)" in script and 'history.replaceState(' not in script)
check('hash restoration shares a closed tab parser',
      "function applyTaskHash()" in script and "tab=taskForHash(location.hash)" in script and
      "window.addEventListener('hashchange',applyTaskHash)" in script)
check('skip anchor is kept outside tab restoration',
      "if(location.hash==='#main')return" in script)
check('render uses the current view announcement',
      "announcementForView(lang,tab,state,family,selected)" in script)
check('script-disabled mode has an explicit bilingual notice',
      '<noscript>' in text and 'JavaScript' in text.split('<noscript>')[1].split('</noscript>')[0] and
      '原型' in text.split('<noscript>')[1].split('</noscript>')[0])

# Only the data + pure helper prefix executes. No document/window/DOM stand-in exists.
pure_runner = r"""const fs=require('node:fs'),vm=require('node:vm');
const c=vm.createContext({}); vm.runInContext(fs.readFileSync(0,'utf8'),c,{timeout:1000});
const out=[];
function test(name,expression){let passed=false;try{passed=vm.runInContext(expression,c,{timeout:1000})===true;}catch(e){if(e.name!=='ReferenceError')throw e;}out.push({check:name,passed});}
for(const [hash,expected] of [['#understand','understand'],['#compare','compare'],['#verify','verify'],['','understand'],['#UNKNOWN','understand'],['#%zz','understand']])
 test('pure task hash '+JSON.stringify(hash),`typeof taskForHash==='function' && taskForHash(${JSON.stringify(hash)})===${JSON.stringify(expected)}`);
for(const locale of ['en','zh']){
 test('pure selected-journey announcement '+locale,`typeof announcementForView==='function' && announcementForView('${locale}','understand','study',-1,'nutrien').includes('Nutrien') && announcementForView('${locale}','understand','study',-1,'nutrien').includes(journeyCountLabel('${locale}',4,4))`);
 test('pure empty-family announcement '+locale,`typeof announcementForView==='function' && announcementForView('${locale}','understand','study',0,'nutrien').includes(words['${locale}'].emptyFamily) && !announcementForView('${locale}','understand','study',0,'nutrien').includes('Nutrien')`);
 for(const [state,key] of [['denied','deniedTitle'],['error','errorTitle']])
  test('pure '+state+' announcement suppresses selection '+locale,`typeof announcementForView==='function' && announcementForView('${locale}','understand','${state}',-1,'nutrien').includes(words['${locale}']['${key}']) && !announcementForView('${locale}','understand','${state}',-1,'nutrien').includes('Nutrien')`);
 test('pure comparison count '+locale,`typeof announcementForView==='function' && announcementForView('${locale}','compare','study',0,'nutrien').includes(journeyCountLabel('${locale}',4,4))`);
 test('pure unknown-state announcement is bounded '+locale,`typeof announcementForView==='function' && announcementForView('${locale}','understand','unexpected',-1,'nutrien').includes(words['${locale}'].stateDisconnected) && !announcementForView('${locale}','understand','unexpected',-1,'nutrien').includes('Nutrien')`);
}
console.log(JSON.stringify(out));"""
pure=subprocess.run(['node','-e',pure_runner],input=script[:script.index('const $=')],text=True,capture_output=True,check=True)
results.extend(json.loads(pure.stdout))
report={'kind':'non-browser research-prototype syntax, structure and pure-copy verification',
        'html_sha256':hashlib.sha256(HTML.read_bytes()).hexdigest(),
        'checks':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),
        'results':results,'browser_checks_executed':0,'screenshots_captured':0,'visual_acceptance':False,
        'production_tests_executed':0,'dom_handlers_executed':0,'assistive_technology_checks':0,'native_source_admissions':0,'paper_modified':False,
        'limitations':['Does not execute DOM handlers, instantiate DOM stand-ins, simulate rendering or test browser history/focus behavior.','Does not prove layout, keyboard interaction, focus restoration, translations in rendered context, authentication, rights or production data.'],
        'count_check_stdout':count.stdout.strip()}
(ROOT/'structure_verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:report[k] for k in ('html_sha256','checks','passed','failed')},indent=2))
print('FAILURES',[x['check'] for x in results if not x['passed']])
raise SystemExit(bool(report['failed']))
