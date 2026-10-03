// Pure reference tests; no production imports or external I/O beyond this report.
'use strict';
const fs=require('node:fs'), assert=require('node:assert/strict'), path=require('node:path');
const out=process.argv[2]||path.join(__dirname,'R13_REFERENCE_VALIDATION.json');
let api;const results=[];
function ck(name,fn){try{fn();results.push({name,passed:true});}catch(e){results.push({name,passed:false,message:e.message});}}
ck('reference module exists',()=>{assert.ok(fs.existsSync(path.join(__dirname,'sensitivity_reference.js')));api=require('./sensitivity_reference.js');});
if(api){
 const point=(id,price,p,v,fee)=>({ready:true,id,security_id:'synthetic:'+id,event_id:'event:'+id,mode:'SYNTHETIC_REFERENCE_ARITHMETIC',model_validated:false,new_recommendation:null,confidence_interval:null,currency:'USD',cost_basis:'net',benchmark:'example_benchmark',horizon_anchor:'2026-09-26',horizon_end:'26 Mar 2027',horizon_months:'6',cutoff:'2026-09-26T20:00:00Z',reference_price:price,fee,probabilities:p,conditional_prices:v,net:p.reduce((s,x,i)=>s+x*v[i],0)/price-1-fee});
 const L=point('DEF-A',28,[.48,.24,.12,.16],[46,34,26,17],.01),R=point('SEM-A',25,[.45,.25,.15,.15],[40,31,24,16],.012);
 for(const n of [L,R]){n.expected_price=n.probabilities.reduce((a,x,i)=>a+x*n.conditional_prices[i],0);n.failure_gross=n.conditional_prices[3]/n.reference_price-1;n.strong_gross=n.conditional_prices[0]/n.reference_price-1;n.positive_probability=n.probabilities[0]+n.probabilities[1];n.required_net_return=.1;n.target_price=n.expected_price/(1+n.fee+.1);}
 const pair={status:'COMPARABLE_SYNTHETIC',left:L,right:R};
 const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
 const copy=x=>JSON.parse(JSON.stringify(x));
 const initial=JSON.stringify(pair),bounds=api.boundaries(pair);
 ck('paired reference input accepted',()=>assert.equal(bounds.ok,true));
 ck('correct original leader',()=>assert.equal(bounds.leader_id,'DEF-A'));
 ck('probability tie at 2.304 percentage points',()=>near(bounds.thresholds.probability,.02304));
 ck('payoff tie computed on weighted favorable value',()=>near(bounds.thresholds.payoff,(L.net-R.net)*28/(.48*46+.24*34)));
 ck('entry tie uses price denominator',()=>near(bounds.thresholds.entry,36.08/(28*(1+.01+R.net))-1));
 for(const mode of ['probability','payoff','entry']){
  const z=api.apply(pair,{side:'left',mode,amount:0}),t=api.apply(pair,{side:'left',mode,amount:bounds.thresholds[mode]}),stress=api.apply(pair,{side:'left',mode,amount:.05});
  ck(mode+' zero is identity',()=>near(z.left.net,L.net));
  ck(mode+' exact threshold reaches tie',()=>assert.equal(t.order,'tie'));
  ck(mode+' benchmark case unchanged',()=>assert.deepEqual(stress.right,R));
  const changed=stress.left,ev=changed.probabilities.reduce((a,p,i)=>a+p*changed.conditional_prices[i],0);
  ck(mode+' export expected value reconciles',()=>near(changed.expected_price,ev));
  ck(mode+' export gross branches reconcile',()=>{near(changed.failure_gross,changed.conditional_prices[3]/changed.reference_price-1);near(changed.strong_gross,changed.conditional_prices[0]/changed.reference_price-1);});
  ck(mode+' export derived target reconciles',()=>near(changed.target_price,ev/(1+changed.fee+.1)));
  ck(mode+' not recommendation or interval',()=>{assert.equal(stress.applied_to_recommendation,false);assert.equal(stress.probability_of_stress,null);assert.equal(stress.risk_adjusted_preference,null);});
 }
 let x=api.apply(pair,{side:'left',mode:'probability',amount:.05});
 ck('probability shift lowers expected return',()=>near(x.left.net,.23392857142857148));
 ck('probability reallocation preserves mass',()=>near(x.left.probabilities.reduce((a,b)=>a+b,0),1));
 ck('strong/modest conditional ratio preserved',()=>near(x.left.probabilities[0]/x.left.probabilities[1],2));
 ck('delayed branch unchanged',()=>near(x.left.probabilities[2],.12));
 ck('failure gains exact shifted mass',()=>near(x.left.probabilities[3],.21));
 ck('probability mode leaves valuations unchanged',()=>assert.deepEqual(x.left.conditional_prices,L.conditional_prices));
 ck('5-point stress changes arithmetic leader',()=>assert.equal(x.order,'right'));
 x=api.apply(pair,{side:'left',mode:'payoff',amount:.10});
 ck('payoff holds probabilities',()=>assert.deepEqual(x.left.probabilities,L.probabilities));
 ck('payoff affects only favorable prices',()=>assert.deepEqual(x.left.conditional_prices,[41.4,30.6,26,17]));
 x=api.apply(pair,{side:'left',mode:'entry',amount:.10});
 ck('entry is hypothetical reference not new quote',()=>{near(x.left.reference_price,30.8);assert.equal(x.quote_changed,false);});
 ck('entry holds scenario values',()=>assert.deepEqual(x.left.conditional_prices,L.conditional_prices));
 ck('all operations preserve original pair',()=>assert.equal(JSON.stringify(pair),initial));
 for(const amount of [null,true,NaN,Infinity,-.1,'5',1.1])ck('invalid amount '+String(amount),()=>assert.equal(api.apply(pair,{mode:'probability',side:'left',amount}).ok,false));
 ck('probability shift cannot exceed favorable mass',()=>assert.equal(api.apply(pair,{mode:'probability',side:'left',amount:.8}).ok,false));
 ck('invalid mode refused',()=>assert.equal(api.apply(pair,{mode:'opinion',side:'left',amount:.05}).ok,false));
 ck('invalid side refused',()=>assert.equal(api.apply(pair,{mode:'entry',side:'third',amount:.05}).ok,false));
 for(const [name,mut] of [
  ['pending input',p=>p.status='NOT_COMPARABLE'],['missing right',p=>p.right=null],['real mode',p=>p.left.mode='LIVE'],['validated claim',p=>p.left.model_validated=true],['zero quote',p=>p.left.reference_price=0],['mixed cutoff',p=>p.right.cutoff='2026-09-27T00:00:00Z'],['different horizon',p=>p.right.horizon_end='26 Sep 2027'],['currency',p=>p.right.currency='GBP'],['bad mass',p=>p.left.probabilities[0]=.9],['net disagrees',p=>p.left.net=.4],['duplicate investment',p=>p.right.security_id=p.left.security_id]]){
  const bad=copy(pair);mut(bad);ck(name+' withheld',()=>assert.equal(api.boundaries(bad).ok,false));
 }
 const swapped={status:pair.status,left:R,right:L};ck('right-side leader symmetric',()=>{const b=api.boundaries(swapped);assert.equal(b.leader_side,'right');near(b.thresholds.probability,.02304);});
 const equal=copy(pair);equal.right={...copy(L),id:'TIE',security_id:'synthetic:TIE'};ck('initial tie not invented advantage',()=>assert.equal(api.boundaries(equal).reason,'BASELINE_TIE'));
 const noSlope=copy(pair);noSlope.left.conditional_prices=[40,40,40,40];noSlope.left.net=40/28-1-.01;ck('no probability slope gives no crossing',()=>assert.equal(api.boundaries(noSlope).thresholds.probability,null));
}
const report={scope:'pure synthetic sensitivity reference; not production model or policy',passed:results.filter(x=>x.passed).length,failed:results.filter(x=>!x.passed).length,tests:results};fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({passed:report.passed,failed:report.failed,failures:results.filter(x=>!x.passed)},null,2));process.exitCode=report.failed?1:0;
