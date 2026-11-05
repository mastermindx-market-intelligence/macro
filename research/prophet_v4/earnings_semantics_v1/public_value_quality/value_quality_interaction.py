"""Fixed public diagnostic; never a native Prophet ranker or promotion test."""
from pathlib import Path
import argparse, hashlib, io, itertools, json, math, re, urllib.request, zipfile
import numpy as np
import pandas as pd

URL='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/32_Portfolios_ME_BEME_OP_2x4x4_CSV.zip'
PROTOCOL_SHA='499ed313bfab7a9bc770b35f0a0cf5f8b08a3988997c7003232f77fac8885989'

def labels(name):
    words=name.upper().split()
    if len(words)!=3: raise ValueError('Unexpected column identity: '+name)
    a,b,c=words
    size={'SMALL':1,'BIG':2,'ME1':1,'ME2':2}.get(a)
    bm={'LOBM':1,'BM1':1,'BM2':2,'BM3':3,'BM4':4,'HIBМ':4,'HIBM':4}.get(b)
    op={'LOOP':1,'OP1':1,'OP2':2,'OP3':3,'OP4':4,'HIOP':4}.get(c)
    if None in (size,bm,op): raise ValueError('Unexpected column identity: '+name)
    return size,bm,op

def read_monthly(raw):
    z=zipfile.ZipFile(io.BytesIO(raw));files=[n for n in z.namelist() if n.lower().endswith('.csv')]
    assert len(files)==1
    text=z.read(files[0]).decode('utf-8-sig');lines=text.splitlines()
    first=next(i for i,l in enumerate(lines) if re.match(r'^\s*\d{6},',l))
    assert 'Average Value Weighted Returns -- Monthly' in '\n'.join(lines[:first])
    header=next(lines[j] for j in range(first-1,-1,-1) if lines[j].lstrip().startswith(','))
    block=[]
    for line in lines[first:]:
        if not re.match(r'^\s*\d{6},',line):break
        block.append(line)
    d=pd.read_csv(io.StringIO(header+'\n'+'\n'.join(block)),index_col=0)
    d.columns=[c.strip() for c in d.columns];mapping={c:labels(c) for c in d.columns}
    assert len(mapping)==32 and len(set(mapping.values()))==32
    assert set(mapping.values())==set(itertools.product([1,2],range(1,5),range(1,5)))
    d.index=pd.PeriodIndex(d.index.astype(str),freq='M')
    assert d.index.is_unique and d.index.is_monotonic_increasing
    d=d.replace([-99.99,-999.],np.nan).astype(float)/100
    d=d.loc['1963-07':'2026-08'];assert d.index.equals(pd.period_range('1963-07','2026-08',freq='M'))
    assert np.isfinite(d.values).all() and (d.values>-1).all()
    return d,mapping

def grid(d,mapping):
    result={}
    for bm,op in itertools.product(range(1,5),repeat=2):
        cols=[c for c in d.columns if mapping[c][1:]==(bm,op)]
        assert len(cols)==2 and {mapping[c][0] for c in cols}=={1,2}
        result[f'BM{bm}_OP{op}']=d[cols].mean(axis=1)
    return pd.DataFrame(result,index=d.index)

def contrast(g):
    return (g.BM4_OP4-g.BM4_OP1)-(g.BM1_OP4-g.BM1_OP1)

