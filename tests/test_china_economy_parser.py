from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collectors.china_economy_release_parser import (parse_sa_html,parse_pmi_html,parse_mof_text,checked_source,stamp_observations,expand_table)
from bs4 import BeautifulSoup


def sa_html(values=None):
 values=values or [.28,.05,.4,.76,.11,.54]
 return '<p>根据季节调整模型对环比增速修订。</p><table><tr><th>年度</th><th>月份</th><th>环比增速(%)</th></tr>'+''.join(f'<tr><td>2026年</td><td>{i+3}月</td><td>{v}</td></tr>' for i,v in enumerate(values))+'</table>'

def pmi_html():
 # Parser-shape fixture only; no synthetic data is shipped as economic history.
 headers=[['PMI','生产','新订单','原材料库存','从业人员','供应商配送时间'],['新出口订单','进口','采购量','主要原材料购进价格','出厂价格','产成品库存','在手订单','生产经营活动预期'],['商务活动','新订单','投入品价格','销售价格','从业人员','业务活动预期']]
 return ''.join('<table><tr><th>年月</th>'+''.join('<th>'+h+'</th>' for h in hs)+'</tr>'+''.join('<tr><td>2026年'+str(m)+'月</td>'+''.join('<td>50.1</td>' for h in hs)+'</tr>' for m in range(3,9))+'</table>' for hs in headers)

def test_sa_parser_exact_values():
 r=parse_sa_html(sa_html(),'industrial_sa','2026-08');assert len(r)==6 and r[-1]['value']==.54

def test_sa_table_rowspan():
 s='<p>季节调整</p><table><tr><th>年度</th><th>月份</th><th>环比增速</th></tr><tr><td rowspan="6">2026年</td><td>3月</td><td>0.1</td></tr>'+''.join(f'<tr><td>{m}月</td><td>0.1</td></tr>' for m in range(4,9))+'</table>'
 assert len(parse_sa_html(s,'retail_sa','2026-08'))==6

def test_sa_missing_declaration():
 with pytest.raises(ValueError,match='declaration'):parse_sa_html(sa_html().replace('季节调整','别的东西'),'industrial_sa','2026-08')

def test_sa_duplicate_table():
 with pytest.raises(ValueError,match='exactly one'):parse_sa_html(sa_html()+sa_html(),'industrial_sa','2026-08')

def test_sa_missing_month():
 h=sa_html().replace('<td>5月</td>','<td>4月</td>')
 with pytest.raises(ValueError):parse_sa_html(h,'industrial_sa','2026-08')

def test_sa_wrong_period():
 with pytest.raises(ValueError,match='reference period'):parse_sa_html(sa_html(),'industrial_sa','2026-09')

def test_sa_unknown_metric():
 with pytest.raises(ValueError,match='admitted'):parse_sa_html(sa_html(),'profits','2026-08')

def test_sa_bad_rate():
 with pytest.raises(ValueError,match='invalid SA'):parse_sa_html(sa_html([.1]*5+[-100]),'industrial_sa','2026-08')

def test_pmi_tables():
 r=parse_pmi_html(pmi_html(),'2026-08');assert len(r)==120
 assert {v['metric_id'] for v in r}>={'pmi_jobs','pmi_nonmfg_jobs','pmi_orders','pmi_exports'}

def test_pmi_bad_diffusion():
 with pytest.raises(ValueError):parse_pmi_html(pmi_html().replace('50.1','110.1',1),'2026-08')

def test_pmi_duplicate():
 with pytest.raises(ValueError,match='duplicate'):parse_pmi_html(pmi_html()+pmi_html(),'2026-08')

def test_pmi_partial_family():
 with pytest.raises(ValueError):parse_pmi_html(pmi_html().split('</table>')[0]+'</table>','2026-08')

FISCAL='''2026年1—8月财政收支情况。全国一般公共预算收入156633亿元，同比增长5.7%。全国一般公共预算支出181451亿元，同比增长1.2%。全国政府性基金预算收入21419亿元，同比下降19.0%。全国政府性基金预算支出51948亿元，同比下降17.0%。国有土地使用权出让收入13753亿元，同比下降28.6%。债务付息支出9188亿元，同比增长5.4%。'''

