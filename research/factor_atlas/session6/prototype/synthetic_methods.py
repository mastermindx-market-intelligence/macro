"""Synthetic diagnostics; does not fit or evaluate any market observation."""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import norm, t

ROOT=Path(__file__).resolve().parents[1]
P=Path(__file__).with_name('synthetic_design.json')
SPEC=json.loads(P.read_text())
RNG=np.random.default_rng(SPEC['seed'])
N=SPEC['monte_carlo_replications']; D=SPEC['sessions']; F=SPEC['factors']
RHO=SPEC['same_date_common_component_share']; SCALE=SPEC['paired_loss_scale']

def rolling(z,h):
    c=np.cumsum(np.concatenate([np.zeros_like(z[:, :1]),z],axis=1),axis=1)
    return (c[:,h:]-c[:,:-h])/math.sqrt(h)

def wilson(k,n,z=1.959963984540054):
    p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]

null=[]
for H in SPEC['overlap_horizons']:
    common=rolling(RNG.normal(size=(N,D+H-1,1)),H)
    individual=rolling(RNG.normal(size=(N,D+H-1,F)),H)
    panel=SCALE*(math.sqrt(RHO)*common+math.sqrt(1-RHO)*individual)
    means=panel.mean(axis=(1,2)); daily=panel.mean(axis=2)
    pooled=panel.std(axis=(1,2),ddof=1)/math.sqrt(D*F)
    date=daily.std(axis=1,ddof=1)/math.sqrt(D)
    blocks=daily.reshape(N,12,21).mean(axis=2)
    blockse=blocks.std(axis=1,ddof=1)/math.sqrt(12)
    k=np.arange(1,H)
    time_inflation=1+2*np.sum((1-k/D)*(1-k/H))
    oracle_se=SCALE*math.sqrt((RHO+(1-RHO)/F)*time_inflation/D)
    critical={'pooled_iid_normal':norm.ppf(.975)*pooled,
              'date_iid_student':t.ppf(.975,D-1)*date,
              '21_session_block_student':t.ppf(.975,11)*blockse,
              'oracle_known_covariance_normal':np.full(N,norm.ppf(.975)*oracle_se)}
    rates={}
    for name,halfwidth in critical.items():
        failed=int(np.count_nonzero(np.abs(means)>halfwidth))
        rates[name]={'false_positive_count':failed,'rate':failed/N,'monte_carlo_wilson_95':wilson(failed,N),'median_interval_half_width':float(np.median(halfwidth))}
    null.append({'horizon':H,'raw_rows_per_replication':D*F,'sessions':D,'calendar_blocks':12,
                 'known_date_variance_inflation':float(time_inflation),'independent_date_equivalents':float(D/time_inflation),
                 'oracle_se':oracle_se,'mean_of_replication_means':float(means.mean()),'methods':rates})
    del panel,common,individual

TR=SPEC['transform_example']; x=RNG.uniform(-3,3,TR['train_n']); xt=RNG.uniform(-3,3,TR['test_n'])
y=np.tanh(x)+RNG.normal(0,TR['noise_sd'],len(x));yt=np.tanh(xt)+RNG.normal(0,TR['noise_sd'],len(xt))
transform={}
for basis,degree in [('weak',1),('strong',9)]:
    A=np.column_stack([(x/3)**j for j in range(degree+1)])
    AT=np.column_stack([(xt/3)**j for j in range(degree+1)])
    C=np.column_stack([A,np.tanh(x)]);CT=np.column_stack([AT,np.tanh(xt)])
    pa=AT@np.linalg.lstsq(A,y,rcond=None)[0];pc=CT@np.linalg.lstsq(C,y,rcond=None)[0]
    la=float(np.mean((yt-pa)**2));lc=float(np.mean((yt-pc)**2))
    transform[basis]={'base_test_mse':la,'augmented_test_mse':lc,'relative_gain':(la-lc)/la}

power=[]
PS=SPEC['power_scenarios']; q=PS['BY_q']; m=PS['tests_for_BY_illustration']; hm=sum(1/j for j in range(1,m+1)); a=q/(m*hm)
for sd in PS['independent_unit_sd']:
    n_plain=math.ceil(((norm.ppf(.975)+norm.ppf(.8))*sd/PS['paired_gain'])**2)
    n_by=math.ceil(((norm.ppf(1-a)+norm.ppf(.8))*sd/PS['paired_gain'])**2)
    power.append({'assumed_independent_unit_sd':sd,'gain_detected_against_zero':PS['paired_gain'],
                  'n_two_sided_alpha_005':n_plain,'n_one_sided_first_BY_discovery':n_by})

# All toy claims are mathematical identities, not sampled market findings.
p=.7; copies=5; wrong=p**copies/(p**copies+(1-p)**copies)
toys={'xor':{'individual_brier':.25,'joint_brier':0.,'joint_observation_adds_information':True},
      'duplicated_evidence':{'true_probability':p,'independent_copy_assumption':wrong,'number_identical_copies':copies,'honest_expected_brier':p*(1-p),'duplicated_expected_brier':p*(1-p)+(wrong-p)**2},
      'pressure_80pct_coverage':{'total_gross':100000000,'classified_gross':80000000,'classified_signed':5000000,'unknown_gross':20000000,'signed_lower':-15000000,'signed_upper':25000000,'sign_identified':False},
      'zero_observed_user_errors': [{'independent_users':n,'one_sided_95_upper_error_rate':1-.05**(1/n)} for n in [30,60,100,300]],
      'BY_first_threshold':{'m':m,'q':q,'harmonic':hm,'threshold':a}}

result={'scope':SPEC['scope'],'protocol_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'environment':{'python':sys.version.split()[0],'numpy':np.__version__,'scipy':scipy.__version__},
        'synthetic_only':True,'null_dependence':null,'deterministic_transform_example':transform,'power_scenarios':power,'analytic_toys':toys,
        'limits':'Not empirical market effects or a calibrated production inference method. Oracle knows simulation covariance only; these null laws do not establish coverage for other data processes.'}
(ROOT/'evidence/synthetic_methods_results.json').write_text(json.dumps(result,indent=2)+'\n')
print('NULL SIMULATION: 1000 independent synthetic replications per horizon')
for v in null:
    print('H=',v['horizon'],'effective_date_equivalents=',round(v['independent_date_equivalents'],2),{k:round(x['rate'],3) for k,x in v['methods'].items()})
print('TRANSFORM',json.dumps(transform))
print('POWER',json.dumps(power))
print('TOYS',json.dumps(toys))
print('protocol_sha256',result['protocol_sha256'])
print('code_sha256',result['code_sha256'])
