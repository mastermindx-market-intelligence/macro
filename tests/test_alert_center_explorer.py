"""V2 investigation projection: more visibility, never more signal authority."""
from copy import deepcopy
from datetime import date
from pathlib import Path


def project(signals, events=(), **kwargs):
    assert (Path(__file__).parents[1] / 'engine/alert_center_view.py').is_file()
    from engine.alert_center_view import build_explorer
    return build_explorer(signals, list(events), **kwargs)


def signal(id_, source='themes', type_='reco_change', asset='materials', **extra):
    return dict(alert_id=id_, source=source, type=type_, asset=asset,
                headline='Materials: rating changed', headline_zh='材料：评级变化',
                source_label='Theme Rotation', source_label_zh='主题轮动',
                priority=40, severity='minor', tier='watch', board_date='2026-09-08',
                ts='2026-09-08', link='sector_central.html#theme-materials', **extra)


def test_projection_keeps_every_signal_and_never_mutates_scores_or_ids():
    rows = [signal(str(i), asset=f'subject_{i}') for i in range(85)]
    before = deepcopy(rows)
    result = project(rows)
    assert result['signals'] == before
    assert result['total_signals'] == 85
    assert rows == before
    assert result['sources'][0]['count'] == 85


def test_specific_subject_can_bundle_distinct_changes_without_promotion():
    rows = [signal('a'), signal('b', type_='theme_deteriorating')]
    result = project(rows)
    assert len(result['situations']) == 1
    item = result['situations'][0]
    assert item['member_ids'] == ['a', 'b']
    assert item['primary_alert_id'] == 'a'
    assert item['subject'] == 'Materials'
    assert item['method'] == 'same_source_subject'
    assert 'priority' not in item and 'confidence' not in item
    assert result['signals'] == rows


def test_shared_generic_links_categories_and_macro_names_do_not_join():
    rows = [signal('a', source='altdata', type_='convergence', asset='NVDA'),
            signal('b', source='altdata', type_='convergence', asset='MSFT'),
            signal('c', source='macro', type_='credit', asset='macro'),
            signal('d', source='macro', type_='regime', asset='macro')]
    for row in rows:
        row['link'] = 'alt_data.html#convergence'
    assert project(rows)['situations'] == []


def test_repeated_same_type_and_cross_source_aliases_do_not_fake_a_situation():
    assert project([signal('a'), signal('b')])['situations'] == []
    assert project([signal('a'), signal('b', source='rotation', type_='weak')])['situations'] == []


def test_history_preserves_observed_clocks_and_never_interpolates_firings():
    row = signal('a')
    events = [dict(row, board_date=d, event_date=d, event_ts=None,
                   date_precision='date', recorded_at='2026-09-09T12:00:00Z')
              for d in ['2026-08-20', '2026-09-08']]
    result = project([row], events)
    assert result['history_total'] == 2
    assert len(result['history']) == 2
    assert [e['board_date'] for e in result['history']] == ['2026-09-08', '2026-08-20']
    assert all(e['event_ts'] is None for e in result['history'])
    assert all(e['alert_id'] == 'a' for e in result['history'])
    assert result['history'][0]['recorded_at'] == '2026-09-09T12:00:00Z'


def test_unknown_event_time_is_not_replaced_with_the_record_clock():
    row = signal('a')
    event = dict(row, board_date=None, event_date=None, event_ts=None,
                 date_precision='unknown', recorded_at='2026-09-09T12:00:00Z')
    h = project([row], [event])['history'][0]
    assert h['board_date'] is None and h['event_ts'] is None
    assert h['date_precision'] == 'unknown'


def test_history_cap_is_explicit_and_unmatched_events_are_not_invented():
    row = signal('a')
    result = project([row], [row, row, signal('other', asset='other')], history_limit=1)
    assert result['history_total'] == 2 and result['history_truncated'] == 1


def test_canonical_builder_adds_explorer_without_changing_the_ranked_cap(monkeypatch):
    from engine import alert_triage as at
    rows = [dict(source='macro', type=f'rule_{i}', asset='macro', ts='2026-09-08',
                 board_date='2026-09-08', tier='watch', raw_sev='medium',
                 headline=f'Observed change {i}', detail='', edge='') for i in range(4)]
    monkeypatch.setattr(at, '_macro_raw', lambda *args: at._read('macro', at.READ_OK, rows))
    monkeypatch.setattr(at, '_jsonl_raw', lambda source, *args: at._read(source, at.READ_OK_ZERO, []))
    monkeypatch.setattr(at, '_load_context', lambda: {'_state': at.READ_OK})
    monkeypatch.setattr(at, '_registry_index', lambda: {})
    monkeypatch.setattr(at, '_rule_scorecard', lambda: {})
    monkeypatch.setattr(at, 'ic_severity_cap', lambda source, type_, band: (band, {}))
    monkeypatch.setattr(at, '_events', lambda today: {'items': [], 'next': None})
    uncapped = at.build_triage(today=date(2026, 9, 9), max_items=10)
    capped = at.build_triage(today=date(2026, 9, 9), max_items=1)
    assert 'explorer' in capped, 'The production assembler must feed the investigation UI'
    assert len(capped['alerts']) == 1 and capped['summary']['total'] == 1
    assert capped['alerts'] == uncapped['alerts'][:1]
    assert capped['explorer']['signals'] == uncapped['alerts']
    assert capped['explorer']['history_total'] == 4
    assert capped['explorer']['situations'] == []


