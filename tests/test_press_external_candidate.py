"""External source planning must not become writer or publication admission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.press import desk_planner as P
from tests import press_fixtures as F

HERE = Path(__file__).resolve().parents[1] / 'research/agentic_media/public_intelligence_20261011'
NEWS_FEED = 'https://www.whitehouse.gov/news/feed/'
FACT_FEED = 'https://www.whitehouse.gov/fact-sheets/feed/'
RESEARCH_URL = (
    'https://www.whitehouse.gov/research/2026/10/'
    'fact-sheet-trump-administration-announces-the-most-ambitious-set-of-science-initiatives-this-century/'
)


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


def test_explicit_no_share_keeps_only_reviewed_source_claims(inputs):
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(derived_share=None))
    result = P.plan_external_candidate(**inputs)
    claims = json.loads(inputs['qualification_path'].read_text())['external_planning']['reviewed_claims']
    facts = result['validation_context']['facts']
    assert [fact['text'] for fact in facts] == [claim['literal'] for claim in claims]
    assert all(fact['tier'] == 'third_party' for fact in facts)
    assert all(not fact.get('derived_from_external') for fact in facts)
    assert result['validation_context']['allowed_links'] == ['https://www.mastermind-x.com/stocks/NVDA.html']
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert result['cadence_consumed'] is False


@pytest.mark.parametrize('value', [{}, [], False, '', {'percent': '0'}])
def test_no_share_requires_explicit_null_not_a_malformed_calculation(inputs, value):
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(derived_share=value))
    with pytest.raises(ValueError, match='share derivation'):
        P.plan_external_candidate(**inputs)


def test_missing_share_review_is_not_implicit_no_share(inputs):
    mutate(inputs, 'qualification', lambda q: q['external_planning'].pop('derived_share'))
    with pytest.raises(ValueError, match='explicit external planning'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('gate', ['rights', 'event', 'ticker', 'literal'])
def test_no_share_keeps_other_qualification_gates(inputs, gate):
    def change(q):
        q['external_planning']['derived_share'] = None
        if gate == 'rights': q['rights_basis']['qualification'] = 'unqualified'
        elif gate == 'event': q['event_date'] = '2026-10-01'
        elif gate == 'ticker': q['external_planning']['reviewed_tickers'] = {'FAKE': 'NVIDIA'}
        elif gate == 'literal': q['external_planning']['reviewed_claims'][0]['literal'] = 'invented'
    mutate(inputs, 'qualification', change)
    with pytest.raises(ValueError):
        P.plan_external_candidate(**inputs)


def qualify_context(inputs, *, dated='2026-10-10', fact_id='market_state_score'):
    artifact = 'data/market_state/latest.json'
    path = inputs['root'] / artifact
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = dump(path, {'asof': dated, 'score': 53, 'verdict': 'MIXED'})
    row = {'id': fact_id, 'artifact': artifact, 'sha256': digest,
           'relevance': 'Market backdrop for interpreting the announced investment; not evidence of its price effect.'}
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    return path, row


def test_reviewed_context_uses_bound_engine_bytes_without_promoting_external_claims(inputs):
    path, row = qualify_context(inputs)
    before = path.read_bytes()
    result = P.plan_external_candidate(**inputs)
    facts = result['validation_context']['facts']
    assert len(facts) == 10
    assert {fact['tier'] for fact in facts[:-1]} == {'third_party'}
    assert facts[-1]['id'] == 'market_state_score'
    assert facts[-1]['values'] == ['53']
    assert facts[-1]['tier'] == 'first_party'
    assert facts[-1]['dated'] == '2026-10-10'
    assert facts[-1]['receipt'] == 'sha256:' + row['sha256']
    assert facts[-1]['context_relevance'] == row['relevance']
    assert result['source_revisions']['artifact:data/market_state/latest.json'] == facts[-1]['receipt']
    assert path.read_bytes() == before
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False


@pytest.mark.parametrize('dated', ['2026-10-07', '2026-10-12', None, '2026-13-10'])
def test_reviewed_context_rejects_stale_future_missing_or_invalid_date(inputs, dated):
    qualify_context(inputs, dated=dated)
    with pytest.raises(ValueError, match='context.*date|context.*window'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('change', ['hash', 'artifact', 'id', 'duplicate', 'empty', 'relevance', 'tier'])
def test_reviewed_context_cannot_inject_or_relabel_facts(inputs, change):
    path, _ = qualify_context(inputs)
    if change == 'hash':
        path.write_text(path.read_text() + ' ')
    else:
        def patch(q):
            rows = q['external_planning']['first_party_context']
            if change == 'artifact': rows[0]['artifact'] = 'data/vendor/news.json'
            elif change == 'id': rows[0]['id'] = 'invented_fact'
            elif change == 'duplicate': rows.append(rows[0].copy())
            elif change == 'empty': rows.clear()
            elif change == 'relevance': rows[0]['relevance'] = ''
            elif change == 'tier': rows[0]['tier'] = 'first_party'
        mutate(inputs, 'qualification', patch)
    with pytest.raises(ValueError):
        P.plan_external_candidate(**inputs)


def test_reviewed_context_rejects_symlinked_artifact(inputs, tmp_path):
    path, _ = qualify_context(inputs)
    outside = tmp_path / 'outside.json'
    path.rename(outside)
    path.symlink_to(outside)
    with pytest.raises(ValueError):
        P.plan_external_candidate(**inputs)


def test_selected_measurements_meet_receipt_floor_but_do_not_approve_story(inputs):
    from engine.press import validators as V
    plain = P.plan_external_candidate(**inputs)['validation_context']
    path, row = qualify_context(inputs)
    payload = json.loads(path.read_text())
    payload['components'] = [
        {'key': key, 'label_en': key, 'score': score, 'weight': 0.2}
        for key, score in [('trend', 71), ('risk', 29), ('vol', 83), ('breadth', 17)]
    ]
    digest = dump(path, payload)
    rows = [{**row, 'id': fid, 'sha256': digest} for fid in [
        'market_state_score', 'market_state_trend', 'market_state_risk',
        'market_state_vol', 'market_state_breadth']]
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=rows))
    context = P.plan_external_candidate(**inputs)['validation_context']
    draft = {'body_html': '<p>The market-state composite reads 53. Trend scores 71. '
             'Risk appetite scores 29. Volatility scores 83. Breadth scores 17.</p>'}
    cfg = P.load_config(inputs['root'])
    assert V.check_receipts(draft, plain, cfg)['ok'] is False
    result = V.check_receipts(draft, context, cfg)
    assert result['ok'] is True
    assert context['min_anchored_receipts'] == 5
    assert set(result['metrics']['values']) == {53, 71, 29, 83, 17}


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


def retarget(inputs, url, section, feed_url):
    from engine.whitehouse_feed import _slug_id
    def patch_document(d):
        d['url'] = url
        d['section'] = section
        d['id'] = _slug_id(url, d['published'])
    mutate(inputs, 'document', patch_document)
    d = json.loads(inputs['document_path'].read_text())
    def patch_qualification(q):
        q['existing_feed_ingress']['url'] = feed_url
        q['existing_feed_ingress']['candidate'].update(
            url=d['url'], section=d['section'], id=d['id'])
        q['external_planning']['feed_url'] = feed_url
    mutate(inputs, 'qualification', patch_qualification)


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


def test_aggregate_feed_fact_sheet_is_planning_only(inputs):
    url = json.loads(inputs['document_path'].read_text())['url']
    retarget(inputs, url=url, section='news', feed_url=NEWS_FEED)
    result = P.plan_external_candidate(**inputs)
    assert result['operation'] == 'planning_only'
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert result['cadence_consumed'] is False
    assert '/fact-sheets/' in result['validation_context']['primary_source']['url']
    assert result['validation_context']['facts'][-1]['values'] == ['62.5']


def test_aggregate_research_route_keeps_reviewed_fixture_identity(inputs):
    retarget(inputs, url=RESEARCH_URL, section='news', feed_url=NEWS_FEED)
    result = P.plan_external_candidate(**inputs)
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert '/research/' in result['validation_context']['primary_source']['url']
    assert result['validation_context']['allowed_links'] == ['https://www.mastermind-x.com/stocks/NVDA.html']
    assert result['source_ref'].endswith(
        'fact-sheet-trump-administration-announces-the-most-ambitious-set-of-science-init')


def test_section_specific_feed_rejects_other_canonical_path(inputs):
    retarget(inputs, url=RESEARCH_URL, section='fact-sheets', feed_url=FACT_FEED)
    with pytest.raises(ValueError, match='canonical White House document'):
        P.plan_external_candidate(**inputs)


def test_unknown_aggregate_route_rejected(inputs):
    retarget(inputs, url=(
        'https://www.whitehouse.gov/administration/2026/10/'
        'fact-sheet-trump-administration-announces-the-most-ambitious-set-of-science-initiatives-this-century/'
    ), section='news', feed_url=NEWS_FEED)
    with pytest.raises(ValueError, match='canonical White House document'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('url', [
    'https://www.whitehouse.gov/news/../fact-sheets/secret/',
    'https://www.whitehouse.gov/news/%2e%2e/fact-sheets/secret/',
    'https://www.whitehouse.gov/news/%2ffact-sheets/secret/',
    'https://www.whitehouse.gov/fact-sheets%2f2026/10/slug/',
    'https://www.whitehouse.gov/news//fact-sheets/secret/',
    'https://www.whitehouse.gov/news/./fact-sheets/secret/',
    'https://www.whitehouse.gov/news/2026/10/slu\ng/',
    '\thttps://www.whitehouse.gov/news/2026/10/slug/',
    'https://www.whitehouse.gov/news/2026/10/slug/?',
])
def test_malformed_or_encoded_separator_routes_rejected(inputs, url):
    retarget(inputs, url=url, section='news', feed_url=NEWS_FEED)
    with pytest.raises(ValueError, match='canonical White House document'):
        P.plan_external_candidate(**inputs)


def test_aggregate_feed_identity_mismatch_rejected(inputs):
    url = json.loads(inputs['document_path'].read_text())['url']
    retarget(inputs, url=url, section='news', feed_url=NEWS_FEED)
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(feed_url=FACT_FEED))
    with pytest.raises(ValueError, match='feed identity'):
        P.plan_external_candidate(**inputs)


def test_unknown_section_cannot_match_a_missing_feed(inputs):
    retarget(inputs, url='https://www.whitehouse.gov/unknown/2026/10/slug/',
             section='unknown', feed_url=None)
    with pytest.raises(ValueError, match='feed identity'):
        P.plan_external_candidate(**inputs)


def test_aggregate_body_requires_its_own_qualification(inputs):
    url = json.loads(inputs['document_path'].read_text())['url']
    retarget(inputs, url=url, section='news', feed_url=NEWS_FEED)
    def change_body(document):
        document['body'] = 'Different aggregate heading\n' + document['body']
        document['body_sha256'] = hashlib.sha256(document['body'].encode()).hexdigest()
    mutate(inputs, 'document', change_body)
    with pytest.raises(ValueError, match='source body hash mismatch'):
        P.plan_external_candidate(**inputs)


def test_aggregate_admission_does_not_bypass_freshness_or_rights(inputs):
    url = json.loads(inputs['document_path'].read_text())['url']
    retarget(inputs, url=url, section='news', feed_url=NEWS_FEED)
    inputs['as_of'] = '2026-10-12T00:00:00Z'
    with pytest.raises(ValueError, match='event.*window'):
        P.plan_external_candidate(**inputs)
    inputs['as_of'] = '2026-10-11T23:00:00Z'
    mutate(inputs, 'qualification', lambda q: q['rights_basis'].update(qualification='unqualified'))
    with pytest.raises(ValueError, match='rights qualification'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('payload', [
    {'asof': '2026-10-10', 'score': 53, 'verdict': 'MIXED', 'components': {'trend': 70}},
    {'asof': '2026-10-10', 'score': 53, 'verdict': 'MIXED', 'components': 7},
])
def test_malformed_extractor_payload_rejects_as_value_error(inputs, payload):
    path, row = qualify_context(inputs)
    row['sha256'] = dump(path, payload)
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    with pytest.raises(ValueError, match='artifact is malformed'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('rows', [None, {}, 'none', [], [{}] * 21])
def test_context_presence_requires_nonempty_bounded_review_not_null(inputs, rows):
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=rows))
    with pytest.raises(ValueError, match='bounded reviewed'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('artifact', ['/data/market_state/latest.json', 'data/../data/market_state/latest.json'])
def test_context_artifact_identity_is_canonical_relative_path(inputs, artifact):
    _, row = qualify_context(inputs)
    row['artifact'] = artifact
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    with pytest.raises(ValueError, match='identity'):
        P.plan_external_candidate(**inputs)


def test_conflicting_context_revisions_reject_without_rereading(inputs, monkeypatch):
    from engine.press import external_candidate as E
    _, row = qualify_context(inputs)
    other = {**row, 'id': 'market_state_trend', 'sha256': 'a' * 64}
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row, other]))
    read, calls = E._read_bound, []
    def count(path, *args):
        calls.append(path)
        return read(path, *args)
    monkeypatch.setattr(E, '_read_bound', count)
    with pytest.raises(ValueError, match='conflicting artifact revisions'):
        P.plan_external_candidate(**inputs)
    assert calls.count(inputs['root'] / row['artifact']) == 1


def test_reviewed_context_rejects_symlinked_parent_even_for_identical_bytes(inputs, tmp_path):
    path, _ = qualify_context(inputs)
    outside = tmp_path / 'engine-data'
    path.parent.rename(outside)
    path.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='traverse a symlink'):
        P.plan_external_candidate(**inputs)


@pytest.mark.parametrize('suffix', ['', '\nnot-json', '\n[]'])
def test_reviewed_risk_history_requires_complete_object_jsonl(inputs, suffix):
    artifact = 'data/risk_radar/forward_log.jsonl'
    path = inputs['root'] / artifact
    path.parent.mkdir(parents=True, exist_ok=True)
    history = [dict(asof='2026-10-09', state='watch', dominant_scare='rates', top_score=45,
                    drawdown_prob={'h21': 0.12}),
               dict(asof='2026-10-10', state='caution', dominant_scare='rates', top_score=70,
                    drawdown_prob={'h21': 0.19, 'h10': 0.11, 'h5': 0.06})]
    path.write_text('\n'.join(json.dumps(row) for row in history) + suffix + '\n')
    row = dict(id='risk_radar', artifact=artifact, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               relevance='Dated risk backdrop, not evidence of the event effect.')
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    if suffix:
        with pytest.raises(ValueError, match='artifact is malformed'):
            P.plan_external_candidate(**inputs)
    else:
        fact = P.plan_external_candidate(**inputs)['validation_context']['facts'][-1]
        assert fact['id'] == 'risk_radar' and fact['dated'] == '2026-10-10'
        # This legacy row has no target/calibration evidence. Keep its dated
        # state receipt, but do not make its naked probabilities quotable.
        assert fact['values'] == ['70']
        assert 'probability' not in fact['text']
        assert fact['receipt'] == 'sha256:' + row['sha256']


def test_no_share_plus_context_changes_candidate_identity_and_writes_nothing(inputs):
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(derived_share=None))
    plain = P.plan_external_candidate(**inputs)
    qualify_context(inputs)
    snapshot = lambda: {str(p): p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}
    before = snapshot()
    result = P.plan_external_candidate(**inputs)
    assert result['candidate_id'] != plain['candidate_id']
    assert result['validation_context']['facts'][:-1] == plain['validation_context']['facts']
    assert len(result['validation_context']['facts']) == len(plain['validation_context']['facts']) + 1
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert snapshot() == before


@pytest.mark.parametrize('relevance', ['  ', 'x' * 501])
def test_context_relevance_must_be_bounded_substantive_metadata(inputs, relevance):
    _, row = qualify_context(inputs)
    row['relevance'] = relevance
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    with pytest.raises(ValueError, match='relevance'):
        P.plan_external_candidate(**inputs)


def test_external_literals_alone_do_not_count_as_our_measurements(inputs):
    from engine.press import validators as V
    plain = P.plan_external_candidate(**inputs)['validation_context']
    draft = {'body_html': '<p>' + '. '.join(f['text'] for f in plain['facts']) + '.</p>'}
    cfg = P.load_config(inputs['root'])
    assert V.check_receipts(draft, plain, cfg)['ok'] is False
    assert V.check_our_value(draft, plain, cfg)['ok'] is False


def test_reviewed_context_cannot_admit_lexicon_violating_engine_text(inputs):
    path, row = qualify_context(inputs)
    row['sha256'] = dump(path, {'asof': '2026-10-10', 'score': 53, 'verdict': 'guaranteed'})
    mutate(inputs, 'qualification', lambda q: q['external_planning'].update(first_party_context=[row]))
    with pytest.raises(ValueError, match='Press lexicon'):
        P.plan_external_candidate(**inputs)


# Exact-date retained Treasury context (synthetic, offline fixtures).
"""Opt-in Treasury parquet context: exact dates, hash custody, no inflation.

