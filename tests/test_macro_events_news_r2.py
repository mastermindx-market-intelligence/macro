"""Assertions on the new component only; no production-template integration."""
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]

def render_component(**overrides):
    values = dict(alerts=[], macro_news=None, macro_catalysts=[], latest=None,
                  generated_utc='2026-09-29 08:00')
    values.update(overrides)
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'))
    return env.get_template('_macro_events_news.html.j2').render(**values)

def example_data():
    return dict(alerts=[dict(rule='fixture', tier='watch', plain_en='Observed change',
                            message='Example observation', date='2026-09-28')],
                macro_catalysts=[dict(label='Example release',date='2026-09-30')],
                macro_news=dict(headlines=[dict(title='Example story',url='https://example.com/fixture')]))

def dom(**values): return BeautifulSoup(render_component(**values),'html.parser')
def row(**values):
    result={'rule':'test_rule','tier':'watch','plain_en':'An observed change','message':'Underlying evidence'}
    result.update(values)
    return result

def test_source_population_preserved_and_calendar_never_review():
    rows=[row(),row(tier='act'),row(tier='context'),row(tier='future'),row(rule='event_risk',tier='act')]
    d=dom(alerts=rows)
    assert len(d.select('[data-al-row]'))==5
    assert len(d.select('[data-nd-item="review"]'))==2
    assert len(d.select('[data-nd-item="calendar"]'))==1
    assert len(d.select('[data-nd-item="context"]'))==2
    assert 'event_risk' not in d.get_text()

@pytest.mark.parametrize('schedule,heading',[(None,'Calendar unavailable'),([], 'No later scheduled events in this snapshot')])
def test_calendar_unknown_distinct_from_empty(schedule,heading):
    d=dom(macro_catalysts=schedule)
    assert heading in d.get_text()
    assert 'does not mean there are no events' in d.get_text() if schedule is None else 'Calendar unavailable' not in d.get_text()

@pytest.mark.parametrize('payload,heading',[(None,'News feed unavailable'),({'headlines':[]},'No headlines in this snapshot')])
def test_news_unknown_distinct_from_empty(payload,heading):
    assert heading in dom(macro_news=payload).get_text()

def test_dedup_only_exact_url_and_title_preserves_distinct_reporting():
    h={'title':'A headline','url':'https://example.com/a'}
    d=dom(macro_news={'headlines':[h,dict(h),dict(h,url='https://example.com/b'),dict(h,title='Other reporting')]})
    assert len(d.select('.nd-story'))==3
    assert '1 exact duplicate item(s) omitted' in d.get_text(' ',strip=True)

def test_honest_story_cap():
    d=dom(macro_news={'headlines':[{'title':str(i),'url':f'https://example.com/{i}'} for i in range(30)]})
    assert len(d.select('.nd-story'))==24
    assert 'first 24 headlines in source order' in d.get_text()

@pytest.mark.parametrize('url',['javascript:alert(1)','data:text/html,bad','//unverified.example/a','httpsx://bad'])
def test_unsafe_source_url_never_becomes_anchor(url):
    d=dom(macro_news={'headlines':[{'title':'Story','url':url}]})
    assert not d.select('.nd-story h4 a')
    assert 'Source link unavailable.' in d.get_text()

def test_source_links_are_escaped_safe_new_tabs():
    d=dom(macro_news={'headlines':[{'title':'<script>alert(1)</script>','url':'https://example.com/" onclick="alert(1)'}]})
    assert not d.select('script')
    a=d.select_one('.nd-story h4 a')
    assert a['target']=='_blank' and set(a['rel'])=={'noopener','noreferrer'}
    assert not a.get('onclick')
    assert '<script>alert(1)</script>' in a.get_text()

def test_external_prose_escaped_across_sections():
    evil='<img src=x onerror=alert(1)>'
    d=dom(alerts=[row(message=evil,what_en=evil)],macro_catalysts=[{'label':evil,'date':evil}])
    assert not d.select('img,script')
    assert evil in d.get_text()

def test_publishers_not_pipeline_names():
    d=dom(macro_news={'headlines':[{'title':'A','source':'news_rss','source_name':'Reuters'},
        {'title':'B','source':'news_rss','domain':'example.com'}, {'title':'C','source':'news_rss'}]})
    assert 'news_rss' not in str(d)
    assert [p.get_text(' ',strip=True) for p in d.select('.nd-publisher')][:2]==['Reuters','example.com']
    assert 'Publisher unavailable' in d.get_text()

def test_published_not_inferred_from_seen():
    d=dom(macro_news={'headlines':[{'title':'A','seendate':'2026-09-28T13:00:00Z'}]})
    assert 'Seen' in d.select_one('.nd-story-meta').get_text()
    assert 'Published' not in d.select_one('.nd-story-meta').get_text()

def test_missing_source_clocks_not_imputed_from_build_time():
    d=dom(alerts=[row()],generated_utc='2026-09-29 08:00')
    a=d.select_one('.nd-alert')
    assert not a.select('time')
    assert 'Alert observation time was not supplied' in a.get_text()

def test_no_all_clear_from_quiet_review():
    assert 'not an all-clear on market risk' in dom().get_text()

@pytest.mark.parametrize('values,phrase',[
    ({'put_state':'unknown'},'No call is made'),
    ({'put_state_reliable':False},'No call is made'),
    ({'fed_put':None},'No call is made'),
    ({'put_state':'known','fed_put':False,'verdict':'stand_aside'},'stand aside'),
])
def test_dislocation_preserves_unknown_and_stand_aside(values,phrase):
    v={'dislocation_active':True,**values}
    d=dom(latest={'dislocation':v})
    assert len(d.select('[data-al-row]'))==1
    assert phrase in d.select_one('.nd-change').get_text()

