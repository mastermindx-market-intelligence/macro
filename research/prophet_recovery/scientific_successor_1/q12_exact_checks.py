#!/usr/bin/env python3
"""Fictional exact-arithmetic Q12 exhibits. No finance data, fitting, or native imports.

Run this file in its own evidence directory. It writes Q12_EXACT_RESULTS.json.
The small matrix helpers are test-only, not a production optimizer/evaluator.
"""
from __future__ import annotations
from fractions import Fraction as F
from itertools import combinations, product
from pathlib import Path
import json
import platform


def dot(a, b):
    if len(a) != len(b):
        raise ValueError('dimension mismatch')
    return sum((F(x) * F(y) for x, y in zip(a, b)), F(0))


def mv(a, x):
    return [dot(row, x) for row in a]


def transpose(a):
    return [list(c) for c in zip(*a)]


def rref(a):
    a = [[F(x) for x in row] for row in a]
    if not a:
        return a, []
    ncol, r, pivots = len(a[0]), 0, []
    if any(len(row) != ncol for row in a):
        raise ValueError('ragged matrix')
    for col in range(ncol):
        pivot = next((i for i in range(r, len(a)) if a[i][col]), None)
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        v = a[r][col]
        a[r] = [x / v for x in a[r]]
        for i in range(len(a)):
            if i != r:
                v = a[i][col]
                a[i] = [x - v * y for x, y in zip(a[i], a[r])]
        pivots.append(col)
        r += 1
        if r == len(a):
            break
    return a, pivots


def rank(a):
    return len(rref(a)[1])


def inverse(a):
    n = len(a)
    if any(len(row) != n for row in a):
        raise ValueError('matrix not square')
    aug = [list(row) + [int(i == j) for j in range(n)] for i, row in enumerate(a)]
    reduced, piv = rref(aug)
    if piv[:n] != list(range(n)) or len(piv) != n:
        raise ValueError('singular matrix')
    return [row[n:] for row in reduced]


def gram(rows, weights=None):
    p = len(rows[0])
    weights = [F(1)] * len(rows) if weights is None else weights
    return [[sum((F(w)*F(row[i])*F(row[j]) for w, row in zip(weights, rows)), F(0))
             for j in range(p)] for i in range(p)]


def add_outer(a, v, weight=F(1)):
    return [[F(a[i][j])+weight*F(v[i])*F(v[j]) for j in range(len(v))]
            for i in range(len(v))]


def top(scores, k):
    return tuple(sorted(sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]))


def payoff(scores, selected):
    return sum((F(scores[i]) for i in selected), F(0)) / len(selected)


def voi(a, b, p, k):
    coarse = [p*x+(1-p)*y for x, y in zip(a, b)]
    base = top(coarse, k)
    value = p*payoff(a, top(a,k))+(1-p)*payoff(b, top(b,k))-payoff(coarse, base)
    return value, base


def shock_moments(lam, assimilation, persistence, vs, vu, cov=F(0)):
    # x=lam*s+u; y=assimilation*(1-lam)*s-(1-persistence)*u+eta.
    aa, bb = assimilation*(1-lam), 1-persistence
    vx = lam*lam*vs+vu+2*lam*cov
    if vx <= 0:
        raise ValueError('nonpositive observed variance')
    cxy = aa*lam*vs-bb*vu+(aa-bb*lam)*cov
    return vx, cxy, cxy/vx


def cell(th, x, z):
    return dot(th, [1,x,z,x*z])


def robust_interval_shortlist(lower, upper, k=2, charge=F(1)):
    base = (0,1)
    subsets = list(combinations(range(4),k))
    def scores(theta):
        return [F(100),F(90),F(80)+theta,F(70)]
    def value(s):
        cost = F(0) if s == base else charge
        return min(payoff(scores(v),s)-payoff(scores(v),base)-cost for v in (lower,upper))
    values={s:value(s) for s in subsets}
    winner=max(subsets,key=lambda s:(values[s],s==base))
    return winner,values


checks=[]

def record(name, fn):
    details=fn()
    checks.append({'name':name,'status':'PASS','details':details})


def c01():
    s=[F(3),F(2),F(2),F(-1)]
    for k in range(1,5):
        for a,b in product(map(F,[-10,0,9]),[F(1,3),F(1),F(7)]):
            assert top(s,k)==top([a+b*x for x in s],k)
    assert top(s,1)!=top([-x for x in s],1)
    return {'affine_cases':36,'positive_scale_required':True}
