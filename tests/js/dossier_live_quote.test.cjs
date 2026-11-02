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
const LEDGER_KEY = 'dq:attempt-ledger:v1';   // must match the shipped module
async function harness(payload = packet(), options = {}) {
  let now = NOW, sequence = 0, response = payload, failed = false, calls = 0, releaseLate = null;
  const timers = new Map(), nodes = {}, listeners = {};
  const names = ['chg','abs','pct','stamp','regular-label','extended','ext-values','ext-status','ext-session','ext-price','ext-abs','ext-pct','ext-reference','ext-age'];
  for(const name of names) nodes[name]=new Node(['stamp','regular-label','ext-status','ext-session','ext-reference','ext-age'].includes(name));
  const prices = [new Node(), new Node()]; prices.forEach(n=>n.setAttribute('data-dq-sym', payload.ticker || 'NVDA'));
  const document = {hidden:false,querySelectorAll:()=>prices,
    querySelector:s=>nodes[s.slice(9,-1)] || null,
    addEventListener:(name,fn)=>listeners[name]=fn};
  // selector is [data-dq-...], whose value begins at offset9.
  const schedule=(fn,ms,repeat)=>{const id=++sequence;timers.set(id,{fn,ms,at:now+ms,repeat});return id;};
  class Clock extends Date {static now(){return now;}}
  // Per-tab sessionStorage stand-in, shared across harnesses via options.storage.
  const storageMap = options.storage || new Map();
  const storageFails = { get:false, set:false };
  const sessionStorage = {
    getItem:k=>{if(storageFails.get) throw Error('storage read denied fixture');
      return storageMap.has(String(k)) ? storageMap.get(String(k)) : null;},
    setItem:(k,v)=>{if(storageFails.set) throw Error('storage write denied fixture');
      storageMap.set(String(k),String(v));},
    removeItem:k=>{storageMap.delete(String(k));},
    clear:()=>{storageMap.clear();}
  };
  // Plain (non-async) function so a pre-origin sync throw is genuinely sync.
  const fetch = function(){
    if(options.beforeFetch) options.beforeFetch(sandbox.window.__dqAttemptLedger.snapshot(), calls);
    calls++;
    if(options.syncThrow) throw Error('pre-origin sync failure fixture');
    if(failed) return Promise.reject(Error('offline fixture'));
    if(options.hang) return new Promise(()=>{});
    if(options.defer) return new Promise(res=>{releaseLate=res;});
    if(options.httpError) return Promise.resolve({ok:false,json:async()=>({})});
    return Promise.resolve({ok:true,json:async()=>response});};
  const sandbox={document,Date:Clock,Promise,console,
    setTimeout:(fn,ms)=>schedule(fn,ms,false),clearTimeout:id=>timers.delete(id),
    setInterval:(fn,ms)=>schedule(fn,ms,true),clearInterval:id=>timers.delete(id),
    fetch,window:{fetch:options.noFetch ? undefined : fetch,
      Promise,sessionStorage:options.noStorage ? undefined : sessionStorage},
  };
  vm.runInNewContext(source,sandbox,{timeout:1000});
  const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
  await flush();
  return {nodes,prices,calls:()=>calls,
    en:name=>nodes[name].querySelector('.l-en')?.textContent,
    zh:name=>nodes[name].querySelector('.l-zh')?.textContent,
    setResponse:value=>{response=value;failed=false;},fail:()=>failed=true,
    snapshot:()=>sandbox.window.__dqAttemptLedger?.snapshot(),
    rerun:async()=>{vm.runInNewContext(source,sandbox,{timeout:1000});await flush();},
    storage:storageMap,raw:()=>storageMap.has(LEDGER_KEY)?storageMap.get(LEDGER_KEY):null,
    dropLedger:()=>storageMap.delete(LEDGER_KEY),
    storageFail:what=>{if(what==='get')storageFails.get=true;else storageFails.set=true;},
    storageOK:()=>{storageFails.get=false;storageFails.set=false;},
    resolveLate:value=>{const r=releaseLate;releaseLate=null;if(r)r({ok:true,json:async()=>value});},
    async advance(ms){const end=now+ms;let count=0;
      while(true){let next=null;
        for(const [id,timer] of timers)if(timer.at<=end&&(!next||timer.at<next[1].at))next=[id,timer];
        if(!next)break;if(++count>6000)throw Error('timer loop');
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
test('ledger survives reload and symbol change with the aggregate intact',async()=>{
  const storage=new Map();
  const h1=await harness(packet(),{storage});
  await h1.advance(15000);                                   // initial read + one tick
  const s1=h1.snapshot();
  assert.equal(s1.aggregate,2);assert.equal(s1.aggregate_known,true);
  assert.equal(s1.series.prior_evidence,false);assert.equal(s1.series.provenance,'new');
  assert.equal(s1.symbol,'NVDA');assert.equal(s1.writer.exclusive_proven,false);
  assert.equal(s1.mode,'observational');assert.equal(s1.authoritative,false);
  assert.equal(s1.enforcement,'none');
  const next=packet(); next.ticker='MSFT';                   // packet(changes) tunes the
  const h2=await harness(next,{storage});                    // extended quote; top level here
  const s2=h2.snapshot();
  assert.equal(s2.aggregate,3);       // restored 2 + this document's own first read
  assert.equal(s2.aggregate_known,true);
  assert.equal(s2.series.prior_evidence,true);assert.equal(s2.series.id,s1.series.id);
  assert.equal(s2.series.provenance,'restored');
  assert.equal(s2.symbol,'MSFT');
  assert.notEqual(s2.document,s1.document);                  // fresh document id per load
  await h2.advance(15000);
  const s3=h2.snapshot();
  assert.equal(s3.aggregate,4);
  assert.ok(s3.records.some(r=>r.symbol==='NVDA'));
  assert.ok(s3.records.some(r=>r.symbol==='MSFT'));
  assert.deepEqual({...s3.uncertainty},                      // a clean handoff is not concurrency
    {storage:false,parse:false,reset:false,loss:false,concurrent_writer:false});
  assert.equal(s3.degraded,null);
});
test('pre-origin sync throw, rejection and HTTP error each count exactly one attempt',async()=>{
  const sync=await harness(packet(),{syncThrow:true});
  await sync.advance(15000);
  const s=sync.snapshot();
  assert.equal(s.aggregate,2);
  assert.deepEqual([...s.records.map(r=>r.outcome)],['sync-error','sync-error']);
  assert.equal(sync.prices[0].textContent,'');               // and the quote stayed honest
  assert.deepEqual([...Object.keys(s.records[0])].sort(),['clock','document','outcome','seq','symbol']);
  const rej=await harness(packet(),{});rej.fail();await rej.advance(15000);
  const r=rej.snapshot();
  assert.equal(r.aggregate,2);
  // the initial read succeeded before fail(), the tick then rejects
  assert.deepEqual([...r.records.map(x=>x.outcome)],['response','reject']);
  const http=await harness(packet(),{httpError:true});
  await http.advance(15000);
  const hh=http.snapshot();
  assert.equal(hh.aggregate,2);
  assert.deepEqual([...hh.records.map(x=>x.outcome)],['http-error','http-error']);
  assert.equal(http.prices[0].textContent,'');
  for(const snap of [s,r,hh]) for(const rec of snap.records)
    assert.equal(JSON.stringify(rec).indexOf('$'),-1);       // no quote data in the ledger
});
test('timeout counts once and a late response never adds a second count',async()=>{
  const h=await harness(packet(),{defer:true});
  let s=h.snapshot();
  assert.equal(s.aggregate,1);
  assert.deepEqual([...s.records.map(r=>r.outcome)],['pending']); // counted before the request exists
  await h.advance(6000);                                     // the watchdog fires
  s=h.snapshot();
  assert.equal(s.aggregate,1);
  assert.deepEqual([...s.records.map(r=>r.outcome)],['timeout']);
  assert.equal(h.calls(),1);
  h.resolveLate(packet());                                   // the response straggles in
  await h.advance(9000);                                     // crosses the next 15s tick
  s=h.snapshot();
  assert.equal(s.aggregate,2);                               // exactly one NEW attempt
  assert.deepEqual([...s.records.map(r=>r.outcome)],['timeout','pending']);
  assert.equal(h.calls(),2);                                 // unsettled is shown, not guessed
  h.resolveLate(packet());                                   // now settle the tick's response
  await h.advance(0);
  s=h.snapshot();
  assert.deepEqual([...s.records.map(r=>r.outcome)],['timeout','response']);
  assert.equal(h.prices[0].textContent,'100.00');            // and the paint still landed
});
test('hidden tabs and overlapped ticks are never counted',async()=>{
  const h=await harness(packet());
  await h.visibility(true);
  await h.advance(45000);                                    // three missed ticks, none counted
  assert.equal(h.snapshot().aggregate,1);
  assert.equal(h.calls(),1);
  await h.visibility(false);
  await h.advance(1);                                        // the reveal's immediate read
  assert.equal(h.snapshot().aggregate,2);
  assert.equal(h.snapshot().records.at(-1).outcome,'response');
});
test('storage failure is sticky degradation that never stops the quote',async()=>{
  const h=await harness(packet());
  const durable=h.raw();                                     // what load persisted
  h.storageFail('set');
  await h.advance(15000);
  const s=h.snapshot();
  assert.equal(s.aggregate,2);                               // counted in memory regardless
  assert.equal(s.aggregate_known,true);                      // the live count stays ours to know
  assert.equal(s.uncertainty.storage,true);
  assert.deepEqual([...s.degraded.reasons],['storage']);
  assert.equal(h.prices[0].textContent,'100.00');            // quoting unaffected
  assert.equal(h.raw(),durable);                             // and nothing was pretended durable
  h.storageOK();
  await h.advance(15000);
  const s2=h.snapshot();
  assert.equal(s2.aggregate,3);
  assert.equal(s2.uncertainty.storage,true);                 // sticky within the document
  const h2=await harness(packet(),{storage:h.storage});      // and sticky across a reload
  const s3=h2.snapshot();
  assert.equal(s3.aggregate,4);
  assert.equal(s3.uncertainty.storage,true);
  assert.ok(s3.degraded.reasons.includes('storage'));
});
test('corrupt storage is parse-degraded and never claims a healthy zero',async()=>{
  const storage=new Map();
  const h1=await harness(packet(),{storage});
  await h1.advance(15000);
  assert.equal(h1.snapshot().aggregate,2);
  storage.set(LEDGER_KEY,'{"v":1,not json');
  const h2=await harness(packet(),{storage});
  const s=h2.snapshot();
  assert.equal(s.uncertainty.parse,true);
  assert.deepEqual([...s.degraded.reasons],['parse']);
  assert.equal(s.aggregate_known,false);                     // prior total UNKNOWN, not zero
  assert.equal(s.series.prior_evidence,false);
  assert.equal(s.series.provenance,'unreadable');
  await h2.advance(15000);
  const s2=h2.snapshot();
  assert.equal(s2.aggregate,2);                              // climbs from the corruption boundary
  assert.equal(s2.aggregate_known,false);                    // without ever claiming the past
  assert.equal(s2.uncertainty.parse,true);                   // sticky across attempts
  const h3=await harness(packet(),{storage});                // and across another reload
  assert.equal(h3.snapshot().uncertainty.parse,true);
  assert.deepEqual([...h3.snapshot().degraded.reasons],['parse']);
});
test('mid-life deletion is a sticky reset; a fresh tab never claims prior completeness',async()=>{
  const storage=new Map();
  const h1=await harness(packet(),{storage});
  await h1.advance(15000);                                   // aggregate 2, durably written
  h1.dropLedger();                                           // evidence destroyed underneath us
  await h1.advance(15000);
  const s=h1.snapshot();
  assert.equal(s.uncertainty.reset,true);
  assert.deepEqual([...s.degraded.reasons],['reset']);
  assert.equal(s.aggregate_known,false);                     // the vanished portion is unknown
  assert.equal(s.aggregate,3);                               // ours, monotonic, still climbing
  const fresh=new Map();
  const h2=await harness(packet(),{storage:fresh});
  const s2=h2.snapshot();
  assert.equal(s2.series.prior_evidence,false);
  assert.equal(s2.series.provenance,'new');
  assert.equal(s2.aggregate_known,true);
  assert.equal(s2.aggregate,1);
  assert.equal(s2.writer.exclusive_proven,false);            // still no completeness claim
});
test('a rolled-back counter is detected and never rewinds',async()=>{
  const h=await harness(packet());
  await h.advance(15000);                                    // aggregate 2
  const old=h.raw();                                         // a stale copy of the ledger
  await h.advance(15000);                                    // aggregate 3
  h.storage.set(LEDGER_KEY,old);                             // someone restores the old copy
  await h.advance(15000);
  const s=h.snapshot();
  assert.equal(s.uncertainty.reset,true);                    // rollback surfaced under reset
  assert.deepEqual([...s.degraded.reasons],['rollback']);
  assert.equal(s.aggregate,4);                               // ours, monotonic, never rewound
});
test('duplicate script execution counts conservatively and flags the loss',async()=>{
  const h=await harness(packet());
  await h.rerun();                                           // same document runs it again
  await h.advance(15000);
  const s=h.snapshot();
  assert.equal(s.aggregate,2);                               // two pollers fetched; one counted
  assert.ok(h.calls()>=4);                                   // both really ran
  assert.equal(s.uncertainty.loss,true);                     // and the ledger says so
  assert.equal(s.uncertainty.concurrent_writer,true);
  assert.equal(s.writer.exclusive_proven,false);
});
test('two live writers in one storage scope fail completeness closed',async()=>{
  const storage=new Map();
  const a=await harness(packet(),{storage});
  const b=await harness(packet(),{storage});                 // a frame writing alongside
  await a.advance(15000);
  const s=a.snapshot();
  assert.equal(s.uncertainty.concurrent_writer,true);
  assert.ok(s.degraded.reasons.includes('concurrent_writer'));
  assert.equal(s.writer.exclusive_proven,false);
  assert.ok(s.aggregate>=3);                                 // nobody's increment was dropped
  const sb=b.snapshot();
  assert.ok(sb.aggregate>=s.aggregate-1);
});
test('history keeps 64 records and the total stays exact past 64',async()=>{
  const storage=new Map();
  const h=await harness(packet(),{storage});
  await h.advance(70*15000);                                 // initial + 70 ticks
  const s=h.snapshot();
  assert.equal(s.aggregate,71);
  assert.equal(s.records.length,64);
  assert.equal(s.history_truncated,true);
  assert.equal(s.history_limit,64);
  assert.deepEqual([...s.records.map(r=>r.seq)],Array.from({length:64},(_,i)=>i+8));
  const h2=await harness(packet(),{storage});                // survives a reload
  const s2=h2.snapshot();
  assert.equal(s2.aggregate,72);
  assert.equal(s2.records.length,64);
  assert.equal(s2.history_truncated,true);
});
test('a denied read is never misreported as a reset',async()=>{
  const h=await harness(packet());
  await h.advance(15000);                                    // aggregate 2, durably written
  const durable=h.raw();
  h.storageFail('get');                                      // reads denied, data still there
  await h.advance(15000);
  const s=h.snapshot();
  assert.equal(s.uncertainty.storage,true);
  assert.equal(s.uncertainty.reset,false);                   // denial is not deletion
  assert.deepEqual([...s.degraded.reasons],['storage']);
  assert.equal(s.aggregate,3);                               // monotonic, no fabricated rollback
  h.storageOK();
  await h.advance(15000);
  const s2=h.snapshot();
  assert.equal(s2.uncertainty.reset,false);
  assert.equal(s2.uncertainty.parse,false);                  // and the durable data survived intact
  assert.equal(JSON.parse(h.raw()).aggregate,s2.aggregate);
  assert.notEqual(h.raw(),durable);
});
test('no sessionStorage at all degrades honestly and still quotes',async()=>{
  const h=await harness(packet(),{noStorage:true});
  const s=h.snapshot();
  assert.equal(s.uncertainty.storage,true);
  assert.equal(s.aggregate_known,false);                     // nothing readable: prior unknown
  assert.equal(s.series.provenance,'unstored');
  assert.equal(s.aggregate,1);                               // this document's own attempt still counts
  assert.equal(h.prices[0].textContent,'100.00');            // quoting unaffected
  await h.advance(15000);
  assert.equal(h.snapshot().aggregate,2);
});
test('snapshots are frozen deep copies that cannot touch the ledger',async()=>{
  const h=await harness(packet());
  await h.advance(15000);
  const s=h.snapshot();
  // the thrown TypeError is the vm realm's, so match the message, not the class
  assert.throws(()=>{s.aggregate=999;},/Cannot assign to read only property/);
  assert.throws(()=>{s.records.push({seq:999});},/not extensible/);
  assert.throws(()=>{s.records[0].outcome='forged';},/Cannot assign to read only property/);
  assert.throws(()=>{s.uncertainty.storage=true;},/Cannot assign to read only property/);
  const t=h.snapshot();
  assert.equal(t.aggregate,s.aggregate);
  assert.equal(t.records.length,s.records.length);
  assert.equal(t.uncertainty.storage,false);
  assert.equal(t.records[0].outcome,'response');
  assert.equal(Object.isFrozen(t),true);
  assert.equal(Object.isFrozen(t.records),true);
  assert.equal(Object.isFrozen(t.records[0]),true);
  assert.equal(Object.isFrozen(t.uncertainty),true);
  assert.equal(t.schema,'dq-attempt-ledger/1');
  assert.equal(typeof t.document,'string');
  assert.equal(typeof t.clock,'number');
  assert.deepEqual([...Object.keys(t)].sort(),['aggregate','aggregate_known','authoritative','clock',
    'degraded','document','enforcement','history_limit','history_truncated','mode','prior_history_complete','records',
    'schema','series','symbol','uncertainty','writer']);
});

test('DOM accounting is the last bounded event snapshot and does not add a request',async()=>{
  const h=await harness(packet());
  const dom=JSON.parse(h.nodes.stamp.getAttribute('data-dq-accounting'));
  assert.equal(dom.aggregate,1); assert.equal(h.calls(),1);
  assert.equal(dom.records[0].document,dom.document);
  assert.equal(dom.prior_history_complete,false);
  assert.equal(dom.authoritative,false); assert.equal(dom.enforcement,'none');
  assert.equal(dom.records[0].outcome,'response');
});
test('malformed structured and oversized storage cannot masquerade as valid history',async()=>{
  const seed=await harness(packet());
  for(const mutate of [
    x=>{x.aggregate=1.5;}, x=>{x.records[0].symbol='SECRET '.repeat(100);},
    x=>{x.records[0].outcome='fabricated';}, x=>{x.records=Array(65).fill(x.records[0]);},
    x=>{x.degraded={reasons:['unknown'],at_clock:NOW};}, x=>{x.seq=Number.MAX_SAFE_INTEGER;}
  ]) {
    const data=JSON.parse(seed.raw());mutate(data);
    const h=await harness(packet(),{storage:new Map([[LEDGER_KEY,JSON.stringify(data)]])});
    assert.equal(h.snapshot().uncertainty.parse,true);
    assert.equal(h.snapshot().aggregate_known,false);
    assert.equal(h.prices[0].textContent,'100.00');
  }
  const h=await harness(packet(),{storage:new Map([[LEDGER_KEY,' '.repeat(32769)]])});
  assert.equal(h.snapshot().uncertainty.parse,true);
  assert.equal(h.calls(),1);
});
test('duplicate script is visible in the original snapshot immediately',async()=>{
  const h=await harness(packet());await h.rerun();
  assert.equal(h.snapshot().uncertainty.loss,true);
  assert.equal(h.snapshot().aggregate_known,false);
});

test('each invocation sees its already-recorded pending attempt before fetch can fail',async()=>{
  const seen=[];
  const h=await harness(packet(),{syncThrow:true,beforeFetch:(s,calls)=>{
    assert.equal(s.aggregate,calls+1);
    assert.equal(s.records.at(-1).outcome,'pending');
    assert.equal(s.records.at(-1).document,s.document);
    seen.push(s.records.at(-1).seq);
  }});
  await h.advance(30000);
  assert.deepEqual(seen,[1,2,3]); assert.equal(h.calls(),3);
});
