#!/usr/bin/env python3
"""PB-C selected-panel diagnostics. Does not estimate a population hazard or trade rule.

Offline: python reproduce_pilot.py --directory . --simulations 10000
Inputs are source-verified event records and derived Treasury flags, not raw equities.
All reported permutation probabilities are conditional diagnostics under an incomplete
calendar model. Calendar dependence and selection are not covered by Monte Carlo error.
"""
from __future__ import annotations
import argparse, bisect, collections, csv, datetime as dt, hashlib, json
from pathlib import Path
import numpy as np

SEED = 20261007
FROZEN_UNIVERSE = 'AAPL MSFT AMZN GOOG META NVDA TSLA AMD INTC AVGO MU TSM QCOM ANET VRT DELL HPE COHR LITE ETN ORCL LMT RTX NOC MP ALB CSCO IBM TXN ADBE CAT DE PG KO HON PEP'.split()

def read_json(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def probability_record(obs, sims):
    hits = int(np.sum(sims >= obs))
    p = (hits + 1) / (len(sims) + 1)
    se = float(np.sqrt(p * (1-p) / (len(sims)+1)))
    no_variation=bool(np.all(sims==sims[0]))
    uninformative=no_variation and int(sims[0])==int(obs)
    return {'status':'UNINFORMATIVE_CONSTANT_SIMULATION' if uninformative else ('NO_SIMULATED_VARIATION' if no_variation else 'VARIABLE_SIMULATION'),
            'observed': int(obs), 'null_mean': float(np.mean(sims)), 'null_median': float(np.median(sims)),
            'null_q025': float(np.quantile(sims,.025)),
            'null_q975': float(np.quantile(sims,.975)),
            'one_sided_p_plus_one': None if uninformative else p, 'monte_carlo_se_only': None if uninformative else se,
            'simulations': len(sims), 'exceedances': hits,
            'distinct_simulated_statistic_values':int(len(np.unique(sims))),
            'inference_scope': 'EXPLORATORY_CONDITIONAL_DIAGNOSTIC_NOT_CAUSAL_OR_POPULATION'}

def validate(events, stress, sessions):
    def require(condition,message):
        if not condition: raise ValueError(message)
    ids = [e['root_event_id'] for e in events]
    require(len(ids)==len(set(ids)),'duplicate root identity')
    require(len(sessions)==250 and '2025-01-09' not in sessions,'NYSE session count or Jan9 closure')
    require(sessions==sorted(set(sessions)),'sessions must be sorted and unique')
    require(all(dt.date.fromisoformat(s).year==2025 for s in sessions),'session year')
    dates=[(dt.date(2025,1,1)+dt.timedelta(days=i)).isoformat() for i in range(365)]
    require([r['date'] for r in stress]==dates,'stress calendar must contain every 2025 date once in order')
    for e in events:
        require(dt.date.fromisoformat(e['event_date']).year==2025,'event year')
        members=e['issuer_tickers']
        require(bool(members) and len(members)==len(set(members)),'issuer set empty or duplicated')
        require(e['primary_issuer'] in members and set(members)<=set(FROZEN_UNIVERSE),'frozen issuer mapping')
        require(e['scheduling'] in {'SCHEDULED','DISCRETIONARY','UNKNOWN'},'scheduling')
        require(bool(e['sources']) and all(s.get('opened') for s in e['sources']),'source-open flags')
        require(e.get('economic_direction') in {'POSITIVE','MIXED','NEGATIVE','UNKNOWN','ATTENTION'},'direction')
        require(e.get('population_capture_complete') is False,'pilot coverage cannot be promoted')
    for row in stress:
        for instrument in ['nominal2y','real10y']:
            v=row[instrument]
            require(v['source_observation_date'] < row['date'],'same-day or future stress source')
            require(v['stress_any_prior5'] in [0,1] and v['stress_any_prior10'] in [0,1],'binary exposure')
            require(v['stress_any_prior5'] <= v['stress_any_prior10'],'five-session exposure not nested')
    return {'unique_roots':len(events), 'source_open_flags_checked':True,
            'calendar_2025_sessions':250,'lag_invariants_checked':True,
            'semantic_source_truth_proved_by_these_checks':False}

def draws_for_events(events, sessions, n, rng=None, move_scheduled=False):
    """Only trading-date events enter the exact month+weekday randomization.
    Scheduled dates stay fixed except in the explicitly labeled calendar diagnostic.
    Weekend/holiday originals are excluded; moving their weekday would violate the null.
    """
    by_stratum=collections.defaultdict(list)
    for j,s in enumerate(sessions):
        d=dt.date.fromisoformat(s)
        by_stratum[(d.month,d.weekday())].append(j)
    kept=sorted([e for e in events if e.get('timing_analysis_eligible',True) and e['event_date'] in sessions],key=lambda e:e['root_event_id'])
    excluded=[e['root_event_id'] for e in events if not e.get('timing_analysis_eligible',True) or e['event_date'] not in sessions]
    index={s:i for i,s in enumerate(sessions)}
    observed=np.array([index[e['event_date']] for e in kept],dtype=int)
    draws=np.zeros((n,len(kept)),dtype=np.int16)
    for j,e in enumerate(kept):
        d=dt.date.fromisoformat(e['event_date'])
        if e['scheduling']=='SCHEDULED' and not move_scheduled:
            draws[:,j]=observed[j]
        else:
            # The same root gets the same random assignments across case/order changes.
            root_seed=int.from_bytes(hashlib.sha256(f'{SEED}:{e["root_event_id"]}'.encode()).digest()[:16],'big')
            root_rng=np.random.default_rng(root_seed)
            draws[:,j]=root_rng.choice(by_stratum[(d.month,d.weekday())],n)
    return kept, observed, draws, excluded

def pairs(events, disjoint=True):
    return [(i,j) for i in range(len(events)) for j in range(i+1,len(events))
            if events[i]['primary_issuer']!=events[j]['primary_issuer']
            and (not disjoint or not set(events[i]['issuer_tickers']) & set(events[j]['issuer_tickers']))]

def sequence_stat(observed, draws, event_rows, horizon, disjoint=True,exclude_shared_program=False):
    ps=pairs(event_rows,disjoint)
    if exclude_shared_program:
        ps=[(i,j) for i,j in ps if not set(event_rows[i].get('program_ids',[])) & set(event_rows[j].get('program_ids',[]))]
    if not ps:
        return {'status':'NOT_ESTIMABLE_NO_ELIGIBLE_ROOT_PAIRS','observed':None,
                'one_sided_p_plus_one':None,'eligible_distinct_issuer_root_pairs':0}
    sim=np.zeros(draws.shape[0],dtype=int)
    obs=0
    for i,j in ps:
        obs += abs(int(observed[i])-int(observed[j])) <= horizon
        sim += np.abs(draws[:,i]-draws[:,j]) <= horizon
    out=probability_record(obs,sim)
    out.update({'eligible_distinct_issuer_root_pairs':len(ps),
                'distance_sessions':horizon,
                'requires_disjoint_observed_issuer_sets':disjoint,
                'same_session_pairs':sum(int(observed[i])==int(observed[j]) for i,j in ps),
                'statistic':'UNORDERED_DISTINCT_ROOT_PAIR_PROXIMITY',
                'same_session_order':'NOT_INFERRED',
                'excludes_direct_shared_program_pairs':exclude_shared_program,
                'observed_close_pairs_with_direct_shared_program':sum(abs(int(observed[i])-int(observed[j]))<=horizon and bool(set(event_rows[i].get('program_ids',[])) & set(event_rows[j].get('program_ids',[]))) for i,j in ps),
                'observed_close_pairs_with_same_named_customer_network':sum(abs(int(observed[i])-int(observed[j]))<=horizon and bool(event_rows[i].get('common_customer_network_id')) and event_rows[i].get('common_customer_network_id')==event_rows[j].get('common_customer_network_id') for i,j in ps),
                'pair_independence_assumed':False,
                'prespecified_preevent_economic_graph_available':False})
    return out

def run_case(label, rows, sessions, stress_by_date, n, rng, calendar_move=False):
    kept,obs,draws,excluded=draws_for_events(rows,sessions,n,rng,calendar_move)
    result={'name':label, 'roots_in_input':len(rows),'roots_on_trading_dates':len(kept),
            'excluded_nontrading_or_timing_ineligible_roots':excluded,
            'scheduled_events_moved':calendar_move,
            'movable_roots':sum(calendar_move or e['scheduling']!='SCHEDULED' for e in kept),
            'exact_source_clocks_in_kept':sum(bool(e.get('exact_source_clock')) for e in kept),
            'certified_earliest_public_clocks_in_kept':sum(bool(e.get('earliest_public_certified')) for e in kept),
            'null_model':'INDEPENDENT_UNIFORM_MONTH_WEEKDAY_DATE_RESAMPLING',
            'exchangeability':'ASSUMED_WITHIN_SELECTED_PANEL_NOT_ESTABLISHED',
            'population_arrival_inference':'NOT_SUPPORTED',
            'C3_pair_count_3_sessions':sequence_stat(obs,draws,kept,3),
            'C3_pair_count_5_sessions':sequence_stat(obs,draws,kept,5),
            'C3_excluding_direct_shared_program_pairs_3_sessions':sequence_stat(obs,draws,kept,3,True,True),
            'C3_primary_issuer_only_3_sessions':sequence_stat(obs,draws,kept,3,False)}
    rates={}
    for instrument in ['nominal2y','real10y']:
        for horizon in [5,10]:
            if not kept:
                rates[f'{instrument}_prior{horizon}']={'status':'NOT_ESTIMABLE_NO_ELIGIBLE_EVENTS',
                    'observed':None,'one_sided_p_plus_one':None}
                continue
            flags=np.array([stress_by_date[s][instrument][f'stress_any_prior{horizon}'] for s in sessions],dtype=int)
            o=int(flags[obs].sum())
            s=flags[draws].sum(axis=1)
            value=probability_record(o,s)
            contrast=0
            for e,j in zip(kept,obs):
                date=dt.date.fromisoformat(e['event_date'])
                support=[int(j)] if e['scheduling']=='SCHEDULED' and not calendar_move else [k for k,d in enumerate(sessions) if (dt.date.fromisoformat(d).month,dt.date.fromisoformat(d).weekday())==(date.month,date.weekday())]
                contrast+=len(set(flags[support]))>1
            value['roots_with_exposed_and_unexposed_eligible_dates']=contrast
            if contrast==0:
                value['status']='STRUCTURAL_NO_RATE_TIMING_CONTRAST'
                value['one_sided_p_plus_one']=None; value['monte_carlo_se_only']=None
            value['observed_exposed_root_ids']=[e['root_event_id'] for e,j in zip(kept,obs) if flags[j]]
            rates[f'{instrument}_prior{horizon}']=value
    result['selected_event_alignment_rates_only']=rates
    if label=='broad_first_program_family':
        result['status']='DESCRIPTIVE_FIRST_CAPTURED_PROGRAM_REPRESENTATIVE'
        result['selection_limit']='First representative was selected on observed dates and is not reselected within each permutation.'
        for key in ['C3_pair_count_3_sessions','C3_pair_count_5_sessions','C3_primary_issuer_only_3_sessions','C3_excluding_direct_shared_program_pairs_3_sessions']:
            result[key]['one_sided_p_plus_one']=None
            result[key]['monte_carlo_se_only']=None
        for value in rates.values():
            value['one_sided_p_plus_one']=None
            value['monte_carlo_se_only']=None
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--simulations',type=int,default=10000)
    args=ap.parse_args(); p=args.directory
    if args.simulations<=0: raise ValueError('simulations must be positive')
    panel=read_json(p/'PB_C_EVENT_PANEL.json')
    events=panel['events']
    stress=read_json(p/'PB_C_STRESS_WINDOWS.json')['daily_derived_rates']
    with (p/'nyse_calendar_2025.csv').open() as f:
        sessions=[r['date'] for r in csv.DictReader(f)]
    checks=validate(events,stress,sessions)
    sd={r['date']:r for r in stress}
    first=[e for e in events if e.get('calendar_audit_first2025')]
    calendar=[e for e in first if e['scheduling']=='SCHEDULED']
    strict=[e for e in events if e['scheduling']=='DISCRETIONARY' and e['economic_direction']=='POSITIVE']
    broad=[e for e in events if e['sampling_arm']=='material_event_pilot' and e['scheduling']!='SCHEDULED' and e['economic_direction'] in {'POSITIVE','MIXED'}]
    cases=[('calendar_first_results_schedule_type',calendar,True),
           ('calendar_prior_notice_certified',[e for e in calendar if e.get('prior_schedule_certified')],True),
           ('strict_freely_timed_positive',strict,False),
           ('broad_unscheduled_candidate',broad,False),
           ('broad_positive_content_only',[e for e in broad if e['economic_direction']=='POSITIVE'],False),
           ('broad_ex_NVDA',[e for e in broad if 'NVDA' not in e['issuer_tickers']],False),
           ('broad_ex_NVDA_AMD_ORCL',[e for e in broad if not set(e['issuer_tickers']) & {'NVDA','AMD','ORCL'}],False),
           ('broad_exact_source_clock',[e for e in broad if e.get('exact_source_clock')],False)]
    # Source/document-date alternatives are conditional sensitivities, never default first-public claims.
    hpe=[]; tsm=[]
    for e in broad:
        h=dict(e); t=dict(e)
        if e['root_event_id']=='PBC-D-HPE-20250627-DOJ-SETTLEMENT':
            h['event_date']='2025-06-27'; h['timing_analysis_eligible']=True
        if e['root_event_id']=='PBC-TECH-TSM-US-EXPANSION-20250303': t['event_date']='2025-03-04'
        hpe.append(h); tsm.append(t)
    cases.extend([('broad_HPE_document_date_assumed',hpe,False),('broad_TSM_Taiwan_source_date',tsm,False)])
    for species in sorted({e['primary_species'] for e in broad}):
        cases.append(('broad_ex_species_'+species,[e for e in broad if e['primary_species']!=species],False))
    # Coarsening repeated-program roots is a disclosed sensitivity; root event identities remain intact.
    coarse=[]; groups=set()
    for e in sorted(broad,key=lambda e:(e['event_date'],e['root_event_id'])):
        g=e.get('program_family_id') or e['root_event_id']
        if g not in groups:coarse.append(e);groups.add(g)
    cases.append(('broad_first_program_family',coarse,False))
    rng=np.random.default_rng(SEED)
    results=[run_case(label,rows,sessions,sd,args.simulations,rng,move) for label,rows,move in cases]
    counts={
      'unique_root_events':len(events),
      'issuers_represented':len(set(t for e in events for t in e['issuer_tickers'])),
      'primary_species_mutually_exclusive':dict(collections.Counter(e['primary_species'] for e in events)),
      'scheduling':dict(collections.Counter(e['scheduling'] for e in events)),
      'direction_content_only':dict(collections.Counter(e['economic_direction'] for e in events)),
      'sampling_arm':dict(collections.Counter(e['sampling_arm'] for e in events)),
      'first_results_audit_members':len(first),
      'source_urls':len(set(s['url'] for e in events for s in e['sources'])),
      'earliest_public_certified':sum(bool(e.get('earliest_public_certified')) for e in events),
      'exact_source_clock':sum(bool(e.get('exact_source_clock')) for e in events)}
    report={'status':'RETROSPECTIVE_SELECTED_PANEL_DIAGNOSTICS', 'seed':SEED,
      'simulations_per_case':args.simulations,'numpy_version':np.__version__,
      'bit_generator':'PCG64','seed_scheme':'first128bits_SHA256(master_seed:root_event_id)',
      'canonical_event_order':'root_event_id','same_root_random_draws_shared_across_sensitivities':True,
      'counts':counts,'checks':checks,'analyses':results,
      'C1_population_hazard':'NOT_ESTIMABLE_INCOMPLETE_CAPTURE_AND_PRIMARY_STRESS_DATA',
      'C2_linkage_interaction':'NOT_ESTIMABLE_NO_PREEVENT_MATCHED_RISK_SET',
      'C4_market_persistence':'NOT_ESTIMABLE_NO_ADMITTED_ADJUSTED_RETURN_PANEL',
      'provenance':{f:sha(p/f) for f in ['PB_C_EVENT_PANEL.json','PB_C_STRESS_WINDOWS.json','nyse_calendar_2025.csv','PB_C_ANNOUNCEMENT_STUDY_PREREG.md','PB_C_PROTOCOL_AMENDMENTS.md','reproduce_pilot.py']},
      'limits':['Month and weekday do not exhaust earnings, conference or policy calendars.',
                'Search-driven capture can make event dates nonexchangeable.',
                'Rates are prespecified sensitivity exposures, not substitutes for Nasdaq or VIX.',
                'No estimates here confer ranking, trading, sizing, or central-intent authority.']}
    (p/'PB_C_ANALYSIS_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'counts':counts,'cases':len(results),'checks':checks},indent=2))

if __name__=='__main__':main()
