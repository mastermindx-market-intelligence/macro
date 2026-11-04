import assert from 'node:assert/strict';
import { readFileSync,writeFileSync } from 'node:fs';
import { dirname,resolve } from 'node:path';
import { fileURLToPath,pathToFileURL } from 'node:url';

// Executable design witnesses. These functions are test oracles, NOT runtime
// payloads, stores, routes, or evidence that the proposed UI is implemented.
const here=dirname(fileURLToPath(import.meta.url)),src=process.env.D08A_SOURCE_ROOT||resolve(here,'../../source');
const {contractIdentity}=await import(pathToFileURL(resolve(src,'terminal/terminal/lib/optionsContractShortlist.ts')).href);
const report={kind:'D08A_PROPOSED_DESIGN_WITNESSES_NOT_PRODUCT_TESTS',executedAt:new Date().toISOString(),tests:[]};
function test(id,description,fn){try{fn();report.tests.push({id,description,status:'PASS'});}catch(e){report.tests.push({id,description,status:'FAIL',error:e.message});}}
const realDate=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v;
function sameDayWitness(row,session){return realDate(session)&&realDate(row.exp)&&row.zerodte===true&&row.exp===session;}
function cutoffWitness(availableAt,cutoff){return typeof availableAt==='string'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(availableAt)&&Number.isFinite(Date.parse(availableAt))&&Date.parse(availableAt)<=cutoff;}
function qualifyWitness(origin,receiver){
 const copied=structuredClone(origin);
 if(receiver.access!=='allowed')return{state:receiver.access,origin:copied};
 if(!receiver.listingBindingVerified)return{state:'identity_ambiguous',origin:copied};
 if(!origin.ownerRecordId||!contractIdentity(origin.contract).ok)return{state:'root_only',origin:copied};
 if(!receiver.book)return{state:'missing_book',origin:copied};
 if(receiver.cutoff!=null&&!cutoffWitness(receiver.book.availableAt,receiver.cutoff))return{state:'later_or_unknown_book',origin:copied};
 return{state:'contract_context',origin:copied,book:structuredClone(receiver.book)};
}
const origin={family:'flow',sourceKey:'fixture/feed',ownerRecordId:'fixture:e1',sourceSession:'2026-10-30',sourceDigest:'original',grain:'coalesced_contract_event',n_prints:3,eventAt:'2026-10-30T19:59:00Z',listing:{sourceNamespace:'fixture.options',exactRoot:'NVDA'},contract:{root:'NVDA',exp:'2026-11-20',strike:210,right:'C'}};
const receiver={access:'allowed',listingBindingVerified:true,book:{sourceKey:'fixture/book',availableAt:'2026-10-30T19:58:00Z',sourceSession:'2026-10-30'},cutoff:Date.parse(origin.eventAt)};
test('D01','Exact qualified transfer keeps original aggregate grain and independent book',()=>{const x=qualifyWitness(origin,receiver);assert.equal(x.state,'contract_context');assert.deepEqual(x.origin,origin);assert.equal(x.origin.n_prints,3);assert.notEqual(x.book.sourceKey,x.origin.sourceKey);});
test('D02','Missing record ID cannot be supplied by the receiver book',()=>{const x=qualifyWitness({...origin,ownerRecordId:null},receiver);assert.equal(x.state,'root_only');assert.equal(x.origin.ownerRecordId,null);});
test('D03','Incomplete contract remains root context, never repaired from later book',()=>{const x=qualifyWitness({...origin,contract:{root:'NVDA'}},receiver);assert.equal(x.state,'root_only');assert.equal(x.origin.contract.exp,undefined);});
test('D04','Unverified listing mapping refuses automatic ticker join',()=>assert.equal(qualifyWitness(origin,{...receiver,listingBindingVerified:false}).state,'identity_ambiguous'));
test('D05','Missing dated book returns reason and intact origin',()=>{const x=qualifyWitness(origin,{...receiver,book:null});assert.equal(x.state,'missing_book');assert.deepEqual(x.origin,origin);});
test('D06','Later book cannot be presented as available at observation cutoff',()=>assert.equal(qualifyWitness(origin,{...receiver,book:{...receiver.book,availableAt:'2026-10-30T20:00:00Z'}}).state,'later_or_unknown_book'));
test('D07','Unknown availability is not supplied by build/retrieval clocks',()=>assert.equal(qualifyWitness(origin,{...receiver,book:{builtAt:'2026-10-30T19:00:00Z',retrievedAt:'2026-10-30T20:00:00Z'}}).state,'later_or_unknown_book'));
test('D08','Denied and unverified access remain different declines',()=>{assert.equal(qualifyWitness(origin,{...receiver,access:'denied'}).state,'denied');assert.equal(qualifyWitness(origin,{...receiver,access:'unverified'}).state,'unverified');});
test('D09','0DTE is source-session based across UTC day boundaries',()=>{assert(sameDayWitness({exp:'2026-10-30',zerodte:true},'2026-10-30'));assert(!sameDayWitness({exp:'2026-10-30',zerodte:true},'2026-10-31'));});
test('D10','Impossible expiry and flag/date mismatch do not qualify0DTE',()=>{assert(!sameDayWitness({exp:'2026-02-30',zerodte:true},'2026-02-30'));assert(!sameDayWitness({exp:'2026-11-20',zerodte:true},'2026-10-30'));assert(!sameDayWitness({exp:'2026-10-30',zerodte:false},'2026-10-30'));});
test('D11','Daylight-saving duplicate local clocks need explicit offsets',()=>{assert(!cutoffWitness('2026-11-01T01:30:00',Date.parse('2026-11-01T06:00:00Z')));assert(cutoffWitness('2026-11-01T01:30:00-04:00',Date.parse('2026-11-01T06:00:00Z')));assert(!cutoffWitness('2026-11-01T01:30:00-05:00',Date.parse('2026-11-01T06:00:00Z')));});
const generation={principal:'fixture-user',epoch:4,view:'tape',root:'NVDA',source:'feed',session:'2026-10-30'};
function mayApply(a,b,allowed){return allowed&&Object.keys(generation).every(k=>a[k]===b[k]);}
test('D12','Late prior-root response cannot populate current root',()=>assert(!mayApply(generation,{...generation,root:'SPY'},true)));
test('D13','Access revocation rejects a late successful response',()=>{assert(!mayApply(generation,generation,false));assert(!mayApply({...generation,epoch:5},generation,true));});
test('D14','Different principal,source,session or view invalidates cached response',()=>{for(const k of ['principal','source','session','view'])assert(!mayApply(generation,{...generation,[k]:'other'},true));});
function returnWitness(ref,rows,access){
 if(access!=='allowed')return{state:'access',focus:'scan-heading',selected:null};
 const hit=rows.filter(x=>x.sourceKey===ref.sourceKey&&x.ownerRecordId===ref.ownerRecordId&&x.sourceSession===ref.sourceSession);
 if(hit.length!==1)return{state:hit.length?'ambiguous':'outside_window',focus:'scan-heading',selected:null};
 if(ref.sourceDigest&&hit[0].sourceDigest!==ref.sourceDigest)return{state:'corrected',focus:'scan-heading',selected:null};
 return{state:ref.sourceDigest?'exact_reference':'reference_only',focus:'original-row-action',selected:ref.ownerRecordId};
}
test('D15','Row reorder preserves exact selected reference',()=>assert.equal(returnWitness(origin,[{...origin,ownerRecordId:'other'},origin],'allowed').selected,'fixture:e1'));
test('D16','Expired row does not select nearest time/lookalike',()=>{const x=returnWitness(origin,[{...origin,ownerRecordId:'other'}],'allowed');assert.equal(x.state,'outside_window');assert.equal(x.selected,null);assert.equal(x.focus,'scan-heading');});
test('D17','Duplicate reference returns ambiguity, not first match',()=>assert.equal(returnWitness(origin,[origin,{...origin}],'allowed').state,'ambiguous'));
test('D18','Same URL/session with changed digest is a correction, not original bytes',()=>assert.equal(returnWitness(origin,[{...origin,sourceDigest:'new'}],'allowed').state,'corrected'));
test('D19','No digest means reference restoration, not original-byte proof',()=>assert.equal(returnWitness({...origin,sourceDigest:null},[origin],'allowed').state,'reference_only'));
test('D20','Revoked access clears protected selection on return',()=>assert.equal(returnWitness(origin,[origin],'denied').selected,null));
function safeReturn(raw){try{const u=new URL(raw);return u.origin==='https://beta.mastermind-x.com'&&!u.username&&!u.password&&['/options','/options.html'].includes(u.pathname);}catch{return false;}}
test('D21','Return rejects external,credential-bearing and script URLs',()=>{assert(safeReturn('https://beta.mastermind-x.com/options?tab=tape'));assert(!safeReturn('https://evil.example/options'));assert(!safeReturn('https://user:pass@beta.mastermind-x.com/options'));assert(!safeReturn('javascript:alert(1)'));});
test('D22','Origin history merge preserves incumbent host state',()=>{const old={host:{reader:'existing'},other:2};const next={...old,d08Return:{view:'tape',selectedRow:'safe-reference'}};assert.deepEqual(next.host,old.host);assert.equal(next.other,2);assert.equal(old.d08Return,undefined);});
function geometry(w,compact=false,extra=0,minimum=640){const rail=w<=860?0:compact?72:w<1200?196:224,gutter=w<=600?16:w<1200?20:24,C=w-rail-2*gutter-extra;return{C,dock:C-344>=minimum};}
test('D23','Candidate default dock boundary1255/1256 is exact',()=>{assert(!geometry(1255).dock);assert(geometry(1256).dock);});
test('D24','Candidate compact boundary1095/1096 and explicit preference remain distinct',()=>{assert(!geometry(1095,true).dock);assert(geometry(1096,true).dock);assert(!geometry(1096,false).dock);});
test('D25','Additional chrome/larger domain minimum can refuse otherwise-wide dock',()=>{assert(!geometry(1440,false,200).dock);assert(!geometry(1440,false,0,900).dock);});
test('D26','Fractional content rules and narrow widths use actual usable width',()=>{assert.equal(geometry(390).C,358);assert.equal(geometry(600.5).C,560.5);assert.equal(geometry(860.5).C,624.5);assert.equal(geometry(1024).C,788);});
function mutationWitness(status){return status==='readback_confirmed'?'saved':status==='unknown'?'reconcile_same_operation':status==='not_admitted'?'draft_only':status==='rejected'?'failed':'pending';}
test('D27','Saved requires readback; uncertain effect never creates a new operation',()=>{assert.equal(mutationWitness('accepted'),'pending');assert.equal(mutationWitness('unknown'),'reconcile_same_operation');assert.equal(mutationWitness('not_admitted'),'draft_only');assert.equal(mutationWitness('readback_confirmed'),'saved');});
report.summary={total:report.tests.length,passed:report.tests.filter(x=>x.status==='PASS').length,failed:report.tests.filter(x=>x.status==='FAIL').length};
writeFileSync(resolve(here,'../evidence/design-witness-results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report.summary));process.exitCode=report.summary.failed?1:0;

