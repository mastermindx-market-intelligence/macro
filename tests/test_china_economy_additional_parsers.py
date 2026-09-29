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
