"""Production Save composition on exact live candidate nodes; no browser/auth effect.

The DOM and account service below are boundary doubles. The controller is the
actual shipped module; account mutation semantics are covered separately against
actual WatchStore in test_prophet_save_account_isolation.py and its incumbent tests.
"""
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).parents[1]

DOM = r"""
const assert=require('node:assert/strict');
const observers=[];let mutationQueued=false;
function changed(el){if(!el.isConnected||mutationQueued)return;mutationQueued=true;
  queueMicrotask(()=>{mutationQueued=false;observers.forEach(fn=>fn());});}
function simple(el,sel){
  if(!el)return false;
  if(sel===':scope')return true;
  let no=/\:not\(([^)]+)\)/.exec(sel);if(no){if(simple(el,no[1]))return false;sel=sel.replace(no[0],'');}
  const tag=/^[a-z][a-z0-9-]*/i.exec(sel);if(tag&&el.tag!==tag[0])return false;
  for(const m of sel.matchAll(/#([\w-]+)/g))if(el.id!==m[1])return false;
  for(const m of sel.matchAll(/\.([\w-]+)/g))if(!el.classList.contains(m[1]))return false;
  for(const m of sel.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)){
    if(!el.hasAttribute(m[1])||(m[2]!==undefined&&el.getAttribute(m[1])!==m[2]))return false;
  }return true;
}
function match(el,sel){const parts=sel.replace(/>/g,' > ').trim().split(/\s+/);let i=parts.length-1;
  if(!simple(el,parts[i--]))return false;
  while(i>=0){if(parts[i]==='>'){i--;el=el.parentNode;if(!simple(el,parts[i--]))return false;}
    else{let at=el.parentNode;while(at&&!simple(at,parts[i]))at=at.parentNode;if(!at)return false;el=at;i--;}}
  return true;
}
class El{
  constructor(tag){this.tag=tag;this.children=[];this.parentNode=null;this.attrs={};this.listeners={};this._text='';this.disabled=false;this.scrollTop=0;this.open=false;}
  get isConnected(){return this===html||!!this.parentNode&&this.parentNode.isConnected;}
  get id(){return this.getAttribute('id')||'';}set id(v){this.setAttribute('id',v);}
  get className(){return this.getAttribute('class')||'';}set className(v){this.setAttribute('class',v);}
  get classList(){const e=this;return {contains:k=>e.className.split(/\s+/).includes(k),add:k=>{if(!e.classList.contains(k))e.className=(e.className+' '+k).trim();}};}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  set textContent(v){this._text=String(v);this.children.forEach(c=>c.parentNode=null);this.children=[];changed(this);}
  get value(){return this._value!==undefined?this._value:this.tag==='select'&&this.children[0]?this.children[0].value:'';}
  set value(v){this._value=v;}
  get hidden(){return this.hasAttribute('hidden');}set hidden(v){if(v)this.setAttribute('hidden','');else this.removeAttribute('hidden');}
  setAttribute(k,v){if(this.attrs[k]===String(v))return;this.attrs[k]=String(v);changed(this);}
  getAttribute(k){return Object.prototype.hasOwnProperty.call(this.attrs,k)?this.attrs[k]:null;}
  hasAttribute(k){return this.getAttribute(k)!==null;}
  removeAttribute(k){if(this.hasAttribute(k)){delete this.attrs[k];changed(this);}}
  contains(n){return this===n||this.children.some(c=>c.contains(n));}
  append(...nodes){for(const n of nodes){n.remove();n.parentNode=this;this.children.push(n);}changed(this);}
  replaceChildren(...nodes){this.children.forEach(c=>c.parentNode=null);this.children=[];this._text='';this.append(...nodes);}
  remove(){if(this.parentNode){const p=this.parentNode;p.children=p.children.filter(c=>c!==this);this.parentNode=null;changed(p);}}
  closest(sel){for(let n=this;n;n=n.parentNode)if(sel.split(',').some(s=>match(n,s.trim())))return n;return null;}
  querySelectorAll(sel){let all=[];function walk(e){e.children.forEach(c=>{all.push(c);walk(c);});}walk(this);
    if(sel.startsWith(':scope > '))return this.children.filter(c=>simple(c,sel.slice(9)));
    return all.filter(c=>sel.split(',').some(s=>match(c,s.trim())));}
  querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
  getClientRects(){return this.isConnected&&!this.closest('[hidden],.mx-tier-hidden,.mx-tier-blurred')?[{}]:[];}
  addEventListener(t,fn){(this.listeners[t]||=([])).push(fn);}
  dispatchEvent(e){e.target=e.target||this;e.preventDefault=()=>{};(this.listeners[e.type]||[]).forEach(fn=>fn(e));return true;}
  click(){if(!this.disabled)this.dispatchEvent({type:'click'});}
  focus(){document.activeElement=this;}
  showModal(){this.open=true;}close(){this.open=false;this.dispatchEvent({type:'close'});}
}
const html=new El('html'),body=new El('body');html.append(body);
global.document={documentElement:html,body,readyState:'loading',listeners:{},activeElement:null,
 createElement:t=>new El(t),querySelector:s=>html.querySelector(s),querySelectorAll:s=>html.querySelectorAll(s),
 getElementById:id=>html.querySelector('#'+id),addEventListener(t,fn){(this.listeners[t]||=[]).push(fn);},
 dispatchEvent(e){(this.listeners[e.type]||[]).forEach(fn=>fn(e));}};
global.window=global;global.HTMLDialogElement=El;global.MutationObserver=class{constructor(fn){this.fn=fn;}observe(){observers.push(this.fn);}};
const winEvents={};window.addEventListener=(t,fn)=>(winEvents[t]||=[]).push(fn);
window.scrollX=0;window.scrollY=500;window.scrollTo=o=>{window.scrollX=o.left;window.scrollY=o.top;};
const ev=(type,detail)=>{(winEvents[type]||[]).forEach(fn=>fn({type,detail:detail||{}}));};
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function element(tag,cls,id){const e=new El(tag);if(cls)e.className=cls;if(id)e.id=id;return e;}
const host=element('div');host.setAttribute('data-watchstore-checked-save','');body.append(host);
const panel=element('section','','us-standouts');panel.setAttribute('data-board-asof','2026-11-03');body.append(panel);
const grid=element('div','','us-cand-grid');panel.append(grid);
function candidate(id){const row=element('article','pvcard po-card');row.setAttribute('data-ticker','FLS');row.setAttribute('data-po-id',id);
 const link=element('a','pv-setup-stock-link');link.setAttribute('href','stock.html#FLS');
 const foot=element('footer','po-footer'),details=element('details','pv-setup-inline'),summary=element('summary'),content=element('div','pv-setup-body');
 details.append(summary,content);row.append(link,foot,details);grid.append(row);return {row,link,foot,details,summary,content};}
const first=candidate('screener-0'),second=candidate('screener-1');
let sess={state:'ready',userId:'u1',generation:1}, writes=0, reads=0, inspection=0, saveResult, pendingSave;
window.WatchStore={checkedSession:()=>({...sess}),lists:{refresh:()=>{reads++;return Promise.resolve([{id:'L1',name:'First list'},{id:'L2',name:'Chosen list'}]);}},
 symbols:{saveChecked:(list,names)=>{writes++;assert.equal(list,'L2');assert.deepEqual(names,['FLS']);return pendingSave||Promise.resolve(saveResult||{state:'saved',names:['FLS'],readBackAt:'2026-11-03T12:00:00Z'});},
 inspect:()=>{inspection++;return Promise.resolve({state:'not-confirmed',writeRetryAllowed:false});}}};
let signins=0;window.MDXAuth={open:()=>{signins++;}};
const mod=require(MODULE);mod.init();
const saveDialog=()=>document.getElementById('prophet-save-dialog');
const state=()=>saveDialog().getAttribute('data-save-state');
const buttons=()=>saveDialog().querySelectorAll('button');
const choose=()=>{const s=saveDialog().querySelector('select');s.value='L2';return buttons().find(b=>b.textContent.includes('Save ticker'));};
"""


