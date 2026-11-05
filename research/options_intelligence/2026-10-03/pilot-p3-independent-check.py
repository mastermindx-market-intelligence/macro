#!/usr/bin/env python3
"""Portable preservation of the independent P3 review probes; synthetic only.

The original read-only shell probe used an absolute source path. This version
adds a local --source parameter and digest guard, turns the previously observed
premature-label clock into a refusal assertion, and retains the original closed
numeric/scope findings as explicit regression probes. It writes only stdout.
"""
from pathlib import Path
import argparse,types,hashlib,json,math,random,statistics
from decimal import Decimal,localcontext
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,default=Path(__file__).with_name('pilot-p3-reference.py'))
parser.add_argument('--expected-sha256',default='29fc1cc5ff79abc5a7f0377ea1860113adc851f0aad81feb852d27d45a65a11f')
args=parser.parse_args()
p=args.source;raw=p.read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.expected_sha256:
 raise SystemExit('Source digest differs from the reviewed target; explicit review/version update required.')
m=types.ModuleType('p3');m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__)
checks=[];facts={}
def check(name,cond):
 if not cond:raise AssertionError(name)
 checks.append(name)
def refuse(name,call):
 try:call()
 except m.Refusal as e: checks.append(name);return e.code
 raise AssertionError(name+' did not refuse')
def D(x):return Decimal.from_float(float(x))
def decimal_optimum(rows):
 with localcontext() as ctx:
  ctx.prec=75
  weight=sum(D(r['weight']) for r in rows)
  def grad(b):return sum(D(r['weight'])*D(r['z'])*(1-D(r['y'])/D(r['v1'])*(-b*D(r['z'])).exp()) for r in rows)/weight
  lo,hi=Decimal(-1),Decimal(1)
  if grad(lo)>=0:return float(lo)
  if grad(hi)<=0:return float(hi)
  for _ in range(140):
   mid=(lo+hi)/2
   if grad(mid)<0:lo=mid
   else:hi=mid
  return float((lo+hi)/2)
rng=random.Random(623107);max_beta_error=0.;max_derivative_error=0.;n_boundary=0
for case in range(64):
 rows=[]
 for i in range(rng.randrange(2,9)):
  v1=10**rng.uniform(-3,-0.5);z=rng.uniform(-4,4);y=0. if (case+i)%11==0 else v1*math.exp(rng.uniform(-2,2))
  rows.append({'id':str(i),'y':y,'v1':v1,'z':z,'weight':rng.choice([1,2,3,7])})
 actual=m.fit(rows);expected=decimal_optimum(rows);err=abs(actual['beta']-expected)
 max_beta_error=max(max_beta_error,err);n_boundary+=actual['constrained_optimum']
 check('weighted_decimal_optimum_'+str(case),err<=5.1e-11)
 check('row_permutation_'+str(case),m.fit(list(reversed(rows)))['beta']==actual['beta'])
 scaled=[{**r,'weight':r['weight']*17} for r in rows]
 check('common_weight_scale_'+str(case),abs(m.fit(scaled)['beta']-actual['beta'])<=1e-10)
 with localcontext() as ctx:
  ctx.prec=75;b=D(0.37);tw=sum(D(r['weight']) for r in rows)
  independent_grad=sum(D(r['weight'])*D(r['z'])*(1-D(r['y'])/D(r['v1'])*(-b*D(r['z'])).exp()) for r in rows)/tw
  independent_loss=sum(D(r['weight'])*(D(r['v1']).ln()+b*D(r['z'])+D(r['y'])/D(r['v1'])*(-b*D(r['z'])).exp()) for r in rows)/tw
 actual_eval=m.evaluate(rows,0.37)
 diff=abs(actual_eval['derivative']-float(independent_grad));max_derivative_error=max(max_derivative_error,diff)
 check('decimal_gradient_'+str(case),math.isclose(actual_eval['derivative'],float(independent_grad),rel_tol=2e-12,abs_tol=1e-12))
 check('decimal_QLIKE_'+str(case),math.isclose(actual_eval['loss'],float(independent_loss),rel_tol=2e-12,abs_tol=1e-12))
