'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_MODULE || 'jsdom');
const root = path.resolve(__dirname, '..');
const source = process.env.ODDS_SOURCE || path.join(root, 'site/odds.js');
const code = fs.readFileSync(source, 'utf8');
const html = fs.readFileSync(process.env.ODDS_HTML, 'utf8');
const fixture = JSON.parse(fs.readFileSync(process.env.ODDS_FIXTURE));
const copy = x => JSON.parse(JSON.stringify(x));
const DAY = 86400000;
const epoch = date => Date.parse(date+'T00:00:00Z') / DAY;
const settle = async () => { for(let i=0;i<8;i++) await new Promise(resolve=>setImmediate(resolve)); };
function matrix(day='2026-10-14', ticker='SPY') {
  const m=copy(fixture.matrices.SPY), delta=epoch(day)-m.dates.at(-1);
  m.dates=m.dates.map(d=>d+delta); m.ticker=ticker; m.asof=day; return m;
}
function deferred() { let resolve, reject; const promise=new Promise((a,b)=>{resolve=a;reject=b;}); return {promise,resolve,reject}; }
async function page({catalog=copy(fixture.catalog), matrices=copy(fixture.matrices), ticker='SPY', now='2026-10-14T10:00:00Z', handler, setup}={}) {
  const calls=[], errors=[];
  const vc=new VirtualConsole(); vc.on('jsdomError', error=>errors.push(error.message));
  const dom=new JSDOM(html, {url:'https://fixture.invalid/odds.html?t='+encodeURIComponent(ticker),runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
  const w=dom.window;
  const NativeDate=w.Date;
  w.Date=class extends NativeDate {constructor(...args){super(...(args.length?args:[now]));}static now(){return new NativeDate(now).getTime();}};
  w.matchMedia=()=>({matches:true,addListener(){},removeListener(){}});
  w.fetch=async url=>{
    calls.push(String(url));
    let data;
    if(url==='oddsdata/catalog.json') data=catalog;
    else if(handler) data=await handler(String(url));
    else { const t=decodeURIComponent(String(url).match(/oddsmatrix\/(.*)\.json$/)?.[1]||''); data=matrices[t]||null; }
    return {ok:data!==null,json:async()=>data};
  };
  if (setup) setup(w);
  w.eval(code);
  await settle();
  const q=s=>w.document.querySelector(s);
  const select=async t=>{
    const input=q('#od-tk-input'); input.value=t; input.dispatchEvent(new w.Event('input',{bubbles:true}));
    const row=Array.from(q('#od-tk-sugg').querySelectorAll('.row')).find(r=>r.getAttribute('data-t')===t);
    assert.ok(row, 'requested ticker exists in actual typeahead'); row.dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true})); await settle();
  };
  return {dom,w,q,calls,errors,select,close:()=>w.close(),setNow:value=>{now=value;},badge:(lang='en')=>q('#od-asof-chip').querySelector('.l-'+lang)?.textContent||q('#od-asof-chip').textContent,warning:(lang='en')=>Array.from(q('#od-stale').querySelectorAll('.l-'+lang)).map(n=>n.textContent).join(' ')};
}
function fresh(p) { assert.equal(p.q('#od-stale').hidden,true, 'no stale warning for <=3 weekdays'); }
function stale(p, ticker, day) { assert.equal(p.q('#od-stale').hidden,false,'stale warning visible'); assert.match(p.warning(),new RegExp(ticker)); assert.match(p.warning(),new RegExp(day)); }
function observed(p,ticker,day){assert.match(p.badge(),new RegExp(ticker));assert.match(p.badge(),new RegExp(day));assert.match(p.badge('zh'),new RegExp(day));}