Every fixture in this file is synthetic and written under tmp_path. Nothing
here reads the repository's own data/ tree, invokes a candidate stager, calls a
provider or touches the ledger.
"""

import hashlib
import io
import json
from datetime import date

import pandas as pd
import pytest

from engine.press import desk_planner as P
from engine.press.external_candidate import _reviewed_context
from engine.press.market_snapshot_candidate import plan_market_snapshot_candidate

OBSERVATION = '2026-10-29'
PRIOR = '2026-10-28'
# The eligible same-date example: 10y - 2y = 0.37 and 10y - real 10y = 2.35.
VALUES = {
    'treasury_dgs2': ('data/fred/DGS2.parquet', 'us2y', 4.61),
    'treasury_dgs10': ('data/fred/DGS10.parquet', 'us10y', 4.98),
    'treasury_dgs30': ('data/fred/DGS30.parquet', 'us30y', 5.32),
    'treasury_dfii10': ('data/fred/DFII10.parquet', 'us10y_real', 2.63),
    'treasury_t10yie': ('data/fred/T10YIE.parquet', 'breakeven_10y', 2.35),
    'treasury_t10y2y': ('data/fred/T10Y2Y.parquet', 'spread_2s10s', 0.37),
}
CFG = {'desks': {'brief': {'publication': 'mastermind_news', 'byline': 'The Brief',
                           'min_words': 300, 'max_words': 600,
                           'min_anchored_receipts': 5, 'cadence_per_day': 2,
                           'window_days': 3}}}
RELEVANCE = ('Retained dated Treasury yield measurement; display only, with no '
             'forecast, causal or independence claim.')


def write_frame(root, rel, frame):
    """Retain one synthetic parquet file and return its digest."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine='pyarrow')
    path.write_bytes(buffer.getvalue())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_for(column, rows, index=None):
    labels = index if index is not None else pd.DatetimeIndex(
        [pd.Timestamp(day) for day, _ in rows], name='observation_date')
    return pd.DataFrame({column: [value for _, value in rows]}, index=labels)


