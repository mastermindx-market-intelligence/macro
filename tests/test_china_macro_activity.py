from datetime import date, datetime, timezone
import json

import pandas as pd
import pytest

from collectors.china_property_activity import parse_release, release_links, origin_url, number
from engine.china_macro_evidence import nominal_gdp_four_quarters, build_snapshot, true_credit_impulse

URL='https://www.stats.gov.cn/sj/zxfb/202609/t20260915_1965310.html'
NOW=datetime(2026,9,29,tzinfo=timezone.utc)

def html(extra='', pub='2026/09/15 10:00', title='2026年1—8月份全国房地产市场基本情况'):
    rows=[('房地产开发投资（亿元）',47979,-19.9),('房屋新开工面积（万平方米）',29894,-24.8),('新建商品房销售面积（万平方米）',49880,-12.1),('房地产开发企业本年到位资金（亿元）',50893,-21.0),('二手房交易网签面积（万平方米）',54923,10.6),('商品房待售面积（万平方米）',75349,-1.1)]
    return f'<meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="{pub}"><table>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in rows)+extra+'</table>'

def find(x,id):return next(m for p in x['panels'].values() for m in p['metrics'] if m['id']==id)

def test_real_release_fields_period_units_and_observed_publication():
    d=parse_release(html(),URL,observed_at=NOW)
    r=d.iloc[0]
    assert r.sales_area_ytd_yoy==-12.1 and r.resale_area_ytd_yoy==10.6
    assert r.inventory_stock_sqm10k==75349 and r.publication_time=='2026-09-15T10:00:00+08:00'
    assert r.period_start=='2026-01-01' and r.period_end=='2026-08-31'
    assert len(r.source_sha256)==64

def test_activity_snapshot_exposes_ytd_and_exact_publication_not_climate_replacement():
    d=parse_release(html(),URL,observed_at=NOW)
    x=build_snapshot(lambda g,n:d if (g,n)==('china_property','activity') else None,date(2026,9,29))
    m=find(x,'property_sales_area')
    assert m['value']==-12.1 and 'YTD YoY' in m['label_en']
    assert m['source']['publication_time_verified'] is True
    assert m['source']['url']==URL
    assert 'Resale activity is rising' in x['panels']['property']['headline_en']
    assert find(x,'climate')['value'] is None
    json.dumps(x,allow_nan=False)

def test_observed_publication_filters_unreleased_activity():
    d=parse_release(html(),URL,observed_at=NOW)
    x=build_snapshot(lambda g,n:d if n=='activity' else None,date(2026,9,14))
    assert find(x,'property_sales_area')['value'] is None

@pytest.mark.parametrize('pub',['2026/10/15 10:00','2026/08/15 10:00',''])
def test_invalid_release_chronology_is_rejected(pub):
    with pytest.raises(ValueError):parse_release(html(pub=pub),URL,observed_at=NOW)

def test_duplicate_metric_not_silently_picked():
    with pytest.raises(ValueError):parse_release(html('<tr><td>房地产开发投资（亿元）</td><td>123</td><td>1</td></tr>'),URL,observed_at=NOW)

def test_missing_core_metric_and_impossible_percent_rejected():
    with pytest.raises(ValueError):parse_release(html().replace('房屋新开工面积','unknown'),URL,observed_at=NOW)
    with pytest.raises(ValueError):parse_release(html().replace('-24.8','-101'),URL,observed_at=NOW)

@pytest.mark.parametrize('url',['http://www.stats.gov.cn/sj/x','https://example.com/sj/x','https://www.stats.gov.cn/other/','https://attacker@www.stats.gov.cn/sj/x'])
def test_origin_boundary(url):
    with pytest.raises(ValueError):origin_url(url)

def test_release_index_only_accepts_property_reports_and_preserves_date():
    x='<a href="202609/t20260915_1965310.html">2026年1—8月份全国房地产市场基本情况</a><a href="x">Other release</a>'
    assert release_links(x)==[(URL,(2026,8))]

def test_missing_numbers_are_not_zero():
    assert number('—') is None and number('0')==0 and number(' -19.9 ')==-19.9

def test_gdp_ytd_deaccumulation_and_year_boundary():
    x=pd.Series([100,220,350,500,130,280,440,620],index=pd.date_range('2024-03-31',periods=8,freq='QE'))
    y=nominal_gdp_four_quarters(x)
    assert y.iloc[3]==500 and y.iloc[-1]==620 and y.iloc[4]==530

def test_missing_gdp_quarter_is_not_bridged_or_filled():
    x=pd.Series([100,350,500,130,280,440,620],index=pd.to_datetime(['2024-03-31','2024-09-30','2024-12-31','2025-03-31','2025-06-30','2025-09-30','2025-12-31']))
    y=nominal_gdp_four_quarters(x)
    assert pd.isna(y.loc['2024-12-31']) and y.loc['2025-12-31']==620

def test_gdp_yoy_alone_cannot_produce_impulse():
    gdp=pd.DataFrame({'gdp_yoy':[5.]*12},index=pd.date_range('2023-03-31',periods=12,freq='QE'))
    x=build_snapshot(lambda g,n:gdp if n=='gdp' else None,date(2026,9,29))
    assert find(x,'financing_gdp_change')['value'] is None

def test_latest_incomplete_impulse_keeps_null_not_earlier_value():
    tsf=pd.Series(100.,index=pd.date_range('2023-01-01',periods=36,freq='MS'))
    gdp=pd.Series([10000.]*11+[float('nan')],index=pd.date_range('2023-03-31',periods=12,freq='QE'))
    assert pd.isna(true_credit_impulse(tsf,gdp).iloc[-1])
