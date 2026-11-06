"""Incident-cohort view of the SAME study traces; no new independent sample."""
from pathlib import Path
import json
import numpy as np
from rolling_capacity import make_arrivals, simulate
root=Path(__file__).resolve().parent
p=json.loads((root/'capacity_inputs.json').read_text())
start=p['warmup_days']*1440+300;end=start+720
rows=[]
for seed in p['seeds']:
    a=make_arrivals(p,seed);mask=(a>=start)&(a<end)
    for n in (3,4):
        b=simulate(a,n);r=simulate(a,n,outages=[(start,end)])
        wait=r.service[mask]-a[mask]
        rows.append({'seed':seed,'accounts':n,'reports':int(mask.sum()),
            'within_6h_pct':float(np.mean(wait<=360)*100),
            'p95_delay_hours':float(np.percentile(wait,95)/60),
            'outage_cohort_cleared_hours_after_reopen':float((r.service[mask].max()-end)/60),
            'mean_added_delay_hours':float(np.mean((r.service-b.service)[mask])/60)})
out={'scope':'Same existing 16 traces; incident cohort only, not additional independent samples',
     'outage_hours':[5,17],'raw':rows,'aggregate':[]}
for n in (3,4):
    g=[x for x in rows if x['accounts']==n]
    out['aggregate'].append({'accounts':n,**{k:float(np.mean([x[k] for x in g]))
      for k in ('reports','within_6h_pct','p95_delay_hours','outage_cohort_cleared_hours_after_reopen','mean_added_delay_hours')}})
print(json.dumps(out,indent=2))
