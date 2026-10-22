const test = require('node:test');
const assert = require('node:assert/strict');
const Nav = require(process.env.ALL_TOOLS_SOURCE || '../src/all-tools.js');
const base = 'https://www.mastermind-x.com/sectors/semiconductors.html';
const row = (more={}) => ({href:'../sector_central.html#confluence',en:'Subsector Confluence',zh:'子行业汇聚',descriptionEn:'Where independent signals agree',descriptionZh:'独立信号汇聚',group:'United States',groupZh:'美国',enabled:true,...more});
const snapshot = (rows) => Nav.project(rows,{baseURI:base});

test('uses source destinations rather than a hardcoded product catalog',()=>{
 const v=snapshot([row(),row({href:'../new_desk.html',en:'New desk',zh:'新工作台'})]);
 assert.equal(v.length,2);assert.ok(v.some(x=>x.href.endsWith('/new_desk.html')));
});
test('preserves deep prefix and meaningful fragment',()=>assert.equal(snapshot([row()])[0].href,'https://www.mastermind-x.com/sector_central.html#confluence'));
test('distinct fragments remain distinct tasks',()=>assert.equal(snapshot([row(),row({href:'../sector_central.html#si-explore'})]).length,2));
test('deduplicates exact targets without conflating different regional pages',()=>assert.equal(snapshot([row(),row(),row({href:'../sector_central_china.html#confluence',group:'China',groupZh:'中国'})]).length,2));
test('server-disabled entries never get invented back into the menu',()=>assert.equal(snapshot([row({enabled:false})]).length,0));
test('blank labels and malformed records are omitted',()=>assert.equal(snapshot([row({en:' ',zh:''}),null,{}]).length,0));
for(const href of ['javascript:alert(1)','data:text/html,x','file:///etc/passwd','https://evil.invalid/tool','https://user:pass@www.mastermind-x.com/a.html','//evil.invalid','../a.html\n','https://app.mastermind-x.com.evil.invalid']){
 test('rejects unsafe href '+JSON.stringify(href),()=>assert.equal(snapshot([row({href})]).length,0));
}
test('retains approved cross-product target semantics and isolation',()=>{
 const d=snapshot([row({href:'https://bot.mastermind-x.com',target:'_blank',rel:'noopener',badge:'PRO'})])[0];
 assert.equal(d.target,'_blank');assert.match(d.rel,/noopener/);assert.equal(d.badge,'PRO');
});
test('same-site links do not acquire forced new-tab behavior',()=>assert.equal(snapshot([row()])[0].target,''));
test('snapshot cannot be changed by later provider-object mutation',()=>{const r=row();const v=snapshot([r]);r.en='Other';assert.equal(v[0].en,'Subsector Confluence');assert.ok(Object.isFrozen(v)&&Object.isFrozen(v[0]));});
test('search spans every category and both languages',()=>{const v=snapshot([row(),row({href:'../bonds.html',en:'Bonds',zh:'债券',group:'Other assets'})]);assert.equal(Nav.select(v,{group:'United States',query:'债券'}).length,1);});
test('query text is inert and not an instruction or HTML',()=>assert.equal(Nav.select(snapshot([row()]),{query:'<img src=x onerror=alert(1)>'}).length,0));
test('normalizes unicode, spacing and case without changing destinations',()=>{const v=snapshot([row({en:'Market Dashboard'})]);assert.equal(Nav.select(v,{query:'ＭＡＲＫＥＴ   dashboard'}).length,1);});
test('empty query selects only the chosen scope',()=>{const v=snapshot([row(),row({href:'../bonds.html',en:'Bonds',group:'Other assets'})]);assert.equal(Nav.select(v,{group:'United States'}).length,1);});
test('initial selection balances available owner groups instead of deleting deeper items',()=>{const v=snapshot(Array.from({length:18},(_,i)=>row({href:'../d'+i+'.html',group:i<12?'United States':'Research'})));const first=Nav.startingPoints(v,8);assert.equal(first.length,8);assert.ok(first.some(x=>x.group==='Research'));assert.equal(v.length,18);});
test('source refresh must not rewrite the selected destination identity',()=>assert.equal(Nav.sameDestination(row(),row({href:'../china.html'}),base),false));
test('same canonical URL survives a relative spelling change',()=>assert.equal(Nav.sameDestination(row(),row({href:'https://www.mastermind-x.com/sector_central.html#confluence'}),base),true));

// R39: a displayed source topic must be discoverable without knowing tool names.
test('topic search includes the source-authored English section heading',()=>{
 const v=snapshot([row({section:'Capital & regimes',sectionZh:'资本与周期'})]);
 assert.deepEqual(Nav.select(v,{query:'capital regimes'}),v);
});
test('topic search includes the Chinese section heading and normalizes width',()=>{
 const v=snapshot([row({section:'Find the edge',sectionZh:'寻找优势'})]);
 assert.deepEqual(Nav.select(v,{query:'寻找优势'}),v);
 assert.deepEqual(Nav.select(v,{query:'ＦＩＮＤ   edge'}),v);
});
test('all query terms can span a tool name and its source topic',()=>{
 const v=snapshot([row({en:'Smart Money',zh:'聪明资金',section:'Capital & regimes',sectionZh:'资本与周期'})]);
 assert.deepEqual(Nav.select(v,{query:'money regimes'}),v);
 assert.equal(Nav.select(v,{query:'money regimes impossible'}).length,0);
});
test('topic search remains global while leaving the selected market untouched',()=>{
 const v=snapshot([row({section:'Market overview'}),row({href:'../cycles.html',group:'Research',section:'Global cycles',sectionZh:'全球周期'})]);
 assert.deepEqual(Nav.select(v,{group:'United States',query:'global cycles'}).map(item=>item.group),['Research']);
 assert.equal(Nav.select(v,{group:'United States',query:''})[0].group,'United States');
});
test('long bilingual labels cannot truncate the later section search field',()=>{
 const v=snapshot([row({en:'A'.repeat(400),zh:'乙'.repeat(400),descriptionEn:'C'.repeat(400),descriptionZh:'丁'.repeat(400),section:'Capital & regimes',sectionZh:'资本与周期'})]);
 assert.deepEqual(Nav.select(v,{query:'资本与周期'}),v);
 assert.deepEqual(Nav.select(v,{query:'capital'}),v);
});
test('topic matching does not reintroduce withdrawn or untrusted destinations',()=>{
 const v=snapshot([row({section:'Capital',enabled:false}),row({section:'Capital',href:'https://evil.invalid/tool'})]);
 assert.equal(Nav.select(v,{query:'capital'}).length,0);
});
test('topic search does not index hrefs, tier badges or absent headings',()=>{
 const v=snapshot([row({href:'../private_route_name.html',badge:'PRO'})]);
 assert.equal(Nav.select(v,{query:'private_route_name'}).length,0);
 assert.equal(Nav.select(v,{query:'PRO'}).length,0);
 assert.equal(Nav.select(v,{query:'capital regimes'}).length,0);
});
