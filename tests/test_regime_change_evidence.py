"""Recorded changes through the incumbent world-state read tool, not new events."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

NOW = datetime(2026, 10, 3, 3, 0, tzinfo=timezone.utc)


def row(day='2026-10-02', field='us_rate_pressure', before='neutral', after='pressure'):
    return {'asof': day, 'domain': 'us', 'field': field, 'from': before, 'to': after}


def state(rows=None):
    return {'produced_at': '2026-10-02T23:00:00Z', 'regime': {'quad': 'Q2'},
            'macro_deltas': {'display_only': True, 'transitions': [row()] if rows is None else rows,
                             'n_transitions_14d': 20}}


def project(s):
    from engine.neuralweb.regime_change_evidence import qualify_world_state
    return qualify_world_state(s, now=NOW)


def test_scope_is_recorded_changes_not_complete_timeline_or_onset():
    source = state(); original = copy.deepcopy(source)
    out = project(source); d = out['macro_deltas']
    assert d['transitions'][0]['to'] == 'pressure'
    assert d['n_transitions_14d'] == 1 and d['owner_reported_count'] == 20
    assert d['count_semantics'] == 'retained_records_not_total_market_changes'
    assert d['coverage_complete'] is False and d['event_time_verified'] is False
    assert d['historical_replay_eligible'] is False
    assert out['regime'] == source['regime'] and source == original


@pytest.mark.parametrize('bad', ['2099-01-01', '2026-10-04'])
def test_future_record_does_not_enter_current_change_context(bad):
    d = project(state([row(), row(bad)]))['macro_deltas']
    assert d['n_transitions_14d'] == 1
    assert d['excluded']['future_dated'] == 1
    assert bad not in json.dumps(d['transitions'])


def test_record_after_source_snapshot_is_not_current_evidence():
    d = project(state([row('2026-10-03')]))['macro_deltas']
    assert d['transitions'] == []
    assert d['excluded']['after_source_snapshot'] == 1


@pytest.mark.parametrize('bad', [None, '', 'not-a-date', '2026-13-01', []])
def test_bad_record_dates_are_quarantined(bad):
    d = project(state([row(bad)]))['macro_deltas']
    assert d['transitions'] == [] and d['excluded']['invalid_record'] == 1


def test_old_and_duplicate_records_are_not_extra_current_changes():
    d = project(state([row('2020-01-01'), row(), row()]))['macro_deltas']
    assert len(d['transitions']) == 1
    assert d['excluded']['outside_window'] == 1 and d['excluded']['duplicate_record'] == 1


def test_selection_uses_dates_not_file_order_and_is_bounded():
    rows = [row('2026-09-22', field='field_' + str(i)) for i in range(30)]
    rows += [row('2026-10-02', field='newest')]
    a = project(state(rows))['macro_deltas']
    b = project(state(list(reversed(rows))))['macro_deltas']
    assert a == b and len(a['transitions']) == 20
    assert a['transitions'][0]['field'] == 'newest' and a['omitted_records'] == 11


def test_two_same_day_states_are_not_misrepresented_as_known_sequence():
    d = project(state([row(before='neutral', after='pressure'),
                       row(before='pressure', after='panic')]))['macro_deltas']
    assert len(d['transitions']) == 2
    assert all(r['within_day_order_verified'] is False for r in d['transitions'])
    assert all(r['same_day_field_ambiguous'] is True for r in d['transitions'])


@pytest.mark.parametrize('stamp,status', [(None, 'unknown_date'), ('2099-01-01', 'future_dated')])
def test_unknown_or_future_source_cannot_certify_changes(stamp, status):
    s = state();s['produced_at'] = stamp
    d = project(s)['macro_deltas']
    assert d['reading_status'] == status and d['transitions'] is None


def test_stale_wrapper_is_explicit_even_if_record_looks_recent():
    s = state([row('2026-09-22')]);s['produced_at'] = '2026-09-23T00:00:00Z'
    d = project(s)['macro_deltas']
    assert d['reading_status'] == 'stale'
    assert d['source_snapshot']['as_of'] == '2026-09-23T00:00:00+00:00'


def test_missing_is_not_empty_and_an_empty_projection_is_not_no_change():
    s = state();s['macro_deltas']['transitions'] = None
    d = project(s)['macro_deltas']
    assert d['transitions'] is None and d['n_transitions_14d'] is None
    d = project(state([]))['macro_deltas']
    assert d['transitions'] == [] and d['n_transitions_14d'] == 0
    assert d['coverage_complete'] is False


def test_other_world_state_blocks_are_not_recomputed_or_relabelled():
    s = state();s['portfolio'] = {'current_gross': .4};s['other'] = [1, 2]
    out = project(s)
    assert {k: v for k, v in out.items() if k != 'macro_deltas'} == {k: v for k, v in s.items() if k != 'macro_deltas'}
    legacy = {'regime': {'quad': 'Q3'}}
    assert project(legacy) == legacy


@pytest.mark.parametrize('via_ask', [False, True])
def test_actual_world_state_read_path_retains_qualified_changes(tmp_path, via_ask):
    source = state([row(), row('2099-01-01')]);p = tmp_path / 'data/neuralweb/world_state.json'
    p.parent.mkdir(parents=True);p.write_text(json.dumps(source));before = p.read_bytes()
    if via_ask:
        from engine.neuralweb.ask_brain import _dispatch_read_tool
        out = _dispatch_read_tool('read_world_state', {}, tmp_path)
    else:
        from engine.neuralweb.cortex import _tool_read_world_state
        out = _tool_read_world_state(tmp_path, {})
    assert out['regime'] == source['regime']
    assert out['macro_deltas']['event_time_verified'] is False
    assert out['macro_deltas']['excluded']['future_dated'] == 1
    assert before == p.read_bytes()


def test_same_value_is_not_a_new_change_and_policy_labels_are_not_orders():
    d = project(state([row(before='neutral', after='neutral'), row(field='fx_dxy_action', after='LONG')]))['macro_deltas']
    assert d['excluded']['unchanged_record'] == 1
    assert d['transitions'][0]['recorded_policy_label_not_instruction'] is True


def test_unreadable_world_state_reports_no_raw_filesystem_path(tmp_path):
    from engine.neuralweb.cortex import _tool_read_world_state
    out = _tool_read_world_state(tmp_path, {})
    assert 'error' in out and str(tmp_path) not in json.dumps(out)


def test_world_state_age_limit_matches_existing_registry_not_another_domain():
    import yaml
    from engine.neuralweb.regime_change_evidence import WORLD_STATE_SLA_HOURS
    registry = yaml.safe_load((Path(__file__).parents[1] / 'config/synapse.yml').read_text())
    assert registry['artifacts']['world-state']['freshness_sla_hours'] == WORLD_STATE_SLA_HOURS


def test_excessive_source_projection_does_not_select_a_misleading_prefix():
    from engine.neuralweb.regime_change_evidence import MAX_INPUT_RECORDS
    d = project(state([row()] * (MAX_INPUT_RECORDS + 1)))['macro_deltas']
    assert d['reading_status'] == 'unavailable' and d['transitions'] is None
    assert d['reason'] == 'projection_exceeds_record_limit'


@pytest.mark.parametrize('streaming', [False, True])
def test_actual_chat_tool_result_keeps_change_count_and_time_limits(tmp_path, monkeypatch, streaming):
    from types import SimpleNamespace
    from engine.neuralweb import brain_gateway as gw
    source = state([row(), row('2099-01-01')])
    p = tmp_path / 'data/neuralweb/world_state.json'
    p.parent.mkdir(parents=True);p.write_text(json.dumps(source))
    monkeypatch.setenv('MACRO_LIVE_DIR', str(tmp_path / 'site/live'))
    monkeypatch.setattr(gw, '_resolve_tier', lambda *a, **k: {'tier': 'essential', 'status': 'active', 'features': ['site_full']})

    class Client:
        def __init__(self):
            self.messages = self;self.calls = []
        def create(self, **kwargs):
            self.calls.append(copy.deepcopy(kwargs))
            if len(self.calls) == 1:
                return SimpleNamespace(content=[SimpleNamespace(type='tool_use', id='world_read', name='read_world_state', input={})],
                                       stop_reason='tool_use', usage=SimpleNamespace(input_tokens=10, output_tokens=10))
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='Fixture answer.')],
                                   stop_reason='end_turn', usage=SimpleNamespace(input_tokens=10, output_tokens=10))

    client = Client()
    args = ('What changed in the macro regime?', 'fast', [], {}, tmp_path, tmp_path,
            'http://127.0.0.1:3100', client, 'deepseek-chat', 500, 3)
    if streaming:
        events = list(gw._run_brain_loop_stream(*args, meta_event={'type': 'meta'}, user_id='fixture-user'))
        assert any(json.loads(e[6:]).get('type') == 'done' for e in events if e.startswith('data: '))
    else:
        assert gw._run_brain_loop(*args, user_id='fixture-user')[0]
    results = [b for m in client.calls[1]['messages'] if isinstance(m.get('content'), list)
               for b in m['content'] if isinstance(b, dict) and b.get('type') == 'tool_result']
    assert results
    out = json.loads(results[0]['content']);d = out['macro_deltas']
    assert out['regime'] == source['regime']
    assert d['n_transitions_14d'] == 1 and d['owner_reported_count'] == 20
    assert d['event_time_verified'] is False and d['coverage_complete'] is False
    assert d['excluded']['future_dated'] == 1
    assert '2099-01-01' not in json.dumps(d['transitions'])
