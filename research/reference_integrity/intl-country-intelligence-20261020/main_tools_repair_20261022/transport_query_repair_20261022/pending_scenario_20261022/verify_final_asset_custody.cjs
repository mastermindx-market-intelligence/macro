'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const Q=process.argv[2],P=__dirname,source=fs.readFileSync(path.join(Q,'verify_actual_parent.cjs'),'utf8');
const childOrigin='http://127.0.0.1:3102',asset='/shared_shell_bridge.js',expected={[asset]:'a'.repeat(64)};
function block(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);}
const evaluate=vm.runInNewContext(block('// BEGIN exact cached-response custody','// END exact cached-response custody')+'\n'+block('// BEGIN final captured-asset custody','// END final captured-asset custody')+'\nfinalChildAssetCustody',{URL,expected,childOrigin});
const url=childOrigin+asset+'?v=exact',date='Wed, 21 Oct 2026 12:00:00 GMT';
const prior={scope:'one-context',url,sequence:1,status:200,method:'GET',matches:true,sha256:expected[asset],last_modified:date,etag:null};
const late={scope:prior.scope,url,sequence:2,status:304,method:'GET',if_modified_since:date,if_none_match:null};
const cases=[
 ['valid200',[prior],1,0],
 ['late304_without_prior_matches_property',[prior,late],2,0],
 ['late_unbound304',[late],1,1],
 ['late_body_error_missing_matches',[prior,{...late,status:200,body_error:'closed before body'}],2,1],
 ['late200_missing_matches',[prior,{...prior,sequence:2,matches:undefined}],2,1],
 ['late_redirect_with_matching_hash',[prior,{...prior,sequence:2,status:302}],2,1],
 ['late304_wrong_scope',[prior,{...late,scope:'other-context'}],2,1],
 ['late304_wrong_validator',[prior,{...late,if_modified_since:'different'}],2,1],
 ['late304_wrong_exact_url',[prior,{...late,url:url+'&other=1'}],2,1],
 ['late200_wrong_body',[prior,{...prior,sequence:2,sha256:'b'.repeat(64)}],2,1],
 ['late200_non_GET',[prior,{...prior,sequence:2,method:'POST'}],2,1],
 ['nonasset_status_does_not_enter_population',[prior,{scope:'one-context',url:childOrigin+'/api/shared-shell/status',status:200}],1,0]
];
const results=cases.map(([name,input,n,b])=>{const r=evaluate(input.map(x=>({...x})));assert.equal(r.actual.length,n,name);assert.equal(r.bad.length,b,name);return{name,expected_responses:n,expected_bad:b,pass:true};});
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const receipt={schema:'intl.final_asset_custody_controls.v1',synthetic_controls:true,actual_browser_execution:false,recorded_at:new Date().toISOString(),driver_sha256:hash(source),control_sha256:hash(fs.readFileSync(__filename)),passed:results.length,failed:0,cases:results};
fs.writeFileSync(path.join(P,'final_custody_controls_receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
