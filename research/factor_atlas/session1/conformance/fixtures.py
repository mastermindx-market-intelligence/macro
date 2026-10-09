"""Synthetic contract examples: fixture:* refs have no native owner authority."""
from copy import deepcopy


def candidate_example():
    interval = {'start': '2026-09-02T20:00:00Z', 'end': '2026-09-03T20:00:00Z',
                'reference_sessions': 1, 'alignment': 'EXACT'}
    coverage = {'eligible_count': 3, 'observed_count': 3, 'count_fraction': 1.0, 'weight_fraction': 1.0}
    def metric(value, unit):
        return {'value': value, 'unit': unit, 'status': 'READY', 'reasons': [], 'n_observations': 1,
                'requested_window': deepcopy(interval), 'actual_window': deepcopy(interval),
                'coverage': deepcopy(coverage), 'method_ref': 'fixture:method:monthly-drift',
                'source_refs': ['fixture:price:one']}
    return {
        'schema': 'factor_atlas_read.v0', 'contract_status': 'PROPOSED', 'status': 'READY', 'reasons': [],
        'descriptor': {'semantic_ref': 'fixture:semantic:house-basket', 'cohort_ref': 'fixture:cohort:three-names',
                       'factor_class': 'house_basket', 'relationship': 'DIRECT'},
        'request': {'history_mode': 'PIT_AS_KNOWN', 'window': deepcopy(interval),
                    'measurement_cutoff': '2026-09-04T00:00:00Z', 'current_roster_snapshot_ref': None},
        'series_spec': {'method_ref': 'fixture:method:monthly-drift', 'measurement_kind': 'portfolio_index',
                        'return_kind': 'TOTAL', 'price_basis': 'tradj', 'currency': 'USD',
                        'calendar_ref': 'fixture:calendar:one', 'session_ref': 'fixture:session:rth',
                        'venue_ref': 'fixture:venue:one', 'weighting': 'equal', 'rebalance': 'monthly',
                        'between_rebalances': 'drift', 'dividend_reinvestment': 'constituent_total_return',
                        'costs_ref': 'fixture:costs:explicit-gross-no-costs', 'gross_leverage': 1.0,
                        'base_level': 100.0},
        'owner_receipt_refs': {key: ['fixture:'+key+':unverified-placeholder']
                               for key in ['membership','identity','prices','actions','rights','calendar']},
        'calculation': {'input_manifest_sha256': '1'*64, 'result_core_sha256': '2'*64, 'code_commit': '0'*40,
                        'dependency_lock_sha256': '3'*64, 'metrics_policy_ref': 'fixture:metrics-policy:v0',
                        'revision_ref': 'fixture:revision:original', 'supersedes_ref': None,
                        'correction_reason': None, 'materialized_at': '2026-09-04T00:00:01Z'},
        'observations': [{'interval_start': interval['start'], 'interval_end': interval['end'],
                          'selection_cutoff': '2026-09-02T13:00:00Z',
                          'membership_revision_ref': 'fixture:membership:one',
                          'return': metric(.05, 'return_fraction'), 'index_level': metric(105.0, 'index_level')}],
        'metrics': {'advance_breadth': metric(2/3, 'fraction'), 'hhi': metric(1/3, 'fraction'),
                    'effective_number': metric(3.0, 'effective_count')},
        'authority': {key: False for key in ['may_rank','may_gate','may_size','may_escalate',
                                            'may_write_portfolio','may_write_theme_state']}
    }