record('C01_positive_affine_context_preserves_fixed_k',c01)


def c02():
    s=[F(3),F(2),F(1)]
    worlds=[[v+z for v in s] for z in [F(-10),F(10)]]
    coarse_mse=sum((dot([x-y for x,y in zip(w,s)],[x-y for x,y in zip(w,s)]) for w in worlds),F(0))/6
    assert coarse_mse==100
    value,_=voi(worlds[0],worlds[1],F(1,2),1)
    assert value==0 and all(top(w,1)==(0,) for w in worlds)
    return {'coarse_mean_squared_error':coarse_mse,'context_error':0,'selection_value':value}
record('C02_perfect_forecast_improvement_zero_selection_value',c02)


def c03():
    count=0
    for raw in product([-1,0,1],repeat=6):
        a,b=list(map(F,raw[:3])),list(map(F,raw[3:]))
        for p,k in product([F(1,4),F(1,2),F(3,4)],[1,2]):
            value,base=voi(a,b,p,k)
            assert value>=0
            base_optimal=(payoff(a,base)==payoff(a,top(a,k)) and payoff(b,base)==payoff(b,top(b,k)))
            assert (value==0)==base_optimal
            count+=1
    assert count==4374
    return {'finite_world_checks':count,'equality_iff_common_optimum':True}
record('C03_value_of_information_and_equality_exhaustive',c03)


def c04():
    value,_=voi([F(2),F(0)],[F(0),F(2)],F(1,2),1)
    assert value==1
    return {'gross_selection_value':value,'units':'fictional payoff units'}
record('C04_actual_rank_crossing_can_create_value',c04)


def c05():
    assert shock_moments(F(1,2),F(1),F(0),F(1),F(0))[2]==1
    assert shock_moments(F(1,2),F(1),F(0),F(0),F(1))[2]==-1
    assert shock_moments(F(1),F(1),F(0),F(1),F(0))[2]==0
    return {'pure_unincorporated_information_slope':1,'pure_pressure_slope':-1,'fully_incorporated_information_slope':0}
record('C05_information_pressure_and_full_price_incorporation',c05)


def c06():
    a=shock_moments(F(1,2),F(1),F(0),F(3),F(1,4))
    b=shock_moments(F(1,2),F(1),F(0),F(1),F(3,4))
    assert a[0]==b[0]==1 and a[2]==F(1,2) and b[2]==F(-1,2)
    return {'information_world':a,'pressure_world':b,'distribution_claim':'identical x distributions additionally follows under independent centered Gaussian components; not simulated'}
record('C06_equal_observed_variance_opposite_remaining_payoff',c06)


def c07():
    l,a,phi=F(1,3),F(1,2),F(1,4)
    values=[]
    for s,u in product([-1,1],repeat=2):
        x=l*s+u;y=a*(1-l)*s-(1-phi)*u
        values.append((x,y))
    ex2=sum((x*x for x,y in values),F(0))/4
    exy=sum((x*y for x,y in values),F(0))/4
    got=shock_moments(l,a,phi,F(1),F(1))
    assert got==(ex2,exy,exy/ex2)
    return {'exact_four_point_moments':got}
record('C07_shock_formula_matches_enumerated_moments',c07)


def c08():
    rows=[[1,-1,-1,1],[1,1,1,1]]
    null=[-1,0,0,1]
    assert mv(rows,null)==[0,0] and rank(rows)==2
    predictions=[]
    for t in [-100,0,100]:
        th=[1-t,0,0,t]
        assert mv(rows,th)==[1,1]
        predictions.append(cell(th,1,-1)-cell(th,-1,-1))
    assert predictions==[200,0,-200]
    return {'design_rank':2,'columns':4,'same_training_predictions':[1,1],'unseen_contrast_by_parameter_shift':predictions}
record('C08_missing_cross_context_support_reverses_unseen_ranking',c08)


def c09():
    rows=[[1,-1,-1,1]]*12+[[1,1,1,1]]*12
    assert rank(rows)==rank(rows*100)==2
    assert len(rows)==24 and len(rows*100)==2400
    return {'months_each_stated_context':12,'rows':24,'replicated_rows':2400,'rank_before_after':[2,2],'month_count_is_not_identification':True}
record('C09_calendar_floor_and_row_replication_cannot_repair_null_space',c09)


