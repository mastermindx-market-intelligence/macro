"""Outcome-free counterexamples against the exact S6 predecessor source.
No market data, protected holdout, empirical feature trial, or source admission.
"""
from __future__ import annotations
import dataclasses, hashlib, json, sys
from decimal import Decimal as D, localcontext
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
import structural_guards as g
M=60_000_000_000

def good(**changes):
    r=g.MinuteClaim('AI','SEC:NVDA',10*M,11*M,12*M,11*M+100,11*M+200,1,
      'r0','raw-2026','ca-v1','PERMITTED_BY_OWNER','FINAL_AS_KNOWN',D('250'),D('45'),D('.50'),13*M,18*M)
    return dataclasses.replace(r,**changes)
def quote(**changes):
    r=g.PrintQuoteClaim(100000,99000,100500,101000,10000,'ELIGIBLE_REGULAR','FINAL_UNCORRECTED',D('22'))
    return dataclasses.replace(r,**changes)
def baseline():
    return [g.BaselineObservation(str(i),i,D(i*i+1)) for i in range(20)]

PROBES=[]
def add(name,why,fn): PROBES.append((name,why,fn))
for f in ['cutoff_ns','source_known_ns','reader_complete_ns','membership_known_ns','label_start_ns','label_end_ns','last_correction_known_ns']:
    add('minute_nan_'+f,'All present clocks must be exact integer nanoseconds, not NaN.',lambda f=f:g.assess_minute(good(**{f:float('nan')})))
add('minute_float_clock','Float nanoseconds can silently lose ordering.',lambda:g.assess_minute(good(membership_known_ns=1.5)))
add('minute_bool_clock','Booleans are not a knowledge timestamp.',lambda:g.assess_minute(good(membership_known_ns=True)))
add('minute_missing_start','Malformed mandatory clocks must return a typed rejection, not crash.',lambda:g.assess_minute(good(minute_start_ns=None)))
add('minute_whitespace_identity','Whitespace is not an identity.',lambda:g.assess_minute(good(security_id='   ')))
add('minute_nonstring_identity','Numeric truthiness is not a canonical ID.',lambda:g.assess_minute(good(security_id=123)))
add('empty_aggregate','No observations must not become a numeric zero-gross witness.',lambda:g.aggregate_synthetic([]))
add('conflicting_action_vintage','Same security-minute cannot have two corporate-action vintages.',lambda:g.aggregate_synthetic([good(),good(factor_id='SEMIS',corporate_action_vintage='ca-v2')]))
add('conflicting_pressure','Same source revision cannot claim two different signed pressures.',lambda:g.aggregate_synthetic([good(),good(factor_id='SEMIS',signed_pressure=D('-45'))]))
add('baseline_nan_cutoff','NaN cutoff bypasses prior-knowledge comparison.',lambda:g.check_prior_baseline('now',float('nan'),baseline()))
add('baseline_nan_known','NaN known-at is not a prior vintage.',lambda:g.check_prior_baseline('now',1000,[dataclasses.replace(r,known_ns=float('nan')) if i==0 else r for i,r in enumerate(baseline())]))
add('baseline_zero_floor_empty','Invalid history floor must reject rather than call median([]).',lambda:g.check_prior_baseline('now',1000,[],min_history=0))
add('baseline_bool_floor','Boolean history floor is an invalid parameter.',lambda:g.check_prior_baseline('now',1000,baseline(),min_history=True))
add('baseline_whitespace_row_id','Whitespace row identity must not pass uniqueness.',lambda:g.check_prior_baseline('now',1000,[dataclasses.replace(r,source_row_id=' ') if i==0 else r for i,r in enumerate(baseline())]))
for f in ['print_time_ns','quote_time_ns','source_receipt_ns','cutoff_ns','quote_age_limit_ns']:
    add('quote_nan_'+f,'NaN clock/age disables ordering or staleness comparison.',lambda f=f:g.assess_quote_reference(quote(**{f:float('nan')})))
add('quote_missing_mandatory_cutoff','Missing mandatory cutoff must reject, not crash.',lambda:g.assess_quote_reference(quote(cutoff_ns=None)))
add('quote_bool_clock','A bool print clock is not an integer clock.',lambda:g.assess_quote_reference(quote(print_time_ns=True,quote_time_ns=0,source_receipt_ns=2,cutoff_ns=3)))
add('decimal_abs_precision','Context-rounded abs must not hide pressure > gross.',lambda:g.assess_minute(good(gross_notional=D('10000000000000000000000000000'),signed_pressure=D('10000000000000000000000000001'))))

results=[]
for name,why,fn in PROBES:
    try:
        out=fn(); value=dataclasses.asdict(out)
        observed='TYPED_REJECTION' if out.status==g.BLOCKED else 'STRUCTURALLY_CLEAR'
        result={'id':name,'required':why,'observation':observed,'satisfied':observed=='TYPED_REJECTION','returned':value}
    except Exception as exc:
        result={'id':name,'required':why,'observation':'EXCEPTION_NOT_TYPED','satisfied':False,'exception':type(exc).__name__,'message':str(exc)}
    results.append(result)
# Arithmetic order dependence is a separate metamorphic invariant.
large=D('10000000000000000000000000000')
rows=[good(security_id='A',gross_notional=large,signed_pressure=D(0),weight=D(1)),good(security_id='B',gross_notional=D(5),signed_pressure=D(0),weight=D(1)),good(security_id='C',gross_notional=D(5),signed_pressure=D(0),weight=D(1))]
a=g.aggregate_synthetic(rows);b=g.aggregate_synthetic(rows[::-1])
results.append({'id':'decimal_aggregation_permutation','required':'Exact nonnegative money aggregation must be order-independent or explicitly precision-rejected.','satisfied':a==b,'observation':'ORDER_DEPENDENT' if a!=b else 'SAME','forward':dataclasses.asdict(a),'reverse':dataclasses.asdict(b)})
source=(ROOT/'source/structural_guards.py').read_bytes()
receipt={'scope':'SYNTHETIC_ADVERSARIAL_SOFTWARE_ONLY','target_commit':'fbaa3812510a67e879c17defa270e16f717d3ce3','target_git_blob':hashlib.sha1(f'blob {len(source)}\0'.encode()+source).hexdigest(),'target_sha256':hashlib.sha256(source).hexdigest(),'probe_count':len(results),'failed_invariants':sum(not x['satisfied'] for x in results),'results':results,'all_financial_authority_false':True,'market_outcomes_read':False}
(ROOT/'evidence/original_adversarial_counterexamples.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='results'},indent=2))
for x in results: print(x['id'],x['observation'])
