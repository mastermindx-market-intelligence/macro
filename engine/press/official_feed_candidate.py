"""Read one reviewed OCC or DOJ RSS item into the existing Press context.

The existing wire parser owns normalization. This adapter is offline: no feed
poll, cursor, registry mutation, writer slot, provider or publication effect.
OCC uses its complete RSS summary. DOJ additionally requires the hash-bound
full release and reuse policy, retaining legal qualifiers beyond the summary.
Qualification records editorial judgments, not a copyright grant.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from engine.marketing.breaking_feed import parse_feed, _strip_html
from engine.press.external_candidate import _instant, _read_bound, _reviewed_context, _value

_OCC = {
    'key': 'occ_news', 'kind': 'rss',
    'url': 'https://www.occ.treas.gov/rss/occ_news.xml',
    'source_name': 'Office of the Comptroller of the Currency', 'tier': 'official',
}
_DOJ = {
    'key': 'doj_news', 'kind': 'rss',
    'url': 'https://www.justice.gov/news/rss?m=1',
    'source_name': 'U.S. Department of Justice', 'tier': 'official',
}
_DOJ_POLICY = 'https://www.justice.gov/legalpolicies'
_DOJ_FIELDS = {'release_sha256', 'policy_sha256', 'source_qualifiers'}
_FDA = {
    'key': 'fda_drugs', 'kind': 'rss',
    'url': 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml',
    'source_name': 'U.S. Food and Drug Administration', 'tier': 'official',
}
_FDA_FIELDS = {'release_sha256', 'policy_sha256', 'source_qualifiers'}
_REQUIRED = {
    'kind', 'source_key', 'feed_url', 'feed_sha256', 'item_url', 'published_at',
    'event_date', 'observed_at', 'rights_basis', 'review_result',
    'reviewed_claims', 'reviewed_tickers', 'allow_stage', 'allow_emit', 'publication_approved',
}


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject a DTD after XML decoding, including UTF-16 byte streams."""

    def doctype(self, name, pubid, system):
        raise ValueError('feed evidence may not declare a DOCTYPE or entities')


def _doj_release(q: dict, summary: str, published, release_path: Path | None,
                 policy_path: Path | None) -> str:
    """Read exact retained agency documents; no fetching or permission effect."""
    from bs4 import BeautifulSoup

    if release_path is None or policy_path is None:
        raise ValueError('DOJ requires retained full release and policy')
    if q['rights_basis'].get('policy_url') != _DOJ_POLICY:
        raise ValueError('DOJ policy identity mismatch')
    release = BeautifulSoup(_read_bound(Path(release_path), q['release_sha256'], 1_000_000), 'html.parser')
    policy = BeautifulSoup(_read_bound(Path(policy_path), q['policy_sha256'], 1_000_000), 'html.parser')
    for doc, expected in ((release, q['item_url']), (policy, _DOJ_POLICY)):
        canonical = doc.select('link[rel="canonical"]')
        if len(canonical) != 1 or canonical[0].get('href') != expected:
            raise ValueError('DOJ document canonical identity mismatch')
        for element in doc.select('script, style, template, noscript'):
            element.decompose()
    bodies = release.select('.node-body .field_body')
    clocks = release.select('.node-date time[datetime]')
    policy_bodies = policy.select('.field_body')
    if len(bodies) != 1 or len(clocks) != 1 or len(policy_bodies) != 1:
        raise ValueError('DOJ document body or clock is ambiguous')
    if _instant(clocks[0]['datetime']) != published:
        raise ValueError('DOJ release and feed publisher clocks differ')
    body = ' '.join(bodies[0].get_text().split())
    policy_text = ' '.join(policy_bodies[0].get_text(' ', strip=True).split())
    if (not body or len(body) > 20_000 or summary not in body
            or 'information on Department of Justice websites is in the public domain' not in policy_text
            or 'permission to copy these materials must be obtained from the original source' not in policy_text):
        raise ValueError('DOJ release summary or policy scope is not corroborated')
    qualifiers = q['source_qualifiers']
    if (not isinstance(qualifiers, list) or not 1 <= len(qualifiers) <= 10
            or any(not isinstance(s, str) or not s.strip() or len(s) > 1000
                   or s not in body for s in qualifiers)):
        raise ValueError('DOJ requires literal source qualifiers')
    # The RSS headline can sound adjudicated. Carry the release's express
    # limitation into the fact list, even if a writer truncates raw documents.
    if ('no determination of liability' in body
            and not any('allegations only' in s and 'no determination of liability' in s
                        for s in qualifiers)):
        raise ValueError('DOJ allegation-only disposition must remain explicit')
    return body