def test_fiscal_amounts_and_direction():
 d={r['metric_id']:r['value'] for r in parse_mof_text(FISCAL,'2026-08')}
 assert d['fiscal_general_revenue']==15663.3 and d['fiscal_land_revenue_growth']==-28.6
 assert d['fiscal_interest_spending']==918.8

def test_fiscal_no_missing_zero():
 with pytest.raises(ValueError):parse_mof_text(FISCAL.replace('9188','—'),'2026-08')

def test_fiscal_ambiguous_duplicate():
 with pytest.raises(ValueError):parse_mof_text(FISCAL+FISCAL,'2026-08')

def test_fiscal_no_wrong_reference():
 with pytest.raises(ValueError):parse_mof_text(FISCAL,'2026-07')

@pytest.mark.parametrize('url',['http://www.stats.gov.cn/x','https://stats.gov.cn.evil.test/x','https://user:pass@www.stats.gov.cn/x','https://localhost/x','https://www.stats.gov.cn:123/x'])
def test_origin_allowlist(url):
 with pytest.raises(ValueError):checked_source(url,'2026-09-15T10:00:00+08:00',html='fixture')

def test_acquisition_receipt_not_invented():
 r=checked_source('https://www.stats.gov.cn/sj/test.html','2026-09-15T10:00:00+08:00','2026-09-29T12:00:00+08:00',html='test')
 assert len(r['response_sha256'])==64 and r['observed_at']=='2026-09-29T12:00:00+08:00'
 out=stamp_observations([{'metric_id':'a','period':'2026-08','value':1}], 's', r, {'a':{'definition_id':'a.v1'}})
 assert out[0]['raw_response_sha256']==r['response_sha256']

def test_future_publication_rejected():
 with pytest.raises(ValueError):checked_source('https://www.stats.gov.cn/sj/test.html','2027-01-01T00:00:00+08:00','2026-09-29T00:00:00+08:00')

def test_safe_monthly_cny_not_usd_or_ytd():
 from collectors.china_economy_release_parser import parse_safe_text
 text='2026年8月，银行结汇17090亿元人民币，售汇13800亿元人民币。2026年1-8月，银行累计结汇143111亿元人民币。按美元计值，2026年8月，银行结汇2518亿美元，售汇2033亿美元。2026年8月，银行代客涉外收入52718亿元人民币，对外付款48486亿元人民币。'
 r=parse_safe_text(text,'2026-08');assert [p['value'] for p in r]==[1709,1380,5271.8,4848.6]
 with pytest.raises(ValueError):parse_safe_text(text,'2026-07')

def test_safe_does_not_silently_use_usd():
 from collectors.china_economy_release_parser import parse_safe_text
 with pytest.raises(ValueError):parse_safe_text('2026年8月，银行结汇2518亿美元，售汇2033亿美元。','2026-08')


def published_twins(content,other=None):
 return '<div class="detail-text-content"><div class="txt-content">'+content+'</div></div><div class="mobile-content"><div class="mobile-news-content">'+(other if other is not None else content)+'</div></div>'

def test_identical_publisher_article_twins_are_not_duplicate_statistics():
 assert len(parse_sa_html(published_twins(sa_html()),'industrial_sa','2026-08'))==6
 assert len(parse_pmi_html(published_twins(pmi_html()),'2026-08'))==120

def test_disagreeing_publisher_twins_are_not_silently_deduplicated():
 with pytest.raises(ValueError,match='disagree'):
  parse_sa_html(published_twins(sa_html(),sa_html().replace('0.54','0.53')),'industrial_sa','2026-08')

def test_ambiguous_publisher_containers_refused():
 with pytest.raises(ValueError,match='ambiguous'):
  parse_sa_html(published_twins(sa_html())+published_twins(sa_html()),'industrial_sa','2026-08')

def test_duplicate_table_inside_one_publisher_article_still_refused():
 with pytest.raises(ValueError,match='exactly one'):
  parse_sa_html(published_twins(sa_html()+sa_html()),'industrial_sa','2026-08')

def test_pmi_two_level_merged_header_selects_component_row():
 h=pmi_html().replace('<tr><th>年月</th><th>PMI</th>','<tr><th></th><th>PMI</th></tr><tr><th>年月</th><th>PMI</th>',1)
 r=parse_pmi_html(published_twins(h),'2026-08')
 assert len(r)==120 and len({p['metric_id'] for p in r})==20