facts['moderate_domain']={'seed':623107,'weighted_books':64,'max_beta_error':max_beta_error,'max_gradient_abs_error':max_derivative_error,'boundary_optima':n_boundary}
# Independent scaler census includes ineligible observations and deliberately shuffled records.
history=[{'root':'SYNTH','clock_bin':'09:35','session':f's{i:03d}','formation_at_ns':100+i,'available_at_ns':101+i,'eligible':i%7!=0,'value':float(i)} for i in range(90)]
qualified=[r for r in history if r['eligible']][-60:];values=sorted(r['value'] for r in qualified)
median=(values[29]+values[30])/2;dev=sorted(abs(x-median) for x in values);mad=(dev[29]+dev[30])/2
s=m.robust_scaler(history,1000,'SYNTH','09:35');shuffled=history[:];rng.shuffle(shuffled)
check('scaler_last60_independent_census',s['selected_sessions']==[r['session'] for r in qualified] and s['observations']==60 and s['census_rows']==90)
check('scaler_median_MAD_independent_order_statistics',s['median']==median and s['mad']==mad and math.isclose(s['scale'],1.4826*mad))
check('scaler_history_permutation',m.robust_scaler(shuffled,1000,'SYNTH','09:35')==s)
minimum=[{**r,'eligible':True} for r in history[:40]]
check('scaler_exactly40_accepted',m.robust_scaler(minimum,1000,'SYNTH','09:35')['observations']==40)
refuse('scaler39_refused',lambda:m.robust_scaler(minimum[:39],1000,'SYNTH','09:35'))
refuse('scaler_future_ineligible_row_not_ignored',lambda:m.robust_scaler(history+[{'root':'SYNTH','clock_bin':'09:35','session':'future','formation_at_ns':999,'available_at_ns':1001,'eligible':False,'value':0}],1000,'SYNTH','09:35'))
refuse('scaler_observation_at_fit_refused',lambda:m.robust_scaler([{**r,'formation_at_ns':1000,'available_at_ns':1000} if i==0 else r for i,r in enumerate(minimum)],1000,'SYNTH','09:35'))
check('transform_zero_is_observed_zero',m.transform(s['median'],s)==0.)
for sign in (1,-1): facts['transform_underflow_'+str(sign)]=refuse('transform_signed_underflow_'+str(sign),lambda sign=sign:m.transform(sign*1e-300,{'median':0.,'scale':1e100}))
facts['scaler']={'observations':s['observations'],'median':s['median'],'mad':s['mad'],'first_session':s['selected_sessions'][0],'last_session':s['selected_sessions'][-1]}
record={'id':'r','source_revision_id':'source','feature_revision_id':'feature','baseline_revision_id':'baseline','label_revision_id':'label','formation_at_ns':1000,'label_mature_at_ns':2000,'label_revision_available_at_ns':2500,'feature_input_available_at_ns':900,'feature_published_at_ns':950,'feature_received_at_ns':980,'nuisance_fit_at_ns':800,'nuisance_latest_training_label_mature_at_ns':790,'baseline_input_available_at_ns':900,'baseline_fit_at_ns':850,'baseline_latest_training_label_mature_at_ns':840,'baseline_published_at_ns':960,'baseline_received_at_ns':990}
c=m.validate_training_chronology([record],3000,4000)
check('chronology_valid_order_not_authenticity',c['status']=='ORDERING_VALID' and c['availability_attested'] is False and c['consumer_capture_attested'] is False)
for key,bad in [('label_revision_available_at_ns',9000),('feature_input_available_at_ns',951),('feature_received_at_ns',1001),('baseline_fit_at_ns',961),('nuisance_fit_at_ns',951),('label_mature_at_ns',3001)]:
 refuse('chronology_reject_'+key,lambda key=key,bad=bad:m.validate_training_chronology([{**record,key:bad}],3000,4000))
refuse('chronology_fit_test_tie',lambda:m.validate_training_chronology([record],3000,3000))
refuse('chronology_duplicate_identity',lambda:m.validate_training_chronology([record,record],3000,4000))
facts['label_available_before_mature']={'refusal':refuse('chronology_complete_label_revision_cannot_precede_maturity',lambda:m.validate_training_chronology([{**record,'label_revision_available_at_ns':1999}],3000,4000))}
# These repeat the concrete counterexamples independently discovered before repair.
tiny=[{'id':'tiny','y':1.,'v1':1.,'z':1e-20,'weight':1.}]
tiny_result=m.fit(tiny)
check('closed_tiny_curved_false_boundary',tiny_result['beta']==0. and not tiny_result['constrained_optimum'])
affine=[{'id':'a','y':0.,'v1':1.,'z':5.,'weight':1.},
        {'id':'b','y':0.,'v1':1.,'z':-1.,'weight':5.},
        {'id':'c','y':0.,'v1':1.,'z':-1e-18,'weight':1.}]
affine_result=m.fit(affine)
check('closed_affine_original_weight_sign_reversal',affine_result['beta']==1. and affine_result['derivative']<0)
subnormal=[{'id':'curved','y':1.,'v1':1.,'z':1e-160,'weight':1.},
           {'id':'affine','y':0.,'v1':1.,'z':-1e-321,'weight':1.}]
subnormal_refusal=refuse('closed_subnormal_false_exact_root',lambda:m.fit(subnormal))
null_history=[{**r,'root':None,'clock_bin':None} for r in minimum]
null_refusal=refuse('closed_null_scaler_scope',lambda:m.robust_scaler(null_history,1000,None,None))
facts['closed_numeric_findings']={'tiny_beta':tiny_result['beta'],'affine_beta':affine_result['beta'],
                                'subnormal_refusal':subnormal_refusal,'null_scope_refusal':null_refusal}
base=m.run_fixtures();check('existing_fixtures_pass',base['passed']==base['case_count'])
check('source_bytes_unchanged_during_probes',raw==p.read_bytes())
print(json.dumps({'status':'PASS','source_sha256':hashlib.sha256(raw).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'independent_assertions':len(checks),'baseline_cases':base['case_count'],'facts':facts},indent=2))
