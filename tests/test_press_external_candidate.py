"""External source planning must not become writer or publication admission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.press import desk_planner as P
from tests import press_fixtures as F

HERE = Path(__file__).resolve().parents[1] / 'research/agentic_media/public_intelligence_20261011'


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + '\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def inputs(tmp_path):
    root = F.fixture_root(tmp_path / 'root')
    (root / 'site/stocks').mkdir(parents=True, exist_ok=True)
    (root / 'site/stocks/NVDA.html').write_text('<html>NVIDIA</html>')
    q = json.loads((HERE / 'whitehouse_event_source_receipt.json').read_text())
    d = json.loads((HERE / 'sources/whitehouse_science_retained_document.json').read_text())
    doc, qualification, policy = (tmp_path / name for name in ('document.json', 'qualification.json', 'policy.txt'))
    policy.write_bytes((HERE / 'sources/whitehouse_copyright_20261011.txt').read_bytes())
    q['external_planning']['document_sha256'] = dump(doc, d)
    return dict(document_path=doc, document_sha256=q['external_planning']['document_sha256'],
                qualification_path=qualification, qualification_sha256=dump(qualification, q),
                policy_path=policy, as_of='2026-10-11T23:00:00Z', root=root)


def mutate(inputs, kind, fn):
    key = {'document': 'document_path', 'qualification': 'qualification_path'}[kind]
    data = json.loads(inputs[key].read_text()); fn(data)
    digest = dump(inputs[key], data)
    inputs[kind + '_sha256'] = digest
    if kind == 'document':
        mutate(inputs, 'qualification', lambda q: q['external_planning'].update(document_sha256=digest))


def test_opt_in_context_and_default_plan_unchanged(inputs, monkeypatch):
    def snapshot():
        return {str(p.relative_to(inputs['root'])): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in inputs['root'].rglob('*') if p.is_file()}
    before_files = snapshot()
    before = P.plan(['brief'], root=inputs['root'], as_of='2026-10-11')
    from engine.press import writer
    monkeypatch.setattr(writer, 'write', lambda *a, **k: pytest.fail('no provider admission'), raising=False)
    result = P.plan_external_candidate(**inputs)
    assert result['operation'] == 'planning_only'
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert result['cadence_consumed'] is False and result['cadence_per_day'] == 2
    assert 'id' not in result and 'slots' not in result and 'draft' not in result
    ctx = result['validation_context']
    assert len(ctx['facts']) == 9 and {f['tier'] for f in ctx['facts']} == {'third_party'}
    assert ctx['facts'][-1]['values'] == ['62.5']
    assert ctx['primary_source']['kind'] == 'external'
    assert ctx['primary_source']['name'] == 'The White House'
    assert ctx['allowed_links'] == ['https://www.mastermind-x.com/stocks/NVDA.html']
    assert ctx['min_anchored_receipts'] == 5
    assert result == P.plan_external_candidate(**inputs)
    assert before == P.plan(['brief'], root=inputs['root'], as_of='2026-10-11')
    assert before_files == snapshot()


@pytest.mark.parametrize('key', ['document_path', 'qualification_path', 'policy_path'])
def test_evidence_hash_mismatch(inputs, key):
    inputs[key].write_bytes(inputs[key].read_bytes() + b' ')
    with pytest.raises(ValueError, match='hash mismatch'): P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('patch', [
    {'body': 'different'}, {'body_sha256': '0' * 64}, {'url': 'https://evil.example/doc'},
    {'published': '2026-10-08T15:05:07+00:00'}, {'guid': 'different'},
    {'body_origin': 'description'}, {'body_truncated': True}, {'normalization': 'unknown'},
    {'rights_status': 'approved'}, {'allow_stage': True},
])
def test_changed_or_incomplete_source_rejected(inputs, patch):
    mutate(inputs, 'document', lambda d: d.update(patch))
    with pytest.raises(ValueError): P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('as_of', ['2026-10-08T14:00:00Z', '2026-10-12T00:00:00Z', '2026-10-11T23:00:00'])
def test_clocks_fail_closed(inputs, as_of):
    inputs['as_of'] = as_of
    with pytest.raises(ValueError): P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('change', ['missing', 'unqualified', 'literal', 'quantity', 'substring', 'tier', 'ticker', 'arithmetic', 'feed'])
def test_qualification_cannot_relabel_or_fabricate(inputs, change):
    def patch(q):
        e = q['external_planning']
        if change == 'missing': q.pop('external_planning')
        elif change == 'unqualified': q['rights_basis']['qualification'] = 'unqualified'
        elif change == 'literal': e['reviewed_claims'][0]['literal'] = 'NVIDIA ($2B)'
        elif change == 'quantity': e['reviewed_claims'][0]['quantity_literal'] = '$2B'
        elif change == 'substring': e['reviewed_claims'][4]['quantity_literal'] = '0'
        elif change == 'tier': e['reviewed_claims'][0]['tier'] = 'first_party'
        elif change == 'ticker': e['reviewed_tickers'] = {'FAKE': 'NVIDIA'}
        elif change == 'arithmetic': e['derived_share']['percent'] = '63'
        elif change == 'feed': e['feed_url'] = 'https://www.whitehouse.gov/news/feed/'
    mutate(inputs, 'qualification', patch)
    with pytest.raises(ValueError): P.plan_external_candidate(**inputs)


def test_existing_coverage_blocks_same_source_even_with_new_revision(inputs):
    first = P.plan_external_candidate(**inputs)
    root = inputs['root']
    stage = root / 'data/press/staging'; stage.mkdir(parents=True, exist_ok=True)
    (stage / 'prior.json').write_text(json.dumps({'sources': [first['source_ref']], 'status': 'in_progress'}))
    mutate(inputs, 'qualification', lambda q: q.update(observed_at='2026-10-11T20:00:00Z'))
    second = P.plan_external_candidate(**inputs)
    assert second['candidate_id'] != first['candidate_id']
    assert second['blocked_by_existing_coverage'] is True
    assert second['allow_stage'] is False


def test_missing_dossier_never_creates_a_route(inputs):
    (inputs['root'] / 'site/stocks/NVDA.html').unlink()
    with pytest.raises(ValueError, match='rendered dossier'): P.plan_external_candidate(**inputs)


def republish(inputs, published):
    from engine.whitehouse_feed import _slug_id
    def patch_document(d):
        d['published'] = published
        d['id'] = _slug_id(d['url'], published)
    mutate(inputs, 'document', patch_document)
    d = json.loads(inputs['document_path'].read_text())
    mutate(inputs, 'qualification', lambda q: q['existing_feed_ingress']['candidate'].update(
        published=d['published'], id=d['id']))


def test_later_publication_retains_reviewed_event_clock(inputs):
    # The source event remains October 8 even when the page is published later.
    republish(inputs, '2026-10-09T15:05:06+00:00')
    result = P.plan_external_candidate(**inputs)
    clocks = result['source_clocks']
    assert clocks['event_date'] == '2026-10-08'
    assert clocks['published_at'] == '2026-10-09T15:05:06+00:00'
    assert {fact['dated'] for fact in result['validation_context']['facts']} == {'2026-10-08'}
    assert result['allow_stage'] is result['allow_emit'] is False


def test_later_publication_cannot_refresh_expired_event(inputs):
    republish(inputs, '2026-10-09T15:05:06+00:00')
    inputs['as_of'] = '2026-10-12T00:00:00Z'
    with pytest.raises(ValueError, match='event.*window'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('event_date', ['2026-10-09', '2026-13-08', '20261008', None, 20261008])
def test_invalid_or_postpublication_event_date_rejected(inputs, event_date):
    mutate(inputs, 'qualification', lambda q: q.update(event_date=event_date))
    with pytest.raises(ValueError):
        P.plan_external_candidate(**inputs)