def c10():
    rows=[[1,-1,0],[1,1,0]]
    identified=[0,2,0];unidentified=[0,0,1]
    assert rank(rows+[identified])==rank(rows)
    assert rank(rows+[unidentified])>rank(rows)
    return {'singular_design_can_identify_some_contrasts':True,'unobserved_feature_need_not_block_unrelated_contrast':True}
record('C10_contrast_specific_identification_not_whole_model_veto',c10)


def c11():
    x=[F(-2),F(-1),F(1),F(2)];z=F(3)
    rows=[[1,v,z*v] for v in x]
    assert rank(rows)==2
    centered=[z*v-sum(z*y for y in x)/4 for v in x]
    assert centered==[z*v for v in x]
    return {'constant_context_times_signal_is_existing_signal_direction':True}
record('C11_interaction_can_duplicate_main_effect',c11)


def c12():
    rows=[[1,-1],[1,1],[1,-2],[1,2]]
    j=gram(rows,[F(1,4)]*4)
    replicated=[row for row in rows for _ in range(100)]
    assert gram(replicated,[F(1,400)]*400)==j
    return {'original_rows':4,'copied_rows':400,'normalized_gram_unchanged':True}
record('C12_fixed_date_mass_not_more_information_from_duplicate_rows',c12)


def c13():
    t,n,rho=F(4),F(1000),F(1)
    variance=(rho+(1-rho)/n)/t
    naive=1/(t*n)
    assert variance==F(1,4) and variance/naive==1000
    return {'true_variance':variance,'iid_row_variance':naive,'underestimate_factor':variance/naive,'assumption':'four independent date shocks, perfect within-date correlation'}
record('C13_shared_date_shocks_not_independent_stocks',c13)


def c14():
    risks={}
    for shrink in [F(0),F(1,5),F(1)]:
        risk=sum(((shrink*(g+e)-g)**2 for g,e in product([F(-1,2),F(1,2)],[-1,1])),F(0))/4
        risks[str(shrink)]=risk
    assert risks=={'0':F(1,4),'1/5':F(1,5),'1':F(1)}
    return {'squared_coefficient_risks':risks,'not_top_k_profit':True}
record('C14_partial_pooling_beats_pool_all_and_fit_each_in_toy_model',c14)


def c15():
    p=F(7,10);up,down,cost=F(30),F(-90),F(5)
    gain=p*up+(1-p)*down-cost
    threshold=(cost-down)/(up-down)
    assert gain==-11 and threshold==F(19,24)
    assert threshold*up+(1-threshold)*down-cost==0
    return {'context_probability':p,'gain_basis_points':gain,'break_even_context_probability':threshold,'not_observed_strategy':True}
record('C15_seventy_percent_context_can_have_negative_decision_value',c15)


def c16():
    gains=[120*p-95 for p in [F(3,5),F(17,20)]]
    assert gains==[-23,7]
    assert 120*F(4,5)-95==1
    return {'point_estimate_gain_bp':1,'context_probability_range':[F(3,5),F(17,20)],'compatible_gain_range_bp':gains}
record('C16_context_probability_uncertainty_reverses_nominal_choice',c16)


def c17():
    # Exact Euclidean unit-ball support, with the minimizing point on the grid.
    d=[F(3),F(4)];center=[F(2),F(3)]
    theta_star=[center[0]-F(3,5),center[1]-F(4,5)]
    analytic=dot(d,center)-5
    vals=[]
    for x,y in product(range(-10,11),repeat=2):
        u,v=F(x,10),F(y,10)
        if u*u+v*v<=1:
            vals.append(dot(d,[center[0]+u,center[1]+v]))
    assert min(vals)==dot(d,theta_star)==analytic==13
    return {'finite_feasible_points':len(vals),'attained_lower_bound':analytic}
record('C17_joint_ellipsoid_support_attains_analytic_bound',c17)


def c18():
    sigma=[[F(1),F(7,8)],[F(7,8),F(1)]];d=[F(1),F(-1)]
    sd=F(1,2); assert dot(d,mv(sigma,d))==sd*sd
    center=[F(10),F(9)]
    shift=[-x/sd for x in mv(sigma,d)]
    assert dot(shift,mv(inverse(sigma),shift))==1
    joint=dot(d,center)-sd
    separate=(center[0]-1)-(center[1]+1)
    assert joint==F(1,2) and separate==-1
    return {'shared_parameter_lower_bound':joint,'separate_marginal_lower_bound':separate,'attainer':shift}
