"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("node:assert/strict");
const test=require("node:test"), path=require("node:path");
const sourcePath=path.resolve(__dirname,"../templates/intl_library_search.js");
const source=fs.readFileSync(sourcePath,"utf8");
// Synthetic permitted labels only; not a production rights/availability decision.
const examples=JSON.parse(fs.readFileSync(path.join(__dirname,"fixtures/intl_library_search_catalogue.json"),"utf8"));
const api=require(sourcePath); const {searchIntlTools:s,acceptIntlSearchReply:a}=api;
function invalid(fn,code){assert.throws(fn,e=>(e instanceof TypeError||e instanceof RangeError)&&e.code===code);}
const identity=()=>({principal_partition:"p",catalogue_generation:"c",query_generation:0,raw_query:"",group_id:null});
test("18 empty and returned closed fields",()=>{const r=s(examples,"");assert.equal(r.length,18);assert.deepEqual(r.map(x=>x.order),Array.from({length:18},(_,i)=>i));for(const x of r)assert.deepEqual(Object.keys(x).sort(),["matched_label","order","presentation_key"]);});
for(const g of new Set(examples.map(x=>x.group_id)))test("group and clear "+g,()=>{assert.equal(s(examples,"",g).length,3);assert.equal(s(examples," \t\n",g).length,3);});
test("unknown group",()=>assert.deepEqual(s(examples,"","absent"),[]));
test("fullwidth NFKC",()=>assert.deepEqual(s(examples,"ＣＲＥＤＩＴ").map(x=>x.presentation_key),s(examples,"credit").map(x=>x.presentation_key)));
test("Chinese alias",()=>assert.ok(s(examples,"供应链").some(x=>x.presentation_key==="trade_supply_links")));
const row=(key,label,order,alias=[])=>({presentation_key:key,group_id:"g",order,label_en:label,label_zh:"",question_en:"policy question",question_zh:"",aliases:alias});
const ranks=[row("prefix","Alpha extended",0),row("alias","Other",1,["alpha"]),row("exact","Alpha",10)];
test("exact prefix other order",()=>assert.deepEqual(s(ranks,"alpha").map(x=>x.presentation_key),["exact","prefix","alias"]));
test("all terms across fields",()=>assert.deepEqual(s(ranks,"alpha policy").map(x=>x.presentation_key),["prefix","alias","exact"]));
test("all terms excludes unmatched",()=>assert.deepEqual(s(ranks,"alpha nowhere"),[]));
test("declared order without mutating input order",()=>{const c=[row("later","A",2),row("first","B",1)];assert.deepEqual(s(c,"").map(x=>x.order),[1,2]);assert.equal(c[0].presentation_key,"later");});
test("nonmutation and metadata exclusion",()=>{const c=structuredClone(examples);c[0].private_metadata="SECRET_UNSEARCHABLE";const before=JSON.stringify(c);s(c,"");assert.deepEqual(s(c,"SECRET_UNSEARCHABLE"),[]);assert.equal(JSON.stringify(c),before);});
test("256 astral scalars",()=>assert.deepEqual(s(examples,"😀".repeat(256)),[]));
test("257 astral scalars",()=>invalid(()=>s(examples,"😀".repeat(257)),"INVALID_QUERY"));
for(const q of ["\ud800","\udc00","x\ud800y","\0","\u0001","\u007f","\u0080",null,undefined,5,{},true])test("invalid query "+JSON.stringify(q),()=>invalid(()=>s(examples,q),"INVALID_QUERY"));
test("composition null",()=>assert.equal(s(examples,"credit",null,{composing:true}),null));
test("composition validates invalid query",()=>invalid(()=>s(examples,"\0",null,{composing:true}),"INVALID_QUERY"));
test("duplicate keys",()=>invalid(()=>s([row("x","A",0),row("x","B",1)],""),"INVALID_CATALOGUE"));
test("duplicate orders",()=>invalid(()=>s([row("x","A",0),row("y","B",0)],""),"INVALID_CATALOGUE"));
for(const field of ["presentation_key","group_id","order","label_en","label_zh","question_en","question_zh","aliases"])test("missing catalogue "+field,()=>{const r=row("x","A",0);delete r[field];invalid(()=>s([r],""),"INVALID_CATALOGUE");});
test("inherited catalogue required field",()=>{const r=row("x","A",0);delete r.presentation_key;Object.setPrototypeOf(r,{presentation_key:"x"});invalid(()=>s([r],""),"INVALID_CATALOGUE");});
test("accessor catalogue field",()=>{let calls=0;const r=row("x","A",0);Object.defineProperty(r,"label_en",{get(){calls++;return "A";}});invalid(()=>s([r],""),"INVALID_CATALOGUE");assert.equal(calls,0);});
test("prototype-name keys",()=>assert.equal(s([row("__proto__","A",0),row("constructor","B",1)],"").length,2));
test("bad catalogue forms",()=>{for(const c of [null,{},true,"text"])invalid(()=>s(c,""),"INVALID_CATALOGUE");});
test("empty tool labels",()=>{const r=row("x","",0);invalid(()=>s([r],""),"INVALID_CATALOGUE");});
test("sparse aliases",()=>{const r=row("x","A",0);r.aliases=Array(1);invalid(()=>s([r],""),"INVALID_CATALOGUE");});
test("same identity",()=>assert.equal(a(identity(),identity()),true));
for(const k of Object.keys(identity())){
test("identity missing "+k,()=>{const r=identity();delete r[k];assert.equal(a(identity(),r),false);assert.equal(a(r,identity()),false);});
test("identity changed "+k,()=>{const r=identity();r[k]={principal_partition:"other",catalogue_generation:"other",query_generation:1,raw_query:" ",group_id:"g"}[k];assert.equal(a(identity(),r),false);});
test("identity accessor "+k,()=>{let calls=0;const r=identity();Object.defineProperty(r,k,{get(){calls++;return identity()[k];}});assert.equal(a(identity(),r),false);assert.equal(calls,0);});
test("identity inherited "+k,()=>{const r=identity();const value=r[k];delete r[k];Object.setPrototypeOf(r,{[k]:value});assert.equal(a(r,r),false);});
}
test("extra identity ordinary hidden symbol",()=>{for(const key of ["extra",Symbol("extra")]){const r=identity();Object.defineProperty(r,key,{value:1});assert.equal(a(r,r),false);}});
test("malformed identical identity",()=>{for(const [k,v] of [["principal_partition",""],["catalogue_generation",""],["query_generation",-1],["query_generation",1.5],["query_generation",Number.MAX_SAFE_INTEGER+1],["raw_query","\0"],["group_id",""]]){const r=identity();r[k]=v;assert.equal(a(r,r),false);}});
test("invalid identity forms never throw",()=>{for(const r of [null,[],true,"x",5])assert.equal(a(r,r),false);});
test("raw identity not normalized",()=>{const x=identity(),y=identity();x.raw_query="Ａ";y.raw_query="a";assert.equal(a(x,y),false);});
test("zero IO VM browser export",()=>{const sandbox={};for(const k of ["fetch","XMLHttpRequest","document","localStorage","sessionStorage","process"])Object.defineProperty(sandbox,k,{get(){throw Error("IO access "+k);}});sandbox.window=sandbox;vm.runInNewContext(source,sandbox);const b=sandbox.IntlLibrarySearch;assert.equal(typeof b.searchIntlTools,"function");assert.equal(b.searchIntlTools(examples,"").length,18);assert.equal(b.acceptIntlSearchReply(identity(),identity()),true);});
test("raw scalar bound before normalization expansion",()=>assert.deepEqual(s(examples,"ﬃ".repeat(256)),[]));
test("extra metadata getter never read",()=>{let calls=0;const r=row("x","A",0);Object.defineProperty(r,"private_metadata",{get(){calls++;throw Error("metadata read");}});assert.equal(s([r],"a").length,1);assert.equal(calls,0);});
test("frozen inputs remain usable",()=>{const r=row("x","A",0,["alias"]);Object.freeze(r.aliases);Object.freeze(r);assert.equal(s(Object.freeze([r]),"alias").length,1);});
test("throwing identity proxy fails closed",()=>{const r=new Proxy(identity(),{ownKeys(){throw Error("malformed proxy");}});assert.equal(a(r,r),false);});
test("Unicode whitespace term separator",()=>assert.ok(s(examples,"credit\u2028bonds").some(x=>x.presentation_key==="credit_bonds")));
test("Unicode whitespace empty query",()=>assert.equal(s(examples,"\u2028").length,18));
test("identity Symbol.toStringTag accessor fails closed without reads",()=>{let calls=0;const r=identity();Object.defineProperty(r,Symbol.toStringTag,{get(){calls++;throw Error("identity getter executed");}});assert.equal(a(r,r),false);assert.equal(calls,0);});


for (const q of ["", "credit"]) test("empty qualified catalogue: "+JSON.stringify(q),()=>assert.deepEqual(s([],q),[]));
test("empty catalogue composition holds",()=>assert.equal(s([],"",null,{composing:true}),null));
for(const ws of ["\r","\v","\f","\u2029","\ufeff","\u2003"]){
  const code=ws.codePointAt(0).toString(16);
  test("Unicode empty query U+"+code,()=>assert.equal(s(examples,ws).length,18));
  test("Unicode term separator U+"+code,()=>assert.ok(s(examples,"credit"+ws+"bonds").some(x=>x.presentation_key==="credit_bonds")));
}
test("revoked identity proxy",()=>{const x=Proxy.revocable(identity(),{});x.revoke();assert.equal(a(x.proxy,identity()),false);});
test("identity values come from descriptors without property gets",()=>{let gets=0;const x=new Proxy(identity(),{get(){gets++;throw Error("second get path");}});assert.equal(a(x,identity()),true);assert.equal(gets,0);});
for (const bad of [null, {}, [{}]]) test("malformed catalogue: "+JSON.stringify(bad),()=>invalid(()=>s(bad,""),"INVALID_CATALOGUE"));