def build_root(tmp_path, *, dates=(PRIOR, OBSERVATION), overrides=None, skip=()):
    """Write the retained series and return (root, {fact_id: digest})."""
    root = tmp_path / 'root'
    overrides = overrides or {}
    digests = {}
    for fact_id, (rel, column, value) in VALUES.items():
        if fact_id in overrides or fact_id in skip:
            continue
        digests[fact_id] = write_frame(
            root, rel, frame_for(column, [(day, value) for day in dates]))
    for fact_id, frame in overrides.items():
        digests[fact_id] = write_frame(root, VALUES[fact_id][0], frame)
    return root, digests


def context_rows(digests, *, only=None):
    rows = []
    for fact_id, (rel, _column, _value) in VALUES.items():
        if fact_id not in digests or (only is not None and fact_id not in only):
            continue
        rows.append({'id': fact_id, 'artifact': rel, 'sha256': digests[fact_id],
                     'relevance': RELEVANCE})
    return rows


def select(root, rows, *, as_of=date(2026, 10, 30), window_days=3,
           observation_date=OBSERVATION):
    return _reviewed_context(rows, root=root, as_of=as_of, window_days=window_days,
                             observation_date=observation_date)


def test_six_retained_series_select_the_requested_date_only(tmp_path):
    root, digests = build_root(tmp_path)
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    facts, revisions = select(root, context_rows(digests))
    assert [fact['id'] for fact in facts] == list(VALUES)
    assert [fact['values'] for fact in facts] == [
        ['4.61'], ['4.98'], ['5.32'], ['2.63'], ['2.35'], ['0.37']]
    assert all(fact['tier'] == 'first_party' for fact in facts)
    assert all(fact['dated'] == OBSERVATION for fact in facts)
    assert all(fact['ref'] == 'artifact:' + VALUES[fact['id']][0] for fact in facts)
    assert all(fact['receipt'] == 'sha256:' + digests[fact['id']] for fact in facts)
    assert revisions == {fact['ref']: fact['receipt'] for fact in facts}
    assert all('FRED series' in fact['source_name'] for fact in facts)
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_the_fact_text_names_the_retained_series_the_date_and_the_unit(tmp_path):
    root, digests = build_root(tmp_path)
    facts, _ = select(root, context_rows(digests))
    for fact in facts:
        text = fact['text'].lower()
        assert fact['source_series'].lower() in text
        assert OBSERVATION in text
        assert fact['unit'] in text
        assert fact['observation_date'] == OBSERVATION
        assert fact['source_artifact'] == VALUES[fact['id']][0]
        for claim in ('predict', 'expect', 'forecast', 'caus', 'independent', 'first-known'):
            assert claim not in text
    derived = {fact['id']: fact.get('derived_from') for fact in facts}
    assert derived['treasury_t10y2y'] == ['treasury_dgs10', 'treasury_dgs2']
    assert derived['treasury_t10yie'] == ['treasury_dgs10', 'treasury_dfii10']
    assert derived['treasury_dgs2'] is None