def metric(series):
    nav=(1+series).cumprod().values;peak=np.maximum.accumulate(np.r_[1,nav])[1:]
    return {'months':len(series),'cagr':float(nav[-1]**(12/len(series))-1),
        'annualized_arithmetic_mean':float(series.mean()*12),
        'annualized_monthly_volatility':float(series.std()*np.sqrt(12)),
        'maximum_monthly_observed_drawdown':float((nav/peak-1).min()),
        'worst_month':float(series.min()),
        'worst_5pct_month_mean':float(series.nsmallest(math.ceil(len(series)*.05)).mean())}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--archive',type=Path)
    parser.add_argument('--expected-archive-sha256');a=parser.parse_args()
    assert hashlib.sha256(a.protocol.read_bytes()).hexdigest()==PROTOCOL_SHA
    assert not a.output_dir.exists(),'Refuse existing results; use a new output directory'
    if a.archive:raw=a.archive.read_bytes()
    else:
        with urllib.request.urlopen(URL,timeout=40) as response:raw=response.read()
    digest=hashlib.sha256(raw).hexdigest()
    if a.expected_archive_sha256:assert digest==a.expected_archive_sha256,'Different public vintage'
    d,mapping=read_monthly(raw);g=grid(d,mapping);test=grid(d[d.columns[::-1]],mapping)
    assert np.allclose(g.values,test.values,rtol=0,atol=0)
    fake=pd.DataFrame({c:np.arange(5)*.001+size*.003+bm*.004+op*.002
        for c,(size,bm,op) in mapping.items()})
    assert np.allclose(contrast(grid(fake,mapping)).values,0,atol=1e-14)
    eras=[('all','1963-07','2026-08'),('1963_1989','1963-07','1989-12'),
          ('1990_2009','1990-01','2009-12'),('2010_2026','2010-01','2026-08')]
    arms=['BM1_OP1','BM1_OP4','BM4_OP1','BM4_OP4']
    results=[];effects=[]
    for era,start,end in eras:
        group=g.loc[start:end]
        for arm in arms:results.append({'era':era,'arm':arm,**metric(group[arm])})
        effects.append({'era':era,'months':len(group),
            'profitability_spread_low_bm':float((group.BM1_OP4-group.BM1_OP1).mean()*12),
            'profitability_spread_high_bm':float((group.BM4_OP4-group.BM4_OP1).mean()*12),
            'value_spread_high_op':float((group.BM4_OP4-group.BM1_OP4).mean()*12),
            'interaction':float(contrast(group).mean()*12)})
    delta=contrast(g).values;n=len(delta);L=12;rng=np.random.default_rng(20260930)
    starts=rng.integers(0,n-L+1,size=(4000,math.ceil(n/L)))
    idx=(starts[:,:,None]+np.arange(L)).reshape(4000,-1)[:,:n]
    means=delta[idx].mean(axis=1)*12
    individual=[]
    for size in [1,2]:
        x={f'BM{bm}_OP{op}':d[c] for c,(sz,bm,op) in mapping.items() if sz==size}
        individual.append({'size':size,'interaction':float(contrast(pd.DataFrame(x)).mean()*12)})
    output={'schema':'prophet.public_value_quality_interaction_result/v1','protocol_sha256':PROTOCOL_SHA,
        'archive_sha256':digest,'archive_bytes':len(raw),'source_url':URL,
        'sample':{'first':str(d.index[0]),'last':str(d.index[-1]),'months':len(d)},
        'column_identities':{k:list(v) for k,v in mapping.items()},'results':results,'contrasts':effects,
        'primary':{'annualized_arithmetic_interaction':float(delta.mean()*12),
            'exploratory_95pct_paired_block_interval':np.quantile(means,[.025,.975]).tolist(),
            'block_months':12,'resamples':4000,'seed':20260930},
        'size_specific_interactions':individual,
        'checks':{'all_cells_and_months_complete':True,'column_permutation_invariant':True,
            'fixed_equal_size_weights':True,'synthetic_additive_null':True,'no_missing_as_zero':True},
        'scope':'Gross revised public research portfolios; no native prices/outcomes/ranks, no factor-model fitting or causal/alpha claim'}
    a.output_dir.mkdir(parents=True);(a.output_dir/'input.zip').write_bytes(raw)
    data=(json.dumps(output,sort_keys=True,indent=2)+'\n').encode();(a.output_dir/'result.json').write_bytes(data)
    print('RESULT_SHA256',hashlib.sha256(data).hexdigest())
    print(json.dumps({k:v for k,v in output.items() if k not in ['column_identities']},indent=2))

if __name__=='__main__':main()
