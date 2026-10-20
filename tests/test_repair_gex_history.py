"""Archive repair must preserve the qualified book without replacing current data."""
import json
from copy import deepcopy

import pandas as pd
import pytest

from scripts import repair_gex_history as repair
from scripts import build_options_hub_nightly as hub


@pytest.fixture
def archive(tmp_path, monkeypatch):
    history = tmp_path / 'gex_history'
    root = history / 'SPY'
    root.mkdir(parents=True)
    old = dict(root='SPY', asof='2026-10-16', spot_ref=100,
               by_strike=[dict(strike=100, gex_bn=1)],
               history=[dict(date='2026-10-15', value=123)],
               exposure_projection={'old': True})
    path = root / '2026-10-16.json'
    path.write_text(json.dumps(old))
    newer = root / '2026-10-19.json'
    newer.write_text(json.dumps({**old, 'asof': '2026-10-19'}))
    current = tmp_path / 'gex' / 'SPY.json'
    current.parent.mkdir()
    current.write_text(newer.read_text())
    monkeypatch.setattr(repair, 'HIST_DIR', history)
    frame = pd.DataFrame([dict(date='2026-10-16', expiration='2026-10-23', root='SPY', strike=100)])
    monkeypatch.setattr(repair, '_read_year', lambda *a: frame.copy())
    projection = dict(schema='options_hub.exposure_projection/v2', cells_status='complete',
                      metrics={'gamma': {'qualified': 2, 'missing': 1}}, cells=[[1, 2, 3]])
    fresh = {**old, 'net_gex_known_bn': 2, 'exposure_projection': projection}
    import engine.options_exposure_projection as exposure
    context = dict(root='SPY', clocks={'source_session': '2026-10-16'},
                   input_sha256=exposure.exposure_input_digest(frame, frame, '2026-10-16', 'SPY'))
    calls = []
    def compose(g, o, day, root, *, context):
        calls.append((len(g), len(o), day, root, context))
        return context
    monkeypatch.setattr(exposure, 'compose_native_exposure_context', compose)
    monkeypatch.setattr(repair, 'compute_gex', lambda *a, **kw: deepcopy(fresh))
    return path, newer, current, old, fresh, context, calls


def test_qualified_archive_dry_run_and_apply_preserve_current_and_other_dates(archive):
    path, newer, current, old, fresh, context, calls = archive
    original = {p: p.read_bytes() for p in (path, newer, current)}
    tally = repair.repair_root('SPY', None, apply=False, source_date='2026-10-16', exposure_context=context)
    assert tally['changed'] == 1 and tally['n'] == 1
    assert all(p.read_bytes() == body for p, body in original.items())
    tally = repair.repair_root('SPY', None, apply=True, source_date='2026-10-16', exposure_context=context)
    actual = json.loads(path.read_text())
    assert tally['changed'] == 1
    assert actual['exposure_projection'] == fresh['exposure_projection']
    assert actual['net_gex_known_bn'] == 2 and actual['history'] == old['history']
    assert newer.read_bytes() == original[newer] and current.read_bytes() == original[current]
    assert all(c[:4] == (1, 1, '2026-10-16', 'SPY') for c in calls)


@pytest.mark.parametrize('change', [
    {'root': 'QQQ'}, {'clocks': {'source_session': '2026-10-19'}},
    {'_projection_inputs': ()}, {'source_inputs': {}},
])
def test_wrong_or_selected_context_refuses_before_archive_write(archive, change):
    path, _, _, _, _, context, _ = archive
    original = path.read_bytes()
    with pytest.raises(ValueError):
        repair.repair_root('SPY', None, apply=True, source_date='2026-10-16',
                           exposure_context={**context, **change})
    assert path.read_bytes() == original


def test_oversized_preserved_legacy_history_keeps_last_good_archive(archive):
    path, _, _, _, _, context, _ = archive
    old = json.loads(path.read_text()); old['history'] = ['x' * (9 * 1024 * 1024)]
    path.write_text(json.dumps(old)); original = path.read_bytes()
    tally = repair.repair_root('SPY', None, apply=True, source_date='2026-10-16', exposure_context=context)
    assert tally['skipped'] == 1 and tally['changed'] == 0
    assert path.read_bytes() == original


def test_archive_publish_updates_only_successful_roots_truthful_index(archive, monkeypatch):
    path, _, _, _, _, _, _ = archive
    other = path.parent.parent / 'QQQ' / path.name
    other.parent.mkdir(); other.write_text('{}')
    client = object(); uploads = []; indices = []
    monkeypatch.setenv('R2_BUCKET', 'test')
    monkeypatch.setattr(hub, '_r2_client', lambda: client)
    def upload(s3, bucket, local, key):
        uploads.append(key)
        return '/SPY/' in key
    monkeypatch.setattr(hub, '_upload_r2', upload)
    monkeypatch.setattr(hub, 'publish_gex_history_index', lambda *a, **kw: indices.append((a, kw)))
    repair._publish([('SPY', path), ('QQQ', other)], store='existing')
    assert uploads == ['options_hub/gex_history/SPY/2026-10-16.json',
                       'options_hub/gex_history/QQQ/2026-10-16.json']
    assert len(indices) == 1 and indices[0][0][:3] == ('SPY', '2026-10-16', 'existing')
    assert indices[0][1] == {'heal_budget': 0}


def test_context_cli_requires_explicit_root_and_date_before_repairs(monkeypatch):
    monkeypatch.setattr(hub, 'load_exposure_contexts', lambda p: {'SPY': {}})
    with pytest.raises(SystemExit):
        repair.main(['--exposure-context', 'synthetic'])


def test_native_receipt_path_preserves_expiration_representation_in_input_digest():
    from engine.options_exposure_projection import exposure_input_digest
    g = pd.DataFrame([dict(root='SPY', date=pd.Timestamp('2026-10-16'),
        expiration=pd.Timestamp('2026-10-23'), strike=100, right='C', gamma=.1)])
    oi = pd.DataFrame([dict(root='SPY', date=pd.Timestamp('2026-10-16'),
        expiration=pd.Timestamp('2026-10-23'), strike=100, right='C', open_interest=1)])
    expected = exposure_input_digest(g, oi, '2026-10-16', 'SPY')
    normalized = [repair._norm_dates(f, preserve_expiration=True) for f in (g, oi)]
    assert exposure_input_digest(*normalized, '2026-10-16', 'SPY') == expected


def test_changed_input_digest_refuses_before_replacing_archive(archive):
    path, _, _, _, _, context, _ = archive
    before = path.read_bytes(); context['input_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='source rows'):
        repair.repair_root('SPY', None, apply=True, source_date='2026-10-16', exposure_context=context)
    assert path.read_bytes() == before


def test_unqualified_maintenance_cannot_erase_a_dated_projection(archive):
    path, _, _, _, _, _, _ = archive
    old = json.loads(path.read_text())
    old['exposure_projection']['kind'] = 'dated_provider_approximation'
    path.write_text(json.dumps(old)); before = path.read_bytes()
    tally = repair.repair_root('SPY', None, apply=True, source_date='2026-10-16')
    assert tally['skipped'] == 1 and tally['changed'] == 0
    assert path.read_bytes() == before
