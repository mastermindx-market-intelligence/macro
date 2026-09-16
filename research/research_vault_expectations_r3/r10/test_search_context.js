'use strict';
// Research-only tests for selected retained client/renderer functions.
// No browser, network, auth service, market data or production files are used.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const mode = process.argv[2] || 'candidate';
const input = mode === 'baseline' ? 'baseline' : 'candidate';
const client = fs.readFileSync(path.join(root, input, mode === 'baseline' ? 'search_client_r9.js' : 'search_client_r10.js'), 'utf8');
const renderer = fs.readFileSync(path.join(root, input, mode === 'baseline' ? 'render_feed_r9.js' : 'render_feed_r10.js'), 'utf8');
const cases = [];
const tests = [];
function test(name, fn) { tests.push({name, fn}); }
function deferred() { let resolve, reject; const promise = new Promise((a,b) => {resolve=a; reject=b;}); return {promise, resolve, reject}; }
async function settle() { for (let i=0;i<18;i++) await Promise.resolve(); }
function make() {
  const timers = new Map(), requests = [], elements = new Map(); let tid=0, zh=false, user={id:'principal-a'};
  function element(id) {
    if (!elements.has(id)) elements.set(id, {value:'margin',innerHTML:'',textContent:'',classList:{toggle(){}},insertAdjacentHTML(where, html) {this.innerHTML=html+this.innerHTML;}});
    return elements.get(id);
  }
  const s = {
    FILT: {q:'',inst:'DeskA',side:'',theme:''}, LANE:'latest', SEARCH_HITS:null,
    CATALOG_GENERATED:'g1', CATALOG_REQ:1, CATALOG_SOURCE:'live', USER_TIER:'pro',
    ITEMS:[{id:'one',title:'margin research',inst:'DeskA',desk:'',points:[],tags:['growth'],tickers:[],side:'sell',top:true},
           {id:'two',title:'margin discussion',inst:'DeskB',desk:'',points:[],tags:['growth'],tickers:[],side:'buy',top:true}],
    TOTAL_COUNT:2, PAGE_SIZE:18, shownN:18, _feedSig:'', API:'',
    window:{MDXAuth:{user:()=>user}}, doc:{querySelector:()=>null}, $:element,
    DocState:{isSaved:()=>true}, T:(en,cn)=>zh?cn:en, esc:x=>String(x).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])),
    feedUnlocked:()=>s.USER_TIER==='pro', picksLocked:()=>s.USER_TIER!=='pro',
    previewItems:()=>s.ITEMS.slice(0,1), teaseCount:()=>3,
    cardHTML:x=>'CARD:'+x.id, moreButton:()=>'', picksUpgradePanel:()=>'<locked>',lockedTeaser:()=>'<locked>',
    emptyState:(a,b)=>a+'|'+b, renderActiveChips:()=>{},
    setTimeout:fn=>{timers.set(++tid,fn);return tid;},clearTimeout:id=>timers.delete(id),
    withAuth:()=>Promise.resolve({}),
    fetch:(url,opts)=>{const d=deferred();requests.push({url,opts,...d});return d.promise;},
    console
  };
  vm.createContext(s); vm.runInContext(client+'\n'+renderer,s,{timeout:1000});
  return {s, requests, timers, element, user:x=>{user=x;}, zh:x=>{zh=x;},
    async flush(){const jobs=[...timers.values()];timers.clear();for(const fn of jobs) fn();await settle();},
    async start(){s.onSearchInput();await this.flush();},
    async reply(body={available:true,items:[{id:'one'}]},status=200,index=requests.length-1){requests[index].resolve({ok:status>=200&&status<300,status,json:()=>Promise.resolve(body)});await settle();},
    async ready(){await this.start();await this.reply();}
  };
}

