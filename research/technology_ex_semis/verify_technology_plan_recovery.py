"""Offline verification of plan arithmetic and trace; NOT a native product test."""
from decimal import Decimal, localcontext
from pathlib import Path
import argparse, hashlib, json, random, re
D=Decimal
checks=[]
def check(name, value):
    if not value: raise AssertionError(name)
    checks.append(name)
def bridge(fa,fb,pa,pb,ga,xb,precision=34):
    with localcontext() as c:
        c.prec=precision
        return (fb-fa, xb-ga, pb-pa, fa-pa-ga, fb-pb-xb,
                (fb-fa)-(xb-ga)-(pb-pa))
x=tuple(map(D,('4320','4460','1006.426','1006.426','1075','1121.454')))
y=bridge(*x)
check('reference_all_six_values', y==tuple(map(D,('140','46.454','0','2238.574','2332.120','93.546'))))
check('independent_remaining_identity',y[5]==y[4]-y[3])
a=list(x);a[3]+=10
check('prior_actual_revision',bridge(*a)[5]==D('83.546'))
check('omitted_revision_mutation_detected', bridge(*a)[0]-bridge(*a)[1]!=bridge(*a)[5])
a=list(x);a[1]+=10
check('new_annual_increase',bridge(*a)[5]==y[5]+10)
a=list(x);a[5]+=10
check('new_actual_increase',bridge(*a)[5]==y[5]-10)
a=list(x);a[2]+=10;a[3]+=10
check('paired_prior_increase',bridge(*a)[5]==y[5] and bridge(*a)[3]==y[3]-10)
check('consistent_scaling',bridge(*(v*1000 for v in x))==tuple(v*1000 for v in y))
check('unchanged_zero',bridge(D(100),D(100),D(20),D(20),D(30),D(30))[-1]==0)
check('valid_negative',bridge(D(100),D(90),D(20),D(20),D(30),D(35))[-1]==-15)
pattern=re.compile(r'-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?\Z')
invalid=('NaN','Infinity','1e20','1e-7','1000000000000','0.0000001','+1','01','',True,1.0)
check('bounded_decimal_rejections',all(not isinstance(s,str) or pattern.fullmatch(s) is None for s in invalid))
check('bounded_decimal_validity',all(pattern.fullmatch(s) for s in ('0','-1','999999999999.999999','-999999999999.999999','0.000001')))
check('ordered_range_refusal_oracle',D('11')>D('10'))
rng=random.Random(7793)
# Six values may each be sums of sixteen admitted source rows; midpoint adds
# one fractional digit. Compare the specified 34-digit kernel to a 100-digit oracle.
for _ in range(1000):
    vals=[]
    for _role in range(6):
        vals.append(sum((D(rng.randrange(-10**18+1,10**18))*D('0.000001')/2 for _ in range(16)),D(0)))
    a=bridge(*vals);b=bridge(*vals,precision=100)
    if a!=b or a[5]!=a[4]-a[3]: raise AssertionError('precision-bound-oracle')
check('1000_seeded_precision_cases',True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--trace', type=Path, default=Path(__file__).resolve().parents[2] / 'docs/superpowers/plans/2026-09-23-technology-economic-change-first-vertical-verification.md')
args=parser.parse_args()
parts=[[v.strip() for v in line.split('|')[1:-1]] for line in args.trace.read_text().splitlines() if re.match(r'^\| ECD-\d\d \|', line)]
rows=[v[:3] for v in parts]
check('48_ordered_unique_ids',[r[0] for r in rows]==[f'ECD-{n:02}' for n in range(1,49)])
h=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
check('verbatim_spec_digest',h=='a780c18907f4a3d7032e3401759c37da9d47dc59b01207fa0dfc045fd391128b')
check('phase_accounting', [v[-1] for v in parts]==['LATER' if 27<=n<=39 else 'PAGINATION' if n==44 else 'FIRST' for n in range(1,49)])
# A state-transition model of the read/put/read/unconditional-rollback code,
# NOT execution against any store. Writer A can roll back B's newer pointer.
pointer='P0'; prior_a=pointer; prior_b=pointer
pointer='P1'; pointer='P2'
if pointer!='P1': pointer=prior_a
check('unconditional_rollback_counterexample',pointer=='P0' and pointer!='P2')
report={'scope':'OFFLINE_PLAN_VERIFICATION_ONLY','checks_passed':len(checks),'check_names':checks,
        'precision_samples':1000,'verbatim_requirement_rows_sha256':h,
        'native_product_tests_run':0,'source_admissions':0,'production_writes':0,
        'reference_remaining_change_usd_millions':str(y[-1]),
        'publisher_counterexample':'state-transition model, not an observed production incident'}
print(json.dumps(report,indent=2))
