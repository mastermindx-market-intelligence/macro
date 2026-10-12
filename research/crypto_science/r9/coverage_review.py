"""Post-run descriptive decomposition of R9 coverage; no forecast/threshold change."""
from pathlib import Path
import json
import pandas as pd
P=Path(__file__).resolve().parent
H=pd.Timedelta(hours=1)

def main():
    f=pd.read_csv(P/'predictions.csv');e=pd.read_csv(P/'events.csv');rows=[]
    for frame in [f,e]:
        for k in ['issue','entry','end','break_issue','confirm']:
            if k in frame:frame[k]=pd.to_datetime(frame[k])
    for x in e.loc[e.category.eq('lower_first')&e.break_issue.ge(pd.Timestamp('2018-01-01'))].itertuples():
        g=f.loc[(f.lag_hours==x.lag_hours)&(f.issue<x.break_issue)&(f.issue>=x.break_issue-24*H)&(f.entry<x.break_issue)&(f.end>=x.confirm)]
        pre=g.loc[g.watch_status=='prebreak'];feat=pre.loc[pre.feature_status=='ok'];qualified=feat.loc[feat.forecast_status=='ok']
        if not len(g):reason='no_issued_clock_meets_lead_and_expiry'
        elif not len(pre):reason='no_past_qualified_prebreak_context'
        elif not len(feat):reason='price_or_target_history_unavailable'
        elif not len(qualified):reason='forecast_fit_unavailable'
        else:reason='supported'
        assert (reason=='supported')==x.supported
        rows.append({'event_id':x.event_id,'break_issue':str(x.break_issue),'lag_hours':x.lag_hours,'reason':reason,
                     'temporally_possible_clocks':len(g),'prebreak_clocks':len(pre),'known_feature_clocks':len(feat),'qualified_clocks':len(qualified),
                     'past_context_statuses':g.watch_status.value_counts().to_dict()})
    counts=[];frame=pd.DataFrame(rows)
    for lag in [1,6]:
        for period,lo in [('all_issued','2018-01-01'),('reused_2024plus','2024-01-01')]:
            v=frame.loc[(frame.lag_hours==lag)&pd.to_datetime(frame.break_issue).ge(pd.Timestamp(lo))]
            counts.append({'period':period,'lag_hours':lag,'events':len(v),'reasons':v.reason.value_counts().to_dict()})
    out={'classification':'POST_RUN_DESCRIPTIVE_COVERAGE_AUDIT_NO_RESELECTION','rows':rows,'counts':counts,
         'note':'Hierarchical diagnostic of the already frozen support predicate; labels/forecast/threshold/episode selection and original results unchanged. No new model test.'}
    target=P/'coverage_review.json'
    if target.exists():assert json.loads(target.read_text())==out,'Coverage audit differs; reconcile'
    else:target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(counts,indent=2))

if __name__=='__main__':main()
