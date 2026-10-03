/* Pure, synthetic design reference for R12 comparison outputs.
 * No network, storage, model call, rank mutation or recommendation authority.
 * Four-branch semantics belong ONLY to these fixtures: two favorable, one delayed,
 * one negative. A production consumer must use its owner's explicit outcome mapping.
 */
(function(root,factory){
 'use strict'; const api=factory();
 if(typeof module==='object' && module.exports) module.exports=api;
 else root.CatalystSensitivityReference=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const EPS=1e-9;
 const finite=x=>typeof x==='number' && Number.isFinite(x);
 const sum=a=>a.reduce((s,x)=>s+x,0);
 const copy=x=>({...x,probabilities:[...x.probabilities],conditional_prices:[...x.conditional_prices]});
 const expected=n=>n.probabilities.reduce((s,p,i)=>s+p*n.conditional_prices[i],0);
 const net=n=>expected(n)/n.reference_price-1-n.fee;
 const reject=reason=>({ok:false,reason,applied_to_recommendation:false});
 function validate(pair){
  if(!pair || pair.status!=='COMPARABLE_SYNTHETIC') return 'COMPARISON_NOT_QUALIFIED';
  for(const n of [pair.left,pair.right]){
   if(!n || n.ready!==true || n.mode!=='SYNTHETIC_REFERENCE_ARITHMETIC' || n.model_validated!==false || n.new_recommendation!==null) return 'SYNTHETIC_INPUT_REQUIRED';
   if(!finite(n.reference_price)||n.reference_price<=0||!finite(n.fee)||n.fee<0||n.fee>.25) return 'INVALID_REFERENCE_OR_COST';
   if(!Array.isArray(n.probabilities)||!Array.isArray(n.conditional_prices)||n.probabilities.length!==4||n.conditional_prices.length!==4) return 'INVALID_BRANCH_SHAPE';
   if(n.probabilities.some(x=>!finite(x)||x<0||x>1)||Math.abs(sum(n.probabilities)-1)>EPS||n.conditional_prices.some(x=>!finite(x)||x<0)) return 'INVALID_OUTCOMES';
   if(!finite(n.net)||Math.abs(net(n)-n.net)>EPS) return 'RETURN_DOES_NOT_RECONCILE';
   for(const key of ['id','security_id','event_id','cutoff','horizon_anchor','horizon_end','benchmark']) if(typeof n[key]!=='string'||!n[key]) return 'MISSING_COMPARISON_BINDING';
   if(n.currency!=='USD'||n.cost_basis!=='net') return 'UNSUPPORTED_CONVENTION';
  }
  if(pair.left.security_id===pair.right.security_id) return 'SAME_SECURITY';
  for(const key of ['currency','benchmark','horizon_months','horizon_anchor','horizon_end','cost_basis','cutoff']) if(pair.left[key]!==pair.right[key]) return 'MISMATCHED_'+key.toUpperCase();
  return null;
 }
 function apply(pair,draft){
  const error=validate(pair);if(error)return reject(error);
  if(!draft||!['left','right'].includes(draft.side)||!['probability','payoff','entry'].includes(draft.mode)||!finite(draft.amount)||draft.amount<0||draft.amount>1)return reject('INVALID_STRESS');
  const n=copy(pair[draft.side]),p=n.probabilities,v=n.conditional_prices,x=draft.amount,total=p[0]+p[1];
  if(draft.mode==='probability'){
   if(total<=0||x>total+EPS)return reject('INSUFFICIENT_FAVORABLE_MASS');
   const rest=Math.max(0,total-x);p[0]=rest*p[0]/total;p[1]=rest*p[1]/total;p[3]+=x;
  }else if(draft.mode==='payoff'){
   v[0]*=1-x;v[1]*=1-x;
  }else n.reference_price*=1+x;
  // Reconcile every derived scalar in the stressed projection; never mix a new
  // probability/value/entry assumption with copied baseline target or payoff fields.
  n.expected_price=expected(n);n.net=net(n);
  n.failure_gross=v[3]/n.reference_price-1;n.strong_gross=v[0]/n.reference_price-1;
  n.positive_probability=p[0]+p[1];
  n.profit_probability=p.reduce((s,w,i)=>s+(v[i]/n.reference_price-1-n.fee>0?w:0),0);
  n.zero_return_price=n.expected_price/(1+n.fee);
  n.target_price=finite(n.required_net_return)?n.expected_price/(1+n.fee+n.required_net_return):null;
  const left=draft.side==='left'?n:copy(pair.left),right=draft.side==='right'?n:copy(pair.right);
  const delta=left.net-right.net;
  return {ok:true,mode:'SYNTHETIC_ASSUMPTION_STRESS',draft:{...draft},left,right,delta_net:delta,
   order:Math.abs(delta)<EPS?'tie':delta>0?'left':'right',
   applied_to_recommendation:false,quote_changed:false,probability_of_stress:null,
   confidence_interval:null,risk_adjusted_preference:null,portfolio_authority:false};
 }
 function boundaries(pair){
  const error=validate(pair);if(error)return reject(error);
  const delta=pair.left.net-pair.right.net;
  if(Math.abs(delta)<EPS)return reject('BASELINE_TIE');
  const side=delta>0?'left':'right',n=pair[side],other=pair[side==='left'?'right':'left'];
  const p=n.probabilities,v=n.conditional_prices,total=p[0]+p[1],fav=p[0]*v[0]+p[1]*v[1];
  const meanFav=total>0?fav/total:null,erosion=(n.net-other.net)*n.reference_price;
  const inRange=(x,max)=>finite(x)&&x>=0&&x<=max+EPS?x:null;
  const prob=meanFav!==null && meanFav>v[3]?inRange(erosion/(meanFav-v[3]),total):null;
  const payoff=fav>0?inRange(erosion/fav,1):null;
  const denom=n.reference_price*(1+n.fee+other.net);
  const entry=denom>0?inRange(expected(n)/denom-1,1):null;
  return {ok:true,leader_side:side,leader_id:n.id,other_id:other.id,delta_net:Math.abs(delta),
   thresholds:{probability:prob,payoff,entry},probability_of_threshold:null,
   applied_to_recommendation:false,uncertainty_interval:null};
 }
 return Object.freeze({apply,boundaries});
});
