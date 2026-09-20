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

_ROTATION_FADING = re.compile(
    r'^(.+?) was leading but momentum has rolled over to weakening '
    r'\(1W ([+-]?[0-9]+(?:\.[0-9]+)?)%, 3M ([+-]?[0-9]+(?:\.[0-9]+)?)%; '
    r'mom ([+-]?[0-9]+(?:\.[0-9]+)?)\)\. A rotate-out / take-profit watch '
    r'— context only\.$'
)
_ROTATION_TURN_DOWN = re.compile(
    r"^(.+?) (ran|built) ([0-9]+(?:\.[0-9]+)?)% (off its 1-year low|of lead over the market) "
    r"and has now rolled over on confirmed sessions — this week ([+-]?[0-9]+(?:\.[0-9]+)?)% "
    r"vs the market's ([+-]?[0-9]+(?:\.[0-9]+)?)%/wk, ([0-9]{1,3})% of members rolling "
    r"with it( · carried by one name)?\. Context, not a sell list\.$"
)
_ROTATION_TURN_UP = re.compile(
    r"^(.+?) (fell|gave up) ([0-9]+(?:\.[0-9]+)?)% (from its 1-year high|of its lead over the market) "
    r"and has now turned up on confirmed sessions — this week ([+-]?[0-9]+(?:\.[0-9]+)?)% "
    r"vs the market's ([+-]?[0-9]+(?:\.[0-9]+)?)%/wk, ([0-9]{1,3})% of members turning "
    r"with it( · carried by one name)?\. Context, not a buy list\.$"
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

_THEME_RECO_CHANGE = re.compile(
    r'^Theme recommendation for (.+?) changed from ([A-Za-z]+) to ([A-Za-z]+) '
    r'\(score ([0-9]{1,3}), ([^)]+)\)'
    r'(?: — held ([0-9]+) consecutive sessions '
    r'\(constructive flips wait for a second session; risk flips fire immediately\))?\.$',
    re.IGNORECASE,
)
_THEME_DETERIORATING = re.compile(
    r'^(.+?) broke down into deteriorating — momentum and breadth weakening together\. '
    r'Recommendation now ([A-Za-z]+)\.$', re.IGNORECASE,
)
_THEME_TOPPING = re.compile(
    r'^(.+?) dropped from dominant to fading as of the ([0-9]{4}-[0-9]{2}-[0-9]{2}) close '
    r'— momentum cooling at a high\. Historically this read flags elevated pullback risk '
    r'over the next month, not a confirmed top — leaders inside the theme can keep running\. '
    r'Recommendation now ([A-Za-z]+)\.$', re.IGNORECASE,
)
_THEME_EMERGING = re.compile(
    r'^(.+?) entered the (?:emerging phase|EMERGING lifecycle) — accelerating relative strength '
    r'before it is extended \(score ([0-9]{1,3})\)'
    r'(?: — held ([0-9]+) consecutive sessions '
    r'\((?:constructive label shifts are debounced|constructive label shifts wait for a second session); '
    r'risk label shifts fire immediately\))?\.$', re.IGNORECASE,
)
_FOREX_RESIDUAL_HEADLINE = re.compile(
    r"^([A-Z]{3}/[A-Z]{3}): Unusual move the dollar and rates don't explain \((up|down)\)$"
)
_FOREX_RESIDUAL_DETAIL = re.compile(
    r'^([A-Z]{3}) moved beyond what the dollar \+ rates explain '
    r'\(shock z ([+-][0-9]+(?:\.[0-9]+)?)\) — possible intervention / flow / '
    r'geopolitics\. ([A-Z]{3}/[A-Z]{3}) ([0-9]+(?:\.[0-9]+)?)\.$'
)

_DEMAND_AHEAD = re.compile(
    r"^([a-z0-9_]+) \(([+-]?[0-9]+(?:\.[0-9]+)?)% YoY\) is running ahead of "
    r"([A-Z0-9.\-]+)'s analyst revisions — a forward-demand signal not yet fully in "
    r"the price\. Context for review; not a buy signal\.$"
)

_THEME_LEADERSHIP = re.compile(
    r'^(.+?) took the #1 theme rank \(score ([0-9]{1,3})\), displacing (.+?)'
    r'(?: — held #1 for ([0-9]+) consecutive sessions with a '
    r'([0-9]+(?:\.[0-9]+)?)-point margin over #2)?\.$', re.IGNORECASE,
)
_THEME_RECO_RANK = {'avoid': 0, 'trim': 1, 'hold': 2, 'accumulate': 3, 'enter': 4}


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


def _rotation_fading_brief(row: dict, detail: str, detail_zh: str,
                             age: int | None, brief: dict) -> dict | None:
    match = _ROTATION_FADING.fullmatch(detail)
    if row.get('source') != 'rotation' or row.get('type') != 'rotation_fading' or not match:
        return None
    subject, one_week, three_month, momentum = match.groups()
    age_limit = '' if age is None or age <= 2 else (
        f' This event is {age} days old; recheck the current quadrant.')
    age_limit_zh = '' if age is None or age <= 2 else (
        f' 该事件已过去 {age} 天；请复核当前象限。')
    brief.update({
        'status': 'supported', 'family': 'rotation.rotation_fading',
        'change': detail, 'change_zh': detail_zh,
        'implication': (
            f'{subject} moved from leadership into weakening momentum, with 1W '
            f'{one_week}%, 3M {three_month}% and momentum {momentum}; this is a '
            'rotate-out research watch.'),
        'implication_zh': (
            f'{subject} 从领先转入动量走弱；1周 {one_week}%，3月 {three_month}%，'
            f'动量 {momentum}。这是轮出研究观察。'),
        'limitation': (
            'This is context, not a take-profit instruction, sell list, calibrated '
            'probability or separately backtested timing signal. The return horizons '
            f'and quadrant are descriptive snapshots that can reverse.{age_limit}'),
        'limitation_zh': (
            '这只是背景，并非止盈指令、卖出清单、校准概率或经过单独回测的择时信号。'
            f'周期收益与象限只是可能反转的描述性快照。{age_limit_zh}'),
        'next_action': (
            f'Open the current rotation panel and verify {subject} still sits in weakening, '
            'momentum remains negative and its relative-performance profile has not recovered.'),
        'next_action_zh': (
            f'打开当前轮动面板，确认 {subject} 仍处于走弱、动量仍为负且相对表现尚未恢复。'),
        'next_action_label': 'Recheck rollover', 'next_action_label_zh': '复核走弱',
        'reassessment': (
            'Change the read if the quadrant leaves weakening, momentum recovers or '
            'relative performance resumes leadership.'),
        'reassessment_zh': '若象限退出走弱、动量恢复或相对表现重新领先，则改变判断。',
        'evidence_label': 'Open current rotation panel',
        'evidence_label_zh': '打开当前轮动面板',
    })
    return brief


def _rotation_turn_brief(row: dict, detail: str, detail_zh: str,
                          age: int | None, brief: dict) -> dict | None:
    type_ = str(row.get('type') or '')
    up = type_ == 'rotation_turn_up'
    if row.get('source') != 'rotation' or type_ not in {'rotation_turn_down', 'rotation_turn_up'}:
        return None
    match = (_ROTATION_TURN_UP if up else _ROTATION_TURN_DOWN).fullmatch(detail)
    if not match:
        return None
    subject, verb, magnitude, basis, one_week, market_week, breadth_text, concentration = match.groups()
    valid_basis = ((up and verb == 'fell' and basis == 'from its 1-year high') or
                   (up and verb == 'gave up' and basis == 'of its lead over the market') or
                   (not up and verb == 'ran' and basis == 'off its 1-year low') or
                   (not up and verb == 'built' and basis == 'of lead over the market'))
    if not valid_basis:
        return None
    breadth = int(breadth_text)
    leadership_path = verb in {'gave up', 'built'}
    path = 'leadership path' if leadership_path else 'price path'
    path_zh = '领先路径' if leadership_path else '价格路径'
    concentrated = bool(concentration)
    if concentrated:
        participation = (
            f' {breadth}% breadth is concentrated and carried by one name; member breadth '
            'is not independent confirmation.')
        participation_zh = (
            f' {breadth}% 的宽度较集中，且主要由单一成分股带动；成分股宽度并非独立确认。')
    else:
        participation = (
            f' {breadth}% member breadth is descriptive participation, not independent confirmation.')
        participation_zh = (
            f' {breadth}% 的成分股宽度是描述性参与度，并非独立确认。')
    age_limit = '' if age is None or age <= 2 else (
        f' This event is {age} days old; recheck the current turn state.')
    age_limit_zh = '' if age is None or age <= 2 else (
        f' 该事件已过去 {age} 天；请复核当前转向状态。')
    direction = 'up' if up else 'down'
    direction_zh = '上行' if up else '下行'
    verb_phrase = 'turned up' if up else 'rolled over'
    members_phrase = 'turning' if up else 'rolling'
    list_phrase = 'buy' if up else 'sell'
    relative = 'leads' if up else 'lags'
    brief.update({
        'status': 'supported', 'family': f'rotation.rotation_turn_{direction}',
        'change': detail, 'change_zh': detail_zh,
        'implication': (
            f'{subject} {verb_phrase} on confirmed sessions through its {path}; this week '
            f'{one_week}% versus the market {market_week}%/wk, with {breadth}% of members '
            f'{members_phrase} with it.'),
        'implication_zh': (
            f'{subject} 通过其{path_zh}连续确认转为{direction_zh}；本周 {one_week}%，市场 '
            f'{market_week}%/周，{breadth}% 成分股同步转向。'),
        'limitation': (
            f'Confirmed sessions establish a repeated state transition, not future return or '
            f'a {list_phrase} instruction. This is context, not a {list_phrase} list, calibrated '
            f'probability or separately backtested timing signal.{participation}{age_limit}'),
        'limitation_zh': (
            f'连续确认只表明状态反复出现，并不代表未来收益或{("买入" if up else "卖出")}指令。'
            f'这只是背景，不是{("买入" if up else "卖出")}清单、校准概率或经过单独回测的择时信号。'
            f'{participation_zh}{age_limit_zh}'),
        'next_action': (
            f'Open the current rotation panel and verify {subject} remains turned {direction}, '
            f'its weekly relative move still {relative} and member breadth remains near {breadth}%.'),
        'next_action_zh': (
            f'打开当前轮动面板，确认 {subject} 仍为{direction_zh}、本周相对表现继续'
            f'{("领先" if up else "落后")}且成分股宽度仍接近 {breadth}%。'),
        'next_action_label': f'Recheck turn {direction}',
        'next_action_label_zh': f'复核{direction_zh}转向',
        'reassessment': (
            f'Change the read if the turn state reverses, weekly relative performance no longer '
            f'{relative}, or member participation collapses.'),
        'reassessment_zh': (
            f'若转向状态反转、本周相对表现不再{("领先" if up else "落后")}或成分股参与度崩解，则改变判断。'),
        'evidence_label': 'Open current rotation panel',
        'evidence_label_zh': '打开当前轮动面板',
    })
    return brief


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

    residual_headline = _FOREX_RESIDUAL_HEADLINE.fullmatch(_plain(row.get('headline') or ''))
    residual_detail = _FOREX_RESIDUAL_DETAIL.fullmatch(detail)
    if source == 'forex' and type_ == 'residual_shock' and residual_headline and residual_detail:
        headline_pair, direction = residual_headline.groups()
        currency, z_text, detail_pair, price_text = residual_detail.groups()
        pair_asset = detail_pair.replace('/', '')
        z_value = float(z_text)
        expected_direction = 'up' if z_value > 0 else 'down' if z_value < 0 else ''
        pair_currencies = set(detail_pair.split('/'))
        if (headline_pair == detail_pair and pair_asset == str(row.get('asset') or '') and
                currency in pair_currencies and direction == expected_direction):
            age_limit = ''
            age_limit_zh = ''
            if age is None:
                age_limit = ' Event age is unavailable; current validity cannot be established.'
                age_limit_zh = ' 事件时间未知，无法确认当前有效性。'
            elif age > 2:
                age_limit = f' This event is {age} days old; recheck the current residual before using it.'
                age_limit_zh = f' 该事件已过去 {age} 天；使用前请复核当前残差。'
            brief.update({
                'status': 'supported', 'family': 'forex.residual_shock',
                'change': detail, 'change_zh': detail_zh,
                'implication': (
                    f'The source dollar/rates model reports a {z_text} z-score residual in '
                    f'{detail_pair} at {price_text}, flagging an unexplained FX move that '
                    'requires attribution.'),
                'implication_zh': (
                    f'来源的美元/利率模型报告 {detail_pair} 在 {price_text} 出现 {z_text} 的 z 分数残差，'
                    '提示一项需要进一步归因的异常外汇波动。'),
                'limitation': (
                    'A model residual says the named factors did not explain the observed move; '
                    'it does not identify intervention, flows or geopolitics as the cause. The '
                    'z-score is not a probability or return forecast, and this family is documented '
                    f'but not separately backtested as a timing signal.{age_limit}'),
                'limitation_zh': (
                    '模型残差只表示所列因素未能解释该波动；它不能把原因确定为干预、资金流或地缘政治。'
                    'z 分数不是概率或收益预测，且该信号族虽有记录，但未作为择时信号单独回测。'
                    f'{age_limit_zh}'),
                'next_action': (
                    f'Open the current FX timeline and verify the {detail_pair} residual, pair '
                    f'price, broad-dollar and rates inputs, and source clocks before investigating '
                    f'local {currency} catalysts or changing exposure.'),
                'next_action_zh': (
                    f'打开当前外汇时间线，核对 {detail_pair} 残差、汇率、广义美元与利率输入及来源时间，'
                    f'再调查 {currency} 的本地催化因素或调整敞口。'),
                'next_action_label': 'Investigate FX residual',
                'next_action_label_zh': '调查外汇残差',
                'reassessment': (
                    'Change the read if the residual normalizes, the dollar/rates model explains '
                    'the move, or newer source evidence identifies the driver.'),
                'reassessment_zh': (
                    '若残差恢复正常、美元/利率模型可以解释该波动，或更新的来源证据识别出驱动因素，则改变判断。'),
                'evidence_label': 'Open current FX timeline',
                'evidence_label_zh': '打开当前外汇时间线',
            })
            return brief

    demand = _DEMAND_AHEAD.fullmatch(detail)
    if source == 'demand' and type_ == 'demand_ahead' and demand:
        measure, growth_text, ticker = demand.groups()
        if ticker == str(row.get('asset') or ''):
            age_limit = ''
            age_limit_zh = ''
            if age is None:
                age_limit = ' Event age is unavailable; current validity cannot be established.'
                age_limit_zh = ' 事件时间未知，无法确认当前有效性。'
            elif age > 2:
                age_limit = f' This event is {age} days old; recheck the current demand and revisions.'
                age_limit_zh = f' 该事件已过去 {age} 天；请复核当前需求与分析师调整。'
            measure_label = measure.replace('_', ' ')
            brief.update({
                'status': 'supported', 'family': 'demand.demand_ahead',
                'change': detail, 'change_zh': detail_zh,
                'implication': (
                    f'The source reports {measure_label} demand growing {growth_text}% YoY '
                    f'and running ahead of {ticker} analyst revisions, creating a possible '
                    'expectations gap to investigate.'),
                'implication_zh': (
                    f'来源报告 {measure_label} 需求同比增长 {growth_text}%，并领先于 {ticker} '
                    '分析师调整，形成一个值得调查的潜在预期差。'),
                'limitation': (
                    'This source-described demand variant is not proof the stock is underpriced, '
                    'a buy signal, a calibrated probability, or an independent confirmation of '
                    'future returns. Analyst revisions can lag for procedural reasons, and this '
                    f'family is documented but not separately backtested as a timing signal.{age_limit}'),
                'limitation_zh': (
                    '该来源描述的需求变体不能证明股票被低估，也不是买入信号、校准概率或未来收益的'
                    '独立确认。分析师调整可能因流程原因滞后，且该信号族虽有记录，但未作为择时信号'
                    f'单独回测。{age_limit_zh}'),
                'next_action': (
                    f'Open the current demand timeline and verify the {measure_label} as-of date, '
                    f'its {growth_text}% YoY reading, {ticker} revision direction, and whether '
                    'price expectations have already moved.'),
                'next_action_zh': (
                    f'打开当前需求时间线，核对 {measure_label} 的观测日期、{growth_text}% 同比读数、'
                    f'{ticker} 分析师调整方向，以及价格预期是否已经变化。'),
                'next_action_label': 'Recheck demand lead',
                'next_action_label_zh': '复核需求领先',
                'reassessment': (
                    'Change the read if the current demand measure decelerates, analyst revisions '
                    'catch up or reverse, or the price already discounts the change.'),
                'reassessment_zh': (
                    '若当前需求指标减速、分析师调整追上或反转，或价格已经计入该变化，则改变判断。'),
                'evidence_label': 'Open current demand timeline',
                'evidence_label_zh': '打开当前需求时间线',
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

    rotation_fading = _rotation_fading_brief(row, detail, detail_zh, age, brief)
    if rotation_fading is not None:
        return rotation_fading
    rotation_turn = _rotation_turn_brief(row, detail, detail_zh, age, brief)
    if rotation_turn is not None:
        return rotation_turn

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

    reco = _THEME_RECO_CHANGE.fullmatch(detail)
    if source == 'themes' and type_ == 'reco_change' and reco:
        subject, old_reco, new_reco, score_text, label, held_text = reco.groups()
        score = int(score_text)
        old_key, new_key = old_reco.lower(), new_reco.lower()
        direction = 'upgrade' if _THEME_RECO_RANK.get(new_key, 2) > _THEME_RECO_RANK.get(old_key, 2) else 'downgrade'
        held = int(held_text) if held_text else None
        confirmation = f' The constructive change was confirmed for {held} sessions.' if held else ''
        confirmation_zh = f' 该进取方向变化已连续 {held} 个交易日确认。' if held else ''
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck the current recommendation.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前建议。'
        brief.update({
            'status': 'supported', 'family': 'themes.reco_change',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} moved from {old_reco} to {new_reco} at model score {score} '
                f'with a {label} lifecycle label.{confirmation}'),
            'implication_zh': (
                f'{subject} 的模型建议由{old_reco}变为{new_reco}，模型评分 {score}，'
                f'生命周期标签为{label}。{confirmation_zh}'),
            'limitation': (
                f'The recommendation is a model state, not a trade instruction, position size, '
                f'probability or expected return. {score} is a model score, not a probability. '
                'This family is documented, not separately backtested as a timing signal; '
                'constructive changes are delayed for confirmation while risk-direction changes '
                f'fire immediately. Re-fired events do not prove persistence.{age_limit}'),
            'limitation_zh': (
                f'该建议是模型状态，并非交易指令、仓位、概率或预期收益。{score} 是模型评分，'
                '不是概率。该信号族有据可查，但未作为择时信号单独回测；进取方向变化需确认，'
                f'风险方向变化即时触发。重复触发不能证明状态持续。{age_limit_zh}'),
            'next_action': (
                f'Open the current theme page and verify {subject} still shows {new_reco}, '
                f'score {score} and the {label} lifecycle before changing exposure.'),
            'next_action_zh': f'打开当前主题页面，确认 {subject} 仍显示{new_reco}、评分 {score} 与{label}生命周期，再调整敞口。',
            'next_action_label': 'Recheck recommendation',
            'next_action_label_zh': '复核建议',
            'reassessment': (
                f'Change the read if the current recommendation no longer shows {new_reco}, '
                'the lifecycle changes, or the score materially reverses.'),
            'reassessment_zh': f'若当前建议不再为{new_reco}、生命周期改变或评分明显反转，则改变判断。',
            'evidence_label': 'Open current theme page',
            'evidence_label_zh': '打开当前主题页面',
        })
        return brief

    deteriorating = _THEME_DETERIORATING.fullmatch(detail)
    if source == 'themes' and type_ == 'theme_deteriorating' and deteriorating:
        subject, recommendation = deteriorating.groups()
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck the current state.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前状态。'
        brief.update({
            'status': 'supported', 'family': 'themes.theme_deteriorating',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} entered the deteriorating lifecycle with momentum and breadth '
                f'weakening together; the source recommendation is now {recommendation}.'),
            'implication_zh': f'{subject} 进入走弱生命周期，动量与宽度同步转弱；当前来源建议为{recommendation}。',
            'limitation': (
                'The source treats deterioration as an immediate risk-direction event, but '
                'the page payload supplies no calibrated probability, hit rate or individual-name '
                'sell list. This family is documented, not separately backtested as a timing '
                f'signal; repeated firings do not prove persistence.{age_limit}'),
            'limitation_zh': (
                '来源将走弱视为即时风险方向事件，但页面载荷未提供校准概率、命中率或个股卖出清单。'
                f'该信号族有据可查，但未作为择时信号单独回测；重复触发不能证明状态持续。{age_limit_zh}'),
            'next_action': (
                f'Open the current theme page and verify both momentum and breadth still weaken '
                f'together and the recommendation remains {recommendation}.'),
            'next_action_zh': f'打开当前主题页面，确认动量与宽度仍同步走弱，且建议仍为{recommendation}。',
            'next_action_label': 'Recheck deterioration',
            'next_action_label_zh': '复核走弱',
            'reassessment': (
                'Change the read if momentum or breadth recovers, the lifecycle exits '
                'deteriorating, or the recommendation improves.'),
            'reassessment_zh': '若动量或宽度恢复、生命周期退出走弱，或建议改善，则改变判断。',
            'evidence_label': 'Open current theme page',
            'evidence_label_zh': '打开当前主题页面',
        })
        return brief

    topping = _THEME_TOPPING.fullmatch(detail)
    if source == 'themes' and type_ == 'theme_topping' and topping:
        subject, asof_date, recommendation = topping.groups()
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck current momentum.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前动量。'
        brief.update({
            'status': 'supported', 'family': 'themes.theme_topping',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} moved from dominant to fading at the {asof_date} close. The source '
                'frames this as elevated basket-level pullback risk over roughly the next month.'),
            'implication_zh': f'{subject} 在 {asof_date} 收盘时由主导转入退潮；来源将其视为未来约一个月篮子层面回撤风险上升。',
            'limitation': (
                f'This is not a confirmed top, calibrated probability or claim that every leader '
                f'inside the theme must fall; leaders can keep running. Recommendation {recommendation} '
                f'is a model state, not an instruction or position size.{age_limit}'),
            'limitation_zh': (
                f'这并非确认见顶、校准概率，也不表示主题内所有领涨股都会下跌；领涨股仍可能续涨。'
                f'{recommendation} 是模型建议状态，并非交易指令或仓位。{age_limit_zh}'),
            'next_action': (
                f'Open the current theme page and verify {subject} remains fading, momentum is '
                f'still cooling and the recommendation remains {recommendation}.'),
            'next_action_zh': f'打开当前主题页面，确认 {subject} 仍处于退潮、动量继续降温且建议仍为{recommendation}。',
            'next_action_label': 'Recheck pullback risk',
            'next_action_label_zh': '复核回撤风险',
            'reassessment': (
                'Change the read if the theme returns to dominant/leading, momentum reaccelerates '
                'or the recommendation improves.'),
            'reassessment_zh': '若主题恢复主导/领先、动量重新加速或建议改善，则改变判断。',
            'evidence_label': 'Open current theme page',
            'evidence_label_zh': '打开当前主题页面',
        })
        return brief

    emerging = _THEME_EMERGING.fullmatch(detail)
    if source == 'themes' and type_ == 'theme_emerging' and emerging:
        subject, score_text, held_text = emerging.groups()
        score = int(score_text)
        held = int(held_text) if held_text else None
        held_copy = f' and held {held} consecutive sessions' if held else ''
        held_copy_zh = f'，并连续 {held} 个交易日确认' if held else ''
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck the current lifecycle.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前生命周期。'
        brief.update({
            'status': 'supported', 'family': 'themes.theme_emerging',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} entered the emerging lifecycle at score {score}, with relative '
                f'strength accelerating before extension{held_copy}.'),
            'implication_zh': f'{subject} 以评分 {score} 进入新兴生命周期，相对强度在过度延展前加速{held_copy_zh}。',
            'limitation': (
                f'The confirmation stabilizes the label; it does not validate future returns. '
                f'{score} is a model score, not a probability, and this is not a buy list or '
                f'separately backtested timing signal.{age_limit}'),
            'limitation_zh': (
                f'连续确认仅稳定标签，并不验证未来收益。{score} 是模型评分，不是概率；这也不是买入清单'
                f'或经过单独回测的择时信号。{age_limit_zh}'),
            'next_action': (
                f'Open the current theme page and verify {subject} remains emerging, relative '
                'strength still accelerates and the theme is not already extended.'),
            'next_action_zh': f'打开当前主题页面，确认 {subject} 仍处于新兴、相对强度继续加速且尚未过度延展。',
            'next_action_label': 'Recheck emergence',
            'next_action_label_zh': '复核新兴状态',
            'reassessment': (
                'Change the read if the lifecycle leaves emerging, relative strength stalls '
                'or extension becomes excessive.'),
            'reassessment_zh': '若生命周期退出新兴、相对强度停滞或延展过度，则改变判断。',
            'evidence_label': 'Open current theme page',
            'evidence_label_zh': '打开当前主题页面',
        })
        return brief

    leadership = _THEME_LEADERSHIP.fullmatch(detail)
    if source == 'themes' and type_ == 'leadership_rotation' and leadership:
        subject, score_text, old_leader, held_text, margin_text = leadership.groups()
        score = int(score_text)
        held = int(held_text) if held_text else None
        margin = float(margin_text) if margin_text else None
        confirmation = ''
        confirmation_zh = ''
        if held is not None and margin is not None:
            margin_label = f'{margin:g}'
            confirmation = f' The lead held for {held} sessions with a {margin_label}-point margin over #2.'
            confirmation_zh = f' 该领先已持续 {held} 个交易日，并领先第二名 {margin_label} 分。'
        age_limit = '' if age is None or age <= 2 else f' This event is {age} days old; recheck the current leaderboard.'
        age_limit_zh = '' if age is None or age <= 2 else f' 该事件已过去 {age} 天；请复核当前排行榜。'
        brief.update({
            'status': 'supported', 'family': 'themes.leadership_rotation',
            'change': detail, 'change_zh': detail_zh,
            'implication': (
                f'{subject} became the #1 theme at score {score}, displacing {old_leader}.'
                f'{confirmation}'),
            'implication_zh': f'{subject} 以评分 {score} 升至主题第一，取代 {old_leader}。{confirmation_zh}',
            'limitation': (
                f'Theme rank and score are descriptive model outputs—not expected return, '
                f'probability, a recommendation or proof of durable leadership. {score} is a '
                f'model score, not expected return; confirmation filters rank noise but does '
                f'not establish forward edge.{age_limit}'),
            'limitation_zh': (
                f'主题排名与评分是描述性模型输出，并非预期收益、概率、建议或持久领先的证明。'
                f'{score} 是模型评分，不是预期收益；连续确认只过滤排名噪声，并不建立前瞻优势。{age_limit_zh}'),
            'next_action': (
                f'Open the current theme leaderboard and verify {subject} is still #1, its '
                'margin remains decisive and the underlying score leadership persists.'),
            'next_action_zh': f'打开当前主题排行榜，确认 {subject} 仍为第一、领先幅度仍具决定性且评分优势持续。',
            'next_action_label': 'Recheck leadership',
            'next_action_label_zh': '复核主题领先',
            'reassessment': (
                'Change the read if another theme takes #1, the lead margin falls inside '
                'normal score wobble or the score leadership reverses.'),
            'reassessment_zh': '若其他主题升至第一、领先幅度回落到正常评分波动内或评分优势反转，则改变判断。',
            'evidence_label': 'Open current theme leaderboard',
            'evidence_label_zh': '打开当前主题排行榜',
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
