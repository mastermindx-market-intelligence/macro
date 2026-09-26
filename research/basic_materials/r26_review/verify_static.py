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
        super().__init__(); self.ids=[]; self.remote=[]; self.i18n=[]; self.meta={}; self.tabs=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
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
report={'kind':'non-browser research-prototype syntax, structure and pure-copy verification',
        'html_sha256':hashlib.sha256(HTML.read_bytes()).hexdigest(),
        'checks':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),
        'results':results,'browser_checks_executed':0,'screenshots_captured':0,'visual_acceptance':False,
        'production_tests_executed':0,'native_source_admissions':0,'paper_modified':False,
        'limitations':['Does not execute DOM handlers or simulate rendering.','Does not prove layout, keyboard interaction, focus restoration, translations in rendered context, authentication, rights or production data.'],
        'count_check_stdout':count.stdout.strip()}
(ROOT/'structure_verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:report[k] for k in ('html_sha256','checks','passed','failed')},indent=2))
print('FAILURES',[x['check'] for x in results if not x['passed']])
raise SystemExit(bool(report['failed']))