def run(scenario):
    script = 'const MODULE=' + json.dumps(str(ROOT / 'templates/prophet_save.js')) + ';\n' + DOM
    script += '\n(async()=>{' + scenario + "\n})().then(()=>{process.stdout.write('OK');},e=>{console.error(e.stack);process.exitCode=1;});"
    proc = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert proc.stdout == 'OK'


def test_real_module_mounts_once_selects_account_list_and_returns_exact_occurrence():
    run(r"""
      await flush();mod.mount();mod.mount();await flush();
      assert.equal(first.row.querySelectorAll('.pvs-save-pick').length,1);
      assert.equal(second.row.querySelectorAll('.pvs-save-pick').length,1);
      assert.equal(writes,0);
      const pick=second.row.querySelector('.pvs-save-pick');pick.click();await flush();
      assert.equal(state(),'choose');choose().click();await flush();assert.equal(state(),'saved');assert.equal(writes,1);
      buttons()[0].click();await flush();assert.equal(document.activeElement,pick);assert.equal(window.scrollY,500);
      assert.equal(first.row.querySelector('.pvs-save-pick')===pick,false);
    """)


def test_waiting_double_click_and_uncertain_membership_read_never_retry():
    run(r"""
      let settle;pendingSave=new Promise(r=>settle=r);
      first.row.querySelector('.pvs-save-pick').click();await flush();const submit=choose();submit.click();submit.click();
      assert.equal(state(),'waiting');assert.equal(writes,1);
      settle({state:'uncertain'});await flush();assert.equal(state(),'uncertain');
      const inspect=buttons().find(b=>b.textContent.includes('Check account list'));inspect.click();await flush();
      assert.equal(inspection,1);assert.equal(writes,1);assert.equal(state(),'uncertain');
      assert.equal(buttons().some(b=>b.textContent.includes('Save ticker')),false);
      buttons()[0].click();first.row.querySelector('.pvs-save-pick').click();await flush();
      assert.equal(state(),'uncertain');assert.equal(saveDialog().querySelector('select'),null);
      assert.equal(writes,1,'closing/reopening must not turn an unknown effect into a second save');
    """)


