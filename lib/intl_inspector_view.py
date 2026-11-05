"""Detached Inspector presentation from already disclosed Overview output.

This consumer grants no source, calendar or disclosure authority and performs no
financial calculation. Its caller supplies the trusted owner projection and
already resolved public destinations. All returned objects are detached.
"""
from copy import deepcopy
from math import isfinite
import re

INSPECTOR_COPY = {'check_missing_return_evidence': {'en': 'Research next: identify which return evidence is '
                                         'unavailable.',
                                   'zh': '下一步研究：确认哪些回报证据尚未提供。'},
 'clocks_not_supplied': {'en': 'Publication, ingestion and generation clocks were not supplied.',
                         'zh': '未提供发布、接收及生成时间。'},
 'decomposition_unavailable': {'en': 'A common disclosed calculation window is unavailable for the '
                                     'return components.',
                               'zh': '回报组成部分缺少已披露的共同计算区间。'},
 'fx_negative_contribution': {'en': 'The reported FX contribution is negative.',
                              'zh': '已披露的汇率贡献为负。'},
 'fx_positive_contribution': {'en': 'The reported FX contribution is positive.',
                              'zh': '已披露的汇率贡献为正。'},
 'fx_zero_contribution': {'en': 'The reported FX contribution is zero.', 'zh': '已披露的汇率贡献为零。'},
 'inspect_calculation_window': {'en': 'Research next: inspect the calculation window and '
                                      'contributing observations.',
                                'zh': '下一步研究：检查计算区间及其所用观测。'},
 'price_only_boundary': {'en': 'These are price-only returns, not total-return or '
                               'economic-exposure evidence.',
                         'zh': '这些是价格回报，并非总回报或经济敞口证据。'},
 'reported_same_window': {'en': 'Local return, USD return and FX contribution are reported for the '
                                'same calculation window.',
                          'zh': '本币回报、美元回报及汇率贡献采用相同的计算区间。'},
 'return_failed': {'en': 'This return could not be calculated.', 'zh': '此项回报暂时无法计算。'},
 'return_missing': {'en': 'This return is marked missing.', 'zh': '此项回报被标记为缺失。'},
 'return_not_disclosed': {'en': 'This return is not disclosed for the selected context.',
                          'zh': '当前所选条件下未披露此项回报。'},
 'return_stale': {'en': 'This return data is out of date.', 'zh': '此项回报数据已过时。'},
 'return_unknown': {'en': 'Evidence is insufficient for this return.', 'zh': '此项回报的依据尚不足。'},
 'return_unsupported': {'en': 'This return is marked unsupported.', 'zh': '此项回报被标记为不支持。'},
 'selected_return_negative': {'en': 'The selected-period return is negative.', 'zh': '所选期间回报为负。'},
 'selected_return_positive': {'en': 'The selected-period return is positive.', 'zh': '所选期间回报为正。'},
 'selected_return_zero': {'en': 'The selected-period return is zero.', 'zh': '所选期间回报为零。'}}

_LEGS = ('local', 'usd', 'fx_contribution')
_CONTEXT = {'horizon', 'currency_basis', 'return_basis', 'source_reference'}
_QUALITIES = {'qualified', 'stale', 'missing', 'denied', 'failed', 'unsupported', 'unknown'}
_OVERVIEW = {'context', 'configured_count', 'eligible_count', 'ranking_count', 'ranking_status',
             'ranking_reason', 'focus_ids', 'rows', 'summary'}
_IDENTITY = {'slot', 'market_id', 'name_en', 'name_zh'}
_REASON_KEYS = {'denied':'return_not_disclosed', 'stale':'return_stale', 'missing':'return_missing',
                'failed':'return_failed', 'unsupported':'return_unsupported', 'unknown':'return_unknown'}


def _reject():
    raise ValueError('INVALID_INSPECTOR_INPUT')


def _plain(value):
    if value is None or type(value) in (str, int):
        return
    if type(value) is float and isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _plain(item)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _plain(item)
        return
    _reject()


