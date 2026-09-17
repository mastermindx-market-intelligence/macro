"""Deterministic downstream copy; never a score, policy or lifecycle producer.

Both the server-rendered score and its live updater consume this projection.
The measured verdict/number survive unchanged. Only claims about confirmation
are qualified, using existing component tones and a same-session risk envelope.
"""
from __future__ import annotations
from collections.abc import Mapping
from datetime import date
import math


def _map(value):
    return value if isinstance(value, Mapping) else {}


def _number(value):
    return (value if isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) else None)


def _session(value):
    if not isinstance(value, str):
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def market_read(market_state, risk_envelope=None) -> dict:
    """Format observed disagreement without promoting hazard to score authority."""
    ms, re = _map(market_state), _map(risk_envelope)
    verdict = ms.get('verdict')
    session = _session(ms.get('asof'))
    measured = _map(re.get('measured_state'))
    matching = bool(session and re.get('schema') == 'mastermind.risk_envelope/v1'
                    and re.get('market') == 'US' and ms.get('market', 'us') == 'us'
                    and re.get('revision') == 'settled' and re.get('data_state') == 'FRESH'
                    and re.get('source_session') == session
                    and measured.get('as_of') == session and measured.get('usable') is True
                    and measured.get('verdict') == verdict)
    hazard = _map(re.get('hazard_summary')).get('stage') if matching else None
    if hazard not in ('NONE', 'FRAGILE', 'TRANSMITTING', 'BREAKDOWN'):
        hazard = None
    rows = ms.get('components')
    rows = [r for r in rows if isinstance(r, Mapping)] if isinstance(rows, list) else []
    components = {r.get('key'): r for r in rows}
    breadth = components.get('breadth', {})
    trend = components.get('trend', {})
    radar = _map(ms.get('radar'))
    warning = radar.get('is_warning') is True or radar.get('state') in ('watch', 'caution', 'elevated', 'risk-off')
    freshness = _map(ms.get('freshness'))
    incomplete = bool(ms.get('stale_inputs') or ms.get('degraded_components')
                      or freshness.get('stale') is True
                      or freshness.get('any_input_stale') is True
                      or any(r.get('degraded') for r in rows))
    confirmed = bool(breadth.get('tone') == 'good' and trend.get('tone') == 'good'
                     and all(r.get('tone') == 'good' for r in rows)
                     and not warning and not incomplete)
    weak_breadth = breadth.get('tone') == 'bad'
    known = verdict in ('RISK_ON', 'MIXED', 'RISK_OFF')
    label_en, label_zh = {'RISK_ON': ('Risk-on', '风险偏好'),
                          'MIXED': ('Mixed', '分歧'),
                          'RISK_OFF': ('Risk-off', '避险')}.get(verdict, ('Unavailable', '不可用'))
    headline_en, headline_zh = {
        'RISK_ON': ('Trend and participation are supportive; this is not a drawdown forecast.',
                    '趋势与参与度提供支撑；这不是回撤预测。'),
        'MIXED': ('Market readings are mixed; broad confirmation is missing.', '市场读数存在分歧，尚无广泛确认。'),
        'RISK_OFF': ('The measured blend indicates risk-off conditions.', '实测综合读数显示避险状态。'),
    }.get(verdict, ('Current market readings are unavailable.', '当前市场读数不可用。'))
    qualified = verdict == 'RISK_ON' and (not confirmed or hazard not in (None, 'NONE'))
    if qualified:
        label_en, label_zh = 'Uneven support', '支撑不均'
        headline_en, headline_zh = ('Measured support is uneven; a broad advance is not confirmed.',
                                    '实测支撑不均，尚未确认广泛上涨。')
        if not rows:
            label_en, label_zh = 'Risk-on composite', '偏多综合读数'
            headline_en, headline_zh = ('The composite is supportive; participation confirmation is unavailable.',
                                        '综合读数偏多，但参与度确认信息不可用。')
        if incomplete:
            label_en, label_zh = 'Confirmation incomplete', '确认不完整'
            headline_en, headline_zh = (
                'Some inputs are stale or incomplete; broad confirmation is unavailable.',
                '部分输入已过期或不完整，无法确认广泛支撑。')
            if weak_breadth:
                headline_en = 'Breadth is weak; some inputs are stale or incomplete.'
                headline_zh = '广度偏弱；部分输入已过期或不完整。'
        if hazard in ('FRAGILE', 'TRANSMITTING', 'BREAKDOWN'):
            label_en, label_zh = {'FRAGILE': ('Fragile', '脆弱'),
                                  'TRANSMITTING': ('Damage spreading', '损伤扩散'),
                                  'BREAKDOWN': ('Market damage', '市场受损')}[hazard]
            headline_en, headline_zh = ('The supportive composite and settled risk evidence disagree.',
                                        '偏多综合读数与已结算风险证据存在分歧。')
            if weak_breadth:
                headline_en += ' Breadth is weak.'
                headline_zh += '广度偏弱。'
    subline_en = ('Measured blend — read with caution' if qualified else
                  'Measured blend — not a probability' if known else 'Readings unavailable')
    subline_zh = ('实测综合读数——需谨慎解读' if qualified else
                  '实测综合读数——并非概率' if known else '读数不可用')
    if ms.get('capped') is True or ms.get('score_source') in (
            'radar_ceiling', 'hard_force', 'verdict_cap'):
        original = _number(ms.get('raw_score'))
        headline_en = 'A risk constraint caps the score; the underlying blend is separate.'
        headline_zh = '风险约束限制显示分数；原始综合读数单独保留。'
        subline_en = (f'Capped reading — measured blend {original:g}/100' if original is not None
                      else 'Capped reading — original blend unavailable')
        subline_zh = (f'封顶读数——实测综合读数 {original:g}/100' if original is not None
                      else '封顶读数——原始综合读数不可用')
    return {
        'schema': 'market_read.presentation.v1', 'authority': 'presentation_only',
        'measured_verdict': verdict if known else None, 'score': _number(ms.get('score')),
        'qualified': qualified, 'label_en': label_en, 'label_zh': label_zh,
        'headline_en': headline_en, 'headline_zh': headline_zh,
        'subline_en': subline_en, 'subline_zh': subline_zh,
        'action_en': 'Review risk evidence' if qualified else None,
        'action_zh': '查看风险证据' if qualified else None,
        'hazard_stage': hazard, 'context_session': session if matching and hazard else None,
        'context_basis': 'settled' if matching and hazard else None,
        'breadth_score': _number(breadth.get('score')),
    }