def plan_official_feed_candidate(*, feed_path: Path, feed_sha256: str,
                                 qualification_path: Path, qualification_sha256: str,
                                 root: Path, as_of: str, cfg: dict | None = None,
                                 release_path: Path | None = None,
                                 policy_path: Path | None = None) -> dict:
    """Qualify the selected feed bytes, never authorize generation or emit.

    Only the explicit OCC, DOJ and FDA feed contracts are supported. No source
    is installed in a live collector by this function. DOJ and FDA need the original
    release and policy as well as the RSS item; feed text alone cannot qualify it.
    Declared XML encoding is honored before the existing wire parser consumes
    a Unicode tree; a missing publisher clock is never replaced with poll time.
    """
    from engine.press import desk_planner as P
    from lib.pages import rendered_ticker_pages

    q = json.loads(_read_bound(Path(qualification_path), qualification_sha256, 100_000))
    if not isinstance(q, dict):
        raise ValueError('explicit official feed qualification required')
    source = {'occ_news': _OCC, 'doj_news': _DOJ, 'fda_drugs': _FDA}.get(q.get('source_key'))
    required = _REQUIRED | (_DOJ_FIELDS if source is _DOJ else _FDA_FIELDS if source is _FDA else set())
    if source is None or set(q) not in (required, required | {'first_party_context'}):
        raise ValueError('explicit official feed qualification required')
    for key in ('source_key', 'feed_url', 'feed_sha256', 'item_url', 'published_at', 'event_date', 'observed_at'):
        if not isinstance(q[key], str) or not q[key].strip():
            raise ValueError('qualified source identity and clocks must be nonempty strings')
    rights = q['rights_basis']
    if (q['kind'] != 'official_feed_editorial_qualification'
            or q['review_result'] != 'accepted_as_editorial_candidate_only'
            or not isinstance(rights, dict)
            or rights.get('qualification') != 'government_authored_factual_reporting'
            or not isinstance(rights.get('scope'), str) or not rights['scope'].strip()
            or any(q[key] is not False for key in ('allow_stage', 'allow_emit', 'publication_approved'))):
        raise ValueError('source-specific candidate qualification required')
    if (q['feed_url'] != source['url']
            or q['feed_sha256'] != feed_sha256):
        raise ValueError('official source feed identity mismatch')
    feed_path = Path(feed_path)
    if (not re.fullmatch(r'[0-9a-f]{64}', str(feed_sha256)) or feed_path.is_symlink()
            or not feed_path.is_file() or feed_path.stat().st_size > 1_000_000):
        raise ValueError('feed evidence must be a bounded regular file with SHA256')
    raw = feed_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != feed_sha256:
        raise ValueError('feed evidence hash mismatch')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('feed evidence may not declare entities')
    try:
        tree = ET.fromstring(raw, parser=ET.XMLParser(target=_NoDoctypeTreeBuilder()))
    except (ET.ParseError, LookupError, ValueError) as exc:
        raise ValueError('feed XML is malformed') from exc
    entries = tree.findall('./channel/item')
    selected = [i for i in entries if (i.findtext('link') or '').strip() == q['item_url']]
    if len(selected) != 1:
        raise ValueError('one exact source item required')
    item_xml = selected[0]
    try:
        clock = parsedate_to_datetime(item_xml.findtext('pubDate') or '')
        if clock.tzinfo is None:
            raise ValueError('missing timezone')
        published = clock.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError('publisher clock must be explicit and timezone-qualified') from exc
    if _instant(q['published_at']) != published:
        raise ValueError('qualified publisher clock differs')
    uri = urlsplit(q['item_url'])
    hosts = {'www.justice.gov'} if source is _DOJ else {'www.occ.gov', 'www.occ.treas.gov'}
    route = (r'/opa/pr/[a-z0-9]+(?:-[a-z0-9]+)*' if source is _DOJ else
             r'/news-issuances/news-releases/\d{4}/nr-occ-\d{4}-\d+\.html')
    if source is not _FDA and (uri.scheme != 'https' or uri.netloc not in hosts
            or uri.query or uri.fragment
            or not re.fullmatch(route, uri.path)):
        raise ValueError('source must be a canonical supported agency release')
    now, observed = _instant(as_of), _instant(q['observed_at'])
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(q['event_date'])):
            raise ValueError('not a calendar date')
        event_date = date.fromisoformat(q['event_date'])
    except (TypeError, ValueError) as exc:
        raise ValueError('reviewed event date required') from exc
    cfg = cfg if cfg is not None else P.load_config(root)
    desk = cfg['desks']['brief']
    window = int(desk['window_days'])
    if (not event_date <= published.date() <= observed.date() <= now.date()
            or not published <= observed <= now or not 0 <= (now.date() - event_date).days <= window):
        raise ValueError('source event or observation is outside the current Brief window')
    candidates = [i for i in parse_feed(ET.tostring(tree, encoding='unicode'), source)
                  if i['url'] == q['item_url']]
    if len(candidates) != 1:
        raise ValueError('wire parser did not retain one exact item')
    item = candidates[0]
    body = _strip_html(item_xml.findtext('description') or '')
    if (not body or body != item['body_snippet']
            or item_xml.find('{http://purl.org/rss/1.0/modules/content/}encoded') is not None):
        raise ValueError('complete untruncated RSS summary required')
    if source is _DOJ:
        body = _doj_release(q, body, published, release_path, policy_path)
    if source is _FDA:
        from engine.press.fda_document import read_fda_drug_release

        if release_path is None or policy_path is None:
            raise ValueError('FDA requires retained full release and policy')
        body = read_fda_drug_release(q, body, clock, release_path, policy_path)
    claims, tickers = q['reviewed_claims'], q['reviewed_tickers']
    if not isinstance(claims, list) or not 1 <= len(claims) <= 20:
        raise ValueError('bounded reviewed source claims required')
    source_ref = 'official_feed:' + item['id']
    facts = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'literal', 'quantity_literal'}:
            raise ValueError('reviewed source claim fields mismatch')
        literal, atom = claim['literal'], claim['quantity_literal']
        if (not isinstance(literal, str) or not literal.strip() or literal not in body
                or not isinstance(atom, str) or not atom
                or not re.search(r'(?<![\w.$])' + re.escape(atom) + r'(?![\w.])', literal)):
            raise ValueError('reviewed claim or quantity is not in source evidence')
        facts.append({'text': literal, 'values': [str(_value(atom))], 'tier': 'third_party',
                      'ref': source_ref, 'dated': event_date.isoformat(), 'source_name': source['source_name']})
    if source in (_DOJ, _FDA):
        facts.extend({'text': s, 'values': [], 'tier': 'third_party', 'ref': source_ref,
                      'dated': event_date.isoformat(), 'source_name': source['source_name']}
                     for s in q['source_qualifiers'])
    available = rendered_ticker_pages(Path(root) / 'site')
    if not isinstance(tickers, dict) or not 1 <= len(tickers) <= 10:
        raise ValueError('reviewed issuer association required')
    links = []
    for ticker, name in tickers.items():
        if (not isinstance(ticker, str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', ticker)
                or not isinstance(name, str) or not name.strip() or name not in body or ticker not in available):
            raise ValueError('reviewed ticker needs source association and existing dossier')
        links.append(f'https://www.mastermind-x.com/stocks/{ticker}.html')
    revisions = {source_ref: 'sha256:' + feed_sha256}
    if source in (_DOJ, _FDA):
        revisions[source_ref + ':release'] = 'sha256:' + q['release_sha256']
        revisions[source_ref + ':policy'] = 'sha256:' + q['policy_sha256']
    if 'first_party_context' in q:
        context, context_revisions = _reviewed_context(q['first_party_context'], root=Path(root),
                                                      as_of=now.date(), window_days=window)
        facts.extend(context)
        revisions.update(context_revisions)
    published_refs, _ = P.published_refs(root, cfg)
    staged_refs, _ = P.staged_refs(root, cfg)
    context = {key: desk[key] for key in ('publication', 'byline', 'min_words', 'max_words', 'min_anchored_receipts')}
    context.update(desk='brief', as_of=now.date().isoformat(), facts=facts,
                   raw_documents=[{'ref': source_ref, 'text': body}],
                   primary_source={'kind': 'external', 'name': source['source_name'],
                                   'url': ('https://' + uri.netloc + uri.path)
                                   if source is _FDA else item['url']},
                   allowed_links=P._allowed_links(cfg, links))
    return {'schema': 'press.external_candidate_plan.v1', 'operation': 'planning_only',
            'candidate_id': 'press-external-' + P.story_key(source_ref, feed_sha256, qualification_sha256),
            'source_ref': source_ref, 'feed_sha256': feed_sha256,
            'qualification_sha256': qualification_sha256, 'source_revisions': revisions,
            'event_date': event_date.isoformat(), 'published_at': published.isoformat(),
            'blocked_by_existing_coverage': source_ref in published_refs | staged_refs,
            'cadence_per_day': desk['cadence_per_day'], 'cadence_consumed': False,
            'validation_context': context, 'allow_stage': False, 'allow_emit': False, 'publication_approved': False}
