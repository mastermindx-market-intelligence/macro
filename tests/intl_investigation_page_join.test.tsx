// @vitest-environment jsdom
// Source/controlled DOM only: real Jinja -> controller -> incumbent bridge ->
// exact Terminal selectors -> explicit native preflight -> exact Return.
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {join,resolve,dirname} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import InvestigationWorkspace from '@/components/workspaces/InvestigationWorkspace';
import {parseAnalysisRoute} from '@/lib/analysisRoute';
import {GET as baselineGET} from '@/app/api/investigations/baseline/route';
import {GET as reviewGET} from '@/app/api/investigations/review/route';
const boot=vi.hoisted(()=>({closed:false}));
vi.mock('@/lib/investigationBootAdmission',()=>({readInvestigationBootAdmission:()=>true,hasObservedInvestigationClosure:()=>boot.closed,observeInvestigationClosure:()=>{boot.closed=true;}}));
const owners=vi.hoisted(()=>({user:vi.fn(),rpc:vi.fn(),principal:'90000000-0000-4000-8000-000000000009'}));
vi.mock('@/lib/supabase/server',()=>({createClient:async()=>({auth:{getUser:owners.user,getSession:async()=>({data:{session:{access_token:'synthetic-fixture-only'}},error:null})},rpc:owners.rpc})}));
vi.mock('@/lib/rateLimit',()=>({rateLimit:()=>({ok:true})}));
vi.mock('@/lib/i18n',()=>({useLang:()=>({lang:'en'})}));
vi.mock('@/lib/useInvestigationTheme',()=>({useInvestigationTheme:()=> 'dark'}));
vi.mock('next/link',()=>({default:({children,href}:React.PropsWithChildren<{href:string}>)=><a href={href}>{children}</a>}));
vi.mock('@/lib/supabase/investigationAuthOwner',()=>({subscribeInvestigationAuthOwner:()=>({getSnapshot:()=>({availability:'ready',principal_partition:owners.principal,auth_epoch:'synthetic-private-epoch'}),unsubscribe:vi.fn()})}));
const macro=resolve(__dirname,'..');
const require=createRequire(join(process.env.INTL_TERMINAL_SOURCE_ROOT!,'package.json'));
const {JSDOM}=require('jsdom');
const payload=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-m','tests.intl_investigation_page_fixture'],{cwd:macro,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},maxBuffer:4e6}));
const bridgePath=join(macro,'tests/js/shared_shell_bridge.test.cjs');
const existingHarness=readFileSync(bridgePath,'utf8');
const capsule={exports:{} as {harness:(o?:unknown)=>any}};
vm.runInNewContext(existingHarness.slice(0,existingHarness.indexOf('\ntest('))+'\nmodule.exports={harness};',
 {require:createRequire(bridgePath),__dirname:dirname(bridgePath),module:capsule,URL,URLSearchParams,setTimeout,clearTimeout,CustomEvent,console});
function page(view='macro',bridge=true,admitted=true){
 const query=`view=${view}&market=JP&pins=GB,EZ&horizon=1m&basis=usd_unhedged&return_basis=price&group=`;
 const dom=new JSDOM('<!doctype html><html lang="en"><body>'+payload.html+'</body></html>',{url:'https://www.mastermind-x.com/intl.html?'+query,runScripts:'outside-only'});
 const w=dom.window;
 for(const name of ['intl_workspace_state.js','intl_workspace.js'])w.eval(readFileSync(join(macro,'templates',name),'utf8'));
 const root=w.document.querySelector('[data-im-workspace]');
 const handle=w.IntlWorkspace.mountIntlWorkspace(root,w.JSON.parse(root.querySelector('[data-im-config]').textContent));
 const actual=capsule.exports.harness({childUrl:'https://www.mastermind-x.com/intl.html?mmx_shell=1&mmx_generation=g1',referrer:'https://beta.mastermind-x.com/shell'});
 actual.activate({canonicalPath:'/intl.html',catalog:{legacyPaths:['/intl.html'],nativePaths:admitted?['/analysis']:[]}});
 expect(actual.api().active).toBe(true);
 if(bridge)w.MMXSharedShell=actual.api();
 const field=view==='risk'?'EZ.annual_current_account':'GB.policy_rate';
 const link=root.querySelector(`[data-im-panel][data-view="${view}"][data-horizon="1m"][data-basis="usd_unhedged"] [data-im-investigation-field="${field}"]`) as HTMLAnchorElement;
 expect(link).not.toBeNull(); expect(link.hidden).toBe(false);
 return {dom,w,root,handle,actual,link,query,close(){handle.destroy();dom.window.close();}};
}
function activate(p:ReturnType<typeof page>){const e=new p.w.MouseEvent('click',{bubbles:true,cancelable:true,button:0});p.link.dispatchEvent(e);return e;}
beforeEach(()=>{boot.closed=false;vi.stubEnv('INVESTIGATION_API_ADMISSION','open');owners.user.mockResolvedValue({data:{user:{id:owners.principal}},error:null});owners.rpc.mockResolvedValue({data:{status:'listed',items:[]},error:null});});
afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();vi.clearAllMocks();});

