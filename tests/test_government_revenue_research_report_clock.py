from __future__ import annotations

import gzip
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

REPO = Path(os.environ.get('MACRO_REPO', Path.cwd()))
OVERLAY = Path(os.environ.get('GRV_REPORT_CLOCK_OVERLAY', REPO))
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location('research_report_clock_under_test',
    OVERLAY/'engine/government_revenue/research_state.py')
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)
from engine.government_revenue.candidate_grader import GRV_FA1, GraderError, canonical_bytes
from engine.government_revenue.candidates import candidate_queue_content_id

GENERATED = '2026-10-13T09:54:55.596723+00:00'
FUTURE = '2026-10-13T10:00:00+00:00'


def historical_queue():
    return json.loads(gzip.decompress((REPO/'tests/fixtures/government_revenue_candidate_queue_20260901.json.gz').read_bytes()))


def current_queue():
    # Frozen historical records with a synthetic same-day analysis horizon.
    # A nightly-changing live artifact must never be a clock regression fixture.
    queue = historical_queue()
    queue['as_of'] = '2026-10-13T23:59:59.999999+00:00'
    queue['generated_at'] = GENERATED
    return rehash(queue)


def build(queue, generated=GENERATED):
    return state.build_not_started_state(queue=queue, prereg_path=REPO/GRV_FA1.document,
        generated_at=generated, source_digests={p:'a'*64 for p in state.SOURCE_PATHS})


def rehash(queue):
    queue['content_id'] = candidate_queue_content_id(queue)
    return queue


def test_same_day_eod_horizon_is_bounded_without_rewriting_source():
    q=current_queue()
    assert q['as_of']=='2026-10-13T23:59:59.999999+00:00'
    assert q['generated_at']==GENERATED
    before=canonical_bytes(q)
    p=build(q)
    state.validate_research_state(p)
    assert p['as_of']==GENERATED and p['generated_at']==GENERATED
    assert canonical_bytes(q)==before
    assert p['input_admission']['considered_n']==len(q['candidates'])
    assert p['issuance']['issued_n']==p['issuance']['append_count_this_generation']==0
    assert p['outcomes']['evaluated_n']==0 and p['is_running'] is False


@pytest.mark.parametrize('horizon', ['2026-09-01T03:00:00Z','2026-09-01T23:59:59.999999+00:00'])
def test_past_precise_cutoff_and_past_daily_horizon_are_preserved_exactly(horizon):
    q=historical_queue(); q['as_of']=horizon;rehash(q)
    before=canonical_bytes(q)
    p=build(q)
    assert p['as_of']==horizon and canonical_bytes(q)==before
    assert p['input_admission']['considered_n']==173


@pytest.mark.parametrize('horizon', [FUTURE,'2026-10-14T23:59:59.999999+00:00','2026-10-14T00:00:00Z','2026-10-13T23:59:59+00:00'])
def test_only_exact_same_utc_day_inclusive_horizon_may_be_bounded(horizon):
    q=historical_queue();q['as_of']=horizon;rehash(q)
    with pytest.raises(GraderError,match='as_of is future'):
        build(q)


def test_date_only_future_clock_remains_invalid():
    q=historical_queue();q['as_of']='2026-10-14';rehash(q)
    with pytest.raises(GraderError):build(q)


@pytest.mark.parametrize('location', ['queue_known','queue_generated','candidate_known','candidate_generated','event_known','receipt_known','freshness_event','freshness_graph'])
def test_bounded_horizon_never_admits_future_source_clocks(location):
    q=current_queue(); c=q['candidates'][0]
    if location=='queue_known':q['known_at']=FUTURE
    if location=='queue_generated':q['generated_at']=FUTURE
    if location=='candidate_known':c['known_at']=FUTURE
    if location=='candidate_generated':c['generated_at']=FUTURE
    if location=='event_known':c['source_event']['known_at']=FUTURE
    if location=='receipt_known':c['source_receipt_refs'][0]['known_at']=FUTURE
    if location=='freshness_event':c['freshness']['event_known_at']=FUTURE
    if location=='freshness_graph':c['freshness']['graph_known_at']=FUTURE
    rehash(q)
    with pytest.raises(GraderError,match='future candidate'):
        build(q)


def test_past_precise_cutoff_cannot_claim_later_known_evidence_even_before_generation():
    q=historical_queue(); q['as_of']='2026-09-01T03:00:00Z';q['known_at']='2026-09-01T03:01:00Z';rehash(q)
    with pytest.raises(GraderError,match='future candidate knowledge'):build(q)


def test_exact_generation_boundary_is_accepted():
    q=current_queue();q['known_at']=GENERATED;rehash(q)
    assert build(q)['as_of']==GENERATED


def test_report_validator_still_refuses_rehashed_future_asof():
    p=build(historical_queue());p['as_of']=FUTURE;p['content_id']=state.content_id(p)
    with pytest.raises(GraderError,match='as_of is future'):state.validate_research_state(p)
