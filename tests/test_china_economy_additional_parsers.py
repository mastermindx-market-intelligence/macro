"""Factual clause fixtures; not a complete article or synthetic market history."""
import pytest
from collectors.china_economy_release_parser import parse_corporate_text,parse_nea_text

CORPORATE='''2026年1—8月份全国规模以上工业企业利润增长15.7%。
1—8月份，全国规模以上工业企业实现利润总额52719.8亿元，同比增长15.7%。
1—8月份，主要行业利润情况如下：计算机、通信和其他电子设备制造业利润同比增长1.1倍，有色金属冶炼和压延加工业增长82.9%，化学原料和化学制品制造业增长51.0%，汽车制造业下降16.0%，黑色金属冶炼和压延加工业下降62.4%，电力、热力生产和供应业下降15.1%。
1—8月份，规模以上工业企业实现营业收入93.09万亿元，同比增长6.6%；营业收入利润率为5.66%。
8月末，资产负债率为58.5%。8月末，规模以上工业企业应收账款29.48万亿元，同比增长9.0%；产成品存货7.36万亿元，增长11.0%。
产成品存货周转天数为21.3天，同比增加0.6天；应收账款平均回收期为72.2天，同比增加0.9天。
8月份，规模以上工业企业利润同比增长4.2%。'''
NEA='''2026年8月，全社会用电量再破万亿，达到10332亿千瓦时，同比增长1.7%；用电负荷创历史新高。
工业用电量6065亿千瓦时，同比增长2.7%，高技术及装备制造业用电量保持较快增长势头，达到1222亿千瓦时，同比增长7.2%。第三产业用电量2155亿千瓦时，同比增长5.1%；其中，充换电服务业、互联网数据服务用电量增长强劲，分别为172亿、102亿千瓦时，增速分别达到51.2%、37.9%。城乡居民生活用电量1883亿千瓦时，同比下降4.0%。
1—8月，全社会用电量累计71730亿千瓦时，同比增长4.3%。'''

def test_corporate_ytd_month_and_times_not_confused():
 x={r['metric_id']:r['value'] for r in parse_corporate_text(CORPORATE,'2026-08')}
 assert len(x)==19 and x['profits_ytd']==15.7 and x['profits_month']==4.2
 assert x['sector_profit_electronics']==pytest.approx(110)
 assert x['sector_profit_auto']==-16 and x['receivable_days']==72.2
 assert x['receivables']==29.48 and x['profit_margin']==5.66

@pytest.mark.parametrize('a,b',[('29.48万亿元','29.48亿元'),('72.2天','72.2个月'),('应收账款平均回收期','不同概念'),('1.1倍','由亏转盈')])
def test_corporate_unit_or_definition_change_fails(a,b):
 with pytest.raises(ValueError):parse_corporate_text(CORPORATE.replace(a,b),'2026-08')

def test_corporate_duplicate_not_first_match():
 with pytest.raises(ValueError):parse_corporate_text(CORPORATE+CORPORATE,'2026-08')

def test_corporate_wrong_month():
 with pytest.raises(ValueError):parse_corporate_text(CORPORATE,'2026-07')

def test_corporate_direction_stays_signed():
 s=CORPORATE.replace('同比增加0.9天','同比减少0.9天')
 assert {r['metric_id']:r['value'] for r in parse_corporate_text(s,'2026-08')}['cashdays_change']==-.9

def test_nea_monthly_vs_ytd_and_paired_labels():
 x={r['metric_id']:r['value'] for r in parse_nea_text(NEA,'2026-08')}
 assert len(x)==7 and x['power_total']==1.7 and x['power_households']==-4
 assert x['power_charging']==51.2 and x['power_datacenters']==37.9

@pytest.mark.parametrize('a,b',[('工业用电量6065','工业发电量6065'),('1—8月','全年'),('充换电服务业、互联网数据服务','互联网数据服务、充换电服务业'),('同比下降4.0%','同比下降—%')])
def test_nea_cannot_guess_changed_scope_or_order(a,b):
 with pytest.raises(ValueError):parse_nea_text(NEA.replace(a,b),'2026-08')

def test_nea_wrong_reference():
 with pytest.raises(ValueError):parse_nea_text(NEA,'2026-07')


# Supplemental current-period evidence: adversarial synthetic fixtures only.
# The committed catalog, source owner and old seasonal histories are unchanged.
from collectors.china_economy_release_parser import parse_activity_detail


def _detail_release(family, table='', prose='', period='2026-08'):
    year, month = period.split('-'); month = str(int(month))
    labels = {'industry': '规模以上工业增加值', 'retail': '社会消费品零售总额',
              'investment': '固定资产投资', 'pmi': '采购经理指数'}
    label_period = f'1—{month}' if family == 'investment' else month
    title = f'{year}年{label_period}月份{labels[family]}'
    return f'<html><head><meta name="ArticleTitle" content="{title}"></head><body><h1>{title}</h1>{prose}{table}</body></html>'


