"""Finite fabricated BVC -> cumulative window -> matched-clock baseline witness.

No market files, HTTP, credentials, or calendar inference. The dates below are
explicit test inputs and do not attest real trading-session eligibility.
"""
from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo
import pressure as m
from window_pressure import measure_windows

PRIOR=("2026-05-01","2026-05-04","2026-05-05","2026-05-06","2026-05-07",
       "2026-05-08","2026-05-11","2026-05-12","2026-05-13","2026-05-14",
       "2026-05-15","2026-05-18","2026-05-19","2026-05-20","2026-05-21",
       "2026-05-22","2026-05-26","2026-05-27","2026-05-28","2026-05-29")
TARGET="2026-06-01"
GROUPS=(m.Membership("SYNTHETIC_F1","fixture-v1","current_cohort",("A","B")),
        m.Membership("SYNTHETIC_F2","fixture-v1","current_cohort",("B","C")))


def _inputs(day,scale):
    def at(hour,minute=0):
        return int(datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00").replace(tzinfo=ZoneInfo("America/New_York")).timestamp())
    segments=(m.Segment(day,"PRE",at(4),at(9,30),"SYNTHETIC_CALENDAR","FULL"),
              m.Segment(day,"RTH",at(9,30),at(16),"SYNTHETIC_CALENDAR","FULL"),
              m.Segment(day,"AH",at(16),at(20),"SYNTHETIC_CALENDAR","FULL"))
    bars=[]
    for n,sid in enumerate(("A","B","C")):
        for k,start in enumerate(range(at(4),at(9,35),60)):
            segment=segments[0] if start<at(9,30) else segments[1]
            close=100.+10*n+(k%7)*.1
            bars.append(m.Bar(sid,segment,start,start+60,start+62,close,1000.*scale,None,
                             "unadjusted/USD","SYNTHETIC_SOURCE_V1","FIXTURE_RIGHTS_NOT_A_LICENSE"))
    return bars,segments,at(4),at(9,35)


def synthetic_pipeline():
    config=m.disclosed_core_config()
    windows=[]
    scales=[1+i*.05 for i in range(20)]
    for day,scale in list(zip(PRIOR,scales))+[(TARGET,4.)]:
        bars,segments,start,end=_inputs(day,scale)
        windows.append(measure_windows(bars,GROUPS,segments,start_utc_s=start,
            end_utc_s=end,cutoff_utc_s=end+2,config=config))
    target=windows[-1]
    target_gross=target.factors[0].gross_reference
    target_net=target.factors[0].net_reference
    gross_refs=[r.factors[0].gross_reference for r in windows[:-1]]
    net_refs=[r.factors[0].net_reference for r in windows[:-1]]
    assert target_gross is not None and target_net is not None
    assert all(r is not None for r in gross_refs+net_refs)
    baseline=m.matched_baseline(target_gross,gross_refs,PRIOR,m.BaselineConfig(),cutoff_utc_s=end+2)
    net_baseline=m.matched_baseline(target_net,net_refs,PRIOR,m.BaselineConfig(),cutoff_utc_s=end+2)
    center=median(scales);mad=median(abs(s-center) for s in scales)
    independent=(4.-center)/(m.MAD_NORMAL_SCALE*mad)
    replay=measure_windows(reversed(bars),tuple(reversed(GROUPS)),tuple(reversed(segments)),
                           start_utc_s=start,end_utc_s=end,cutoff_utc_s=end+2,config=config)
    future=replace(bars[-1],start_utc_s=end,end_utc_s=end+60,available_at_utc_s=end+62,close=-1.)
    revision=replace(bars[21],close=900.,source_revision="LATER_CORRECTION",available_at_utc_s=end+500)
    prefix=measure_windows(bars+[future,future,revision],GROUPS,segments,start_utc_s=start,
                           end_utc_s=end,cutoff_utc_s=end+2,config=config)
    result={"schema":"factor_atlas.window_pipeline_witness.v1","source":"SYNTHETIC",
        "market_pilot_admitted":False,"source_rights_proven":False,"calendar_eligibility_proven":False,
        "window_start_et":"04:00","window_end_et":"09:35","slots_per_name_per_session":335,
        "sessions":21,"unique_security_minutes":21*335*3,"baseline_n":baseline.n,
        "baseline_coverage":baseline.coverage,"gross_z":baseline.z_raw,
        "independent_gross_z":independent,"net_z":net_baseline.z_raw,
        "net_baseline_n":net_baseline.n,"target_factor_gross_usd":target.factors[0].full_gross_usd,
        "target_factor_estimated_net_usd":target.factors[0].full_estimated_net_usd,
        "target_policy_neutral_gross_usd":target.factors[0].policy_neutral_gross_usd,
        "union_gross_usd":target.union_observed_gross_usd,"factor_sum_gross_usd":target.sum_factor_observed_gross_usd,
        "duplicated_gross_usd":target.duplicated_gross_usd,"replay_equal":target==replay,
        "future_prefix_equal":target==prefix,
        "union_accounting_equal":abs(target.union_observed_gross_usd+target.duplicated_gross_usd-target.sum_factor_observed_gross_usd)<1e-6,
        "all_authority_false":all(not value for name,value in target.authority),
        "window_sha256":m.digest(asdict(target)),"baseline_reference_sha256":baseline.reference_digest,
        "estimator_id":target.estimator_id,"prior_sessions":PRIOR,
        "source_sha256":{name:sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ("pressure.py","window_pressure.py","window_pipeline_witness.py")}}
    assert result['replay_equal'] and result['future_prefix_equal'] and result['union_accounting_equal']
    assert baseline.n==20 and abs(baseline.z_raw-independent)<1e-10
    return result


if __name__=='__main__':
    print(json.dumps(synthetic_pipeline(),sort_keys=True,indent=2,allow_nan=False))