def test_the_same_observation_date_leaves_the_three_day_window(tmp_path):
    root, digests = build_root(tmp_path)
    with pytest.raises(ValueError, match='window'):
        select(root, context_rows(digests), as_of=date(2026, 11, 2))


def test_observation_is_not_a_publication_ingestion_or_vintage_receipt(tmp_path):
    root, digests = build_root(tmp_path)
    facts, _ = select(root, context_rows(digests))
    for fact in facts:
        provenance = fact['source_provenance']
        assert provenance['observation'] == {
            'state': 'present', 'date': OBSERVATION, 'precision': 'day'}
        for key in ('publication_time', 'first_known_time', 'vintage'):
            assert provenance[key]['state'] == 'unavailable'
            assert provenance[key]['value'] is None
            assert provenance[key]['reason']
        assert provenance['rights_admission'] == 'not_granted_by_extraction'


def test_the_last_day_of_the_window_is_still_inside_it(tmp_path):
    root, digests = build_root(tmp_path)
    facts, _ = select(root, context_rows(digests), as_of=date(2026, 11, 1))
    assert len(facts) == 6


def test_an_observation_date_after_the_run_is_refused(tmp_path):
    root, digests = build_root(tmp_path, dates=(PRIOR, OBSERVATION, '2026-10-31'))
    with pytest.raises(ValueError, match='window'):
        select(root, context_rows(digests), observation_date='2026-10-31')