test('real producer: newest catalog date cannot conceal older selected ticker observations',async()=>{
  const p=await page({ticker:'OLD'});try{stale(p,'OLD','2026-10-01');observed(p,'OLD','2026-10-01');assert.match(p.warning('zh'),/历史/);assert.equal(p.q('#od-error').hidden,true);assert.equal(p.q('#od-app').hidden,false);assert.deepEqual(p.errors,[]);}finally{p.close();}
});
test('fresh selected observation is dated and leaves threshold warning hidden',async()=>{
 const p=await page();try{observed(p,'SPY','2026-10-14');fresh(p);assert.deepEqual(p.errors,[]);}finally{p.close();}
});
for(const meta of ['2026-10-14',null,'not-a-date','2027-01-01'])test('selected actual observation, not matrix asof metadata '+String(meta),async()=>{
 const m=copy(fixture.matrices.OLD);m.asof=meta;const p=await page({ticker:'OLD',matrices:{OLD:m}});try{stale(p,'OLD','2026-10-01');observed(p,'OLD','2026-10-01');}finally{p.close();}
});
test('stale-to-fresh selection clears prior ticker warning and updates date',async()=>{
 const p=await page({ticker:'OLD'});try{stale(p,'OLD','2026-10-01');await p.select('SPY');fresh(p);observed(p,'SPY','2026-10-14');assert.doesNotMatch(p.q('#od-stale').textContent,/OLD/);}finally{p.close();}
});
test('pending new ticker never carries the previous freshness badge',async()=>{
 const d=deferred();const p=await page({handler:url=>url.includes('OLD')?d.promise:fixture.matrices.SPY});try{await p.select('OLD');assert.match(p.badge(),/OLD.*loading/i);assert.doesNotMatch(p.badge(),/2026-10-14/);d.resolve(fixture.matrices.OLD);await settle();stale(p,'OLD','2026-10-01');}finally{p.close();}
});
test('failed new ticker clears prior freshness and selecting again recovers',async()=>{
 let attempts=0;const p=await page({ticker:'OLD',handler:url=>url.includes('SPY')?(++attempts===1?null:fixture.matrices.SPY):fixture.matrices.OLD});try{await p.select('SPY');assert.match(p.badge(),/SPY.*unavailable/i);assert.doesNotMatch(p.badge(),/2026-10/);assert.doesNotMatch(p.q('#od-stale').textContent,/OLD/);await p.select('SPY');observed(p,'SPY','2026-10-14');fresh(p);}finally{p.close();}
});
test('late stale A response cannot overwrite newer fresh B freshness',async()=>{
 const a=deferred();const p=await page({ticker:'OLD',handler:url=>url.includes('OLD')?a.promise:fixture.matrices.SPY});try{await p.select('SPY');a.resolve(fixture.matrices.OLD);await settle();observed(p,'SPY','2026-10-14');fresh(p);assert.match(p.q('#od-ident-tk').textContent,/SPY/);}finally{p.close();}
});
test('late fresh A response cannot erase newer stale B warning',async()=>{
 const a=deferred();const p=await page({handler:url=>url.includes('SPY')?a.promise:fixture.matrices.OLD});try{await p.select('OLD');a.resolve(fixture.matrices.SPY);await settle();observed(p,'OLD','2026-10-01');stale(p,'OLD','2026-10-01');}finally{p.close();}
});
test('fresh ticker does not erase stale catalog context warning',async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-01';const p=await page({catalog:cat});try{observed(p,'SPY','2026-10-14');stale(p,'Catalog','2026-10-01');assert.doesNotMatch(p.warning(),/SPY history.*stale/);}finally{p.close();}
});
for(const date of [undefined,null,'','invalid','2026-02-30','2026-10-15',false])test('catalog absent/invalid/future clock is explicitly unknown: '+String(date),async()=>{
 const cat=copy(fixture.catalog);if(date===undefined)delete cat.asof;else cat.asof=date;const p=await page({catalog:cat});try{assert.equal(p.q('#od-stale').hidden,false);assert.match(p.warning(),/Catalog.*date.*unavailable/i);assert.match(p.warning('zh'),/日期.*不可用/);observed(p,'SPY','2026-10-14');}finally{p.close();}
});
for(const date of [null,'2026-10-14',1.5,1e20,epoch('2026-10-15')])test('invalid/future selected epoch day never claims fresh: '+String(date),async()=>{
 const m=matrix();m.dates[m.dates.length-1]=date;const p=await page({matrices:{SPY:m}});try{assert.equal(p.q('#od-stale').hidden,false);assert.match(p.badge(),/SPY.*date.*unavailable/i);assert.match(p.warning(),/SPY.*date.*unavailable/i);}finally{p.close();}
});
test('epoch day zero remains an observed stale date',async()=>{
 const p=await page({matrices:{SPY:matrix('1970-01-01')}});try{observed(p,'SPY','1970-01-01');stale(p,'SPY','1970-01-01');}finally{p.close();}
});
for(const now of ['2026-10-14T00:00:00Z','2026-10-14T00:00:01Z','2026-10-14T23:59:59Z'])test('three-weekday threshold is stable for UTC date '+now,async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-09';const p=await page({catalog:cat,matrices:{SPY:matrix('2026-10-09')},now});try{fresh(p);observed(p,'SPY','2026-10-09');}finally{p.close();}
});
test('four weekdays preserves existing greater-than-three stale threshold',async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-08';const p=await page({catalog:cat,matrices:{SPY:matrix('2026-10-08')}});try{stale(p,'SPY','2026-10-08');assert.match(p.warning(),/Catalog/);}finally{p.close();}
});
test('weekend adds no weekday and leaves fresh receipt intact',async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-09';const p=await page({catalog:cat,matrices:{SPY:matrix('2026-10-09')},now:'2026-10-11T23:59:59Z'});try{fresh(p);observed(p,'SPY','2026-10-09');}finally{p.close();}
});
test('language and theme events preserve bilingual source warning and statistics',async()=>{
 const p=await page({ticker:'OLD'});try{const stats=p.q('#od-verdict').textContent;p.w.document.documentElement.setAttribute('data-lang','zh');p.w.document.dispatchEvent(new p.w.Event('langchange'));p.w.document.dispatchEvent(new p.w.Event('themechange'));await settle();stale(p,'OLD','2026-10-01');assert.match(p.badge('zh'),/OLD.*历史/);assert.equal(p.q('#od-verdict').textContent,stats);}finally{p.close();}
});
test('zero observations retain matching count, unchanged signed returns and original math',async()=>{
 const m=matrix();m.cols.fwd1_bp=m.dates.map((_,i)=>i===m.dates.length-1?null:0);const p=await page({matrices:{SPY:m}});try{assert.match(p.q('#od-verdict').textContent,/299 matching days/);assert.equal(p.q('#od-v-num').textContent,'0.0%');assert.match(p.q('#od-days-table').textContent,/0\.00%/);assert.equal(p.calls.length,2);}finally{p.close();}
});

