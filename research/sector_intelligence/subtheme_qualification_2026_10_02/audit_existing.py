"""Report an existing artifact's measured limitations without fabricating a replay."""
import json
from pathlib import Path


def audit(data):
    return {
        'source':{k:data[k] for k in ('repository','commit','path','source_blob','as_of')},
        'type':'AUDIT_OF_EXISTING_PRODUCER_RESULTS_NOT_NEW_RETURN_BACKTEST',
        'all_promotion_flags_false':not any(r['proven'] for r in data['horizons'].values()),
        'nonpositive_legacy_ic_horizons':[h for h,r in data['horizons'].items() if r['score_ic']<=0],
        'unmatched_population_horizons':[h for h,r in data['horizons'].items()
                                         if r['v2']['n_matured'] and r['n_matured']!=r['v2']['n_matured']],
        'rows_are_not_independent_days':{'snapshot_rows':data['n_snapshots'],'dates':data['n_days']},
        'decision':'Do not promote either score or invert it from this artifact. Repair and regrade the incumbent owner on paired, clock-qualified data.',
        'limits':data['limitations'],
    }


if __name__=='__main__':
    p=Path(__file__).parent/'evidence'/'observed_track_record_excerpt.json'
    print(json.dumps(audit(json.loads(p.read_text())),indent=2))