def test_a_missing_observation_date_is_not_filled_from_a_neighbouring_row(tmp_path):
    root, digests = build_root(tmp_path, overrides={
        'treasury_dgs2': frame_for('us2y', [(PRIOR, 4.61), ('2026-10-30', 4.61)])})
    with pytest.raises(ValueError, match='observation date'):
        select(root, context_rows(digests))


def test_a_ragged_latest_is_not_carried_forward(tmp_path):
    root, digests = build_root(
        tmp_path, dates=(PRIOR, OBSERVATION, '2026-10-30'),
        overrides={'treasury_dgs2': frame_for('us2y', [(PRIOR, 4.61), (OBSERVATION, 4.61)])})
    with pytest.raises(ValueError, match='observation date'):
        select(root, context_rows(digests), observation_date='2026-10-30')
    assert len(select(root, context_rows(digests))[0]) == 6


@pytest.mark.parametrize('fact_id,stale', [('treasury_t10y2y', 0.30), ('treasury_t10yie', 2.30)])
def test_a_derived_series_that_breaks_its_identity_is_refused(tmp_path, fact_id, stale):
    _rel, column, _value = VALUES[fact_id]
    root, digests = build_root(tmp_path, overrides={
        fact_id: frame_for(column, [(PRIOR, stale), (OBSERVATION, stale)])})
    with pytest.raises(ValueError, match='identity'):
        select(root, context_rows(digests))


