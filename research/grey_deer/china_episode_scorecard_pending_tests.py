"""Pending shared-scorecard projection acceptance; not a green product suite."""
import json
from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from engine import risk_radar_scorecard as sc

def _write_jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# Shared machine-feed projection: use the accepted episode owner, not raw alert N.
def _episode_projection_rows():
    days = pd.bdate_range('2026-01-02', periods=100)
    return [{'asof': str(day.date()), 'state': 'risk-off' if i >= 60 else 'calm',
             'alert': i >= 60, 'dominant_scare': 'synthetic',
             'graded': {'any_dd5_within_h21': i >= 60,
                        'outcome': 'true_positive' if i >= 60 else 'calm_quiet',
                        'fwd_dd': {'h21': -.1 if i >= 60 else 0.}}}
            for i, day in enumerate(days)]


def _episode_projection(root, market='cn'):
    return sc.build(root=root, today=date(2026, 9, 24))['markets'][market]['evidence_units']


@pytest.mark.parametrize('market', ['cn', 'hk', 'ca'])
def test_episode_projection_separates_daily_calls_from_independent_units(tmp_path, market):
    rows = _episode_projection_rows()
    _write_jsonl(tmp_path / 'data/risk_radar_intl' / f'{market}_forward_log.jsonl', rows)
    unit = _episode_projection(tmp_path, market)
    assert unit['status'] == 'accruing'
    assert unit['basis'] == 'stored_forward_log_full_history'
    assert unit['counts']['complete_graded_rows'] == 100
    assert unit['counts']['loud_daily_rows'] == 40
    assert unit['counts']['independent_base_windows'] == 5
    assert unit['counts']['matured_loud_episodes'] == 1
    assert unit['counts']['loud_episode_hits'] == 1
    assert unit['counts']['open_loud_episodes'] == 0


@pytest.mark.parametrize('fault', ['missing', 'broken_json', 'scalar', 'invalid_date', 'future_date'])
def test_episode_projection_unavailable_is_not_zero_evidence(tmp_path, fault):
    path = tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl'
    rows = _episode_projection_rows()
    if fault == 'invalid_date': rows[-1]['asof'] = '2026-04-30junk'
    if fault == 'future_date': rows[-1]['asof'] = '2026-10-01'
    if fault != 'missing':
        _write_jsonl(path, rows)
        if fault in ('broken_json', 'scalar'):
            with path.open('a') as handle:
                handle.write('{broken\n' if fault == 'broken_json' else '42\n')
    unit = _episode_projection(tmp_path)
    assert unit['status'] == 'unavailable'
    assert unit['counts'] and all(v is None for v in unit['counts'].values())
    assert unit['reasons']


def test_episode_projection_empty_existing_ledger_has_known_zero_counts(tmp_path):
    _write_jsonl(tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl', [])
    unit = _episode_projection(tmp_path)
    assert unit['status'] == 'empty'
    assert all(v == 0 for v in unit['counts'].values())
    assert unit['reasons'] == []


@pytest.mark.parametrize('grade', [None, {}, {'outcome': 'not-a-complete-grade'}])
def test_episode_projection_incomplete_outcomes_do_not_mature_an_episode(tmp_path, grade):
    rows = [{'asof': '2026-09-03', 'state': 'risk-off', 'alert': True, 'graded': grade}]
    _write_jsonl(tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl', rows)
    count = _episode_projection(tmp_path)['counts']
    assert count['complete_graded_rows'] == count['matured_loud_episodes'] == 0
    assert count['open_loud_episodes'] == 1


def test_episode_projection_has_no_authority_or_model_validation(tmp_path):
    _write_jsonl(tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl', _episode_projection_rows())
    unit = _episode_projection(tmp_path)
    for key in ('authority_source', 'same_model_verified', 'probability_validated', 'capital_policy_validated'):
        assert unit[key] is False
    assert 'can_force' not in unit and 'gross' not in unit
    assert unit['asof_reference'] == '2026-09-24'


def test_episode_projection_does_not_roll_out_to_unqualified_markets(tmp_path):
    result = sc.build(root=tmp_path, today=date(2026, 9, 24))
    for market in ('us', 'kr', 'jp', 'tw', 'in', 'au', 'gb', 'ez'):
        assert 'evidence_units' not in result['markets'][market]


def test_episode_projection_uses_the_canonical_derivation_once(tmp_path, monkeypatch):
    from engine import risk_radar_intl_evidence as evidence
    rows = _episode_projection_rows()
    _write_jsonl(tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl', rows)
    real = evidence.derive_evidence
    calls = []
    def tracked(values):
        calls.append(values)
        return real(values)
    monkeypatch.setattr(evidence, 'derive_evidence', tracked)
    unit = _episode_projection(tmp_path)
    assert calls == [rows]
    assert unit['counts']['matured_loud_episodes'] == 1


def test_episode_projection_roundtrip_uses_existing_two_output_paths(tmp_path):
    _write_jsonl(tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl', _episode_projection_rows())
    result = sc.write(root=tmp_path)
    data = json.loads((tmp_path / 'data/risk_radar/scorecard.json').read_text())
    site = json.loads((tmp_path / 'site/riskdata/scorecard.json').read_text())
    assert result == data == site
    assert data['markets']['cn']['evidence_units']['counts']['matured_loud_episodes'] == 1
    assert data['schema'] == 'risk_radar_scorecard.v1'
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*') if p.is_file()) == [
        'data/risk_radar/scorecard.json', 'data/risk_radar_intl/cn_forward_log.jsonl',
        'site/riskdata/scorecard.json']


def test_episode_projection_duplicate_dates_do_not_multiply_trials(tmp_path):
    path = tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl'
    rows = _episode_projection_rows()
    _write_jsonl(path, rows)
    expected = _episode_projection(tmp_path)['counts']
    _write_jsonl(path, rows + rows[-10:])
    assert _episode_projection(tmp_path)['counts'] == expected


def test_episode_projection_read_error_is_explicit(tmp_path, monkeypatch):
    path = tmp_path / 'data/risk_radar_intl/cn_forward_log.jsonl'
    _write_jsonl(path, _episode_projection_rows())
    original = Path.read_text
    def fail_selected(self, *args, **kwargs):
        if self == path: raise PermissionError('synthetic read failure')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', fail_selected)
    unit = _episode_projection(tmp_path)
    assert unit['status'] == 'unavailable'
    assert all(v is None for v in unit['counts'].values())
    assert 'read_error' in unit['reasons']
