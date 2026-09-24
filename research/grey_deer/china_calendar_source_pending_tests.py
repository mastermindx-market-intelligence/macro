"""NBS source-verification acceptance; product edit was refused.
Run explicitly; pending failures are not part of any passing-test claim.
"""
from datetime import date
from engine import china_event_calendar as cc


# Primary source: NBS Regular Press Release Calendar in 2026, published 2025-12-26.
# Independently transcribed here to catch both date drift and wrong-year reuse.
import pytest


@pytest.mark.parametrize('etype', ['CPI', 'PPI'])
@pytest.mark.parametrize('month,day', list(enumerate([9,11,9,10,11,10,9,9,9,14,9,9], 1)))
def test_nbs_2026_price_schedule_matches_published_dates(etype, month, day):
    rows = cc.china_macro_events(asof=date(2026,month,1), horizon_days=30)
    actual = [r['date'] for r in rows if r['type']==etype and r['date'].startswith(f'2026-{month:02d}')]
    assert actual == [f'2026-{month:02d}-{day:02d}']


def test_nbs_pmi_holiday_move_crosses_month_boundary_without_duplicate():
    rows = cc.china_macro_events(asof=date(2026,2,20), horizon_days=40)
    assert [r['date'] for r in rows if r['type']=='PMI'] == ['2026-03-04','2026-03-31']
    march = cc.china_macro_events(asof=date(2026,3,1), horizon_days=30)
    assert [r['date'] for r in march if r['type']=='PMI'] == ['2026-03-04','2026-03-31']


def test_nbs_january_activity_report_is_present_but_february_is_absent():
    rows = cc.china_macro_events(asof=date(2026,1,1), horizon_days=58)
    assert [r['date'] for r in rows if r['type']=='ACTIVITY'] == ['2026-01-19']


def test_nbs_published_2026_dates_do_not_repeat_as_official_2027_schedule():
    rows = cc.china_macro_events(asof=date(2027,1,1), horizon_days=365)
    assert not any(r['source']=='static' for r in rows)


def test_published_nbs_schedule_and_heuristics_have_distinct_provenance():
    rows = cc.china_macro_events(asof=date(2026,9,24), horizon_days=25)
    pmi = next(r for r in rows if r['type']=='PMI')
    assert pmi['schedule_basis'] == 'published_schedule'
    assert pmi['schedule_year'] == 2026
    assert pmi['schedule_source_url'].startswith('https://www.stats.gov.cn/')
    assert pmi['scheduled_time_local'] == '09:30'
    assert pmi['schedule_timezone'] == 'Asia/Shanghai'
    assert pmi['release_confirmed'] is False
    trade = next(r for r in rows if r['type']=='TRADE')
    assert trade['schedule_basis'] == 'cadence_estimate'
    assert trade['schedule_source_url'] is None
    assert trade['scheduled_time_local'] is None


def test_published_schedule_survives_glance_and_never_becomes_a_signal():
    rows = cc.high_impact_strip(asof=date(2026,10,1), horizon_days=20)
    cpi = next(r for r in rows if r['type']=='CPI')
    assert cpi['date'] == '2026-10-14'
    assert cpi['schedule_basis'] == 'published_schedule'
    assert cpi['is_context_only'] is True
    assert not {'score','weight','dampener','forecast','actual'} & cpi.keys()
