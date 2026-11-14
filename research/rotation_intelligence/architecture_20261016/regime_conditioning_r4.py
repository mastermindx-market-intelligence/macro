"""R4 synthetic regime-estimation diagnostic. No market data, product or network IO.

Run: python regime_conditioning_r4.py > regime_conditioning_results_r4.json
All opportunities/utility are dimensionless invented quantities, not returns.
Oracle hyperparameters and centers are NOT fitted investment-model evidence.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
from pathlib import Path
from statistics import NormalDist
import sys
import numpy as np

G=11
SEED=20261017
REPLICATIONS=12000
HURDLE=0.05
MODELS=('unconditioned','hard_cell','scalar_oracle','joint_oracle')
FLAGS={'market_data_read':False,'native_statistical_qualification':False,
       'investment_authority':False,'oracle_hyperparameters':True,
       'units':'dimensionless_synthetic_opportunity_not_returns',
       'scope':'one_off_mathematical_diagnostic_not_empirical_evaluator'}


def _parameters(n: int,tau: float,rho: float) -> None:
    if type(n) is not int or n<1:
        raise ValueError('n must be a positive integer')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (tau,rho)):
        raise ValueError('finite real parameters required')
    if tau<0 or not 0<=rho<1:
        raise ValueError('tau >= 0 and 0 <= rho < 1 required')


def _array(value, *, center=False):
    a=np.asarray(value)
    if a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError('finite nonboolean numeric arrays required')
    if (center and a.shape!=(G,)) or (not center and (a.ndim!=2 or a.shape[1]!=G or a.shape[0]==0)):
        raise ValueError('complete eleven-group array required')
    return a.astype(float,copy=False)


def covariance(n: int,rho: float):
    _parameters(n,0.,rho)
    return ((1-rho)*np.eye(G)+rho*np.ones((G,G)))/n


def _eigen_shrinkages(n,tau,rho):
    _parameters(n,tau,rho)
    vc=(1+(G-1)*rho)/n;vd=(1-rho)/n;t2=tau*tau
    return vc,vd,{'unconditioned':(0.,0.),'hard_cell':(1.,1.),
        'scalar_oracle':(t2/(t2+1/n),)*2,
        'joint_oracle':(t2/(t2+vc),t2/(t2+vd))}


def estimates(y,a_model,n: int,tau: float,rho: float):
    y=_array(y);a=_array(a_model,center=True)
    _,_,pairs=_eigen_shrinkages(n,tau,rho)
    x=y-a;common=x.mean(axis=1,keepdims=True);contrast=x-common
    return {name:a+kc*common+kd*contrast for name,(kc,kd) in pairs.items()}


def analytic_risks(a_true,a_model,s: int,n: int,tau: float,rho: float):
    a=_array(a_true,center=True);am=_array(a_model,center=True)
    if type(s) is not int or s not in (-1,1):raise ValueError('s must be +1 or -1')
    vc,vd,pairs=_eigen_shrinkages(n,tau,rho)
    b=am-a;bc=float(b.mean());bd=b-bc
    out={}
    for name,(kc,kd) in pairs.items():
        bias=(1-kc)**2*bc**2+(1-kd)**2*float(np.dot(bd,bd))/G
        signal=tau*tau*((kc-s)**2+(G-1)*(kd-s)**2)/G
        noise=(kc*kc*vc+(G-1)*kd*kd*vd)/G
        out[name]=bias+signal+noise
    return out


def decision_metrics(pred,truth):
    pred=_array(pred);truth=_array(truth)
    if pred.shape!=truth.shape:raise ValueError('matched prediction and truth shapes required')
    selected=np.argsort(-pred,axis=1,kind='stable')[:,:3]
    oracle=np.argsort(-truth,axis=1,kind='stable')[:,:3]
    yp=np.take_along_axis(pred,selected,axis=1)
    actual=np.take_along_axis(truth,selected,axis=1).mean(axis=1)
    best=np.take_along_axis(truth,oracle,axis=1).mean(axis=1)
    # Center before summing: exact equality in every selected input stays equality.
    acted=(yp-HURDLE).sum(axis=1)>0
    return {'selected':selected,'regret':best-actual,'actual':actual,
        'optimism':yp.mean(axis=1)-actual,'acted':acted,
        'utility':np.where(acted,actual-HURDLE,0.),
        'oracle_utility':np.maximum(best-HURDLE,0.)}


def uncertainty_example():
    mu=.2;mean_variance=.0025;future_noise_variance=1.
    norm=NormalDist()
    return {'posterior_mean':mu,'posterior_mean_variance':mean_variance,
        'independent_future_noise_variance':future_noise_variance,
        'latent_mean_positive_probability':norm.cdf(mu/math.sqrt(mean_variance)),
        'future_outcome_positive_probability':norm.cdf(mu/math.sqrt(mean_variance+future_noise_variance)),
        'calibrated_financial_forecast':False}


def _summary(a):
    a=np.asarray(a,dtype=float)
    return {'mean':float(a.mean()),'mc_standard_error':float(a.std(ddof=1)/math.sqrt(len(a)))}


def run():
    rng=np.random.Generator(np.random.PCG64(SEED));a=np.linspace(-.3,.3,G)
    cells=[];checks=0
    for n,tau,rho,world in itertools.product((4,12,48),(0.,.1,.4),(0.,.6),('stable','reversal','wrong_center')):
        delta=tau*rng.standard_normal((REPLICATIONS,G))
        eps=(math.sqrt((1-rho)/n)*rng.standard_normal((REPLICATIONS,G))
             +math.sqrt(rho/n)*rng.standard_normal((REPLICATIONS,1)))
        y=a+delta+eps;am=-a if world=='wrong_center' else a
        s=-1 if world=='reversal' else 1;truth=a+s*delta
        es=estimates(y,am,n,tau,rho);risks=analytic_risks(a,am,s,n,tau,rho)
        ds={name:decision_metrics(pred,truth) for name,pred in es.items()}
        models={}
        for name,pred in es.items():
            mse=_summary(((pred-truth)**2).mean(axis=1));closed=risks[name]
            if abs(mse['mean']-closed)>6*mse['mc_standard_error']+1e-11:
                raise AssertionError(f'analytic MSE mismatch: {n,tau,rho,world,name}')
            d=ds[name]
            if np.min(d['regret'])< -1e-12 or np.min(d['oracle_utility']-d['utility'])< -1e-12:
                raise AssertionError('oracle regret negative')
            checks+=1
            models[name]={'mse':mse,'analytic_mse':closed,
                'selected_true_opportunity':_summary(d['actual']),
                'top_three_regret':_summary(d['regret']),
                'selection_optimism':_summary(d['optimism']),
                'act_fraction':float(d['acted'].mean()),'utility':_summary(d['utility']),
                'utility_regret':_summary(d['oracle_utility']-d['utility']),
                'paired_utility_minus_unconditioned':_summary(d['utility']-ds['unconditioned']['utility']),
                'paired_utility_minus_hard_cell':_summary(d['utility']-ds['hard_cell']['utility'])}
        cells.append({'n':n,'tau':tau,'rho':rho,'world':world,'models':models})
    # Nondegenerate flat-center diagnostic, outside the main center-stress grid.
    y=rng.normal(size=(1000,G));es=estimates(y,np.zeros(G),12,.4,.6)
    ranks={name:np.argsort(-value,axis=1,kind='stable')[:,:3] for name,value in es.items()}
    invariance={name:bool(np.array_equal(ranks[name],ranks['hard_cell']))
                for name in ('scalar_oracle','joint_oracle')}
    if not all(invariance.values()):raise AssertionError('positive flat-center rank invariant failed')
    return {'flags':FLAGS,'seed':SEED,'generator':'numpy.PCG64','replications_per_cell':REPLICATIONS,
        'cell_count':len(cells),'analytic_mse_checks':checks,'hyperparameters_fitted':False,
        'standardized_hurdle_not_market_cost':HURDLE,'structural_center':a.tolist(),
        'flat_center_rank_invariance_1000_cases':invariance,'uncertainty_example':uncertainty_example(),
        'environment':{'python':sys.version.split()[0],'numpy':np.__version__},
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cells':cells}

if __name__=='__main__':
    print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