test('returning to a visible tab rechecks current UTC age without fetching again',async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-09';const p=await page({catalog:cat,matrices:{SPY:matrix('2026-10-09')}});try{fresh(p);const calls=p.calls.length;p.setNow('2026-10-15T00:00:01Z');p.w.document.dispatchEvent(new p.w.Event('visibilitychange'));stale(p,'SPY','2026-10-09');assert.equal(p.calls.length,calls);}finally{p.close();}
});
test('returning during a pending selection preserves loading identity',async()=>{
 const d=deferred();const p=await page({handler:url=>url.includes('OLD')?d.promise:fixture.matrices.SPY});try{await p.select('OLD');p.w.document.dispatchEvent(new p.w.Event('visibilitychange'));assert.match(p.badge(),/OLD.*loading/i);assert.doesNotMatch(p.badge(),/2026-10-14/);d.resolve(fixture.matrices.OLD);await settle();stale(p,'OLD','2026-10-01');}finally{p.close();}
});
test('unknown wall clock cannot silently classify dates as fresh',async()=>{
 const p=await page({now:'not-a-date'});try{assert.equal(p.q('#od-stale').hidden,false);assert.match(p.warning(),/Catalog.*unavailable/);assert.match(p.badge(),/date unavailable/);}finally{p.close();}
});
for(const kind of ['network','shape'])test('failed selected '+kind+' load does not retain an old receipt',async()=>{
 const p=await page({handler:url=>url.includes('OLD')?(kind==='network'?Promise.reject(Error('synthetic network failure')):{schema:'wrong'}):fixture.matrices.SPY});try{await p.select('OLD');assert.match(p.badge(),/OLD.*unavailable/i);assert.doesNotMatch(p.badge(),/2026-10-14/);assert.equal(p.q('#od-error').hidden,true);assert.match(p.q('#od-verdict').textContent,/No odds history for OLD/);}finally{p.close();}
});
test('catalog and ticker source clocks are independent through stale-to-fresh recovery',async()=>{
 const cat=copy(fixture.catalog);cat.asof='2026-10-01';const p=await page({catalog:cat,ticker:'OLD'});try{stale(p,'OLD','2026-10-01');assert.match(p.warning(),/Catalog/);await p.select('SPY');observed(p,'SPY','2026-10-14');stale(p,'Catalog','2026-10-01');assert.doesNotMatch(p.warning(),/OLD/);}finally{p.close();}
});
test('retains original symbol fetch order and query-free endpoint policy',async()=>{
 const p=await page();try{await p.select('OLD');await p.select('SPY');assert.deepEqual(p.calls,['oddsdata/catalog.json','oddsmatrix/SPY.json','oddsmatrix/OLD.json','oddsmatrix/SPY.json']);assert.match(p.q('#od-ident-tk').textContent,/SPY/);assert.equal(p.q('#od-error').hidden,true);assert.deepEqual(p.errors,[]);}finally{p.close();}
});

