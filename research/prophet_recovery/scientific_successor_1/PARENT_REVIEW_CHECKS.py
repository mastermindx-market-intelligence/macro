"""Independent H1 specification conformance examples, not an evaluator or backtest.

Reads only the adjacent immutable specification and review binding. No market,
price, grade, identity, provider, runtime, account or production input is opened.
The local positive-rule oracle is test scaffolding, not a production policy.
"""
from __future__ import annotations
import copy
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    'SPECIFICATION_R1.md': '076b151387db48a316ce3adc7fbc193db52d335c',
    'REVIEW_BINDING_R1.json': '58ac4052c8b390554b99b2a3c17efa57f2f0578c',
}
checks: list[dict] = []
def check(name: str, actual, expected=True) -> None:
    ok = actual == expected
    checks.append({'name': name, 'pass': ok, 'actual': str(actual), 'expected': str(expected)})
    if not ok:
        raise AssertionError(f'{name}: {actual!r} != {expected!r}')

for name, expected in EXPECTED.items():
    b = (ROOT / name).read_bytes()
    h = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    check('immutable ' + name, h, expected)
p = json.loads((ROOT / 'REVIEW_BINDING_R1.json').read_text())
s = (ROOT / 'SPECIFICATION_R1.md').read_text()
d = p['locked_design_summary']
r = p['parent_review_policy_proposal']
check('non-executable source preserved', p['run_allowed'], False)
check('all authority flags false', not any(p['authority'].values()))
check('one primary/three fixed fits', (d['primary'], d['k'], d['horizon'], d['fit_count_max']), ('C2-C1', 5, 10, 3))
check('one formal look', d['formal_looks_max'], 1)
check('all four author clarifications present', len(p['author_review_clarifications']), 4)
check('coverage clarification retains unresolved keys', 'including identity-unresolved' in p['author_review_clarifications'][0]['rule'])
check('missing common outcome unresolved', 'including_common_selected_names' in d['missing_selected_endpoint'])
check('pilot economic thresholds exact', tuple(F(str(r[k])) for k in ['minimum_useful_gain_lower_interval_bound', 'maximum_downside_deterioration_upper_interval_bound', 'maximum_interval_radius_each_statistic']), (F(1,200), F(1,400), F(1,400)))
check('coverage gates exact', [r[k] for k in ['minimum_base_input_coverage','minimum_peer_coverage','minimum_test_session_k5_coverage','minimum_training_label_coverage','required_selected_pair_completion_for_positive_qualification']], [.7,.7,.7,.95,1.0])
check('gross-only claim', (d['net_return_claim'], d['probability_claim']), (False,False))

# Date weighting is an algebraic property, not a fitted stock model.
a = [F(1), F(3)]
b = [F(2)]
mean = lambda seq: sum(seq, F(0)) / len(seq)
check('daily-loss weighting not row count', mean(a)+mean(b), F(4))
check('identical row replication within day leaves date mean', mean(a+a)+mean(b), mean(a)+mean(b))
check('raw observation sum would change objective', sum(a)+sum(b) != sum(a+a)+sum(b))

# A synthetic sequential index supplies support metadata, never return labels.
train, cal, test = 126, 42, 252
cal_start, test_start = train, train+cal
fit_cut = cal_start-20
train_kept = [t for t in range(train) if t+11 < fit_cut]
cal_kept = [t for t in range(cal_start,test_start) if t+11 < test_start-20]
check('prospective support purge training count', len(train_kept), 95)
check('prospective support purge audit count', len(cal_kept), 11)
check('no purged record moved into test', test,252)
check('fit boundary rejects equal known-at', not (fit_cut < fit_cut))
check('support-end alone cannot waive late-known label', not (90 < fit_cut and 107 < fit_cut))

# Source-native denominator: no invention of an unknown issuer count.
keys = [('d','AAA','v'),('d','BBB','v'),('d','CCC','v'),('d','DDD','v'),('d','EEE','v')]
resolved_primary_core = keys[:3]
check('two unresolved original keys remain in denominator', F(len(resolved_primary_core),len(keys)), F(3,5))
check('unresolved dropping would falsely pass coverage', F(3,3)>=F(7,10) and F(3,5)<F(7,10))

def dedupe(rows):
    out={}
    for key,value in rows:
        if key in out and out[key]!=value:
            raise ValueError('CONFLICTING_ORIGINAL_KEY')
        out.setdefault(key,value)
    return out