def _detail_table(rows, family='retail', reverse_periods=False):
    if family == 'investment':
        header = '<tr><th>指标</th><th>同比增长(%)</th></tr>'
    else:
        periods = ['1—8月', '1—8月', '8月', '8月'] if reverse_periods else ['8月', '8月', '1—8月', '1—8月']
        header = '<tr><th>指标</th>'+''.join(f'<th>{p}</th>' for p in periods)+'</tr>'
        header += '<tr><th>指标</th><th>绝对量(亿元)</th><th>同比增长(%)</th><th>绝对量(亿元)</th><th>同比增长(%)</th></tr>'
    return '<table>'+header+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</table>'


def _detail_map(html, family='retail', period='2026-08'):
    points, receipt = parse_activity_detail(html, family, period)
    return {p['metric_id']: p['value'] for p in points}, receipt


def test_detail_monthly_column_is_not_ytd_or_absolute_amount():
    table = _detail_table([['社会消费品零售总额', '40000', '0.4', '320000', '1.1'],
                           ['其中：除汽车以外的消费品零售额', '36000', '2.5', '300000', '2.7']])
    values, meta = _detail_map(_detail_release('retail', table))
    assert values == {'retail_yoy': 0.4, 'retail_exauto': 2.5}
    assert meta['history_inferred'] is False and 'retail_rural' in meta['null_reasons']


def test_detail_follows_header_when_columns_move():
    table = _detail_table([['社会消费品零售总额', '320000', '1.1', '40000', '0.4']], reverse_periods=True)
    assert _detail_map(_detail_release('retail', table))[0]['retail_yoy'] == 0.4


@pytest.mark.parametrize('raw', ['—', '…', 'NaN', 'inf', '-100.1', '0.4个百分点', '1,234', 'true', ''])
def test_detail_bad_growth_is_not_assigned_zero(raw):
    table = _detail_table([['社会消费品零售总额', '40000', raw, '320000', '1.1']])
    values, meta = _detail_map(_detail_release('retail', table))
    assert 'retail_yoy' not in values and 'retail_yoy' in meta['null_reasons']


@pytest.mark.parametrize('raw,expected', [('0', 0), ('-0.0', 0), ('-100', -100), ('150.5', 150.5)])
def test_detail_real_zero_or_large_change_survives(raw, expected):
    table = _detail_table([['社会消费品零售总额', '40000', raw, '320000', '1.1']])
    assert _detail_map(_detail_release('retail', table))[0]['retail_yoy'] == expected


@pytest.mark.parametrize('change', ['wrong_month', 'no_growth_unit', 'duplicate_column', 'truncated_row', 'duplicate_table', 'duplicate_row'])
def test_detail_ambiguous_table_is_withheld(change):
    row = ['社会消费品零售总额', '40000', '0.4', '320000', '1.1']
    table = _detail_table([row])
    if change == 'wrong_month': table = table.replace('<th>8月</th>', '<th>7月</th>')
    if change == 'no_growth_unit': table = table.replace('同比增长(%)', '绝对量')
    if change == 'duplicate_column': table = table.replace('1—8月', '8月')
    if change == 'truncated_row': table = _detail_table([row[:-1]])
    if change == 'duplicate_table': table += table
    if change == 'duplicate_row': table = _detail_table([row, row])
    values, receipt = _detail_map(_detail_release('retail', table))
    assert values == {} and receipt['status'] == 'withheld'


def test_detail_investment_remains_cumulative_and_exact_category():
    rows = [['固定资产投资(不含农户)', '-7.2'], ['其中：民间投资', '-10.1'],
            ['制造业', '-2.3'], ['设备工器具购置', '9.3'], ['汽车制造业', '99']]
    prose = '<p>基础设施投资（口径详见附注1）同比下降4.0%。知识产权产品投资同比增长9.2%。东部地区投资同比下降9.4%。</p>'
    values, receipt = _detail_map(_detail_release('investment', _detail_table(rows, 'investment'), prose), 'investment')
    assert values['investment_ytd'] == -7.2 and values['manufacturing_investment'] == -2.3
    assert values['investment_equipment'] == 9.3 and values['investment_infra'] == -4
    assert values['investment_ip'] == 9.2 and values['regional_investment_east'] == -9.4
    assert 'regional_investment_west' in receipt['null_reasons']


@pytest.mark.parametrize('denom,count,accepted', [(41, 29, True), (41, 0, True), (41, 42, False), (42, 29, False)])
def test_detail_count_denominator_is_an_admission_gate(denom, count, accepted):
    text = f'<p>{denom}个大类行业中有{count}个行业增加值保持同比增长。626种产品中有286种产品产量同比增长。</p>'
    values, receipt = _detail_map(_detail_release('industry', prose=text), 'industry')
    assert ('industry_positive' in values) == accepted
    assert values['products_positive'] == 286
    if not accepted: assert 'industry_positive' in receipt['null_reasons']


