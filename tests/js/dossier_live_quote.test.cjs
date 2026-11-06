'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../site/assets/js/dossier-live-quote.js'), 'utf8');
const NOW = Date.parse('2026-10-23T13:29:59Z');
function packet(changes = {}) {
  return { ticker:'NVDA', price:100, prev_close:90, change_abs:10, change_pct:100/9,
    regular_session_date:'2026-10-22', session:'pre', freshness:'delayed',
    extended_quote:{price:99,currency:'USD',change_abs:-1,change_pct:-1,
      completed_regular_reference:{price:100,session_date:'2026-10-22'},
      print_session:'pre',market_session:'pre',freshness:'live',as_of_ms:NOW-1000.25,
      valid_until_ms:NOW+1000,...changes} };
}
class Node {
  constructor(bilingual = false) {
    this.text = ''; this.hidden = false; this.attrs = {}; this.classes = new Set(); this.children = {};
    if(bilingual) {this.children['.l-en'] = new Node();this.children['.l-zh'] = new Node();}
    this.classList = {toggle:(name,on)=>on ? this.classes.add(name) : this.classes.delete(name),
      remove:(...names)=>names.forEach(name=>this.classes.delete(name))};
  }
  get textContent(){return Object.values(this.children).map(n=>n.textContent).join('') || this.text;}
  set textContent(value){this.text=String(value);this.children={};}
  querySelector(selector){return this.children[selector] || null;}
  getAttribute(name){return this.attrs[name] ?? null;}
  setAttribute(name,value){this.attrs[name]=String(value);}
}
async function harness(payload = packet(), options = {}) {
  let now = NOW, sequence = 0, response = payload, failed = false, calls = 0;
  const timers = new Map(), nodes = {}, listeners = {};
  const names = ['chg','abs','pct','stamp','regular-label','extended','ext-values','ext-status','ext-session','ext-price','ext-abs','ext-pct','ext-reference','ext-age'];
  for(const name of names) nodes[name]=new Node(['stamp','regular-label','ext-status','ext-session','ext-reference','ext-age'].includes(name));
  const prices = [new Node(), new Node()]; prices.forEach(n=>n.setAttribute('data-dq-sym','NVDA'));
  const document = {hidden:false,querySelectorAll:()=>prices,
    querySelector:s=>nodes[s.slice(9,-1)] || null,
    addEventListener:(name,fn)=>listeners[name]=fn};
  // selector is [data-dq-...], whose value begins at offset9.
  const schedule=(fn,ms,repeat)=>{const id=++sequence;timers.set(id,{fn,ms,at:now+ms,repeat});return id;};
  class Clock extends Date {static now(){return now;}}
  const fetch = async()=>{calls++;if(failed) throw Error('offline fixture');
    if(options.hang) return new Promise(()=>{});
    return {ok:true,json:async()=>response};};
  const sandbox={document,Date:Clock,Promise,console,
    setTimeout:(fn,ms)=>schedule(fn,ms,false),clearTimeout:id=>timers.delete(id),
    setInterval:(fn,ms)=>schedule(fn,ms,true),clearInterval:id=>timers.delete(id),
    fetch,window:{fetch:options.noFetch ? undefined : fetch,Promise},
  };
  vm.runInNewContext(source,sandbox,{timeout:1000});
  const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
  await flush();
  return {nodes,prices,calls:()=>calls,
    en:name=>nodes[name].querySelector('.l-en')?.textContent,
    zh:name=>nodes[name].querySelector('.l-zh')?.textContent,
    setResponse:value=>{response=value;failed=false;},fail:()=>failed=true,
    async advance(ms){const end=now+ms;let count=0;
      while(true){let next=null;
        for(const [id,timer] of timers)if(timer.at<=end&&(!next||timer.at<next[1].at))next=[id,timer];
        if(!next)break;if(++count>1000)throw Error('timer loop');
        now=next[1].at;if(next[1].repeat)next[1].at+=next[1].ms;else timers.delete(next[0]);
        next[1].fn();await flush();
      }now=end;await flush();},
    async visibility(hidden){document.hidden=hidden;listeners.visibilitychange();await flush();},
    timers,now:()=>now};
}
test('regular and extended signs, completed reference, bilingual labels and price owners stay distinct',async()=>{
  const h=await harness();
  assert.deepEqual(h.prices.map(p=>p.textContent),['100.00','100.00']);
  assert.equal(h.nodes.abs.textContent,'+$10.00');
  assert.equal(h.nodes['ext-price'].textContent,'$99.00');
  assert.equal(h.nodes['ext-abs'].textContent,'-$1.00');assert.equal(h.nodes['ext-pct'].textContent,'-1.00%');
  assert.match(h.en('ext-reference'),/regular close \$100.00 · 2026-10-22/);
  assert.match(h.zh('ext-reference'),/常规时段收盘 \$100.00 · 2026-10-22/);
  assert.equal(h.en('ext-session'),'Pre-market');assert.equal(h.zh('ext-session'),'盘前');
  assert.match(h.en('ext-age'),/^Observed 1s ago$/);assert.match(h.zh('ext-age'),/1秒前/);
  assert.ok(h.nodes.extended.classes.has('neg'));assert.ok(h.nodes.chg.classes.has('pos'));
});
test('exact09:30 equality clears numbers even with a failed next fetch',async()=>{
  const h=await harness();h.fail();await h.advance(999);
  assert.equal(h.nodes['ext-price'].textContent,'$99.00');
  await h.advance(1);assert.equal(h.nodes['ext-price'].textContent,'');
  assert.equal(h.nodes['ext-values'].hidden,true);assert.match(h.en('ext-status'),/expired/);
  assert.equal(h.prices[0].textContent,'100.00');
});
test('repeated packet never resets its observation age or deadline',async()=>{
  const q=packet({valid_until_ms:NOW+118000});const h=await harness(q);
  await h.advance(15000);assert.match(h.en('ext-age'),/^Observed 16s ago$/);
  assert.ok(h.calls()>1);await h.advance(103000);
  assert.equal(h.nodes['ext-price'].textContent,'');
});
test('hidden-tab lifecycle clears elapsed quote on reveal before any new success',async()=>{
  const h=await harness();await h.visibility(true);await h.advance(1000);h.fail();
  await h.visibility(false);assert.equal(h.nodes['ext-price'].textContent,'');
  assert.equal(h.nodes['ext-values'].hidden,true);
});
test('network failure clears extended quote while regular values remain',async()=>{
  const h=await harness(packet({valid_until_ms:NOW+118000}));h.fail();await h.advance(15000);
  assert.equal(h.nodes['ext-price'].textContent,'');assert.equal(h.prices[0].textContent,'100.00');
  assert.equal(h.nodes['ext-values'].hidden,true);assert.match(h.zh('ext-status'),/暂不可用/);
});
test('invalid extended packets never disturb the valid regular view',async()=>{
  const invalid=[null,{price:0},{as_of_ms:NOW+1},{valid_until_ms:NOW},{valid_until_ms:NOW-1001},
    {valid_until_ms:NOW+999999},{freshness:'stale'},{market_session:'post'},
    {print_session:'regular'},{change_pct:1},{currency:'EUR'},
    {completed_regular_reference:{price:100,session_date:'2026-02-30'}}];
  for(const changes of invalid){const q=packet(changes);if(changes===null)q.extended_quote=null;
    const h=await harness(q);assert.equal(h.nodes['ext-price'].textContent,'');
    assert.equal(h.nodes['ext-values'].hidden,true);assert.equal(h.prices[0].textContent,'100.00');}
});
test('post-market and delayed reading retain named session and own age',async()=>{
  const h=await harness(packet({print_session:'post',market_session:'post',freshness:'delayed'}));
  assert.equal(h.en('ext-session'),'After hours');assert.equal(h.zh('ext-session'),'盘后');
  assert.match(h.en('ext-age'),/^Delayed · Observed 1s ago$/);
});
test('bilingual nodes survive clearing then recovering',async()=>{
  const h=await harness(packet({valid_until_ms:NOW+118000}));h.fail();await h.advance(15000);
  h.setResponse(packet({as_of_ms:NOW+14000,valid_until_ms:NOW+118000}));await h.advance(15000);
  assert.equal(h.zh('ext-session'),'盘前');assert.match(h.zh('ext-reference'),/2026-10-22/);
});
test('missing fetch cannot invent an extended quote',async()=>{
  const h=await harness(packet(),{noFetch:true});assert.equal(h.nodes['ext-price'].textContent,'');
  assert.equal(h.calls(),0);
});
