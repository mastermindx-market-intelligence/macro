"""Synthetic native-owner replay; never consumes or acquires a licensed tape."""
from datetime import datetime, timezone
from hashlib import sha256
import json

import numpy as np
import pandas as pd
import pytest

from engine import group_pulse as gp
from engine.company_intelligence.defense_profiles import defense_issuer
from engine.government_revenue import defense_participation_context as ctx
from engine.government_revenue.defense_economics import _axis


@pytest.fixture
def native_owner(tmp_path, request):
    last_day = getattr(request, 'param', '2026-06-30')
    index = pd.bdate_range(end=last_day, periods=230)
    tickers = ['LMT', 'SYN-A', 'SYN-B', 'SYN-C']
    rng = np.random.default_rng(317)
    close = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.0001, .01, (230, 4)), axis=0), index=index, columns=tickers)
    volume = pd.DataFrame(1000., index=index, columns=tickers)
    volume.loc[index[-1], ['LMT', 'SYN-A']] = 2000
    benchmark = pd.Series(100 * np.cumprod(1 + rng.normal(.0002, .007, 230)), index=index)
    basket = {'curated': '2026-06-15', 'members': [{'ticker': t, 'added': '2023-01-01', 'removed': None} for t in tickers]}
    panel = gp.build_member_panel(close, volume, benchmark)
    frames = gp.basket_frames(basket, panel, index[-1])
    generated = (index[-1] + pd.Timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
    pulse = gp.basket_pulse('defense', basket, panel, index[-1], {}, {}, generated, frames, [])
    assert gp.validate_pulse(pulse) == []
    membership = {'version': '2026-06-15', 'baskets': {'defense': basket}}
    observation = {'effective_as_of': last_day, 'configured_members': tickers, 'configured_n': 4,
                   'observed_members': tickers, 'observed_n': 4, 'coverage': 1., 'basis': 'exact_close_at_effective_as_of'}
    owner = {'id': 'defense', 'n_members': 4, 'weighting': 'equal', 'members': [{'symbol': t} for t in tickers], 'observation': observation}
    for relative, value in zip(ctx.OWNER_PATHS[:3], (membership, {'defense': pulse}, {'as_of': last_day, 'baskets': [owner]})):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    for ticker in tickers:
        path = tmp_path / f'data/baskets/ohlcv/{ticker}.parquet'
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({'close': close[ticker], 'volume': volume[ticker]}).to_parquet(path)
    path = tmp_path / ctx.OWNER_PATHS[3]
    path.parent.mkdir(parents=True, exist_ok=True)
    benchmark.to_frame('close').to_parquet(path)
    return tmp_path, pulse


def subject():
    issuer = defense_issuer('LMT')
    return {'LMT': {'identity': {'issuer_binding': {'issuer_id': issuer.company_id},
                                'security_id': next(iter(issuer.security_ids_at(datetime.now(timezone.utc).date())))}}}


def qualify(snapshot, financial=None):
    return ctx.qualify_participation_context(snapshot, financial or subject(), generated_at=datetime.now(timezone.utc).isoformat())


def change_json(root, relative, mutate):
    path = root / relative
    value = json.loads(path.read_bytes())
    mutate(value)
    path.write_text(json.dumps(value))


def test_exact_native_replay_binds_breadth_subject_and_distinct_clocks(native_owner, monkeypatch):
    root, pulse = native_owner
    from lib import store
    monkeypatch.setattr(store, 'read', lambda *a, **k: pytest.fail('must not read another checkout through global store'))
    before = {str(p): sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    snapshot = ctx.load_participation_inputs(root)
    result = qualify(snapshot)
    axis = result['axes_by_ticker']['LMT']['participation']
    assert axis['state'] == 'stale' and axis['facts'] == []
    assert f'{pulse["participation"]["activity_n"]}/4' in axis['summary_en']
    assert '2026-06-30' in axis['summary_en'] and '2026-07-01T00:00:00Z' in axis['summary_en']
    assert 'not an alpha leader' in axis['summary_en'] and 'market-cap concentration' in axis['summary_en']
    assert 'current_membership_not_historical_first_seen' in axis['limitations']
    financial = subject()['LMT']['identity']
    projected = _axis('participation', axis, result['source_bindings'], datetime.now(timezone.utc),
                      {'issuer_id': financial['issuer_binding']['issuer_id'], 'security_id': financial['security_id']})
    assert projected['state'] == 'stale' and projected['owner_ref'] == axis['owner_ref']
    assert before == {str(p): sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault', ['count', 'membership', 'cutoff', 'tape', 'benchmark', 'future', 'future_curation'])
def test_owner_or_replay_contradiction_refuses(native_owner, fault):
    root, _ = native_owner
    if fault == 'count':
        change_json(root, ctx.OWNER_PATHS[1], lambda x: x['defense'].update(n_covered=3))
    elif fault == 'membership':
        change_json(root, ctx.OWNER_PATHS[0], lambda x: x['baskets']['defense']['members'].pop())
    elif fault == 'cutoff':
        change_json(root, ctx.OWNER_PATHS[2], lambda x: x.update(as_of='2026-06-29'))
    elif fault in ('tape', 'benchmark'):
        path = root / ('data/baskets/ohlcv/LMT.parquet' if fault == 'tape' else ctx.OWNER_PATHS[3])
        frame = pd.read_parquet(path)
        frame.loc[frame.index[-1], 'close'] *= 2
        frame.to_parquet(path)
    elif fault == 'future':
        change_json(root, ctx.OWNER_PATHS[1], lambda x: x['defense'].update(generated_at='2999-01-01T00:00:00Z'))
    elif fault == 'future_curation':
        change_json(root, ctx.OWNER_PATHS[0], lambda x: x['baskets']['defense'].update(curated='2999-01-01'))
    with pytest.raises(ValueError, match='participation_'):
        ctx.load_participation_inputs(root)


def test_partial_absence_never_becomes_zero_or_procurement_participation(native_owner):
    root, _ = native_owner
    (root / ctx.OWNER_PATHS[3]).unlink()
    assert ctx.load_participation_inputs(root) is None
    assert qualify(None)['axes_by_ticker'] == {}


@pytest.mark.parametrize('native_owner,cutoff,state', [
    ('2026-06-26', '2026-06-28T12:00:00Z', 'partial'),
    ('2026-06-26', '2026-06-29T13:00:00Z', 'partial'),
    ('2026-06-26', '2026-06-29T22:00:00Z', 'stale'),
    ('2026-07-02', '2026-07-03T22:00:00Z', 'partial'),
    ('2026-07-02', '2026-07-06T13:00:00Z', 'partial'),
    ('2026-07-02', '2026-07-06T22:00:00Z', 'stale'),
], indirect=['native_owner'])
def test_freshness_counts_completed_sessions_not_civil_days(native_owner, cutoff, state, monkeypatch):
    clock = datetime.fromisoformat(cutoff.replace('Z', '+00:00'))
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz else clock.replace(tzinfo=None)
    monkeypatch.setattr(ctx, 'datetime', FrozenDatetime)
    snapshot = ctx.load_participation_inputs(native_owner[0])
    result = ctx.qualify_participation_context(snapshot, subject(), generated_at=cutoff)
    assert result['axes_by_ticker']['LMT']['participation']['state'] == state
    assert result['axes_by_ticker']['LMT']['participation']['observed_at'] == clock.isoformat()


def test_reobserved_current_membership_cannot_be_backdated(native_owner):
    snapshot = ctx.load_participation_inputs(native_owner[0])
    result = ctx.qualify_participation_context(snapshot, subject(), generated_at='2026-07-02T00:00:00Z')
    assert result['axes_by_ticker'] == {} and result['local_proof']['state'] == 'observation_after_cutoff'


def test_foreign_security_and_mutated_retained_owner_are_rejected(native_owner):
    snapshot = ctx.load_participation_inputs(native_owner[0])
    financial = subject()
    financial['LMT']['identity']['security_id'] = 'SEC:US-XNYS-NOC'
    with pytest.raises(ValueError, match='subject_mismatch'):
        qualify(snapshot, financial)
    snapshot['raw_bytes'][ctx.OWNER_PATHS[1]] += b' '
    with pytest.raises(ValueError, match='bytes_mismatch'):
        qualify(snapshot)


def test_mutation_during_native_read_and_symlink_cannot_escape_receipt(native_owner, monkeypatch):
    root, _ = native_owner
    original = gp.load_member_tape
    def torn_read(*a, **kw):
        out = original(*a, **kw)
        path = root / ctx.OWNER_PATHS[0]
        path.write_bytes(path.read_bytes() + b' ')
        return out
    monkeypatch.setattr(gp, 'load_member_tape', torn_read)
    with pytest.raises(ValueError, match='inputs_changed'):
        ctx.load_participation_inputs(root)
    path = root / ctx.OWNER_PATHS[3]
    path.rename(path.with_suffix('.held'))
    path.symlink_to(path.with_suffix('.held'))
    with pytest.raises(ValueError, match='symlink'):
        ctx.load_participation_inputs(root)


def test_membership_symlink_is_refused_before_reading_any_content(native_owner, monkeypatch):
    root, _ = native_owner
    path = root / ctx.OWNER_PATHS[0]
    path.rename(path.with_suffix('.held'))
    path.symlink_to(path.with_suffix('.held'))
    monkeypatch.setattr(type(path), 'read_bytes', lambda self: pytest.fail('symlink must be refused before a read'))
    with pytest.raises(ValueError, match='symlink'):
        ctx.participation_input_paths(root)
