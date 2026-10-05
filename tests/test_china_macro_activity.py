from datetime import date, datetime, timezone
import json

import pandas as pd
import pytest

from collectors.china_property_activity import (
    INDEX, fetch_activity, parse_release, release_links, origin_url, number,
)
from engine.china_macro_evidence import nominal_gdp_four_quarters, build_snapshot, true_credit_impulse

URL='https://www.stats.gov.cn/sj/zxfb/202609/t20260915_1965310.html'
NOW=datetime(2026,9,29,tzinfo=timezone.utc)

def html(extra='', pub='2026/09/15 10:00', title='2026年1—8月份全国房地产市场基本情况'):
    rows=[('房地产开发投资（亿元）',47979,-19.9),('房屋新开工面积（万平方米）',29894,-24.8),('新建商品房销售面积（万平方米）',49880,-12.1),('房地产开发企业本年到位资金（亿元）',50893,-21.0),('二手房交易网签面积（万平方米）',54923,10.6),('商品房待售面积（万平方米）',75349,-1.1)]
    return f'<meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="{pub}"><table>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in rows)+extra+'</table>'

def find(x,id):return next(m for p in x['panels'].values() for m in p['metrics'] if m['id']==id)

class HttpResponse:
    def __init__(self,text,status,url,ctype='text/html'):
        self.text=text;self.content=text.encode();self.status_code=status;self.url=url
        self.headers={'Content-Type':ctype};self.encoding='utf-8'
    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError('http '+str(self.status_code))

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

def test_property_activity_checks_robots_once_and_keeps_receipt_metadata():
    calls=[]
    index='<a href="202609/t20260915_1965310.html">2026年1—8月份全国房地产市场基本情况</a>'
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/robots.txt'): return HttpResponse('',404,url,'text/plain')
        if url==INDEX: return HttpResponse(index,200,url)
        if url==URL: return HttpResponse(html(),200,url)
        raise AssertionError(url)
    d=fetch_activity(get)
    assert calls==['https://www.stats.gov.cn/robots.txt',INDEX,URL]
    r=d.iloc[0]
    assert r.robots_policy=='not_published' and r.robots_http_status==404
    assert len(r.robots_sha256)==64

def test_property_activity_robots_disallow_stops_before_index():
    calls=[]
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/robots.txt'):
            return HttpResponse('User-agent: *\nDisallow: /sj/\n',200,url,'text/plain')
        raise AssertionError('index must not be fetched')
    with pytest.raises(ValueError,match='robots_disallowed'):
        fetch_activity(get)
    assert calls==['https://www.stats.gov.cn/robots.txt']

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


def _activity_getter(body=None, *, prefix_bytes=b''):
    calls=[]
    article=body if body is not None else html('<tr><td>新建商品房销售额（亿元）</td><td>100</td><td>-11.0</td></tr>')
    index='<a href="202609/t20260915_1965310.html">2026年1—8月份全国房地产市场基本情况</a>'
    def get(url, **kwargs):
        calls.append((url,kwargs))
        if url.endswith('/robots.txt'): return HttpResponse('',404,url,'text/plain')
        assert kwargs['allow_redirects'] is False
        if url==INDEX:return HttpResponse(index,200,url)
        assert url==URL
        r=HttpResponse(article,200,url);r.content=prefix_bytes+r.content
        return r
    return get,calls,article


def test_property_acquisition_reaches_existing_economy_reader_with_bound_values():
    from pathlib import Path
    from engine.china_economy_store import document_from_store
    from engine.china_economy import build_economy,metric_view,timestamp
    get,calls,_=_activity_getter()
    frame=fetch_activity(get,clock=lambda:NOW)
    catalog=json.loads((Path(__file__).parents[1]/'config/china_economy_catalog.json').read_text())['metrics']
    catalog={k:v for k,v in catalog.items() if k.startswith('housing_')}
    doc=document_from_store(lambda g,t:frame if (g,t)==('china_property','activity') else None,
                            catalog,as_of=NOW,reference_period='2026-08')
    assert not doc['source_errors']
    assert len(doc['observations'])==4
    assert {p['metric_id'] for p in doc['observations']}==set(catalog)
    values={p['metric_id']:p['value'] for p in doc['observations']}
    assert values['housing_sales_area']==-12.1 and values['housing_starts']==-24.8
    assert values['housing_investment']==-19.9 and values['housing_sales_value']==-11.0
    dialog=build_snapshot(lambda g,t:frame if (g,t)==('china_property','activity') else None,NOW.date())
    assert find(dialog,'property_sales_area')['value']==values['housing_sales_area']
    assert len(calls)==3


