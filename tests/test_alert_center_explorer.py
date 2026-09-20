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
    assert brief['attention'] == 'earlier_priority'
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
    assert brief['attention'] == 'earlier_priority'
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


def test_attention_language_uses_canonical_tier_and_freshness_not_numeric_priority():
    fresh_act = signal('fresh-act'); fresh_act.update({'tier': 'act', 'priority': 1, 'age_days': 2})
    old_act = signal('old-act'); old_act.update({'tier': 'act', 'priority': 100, 'age_days': 3})
    fresh_watch = signal('fresh-watch'); fresh_watch.update({'tier': 'watch', 'priority': 99, 'age_days': 0})
    old_watch = signal('old-watch'); old_watch.update({'tier': 'watch', 'priority': 100, 'age_days': 9})
    context = signal('context'); context.update({'tier': 'context', 'priority': 100, 'age_days': 0})
    rows = (fresh_act, old_act, fresh_watch, old_watch, context)
    result = project(list(rows))
    briefs = [result['briefs'][r['alert_id']] for r in rows]
    assert [b['attention'] for b in briefs] == [
        'review_first', 'earlier_priority', 'watch_next', 'for_awareness', 'for_awareness']


def test_unknown_recency_never_impersonates_a_current_review_first_alert():
    row = signal('unknown-age')
    row.update({'tier': 'act', 'priority': 100, 'age_days': None, 'board_date': None})
    assert project([row])['briefs'][row['alert_id']]['attention'] == 'earlier_priority'



def test_fresh_watch_families_get_source_bound_decision_briefs_without_new_authority():
    rows = []
    commodity = signal('commodity-watch', source='commodity', type_='price_shock', asset='oil')
    commodity.update({
        'tier': 'watch', 'age_days': 1, 'priority': 48,
        'detail': 'Oil 95.47 $/bbl — the acute move is settling.',
        'detail_zh': '原油 95.47 美元/桶 — 剧烈波动正在平息。',
        'link': 'commodities.html#timeline', 'fire_count': 2,
        'validation': {'verdict': 'documented', 'note': 'Not separately backtested as a timing signal.'},
    })
    allocation = signal('allocation-watch', source='vector', type_='allocation_change', asset='vector')
    allocation.update({
        'tier': 'watch', 'age_days': 1, 'priority': 48,
        'detail': 'Optimal strategy moved 41% → 43% BTC (momentum × risk grid).',
        'detail_zh': '最优策略从 41% 调整为 43% BTC（动量 × 风险网格）。',
        'edge': 'Strategy output — beat buy-and-hold in backtest.',
        'link': 'vector.html#allocation', 'fire_count': 7,
        'validation': {'verdict': 'calibrated', 'note': 'Strategy output — beat buy-and-hold in backtest.'},
    })
    convergence = signal('convergence-watch', source='altdata', type_='convergence', asset='EXE')
    convergence.update({
        'tier': 'watch', 'age_days': 1, 'priority': 48,
        'detail': 'EXE lit up by 2 independent alt-data channels: Material 8-K cluster, Special situation.',
        'detail_zh': 'EXE 被 2 个独立替代数据渠道同时触发：重大8-K集群、特殊事件。',
        'link': 'alt_data.html#convergence', 'fire_count': 2,
        'validation': {'verdict': 'documented', 'note': 'Not separately backtested as a timing signal.'},
    })
    rotation = signal('rotation-watch', source='rotation', type_='rotation_emerging', asset='consumerfarmdirect')
    rotation.update({
        'tier': 'watch', 'age_days': 1, 'priority': 48,
        'detail': 'Farm-Direct just turned improving & accelerating (1W +1.7%, 1M -4.3%, 3M -3.8%; accel +2.0). An early rotate-in candidate — context, not a buy list.',
        'detail_zh': 'Farm-Direct 刚转为改善且加速（1周 +1.7%，1月 -4.3%，3月 -3.8%；加速 +2.0）。早期轮入候选 — 仅作参考，非买入清单。',
        'link': 'subsector_rotation.html#rotation-app', 'fire_count': 2,
        'validation': {'verdict': 'documented', 'note': 'Not separately backtested as a timing signal.'},
    })
    rows.extend((commodity, allocation, convergence, rotation))
    before = deepcopy(rows)
    result = project(rows)
    assert rows == before
    briefs = [result['briefs'][row['alert_id']] for row in rows]
    assert [brief['family'] for brief in briefs] == [
        'commodity.price_shock', 'vector.allocation_change',
        'altdata.convergence', 'rotation.rotation_emerging']
    assert all(brief['status'] == 'supported' for brief in briefs)
    assert all(brief['attention'] == 'watch_next' for brief in briefs)
    assert [brief['next_action_label'] for brief in briefs] == [
        'Recheck oil', 'Open allocation', 'Inspect channels', 'Check rotation']
    assert 'does not establish direction' in briefs[0]['limitation']
    assert 'historical backtest' in briefs[1]['limitation']
    assert 'channel count is not a probability' in briefs[2]['limitation']
    assert 'not a buy list' in briefs[3]['limitation']
    assert all(brief['evidence_scope'] == 'current_panel_not_historical_archive' for brief in briefs)


