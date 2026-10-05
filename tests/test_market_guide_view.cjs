/* DOM adapter unit tests only. This harness is not a browser or accessibility proof. */
'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.join(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,'research/reference_rethink_20260921',name),'utf8');
const fixtureJSON=require('node:child_process').execFileSync(process.env.PYTHON||'python3',[path.join(__dirname,'fixtures/market-guide/compile_fixture.py')],{encoding:'utf8'});
const fixture=()=>JSON.parse(fixtureJSON);
function harness(url='https://review.invalid/reference.html',data=fixture(),options={}){
  let doc,context;
  class Element {
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.dataset={};this.handlers={};this.parent=null;this.hidden=false;this.open=false;this._text='';this.value='';}
    set textContent(text){this.children=[];this._text=String(text);}
    get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
    set innerHTML(_){throw new Error('Dynamic innerHTML is forbidden');}
    setAttribute(key,value){this.attrs[key]=String(value);if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=String(value);if(key==='id')this.id=value;}
    getAttribute(key){return this.attrs[key]??null;}
    append(...items){for(const item of items){item.parent=this;this.children.push(item);}}
    replaceChildren(...items){for(const item of this.children)item.parent=null;this.children=[];this._text='';this.append(...items);}
    addEventListener(type,fn){(this.handlers[type] ||= new Set()).add(fn);}
    removeEventListener(type,fn){this.handlers[type]?.delete(fn);}
    fire(type,options={}){for(const fn of [...(this.handlers[type]||[])])fn({type,target:this,currentTarget:this,preventDefault(){},...options});}
    matches(selector){
      if(selector.startsWith('.'))return (this.attrs.class||'').split(' ').includes(selector.slice(1));
      const attr=/^\[([^=]+)(?:="([^"]*)")?\]$/.exec(selector);
      if(attr)return Object.hasOwn(this.attrs,attr[1])&&(attr[2]===undefined||this.attrs[attr[1]]===attr[2]);
      if(selector.startsWith('#'))return this.id===selector.slice(1);
      return this.tagName===selector.toUpperCase();
    }
    all(selector){return this.children.flatMap(child=>[...(child.matches(selector)?[child]:[]),...child.all(selector)]);}
    querySelector(selector){return this.all(selector)[0]||null;}
    focus(){doc.activeElement=this;}
    showModal(){this.open=true;}
    close(){this.open=false;this.fire('close');}
    get isConnected(){let node=this;while(node.parent)node=node.parent;return node===doc.body;}
    remove(){if(this.parent){this.parent.children=this.parent.children.filter(c=>c!==this);this.parent=null;}}
    prepend(...items){for(const item of items)item.parent=this;this.children=[...items,...this.children];}
  }
  doc=Object.assign(new Element('document'),{body:new Element('body'),documentElement:new Element('html'),createElement:tag=>new Element(tag),title:'Macro dashboard'});
  doc.documentElement.lang='en';doc.documentElement.setAttribute('data-theme','light');
  doc.querySelector=selector=>doc.body.querySelector(selector);
  doc.getElementById=id=>doc.body.querySelector('#'+id);
  doc.activeElement=doc.body;
  for(const [tag,id,cls] of [['button','language',''],['button','theme',''],['div','app',''],['section','fallback','fallback'],['dialog','help','']]){const e=new Element(tag);e.setAttribute('id',id);if(cls)e.setAttribute('class',cls);doc.body.append(e);}
  const handlers={},history=[];
  context={document:doc,URL,URLSearchParams,console,location:{href:url,origin:new URL(url).origin},scrollY:0,
    scrollTo(x,y){context.scrollY=y;},
    addEventListener(type,fn){(handlers[type] ||= new Set()).add(fn);},
    removeEventListener(type,fn){handlers[type]?.delete(fn);},
    history:{pushState(_,__,url){history.push(url);context.location.href=url;},replaceState(_,__,url){context.location.href=url;}},
  };
  context.window=context;vm.createContext(context);vm.runInContext(read('guide-client.js'),context);vm.runInContext(read('guide-view.js'),context);
  const host=doc.getElementById('app'),dialog=doc.getElementById('help');
  if(options.seedHost){if(options.seedHost.className)host.setAttribute('class',options.seedHost.className);if(options.seedHost.text)host.textContent=options.seedHost.text;}
  const app=context.MastermindGuideView.mount({host,dialog,manifest:data,ownerOrigin:context.location.origin,...options});
  return {context,doc,host,dialog,app,history,click:e=>{assert.ok(e,'click target exists');e.fire('click');},find:(selector)=>host.querySelector(selector),all:(selector)=>host.all(selector),fire:type=>[...(handlers[type]||[])].forEach(fn=>fn())};
}
test('mounts three source-defined questions and preserves fallback until valid data',()=>{
 const h=harness();assert.equal(h.find('h1').textContent,'Market Guide');assert.equal(h.all('[data-topic]').length,3);assert.equal(h.doc.getElementById('fallback').hidden,true);
});
test('question routes to curated source membership rather than all internal families',()=>{
 const h=harness();h.click(h.find('[data-topic="risk"]'));assert.equal(h.all('article').length,2);assert.match(h.find('#result-count').textContent,/2/);
});
test('search and deep-link coverage alias share one canonical result',()=>{
 const h=harness('https://review.invalid/reference.html#regime-badge');assert.equal(h.find('h1').textContent,'Market Regime');assert.ok(h.find('[data-alias]'));
 h.click(h.find('[data-home]'));const input=h.find('#search');input.value='Regime Badge';input.fire('input');assert.equal(h.all('article').length,1);assert.equal(h.find('article').querySelector('a').textContent,'Market Regime');
});
test('board name opens an explanatory view, not an indicator page',()=>{
 const h=harness('https://review.invalid/reference.html#prophet-stock-signals-board');assert.ok(h.find('[data-coverage="not_an_indicator"]'));assert.match(h.host.textContent,/not an indicator/);assert.equal(h.all('[data-presentation]').length,0);
});
test('risk and strength exact-source higher texts stay different in the real DOM adapter',()=>{
 const risk=harness('https://review.invalid/reference.html#risk-radar');risk.click(risk.find('[data-choice="interpretation_up"]'));assert.match(risk.find('[data-reading-text]').textContent,/not an exit signal/);
 const score=harness('https://review.invalid/reference.html#market-state-score');score.click(score.find('[data-choice="interpretation_up"]'));assert.match(score.find('[data-reading-text]').textContent,/supportive/);
});
test('quadrant has four combinations, one selected example and no current score',()=>{
 const h=harness('https://review.invalid/reference.html#regime-quadrant');assert.equal(h.all('[data-choice]').length,4);assert.equal(h.all('[aria-pressed="true"]').length,1);
 h.click(h.find('[data-choice="growth-up-inflation-up"]'));assert.equal(h.all('[aria-pressed="true"]').length,1);assert.match(h.context.location.href,/growth-up-inflation-up/);assert.match(h.host.textContent,/No cell here represents today/);
});
test('confirmation has no synthetic rising/falling buttons',()=>{
 const h=harness('https://review.invalid/reference.html#transition-state');assert.equal(h.all('[data-choice]').length,0);assert.match(h.host.textContent,/Confirmation, not direction/);
});
test('a generic non-directional definition is not mislabeled as regime confirmation',()=>{
 const data=fixture();data.entries[4].presentation.readings=data.entries[4].presentation.readings.slice(2);
 const h=harness('https://review.invalid/reference.html#evidence-matrix',data);assert.doesNotMatch(h.host.textContent,/Confirmation, not direction/);assert.match(h.host.textContent,/What the reading describes/);
});
test('sources are visible on demand and an absent source is explained',()=>{
 const h=harness('https://review.invalid/reference.html#market-state-score');assert.equal(h.find('[data-source]').getAttribute('href'),'https://fred.stlouisfed.org/series/VIXCLS');
 const missing=harness('https://review.invalid/reference.html#risk-radar');assert.match(missing.host.textContent,/No public source link/);
});
test('retired content retains original and links to current explanation',()=>{
 const data=fixture();data.entries[6].status='deprecated';data.entries[6].replacement_chain=['posture-dial'];
 const h=harness('https://review.invalid/reference.html#market-regime',data);assert.ok(h.find('[data-retired]'));assert.equal(h.find('h1').textContent,'Market Regime');assert.ok(h.find('[data-entry-link="posture-dial"]'));
});
test('uncovered board cannot masquerade as an empty successful signal',()=>{
 const data=fixture();data.coverage[2].state='not_covered';data.coverage[2].related_ids=[];
 const h=harness('https://review.invalid/reference.html#prophet-stock-signals-board',data);assert.match(h.host.textContent,/not available yet/);assert.ok(h.find('[data-coverage="not_covered"]'));
});
test('untrusted label and missing hash enter text nodes, not markup',()=>{
 const data=fixture();data.entries[0].label.en='<img src=x onerror=alert(1)>';
 const h=harness('https://review.invalid/reference.html#market-state-score',data);assert.equal(h.find('h1').textContent,data.entries[0].label.en);assert.equal(h.all('img').length,0);
 const unknown=harness('https://review.invalid/reference.html#%3Cscript%3E');assert.equal(unknown.find('[data-missing-name]').textContent,'<script>');
});
test('invalid data leaves the server-rendered fallback accessible',()=>{
 const data=fixture();data.live_values=true;const h=harness(undefined,data);assert.ok(h.app.error);assert.equal(h.doc.getElementById('fallback').hidden,false);assert.match(h.host.textContent,/still readable/);
});
test('full guide and quick help share the exact definition and limitation',()=>{
 const h=harness();const opener=h.find('[data-help="market-state-score"]');h.context.scrollY=123;h.click(opener);assert.equal(h.dialog.open,true);
 assert.match(h.dialog.textContent,/Definition for Market State Score/);assert.match(h.dialog.textContent,/Not a timing call/);
 h.click(h.dialog.querySelector('[data-choice="interpretation_up"]'));h.click(h.dialog.querySelector('[data-entry-link="market-state-score"]'));
 assert.equal(h.dialog.open,false);assert.match(h.context.location.href,/reading=interpretation_up/);assert.match(h.find('[data-reading-text]').textContent,/supportive/);
});
test('close adapter restores the exact trigger and recorded scroll; native browser behavior still unproven',()=>{
 const h=harness(),opener=h.find('[data-help="market-state-score"]');h.context.scrollY=321;h.click(opener);h.click(h.dialog.querySelector('[data-close]'));
 assert.equal(h.doc.activeElement,opener);assert.equal(h.context.scrollY,321);
});
test('language and theme toggles preserve chosen signal and interpretation',()=>{
 const h=harness('https://review.invalid/reference.html?reading=interpretation_up#risk-radar');h.click(h.doc.getElementById('language'));assert.equal(h.find('h1').textContent,'回撤风险雷达');assert.equal(h.doc.documentElement.lang,'zh-CN');
 h.click(h.doc.getElementById('theme'));assert.equal(h.doc.documentElement.dataset.theme,'dark');assert.match(h.context.location.href,/#risk-radar/);
});
test('duplicate query warning clears when the user chooses a clean navigation',()=>{
 const h=harness('https://review.invalid/reference.html?q=a&q=b#risk-radar');assert.ok(h.find('[data-route-warning]'));h.click(h.find('[data-home]'));assert.equal(h.find('[data-route-warning]'),null);
});
test('back-forward handler rehydrates query and language without extra requests',()=>{
 const h=harness();h.context.location.href='https://review.invalid/reference.html?q=Regime+Badge&lang=zh';h.fire('popstate');assert.equal(h.find('#search').value,'Regime Badge');assert.equal(h.all('article').length,1);assert.equal(h.doc.documentElement.lang,'zh-CN');
});
test('dispose removes owned listeners and restores the fallback',()=>{
 const h=harness();h.app.dispose();assert.equal(h.host.children.length,0);assert.equal(h.doc.getElementById('fallback').hidden,false);h.fire('popstate');assert.equal(h.host.children.length,0);
});

test('home does not instantiate a hidden full catalog before the user asks',()=>{
 const h=harness();assert.equal(h.all('article').length,0);h.click(h.find('[data-browse]'));assert.ok(h.all('article').length>0);
});
test('Enter opens an exact alias, not an arbitrary search result',()=>{
 const h=harness(),input=h.find('#search');input.value='Regime Badge';input.fire('input');input.fire('keydown',{key:'Enter'});assert.equal(h.find('h1').textContent,'Market Regime');
});
test('context-only mounting leaves the host title, URL, language and page controls alone',()=>{
 const url='https://review.invalid/macro.html?desk=us#regime-radar';const h=harness(url,fixture(),{mode:'context'});
 assert.equal(h.context.location.href,url);assert.equal(h.doc.title,'Macro dashboard');assert.equal(h.host.textContent,'');assert.equal(h.doc.documentElement.lang,'en');
 assert.equal(h.doc.getElementById('language').handlers.click,undefined);assert.equal(h.history.length,0);
});
test('context mode never mutates or clears its host container',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context',seedHost:{className:'macro-slot existing',text:'Preserve host content'}});
 assert.equal(h.host.getAttribute('class'),'macro-slot existing');assert.equal(h.host.textContent,'Preserve host content');
 h.app.openHelp('risk-radar',h.doc.getElementById('theme'));assert.equal(h.dialog.open,true);
 assert.equal(h.host.getAttribute('class'),'macro-slot existing');assert.equal(h.host.textContent,'Preserve host content');
 h.app.dispose();assert.equal(h.host.getAttribute('class'),'macro-slot existing');assert.equal(h.host.textContent,'Preserve host content');
});
test('context help surfaces a caller-supplied current reading without interpreting it',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});
 const opener=h.doc.getElementById('theme');
 opener.setAttribute('data-guide-current-en','56 / 100 · Caution');
 opener.setAttribute('data-guide-current-zh','56 / 100 · 谨慎');
 opener.setAttribute('data-guide-asof','2026-09-23');
 h.app.openHelp('risk-radar',opener);
 assert.equal(h.dialog.querySelector('[data-guide-current-value]').textContent,'56 / 100 · Caution');
 assert.equal(h.dialog.querySelector('[data-guide-current-asof]').textContent,'2026-09-23');
 h.doc.documentElement.setAttribute('data-lang','zh');h.doc.fire('langchange');
 assert.equal(h.dialog.querySelector('[data-guide-current-value]').textContent,'56 / 100 · 谨慎');
 assert.match(h.dialog.textContent,/当前读数/);
});
test('context help aligns its example with a caller-supplied interpretation state',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});
 const opener=h.doc.getElementById('theme');opener.setAttribute('data-guide-current-en','Risk 56 · Watch');opener.setAttribute('data-guide-reading','interpretation_down');
 h.app.openHelp('risk-radar',opener);
 assert.equal(h.dialog.querySelector('[data-choice="interpretation_down"]').getAttribute('aria-pressed'),'true');
 assert.equal(h.dialog.querySelector('[data-choice="interpretation_neutral"]').getAttribute('aria-pressed'),'false');
});
test('unknown caller interpretation cannot manufacture a selected guide state',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});const opener=h.doc.getElementById('theme');
 opener.setAttribute('data-guide-current-en','Risk 56');opener.setAttribute('data-guide-reading','guaranteed_buy');h.app.openHelp('risk-radar',opener);
 assert.equal(h.dialog.querySelector('[data-choice="interpretation_neutral"]').getAttribute('aria-pressed'),'true');
 assert.equal(h.dialog.all('[data-choice="guaranteed_buy"]').length,0);
});
test('current-reading text remains inert and is absent when the caller supplies none',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});
 const opener=h.doc.getElementById('theme');opener.setAttribute('data-guide-current-en','<img src=x onerror=alert(1)>');
 h.app.openHelp('risk-radar',opener);
 assert.equal(h.dialog.querySelector('[data-guide-current-value]').textContent,'<img src=x onerror=alert(1)>');
 assert.equal(h.dialog.all('img').length,0);h.dialog.close();
 const h2=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});h2.app.openHelp('risk-radar',h2.doc.getElementById('theme'));
 assert.equal(h2.dialog.querySelector('[data-guide-current]'),null);
});
test('context help reads the same source and links to the full guide without seizing navigation',()=>{
 const url='https://review.invalid/macro.html#regime-radar';const h=harness(url,fixture(),{mode:'context'});const opener=h.doc.getElementById('theme');
 h.app.openHelp('risk-radar',opener);assert.equal(h.dialog.open,true);assert.equal(h.dialog.querySelector('#help-title').textContent,'Risk Radar');
 assert.equal(h.dialog.querySelector('[data-entry-link="risk-radar"]').getAttribute('href'),'https://review.invalid/reference.html#risk-radar');
 assert.equal(h.context.location.href,url);assert.equal(h.doc.title,'Macro dashboard');h.dialog.close();assert.equal(h.doc.activeElement,opener);
});
test('context help follows existing language events without changing the document title',()=>{
 const h=harness('https://review.invalid/macro.html',fixture(),{mode:'context'});h.app.openHelp('market-state-score',h.doc.body);
 h.doc.documentElement.setAttribute('data-lang','zh');h.doc.fire('langchange');assert.equal(h.dialog.querySelector('#help-title').textContent,h.app.model.get('market-state-score').label.zh);
 assert.equal(h.doc.title,'Macro dashboard');assert.match(h.dialog.querySelector('[data-entry-link="market-state-score"]').getAttribute('href'),/lang=zh/);
});
test('context mode rejects unsafe full-guide destinations before binding controls',()=>{
 assert.throws(()=>harness('https://review.invalid/macro.html',fixture(),{mode:'context',guidePath:'//attacker.invalid/guide'}),/Unsafe/);
});