def _closed(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _reject()


def _text(value, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or any(ord(c)<32 or 127<=ord(c)<=159 for c in value):
        _reject()


def _context(context, overview=False):
    _closed(context, _CONTEXT | ({'source_reference_reason'} if overview else set()))
    _text(context['horizon'])
    _text(context['source_reference'], nullable=True)
    if context['currency_basis'] not in ('local','usd_unhedged') or context['return_basis'] != 'price':
        _reject()
    if overview:
        _text(context['source_reference_reason'], nullable=True)


def _window(window):
    if window is None:
        return
    _closed(window, {'start','end','calendar_policy','endpoint_observations'})
    for key in ('start','end','calendar_policy'):
        _text(window[key])
    _closed(window['endpoint_observations'], {'price_start','price_end','fx_start','fx_end'})
    for stamp in window['endpoint_observations'].values():
        _text(stamp, nullable=True)


def _metric(metric, unit):
    if type(metric) is not dict or set(metric) not in ({'value','unit','quality','reason'},
                                                     {'value','unit','quality','reason','window'}):
        _reject()
    if metric['unit'] != unit or type(metric['quality']) is not str or metric['quality'] not in _QUALITIES:
        _reject()
    _text(metric['reason'], nullable=True)
    _window(metric.get('window'))
    value = metric['value']
    if metric['quality'] == 'qualified':
        if type(value) not in (int,float) or metric.get('window') is None or metric['reason'] is not None:
            _reject()
    elif value is not None:
        _reject()


def _validate(overview, context, selected_market, deeper_links):
    try:
        for value in (overview,context,selected_market,deeper_links):
            _plain(value)
    except RecursionError:
        _reject()
    _closed(overview, _OVERVIEW)
    _context(context)
    _context(overview['context'], overview=True)
    _text(selected_market)
    for key in ('configured_count','eligible_count','ranking_count'):
        if type(overview[key]) is not int or overview[key] < 0:
            _reject()
    if overview['ranking_status'] not in ('available','unavailable'):
        _reject()
    _text(overview['ranking_reason'], nullable=True)
    if type(overview['rows']) is not list or type(overview['focus_ids']) is not list:
        _reject()
    if overview['configured_count'] != len(overview['rows']):
        _reject()
    summary = overview['summary']
    _closed(summary, {'kind','highest_market_id','lowest_market_id','positive_count',
                      'fx_detracted_count','fx_eligible_count','reason'})
    if summary['kind'] not in ('highest_lowest_returns','unavailable'):
        _reject()
    for key in ('highest_market_id','lowest_market_id','reason'):
        _text(summary[key], nullable=True)
    for key in ('positive_count','fx_detracted_count','fx_eligible_count'):
        if summary[key] is not None and (type(summary[key]) is not int or summary[key] < 0):
            _reject()
    ids, slots = set(), set()
    for row in overview['rows']:
        if type(row) is not dict:
            _reject()
        if set(row) == {'slot','quality','reason'}:
            if row['quality'] != 'denied' or row['reason'] != 'metadata_denied':
                _reject()
        else:
            unknown = set(row) == _IDENTITY | {'quality','reason','metric'}
            if not unknown:
                _closed(row, _IDENTITY | {'index_id','index_label','metric',*_LEGS})
                _text(row['index_id']); _text(row['index_label'])
                for leg in (*_LEGS, 'metric'):
                    _closed(row[leg], {'value','unit','quality','reason','window'})
                    _metric(row[leg], 'percentage_points' if leg=='fx_contribution' else 'percent')
                selected = 'local' if overview['context']['currency_basis']=='local' else 'usd'
                if row['metric'] != row[selected]:
                    _reject()
            elif row['quality'] != 'unknown' or type(row['metric']) is not dict or row['metric'].get('quality') != 'unknown':
                _reject()
            else:
                _text(row['reason'])
                _closed(row['metric'], {'value','unit','quality','reason'})
                if row['metric']['reason'] != row['reason']:
                    _reject()
            for key in ('market_id','name_en','name_zh'):
                _text(row[key])
            _metric(row['metric'], 'percent')
            if row['market_id'] in ids:
                _reject()
            ids.add(row['market_id'])
        if type(row['slot']) is not int or row['slot'] < 0 or row['slot'] in slots:
            _reject()
        slots.add(row['slot'])
    for market in overview['focus_ids']:
        _text(market)
        if market not in ids:
            _reject()
    if len(set(overview['focus_ids'])) != len(overview['focus_ids']):
        _reject()
    if type(deeper_links) is not list:
        _reject()
    tool_keys = set()
    for link in deeper_links:
        _closed(link, {'market_id','tool_key','label_en','label_zh','route_state','target'})
        for key in ('market_id','tool_key','label_en','label_zh'):
            _text(link[key])
        if link['route_state'] != 'available' or link['tool_key'] in tool_keys:
            _reject()
        tool_keys.add(link['tool_key'])
        target=link['target']
        _closed(target, {'page_id','route','region_id'})
        if target['page_id']=='macro:intl':
            if target['route']!='/intl.html' or type(target['region_id']) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_:-]*',target['region_id']):
                _reject()
        elif target['page_id']=='macro:intl_stocks':
            if target['route']!='/intl_stocks.html' or target['region_id'] is not None:
                _reject()
        else:
            _reject()


def _copy_key(key):
    return {'key':key, 'params':{}}


def _withheld(leg):
    return {'value':None, 'unit':'percentage_points' if leg=='fx_contribution' else 'percent',
            'quality':'unknown','reason':'not_disclosed_by_overview','window':None}


def build_inspector_view(overview, *, selected_market, context, deeper_links=None):
    """Project a single disclosed market, without inferring missing evidence.

    Malformed inputs raise ValueError. A valid but mismatched context or absent
    selection returns the same nonidentifying empty shape. The source reference
    is disclosed only when this particular market has a full owner row.
    """
    links=[] if deeper_links is None else deeper_links
    _validate(overview,context,selected_market,links)
    output={'status':'unavailable','reason':'selected_market_unavailable',
            'context':{**context, 'source_reference':None,
                       'source_reference_reason':'not_disclosed_for_selected_market'},
            'market':None,'metrics':None,
            'interpretation':{'selected_sign':'unavailable','fx_effect':'unavailable','decomposition':'unavailable'},
            'supports':[],'limits':[],'research_prompts':[],'evidence':[],'deeper_links':[]}
    if any(context[key] != overview['context'][key] for key in _CONTEXT):
        output['reason']='context_mismatch'
        return output
    row=next((row for row in overview['rows'] if row.get('market_id')==selected_market),None)
    if row is None:
        return output
    output['market']={key:deepcopy(row.get(key)) for key in ('market_id','name_en','name_zh','index_id','index_label')}
    if 'index_id' in row:
        output['context']['source_reference']=overview['context']['source_reference']
        output['context']['source_reference_reason']=overview['context']['source_reference_reason']
    metrics={leg:deepcopy(row[leg]) if leg in row else _withheld(leg) for leg in _LEGS}
    metrics['selected']=deepcopy(row['metric'])
    metrics['selected_leg']='local' if context['currency_basis']=='local' else 'usd'
    output['metrics']=metrics
    complete=all(metrics[leg]['quality']=='qualified' for leg in (*_LEGS,'selected'))
    output['status']='available' if complete else 'partial'
    output['reason']=None if complete else 'incomplete_return_evidence'
    if metrics['selected']['quality']=='qualified':
        value=metrics['selected']['value']
        sign='positive' if value>0 else 'negative' if value<0 else 'zero'
        output['interpretation']['selected_sign']=sign
        output['supports'].append(_copy_key('selected_return_'+sign))
    windows=[metrics[leg].get('window') for leg in _LEGS]
    common=complete and all(windows) and all(
        tuple(w[k] for k in ('start','end','calendar_policy')) == tuple(windows[0][k] for k in ('start','end','calendar_policy'))
        for w in windows[1:])
    if common:
        value=metrics['fx_contribution']['value']
        effect='positive_contribution' if value>0 else 'negative_contribution' if value<0 else 'zero_contribution'
        output['interpretation'].update(fx_effect=effect,decomposition='reported_same_window')
        output['supports'].extend([_copy_key('reported_same_window'),_copy_key('fx_'+effect)])
    limit_keys=[]
    for leg in (*_LEGS,'selected'):
        quality=metrics[leg]['quality']
        if quality!='qualified' and _REASON_KEYS[quality] not in limit_keys:
            limit_keys.append(_REASON_KEYS[quality])
    if not common:
        limit_keys.append('decomposition_unavailable')
    limit_keys.extend(['clocks_not_supplied','price_only_boundary'])
    output['limits']=[_copy_key(key) for key in limit_keys]
    output['research_prompts']=[_copy_key('inspect_calculation_window' if complete else 'check_missing_return_evidence')]
    for leg in _LEGS:
        metric=metrics[leg]; window=metric.get('window')
        output['evidence'].append({'field_id':leg,'metric':deepcopy(metric),
            'calculation_window':{k:window[k] for k in ('start','end','calendar_policy')} if window else None,
            'endpoint_observations':deepcopy(window['endpoint_observations']) if window else None,
            'clocks':dict.fromkeys(('observation','publication','ingestion','generation')),
            'clock_reason':'not_supplied_by_overview'})
    output['deeper_links']=deepcopy([link for link in links if link['market_id']==selected_market])
    return output
