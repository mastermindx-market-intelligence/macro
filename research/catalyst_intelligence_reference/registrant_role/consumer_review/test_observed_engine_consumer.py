"""Consumes the structured transcript of the completed M1 real-module probe.

This does NOT rerun the remote module or turn fixture inputs into live records.
"""
import json
from pathlib import Path
import pytest
from review_projection import attach_relationship_review
from render_reference import render_fixture_fragment
TRACE=json.loads((Path(__file__).parent/'fixtures/ENGINE_TRACE_OBSERVED.json').read_text())


@pytest.mark.parametrize('surface',['snapshot','desk'])
def test_actual_return_keeps_source_visible_without_a_direct_claim(surface):
    base=TRACE[surface]
    out=attach_relationship_review(base,TRACE['rows'],as_of='2026-09-27')
    assert out['situations']==base['situations']
    assert out['counts']==base['counts']
    assert out['relationship_review']['records'][0]['source_record_id']=='filing-related'
    assert out['relationship_review']['records'][0]['affected_relationship_confirmed'] is False
    assert all(r['id']!='filing-related' for r in out['situations'])


def test_original_false_text_reason_reclassified():
    out=attach_relationship_review(TRACE['snapshot'],TRACE['rows'],as_of='2026-09-27')
    assert out['coverage']['events_total']==2
    assert out['coverage']['classified']==1
    assert out['coverage']['deferred_to_text_lane']==0
    assert out['coverage']['relationship_review_records']==1


def test_arbitrage_receiver_observed_only_direct():
    assert TRACE['arb_candidate_ids']==['filing-direct']
    assert TRACE['production_writes'] is False and TRACE['live_data'] is False


@pytest.mark.parametrize('surface',['snapshot','desk'])
@pytest.mark.parametrize('locale',['en','zh'])
def test_render_from_actual_engine_return(surface,locale):
    out=attach_relationship_review(TRACE[surface],TRACE['rows'],as_of='2026-09-27')
    html=render_fixture_fragment(out['relationship_review'],entitled_fixture=True,locale=locale)
    assert 'FIX-B' in html and 'https://example.invalid/filing' in html
    assert 'A parent transaction is discussed.' in html
    assert 'filing-direct' not in html


def test_snapshot_and_desk_share_one_projection():
    a=attach_relationship_review(TRACE['snapshot'],TRACE['rows'],as_of='2026-09-27')
    b=attach_relationship_review(TRACE['desk'],TRACE['rows'],as_of='2026-09-27')
    assert a['relationship_review']==b['relationship_review']
    assert a['relationship_review']['independent_event_count'] is None
