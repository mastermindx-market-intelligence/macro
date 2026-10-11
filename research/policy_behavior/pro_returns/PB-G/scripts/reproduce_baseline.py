#!/usr/bin/env python3
"""PB-G read-only recomputation of immutable A/B/E returns. No forecast recoding.

Fetch the immutable files named in PB_G_BASELINE_SOURCE_RECEIPTS.json into a
user-selected disposable directory, preserving their exact bytes and basenames.
Pass that directory with --source-dir. This script performs no network requests.
The receipts and output default to the PB-G packet root, beside this scripts/
directory. The supplied PB-A pilot is consulted only after independent scoring.
Outputs are synthesis evidence, not a new canonical event database or live model.
"""
from pathlib import Path
from collections import Counter
from itertools import combinations
import argparse
import hashlib
import json
import math

PACKET_ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir', type=Path, required=True,
                    help='Disposable directory of exact immutable source mirrors, named per receipts')
parser.add_argument('--receipts', type=Path,
                    default=PACKET_ROOT / 'PB_G_BASELINE_SOURCE_RECEIPTS.json',
                    help='Source receipt manifest; defaults to the PB-G packet root')
parser.add_argument('--output', type=Path,
                    default=PACKET_ROOT / 'PB_G_BASELINE_RECOMPUTED.json',
                    help='Output JSON file; defaults to the PB-G packet root')
args = parser.parse_args()
SOURCE_ROOT = args.source_dir.resolve()

def read(name):
    return json.loads((SOURCE_ROOT / name).read_text())

def git_blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

receipts = json.loads(args.receipts.read_text())
for source in receipts['sources']:
    raw = (SOURCE_ROOT / source['file']).read_bytes()
    assert git_blob_sha(raw) == source['git_blob_sha'], source['file']

casebook = read('PB_A_CASEBOOK.json')
forecast = read('PB_A_FORECAST_FREEZE.json')['forecast_payload']
outcomes = read('PB_A_OUTCOMES.json')
cases = {x['episode_id']: x for x in casebook['episodes']}
predictions = {x['episode_id']: x for x in forecast['episodes']}
truths = {x['episode_id']: x for x in outcomes['episodes']}
assert set(cases) == set(predictions) == set(truths)
models = ['M0', 'M1', 'M2', 'C0', 'C1']
classes = ['DOWN', 'HOLD', 'UP']
assert forecast['class_order'] == classes
targets = ['fed_target_midpoint_net_direction', 'first_subsequent_rate_change_within_horizon']
horizons = ['1', '3', '6']
primary = [k for k, v in predictions.items() if v['cohort'] == 'PRIMARY']
challenge = [k for k, v in predictions.items() if v['cohort'] == 'ADVERSARIAL_CHALLENGE']

def pred(episode, horizon, target, model):
    return predictions[episode]['forecasts'][horizon]['policy_targets'][target][model]

def truth(episode, horizon, target):
    return truths[episode]['horizons'][horizon]['policy']['targets'][target]

def score(ids, horizon, target, model):
    eligible = [i for i in ids if truth(i, horizon, target)['status'] == 'OBSERVED']
    scored = [i for i in eligible if not pred(i, horizon, target, model)['abstain']]
    correct = 0
    brier, nll = [], []
    for episode in scored:
        f = pred(episode, horizon, target, model)
        y = truth(episode, horizon, target)['direction']
        probabilities = f['probabilities_down_hold_up']
        assert abs(sum(probabilities) - 1) < 1e-12
        assert probabilities[classes.index(f['direction'])] == .6
        assert all(p == .2 for c, p in zip(classes, probabilities) if c != f['direction'])
        correct += f['direction'] == y
        brier.append(sum((p - int(c == y)) ** 2 for c, p in zip(classes, probabilities)))
        nll.append(-math.log(probabilities[classes.index(y)]))
    n = len(scored)
    return {
        'eligible_count': len(eligible), 'scored_count': n, 'correct_count': correct,
        'accuracy': correct / n if n else None,
        'coverage': n / len(eligible) if eligible else None,
        'abstentions': len(eligible) - n,
        'brier': sum(brier) / n if n else None,
        'negative_log_loss': sum(nll) / n if n else None,
        'episode_ids': scored,
        'true_class_counts': dict(Counter(truth(i, horizon, target)['direction'] for i in scored)),
    }

def comparison(ids, horizon, target, members):
    common = [i for i in ids if truth(i, horizon, target)['status'] == 'OBSERVED'
              and all(not pred(i, horizon, target, m)['abstain'] for m in members)]
    return {
        'count': len(common), 'episode_ids': common,
        'models': {m: score(common, horizon, target, m) for m in members},
        'direction_disagreement_ids': [i for i in common if len({pred(i, horizon, target, m)['direction'] for m in members}) > 1],
    }

def summarize(ids):
    return {target: {h: {
        'own_coverage': {m: score(ids, h, target, m) for m in models},
        'pairwise_common_coverage': {'__'.join(pair): comparison(ids, h, target, pair)
                                     for pair in combinations(models, 2)},
        'all_three_common_coverage': comparison(ids, h, target, ['M0', 'M1', 'M2']),
    } for h in horizons} for target in targets}

