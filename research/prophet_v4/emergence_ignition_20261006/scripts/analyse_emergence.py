#!/usr/bin/env python3
"""Frozen emergence historical diagnostic; reads compact Git snapshots, writes research only.
No fitting, production imports, ranking, trading, or candidate-episode creation.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, random, statistics
from pathlib import Path

HORIZONS=(3,5,10,12,20)
BASE_FEATURES=('alpha','setup','ext_z','off_high','sector_rank_fraction','alignment_quality','signal_proximity','vol_ann_pct')
OPEN={'buy_now','partial'}

def at(d,*ks):
    for k in ks:
        if not isinstance(d,dict): return None
        d=d.get(k)
    return d

def num(x):
    return float(x) if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(float(x)) else None

def count_flags(r):
    # Deliberately retains parent legacy definition. NOT an independent-PIT-family count.
    news=r.get('news_burst')
    sue=num(r.get('sue_z'))
    own=at(r,'smartmoney_chip','action')
    return int(bool(news))+int(sue is not None and sue!=0)+int(own in ('new','add'))

def getrow(b,t):
    rows=[(l,i,r) for l in ('buy','watch','leaders','laggards') for i,r in enumerate(b.get(l,[])) if r.get('ticker')==t]
    return rows[0] if rows else None

def technical(r,mode='valid'):
    if not isinstance(r,dict): return None
    s=r.get('signal')
    if not isinstance(s,dict): return None
    tier=s.get('tier_cascade')
    if mode=='raw': return tier in ('T1','T2')
    if not s.get('asof') or s.get('eligible') is None: return None
    if tier not in ('T1','T2'): return False
    eligible=s.get('eligible');provisional=s.get('tier_observation_provisional')
    if eligible is False or provisional is True or s.get('provisional') is True: return False
    if eligible is not True or provisional is not False: return None
    # A claimed observation after the board cut is not counted as already known.
    if not s.get('asof'): return None
    return True

def strict_baseline(r):
    es=at(r,'entry_signal','status')
    return at(r,'signal','tier_cascade') not in ('T1','T2') and es is not None and es not in OPEN

def features(r):
    sr=num(r.get('sector_rank'));sn=num(r.get('sector_n'))
    return dict(alpha=num(r.get('alpha')),setup=num(r.get('setup')),ext_z=num(r.get('ext_z')),
        off_high=num(r.get('off_high')),sector_rank_fraction=sr/sn if sr is not None and sn else None,
        alignment_quality=num(at(r,'conviction','alignment','quality')),
        signal_proximity=num(at(r,'signal','bars_to_cross')),
        vol_ann_pct=num(at(r,'risk_sizing','vol_ann_pct')))

def baseline(b,r,index):
    news=r.get('news_burst') or {};sue=num(r.get('sue_z'));own=r.get('smartmoney_chip') or {}
    return dict(ticker=r['ticker'],as_of=b['as_of'],sector=r.get('sector'),entry_status=at(r,'entry_signal','status'),
       tier_at_start=at(r,'signal','tier_cascade'),legacy_count=count_flags(r),
       legacy_family_pattern='+'.join(x for x,y in [('news',bool(news)),('sue_nonzero',sue is not None and sue!=0),('ownership',own.get('action') in ('new','add'))] if y),
       news_direction=news.get('sentiment_lean'),sue_z=sue,ownership_action=own.get('action'),ownership_period=own.get('period_end'),
       observation_ref='git:'+b['source_blob']+'#watch/'+str(index),source_commit=b['source_commit'],
       source_commit_at=b['source_commit_at'],source_sha256=b['source_sha256'],source_blob=b['source_blob'],
       board_definition=b.get('board_definition'),canonical_episode_id=None,strict_family_qualification='UNAVAILABLE',
       **features(r))

def outcome(bs,base,h,mode='valid',kind='technical'):
    start=next(i for i,b in enumerate(bs) if b['as_of']==base['as_of'])
    future=bs[start+1:start+1+h];n=len(future);obs=[];positive=None;unknown_state=0;missing=0
    for j,b in enumerate(future,1):
        found=getrow(b,base['ticker'])
        if found is None:
            missing+=1;obs.append(False);continue
        lane,_,r=found;obs.append(True)
        if kind=='technical': val=technical(r,mode)
        elif kind=='buy_tier': val=technical(r,mode) if lane=='buy' else False
        elif kind=='availability':
            state=at(r,'entry_signal','status');val=state in OPEN if state is not None else None
        else: raise ValueError(kind)
        # Reject explicit future technical clocks for a point-in-time decision cut.
        if val and kind in ('technical','buy_tier') and mode=='valid':
            clock=at(r,'signal','tier_observed_date')
            if clock is not None and str(clock)>b['as_of']: val=None
            clock=at(r,'signal','asof')
            if clock is not None and str(clock)>b['as_of']: val=None
        if val is None: unknown_state+=1
        if val is True and positive is None:
            positive=dict(sessions=j,date=b['as_of'],lane=lane,tier=at(r,'signal','tier_cascade'),source_commit=b['source_commit'],
                source_commit_at=b['source_commit_at'],entry_status=at(r,'entry_signal','status'),
                signal_asof=at(r,'signal','asof'),provisional=at(r,'signal','tier_observation_provisional'))
    if positive is not None: state='OBSERVED_CONVERSION'
    elif n<h: state='RIGHT_CENSORED'
    elif missing or unknown_state: state='OBSERVATION_GAP_OR_UNKNOWN_STATE'
    else: state='OBSERVED_NONCONVERSION'
    return dict(horizon=h,mode=mode,endpoint=kind,state=state,positive=positive,mature=n==h,
        global_sessions_available=n,observed_candidate_sessions=sum(obs),missing_candidate_sessions=missing,
        unknown_state_sessions=unknown_state,complete_observation=n==h and not missing and not unknown_state)

def summarize_outcomes(outcomes):
    n=len(outcomes);states=collections.Counter(o['state'] for o in outcomes)
    mature=[o for o in outcomes if o['mature']];pos=sum(o['positive'] is not None for o in mature)
    knownneg=sum(o['state']=='OBSERVED_NONCONVERSION' for o in mature);unresolved=len(mature)-pos-knownneg
    sessionvals=[o['positive']['sessions'] for o in outcomes if o['positive'] is not None]
    return dict(n_baselines=n,n_horizon_mature=len(mature),n_observed_conversions=sum(o['positive'] is not None for o in outcomes),
        n_mature_observed_conversions=pos,n_observed_nonconversions=knownneg,
        n_right_censored_no_observed_conversion=states['RIGHT_CENSORED'],
        n_gapped_or_unknown_no_observed_conversion=states['OBSERVATION_GAP_OR_UNKNOWN_STATE'],
        observed_capture_fraction=pos/len(mature) if mature else None,
        true_conversion_risk_bounds=[pos/len(mature),(pos+unresolved)/len(mature)] if mature else None,
        median_observed_sessions_to_conversion=statistics.median(sessionvals) if sessionvals else None,
        n_complete_followups=sum(o['complete_observation'] for o in outcomes),
        total_observed_candidate_sessions=sum(o['observed_candidate_sessions'] for o in outcomes))

def quantile(xs,p):
    if not xs: return None
    xs=sorted(xs);x=(len(xs)-1)*p;lo=int(x);hi=min(lo+1,len(xs)-1)
    return xs[lo]+(xs[hi]-xs[lo])*(x-lo)

def cmean(x):return sum(x)/len(x) if x else None

def comparison(bs,exposed,controls,h,mode,match,seed):
    # All matching uses baseline fields only. Fixed 3-nearest policy; no optimized calipers.
    records=[];unmatched=[];used=set();pairs=[];balance=[]
    # Cross-sectional scaling is recomputed on the SAME board date; later covariates
    # must not influence an earlier match even though this is historical discovery.
    scale_by_date={}
    for b in bs:
        fs=[features(r) for r in b.get('watch',[]) if strict_baseline(r)]
        scale={}
        for f in BASE_FEATURES:
            vals=[r[f] for r in fs if r.get(f) is not None]
            scale[f]=statistics.pstdev(vals) if len(vals)>1 and statistics.pstdev(vals)>0 else 1.
        scale_by_date[b['as_of']]=scale
    used_exposed=set()
    for e in exposed:
        scale=scale_by_date[e['as_of']]
        eo=outcome(bs,e,h,mode)
        if not eo['mature']: continue
        if match=='issuer_disjoint_nn3' and e['ticker'] in used:
            unmatched.append(e['ticker']+':already_enrolled_as_control');continue
        cs=[c for c in controls if c['as_of']==e['as_of'] and c['ticker']!=e['ticker']]
        if match!='date': cs=[c for c in cs if c['sector']==e['sector'] and c['sector'] is not None]
        if match in ('date_sector_state','date_sector_state_nn3','issuer_disjoint_nn3'): cs=[c for c in cs if c['entry_status']==e['entry_status']]
        if match in ('date_sector_state_nn3','issuer_disjoint_nn3'):
            cs=[c for c in cs if c['ticker'] not in used]
            if match=='issuer_disjoint_nn3': cs=[c for c in cs if c['ticker'] not in used_exposed]
            def dist(c):
                fs=[f for f in BASE_FEATURES if c.get(f) is not None and e.get(f) is not None]
                return (sum(((c[f]-e[f])/scale[f])**2 for f in fs)/len(fs) if fs else math.inf,c['ticker'])
            cs=sorted(cs,key=dist)[:3]
            used.update(c['ticker'] for c in cs)
        if not cs:unmatched.append(e['ticker']);continue
        used_exposed.add(e['ticker'])
        eos=eo['positive'] is not None;co=[outcome(bs,c,h,mode) for c in cs]
        cspos=[o['positive'] is not None for o in co]
        control_lower=cmean([float(o['positive'] is not None) for o in co])
        control_upper=cmean([float(o['state']!='OBSERVED_NONCONVERSION') for o in co])
        lower=float(eos);upper=float(eo['state']!='OBSERVED_NONCONVERSION')
        records.append(dict(date=e['as_of'],ticker=e['ticker'],sector=e['sector'],t=float(eos),c=cmean(cspos),
            lower_difference=lower-control_upper,upper_difference=upper-control_lower,
            control_n=len(cs),t_gap=eo['missing_candidate_sessions']+eo['unknown_state_sessions'],
            c_gap=cmean([o['missing_candidate_sessions']+o['unknown_state_sessions'] for o in co])))
        for c,o in zip(cs,co):
            pairs.append(dict(exposed_ticker=e['ticker'],control_ticker=c['ticker'],date=e['as_of'],horizon=h,
                mode=mode,matching=match,control_weight=1/len(cs),exposed_state=eo['state'],control_state=o['state'],
                exposed_observed_conversion=eos,control_observed_conversion=o['positive'] is not None))
        for f in BASE_FEATURES:
            vals=[c[f] for c in cs if c.get(f) is not None]
            if e.get(f) is not None and vals:
                balance.append(dict(feature=f,treated=e[f],control=cmean(vals),standardized_difference=(e[f]-cmean(vals))/scale[f]))
    if not records:return dict(n_matched_exposed=0,unmatched_tickers=unmatched),pairs
    dates=sorted(set(r['date'] for r in records));groups={d:[r for r in records if r['date']==d] for d in dates}
    rng=random.Random(seed);boot=[]
    for _ in range(10000):
        sample=[r for d in rng.choices(dates,k=len(dates)) for r in groups[d]]
        boot.append(cmean([r['t']-r['c'] for r in sample]))
    tr=cmean([r['t'] for r in records]);cr=cmean([r['c'] for r in records])
    weights=collections.Counter()
    for p in pairs:weights[p['control_ticker']]+=p['control_weight']
    total=sum(weights.values());neff=total**2/sum(w*w for w in weights.values()) if weights else None
    bal={}
    for f in BASE_FEATURES:
        vals=[r for r in balance if r['feature']==f]
        bal[f]=dict(pairs=len(vals),exposed_mean=cmean([r['treated'] for r in vals]),control_mean=cmean([r['control'] for r in vals]),
            mean_standardized_difference=cmean([r['standardized_difference'] for r in vals]))
    def concentration(key):
        count=collections.Counter(r[key] for r in records)
        return dict(counts=dict(count),max_share=max(count.values())/len(records),kish_effective_clusters=len(records)**2/sum(v*v for v in count.values()))
    result=dict(n_matched_exposed=len(records),n_dates=len(dates),n_control_unique_tickers=len(weights),
        control_weight_effective_n=neff,observed_capture_exposed=tr,observed_capture_controls=cr,
        observed_capture_difference=tr-cr,observed_capture_relative_risk=tr/cr if cr else None,
        observed_capture_odds_ratio=(tr/(1-tr))/(cr/(1-cr)) if tr<1 and 0<cr<1 else None,
        date_cluster_bootstrap_capture_difference_95ci=[quantile(boot,.025),quantile(boot,.975)],
        bootstrap_status=('DEGENERATE_OBSERVED_CONTRAST_NOT_PRECISE_NULL' if len({round(r['t']-r['c'],12) for r in records})==1 else 'SMALL_DATE_CLUSTER_DESCRIPTIVE_INTERVAL'),
        true_conversion_difference_identification_bounds=[cmean([r['lower_difference'] for r in records]),cmean([r['upper_difference'] for r in records])],
        mean_unobserved_or_unknown_followup_sessions={'exposed':cmean([r['t_gap'] for r in records]),'control':cmean([r['c_gap'] for r in records])},
        unmatched_tickers=unmatched,date_concentration=concentration('date'),sector_concentration=concentration('sector'),
        feature_balance=bal,estimand='OBSERVED_CAPTURE_YIELD_NOT_TRUE_CONVERSION_RISK',records=records)
    return result,pairs

def writecsv(path,rows):
    if not rows: path.write_text('');return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def run(boards,cutoff,name,out):
    bs=[b for b in boards if b.get('rank_by')=='us_prophet_v3' and '2026-08-17'<=b['as_of']<=cutoff]
    bs.sort(key=lambda b:b['as_of'])
    exp=[];allctl=[];seen=set();exclusions=collections.Counter();rawfirst=[];rawseen=set()
    for b in bs:
        for i,r in enumerate(b.get('watch',[])):
            if count_flags(r)>=2 and r['ticker'] not in rawseen:
                rawfirst.append(baseline(b,r,i));rawseen.add(r['ticker'])
            if not strict_baseline(r):
                exclusions['already_tier_T1_T2' if at(r,'signal','tier_cascade') in ('T1','T2') else 'entry_open_or_unknown']+=1
                continue
            e=baseline(b,r,i)
            if e['legacy_count']>=2:
                if e['ticker'] not in seen:exp.append(e);seen.add(e['ticker'])
            else:allctl.append(e)
    results={'window':name,'start':bs[0]['as_of'] if bs else None,'end':cutoff,'board_sessions':[b['as_of'] for b in bs],
        'exposure_definition':'FIRST_TICKER_UNRESOLVED_WATCH_LEGACY_GE2_NOT_VALIDATED_FAMILY_EXPOSURE',
        'strict_PIT_independent_family_exposure_n':None,'strict_PIT_independent_family_exposure_status':'NOT_IDENTIFIABLE_FROM_LEGACY_FLAGS',
        'n_exposed_first_ticker_baselines':len(exp),'n_parent_legacy_first_watch_baselines':len(rawfirst),
        'n_control_date_ticker_rows':len(allctl),'n_control_unique_tickers':len(set(x['ticker'] for x in allctl)),
        'exposed_dates':dict(collections.Counter(e['as_of'] for e in exp)),'exposed_sectors':dict(collections.Counter(e['sector'] for e in exp)),
        'baseline_exclusions':dict(exclusions),'horizons':{},'matched':{},'temporal_slices':{},'leave_one_out':{}}
    outcome_rows=[];allpairs=[]
    for h in HORIZONS:
        results['horizons'][str(h)]={}
        for mode in ('raw','valid'):
            for kind in ('technical','buy_tier','availability'):
                if kind=='availability' and mode=='raw':continue
                os=[outcome(bs,e,h,mode,kind) for e in exp]
                results['horizons'][str(h)][mode+'_'+kind]=summarize_outcomes(os)
                for e,o in zip(exp,os):outcome_rows.append(dict(ticker=e['ticker'],as_of=e['as_of'],**o))
        for mode in ('raw','valid'):
            for match in ('date','date_sector','date_sector_state','date_sector_state_nn3','issuer_disjoint_nn3'):
                val,pairs=comparison(bs,exp,allctl,h,mode,match,20261006+h)
                results['matched'][str(h)+'_'+mode+'_'+match]=val;allpairs+=pairs
    for tag,subset in [('through_Sep10',[e for e in exp if e['as_of']<='2026-09-10']),('after_Sep10',[e for e in exp if e['as_of']>'2026-09-10'])]:
        results['temporal_slices'][tag]=summarize_outcomes([outcome(bs,e,12,'valid') for e in subset])
    for e in exp:
        subset=[x for x in exp if x['ticker']!=e['ticker']]
        result,_=comparison(bs,subset,allctl,12,'valid','date_sector_state',20261006)
        results['leave_one_out'][e['ticker']]={k:result.get(k) for k in ['n_matched_exposed','observed_capture_difference']}
    # Compatibility check only: retains parent all-watch first-per-ticker and simple raw-tier capture.
    results['parent_compatibility']={str(h):summarize_outcomes([outcome(bs,e,h,'raw') for e in rawfirst]) for h in HORIZONS}
    for e in exp:
        for mode in ('raw','valid'):
            o=outcome(bs,e,max(1,len(bs)),mode)
            e['first_'+mode+'_confirmation']=o['positive']
        o=outcome(bs,e,max(1,len(bs)),'valid','availability');e['first_entry_open']=o['positive']
        start=next(i for i,b in enumerate(bs) if b['as_of']==e['as_of'])
        later=[(b['as_of'],getrow(b,e['ticker']) is not None) for b in bs[start+1:]]
        missing=[d for d,present in later if not present]
        e['first_absent_from_observed_board']=missing[0] if missing else None
        e['last_seen_in_observed_board']=next((d for d,present in reversed(later) if present),e['as_of'])
        e['expiry_status']='UNAVAILABLE_NO_CANONICAL_EXPIRY_RELATION'
    writecsv(out/(name+'_exposed_baselines.csv'),exp)
    writecsv(out/(name+'_outcomes.csv'),outcome_rows)
    writecsv(out/(name+'_matched_pairs.csv'),allpairs)
    writecsv(out/(name+'_control_baselines.csv'),allctl)
    (out/(name+'_summary.json')).write_text(json.dumps(results,indent=2,sort_keys=True,allow_nan=False))
    return results,exp

def selftest():
    def b(d,rows):return dict(as_of=d,buy=[],watch=rows,leaders=[],laggards=[])
    base={'ticker':'A','as_of':'2026-09-01'}
    r={'ticker':'A','signal':{'tier_cascade':None}}
    xs=[b('2026-09-01',[r]),b('2026-09-02',[]),b('2026-09-03',[r])]
    assert outcome(xs,base,2)['state']=='OBSERVATION_GAP_OR_UNKNOWN_STATE'
    assert outcome(xs,base,3)['state']=='RIGHT_CENSORED'
    assert technical({'signal':{'tier_cascade':'T1','eligible':True,'tier_observation_provisional':True,'asof':'2026-09-03'}}) is False
    assert technical({'signal':{'tier_cascade':'T1','tier_observation_provisional':False,'asof':'2026-09-03'}}) is None
    print('PASS: absent observation is unknown; horizon censored; provisional excluded; missing eligibility unknown')

def main():
    p=argparse.ArgumentParser();p.add_argument('--latest',type=Path);p.add_argument('--first',type=Path);p.add_argument('--out',type=Path);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:selftest();return
    a.out.mkdir(parents=True,exist_ok=True)
    latest=json.loads(a.latest.read_text());first=json.loads(a.first.read_text())
    for name,data,end in [('parent_window_latest',latest,'2026-09-25'),('extended_window_latest',latest,'2026-10-05'),('extended_window_first',first,'2026-10-05')]:
        result,exp=run(data,end,name,a.out)
        print(json.dumps({'window':name,'exposed':len(exp),'dates':len(result['board_sessions']),'H12':result['horizons']['12']['valid_technical'],
            'matched_H12':{k:v for k,v in result['matched']['12_valid_date_sector_state'].items() if k not in ['records','feature_balance']}}))
    (a.out/'reproduction_environment.json').write_text(json.dumps({'seed':20261006,'bootstrap_replicates':10000,
        'input_digests':{str(a.latest.name):hashlib.sha256(a.latest.read_bytes()).hexdigest(),str(a.first.name):hashlib.sha256(a.first.read_bytes()).hexdigest()},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'production_effects':'NONE','prospective_evidence':'NONE'},indent=2))
if __name__=='__main__':main()