record('C18_shared_uncertainty_pairing_beats_incompatible_extremes',c18)


def c19():
    wide,values_wide=robust_interval_shortlist(F(5),F(55))
    narrow,values_narrow=robust_interval_shortlist(F(25),F(35))
    assert wide==(0,1) and narrow==(0,2)
    assert values_wide[(0,2)]==F(-7,2)
    assert values_narrow[(0,2)]==F(13,2)
    assert values_wide[(0,1)]==values_narrow[(0,1)]==0
    return {'wide_interval_choice':'A,B','wide_A_C_lower_gain_bp':values_wide[(0,2)],'narrow_interval_choice':'A,C','narrow_A_C_lower_gain_bp':values_narrow[(0,2)],'alternatives_each':6,'charge_per_changed_basket_bp':1}
record('C19_robust_incumbent_relative_shortlist_defers_uncertain_swap',c19)


def c20():
    base=(0,1);chosen=(0,2)
    for theta in range(25,36):
        scores=[100,90,80+theta,70]
        assert payoff(scores,chosen)-payoff(scores,base)-1>=F(13,2)
    # This possible realized common shock destroys absolute profit, not the contrast.
    realized=[F(x)-200 for x in [100,90,110,70]]
    assert payoff(realized,chosen)<0 and payoff(realized,base)<0
    return {'all_eleven_parameter_values_positive_relative_lower_gain':True,'negative_absolute_payoffs_still_possible':True}
record('C20_robust_relative_model_gain_is_not_profit_guarantee',c20)


def c21():
    j=[[F(10000),F(0)],[F(0),F(1)]];d=[F(0),F(1)];jinv=inverse(j)
    before=dot(d,mv(jinv,d))
    reductions=[]
    for v in [[F(1),F(0)],[F(0),F(1)],[F(1),F(1)]]:
        exact=before-dot(d,mv(inverse(add_outer(j,v)),d))
        formula=dot(d,mv(jinv,v))**2/(1+dot(v,mv(jinv,v)))
        assert exact==formula
        reductions.append(exact)
    assert reductions[0]==0 and reductions[1]==F(1,2)
    return {'initial_decision_variance_scale':before,'irrelevant_row_reduction':reductions[0],'relevant_row_reduction':reductions[1],'mixed_row_reduction':reductions[2]}
record('C21_decision_specific_value_of_additional_design_support',c21)


def c22():
    rows=[[1,0]]*10000
    assert rank(rows)==rank(rows+[[1,0]])==1
    assert rank(rows+[[0,1]])==2
    return {'rows_along_one_axis':10000,'one_cross_axis_row_closes_rank_gap':True,'no_data_or_power_claim':True}
record('C22_one_new_support_direction_can_beat_ten_thousand_duplicates',c22)


def c23():
    # A stock-specific error box (|e_i|<=2) worsens the same fixed-K pair by 2,
    # not by arbitrary full-universe extremes. A pure common error cancels.
    wdiff=[F(0),F(-1,2),F(1,2),F(0)]
    bound=2*sum(abs(x) for x in wdiff)
    worst=min(dot(wdiff,e) for e in product([-2,2],repeat=4))
    assert worst==-bound==-2 and dot(wdiff,[100]*4)==0
    return {'worst_stock_specific_error_bp':worst,'common_level_error_cancels':True}
record('C23_model_error_allowance_targets_the_actual_swap',c23)


def c24():
    # General quadratic uncertainty is in coefficient units, not future-return volatility.
    j=[[F(2),F(1)],[F(1),F(3)]]
    for a,b in product(range(-3,4),repeat=2):
        d=[F(a),F(b)]
        for v in [[F(1),F(0)],[F(0),F(1)],[F(1),F(-1)]]:
            old=dot(d,mv(inverse(j),d));new=dot(d,mv(inverse(add_outer(j,v)),d))
            assert new<=old
    return {'finite_information_updates':147,'uncertainty_does_not_increase_under_stated_model':True}
record('C24_information_update_monotonicity',c24)



def c25():
    slopes=[]
    for h in range(1,9):
        assimilation=1-F(9,10)**h
        persistence=F(1,10)**h
        slopes.append(shock_moments(F(1,2),assimilation,persistence,F(3),F(1,4))[2])
    assert slopes[0]==F(-3,20)
    assert all(x<0 for x in slopes[:3]) and all(x>0 for x in slopes[3:])
    assert slopes[3]==F(159,20000)
    return {'horizons':list(range(1,9)),'remaining_return_slopes':slopes,
            'first_positive_stipulated_horizon':4,
            'interpretation':'different relaxation speeds; not a holding policy or measured time constant'}
