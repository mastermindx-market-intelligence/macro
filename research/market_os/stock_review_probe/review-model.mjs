/** Synthetic interaction probe only. No network, storage, market or account integration. */
export const laneOrder = ['Buy now','Almost ready','In favour','Take profits','Watch — don’t chase','Stand aside'];
export const fixtures = [
 {id:'NASDAQ:AVGO:USD',symbol:'AVGO',name:'Broadcom',venue:'NASDAQ',currency:'USD',theme:'Semiconductors',price:331.60,change:3.25,volume:2.0,average:1.8,lane:'Watch — don’t chase',meaning:'Moving without a base. Watch, don’t chase.',options:null},
 {id:'NASDAQ:AMD:USD',symbol:'AMD',name:'AMD',venue:'NASDAQ',currency:'USD',theme:'Semiconductors',price:188.64,change:2.31,volume:1.8,average:0.4,lane:'Almost ready',meaning:'Wait for a reclaim on volume.',options:null},
 {id:'NASDAQ:NVDA:USD',symbol:'NVDA',name:'NVIDIA',venue:'NASDAQ',currency:'USD',theme:'Semiconductors',price:181.54,change:1.82,volume:1.4,average:0.3,lane:'Almost ready',meaning:'Wait for a reclaim on volume.',options:null},
 {id:'NASDAQ:MSFT:USD',symbol:'MSFT',name:'Microsoft',venue:'NASDAQ',currency:'USD',theme:'Software',price:516.20,change:0.84,volume:1.1,average:0.6,lane:'In favour',meaning:'Trend intact. No fresh chase.',options:null},
 {id:'NASDAQ:CRWD:USD',symbol:'CRWD',name:'CrowdStrike',venue:'NASDAQ',currency:'USD',theme:'Cybersecurity',price:430.28,change:-0.65,volume:0.8,average:-0.7,lane:'Stand aside',meaning:'No confirmed setup in this example.',options:null},
 {id:'NASDAQ:QCOM:USD',symbol:'QCOM',name:'Qualcomm',venue:'NASDAQ',currency:'USD',theme:'Semiconductors',price:null,change:null,volume:null,average:null,lane:'Stand aside',meaning:'Current quote unavailable. No entry conclusion.',options:null}
];
const finite=v=>typeof v==='number' && Number.isFinite(v);
const validRows=rows=>Array.isArray(rows) && rows.every(r=>r && typeof r.id==='string' && r.id && typeof r.symbol==='string') && new Set(rows.map(r=>r.id)).size===rows.length;
const copyRows=rows=>rows.map(r=>({...r}));
export function filterRows(rows,{query='',lane='All',theme='All'}={}) {
 const q=String(query).trim().toLocaleLowerCase();
 return rows.filter(r=>(lane==='All'||r.lane===lane) && (theme==='All'||r.theme===theme) && (!q||[r.symbol,r.name,r.venue,r.currency].some(v=>String(v||'').toLocaleLowerCase().includes(q))));
}
export function sortRows(rows,sort='volume') {
 return rows.map((r,i)=>({r,i})).sort((a,b)=>{
  if(sort==='symbol') return a.r.symbol.localeCompare(b.r.symbol)||a.i-b.i;
  const key=sort==='price-asc'?'price':sort==='change'?'change':'volume';
  const av=a.r[key],bv=b.r[key];
  if(!finite(av)&&!finite(bv)) return a.i-b.i;
  if(!finite(av)) return 1; if(!finite(bv)) return -1;
  return (sort==='price-asc'?av-bv:bv-av)||a.i-b.i;
 }).map(x=>x.r);
}
export function counts(rows) {
 const c=Object.fromEntries(laneOrder.map(l=>[l,0])); c.All=rows.length;
 for(const r of rows) if(laneOrder.includes(r.lane)) c[r.lane]++; else c.Unclassified=(c.Unclassified||0)+1;
 return c;
}
export function createState(rows=fixtures) {
 if(!validRows(rows)) throw new TypeError('Rows must carry unique, nonempty listing identities.');
 return {rows:copyRows(rows),selectedId:null,inspectorOpen:false,query:'',lane:'All',theme:'All',sort:'volume',compare:[],compareOpen:false,saved:[],revision:1,pending:null,sourceStatus:'ready',notice:'',saveSerial:0,save:{status:'idle',id:null,requestId:0,error:''}};
}
export function inspected(s) { return s.rows.find(r=>r.id===s.selectedId); }
export function reduce(s,e) {
 const exists=id=>s.rows.some(r=>r.id===id);
 switch(e.type) {
  case 'inspect': return exists(e.id)?{...s,selectedId:e.id,inspectorOpen:true,notice:''}:s;
  case 'closeInspector': return {...s,inspectorOpen:false};
  case 'filter': return {...s,...(typeof e.query==='string'?{query:e.query.slice(0,200)}:{}),...(['All',...laneOrder].includes(e.lane)?{lane:e.lane}:{}),...(typeof e.theme==='string'?{theme:e.theme}:{}),notice:''};
  case 'sort': return ['volume','change','symbol','price-asc'].includes(e.sort)?{...s,sort:e.sort}:s;
  case 'clearFilters': return {...s,query:'',lane:'All',theme:'All',notice:''};
  case 'compare': {
   if(s.compare.includes(e.id)) return {...s,compare:s.compare.filter(id=>id!==e.id),notice:''};
   if(!exists(e.id)) return s;
   if(s.compare.length>=3) return {...s,notice:'Compare up to three listings. Remove one to add another.'};
   return {...s,compare:[...s.compare,e.id],notice:''};
  }
  case 'openCompare': return s.compare.length>=2?{...s,compareOpen:true}:s;
  case 'closeCompare': return {...s,compareOpen:false};
  case 'clearCompare': return {...s,compare:[],compareOpen:false,notice:''};
  case 'stage': {
   if(!Number.isSafeInteger(e.revision)||e.revision<=Math.max(s.revision,s.pending?.revision||0)) return s;
   if(!validRows(e.rows)) return {...s,notice:'Example update rejected: listing identities are invalid.'};
   return {...s,pending:{rows:copyRows(e.rows),revision:e.revision},notice:''};
  }
  case 'apply': return s.pending?{...s,rows:s.pending.rows,revision:s.pending.revision,pending:null,notice:s.sourceStatus==='error'?'Buffered example applied; the source is still unavailable.':'Example snapshot updated. Your selection is retained.'}:s;
  case 'saveStart': {
   if(!exists(e.id)||s.sourceStatus!=='ready'||s.save.status==='pending') return s;
   if(s.saved.includes(e.id)) return {...s,save:{status:'success',id:e.id,requestId:s.save.requestId,error:''},notice:'Already in this tab’s demo watchlist.'};
   return {...s,saveSerial:s.saveSerial+1,save:{status:'pending',id:e.id,requestId:s.saveSerial+1,error:''},notice:''};
  }
  case 'saveResult': {
   if(s.save.status!=='pending'||s.save.id!==e.id||s.save.requestId!==e.requestId) return s;
   return e.ok===true?{...s,saved:[...new Set([...s.saved,e.id])],save:{status:'success',id:e.id,requestId:s.save.requestId,error:''},notice:'Saved to this tab’s demo watchlist only.'}:{...s,save:{status:'error',id:e.id,requestId:s.save.requestId,error:'Demo save failed. Nothing was added.'},notice:'Demo save failed. Nothing was added.'};
  }
  case 'sourceError': return {...s,sourceStatus:'error',notice:'Source unavailable. The previous example snapshot is retained, not current data.'};
  case 'sourceRestore': return {...s,sourceStatus:'ready',notice:'Example source restored.'};
  default:return s;
 }
}
