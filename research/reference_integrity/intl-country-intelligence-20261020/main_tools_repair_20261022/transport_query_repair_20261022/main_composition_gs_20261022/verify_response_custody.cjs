'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root="/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022",out="/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_gs_20261022";
const raw=fs.readFileSync(path.join(root,'verify_actual_parent.cjs'),'utf8');
const start=raw.indexOf('// BEGIN exact cached-response custody'),end=raw.indexOf('// END exact cached-response custody',start);
assert(start>=0&&end>start);
const childOrigin='http://127.0.0.1:3102',asset='/shared_shell_bridge.js';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const expected={[asset]:hash(fs.readFileSync(path.join(root,'proposed_shellquery20261022_repair',asset)))};
const qualify=vm.runInNewContext(raw.slice(start,end)+'\ncachedResponseEvidence',{URL,expected,childOrigin});
const url=childOrigin+asset+'?v=24d7bb10',stamp='Wed, 21 Oct 2026 12:00:00 GMT';
const prior={scope:'synthetic-custody-controls',url,sequence:1,status:200,method:'GET',matches:true,sha256:expected[asset],last_modified:stamp,etag:null};
const row={scope:prior.scope,url,sequence:2,status:304,method:'GET',if_modified_since:stamp,if_none_match:null};
const cases=[
 ['matching_last_modified',{}, {},true],
 ['matching_etag',{if_none_match:'"approved-body"'},{etag:'"approved-body"'},true],
 ['etag_precedence_over_date',{if_none_match:'"approved-body"',if_modified_since:'different-date'},{etag:'"approved-body"'},true],
 ['no_prior_response',{},null,false],
 ['different_scope',{scope:'different-context'},{},false],
 ['different_exact_query',{url:url+'&other=1'},{},false],
 ['different_origin',{url:'http://127.0.0.1:3999'+asset+'?v=24d7bb10'},{},false],
 ['wrong_body_hash',{}, {sha256:'0'.repeat(64)},false],
 ['unmatched_prior',{}, {matches:false},false],
 ['prior_has_body_error',{}, {body_error:'unavailable'},false],
 ['missing_validator',{if_modified_since:null},{},false],
 ['different_modified_since',{if_modified_since:'Thu, 22 Oct 2026 12:00:00 GMT'},{},false],
 ['bad_etag_cannot_use_matching_date',{if_none_match:'"wrong"'},{etag:'"approved-body"'},false],
 ['redirect_is_not_revalidation',{status:302},{},false],
 ['non_get_revalidation',{method:'POST'},{},false],
 ['non_get_prior',{}, {method:'POST'},false],
 ['future_prior',{}, {sequence:3},false],
 ['missing_prior_sequence',{}, {sequence:undefined},false],
 ['missing_revalidation_sequence',{sequence:undefined},{},false],
 ['only_prior_304',{}, {status:304},false],
 ['failed_header_capture',{body_error:'header capture failed'},{},false],
 ['prior_validator_absent',{}, {last_modified:null},false]
];
const results=cases.map(([name,changeRow,changePrior,want])=>{
 const actual=qualify({...row,...changeRow},changePrior===null?[]:[{...prior,...changePrior}]);
 assert.equal(!!actual,want,name);
 if(actual){assert.equal(actual.cached_sha256,expected[asset],name);assert.equal(actual.prior_sequence,1,name);}
 return {name,expected_qualified:want,qualified:!!actual,pass:true};
});
const receipt={schema:'intl.response_custody_controls.v1',recorded_at:new Date().toISOString(),synthetic_controls:true,actual_browser_execution:false,driver_sha256:hash(Buffer.from(raw)),control_sha256:hash(fs.readFileSync(__filename)),cases:results,passed:results.length,failed:0};
fs.writeFileSync(path.join(out,'response_custody_controls_receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({passed:results.length,failed:0,driver_sha256:receipt.driver_sha256}));