def test_aged_vector_impulse_brief_exposes_decay_and_blind_spot_without_fresh_urgency():
    row = signal('vector-impulse', source='vector', type_='impulse_warn_down', asset='vector')
    row.update({
        'tier': 'act', 'severity': 'critical', 'priority': 76, 'age_days': 16,
        'detail': 'DVOL intraday-range spike (unusually large versus its own history) — the options market is repricing risk. BTC $81,264.',
        'detail_zh': 'DVOL 日内波幅激增（相对自身历史异常偏大）— 期权市场正在重新定价风险。BTC 81,264 美元。',
        'edge': 'Forward de-risk window from a verified LEADING precursor cross (impulse radar). Holdout-validated, leak-free; act early — the edge decays in ~2-4 days. BLIND to slow/options-calm flushes.',
        'edge_zh': '来自经验证的领先前兆突破的前瞻减仓窗口（脉冲雷达）。已通过留出样本、无前视；优势在约 2-4 天内衰减。对缓慢/期权平静式下跌无效。',
        'link': 'vector.html#impulse',
        'validation': {'verdict': 'calibrated', 'note': 'Holdout-validated leading precursor.'},
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert brief['family'] == 'vector.impulse_warn_down'
    assert brief['attention'] == 'earlier_priority'
    assert brief['next_action_label'] == 'Recheck impulse'
    assert '2–4 day edge window has elapsed' in brief['limitation']
    assert 'slow or options-calm selloffs' in brief['limitation']
    assert 'current impulse panel' in brief['next_action']



def test_vector_impulse_window_copy_is_age_aware():
    def row(alert_id, age):
        value = signal(alert_id, source='vector', type_='impulse_warn_down', asset='vector')
        value.update({
            'tier': 'act', 'age_days': age,
            'detail': 'DVOL intraday-range spike (unusually large versus its own history) — the options market is repricing risk. BTC $81,264.',
            'edge': 'Forward de-risk window; the edge decays in ~2-4 days.',
            'link': 'vector.html#impulse',
        })
        return value
    fresh, unknown = row('fresh-impulse', 1), row('unknown-impulse', None)
    result = project([fresh, unknown])['briefs']
    fresh_brief, unknown_brief = result[fresh['alert_id']], result[unknown['alert_id']]
    assert fresh_brief['attention'] == 'review_first'
    assert 'bounded to that short horizon' in fresh_brief['limitation']
    assert 'has elapsed' not in fresh_brief['limitation']
    assert unknown_brief['attention'] == 'earlier_priority'
    assert 'event age is unavailable' in unknown_brief['limitation']
    assert 'has elapsed' not in unknown_brief['limitation']


def test_aged_impulse_takeaway_never_repeats_expired_act_early_copy():
    row = signal('aged-impulse-copy', source='vector', type_='impulse_warn_down', asset='vector')
    row.update({
        'tier': 'act', 'age_days': 17,
        'detail': 'DVOL intraday-range spike (unusually large versus its own history) — the options market is repricing risk. BTC $81,264.',
        'detail_zh': 'DVOL 日内波幅激增（相对自身历史异常偏大）— 期权市场正在重新定价风险。BTC 81,264 美元。',
        'edge': 'Forward de-risk window from a verified LEADING precursor cross; act early — the edge decays in ~2-4 days.',
        'edge_zh': '来自经验证领先前兆突破的前瞻减仓窗口；应尽早行动 — 优势在约 2-4 天内衰减。',
        'link': 'vector.html#impulse',
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['attention'] == 'earlier_priority'
    assert 'originally reported' in brief['implication']
    assert 'act early' not in brief['implication'].lower()
    assert '历史' in brief['implication_zh']


def test_rotation_brief_describes_actual_horizons_without_inventing_negative_returns():
    row = signal('rotation-positive', source='rotation', type_='rotation_emerging', asset='security')
    row.update({
        'tier': 'watch', 'age_days': 1,
        'detail': 'Security just turned leading & accelerating (1W +6.9%, 1M +4.4%, 3M +26.7%; accel +4.8). An early rotate-in candidate — context, not a buy list.',
        'detail_zh': 'Security 刚转为领先且加速（1周 +6.9%，1月 +4.4%，3月 +26.7%；加速 +4.8）。早期轮入候选 — 仅作参考，非买入清单。',
        'link': 'subsector_rotation.html#rotation-app',
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert '1W +6.9%, 1M +4.4%, 3M +26.7%' in brief['implication']
    assert 'negative one- and three-month returns' not in brief['limitation']
    assert 'descriptive' in brief['limitation']


def test_allocation_brief_preserves_source_localized_implication():
    row = signal('allocation-localized', source='vector', type_='allocation_change', asset='vector')
    row.update({
        'tier': 'watch', 'age_days': 1,
        'detail': 'Optimal strategy moved 41% → 43% BTC (momentum × risk grid).',
        'detail_zh': '最优策略从 41% 调整为 43% BTC（动量 × 风险网格）。',
        'edge': 'Strategy output — beat buy-and-hold in backtest.',
        'edge_zh': '来源本地化：策略输出在历史回测中跑赢买入并持有。',
        'link': 'vector.html#allocation',
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['implication_zh'] == row['edge_zh']


def test_instrument_risk_regime_brief_separates_threshold_state_from_market_forecast():
    commodity = signal('commodity-risk', source='commodity', type_='risk_regime', asset='copper')
    commodity.update({
        'tier': 'watch', 'severity': 'major', 'age_days': 10,
        'headline': 'Copper risk turned Elevated', 'headline_zh': '铜风险转为升高',
        'detail': 'Risk Index rose through the threshold to 34. Copper 6.47 $/lb.',
        'detail_zh': '风险指数上穿阈值至 34。铜 6.47 美元/磅。',
        'link': 'commodities.html#timeline',
        'validation': {'verdict': 'confirmer', 'horizon': '21d', 'n': None},
    })
    forex = signal('forex-risk', source='forex', type_='risk_regime', asset='USDCAD')
    forex.update({
        'tier': 'watch', 'age_days': 1,
        'headline': 'USD/CAD risk turned Calm', 'headline_zh': 'USD/CAD 风险转为平静',
        'detail': 'Risk Index fell back below its threshold to 11. USD/CAD 1.3988.',
        'detail_zh': '风险指数回落跌破阈值至 11。USD/CAD 1.3988。',
        'link': 'forex.html#timeline',
        'validation': {'verdict': 'documented',
                       'note': 'Conviction is documented, not separately backtested as a timing signal.'},
    })
    rows = [commodity, forex]
    before = deepcopy(rows)
    result = project(rows)['briefs']
    assert rows == before
    copper, fx = result[commodity['alert_id']], result[forex['alert_id']]
    assert [copper['family'], fx['family']] == [
        'commodity.risk_regime', 'forex.risk_regime']
    assert [copper['attention'], fx['attention']] == ['for_awareness', 'watch_next']
    assert '34' in copper['implication'] and 'instrument-specific' in copper['limitation']
    assert 'confirmer' in copper['limitation'] and '10 days old' in copper['limitation']
    assert '11' in fx['implication'] and 'not an all-clear' in fx['implication']
    assert 'not separately backtested' in fx['limitation']
    assert [copper['next_action_label'], fx['next_action_label']] == [
        'Recheck commodity risk', 'Recheck FX risk']
    assert [copper['next_action_label_zh'], fx['next_action_label_zh']] == [
        '复核商品风险', '复核外汇风险']
    assert '商品时间线' in copper['next_action_zh']
    assert '外汇时间线' in fx['next_action_zh']
    assert all(result[row['alert_id']]['evidence_scope'] == 'current_panel_not_historical_archive'
               for row in rows)


def test_macro_gex_brief_is_a_volatility_backdrop_not_a_directional_call():
    row = signal('gex-flip', source='macro', type_='gex_flip_cross', asset='macro')
    row.update({
        'tier': 'watch', 'age_days': 3,
        'detail': 'GEX: net GEX changed sign (net +5bn, spot vs flip +0.2%)',
        'detail_zh': 'GEX：净 GEX 转变方向（净 +5bn，现价相对翻转点 +0.2%）',
        'edge': 'Medium — changes the volatility backdrop, not the direction.',
        'edge_zh': '中 — 改变的是波动背景，而非方向。',
        'link': 'macro_context.html#board', 'fire_count': 7,
        'validation': {'verdict': 'confirmer', 'horizon': 'intraday/days',
                       'extra': [('history', 'accruing (n small)')]},
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert brief['family'] == 'macro.gex_flip_cross'
    assert brief['attention'] == 'for_awareness'
    assert brief['implication'] == row['edge']
    assert 'not a directional call' in brief['limitation']
    assert 'history is still accruing' in brief['limitation']
    assert '3 days old' in brief['limitation']
    assert brief['next_action_label'] == 'Recheck gamma'
    assert 'net GEX' in brief['next_action'] and 'spot-versus-flip' in brief['next_action']


def test_macro_fragility_and_breadth_briefs_expose_non_timer_limits():
    fragility = signal('fragility', source='macro', type_='hidden_fragility', asset='macro')
    fragility.update({
        'tier': 'watch', 'age_days': 3,
        'detail': 'Complacency watch: calm tape starting to mask weakening internals',
        'detail_zh': '自满预警：平静走势开始掩盖走弱的内部结构',
        'edge': "Medium — a calm-over-weak CONTEXT (the conjunction matters, not low VIX alone). Size down, don't chase.",
        'edge_zh': '中 — 平静掩盖走弱的背景（关键是组合而非单看低VIX）。缩小仓位，不要追高。',
        'link': 'macro.html#dlg-risk',
        'validation': {'verdict': 'documented'},
    })
    breadth = signal('breadth', source='macro', type_='breadth_divergence', asset='macro')
    breadth.update({
        'tier': 'watch', 'age_days': 3,
        'detail': 'Breadth divergence: index near its 1y high while %>200dma is weak (16% pctile) — fewer names carrying the tape',
        'detail_zh': '宽度背离：指数接近一年高点但 %>200日均线偏弱（16% 分位）— 抬指数的个股在减少',
        'edge': 'Medium — fewer names carrying the index; a thinning-tape caution, not a timer.',
        'edge_zh': '中 — 抬指数的个股在减少；属于宽度变薄的警示，而非择时。',
        'link': 'macro.html#dlg-risk',
        'validation': {'verdict': 'documented'},
    })
    result = project([fragility, breadth])['briefs']
    f, b = result[fragility['alert_id']], result[breadth['alert_id']]
    assert [f['family'], b['family']] == [
        'macro.hidden_fragility', 'macro.breadth_divergence']
    assert f['implication'] == fragility['edge'] and b['implication'] == breadth['edge']
    assert 'conjunction' in f['limitation'] and 'not separately backtested' in f['limitation']
    assert 'not a market-top probability or timer' in b['limitation']
    assert '16% percentile' in b['limitation']
    assert [f['next_action_label'], b['next_action_label']] == [
        'Recheck fragility', 'Recheck breadth']


def test_new_risk_family_copy_abstains_when_the_source_shape_is_unrecognized():
    rows = [
        signal('bad-risk', source='commodity', type_='risk_regime', asset='oil'),
        signal('bad-gex', source='macro', type_='gex_flip_cross', asset='macro'),
        signal('bad-breadth', source='macro', type_='breadth_divergence', asset='macro'),
    ]
    rows[0]['detail'] = 'Risk changed, but the source shape is unknown.'
    rows[1]['detail'] = 'Dealer gamma changed in an unsupported form.'
    rows[2]['detail'] = 'Breadth weakened in an unsupported form.'
    briefs = project(rows)['briefs']
    assert all(briefs[row['alert_id']]['status'] == 'fallback' for row in rows)
    assert all(briefs[row['alert_id']]['family'] is None for row in rows)


def test_theme_change_families_get_source_bound_decision_briefs_without_trade_authority():
    reco = signal('theme-reco', source='themes', type_='reco_change', asset='ai_infra')
    reco.update({
        'tier': 'watch', 'age_days': 3,
        'headline': '↑ AI Infrastructure: Avoid → Hold',
        'headline_zh': '↑ AI 基础设施：规避 → 持有',
        'detail': 'Theme recommendation for AI Infrastructure changed from Avoid to Hold (score 57, neutral).',
        'detail_zh': 'AI 基础设施 的主题建议由「规避」变为「持有」（评分 57，中性）。',
        'link': 'sector_central.html#theme-ai_infra', 'fire_count': 4,
        'validation': {'verdict': 'documented',
                       'note': 'Conviction is documented, not separately backtested as a timing signal.'},
    })
    deteriorating = signal('theme-down', source='themes', type_='theme_deteriorating', asset='managed_care')
    deteriorating.update({
        'tier': 'watch', 'age_days': 3,
        'headline': '🔻 Managed Care & Insurers is deteriorating',
        'headline_zh': '🔻 管理式医疗与保险 走弱',
        'detail': 'Managed Care & Insurers broke down into deteriorating — momentum and breadth weakening together. Recommendation now Avoid.',
        'detail_zh': '管理式医疗与保险 转入「走弱」 — 动量与广度同步转弱，当前建议「规避」。',
        'link': 'sector_central.html#theme-managed_care', 'fire_count': 4,
        'validation': {'verdict': 'documented'},
    })
    topping = signal('theme-top', source='themes', type_='theme_topping', asset='us_sector_energy')
    topping.update({
        'tier': 'watch', 'age_days': 4,
        'headline': '⚠️ Energy (Equal-Weight): strength fading off the high',
        'headline_zh': '⚠️ 能源（等权）：高位动能减弱',
        'detail': 'Energy (Equal-Weight) dropped from dominant to fading as of the 2026-09-16 close — momentum cooling at a high. Historically this read flags elevated pullback risk over the next month, not a confirmed top — leaders inside the theme can keep running. Recommendation now Trim.',
        'detail_zh': '能源（等权） 自「主导」转入「退潮」（截至 2026-09-16 收盘）— 高位动能降温。历史上该读数指向未来约一个月的回撤风险上升，并非确认见顶 — 主题内的领涨股仍可能续涨。当前建议「减仓」。',
        'link': 'sector_central.html#theme-us_sector_energy', 'fire_count': 2,
        'validation': {'verdict': 'documented'},
    })
    emerging = signal('theme-emerge', source='themes', type_='theme_emerging', asset='us_sector_utilities')
    emerging.update({
        'tier': 'watch', 'age_days': 1,
        'headline': '🌱 Utilities (Equal-Weight) is emerging',
        'headline_zh': '🌱 公用事业（等权） 进入新兴阶段',
        'detail': 'Utilities (Equal-Weight) entered the EMERGING lifecycle — accelerating relative strength before it is extended (score 38) — held 2 consecutive sessions (constructive label shifts are debounced; risk label shifts fire immediately).',
        'detail_zh': '公用事业（等权） 进入「新兴」阶段 — 相对强度加速且尚未过度延展（评分 38），已连续 2 个交易日确认（进取方向去抖，风险方向即时）。',
        'link': 'sector_central.html#theme-us_sector_utilities',
        'validation': {'verdict': 'documented'},
    })
    leadership = signal('theme-lead', source='themes', type_='leadership_rotation', asset='crypto')
    leadership.update({
        'tier': 'watch', 'age_days': 23,
        'headline': '🔄 New theme leader: Crypto & Digital Assets',
        'headline_zh': '🔄 新主题领涨：加密与数字资产',
        'detail': 'Crypto & Digital Assets took the #1 theme rank (score 71), displacing Gold Miners — held #1 for 2 consecutive sessions with a 3-point margin over #2.',
        'detail_zh': '加密与数字资产 升至主题排名第一（评分 71），取代 黄金矿业 — 已连续 2 个交易日保持第一，领先第二名 3 分。',
        'link': 'sector_central.html#theme-crypto',
        'validation': {'verdict': 'documented'},
    })
    rows = [reco, deteriorating, topping, emerging, leadership]
    before = deepcopy(rows)
    briefs = project(rows)['briefs']
    assert rows == before
    values = [briefs[row['alert_id']] for row in rows]
    assert [brief['family'] for brief in values] == [
        'themes.reco_change', 'themes.theme_deteriorating', 'themes.theme_topping',
        'themes.theme_emerging', 'themes.leadership_rotation']
    assert all(brief['status'] == 'supported' for brief in values)
    assert [brief['attention'] for brief in values] == [
        'for_awareness', 'for_awareness', 'for_awareness', 'watch_next', 'for_awareness']
    assert [brief['next_action_label'] for brief in values] == [
        'Recheck recommendation', 'Recheck deterioration', 'Recheck pullback risk',
        'Recheck emergence', 'Recheck leadership']
    assert 'not a trade instruction' in values[0]['limitation']
    assert 'momentum and breadth' in values[1]['next_action']
    assert 'not a confirmed top' in values[2]['limitation']
    assert 'held 2 consecutive sessions' in values[3]['implication']
    assert 'not expected return' in values[4]['limitation']
    assert all(brief['evidence_scope'] == 'current_panel_not_historical_archive'
               for brief in values)


def test_theme_briefs_preserve_asymmetric_confirmation_and_score_boundaries():
    constructive = signal('theme-constructive', source='themes', type_='reco_change', asset='security')
    constructive.update({
        'tier': 'watch', 'age_days': 1,
        'detail': 'Theme recommendation for Security changed from Hold to Accumulate (score 64, emerging) — held 2 consecutive sessions (constructive flips wait for a second session; risk flips fire immediately).',
        'detail_zh': 'Security 的主题建议由「持有」变为「加仓」（评分 64，新兴），已连续 2 个交易日确认（进取方向需连续确认，风险方向即时）。',
        'link': 'sector_central.html#theme-security',
        'validation': {'verdict': 'documented'},
    })
    downgrade = signal('theme-risk', source='themes', type_='reco_change', asset='retail')
    downgrade.update({
        'tier': 'watch', 'age_days': 1,
        'detail': 'Theme recommendation for Retail changed from Accumulate to Avoid (score 31, deteriorating).',
        'detail_zh': 'Retail 的主题建议由「加仓」变为「规避」（评分 31，走弱）。',
        'link': 'sector_central.html#theme-retail',
        'validation': {'verdict': 'documented'},
    })
    c, d = [project([row])['briefs'][row['alert_id']] for row in (constructive, downgrade)]
    assert 'confirmed for 2 sessions' in c['implication']
    assert 'constructive changes are delayed for confirmation' in c['limitation']
    assert 'risk-direction changes fire immediately' in d['limitation']
    assert '64 is a model score, not a probability' in c['limitation']
    assert '31 is a model score, not a probability' in d['limitation']


def test_theme_family_specific_copy_abstains_on_unsupported_shapes():
    types = ('reco_change', 'theme_deteriorating', 'theme_topping',
             'theme_emerging', 'leadership_rotation')
    rows = []
    for type_ in types:
        row = signal(f'bad-{type_}', source='themes', type_=type_, asset='theme')
        row.update({'detail': f'{type_} changed in an unsupported shape.',
                    'link': 'sector_central.html#theme-theme'})
        rows.append(row)
    briefs = project(rows)['briefs']
    assert all(briefs[row['alert_id']]['status'] == 'fallback' for row in rows)
    assert all(briefs[row['alert_id']]['family'] is None for row in rows)


def test_rotation_rollover_and_confirmed_turns_get_breadth_aware_briefs():
    fading = signal('rotation-fading', source='rotation', type_='rotation_fading', asset='smartwatches')
    fading.update({
        'tier': 'context', 'age_days': 2,
        'detail': 'Smartwatches was leading but momentum has rolled over to weakening (1W +0.1%, 3M +7.8%; mom -0.0). A rotate-out / take-profit watch — context only.',
        'detail_zh': 'Smartwatches 此前领先，但动量已转弱（1周 +0.1%，3月 +7.8%；动量 -0.0）。轮出/止盈观察 — 仅作参考。',
        'link': 'subsector_rotation.html#rotation-app',
        'validation': {'verdict': 'documented'},
    })
    turn_down = signal('rotation-down', source='rotation', type_='rotation_turn_down', asset='materials')
    turn_down.update({
        'tier': 'context', 'age_days': 2,
        'detail': "Materials ran 39.6% off its 1-year low and has now rolled over on confirmed sessions — this week -2.4% vs the market's -0.7%/wk, 62% of members rolling with it. Context, not a sell list.",
        'detail_zh': 'Materials 自一年低点上涨 39.6%，现已连续多个交易日确认转为下行——本周 -2.4%，市场为 -0.7%/周，62% 成分股同步走弱。仅作参考，非卖出清单。',
        'link': 'subsector_rotation.html#rotation-app',
        'validation': {'verdict': 'documented'},
    })
    turn_up = signal('rotation-up', source='rotation', type_='rotation_turn_up', asset='batteries')
    turn_up.update({
        'tier': 'context', 'age_days': 11,
        'detail': "Batteries fell 24.7% from its 1-year high and has now turned up on confirmed sessions — this week +8.3% vs the market's -0.3%/wk, 73% of members turning with it. Context, not a buy list.",
        'detail_zh': 'Batteries 自一年高点回落 24.7%，现已连续多个交易日确认转为上行——本周 +8.3%，市场为 -0.3%/周，73% 成分股同步转向。仅作参考，非买入清单。',
        'link': 'subsector_rotation.html#rotation-app',
        'validation': {'verdict': 'documented'},
    })
    rows = [fading, turn_down, turn_up]
    before = deepcopy(rows)
    briefs = project(rows)['briefs']
    assert rows == before
    values = [briefs[row['alert_id']] for row in rows]
    assert [brief['family'] for brief in values] == [
        'rotation.rotation_fading', 'rotation.rotation_turn_down', 'rotation.rotation_turn_up']
    assert all(brief['status'] == 'supported' for brief in values)
    assert all(brief['attention'] == 'for_awareness' for brief in values)
    assert [brief['next_action_label'] for brief in values] == [
        'Recheck rollover', 'Recheck turn down', 'Recheck turn up']
    assert 'not a take-profit instruction' in values[0]['limitation']
    assert '62% of members' in values[1]['implication']
    assert 'not a sell list' in values[1]['limitation']
    assert '73% of members' in values[2]['implication']
    assert 'not a buy list' in values[2]['limitation']
    assert '11 days old' in values[2]['limitation']
    assert all(brief['evidence_scope'] == 'current_panel_not_historical_archive'
               for brief in values)


def test_rotation_turn_brief_discloses_concentration_and_leadership_basis():
    down = signal('rotation-down-concentrated', source='rotation', type_='rotation_turn_down', asset='software')
    down.update({
        'tier': 'context', 'age_days': 1,
        'detail': "Software built 18.5% of lead over the market and has now rolled over on confirmed sessions — this week -3.2% vs the market's -0.8%/wk, 25% of members rolling with it · carried by one name. Context, not a sell list.",
        'link': 'subsector_rotation.html#rotation-app',
        'validation': {'verdict': 'documented'},
    })
    up = signal('rotation-up-lead', source='rotation', type_='rotation_turn_up', asset='crop_inputs')
    up.update({
        'tier': 'context', 'age_days': 1,
        'detail': "Crop Inputs gave up 16.0% of its lead over the market and has now turned up on confirmed sessions — this week +6.4% vs the market's -1.2%/wk, 88% of members turning with it. Context, not a buy list.",
        'link': 'subsector_rotation.html#rotation-app',
        'validation': {'verdict': 'documented'},
    })
    d, u = [project([row])['briefs'][row['alert_id']] for row in (down, up)]
    assert 'leadership path' in d['implication'] and 'leadership path' in u['implication']
    assert 'carried by one name' in d['limitation']
    assert '25% breadth is concentrated' in d['limitation']
    assert '88% of members' in u['implication']


def test_rotation_family_specific_copy_abstains_on_unsupported_shapes():
    rows=[]
    for type_ in ('rotation_fading','rotation_turn_down','rotation_turn_up'):
        row=signal(f'bad-{type_}',source='rotation',type_=type_,asset='rotation')
        row.update({'detail':f'{type_} changed in an unsupported shape.',
                    'link':'subsector_rotation.html#rotation-app'})
        rows.append(row)
    briefs=project(rows)['briefs']
    assert all(briefs[row['alert_id']]['status']=='fallback' for row in rows)
    assert all(briefs[row['alert_id']]['family'] is None for row in rows)


def test_demand_ahead_gets_expectations_gap_brief_without_mutation():
    row = signal('demand-ahead', source='demand', type_='demand_ahead', asset='AVGO')
    row.update({
        'tier': 'context', 'age_days': 2,
        'detail': "ai_datacenter (+69% YoY) is running ahead of AVGO's analyst revisions — a forward-demand signal not yet fully in the price. Context for review; not a buy signal.",
        'detail_zh': 'ai_datacenter (+69% YoY) 跑在 AVGO 分析师评级调整之前——一个尚未充分计入价格的前瞻需求信号。供审阅参考；非买入信号。',
        'link': 'demand.html#timeline',
        'validation': {'verdict': 'documented'},
    })
    before = deepcopy(row)
    brief = project([row])['briefs'][row['alert_id']]
    assert row == before
    assert brief['status'] == 'supported'
    assert brief['family'] == 'demand.demand_ahead'
    assert brief['attention'] == 'for_awareness'
    assert '69% YoY' in brief['implication']
    assert 'AVGO' in brief['implication']
    assert 'possible expectations gap' in brief['implication']
    assert 'not proof the stock is underpriced' in brief['limitation']
    assert 'not separately backtested' in brief['limitation']
    assert brief['next_action_label'] == 'Recheck demand lead'
    assert brief['evidence_label'] == 'Open current demand timeline'
    assert brief['evidence_scope'] == 'current_panel_not_historical_archive'


def test_demand_ahead_discloses_age_and_revision_catchup_falsifier():
    row = signal('demand-old', source='demand', type_='demand_ahead', asset='CRWD')
    row.update({
        'tier': 'context', 'age_days': 11,
        'detail': "own_rpo (+38% YoY) is running ahead of CRWD's analyst revisions — a forward-demand signal not yet fully in the price. Context for review; not a buy signal.",
        'link': 'demand.html#timeline',
        'validation': {'verdict': 'documented'},
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert '11 days old' in brief['limitation']
    assert 'revisions catch up' in brief['reassessment']
    assert 'demand measure decelerates' in brief['reassessment']
    assert 'already discounts the change' in brief['reassessment']


def test_demand_ahead_abstains_on_malformed_or_ticker_mismatched_shapes():
    malformed = signal('demand-malformed', source='demand', type_='demand_ahead', asset='AVGO')
    malformed.update({'detail': 'Demand is ahead in an unsupported shape.',
                      'link': 'demand.html#timeline'})
    mismatch = signal('demand-mismatch', source='demand', type_='demand_ahead', asset='AVGO')
    mismatch.update({
        'detail': "ai_datacenter (+69% YoY) is running ahead of HUBB's analyst revisions — a forward-demand signal not yet fully in the price. Context for review; not a buy signal.",
        'link': 'demand.html#timeline',
    })
    briefs = project([malformed, mismatch])['briefs']
    assert all(briefs[row['alert_id']]['status'] == 'fallback' for row in (malformed, mismatch))
    assert all(briefs[row['alert_id']]['family'] is None for row in (malformed, mismatch))


def test_forex_residual_shock_gets_unexplained_move_brief_without_false_attribution():
    row = signal('fx-residual', source='forex', type_='residual_shock', asset='USDCNH')
    row.update({
        'tier': 'context', 'age_days': 2,
        'headline': "USD/CNH: Unusual move the dollar and rates don't explain (up)",
        'detail': 'CNH moved beyond what the dollar + rates explain (shock z +1.6) — possible intervention / flow / geopolitics. USD/CNH 6.6560.',
        'detail_zh': 'CNH 走势超出美元+利率可解释范围（冲击 z +1.6）— 可能为干预/资金流/地缘。USD/CNH 6.6560。',
        'link': 'forex.html#timeline',
        'validation': {'verdict': 'documented'},
    })
    before = deepcopy(row)
    brief = project([row])['briefs'][row['alert_id']]
    assert row == before
    assert brief['status'] == 'supported'
    assert brief['family'] == 'forex.residual_shock'
    assert brief['attention'] == 'for_awareness'
    assert '+1.6 z-score residual' in brief['implication']
    assert 'USD/CNH' in brief['implication']
    assert 'does not identify intervention, flows or geopolitics as the cause' in brief['limitation']
    assert 'not a probability or return forecast' in brief['limitation']
    assert brief['next_action_label'] == 'Investigate FX residual'
    assert brief['evidence_label'] == 'Open current FX timeline'
    assert brief['evidence_scope'] == 'current_panel_not_historical_archive'


def test_forex_residual_shock_discloses_staleness_and_normalization_falsifier():
    row = signal('fx-residual-old', source='forex', type_='residual_shock', asset='USDJPY')
    row.update({
        'tier': 'context', 'age_days': 12,
        'headline': "USD/JPY: Unusual move the dollar and rates don't explain (up)",
        'detail': 'JPY moved beyond what the dollar + rates explain (shock z +2.6) — possible intervention / flow / geopolitics. USD/JPY 153.8550.',
        'link': 'forex.html#timeline',
        'validation': {'verdict': 'documented'},
    })
    brief = project([row])['briefs'][row['alert_id']]
    assert brief['status'] == 'supported'
    assert '12 days old' in brief['limitation']
    assert 'residual normalizes' in brief['reassessment']
    assert 'dollar/rates model explains the move' in brief['reassessment']
    assert 'newer source evidence identifies the driver' in brief['reassessment']


def test_forex_residual_shock_abstains_on_pair_direction_or_shape_mismatch():
    mismatch_pair = signal('fx-pair', source='forex', type_='residual_shock', asset='USDCNH')
    mismatch_pair.update({
        'headline': "USD/CNH: Unusual move the dollar and rates don't explain (up)",
        'detail': 'CNH moved beyond what the dollar + rates explain (shock z +1.6) — possible intervention / flow / geopolitics. EUR/USD 1.1470.',
        'link': 'forex.html#timeline',
    })
    mismatch_direction = signal('fx-direction', source='forex', type_='residual_shock', asset='EURUSD')
    mismatch_direction.update({
        'headline': "EUR/USD: Unusual move the dollar and rates don't explain (up)",
        'detail': 'EUR moved beyond what the dollar + rates explain (shock z -2.3) — possible intervention / flow / geopolitics. EUR/USD 1.1470.',
        'link': 'forex.html#timeline',
    })
    malformed = signal('fx-malformed', source='forex', type_='residual_shock', asset='EURUSD')
    malformed.update({'headline': 'EUR/USD residual changed', 'detail': 'Unsupported residual shape.',
                      'link': 'forex.html#timeline'})
    rows = [mismatch_pair, mismatch_direction, malformed]
    briefs = project(rows)['briefs']
    assert all(briefs[row['alert_id']]['status'] == 'fallback' for row in rows)
    assert all(briefs[row['alert_id']]['family'] is None for row in rows)