def test_property_receipts_bind_exact_http_bytes_not_reencoded_text():
    import hashlib
    get,_,body=_activity_getter(prefix_bytes=b'\xef\xbb\xbf')
    frame=fetch_activity(get,clock=lambda:NOW);row=frame.iloc[0]
    expected=hashlib.sha256(b'\xef\xbb\xbf'+body.encode()).hexdigest()
    assert row.source_sha256==row.sales_area_ytd_yoy__response_sha256==expected
    assert row.source_hash_basis=='exact_http_response_bytes'
    assert row.sales_area_ytd_yoy__definition_id=='housing_sales_area.v1'


def test_mutated_property_number_cannot_borrow_its_old_receipt():
    from pathlib import Path
    from engine.china_economy_store import document_from_store
    get,_,_=_activity_getter();frame=fetch_activity(get,clock=lambda:NOW)
    frame.loc[frame.index[0],'sales_area_ytd_yoy']=100.0
    cat=json.loads((Path(__file__).parents[1]/'config/china_economy_catalog.json').read_text())['metrics']
    doc=document_from_store(lambda g,t:frame,{'housing_sales_area':cat['housing_sales_area']},
                            as_of=NOW,reference_period='2026-08')
    assert not doc['observations']
    assert any('value_receipt_mismatch' in error for error in doc['source_errors'].values())


def test_property_legacy_parser_output_is_not_silently_promoted_to_receipt_verified():
    from pathlib import Path
    from engine.china_economy_store import document_from_store
    frame=parse_release(html(),URL,observed_at=NOW)
    cat=json.loads((Path(__file__).parents[1]/'config/china_economy_catalog.json').read_text())['metrics']
    doc=document_from_store(lambda g,t:frame,{'housing_sales_area':cat['housing_sales_area']},
                            as_of=NOW,reference_period='2026-08')
    assert not doc['observations'] and doc['source_errors']


@pytest.mark.parametrize('status,actual_url,ctype',[
    (302,URL,'text/html'),(200,URL+'?redirected=1','text/html'),
    (200,None,'text/html'),(200,URL,'application/json'),
])
def test_property_release_response_is_exact_before_receipt_admission(status,actual_url,ctype):
    get,_,_=_activity_getter()
    def changed(url,**kwargs):
        if url==URL:
            assert kwargs['allow_redirects'] is False
            return HttpResponse(html(),status,actual_url,ctype)
        return get(url,**kwargs)
    with pytest.raises(ValueError,match='response'):
        fetch_activity(changed,clock=lambda:NOW)


def test_property_competing_same_month_index_links_are_refused():
    text='<a href="202609/one.html">2026年1—8月份全国房地产市场基本情况</a>'
    assert len(release_links(text+text))==1
    with pytest.raises(ValueError,match='ambiguous'):
        release_links(text+text.replace('one.html','two.html'))


def test_property_duplicate_article_tables_are_not_selected_arbitrarily():
    content=html();table=content[content.index('<table>'):]
    with pytest.raises(ValueError,match='ambiguous'):
        parse_release(content+table,URL,observed_at=NOW)


def test_property_publisher_desktop_and_mobile_copies_must_agree():
    content=html();meta,table=content.split('<table>',1);table='<table>'+table
    a='<div class="detail-text-content"><div class="txt-content">'+table+'</div></div>'
    b='<div class="mobile-content"><div class="mobile-news-content">'+table+'</div></div>'
    assert len(parse_release(meta+a+b,URL,observed_at=NOW))==1
    with pytest.raises(ValueError,match='disagree'):
        parse_release(meta+a+b.replace('-12.1','-12.2'),URL,observed_at=NOW)


@pytest.mark.parametrize('url',[
    'https://www.stats.gov.cn:444/sj/x','https://www.stats.gov.cn/sj/x#fragment',
])
def test_property_origin_rejects_nonstandard_port_or_fragment(url):
    with pytest.raises(ValueError):origin_url(url)