def test_account_specific_watchlist_evidence_is_not_expanded_into_global_view():
    public = signal('public')
    private = signal('private', source='watchlist', type_='buy_zone_enter', asset='PERSONAL')
    result = project([public, private], [public, private])
    assert [a['alert_id'] for a in result['signals']] == ['public']
    assert [a['alert_id'] for a in result['history']] == ['public']
    assert result['restricted_sources'] == ['watchlist']
    assert result['total_signals'] == 1


def test_nonfinite_optional_metrics_are_null_in_the_json_projection_only():
    import json
    row = signal('a', validation={'hit': float('nan'), 'n': 0, 'ic': float('inf')})
    result = project([row])
    assert result['signals'][0]['validation'] == {'hit': None, 'n': 0, 'ic': None}
    json.dumps(result, allow_nan=False)
    assert row['validation']['hit'] != row['validation']['hit']


def test_negative_history_limits_are_rejected():
    import pytest
    with pytest.raises(ValueError):
        project([], history_limit=-1)


def test_history_detail_is_the_original_event_not_the_latest_representative():
    current = signal('a', detail='Latest summary', detail_zh='最新摘要')
    old = dict(current, headline='Original event', detail='Original detail',
               detail_zh='原始详情', board_date='2026-08-20', event_date='2026-08-20')
    result = project([current], [old])
    assert result['history'][0]['detail'] == 'Original detail'
    assert result['history'][0]['detail_zh'] == '原始详情'
    assert current['detail'] == 'Latest summary'


def test_history_missing_detail_is_not_filled_from_the_latest_event():
    current = signal('a', detail='Latest detail must not leak backward')
    old = {k: v for k, v in current.items() if k != 'detail'}
    result = project([current], [old])
    assert result['history'][0]['detail'] == ''



def test_macro_transition_gets_source_bound_action_brief_without_mutation():
    row = signal('macro-transition', source='macro', type_='transition_state_change', asset='macro')
    row.update({
        'tier': 'act', 'severity': 'critical', 'priority': 76, 'age_days': 10,
        'detail': "The regime's footing went from a new regime to shifting (4 warning flags active)",
        'detail_zh': '周期状态由「新周期」转为「转换中」（4 个预警激活）',
        'edge': 'High — a regime shift re-prices everything downstream.',
        'edge_zh': '高 — 周期转变会重新定价其下游的一切。',
        'link': 'macro.html#regime-radar',
    })
    before = deepcopy(row)
    result = project([row])
    projected = result['signals'][0]
    brief = result['briefs'][row['alert_id']]
    assert row == before
    assert brief['schema'] == 'mastermind.alert_brief.v1'
    assert brief['status'] == 'supported'
    assert brief['family'] == 'macro.transition_state_change'
    assert brief['attention'] == 'review_first'
    assert brief['change'] == row['detail']
    assert brief['change_zh'] == row['detail_zh']
    assert brief['next_action_label'] == 'Recheck regime'
    assert brief['evidence_scope'] == 'current_panel_not_historical_archive'
    assert '10 days old' in brief['limitation']


def test_macro_risk_brief_keeps_source_risk_separate_from_attention_priority():
    row = signal('macro-risk', source='macro', type_='risk_state_elevated', asset='macro')
    row.update({
        'tier': 'act', 'severity': 'major', 'priority': 64, 'age_days': 8,
        'detail': 'Equity risk-state crossed into ELEVATED (63/100) — positioning/vol/breadth fragility building; de-gross, favor entries over chasing leaders',
        'detail_zh': '股票风险状态进入偏高区（63/100）— 仓位/波动/宽度脆弱性上升；降低敞口、择优入场而非追高',
        'edge': 'High — the equity-internal early-warning the credit gauge misses. De-risk response is sizing, not selection.',
        'edge_zh': '高 — 信用指标看不到的股票内部早期预警。应对是调仓位，而非选股。',
        'link': 'macro.html#dlg-risk',
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert '63/100' in brief['change']
    assert 'attention priority 64' in brief['limitation']
    assert 'return forecast' in brief['limitation']
    assert brief['next_action_label'] == 'Recheck risk'


def test_unrecognized_macro_shape_abstains_from_family_specific_copy():
    row = signal('macro-unknown', source='macro', type_='transition_state_change', asset='macro')
    row.update({'tier': 'act', 'detail': 'The regime changed in an unsupported shape',
                'detail_zh': '周期发生变化，但格式未知', 'link': 'macro.html#regime-radar'})
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'fallback'
    assert brief['family'] is None
    assert brief['change'] == row['detail']
    assert brief['next_action_label'] == 'Inspect evidence'
    assert brief['reassessment'] == ''


def test_attention_language_derives_from_canonical_tier_not_numeric_priority():
    act = signal('act'); act.update({'tier': 'act', 'priority': 1})
    watch = signal('watch'); watch.update({'tier': 'watch', 'priority': 99})
    context = signal('context'); context.update({'tier': 'context', 'priority': 100})
    result = project([act, watch, context])
    briefs = [result['briefs'][r['alert_id']] for r in (act, watch, context)]
    assert [b['attention'] for b in briefs] == ['review_first', 'watch_next', 'for_awareness']