def test_a_derived_series_without_its_selected_dependencies_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    rows = context_rows(digests, only={'treasury_t10y2y'})
    with pytest.raises(ValueError, match='dependencies'):
        select(root, rows)


def test_raw_yields_alone_need_no_derived_series(tmp_path):
    root, digests = build_root(tmp_path)
    rows = context_rows(digests, only={'treasury_dgs2', 'treasury_dgs10', 'treasury_dgs30'})
    facts, _ = select(root, rows)
    assert [fact['id'] for fact in facts] == [
        'treasury_dgs2', 'treasury_dgs10', 'treasury_dgs30']


def test_a_wrong_column_is_refused(tmp_path):
    root, digests = build_root(tmp_path, overrides={
        'treasury_dgs2': frame_for('us10y', [(PRIOR, 4.61), (OBSERVATION, 4.61)])})
    with pytest.raises(ValueError, match='schema'):
        select(root, context_rows(digests))


def test_a_second_column_is_refused(tmp_path):
    frame = frame_for('us2y', [(PRIOR, 4.61), (OBSERVATION, 4.61)])
    frame['extra'] = [1.0, 2.0]
    root, digests = build_root(tmp_path, overrides={'treasury_dgs2': frame})
    with pytest.raises(ValueError, match='schema'):
        select(root, context_rows(digests))


@pytest.mark.parametrize('bad', [float('nan'), float('inf')])
def test_a_nonfinite_value_is_refused(tmp_path, bad):
    root, digests = build_root(tmp_path, overrides={
        'treasury_dgs2': frame_for('us2y', [(PRIOR, 4.61), (OBSERVATION, bad)])})
    with pytest.raises(ValueError, match='finite'):
        select(root, context_rows(digests))


@pytest.mark.parametrize('bad', ['4.61', True])
def test_a_nonnumeric_or_boolean_value_is_refused(tmp_path, bad):
    root, digests = build_root(tmp_path, overrides={
        'treasury_dgs2': frame_for('us2y', [(PRIOR, bad), (OBSERVATION, bad)])})
    with pytest.raises(ValueError, match='numeric'):
        select(root, context_rows(digests))


@pytest.mark.parametrize('index', [
    pd.Index(['2026-10-28', '2026-10-29'], dtype='object'),
    pd.DatetimeIndex([pd.Timestamp('2026-10-28 06:00'), pd.Timestamp('2026-10-29 06:00')]),
    pd.DatetimeIndex([pd.Timestamp('2026-10-29'), pd.Timestamp('2026-10-28')]),
    pd.DatetimeIndex([pd.Timestamp('2026-10-28'), pd.Timestamp('2026-10-28')]),
    pd.DatetimeIndex([pd.Timestamp('2026-10-28', tz='UTC'), pd.Timestamp('2026-10-29', tz='UTC')]),
])
def test_a_malformed_index_is_refused(tmp_path, index):
    frame = pd.DataFrame({'us2y': [4.61, 4.61]}, index=index)
    root, digests = build_root(tmp_path, overrides={'treasury_dgs2': frame})
    with pytest.raises(ValueError, match='treasury'):
        select(root, context_rows(digests))


def test_a_hash_mismatch_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    rows = context_rows(digests)
    rows[0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='hash'):
        select(root, rows)


def test_a_symlinked_series_file_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    rel = VALUES['treasury_dgs2'][0]
    held = tmp_path / 'held-DGS2.parquet'
    held.write_bytes((root / rel).read_bytes())
    (root / rel).unlink()
    (root / rel).symlink_to(held)
    with pytest.raises(ValueError, match='symlink'):
        select(root, context_rows(digests))


def test_a_symlinked_parent_directory_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    fred = root / 'data/fred'
    moved = tmp_path / 'fred-moved'
    fred.rename(moved)
    fred.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        select(root, context_rows(digests))


def test_an_unsupported_source_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    rows = context_rows(digests)
    rows[0] = dict(rows[0], artifact='data/fred/OTHER.parquet')
    with pytest.raises(ValueError, match='identity or relevance'):
        select(root, rows)


def test_an_unknown_fact_id_is_refused(tmp_path):
    root, digests = build_root(tmp_path)
    rows = context_rows(digests)
    rows[0] = dict(rows[0], id='treasury_dgs5')
    with pytest.raises(ValueError, match='unknown treasury fact id'):
        select(root, rows)


def test_the_treasury_series_stay_closed_without_the_opt_in(tmp_path):
    root, digests = build_root(tmp_path)
    with pytest.raises(ValueError, match='observation date'):
        _reviewed_context(context_rows(digests), root=root, as_of=date(2026, 10, 30),
                          window_days=3)