// Exact untransformed production helper, isolated only to observe its integer
// count. Full-page cases above independently prove the helper's DOM consumers.
const vm = require('node:vm');
function elapsed(date, now) {
 const start=code.indexOf('  function bizDaysSince(isoDate) {');
 const end=code.indexOf('\n  function ',start+1);
 assert.ok(start>=0 && end>start);
 const NativeDate=Date;
 class Clock extends NativeDate {constructor(...args){super(...(args.length?args:[now]));}}
 return vm.runInNewContext('('+code.slice(start,end).trim()+')',{Date:Clock,isFinite})(date);
}
for(const [date,now,expected] of [
 ['2026-10-09','2026-10-12T00:00:00Z',1],
 ['2026-10-09','2026-10-12T12:00:00Z',1],
 ['2026-10-08','2026-10-13T12:00:00Z',3],
 ['2026-10-07','2026-10-13T12:00:00Z',4],
 ['2026-10-10','2026-10-12T12:00:00Z',1],
 ['2026-10-11','2026-10-12T12:00:00Z',1],
 ['2026-10-10','2026-10-11T12:00:00Z',0],
 ['2026-10-09','2026-10-13T01:00:00+14:00',1],
 ['2026-10-09','2026-10-12T23:30:00-11:00',2],
 ['2024-02-29','2024-03-05T23:59:59Z',3],
 ['2026-10-15','2026-10-14T23:59:59Z',null],
 ['2026-02-30','2026-10-14T23:59:59Z',null],
 [null,'2026-10-14T23:59:59Z',null],
 ['2026-10-14','2026-10-14T23:59:59Z',0],
])test('exact UTC weekday count '+String(date)+' to '+now,()=>assert.equal(elapsed(date,now),expected));

