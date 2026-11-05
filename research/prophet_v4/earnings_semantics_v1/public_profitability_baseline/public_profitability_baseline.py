"""Fixed public research-portfolio comparison, not a Prophet model or execution test."""
from pathlib import Path
import argparse,hashlib,io,json,math,re,sys,urllib.request,zipfile
import numpy as np
import pandas as pd
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',required=True,help='New isolated evidence directory; never an existing result')
parser.add_argument('--archive',type=Path,help='Optional exact previously captured public archive')
args=parser.parse_args()
ROOT=Path(args.output_dir).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
protocol_path=Path(__file__).resolve().parent/'public-profitability-protocol.json'
protocol_raw=protocol_path.read_bytes()
assert hashlib.sha256(protocol_raw).hexdigest()=='3e931f5a98e3b1002971e4ef2b36378bb50654b37037b4032dcfdbdc6833c2bd'
protocol=json.loads(protocol_raw)
output=ROOT/'public-profitability-result.json'
assert not output.exists(),'Existing result must be consumed, not silently rerun or replaced'
if args.archive is not None:
    assert args.archive.stat().st_size<=4_000_000
    raw=args.archive.read_bytes()
else:
    with urllib.request.urlopen(protocol['download'],timeout=35) as response:
        raw=response.read(4_000_001)
assert hashlib.sha256(raw).hexdigest()=='b365749f6f1bfad2484b8f539197d3fc8874863bf49067ffb70c7fe8ec9bfafc','Public dataset revision changed; do not silently relabel a new vintage as the original study'
assert len(raw)<=4_000_000,'Dataset exceeds declared bounded read'
(ROOT/'25_Portfolios_ME_OP_5x5_CSV.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    names=[x for x in archive.namelist() if x.lower().endswith('.csv')]
    assert len(names)==1,names
    text=archive.read(names[0]).decode('utf-8-sig')
lines=text.splitlines()
first=next(i for i,line in enumerate(lines) if re.match(r'^\s*\d{6},',line))
header=next(lines[i] for i in range(first-1,-1,-1) if lines[i].startswith(','))
assert 'Value Weighted' in '\n'.join(lines[:first]),'First source table is not declared value weighted'
block=[]
for line in lines[first:]:
    if not re.match(r'^\s*\d{6},',line):break
    block.append(line)
data=pd.read_csv(io.StringIO(header+'\n'+'\n'.join(block)),index_col=0)
data.columns=[x.strip() for x in data.columns]
data.index=pd.PeriodIndex(data.index.astype(str),freq='M')
assert data.index.is_unique and data.index.is_monotonic_increasing
mapping={}
for label in data.columns:
    tokens=label.upper().split()
    assert len(tokens)==2,(label,tokens)
    size={'SMALL':1,'BIG':5}.get(tokens[0])
    if size is None:
        match=re.fullmatch(r'ME([1-5])',tokens[0]);assert match,label;size=int(match[1])
    op={'LOOP':1,'HIOP':5}.get(tokens[1])
    if op is None:
        match=re.fullmatch(r'OP([1-5])',tokens[1]);assert match,label;op=int(match[1])
    assert (size,op) not in mapping;mapping[(size,op)]=label
assert set(mapping)=={(s,p) for s in range(1,6) for p in range(1,6)}
data=data.replace([-99.99,-999.0],np.nan).astype(float)/100
sample=data.loc[protocol['start']:protocol['end_inclusive']]
assert sample.index.equals(pd.period_range(protocol['start'],protocol['end_inclusive'],freq='M'))
assert np.isfinite(sample.to_numpy()).all() and (sample.to_numpy()>-1).all()
series={}
for name,rank in [('LOW_OP',1),('MIDDLE_OP',3),('HIGH_OP',5)]:
    columns=[mapping[(size,rank)] for size in range(1,6)]
    series[name]=sample[columns].mean(axis=1)
    assert np.allclose(series[name],sum(sample[col] for col in reversed(columns))/5)

def metrics(x):
    assert len(x)>1 and np.isfinite(x.to_numpy()).all()
    wealth=np.cumprod(1+x.to_numpy());peaks=np.maximum.accumulate(np.r_[1.0,wealth])[1:]
    return {'months':len(x),'cagr':float(wealth[-1]**(12/len(x))-1),
            'annualized_mean':float(12*x.mean()),'annualized_monthly_volatility':float(np.sqrt(12)*x.std(ddof=1)),
            'max_monthly_observed_drawdown':float(np.min(wealth/peaks-1)),
            'worst_month':float(x.min()),'worst_5pct_mean':float(x.nsmallest(math.ceil(.05*len(x))).mean())}
results=[]
eras=[['ALL',protocol['start'],protocol['end_inclusive']]]+[[a+'_'+b,a,b] for a,b in protocol['eras']]
for era,a,b in eras:
    for name,x in series.items():results.append({'era':era,'portfolio':name,**metrics(x.loc[a:b])})
spread=series['HIGH_OP']-series['LOW_OP'];delta=spread.to_numpy();n=len(delta);L=12;reps=4000
rng=np.random.default_rng(20260930)
starts=rng.integers(0,n-L+1,size=(reps,math.ceil(n/L)))
indices=(starts[:,:,None]+np.arange(L)).reshape(reps,-1)[:,:n]
means=delta[indices].mean(axis=1)*12
ci=np.quantile(means,[.025,.975]).tolist()
matched=[]
for size in range(1,6):
    high=sample[mapping[(size,5)]];low=sample[mapping[(size,1)]]
    matched.append({'size_quintile':size,'high_minus_low_annualized_mean':float((high-low).mean()*12),
                    'high_op':metrics(high),'low_op':metrics(low)})
result={'schema':'prophet.public_profitability_descriptive_result/v1',
 'protocol_sha256':hashlib.sha256(protocol_raw).hexdigest(),
 'source':{'url':protocol['download'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
           'table':'FIRST_MONTHLY_VALUE_WEIGHTED_RETURNS','columns':list(data.columns),
           'first_available':str(data.index.min()),'last_available':str(data.index.max())},
 'sample':{'first':str(sample.index.min()),'last':str(sample.index.max()),'months':len(sample)},
 'results':results,'matched_size_results':matched,
 'high_minus_low':{'annualized_arithmetic_mean':float(spread.mean()*12),'exploratory_95pct_moving_block_interval':ci,
                   'block_months':12,'resamples':reps,'seed':20260930,
                   'positive_spread_month_fraction':float((spread>0).mean())},
 'checks':{'all_25_named_cells_resolved':True,'complete_fixed_month_sample':True,
           'no_missing_or_imputed_returns':True,'identical_size_weights_in_all_arms':True,
           'column_order_invariance':True,'no_outcome_fit_or_parameter_search':True},
 'environment':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__},
 'limits':protocol['limitations']+[protocol['costs']],
 'state':'EXPLORATORY_PUBLIC_RESEARCH_NOT_NATIVE_PROMOTION','rank_authority':False,'entry_authority':False}
encoded=(json.dumps(result,indent=2,allow_nan=False)+'\n').encode();output.write_bytes(encoded)
print('PUBLIC_RESULT_SHA256',hashlib.sha256(encoded).hexdigest())
print(json.dumps({'sample':result['sample'],'primary':result['high_minus_low'],'all_eras':results,
                  'size_contrasts':[{'size_quintile':x['size_quintile'],'high_minus_low_annualized_mean':x['high_minus_low_annualized_mean']} for x in matched]},indent=2))