def test_the_incumbent_json_context_is_unchanged_without_an_observation_date(tmp_path):
    root = tmp_path / 'root'
    rel = 'data/market_state/latest.json'
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        'asof': OBSERVATION, 'score': 53, 'verdict': 'MIXED',
        'components': [{'key': 'risk', 'label_en': 'Risk appetite', 'score': 14, 'weight': 0.18},
                       {'key': 'breadth', 'label_en': 'Breadth', 'score': 24, 'weight': 0.16}]}))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = [{'id': fact_id, 'artifact': rel, 'sha256': digest, 'relevance': RELEVANCE}
            for fact_id in ('market_state_score', 'market_state_risk', 'market_state_breadth')]
    facts, revisions = _reviewed_context(rows, root=root, as_of=date(2026, 10, 30),
                                         window_days=3)
    assert [fact['id'] for fact in facts] == [
        'market_state_score', 'market_state_risk', 'market_state_breadth']
    assert all(fact['tier'] == 'first_party' for fact in facts)
    assert all(fact['dated'] == OBSERVATION for fact in facts)
    assert revisions == {'artifact:data/market_state/latest.json': 'sha256:' + digest}


def candidate_inputs(tmp_path, root, digests):
    qualification = tmp_path / 'qualification.json'
    qualification.write_text(json.dumps({
        'schema': 'press.market_snapshot_qualification.v1',
        'proposition_id': 'treasury-curve',
        'observation_date': OBSERVATION,
        'first_party_context': context_rows(digests),
        'review_result': 'accepted_as_market_candidate_only',
        'allow_stage': False, 'allow_emit': False, 'publication_approved': False}))
    return {'qualification_path': qualification,
            'qualification_sha256': hashlib.sha256(qualification.read_bytes()).hexdigest()}


def test_the_candidate_plan_is_planning_only_and_leaves_the_fixtures_untouched(
        tmp_path, monkeypatch):
    root, digests = build_root(tmp_path)
    inputs = candidate_inputs(tmp_path, root, digests)
    monkeypatch.setattr(P, 'published_refs', lambda *a, **k: (set(), set()))
    monkeypatch.setattr(P, 'staged_refs', lambda *a, **k: (set(), set()))
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = plan_market_snapshot_candidate(**inputs, root=root,
                                            as_of='2026-10-30T00:00:00Z', cfg=CFG)
    assert result['operation'] == 'planning_only'
    assert result['allow_stage'] is False and result['allow_emit'] is False
    assert result['publication_approved'] is False and result['cadence_consumed'] is False
    assert result['observation_date'] == OBSERVATION
    facts, revisions = select(root, context_rows(digests))
    assert result['validation_context']['facts'] == facts
    assert all(result['source_revisions'][ref] == receipt
               for ref, receipt in revisions.items())
    assert set(result['source_revisions']) == {
        f'artifact:{rel}' for rel, _column, _value in VALUES.values()} | {result['source_ref']}
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_the_candidate_keeps_the_three_day_window_for_treasury_rows(tmp_path, monkeypatch):
    root, digests = build_root(tmp_path)
    inputs = candidate_inputs(tmp_path, root, digests)
    monkeypatch.setattr(P, 'published_refs', lambda *a, **k: (set(), set()))
    monkeypatch.setattr(P, 'staged_refs', lambda *a, **k: (set(), set()))
    with pytest.raises(ValueError, match='window'):
        plan_market_snapshot_candidate(**inputs, root=root,
                                       as_of='2026-11-02T00:00:00Z', cfg=CFG)

# ON RRP adds one measurement, not a receipt multiplier or admission exemption.
from engine.press import rrp_context as RRP
from engine.press import validators as RRP_V


def rrp_inputs(tmp_path, *, frame=None):
    root = tmp_path / 'rrp'
    if frame is None:
        frame = frame_for('on_rrp', [('2026-10-30', 4.375), ('2026-11-02', 5.087)])
    digest = write_frame(root, RRP.ARTIFACT, frame)
    row = dict(id=RRP.FACT_ID, artifact=RRP.ARTIFACT, sha256=digest,
               relevance='Dated overnight RRP usage only; no liquidity or causal inference.')
    return root, row


def rrp_select(root, row, *, observed='2026-11-02', cutoff=date(2026, 11, 3)):
    return _reviewed_context([row], root=root, as_of=cutoff, window_days=3,
                             observation_date=observed)


def test_rrp_one_exact_measurement_preserves_units_origin_and_unknown_clocks(tmp_path):
    root, row = rrp_inputs(tmp_path)
    before = (root / RRP.ARTIFACT).read_bytes()
    facts, revisions = rrp_select(root, row)
    assert len(facts) == 1
    fact = facts[0]
    assert fact['values'] == ['5.087']
    assert fact['dated'] == '2026-11-02'
    assert fact['unit'] == 'billions of US dollars'
    assert fact['source_series'] == 'RRPONTSYD'
    assert 'Federal Reserve Bank of New York' in fact['source_name']
    assert fact['source_url'] == 'https://fred.stlouisfed.org/series/RRPONTSYD'
    assert revisions == {'artifact:' + RRP.ARTIFACT: 'sha256:' + row['sha256']}
    assert all(fact['source_provenance'][key]['state'] == 'unavailable'
               for key in ('publication_time', 'first_known_time', 'vintage'))
    assert fact['source_provenance']['rights_admission'] == 'not_granted_by_extraction'
    assert (root / RRP.ARTIFACT).read_bytes() == before


