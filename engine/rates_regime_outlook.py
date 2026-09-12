"""One dated research projection for the existing Rates & Inflation Command.

No fitting, collection, ledger writes, model inference, or allocation changes.
The existing RIC builder owns publication. Complete owner inputs and their byte
hashes are consumed; no manually selected research-excerpt file is read.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import math

from engine.regime_research_inputs import cutoff_utc, curve_snapshot
from engine.regime_research import seal, validate_seal
from engine.regime_transition_research import AUTHORITY, STATES, month_after, month_number

SCHEMA = "rates_command.regime_outlook.v1"
SOURCE_FILES = {
    "transmission": "transmission/latest.json", "regime": "regime/latest.json",
    "regime_one": "regime/regime_one.json", "calibration": "regime/hmm_latest.json",
    "dollar": "forex/latest.json", "oil": "commodity/latest.json",
    "oil_shock": "commodity/shock_state.json", "policy": "policy/intel.json",
    "bonds": "bonds/bond_health.json", "release": "release_forecast/latest.json",
}
PATHS = (
    ("orderly_disinflation", "Orderly disinflation", "通胀有序降温",
     "Inflation cools without broad labor or credit deterioration.", "通胀降温，但就业和信用未全面恶化。"),
    ("growth_deterioration", "Growth deterioration", "增长趋弱",
     "Lower yields accompany weakening activity and financing conditions.", "收益率下行伴随经济活动和融资条件走弱。"),
    ("renewed_inflation_pressure", "Renewed inflation pressure", "通胀压力再起",
     "Price pressure persists or broadens beyond a single oil move.", "价格压力持续或扩散，而非仅有油价一项变动。"),
    ("long_end_premium_shock", "Long-end premium pressure", "长端溢价压力",
     "Long yields rise beyond what near-term policy pricing alone explains.", "长端收益率上行，短期政策定价不能单独解释。"),
    ("technical_pause", "A pause, not yet a durable turn", "暂时缓和，尚非持久转向",
     "Market momentum eases before durable fundamental confirmation.", "市场动能先行缓和，基本面持久转向尚待确认。"),
)


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _get(value: Any, *keys: str) -> Any:
    for key in keys:
        value = _mapping(value).get(key)
    return value


def _number(value: Any) -> float | None:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except (ValueError,OverflowError):
        return None


def _date(value: Any) -> date | None:
    if not isinstance(value,str):
        return None
    try:
        if len(value)==10:
            return date.fromisoformat(value)
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).date()
    except (ValueError,TypeError,OverflowError):
        return None


def _future_clock(value: Any, cutoff: datetime) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) == 10:
        parsed = _date(value)
        return parsed is not None and parsed > cutoff.date()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.astimezone(timezone.utc) > cutoff
    except (ValueError, TypeError, OverflowError):
        return False


def _research_contract(value: Any) -> bool:
    """A matching digest is integrity, not schema or economic authority."""
    if not validate_seal(value) or value.get("schema") != "regime_one.integrated_research.v1":
        return False
    if value.get("source_basis") != "LATEST_REVISED_EXPLORATORY":
        return False
    def no_authority(obj):
        a = obj.get("authority")
        return isinstance(a, dict) and set(a) == set(AUTHORITY) and all(v is False for v in a.values())
    if not no_authority(value) or any(value.get(k) is not False for k in
        ("forward_ledger_advanced", "historical_live_issuance_claimed", "empirically_calibrated")):
        return False
    forecast = value.get("forecast")
    if forecast is None:
        return value.get("status") in ("UNAVAILABLE", "PARTIAL")
    if not isinstance(forecast, dict) or not no_authority(forecast):
        return False
    if value.get("target_name") != "operational_house_quadrant_at_closed_month_end":
        return False
    origin = value.get("origin_period")
    try:
        month_number(origin)
        rows = forecast.get("horizons")
        if not isinstance(rows, list) or [r.get("horizon_months") for r in rows] != [1, 3, 6, 12]:
            return False
        for row in rows:
            h = row["horizon_months"]
            if isinstance(h, bool) or row.get("target_period") != month_after(origin, h):
                return False
            p = row.get("occupancy")
            if not isinstance(p, dict) or set(p) != set(STATES):
                return False
            numbers = [_number(p[s]) for s in STATES]
            if any(x is None or x < 0 or x > 1 for x in numbers) or abs(sum(numbers)-1) > 1e-8:
                return False
            exit_probability = _number(row.get("first_exit_by_horizon"))
            if exit_probability is None or not 0 <= exit_probability <= 1:
                return False
        return forecast.get("origin_period") == origin and forecast.get("target_name") == value["target_name"]
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return False


def read_owner_json(data_root: Path, relative: str) -> tuple[dict, dict]:
    root=Path(data_root).resolve(); path=root/relative
    receipt={"path":"data/"+relative,"sha256":None,"status":"missing"}
    try:
        if not path.resolve().is_relative_to(root):
            receipt['status']='outside_source_root'; return {},receipt
        raw=path.read_bytes()
        receipt['sha256']=hashlib.sha256(raw).hexdigest()
        if len(raw)>8_000_000:
            receipt['status']='oversized'; return {},receipt
        def reject_constant(value):
            raise ValueError('Nonfinite JSON')
        obj=json.loads(raw,parse_constant=reject_constant)
        if not isinstance(obj,dict):
            receipt['status']='invalid_shape'; return {},receipt
        receipt['status']='available';return obj,receipt
    except FileNotFoundError:
        return {},receipt
    except (OSError,UnicodeError,ValueError,TypeError,OverflowError):
        receipt['status']='invalid';return {},receipt


def compose_outlook(inputs: Mapping[str,Any], *, analysis_cutoff: str | datetime,
                    receipts: Mapping[str,dict], curves: dict | None = None) -> dict:
    cutoff=cutoff_utc(analysis_cutoff); today=cutoff.date()
    tx=_mapping(inputs.get('transmission')); reg=_mapping(inputs.get('regime'))
    one=_mapping(inputs.get('regime_one')); oil=_mapping(inputs.get('oil'))
    policy=_mapping(inputs.get('policy')); calibration=_mapping(inputs.get('calibration'))
    evidence=[]
    source_clock={}
    for name,obj in inputs.items():
        obj=_mapping(obj)
        raw=obj.get('asof',obj.get('as_of',obj.get('date')))
        parsed=_date(raw)
        age=(today-parsed).days if parsed else None
        source_clock[name]={"source_date":raw if isinstance(raw,str) else None,
                            "clock_basis":"owner_artifact_date_not_per_field_observation",
                            "age_calendar_days":age,"future_dated":_future_clock(raw,cutoff)}
    def add(key, source, field, value, unit, en, zh, *, clock=None, maximum_age=7, basis=None):
        owner_clock=source_clock.get(source,{})
        parsed=_date(clock) if clock is not None else _date(owner_clock.get('source_date'))
        age=(today-parsed).days if parsed else None
        status='owner_context_limited_clock'
        if value is None: status='missing'
        elif parsed is None: status='unknown_date'
        elif _future_clock(clock if clock is not None else owner_clock.get("source_date"),cutoff): status='future_observation_refused'
        elif age>maximum_age: status='stale'
        elif clock is not None: status='dated_observation'
        evidence.append({"id":key,"source":source,"field":field,"value":value,"unit":unit,
                         "label":{"en":en,"zh":zh},"status":status,"source_date":str(parsed) if parsed else None,
                         "age_calendar_days":age,"research_age_budget_days":maximum_age,
                         "clock_basis":basis or ('source_observation_date' if clock is not None else 'owner_artifact_date'),
                         "available_at":None,"historical_pit_eligible":False,
                         "source_receipt":dict(receipts.get(source,{}))})
        return evidence[-1]
    add('real_rate_direction','transmission','state.rates.direction',_get(tx,'state','rates','direction'),None,
        'Real-rate direction','实际利率方向')
    for key,field,en,zh in (
        ('real10','real_10y','10-year real yield','10年期实际收益率'),
        ('real_change22','real_10y_chg_22d_bp','Real yield: owner 22-day change','实际收益率：原引擎22日变动'),
        ('real_change63','real_10y_chg_63d_bp','Real yield: owner 63-day change','实际收益率：原引擎63日变动')):
        add(key,'transmission','state.rates.'+field,_number(_get(tx,'state','rates',field)),
            'percent' if key=='real10' else 'basis_points',en,zh)
    add('inflation_direction','transmission','state.inflation.direction',_get(tx,'state','inflation','direction'),None,
        'Economic inflation direction','经济通胀方向')
    add('core_pce','transmission','state.inflation.core_pce_yoy',_number(_get(tx,'state','inflation','core_pce_yoy')),'percent',
        'Core PCE year-on-year','核心PCE同比')
    add('breakeven_direction','transmission','breakeven_decomp.direction',_get(tx,'breakeven_decomp','direction'),None,
        'Inflation compensation direction','通胀补偿方向',clock=_get(tx,'breakeven_decomp','as_of'))
    dollar=_mapping(tx.get('dollar_channel'))
    add('dollar_direction','transmission','dollar_channel.usd_dir',dollar.get('usd_dir'),None,
        'Dollar direction','美元方向',clock=dollar.get('asof'),basis='dollar_owner_artifact_date_not_spot_observation')
    add('term_premium_change','transmission','yield_curve.regime.term_premium_chg_bp',
        _number(_get(tx,'yield_curve','regime','term_premium_chg_bp')),'basis_points',
        'Owner-model term-premium change','原模型期限溢价变动',
        clock=_get(tx,'yield_curve','asof'),basis='curve_owner_calculation_date_not_term_premium_observation')
    add('curve_direction','transmission','yield_curve.regime.key',_get(tx,'yield_curve','regime','key'),None,
        'Curve configuration','曲线形态',clock=_get(tx,'yield_curve','asof'))
    nominal=_mapping(_get(tx,'yield_momentum','series','30y'))
    add('nominal30_velocity','transmission','yield_momentum.series.30y.velocity_bp.22d',
        _number(_get(nominal,'velocity_bp','22d')),'basis_points','30-year nominal change','30年期名义收益率变动',clock=nominal.get('as_of'))
    add('nominal30_acceleration','transmission','yield_momentum.series.30y.acceleration_bp',
        _number(nominal.get('acceleration_bp')),'basis_points','30-year nominal acceleration','30年期名义收益率加速度',clock=nominal.get('as_of'))
    for key,field,en,zh in (
        ('claims_level_z','claims_z','Claims standardized level, not change','初请标准化水平，非变化方向'),
        ('hiring_change','indeed_chg_3m_pct','Job postings: three-month change','职位发布三个月变化'),
        ('income_proxy','withheld_tax_yoy_pct','Withheld-tax income proxy: year-on-year','预扣税收入代理：同比')):
        add(key,'regime','labor_nowcast.'+field,_number(_get(reg,'labor_nowcast',field)),
            'standard_deviations' if key=='claims_level_z' else 'percent',en,zh)
    # Do not guess which nesting/schema a financial-conditions owner used.
    # Per-field dates are used only when that exact contract is present.
    conditions=_mapping(reg.get('conditions'))
    add('credit_spread','regime','conditions.hy_oas',_number(conditions.get('hy_oas')),'percentage_points',
        'High-yield credit spread','高收益信用利差',clock=_get(conditions,'vintages','hy_oas'))
    add('oil_trend','oil','assets.oil.trend',_get(oil,'assets','oil','trend'),None,
        'Oil trend, not shock cause','油价趋势，非冲击成因')
    add('policy_context_date','policy','as_of',policy.get('as_of'),None,
        'Dated policy research','带日期的政策研究',maximum_age=14)
    by_id={e['id']:e for e in evidence}
    def condition(key, rule, expected, text_en, text_zh):
        e=by_id[key]; value=e['value']; state='unknown'
        if e['status'] in ('dated_observation','owner_context_limited_clock'):
            if rule=='enum' and isinstance(value,str):
                state='supporting' if value in expected[0] else 'contrary' if value in expected[1] else 'unknown'
            elif rule=='sign' and _number(value) is not None:
                sign=1 if value>0 else -1 if value<0 else 0
                state='supporting' if sign in expected[0] else 'contrary' if sign in expected[1] else 'unknown'
        return {'evidence_id':key,'status':state,'rule':rule,'expected_support':list(expected[0]),
                'expected_contrary':list(expected[1]),'statement':{'en':text_en,'zh':text_zh},
                'evidence_clock_status':e['status']}
    cooling=condition('inflation_direction','enum',(('cooling',),('re-accelerating','rising')),
                      'Inflation cooling supports this condition, not a complete soft-landing forecast.',
                      '通胀降温支持此条件，但不等于完整软着陆预测。')
    easing=condition('real_rate_direction','enum',(('falling',),('rising',)),
                     'Real-rate direction must actually turn down; slower increases are different.',
                     '实际利率需真正转为下行；上行放缓并不相同。')
    hiring=condition('hiring_change','sign',((0,1),(-1,)),
                     'Job-posting growth is one labor observation, not proof of employment stability.',
                     '职位发布增长只是一项就业观察，不足以证明就业稳定。')
    wage=condition('income_proxy','sign',((0,1),(-1,)),
                   'Nominal withheld-tax income is a proxy, not real wage growth.',
                   '名义预扣税收入是代理指标，不是实际工资增长。')
    be_up=condition('breakeven_direction','enum',(('rising',),('falling',)),
                    'Rising inflation compensation is not pure expected inflation.',
                    '通胀补偿上升并非纯粹的通胀预期。')
    inflation_up=condition('inflation_direction','enum',(('re-accelerating','rising'),('cooling',)),
                           'A broad renewed-inflation read needs more than an oil-price move.',
                           '全面再通胀判断需要超出油价变动的证据。')
    tp=condition('term_premium_change','sign',((1,),(-1,)),
                  'The owner term-premium model is rising; model uncertainty remains.',
                  '原期限溢价模型上行，仍有模型不确定性。')
    slowing=condition('nominal30_acceleration','sign',((-1,),(1,)),
                       'Nominal long-yield acceleration is slowing; this is not a real-yield reversal.',
                       '长期名义收益率加速度降低，不等于实际收益率反转。')
    hiring_weak=condition('hiring_change','sign',((-1,),(0,1)),
                          'Falling postings would support weakening labor demand.',
                          '职位发布下降将支持劳动力需求趋弱的判断。')
    path_conditions=((cooling,easing,hiring,wage),(hiring_weak,easing),
                     (inflation_up,be_up),(tp,), (slowing,easing))
    watches=(
        ('Watch hiring, credit, inflation breadth and real-yield follow-through.', '观察招聘、信用、通胀广度和实际收益率后续走势。'),
        ('Watch claims, income and credit deterioration, not lower yields alone.', '观察初请、收入和信用恶化，不能只看收益率下降。'),
        ('Watch services and wages, inflation compensation and policy repricing.', '观察服务和工资、通胀补偿与政策重定价。'),
        ('Watch long-end demand, issuance and alternative premium-model estimates.', '观察长端需求、发行和其他溢价模型估计。'),
        ('Watch whether a nominal pause becomes an actual, persistent real-yield decline.', '观察名义收益率暂缓是否转为实际收益率持续下行。'))
    paths=[]
    for meta,conditions_for_path,watch in zip(PATHS,path_conditions,watches):
        key,en,zh,assume_en,assume_zh=meta
        paths.append({'id':key,'title':{'en':en,'zh':zh},'assumption':{'en':assume_en,'zh':assume_zh},
                      'conditions':list(conditions_for_path),'watch':{'en':watch[0],'zh':watch[1]},
                      'probability':None,'probability_status':'overlapping_research_hypothesis_not_forecast_target'})
    disagreements=[]
    def usable_evidence(key):
        return by_id[key]['status'] in ('dated_observation','owner_context_limited_clock')
    if usable_evidence('inflation_direction') and usable_evidence('breakeven_direction') and by_id['inflation_direction']['value']=='cooling' and by_id['breakeven_direction']['value']=='rising':
        disagreements.append({'id':'inflation_vs_compensation','en':'Economic inflation is cooling while market inflation compensation rises. Those are different objects, not cancelling votes.',
                              'zh':'经济通胀降温，市场通胀补偿却上升。两者含义不同，不能简单抵消。'})
    velocity=by_id['nominal30_velocity']['value']; accel=by_id['nominal30_acceleration']['value']
    if usable_evidence('nominal30_velocity') and usable_evidence('nominal30_acceleration') and velocity is not None and accel is not None and velocity>0 and accel<0:
        disagreements.append({'id':'slower_not_lower','en':'Long nominal yields are still rising, but more slowly. This does not establish a durable real-rate peak.',
                              'zh':'长期名义收益率仍上行，但速度放缓。这不足以确认实际利率持久见顶。'})
    tape=_get(one,'tape','quad'); economic=_get(one,'macro','quad')
    one_age=source_clock.get('regime_one',{}).get('age_calendar_days')
    if one_age is not None and 0<=one_age<=7 and not source_clock.get('regime_one',{}).get('future_dated') and tape in ('Q1','Q2','Q3','Q4') and economic in ('Q1','Q2','Q3','Q4') and tape!=economic:
        disagreements.append({'id':'tape_vs_economy','en':'Market-price and economic-data regime readings disagree; neither is a future-regime probability.',
                              'zh':'市场价格与经济数据的状态判断不一致；两者均非未来状态概率。'})
    research=calibration.get('transition_research')
    research_status='not_published_by_calibration_owner'
    if isinstance(research,dict):
        if not _research_contract(research): research_status='invalid_calibration_generation_or_contract';research=None
        elif research.get('schema')!='regime_one.integrated_research.v1': research_status='unsupported_calibration_schema';research=None
        elif _date(research.get('analysis_cutoff')) is None or _future_clock(research.get('analysis_cutoff'),cutoff):
            research_status='future_or_unknown_calibration_cutoff';research=None
        else: research_status=research.get('status','UNAVAILABLE')
    usable=sum(e['status'] in ('dated_observation','owner_context_limited_clock') for e in evidence)
    output={'schema':SCHEMA,'analysis_cutoff':cutoff.isoformat(),'source_receipts':dict(receipts),
            'transmission_sha256':_mapping(receipts.get('transmission')).get('sha256'),
            'source_clocks':source_clock,'availability':'partial' if usable else 'unavailable',
            'evidence':evidence,'conditional_paths':paths,'disagreements':disagreements,
            'curve_history':curves,'regime_reads':{'tape':tape,'economic':economic,
                'source_asof':one.get('asof'),'confirmed':reg.get('quad'),'pending':reg.get('pending_quad'),
                'pending_sessions':reg.get('pending_days'),'membership_is_forecast':False},
            'quantitative_research':research,'quantitative_status':research_status,
            'authority':dict(AUTHORITY),'path_ranking':None,
            'disclosure':{'en':'Conditional research, not trade instructions. The five paths overlap; their conditions are not probabilities.',
                          'zh':'条件性研究，非交易指令。五条路径可以重叠；条件不是概率。'},
            'missing_capabilities':['Portfolio exposure requires an owner-bound position/return contract; no allocation is inferred.',
                                    'Prospective issuance/grading must use the existing owner ledger; no new ledger is created.']}
    return seal(output)


def build_outlook(data_root: Path, *, analysis_cutoff: str | datetime) -> dict:
    inputs={};receipts={}
    for name,path in SOURCE_FILES.items():
        inputs[name],receipts[name]=read_owner_json(data_root,path)
    curves=curve_snapshot(data_root,analysis_cutoff)
    return compose_outlook(inputs,analysis_cutoff=analysis_cutoff,receipts=receipts,curves=curves)
