'use strict';
/* Deterministic zero-browser-dependency DOM boundary on the actual JS renderer.
 * Executed by tests/test_market_navigator_view.py with the Python-owned wire.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {createHash} = require('node:crypto');

class Node {
  constructor(tag, doc) {
    this.tagName = tag;
    this.ownerDocument = doc;
    this.attrs = {};
    this.children = [];
    this.className = '';
    this.textContent = '';
    this.events = {};
    this.open = false;
    this.parentElement = null;
  }
  appendChild(child) {
    assert(child instanceof Node);
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  replaceChildren(...nodes) {
    nodes.forEach(node => { node.parentElement = this; });
    this.children = nodes;
  }
  setAttribute(key,value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key] || null; }
  addEventListener(name, fn) { this.events[name] = fn; }
  focus() { this.ownerDocument.activeElement = this; }
  set innerHTML(_value) { throw new Error('unsanitized HTML write'); }
  get innerHTML() { throw new Error('raw HTML read'); }
  walk() { return [this,...this.children.flatMap(c=>c.walk())]; }
  querySelectorAll(selector) {
    // Purposefully narrow test-only selector engine: real Chromium proof covers
    // full selector semantics.
    if (selector==='.mnv-path-details[open]') return this.walk().filter(x=>x.className==='mnv-path-details'&&x.open);
    const attr=selector.match(/^\[aria-label="([^"]+)"\]$/);
    if (attr) return this.walk().filter(x=>x.attrs['aria-label']===attr[1]);
    const cls=selector.match(/^\.([a-z0-9-]+)$/i);
    if (cls) return this.walk().filter(x=>x.className.split(' ').includes(cls[1]));
    throw new Error('unsupported test selector: '+selector);
  }
  querySelector(selector) {return this.querySelectorAll(selector)[0] || null;}
}
const doc = {activeElement:null};
doc.createElement = tag => new Node(tag,doc);
global.document = doc;

const client = require('../templates/market_navigator_client.js');
const viewModule = require('../templates/market_navigator_view.js');
const wire=JSON.parse(fs.readFileSync(0,'utf8'));
const request={request_id:'navigator-1',horizon:'swing',as_of:wire.requested_as_of,
  subject_binding_sha256:createHash('sha256').update('SPY:ARCX','utf8').digest('hex')};
const data=client.validate(wire,request);
const mount=new Node('main',doc);
const view=viewModule.createView(mount,{language:'en',theme:'dark',subjectLabel:'SPY · NYSE Arca'});
assert.equal(mount.querySelector('.mnv-empty-title').textContent,'No validated context selected');

view.render({status:'recorded_context',data});
assert.equal(mount.querySelectorAll('.mnv-path').length,3);
assert.equal(mount.querySelectorAll('.mnv-path-state').length,3);
assert.equal(mount.querySelectorAll('.mnv-path-diagnosis').length,3);
const explanations=mount.querySelectorAll('.mnv-path-diagnosis').map(n=>n.textContent);
assert(explanations.some(t=>t.includes('Defined trigger conditions hold')));
assert(explanations.some(t=>t.includes('Specified trigger conditions not yet met: 1')));
assert(explanations.some(t=>t.includes('Required condition comparisons not established: 1')));
assert(explanations.every(t=>!t.toLowerCase().includes('buy')&&!t.includes('%')));
assert.equal(mount.querySelector('.mnv-regime').textContent,'Mixed');
assert(mount.querySelector('.mnv-meta').textContent.includes('SPY'));
assert.equal(mount.querySelector('.mnv').attrs.lang,'en');
assert.equal(mount.querySelector('.mnv').attrs['data-theme'],'dark');
assert(mount.walk().some(x=>x.textContent.includes('No calibrated probabilities')));
assert(!mount.walk().some(x=>x.textContent.includes('100% probable')));
const first = mount.querySelectorAll('.mnv-path-details')[0];
first.open=true;
view.setLanguage('zh');
assert.equal(mount.querySelector('.mnv').attrs.lang,'zh');
assert.equal(mount.querySelectorAll('.mnv-path-details[open]').length,1);
assert(mount.walk().some(x=>x.textContent.includes('仅供研究参考')));
assert(mount.querySelectorAll('.mnv-path-diagnosis').some(n=>
  n.textContent.includes('尚未满足的既定触发条件')));
view.setTheme('light');
assert.equal(mount.querySelector('.mnv').attrs['data-theme'],'light');
assert.equal(mount.querySelectorAll('.mnv-path-details[open]').length,1);

view.render({status:'loading',data:null});
assert.equal(mount.querySelectorAll('.mnv-path').length,0);
assert(mount.querySelector('.mnv-empty-title').textContent.includes('正在检查'));
view.render({status:'unavailable',data:null});
assert.equal(mount.querySelectorAll('.mnv-path').length,0);
view.render({status:'recorded_context',data:{...data,authority:{...data.authority,trading:true}}});
assert.equal(mount.querySelectorAll('.mnv-path').length,0);
assert(mount.querySelector('.mnv-empty-title').textContent.includes('未通过验证'));
view.render({status:'recorded_context',data});
assert.equal(mount.querySelectorAll('.mnv-path').length,3);
view.dispose();
assert.equal(mount.children.length,0);
view.render({status:'recorded_context',data});
assert.equal(mount.children.length,0);
assert.throws(()=>viewModule.createView(null));
assert.throws(()=>viewModule.createView(new Node('main',doc),{language:'xx'}));
assert.throws(()=>viewModule.createView(new Node('main',doc),{subjectLabel:' '.repeat(97)}));
console.log('view DOM boundary: PASS — real Python wire, both languages, themes, open state, errors, dispose, authority refusal');
