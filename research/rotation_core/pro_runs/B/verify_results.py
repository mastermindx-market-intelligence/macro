"""Independent vectorized accounting cross-check on the four market/bill rules."""
import json
import numpy as np
import pandas as pd
from inputs import ROOT,french

def main():
    f=french('factors')[0][1]
    choices=pd.read_pickle(ROOT/'audit_choices.pkl')
    observed=pd.read_pickle(ROOT/'audit_paths.pkl')
    checks={}
    for rid in ['R1','R2','R3','R4']:
        e=choices[rid].eq('M').astype(float).where(choices[rid].notna())
        holding=e.shift(2).fillna(0);execution=e.shift(1).fillna(0)
        c=pd.Series(np.where(f.index<pd.Timestamp('1975-01-01'),.0025,.0005),index=f.index)
        expected=(1+holding*(f['Mkt-RF']+f.RF)+(1-holding)*f.RF)*(1-c*(execution-holding).abs())-1
        mask=observed[rid].notna()
        checks[rid]=float((expected[mask]-observed.loc[mask,rid]).abs().max())
        assert checks[rid]<1e-12
    receipt={'independent_vectorized_market_rules_max_abs_error':checks,'checked_rows':{r:int(observed[r].notna().sum()) for r in checks}}
    (ROOT/'out'/'independent_checks.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))

if __name__=='__main__':main()
