'use strict';
// Inert DOM for a real JS host-scope integration test. Chromium supplies
// independent render/focus/viewport proof; no jsdom/network dependency.
const assert=require('node:assert/strict');
const fs=require('node:fs');
if (!globalThis.crypto?.subtle) globalThis.crypto=require('node:crypto').webcrypto;
class Node {
  constructor(tag,doc) {
    this.tagName=tag;this.ownerDocument=doc;this.className='';
    this.textContent='';this.attrs={};this.children=[];this.parentElement=null;
    this.events={};this.open=false;
  }
  appendChild(child) {child.parentElement=this;this.children.push(child);return child;}
  replaceChildren(...children){this.children=children;children.forEach(c=>c.parentElement=this);}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k]||null;}
  addEventListener(name,handler){this.events[name]=handler;}
  focus(){this.ownerDocument.activeElement=this;}
  set innerHTML(_v){throw Error('raw HTML injection');}
  walk(){return [this,...this.children.flatMap(node=>node.walk())];}
  querySelectorAll(selector){
    if(selector==='.mnv-path-details[open]')
      return this.walk().filter(n=>n.className==='mnv-path-details'&&n.open);
    const cls=/^\.([\w-]+)$/.exec(selector);
    if(cls)return this.walk().filter(n=>n.className.split(' ').includes(cls[1]));
    throw Error('unsupported test locator '+selector);
  }
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
const doc={activeElement:null};doc.createElement=tag=>new Node(tag,doc);
globalThis.document=doc;
globalThis.MastermindNavigatorClient=require('../templates/market_navigator_client.js');
globalThis.MastermindNavigatorView=require('../templates/market_navigator_view.js');
const mountApi=require('../templates/market_navigator_mount.js');
const wire=JSON.parse(fs.readFileSync(0,'utf8'));
const root=new Node('main',doc);
let scope='accountA:site-full',reads=0,pending=[];
const surface=mountApi.createSurface(root,{getScope:()=>scope});
function binding(overrides={}){return {
 scope_key:scope,subject:'SPY:ARCX',horizon:'swing',as_of:wire.requested_as_of,
 subjectLabel:'SPY · NYSE Arca',language:'en',theme:'dark',
 read:async req=>{reads++;return {...wire,request_id:req.request_id}},
 ...overrides
};}
(async()=>{
 surface.rebind(binding());
 assert.equal(reads,0,'component must never auto-read');
 assert.equal(root.querySelectorAll('.mnv-path').length,0);
 assert.equal(await surface.activate(),true);
 assert.equal(reads,1);
 assert.equal(root.querySelectorAll('.mnv-path').length,3);
 surface.setLanguage('zh');surface.setTheme('light');
 assert.equal(root.querySelector('.mnv').getAttribute('lang'),'zh');
 assert.equal(root.querySelector('.mnv').getAttribute('data-theme'),'light');

 scope='accountB:site-full';
 assert.equal(await surface.activate(),false,'stale scope must refuse');
 assert.equal(reads,1,'old account read forbidden');
 assert.equal(root.querySelectorAll('.mnv-path').length,0);

 surface.rebind(binding({subject:'QQQ:XNAS'}));
 assert.equal(await surface.activate(),true);
 assert.equal(reads,2);
 assert.equal(root.querySelector('.mnv-empty-title').textContent,
              'The returned evidence did not pass validation.');
 assert.equal(root.querySelectorAll('.mnv-path').length,0);

 surface.rebind(binding());
 assert.equal(await surface.activate(),true);
 assert.equal(root.querySelectorAll('.mnv-path').length,3);

 // Scope switch between dispatch and return: even if source ignores Abort,
 // neither the stale result nor a subsequent activate may disclose it.
 let resolver;
 surface.rebind(binding({read:()=>{reads++;return new Promise(resolve=>resolver=resolve)}}));
 const underway=surface.activate();
 for (let n=0;n<60&&!resolver;n++)await new Promise(resolve=>setTimeout(resolve,1));
 assert.equal(typeof resolver,'function');
 scope='accountC:site-full';
 resolver({...wire,request_id:'navigator-1'});
 assert.equal(await underway,false);
 assert.equal(root.querySelectorAll('.mnv-path').length,0);
 const before=reads;
 assert.equal(await surface.activate(),false);
 assert.equal(reads,before);

 // Incomplete or unrecognized new scope must clear old content first.
 assert.throws(()=>surface.rebind({scope_key:'bad'}));
 assert.equal(root.children.length,0);
 surface.rebind(binding());
 assert.equal(await surface.activate(),true);
 assert.equal(root.querySelectorAll('.mnv-path').length,3);
 surface.dispose();surface.dispose();
 assert.equal(root.children.length,0);
 await assert.rejects(()=>surface.activate(),/unavailable/);
 console.log(JSON.stringify({passed:true,reads,stale_scope_refused:true,
    cross_subject_refused:true,midflight_switch_withdrawn:true,auto_reads:0}));
})().catch(error=>{console.error(error);process.exitCode=1;});