record('C25_one_mechanism_short_reversal_long_continuation',c25)


def c26():
    # Correlated innovations require the covariance terms; zero-covariance formula is conditional.
    lam,assim,phi=F(1,3),F(1,2),F(1,4)
    moments=[]
    for a,b in product([-1,1],repeat=2):
        signal=F(a);pressure=F(a,2)+F(b)
        x=lam*signal+pressure
        y=assim*(1-lam)*signal-(1-phi)*pressure
        moments.append((x,y))
    vx=sum((x*x for x,y in moments),F(0))/4
    cov=sum((x*y for x,y in moments),F(0))/4
    result=shock_moments(lam,assim,phi,F(1),F(5,4),F(1,2))
    incorrect=shock_moments(lam,assim,phi,F(1),F(5,4),F(0))
    assert result==(vx,cov,cov/vx) and result!=incorrect
    return {'correct_correlated_moments':result,'wrong_independence_moments':incorrect}
record('C26_correlated_latent_shocks_require_extra_terms',c26)


def c27():
    # Fixed equal-K selection stability is the intersection of selected/unselected
    # affine score inequalities. At equality the declared index tie rule keeps B.
    base=[F(100),F(90),F(80),F(70)]
    loading=[F(0),F(0),F(1),F(0)]
    selected=(0,1)
    lower,upper=None,None
    for i,j in product(selected,[2,3]):
        intercept=base[i]-base[j];slope=loading[i]-loading[j]
        if slope>0:
            bound=-intercept/slope
            lower=bound if lower is None else max(lower,bound)
        elif slope<0:
            bound=-intercept/slope
            upper=bound if upper is None else min(upper,bound)
        else:
            assert intercept>=0
    assert lower is None and upper==10
    for theta in map(F,range(-100,101)):
        actual=top([b+theta*h for b,h in zip(base,loading)],2)
        assert (actual==selected)==(theta<=upper)
    assert top([b+F(10001,1000)*h for b,h in zip(base,loading)],2)==(0,2)
    # Additional information about theta cannot change optimal selection inside [5,9].
    worlds=[[b+t*h for b,h in zip(base,loading)] for t in (F(5),F(9))]
    assert voi(worlds[0],worlds[1],F(1,2),2)[0]==0
    return {'fixed_k_stability_interval':'theta <= 10, with declared tie rule',
            'integer_parameter_cases':201,'information_within_5_to_9_selection_value':0}
record('C27_exact_selection_stability_boundary',c27)


def c28():
    # A strict gap >2*epsilon certifies unchanged top-K for an l-infinity
    # score-error box. It says nothing about the absolute return level.
    scores=[F(10),F(8),F(5),F(1)];epsilon=F(1)
    baseline=top(scores,2)
    assert scores[1]-scores[2]>2*epsilon
    for error in product([-epsilon,epsilon],repeat=4):
        assert top([s+e for s,e in zip(scores,error)],2)==baseline
    close=[F(10),F(6),F(5),F(1)]
    assert top([close[0],close[1]-epsilon,close[2]+epsilon,close[3]],2)!=(0,1)
    return {'error_box_vertices_checked':16,'sufficient_margin':'> 2*epsilon',
            'not_a_claim_that_all_uncertainty_boxes_are_empirically_valid':True}
record('C28_rank_margin_precision_not_uniform_forecast_perfection',c28)


def serial(x):
    if isinstance(x,F):
        return {'exact':str(x),'decimal':float(x)}
    if isinstance(x,dict):
        return {str(k):serial(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):
        return [serial(v) for v in x]
    return x


if __name__=='__main__':
    report={'evidence_class':'exact fictional mathematical checks; not empirical validation',
            'python':platform.python_version(),'passed':len(checks),'failed':0,
            'financial_data_read':False,'native_modules_imported':False,'model_fitted':False,
            'registered_trial_run':False,'checks':checks}
    dest=Path(__file__).with_name('Q12_EXACT_RESULTS.json')
    dest.write_text(json.dumps(serial(report),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'passed':len(checks),'failed':0,'python':platform.python_version(),'result_file':str(dest)}))
