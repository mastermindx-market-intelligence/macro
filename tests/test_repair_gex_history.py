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
    assert indices[0][1]['heal_budget'] == 0 and set(indices[0][1]) == {'heal_budget', 'outcome'}
    assert isinstance(indices[0][1]['outcome'], dict)


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


# ---------------------------------------------------------------------------
# Truthful archive publication outcome + main CLI failure propagation.
# A False upload or an exception is unconfirmed — never proof a remote object
# is absent — and every scenario below uses fake clients only.
# ---------------------------------------------------------------------------

R2_KEY = 'options_hub/gex_history/SPY/2026-10-16.json'
NOT_ATTEMPTED_INDEX = {'key': 'options_hub/gex_history/SPY/dates.json', 'status': 'not_attempted', 'index_attempted': False,
                       'index_uploaded': None, 'healed': 0}


def _recording_upload(calls, verdicts):
    """Fake _upload_r2: verdicts(key) -> bool or exception instance; no network."""
    def upload(s3, bucket, local, key):
        calls.append(key)
        verdict = verdicts(key)
        if isinstance(verdict, BaseException):
            raise verdict
        return verdict
    return upload


def _contract_publish(calls, status='success'):
    """Fake index publisher honoring the detailed-outcome seam contract."""
    def publish(root, asof, theta_store, polygon_gex_dir, out_dir, s3, bucket,
                heal_budget=0, **kw):
        calls.append((root, asof, heal_budget))
        outcome = kw.get('outcome')
        if outcome is not None:
            outcome.update(status=status, list_ok=status != 'list_failed',
                           index_attempted=status != 'list_failed',
                           index_uploaded=(status == 'success'), healed=0)
        return 0
    return publish


def _legacy_publish(calls):
    """The pre-fix index seam: integer healed count only, outcome ignored."""
    def publish(root, asof, theta_store, polygon_gex_dir, out_dir, s3, bucket,
                heal_budget=0, **kw):
        calls.append((root, asof, heal_budget))
        return 0
    return publish


def _wire(archive, monkeypatch, *, upload, publish, client=object(), bucket='test'):
    _, _, _, _, _, context, _ = archive
    monkeypatch.setattr(hub, 'load_exposure_contexts', lambda p: {'SPY': context})
    monkeypatch.setattr(hub, '_r2_client', lambda: client)
    if bucket is None:
        monkeypatch.delenv('R2_BUCKET', raising=False)
    else:
        monkeypatch.setenv('R2_BUCKET', bucket)
    monkeypatch.setattr(hub, '_upload_r2', upload)
    monkeypatch.setattr(hub, 'publish_gex_history_index', publish)


MAIN_ARGS = ['--apply', '--publish', '--date', '2026-10-16', '--roots', 'SPY',
             '--exposure-context', 'synthetic']


def test_regression_failed_publication_that_used_to_exit_zero_now_exits_nonzero(archive, monkeypatch):
    """Regression for the commissioned defect: with the snapshot upload returning
    False and the legacy index seam returning 0 healed, the OLD main returned 0
    even though the requested publication had failed. Not just a missing new
    API — this is exactly the old silent-success path."""
    path, _, current, _, _, _, _ = archive
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: False),
          publish=_legacy_publish(publish_calls))
    before = current.read_bytes()
    assert repair.main(MAIN_ARGS) == 1
    assert uploads == [R2_KEY]                          # one attempt, no implicit retry
    assert publish_calls == []                          # no confirmed snapshot → no index
    assert current.read_bytes() == before               # no current gex/vol/boards writes
    assert json.loads(path.read_text())['net_gex_known_bn'] == 2  # local repair still applied


def test_publish_missing_client_or_bucket_marks_every_key_not_attempted(archive, monkeypatch):
    path, _, _, _, _, _, _ = archive
    uploads, publish_calls = [], []
    for kwargs in ({'client': None}, {'bucket': None}):
        uploads.clear(); publish_calls.clear()
        _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
              publish=_contract_publish(publish_calls), **kwargs)
        summary = repair._publish([('SPY', path)])
        assert sorted(summary) == ['attempted', 'confirmed', 'incomplete', 'indices',
                                   'keys', 'not_attempted', 'requested', 'unconfirmed']
        assert summary['keys'] == {R2_KEY: {'status': 'not_attempted', 'attempts': 0}}
        assert summary['indices'] == {'SPY': dict(NOT_ATTEMPTED_INDEX)}
        assert (summary['requested'], summary['attempted'], summary['confirmed'],
                summary['unconfirmed'], summary['not_attempted']) == (1, 0, 0, 0, 1)
        assert summary['incomplete'] is True
        assert uploads == [] and publish_calls == []    # explicitly never attempted


