"""Pure investigation projection over Alert Triage's existing evidence.

No readers, persistence, new signal IDs, scoring or outbound authority live here.
The capped legacy board and its push consumers remain unchanged.
"""
from __future__ import annotations

from datetime import date
import unicodedata
import math
import re

from engine import alert_time


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_json_safe(v) for v in value)
    return value


def _key(row: dict) -> tuple[str, str, str]:
    source = str(row.get('source') or '')
    return source, str(row.get('type') or ''), str(row.get('asset') or source)


def _clock_key(row: dict) -> tuple:
    day = alert_time.parse_date(row.get('board_date')) or date.min
    instant = alert_time.parse_instant(row.get('event_ts'))
    return day, instant.timestamp() if instant is not None else 0.0


def _plain(text: str) -> str:
    text = str(text or '').strip()
    while text and (unicodedata.category(text[0])[0] in 'PS' or text[0].isspace()):
        text = text[1:]
    return text.strip()


BRIEF_SCHEMA = 'mastermind.alert_brief.v1'
_TRANSITION_DETAIL = re.compile(
    r"^The regime's footing went from (.+?) to (.+?) \((\d+) warning flags active\)$"
)
_RISK_DETAIL = re.compile(
    r'^Equity risk-state crossed into ([A-Z][A-Z _-]+) \((\d{1,3})/100\) — (.+?); (.+)$'
)
_COMMODITY_PRICE_SHOCK = re.compile(
    r'^Oil ([0-9][0-9,.]*) \$/bbl — the acute move is settling\.$'
)
_VECTOR_ALLOCATION_CHANGE = re.compile(
    r'^Optimal strategy moved ([0-9]{1,3})% → ([0-9]{1,3})% BTC '
    r'\(momentum × risk grid\)\.$'
)
_ALTDATA_CONVERGENCE = re.compile(
    r'^(.+?) lit up by ([0-9]+) independent alt-data channels: (.+)\.$'
)
_ROTATION_EMERGING = re.compile(
    r'^(.+?) just turned (improving|leading) & accelerating '
    r'\(1W ([+-]?[0-9]+(?:\.[0-9]+)?)%, '
    r'1M ([+-]?[0-9]+(?:\.[0-9]+)?)%, '
    r'3M ([+-]?[0-9]+(?:\.[0-9]+)?)%; accel '
    r'([+-]?[0-9]+(?:\.[0-9]+)?)\)\. An early rotate-in candidate '
    r'— context, not a buy list\.$'
)
_VECTOR_IMPULSE_DOWN = re.compile(
    r'^DVOL intraday-range spike \(unusually large versus its own history\) '
    r'— the options market is repricing risk\. BTC \$([0-9][0-9,]*)\.$'
)

_INSTRUMENT_RISK_HEADLINE = re.compile(
    r'^(.+?) risk turned (Elevated|Calm)$'
)
_INSTRUMENT_RISK_DETAIL = re.compile(
    r'^Risk Index (rose through|fell back below) (?:the|its) threshold to '
    r'([0-9]{1,3})\. (.+)\.$'
)
_GEX_FLIP_DETAIL = re.compile(
    r'^GEX: (spot crossed the gamma flip|net GEX changed sign) '
    r'\(net ([+-]?(?:[0-9]+bn|n/a)), spot vs flip '
    r'([+-]?(?:[0-9]+(?:\.[0-9]+)?%|n/a))\)'
    r'( — measured across [0-9]+ sessions, not overnight: no chain snapshot exists for '
    r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:, [0-9]{4}-[0-9]{2}-[0-9]{2})*, '
    r'so the crossing point inside that span is unobserved)?$'
)
_HIDDEN_FRAGILITY_DETAIL = re.compile(
    r'^(Complacency watch: calm tape starting to mask weakening internals|'
    r'Hidden fragility: a calm surface \(cheap VIX, contango\) over weakening '
    r'internals \(thinning breadth, HY widening\) — the classic complacent '
    r'pre-drawdown setup)$'
)
_BREADTH_DIVERGENCE_DETAIL = re.compile(
    r'^Breadth divergence: index near its 1y high while %>200dma is weak '
    r'\(([0-9]{1,3})% pctile\) — fewer names carrying the tape$'
)


def _attention(row: dict) -> str:
    """Translate source tier + canonical freshness into page attention only."""
    tier = str(row.get('tier') or '')
    age = _age_days(row)
    if tier == 'act':
        return 'review_first' if age is not None and age <= 2 else 'earlier_priority'
    if tier == 'watch' and age is not None and age <= 2:
        return 'watch_next'
    return 'for_awareness'


