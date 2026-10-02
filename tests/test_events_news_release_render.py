"""Projection -> escaped Jinja detail without parent-template integration."""
from copy import deepcopy
import sys
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jinja2 import Environment, FileSystemLoader
sys.path.insert(0,str(ROOT/'tests'))
from events_news_release_fixture import historical_data

def render_component(**data):
    return Environment(loader=FileSystemLoader(ROOT/'templates')).get_template('_macro_events_news.html.j2').render(**data)


def soup(state='available'):
    return BeautifulSoup(render_component(**historical_data(state)), 'html.parser')


def test_qualified_result_is_nested_not_an_alert_copy():
    s=soup();assert len(s.select('[data-nd-item]'))==1 and len(s.select('[data-al-row]'))==0
    p=s.select_one('[data-nd-official-count]')
    assert p['data-nd-official-count']=='2' and p.name=='details' and not p.has_attr('open')
    assert len(p.select('.nd-official-metric'))==2
    assert [x.get_text(strip=True) for x in p.select('.nd-official-value')]==['0.1%','0.2%']
    assert '2026-07' in p.get_text()
    assert len(p.select('[data-nd-provenance]'))==2
    assert not any(d.has_attr('open') for d in p.select('[data-nd-provenance]'))

@pytest.mark.parametrize('state,count',[('partial',1),('withheld',0),('quarantine_missing',0),('mismatch',0),('unsupported',0),('binding_mismatch',0),('repaired',2)])
def test_failure_and_partial_counts_match_numbers(state,count):
    s=soup(state);assert int(s.select_one('[data-nd-official-count]')['data-nd-official-count'])==count
    assert len(s.select('.nd-official-value'))==count
    if not count: assert s.select('.nd-official-missing')


def test_source_clocks_are_not_relabelled_as_publication():
    s=soup('repaired');text=s.select_one('[data-nd-provenance]').get_text()
    assert '2026-07-30T12:30:56.032836+00:00' in text
    assert '2026-08-11T08:24:15.196500+00:00' in text
    assert s.select_one('.nd-evidence-cutoff').get_text().find('2026-08-11T09:00:00+00:00')>=0

@pytest.mark.parametrize('field',['publisher','source_sha256','receipt_id','observed_at','verified_at','display_value'])
def test_imported_macro_autoescapes_every_value(field):
    data=historical_data();data['macro_catalysts'][0]['official_evidence']['metrics'][0][field]='<img src=x onerror="window.injected=1">'
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('.nd-official-evidence img')
    assert not s.select('.nd-official-evidence script')
    assert 'onerror' in s.get_text()

@pytest.mark.parametrize('raw',[None,{},'bad',[],{'schema':'other'}, {'schema':'release_event_evidence.v1','event_type':'PCE','release_date':'2026-08-12'}])
def test_bad_projection_does_not_show_values(raw):
    data=historical_data();data['macro_catalysts'][0]['official_evidence']=raw
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('.nd-official-value')


def test_bad_unit_not_counted_available():
    data=historical_data();data['macro_catalysts'][0]['official_evidence']['metrics'][0]['unit']='basis_points'
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert s.select_one('[data-nd-official-count]')['data-nd-official-count']=='1'
    assert len(s.select('.nd-official-value'))==1


def test_no_projection_retains_old_component_markup():
    data=historical_data();data['macro_catalysts'][0].pop('official_evidence')
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('[data-nd-official-count]')


def test_existing_alert_rows_unchanged_when_official_result_added():
    data=historical_data();data['alerts']=[dict(rule='fixture',tier='watch',message='observation')]
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert len(s.select('[data-al-row]'))==1 and len(s.select('[data-nd-item]'))==2


def test_evidence_for_another_snapshot_is_not_displayed():
    data=historical_data()
    data['generated_utc']='2026-08-12T12:00:00Z'
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('.nd-official-value')
    assert s.select_one('[data-nd-official-count]')['data-nd-official-count']=='0'
    assert 'event or snapshot' in s.get_text()


@pytest.mark.parametrize('field',[
    'scheduled_reference_period','expected_reference_period','forecast_period','reference_period',
])
def test_changed_reference_after_projection_withholds_stale_result(field):
    data=historical_data()
    data['macro_catalysts'][0][field]='June 2026'
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('.nd-official-value')
    assert s.select_one('[data-nd-official-count]')['data-nd-official-count']=='0'


def test_removed_reference_after_projection_requires_reprojection():
    data=historical_data()
    event=data['macro_catalysts'][0]
    from engine.events_news_release_evidence import attach_event_actual_evidence
    import json
    event['reference_period']='July 2026'
    rows=json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())['rows']
    data['macro_catalysts']=attach_event_actual_evidence(
        [event],rows,as_of=data['generated_utc'],
        defects_path=ROOT/'tests/fixtures/events_news_actual_defects.json')
    data['macro_catalysts'][0].pop('reference_period')
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert not s.select('.nd-official-value')


def test_unchanged_explicit_reference_displays_qualified_result():
    data=historical_data()
    event=data['macro_catalysts'][0]
    from engine.events_news_release_evidence import attach_event_actual_evidence
    import json
    event['reference_period']='July 2026'
    rows=json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())['rows']
    data['macro_catalysts']=attach_event_actual_evidence(
        [event],rows,as_of=data['generated_utc'],
        defects_path=ROOT/'tests/fixtures/events_news_actual_defects.json')
    assert len(BeautifulSoup(render_component(**data),'html.parser').select('.nd-official-value'))==2


@pytest.mark.parametrize('family,label',[
    ('NFP','Thousands of payroll jobs'),('CLAIMS','Thousands of initial claims'),
])
def test_thousands_label_preserves_the_measured_quantity(tmp_path,family,label):
    import json
    from test_events_news_release_evidence import publication
    from engine import release_actuals as official
    from engine.events_news_release_evidence import attach_event_actual_evidence
    policy=tmp_path/'policy.json'
    policy.write_text(json.dumps({'schema':'official_actual_defects.v1','defects_by_receipt':{}}))
    rows=official.normalize_publication(publication(family),defects_path=policy)
    data={'alerts':[],'macro_news':{'headlines':[]},'latest':None,
          'generated_utc':'2026-09-30T13:00:00Z'}
    data['macro_catalysts']=attach_event_actual_evidence(
        [{'type':family,'date':'2026-09-30'}],rows,
        as_of=data['generated_utc'],defects_path=policy)
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert label in s.select_one('.nd-official-unit').get_text()
    assert 'Thousands of people' not in s.get_text()


def test_recent_result_only_row_uses_honest_generic_release_label():
    import json
    from engine.events_news_release_evidence import attach_recent_event_actual_evidence
    rows=json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())['rows']
    events=attach_recent_event_actual_evidence(
        [],rows,as_of='2026-08-12T13:00:00Z',lookback_days=1,
        defects_path=ROOT/'tests/fixtures/events_news_actual_defects.json')
    data={'alerts':[],'macro_news':{'headlines':[]},'latest':None,
          'generated_utc':'2026-08-12T13:00:00Z','macro_catalysts':events}
    s=BeautifulSoup(render_component(**data),'html.parser')
    assert 'Recent official release' in s.get_text()
    assert len(s.select('.nd-official-value'))==2
    assert 'Scheduled event' not in s.get_text()