@pytest.mark.parametrize('mutation', ["first.link.setAttribute('href','stock.html#OTHER');",
                                      "panel.setAttribute('data-board-asof','2026-11-04');",
                                      "first.row.classList.add('mx-tier-hidden');",
                                      "first.row.remove();",
                                      "sess={state:'ready',userId:'u2',generation:2};ev('mdx-auth');",
                                      "ev('mmx-access-tier');",
                                      "document.dispatchEvent({type:'candidate-pool-hydrated'});"])
def test_context_loss_drops_late_success_without_reopening_stale_candidate(mutation):
    run(r"""
      let settle;pendingSave=new Promise(r=>settle=r);
      first.row.querySelector('.pvs-save-pick').click();await flush();choose().click();
    """ + mutation + r"""
      await flush();settle({state:'saved',names:['FLS'],readBackAt:'then'});await flush();
      assert.equal(saveDialog().open,false);assert.equal(writes,1);
      assert.notEqual(document.activeElement,first.row.querySelector('.pvs-save-pick'));
    """)


def test_signin_resumes_only_the_chooser_and_never_saves_automatically():
    run(r"""
      sess={state:'signed_out',userId:null,generation:1};
      first.row.querySelector('.pvs-save-pick').click();await flush();assert.equal(state(),'signed-out');
      buttons().find(b=>b.textContent.includes('Sign in')).click();assert.equal(signins,1);assert.equal(saveDialog().open,false);
      sess={state:'ready',userId:'u1',generation:2};ev('mdx-auth',{event:'SIGNED_IN'});await flush();
      assert.equal(saveDialog().open,true);assert.equal(state(),'choose');assert.equal(writes,0);
    """)