it.each(['macro','risk'])('real %s Jinja anchor uses live Return, exact references and current-parent admitted bridge',view=>{
 const p=page(view);try{
  const before=new URL(p.link.getAttribute('data-im-investigation-href')!,'https://app.mastermind-x.com');
  expect(activate(p).defaultPrevented).toBe(true);
  const nav=p.actual.lastOf('NAVIGATE');expect(nav).not.toBeNull();
  expect(nav.href.startsWith('https://www.mastermind-x.com/analysis?')).toBe(true); // incumbent bridge canonical child representation, parent owns replacement
  const url=new URL(nav.href);for(const name of ['intl_context','intl_generation','intl_fingerprint','intl_field'])expect(url.searchParams.getAll(name)).toEqual(before.searchParams.getAll(name));
  const route=parseAnalysisRoute(Object.fromEntries(url.searchParams));expect(route.kind).toBe('investigations');
  if(route.kind!=='investigations')throw Error('strict route refused');
  expect(route.intlReturnTo).toBe('https://www.mastermind-x.com/intl.html?'+p.query);
  expect(route.intlEntry?.fields).toEqual([view==='risk'?'EZ.annual_current_account':'GB.policy_rate']);
  p.handle.dispatch(p.w.JSON.parse(JSON.stringify({type:'pin',market_id:'JP'})));p.handle.dispatch(p.w.JSON.parse(JSON.stringify({type:'select_market',market_id:null}))); activate(p);
  const returned=new URL(p.actual.lastOf('NAVIGATE').href).searchParams.get('intl_return')!;
  expect(new URL(returned).searchParams.get('market')).toBe('');expect(new URL(returned).searchParams.get('pins')).toBe('GB,EZ,JP');
  p.handle.dispatch(p.w.JSON.parse(JSON.stringify({type:'set_horizon',horizon:'3m'})));
  p.handle.dispatch(p.w.JSON.parse(JSON.stringify({type:'set_basis',currency_basis:'local'})));
  const next=p.root.querySelector(`[data-im-panel][data-view="${view}"][data-horizon="3m"][data-basis="local"] [data-im-investigate]`);
  const original=new URL(next.getAttribute('data-im-investigation-href'),'https://app.mastermind-x.com');
  next.dispatchEvent(new p.w.MouseEvent('click',{bubbles:true,cancelable:true}));
  const moved=new URL(p.actual.lastOf('NAVIGATE').href),back=new URL(moved.searchParams.get('intl_return')!);
  expect(back.searchParams.get('view')).toBe(view);expect(back.searchParams.get('horizon')).toBe('3m');expect(back.searchParams.get('basis')).toBe('local');expect(back.searchParams.get('return_basis')).toBe('price');
  for(const name of ['intl_context','intl_generation','intl_fingerprint','intl_field'])expect(moved.searchParams.getAll(name)).toEqual(original.searchParams.getAll(name));
 }finally{p.close();}
});

it.each(['macro','risk'])('standalone %s retains legitimate app-origin fallback and bilingual canonical action',view=>{
 const p=page(view,false);try{const url=new URL(p.link.href);expect(url.origin).toBe('https://app.mastermind-x.com');expect(url.pathname).toBe('/analysis');expect(p.link.className).toBe('gbtn');expect(p.link.querySelector('.l-en')?.textContent).toBe('Investigate');expect(p.link.querySelector('.l-zh')?.textContent).toBe('调查研究');}finally{p.close();}
});

