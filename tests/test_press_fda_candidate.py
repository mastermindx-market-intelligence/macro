"""The FDA source seam stays an offline third-party candidate, never admission."""
import hashlib
import json
from html import escape

import pytest

from engine.press.official_feed_candidate import plan_official_feed_candidate
from tests import press_fixtures as F

RAW = 'http://www.fda.gov/drugs/resources-information-approved-drugs/example-approval'
CANONICAL = RAW.replace('http:', 'https:', 1)
POLICY = 'https://www.fda.gov/about-fda/about-website/website-policies'
FEED = 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml'
SUMMARY = 'On October 14, 2026, FDA announced an expanded indication for ExampleBio.'
QUALIFIER = 'The 77 patients belonged to the earlier cohort, not a new trial.'
POLICY_TEXT = ('Unless otherwise noted, the contents of the FDA website (www.fda.gov) — '
               'both text and graphics — are not copyrighted. '
               'They are in the public domain and may be republished, reprinted and otherwise '
               'used freely by anyone without the need to obtain permission from FDA. '
               'The copied item lists the date that the material was copied and '
               'provides a link back to its source.')


def put(path, value):
    path.write_text(value)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def args(tmp_path):
    root = F.fixture_root(tmp_path / 'root')
    (root / 'site/stocks').mkdir(parents=True, exist_ok=True)
    (root / 'site/stocks/EXB.html').write_text('ExampleBio fixture dossier')
    feed, release, policy, qualification = [tmp_path / name for name in
                                          ('feed.xml', 'release.html', 'policy.html', 'q.json')]
    digest = put(feed, '<rss><channel><item><title>Example approval</title>'
                 f'<link>{RAW}</link><guid>stable-example-approval</guid>'
                 '<pubDate>Wed, 14 Oct 2026 11:15:50 EDT</pubDate>'
                 f'<description>{escape(SUMMARY)}</description></item></channel></rss>')
    release_hash = put(release, f'<link rel="canonical" href="{CANONICAL}">'
                       '<meta property="article:published_time" content="Wed, 10/14/2026 - 11:15">'
                       f'<article><div class="col-md-8"><p>{SUMMARY}</p><p>{QUALIFIER}</p></div></article>')
    policy_hash = put(policy, f'<link rel="canonical" href="{POLICY}">'
                     f'<article><div class="col-md-8"><p>{POLICY_TEXT}</p></div></article>')
    q = {'kind': 'official_feed_editorial_qualification', 'source_key': 'fda_drugs',
         'feed_url': FEED, 'feed_sha256': digest, 'item_url': RAW,
         'published_at': '2026-10-14T15:15:50+00:00', 'event_date': '2026-10-14',
         'observed_at': '2026-10-15T18:13:00+00:00',
         'rights_basis': {'qualification': 'government_authored_factual_reporting',
                          'scope': 'FDA-authored factual announcement only; no third-party labeling.',
                          'policy_url': POLICY},
         'review_result': 'accepted_as_editorial_candidate_only',
         'reviewed_claims': [{'literal': QUALIFIER, 'quantity_literal': '77'}],
         'reviewed_tickers': {'EXB': 'ExampleBio'}, 'source_qualifiers': [QUALIFIER],
         'release_sha256': release_hash, 'policy_sha256': policy_hash,
         'allow_stage': False, 'allow_emit': False, 'publication_approved': False}
    return dict(feed_path=feed, feed_sha256=digest, qualification_path=qualification,
                qualification_sha256=put(qualification, json.dumps(q)), root=root,
                as_of='2026-10-15T18:15:00+00:00', release_path=release, policy_path=policy)


def test_fda_candidate_preserves_raw_identity_and_full_clinical_scope(args):
    before = {p: p.read_bytes() for p in args['root'].parent.rglob('*') if p.is_file()}
    result = plan_official_feed_candidate(**args)
    context = result['validation_context']
    assert result['source_ref'] == 'official_feed:' + hashlib.sha1(
        b'fda_drugs|stable-example-approval').hexdigest()
    assert result['allow_stage'] is result['allow_emit'] is result['publication_approved'] is False
    assert result['operation'] == 'planning_only' and result['cadence_consumed'] is False
    assert context['primary_source']['url'] == CANONICAL
    assert context['allowed_links'] == ['https://www.mastermind-x.com/stocks/EXB.html']
    assert context['min_anchored_receipts'] == 5
    assert all(f['tier'] == 'third_party' for f in context['facts'])
    assert context['facts'][-1]['text'] == QUALIFIER and context['facts'][-1]['values'] == []
    assert QUALIFIER in context['raw_documents'][0]['text']
    assert len(result['source_revisions']) == 3
    assert before == {p: p.read_bytes() for p in args['root'].parent.rglob('*') if p.is_file()}


def test_fda_item_without_guid_keeps_the_original_http_url_identity(args):
    q = json.loads(args['qualification_path'].read_text())
    args['feed_sha256'] = put(args['feed_path'], args['feed_path'].read_text().replace(
        '<guid>stable-example-approval</guid>', ''))
    q['feed_sha256'] = args['feed_sha256']
    args['qualification_sha256'] = put(args['qualification_path'], json.dumps(q))
    result = plan_official_feed_candidate(**args)
    assert result['source_ref'] == 'official_feed:' + hashlib.sha1(
        ('fda_drugs|' + RAW).encode()).hexdigest()
    assert result['validation_context']['primary_source']['url'] == CANONICAL


@pytest.mark.parametrize('field', ['release_path', 'policy_path'])
def test_fda_candidate_needs_each_original_document(args, field):
    args[field] = None
    with pytest.raises(ValueError):
        plan_official_feed_candidate(**args)


@pytest.mark.parametrize('patch', [
    {'allow_stage': True}, {'publication_approved': True},
    {'source_key': 'fda_anything'}, {'source_qualifiers': []},
    {'reviewed_tickers': {'EXB': 'Unrelated issuer'}},
])
def test_fda_candidate_cannot_self_admit_or_invent_association(args, patch):
    q = json.loads(args['qualification_path'].read_text())
    q.update(patch)
    args['qualification_sha256'] = put(args['qualification_path'], json.dumps(q))
    with pytest.raises(ValueError):
        plan_official_feed_candidate(**args)


@pytest.mark.parametrize('release_ending, accepted', [
    ('non-muscle invasive bladder cancer (NMIBC).', True),
    ('non-muscle invasive bladder cancer (UNAPPROVED).', False),
    ('a different disease (DD).', False),
])
def test_rss_can_omit_expanded_initialism_but_not_change_indication(args, release_ending, accepted):
    # The actual retained FDA release includes "(NMIBC)" after its expansion;
    # the complete RSS summary omits only that redundant initialism.
    prefix = 'On October 14, 2026, FDA announced an expanded indication for ExampleBio in '
    summary = prefix + 'non-muscle invasive bladder cancer.'
    q = json.loads(args['qualification_path'].read_text())
    args['feed_sha256'] = put(args['feed_path'], args['feed_path'].read_text().replace(
        escape(SUMMARY), escape(summary)))
    q['feed_sha256'] = args['feed_sha256']
    q['release_sha256'] = put(args['release_path'], args['release_path'].read_text().replace(
        SUMMARY, prefix + release_ending))
    args['qualification_sha256'] = put(args['qualification_path'], json.dumps(q))
    if accepted:
        body = plan_official_feed_candidate(**args)['validation_context']['raw_documents'][0]['text']
        assert release_ending in body and QUALIFIER in body
    else:
        with pytest.raises(ValueError):
            plan_official_feed_candidate(**args)
