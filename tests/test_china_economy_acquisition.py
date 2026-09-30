"""Deterministic adversarial fixtures, never used as an economic feed."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import hashlib, json
import pandas as pd
import pytest
import requests
from collectors.china_economy_acquisition import (
    article_identity, parse_acquisition, checked_url, collect_releases, discover_release,
    CollectionBatch, qualify_against_owner, MAX_BYTES,
)
from collectors.china_economy_adapter import enrich_existing_frames, configured_targets
from engine.china_economy_store import frames_from_receipt, document_from_store, build_from_store

CAT=json.loads((Path(__file__).parents[1]/'config/china_economy_catalog.json').read_text())['metrics']
NOW='2026-09-29T12:00:00+08:00'
URL='https://www.stats.gov.cn/sj/zxfb/202609/test.html'
SAFE='https://www.safe.gov.cn/safe/2026/0915/test.html'

def sa_page(title='2026年8月份规模以上工业增加值增长5.2%',pub='2026/09/15 10:00'):
    rows=''.join(f'<tr><td>2026年</td><td>{m}月</td><td>{v}</td></tr>' for m,v in zip(range(3,9),[.28,.05,.4,.76,.11,.54]))
    return f'<title>{title}</title><meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="{pub}"><p>根据季节调整模型对环比增速修订。</p><table><tr><th>年度</th><th>月份</th><th>环比增速(%)</th></tr>{rows}</table>'

def safe_page():
    return '<title>2026年8月银行结售汇数据</title><meta name="PubDate" content="2026-09-15"><p>2026年8月，银行结汇17090亿元人民币，售汇13800亿元人民币。2026年8月，银行代客涉外收入52718亿元人民币，对外付款48486亿元人民币。</p>'

def response(body=None,status=200,url=URL,ctype='text/html'):
    if url.endswith('/robots.txt') and body is None and status == 200:
        status=404;body='';ctype='text/plain'
    payload = body if body is not None else sa_page()
    return SimpleNamespace(content=payload.encode(),status_code=status,url=url,headers={'Content-Type':ctype})

def robots(body='User-agent: *\nAllow: /\n',status=200,url='https://www.stats.gov.cn/robots.txt'):
    return response(body,status,url,'text/plain')

def rec(observed=NOW,sha='a'*64,url=URL):
    return {'url':url,'published_at':'2026-09-15T10:00:00+08:00','observed_at':observed,'response_sha256':sha}

def point(value,metric='industrial_sa',period='2026-08'):
    return {'metric_id':metric,'period':period,'value':value}

def wide(value,receipt=None,metric='industrial_sa'):
    return frames_from_receipt([point(value,metric)],receipt or rec(),CAT)

def legacy_merge(old,new):
    return new.combine_first(old)  # actual lib.store upsert merge contract

def build(frames):
    return build_from_store(lambda g,t:frames.get(g+'/'+t),CAT,NOW)

@pytest.mark.parametrize('family,title',[('industry','2026年8月份规模以上工业增加值增长5.2%'),('retail','2026年1—8月份社会消费品零售总额增长1.1%'),('investment','2026年1—8月份全国固定资产投资基本情况')])
def test_three_seasonal_families_actual_bytes(family,title):
    raw=b'\xef\xbb\xbf'+sa_page(title).encode()
    frames,receipt,points=parse_acquisition(family,URL,raw,NOW,'2026-08',CAT)
    assert receipt['response_sha256']==hashlib.sha256(raw).hexdigest()
    assert receipt['response_bytes']==len(raw) and receipt['response_hash_basis']=='exact_http_response_bytes'
    assert receipt['publication_precision']=='minute' and len(points)==6
    assert build(frames)['counts']['valid_current']==1

@pytest.mark.parametrize('title,pub,reason',[
 ('2026年7月份规模以上工业增加值','2026/09/15 10:00','wrong_reference'),
 ('2026年8月份社会消费品零售总额','2026/09/15 10:00','wrong_release'),
 ('2026年8月份规模以上工业增加值','2026/08/10 10:00','precedes_reference'),
 ('2026年8月份规模以上工业增加值','2026/09/30 10:00','after_acquisition'),
 ('2026年8月份规模以上工业增加值','unknown','invalid_publication'),
])
def test_identity_period_and_chronology(title,pub,reason):
    with pytest.raises(ValueError,match=reason):parse_acquisition('industry',URL,sa_page(title,pub).encode(),NOW,'2026-08',CAT)

@pytest.mark.parametrize('extra,reason',[
 ('<meta name="PubDate" content="2026/09/16 10:00">','conflicting_publication_dates'),
 ('<meta name="PubDate" content="2026/09/15 11:00">','conflicting_publication_times'),
 ('<meta name="ArticleTitle" content="different">','conflicting_article_titles'),
])
def test_conflicting_metadata_refused(extra,reason):
    with pytest.raises(ValueError,match=reason):article_identity(sa_page()+extra,'industry','2026-08')

def test_precise_publisher_time_wins_only_when_date_agrees():
    r=article_identity(sa_page()+'<meta name="publishdate" content="2026-09-15">','industry','2026-08')
    assert r['published_at']=='2026-09-15T10:00:00+08:00'

def test_no_url_date_or_script_timestamp_as_publication():
    p=sa_page().replace('<meta name="PubDate" content="2026/09/15 10:00">','')+'<script>var date="2026/09/15 10:00"</script>'
    with pytest.raises(ValueError,match='publication_evidence_missing'):article_identity(p,'industry','2026-08')

def test_profits_mobile_visible_publisher_timestamp():
    p='<title>2026年1—8月份全国规模以上工业企业利润增长15.7%</title><font class="xilan_titf"><script>fake date</script>发布时间：2026-09-28&nbsp; 09:30</font>'
    assert article_identity(p,'profits','2026-08')['published_at']=='2026-09-28T09:30:00+08:00'

def test_power_year_in_body_not_url():
    p='<title>8月份全社会用电量再破万亿</title><meta name="PubDate" content="2026-09-20 11:38:19"><p>2026年8月，全社会用电量10332亿千瓦时。</p>'
    assert article_identity(p,'power','2026-08')['publication_precision']=='second'
    with pytest.raises(ValueError,match='reference'):article_identity(p.replace('2026年8月','2025年8月'),'power','2026-08')

def test_date_only_is_explicit_conservative_boundary():
    _,r,p=parse_acquisition('safe',SAFE,safe_page().encode(),NOW,'2026-08',CAT)
    assert r['published_at']=='2026-09-15T23:59:59+08:00'
    assert r['publication_precision']=='day_conservative_end' and [x['value'] for x in p]==[1709,1380,5271.8,4848.6]

@pytest.mark.parametrize('url',['http://www.stats.gov.cn/sj/x','https://www.stats.gov.cn.evil.test/sj/x','https://u:p@www.stats.gov.cn/sj/x','https://www.stats.gov.cn/sj/../x','https://www.stats.gov.cn/sj/%2e%2e/x','https://www.stats.gov.cn/sj/x?token=x','https://www.stats.gov.cn/sj/x#x','https://www.stats.gov.cn:8080/sj/x','https://www.safe.gov.cn/safe/x','https://www.stats.gov.cn/admin/x'])
def test_exact_public_origin_contract(url):
    with pytest.raises(ValueError):checked_url(url,'industry')

@pytest.mark.parametrize('status,ctype,body',[(502,'text/html',b'ok'),(403,'text/html',b'denied'),(302,'text/html',b'redirect'),(200,'application/json',b'{}'),(200,'text/html',b''),(200,'text/html',b'a'*(MAX_BYTES+1)),(200,'text/html',b'\xff')])
def test_bad_http_body_not_a_release(status,ctype,body):
    with pytest.raises((ValueError,UnicodeDecodeError)):parse_acquisition('industry',URL,body,NOW,'2026-08',CAT,status=status,content_type=ctype)

def test_published_robots_allow_is_bound_to_release_receipt():
    calls=[]
    def get(url,**kwargs):
        calls.append(url)
        return robots() if url.endswith('/robots.txt') else response(url=url)
    b=collect_releases({'industry':URL},'2026-08',get,CAT,lambda:datetime.fromisoformat(NOW))
    assert b.status=='ok' and calls==['https://www.stats.gov.cn/robots.txt',URL]
    rr=b.receipts['industry']['robots']
    assert rr['policy']=='published' and rr['http_status']==200 and rr['allowed'] is True
    assert rr['checked_path']=='/sj/zxfb/202609/test.html' and len(rr['response_sha256'])==64

def test_missing_robots_means_no_explicit_disallow_not_no_check():
    calls=[]
    def get(url,**kwargs):
        calls.append(url);return response(url=url)
    b=collect_releases({'industry':URL},'2026-08',get,CAT,lambda:datetime.fromisoformat(NOW))
    assert b.status=='ok' and calls[0].endswith('/robots.txt')
    assert b.receipts['industry']['robots']['policy']=='not_published'
    assert b.receipts['industry']['robots']['http_status']==404

def test_robots_disallow_blocks_article_before_fetch():
    calls=[]
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/robots.txt'):
            return robots('User-agent: *\nDisallow: /sj/\n')
        raise AssertionError('article must not be fetched')
    b=collect_releases({'industry':URL},'2026-08',get,CAT)
    assert calls==['https://www.stats.gov.cn/robots.txt']
    assert not b.frames and b.failures['industry']['reason']=='robots_disallowed'

def test_robots_redirect_or_html_200_fails_closed():
    for mode in ('redirect','html'):
        calls=[]
        def get(url,**kwargs):
            calls.append(url)
            if mode=='redirect':
                return response('moved',302,url,'text/html')
            return response('<html>not robots</html>',200,url,'text/html')
        b=collect_releases({'industry':URL},'2026-08',get,CAT)
        assert len(calls)==1 and not b.frames
        assert b.failures['industry']['reason'].startswith('robots_')

def test_index_and_release_share_one_robots_fetch():
    index='https://www.stats.gov.cn/sj/zxfb/';calls=[];cache={}
    h='<a href="202609/test.html">2026年8月份规模以上工业增加值</a>'
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/robots.txt'): return robots()
        if url==index: return response(h,url=index)
        return response(url=url)
    targets,failures=configured_targets({'sources':{'industry':{'index_url':index}}},get,'2026-08',cache)
    batch=collect_releases(targets,'2026-08',get,CAT,lambda:datetime.fromisoformat(NOW),robots_cache=cache)
    assert not failures and batch.status=='ok'
    assert calls.count('https://www.stats.gov.cn/robots.txt')==1
    assert calls.count(index)==1 and calls.count(URL)==1

def test_independent_publisher_survives_http_failure():
    calls=[]
    def get(url,**kwargs):
        calls.append((url,kwargs))
        if url.endswith('/robots.txt'): return response(url=url)
        return response(status=502,url=url) if url==URL else response(safe_page(),url=SAFE)
    b=collect_releases({'industry':URL,'safe':SAFE},'2026-08',get,CAT,lambda:datetime.fromisoformat(NOW))
    assert b.status=='blocked' and set(b.receipts)=={'safe'} and len(calls)==4
    assert all(c[1]['retries']==1 and c[1]['allow_redirects'] is False for c in calls)

@pytest.mark.parametrize('status',[401,403,429])
def test_host_denial_no_sibling_probe_or_retry(status):
    calls=[]
    def get(url,**kwargs):calls.append(url);return response(status=status,url=url)
    b=collect_releases({'industry':URL,'retail':URL.replace('test','retail')},'2026-08',get,CAT)
    assert len(calls)==1 and len(b.failures)==2

@pytest.mark.parametrize('status',[401,403,429])
def test_adapter_raised_http_denial_also_stops_host(status):
    calls=[]
    def get(url,**kwargs):
        calls.append(url);r=requests.Response();r.status_code=status
        raise requests.HTTPError('fixture denial',response=r)
    b=collect_releases({'industry':URL,'retail':URL.replace('test','retail')},'2026-08',get,CAT)
    assert len(calls)==1 and len(b.failures)==2

def test_changed_number_cannot_borrow_old_receipt():
    frames=wide(.54);key=next(iter(frames));old=frames[key]
    changed=pd.DataFrame({'indpro_mom':[9.]},index=old.index)
    frames[key]=legacy_merge(old,changed)
    x=build(frames);assert x['metrics']['industrial_sa']['value'] is None
    assert 'value_receipt_mismatch' in x['source_errors'][key+'.indpro_mom']

def test_null_revision_cannot_resurrect_old_value_as_verified():
    old=wide(.54);new=wide(None,rec(sha='b'*64));key=next(iter(old))
    mixed=legacy_merge(old[key],new[key]);assert mixed['indpro_mom'].iloc[0]==.54
    assert build({key:mixed})['metrics']['industrial_sa']['value'] is None

@pytest.mark.parametrize('bad',[True,float('inf'),float('nan'),'junk'])
def test_nonfinite_or_boolean_receipt_value_refused(bad):
    with pytest.raises(ValueError):wide(bad)

def test_parquet_roundtrip_preserves_receipt_value_binding(tmp_path):
    pytest.importorskip("pyarrow", reason="Actual parquet engine required; no serialization fixture substitutes for it")
    frames=wide(0);key=next(iter(frames));p=tmp_path/'metric.parquet';frames[key].to_parquet(p)
    assert build({key:pd.read_parquet(p)})['metrics']['industrial_sa']['value']==0

def test_disagreement_with_unreceipted_owner_is_held_not_overwritten():
    incoming=wide(.54);key=next(iter(incoming));old=pd.DataFrame({'indpro_mom':[.99]},index=pd.to_datetime(['2026-08-01']))
    b=CollectionBatch(frames=incoming);out=qualify_against_owner(b,{'activity_sa':old},lambda g,t:None,CAT)
    assert out['activity_sa']['indpro_mom'].iloc[0]==.99 and b.status=='blocked'
    assert b.conflicts[0]['periods']==['2026-08'] and '__value_sha256' not in ' '.join(out['activity_sa'].columns)

def test_same_value_can_be_enriched_without_changing_it():
    incoming=wide(.54);key=next(iter(incoming));table=key.split('/')[1]
    old=pd.DataFrame({'indpro_mom':[.54]},index=pd.to_datetime(['2026-08-01']))
    b=CollectionBatch(frames=incoming);out=qualify_against_owner(b,{table:old},lambda g,t:None,CAT)
    assert b.status=='ok' and build({'china_macro/'+table:out[table]})['metrics']['industrial_sa']['value']==.54

def test_valid_same_source_newer_revision_is_admitted():
    old=wide(.54,rec('2026-09-28T12:00:00+08:00'));new=wide(.55,rec(sha='b'*64));key=next(iter(old));table=key.split('/')[1]
    b=CollectionBatch(frames=new);out=qualify_against_owner(b,{},lambda g,t:old.get(g+'/'+t),CAT)
    assert b.status=='ok' and out[table]['indpro_mom'].iloc[0]==.55

def test_owner_read_failure_is_path_local():
    frames={**wide(.54),**wide(1709,metric='fx_surrender')};b=CollectionBatch(frames=frames)
    def read(g,t):
        if t==next(iter(wide(.54))).split('/')[1]:raise OSError('fixture')
        return None
    out=qualify_against_owner(b,{'legacy':pd.DataFrame({'x':[1]})},read,CAT)
    assert b.failures and any('fx_surrender' in f for f in out.values())

def test_discovery_exact_month_unique_and_relative():
    index='https://www.stats.gov.cn/sj/zxfb/'
    h='<a href="202609/test.html">2026年8月份规模以上工业增加值</a><a href="202608/old.html">2026年7月份规模以上工业增加值</a>'
    assert discover_release(h,index,'industry','2026-08')==URL
    with pytest.raises(ValueError):discover_release(h,index,'industry','2026-09')
    with pytest.raises(ValueError):discover_release(h+h.replace('test.html','other.html'),index,'industry','2026-08')

def test_shared_index_fetched_once():
    index='https://www.stats.gov.cn/sj/zxfb/';calls=[]
    h='<a href="202609/test.html">2026年8月份规模以上工业增加值</a><a href="202609/retail.html">2026年1—8月份社会消费品零售总额</a>'
    def get(url,**kwargs):
        calls.append(url)
        return response(url=url) if url.endswith('/robots.txt') else response(h,url=url)
    t,f=configured_targets({'sources':{'industry':{'index_url':index},'retail':{'index_url':index}}},get,'2026-08')
    assert calls.count('https://www.stats.gov.cn/robots.txt')==1
    assert calls.count(index)==1 and len(t)==2 and not f

def test_feature_disabled_has_no_network_or_store_effect():
    def fail(*a,**kw):raise AssertionError('should not run')
    adapter=SimpleNamespace(cfg={},http_get=fail);old={'legacy':pd.DataFrame({'x':[1]})}
    out,b=enrich_existing_frames(adapter,old,fail,catalog=CAT)
    assert out is old and b is None

def test_explicit_stale_release_not_relabelled_latest():
    def fail(*a,**kw):raise AssertionError('should not run')
    t,f=configured_targets({'sources':{'industry':{'url':URL,'period':'2026-07'}}},fail,'2026-08')
    assert not t and 'expected_period' in f['industry']['reason']

def test_configured_adapter_to_store_to_overview_roundtrip():
    a=SimpleNamespace(cfg={'economy_releases':{'enabled':True,'sources':{'industry':{'url':URL,'period':'2026-08'}}}},http_get=lambda url,**kwargs:response(url=url))
    frames,b=enrich_existing_frames(a,{'legacy':pd.DataFrame({'x':[1]})},lambda g,t:None,catalog=CAT,clock=lambda:datetime.fromisoformat(NOW))
    assert b.status=='ok' and len(b.receipts)==1
    evidence=build({'china_macro/'+t:f for t,f in frames.items()})
    assert evidence['metrics']['industrial_sa']['value']==.54
    assert evidence['counts']['valid_current']==1 and evidence['counts']['valid_current']<128

def test_no_primary_data_cannot_be_masked_by_optional_extension():
    a=SimpleNamespace(cfg={'economy_releases':{'enabled':True}},http_get=lambda:None)
    with pytest.raises(ValueError,match='mask_primary'):enrich_existing_frames(a,{},lambda g,t:None,catalog=CAT)

@pytest.mark.parametrize('config',['wrong',{'enabled':True,'unknown':1},{'enabled':True,'sources':{}},{'enabled':True,'sources':{'industry':{'url':URL}}}])
def test_bad_config_preserves_legacy_and_declares_blocked(config):
    a=SimpleNamespace(cfg={'economy_releases':config},http_get=lambda *a,**k:None);old={'legacy':pd.DataFrame({'x':[1]})}
    out,b=enrich_existing_frames(a,old,lambda g,t:None,catalog=CAT,clock=lambda:datetime.fromisoformat(NOW))
    assert 'legacy' in out and b.status=='blocked'


def test_metadata_only_tampering_does_not_leave_verified_numbers():
    frames=wide(.54);key=next(iter(frames));frames[key]['indpro_mom__definition_id']='fabricated.definition'
    assert build(frames)['metrics']['industrial_sa']['value'] is None


def test_old_acquisition_cannot_overwrite_later_qualified_revision():
    old=wide(.54);new=wide(.55,rec('2026-09-28T12:00:00+08:00',sha='b'*64));key=next(iter(old))
    b=CollectionBatch(frames=new);out=qualify_against_owner(b,{},lambda g,t:old.get(g+'/'+t),CAT)
    assert b.conflicts and not out


def test_one_conflicting_month_withholds_entire_incoming_seasonal_column():
    incoming=frames_from_receipt([point(.1,period='2026-07'),point(.54)],rec(),CAT)
    old=pd.DataFrame({'indpro_mom':[.99]},index=pd.to_datetime(['2026-08-01']))
    b=CollectionBatch(frames=incoming);out=qualify_against_owner(b,{},lambda g,t:old,CAT)
    assert b.conflicts and not out  # no July-new/August-old stitched seasonal vintage


def test_unrelated_legacy_columns_and_dates_survive_enrichment():
    old=pd.DataFrame({'legacy_industry':[3.,4.]},index=pd.to_datetime(['2026-07-01','2026-08-01']))
    b=CollectionBatch(frames=wide(.54));out=qualify_against_owner(b,{'activity_sa':old},lambda g,t:None,CAT)
    assert list(out['activity_sa']['legacy_industry'])==[3.,4.]


def test_empty_enabled_acquisition_never_declares_success():
    a=SimpleNamespace(cfg={'economy_releases':{'enabled':True,'sources':{}}},http_get=lambda *a,**k:None)
    out,b=enrich_existing_frames(a,{'legacy':pd.DataFrame({'x':[1]})},lambda g,t:None,catalog=CAT)
    assert b.status=='blocked' and 'legacy' in out


def test_source_response_url_change_not_silently_followed():
    def get(url,**kwargs):
        return response(url=url) if url.endswith('/robots.txt') else response(url=URL+'2')
    b=collect_releases({'industry':URL},'2026-08',get,CAT)
    assert not b.frames and b.failures['industry']['reason']=='unexpected_response_url'


def test_index_http_error_cached_once_for_all_dependent_families():
    calls=[];index='https://www.stats.gov.cn/sj/zxfb/'
    def get(url,**kwargs):
        calls.append(url)
        return response(url=url) if url.endswith('/robots.txt') else response(status=502,url=url)
    t,f=configured_targets({'sources':{'industry':{'index_url':index},'retail':{'index_url':index}}},get,'2026-08')
    assert calls.count('https://www.stats.gov.cn/robots.txt')==1
    assert calls.count(index)==1 and not t and len(f)==2


def test_paragraph_wrapper_scopes_equal_publisher_twins_and_keeps_title_year():
    import ast
    text=(Path(__file__).with_name('test_china_economy_additional_parsers.py')).read_text()
    tree=ast.parse(text)
    fixture=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CORPORATE' for t in n.targets))
    body=fixture.split('。',1)[1]  # article body has 1–8, year supplied by publisher title
    title='2026年1—8月份全国规模以上工业企业利润增长15.7%'
    page=f'<title>{title}</title><meta name="PubDate" content="2026/09/28 09:30"><div class="detail-text-content"><div class="txt-content">{body}</div></div><div class="mobile-content"><div class="mobile-news-content">{body}</div></div>'
    _,_,points=parse_acquisition('profits',URL,page.encode(),NOW,'2026-08',CAT)
    assert len(points)==19


_DETAIL_INDUSTRY_TABLE = '''<table><tr><th>指标</th><th>8月</th><th>8月</th><th>1—8月</th><th>1—8月</th></tr><tr><th>指标</th><th>绝对量</th><th>同比增长(%)</th><th>绝对量</th><th>同比增长(%)</th></tr><tr><td>规模以上工业增加值</td><td>…</td><td>5.2</td><td>…</td><td>5.3</td></tr><tr><td>制造业</td><td>…</td><td>6.1</td><td>…</td><td>5.7</td></tr></table>'''


def test_same_response_enriches_new_values_without_replacing_history():
    old_frames, _, core = parse_acquisition('industry', URL, sa_page().encode(), NOW, '2026-08', CAT)
    raw = (sa_page()+_DETAIL_INDUSTRY_TABLE).encode()
    frames, receipt, points = parse_acquisition('industry', URL, raw, NOW, '2026-08', CAT)
    assert [p for p in points if p['metric_id']=='industrial_sa'] == core
    pd.testing.assert_series_equal(frames['china_macro/activity_sa']['indpro_mom'], old_frames['china_macro/activity_sa']['indpro_mom'])
    assert len(points)==len(core)+2
    assert len([p for p in points if p['metric_id']=='industrial_yoy'])==1
    assert receipt['supplemental_evidence']['history_inferred'] is False
    for frame in frames.values():
        for col in frame.columns:
            if col.endswith('__response_sha256'):
                assert set(frame[col].dropna()) == {hashlib.sha256(raw).hexdigest()}
    assert build(frames)['metrics']['output_manufacturing']['value']==6.1


def test_bad_supplemental_table_cannot_erase_valid_core_history():
    _, _, before = parse_acquisition('industry', URL, sa_page().encode(), NOW, '2026-08', CAT)
    raw = (sa_page()+_DETAIL_INDUSTRY_TABLE*2).encode()
    frames, receipt, after = parse_acquisition('industry', URL, raw, NOW, '2026-08', CAT)
    assert before==after
    assert receipt['supplemental_evidence']['status']=='withheld'
    assert 'industrial_yoy' in receipt['supplemental_evidence']['null_reasons']
    assert build(frames)['counts']['valid_current']==1


def test_new_detail_respects_unqualified_legacy_disagreement():
    frames, receipt, _ = parse_acquisition('industry', URL, (sa_page()+_DETAIL_INDUSTRY_TABLE).encode(), NOW, '2026-08', CAT)
    old = pd.DataFrame({'indpro_yoy':[99.]}, index=pd.to_datetime(['2026-08-01']))
    batch = CollectionBatch(frames=frames,receipts={'industry':receipt})
    qualified = qualify_against_owner(batch, {'indpro':old}, lambda g,t:None, CAT)
    assert qualified['indpro'].iloc[0]['indpro_yoy']==99
    assert batch.conflicts and batch.status=='blocked'
    result = build({'china_macro/'+k:v for k,v in qualified.items()})
    assert result['metrics']['industrial_yoy']['value'] is None
    assert result['metrics']['output_manufacturing']['value']==6.1
    assert result['metrics']['industrial_sa']['value']==.54


def test_fai_monthly_and_nbs_ytd_keep_distinct_values_and_index_name():
    official=frames_from_receipt([point(-7.2,'investment_ytd')],rec(),CAT)
    old=pd.DataFrame({'fai_yoy':[-13.51]},index=pd.DatetimeIndex(['2026-08-01'],name='REPORT_DATE'))
    batch=CollectionBatch(frames=official)
    qualified=qualify_against_owner(batch,{'fai':old},lambda g,t:old if (g,t)==('china_macro','fai') else None,CAT)
    assert not batch.conflicts and not batch.failures
    assert qualified['fai'].index.name=='REPORT_DATE'
    assert qualified['fai'].iloc[0]['fai_yoy']==-13.51
    assert qualified['fai'].iloc[0]['fai_ytd_yoy']==-7.2
    assert qualified['fai'].iloc[0]['fai_ytd_yoy__definition_id']=='investment_ytd.nbs_comparable.v2'


def test_fai_mismatching_official_value_still_triggers_existing_conflict_guard():
    official=frames_from_receipt([point(-7.2,'investment_ytd')],rec(),CAT)
    old=pd.DataFrame({'fai_ytd_yoy':[-9.9]},index=pd.DatetimeIndex(['2026-08-01'],name='REPORT_DATE'))
    batch=CollectionBatch(frames=official)
    qualified=qualify_against_owner(batch,{'fai':old},lambda g,t:None,CAT)
    assert batch.conflicts and batch.status=='blocked'
    assert qualified['fai'].iloc[0]['fai_ytd_yoy']==-9.9