def _age_days(row: dict) -> int | None:
    value = row.get('age_days')
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _fallback_brief(row: dict) -> dict:
    validation = row.get('validation') if isinstance(row.get('validation'), dict) else {}
    implication = str(row.get('edge') or validation.get('note') or '')
    implication_zh = str(row.get('edge_zh') or validation.get('note_zh') or implication)
    verdict = str(validation.get('verdict') or '')
    if verdict in {'no_edge', 'killed'}:
        limitation = 'No validated forward edge. Use this as evidence context, not a timing signal.'
        limitation_zh = '没有经过验证的前瞻优势。应将其作为证据背景，而非择时信号。'
    elif verdict == 'underpowered':
        limitation = 'The available sample is insufficient for a predictive claim.'
        limitation_zh = '现有样本不足以支持预测性结论。'
    elif int(row.get('fire_count') or 0) > 1:
        limitation = 'Repeated firings are observations, not proof the condition stayed active between them.'
        limitation_zh = '重复触发只是观测记录，并不能证明状态在期间持续有效。'
    else:
        limitation = 'Attention level and predictive evidence are separate.'
        limitation_zh = '关注级别与预测证据是两回事。'
    link = str(row.get('link') or '')
    return {
        'schema': BRIEF_SCHEMA, 'status': 'fallback', 'family': None,
        'attention': _attention(row),
        'change': str(row.get('detail') or _plain(row.get('headline') or '')),
        'change_zh': str(row.get('detail_zh') or row.get('detail') or _plain(row.get('headline_zh') or '')),
        'implication': implication, 'implication_zh': implication_zh,
        'limitation': limitation, 'limitation_zh': limitation_zh,
        'next_action': 'Open the source evidence before drawing a conclusion.',
        'next_action_zh': '先打开来源证据，再形成结论。',
        'next_action_label': 'Inspect evidence', 'next_action_label_zh': '查看证据',
        'reassessment': '', 'reassessment_zh': '',
        'evidence_scope': 'current_panel_not_historical_archive' if link else 'no_verified_destination',
        'evidence_label': 'Open source evidence', 'evidence_label_zh': '打开来源证据',
        'event_age_days': _age_days(row),
    }


