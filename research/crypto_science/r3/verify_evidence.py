"""Verify the frozen R3 diagnostic; passing is not strategy acceptance.

Reads local recorded outputs and their exact input/source hashes. Never calls
providers, model gates or data writers. Recompute only the accounting assertions,
not the predictive study or its thresholds.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    r = json.loads((HERE / 'cohort_results.json').read_text())
    assert r['classification'] == 'SOURCE_OBSERVED_RETROSPECTIVE_DIAGNOSTIC_NOT_PUBLICATION_QUALIFIED'
    assert r['plan_commit'] == '953eedfa53a5a201efebc03b74853316cad6a2cf'
    assert r['candidate_head'] == 'cc5f0a2d16311db7639aba5f8f54ef6772a30374'
    assert r['script_sha256'] == digest(HERE.parent / 'r3_cohort_study.py')
    hashes = r['input_source_gate_sha256']
    assert len(hashes) == 15
    for relative, expected in hashes.items():
        assert digest(ROOT / relative) == expected, f'Input/source drift: {relative}'
    assert r['unchanged'] is True and r['default_fire_parity'] is True
    assert r['funding']['current_values_unchanged'] is True
    assert r['funding']['old_new_semantic_equivalence'] == 'NOT_ESTABLISHED'

    signals = pd.read_csv(HERE / 'source_observed_conditions.csv', index_col='date',
                          parse_dates=['date'], dtype={'d2': 'boolean', 'd3': 'boolean', 'u1': 'boolean'})
    assert len(signals) == 4393 and signals.index.is_unique and signals.index.is_monotonic_increasing
    for key, values in r['observations'].items():
        assert int(signals[key].notna().sum()) == values['observed_days']
        assert int(signals[key].isna().sum()) == values['unknown_days']
        assert values['known_condition_parity'] is True
    episodes = pd.read_csv(HERE / 'episode_outcomes.csv', parse_dates=['date'])
    rows = r['cohorts']
    expected = set(itertools.product(
        ['R2_mature_only', 'observed_lag0', 'observed_assumed_lag1d', 'observed_assumed_lag2d'],
        ['d2', 'd3', 'u1'], ['full', 'reused_2024_plus'], [3, 7]))
    actual = [(x['policy'], x['leg'], x['period'], x['episode_separation_days']) for x in rows]
    assert len(rows) == 48 and set(actual) == expected and len(set(actual)) == 48
    assert len(episodes) == 2090  # Repeated scenario outcomes, NOT independent sample size.
    for row in rows:
        p, leg, period, sep = row['policy'], row['leg'], row['period'], row['episode_separation_days']
        e = episodes[(episodes.policy == p) & (episodes.leg == leg)
                     & (episodes.period == period) & (episodes.separation_days == sep)]
        assert e.date.is_unique
        assert e.date.sort_values().diff().dropna().gt(pd.Timedelta(days=sep)).all()
        if period == 'reused_2024_plus':
            assert e.date.ge(pd.Timestamp('2024-01-01')).all()
        n, h = len(e), int(e.hit.sum())
        assert n == row['mature_episodes'] and h == row['hit_episodes']
        assert row['false_episodes'] == n - h
        assert row['selected_onsets'] == n + row['pending_or_ineligible_episodes']
        assert 0 <= row['hit_trigger_rows'] <= row['trigger_rows'] <= row['eligible_days']
        assert 0 <= row['positive_outcome_days'] <= row['eligible_days'] <= row['known_source_days']
        if n:
            assert np.isclose(h / n, row['episode_hit_fraction'])
            assert np.isclose(e.forward_min_pct.median(), row['episode_forward_min_median_pct'])
            assert np.isclose(e.forward_max_pct.median(), row['episode_forward_max_median_pct'])
        if row['trigger_rows']:
            assert np.isclose(row['hit_trigger_rows'] / row['trigger_rows'], row['conditional_event_frequency'])
        if row['eligible_days']:
            assert np.isclose(row['positive_outcome_days'] / row['eligible_days'], row['base_rate'])
            assert np.isclose(30 * (n - h) / row['eligible_days'], row['false_episodes_per_30_eligible_days'])
        ci = row['episode_hit_fraction_block95']
        assert ci is None or (0 <= ci[0] <= ci[1] <= 1)
        assert e.forward_min_pct.le(e.forward_max_pct).all()
        hit = e.forward_min_pct.le(-5.) if leg != 'u1' else e.forward_max_pct.ge(5.)
        assert np.array_equal(hit.to_numpy(), e.hit.to_numpy())

    # R1/R2 evidence is immutable; we do not re-run a now-superseded diagnostic.
    old_paths = ['research/crypto_science/r2', 'research/crypto_science/r2_replay.py',
                 'research/crypto_science/temporal_audit_r1.py',
                 'research/crypto_science/temporal_audit_initial.py',
                 'research/crypto_science/r1_audit.json', 'research/crypto_science/r1_audit_initial.json',
                 'research/crypto_science/r1_prefix_cutoffs.csv',
                 'research/crypto_science/r1_prefix_cutoffs_initial.csv',
                 'research/crypto_science/r1_label_boundary_exploratory.json']
    changed = subprocess.check_output(['git', 'diff', '--name-only', r['baseline'], '--', *old_paths],
                                      cwd=ROOT, text=True).strip()
    assert not changed, f'Prior evidence changed: {changed}'
    manifest = HERE / 'MANIFEST.json'
    if manifest.exists():
        for entry in json.loads(manifest.read_text())['files']:
            assert digest(HERE / entry['path']) == entry['sha256'], entry['path']
    print('R3_EVIDENCE_VERIFIED: 48 cohorts, 2090 scenario-episode rows; mature counts, dates, hits and rates agree.')
    print('INPUT_SOURCE_GATE_HASHES: 15 unchanged. Default fire and current funding parity retained. R1/R2 unchanged.')
    print('DIAGNOSTIC ONLY: source observed is not publication qualified; no live gate or allocation acceptance.')


if __name__ == '__main__':
    main()
