"""Synthetic arithmetic checks, NOT a reproduction of either earnings study."""
from fractions import Fraction as F
from pathlib import Path
from hashlib import sha256
import json
import argparse
parser=argparse.ArgumentParser()
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
if args.output.exists(): raise SystemExit("refusing to overwrite an existing result")
R=args.output.parent
R.mkdir(parents=True,exist_ok=True)
p=[F(95,100),F(92,100),F(2,100)];G=F(2);N=3
weights=[G/N*2*(x-F(1,2)) for x in p]
assert weights==[F(3,5),F(14,25),-F(16,25)]
assert sum(weights)==F(13,25)
assert sum(abs(w) for w in weights)==F(9,5)
# Uniform market return with no idiosyncratic information still yields nonzero P&L.
market_only=sum(w*F(1,100) for w in weights)
assert market_only==F(13,2500)
# A post-earnings purchase cannot claim a price move before its own entry.
pre,ready,end=F(100),F(110),F(112)
unavailable_move=ready/pre-1
remaining_move=end/ready-1
full_move=end/pre-1
assert (1+unavailable_move)*(1+remaining_move)==1+full_move
# Entry size based on eventual session count changes as future events arrive.
first_weight_2=G/2*2*(p[0]-F(1,2))
first_weight_10=G/10*2*(p[0]-F(1,2))
assert first_weight_2!=first_weight_10
out={'schema':'prophet.earnings_timing_review_counterexamples/v1',
     'source_formula_ref':'arxiv:2606.29734v1:Appendix_C.2',
     'formula_scope':'Literal equation in manuscript only; repository currently has no implementation to inspect.',
     'neutrality_counterexample':{'percentiles':[float(x) for x in p],
         'G':2,'N':3,'weights':[float(x) for x in weights],
         'net_exposure':float(sum(weights)),'gross_exposure':float(sum(abs(x) for x in weights)),
         'uniform_1pct_market_move_pnl':float(market_only)},
     'future_count_sensitivity':{'first_percentile':float(p[0]),
         'first_weight_if_eventual_N2':float(first_weight_2),
         'first_weight_if_eventual_N10':float(first_weight_10),
         'interpretation':'A causal implementation needs an ex-ante allocation denominator or a declared sequential policy; not proof the unpublished code uses future counts.'},
     'entry_time_counterexample':{'prices':[100,110,112],
         'before_entry_fraction':float(unavailable_move),
         'post_entry_fraction':float(remaining_move),
         'whole_window_fraction':float(full_move),
         'multiplicative_identity_verified':True,
         'interpretation':'12% event-window appreciation is not 12% earned by a buyer at110; later costs would reduce the remaining1.818%.'},
     'limits':['No real stock outcomes or model inference.',
               'No claim that the papers reported precisely these synthetic rows.',
               'No source-data license or live strategy authority.']}
b=(json.dumps(out,indent=2)+'\n').encode();args.output.write_bytes(b)
print(json.dumps({'net_exposure':float(sum(weights)),'remaining_move':float(remaining_move),'result_sha256':sha256(b).hexdigest()},indent=2))