check('identical transport duplicate only collapses once', len(dedupe([(keys[0],'a'),(keys[0],'a')])),1)
try:
    dedupe([(keys[0],'a'),(keys[0],'b')])
    conflict=False
except ValueError:
    conflict=True
check('conflicting transport version cannot use keep-last',conflict)

# Basic interval and envelope checks on made-up scalar quantiles, no bootstrap.
def basic(theta, qlow, qhigh):
    return (2*theta-qhigh,2*theta-qlow)
def envelope(a,b):
    return min(a[0],b[0]),max(a[1],b[1])
def radius(theta, bounds):
    return max(abs(theta-bounds[0]),abs(bounds[1]-theta))
check('basic interval is not percentile interval', basic(F(6,1000),F(4,1000),F(7,1000)),(F(5,1000),F(8,1000)))
check('stress uses wider envelope, not nicer interval', envelope((F(5,1000),F(7,1000)),(F(3,1000),F(9,1000))), (F(3,1000),F(9,1000)))
check('asymmetric maximum radius enforced', radius(F(6,1000),(F(55,10000),F(9,1000))),F(3,1000))

# The acceptance inequality checks do not supply an empirical uncertainty estimate.
base = dict(source_bound=True, complete_selected=True, inference_qualified=True,
            variation_delta=True, variation_gamma=True, all_months_covered=True,
            diversity_qualified=True, scope_bound=True, has_disagreement=True,
            peer_attribution_qualified=True,
            gain=(F(5,1000),F(75,10000)), gain_point=F(625,100000),
            harm=(F(0),F(25,10000)), harm_point=F(125,100000))
def synthetic_positive_gate(v):
    compulsory = ['source_bound','complete_selected','inference_qualified','variation_delta',
        'variation_gamma','all_months_covered','diversity_qualified','scope_bound',
        'has_disagreement','peer_attribution_qualified']
    return (all(v[k] for k in compulsory)
        and v['gain'][0]>=F(1,200) and v['harm'][1]<=F(1,400)
        and radius(v['gain_point'],v['gain'])<=F(1,400)
        and radius(v['harm_point'],v['harm'])<=F(1,400))
check('synthetic all-gates positive boundary',synthetic_positive_gate(base))
for key in ['source_bound','complete_selected','inference_qualified','variation_delta',
            'variation_gamma','all_months_covered','diversity_qualified','scope_bound',
            'has_disagreement','peer_attribution_qualified']:
    v=copy.deepcopy(base);v[key]=False
    check('negative control '+key,synthetic_positive_gate(v),False)
v=copy.deepcopy(base);v['gain']=(F(49,10000),F(75,10000))
check('attractive point cannot replace lower-bound threshold',synthetic_positive_gate(v),False)
v=copy.deepcopy(base);v['harm']=(F(0),F(26,10000))
check('downside upper-bound threshold enforced',synthetic_positive_gate(v),False)
v=copy.deepcopy(base);v['gain']=(F(5,1000),F(11,1000))
check('sufficient lower bound but insufficient precision',synthetic_positive_gate(v),False)
v=copy.deepcopy(base);v['harm']=(F(0),F(0));v['harm_point']=F(0);v['variation_gamma']=False
check('no observed differential harm is not certain safety',synthetic_positive_gate(v),False)

# Both declared block lengths need their own feasibility accounting.
L=32
check('planned final window accommodates two stress blocks',252>=2*(2*L))
check('shorter window can fit L yet not stress2L',100>=2*L and 100<2*(2*L))
check('bootstrap lengths not independent trial arms',d['fit_names'],['C0','C1','C2'])
check('Bonferroni marginal-error sum',F(25,1000)*2,F(5,100))
z=NormalDist().inv_cdf(1-.025/2)
check('conditional precision arithmetic', [math.ceil((z*x/.0025)**2) for x in [.01,.02,.04]],[81,322,1287])

result = {
    'kind':'independent_source_blind_specification_review_checks',
    'source_commit':'f05ea4c41c2512a739937839f76664158c75809f',
    'checks':checks,'passed':len(checks),'failed':0,
    'market_data_read':False,'backtest_executed':False,'model_fit_executed':False,
    'bootstrap_executed':False,'native_runtime_smoke_executed':False,
    'application_source_changed':False,'production_authority':False,
    'review_boundary':'Policy/algebra conformance only; no claim of calibrated financial inference or accepted native implementation.'
}
raw=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode()
(ROOT/'REVIEW_CHECKS.json').write_bytes(raw)
print(json.dumps({'passed':len(checks),'failed':0,'sha256':hashlib.sha256(raw).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}))