def test_main_missing_client_exits_nonzero_without_attempts(archive, monkeypatch):
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=_contract_publish(publish_calls), client=None)
    assert repair.main(MAIN_ARGS) == 1
    assert uploads == [] and publish_calls == []


def test_publish_import_failure_marks_keys_not_attempted(archive, monkeypatch):
    path, _, _, _, _, context, _ = archive
    monkeypatch.setattr(hub, 'load_exposure_contexts', lambda p: {'SPY': context})
    monkeypatch.setenv('R2_BUCKET', 'test')
    monkeypatch.delattr(hub, '_r2_client')              # publish seam import fails
    summary = repair._publish([('SPY', path)])
    assert summary['keys'] == {R2_KEY: {'status': 'not_attempted', 'attempts': 0}}
    assert summary['indices'] == {'SPY': dict(NOT_ATTEMPTED_INDEX)}
    assert summary['not_attempted'] == 1 and summary['incomplete'] is True


@pytest.mark.parametrize('verdict', [False, RuntimeError('synthetic upload failure')])
def test_snapshot_upload_false_or_exception_is_unconfirmed_never_retried(archive, monkeypatch, verdict):
    path, _, _, _, _, _, _ = archive
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: verdict),
          publish=_contract_publish(publish_calls))
    summary = repair._publish([('SPY', path)])
    status = 'unconfirmed' if verdict is False else 'exception'
    assert summary['keys'] == {R2_KEY: {'status': status, 'attempts': 1}}
    assert uploads == [R2_KEY]                          # exactly one attempt, no retry
    assert summary['indices'] == {'SPY': dict(NOT_ATTEMPTED_INDEX)}
    assert summary['confirmed'] == 0 and summary['unconfirmed'] == 1
    assert summary['incomplete'] is True and publish_calls == []


def test_partial_success_preserves_confirmed_and_fails_the_run(archive, monkeypatch):
    path, _, _, _, _, _, _ = archive
    other = path.parent.parent / 'QQQ' / path.name
    other.parent.mkdir(exist_ok=True); other.write_text('{}')
    qqq_key = 'options_hub/gex_history/QQQ/2026-10-16.json'
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch,
          upload=_recording_upload(uploads, lambda key: key.endswith('/SPY/2026-10-16.json')),
          publish=_contract_publish(publish_calls))
    summary = repair._publish([('SPY', path), ('QQQ', other)])
    assert uploads == [R2_KEY, qqq_key]                 # both requested keys attempted once
    assert summary['keys'] == {R2_KEY: {'status': 'confirmed', 'attempts': 1},
                               qqq_key: {'status': 'unconfirmed', 'attempts': 1}}
    assert summary['confirmed'] == 1 and summary['unconfirmed'] == 1
    assert summary['indices'] == {
        'SPY': {'key': 'options_hub/gex_history/SPY/dates.json', 'status': 'success', 'index_attempted': True, 'index_uploaded': True,
                'healed': 0},
        'QQQ': {**NOT_ATTEMPTED_INDEX, 'key': 'options_hub/gex_history/QQQ/dates.json'}}
    assert summary['incomplete'] is True                # acknowledged success kept, run fails


def test_publish_all_success_main_exits_zero_exact_calls(archive, monkeypatch):
    path, _, current, _, _, _, _ = archive
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=_contract_publish(publish_calls))
    before = current.read_bytes()
    assert repair.main(MAIN_ARGS) == 0
    assert uploads == [R2_KEY]                          # exact dated key only
    assert publish_calls == [('SPY', '2026-10-16', 0)]  # heal_budget=0, dated asof only
    assert current.read_bytes() == before               # no current gex/vol/boards writes


def test_index_publish_exception_is_unconfirmed_and_keeps_object_success(archive, monkeypatch):
    path, _, _, _, _, _, _ = archive
    uploads, publish_calls = [], []
    def publish(*a, **kw):
        publish_calls.append(a)
        raise RuntimeError('synthetic index failure')
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=publish)
    summary = repair._publish([('SPY', path)])
    assert summary['keys'][R2_KEY] == {'status': 'confirmed', 'attempts': 1}
    assert summary['indices'] == {'SPY': {'key': 'options_hub/gex_history/SPY/dates.json', 'status': 'exception', 'index_attempted': None,
                                          'index_uploaded': None, 'healed': 0}}
    assert summary['confirmed'] == 1 and summary['incomplete'] is True
    assert len(publish_calls) == 1                      # attempted once, not retried