def build_alert_brief(row: dict) -> dict:
    """Build presentation-only copy without changing alert authority or identity."""
    brief = _fallback_brief(row)
    source, type_ = str(row.get('source') or ''), str(row.get('type') or '')
    detail = str(row.get('detail') or '')
    detail_zh = str(row.get('detail_zh') or detail)
    validation = row.get('validation') if isinstance(row.get('validation'), dict) else {}
    edge = str(row.get('edge') or validation.get('note') or '')
    edge_zh = str(row.get('edge_zh') or validation.get('note_zh') or edge)
    age = _age_days(row)

    transition = _TRANSITION_DETAIL.fullmatch(detail)
    if source == 'macro' and type_ == 'transition_state_change' and transition:
        age_clause = f'This event is {age} days old; ' if age is not None and age > 2 else ''
        age_clause_zh = f'该事件发生于 {age} 天前；' if age is not None and age > 2 else ''
        brief.update({
            'status': 'supported', 'family': 'macro.transition_state_change',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge, 'implication_zh': edge_zh,
            'limitation': (
                'A regime-model transition is not market confirmation or a price forecast. '
                f'{age_clause}re-check the current regime before acting.'),
            'limitation_zh': (
                '周期模型转换并不等于市场确认或价格预测。'
                f'{age_clause_zh}行动前应重新核对当前周期状态。'),
            'next_action': (
                'Open the current Regime Radar and compare today’s state before changing '
                'growth-sensitive exposure.'),
            'next_action_zh': '打开当前周期雷达，在调整增长敏感型敞口前核对今日状态。',
            'next_action_label': 'Recheck regime', 'next_action_label_zh': '复核周期',
            'reassessment': (
                'Change the read only if the current radar has returned to a stable state '
                'or the named warning flags have cleared.'),
            'reassessment_zh': '仅当当前雷达恢复稳定状态或相关预警消退时，才改变判断。',
            'evidence_label': 'Open current Regime Radar',
            'evidence_label_zh': '打开当前周期雷达',
        })
        return brief

    risk = _RISK_DETAIL.fullmatch(detail)
    if source == 'macro' and type_ == 'risk_state_elevated' and risk:
        source_score = int(risk.group(2))
        priority = row.get('priority')
        priority_text = str(priority) if isinstance(priority, (int, float)) and not isinstance(priority, bool) else 'unknown'
        age_sentence = f' This event is {age} days old.' if age is not None and age > 2 else ''
        age_sentence_zh = f' 该事件发生于 {age} 天前。' if age is not None and age > 2 else ''
        brief.update({
            'status': 'supported', 'family': 'macro.risk_state_elevated',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge, 'implication_zh': edge_zh,
            'limitation': (
                f'{source_score}/100 is the source risk-state reading; attention priority '
                f'{priority_text} is a separate ordering value, not a return forecast or '
                f'stock-selection score.{age_sentence}'),
            'limitation_zh': (
                f'{source_score}/100 是来源风险状态读数；关注优先级 {priority_text} 是独立的排序值，'
                f'并非收益预测或选股评分。{age_sentence_zh}'),
            'next_action': (
                'Open the current Risk Envelope, re-check breadth, volatility and positioning, '
                'then review gross exposure before chasing leaders.'),
            'next_action_zh': '打开当前风险框架，复核宽度、波动与仓位，再决定是否追逐领涨标的。',
            'next_action_label': 'Recheck risk', 'next_action_label_zh': '复核风险',
            'reassessment': (
                'Reassess when the current source no longer reports ELEVATED or the named '
                'fragility inputs improve.'),
            'reassessment_zh': '当当前来源不再显示偏高状态，或相关脆弱性指标改善时再重新评估。',
            'evidence_label': 'Open current Risk Envelope',
            'evidence_label_zh': '打开当前风险框架',
        })
        return brief

    impulse = _VECTOR_IMPULSE_DOWN.fullmatch(detail)
    if source == 'vector' and type_ == 'impulse_warn_down' and impulse:
        if age is None:
            window_limit = (
                'The source describes a 2–4 day edge window, but event age is unavailable, '
                'so current validity cannot be established.')
            window_limit_zh = '来源描述的是 2–4 天优势窗口，但事件时间未知，无法确认当前有效性。'
            implication = (
                'The source reports a short leading de-risk window, but without an event '
                'age it cannot be treated as current.')
            implication_zh = '来源报告了一个短期领先减仓窗口，但事件时间未知，不能视为当前信号。'
            blind_spot = (
                'The model is blind to slow or options-calm selloffs, so this is not a '
                'current de-risk instruction.')
            blind_spot_zh = '该模型无法识别缓慢下跌或期权市场平静的抛售，因此这不是当前减仓指令。'
            reassessment = (
                'Restore fresh urgency only if the current panel shows a new precursor '
                'cross with a new event clock.')
            reassessment_zh = '仅当当前面板出现带有新事件时间的新前兆突破时，才恢复最新紧迫性。'
        elif age <= 4:
            unit = 'day' if age == 1 else 'days'
            window_limit = (
                f'The source describes a 2–4 day edge window; this event is {age} {unit} '
                'old, so any urgency is bounded to that short horizon.')
            window_limit_zh = f'来源描述的是 2–4 天优势窗口；该事件已过去 {age} 天，紧迫性仅限于这一短期范围。'
            implication = edge or (
                'The source reports a fresh leading precursor with a short forward de-risk window.')
            implication_zh = edge_zh or '来源报告了一个最新领先前兆，伴随短期前瞻减仓窗口。'
            blind_spot = (
                'The model is blind to slow or options-calm selloffs, so this is a bounded '
                'risk-management signal rather than a universal selloff detector.')
            blind_spot_zh = '该模型无法识别缓慢下跌或期权市场平静的抛售，因此这是有限的风险管理信号，并非通用下跌探测器。'
            reassessment = (
                'Reassess if the current panel no longer shows the precursor cross or once '
                'the short edge window expires.')
            reassessment_zh = '若当前面板不再显示前兆突破，或短期优势窗口结束，则重新评估。'
        else:
            window_limit = (
                f'The source describes a 2–4 day edge window; at {age} days old, that '
                '2–4 day edge window has elapsed.')
            window_limit_zh = f'来源描述的是 2–4 天的优势窗口；该事件已过去 {age} 天，窗口已经结束。'
            implication = (
                f'The source originally reported a short leading de-risk window from this '
                f'precursor; at {age} days old, that signal is historical rather than current.')
            implication_zh = f'来源曾报告该前兆带来的短期领先减仓窗口；事件已过去 {age} 天，属于历史信号而非当前信号。'
            blind_spot = (
                'The model is blind to slow or options-calm selloffs, so this is not a '
                'current de-risk instruction.')
            blind_spot_zh = '该模型无法识别缓慢下跌或期权市场平静的抛售，因此这不是当前减仓指令。'
            reassessment = (
                'Restore fresh urgency only if the current panel shows a new precursor '
                'cross with a new event clock.')
            reassessment_zh = '仅当当前面板出现带有新事件时间的新前兆突破时，才恢复最新紧迫性。'
        brief.update({
            'status': 'supported', 'family': 'vector.impulse_warn_down',
            'change': detail, 'change_zh': detail_zh,
            'implication': implication, 'implication_zh': implication_zh,
            'limitation': f'{window_limit} {blind_spot}',
            'limitation_zh': f'{window_limit_zh}{blind_spot_zh}',
            'next_action': (
                'Open the current impulse panel and verify whether a new leading precursor '
                'cross exists before changing risk.'),
            'next_action_zh': '打开当前脉冲面板，确认是否出现新的领先前兆突破，再调整风险。',
            'next_action_label': 'Recheck impulse',
            'next_action_label_zh': '复核脉冲',
            'reassessment': reassessment,
            'reassessment_zh': reassessment_zh,
            'evidence_label': 'Open current impulse panel',
            'evidence_label_zh': '打开当前脉冲面板',
        })
        return brief

    commodity = _COMMODITY_PRICE_SHOCK.fullmatch(detail)
    if source == 'commodity' and type_ == 'price_shock' and commodity:
        brief.update({
            'status': 'supported', 'family': 'commodity.price_shock',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                'The acute oil move is losing intensity, which may reduce immediate '
                'shock pressure without establishing the next price direction.'),
            'implication_zh': '原油急剧波动正在减弱，短期冲击压力可能下降，但下一价格方向仍未确定。',
            'limitation': (
                'The source says the shock is settling; it does not establish direction, '
                'a durable regime, or a separately backtested timing edge. Re-fired '
                'observations do not prove continuous stabilization.'),
            'limitation_zh': (
                '来源仅表示冲击正在平息；这不能确定方向、持久状态或经过单独回测的择时优势。'
                '重复触发也不能证明稳定状态持续存在。'),
            'next_action': (
                'Open the current commodity timeline and confirm whether the shock is '
                'still settling before changing oil-sensitive exposure.'),
            'next_action_zh': '打开当前商品时间线，确认冲击是否仍在平息，再调整原油敏感敞口。',
            'next_action_label': 'Recheck oil', 'next_action_label_zh': '复核原油',
            'reassessment': (
                'Change the read if the current timeline shows renewed acceleration, '
                'a new shock direction, or the stabilization state has disappeared.'),
            'reassessment_zh': '若当前时间线显示冲击重新加速、方向改变或稳定状态消失，则改变判断。',
            'evidence_label': 'Open current commodity timeline',
            'evidence_label_zh': '打开当前商品时间线',
        })
        return brief

    allocation = _VECTOR_ALLOCATION_CHANGE.fullmatch(detail)
    if source == 'vector' and type_ == 'allocation_change' and allocation:
        old_weight, new_weight = allocation.group(1), allocation.group(2)
        brief.update({
            'status': 'supported', 'family': 'vector.allocation_change',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge,
            'implication_zh': edge_zh or '这是策略模型的配置输出；历史回测曾跑赢买入并持有。',
            'limitation': (
                f'The {old_weight}% → {new_weight}% change is a model allocation output. '
                'Its historical backtest does not guarantee future returns, and repeated '
                'firings do not prove the allocation stayed unchanged between observations.'),
            'limitation_zh': (
                f'{old_weight}% → {new_weight}% 是模型配置输出。历史回测不能保证未来收益，'
                '重复触发也不能证明两次观测之间的配置保持不变。'),
            'next_action': (
                'Open the current allocation panel and compare the current BTC weight and '
                'momentum/risk inputs before changing exposure.'),
            'next_action_zh': '打开当前配置面板，比较最新 BTC 权重与动量/风险输入，再调整敞口。',
            'next_action_label': 'Open allocation',
            'next_action_label_zh': '打开配置',
            'reassessment': (
                f'Reassess if the current panel no longer shows {new_weight}% BTC or the '
                'momentum/risk grid reverses direction.'),
            'reassessment_zh': f'若当前面板不再显示 {new_weight}% BTC，或动量/风险网格反转，则重新评估。',
            'evidence_label': 'Open current allocation panel',
            'evidence_label_zh': '打开当前配置面板',
        })
        return brief

    convergence = _ALTDATA_CONVERGENCE.fullmatch(detail)
    if source == 'altdata' and type_ == 'convergence' and convergence:
        asset, channel_count, channel_names = convergence.groups()
        brief.update({
            'status': 'supported', 'family': 'altdata.convergence',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'The source reports {channel_count} alt-data channels converging on '
                f'{asset}; this is a research lead, not confirmation.'),
            'implication_zh': f'来源报告 {channel_count} 个替代数据渠道同时指向 {asset}；这是研究线索，不是确认。',
            'limitation': (
                'The channel count is not a probability, expected return, or proof of '
                'independent economic causes. This family is not separately backtested '
                'as a timing signal, and repeated firings do not prove persistence.'),
            'limitation_zh': (
                '渠道数量不是概率、预期收益，也不能证明存在独立的经济原因。该信号族未作为择时信号'
                '单独回测，重复触发也不能证明状态持续。'),
            'next_action': (
                f'Open the current convergence panel, inspect the named channels '
                f'({channel_names}) and their source timestamps, then decide whether '
                f'{asset} merits deeper research.'),
            'next_action_zh': f'打开当前汇聚面板，检查相关渠道及来源时间，再决定是否深入研究 {asset}。',
            'next_action_label': 'Inspect channels',
            'next_action_label_zh': '检查渠道',
            'reassessment': (
                'Change the read if the channels disappear, collapse to one underlying '
                'event, or newer source evidence contradicts the convergence.'),
            'reassessment_zh': '若渠道消失、实际来自同一底层事件，或更新证据与汇聚结论矛盾，则改变判断。',
            'evidence_label': 'Open current convergence panel',
            'evidence_label_zh': '打开当前汇聚面板',
        })
        return brief

    rotation = _ROTATION_EMERGING.fullmatch(detail)
    if source == 'rotation' and type_ == 'rotation_emerging' and rotation:
        subject, state, one_week, one_month, three_month, acceleration = rotation.groups()
        state_zh = {'improving': '改善', 'leading': '领先'}[state]
        horizon_text = f'1W {one_week}%, 1M {one_month}%, 3M {three_month}%'
        brief.update({
            'status': 'supported', 'family': 'rotation.rotation_emerging',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} is {state} and accelerating, with {horizon_text} and '
                f'acceleration {acceleration}; this is an early research candidate.'),
            'implication_zh': (
                f'{subject} 当前处于{state_zh}且加速状态；1周 {one_week}%，1月 {one_month}%，'
                f'3月 {three_month}%，加速 {acceleration}。这是一个早期研究候选。'),
            'limitation': (
                'This is explicitly context, not a buy list or a separately backtested '
                'timing signal. The 1W/1M/3M return profile and state label are descriptive '
                'snapshots that can reverse; repeated firings do not prove persistence.'),
            'limitation_zh': (
                '这明确只是背景，不是买入清单，也不是经过单独回测的择时信号。1周/1月/3月收益'
                '与状态标签只是可能反转的描述性快照；重复触发也不能证明状态持续。'),
            'next_action': (
                f'Open the current rotation panel and confirm {subject} still ranks {state} '
                'and accelerating before promoting it to a research candidate.'),
            'next_action_zh': f'打开当前轮动面板，确认 {subject} 仍处于{state_zh}且加速状态，再将其列为研究候选。',
            'next_action_label': 'Check rotation',
            'next_action_label_zh': '检查轮动',
            'reassessment': (
                f'Change the read if the current status loses its {state}/accelerating '
                'classification or the observed horizon profile deteriorates.'),
            'reassessment_zh': f'若当前状态不再{state_zh}/加速，或所示周期表现恶化，则改变判断。',
            'evidence_label': 'Open current rotation panel',
            'evidence_label_zh': '打开当前轮动面板',
        })
        return brief

    risk_headline = _INSTRUMENT_RISK_HEADLINE.fullmatch(_plain(row.get('headline') or ''))
    risk_detail = _INSTRUMENT_RISK_DETAIL.fullmatch(detail)
    if source in {'commodity', 'forex'} and type_ == 'risk_regime' and risk_headline and risk_detail:
        subject, named_state = risk_headline.groups()
        movement, score_text, observed = risk_detail.groups()
        expected_state = 'Elevated' if movement == 'rose through' else 'Calm'
        if named_state == expected_state:
            score = int(score_text)
            age_limit = ''
            age_limit_zh = ''
            if age is None:
                age_limit = ' Event age is unavailable; current validity cannot be established.'
                age_limit_zh = ' 事件时间未知，无法确认当前有效性。'
            elif age > 2:
                unit = 'day' if age == 1 else 'days'
                age_limit = f' This event is {age} {unit} old; recheck the current timeline.'
                age_limit_zh = f' 该事件已过去 {age} 天；请复核当前时间线。'
            if named_state == 'Elevated':
                implication = (
                    f'{subject} crossed into its source-defined elevated risk state at '
                    f'{score}; this warrants closer review of that instrument.')
                implication_zh = f'{subject} 的来源风险指数升至 {score}，进入偏高状态；应加强对该标的的风险复核。'
                state_read = 'remains Elevated'
                state_read_zh = '仍处于偏高状态'
            else:
                implication = (
                    f'{subject} fell back into its source-defined calm risk state at '
                    f'{score}; measured risk eased, but this is not an all-clear.')
                implication_zh = f'{subject} 的来源风险指数回落至 {score}，进入平静状态；风险读数下降，但并非全面解除警报。'
                state_read = 'remains Calm'
                state_read_zh = '仍处于平静状态'
            verdict = str(validation.get('verdict') or '')
            if verdict == 'confirmer':
                horizon = str(validation.get('horizon') or '').strip()
                horizon_label = (
                    f' {horizon[:-1]}-day' if horizon.endswith('d') and horizon[:-1].isdigit()
                    else f' {horizon}' if horizon else '')
                evidence_limit = (
                    f'The source classifies this as a{horizon_label} confirmer; it does not '
                    'publish a probability, price direction or complete performance statistics '
                    'in this snapshot.')
                evidence_limit_zh = '来源将其归类为确认项；该快照未提供概率、价格方向或完整绩效统计。'
            else:
                note = str(validation.get('note') or '').strip()
                evidence_limit = note or (
                    'This source family is documented, not separately backtested as a timing signal.')
                evidence_limit_zh = str(validation.get('note_zh') or '').strip() or (
                    '该来源信号族有据可查，但未作为择时信号单独回测。')
            source_name = 'commodity' if source == 'commodity' else 'FX'
            source_name_zh = '商品' if source == 'commodity' else '外汇'
            brief.update({
                'status': 'supported', 'family': f'{source}.risk_regime',
                'change': detail, 'change_zh': detail_zh,
                'implication': implication, 'implication_zh': implication_zh,
                'limitation': (
                    f'{evidence_limit} The reading is instrument-specific—not a market-wide '
                    f'probability, return forecast or trade instruction.{age_limit}'),
                'limitation_zh': (
                    f'{evidence_limit_zh} 该读数仅针对单一标的，并非全市场概率、收益预测或交易指令。'
                    f'{age_limit_zh}'),
                'next_action': (
                    f'Open the current {source_name} timeline and verify that {subject} '
                    f'{state_read} before changing exposure.'),
                'next_action_zh': f'打开当前{source_name_zh}时间线，确认 {subject} {state_read_zh}，再调整敞口。',
                'next_action_label': f'Recheck {source_name} risk',
                'next_action_label_zh': f'复核{source_name_zh}风险',
                'reassessment': (
                    f'Change the read if the current risk index recrosses its threshold or '
                    f'the current timeline no longer shows {named_state}.'),
                'reassessment_zh': f'若当前风险指数重新穿越阈值，或时间线不再显示{"偏高" if named_state == "Elevated" else "平静"}状态，则改变判断。',
                'evidence_label': f'Open current {source_name} timeline',
                'evidence_label_zh': f'打开当前{source_name_zh}时间线',
            })
            return brief

    gex = _GEX_FLIP_DETAIL.fullmatch(detail)
    if source == 'macro' and type_ == 'gex_flip_cross' and gex:
        event_kind, net_gex, spot_vs_flip, gap_disclosure = gex.groups()
        age_limit = ''
        age_limit_zh = ''
        if age is None:
            age_limit = ' Event age is unavailable, so current validity cannot be established.'
            age_limit_zh = ' 事件时间未知，无法确认当前有效性。'
        elif age > 2:
            unit = 'day' if age == 1 else 'days'
            age_limit = f' This event is {age} {unit} old; current gamma may have changed.'
            age_limit_zh = f' 该事件已过去 {age} 天；当前 Gamma 状态可能已经改变。'
        extra = ' '.join(str(item) for item in validation.get('extra') or [])
        sample_limit = (
            ' The validation history is still accruing with a small sample.'
            if 'n small' in extra.lower() else '')
        sample_limit_zh = ' 验证历史仍在积累，样本量较小。' if sample_limit else ''
        gap_limit = (
            ' The source measured the transition across multiple sessions with missing '
            'chain snapshots, so the exact crossing time is unobserved.'
            if gap_disclosure else '')
        gap_limit_zh = ' 来源跨多个交易日测量该变化，且期间缺少期权链快照，因此无法观测准确穿越时点。' if gap_disclosure else ''
        brief.update({
            'status': 'supported', 'family': 'macro.gex_flip_cross',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge or (
                f'{event_kind} with net GEX {net_gex} and spot-versus-flip {spot_vs_flip}; '
                'the volatility backdrop changed.'),
            'implication_zh': edge_zh or (
                f'{event_kind}；净 GEX 为 {net_gex}，现价相对翻转点为 {spot_vs_flip}，波动背景发生变化。'),
            'limitation': (
                'This is a volatility-backdrop confirmer, not a directional call, return '
                'forecast or proof that the state persisted between firings.'
                f'{sample_limit}{gap_limit}{age_limit}'),
            'limitation_zh': (
                '这是波动背景确认项，并非方向判断、收益预测，也不能证明状态在重复触发之间持续。'
                f'{sample_limit_zh}{gap_limit_zh}{age_limit_zh}'),
            'next_action': (
                'Open the current gamma board and verify net GEX, spot-versus-flip and '
                'chain-snapshot continuity before changing volatility assumptions.'),
            'next_action_zh': '打开当前 Gamma 面板，复核净 GEX、现价相对翻转点和期权链快照连续性，再调整波动假设。',
            'next_action_label': 'Recheck gamma', 'next_action_label_zh': '复核 Gamma',
            'reassessment': (
                'Change the read if current net GEX or the spot side of the flip reverses, '
                'or newer chain evidence contradicts the crossing.'),
            'reassessment_zh': '若当前净 GEX 或现价相对翻转点的方向反转，或更新期权链证据与该变化矛盾，则改变判断。',
            'evidence_label': 'Open current gamma board',
            'evidence_label_zh': '打开当前 Gamma 面板',
        })
        return brief

    fragility = _HIDDEN_FRAGILITY_DETAIL.fullmatch(detail)
    if source == 'macro' and type_ == 'hidden_fragility' and fragility:
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck both legs now.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请重新核对两个条件。'
        brief.update({
            'status': 'supported', 'family': 'macro.hidden_fragility',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge, 'implication_zh': edge_zh,
            'limitation': (
                'The source requires the calm-surface and weakening-internals conjunction; '
                'low VIX alone is insufficient. This family is documented, not separately '
                f'backtested as a timing signal; it provides no market-top probability or countdown.{age_limit}'),
            'limitation_zh': (
                '来源要求“表面平静”与“内部走弱”同时成立；仅有低 VIX 并不充分。该信号族有据可查，'
                f'但未作为择时信号单独回测，也不提供市场顶部概率或倒计时。{age_limit_zh}'),
            'next_action': (
                'Open the current risk panel and verify both the VIX/contango calm leg and '
                'the breadth/credit fragility leg before changing gross exposure.'),
            'next_action_zh': '打开当前风险面板，同时复核 VIX/contango 平静条件与宽度/信用脆弱条件，再调整总敞口。',
            'next_action_label': 'Recheck fragility',
            'next_action_label_zh': '复核脆弱性',
            'reassessment': (
                'Change the read if either the calm-surface leg or the weakening-internals '
                'leg disappears in the current panel.'),
            'reassessment_zh': '若当前面板中的表面平静条件或内部走弱条件任一消失，则改变判断。',
            'evidence_label': 'Open current risk panel',
            'evidence_label_zh': '打开当前风险面板',
        })
        return brief

    breadth = _BREADTH_DIVERGENCE_DETAIL.fullmatch(detail)
    if source == 'macro' and type_ == 'breadth_divergence' and breadth:
        percentile = int(breadth.group(1))
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck current breadth.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前市场宽度。'
        brief.update({
            'status': 'supported', 'family': 'macro.breadth_divergence',
            'change': detail, 'change_zh': detail_zh,
            'implication': edge, 'implication_zh': edge_zh,
            'limitation': (
                f'The {percentile}% percentile is a descriptive breadth state, not a '
                'market-top probability or timer. This family is documented, not separately '
                f'backtested as a timing signal.{age_limit}'),
            'limitation_zh': (
                f'{percentile}% 分位是描述性的市场宽度状态，并非市场顶部概率或择时计时器。'
                f'该信号族有据可查，但未作为择时信号单独回测。{age_limit_zh}'),
            'next_action': (
                'Open the current risk panel and verify that the index remains near its '
                'one-year high while the share above the 200-day average is still weak.'),
            'next_action_zh': '打开当前风险面板，确认指数仍接近一年高点，且站上 200 日均线的个股占比依然偏弱。',
            'next_action_label': 'Recheck breadth',
            'next_action_label_zh': '复核宽度',
            'reassessment': (
                'Change the read if breadth recovers materially or the index is no longer '
                'near the referenced high.'),
            'reassessment_zh': '若市场宽度明显恢复，或指数不再接近所述高点，则改变判断。',
            'evidence_label': 'Open current risk panel',
            'evidence_label_zh': '打开当前风险面板',
        })
        return brief

    return brief


