"""Attribution diagnostics requested by the frozen protocol and independent review.

No new entry, filter, threshold, position size, or holding policy is selected here.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import analyze as a

def main(root=None):
    root=Path(root or Path(__file__).resolve().parent);out=root/'results'
    events=pd.read_csv(out/'defensive_events.csv',parse_dates=['date','exit_date'])
    archived=pd.read_csv(root/'data/archive/signal_state_events.csv')
    archived=archived[archived.frame.eq('1D')].copy()
    archived['date']=pd.to_datetime(archived.signal_date)
    first=pd.read_csv(out/'archived_first_watch_core.csv')
    first['date']=pd.to_datetime(first.signal_date)
    core_a=archived[archived.panel.eq('CORE5')&archived.cell.eq('JOINT')].copy()
    core_b=first[first.status.eq('FILLED')].copy()
    for z in [core_a,core_b]:assert not z.duplicated(['symbol','date']).any()
    ca=core_a[['symbol','date','entry_date','exit_date','net']].rename(columns={x:'context_'+x for x in ['entry_date','exit_date','net']})
    cb=core_b[['symbol','date','episode','arm_date','entry_date','exit_date','net','entry_horizon_net']].rename(columns={x:'watch_'+x for x in ['entry_date','exit_date','net']})
    rec=ca.merge(cb,on=['symbol','date'],how='outer',indicator='membership')
    rec=rec.merge(archived[['symbol','date','cell']].rename(columns={'cell':'archived_context_at_signal'}),on=['symbol','date'],how='left',validate='one_to_one')
    rec=rec.merge(events[['symbol','date','sequence','watch_id','watch_arm_t']],on=['symbol','date'],how='left',validate='one_to_one')
    def reason(r):
        if r.membership=='both':return 'SAME_SIGNAL_DIFFERENT_ENDPOINT'
        if r.membership=='right_only':
            return 'FIRST_WATCH_CROSS_OUTSIDE_JOINT_CONTEXT' if pd.notna(r.archived_context_at_signal) else 'NO_COMPLETE_CONTEXT_EVENT_UNRESOLVED'
        if r.sequence=='REPEAT':return 'LATER_CROSS_WITHIN_WATCH'
        if r.sequence=='NO_ACTIVE_WATCH':return 'CONTEXT_CROSS_OUTSIDE_ACTIVE_WATCH'
        return 'CONTEXT_ONLY_UNRESOLVED'
    rec['reason']=rec.apply(reason,axis=1)
    rec['endpoint_sessions_differ']=rec.context_exit_date.ne(rec.watch_exit_date)&rec.membership.eq('both')
    rec['watch_minus_signal_horizon_net']=rec.watch_net-rec.entry_horizon_net
    rec.to_csv(out/'v11_cohort_membership.csv',index=False)
    recon={'archived_context_core_joint':len(core_a),'archived_watches':len(first),
           'watch_status_counts':first.status.value_counts().to_dict(),
           'first_watch_filled':len(core_b),'membership_counts':rec.membership.value_counts().to_dict(),
           'reason_counts':rec.reason.value_counts().to_dict(),
           'common_endpoint_differences':int(rec.endpoint_sessions_differ.sum()),
           'context_positive':int((core_a.net>0).sum()),'watch_positive':int((core_b.net>0).sum()),
           'watch_entry_horizon_positive':int((core_b.entry_horizon_net>0).sum()),
           'watch_entry_horizon_available':int(core_b.entry_horizon_net.notna().sum()),
           'watch_mean_return':float(core_b.net.mean()),'watch_mean_entry_horizon_return':float(core_b.entry_horizon_net.mean()),
           'explanation':'Study A requires JOINT on signal date and exits signal+126. Study B arms in JOINT, waits for its first cross, and exits arm+126; the context may change while waiting.'}
    a.dump(out/'v11_cohort_reconciliation.json',a.clean(recon))
    # Post-outcome diagnostics of the already registered account paths.
    paths=pd.read_csv(out/'portfolio_paths.csv',parse_dates=['date'])
    annual=pd.read_csv(out/'portfolio_annual.csv');diagnostics=[]
    for (ex,pop,pol),g in paths.groupby(['experiment','population','policy'],sort=False):
        g=g.sort_values('date').reset_index(drop=True);nav=g.nav.to_numpy();fee=.0005 if ex=='DEFENSIVE' else .001
        exposure=g.held.to_numpy()/(nav+fee*g.held.to_numpy())
        dd=nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1;trough=int(np.argmin(dd))
        peakval=max(1.,nav[:trough+1].max());prior=np.flatnonzero(np.isclose(nav[:trough+1],peakval,rtol=0,atol=1e-12))
        peak=int(prior[-1]) if len(prior) else 0
        later=np.flatnonzero(nav[trough+1:]>=peakval);recover=int(trough+1+later[0]) if len(later) else None
        an=annual[(annual.experiment==ex)&(annual.population==pop)&(annual.policy==pol)&annual.scenario.eq('PRIMARY')]
        full=an[an.year<2026]
        diagnostics.append({'experiment':ex,'population':pop,'policy':pol,'max_drawdown':float(dd[trough]),
           'peak_date':str(g.date.iloc[peak].date()),'trough_date':str(g.date.iloc[trough].date()),
           'recovery_date':str(g.date.iloc[recover].date()) if recover is not None else None,
           'exposure_peak':float(exposure[peak]),'exposure_trough':float(exposure[trough]),
           'max_exposure_before_trough':float(exposure[peak:trough+1].max()),'max_exposure_all':float(exposure.max()),
           'positive_full_calendar_years':int((full['return']>0).sum()),'full_calendar_years':len(full),
           'worst_full_calendar_year':int(full.loc[full['return'].idxmin(),'year']),
           'worst_full_calendar_year_return':float(full['return'].min()),
           'partial_2026_return':float(an.loc[an.year.eq(2026),'return'].iloc[0])})
    pd.DataFrame(diagnostics).to_csv(out/'portfolio_diagnostics.csv',index=False)
    # Accepted-sector paired differences: these are trade-return contrasts, not CAGR CIs.
    manifest=json.loads((root/'data/input_manifest.json').read_text())
    spy=next(x for x in manifest['assets'] if x['ticker']=='SPY')
    ix=pd.read_parquet(spy['path']).loc['2010-01-04':'2026-10-08'].index
    tr=pd.read_csv(out/'portfolio_trades.csv');sector=tr[tr.experiment.eq('SECTOR')&tr.policy.isin(['RSI_SELECTED','RSI_ALL_SECTORS','RSI_SPY'])].copy()
    sector['date']=[ix[int(t)] for t in sector.signal_t]
    p=sector.pivot(index=['nominee','signal_t','date'],columns='policy',values='trade_net').reset_index()
    status=sector.groupby(['nominee','signal_t']).closed.agg(['all','any'])
    assert (status['all']==status['any']).all()
    p=p.merge(status['all'].rename('closed'),on=['nominee','signal_t'],validate='one_to_one')
    p['halfyear']=p.date.dt.year*2+(p.date.dt.month>6).astype(int)
    grid,w=a.block_weights(pd.Timestamp('2020-01-01'),pd.Timestamp('2026-10-08'))
    contrasts=[]
    for comparator in ['RSI_ALL_SECTORS','RSI_SPY']:
        g=p[p.closed].assign(delta=lambda q:q.RSI_SELECTED-q[comparator])
        _,lo,hi,valid,support,eligible=a.boot_mean(g,'delta',grid,w)
        contrasts.append({'comparator':comparator,'n_closed':len(g),'dates':g.date.nunique(),
             'mean_selected_minus_alternative':float(g.delta.mean()),'lo':lo,'hi':hi,
             'selected_beats_alternative':float((g.delta>0).mean()),'valid_draw_fraction':valid,
             'populated_halfyears':support,'interval_available':eligible})
    p.to_csv(out/'sector_accepted_paired.csv',index=False)
    pd.DataFrame(contrasts).to_csv(out/'sector_accepted_contrasts.csv',index=False)
    # Known-low location and horizon survival: necessary durable-pivot diagnostics,
    # not the earlier independent-pivot precision/coverage metric.
    dr=[]
    for (pop,cell),g in events.groupby(['panel','cell']):
        dr.append({'panel':pop,'cell':cell,'n':len(g),'reference_age_median':float(g.reference_age.median()),
          'entry_distance_atr_median':float(g.entry_distance_atr.median()),
          'reference_untouched_126':float((~g.reference_touch_horizon).mean()),
          'reference_not_undercut_126':float((~g.reference_break_horizon).mean()),
          'tolerant_reference_not_broken_126':float((~g.tolerant_reference_break_horizon).mean()),
          'eventual_loser_stop_delta':float((g.loc[g.net<=0,'stop_net']-g.loc[g.net<=0,'net']).mean()),
          'eventual_winner_stop_delta':float((g.loc[g.net>0,'stop_net']-g.loc[g.net>0,'net']).mean())})
    pd.DataFrame(dr).to_csv(out/'reference_location.csv',index=False)
    print(json.dumps(a.clean({'cohort_reconciliation':recon,'sector_accepted_contrasts':contrasts})),flush=True)

if __name__=='__main__':main()
