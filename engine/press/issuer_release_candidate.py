"""Opt-in, retained SEC issuer-release qualification; never a collector/selector.

Hashes bind reviewed evidence, not legal authority or economic truth. SEC hosts
issuer-authored exhibits: their figures remain third-party claims. A candidate
does not grant a writer invocation, first-party value credit, or publication.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from engine.press.external_candidate import _instant, _read_bound, _reviewed_context

_FIELDS = {
    'kind', 'source_origin', 'source_url', 'accession', 'issuer', 'title',
    'document_sha256', 'body_sha256', 'release_date', 'release_date_literal',
    'declared_available_at', 'availability_literal', 'fiscal_period_literal',
    'review_result', 'rights_basis', 'reviewed_claims', 'reviewed_tickers',
    'source_qualifiers', 'allow_stage', 'allow_emit', 'publication_approved',
}


def _bound(path, digest, limit):
    if not isinstance(path, (str, Path)):
        raise ValueError('retained evidence path must be explicit')
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('evidence must not traverse a symlink')
    try:
        return _read_bound(path, digest, limit)
    except (OSError, UnicodeError) as exc:
        raise ValueError('retained evidence is unreadable UTF-8') from exc


def normalized_issuer_body(raw_text: str) -> tuple[str, str]:
    """Exact matching representation and its digest, for qualification callers.

    This is a normalized HTML reconstruction, not original-byte provenance or
    a browser transcription. Original HTML retains its separate required hash.
    Inline tag boundaries can introduce spaces; reviewed literals must match
    THIS representation. No network or retained-file producer is invoked.
    """
    soup = BeautifulSoup(raw_text, 'html.parser')
    for node in soup.select('script,style,template,noscript'):
        node.decompose()
    body = ' '.join(soup.get_text(' ', strip=True).split())
    return body, hashlib.sha256(body.encode()).hexdigest()


def _clock(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} requires a timezone-qualified instant')
    try:
        return _instant(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{label} requires a timezone-qualified instant') from exc


# Match unsigned decimal/percent tokens and comma-grouped amounts as units.
# A comma followed by a space is ordinary punctuation, not numeric grouping.
# This is a source-boundary check, not a signed/locale/notation parser.
_NUMERIC_SOURCE_TOKEN = re.compile(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?%?|[0-9]+(?:\.[0-9]+)?%?')


def _whole_numeric_occurrence(value: str, source: str) -> bool:
    """Require one exact occurrence whose numeric tokens are complete in source.

    Search ALL occurrences: an earlier truncated match must not hide a later
    complete one. Non-numeric prose stays under the existing literal contract.
    """
    source_tokens = [(m.start(), m.end()) for m in _NUMERIC_SOURCE_TOKEN.finditer(source)]
    value_tokens = [(m.start(), m.end()) for m in _NUMERIC_SOURCE_TOKEN.finditer(value)]
    for occurrence in re.finditer(re.escape(value), source):
        start, end = occurrence.span()
        # A matched numeric literal must not stop in the middle of an
        # alphanumeric source token (e.g. $1M, $1,000USD, FY1).
        # Word-only literals retain their existing exact-substring behavior.
        if value_tokens and (
                (start and (source[start - 1].isalnum() or source[start - 1] == '_'))
                or (end < len(source) and (source[end].isalnum() or source[end] == '_'))):
            continue
        if all((start + left, start + right) in source_tokens
               for left, right in value_tokens):
            return True
    return False


def _literal(value, body, label, limit=3000):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or value not in body
            or (label in ('claim', 'source qualifier')
                and not _whole_numeric_occurrence(value, body))):
        raise ValueError(f'{label} is not a literal source span')
    return value


def plan_issuer_release_candidate(*, document_path, document_sha256,
                                  qualification_path, qualification_sha256,
                                  retrieval_path, retrieval_sha256,
                                  root, as_of, cfg=None):
    """Read original retained HTML and separately reviewed use/claim bindings.

    No URL is fetched. Declared availability is a source assertion, not an
    observed first-publication clock. No raw-body digest comes from Web extract.
    The caller pins the qualification and retrieval receipt it actually reviewed.
    """
    from engine.press import desk_planner as P
    from lib.pages import rendered_ticker_pages

    raw_text = _bound(document_path, document_sha256, 2_000_000)
    q = json.loads(_bound(qualification_path, qualification_sha256, 100_000))
    receipt = json.loads(_bound(retrieval_path, retrieval_sha256, 20_000))
    if (not isinstance(q, dict) or set(q) not in (_FIELDS, _FIELDS | {'first_party_context'})
            or q['kind'] != 'sec_issuer_release_qualification'
            or q['source_origin'] != 'issuer_authored'
            or q['review_result'] != 'accepted_as_editorial_candidate_only'
            or any(q[k] is not False for k in ('allow_stage', 'allow_emit', 'publication_approved'))):
        raise ValueError('explicit issuer-authored candidate qualification required')
    if any(not isinstance(q[k], str) or not q[k].strip() for k in (
            'source_url', 'accession', 'issuer', 'title', 'document_sha256',
            'body_sha256', 'release_date', 'release_date_literal', 'fiscal_period_literal')):
        raise ValueError('qualified source identity and dates must be nonempty strings')
    uri = urlsplit(q['source_url'])
    match = re.fullmatch(r'/Archives/edgar/data/([1-9][0-9]*)/([0-9]{18})/([A-Za-z0-9_-]+\.htm)', uri.path)
    if (uri.scheme != 'https' or uri.netloc != 'www.sec.gov' or uri.query or uri.fragment
            or not match or not re.fullmatch(r'[0-9]{10}-[0-9]{2}-[0-9]{6}', str(q['accession']))
            or q['accession'].replace('-', '') != match[2]
            or q['document_sha256'] != document_sha256):
        raise ValueError('SEC exhibit URL/accession/document identity mismatch')
    size = len(raw_text.encode('utf-8'))
    if (not isinstance(receipt, dict) or receipt.get('url') != q['source_url']
            or receipt.get('final_url') != q['source_url'] or receipt.get('status') != 200
            or receipt.get('method') != 'GET' or receipt.get('raw_sha256') != document_sha256
            or receipt.get('bytes') != size):
        raise ValueError('original-byte retrieval identity mismatch')
    rights = q['rights_basis']
    if (not isinstance(rights, dict)
            or set(rights) != {'qualification', 'scope', 'limitations', 'terms_review'}
            or rights['qualification'] != 'independent_factual_citation'
            or not isinstance(rights['scope'], str) or not rights['scope'].strip()
            or not isinstance(rights['limitations'], list) or not rights['limitations']
            or any(not isinstance(v, str) or not v.strip() for v in rights['limitations'])
            or not isinstance(rights['terms_review'], str) or not rights['terms_review'].strip()):
        raise ValueError('reviewed factual-use scope and actual restrictions required')
    body, body_sha256 = normalized_issuer_body(raw_text)
    if (not body or len(body) > 200_000 or not re.search(r'Exhibit\s+99\b', body, re.I)
            or body_sha256 != q['body_sha256']):
        raise ValueError('complete normalized Exhibit99 body identity mismatch')
    for key in ('issuer', 'title', 'release_date_literal', 'fiscal_period_literal'):
        _literal(q[key], body, key)
    now, observed = _clock(as_of, 'as_of'), _clock(receipt.get('observed_at'), 'observed_at')
    event = date.fromisoformat(q['release_date'])
    # A literal date association is checked, rather than trusting an arbitrary
    # date substring elsewhere in a long financial exhibit.
    try:
        declared_date = datetime.strptime(q['release_date_literal'], '%b. %d, %Y').date()
    except ValueError:
        try:
            declared_date = datetime.strptime(q['release_date_literal'], '%B %d, %Y').date()
        except ValueError as exc:
            raise ValueError('unsupported declared release date literal') from exc
    if event != declared_date or observed > now or observed.date() < event or event > now.date():
        raise ValueError('release and observation clocks are inconsistent')
    declared = q['declared_available_at']
    if declared is not None:
        literal = _literal(q['availability_literal'], body, 'declared availability')
        declared = _clock(declared, 'declared availability')
        # One explicit issuer-release form, not a general date parser. ET is
        # New York civil time on the declared release date (including DST),
        # not a caller-chosen offset. Unsupported forms retain a null clock.
        clock = re.fullmatch(r'beginning at (1[0-2]|[1-9]):([0-5][0-9]) ([ap])\.m\. ET today', literal)
        if clock is None:
            raise ValueError('unsupported declared availability time/timezone literal; leave clock null')
        hour = int(clock[1]) % 12 + (12 if clock[3] == 'p' else 0)
        expected = datetime.combine(event, time(hour, int(clock[2])), ZoneInfo('America/New_York'))
        # ET alone cannot disambiguate a repeated autumn time, and a spring
        # gap has no corresponding local instant. Never choose fold0 or let
        # ZoneInfo normalize a nonexistent wall clock without source evidence.
        roundtrip = expected.astimezone(timezone.utc).astimezone(expected.tzinfo)
        if (expected.utcoffset() != expected.replace(fold=1).utcoffset()
                or roundtrip.replace(tzinfo=None) != expected.replace(tzinfo=None)):
            raise ValueError('ambiguous or nonexistent declared availability; leave clock null')
        if declared != expected.astimezone(timezone.utc) or declared > observed:
            raise ValueError('declared availability clock differs from literal time/timezone')
    elif q['availability_literal'] is not None:
        raise ValueError('availability literal requires its separate declared clock')
    cfg = cfg if cfg is not None else P.load_config(root)
    desks = cfg.get('desks') if isinstance(cfg, dict) else None
    if (not isinstance(desks, dict) or not isinstance(desks.get('brief'), dict)
            or not {'window_days', 'publication', 'byline', 'min_words', 'max_words',
                    'min_anchored_receipts', 'cadence_per_day'}.issubset(desks['brief'])):
        raise ValueError('config/press.yml is missing or invalid for the Brief desk')
    desk = cfg['desks']['brief']
    if (now.date() - event).days > int(desk['window_days']):
        raise ValueError('issuer event is outside the current Brief window')
    qualifiers = q['source_qualifiers']
    if not isinstance(qualifiers, list) or not 1 <= len(qualifiers) <= 10:
        raise ValueError('reviewed material source qualifiers required')
    qualifiers = [_literal(v, body, 'source qualifier') for v in qualifiers]
    ref = f'issuer_sec:{q["accession"]}:{match[3]}'
    claims = q['reviewed_claims']
    if not isinstance(claims, list) or not 1 <= len(claims) <= 20:
        raise ValueError('bounded reviewed issuer claims required')
    facts, ids = [], set()
    for claim in claims:
        if (not isinstance(claim, dict) or set(claim) != {'id', 'literal', 'quantity_literals'}
                or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', str(claim['id'])) or claim['id'] in ids):
            raise ValueError('reviewed claim identity mismatch')
        ids.add(claim['id'])
        literal = _literal(claim['literal'], body, 'claim')
        atoms = claim['quantity_literals']
        if not isinstance(atoms, list) or len(atoms) > 20:
            raise ValueError('bounded literal quantities required')
        values = []
        for atom in atoms:
            if (not isinstance(atom, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', atom)
                    or not re.search(r'(?<![\w.])' + re.escape(atom) + r'(?![\w.])', literal)
                    or not _whole_numeric_occurrence(atom, literal)):
                raise ValueError('claim quantity is not a whole source atom')
            values.append(atom)
        facts.append({'id': claim['id'], 'text': literal, 'values': values, 'ref': ref,
                      'tier': 'third_party', 'dated': event.isoformat(), 'source_name': q['issuer'],
                      'context_relevance': 'Issuer-reported for ' + q['fiscal_period_literal']
                          + '; not independently verified. Material limitations remain separate issuer qualifier facts.'})
    # Preserve the actual literal qualifications even if a prompt trims a long
    # source document. They remain external, with no our-value/receipt credit.
    facts.extend({'id': f'issuer_qualifier_{i}', 'text': v, 'values': [], 'ref': ref,
                  'tier': 'third_party', 'dated': event.isoformat(), 'source_name': q['issuer']}
                 for i, v in enumerate(qualifiers))
    tickers = q['reviewed_tickers']
    if not isinstance(tickers, dict) or not 1 <= len(tickers) <= 10:
        raise ValueError('reviewed issuer/ticker association required')
    pages = rendered_ticker_pages(Path(root) / 'site')
    links = []
    for ticker, literal in tickers.items():
        if (not isinstance(ticker, str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', ticker) or ticker not in pages
                or not isinstance(literal, str) or q['issuer'] not in literal
                or not re.search(r'(?<![A-Z0-9])' + re.escape(ticker) + r'(?![A-Z0-9])', literal)):
            raise ValueError('reviewed issuer association or canonical dossier missing')
        _literal(literal, body, 'issuer/ticker association')
        links.append(f'https://www.mastermind-x.com/stocks/{ticker}.html')
    revisions = {ref: 'sha256:' + document_sha256,
                 ref + ':retrieval': 'sha256:' + retrieval_sha256}
    if 'first_party_context' in q:
        contextual, bindings = _reviewed_context(q['first_party_context'], root=Path(root),
                                               as_of=now.date(), window_days=int(desk['window_days']))
        facts.extend(contextual)
        revisions.update(bindings)
    pub, _ = P.published_refs(root, cfg)
    staged, _ = P.staged_refs(root, cfg)
    context = {'desk': 'brief', 'publication': desk['publication'], 'byline': desk['byline'],
               'as_of': now.date().isoformat(), 'min_words': desk['min_words'], 'max_words': desk['max_words'],
               'min_anchored_receipts': desk['min_anchored_receipts'], 'facts': facts,
               'raw_documents': [{'ref': ref, 'text': body}],
               'primary_source': {'kind': 'external', 'name': q['issuer'], 'url': q['source_url'], 'ref': ref},
               'allowed_links': P._allowed_links(cfg, links)}
    return {'schema': 'press.external_candidate_plan.v1', 'operation': 'planning_only',
            'candidate_id': 'press-external-' + P.story_key(ref, document_sha256, qualification_sha256),
            'source_ref': ref, 'source_url': q['source_url'], 'document_sha256': document_sha256,
            'body_sha256': body_sha256,
            'qualification_sha256': qualification_sha256, 'retrieval_sha256': retrieval_sha256,
            'source_clocks': {'event_date': event.isoformat(),
                              'declared_available_at': declared.isoformat() if declared else None,
                              'observed_at': observed.isoformat(), 'as_of': now.isoformat()},
            'source_origin': 'issuer_authored', 'rights_basis': rights, 'source_revisions': revisions,
            'blocked_by_existing_coverage': ref in pub | staged,
            'cadence_per_day': desk['cadence_per_day'], 'cadence_consumed': False,
            'validation_context': context, 'allow_stage': False, 'allow_emit': False,
            'publication_approved': False}