def _subject(rows: list[dict], asset: str, language: str = 'en') -> str:
    # A display label only. Matching NEVER depends on title text or a generic link.
    field = 'headline_zh' if language == 'zh' else 'headline'
    for row in rows:
        headline = _plain(row.get(field) or '')
        for separator in (':', '：'):
            if separator in headline:
                label = headline.split(separator, 1)[0].strip()
                if 0 < len(label) <= 80:
                    return label
    return asset.replace('_', ' ') if asset.isupper() else asset.replace('_', ' ').title()


def _situations(signals: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in signals:
        source, _, asset = _key(row)
        if not asset or asset.lower() in {source.lower(), 'macro', 'rates', 'vector', 'all'}:
            continue
        groups.setdefault((source, asset), []).append(row)
    result = []
    for (source, asset), rows in groups.items():
        if len({r.get('type') for r in rows}) < 2:
            continue
        result.append({'primary_alert_id': rows[0]['alert_id'],
                       'member_ids': list(dict.fromkeys(r['alert_id'] for r in rows)),
                       'subject': _subject(rows, asset), 'subject_zh': _subject(rows, asset, 'zh'),
                       'source': source, 'source_label': rows[0].get('source_label', source),
                       'source_label_zh': rows[0].get('source_label_zh', source),
                       'method': 'same_source_subject'})
    return result


def build_explorer(signals: list[dict], raw_events: list[dict], *,
                   history_limit: int = 1000) -> dict:
    """Expose uncapped signals and bounded observed history without promotion.

    The caller supplies the already-ranked, future-quarantined populations.
    Derived situations are same-source exact-subject views, not new entities.
    History rows refer to the existing parent alert_id; no synthetic event ID.
    """
    if isinstance(history_limit, bool) or not isinstance(history_limit, int) or history_limit < 0:
        raise ValueError('history_limit must be a non-negative integer')
    # Tenant-bound sentinel evidence must not expand into a shared page.
    signals = [_json_safe(r) for r in signals if r.get('source') != 'watchlist']
    briefs = {str(row['alert_id']): build_alert_brief(row)
              for row in signals if row.get('alert_id')}
    index = {_key(row): row for row in signals}
    sources: dict[str, dict] = {}
    for row in signals:
        source = str(row.get('source') or '')
        info = sources.setdefault(source, {'source': source, 'count': 0,
            'label': row.get('source_label', source),
            'label_zh': row.get('source_label_zh', source)})
        info['count'] += 1
    history = []
    clock_fields = ('board_date', 'event_date', 'event_ts', 'source_asof',
                    'recorded_at', 'date_precision')
    for event in raw_events:
        parent = index.get(_key(event))
        if parent is None:
            continue
        history.append({
            'alert_id': parent['alert_id'], 'source': parent['source'],
            'asset': parent.get('asset'), 'type': parent.get('type'),
            'source_label': parent.get('source_label', parent['source']),
            'source_label_zh': parent.get('source_label_zh', parent['source']),
            'headline': _plain(event.get('headline') or parent.get('headline') or ''),
            'headline_zh': _plain(event.get('headline_zh') or event.get('headline') or ''),
            'detail': str(event.get('detail') or ''),
            'detail_zh': str(event.get('detail_zh') or event.get('detail') or ''),
            **{key: event.get(key) for key in clock_fields},
        })
    history.sort(key=_clock_key, reverse=True)
    return {'schema': 'mastermind.alert_center_view.v1',
            'brief_schema': BRIEF_SCHEMA, 'briefs': briefs,
            'signals': list(signals), 'total_signals': len(signals),
            'restricted_sources': ['watchlist'],
            'sources': sorted(sources.values(), key=lambda s: s['label']),
            'situations': _situations(signals), 'history': history[:history_limit],
            'history_total': len(history), 'history_limit': history_limit,
            'history_truncated': max(0, len(history) - history_limit)}
