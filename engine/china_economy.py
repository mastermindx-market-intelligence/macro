"""Economy-wide interpretation of the existing China evidence publication.

Pure functions: no HTTP, persistence, ranking, forecasts or trading permission.
The output is an OPTIONAL `economy` field on the existing macro evidence JSON.
A fixed six-domain diagnostic shows breadth, never a GDP-weighted health score.
Monthly SA activity pace and slopes of published rates are deliberately different.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone, date
import calendar
import math
import re
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

SCHEMA = 'mastermind.china_economy_lens.v1'
GROUPS = {
 'production': ('Production & services', '生产与服务'),
 'households': ('Household demand', '居民需求'),
 'investment': ('Business investment', '企业投资'),
 'housing': ('Housing & construction', '房地产与建筑'),
 'external': ('External demand', '外部需求'),
 'employment': ('Employment', '就业'),
 'orders': ('Orders & business surveys', '订单与企业调查'),
 'prices': ('Prices & cost pressure', '价格与成本压力'),
 'fiscal': ('Fiscal cash flows', '财政收支'),
 'corporate': ('Business cash collection', '企业回款'),
 'physical': ('Physical activity', '实物活动'),
 'regions': ('Regional investment', '区域投资'),
}
# One vote per domain. These are research weights, not GDP or portfolio weights.
# Multiple measures within a family/domain never create extra economy-wide votes.
DOMAINS = [
 {'id':'production','state':['industrial_yoy','services_yoy'],
  'momentum':['industrial_sa','services_yoy'],'headline':'industrial_yoy',
  'qualifier_en':'Real industry and services; pace blends industrial SA evidence with the services growth reading.',
  'qualifier_zh':'工业和服务业实际产出；动能同时查看工业季调速度及服务业公布增速。'},
 {'id':'households','state':['retail_yoy','services_retail_ytd'],
  'momentum':['retail_sa','services_retail_ytd'],'headline':'retail_yoy',
  'qualifier_en':'Retail and service spending are different coverage. This is not total household consumption.',
  'qualifier_zh':'社零与服务零售覆盖不同，不等于居民全部消费。'},
 {'id':'investment','state':['investment_ytd'],'momentum':['investment_sa'],
  'headline':'investment_ytd','qualifier_en':'Investment growth includes prices; monthly pace uses the official seasonal revision.',
  'qualifier_zh':'投资增速包含价格变化；月度速度使用官方季调修订序列。'},
 {'id':'housing','state':['housing_sales_area','housing_starts'],
  'momentum':['housing_sales_area','housing_starts'],'headline':'housing_sales_area',
  'qualifier_en':'Cumulative new-development readings, not monthly activity or the resale market.',
  'qualifier_zh':'新开发市场累计读数，不等于单月活动或二手房市场。'},
 {'id':'external','state':['exports_cny'],'momentum':['exports_cny'],
  'headline':'exports_cny','qualifier_en':'Nominal CNY exports. Survey orders remain a separate forward-looking observation.',
  'qualifier_zh':'人民币名义出口；出口订单调查单独列为前瞻观测。'},
 {'id':'employment','state':['pmi_jobs','pmi_nonmfg_jobs'],
  'momentum':['pmi_jobs','pmi_nonmfg_jobs'],'headline':'pmi_jobs',
  'qualifier_en':'Employment surveys, not a headcount. Unadjusted unemployment is contextual, not silently substituted.',
  'qualifier_zh':'用工调查而非就业人数；未季调失业率另作背景，不暗中替代。'},
]
LABELS = {
 'improving': ('Improving', '改善'), 'fading': ('Fading', '转弱'), 'steady':('Little change','变化不大'),
 'mixed':('Mixed','分化'), 'unknown':('Not enough evidence','证据不足'),
 'above':('Above reference','高于基准'), 'below':('Below reference','低于基准'),
 'at_reference':('Near reference','接近基准'), 'observed':('Observed','观测值'),
}


def number(v: Any) -> float | None:
    if isinstance(v,bool): return None
    try: n=float(v)
    except (ValueError,TypeError,OverflowError): return None
    return n if math.isfinite(n) else None


def month_index(s: str) -> int:
    if not isinstance(s,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',s):
        raise ValueError('invalid YYYY-MM reference period')
    y,m=map(int,s.split('-'));return y*12+m-1


def month_from_index(n: int) -> str:
    return f'{n//12:04}-{n%12+1:02}'


def month_end(s: str) -> date:
    month_index(s);y,m=map(int,s.split('-'));return date(y,m,calendar.monthrange(y,m)[1])


def timestamp(value: str | datetime) -> datetime:
    v=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if not isinstance(v,datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError('timezone-aware timestamp required')
    return v


def classify_change(value: float | None, threshold: float) -> str:
    if value is None:return 'unknown'
    return 'improving' if value>threshold else 'fading' if value < -threshold else 'steady'


def safe_round(v, digits=6):
    return round(v,digits) if number(v) is not None else None


def compound(percentages: list[float | None]) -> float | None:
    """A sequence of returns, not growth-rate levels; caller owns SA/type gates."""
    if not percentages or any(number(v) is None or v <= -100 for v in percentages):return None
    return 100*(math.prod(1+v/100 for v in percentages)-1)


def slope(values: list[float]) -> float:
    xbar=(len(values)-1)/2
    den=sum((i-xbar)**2 for i in range(len(values)))
    return sum((i-xbar)*(v-mean(values)) for i,v in enumerate(values))/den if den else 0.


def _path(rows: list[dict], expected_period: str, n: int) -> list[dict] | None:
    """Require every calendar month, valid endpoint and one exact definition."""
    idx=month_index(expected_period)
    by={r['period']:r for r in rows}
    desired=[by.get(month_from_index(i)) for i in range(idx-n+1,idx+1)]
    if any(r is None or number(r.get('value')) is None for r in desired):return None
    if len({r.get('definition_id') for r in desired})!=1:return None
    return desired


def pace(meta: dict, rows: list[dict], expected_period: str) -> dict:
    out={'method':'none','current_3m':None,'previous_3m':None,'change_in_pace':None,
         'slope_recent_3m':None,'slope_previous_3m':None,'acceleration':None,
         'pace_unit':None,'acceleration_unit':None,'direction':'unknown','reason':'insufficient_history',
         'required_months':6,'is_activity_growth':False,'original_vintage':False,'window_sensitivity':None}
    kind=meta['kind']
    if meta.get('frequency')!='monthly' or kind not in {'sa_mom','survey','yoy','ytd_yoy'}:
        out['reason']='not_a_monthly_pace_measure';return out
    recent=_path(rows,expected_period,3)
    six=_path(rows,expected_period,6)
    if kind=='ytd_yoy' and recent and len({r['period'][:4] for r in recent})>1:recent=None
    if kind=='ytd_yoy' and six and len({r['period'][:4] for r in six})>1:six=None
    out['method']='compounded_SA_3month_growth' if kind=='sa_mom' else 'change_in_reported_reading'
    out['pace_unit']='% over 3 months' if kind=='sa_mom' else ('index points' if kind=='survey' else 'percentage points')
    out['is_activity_growth']=kind=='sa_mom'
    out['comparison_level_unit']=meta.get('unit')
    if kind=='sa_mom':
        # Revised monthly histories must remain a coherent release. Mixing old
        # and new seasonal revisions can manufacture a turn.
        if recent and len({r['vintage_id'] for r in recent})>1:recent=None
        if six and len({r['vintage_id'] for r in six})>1:
            out['reason']='mixed_seasonal_revision';return out
        if recent:out['current_3m']=safe_round(compound([r['value'] for r in recent]))
        if six:
            out['previous_3m']=safe_round(compound([r['value'] for r in six[:3]]))
            if out['current_3m'] is not None and out['previous_3m'] is not None:
                change=out['current_3m']-out['previous_3m']
                out.update(change_in_pace=safe_round(change),direction=classify_change(change,.05),reason=None)
        four=_path(rows,expected_period,4)
        if four and len({r['vintage_id'] for r in four})==1:
            cur2=compound([r['value'] for r in four[-2:]])
            prev2=compound([r['value'] for r in four[:2]])
            if cur2 is not None and prev2 is not None:
                d2=classify_change(cur2-prev2,.05)
                out['window_sensitivity']={'current_2m':safe_round(cur2),'previous_2m':safe_round(prev2),
                    'change_in_pace_2m':safe_round(cur2-prev2),'direction_2m':d2,
                    'agrees_with_3m': d2==out['direction'] if out['direction']!='unknown' else None,
                    'interpretation':'descriptive_window_check_NOT_statistical_confidence'}
        # No annualization and no mixing rate curvature with the actual pace.
        return out
    if recent:out['slope_recent_3m']=safe_round(slope([r['value'] for r in recent]))
    out['slope_unit']='index points/month' if kind=='survey' else 'percentage points/month'
    if six:
        recent_vals=[r['value'] for r in six[3:]];old_vals=[r['value'] for r in six[:3]]
        out['current_3m']=safe_round(mean(recent_vals));out['previous_3m']=safe_round(mean(old_vals))
        change=(out['current_3m']-out['previous_3m'])*meta.get('polarity',1)
        out['change_in_pace']=safe_round(change)
        out['slope_previous_3m']=safe_round(slope(old_vals))
        # Window centers are three months apart. Units must be /month^2.
        out['acceleration']=safe_round((out['slope_recent_3m']-out['slope_previous_3m'])/3)
        out['acceleration_unit']='index points/month²' if kind=='survey' else 'percentage points/month²'
        out['direction']=classify_change(change,meta['direction_deadband'])
        out['reason']=None
    if kind=='ytd_yoy':out['warning']='slope_of_cumulative_reported_growth_NOT_monthly_activity'
    out['vintage_mode']='single_release' if len({r['vintage_id'] for r in (six or recent or [])})<=1 else 'sequence_of_published_releases_not_original_vintage_replay'
    return out


def select_observations(meta: dict, observations: list[dict], sources: dict, as_of: datetime) -> tuple[list[dict],list[dict]]:
    by: dict[str,list[dict]]={};problems=[]
    for row in observations:
        if row.get('metric_id')!=meta['id']:continue
        try:
            month_index(row['period']);pub=timestamp(row['published_at']);source=sources[row['source_id']]
            url=urlparse(source['url'])
            if url.scheme!='https' or url.hostname not in {'www.stats.gov.cn','www.mof.gov.cn','m.mof.gov.cn','www.nea.gov.cn','www.pbc.gov.cn','www.safe.gov.cn'} or url.username or url.password or url.port not in (None,443):
                raise ValueError('source_origin_not_admitted')
            if pub!=timestamp(source['published_at']):raise ValueError('source_publication_mismatch')
            if row.get('definition_id')!=meta['definition_id']:raise ValueError('definition_mismatch')
            if pub>as_of:continue
            observed=row.get('observed_at')
            if observed is not None:
                acquired=timestamp(observed)
                if acquired>as_of:continue
                if acquired<pub:raise ValueError('publication_after_acquisition')
            if meta['kind']!='survey' and pub.astimezone(ZoneInfo('Asia/Shanghai')).date()<month_end(row['period']):
                raise ValueError('publication_before_reference_period_completed')
            if meta['kind']!='survey' and month_end(row['period'])>as_of.date():continue
            if meta['kind']=='survey' and month_index(row['period'])>as_of.year*12+as_of.month-1:continue
            if meta.get('frequency')=='quarterly' and int(row['period'][-2:])%3:raise ValueError('not_a_quarter_end')
            value=number(row.get('value'))
            if row.get('value') is not None and value is None:raise ValueError('nonfinite_or_boolean')
            if meta['kind']=='survey' and value is not None and not 0<=value<=100:raise ValueError('invalid_diffusion_range')
            if meta['kind']=='sa_mom' and value is not None and value<=-100:raise ValueError('invalid_growth_rate')
            r=deepcopy(row);r['value']=value;r['_pub']=pub
            by.setdefault(r['period'],[]).append(r)
        except (ValueError,KeyError,TypeError) as exc:
            problems.append({'period':row.get('period'),'reason':str(exc),'source_id':row.get('source_id')})
    result=[]
    for period,group in sorted(by.items()):
        last=max(r['_pub'] for r in group);fresh=[r for r in group if r['_pub']==last]
        signatures={(r['value'],r['definition_id'],r['vintage_id']) for r in fresh}
        chosen=deepcopy(fresh[0]);chosen.pop('_pub',None)
        if len(signatures)>1:
            chosen['value']=None;problems.append({'period':period,'reason':'conflicting_duplicate_at_same_release'})
        result.append(chosen)
    return result,problems


def metric_view(meta: dict, observations:list[dict], sources:dict, as_of:datetime, reference_period:str) -> dict:
    rows,problems=select_observations(meta,observations,sources,as_of)
    eligible=[r for r in rows if month_index(r['period'])<=month_index(reference_period)]
    latest=eligible[-1] if eligible else None
    m=deepcopy(meta);m.update(value=latest['value'] if latest else None,
        reference_period=latest['period'] if latest else None,requested_period=reference_period,
        source_id=latest['source_id'] if latest else None,published_at=latest['published_at'] if latest else None,
        source=sources.get(latest['source_id']) if latest else None,problems=problems)
    m['status']='unavailable' if m['value'] is None else 'current' if latest['period']==reference_period else 'older_period'
    if any(p.get('period')==reference_period for p in problems):m['status']='quality_hold';m['value']=None
    m['change_1m']=None
    # Keep latest-published dynamics visible across a calendar rollover without
    # pretending the metric is current for the requested assessment month.
    # A quality-held requested period never falls back to an older pace.
    pace_period=(latest['period'] if latest and m['status'] in {'current','older_period'}
                 else reference_period)
    m['pace_reference_period']=pace_period if latest and m['status'] in {'current','older_period'} else None
    pair=_path(eligible,pace_period,2) if meta['frequency']=='monthly' and m['pace_reference_period'] else None
    if pair and meta['kind']=='sa_mom' and len({r['vintage_id'] for r in pair})>1:pair=None
    if pair and meta['kind']=='ytd_yoy' and pair[0]['period'][:4]!=pair[-1]['period'][:4]:pair=None
    m['change_unit']='percentage points' if meta['unit'].startswith('%') else 'index points' if meta['kind']=='survey' else meta['unit']
    if pair:
        m['change_1m']=safe_round(pair[-1]['value']-pair[0]['value'])
    neutral=meta.get('neutral')
    if m['value'] is None:m['state']='unknown'
    elif neutral is None or meta['kind'] in {'ratio','level','count'}:m['state']='observed'
    else:
        delta=(m['value']-neutral)*meta.get('polarity',1)
        m['state']='above' if delta>0 else 'below' if delta<0 else 'at_reference'
    m['pace']=(pace(meta,eligible,pace_period)
               if m['status'] in {'current','older_period'} and m['pace_reference_period']
               else pace(meta,[],reference_period))
    dates=[];values=[]
    if eligible:
        lookup={r['period']:(r['value'] if meta['kind']!='sa_mom' or r['vintage_id']==eligible[-1]['vintage_id'] else None) for r in eligible}
        for i in range(month_index(eligible[0]['period']),month_index(reference_period)+1):
            s=month_from_index(i);dates.append(s+'-01');values.append(lookup.get(s))
    m['chart']={'dates':dates[-120:],'vals':values[-120:]}
    m['reference']=neutral;m['chart_kind']='line'
    m['display']='—' if m['value'] is None else f'{m["value"]:,.{meta["precision"]}f}'
    m['point_count']=sum(v is not None for v in values)
    m['level_label_en'],m['level_label_zh']=LABELS[m['state']]
    m['direction_label_en'],m['direction_label_zh']=LABELS[m['pace']['direction']]
    return m


def consensus(states: list[str], admitted:set[str]) -> str:
    valid=[s for s in states if s in admitted]
    if not valid or len(valid)!=len(states):return 'unknown'
    return valid[0] if len(set(valid))==1 else 'mixed'


def domain_view(spec:dict,metrics:dict,reference_period:str) -> dict:
    state_rows=[metrics.get(k) for k in spec['state']]
    mom_rows=[metrics.get(k) for k in spec['momentum']]
    state=consensus([m['state'] if m and m['status']=='current' else 'unknown' for m in state_rows],{'above','below','at_reference'})
    mom=consensus([m['pace']['direction'] if m and m['status']=='current' else 'unknown' for m in mom_rows],{'improving','fading','steady'})
    title=GROUPS[spec['id']]
    return {**deepcopy(spec),'title_en':title[0],'title_zh':title[1],'state':state,'momentum':mom,
        'state_en':LABELS[state][0],'state_zh':LABELS[state][1],
        'momentum_en':LABELS[mom][0],'momentum_zh':LABELS[mom][1],
        'headline_metric':spec['headline'],'reference_period':reference_period,
        'weight':1,'weight_type':'research_domain_count_NOT_GDP',
        'drivers':[{'metric_id':m['id'],'direction':m['pace']['direction'],'method':m['pace']['method']} for m in mom_rows if m]}


def breadth(domains:list[dict]) -> dict:
    total=len(DOMAINS)
    counts={key:sum(d['momentum']==key for d in domains) for key in ['improving','fading','steady','mixed','unknown']}
    covered=total-counts['unknown']
    ready=covered>=4
    headline_en='Economic direction needs more evidence.';headline_zh='经济方向仍需更多证据。'
    if ready:
        if counts['improving']>=4:headline_en,headline_zh='Improvement is broadening.','改善正在扩散。'
        elif counts['fading']>=4:headline_en,headline_zh='Economic momentum is weakening broadly.','经济动能普遍减弱。'
        else:headline_en,headline_zh='Growth remains uneven.','增长仍然分化。'
    return {'universe':total,'covered':covered,'counts':counts,'eligible':ready,'minimum_coverage':4,
        'improvement_lower_bound_pct':round(counts['improving']/total*100,1),
        'improvement_upper_bound_pct':round((counts['improving']+counts['unknown'])/total*100,1),
        'bounds_type':'missing-domain bounds, NOT statistical confidence intervals',
        'headline_en':headline_en,'headline_zh':headline_zh,
        'is_gdp_nowcast':False,'is_probability':False,'not_trade_authority':True,
        'method_en':'One diagnostic vote per six fixed growth domains; conflicting evidence stays mixed. No weight is reassigned when a domain is unavailable. This is not a GDP-weighted economy score.',
        'method_zh':'六个固定增长领域各一票；冲突保留为分化。缺失时不转移权重；这不是GDP加权经济评分。'}


def diagnostic(key,en,zh,ids,metrics,operation,unit,method_en,method_zh):
    parts=[metrics.get(i) for i in ids]
    ready=all(m and m['status']=='current' and m['value'] is not None for m in parts)
    ready=ready and len({m['reference_period'] for m in parts if m})==1
    value=None
    if ready:
        try:value=number(operation([m['value'] for m in parts]))
        except (ArithmeticError,ValueError,TypeError):pass
    return {'id':key,'label_en':en,'label_zh':zh,'value':safe_round(value,3),'display':f'{value:+,.2f}' if value is not None else '—',
        'unit':unit,'input_ids':ids,'reference_period':parts[0]['reference_period'] if ready else None,
        'status':'current' if value is not None else 'unavailable','method_en':method_en,'method_zh':method_zh,'authority':'descriptive_only'}


def build_economy(document:dict, as_of:str|datetime|None=None, reference_period:str|None=None) -> dict:
    if document.get('schema')!='mastermind.china_economy_review_input.v1' and document.get('schema')!='mastermind.china_economy_store_input.v1':
        raise ValueError('unsupported economy input contract')
    now=timestamp(as_of or document['as_of']).astimezone(ZoneInfo('Asia/Shanghai'))
    reference_period=reference_period or document['display_reference_period'];month_index(reference_period)
    if month_index(reference_period)>now.year*12+now.month-1:raise ValueError('future display reference period')
    catalog=document['catalog'];sources=document['sources'];observations=document['observations']
    if any(k!=v['id'] for k,v in catalog.items()):raise ValueError('catalog identity mismatch')
    metrics={k:metric_view(v,observations,sources,now,reference_period) for k,v in catalog.items()}
    domains=[domain_view(s,metrics,reference_period) for s in DOMAINS]
    diagnostics=[]
    specs=[
        ('orders_inventory','Orders versus inventory','订单与库存差',['pmi_orders','pmi_finished_inventory'],lambda v:v[0]-v[1],'index points','New-order diffusion minus finished-inventory diffusion. Not a physical stock/flow ratio or validated demand forecast.','新订单扩散减产成品库存扩散；非实际库存流量比，也不是已验证需求预测。'),
        ('input_output_prices','Input versus selling prices','购进与售价差',['pmi_input_prices','pmi_output_prices'],lambda v:v[0]-v[1],'index points','Survey input-price diffusion minus selling-price diffusion; NOT a measured profit margin.','投入价格扩散减售价扩散；不是实际利润率。'),
        ('large_small','Large versus small firms','大中小分化',['pmi_large','pmi_small'],lambda v:v[0]-v[1],'index points','Large-firm PMI minus small-firm PMI; both 50-reference diffusion indices.','大企业PMI减小企业PMI，二者均以50为无变化基准。'),
        ('retail_auto_gap','Retail excluding autos','汽车与其他消费差',['retail_exauto','retail_yoy'],lambda v:v[0]-v[1],'percentage points','Growth gap, not the automotive contribution; aggregation weights are not available here.','增速差不是汽车贡献，未提供聚合权重。'),
        ('fiscal_cash_gap','General-budget cash gap','一般预算收支差额',['fiscal_general_spending','fiscal_general_revenue'],lambda v:v[0]-v[1],'CNY bn YTD','Spending minus revenue, same YTD period. Not an official deficit or a structural fiscal impulse.','同期累计支出减收入，不是官方赤字或结构性财政脉冲。'),
        ('interest_share','Interest share of spending','付息占支出比重',['fiscal_interest_spending','fiscal_general_spending'],lambda v:100*v[0]/v[1] if v[1]>0 else None,'%','Interest divided by general-budget spending; same budget and period.','同预算同期付息除以一般公共预算支出。'),
        ('land_share','Land share of local funds','土地占地方基金收入',['fiscal_land_revenue','fiscal_local_fund_revenue'],lambda v:100*v[0]/v[1] if v[1]>0 else None,'%','Land-use-right receipts divided by local government-fund revenue; NOT all local public revenue.','土地出让收入除以地方政府性基金收入，不是全部地方公共收入。'),
        ('industry_breadth','Industries growing','增长行业占比',['industry_positive'],lambda v:100*v[0]/41,'% of 41 industries','Unweighted count of industries with rising real value added; not GDP weights.','实际增加值增长行业的等权计数，不是GDP权重。'),
        ('product_breadth','Products growing','增长产品占比',['products_positive'],lambda v:100*v[0]/626,'% of 626 products','Physical-product count breadth; not the same population as industry value-added breadth.','实物产品数量广度；与行业增加值广度不是同一总体。'),
    ]
    specs += [
        ('fx_conversion_balance','Bank FX conversion balance','银行结售汇差额',['fx_surrender','fx_purchase'],lambda v:v[0]-v[1],'CNY bn / month','FX sold to banks minus FX bought from banks. Includes conversion for clients and banks; not an equity-investment flow.','结汇减售汇，包含银行自营及代客兑换；不是股票投资流量。'),
        ('external_payment_balance','Bank-client external balance','银行代客涉外收付款差额',['external_receipts','external_payments'],lambda v:v[0]-v[1],'CNY bn / month','External receipts minus payments for bank clients; includes RMB and FX. Not the whole balance of payments or net foreign direct investment.','银行代客涉外收入减付款，包含人民币及外汇；并非完整国际收支或外商直接投资净额。'),
    ]
    for args in specs:diagnostics.append(diagnostic(*args[:4],metrics,*args[4:]))
    groups=[]
    for key,(en,zh) in GROUPS.items():
        selected=[m['id'] for m in metrics.values() if m['group']==key]
        if selected:groups.append({'id':key,'title_en':en,'title_zh':zh,'metric_ids':selected})
    return {'schema':SCHEMA,'as_of':now.isoformat(),'reference_period':reference_period,'input_class':document.get('input_class'),
        'authority':'economic_description_only','original_vintage_replay':False,'is_live_feed':False,
        'base_publication_owner':'existing china_macro_evidence snapshot; additive economy field',
        'metrics':metrics,'domains':domains,'breadth':breadth(domains),'groups':groups,'diagnostics':diagnostics,
        'sources':deepcopy(sources),
        'known_source_conflicts':deepcopy(document.get('known_source_conflicts',[])),
        'activity_pulse':{
            'assessment_period':reference_period,
            'coverage_basis':'latest_available_per_series_not_current_month_votes',
            'reference_periods':{k:metrics[k].get('pace_reference_period')
                for k in ['industrial_sa','retail_sa','investment_sa']},
            'all_current_for_assessment':all(metrics[k]['status']=='current'
                for k in ['industrial_sa','retail_sa','investment_sa']),
            'metric_ids':['industrial_sa','retail_sa','investment_sa'],
            'improving_3m':sum(metrics[k]['pace']['direction']=='improving' for k in ['industrial_sa','retail_sa','investment_sa']),
            'improving_2m':sum((metrics[k]['pace'].get('window_sensitivity') or {}).get('direction_2m')=='improving' for k in ['industrial_sa','retail_sa','investment_sa']),
            'window_sensitive':sum((metrics[k]['pace'].get('window_sensitivity') or {}).get('agrees_with_3m') is False for k in ['industrial_sa','retail_sa','investment_sa']),
            'covered_3m':sum(metrics[k]['pace']['change_in_pace'] is not None for k in ['industrial_sa','retail_sa','investment_sa']),
            'universe':3,'gdp_weighted':False,
            'method_en':'Three independently reported SA activity series. Each 3-month window is compounded and compared with its preceding 3 months; a separate 2-month check exposes window sensitivity.',
            'method_zh':'三项独立公布的季调活动序列。三月窗口按复利累计并与前一三月比较；二月窗口另作敏感性检查。'},
        'counts':{'catalog':len(metrics),'valid_current':sum(m['status']=='current' for m in metrics.values()),'diagnostics':len(diagnostics)},
        'limitations':[
           'Source-checked review transcriptions are not production ingestion or original-vintage observations.',
           'Prices, credit, fiscal and market positioning are context, not duplicated votes in real-economy momentum.',
           'Three-month SA growth measures activity pace. Slopes of YoY/YTD/PMI readings measure changes in reported rates, not GDP velocity.',
           'Short histories, seasonal revision mixtures and missing calendar periods do not produce acceleration.',
           'Candidate automatic enrollment is NBS-only with source attribution; SAFE stays held for commercial-republication permission, while NEA/MOF remain held for separate source/index/robots admission.'
        ]}


def extend_snapshot(base_snapshot:dict, economy:dict) -> dict:
    """One publication owner; no mutation of the original four-panel snapshot."""
    if 'economy' in base_snapshot:raise ValueError('existing economy extension requires explicit version reconciliation')
    out=deepcopy(base_snapshot);out['economy']=deepcopy(economy);return out
