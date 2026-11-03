'use strict';
// Execute the production function, not a reimplementation. No packages or network.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const target = process.argv[2] || path.join(__dirname, '..', 'templates', 'rotation_events.js');
const src = fs.readFileSync(target, 'utf8');
const m = src.match(/\/\* EARLY_CONTEXT_FN_START \*\/([\s\S]*?)\/\* EARLY_CONTEXT_FN_END \*\//);
assert.ok(m, 'production function markers');
const escSource = "function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');}";
const make = (prefix) => vm.runInNewContext('(function(){' + prefix + m[1] + ';return earlyContextHtml;})()');
const fn = make(escSource), fnNoEsc = make('');
const DAY = 86400000, NOW = Date.parse('2026-10-22T20:00:00Z'), AS = '2026-10-22';
const day = ms => new Date(ms).toISOString().slice(0, 10);
function W(s, n, d, date=AS, extra={}) {
  return {...{eligible:true,sessions:s,start:day(Date.parse(date+'T00:00:00Z')-s*DAY),end:date,
    numerator_return_pct:n,denominator_return_pct:d,ratio_return_pct:((1+n/100)/(1+d/100)-1)*100,
    reason_codes:[],shape:'UNTRUSTED'},...extra};
}
function R(extra={}) {
  return {...{schema:'ratio_lens.short_horizon.v1',pair_id:'xlp_vs_xlk',context_group:'defensive_sector',num:'XLP',den:'XLK',
    name_en:'Staples / technology',name_zh:'必需消费 / 科技',requested_as_of:AS,value_as_of:AS,eligible_2s:true,
    interpretation:'UNTRUSTED',absolute_2s:{receiver_state:'DOWN',donor_state:'UP'},reason_codes:[],
    horizons:{'2s':W(2,2,-1),'5s':W(5,3,1),'20s':W(20,6,2)},lineage:{status:'COMPLETE',roots:['test']}},...extra};
}
function C(extra={}) {
  return {...{schema:'rotation_early_context/v1',definition_id:'rotation_early_context/1',display_only:true,as_of:AS,
    state:'DEFENSIVE_RELATIVE_STRENGTH',reason_codes:[],pairs:[R()],availability:{status:'UNKNOWN',available_at:null},
    lineage:{status:'UNKNOWN',roots:[],revisions:{},dependency_groups:['equity_price']}},...extra};
}
const render = (c=C(),lang='en',now=NOW) => fn({early_context:c},lang,now);
const has = (h,s) => assert.ok(h.includes(s),'missing '+s), not = (h,s) => assert.ok(!h.includes(s),'unexpected '+s);
const pairWindow = w => render(C({pairs:[R({horizons:{'2s':w,'5s':W(5,3,1),'20s':W(20,6,2)}})]}));
const T=[], test=(name,run)=>T.push([name,run]);
test('divergence: absolute legs and correct percent units',()=>{
  const h=render(); has(h,'Defensive leg rising; risk leg falling'); has(h,'+2.00%'); has(h,'-1.00%'); has(h,'+3.03%');
  not(h,'+200.00%'); has(h,'Forecast and sizing: not qualified'); has(h,'Price comparison, not measured fund flows');
});
test('both falling is only relative shelter',()=>{
  const h=pairWindow(W(2,-1,-3)); has(h,'Relative shelter only: both legs falling'); not(h,'Defensive leg rising');
});
test('both rising, flat and defensive weakness remain distinct',()=>{
  has(pairWindow(W(2,1,.5)),'Both legs rising'); has(pairWindow(W(2,0,0)),'Both legs flat');
  has(pairWindow(W(2,0,-1)),'Defensive leg flat'); has(pairWindow(W(2,1,0)),'Risk leg flat');
  has(pairWindow(W(2,-2,1)),'Defensive leg falling; risk leg rising');
});
test('missing packet is not quiet or an all-clear',()=>{
  const h=fn({},'en',NOW); has(h,'unavailable'); not(h,'No registered'); not(h,'no early shift');
});
test('empty is different from malformed pairs',()=>{
  has(render(C({pairs:[]})),'No registered defensive comparisons');
  has(render(C({pairs:undefined})),'PACKET_UNREADABLE'); has(render(C({pairs:[null]})),'PAIR_UNREADABLE');
});
test('unrecognized schema, definition and promoted authority fail closed',()=>{
  for(const bad of [{schema:'other'},{definition_id:'other'},{display_only:false},{display_only:undefined}]) has(render(C(bad)),'SCHEMA_UNRECOGNIZED');
});
test('invalid state cannot become a verdict',()=>{
  for(const state of ['BUY',1,false,{},undefined]) has(render(C({state})),'STATE_UNRECOGNIZED');
  has(render(C({state:null})),'no state recorded');
});
test('strict calendar dates reject JavaScript normalization',()=>{
  for(const as_of of ['2026-02-30','2026-04-31','2026-1-01','not-a-date']) has(render(C({as_of})),'AS_OF_UNREADABLE');
  has(pairWindow(W(2,2,-1,AS,{start:'2026-02-30'})),'WINDOW_START_UNREADABLE');
});
test('source dates in future fail against supplied display clock',()=>{
  has(render(C({as_of:'2026-10-23'})),'AS_OF_IN_FUTURE');
});
test('clock must be finite, nonnegative and a representable Date',()=>{
  for(const now of [NaN,Infinity,-1,'now',null,1e100]) has(fn({early_context:C()},'en',now),'CLOCK_UNUSABLE');
  has(fn({early_context:C()},'en',undefined),'CLOCK_UNUSABLE');
});
test('pure clock: no hidden Date.now and deterministic replays',()=>{
  not(m[1],'Date.now('); assert.equal(render(),render());
  has(render(C(),'en',NOW+20*DAY),'Historical/stale snapshot');
});
test('stale snapshot is prominent and historical values stay dated',()=>{
  const h=render(C(),'en',NOW+5*DAY); has(h,'Historical/stale snapshot — not a current signal'); has(h,AS); has(h,'+2.00%');
});
test('null bool strings and nonfinite numbers cannot become measured zero',()=>{
  for(const key of ['numerator_return_pct','denominator_return_pct','ratio_return_pct'])
    for(const bad of [null,true,false,'2',NaN,Infinity,-Infinity]) {
      const h=pairWindow(W(2,2,-1,AS,{[key]:bad})); has(h,'WINDOW_VALUE_NOT_A_FINITE_NUMBER'); not(h,'Defensive leg rising');
    }
});
test('absolute returns at or below minus one hundred fail',()=>{
  for(const key of ['numerator_return_pct','denominator_return_pct']) for(const bad of [-100,-101])
    has(pairWindow(W(2,2,-1,AS,{[key]:bad})),'WINDOW_ABSOLUTE_RETURN_AT_OR_BELOW_MINUS_100');
  has(pairWindow(W(2,-99.9,-1)),'-99.90%');
});
test('relative wealth must equal both absolute legs',()=>{
  has(pairWindow(W(2,2,-1,AS,{ratio_return_pct:99})),'WINDOW_RATIO_INCONSISTENT');
});
test('window eligibility count end and start are independently checked',()=>{
  for(const bad of [false,null,undefined,'true']) has(pairWindow(W(2,2,-1,AS,{eligible:bad})),'WINDOW_NOT_INDEPENDENTLY_ELIGIBLE');
  for(const bad of [3,'2',null]) has(pairWindow(W(2,2,-1,AS,{sessions:bad})),'WINDOW_SESSION_COUNT_MISMATCH');
  has(pairWindow(W(2,2,-1,AS,{end:'2026-10-21'})),'WINDOW_END_DATE_MISMATCH');
  has(pairWindow(W(2,2,-1,AS,{start:AS})),'WINDOW_START_UNREADABLE');
});
test('row eligibility is explicit true, never implicit',()=>{
  for(const bad of [undefined,null,'true',false]) has(render(C({pairs:[R({eligible_2s:bad})]})),'ROW_2S_NOT_ELIGIBLE');
});
test('row requested and value dates must match context',()=>{
  for(const key of ['requested_as_of','value_as_of']) has(render(C({pairs:[R({[key]:'2026-10-21'})]})),'ROW_DATE_MISMATCH');
});
test('context may be newer than legacy event date',()=>{
  const h=fn({as_of:'2026-10-01',early_context:C()},'en',NOW); has(h,'+2.00%'); not(h,'ROW_DATE_MISMATCH');
});
test('sign disagreement is visible but flat is not an opposite direction',()=>{
  const h=render(C({pairs:[R({horizons:{'2s':W(2,2,-1),'5s':W(5,3,1),'20s':W(20,-4,2)}})]})); has(h,'directions disagree');
  const flat=render(C({pairs:[R({horizons:{'2s':W(2,0,0),'20s':W(20,1,0)}})]})); not(flat,'directions disagree');
});
test('longer windows remain independently unavailable',()=>{
  const h=render(C({pairs:[R({horizons:{'2s':W(2,2,-1),'5s':W(5,3,1,AS,{eligible:false})}})]}));
  has(h,'Five-session — unavailable'); has(h,'Twenty-session comparison unavailable');
});
test('conflicting aliases abstain for both, including differing endpoints',()=>{
  for(const extra of [{horizons:{'2s':W(2,9,-9)}},{eligible_2s:undefined},{schema:'wrong'},
    {horizons:{...R().horizons,'2s':W(2,2,-1,AS,{end:'2026-10-21'})}}]) {
    const h=render(C({pairs:[R(),R({num:' xlp ',den:'xlk',...extra})]}));
    assert.equal(h.split('Abstained: duplicate alias').length-1,2); not(h,'+2.00%');
  }
});
test('identical aliases collapse without adding evidence',()=>{
  const h=render(C({pairs:[R(),R({pair_id:'alias',num:'xlp',den:' xlk '})]}));
  has(h,'Duplicate alias collapsed'); assert.equal(h.split('class="rc-ec-pair"').length-1,1);
});
test('pair identities have an unambiguous delimiter',()=>{
  const h=render(C({pairs:[R({num:'AB',den:'C'}),R({num:'A',den:'BC'})]}));
  has(h,'AB / C'); has(h,'A / BC'); not(h,'Duplicate alias'); not(h,'Abstained');
});
test('retailers and broadening are not sector confirmations',()=>{
  const h=render(C({pairs:[R({num:'WMT',context_group:'retailer_context'}),R({num:'DIA',context_group:'broadening_proxy'})]}));
  has(h,'No registered defensive comparisons'); not(h,'WMT'); not(h,'DIA');
});
test('row bound, whitespace and unknown schema abstain',()=>{
  has(render(C({pairs:Array.from({length:65},()=>R())})),'ROW_LIMIT_EXCEEDED');
  has(render(C({pairs:[R({num:'  '})]})),'ROW_PAIR_IDENTITY_MISSING');
  has(render(C({pairs:[R({schema:'other'})]})),'ROW_SCHEMA_UNRECOGNIZED');
});
test('all dynamic labels and reasons are escaped',()=>{
  const bad='</div><script>alert("1")</script>&';
  const h=render(C({reason_codes:[bad],pairs:[R({num:bad,name_en:bad,pair_id:bad,reason_codes:[bad]})]}));
  not(h,'<script>'); has(h,'&lt;script&gt;'); has(h,'&quot;'); has(h,'&amp;');
  assert.ok(!/\son[a-z]+\s*=\s*["']/.test(h));
});
test('unknown quality stays outside collapsed details',()=>{
  const h=render(); assert.ok(h.indexOf('Availability: UNKNOWN')<h.indexOf('<details')); has(h,'Lineage: UNKNOWN');
});
test('reason output is bounded',()=>{
  const h=render(C({reason_codes:Array.from({length:50},(_,i)=>'CODE_'+i)})); has(h,'CODE_9'); not(h,'CODE_10');
});
test('input is never mutated and shared escape helper is optional',()=>{
  const c=C(), before=JSON.stringify(c); render(c); render(c,'zh'); assert.equal(JSON.stringify(c),before);
  has(fnNoEsc({early_context:c},'en',NOW),'Early defensive rotation evidence');
});
test('Chinese means early observation, not early morning',()=>{
  const h=render(C(),'zh'); has(h,'早期防御性轮动证据'); not(h,'早盘'); has(h,'防御端上涨；风险端下跌');
});
test('real consumer is mounted and fed by existing fetch, including missing data',()=>{
  has(src,'border-radius:var(--r-card,12px)'); has(src,'border-radius:var(--r-ctl,8px)');
  has(src,'id="rc-early-context"'); has(src,"earlyContextHtml(res[0],isZh()?'zh':'en',Date.now())");
  assert.ok(src.indexOf('earlyContextHtml(res[0]')<src.indexOf('if(!res[0]&&!res[1])'));
  not(src,'No money-flow events right now'); not(src,'Nothing to do.'); not(src,'Money leaving ');
});
let failed=0;
for(const [name,run] of T) { try {run(); console.log('ok - '+name);} catch(e) {failed++; console.error('FAIL - '+name+' :: '+e.message);} }
console.log((T.length-failed)+'/'+T.length+' passed'); process.exitCode=failed?1:0;