@pytest.mark.parametrize('observed', [None, '2026-11-01', '2026-11-02T00:00:00',
                                     '2026-02-30', '2026-11-04'])
def test_rrp_missing_or_inexact_date_never_uses_latest(tmp_path, observed):
    root, row = rrp_inputs(tmp_path)
    with pytest.raises(ValueError):
        rrp_select(root, row, observed=observed)


@pytest.mark.parametrize('cutoff', [date(2026, 11, 1), date(2026, 11, 6)])
def test_rrp_original_window_rejects_future_or_stale_measurement(tmp_path, cutoff):
    root, row = rrp_inputs(tmp_path)
    with pytest.raises(ValueError, match='window'):
        rrp_select(root, row, cutoff=cutoff)


@pytest.mark.parametrize('mutation', ['hash', 'id', 'path', 'symlink', 'duplicate_selection'])
def test_rrp_custody_or_identity_mismatch_refuses(tmp_path, mutation):
    root, row = rrp_inputs(tmp_path)
    if mutation == 'hash':
        row['sha256'] = '0' * 64
    elif mutation == 'id':
        row['id'] = 'rrp_counterparties'
    elif mutation == 'path':
        row['artifact'] = 'data/fred/OTHER.parquet'
    elif mutation == 'symlink':
        path = root / RRP.ARTIFACT
        saved = path.with_suffix('.saved')
        path.rename(saved)
        path.symlink_to(saved)
    with pytest.raises(ValueError):
        _reviewed_context([row, row] if mutation == 'duplicate_selection' else [row],
                          root=root, as_of=date(2026, 11, 3), window_days=3,
                          observation_date='2026-11-02')


@pytest.mark.parametrize('mutation', ['column', 'duplicate_date', 'unsorted', 'intraday',
                                     'timezone', 'negative', 'nan', 'boolean'])
def test_rrp_malformed_measurement_refuses(tmp_path, mutation):
    frame = frame_for('on_rrp', [('2026-10-30', 4.375), ('2026-11-02', 5.087)])
    if mutation == 'column':
        frame.columns = ['counterparties']
    elif mutation == 'duplicate_date':
        frame.index = pd.DatetimeIndex(['2026-11-02', '2026-11-02'])
    elif mutation == 'unsorted':
        frame = frame.iloc[::-1]
    elif mutation == 'intraday':
        frame.index += pd.Timedelta(hours=1)
    elif mutation == 'timezone':
        frame.index = frame.index.tz_localize('UTC')
    elif mutation == 'negative':
        frame.iloc[-1, 0] = -5.087
    elif mutation == 'nan':
        frame.iloc[-1, 0] = float('nan')
    elif mutation == 'boolean':
        frame = frame.astype(bool)
    root, row = rrp_inputs(tmp_path, frame=frame)
    with pytest.raises(ValueError):
        rrp_select(root, row)


def test_rrp_packet_and_unchanged_validators_do_not_promote_one_fact(tmp_path):
    root, row = rrp_inputs(tmp_path)
    q = dict(schema='press.market_snapshot_qualification.v1',
             proposition_id='overnight-rrp-usage-after-month-end', observation_date='2026-11-02',
             first_party_context=[row], review_result='accepted_as_market_candidate_only',
             allow_stage=False, allow_emit=False, publication_approved=False)
    path = tmp_path / 'qualification.json'
    digest = dump(path, q)
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = plan_market_snapshot_candidate(qualification_path=path,
        qualification_sha256=digest, root=root, as_of='2026-11-03T07:30:00Z', cfg=CFG)
    slot = result['validation_context']
    assert len(slot['facts']) == 1
    # An offline source-text probe, never a generated/staged article.
    probe = {'body_html': '<p>' + slot['facts'][0]['text'] + '</p>'}
    receipts = RRP_V.check_receipts(probe, slot, CFG)
    assert receipts['ok'] is False
    assert receipts['metrics']['receipts'] == 1
    assert receipts['metrics']['minimum'] == 5
    share = RRP_V.check_our_value(probe, slot, CFG)
    assert share['metrics']['floor'] == .4
    assert share['metrics']['granularity'] == 'sentence'
    # Repetition and rounded representations are still only one receipt.
    probe['body_html'] *= 5
    assert RRP_V.check_receipts(probe, slot, CFG)['metrics']['receipts'] == 1
    assert RRP_V.check_fact_anchor({'body_html': '<p>Usage was 5.087 million dollars.</p>'}, slot, CFG)['ok'] is False
    assert all(result[key] is False for key in ('allow_stage', 'allow_emit', 'publication_approved', 'cadence_consumed'))
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
