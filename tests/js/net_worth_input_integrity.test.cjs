'use strict';
// Execute the complete shipped controller with explicit DOM/clipboard doubles.
// This is source behavior, not visual, browser-permission or production proof.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = process.env.NET_WORTH_SOURCE || path.resolve(__dirname, '../../templates/calculators/net_worth.html.j2');
const source = fs.readFileSync(sourcePath, 'utf8');
const controller = [...source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
  .map(m => m[1]).find(s => s.includes('net-worth self-check'));
assert.ok(controller, 'the actual complete Net Worth controller is present');
const FIELDS = ['cash','invest','retire','realestate','vehicles','otherassets','mortgage','loans','creditcard','otherdebts'];
const OUTPUTS = ['out-main','out-assets','out-liab','out-dta'];
function boot(lang = 'en') {
  const callbacks = {}, nodes = {}, writes = [], errors = [];
  function element() {
    const attrs = {}, classes = new Set(), listeners = {};
    return {value:'', textContent:'', className:'',
      classList:{add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c)},
      setAttribute:(k,v)=>{attrs[k]=String(v);}, getAttribute:k=>attrs[k] ?? null,
      removeAttribute:k=>{delete attrs[k];}, hasAttribute:k=>Object.hasOwn(attrs,k),
      addEventListener:(k,fn)=>{(listeners[k] ||= []).push(fn);},
      dispatch:k=>{for(const fn of listeners[k] || []) fn();}
    };
  }
  // Only materialize description nodes that exist in the real template/page markup.
  const errorIds = [...source.matchAll(/\bid="([^"]+-error)"/g)].map(m=>m[1]);
  assert.equal(new Set(errorIds).size, errorIds.length, 'error-description ids must be unique');
  for(const id of [...FIELDS,...OUTPUTS,'out-plain','copy-result','copied',...errorIds]) nodes[id]=element();
  const attrs={'data-lang':lang};
  const document = {getElementById:id=>nodes[id],
    documentElement:{getAttribute:k=>attrs[k] ?? null},
    addEventListener:(k,fn)=>{(callbacks[k] ||= []).push(fn);},
    createElement:()=>element(), body:{appendChild(){},removeChild(){}}};
  const navigator={clipboard:{writeText:line=>{writes.push(line);return Promise.resolve();}}};
  vm.runInNewContext(controller,{document,navigator,console:{error:(...a)=>errors.push(a)},setTimeout:()=>0,clearTimeout(){}});
  for(const fn of callbacks.DOMContentLoaded || []) fn();
  assert.deepEqual(errors, [], 'the actual built-in numerical fixtures stay green');
  return {nodes,writes,document,navigator,
    input:(id,value)=>{nodes[id].value=value;nodes[id].dispatch('input');},
    language:value=>{attrs['data-lang']=value;for(const fn of callbacks.langchange || []) fn();},
    copy:()=>nodes['copy-result'].dispatch('click')};
}
function withheld(b) {
  for(const id of OUTPUTS) assert.equal(b.nodes[id].textContent,'—',id+' must not assert an incomplete balance');
}
for(const id of FIELDS) for(const token of ['n/a','?','Infinity','1e999']) {
  test(id+' rejects nonblank invalid '+token+' and recovers without reload',()=>{
    const b=boot(); b.input('cash','10,000'); b.input('mortgage','20,000');
    assert.equal(b.nodes['out-main'].textContent,'−$10,000');
    b.input(id,token); withheld(b);
    assert.equal(b.nodes[id].getAttribute('aria-invalid'),'true');
    assert.match(errorDescription(b,id), /valid amount/i);
    assert.match(b.nodes['out-plain'].textContent,/correct|valid amount/i);
    const before=b.writes.length; b.copy(); assert.equal(b.writes.length,before,'invalid result cannot be copied');
    b.input(id,'0');
    assert.notEqual(b.nodes['out-main'].textContent,'—','explicit zero recovers the current balance');
    assert.equal(b.nodes[id].getAttribute('aria-invalid'),null);
    assert.equal(b.nodes[id].getAttribute('aria-describedby'),null);
  });
}
test('invalid debt can never become the reassuring zero-debt interpretation',()=>{
  const b=boot(); b.input('cash','10,000'); b.input('mortgage','n/a'); withheld(b);
  assert.doesNotMatch(b.nodes['out-plain'].textContent,/You own|0.0%|financed by debt/);
});
test('blank, whitespace and explicit zero retain optional-field semantics',()=>{
  const b=boot(); withheld(b);
  b.input('cash','  '); withheld(b); assert.equal(b.nodes.cash.getAttribute('aria-invalid'),null);
  b.input('cash','0'); assert.equal(b.nodes['out-main'].textContent,'$0');
  b.input('mortgage','10'); assert.equal(b.nodes['out-main'].textContent,'−$10');
  b.input('cash','10'); assert.equal(b.nodes['out-main'].textContent,'$0');
});
test('canonical worked household remains assets 700k, liabilities 360k, net 340k',()=>{
  const b=boot(); const values=['25,000','80,000','120,000','450,000','20,000','5,000','320,000','30,000','6,000','4,000'];
  FIELDS.forEach((id,i)=>b.input(id,values[i]));
  assert.equal(b.nodes['out-assets'].textContent,'$700,000');
  assert.equal(b.nodes['out-liab'].textContent,'$360,000');
  assert.equal(b.nodes['out-main'].textContent,'$340,000');
  assert.equal(b.nodes['out-dta'].textContent,'51.4%');
});
test('all invalid fields are marked, correction preserves the remaining error',()=>{
  const b=boot(); FIELDS.forEach(id=>b.input(id,'?'));
  FIELDS.forEach(id=>assert.equal(b.nodes[id].getAttribute('aria-invalid'),'true',id));
  b.input('cash','0'); withheld(b);
  assert.equal(b.nodes.cash.getAttribute('aria-invalid'),null);
  assert.equal(b.nodes.invest.getAttribute('aria-invalid'),'true');
});
test('invalid recovery is field-specific and follows EN/ZH without losing inputs',()=>{
  const b=boot(); b.input('cash','10,000'); b.input('mortgage','n/a');
  assert.match(b.nodes['out-plain'].textContent,/Mortgage/);
  b.language('zh'); withheld(b);
  assert.match(b.nodes['out-plain'].textContent,/房贷/);
  assert.doesNotMatch(b.nodes['out-plain'].textContent,/Mortgage/);
  assert.equal(b.nodes.mortgage.value,'n/a'); assert.equal(b.nodes.cash.value,'10,000');
  b.language('en'); assert.match(b.nodes['out-plain'].textContent,/Mortgage/);
});
test('finite inputs whose aggregate overflows withhold all derived values',()=>{
  const b=boot(); b.input('cash','1e308'); b.input('invest','1e308'); withheld(b);
  assert.match(b.nodes['out-plain'].textContent,/large|finite/i);
  b.language('zh'); assert.match(b.nodes['out-plain'].textContent,/金额|范围|有限/);
  b.input('invest','0'); assert.notEqual(b.nodes['out-main'].textContent,'—');
});
test('the debt ratio does not overflow solely from multiplying a finite balance by 100 first',()=>{
  const b=boot(); b.input('cash','1e308'); b.input('mortgage','1e308');
  assert.equal(b.nodes['out-main'].textContent,'$0'); assert.equal(b.nodes['out-dta'].textContent,'100%');
});
test('subtraction and ratio overflow also withhold every derived value',()=>{
  const subtraction=boot(); subtraction.input('cash','1e308'); subtraction.input('mortgage','-1e308'); withheld(subtraction);
  const ratio=boot(); ratio.input('cash','1e-308'); ratio.input('mortgage','1e308'); withheld(ratio);
});
test('a current valid copy writes the exact result and acknowledges success',async()=>{
  const b=boot(); b.input('cash','10,000'); b.input('mortgage','20,000');
  b.copy(); await Promise.resolve();
  assert.deepEqual(b.writes,['Net worth: −$10,000 · assets $10,000 · liabilities $20,000 · debt-to-asset 200% — mastermind-x.com']);
  assert.equal(b.nodes.copied.classList.contains('show'),true);
});
for (const changedAmount of ['n/a','50']) test('a pending valid copy cannot restore its receipt after an edit to '+changedAmount,async()=>{
  const b=boot(); b.input('cash','100');
  let finish; b.navigator.clipboard.writeText=line=>{b.writes.push(line);return new Promise(resolve=>{finish=resolve;});};
  b.copy(); assert.equal(b.writes.length,1);
  b.input('mortgage',changedAmount); if(changedAmount === 'n/a') withheld(b); finish(); await Promise.resolve();
  assert.equal(b.nodes.copied.classList.contains('show'),false);
});
test('editing a copied result invalidates its visible receipt immediately',()=>{
  const b=boot(); b.input('cash','100'); b.nodes.copied.classList.add('show');
  b.input('mortgage','n/a'); assert.equal(b.nodes.copied.classList.contains('show'),false);
});

