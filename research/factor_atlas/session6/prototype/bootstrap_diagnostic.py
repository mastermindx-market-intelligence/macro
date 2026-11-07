"""Finite-sample coverage test of whole-block percentile resampling; synthetic only."""
from pathlib import Path
import hashlib, json, math
import numpy as np
from scipy.stats import norm, t
ROOT=Path(__file__).resolve().parent
P=ROOT/'bootstrap_diagnostic_spec.json'
s=json.loads(P.read_text()); rng=np.random.default_rng(s['seed']); out=[]

def interval(k,n):
    z=norm.ppf(.975); p=k/n; den=1+z*z/n
    m=(p+z*z/(2*n))/den; d=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [m-d,m+d]

for h in s['horizons']:
    counts={'block_percentile':0,'oracle':0,'nonoverlap_Student':0}
    d=s['sessions']; f=s['factors']; rho=s['common_share']; scale=s['loss_scale']
    # Average over F independent idiosyncratic terms analytically; same Gaussian law.
    sigma=scale*math.sqrt(rho+(1-rho)/f)
    k=np.arange(1,h); vif=1+2*np.sum((1-k/d)*(1-k/h)); se=sigma*math.sqrt(vif/d)
    for _ in range(s['replications']):
        innovations=rng.normal(size=d+h-1)
        daily=np.convolve(innovations,np.ones(h)/math.sqrt(h),mode='valid')*sigma
        blockmeans=daily.reshape(12,21).mean(axis=1)
        draws=rng.integers(0,12,size=(s['resamples'],12))
        bmeans=blockmeans[draws].mean(axis=1)
        low,high=np.quantile(bmeans,[.025,.975])
        counts['block_percentile']+=int(low>0 or high<0)
        counts['oracle']+=int(abs(daily.mean())>norm.ppf(.975)*se)
        nonoverlap=daily[::h]
        width=t.ppf(.975,len(nonoverlap)-1)*nonoverlap.std(ddof=1)/math.sqrt(len(nonoverlap))
        counts['nonoverlap_Student']+=int(abs(nonoverlap.mean())>width)
    out.append({'horizon':h,'counts':counts,'rates':{name:{'rate':k/s['replications'],
      'monte_carlo_wilson_95':interval(k,s['replications'])} for name,k in counts.items()}})
res={'status':s['status'],'spec_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
 'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':out,'limits':s['limitation']}
(ROOT.parent/'evidence/bootstrap_diagnostic_results.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
