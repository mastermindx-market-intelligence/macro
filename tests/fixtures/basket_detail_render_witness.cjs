'use strict';
// Controlled source-render witness only. No browser, network, layout or native-focus proof.
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(process.argv[2],'utf8');
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const source=scripts.find(x=>x.includes('const DETAIL = '));
if(!source)throw Error('Missing incumbent detail script');
const attrs={'data-lang':'en','data-theme':'dark'},fetches=[];
const element=()=>({innerHTML:'',style:{},dataset:{},querySelector:()=>null,querySelectorAll:()=>[],setAttribute(){},getAttribute:()=>null,addEventListener(){},focus(){},remove(){},appendChild(){},insertBefore(){},prepend(x){this.innerHTML=x.innerHTML+this.innerHTML;}});
const app=element(),root=element();root.getAttribute=k=>attrs[k]||null;root.setAttribute=(k,v)=>attrs[k]=v;
const document={readyState:'loading',documentElement:root,activeElement:null,getElementById:id=>id==='app'?app:null,querySelectorAll:()=>[],querySelector:()=>null,createElement:element,addEventListener(){}};
const context={document,console,URL,Date,Math,JSON,Set,Map,Intl,encodeURIComponent,decodeURIComponent,getComputedStyle:()=>({getPropertyValue:()=> '#888'}),fetch:async url=>{fetches.push(url);return{ok:false,json:async()=>null};},setTimeout:()=>0,clearTimeout(){},setInterval:()=>0,clearInterval(){},requestAnimationFrame:()=>0,localStorage:{getItem:()=>null,setItem(){}},location:{href:'https://controlled.invalid/basket_canada/ca_asset_mgrs.html'}};
context.window=context;context.addEventListener=()=>{};
vm.createContext(context);vm.runInContext(source,context,{timeout:3000});
const cells={};
for(const lang of ['en','zh']){
 attrs['data-lang']=lang;vm.runInContext('render()',context,{timeout:3000});
 cells[lang]=app.innerHTML;
}
fs.writeFileSync(process.argv[3],JSON.stringify({scope:'Incumbent emitted JavaScript in Node VM; minimal string DOM; all fetches return unavailable locally; no browser or network',cells,blocked_optional_fetches:fetches},null,2)+'\n');