def test_real_seam_list_failure_reports_list_failed_and_main_exits_nonzero(archive, monkeypatch):
    """The REAL publish_gex_history_index against a fake client whose LIST fails:
    it returns 0 exactly like a genuine zero-heal success, so the detailed
    outcome must carry the distinction — zero healed is not success."""
    path, _, _, _, _, _, _ = archive
    uploads = []
    class FailingList:
        def list_objects_v2(self, **kw):
            raise RuntimeError('synthetic list failure')
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=hub.publish_gex_history_index, client=FailingList())
    summary = repair._publish([('SPY', path)])
    assert uploads == [R2_KEY]
    assert summary['keys'][R2_KEY] == {'status': 'confirmed', 'attempts': 1}
    assert summary['indices'] == {'SPY': {'key': 'options_hub/gex_history/SPY/dates.json', 'status': 'list_failed', 'index_attempted': False,
                                          'index_uploaded': None, 'healed': 0}}
    assert summary['confirmed'] == 1 and summary['incomplete'] is True
    uploads.clear()
    assert repair.main(MAIN_ARGS) == 1
    assert uploads == [R2_KEY]                          # main publication attempted once more


def test_real_seam_index_upload_false_is_unconfirmed_but_written_locally(archive, monkeypatch):
    path, _, _, _, _, _, _ = archive
    uploads, list_calls, heal_calls = [], [], []
    class EmptyList:
        def list_objects_v2(self, **kw):
            list_calls.append(kw['Prefix'])
            return {'Contents': [], 'IsTruncated': False}
    _wire(archive, monkeypatch,
          upload=_recording_upload(uploads, lambda key: not key.endswith('dates.json')),
          publish=hub.publish_gex_history_index, client=EmptyList())
    monkeypatch.setattr(hub, 'gex_history_missed_sessions', lambda existing, asof: [])
    monkeypatch.setattr(hub, '_heal_gex_history',
                        lambda *a, **k: heal_calls.append(a) or [])
    monkeypatch.setattr(hub, 'build_gex_dates_index',
                        lambda days, *, root, asof: {'root': root, 'dates': list(days)})
    summary = repair._publish([('SPY', path)])
    index = json.loads((repair.HIST_DIR / 'SPY' / 'dates.json').read_text())
    assert index == {'root': 'SPY', 'dates': []}        # index written locally, then…
    assert summary['indices'] == {'SPY': {'key': 'options_hub/gex_history/SPY/dates.json', 'status': 'index_upload_unconfirmed',
                                          'index_attempted': True, 'index_uploaded': False,
                                          'healed': 0}}
    assert uploads == [R2_KEY, 'options_hub/gex_history/SPY/dates.json']
    assert list_calls == ['options_hub/gex_history/SPY/']   # one LIST, no implicit retry
    assert len(heal_calls) == 1 and heal_calls[0][1] == []  # heal_budget=0, nothing to heal
    assert summary['incomplete'] is True


def test_no_change_publication_requests_nothing_and_exits_zero(archive, monkeypatch):
    _, _, _, old, _, _, _ = archive
    uploads, publish_calls, client_calls = [], [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=_contract_publish(publish_calls))
    monkeypatch.setattr(hub, '_r2_client', lambda: client_calls.append(1) or object())
    monkeypatch.setattr(repair, 'compute_gex', lambda *a, **kw: deepcopy(old))
    assert repair.main(MAIN_ARGS) == 0
    assert uploads == [] and publish_calls == [] and client_calls == []
    assert repair._publish([]) == {'requested': 0, 'attempted': 0, 'confirmed': 0,
                                   'unconfirmed': 0, 'not_attempted': 0, 'keys': {},
                                   'indices': {}, 'incomplete': False}


def test_dry_run_publish_ignored_effect_free_same_exit_semantics(archive, monkeypatch):
    path, newer, current, _, _, _, _ = archive
    uploads, publish_calls = [], []
    _wire(archive, monkeypatch, upload=_recording_upload(uploads, lambda key: True),
          publish=_contract_publish(publish_calls))
    def _no_client():
        raise AssertionError('dry run must not construct an R2 client')
    monkeypatch.setattr(hub, '_r2_client', _no_client)
    original = {p: p.read_bytes() for p in (path, newer, current)}
    assert repair.main(['--publish', '--date', '2026-10-16', '--roots', 'SPY',
                        '--exposure-context', 'synthetic']) == 0
    assert all(p.read_bytes() == body for p, body in original.items())
    assert uploads == [] and publish_calls == []