test('healthy response remains ready',async()=>{const h=make();await h.ready();assert.equal(h.s.SEARCH_STATUS,'ready');assert.match(h.element('feed').innerHTML,/CARD:one/);});
test('HTTP 200 JSON null resolves unavailable, not perpetual pending',async()=>{const h=make();await h.start();await h.reply(null);assert.equal(h.s.SEARCH_STATUS,'unavailable');});
test('HTTP 200 JSON null displays incomplete-search notice',async()=>{const h=make();await h.start();await h.reply(null);assert.match(h.element('feed').innerHTML,/temporarily unavailable/);});
test('clearing institution via existing render path resubmits',async()=>{const h=make();await h.ready();h.s.FILT.inst='';h.s.renderFeed();await h.flush();assert.equal(h.requests.length,2);assert.equal(h.requests[1].url.includes('institution='),false);});
for (const [name, change] of [
  ['theme',h=>{h.s.FILT.theme='growth';}],['side',h=>{h.s.FILT.side='sell';}],['lane',h=>{h.s.LANE='saved';}],
  ['catalog generation',h=>{h.s.CATALOG_GENERATED='g2';}],['catalog request generation',h=>{h.s.CATALOG_REQ++;}],
  ['same-tier principal',h=>{h.user({id:'principal-b'});}],['tier',h=>{h.s.USER_TIER='free';}]
]) test(name+' change follows existing render path into a new request',async()=>{const h=make();await h.ready();change(h);h.s.renderFeed();assert.equal(h.s.SEARCH_STATUS,'pending');await h.flush();assert.equal(h.requests.length,2);});
test('clear-query render cancels queued work and becomes idle',async()=>{const h=make();h.s.onSearchInput();h.s.FILT.q='';h.element('q').value='';h.s.renderFeed();assert.equal(h.s.SEARCH_STATUS,'idle');await h.flush();assert.equal(h.requests.length,0);});
test('ordinary repeated renders do not duplicate requests',async()=>{const h=make();await h.ready();for(let i=0;i<20;i++)h.s.renderFeed();await h.flush();assert.equal(h.requests.length,1);assert.equal(h.s.SEARCH_STATUS,'ready');});
test('burst facet changes coalesce to latest context',async()=>{const h=make();await h.ready();for(let i=0;i<12;i++){h.s.FILT.inst='Desk'+i;h.s.renderFeed();}await h.flush();assert.equal(h.requests.length,2);assert.match(h.requests[1].url,/institution=Desk11/);});
test('return to an earlier context cannot resurrect its pending reply',async()=>{const h=make();await h.start();h.s.FILT.inst='DeskB';h.s.renderFeed();await h.flush();h.s.FILT.inst='DeskA';h.s.renderFeed();await h.flush();assert.equal(h.requests.length,3);await h.reply({available:true,items:[{id:'two'}]},200,0);assert.equal(h.s.SEARCH_STATUS,'pending');await h.reply({available:true,items:[{id:'one'}]},200,2);assert.equal(h.s.SEARCH_STATUS,'ready');assert.match(h.element('feed').innerHTML,/CARD:one/);});
test('null stale response cannot erase a newer ready response',async()=>{const h=make();await h.start();h.element('q').value='discussion';h.s.onSearchInput();await h.flush();await h.reply({available:true,items:[{id:'two'}]},200,1);await h.reply(null,200,0);assert.equal(h.s.SEARCH_STATUS,'ready');assert.equal(h.s.SEARCH_HITS.two,1);});
test('different-query stale response remains ignored',async()=>{const h=make();await h.start();h.element('q').value='changed';h.s.onSearchInput();await h.flush();await h.reply({available:true,items:[]},200,1);await h.reply({available:true,items:[{id:'one'}]},200,0);assert.equal(Object.keys(h.s.SEARCH_HITS).length,0);});
test('synchronous auth helper failure becomes unavailable',async()=>{const h=make();h.s.withAuth=()=>{throw Error('fixture failure');};await h.start();assert.equal(h.s.SEARCH_STATUS,'unavailable');});
test('rejected auth helper becomes unavailable without a fetch',async()=>{const h=make();h.s.withAuth=()=>Promise.reject(Error('fixture'));await h.start();assert.equal(h.s.SEARCH_STATUS,'unavailable');assert.equal(h.requests.length,0);});
test('network rejection remains unavailable with labelled permitted fallback',async()=>{const h=make();await h.start();h.requests[0].reject(Error('fixture'));await settle();assert.equal(h.s.SEARCH_STATUS,'unavailable');assert.match(h.element('feed').innerHTML,/permitted catalog/);});
test('bad JSON rejects to unavailable',async()=>{const h=make();await h.start();h.requests[0].resolve({ok:true,status:200,json:()=>Promise.reject(Error('fixture'))});await settle();assert.equal(h.s.SEARCH_STATUS,'unavailable');});
test('explicit unavailable remains distinct from healthy empty',async()=>{const h=make();await h.start();await h.reply({available:false,items:[]});assert.equal(h.s.SEARCH_STATUS,'unavailable');assert.match(h.element('feed').innerHTML,/permitted catalog/);});
test('healthy empty does not widen from local text matches',async()=>{const h=make();await h.start();await h.reply({available:true,items:[]});assert.equal(h.s.SEARCH_STATUS,'ready');assert.doesNotMatch(h.element('feed').innerHTML,/CARD:/);assert.match(h.element('feed').innerHTML,/No reports match/);});
for (const status of [401,402,403]) test('denial '+status+' does not widen via local fallback',async()=>{const h=make();await h.start();await h.reply(null,status);assert.equal(h.s.SEARCH_STATUS,'denied');assert.doesNotMatch(h.element('feed').innerHTML,/CARD:/);assert.match(h.element('feed').innerHTML,/not authorized/);});
test('malformed ID with terminal newline is rejected',async()=>{const h=make();await h.start();await h.reply({available:true,items:[{id:'one\n'}]});assert.equal(h.s.SEARCH_STATUS,'unavailable');});
test('language-only rendering does not issue more requests',async()=>{const h=make();await h.start();await h.reply({available:false,items:[]});h.zh(true);h.s.renderFeed();await h.flush();assert.equal(h.requests.length,1);assert.match(h.element('feed').innerHTML,/全文搜索暂时不可用/);});
test('unavailable re-render does not auto-retry indefinitely',async()=>{const h=make();await h.start();await h.reply({available:false,items:[]});for(let i=0;i<30;i++)h.s.renderFeed();await h.flush();assert.equal(h.requests.length,1);});
test('source data is not modified by scope reconciliation',async()=>{const h=make();const before=JSON.stringify(h.s.ITEMS);await h.ready();h.s.FILT.inst='';h.s.renderFeed();await h.flush();assert.equal(JSON.stringify(h.s.ITEMS),before);});
test('only current response survives out-of-order same-query facets',async()=>{const h=make();await h.start();h.s.FILT.inst='DeskB';h.s.renderFeed();await h.flush();assert.equal(h.requests.length,2);await h.reply({available:true,items:[{id:'two'}]},200,1);await h.reply({available:true,items:[{id:'one'}]},200,0);assert.equal(h.s.SEARCH_HITS.two,1);assert.match(h.element('feed').innerHTML,/CARD:two/);});
(async()=>{
  for(const t of tests){try{await t.fn();cases.push({name:t.name,status:'PASS'});}catch(e){cases.push({name:t.name,status:'FAIL',error:String(e.message)});}}
  const result={executed_at_utc:new Date().toISOString(),node:process.version,mode,scope:'Selected byte-verified R9 client/renderer and R10 candidate with synthetic controlled timers/network/DOM/auth. No browser or production proof.',total:cases.length,passed:cases.filter(x=>x.status==='PASS').length,failed:cases.filter(x=>x.status==='FAIL').length,cases};
  console.log(JSON.stringify(result,null,2));process.exitCode=result.failed?1:0;
})();