for(const [lang,heading] of [['en','Signals, terms & dashboard names'],['zh','指标、术语与看板名称']]){
 test(`topic to global search updates heading, membership and URL (${lang})`,()=>{
  const h=harness('https://review.invalid/reference.html'+(lang==='zh'?'?lang=zh':''));
  h.click(h.find('[data-topic="risk"]'));
  assert.equal(h.find('#results').querySelector('h3').textContent,h.app.model.questions.find(q=>q.id==='risk').label[lang]);
  const input=h.find('#search');input.value='Regime Badge';input.fire('input');
  assert.equal(h.find('#results').querySelector('h3').textContent,heading);
  assert.deepEqual(h.find('#result-list').all('[data-entry-link]').map(n=>n.getAttribute('data-entry-link')),['market-regime']);
  assert.match(h.find('#result-count').textContent,/1/);
  const url=new URL(h.context.location.href);assert.equal(url.searchParams.has('topic'),false);assert.equal(url.searchParams.get('q'),'Regime Badge');
  assert.equal(h.find('#search'),input); // Typing must not replace the focused input.
  h.click(h.find('[data-entry-link="market-regime"]'));h.click(h.find('[data-home]'));
  assert.equal(h.find('#results').querySelector('h3').textContent,heading);
  assert.equal(h.find('#search').value,'Regime Badge');
 });
}
