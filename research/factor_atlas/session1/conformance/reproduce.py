"""Print a deterministic synthetic result core; no native inputs or effects."""
from pathlib import Path
import hashlib
import json
import oracle as o

root = Path(__file__).resolve().parents[1]
initial = [1/3] * 3
first_returns = [1, 0, 0]
second_returns = [-.5, 0, 0]
first = o.strict_return(initial, first_returns)
second_drift = o.strict_return(o.drift_weights(initial, first_returns), second_returns)
second_reset = o.strict_return(initial, second_returns)
source = {'revision': 'fixture:revision:original', 'synthetic_value': 100,
          'source_bytes_sha256': hashlib.sha256(b'SYNTHETIC ORIGINAL INPUT ONLY').hexdigest()}
corrected = {**source, 'revision': 'fixture:revision:corrected',
             'source_bytes_sha256': hashlib.sha256(b'SYNTHETIC CORRECTED INPUT; SAME NUMERIC VALUE').hexdigest()}
result = {
    'scope': 'ORIGINAL_SYNTHETIC_MATHEMATICAL_CONFORMANCE_NOT_NATIVE_PILOT',
    'native_owner_source_files_read': [], 'market_data_read': False, 'network_calls': 0, 'remote_writes': 0,
    'oracle_sha256': hashlib.sha256((root/'conformance/oracle.py').read_bytes()).hexdigest(),
    'schema_sha256': hashlib.sha256((root/'contracts/factor_read_model.v0.schema.json').read_bytes()).hexdigest(),
    'policy_sha256': hashlib.sha256((root/'contracts/metrics_policy.v0.json').read_bytes()).hexdigest(),
    'round_trip': {'monthly_drift_return_fraction': o.horizon_return([first, second_drift], 2),
                   'daily_reset_return_fraction': o.horizon_return([first, second_reset], 2)},
    'synthetic_cohort_comparison': {'current_roster_return_fraction': o.strict_return([.5,.5],[.1,0]),
                                   'pit_return_fraction': o.strict_return([.5,.5],[.1,-.1]),
                                   'qualification': 'fixture calculation, not historical owner membership evidence'},
    'missing_holding': {'return_fraction': o.strict_return([.8,.2],[.1,None]),
                        'available_weight': o.weight_coverage([.8,.2],[.1,None]),
                        'index_with_unresolved_gap': o.link_returns([.1,None,.2])},
    'known_actions': {'split_return_fraction': o.claims_return(100,[2*50]),
                      'dividend_total_return_fraction': o.claims_return(100,[99],cash=2),
                      'spinoff_return_fraction': o.claims_return(100,[80,20]),
                      'cash_merger_return_fraction': o.claims_return(100,[],cash=95),
                      'missing_spinoff_value': o.claims_return(100,[80,None])},
    'concentration_after_drift': o.concentration([.5,.25,.25]),
    'partial_advance_breadth': o.advance_breadth([.1,0,-.1,.2,None],[.2]*5),
    'linked_attribution': o.linked_contributions([{'A':.1,'B':-.02},{'A':-.05,'B':.01}]),
    'correction_input_identity': {'original_sha256':o.canonical_digest(source),
                                 'corrected_sha256':o.canonical_digest(corrected),
                                 'numeric_value_equal':source['synthetic_value']==corrected['synthetic_value']},
}
print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
