"""LLR-24 planning arithmetic; no market data or network access.

Rates, record sizes and 252 sessions/year are scenarios, not measurements.
Output uses decimal GB/TB. Run from any directory with Python 3.
"""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
SESSION_SECONDS = {'rth': 6.5 * 3600, 'extended': 9.5 * 3600, 'overnight': 8 * 3600}
SESSIONS = 252
HOT_SESSIONS = 30
R2_STANDARD = 0.015
R2_IA = 0.010
R2_IA_RETRIEVAL = 0.010
UNIVERSES = [50, 100, 300, 3000]
LANES = {
 'bars_1m': {'rates': {k: 1/60 for k in SESSION_SECONDS}, 'raw_bytes': 160, 'stored_bytes': 64},
 'trades': {'rates': {'rth': 2, 'extended': 0.25, 'overnight': 0.05}, 'raw_bytes': 96, 'stored_bytes': 40},
 'l1': {'rates': {'rth': 10, 'extended': 1, 'overnight': 0.1}, 'raw_bytes': 144, 'stored_bytes': 48},
 'l2_deltas': {'rates': {'rth': 25, 'extended': 2.5, 'overnight': 0.3}, 'raw_bytes': 192, 'stored_bytes': 64},
 'l3_mbo': {'rates': {'rth': 50, 'extended': 5, 'overnight': 0.6}, 'raw_bytes': 144, 'stored_bytes': 48},
}

def estimate(n, lane, activity=1):
    spec = LANES[lane]
    events = n * sum(SESSION_SECONDS[k] * spec['rates'][k] for k in SESSION_SECONDS)
    if lane != 'bars_1m':
        events *= activity
    daily_gb = events * spec['stored_bytes'] / 1e9
    annual_gb = daily_gb * SESSIONS
    return dict(names=n, lane=lane, activity=activity, events_day=events,
        stored_gb_day=daily_gb, stored_gb_year=annual_gb,
        hot_ssd_gb=daily_gb * HOT_SESSIONS,
        raw_vendor_gb_year=events * spec['raw_bytes'] * SESSIONS / 1e9,
        r2_standard_month_at_full_retention=annual_gb * R2_STANDARD,
        r2_ia_month_at_full_retention=annual_gb * R2_IA)

rows = [estimate(n, lane) for n in UNIVERSES for lane in LANES]
tiers = []
for n in UNIVERSES:
    for activity in [0.2, 1, 5]:
        pieces = [estimate(n, lane, activity) for lane in ['bars_1m', 'trades', 'l1']]
        daily = sum(p['stored_gb_day'] for p in pieces)
        tiers.append(dict(names=n, activity=activity, stored_gb_day=daily,
            stored_gb_year=daily*SESSIONS, hot_ssd_gb=daily*HOT_SESSIONS,
            r2_one_copy_month=daily*SESSIONS*R2_STANDARD,
            r2_two_copies_month=daily*SESSIONS*R2_STANDARD*2,
            rth_events_sec=n*(LANES['trades']['rates']['rth']+LANES['l1']['rates']['rth'])*activity))

calibration_n = (1.96**2 * 0.25 / 0.05**2)
power_n_per_arm = 2 * (1.96 + 0.841621)**2 * 0.25 / 0.05**2
result = dict(assumption_status='PROPOSAL_NOT_MEASURED', currency='USD',
    units='decimal GB; one compressed copy unless stated', sessions_per_year=SESSIONS,
    session_seconds=SESSION_SECONDS, hot_sessions=HOT_SESSIONS, lanes=LANES,
    r2_prices={'standard_gb_month':R2_STANDARD,'ia_gb_month':R2_IA,
       'ia_retrieval_gb':R2_IA_RETRIEVAL}, rows=rows, tier_b=tiers,
    calibration_illustration={'iid_n_for_95pct_halfwidth_5pp_at_p_half':calibration_n,
       'iid_n_per_arm_for_5pp_difference_power80_two_sided05':power_n_per_arm,
       'warning':'These are IID approximations, not clustered-study power or promotion gates.'})
OUT.joinpath('storage_scenarios.json').write_text(json.dumps(result, indent=2)+'\n')
lines=['# Storage arithmetic', '', 'Planning assumptions only; prices and source qualifications are discussed in chapter 05.', '',
 '| Names | Lane | GB/day | GB/year | 30-session SSD GB | R2 Standard $/month, full annual retention |',
 '|---:|---|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['names']} | {r['lane']} | {r['stored_gb_day']:.3f} | {r['stored_gb_year']:.1f} | {r['hot_ssd_gb']:.1f} | {r['r2_standard_month_at_full_retention']:.2f} |")
lines += ['', '## Tier B: bars + trades + L1', '', '| Names | Activity multiplier | GB/day | GB/year | Hot SSD GB | One / two copies $ per month |', '|---:|---:|---:|---:|---:|---:|']
for r in tiers:
    lines.append(f"| {r['names']} | {r['activity']} | {r['stored_gb_day']:.3f} | {r['stored_gb_year']:.1f} | {r['hot_ssd_gb']:.1f} | {r['r2_one_copy_month']:.2f} / {r['r2_two_copies_month']:.2f} |")
OUT.joinpath('STORAGE_ARITHMETIC.md').write_text('\n'.join(lines)+'\n')
assert len(rows) == 20 and len(tiers) == 12
assert sum(SESSION_SECONDS.values()) == 24 * 3600
print(json.dumps({'rows': len(rows), 'tier_b_300_base': next(r for r in tiers if r['names']==300 and r['activity']==1),
  'iid_calibration_n': calibration_n, 'iid_power_n_per_arm': power_n_per_arm}, indent=2))