// A shared summary can prioritize an error, but each invalid input must describe itself.
const ERROR_NAMES = {
  cash:['Cash & savings','现金与存款'], invest:['Investments','投资'],
  retire:['Retirement accounts','退休账户'], realestate:['Real estate','房地产'],
  vehicles:['Vehicles','车辆'], otherassets:['Other assets','其他资产'],
  mortgage:['Mortgage','房贷'], loans:['Student & other loans','学生贷款及其他'],
  creditcard:['Credit card debt','信用卡欠款'], otherdebts:['Other debts','其他债务']
};
function errorDescription(b,id) {
  const refs=(b.nodes[id].getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean);
  return refs.map(ref=>{
    assert.ok(b.nodes[ref], id+' references a missing description: '+ref);
    return b.nodes[ref].textContent;
  }).join(' ');
}
for(const [li,lang] of ['en','zh'].entries()) for(const id of FIELDS) {
  test(lang+' simultaneous error description identifies '+id,()=>{
    const b=boot(lang); FIELDS.forEach(field=>b.input(field,'n/a')); withheld(b);
    assert.equal(b.nodes[id].getAttribute('aria-invalid'),'true');
    const description=errorDescription(b,id);
    assert.ok(description.includes(ERROR_NAMES[id][li]),id+' incorrectly described as: '+description);
  });
}
test('language changes relocalize every active field error without changing input values',()=>{
  const b=boot(); FIELDS.forEach(id=>b.input(id,'n/a'));
  b.language('zh'); withheld(b);
  FIELDS.forEach(id=>{
    assert.ok(errorDescription(b,id).includes(ERROR_NAMES[id][1]),id+' has no own Chinese description');
    assert.equal(b.nodes[id].value,'n/a');
  });
  b.language('en');
  FIELDS.forEach(id=>assert.ok(errorDescription(b,id).includes(ERROR_NAMES[id][0]),id+' has no own English description'));
});
test('partial correction clears its obsolete description and preserves other errors',()=>{
  const b=boot(); FIELDS.forEach(id=>b.input(id,'n/a'));
  const priorRefs=b.nodes.cash.getAttribute('aria-describedby').split(/\s+/);
  b.input('cash','0'); withheld(b);
  assert.equal(b.nodes.cash.getAttribute('aria-invalid'),null);
  assert.equal(b.nodes.cash.getAttribute('aria-describedby'),null);
  priorRefs.forEach(ref=>assert.equal(b.nodes[ref].textContent,'','corrected input retains stale description'));
  assert.ok(errorDescription(b,'mortgage').includes('Mortgage'));
  FIELDS.slice(1).forEach(id=>b.input(id,'0'));
  assert.equal(b.nodes['out-main'].textContent,'$0');
  FIELDS.forEach(id=>{
    assert.equal(b.nodes[id].getAttribute('aria-describedby'),null);
    assert.equal(b.nodes[id].getAttribute('aria-invalid'),null);
  });
});