def test_detail_pmi_reads_levels_not_previous_month_changes():
    text = '<p>大型企业PMI为50.6%，比上月上升1.1个百分点；中型企业PMI为49.4%，比上月下降0.3个百分点；小型企业PMI为47.9%，比上月上升0.5个百分点。建筑业商务活动指数为46.9%，服务业商务活动指数为49.3%。</p>'
    values, receipt = _detail_map(_detail_release('pmi', prose=text), 'pmi')
    assert values == {'pmi_large': 50.6, 'pmi_medium': 49.4, 'pmi_small': 47.9, 'pmi_construction': 46.9, 'pmi_services': 49.3}
    assert receipt['status'] == 'complete' and receipt['history_inferred'] is False


def test_detail_pmi_reads_ordered_medium_small_pair_from_current_nbs_wording():
    text = '<p>大型企业PMI为50.6%，与上月持平；中、小型企业PMI分别为49.7%和48.9%，比上月上升0.3个和1.0个百分点。</p>'
    points, receipt = parse_activity_detail(
        _detail_release('pmi', prose=text, period='2026-09'), 'pmi', '2026-09')
    values = {p['metric_id']: p['value'] for p in points}
    assert values['pmi_large'] == 50.6
    assert values['pmi_medium'] == 49.7
    assert values['pmi_small'] == 48.9
    assert 'pmi_medium' not in receipt['null_reasons']
    assert 'pmi_small' not in receipt['null_reasons']


@pytest.mark.parametrize('text', ['大型企业PMI为101%。', '大型企业PMI为50.6%。大型企业PMI为50.7%。', '大型企业PMI比上月上升1.1个百分点。'])
def test_detail_pmi_invalid_or_ambiguous_is_missing(text):
    values, receipt = _detail_map(_detail_release('pmi', prose='<p>'+text+'</p>'), 'pmi')
    assert 'pmi_large' not in values and 'pmi_large' in receipt['null_reasons']


def test_detail_never_invents_prior_points_from_reported_deltas():
    points, _ = parse_activity_detail(_detail_release('pmi', prose='<p>大型企业PMI为50.6%，比上月上升1.1个百分点。</p>'), 'pmi', '2026-08')
    assert points == [{'metric_id': 'pmi_large', 'period': '2026-08', 'value': 50.6}]


def test_detail_wrong_release_period_is_rejected():
    with pytest.raises(ValueError, match='reference'):
        parse_activity_detail(_detail_release('pmi', period='2026-07'), 'pmi', '2026-08')


def test_detail_repeated_article_copies_must_agree():
    body = '<p>大型企业PMI为50.6%。</p>'
    desktop = '<div class="detail-text-content"><div class="txt-content">'+body+'</div></div>'
    mobile = '<div class="mobile-content"><div class="mobile-news-content">'+body+'</div></div>'
    values, _ = _detail_map(_detail_release('pmi', prose=desktop+mobile), 'pmi')
    assert values['pmi_large'] == 50.6
    with pytest.raises(ValueError, match='disagree'):
        _detail_map(_detail_release('pmi', prose=desktop+mobile.replace('50.6', '50.7')), 'pmi')


def test_detail_investment_requires_a_cumulative_reference_not_monthly_only():
    table = _detail_table([['固定资产投资(不含农户)', '-7.2']], 'investment')
    html = _detail_release('investment', table).replace('2026年1—8月份', '2026年8月份')
    with pytest.raises(ValueError, match='reference'):
        _detail_map(html, 'investment')


@pytest.mark.parametrize('extra', [
    '中型企业PMI为52.0%。',
    '中、小型企业PMI分别为52.0%和48.9%。',
    '中、小型企业PMI分别为49.7%和48.9%。',
])
def test_ordered_pmi_pair_conflicts_fail_closed(extra):
    text = '<p>中、小型企业PMI分别为49.7%和48.9%。' + extra + '</p>'
    values, receipt = _detail_map(
        _detail_release('pmi', prose=text, period='2026-09'), 'pmi', '2026-09')
    assert 'pmi_medium' not in values
    assert 'pmi_medium' in receipt['null_reasons']


@pytest.mark.parametrize('pair', ['101%和48.9%', '49.7%和101%'])
def test_ordered_pmi_pair_out_of_range_withholds_both(pair):
    values, receipt = _detail_map(_detail_release(
        'pmi', prose='<p>中、小型企业PMI分别为'+pair+'。</p>',
        period='2026-09'), 'pmi', '2026-09')
    assert 'pmi_medium' not in values and 'pmi_small' not in values


def test_ordered_pmi_pair_zero_is_not_missing():
    values, _ = _detail_map(_detail_release(
        'pmi', prose='<p>中、小型企业PMI分别为0%和48.9%。</p>',
        period='2026-09'), 'pmi', '2026-09')
    assert values['pmi_medium'] == 0
    assert values['pmi_small'] == 48.9