result = {
    'schema': 'pb_g_frozen_baseline_reconciliation.v1',
    'scope': 'RESEARCH_ONLY; independent arithmetic over unchanged historical forecast and outcome artifacts',
    'methodology': {
        'M2_alias': 'M2-min, new-action persistence plus conventional policy-floor exception; rich M2 untested',
        'probabilities': 'Immutable [0.6 coded class; 0.2 each alternative]; no fitted or calibrated probabilities',
        'source_files_verified_against_git_blob_sha': len(receipts['sources']),
        'historical_decision_inputs_modified': False,
        'historical_forecasts_modified': False,
        'historical_outcomes_modified': False,
        'secondary_slices': 'PB-G descriptive reaggregation; no new confirmatory estimand or inferential test',
    },
    'primary_count': len(primary), 'separate_challenge_count': len(challenge),
    'primary': summarize(primary), 'challenge': summarize(challenge),
    'source_family': {}, 'source_regime': {},
}

for field, output in [('episode_family', 'source_family'), ('regime', 'source_regime')]:
    for value in sorted({cases[i][field] for i in primary}):
        selected = [i for i in primary if cases[i][field] == value]
        result[output][value] = {
            'episode_count': len(selected), 'episode_ids': selected,
            'targets': {target: {h: {m: score(selected, h, target, m) for m in models}
                                 for h in horizons} for target in targets},
        }

result['target_outcome_mismatch_rows'] = [
    {'episode_id': i, 'horizon': h}
    for i in cases for h in horizons
    if truth(i, h, targets[0])['direction'] != truth(i, h, targets[1])['direction']
]

# Verify the independent calculations against source pilot after computing all results.
pilot = read('PB_A_BASELINE_PILOT.json')
checks = 0
for cohort_name, computed in [('PRIMARY', result['primary']), ('ADVERSARIAL_CHALLENGE', result['challenge'])]:
    for target in targets:
        for h in horizons:
            original = pilot['cohorts'][cohort_name]['targets'][target][h]['ALL']
            for model in models:
                a = computed[target][h]['own_coverage'][model]
                b = original['own_coverage'][model]
                assert a['scored_count'] == b['count']
                assert a['episode_ids'] == b['episode_ids']
                for left, right in [('accuracy', 'direction_accuracy'), ('brier', 'multiclass_brier_sum_squared_range_0_to_2'), ('negative_log_loss', 'negative_log_likelihood_natural_log')]:
                    assert (a[left] is None and b[right] is None) or math.isclose(a[left], b[right], abs_tol=1e-12)
                checks += 1
result['supplied_pilot_own_score_groups_exactly_reproduced'] = checks

b = read('PB_B_CASEBOOK.json')
b_forecasts = [(row['episode_id'], model, f) for row in b['episodes'] for model, f in row['decision_time']['forecasts'].items()]
assert len(b_forecasts) == 45
assert all(f['abstention_state']['abstains'] and f['directional_or_probabilistic_forecast'] is None and f['probability'] is None for _, _, f in b_forecasts)
result['PB_B'] = {
    'snapshot_count': len(b['episodes']), 'forecast_slot_count': len(b_forecasts),
    'abstention_count': len(b_forecasts), 'comparison_eligible_count': sum(r['accuracy_comparison_eligible'] for r in b['episodes']),
    'policy_target_cluster_counts': dict(Counter(r['policy_target_cluster_id'] for r in b['episodes'])),
    'family_counts': dict(Counter(r['episode_family'] for r in b['episodes'])),
    'case_membership': [{'episode_id': r['episode_id'], 'family': r['episode_family'], 'policy_target_cluster_id': r['policy_target_cluster_id'], 'cut': r['decision_cut_utc']} for r in b['episodes']],
    'target': 'Next scheduled BOJ announcement, not the PB-A fixed calendar-horizon Fed endpoints',
}
e = read('PB_E_NETWORK_EDGES.json')
result['PB_E'] = {
    'structural_dossier_count': len(e['cases']), 'edge_count': len(e['edges']),
    'forecast_comparison_eligible': 0,
    'reason': 'Financial/legal relationship dossiers with typed obligations and observations; no frozen M0/M1/M2 forecast target, horizon, probabilities or same-cut outcome comparators',
    'case_membership': [{'case_id': r['case_id'], 'title': r['title'], 'control_type': r['control_type']} for r in e['cases']],
    'taxonomy_names': list(e['taxonomy']),
}
result['denominator_ruling'] = {
    'policy_primary_snapshots_A_plus_B': len(primary) + len(b['episodes']),
    'heterogeneous_records_A_B_E_excluding_challenge': len(primary) + len(b['episodes']) + len(e['cases']),
    'heterogeneous_records_including_separate_challenge': len(cases) + len(b['episodes']) + len(e['cases']),
    'A_M0_M2_min_common_primary_episodes': len(result['primary'][targets[0]]['1']['pairwise_common_coverage']['M0__M2']['episode_ids']),
    'A_all_three_common_primary_episodes': len(result['primary'][targets[0]]['1']['all_three_common_coverage']['episode_ids']),
    'rich_M2_scored_episodes': 0,
    'supported_40_to_60_comparable_baseline': False,
    'ruling': 'PRECISE_DATA_INSUFFICIENCY_PROVEN; historical abstentions and the separate challenge remain unchanged',
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'verified_sources': len(receipts['sources']), 'verified_score_groups': checks, 'denominators': result['denominator_ruling']}, indent=2))