it.each(['generation','fingerprint','field','context','href'])('tampered %s reference never navigates or substitutes',key=>{
 const p=page();try{
  if(key==='href')p.link.setAttribute('data-im-investigation-href',p.link.getAttribute('data-im-investigation-href')!+'&token=forbidden');
  else p.link.setAttribute('data-im-investigation-'+key,key==='generation'?'im-workspace-generation:12345678-1234-4123-8123-123456789012':'wrong');
  const count=p.actual.sent.length;expect(activate(p).defaultPrevented).toBe(true);expect(p.actual.sent.length).toBe(count);
 }finally{p.close();}
});
it('refused bridge owns launch without standalone fallback; source replacement removes old action',()=>{
 const p=page('macro',true,false);try{expect(activate(p).defaultPrevented).toBe(true);expect(p.actual.lastOf('NAVIGATE')).toBeNull();
 p.handle.replaceSource('im-workspace-generation:12345678-1234-4123-8123-123456789012',payload.generation);expect(p.link.hidden).toBe(true);expect(p.link.hasAttribute('href')).toBe(false);
 }finally{p.close();}
});

it.each([['macro','qualified'],['risk','qualified'],['macro','missing'],['risk','mismatch']])('real %s/%s anchor → explicit native preflight → exact Return, no substitution or automatic Save',async(view,dependency)=>{
 const p=page(view);activate(p);const href=p.actual.lastOf('NAVIGATE').href;p.close();
 const route=parseAnalysisRoute(Object.fromEntries(new URL(href).searchParams));if(route.kind!=='investigations'||!route.intlEntry)throw Error('strict entry refused');
 const calls:Array<{url:string,method:string}>=[];
 vi.stubGlobal('fetch',vi.fn<typeof fetch>(async(input,init)=>{
  const url=String(input),method=init?.method??'GET';calls.push({url,method});if(method!=='GET')throw Error('Unexpected automatic mutation');
  if(url.startsWith('https://pub-')){
   const name=new URL(url).pathname.split('/').at(-1)!;
   if(dependency==='missing' && name.includes('_f180'))return new Response('missing',{status:404});
   const raw=readFileSync(join(payload.files,name));
   return new Response(dependency==='mismatch' && name.includes('_f180')?Buffer.concat([raw,Buffer.from(' ')]):raw,{headers:{'content-type':'application/json'}});
  }
  if(url.startsWith('/api/investigations/baseline?'))return baselineGET(new Request('https://terminal.test'+url));
  if(url.startsWith('/api/investigations/review?'))return reviewGET(new Request('https://terminal.test'+url));
  return new Response(JSON.stringify(url.startsWith('/api/investigations')?{investigations:[]}:{layouts:[],alerts:[],outbox:[]}),{headers:{'content-type':'application/json'}});
 }));
 (globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{
  await act(async()=>root.render(<InvestigationWorkspace ownerKey={owners.principal} initialIntlEntry={route.intlEntry} intlReturnTo={route.intlReturnTo}/>));
  expect(calls.some(c=>c.url.includes('/baseline?'))).toBe(false);
  await act(async()=>{const b=[...host.querySelectorAll('button')].find(b=>b.textContent==='Use this International selection');expect(b).toBeDefined();b!.click();});
  expect(calls.some(c=>c.url.includes('/baseline?'))).toBe(true);expect(owners.user).toHaveBeenCalled();
  if(dependency==='qualified'){
   expect(host.querySelector<HTMLInputElement>('[aria-label="Title"]')?.value).toBe('');expect(host.querySelector<HTMLTextAreaElement>('[aria-label="Research question"]')?.value).toBe('');
  }else{
   expect(host.querySelector('[aria-label="Title"]')).toBeNull();
   expect(host.querySelector('[aria-label="Research question"]')).toBeNull();
   expect(host.textContent).toContain('unavailable');
   // Exact selected bytes fail; no read of a different generation, POST or
   // invented source may supply a substitute. Current descriptor checks may
   // still run under the incumbent native owner.
   expect(calls.filter(c=>c.url.startsWith('https://pub-')&&c.url.includes('intl_generation_')&&!c.url.includes('current')&&!c.url.includes('descriptor')).every(c=>c.url.includes('_f180'))).toBe(true);
  }
  expect(host.querySelector<HTMLAnchorElement>('a[href^="https://www.mastermind-x.com/intl.html"]')?.href).toBe(route.intlReturnTo);
  expect(calls.every(c=>c.method==='GET')).toBe(true);expect(owners.rpc.mock.calls.some(([name])=>name==='apply_investigation_revision_v2')).toBe(false);
 }finally{await act(async()=>root.unmount());host.remove();sessionStorage.clear();(globalThis as any).IS_REACT_ACT_ENVIRONMENT=false;}
});
