#!/usr/bin/env python3
"""Summarize frozen results for the research report; no new rule search."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import study as st

p=Path(__file__).parent/'results'
e=pd.read_parquet(p/'base_events.parquet');piv=pd.read_parquet(p/'reference_pivots.parquet')
lock=json.loads((p/'selection_lock.json').read_text());v=pd.read_csv(p/'development_validation.csv')
cols=['rule_id','side','stoch_tf','stoch_mode','macd_tf','macd_mode','filter','split','n','assets','groups','quarters',
      'qualified_n','timely_durable_n','timely_durable_rate','qualified_survival63','survival63','recall','balance_score','median_age','median_distance_atr']
v[cols].to_csv(p/'full_grid_development_validation.csv',index=False,float_format='%.6g')
rows=[];years=[]
for x in lock['selected']:
    r=x['rule'];q=st.select_events(e,r)
    qual=q[q.qualified]
    ci=st.interval(qual,field='survive63');yi=st.interval(qual,field='survive63',cluster='year')
    z=v[(v.rule_id==r['rule_id'])&(v['split']=='validation')].iloc[0]
    rows.append({'rule_id':r['rule_id'],'selection_reasons':';'.join(x['selection_reasons']),
                 'validation_n':int(z.n),'validation_precision':z.timely_durable_rate,'validation_recall':z.recall,
                 'qualified_survival_ci_low':ci[0],'qualified_survival_ci_high':ci[1],
                 'qualified_survival_year_ci_low':yi[0],'qualified_survival_year_ci_high':yi[1],
                 'strict_timely_durable_rate':float((q.qualified*q.strict63).mean()),
                 'strict_qualified_survival':qual.strict63.mean(),
                 'within_age_n':int((q.age<=21).sum()),'within_distance_n':int((q.distance<=2).sum()),
                 'deep_price_n':int((q.depth>=4).sum()),
                 'last_evaluable_signal':str(q.date.max().date()) if len(q) else '',
                 'successes_2020':int(q.loc[q.date.dt.year.eq(2020),'primary63'].sum()),
                 'total_successes':int(q.primary63.sum())})
    for year,g in q.groupby(q.date.dt.year):
        years.append({'rule_id':r['rule_id'],'year':year,'n':len(g),'qualified_n':int(g.qualified.sum()),
                      'successes':int(g.primary63.sum()),'precision':g.primary63.mean(),
                      'conditional_survival':g.loc[g.qualified,'survive63'].mean()})
pd.DataFrame(rows).to_csv(p/'selected_diagnostics.csv',index=False)
pd.DataFrame(years).to_csv(p/'by_year.csv',index=False)
pd.DataFrame([{'side':side,'split':sp,'pool':pool,'pivots':len(g),'assets':g.ticker.nunique()}
              for (side,sp,pool),g in piv.assign(pool=np.where(piv.asset_class.eq('crypto'),'crypto','primary')).groupby(['side','split','pool'])]).to_csv(p/'pivot_counts.csv',index=False)

# Illustrative charts: fixed instruments/dates from major historical reversals,
# showing successes and failures without using them to select a rule.
_,data,items,eqcal,_=st.load_inputs(Path(__file__).parent/'data/input_manifest.json')
chart_specs=[('SPY','2020-01-01','2020-12-31'),('SPY','2022-01-01','2023-06-30'),
             ('TLT','2021-01-01','2024-06-30'),('NVDA','2021-01-01','2023-06-30')]
chart_rows=[];event_rows=[]
for ticker,a,b in chart_specs:
    d=data[ticker];f=st.features(d,eqcal)
    z=d.loc[a:b,['open','high','low','close']].copy()
    z['weekly_k']=f['1W'].loc[z.index,'k'];z['weekly_d']=f['1W'].loc[z.index,'d']
    z['weekly_hist_atr']=f['1W'].loc[z.index,'hnorm'];z['weekly_q20']=f['1W'].loc[z.index,'q20']
    z['three_day_hist_atr']=f['3D'].loc[z.index,'hnorm']
    z['daily_hist_atr']=f['1D'].loc[z.index,'hnorm'];z['ticker']=ticker;z['chart']=ticker+'_'+a[:4]
    chart_rows.append(z.reset_index())
    rid='bottom|S1W:curl|M1W:deep'
    qe=e[e.ticker.eq(ticker)&e.base.eq(rid)&e.date.between(a,b)].copy()
    qe['chart']=ticker+'_'+a[:4]
    event_rows.append(qe[['chart','ticker','date','candidate_date','candidate_price','signal_close','atr_p','age','distance','depth','qualified','primary63','survive63','strict63','matched_pivot','split63']])
pd.concat(chart_rows).to_csv(p/'illustrative_prices.csv',index=False,float_format='%.8g')
pd.concat(event_rows).to_csv(p/'illustrative_events.csv',index=False)
print('EXPORT_COMPLETE',len(v),len(rows),len(years),flush=True)
