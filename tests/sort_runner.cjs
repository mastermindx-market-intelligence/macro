'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
function fakeClasses(initial='') {
  const set = new Set(initial.split(/\s+/).filter(Boolean));
  return {add: v=>set.add(v), remove:v=>set.delete(v), contains:v=>set.has(v)};
}
function runContract(spec) {
  const rows = spec.rows.map(r=>({dataset:r, identity:r.ticker}));
  const originalRows = rows.slice();
  const fingerprint = rows.map(r=>JSON.stringify(r.dataset)).sort().join('\n');
  const headers = spec.headers.map(col=>({col,classList:fakeClasses('sortable'),indicator:{textContent:'↕'},querySelector(){return this.indicator;}}));
  const tbody = {querySelectorAll:()=>rows.slice(),appendChild(r){rows.splice(rows.indexOf(r),1);rows.push(r);}};
  const document = {
    getElementById:id=>id==='fd-book-body'?tbody:null,
    querySelectorAll:selector=>selector==='#fd-book th'?headers:[],
    querySelector:selector=>headers.find(h=>selector===`#fd-book th[data-col="${h.col}"]`)||null
  };
  const context={document,window:{}}; vm.createContext(context);vm.runInContext(payload.sortScript,context);
  return {sort:col=>context.window.fdSort(col),order:()=>rows.map(r=>r.identity),indicator:col=>headers.find(h=>h.col===col).indicator.textContent,selected:()=>headers.filter(h=>h.classList.contains('sorted')).map(h=>h.col),intact:()=>rows.every(r=>originalRows.includes(r))&&rows.map(r=>JSON.stringify(r.dataset)).sort().join('\n')===fingerprint,close(){}};
}
function runDom(spec){
  const {JSDOM, VirtualConsole}=require(process.env.JSDOM_MODULE);
  const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(e.type!=='css parsing')errors.push(e.message);});
  const dom=new JSDOM(spec.html,{runScripts:'dangerously',url:'https://fixture.test/fund_test.html',virtualConsole:vc});
  const d=dom.window.document;
  if(errors.length)throw new Error(errors.join('\n'));
  const originalRows=[...d.querySelectorAll('#fd-book-body tr')];
  const fingerprint=originalRows.map(r=>r.outerHTML).sort().join('\n');
  return {sort:col=>d.querySelector(`#fd-book th[data-col="${col}"]`).click(),order:()=>[...d.querySelectorAll('#fd-book-body tr')].map(r=>r.dataset.ticker),indicator:col=>d.querySelector(`#fd-book th[data-col="${col}"] .sort-ind`).textContent,selected:()=>[...d.querySelectorAll('#fd-book th.sorted')].map(h=>h.dataset.col),intact:()=>{const rows=[...d.querySelectorAll('#fd-book-body tr')];return rows.every(r=>originalRows.includes(r))&&rows.map(r=>r.outerHTML).sort().join('\n')===fingerprint;},close:()=>dom.window.close()};
}
const results=[];
for(const spec of payload.cases){
  const doc=process.env.JSDOM_MODULE?runDom(spec):runContract(spec);
  for(const step of spec.steps){doc.sort(step.col);results.push({id:step.id,actual:doc.order(),expected:step.expected,indicator:doc.indicator(step.col),expectedIndicator:step.indicator,selected:doc.selected(),col:step.col,intact:doc.intact()});}
  doc.close();
}
process.stdout.write(JSON.stringify(results));
