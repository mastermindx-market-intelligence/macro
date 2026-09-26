"""Fed policy path — the market-implied rate path vs the FOMC dot-plot.

ADDITIVE / leaf module — imports nothing from the scoring core, and nothing in the
scoring path imports it. It assembles a DISPLAY block (bonds.html + the latest.json
LLM-context vector) from three free, keyless feeds:

  • the FOMC dot-plot median (FRED FEDTARMD) — the Fed's own projected path,
  • the source-reported target range (FRED DFEDTARU/DFEDTARL) — where policy is set today,
  • the ZQ/SR3 futures-implied path (collectors/rate_futures.py) — separately labeled
    EFFR and SOFR interpolated relative horizons,

plus the curve primitives already in the frame (near-term forward spread, the
term-premium-adjusted slope, the us2y−funds rate-expectations proxy).

DISCIPLINE — display / context ONLY. The implied path LEVEL is a market PRICE, not a
forecast edge, and a repricing observation is not by itself an identified
policy shock or a trading edge. There is therefore NO scored leg and NO MRS entry — this only
enlarges the facts the read can cite. See research/DATA_SIGNAL_EXPANSION_2026.md #2.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

_QUARTER = 0.25  # one 25bp move


def _cfg() -> dict:
    return config.load().get("rate_futures", {}) or {}


def _r(v, nd: int = 2):
    """Finite scalar only; malformed optional values are explicit missingness."""
    if isinstance(v, (bool, np.bool_)) or v is None:
        return None
    try:
        value = float(v)
        return round(value, nd) if np.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _date_label(value) -> str | None:
    """Daily labels only: never infer a release instant from a date."""
    if value is None or isinstance(value, (bool, int, float, np.number)):
        return None
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tz is not None or stamp != stamp.normalize():
            return None
        return stamp.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _path_evidence(row, source_asof, analysis_day, horizons, family, status=None):
    clean = {f"m{h}": _r(row.get(f"m{h}"), 8) for h in horizons} if isinstance(row, dict) else {}
    present = any(v is not None for v in clean.values())
    day = _date_label(source_asof)
    age = ((pd.Timestamp(analysis_day) - pd.Timestamp(day)).days
           if day is not None and analysis_day is not None else None)
    if status not in ('read_unavailable', 'invalid_source'):
        status = ('missing' if not present else
                  'observation_date_unknown' if day is None else
                  'analysis_date_unknown' if analysis_day is None else
                  'after_analysis_date' if age < 0 else
                  'same_date_context' if age == 0 else 'stale_dated_context')
    return {
        "contract_family": family, "underlying": "EFFR" if family == "ZQ" else "SOFR",
        "aggregation": "calendar_month_average" if family == "ZQ" else "quarterly_compounded",
        "representation": "interpolated_relative_horizons_not_individual_contracts",
        "source_asof": day, "analysis_asof": analysis_day, "age_calendar_days": age,
        "status": status, "last_observed_path": clean if present else None,
        "usable_as_same_date_context": present and status == 'same_date_context',
        "actual_contract_ids": None, "target_period_identity_qualified": False,
        "available_at": None, "historical_availability_qualified": False,
    }


def _last(s: pd.Series | None) -> float | None:
    if s is None:
        return None
    for value in reversed(s.tolist()):
        number = _r(value, 8)
        if number is not None:
            return number
    return None


def _interp_horizon(path_row: dict, horizons: list[int], h: float) -> float | None:
    """Interpolate between observed horizons only; never silently extrapolate."""
    wanted = _r(h, 8)
    if wanted is None or not isinstance(path_row, dict):
        return None
    pts = sorted((float(hm), value) for hm in set(horizons)
                 if (value := _r(path_row.get(f"m{hm}"), 8)) is not None)
    if not pts or wanted < pts[0][0] or wanted > pts[-1][0]:
        return None
    for x, y in pts:
        if x == wanted:
            return y
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 < wanted < x1:
            return y0 + (y1 - y0) * (wanted - x0) / (x1 - x0)
    return None


def _dots_by_year(dot_series: pd.Series | None, this_year: int) -> list[dict]:
    """Retain finite projection-year values; publication time remains unqualified."""
    if (not isinstance(dot_series, pd.Series) or
            not isinstance(dot_series.index, pd.DatetimeIndex) or dot_series.index.hasnans
            or not dot_series.index.is_unique or dot_series.index.tz is not None):
        return []
    by_year: dict[int, float] = {}
    for ts, value in dot_series.sort_index().items():
        value = _r(value, 8)
        if value is not None:
            by_year[pd.Timestamp(ts).year] = value
    return [{"year": y, "median": round(by_year[y], 3)}
            for y in sorted(by_year) if y >= this_year]


def _lean(gap_bp: float | None) -> tuple[str, str]:
    if gap_bp is None:
        return ("—", "—")
    if abs(gap_bp) < 13:  # < ~half a 25bp move = essentially aligned
        return ("market ≈ the Fed", "市场与美联储基本一致")
    if gap_bp < 0:        # market prices a LOWER rate than the Fed projects
        return ("market more dovish than the Fed", "市场比美联储更鸽派")
    return ("market more hawkish than the Fed", "市场比美联储更鹰派")


def compute(*, asof, policy_rate, target_low, target_high, dot_series,
            zq_path_row, sofr_path_row, zq_front_implied,
            ntfs, curve_tp_adj, rate_exp_proxy, cfg=None,
            zq_path_asof=None, sofr_path_asof=None, policy_asof=None,
            path_status=None, front_asof=None,
            target_low_asof=None, target_high_asof=None) -> dict | None:
    """Assemble explicitly dated context; preserve old keys without false basis joins.

    Undated inputs remain descriptive evidence, never same-date comparisons.
    SOFR is separate from EFFR. Relative mN points are not individually identified
    contracts and do not identify meeting probabilities or a causal policy shock.
    """
    cfg = cfg if cfg is not None else _cfg()
    horizons = list(cfg.get("horizons_m", [1, 3, 6, 12]))
    if (not horizons or len(horizons) > 24 or any(isinstance(h, bool) or
            not isinstance(h, int) or h <= 0 or h > 120 for h in horizons)
            or len(set(horizons)) != len(horizons)):
        raise ValueError("horizons_m must contain unique positive integer months")
    analysis_day = _date_label(asof)
    status = path_status if isinstance(path_status, dict) else {}
    zq = _path_evidence(zq_path_row, zq_path_asof, analysis_day, horizons, 'ZQ', status.get('zq'))
    sofr = _path_evidence(sofr_path_row, sofr_path_asof, analysis_day, horizons, 'SR3', status.get('sofr'))
    policy_rate = _r(policy_rate, 8)
    target_low, target_high = _r(target_low, 8), _r(target_high, 8)
    low_day, high_day = _date_label(target_low_asof), _date_label(target_high_asof)
    range_status = ('missing_bounds' if target_low is None or target_high is None else
                    'invalid_bounds' if target_low > target_high else
                    'dates_unknown' if low_day is None or high_day is None else
                    'mixed_dates' if low_day != high_day else
                    'analysis_date_unknown' if analysis_day is None else
                    'after_analysis_date' if low_day > analysis_day else
                    'same_date_frame_bounds' if low_day == analysis_day else
                    'older_matched_frame_bounds')
    tmid = ((target_low + target_high) / 2 if range_status in
            ('same_date_frame_bounds', 'older_matched_frame_bounds') else None)
    range_evidence = {'lower_value': target_low, 'upper_value': target_high,
                      'lower_asof': low_day, 'upper_asof': high_day,
                      'status': range_status, 'observation_origin': 'frame_aligned_unverified',
                      'historical_availability_qualified': False}
    pol = policy_rate if policy_rate is not None else tmid
    policy_day = _date_label(policy_asof)
    reference_current = policy_rate is not None and policy_day == analysis_day and analysis_day is not None
    path = zq['last_observed_path'] if zq['usable_as_same_date_context'] else None
    implied = {'now': _r(pol)}
    if path:
        implied.update({key: _r(value) for key, value in path.items()})
    path_src = 'ZQ fed-funds futures' if path else None
    path_src_zh = 'ZQ 联邦基金期货' if path else None
    comparable = path is not None and reference_current
    m12, m6 = (path or {}).get('m12'), (path or {}).get('m6')
    bp12 = round((m12 - policy_rate) * 100, 4) if comparable and m12 is not None else None
    eq12 = round((policy_rate - m12) / _QUARTER, 6) if bp12 is not None else None
    eq6 = round((policy_rate - m6) / _QUARTER, 6) if comparable and m6 is not None else None
    comparison_status = ('effective_rate_reference_unavailable' if policy_rate is None else
                         'reference_date_unqualified' if not reference_current else
                         'path_date_unqualified' if path is None else
                         'horizon_unavailable' if m12 is None else 'same_date_frame_reference')
    dots = _dots_by_year(dot_series, pd.Timestamp(analysis_day).year) if analysis_day else []
    # A dot is a year-end target midpoint; the available interpolated EFFR path
    # lacks both an accepted midpoint basis mapping and exact target-period identity.
    gap_reasons = (['target_basis_unqualified', 'dot_publication_clock_unqualified',
                    'target_period_identity_unqualified'] if dots else ['dot_path_unavailable'])
    front_value = _r(zq_front_implied, 8)
    front = ({'implied_average_rate': front_value, 'frame_asof': _date_label(front_asof),
              'contract_family': 'ZQ', 'contract_identity_qualified': False,
              'target_period_identity_qualified': False, 'observation_origin': 'frame_unverified',
              'historical_availability_qualified': False} if front_value is not None else None)
    head_en = head_zh = None
    if bp12 is not None:
        head_en = (f"Dated ZQ 12m pricing: {bp12:+.1f}bp vs EFFR frame reference "
                   f"({policy_rate:.2f}% → {m12:.2f}%); {abs(eq12):.2f} ×25bp "
                   f"{'cut' if eq12 >= 0 else 'hike'} equivalents, not a meeting count")
        head_zh = (f"有日期的 ZQ 12个月定价较 EFFR 框架参考值 {bp12:+.1f}基点"
                   f"（{policy_rate:.2f}% → {m12:.2f}%）；相当于 {abs(eq12):.2f} 个25基点"
                   f"{'降息' if eq12 >= 0 else '加息'}幅度，并非会议次数")
    elif pol is not None:
        basis = 'EFFR frame reference' if policy_rate is not None else 'target-range midpoint reference'
        head_en = f"Policy reference {pol:.2f}% ({basis}); no qualified 12m comparison"
        head_zh = f"政策参考值 {pol:.2f}%（{'EFFR 框架参考值' if policy_rate is not None else '目标区间中点'}）；12个月比较未合格"
    elif path:
        head_en, head_zh = 'Dated ZQ path; effective-rate reference unavailable', '有日期的 ZQ 路径；有效利率参考值缺失'
    elif target_low is not None or target_high is not None:
        head_en, head_zh = ('Dated target-bound observations; no qualified midpoint',
                            '有日期的目标边界观测；中点未合格')
    elif sofr['last_observed_path']:
        head_en, head_zh = 'SOFR context only; no fed-funds path', '仅有 SOFR 上下文；没有联邦基金利率路径'
    read_en, read_zh = [], []
    if policy_rate is not None:
        read_en.append(f'EFFR reference frame row {policy_day or "unknown"}; source origin unverified. ')
        read_zh.append(f'EFFR 参考框架行日期 {policy_day or "不明"}；源观测来源未核实。')
    if target_low is not None or target_high is not None:
        read_en.append(f'Target-bound frame dates: lower {low_day or "unknown"}, '
                       f'upper {high_day or "unknown"}; '
                       f'{"matched dated bounds" if tmid is not None else "no qualified midpoint"}. ')
        read_zh.append(f'目标边界框架日期：下限 {low_day or "不明"}，上限 {high_day or "不明"}；'
                       f'{"有日期的匹配边界" if tmid is not None else "中点未合格"}。')
    date_status_labels = {
        'missing': ('no usable path', '没有可用路径'),
        'observation_date_unknown': ('observation date unknown', '观测日期不明'),
        'analysis_date_unknown': ('analysis date unknown', '分析日期不明'),
        'after_analysis_date': ('later than the analysis date; not used', '晚于分析日期；不使用'),
        'same_date_context': ('same-date descriptive context only', '仅为同日期描述性上下文'),
        'stale_dated_context': ('older observations retained, not current pricing', '保留较早观测，不视为当前定价'),
        'invalid_source': ('invalid source structure; not used', '源结构无效；不使用'),
        'read_unavailable': ('source read unavailable', '源读取不可用'),
    }
    for key, label, zh in ((zq, 'ZQ/EFFR', 'ZQ/EFFR'), (sofr, 'SR3/SOFR', 'SR3/SOFR')):
        date_text = key['source_asof'] or 'unknown'
        status_en, status_zh = date_status_labels[key['status']]
        read_en.append(f"{label} observation date {date_text}: {status_en}. ")
        read_zh.append(f"{zh} 观测日期 {key['source_asof'] or '不明'}：{status_zh}。")
    if sofr['last_observed_path']:
        read_en.append('SOFR is a separate quarterly-compounded rate, not a fed-funds target proxy. ')
        read_zh.append('SOFR 是单独的季度复利利率，不是联邦基金目标利率替代值。')
    if front:
        read_en.append('Continuous ZQ front quote has no qualified fixed contract period; not an m1 point. ')
        read_zh.append('连续 ZQ 近月报价缺少合格的固定合约期间；不作 m1 点使用。')
    if dots:
        read_en.append('Dots retained; market-versus-dot gap withheld without matched basis and target period. ')
        read_zh.append('保留点阵图；没有匹配的利率基础及目标期间，市场与点阵图差值暂不提供。')
    ntfs = _r(ntfs, 8)
    if ntfs is not None:
        read_en.append(f'Near-term forward spread {ntfs:+.2f}pp; not a meeting-specific probability. ')
        read_zh.append(f'近端远期利差 {ntfs:+.2f}个百分点；并非单次会议概率。')
    note_en = ('Display context only. ZQ/EFFR monthly averages and SR3/SOFR quarterly compounding '
               'are different bases. Dates are observations, not receipt timestamps. Relative horizons '
               'do not identify fixed contracts, meeting probabilities or a causal policy surprise. '
               'An EFFR frame reference may be carried or revised; same date is not live/replay proof. '
               'A build timestamp never refreshes its sources.')
    note_zh = ('仅供展示上下文。ZQ/EFFR 月均值与 SR3/SOFR 季度复利基础不同。观测日期不是接收时间。'
               '相对期限不能识别固定合约、会议概率或因果政策意外。EFFR 框架参考值可能经过填充或修订；'
               '日期相同不代表实时或历史回放证明。构建时间不会更新源观测。')
    out = {
        'asof': analysis_day, 'built': datetime.now(timezone.utc).isoformat(),
        'calculation_version': 'fed_path.date_basis.v2', 'horizons_m': list(horizons),
        'display_only': True, 'authority': False, 'can_score': False,
        'can_rank': False, 'can_size': False, 'can_gate': False, 'can_trade': False,
        'historical_availability_qualified': False, 'current_session_freshness': 'not_certified',
        'policy_rate': _r(policy_rate), 'target_low': _r(target_low),
        'target_high': _r(target_high), 'target_mid': _r(tmid),
        'target_range_evidence': range_evidence,
        'policy_reference_evidence': {'underlying': 'EFFR', 'source_column': 'fed_funds',
            'source_asof': policy_day, 'value': policy_rate,
            'observation_origin': 'frame_aligned_unverified',
            'historical_availability_qualified': False},
        'policy_reference_asof': policy_day, 'policy_observation_origin': 'frame_aligned_unverified',
        'implied': implied, 'implied_source_en': path_src, 'implied_source_zh': path_src_zh,
        'implied_bp_12m': bp12, 'implied_cuts_12m': round(eq12) if eq12 is not None else None,
        'implied_cuts_6m': round(eq6) if eq6 is not None else None,
        'implied_cut_equivalents_12m': eq12, 'implied_cut_equivalents_6m': eq6,
        'cut_count_interpretation': 'rounded_25bp_equivalents_not_meeting_counts_or_probabilities',
        'pricing_comparison_status': comparison_status,
        'sofr_path': ({k:_r(v) for k,v in sofr['last_observed_path'].items()}
                      if sofr['usable_as_same_date_context'] else None),
        'path_evidence': {'zq':zq, 'sofr':sofr}, 'front_quote_context': front,
        'dots': dots, 'gap': None, 'gap_unavailable_reasons': gap_reasons,
        'ntfs': _r(ntfs), 'curve_tp_adj': _r(curve_tp_adj), 'rate_exp_proxy': _r(rate_exp_proxy),
        'headline_en': head_en, 'headline_zh': head_zh,
        'read_en': ''.join(read_en).strip(), 'read_zh': ''.join(read_zh),
        'note_en': note_en, 'note_zh': note_zh,
    }
    if (pol is None and not dots and not zq['last_observed_path'] and
            not sofr['last_observed_path'] and front is None
            and target_low is None and target_high is None):
        return None
    return out



def validated_pricing_view(payload: dict) -> dict:
    """Reconcile the versioned display object with its own dated economic inputs.

    Reuses compute() rather than defining another pricing formula. This checks
    internal consistency only, NOT source authenticity or historical availability.
    Old copied headlines cannot override the verified numeric interpretation.
    """
    from copy import deepcopy
    import json

    def unavailable(reason):
        original = payload if isinstance(payload, dict) else {}
        return {'calculation_version': original.get('calculation_version'),
                'asof': _date_label(original.get('asof')), 'implied': {},
                'policy_rate': None, 'implied_bp_12m': None, 'implied_cuts_12m': None,
                'implied_cuts_6m': None, 'implied_cut_equivalents_12m': None,
                'implied_cut_equivalents_6m': None, 'dots': [], 'gap': None,
                'path_evidence': {}, 'pricing_comparison_status': 'inconsistent_source_object',
                'consumer_validation': {'status': 'unavailable', 'reason': reason},
                'historical_availability_qualified': False,
                'current_session_freshness': 'not_certified',
                'implied_source_en': None, 'implied_source_zh': None,
                'headline_en': 'Dated pricing comparison unavailable',
                'headline_zh': '有日期的定价比较不可用',
                'read_en': 'Source dates, rate basis or values are inconsistent; no pricing assertion.',
                'read_zh': '源日期、利率基础或数值不一致；不作定价断言。',
                'note_en': 'Internal consistency only; no source authentication or live/decision-time proof.',
                'note_zh': '仅检查内部一致性；不是源认证、实时或决策时点证明。',
                'display_only': True, 'authority': False, 'can_score': False,
                'can_rank': False, 'can_size': False, 'can_gate': False, 'can_trade': False}

    try:
        if not isinstance(payload, dict):
            return unavailable('not_an_object')
        if payload.get('calculation_version') != 'fed_path.date_basis.v2':
            return unavailable('unsupported_calculation_version')
        ref=payload['policy_reference_evidence']; bounds=payload['target_range_evidence']
        evidence=payload['path_evidence']; zq=evidence['zq']; sofr=evidence['sofr']
        if not all(isinstance(v,dict) for v in (ref,bounds,evidence,zq,sofr)):
            return unavailable('invalid_evidence_structure')
        # Dates/bases and redundant outputs are checked below against compute's
        # canonical reconstruction. A source may be consistently stale/missing.
        dots=payload.get('dots') or []
        ds=(pd.Series({pd.Timestamp(year=int(d['year']),month=12,day=31):d['median']
                       for d in dots}) if dots else None)
        front=payload.get('front_quote_context') or {}
        rebuilt=compute(asof=payload.get('asof'),
            policy_rate=ref.get('value'), policy_asof=ref.get('source_asof'),
            target_low=bounds.get('lower_value'), target_high=bounds.get('upper_value'),
            target_low_asof=bounds.get('lower_asof'), target_high_asof=bounds.get('upper_asof'),
            dot_series=ds, zq_path_row=zq.get('last_observed_path'),
            sofr_path_row=sofr.get('last_observed_path'), zq_path_asof=zq.get('source_asof'),
            sofr_path_asof=sofr.get('source_asof'),
            path_status={'zq':zq.get('status'), 'sofr':sofr.get('status')},
            zq_front_implied=front.get('implied_average_rate'), front_asof=front.get('frame_asof'),
            ntfs=payload.get('ntfs'), curve_tp_adj=payload.get('curve_tp_adj'),
            rate_exp_proxy=payload.get('rate_exp_proxy'),
            cfg={'horizons_m':payload['horizons_m']})
        if rebuilt is None:
            return unavailable('no_reconstructible_evidence')
        protected=('asof','calculation_version','horizons_m','policy_reference_evidence',
                   'target_range_evidence','policy_reference_asof','policy_observation_origin',
                   'policy_rate','target_low','target_high','target_mid','implied','sofr_path',
                   'implied_bp_12m','implied_cuts_12m','implied_cuts_6m',
                   'implied_cut_equivalents_12m','implied_cut_equivalents_6m',
                   'pricing_comparison_status','path_evidence','front_quote_context','dots','gap',
                   'historical_availability_qualified','current_session_freshness',
                   'display_only','authority','can_rank','can_score','can_gate','can_size','can_trade')
        def canonical(obj):
            return json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        for key in protected:
            if key not in payload or canonical(payload[key]) != canonical(rebuilt[key]):
                return unavailable('inconsistent_'+key)
        rebuilt['built']=payload.get('built')
        rebuilt['consumer_validation']={'status':'internally_consistent',
            'source_authentication':False,'historical_availability_qualified':False}
        return deepcopy(rebuilt)
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):
        return unavailable('malformed_evidence')


def _read_path_row(store_key: str, *, asof=None) -> tuple[dict | None, str | None]:
    """One read, finite daily source row, no per-column date mixing or filling.

    An all-null latest row falls back only as an explicitly older entire row.
    Future rows cannot replace an available row on/before the supplied daily cut.
    This observation-date filter is not a historical knowledge-time reconstruction.
    """
    df = store.read('rate_futures', store_key)
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return None, None
    if not isinstance(df, pd.DataFrame):
        raise ValueError('path table is not a DataFrame')
    idx = df.index
    if (not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or not idx.is_unique
            or idx.tz is not None or not idx.equals(idx.normalize()) or not df.columns.is_unique):
        raise ValueError('path table requires unique timezone-naive daily labels')
    columns = [c for c in df.columns if isinstance(c, str) and c.startswith('m') and c[1:].isdigit()]
    if not columns:
        return None, None
    clean = df[columns].apply(lambda s: s.map(lambda v: _r(v, 8))).sort_index()
    clean = clean.dropna(how='all')
    if clean.empty:
        return None, None
    cut = _date_label(asof)
    eligible = clean.loc[:cut] if cut else clean
    selected = eligible if not eligible.empty else clean
    row = selected.iloc[-1]
    return {c: _r(row[c], 8) for c in selected.columns}, _date_label(selected.index[-1])


def snapshot(f: pd.DataFrame, cfg: dict | None = None) -> dict | None:
    """Existing store -> compute route; source failures are isolated and dated."""
    from engine.bonds import near_term_forward_spread
    cfg = cfg if cfg is not None else _cfg()
    asof = f.index.max() if len(f) else None

    def frame_value(column):
        if (column not in f or not f.columns.is_unique
                or not isinstance(f.index, pd.DatetimeIndex)
                or not f.index.is_unique or f.index.hasnans or f.index.tz is not None
                or not f.index.is_monotonic_increasing or not f.index.equals(f.index.normalize())):
            return None, None
        series = f[column].map(lambda v: _r(v, 8)).dropna()
        if series.empty:
            return None, None
        return float(series.iloc[-1]), _date_label(series.index[-1])

    policy_rate, policy_asof = frame_value('fed_funds')
    target_low, low_asof = frame_value('fed_target_lower')
    target_high, high_asof = frame_value('fed_target_upper')
    zq_front_implied, front_asof = frame_value('zq_implied_rate')
    rate_exp_proxy, _ = frame_value('rate_expectations_proxy')
    curve_tp_adj, _ = frame_value('curve_tp_adj')
    try:
        ntfs = _last(near_term_forward_spread(f))
    except Exception:
        ntfs = None
    try:
        dot_df = store.read('fred', 'FEDTARMD')
        dot_series = (dot_df.iloc[:, 0] if isinstance(dot_df, pd.DataFrame) and not dot_df.empty else None)
        if dot_series is not None:
            dot_series = dot_series.map(lambda v: _r(v, 8)).dropna()
            if not isinstance(dot_series.index, pd.DatetimeIndex) or dot_series.index.hasnans:
                dot_series = None
    except Exception:
        dot_series = None
    # No frame fallback: a filled single dot cannot recover projection-year identity.
    rows, dates, statuses = {}, {}, {}
    for short, key in (('zq', 'zq_path'), ('sofr', 'sofr_path')):
        try:
            rows[short], dates[short] = _read_path_row(key, asof=asof)
        except ValueError:
            rows[short], dates[short], statuses[short] = None, None, 'invalid_source'
        except Exception:
            rows[short], dates[short], statuses[short] = None, None, 'read_unavailable'
    return compute(asof=asof, policy_rate=policy_rate, policy_asof=policy_asof,
                   target_low=target_low, target_high=target_high, dot_series=dot_series,
                   target_low_asof=low_asof, target_high_asof=high_asof,
                   zq_path_row=rows['zq'], sofr_path_row=rows['sofr'],
                   zq_path_asof=dates['zq'], sofr_path_asof=dates['sofr'], path_status=statuses,
                   zq_front_implied=zq_front_implied, front_asof=front_asof, ntfs=ntfs,
                   curve_tp_adj=curve_tp_adj, rate_exp_proxy=rate_exp_proxy, cfg=cfg)
