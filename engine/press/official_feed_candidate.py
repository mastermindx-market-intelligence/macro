"""Read one reviewed OCC RSS item into the existing Press planning context.

The existing wire parser owns normalization. This adapter is offline: no feed
poll, cursor, registry mutation, writer slot, provider or publication effect.
Only the agency's complete RSS summary is evidence; it is never called a full
release. Qualification records editorial judgments, not a copyright grant.
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
_REQUIRED = {
    'kind', 'source_key', 'feed_url', 'feed_sha256', 'item_url', 'published_at',
    'event_date', 'observed_at', 'rights_basis', 'review_result',
    'reviewed_claims', 'reviewed_tickers', 'allow_stage', 'allow_emit', 'publication_approved',
}


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject a DTD after XML decoding, including UTF-16 byte streams."""

    def doctype(self, name, pubid, system):
        raise ValueError('feed evidence may not declare a DOCTYPE or entities')


def plan_official_feed_candidate(*, feed_path: Path, feed_sha256: str,
                                 qualification_path: Path, qualification_sha256: str,
                                 root: Path, as_of: str, cfg: dict | None = None) -> dict:
    """Qualify the selected feed bytes, never authorize generation or emit.

    OCC's documented feed is currently the sole supported source contract. The
    source is deliberately not installed in a live collector by this function.
    Declared XML encoding is honored before the existing wire parser consumes
    a Unicode tree; a missing publisher clock is never replaced with poll time.
    """
    from engine.press import desk_planner as P
    from lib.pages import rendered_ticker_pages

    q = json.loads(_read_bound(Path(qualification_path), qualification_sha256, 100_000))
    if not isinstance(q, dict) or set(q) not in (_REQUIRED, _REQUIRED | {'first_party_context'}):
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
    if (q['source_key'] != _OCC['key'] or q['feed_url'] != _OCC['url']
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
    if (uri.scheme != 'https' or uri.netloc not in {'www.occ.gov', 'www.occ.treas.gov'}
            or uri.query or uri.fragment
            or not re.fullmatch(r'/news-issuances/news-releases/\d{4}/nr-occ-\d{4}-\d+\.html', uri.path)):
        raise ValueError('source must be a canonical OCC release')
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
    candidates = [i for i in parse_feed(ET.tostring(tree, encoding='unicode'), _OCC)
                  if i['url'] == q['item_url']]
    if len(candidates) != 1:
        raise ValueError('wire parser did not retain one exact item')
    item = candidates[0]
    body = _strip_html(item_xml.findtext('description') or '')
    if (not body or body != item['body_snippet']
            or item_xml.find('{http://purl.org/rss/1.0/modules/content/}encoded') is not None):
        raise ValueError('complete untruncated RSS summary required')
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
                      'ref': source_ref, 'dated': event_date.isoformat(), 'source_name': _OCC['source_name']})
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
                   primary_source={'kind': 'external', 'name': _OCC['source_name'], 'url': item['url']},
                   allowed_links=P._allowed_links(cfg, links))
    return {'schema': 'press.external_candidate_plan.v1', 'operation': 'planning_only',
            'candidate_id': 'press-external-' + P.story_key(source_ref, feed_sha256, qualification_sha256),
            'source_ref': source_ref, 'feed_sha256': feed_sha256,
            'qualification_sha256': qualification_sha256, 'source_revisions': revisions,
            'event_date': event_date.isoformat(), 'published_at': published.isoformat(),
            'blocked_by_existing_coverage': source_ref in published_refs | staged_refs,
            'cadence_per_day': desk['cadence_per_day'], 'cadence_consumed': False,
            'validation_context': context, 'allow_stage': False, 'allow_emit': False, 'publication_approved': False}
