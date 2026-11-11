const fs=require('fs'),path=require('path'),assert=require('assert');
const text=fs.readFileSync(path.join(__dirname,'../templates/stock.html.j2'),'utf8');
function block(t){const a=t.indexOf('      if (pos.short_flow) {');const b=t.indexOf('      if (pos.insider)',a);assert(a>=0&&b>a);return t.slice(a,b);}
function render(t,sf,locale){let rows=[];const f=new Function('pos','LF','lz','esc','signPct','kvRow','var html="";'+block(t)+';return html;');return {html:f({short_flow:sf},k=>k,(en,zh)=>locale==='zh'?zh:en,s=>String(s).replace(/[<>&"]/g,'_'),n=>String(n),(k,v,w)=>{rows.push([k,v,w]);return '<div>'+k+':'+v+'</div>'}),rows};}
const notes={partial:['Partial history','历史样本不足'],observed_zero:['Reported zero','报告的卖空成交量为零']};let cases=0;
for(const lang of ['en','zh'])for(const [state,note] of Object.entries(notes)){
 const sf={state,short_ratio_pct:state==='observed_zero'?0:50,trend_pp:-2,ratio_z:state==='partial'?null:0,n_days:8,asof:'2026-11-11'};
 const out=render(text,sf,lang);assert(out.html.includes(note[lang==='en'?0:1]));assert(out.rows.find(r=>r[0]==='sfratio')[1]===(state==='observed_zero'?'0.0%':'50.0%'));
 if(state==='observed_zero')assert(!out.html.includes('unavailable')&&!out.html.includes('暂无可用'));
 cases++;
}
const baseline=process.env.SHORT_FLOW_BASELINE;
if(baseline){const old=fs.readFileSync(baseline,'utf8');for(const lang of ['en','zh'])for(const state of [undefined,'observed','unknown','unavailable','parse_error','no_observation'])for(let i=0;i<100;i++){
 const sf={state,short_ratio_pct:i,trend_pp:i-50,ratio_z:i%3===0?null:(i-50)/10,n_days:20+i,asof:'2026-11-11'};
 assert.deepStrictEqual(render(text,sf,lang),render(old,sf,lang));cases++;
}for(const lang of ['en','zh'])for(const state of Object.keys(notes)){
 const sf={state,short_ratio_pct:0,trend_pp:-37.5,ratio_z:null,n_days:8,asof:'2026-11-11'};
 assert.deepStrictEqual(render(text,sf,lang).rows,render(old,sf,lang).rows);cases++;
}}
if(process.argv[2]){
 const sf=JSON.parse(fs.readFileSync(process.argv[2],'utf8')).short_flow;
 for(const lang of ['en','zh']){const out=render(text,sf,lang);const note=notes[sf.state];if(note)assert(out.html.includes(note[lang==='en'?0:1]));else assert(!out.html.includes('Partial history')&&!out.html.includes('Reported zero'));
 assert(out.rows.find(r=>r[0]==='sfratio')[1]===(sf.short_ratio_pct==null?'na':sf.short_ratio_pct.toFixed(1)+'%'));cases++;}
}
console.log(JSON.stringify({passed:cases,baselineParity:!!baseline}));