// Selection integrity: exercise real events while a new matrix is unresolved.
// Chart rendering remains the actual controller's SVG path. Optional setup is
// used only for ResizeObserver delivery and export side-effect interception.
const click=(p,sel)=>{const el=p.q(sel);assert.ok(el,sel);el.dispatchEvent(new p.w.MouseEvent('click',{bubbles:true,cancelable:true}));};
const tab=(p,name)=>click(p,'#od-tabs .tabbtn[data-tab="'+name+'"]');
const waitRepaint=()=>new Promise(resolve=>setTimeout(resolve,130));
function pending(p,ticker='OLD') {
 assert.ok(p.q('#od-verdict .od-skel-block'),'verdict remains loading, not old-matrix statistics');
 assert.equal(p.q('#od-ident-tk').textContent,ticker,'identity follows selected ticker');
 assert.equal(p.q('#od-ident-sub').textContent,'','old observation date is cleared');
 assert.equal(p.q('#od-move-chip').hidden,true,'old move is hidden');
 assert.match(p.q('#od-match-count').textContent,/loading/i,'pending is not zero matching days');
 assert.match(p.badge(),new RegExp(ticker+'.*loading'));
 for(const id of ['#od-price-chart','#od-path-chart','#od-hist-chart','#od-strip-chart','#od-days-table']) {
  assert.ok(p.q(id+' .od-skel-block'),id+' is a skeleton');
  assert.equal(p.q(id+' svg'),null,id+' contains no prior plot');
 }
 for(const id of ['#od-path-note','#od-ret-note'])assert.equal(p.q(id).textContent,'',id+' clears prior sample counts');
 assert.equal(p.q('#od-vol-strip').hidden,true);
}
test('initial unresolved history has a consistent selected identity and loading state',async()=>{
 const d=deferred();const p=await page({handler:()=>d.promise});
 try {pending(p,'SPY');click(p,'#od-ctl-horizon .od-opt[data-v="5d"]');tab(p,'path');pending(p,'SPY');
  d.resolve(fixture.matrices.SPY);await settle();assert.ok(p.q('#od-path-chart svg'));observed(p,'SPY','2026-10-14');
 }finally{p.close();}
});
for(const [control,value] of [['horizon','5d'],['range','5y'],['tol','1']])test('pending selection cannot repaint old matrix via '+control,async()=>{
 const d=deferred();const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY});
 try {await p.select('OLD');click(p,'#od-ctl-'+control+' .od-opt[data-v="'+value+'"]');await settle();
  // This was the reviewer's causal SPY -> OLD -> 5d reproduction.
  pending(p);assert.doesNotMatch(p.q('#od-verdict').textContent,/On Wed Oct 14, OLD/);
  d.resolve(fixture.matrices.OLD);await settle();
  assert.equal(p.q('#od-verdict .od-skel-block'),null);assert.match(p.q('#od-verdict').textContent,/On Thu Oct 1, OLD/);
  observed(p,'OLD','2026-10-01');assert.equal(p.q('#od-ctl-'+control+' .od-opt.on').dataset.v,value);
  if(control==='horizon')assert.match(p.q('#od-verdict').textContent,/next week/);
  if(control==='range')assert.match(p.q('#od-verdict').textContent,/5 years/);
  assert.deepEqual(p.errors,[]);
 }finally{p.close();}
});
for(const name of ['path','returns'])test('pending selection clears previously rendered '+name+' pane and notes',async()=>{
 const d=deferred();const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY});
 try {tab(p,name);await settle();const id=name==='path'?'#od-path-chart':'#od-hist-chart';
  assert.ok(p.q(id+' svg'),'positive control: previous data was rendered');
  assert.ok(p.q(name==='path'?'#od-path-note':'#od-ret-note').textContent);
  await p.select('OLD');pending(p);tab(p,'days');tab(p,name);await settle();pending(p);
  d.resolve(fixture.matrices.OLD);await settle();assert.ok(p.q(id+' svg'));assert.match(p.q('#od-verdict').textContent,/On Thu Oct 1, OLD/);
 }finally{p.close();}
});
test('pending selection survives theme, language, hash-tab and ResizeObserver redraws',async()=>{
 const d=deferred(),resize=[];const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY,
  setup:w=>{w.ResizeObserver=class {constructor(fn){resize.push(fn)}observe(){}};}});
 try {await p.select('OLD');
  for(const name of ['days','path','returns']) {p.w.location.hash='#'+name;p.w.dispatchEvent(new p.w.HashChangeEvent('hashchange'));
   p.w.document.dispatchEvent(new p.w.Event('themechange'));p.w.document.documentElement.setAttribute('data-lang','zh');
   p.w.document.dispatchEvent(new p.w.Event('langchange'));resize.forEach(fn=>fn());await waitRepaint();pending(p);}
  d.resolve(fixture.matrices.OLD);await settle();assert.ok(p.q('#od-hist-chart svg'));assert.deepEqual(p.errors,[]);
 }finally{p.close();}
});
test('pending selection disables matrix factors without losing retained preferences',async()=>{
 const cat=copy(fixture.catalog);cat.factors=[{id:'magnitude',label_en:'Move size',label_zh:'涨跌幅',buckets:{}}];cat.defaults.active=['magnitude'];
 const d=deferred();const p=await page({catalog:cat,handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY});
 try {assert.equal(p.q('.od-cond[data-f="magnitude"]').getAttribute('aria-checked'),'true');
  await p.select('OLD');const row=p.q('.od-cond[data-f="magnitude"]');assert.equal(row.querySelector('button.od-switch').disabled,true);
  assert.match(row.querySelector('.od-cond-val').textContent,/loading/i);click(p,'.od-cond[data-f="magnitude"]');pending(p);
  d.resolve(fixture.matrices.OLD);await settle();assert.equal(p.q('.od-cond[data-f="magnitude"]').getAttribute('aria-checked'),'true');
  assert.equal(p.q('.od-cond button.od-switch').disabled,false);assert.doesNotMatch(p.q('.od-cond-val').textContent,/loading/i);
 }finally{p.close();}
});
test('pending selection cannot export old history under the newly selected ticker',async()=>{
 const d=deferred(),downloads=[];let blobs=0;const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY,
  setup:w=>{w.URL.createObjectURL=()=>{blobs++;return 'blob:fixture';};w.URL.revokeObjectURL=()=>{};
   w.HTMLAnchorElement.prototype.click=function(){downloads.push(this.download);};}});
 try {click(p,'#od-csv');assert.deepEqual(downloads,['odds_SPY_1d_10y.csv']);
  await p.select('OLD');click(p,'#od-csv');assert.equal(blobs,1,'no pending export blob');assert.equal(downloads.length,1);
  d.resolve(fixture.matrices.OLD);await settle();click(p,'#od-csv');assert.deepEqual(downloads,['odds_SPY_1d_10y.csv','odds_OLD_1d_10y.csv']);
 }finally{p.close();}
});
for(const kind of ['network','shape'])test('pending '+kind+' failure clears skeletons and recovery uses latest controls',async()=>{
 const d=deferred();let attempts=0;const p=await page({handler:u=>u.includes('OLD')?(++attempts===1?d.promise:fixture.matrices.OLD):fixture.matrices.SPY});
 try {tab(p,'path');await settle();await p.select('OLD');click(p,'#od-ctl-horizon .od-opt[data-v="20d"]');
  if(kind==='network')d.reject(Error('synthetic outage'));else d.resolve({schema:'wrong'});await settle();
  assert.match(p.q('#od-verdict').textContent,/No odds history for OLD/);assert.equal(p.q('#od-verdict .od-skel-block'),null);
  assert.equal(p.q('#od-path-chart .od-skel-block'),null);assert.equal(p.q('#od-path-note').textContent,'');assert.match(p.badge(),/OLD.*unavailable/);
  tab(p,'returns');assert.equal(p.q('#od-hist-chart .od-skel-block'),null);assert.equal(p.q('#od-ret-note').textContent,'');
  await p.select('OLD');assert.match(p.q('#od-verdict').textContent,/On Thu Oct 1, OLD/);assert.match(p.q('#od-verdict').textContent,/next month/);
  assert.ok(p.q('#od-hist-chart svg'));assert.deepEqual(p.errors,[]);
 }finally{p.close();}
});
test('pending A to B to A request generations cannot restore superseded statistics',async()=>{
 const b=deferred(),a2=deferred();let aCalls=0;const p=await page({handler:u=>u.includes('OLD')?b.promise:(++aCalls===1?fixture.matrices.SPY:a2.promise)});
 try {await p.select('OLD');await p.select('SPY');click(p,'#od-ctl-horizon .od-opt[data-v="5d"]');
  b.resolve(fixture.matrices.OLD);await settle();pending(p,'SPY');
  a2.resolve(matrix('2026-10-13'));await settle();assert.match(p.q('#od-verdict').textContent,/On Tue Oct 13, SPY/);observed(p,'SPY','2026-10-13');
 }finally{p.close();}
});
test('Factor Match stays independently usable during selected history loading',async()=>{
 const d=deferred();const fm={schema:'odds_factor_match.v1',asof:'2026-10-14',min_n:10,market:{},
  templates:[{id:'market',label_en:'Market context',label_zh:'市场环境',factors:[]}],horizons:['1d'],
  rows:[{t:'SPY',name:'S&P fixture',sec:'Index',res:{market:{'1d':[100,.6,25]}}}]};
 const p=await page({handler:u=>u==='oddsdata/factor_match.json'?fm:u.includes('OLD')?d.promise:fixture.matrices.SPY});
 try {await p.select('OLD');tab(p,'fm');await settle();assert.ok(p.q('#od-fm-table tr[data-t="SPY"]'));assert.match(p.q('#od-fm-table').textContent,/60%/);
  assert.equal(p.q('#od-pane-fm').hidden,false);pending(p);assert.equal(p.calls.filter(u=>u==='oddsdata/factor_match.json').length,1);
  click(p,'#od-fm-table tr[data-t="SPY"]');await settle();assert.equal(p.q('#od-pane-days').hidden,false);observed(p,'SPY','2026-10-14');
  d.resolve(fixture.matrices.OLD);await settle();observed(p,'SPY','2026-10-14');assert.deepEqual(p.errors,[]);
 }finally{p.close();}
});