@pytest.mark.parametrize('stage', ['list', 'local_write', 'upload'])
def test_index_exception_preserves_actual_upload_phase(archive, monkeypatch, stage):
    path, *_ = archive
    calls = []
    _wire(archive, monkeypatch,
          upload=_recording_upload(calls, lambda key: True),
          publish=hub.publish_gex_history_index)
    monkeypatch.setattr(hub, '_list_gex_history_dates', lambda *a: [])
    monkeypatch.setattr(hub, 'gex_history_missed_sessions', lambda *a: [])
    monkeypatch.setattr(hub, '_heal_gex_history', lambda *a: [])
    def fail(*a, **kw):
        raise RuntimeError('private-error-sentinel')
    if stage == 'list':
        monkeypatch.setattr(hub, '_list_gex_history_dates', fail)
    elif stage == 'local_write':
        monkeypatch.setattr(hub, '_write_json', fail)
    else:
        monkeypatch.setattr(hub, '_upload_r2', _recording_upload(calls,
            lambda key: RuntimeError('private-error-sentinel') if key.endswith('dates.json') else True))
    result = repair._publish([('SPY', path)])
    entry = result['indices']['SPY']
    assert entry['index_attempted'] is (stage == 'upload')
    assert entry['index_uploaded'] is None
    assert entry['key'] == 'options_hub/gex_history/SPY/dates.json'
    assert result['incomplete'] and result['confirmed'] == 1
    assert 'private-error-sentinel' not in json.dumps(result)
    assert calls == [R2_KEY] + (['options_hub/gex_history/SPY/dates.json'] if stage == 'upload' else [])


def test_cli_emits_per_key_outcome_without_exception_text(archive, monkeypatch, capsys):
    calls = []
    _wire(archive, monkeypatch, upload=_recording_upload(calls,
          lambda key: RuntimeError('private-error-sentinel')), publish=_contract_publish([]))
    assert repair.main(MAIN_ARGS) == 1
    raw = capsys.readouterr().out
    result = json.loads(raw)
    assert result['attempt_unit'] == 'publisher_wrapper_call'
    assert result['acknowledgement_only'] is True
    assert result['publication']['keys'][R2_KEY]['attempts'] == 1
    assert result['publication']['indices']['SPY']['key'].endswith('/SPY/dates.json')
    assert 'private-error-sentinel' not in raw


def test_client_construction_exception_reports_no_upload_attempt(archive, monkeypatch):
    path, *_ = archive
    def fail():
        raise RuntimeError('private-error-sentinel')
    monkeypatch.setattr(hub, '_r2_client', fail)
    result = repair._publish([('SPY', path)])
    assert result['not_attempted'] == 1 and result['attempted'] == 0
    assert result['incomplete'] and 'private-error-sentinel' not in json.dumps(result)


@pytest.mark.parametrize('listed,uploaded,expected_status', [
    (None, True, 'list_failed'), ([], False, 'index_upload_unconfirmed'),
    ([], True, 'success'),
])
def test_optional_index_report_keeps_legacy_integer_and_native_calls(
        tmp_path, monkeypatch, listed, uploaded, expected_status):
    calls = []
    monkeypatch.setattr(hub, '_list_gex_history_dates', lambda *a: listed)
    monkeypatch.setattr(hub, 'gex_history_missed_sessions', lambda *a: [])
    monkeypatch.setattr(hub, '_heal_gex_history', lambda *a: [])
    monkeypatch.setattr(hub, '_upload_r2', lambda *a: calls.append(a[3]) or uploaded)
    args = ('SPY', '2026-10-16', None, None, tmp_path, object(), 'fake', 0)
    legacy = hub.publish_gex_history_index(*args)
    legacy_calls = list(calls); calls.clear()
    outcome = {'stale_field': True}
    detailed = hub.publish_gex_history_index(*args, outcome=outcome)
    assert type(legacy) is int and type(detailed) is int and legacy == detailed == 0
    assert calls == legacy_calls
    assert outcome['status'] == expected_status and 'stale_field' not in outcome


def test_no_change_cli_explicitly_reports_zero_publication_requests(archive, monkeypatch, capsys):
    _, _, _, old, _, _, _ = archive
    _wire(archive, monkeypatch, upload=_recording_upload([], lambda key: True),
          publish=_contract_publish([]))
    monkeypatch.setattr(repair, 'compute_gex', lambda *a, **kw: deepcopy(old))
    assert repair.main(MAIN_ARGS) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['publication']['requested'] == 0
    assert result['publication']['keys'] == result['publication']['indices'] == {}
