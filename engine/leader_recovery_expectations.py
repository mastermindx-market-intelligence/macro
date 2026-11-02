"""Source-dated observations from the incumbent revisions owner, not a thesis score.

Breadth = NET/(up+down), in [-1,1]. Coverage breadth = NET/n_covering, NOT the
share of all analysts that upgraded. Estimate drift is already in percent units.
"""
from __future__ import annotations
from datetime import date
import hashlib,json,math
import pandas as pd
import numpy as np

FIELDS = {
    'net_up_30d': ('net_revisions_30d', 'count'),
    'n_analysts': ('reviser_count_30d', 'count'),
    'n_covering': ('covering_analysts', 'count'),
    'breadth': ('net_reviser_breadth', 'ratio_minus1_to1'),
    'breadth_cov': ('coverage_normalized_net_revisions', 'ratio'),
    'est_chg_30d': ('eps_estimate_change_30d', 'percent'),
    'est_chg_90d': ('eps_estimate_change_90d', 'percent'),
    'rev_growth_fwd': ('forward_revenue_growth_estimate', 'percent'),
    'eps_dispersion_norm': ('eps_estimate_dispersion', 'nonnegative_ratio'),
    'rev_n_analysts': ('revenue_estimate_analysts', 'count'),
}


def project_expectations(ticker: str, revisions: pd.DataFrame, *, as_of: date,
                         sessions: list[date]) -> dict:
    result = {'schema': 'leader_recovery_expectations.v1', 'ticker': ticker,
              'as_of': as_of.isoformat(), 'availability': 'UNAVAILABLE', 'reason': None,
              'source': 'data/revisions/latest.parquet', 'source_date': None,
              'source_age_sessions': None, 'readings': {}, 'quality_flags': [],
              'revision_direction': 'UNKNOWN', 'thesis_state': 'UNKNOWN',
              'first_seen_qualified': False, 'historical_identity_qualified': False,
              'freshness_adjudicated': False,
              'basis': 'forward_fiscal_year_consensus_estimates',
              'disclosure': 'Snapshot observations, not actual reported revenue growth or a thesis verdict.'}
    if not isinstance(revisions, pd.DataFrame) or ticker not in revisions.index:
        return {**result, 'reason': 'ticker_not_in_revisions_source'}
    row = revisions.loc[ticker]
    if not isinstance(row, pd.Series):
        return {**result, 'reason': 'ambiguous_duplicate_ticker'}
    try:
        raw_date = row.get('asof')
        if not isinstance(raw_date, (str, date)):
            raise ValueError('invalid_source_date_type')
        stamp = pd.Timestamp(raw_date)
        if pd.isna(stamp):raise ValueError('missing_date')
        source_date = stamp.date()
    except (TypeError, ValueError, OverflowError):
        return {**result, 'reason': 'source_date_unavailable'}
    result['source_date'] = source_date.isoformat()
    if source_date > as_of:
        return {**result, 'reason': 'source_after_price_cut'}
    result['source_age_sessions'] = sum(source_date < d <= as_of for d in sessions)
    for key, (name, unit) in FIELDS.items():
        raw = row.get(key)
        try:
            value = float(raw)
            if isinstance(raw, (bool,np.bool_)) or not math.isfinite(value):raise ValueError('invalid_numeric')
            if unit == 'count' and (not value.is_integer() or (key != 'net_up_30d' and value < 0)):raise ValueError('invalid_count')
            if unit == 'ratio_minus1_to1' and not -1 <= value <= 1:raise ValueError('invalid_ratio')
            if unit == 'nonnegative_ratio' and value < 0:raise ValueError('invalid_dispersion')
        except (TypeError, ValueError, OverflowError):value = None
        result['readings'][name] = {'value': value, 'unit': unit}
    def val(name):return result['readings'][name]['value']
    net = val('net_revisions_30d')
    for denominator, ratio, flag in (
        ('reviser_count_30d', 'net_reviser_breadth', 'inconsistent_reviser_breadth'),
        ('covering_analysts', 'coverage_normalized_net_revisions', 'inconsistent_coverage_breadth'),
    ):
        count, observed = val(denominator), val(ratio)
        if net is not None and count is not None and observed is not None:
            if count <= 0 or abs(net / count - observed) > .0002:result['quality_flags'].append(flag)
    signs = {1 if v > 0 else -1 if v < 0 else 0 for v in (val('eps_estimate_change_30d'),net) if v is not None}
    if signs and not result['quality_flags']:
        result['revision_direction'] = ('MIXED' if 1 in signs and -1 in signs else
            'POSITIVE_OBSERVATIONS' if 1 in signs else 'NEGATIVE_OBSERVATIONS' if -1 in signs else 'FLAT_OBSERVATIONS')
    result['availability'] = 'SOURCE_DATED_OBSERVATIONS' if any(x['value'] is not None for x in result['readings'].values()) else 'UNAVAILABLE'
    if result['availability']=='UNAVAILABLE':result['reason']='all_numeric_readings_missing'
    result['source_fingerprint_sha256']=hashlib.sha256(json.dumps({'ticker':ticker,'source_date':result['source_date'],'readings':result['readings']},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return result
