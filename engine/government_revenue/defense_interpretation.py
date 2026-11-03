"""Closed bilingual economic interpretation of already admitted issuer facts.

Pure presentation catalogue: no intake, attribution, forecasts, valuation,
financial calculation, or admission. Canonical reconstruction at read time
prevents an altered narrative from acquiring authority through a new hash.
"""
import math

SCHEMA='defense_economic_interpretation.v1'
CORE=('defense_segment_sales','defense_segment_operating_profit','defense_segment_margin')
SEGMENTS={'LMT':('Missiles and Fire Control','导弹与火控'),'RTX':('Raytheon','雷神'),'NOC':('Defense Systems','防务系统'),'LHX':('Missile Solutions','导弹解决方案')}


def _refs(index,*metrics):
    return [{'fact_id':index[k]['fact_id'],'owner_ref':index[k]['owner_ref']} for k in metrics if k in index]


def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('interpretation_numeric_fact_invalid')
    return format(value,',g')


def build_defense_interpretation(ticker,facts):
    """Return only canonical content; unsupported/missing baselines stay absent."""
    if ticker not in SEGMENTS:return None
    index={f['fact_id'].rsplit(':',1)[-1]:f for f in facts}
    if any(k not in index for k in CORE):return None
    core=[index[k] for k in CORE]
    if len({f['period'] for f in core})!=1 or [f['fact_class'] for f in core]!=['reported_segment_sales','reported_segment_operating_profit','reported_segment_margin'] or [f['unit'] for f in core]!=['USD_million','USD_million','percent']:
        return None
    segment,zh=SEGMENTS[ticker];period=core[0]['period'];sales,profit,margin=(_number(f['value']) for f in core)
    def chain(stage,state,en,cn,*metrics):return {'stage':stage,'state':state,'summary_en':en,'summary_zh':cn,'fact_refs':_refs(index,*metrics),'owner_refs':[]}
    def case(kind,assumption,assumption_zh,implication,implication_zh,invalidation,invalidation_zh,*metrics):
        return {'kind':kind,'assumption_en':assumption,'assumption_zh':assumption_zh,'implication_en':implication,'implication_zh':implication_zh,'invalidation_en':invalidation,'invalidation_zh':invalidation_zh,'fact_refs':_refs(index,*metrics),'owner_refs':[]}
    chains=[
        chain('demand','unknown','Reported segment sales are historical revenue; they do not measure new program funding, funded orders, or future issuer demand.','已披露分部销售额属于历史收入，不能作为新增项目资金、已获资金订单或未来发行人需求的数值。','defense_segment_sales'),
        chain('capture','unknown',f'{segment} is verified issuer segment context. Specific procurement roles, workshare, and conversion timing remain unqualified.',f'{zh}是已核验的发行人分部资料；具体采购角色、项目份额及转化时间仍未核验。',*CORE),
        chain('margin','reported',f'{period} {segment}: sales USD {sales} million, reported operating profit USD {profit} million, margin {margin}%.',f'{period} {zh}：销售额{sales}百万美元、已披露营业利润{profit}百万美元、利润率{margin}%。',*CORE),
        chain('common_cash','unknown','Reported segment profit does not fix cash available to common shareholders; payment timing, working capital, capital spending, and corporate claims remain unquantified.','分部营业利润不能确定普通股股东可得现金；收款时间、营运资金、资本支出及公司层面索偿仍未量化。','defense_segment_operating_profit')]
    scenarios=[
        case('conditional_baseline',f'Assume verified contract work is delivered and future cost discipline is consistent with the reported {segment} baseline.',f'假设已核验合约工作获交付，且未来成本控制与已披露{zh}基准一致。','Work may convert into profit under those conditions; payment timing and investment needs still determine cash conversion. No revenue increment or per-share value is estimated.','在这些条件下，工作量可能转化为利润；收款时间及投资需要仍决定现金转化。不估计收入增量或每股价值。','A new unfavorable charge, weaker reported margin, delivery delay, or source correction weakens this premise.','新增不利费用、已披露利润率转弱、交付延误或来源更正，均削弱这一前提。',*CORE),
        case('downside','Assume delivery or qualification takes longer, or costs and investment needs rise before customer payments.','假设交付或认证需时更长，或成本及投资需要在客户付款前上升。','More program funding can coexist with weaker margin or cash conversion. Issuer workshare and the size of any effect are not assumed.','项目资金增加仍可能伴随利润率或现金转化转弱。不假设发行人项目份额或影响幅度。','Verified delivery, cost, margin, and cash evidence contradicting these conditions would weaken the downside case.','经核验的交付、成本、利润率及现金证据若与这些条件相反，将削弱下行情景。','defense_segment_operating_profit','defense_segment_margin')]
    unknowns=['program_workshare','issuer_specific_forward_demand','revenue_conversion_timing','working_capital','capital_spending','common_shareholder_cash','observed_market_expectations','numerical_valuation']
    prior_period=str(int(period[:4])-1)+period[4:] if len(period)==6 and period[:4].isdigit() else None
    noc_qualified=all(k in index for k in ('siaw_unfavorable_eac','sentinel_prior_favorable_eac','defense_segment_prior_margin')) and index['siaw_unfavorable_eac']['period']==period and index['sentinel_prior_favorable_eac']['period']==index['defense_segment_prior_margin']['period']==prior_period
    if ticker=='NOC' and noc_qualified:
        adverse=index['siaw_unfavorable_eac'];prior=index['sentinel_prior_favorable_eac'];oldmargin=index['defense_segment_prior_margin']
        chains[2]=chain('margin','reported',f'{period} margin {margin}% versus {oldmargin["period"]} { _number(oldmargin["value"])}%; SiAW unfavorable EAC USD {_number(adverse["value"])} million is current, Sentinel favorable EAC USD {_number(prior["value"])} million is prior and a different program.',f'{period}利润率{margin}%，对比{oldmargin["period"]}的{_number(oldmargin["value"])}%；当前SiAW不利EAC为{_number(adverse["value"])}百万美元，Sentinel有利EAC{_number(prior["value"])}百万美元属于前期及不同项目。','defense_segment_margin','defense_segment_prior_margin','siaw_unfavorable_eac','sentinel_prior_favorable_eac')
        chains[3]=chain('common_cash','unknown','An EAC estimate adjustment is not a cash-flow timing measure. The prior Sentinel credit cannot be netted against the current SiAW charge to establish cash capture.','EAC估计调整不是现金流时间指标；不能以此前Sentinel有利调整抵销当前SiAW不利费用来推定现金获益。','siaw_unfavorable_eac','sentinel_prior_favorable_eac')
        scenarios=[case('conditional_baseline','Assume no further unfavorable cost-estimate revisions and no additional schedule deterioration.','假设不再出现不利成本估计修订，且进度不进一步恶化。','That could reduce the cost-risk concern; it does not establish margin reversion to the prior-year comparison or normalized common-shareholder cash.','这可能减轻成本风险疑虑，但不能证明利润率回归此前对比期水平，或普通股股东现金达到正常化水平。','Further unfavorable EACs or weaker reported margin invalidate the stabilization premise.','后续不利EAC调整或已披露利润率转弱，将否定成本稳定这一前提。','siaw_unfavorable_eac','defense_segment_margin','defense_segment_prior_margin'),case('downside','Assume further unfavorable EAC revisions arise while program funding or backlog remains available.','假设项目资金或积压订单仍存在，但继续出现不利EAC修订。','Demand availability may then fail to protect margin and cash conversion. The prior favorable Sentinel item is a separate program/period, not an offset.','需求存在也可能无法保障利润率及现金转化；此前Sentinel有利项目属于不同项目及期间，不是抵销项。','Source-qualified cost recovery and margin evidence inconsistent with continuing estimate losses would weaken this case.','经来源核验的成本回收及利润率证据若与持续估计损失不一致，将削弱该情景。','siaw_unfavorable_eac','sentinel_prior_favorable_eac','defense_segment_margin')]
    lhx_metrics=('msl_preferred_payout_terms','msl_qipo_conversion_terms','msl_nonipo_redemption_terms','space_business_sale_completed_terms','space_business_sale_retained_scope','space_business_sale_pending_terms')
    lhx_qualified=all(k in index for k in lhx_metrics) and all(token in str(index[metric]['value']) for metric,token in (
        ('msl_qipo_conversion_terms','20%'),('msl_qipo_conversion_terms','10%'),
        ('space_business_sale_completed_terms','$845 million'),('space_business_sale_retained_scope','~40%'),
        ('space_business_sale_retained_scope','RS-25'),('msl_nonipo_redemption_terms','110%')))
    if ticker=='LHX' and lhx_qualified:
        terms=('msl_preferred_payout_terms','msl_qipo_conversion_terms','msl_nonipo_redemption_terms')
        sale=('space_business_sale_pending_terms','space_business_sale_completed_terms','space_business_sale_retained_scope')
        chains[1]=chain('capture','reported','Completed space-business majority sale: USD 845 million total enterprise value, about 40% of the new company retained, RS-25 excluded; prior pending net-value basis is separate.','已完成航天业务多数股权出售报告总企业价值845百万美元、保留约40%股权，RS-25不在出售范围；此前待完成交易的净价值口径另列。',*sale)
        chains[3]=chain('common_cash','conditional','Preferred liquidation preference, conditional QIPO conversion and non-IPO redemption constrain common-holder transmission; the approximately 10% QIPO stake is a company expectation, not current ownership.','优先股清算优先额、有条件QIPO转换及无IPO赎回条款约束普通股获益路径；QIPO约10%股权是公司预期，不是当前持股。',*terms)
        scenarios=[case('conditional_baseline','Assume the disclosed preferred terms remain in force and a qualifying IPO meets the contractual conditions.','假设已披露优先股条款继续有效，且合资格IPO符合合约条件。','Conversion at the disclosed 20% discount uses a variable number of subsidiary common shares; ownership depends on IPO valuation. No current dilution percentage or LHX per-share value is inferred.','按已披露20%折让转换时，子公司普通股数量可变，持股取决于IPO估值；不推定当前摊薄比例或LHX每股价值。','A change in contractual terms, a nonqualifying IPO, or failure to meet conditions invalidates this branch.','合约条款变化、IPO不符合资格或条件未达成，将使该分支失效。','msl_qipo_conversion_terms','msl_preferred_payout_terms'),case('downside','Assume a qualifying IPO does not occur by the disclosed deadline; apply the disclosed milestone-dependent redemption alternatives, not an assumed ordinary-share cash payout.','假设合资格IPO未在已披露期限前发生；适用条款所述、取决于里程碑的赎回备选方式，而非假设普通股获得现金支付。','The cumulative preferred claim and contractual redemption premium can change the residual economic path. Reported segment profit and the sale enterprise value do not equal common-holder cash.','累计优先索偿及合约赎回溢价可能改变剩余权益路径；分部营业利润及出售企业价值均不等于普通股股东现金。','A qualifying conversion or source-qualified evidence of different milestone/redemption treatment would invalidate this branch.','合资格转换，或经来源核验的不同里程碑／赎回处理证据，将使该分支失效。',*terms,'defense_segment_operating_profit')]
        unknowns+=['preferred_common_cash_bridge','sale_net_proceeds_to_common','future_QIPO_valuation']
    # Consolidated cash is historical issuer context, not segment cash or
    # cash distributable to common shareholders. Keep corporate claims intact.
    cash_metrics=('issuer_operating_cash_quarter','issuer_operating_cash_quarter_prior',
                  'issuer_free_cash_quarter','issuer_free_cash_quarter_prior',
                  'issuer_operating_cash_half_year','issuer_operating_cash_half_year_prior',
                  'issuer_free_cash_half_year','issuer_free_cash_half_year_prior')
    if all(k in index for k in cash_metrics):
        cash=[index[k] for k in cash_metrics]
        if all(f['fact_class']=='reported_cashflow' and f['unit']=='USD_million' for f in cash):
            cf='adjusted free cash flow' if ticker=='NOC' else 'free cash flow'
            cfzh='调整后自由现金流' if ticker=='NOC' else '自由现金流'
            values=[_number(f['value']) for f in cash]
            en=(f" Consolidated {cash[0]['period']} operating cash USD {values[0]} million "
                f"versus {cash[1]['period']} {values[1]} million; {cf} {values[2]} versus {values[3]} million. "
                f"{cash[4]['period']} operating cash {values[4]} versus {cash[5]['period']} {values[5]} million; "
                f"{cf} {values[6]} versus {values[7]} million. Quarter and half-year durations are separate; "
                "these are issuer-reported cash measures, not segment or distributable common-holder cash.")
            cn=(f" 公司合并{cash[0]['period']}经营现金为{values[0]}百万美元，对比{cash[1]['period']}的{values[1]}百万美元；"
                f"{cfzh}为{values[2]}对比{values[3]}百万美元。{cash[4]['period']}经营现金为{values[4]}对比"
                f"{cash[5]['period']}的{values[5]}百万美元，{cfzh}为{values[6]}对比{values[7]}百万美元。"
                "季度与半年度期间分别记录；这些是公司披露现金指标，并非分部现金或可分配给普通股股东的现金。")
            chains[3]['summary_en']+=en;chains[3]['summary_zh']+=cn
            chains[3]['fact_refs']+=_refs(index,*cash_metrics)
    backlog=[k for k in index if k.startswith('issuer_backlog')]
    if backlog:
        current=index.get('issuer_backlog')
        if current is not None and current['fact_class']=='reported_backlog':
            amount=_number(current['value']);unit='million' if current['unit']=='USD_million' else 'billion'
            chains[0]['summary_en']+=f" Reported consolidated backlog stock: USD {amount} {unit} at {current['period']}. Funding classifications and issuer definitions remain separate; backlog is not revenue or a conversion forecast."
            chains[0]['summary_zh']+=f" 披露公司合并积压订单存量为{amount}{'百万' if unit=='million' else '十亿'}美元，期间为{current['period']}。资金分类及发行人口径分别保留；积压订单不是收入或转化预测。"
            if ticker=='RTX':
                chains[0]['summary_en']+=' The company total includes commercial and defense backlog; it is not Raytheon segment backlog.'
                chains[0]['summary_zh']+=' 公司总额包括商用及防务积压订单，并非雷神分部积压订单。'
            chains[0]['fact_refs']+=_refs(index,*backlog)
    guidance=[k for k in index if '_guidance_' in k and index[k]['fact_class']=='reported_guidance']
    if guidance:
        chains[3]['summary_en']+=' Full-year issuer cash guidance is a forecast with its original unit and accounting basis, not reported cash or an achieved conversion rate. Prior-update comparisons quote this release, not historical vintages.'
        chains[3]['summary_zh']+=' 全年发行人现金指引为预测，保留原单位及会计口径，并非已实现现金或已达到的转化率。此前更新对比引述本次披露，并非历史版本。'
        chains[3]['fact_refs']+=_refs(index,*guidance[:1])
    components=[k for k in index if '_cash_change_half_year' in k]
    if components:
        chains[3]['summary_en']+=' Signed first-half cash-flow movements in receivables, contract assets, inventories, payables and contract liabilities are separately disclosed components; no working-capital stock or total is inferred.'
        chains[3]['summary_zh']+=' 应收账款、合约资产、存货、应付账款及合约负债的上半年现金流变动为分别披露的带正负号项目；不推定营运资金存量或合计。'
        if len(chains[3]['fact_refs'])<12:
            chains[3]['fact_refs']+=_refs(index,*components[:1])
    return {'schema':SCHEMA,'chain':chains,'scenarios':scenarios,'unknowns':unknowns}


def validate_defense_interpretation(value,ticker,facts):
    if value is None:return
    if value!=build_defense_interpretation(ticker,facts):
        raise ValueError('interpretation_not_canonical_admitted_fact_projection')
