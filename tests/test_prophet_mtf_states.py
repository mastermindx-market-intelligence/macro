"""Execute the shipped Turn Setups request/render owner with deterministic boundaries.

No fabricated owner exports and no network. A real-browser pass covers HTML parsing,
layout and focus; this suite covers source failures and request races without sleeps.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    "loading", "ready", "empty", "invalid_payloads", "http", "network", "json",
    "timeout", "retry", "obsolete", "parallel", "delayed_names", "count_cap",
    "injection", "missing_k", "focus_success", "focus_failure", "focus_moved",
    "no_abortcontroller", "partial", "health_counts", "hysteresis", "limited_history",
]

NODE = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('templates/dashboard.html.j2', 'utf8');
const marker = '/* TS-U3 dash-tape-band + dash-mtf-section JS';
assert.equal(source.split(marker).length, 2);
const start = source.indexOf(marker);
const script = source.slice(start, source.indexOf('// See-more folds', start)) + '\n})();';
assert.ok(!script.includes('{{') && !script.includes('{%'));
assert.ok(!script.includes('var PLV_URL'));
const decode = s => s.replace(/&quot;/g,'"').replace(/&#39;/g,"'")
  .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const flush = () => new Promise(resolve => setImmediate(resolve));

function row(overrides = {}) {
  return {state:'UPTURN_WATCH', k:2, since:'2026-10-29',
    monthly_phase:'below_water,rising', basket_ids:['consumer_staples'],
    legs:{d_macd:true,d3_confluence:true,w_macd:'none',w2_macd:false},
    trend:{d:{pos:true,bars_since_cross:1},d3:{pos:true,bars_since_cross:2},
      w:{pos:false,bars_since_cross:null},w2:{pos:false,bars_since_cross:null}}, ...overrides};
}
function payload(overrides = {}) {
  return {schema:'mtf_upturn.v1',as_of:'2026-10-30',universe_n:100,
    tickers:{ACME:row()},cohort:{confirmed:[],watch:['ACME']},...overrides};
}
async function client({abort = true} = {}) {
  const document = {activeElement:null};
  class Element {
    constructor(id='', html='') {
      this.id=id; this.attrs={}; this.events={}; this.hidden=false; this._disabled=false;
      const classes = new Set();
      this.classList = {
        toggle(name) { if(classes.has(name)){classes.delete(name);return false;} classes.add(name);return true; },
        contains(name) {return classes.has(name);},
        add(name) {classes.add(name);},
      };
      this.innerHTML=html;
    }
    set innerHTML(value) {
      this._html=String(value); this.children=[];
      if(this.id==='dash-mtf-body') {
        if(value.includes('class="mtf-skel"')) {
          this.skeleton=new Element(); this.skeleton.hidden=true;
        } else this.skeleton=null;
        if(value.includes('dash-mtf-collapse')) {
          this.fold=new Element(); this.fold.classList.add('is-collapsed');
          this.more=new Element(); this.more.setAttribute('aria-expanded','false');
        } else {this.fold=null;this.more=null;}
        for(const match of value.matchAll(/<td class="dash-mtf-baskets" data-mtf-symbol="([^"]*)">([\s\S]*?)<\/td>/g)) {
          const cell=new Element('',match[2]); cell.setAttribute('data-mtf-symbol',decode(match[1])); this.children.push(cell);
        }
      }
    }
    get innerHTML(){return this._html;}
    get textContent(){return decode(this._html.replace(/<[^>]*>/g,''));}
    set textContent(value){this._html=String(value);}
    setAttribute(name,value){this.attrs[name]=String(value);}
    getAttribute(name){return this.attrs[name]??null;}
    querySelector(selector){
      if(selector==='.mtf-skel') return this.skeleton;
      if(selector==='.dash-mtf-more') return this.more;
      if(selector==='.dash-mtf-collapse') return this.fold;
      throw new Error('Unexpected selector '+selector);
    }
    querySelectorAll(selector){
      if(selector==='[data-mtf-symbol]') return this.children;
      throw new Error('Unexpected selector '+selector);
    }
    addEventListener(type,handler){(this.events[type]??=[]).push(handler);}
    click(){if(!this.disabled&&!this.hidden)(this.events.click??[]).forEach(fn=>fn({target:this}));}
    focus(){document.activeElement=this;}
    set disabled(value){
      this._disabled=!!value;
      if(value&&document.activeElement===this) document.activeElement=document.body;
    }
    get disabled(){return this._disabled;}
  }
  const ids = Object.fromEntries(['dash-mtf-section','dash-mtf-body','dash-mtf-status','dash-mtf-retry','dash-mtf-heading','outside-control']
    .map(id=>[id,new Element(id)]));
  ids['dash-mtf-body'].innerHTML='<div class="mtf-skel" aria-hidden="true" hidden></div>';
  ids['dash-mtf-retry'].hidden=true;
  document.body=new Element('body');
  document.activeElement=document.body;
  document.documentElement={getAttribute(){return 'en';}};
  document.getElementById=id=>ids[id]??null;
  const timers=new Map(), requests=[];
  let timerId=0;
  const context={document,console,Promise,Number,Date,Set,window:{},
    setTimeout(fn,delay){const id=++timerId;timers.set(id,{fn,delay});return id;},
    clearTimeout(id){timers.delete(id);},
    fetch(url,options={}) {
      let resolve,reject;
      const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
      requests.push({url,options,resolve,reject});return promise;
    },
  };
  if(abort) context.AbortController=AbortController;
  vm.runInNewContext(script,context,{filename:'actual-prophet-mtf-owner.js'});
  await flush();
  const mtf=()=>requests.filter(r=>r.url==='stockdata/mtf_upturn.json');
  async function answer(request,data,kind='ok') {
    if(kind==='network') request.reject(new Error('network'));
    else request.resolve({ok:kind!=='http',json:async()=>{
      if(kind==='json')throw new SyntaxError('bad JSON');return data;
    }});
    await flush();
  }
  return {ids,document,requests,mtf,answer,
    panel:ids['dash-mtf-section'],body:ids['dash-mtf-body'],status:ids['dash-mtf-status'],
    retry:ids['dash-mtf-retry'],heading:ids['dash-mtf-heading'],
    state:()=>ids['dash-mtf-section'].getAttribute('data-mtf-state'),
    async expire(){const due=[...timers.entries()].filter(([,t])=>t.delay===4000);
      for(const [id,t] of due){if(timers.delete(id))t.fn();}await flush();},
  };
}
function unavailable(c){
  assert.equal(c.state(),'unavailable');
  assert.equal(c.body.getAttribute('aria-busy'),'false');
  assert.equal(c.body.innerHTML,'');
  assert.equal(c.retry.hidden,false);assert.equal(c.retry.disabled,false);
  assert.match(c.status.textContent,/no result has been inferred/);
  assert.match(c.status.textContent,/无法验证数据源/);
  assert.doesNotMatch(c.status.textContent,/0 qualifying|No qualifying/);
}
async function run(name) {
  const c=await client({abort:name!=='no_abortcontroller'});
  if(name==='loading'){
    assert.equal(c.state(),'loading');
    assert.equal(c.body.getAttribute('aria-busy'),'true');
    assert.equal(c.body.skeleton.hidden,false);
    assert.match(c.status.textContent,/Loading the published/);
    assert.match(c.status.textContent,/正在加载/);
    assert.equal(c.mtf().length,1);return;
  }
  if(name==='partial'){
    await c.answer(c.mtf()[0],payload({evaluated_n:99,failed_n:1}));
    assert.equal(c.state(),'ready');assert.match(c.status.textContent,/Partial: 1 calculations unavailable/);
    assert.match(c.status.textContent,/部分结果/);return;
  }
  if(name==='hysteresis'){
    await c.answer(c.mtf()[0],payload({tickers:{ACME:row({state:'UPTURN_CONFIRMED',k:2})},
      cohort:{confirmed:['ACME'],watch:[]}}));
    assert.equal(c.state(),'ready');assert.match(c.body.innerHTML,/TURNING UP/);return;
  }
  if(name==='health_counts'){
    const bad=[
      payload({evaluated_n:0,failed_n:100}),
      payload({evaluated_n:null,failed_n:null}),
      payload({tickers:{},cohort:{confirmed:[],watch:[]}}),
      payload({evaluated_n:99}),payload({failed_n:1}),
      payload({evaluated_n:100,failed_n:-1}),payload({evaluated_n:'99',failed_n:1}),
      payload({evaluated_n:100,failed_n:1}),
      payload({evaluated_n:99,failed_n:1,tickers:{},cohort:{confirmed:[],watch:[]}}),
    ];
    for(const data of bad){const x=await client();await x.answer(x.mtf()[0],data);unavailable(x);}
    return;
  }
  if(name==='invalid_payloads'){
    const bad=[
      null,[],{},payload({schema:'other'}),payload({as_of:'2026-02-30'}),
      payload({as_of:'2026-10-30T12:00:00Z'}),payload({universe_n:0}),
      payload({universe_n:'100'}),payload({error:'internal private error'}),
      payload({tickers:[]}),payload({tickers:{}}),payload({cohort:{watch:'ACME',confirmed:[]}}),
      payload({cohort:{watch:['ACME']}}),payload({cohort:{watch:[null],confirmed:[]}}),
      payload({tickers:{ACME:[]}}),payload({tickers:{ACME:row({state:'NONE'})}}),
      payload({tickers:{ACME:row({k:'2'})}}),payload({tickers:{ACME:row({k:5})}}),
      payload({tickers:{ACME:row({k:1})}}),payload({tickers:{ACME:row({htf_coverage:'true'})}}),
      payload({tickers:{ACME:row({legs:[]})}}),
      payload({tickers:{ACME:row({legs:{d_macd:'true'}})}}),
      payload({tickers:{ACME:row({legs:{w_macd:'wrong'}})}}),
      payload({tickers:{ACME:row({trend:{w:{pos:'true'}}})}}),
      payload({tickers:{ACME:row({trend:{w:{bars_since_cross:-1}}})}}),
      payload({tickers:{ACME:row({basket_ids:'technology'})}}),
      payload({tickers:{ACME:row({basket_ids:[null]})}}),
      payload({tickers:{ACME:row({monthly_phase:{}})}}),
      payload({tickers:{ACME:row({since:'tomorrow'})}}),
      payload({tickers:{ACME:row({legs:null})}}),
      payload({tickers:{ACME:row({legs:{d_macd:true,d3_confluence:true,w_macd:'none'}})}}),
      payload({tickers:{ACME:row({trend:null})}}),
      payload({tickers:{ACME:row({trend:{d:{pos:true,bars_since_cross:1}}})}}),
      payload({cohort:{confirmed:[],watch:[]}}),
      payload({cohort:{confirmed:[],watch:['ACME','ACME']}}),
      payload({tickers:{ACME:row(),ZEUS:row()},universe_n:1,
        cohort:{confirmed:[],watch:['ACME','ZEUS']}}),
    ];
    for(const data of bad){const x=await client();await x.answer(x.mtf()[0],data);unavailable(x);
      assert.doesNotMatch(x.status.textContent,/internal private error/);}
    return;
  }
  if(['http','network','json'].includes(name)){
    await c.answer(c.mtf()[0],null,name);unavailable(c);return;
  }
  if(['timeout','no_abortcontroller'].includes(name)){
    await c.expire();unavailable(c);
    if(name==='timeout')assert.equal(c.mtf()[0].options.signal.aborted,true);
    else assert.equal(c.mtf()[0].options.signal,undefined);
    await c.answer(c.mtf()[0],payload());unavailable(c);return;
  }
  if(['retry','obsolete','focus_success','focus_failure','focus_moved'].includes(name)){
    await c.expire();unavailable(c);
    c.retry.focus();c.retry.click();await flush();
    assert.equal(c.mtf().length,2);assert.equal(c.state(),'loading');
    assert.equal(c.retry.disabled,true);
    c.retry.click();await flush();assert.equal(c.mtf().length,2);
    if(name==='focus_moved')c.ids['outside-control'].focus();
    if(name==='focus_failure'){
      await c.answer(c.mtf()[1],null,'http');unavailable(c);
      assert.equal(c.document.activeElement,c.retry);return;
    }
    await c.answer(c.mtf()[1],payload({as_of:'2026-11-02'}));
    assert.equal(c.state(),'ready');assert.equal(c.retry.hidden,true);
    assert.match(c.status.textContent,/2026-11-02/);
    if(name==='focus_success')assert.equal(c.document.activeElement,c.heading);
    if(name==='focus_moved')assert.equal(c.document.activeElement,c.ids['outside-control']);
    if(name==='obsolete'){
      await c.answer(c.mtf()[0],payload({cohort:{confirmed:[],watch:[]}}));
      assert.equal(c.state(),'ready');assert.match(c.status.textContent,/2026-11-02/);
    }
    return;
  }
  if(name==='empty'){
    await c.answer(c.mtf()[0],payload({evaluated_n:100,failed_n:0,tickers:{},cohort:{confirmed:[],watch:[]}}));
    assert.equal(c.state(),'empty');assert.match(c.status.textContent,/0 qualifying setups · as of 2026-10-30/);
    assert.match(c.body.innerHTML,/No qualifying turn setups in this snapshot/);
    assert.match(c.body.innerHTML,/此快照/);assert.doesNotMatch(c.body.innerHTML,/tonight/);
    assert.equal(c.retry.hidden,true);return;
  }
  if(name==='count_cap'||name==='delayed_names'){
    const tickers={},watch=[];
    for(let i=0;i<(name==='count_cap'?45:15);i++){const sym='T'+i;tickers[sym]=row();watch.push(sym);}
    await c.answer(c.mtf()[0],payload({tickers,cohort:{confirmed:[],watch}}));
    assert.equal(c.state(),'ready');
    assert.equal((c.body.innerHTML.match(/class="dash-mtf-k"/g)||[]).length,name==='count_cap'?40:15);
    c.body.more.click();assert.equal(c.body.more.getAttribute('aria-expanded'),'true');
    if(name==='count_cap')assert.match(c.status.textContent,/40 of 45/);
    else{
      const more=c.body.more,cell=c.body.children[0];
      more.focus();
      await c.answer(c.requests.find(r=>r.url==='basketdata/baskets.json'),
        {baskets:[{id:'consumer_staples',name:'Consumer staples',name_zh:'必需消费'}]});
      assert.equal(c.body.more,more);assert.equal(c.document.activeElement,more);
      assert.equal(more.getAttribute('aria-expanded'),'true');
      assert.match(cell.innerHTML,/Consumer staples/);assert.match(cell.innerHTML,/必需消费/);
    }
    return;
  }
  const data=payload();
  if(name==='limited_history')data.tickers.ACME.htf_coverage=false;
  if(name==='injection')data.tickers.ACME.monthly_phase='x" onmouseover="alert(1)<img src=x>';
  if(name==='missing_k'){
    delete data.tickers.ACME.k;
    await c.answer(c.mtf()[0],data);unavailable(c);return;
  }
  await c.answer(c.mtf()[0],data);
  assert.equal(c.state(),'ready');assert.equal(c.body.getAttribute('aria-busy'),'false');
  assert.equal(c.retry.hidden,true);assert.match(c.status.textContent,/1 qualifying setup ·/);
  assert.match(c.body.innerHTML,/<b>ACME<\/b>/);assert.match(c.body.innerHTML,/2026-10-30/);
  if(name==='injection'){
    assert.match(c.body.innerHTML,/&quot; onmouseover=&quot;/);
    assert.doesNotMatch(c.body.innerHTML,/" onmouseover="/);
    assert.doesNotMatch(c.body.innerHTML,/<img/);
  }
  if(name==='limited_history'){
    assert.match(c.body.innerHTML,/dash-mtf-leg unknown/);
    assert.match(c.body.innerHTML,/Unknown, not negative/);
    assert.match(c.body.innerHTML,/双周历史不足/);
    assert.match(c.body.innerHTML,/data-tip-en="W"/);
  }
  if(name==='parallel'){
    assert.equal(c.requests.filter(r=>r.url==='live/basket_pulse.json').length,1);
    await c.expire();assert.equal(c.state(),'ready');
  }
}
run(process.argv[1]).then(()=>console.log('PASS '+process.argv[1]))
  .catch(error=>{console.error(error);process.exitCode=1;});
"""


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_turn_setup_source_owner(scenario):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the shipped browser owner")
    result = subprocess.run(
        [node, "-e", NODE, scenario], cwd=ROOT, capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"PASS {scenario}" in result.stdout