def test_setup_overlay_closes_modal_then_reopens_same_body_section_and_reading_position():
    run(r"""
      const native=element('dialog','','pv-setup-dialog'),head=element('header','pvs-dialog-head'),target=element('div','pvs-dialog-content');
      const closer=element('button','pvs-close');head.append(closer);native.append(head,target);body.append(native);
      const sources=element('section','','source-panel');sources.setAttribute('role','tabpanel');sources.setAttribute('data-pvs-section','sources');first.content.append(sources);
      const tab=element('button');tab.setAttribute('aria-controls','source-panel');head.append(tab);
      let selected=0;tab.addEventListener('click',()=>selected++);
      first.summary.addEventListener('click',()=>{target.append(first.content);native.showModal();});
      closer.addEventListener('click',()=>{first.details.append(first.content);native.close();});
      first.summary.click();await flush();native.scrollTop=177;
      const pick=native.querySelector('.pvs-save-setup');assert.ok(pick);pick.click();await flush();
      assert.equal(native.open,false,'only one modal owner at a time');assert.equal(saveDialog().open,true);
      choose().click();await flush();buttons()[0].click();await flush();
      assert.equal(native.open,true);assert.equal(native.contains(first.content),true);
      assert.equal(native.scrollTop,177);assert.equal(selected,1);
      assert.equal(document.activeElement,native.querySelector('.pvs-save-setup'));
    """)


def test_dense_table_uses_the_same_exact_inert_source_and_returns_its_own_control():
    run(r"""
      const wrap=element('div','','us-stocktable-wrap'),tbody=element('tbody'),row=element('tr'),cell=element('td');
      const link=element('a','stf-tkr');link.setAttribute('href','stock.html#FLS');
      const detail=element('details','pv-setup-inline');detail.setAttribute('data-setup-ticker','FLS');
      const holder=element('template','pvs-body-source');holder.content=element('fragment');holder.content.append(element('div','pv-setup-body'));
      detail.append(element('summary'),holder);cell.append(link,detail);row.append(cell);tbody.append(row);wrap.append(tbody);panel.append(wrap);
      await flush();const pick=cell.querySelector('.pvs-save-pick');assert.ok(pick);pick.click();await flush();
      choose().click();await flush();assert.equal(state(),'saved');buttons()[0].click();await flush();
      assert.equal(document.activeElement,pick);assert.equal(holder.content.children.length,1);
    """)


@pytest.mark.parametrize('answer,expected', [('[]', 'empty'), ('null', 'unavailable')])
def test_missing_lists_cannot_implicitly_create_or_save(answer, expected):
    run("WatchStore.lists.refresh=()=>Promise.resolve(" + answer + r""");
      first.row.querySelector('.pvs-save-pick').click();await flush();
      assert.equal(state(),""" + json.dumps(expected) + r""");assert.equal(writes,0);
    """)


def test_dashboard_has_production_checked_host_and_both_assets_only_in_stocks_mode():
    from tests.test_dashboard_template_render import _base_vm, _env
    from bs4 import BeautifulSoup
    for mode in ('stocks', 'macro'):
        page = BeautifulSoup(_env().get_template('dashboard.html.j2').render(**_base_vm(), mode=mode), 'html.parser')
        assert bool(page.select('[data-watchstore-checked-save]')) is (mode == 'stocks')
        assert bool(page.select('script[src="prophet_save.js"]')) is (mode == 'stocks')
        assert bool(page.select('link[href="prophet_save.css"]')) is (mode == 'stocks')
        if mode == 'stocks':
            scripts = [s.get('src') for s in page.select('script[src]')]
            assert scripts.index('theme.js') < scripts.index('watchstore.js') < scripts.index('prophet_save.js')


def test_static_copy_includes_the_new_production_assets():
    import ast
    source = ast.parse((ROOT / 'scripts/build_site.py').read_text())
    assets = next(n.iter for n in ast.walk(source) if isinstance(n, ast.For)
                  and isinstance(n.target, ast.Name) and n.target.id == 'asset'
                  and isinstance(n.iter, ast.Tuple) and any(isinstance(e, ast.Constant) and e.value == 'watchstore.js' for e in n.iter.elts))
    assert {'prophet_save.js', 'prophet_save.css'} <= {e.value for e in assets.elts if isinstance(e, ast.Constant)}
