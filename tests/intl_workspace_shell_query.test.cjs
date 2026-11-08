'use strict';
// Pure contract guard for the actual private URL projection. Full mount/popstate
// causality is separately qualified with the existing real-page fixture; no
// browser/provider or replacement reducer is used by this focused guard.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'templates/intl_workspace.js'),'utf8');
const start=source.indexOf('  function workspaceLocationQuery(window) {');
const end=source.indexOf('\n  function popstate(controller) {',start);
assert(start>=0&&end>start,'The actual owning consumer projection must exist');
const project=vm.runInNewContext(source.slice(start,end)+'\nworkspaceLocationQuery');
const reducer=require('../templates/intl_workspace_state.js').createIntlWorkspaceState({markets:['GB','EZ'],horizons:['1m','3m'],bases:['local','usd_unhedged'],default_horizon:'1m',default_basis:'usd_unhedged',source_reference:'synthetic:query-contract',anchor_ids:[],library_group_ids:[]});
const macro='view=macro&market=GB&pins=GB,EZ&horizon=3m&basis=local&return_basis=price&group=';
const frame='&mmx_shell=1&mmx_generation=fixture-generation';
const read=query=>project({location:{search:query}});
test('exact framed source metadata preserves canonical Macro/Risk business bytes',()=>{
 for(const query of [macro,macro.replace('view=macro&market=GB','view=risk&market=EZ').replace('horizon=3m&basis=local','horizon=1m&basis=usd_unhedged')]){
  assert.equal(read('?'+query+frame),'?'+query);
  assert.equal(reducer.parseQuery(read('?'+query+frame)).ok,true);
 }
 assert.equal(read('?'+macro+'&mmx%5Fshell=1&mmx_generation=fixture-generation'),'?'+macro);
 assert.equal(read('?'+macro.replace('GB,EZ','GB%2CEZ')+frame),'?'+macro.replace('GB,EZ','GB%2CEZ'));
});
test('unknown/duplicate user fields remain invalid and plain reducer stays strict',()=>{
 for(const query of [macro+'&unknown_business=1'+frame,macro+'&view=risk'+frame,macro+frame+'&bad=%ZZ',macro.replace('GB,EZ','GB%2CEZ')+frame])assert.equal(reducer.parseQuery(read('?'+query)).ok,false);
 assert.equal(reducer.parseQuery('?'+macro+frame).ok,false);
 assert.equal(reducer.parseQuery('?'+macro).ok,true);
});
test('malformed, missing or duplicate reserved pairs are not projected',()=>{
 for(const extra of ['', '&mmx_shell=1','&mmx_generation=fixture-generation','&mmx_shell=0&mmx_generation=fixture-generation','&mmx_shell=1&mmx_generation=','&mmx_shell=1&mmx_generation=bad%2Fgeneration','&mmx_shell=1&mmx_shell=1&mmx_generation=fixture-generation','&mmx_shell=1&mmx_generation=a&mmx_generation=b','&mmx_shell=1&mmx_generation=%ZZ']){
  const raw='?'+macro+extra;assert.equal(read(raw),raw);
 }
 for(const raw of ['?'+macro+frame+'&mmx_shell=0','?'+macro+frame+'&mmx_generation=x','?'+macro+'&mmx_shell=1&mmx_generation='+'a'.repeat(129),'?'+'x'.repeat(2305),'?'+Array(19).fill('x=1').join('&')])assert.equal(read(raw),raw);
});