function shareEffects(w) {
 const downloads=[],images=[],painted=[],fallbacks=[];
 w.HTMLAnchorElement.prototype.click=function(){downloads.push({name:this.download,painted:painted.slice()});};
 const ctx=new Proxy({measureText:s=>({width:String(s).length*8}),fillText:s=>painted.push(String(s))},
  {get:(target,key)=>key in target?target[key]:(()=>{})});
 w.HTMLCanvasElement.prototype.getContext=()=>ctx;
 w.HTMLCanvasElement.prototype.toDataURL=()=> 'data:image/png;base64,AA==';
 w.Image=class {constructor(){images.push(this);}set src(v){this._src=v;}get src(){return this._src;}};
 const timer=w.setTimeout.bind(w);w.setTimeout=(fn,ms,...args)=>ms===1500?(fallbacks.push(fn),0):timer(fn,ms,...args);
 return {downloads,images,painted,fallbacks};
}
function originalShare(e) {
 assert.equal(e.downloads.length,1,'one click-time export completes');
 assert.equal(e.downloads[0].name,'odds_SPY_1d_2026-10-14.png','filename retains click-time ticker and horizon');
 assert.ok(e.downloads[0].painted.includes('SPY'),'card retains click-time ticker');
 assert.ok(!e.downloads[0].painted.includes('OLD'),'new selection cannot relabel captured statistics');
 assert.ok(e.downloads[0].painted.some(s=>s.includes('closed higher the next day')),'card retains click-time horizon');
 assert.ok(e.downloads[0].painted.some(s=>s.includes('Oct 14 2026')),'card retains click-time observation date');
}
test('pending selection clears the actual price chart summary and restores current counts',async()=>{
 const d=deferred();let created=0,destroyed=0;
 const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY,
  setup:w=>{w.MMChart={create:()=>{created++;return {destroy(){destroyed++;}};}};}});
 try {assert.match(p.q('#od-days-note').textContent,/closed higher/,'actual controller populated the note');
  const initial=p.q('#od-days-note').textContent;assert.equal(created,1);
  await p.select('OLD');assert.equal(p.q('#od-days-note').textContent,'');assert.equal(destroyed,1);
  click(p,'#od-ctl-horizon .od-opt[data-v="5d"]');assert.equal(p.q('#od-days-note').textContent,'');
  d.resolve(fixture.matrices.OLD);await settle();assert.match(p.q('#od-days-note').textContent,/5d forward/);
  assert.notEqual(p.q('#od-days-note').textContent,initial);assert.equal(created,2);
 }finally{p.close();}
});
for(const completion of ['onload','onerror','timeout'])test('in-flight Share keeps its click-time snapshot through pending selection and '+completion,async()=>{
 const d=deferred();let e;const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY,setup:w=>{e=shareEffects(w);}});
 try {click(p,'#od-share');assert.equal(e.images.length,1);assert.equal(e.downloads.length,0);
  await p.select('OLD');assert.match(p.badge(),/OLD.*loading/);
  click(p,'#od-ctl-horizon .od-opt[data-v="5d"]');p.setNow('2026-10-15T00:00:01Z');
  if(completion==='timeout')e.fallbacks[0]();else e.images[0][completion]();await settle();originalShare(e);
  e.images[0].onload();e.images[0].onerror();e.fallbacks[0]();assert.equal(e.downloads.length,1,'callbacks are idempotent');
  d.resolve(fixture.matrices.OLD);await settle();
 }finally{p.close();}
});
for(const result of ['success','failure'])test('in-flight Share keeps its click-time snapshot after new selected '+result,async()=>{
 let e;const p=await page({handler:u=>u.includes('OLD')?(result==='success'?fixture.matrices.OLD:null):fixture.matrices.SPY,setup:w=>{e=shareEffects(w);}});
 try {click(p,'#od-share');await p.select('OLD');e.images[0].onerror();await settle();originalShare(e);
  assert.match(p.badge(),result==='success'?/OLD.*2026-10-01/:/OLD.*unavailable/);
 }finally{p.close();}
});
test('in-flight Share keeps original history through same-ticker reload',async()=>{
 let e,calls=0;const p=await page({handler:()=>++calls===1?fixture.matrices.SPY:matrix('2026-10-13'),setup:w=>{e=shareEffects(w);}});
 try {click(p,'#od-share');await p.select('SPY');observed(p,'SPY','2026-10-13');e.images[0].onerror();await settle();originalShare(e);
 }finally{p.close();}
});
test('in-flight Share filename and rendered statistics retain the same horizon snapshot',async()=>{
 let e;const p=await page({setup:w=>{e=shareEffects(w);}});
 try {click(p,'#od-share');click(p,'#od-ctl-horizon .od-opt[data-v="5d"]');click(p,'#od-ctl-range .od-opt[data-v="5y"]');
  e.images[0].onerror();await settle();originalShare(e);assert.match(p.q('#od-verdict').textContent,/next week/);
  assert.ok(e.downloads[0].painted.some(s=>s.includes('10 years')),'share retains click-time range');
 }finally{p.close();}
});
test('in-flight Share keeps click-time language through later language and theme events',async()=>{
 let e;const p=await page({setup:w=>{e=shareEffects(w);}});
 try {click(p,'#od-share');p.w.document.documentElement.setAttribute('data-lang','zh');p.w.document.dispatchEvent(new p.w.Event('langchange'));
  p.w.document.dispatchEvent(new p.w.Event('themechange'));e.images[0].onerror();await settle();originalShare(e);
 }finally{p.close();}
});
test('detached old Share button cannot begin a new export during selected loading',async()=>{
 const d=deferred();let e;const p=await page({handler:u=>u.includes('OLD')?d.promise:fixture.matrices.SPY,setup:w=>{e=shareEffects(w);}});
 try {const old=p.q('#od-share');await p.select('OLD');old.dispatchEvent(new p.w.MouseEvent('click',{bubbles:true}));
  assert.equal(e.images.length,0);assert.equal(e.downloads.length,0);d.resolve(fixture.matrices.OLD);await settle();
  click(p,'#od-share');e.images[0].onerror();assert.equal(e.downloads[0].name,'odds_OLD_1d_2026-10-01.png');
  assert.ok(e.downloads[0].painted.includes('OLD'));
 }finally{p.close();}
});