def test_context_uses_specific_observation_not_generic_heading():
    d=dom(alerts=[row(tier='context',plain_en='A star manager moved',message='ARKW added ABNB by 46%')])
    assert 'ARKW added ABNB by 46%' in d.select_one('.nd-item-title').get_text()
    assert 'A star manager moved' not in d.select_one('.nd-item-title').get_text()

def test_no_raw_scorer_fields_or_channel_slugs():
    d=dom(macro_news={'headlines':[{'title':'A','theme':'capital_return',
        'importance_reasons':['tier-1 macro term'],'channels':['fiscal_trade'],'importance_score':99}]})
    assert 'capital_return' not in str(d) and 'fiscal_trade' not in str(d) and 'tier-1 macro term' not in str(d)

def test_no_default_expanded_boilerplate():
    d=dom(**example_data())
    assert not d.select('details[open]')
    assert all(x.select_one('summary') for x in d.select('details'))

def test_malformed_list_members_skipped_without_crash():
    d=dom(alerts=[None,14,'bad',row()],macro_catalysts=[None,{'label':'Event'}],macro_news={'headlines':[None,{'title':'Story'}]})
    assert len(d.select('[data-al-row]'))==1
    assert len(d.select('.nd-event'))==1
    assert len(d.select('.nd-story'))==1

def test_static_content_accessible_without_enhancement():
    d=dom(**example_data())
    assert d.select_one('.nd-tools').has_attr('hidden')
    assert all(not n.has_attr('hidden') for n in d.select('[data-nd-item]'))
    assert d.select_one('#dlg-news')['aria-labelledby']=='nd-title'

@pytest.mark.parametrize('value',[34,True,'unavailable',{'status':'failed'}])
def test_invalid_calendar_payload_does_not_claim_empty_schedule(value):
    assert 'Calendar unavailable' in dom(macro_catalysts=value).get_text()

@pytest.mark.parametrize('value',[34,True,'unavailable',{'status':'failed'}])
def test_invalid_news_rows_fail_closed(value):
    assert 'News feed unavailable' in dom(macro_news={'headlines':value}).get_text()

def test_ticker_string_not_split_into_characters():
    d=dom(macro_news={'headlines':[{'title':'Story','tickers':'NVDA'}]})
    assert [n.get_text() for n in d.select('.nd-ticker')]==['NVDA']

@pytest.mark.parametrize('value',[None,123,True,'missing',{},[None,123]])
def test_r2_unknown_alert_source_never_claims_no_priority_changes(value):
    d=dom(alerts=value)
    assert 'Alert source unavailable' in d.get_text()
    assert 'No priority changes in this snapshot' not in d.get_text()

@pytest.mark.parametrize('payload',[{'status':'failed'},{'headlines':[None,42]},{'headlines':[{'title':'  '}]},{'headlines':[{'title':123}]}])
def test_r2_invalid_or_missing_news_records_never_claim_empty(payload):
    assert 'News feed unavailable' in dom(macro_news=payload).get_text()

def test_r2_four_tasks_and_nonoperative_follow_state():
    d=dom();assert [x['data-nd-mode'] for x in d.select('[role="tab"]')]==['briefing','releases','stories','following']
    assert d.select_one('.nd-following button').has_attr('disabled')
    assert not d.select('form')
    assert len(d.select('#nd-task-panel'))==1

def test_r2_unhashable_theme_is_safe_and_still_displays_story():
    assert len(dom(macro_news={'headlines':[{'title':'Story','theme':{'unexpected':'shape'}}]}).select('.nd-story'))==1

def test_r2_partial_malformed_data_is_disclosed():
    d=dom(macro_news={'headlines':[None,{'title':'Story'}]})
    assert not d.select_one('.nd-data-caveat').has_attr('hidden')

def test_r2_multiple_clocks_and_identity_escaped_without_imputation():
    h={'title':'Story','url':'https://example.com/story','source_name':'Reuters',
       'pub_date':'2026-09-28','seendate':'2026-09-29T01:00:00Z',
       'first_seen_utc':'2026-09-28T15:00:00Z','event_id':'<svg onload=alert(1)>'}
    d=dom(macro_news={'headlines':[h]});r=d.select_one('.nd-story')
    assert r['data-nd-published']==h['pub_date'] and r['data-nd-seen']==h['seendate']
    assert r['data-nd-first-seen']==h['first_seen_utc']
    trail=r.select_one('.nd-story-source-trail')
    assert trail and not trail.has_attr('open')
    text=trail.get_text(' ',strip=True)
    assert 'Publisher' in text and 'Reuters' in text
    assert 'Published · source clock' in text
    assert 'Seen · source clock' in text
    assert 'First seen · ledger clock' in text
    assert 'Correction lineage' in text and 'Not supplied to this component' in text
    assert 'does not mean the source has never changed' in text
    source_link=trail.select_one('a[href]')
    assert source_link['href']=='https://example.com/story'
    assert source_link['target']=='_blank'
    assert set(source_link['rel'])=={'noopener','noreferrer'}
    assert not d.select('svg[onload]')


def test_r2_story_source_trail_does_not_impute_missing_clocks():
    d=dom(macro_news={'headlines':[{'title':'Story','source_name':'Reuters'}]})
    trail=d.select_one('.nd-story-source-trail')
    text=trail.get_text(' ',strip=True)
    assert text.count('Not supplied') >= 4
    assert 'Correction lineage' in text
