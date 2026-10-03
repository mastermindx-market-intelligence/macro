"""Receipt-qualified extensions for the EXISTING ChinaMacroAdapter.

This module has no scheduler, credentials, retry loop, store writes or renderer.
The existing adapter supplies HTTP; its existing runner remains the only writer.
One failed release cannot bless a value or destroy independent legacy sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Callable
from urllib import robotparser
from urllib.parse import unquote, urlparse, urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd

from collectors import china_economy_release_parser as parsers
from engine.china_economy import month_index, month_end, number, timestamp
from engine.china_economy_store import binding, frames_from_receipt, value_receipt_digest

log = logging.getLogger(__name__)
VERSION = 'china-economy-acquisition.v1.2'
MAX_BYTES = 4_000_000
ROBOTS_MAX_BYTES = 512_000
USER_AGENT = 'Mozilla/5.0 (compatible; MastermindEconomicData/1.0)'
TZ = ZoneInfo('Asia/Shanghai')
# Exact source families, not an arbitrary URL fetch API.
FAMILIES = {
    'industry': ('www.stats.gov.cn', '规模以上工业增加值', 'industrial_sa'),
    'retail': ('www.stats.gov.cn', '社会消费品零售总额', 'retail_sa'),
    'investment': ('www.stats.gov.cn', '固定资产投资', 'investment_sa'),
    'pmi': ('www.stats.gov.cn', '采购经理指数', None),
    'profits': ('www.stats.gov.cn', '工业企业利润', None),
    'fiscal': ('gks.mof.gov.cn', '财政收支情况', None),
    'safe': ('www.safe.gov.cn', '银行结售汇', None),
    'power': ('www.nea.gov.cn', '全社会用电量', None),
}
PATHS = {
    'www.stats.gov.cn': ('/sj/', '/xxgk/', '/zwfwck/sjfb/'),
    'gks.mof.gov.cn': ('/tongjishuju/',),
    'm.mof.gov.cn': ('/czsj/',),
    'www.safe.gov.cn': ('/safe/',),
    'www.nea.gov.cn': ('/',),
}
# These three NBS series explicitly publish revised seasonally adjusted history
# inside each new monthly release. A later official release URL is therefore a
# new vintage of the SAME statistical series, not an unrelated source. Keep this
# allowlist narrow: ordinary YoY/YTD/survey values may not use it.
NBS_SA_REVISION_FAMILIES = {
    'industrial_sa': 'industry',
    'retail_sa': 'retail',
    'investment_sa': 'investment',
}


def _nbs_sa_revision_lineage(meta: dict, old_url: str, new_url: str) -> bool:
    family = NBS_SA_REVISION_FAMILIES.get(meta.get('id'))
    if not family or not isinstance(old_url, str) or not isinstance(new_url, str):
        return False
    try:
        checked_url(old_url, family)
        checked_url(new_url, family)
    except ValueError:
        return False
    return (urlparse(old_url).hostname == 'www.stats.gov.cn'
            and urlparse(new_url).hostname == 'www.stats.gov.cn')


def checked_url(url: str, family: str) -> str:
    if family not in FAMILIES:
        raise ValueError('unsupported_release_family')
    p = urlparse(url)
    hosts = {FAMILIES[family][0]} | ({'m.mof.gov.cn'} if family == 'fiscal' else set())
    decoded = unquote(p.path)
    if (p.scheme != 'https' or p.hostname not in hosts or p.username or p.password
            or p.port not in (None, 443) or p.query or p.fragment
            or '\\' in decoded or any(x in {'.', '..'} for x in decoded.split('/'))
            or not any(decoded.startswith(prefix) for prefix in PATHS.get(p.hostname, ()))):
        raise ValueError('unapproved_source_url')
    return url


def check_robots(url: str, http_get: Callable, cache: dict | None = None) -> dict:
    """Enforce one publisher robots policy per host, then check this exact path.

    A missing robots file (404/410) contains no explicit disallow and is admitted.
    Redirected, denied, malformed, or transport-ambiguous robots responses fail
    the source family closed. Only status/hash metadata is retained; never body text.
    """
    host = urlparse(url).hostname
    if not host:
        raise ValueError('robots_host_missing')
    cache = cache if cache is not None else {}
    if host not in cache:
        robots_url = f'https://{host}/robots.txt'
        try:
            response = http_get(
                robots_url, timeout=10, retries=1, allow_redirects=False,
                headers={'User-Agent': USER_AGENT, 'Accept': 'text/plain,*/*;q=0.1'},
            )
            if getattr(response, 'url', robots_url) != robots_url:
                raise ValueError('robots_unexpected_response_url')
            status = int(response.status_code)
            body = bytes(response.content or b'')
            base = {
                'url': robots_url,
                'http_status': status,
                'response_sha256': hashlib.sha256(body).hexdigest(),
                'response_bytes': len(body),
            }
            if status in {404, 410}:
                cache[host] = {
                    'receipt': {**base, 'policy': 'not_published'},
                    'parser': None,
                }
            elif status == 200:
                ctype = str(response.headers.get('Content-Type', '')).lower()
                if not body or len(body) > ROBOTS_MAX_BYTES:
                    raise ValueError('robots_invalid_body')
                if 'text/html' in ctype:
                    raise ValueError('robots_invalid_content_type')
                parser = robotparser.RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(body.decode('utf-8-sig', errors='replace').splitlines())
                cache[host] = {
                    'receipt': {**base, 'policy': 'published'},
                    'parser': parser,
                }
            else:
                raise ValueError(f'robots_http_status_{status}')
        except Exception as exc:
            # Adapter.http_get raises HTTPError on 404/410 before returning the
            # response. Preserve the same "robots not published" semantics as a
            # non-raising HTTP client, but only when the exception carries the
            # exact same-origin robots response.
            failed = getattr(exc, 'response', None)
            failed_status = getattr(failed, 'status_code', None)
            failed_url = getattr(failed, 'url', None) if failed is not None else None
            if failed is not None and failed_status in {404, 410} and failed_url == robots_url:
                body = bytes(getattr(failed, 'content', b'') or b'')
                cache[host] = {
                    'receipt': {
                        'url': robots_url,
                        'http_status': int(failed_status),
                        'response_sha256': hashlib.sha256(body).hexdigest(),
                        'response_bytes': len(body),
                        'policy': 'not_published',
                    },
                    'parser': None,
                }
            else:
                reason = str(exc)[:100] if isinstance(exc, ValueError) else 'robots_acquisition_failed'
                cache[host] = {'error': reason}
    state = cache[host]
    if state.get('error'):
        raise ValueError(state['error'])
    parser = state.get('parser')
    if parser is not None and not parser.can_fetch(USER_AGENT, url):
        raise ValueError('robots_disallowed')
    return {**state['receipt'], 'checked_path': urlparse(url).path, 'allowed': True}


def _visible_text(soup) -> str:
    # Prevent script/JSON schema dates from impersonating article publication.
    copy = BeautifulSoup(str(soup), 'html.parser')
    for e in copy(['script', 'style', 'noscript']):
        e.decompose()
    return copy.get_text(' ', strip=True)


def _date(value: str) -> tuple[datetime, str]:
    value = re.sub(r'\s+', ' ', value).strip()
    m = re.fullmatch(r'(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?', value)
    if not m:
        raise ValueError('invalid_publication_date')
    y, mo, d = map(int, m.group(1, 2, 3))
    if m[4] is None:
        return datetime(y, mo, d, 23, 59, 59, tzinfo=TZ), 'day_conservative_end'
    return datetime(y, mo, d, int(m[4]), int(m[5]), int(m[6] or 0), tzinfo=TZ), ('second' if m[6] else 'minute')


def article_identity(html: str, family: str, expected_period: str) -> dict:
    """Verify family, reference month and publication from the same document."""
    month_index(expected_period)
    soup = BeautifulSoup(html, 'html.parser')
    titles = [x.get('content', '').strip() for x in soup.select('meta[name]')
              if x.get('name', '').lower() == 'articletitle' and x.get('content')]
    if len(set(titles)) > 1:
        raise ValueError('conflicting_article_titles')
    title = titles[0] if titles else (soup.title.get_text(' ', strip=True) if soup.title else '')
    if FAMILIES[family][1] not in title:
        raise ValueError('wrong_release_family')
    y, m = map(int, expected_period.split('-'))
    pattern = rf'{y}年(?:1[—–－-])?{m}月(?:份)?'
    if not re.search(pattern, re.sub(r'\s+', '', title)):
        # NEA headlines omit the year. Require the year-month IN the article too.
        text = re.sub(r'\s+', '', _visible_text(soup))
        if family != 'power' or not re.search(rf'(?<!\d){m}月份', title) or not re.search(rf'{y}年{m}月[,，]', text):
            raise ValueError('wrong_reference_period')
    dates = [x.get('content', '').strip() for x in soup.select('meta[name]')
             if x.get('name', '').lower() in {'pubdate', 'publishdate'} and x.get('content')]
    if not dates:
        # NBS's mobile release uses this publisher-defined visible timestamp.
        elements = soup.select('.xilan_titf') if family == 'profits' else []
        if family == 'fiscal':
            elements = soup.select('.pubtime, .time, .times, .article-time')
        for element in elements:
            match = re.search(r'发布时间[：:]\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)', _visible_text(element))
            if match:
                dates.append(match[1])
        if family == 'fiscal' and not dates:
            # Explicit publisher footer, never URL date or arbitrary first date.
            matches = re.findall(r'发布日期[：:]\s*(20\d{2}年\d{1,2}月\d{1,2}日)', _visible_text(soup))
            dates.extend(matches)
    if not dates:
        raise ValueError('publication_evidence_missing')
    parsed = [_date(x) for x in dates]
    if len({x[0].date() for x in parsed}) != 1:
        raise ValueError('conflicting_publication_dates')
    precise = [x for x in parsed if x[1] != 'day_conservative_end']
    if len({x[0] for x in precise}) > 1:
        raise ValueError('conflicting_publication_times')
    published, precision = precise[0] if precise else parsed[0]
    if published.date() < month_end(expected_period):
        raise ValueError('release_precedes_reference_end')
    return {'title': title, 'published_at': published.isoformat(), 'publication_precision': precision,
            'reference_period': expected_period, 'family': family}


def parse_acquisition(family: str, url: str, body: bytes, observed_at: str, expected_period: str,
                      catalog: dict, *, status: int = 200, content_type: str = 'text/html') -> tuple[dict, dict, list]:
    checked_url(url, family)
    if status != 200:
        raise ValueError(f'http_status_{status}')
    if 'text/html' not in content_type.lower() or not body or len(body) > MAX_BYTES:
        raise ValueError('invalid_source_body')
    html = body.decode('utf-8-sig', errors='strict')
    identity = article_identity(html, family, expected_period)
    observed = timestamp(observed_at)
    if timestamp(identity['published_at']) > observed:
        raise ValueError('publication_after_acquisition')
    seasonal = FAMILIES[family][2]
    if seasonal:
        points = parsers.parse_sa_html(html, seasonal, expected_period)
    elif family == 'pmi':
        points = parsers.parse_pmi_html(html, expected_period)
    else:
        # The existing paragraph parsers need the title/reference plus body text.
        text = identity['title'] + ' ' + _visible_text(parsers.publisher_article_root(html))
        function = {'fiscal': parsers.parse_mof_text, 'safe': parsers.parse_safe_text,
                    'profits': parsers.parse_corporate_text, 'power': parsers.parse_nea_text}[family]
        points = function(text, expected_period)
    supplemental = None
    if family in {'industry', 'retail', 'investment', 'pmi'}:
        try:
            details, supplemental = parsers.parse_activity_detail(html, family, expected_period)
            points = points + details
        except ValueError as exc:
            # Detail admission cannot erase a valid seasonal/survey history.
            supplemental = {'scope': 'same_release_current_period_only', 'status': 'withheld',
                            'admitted_metrics': [], 'null_reasons': {'_detail': str(exc)},
                            'history_inferred': False}
    if not points:
        raise ValueError('empty_release')
    receipt = {**identity, 'url': url, 'observed_at': observed.isoformat(),
               'response_sha256': hashlib.sha256(body).hexdigest(), 'http_status': status,
               'content_type': content_type, 'response_bytes': len(body), 'parser_version': VERSION,
               'response_hash_basis': 'exact_http_response_bytes', 'original_vintage': False}
    if supplemental is not None:
        receipt['supplemental_evidence'] = supplemental
    frames = frames_from_receipt(points, receipt, catalog)
    if any(not k.startswith('china_macro/') for k in frames):
        raise ValueError('wrong_collector_group')
    return frames, receipt, points


@dataclass
class CollectionBatch:
    frames: dict = field(default_factory=dict)
    receipts: dict = field(default_factory=dict)
    failures: dict = field(default_factory=dict)
    pending: dict = field(default_factory=dict)
    conflicts: list = field(default_factory=list)
    requested: int = 0

    @property
    def status(self):
        return 'blocked' if self.failures or self.conflicts else 'ok'


def _merge_disjoint(left, right):
    """Source families may share dates/tables but may not fight over one cell."""
    result = {k: v.copy() for k, v in left.items()}
    for key, frame in right.items():
        if key not in result:
            result[key] = frame.copy(); continue
        overlap = set(result[key].columns) & set(frame.columns)
        if overlap and len(result[key].index.intersection(frame.index)):
            raise ValueError('two_release_families_claim_same_cells')
        result[key] = frame.combine_first(result[key])
    return result


def collect_releases(targets: dict, expected_period: str | None, http_get: Callable, catalog: dict,
                     clock: Callable = lambda: datetime.now(timezone.utc),
                     robots_cache: dict | None = None) -> CollectionBatch:
    """One bounded acquisition per configured family; retry owner is Adapter.

    Backward-compatible string targets use expected_period. Planned targets
    carry their own exact url + period so different source families may advance
    on different publication clocks in the same run.
    """
    if expected_period is not None:
        month_index(expected_period)
    if not isinstance(targets, dict) or len(targets) > len(FAMILIES):
        raise ValueError('invalid_release_target_set')
    batch = CollectionBatch(requested=len(targets)); unavailable_hosts = set()
    robots_cache = robots_cache if robots_cache is not None else {}
    for family, target in targets.items():
        url = target
        period = expected_period
        try:
            if isinstance(target, dict):
                if set(target) != {'url', 'period'}:
                    raise ValueError('invalid_planned_release_target')
                url = target['url']; period = target['period']
                month_index(period)
            elif period is None:
                raise ValueError('release_period_required')
            checked_url(url, family)
            host = urlparse(url).hostname
            if host in unavailable_hosts:
                raise ValueError('host_unavailable_this_batch')
            robots = check_robots(url, http_get, robots_cache)
            response = http_get(url, timeout=15, retries=1, allow_redirects=False,
                                headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'})
            if response.status_code in {401, 403, 429}:
                unavailable_hosts.add(host)
            # Redirects must not switch origin or bypass a denial.
            if getattr(response, 'url', url) != url:
                raise ValueError('unexpected_response_url')
            frames, receipt, _ = parse_acquisition(family, url, response.content, clock().isoformat(),
                period, catalog, status=response.status_code, content_type=response.headers.get('Content-Type', ''))
            receipt['robots'] = robots
            batch.frames = _merge_disjoint(batch.frames, frames)
            batch.receipts[family] = receipt
        except Exception as exc:
            # Fixed, bounded messages: don't copy arbitrary HTML/headers/tokens.
            batch.failures[family] = {'error_class': type(exc).__name__, 'reason': str(exc)[:100] if isinstance(exc, ValueError) else 'acquisition_failed'}
            response = getattr(exc, 'response', None)
            denied = response is not None and response.status_code in {401,403,429}
            if denied or type(exc).__name__ in {'ConnectionError', 'ConnectTimeout', 'ReadTimeout', 'Timeout'}:
                unavailable_hosts.add(urlparse(url).hostname)
    return batch


def qualify_against_owner(batch: CollectionBatch, legacy_frames: dict, read: Callable, catalog: dict) -> dict:
    """Enrich agreeing/new cells or a receipt-qualified published revision.

    A differing unreceipted legacy value remains unchanged and unqualified. All
    cells of the affected column are withheld to avoid stitching SA vintages.
    The three known NBS SA series may advance to a later official monthly release
    URL because NBS republishes a revised history in each release; every other
    cross-URL disagreement remains blocked. Raw nulls get a null-value digest;
    combine_first cannot resurrect them as verified old numbers.
    """
    owner_meta = {}
    for meta in catalog.values():
        group, table, column = binding(meta['owner_path'])
        key = (group + '/' + table, column)
        if key in owner_meta:
            raise ValueError('duplicate_catalog_owner_binding')
        owner_meta[key] = meta
    result = {k: v.copy() for k, v in legacy_frames.items()}
    for path, incoming in batch.frames.items():
        group, table = path.split('/')
        if group != 'china_macro':
            raise ValueError('wrong_collector_group')
        try:
            stored = read(group, table)
            stored = stored.copy() if stored is not None else pd.DataFrame()
            existing = result.get(table, pd.DataFrame()).combine_first(stored)
            if not existing.empty and (existing.index.has_duplicates or existing.columns.has_duplicates
                    or existing.index.to_period('M').has_duplicates):
                raise ValueError('duplicate_owner_cells')
        except Exception as exc:
            batch.failures[path] = {'error_class': type(exc).__name__, 'reason': 'owner_read_or_identity_failed'}
            continue
        qualified = incoming.copy()
        for col in [x for x in incoming if '__' not in x]:
            unsafe = []
            for d in incoming.index.intersection(existing.index):
                if col not in existing:
                    continue
                old, new = number(existing.at[d, col]), number(incoming.at[d, col])
                # A wide frame has structural NaNs where this release carries no
                # point for this metric/month. That is not a null revision and
                # must make no claim against the existing owner. An explicit
                # source-null DOES carry a value digest and keeps the fail-safe
                # revision/mismatch path below.
                new_digest = incoming.at[d, col+'__value_sha256'] if col+'__value_sha256' in incoming else None
                if new is None and not isinstance(new_digest, str):
                    continue
                if old is None or old == new:
                    continue
                # A normal revision must retain its exact source URL. The narrow
                # exception is a newer official NBS monthly vintage for one of
                # the three catalogued SA histories (see NBS_SA_REVISION_FAMILIES).
                row = existing.loc[d]; newrow = incoming.loc[d]
                try:
                    prior_digest = row.get(col+'__value_sha256')
                    old_receipt = {name: row.get(col+'__'+name) for name in ('source_url','published_at','response_sha256','definition_id','observed_at')}
                    valid_prior = prior_digest == value_receipt_digest(
                        col, d.strftime('%Y-%m'), old, old_receipt)
                    old_url = row.get(col+'__source_url')
                    new_url = newrow.get(col+'__source_url')
                    same_definition = (
                        row.get(col+'__definition_id') == newrow.get(col+'__definition_id'))
                    same_url = old_url == new_url
                    meta = owner_meta.get((path, col), {})
                    same_lineage = same_url or _nbs_sa_revision_lineage(
                        meta, old_url, new_url)
                    later = timestamp(newrow[col+'__observed_at']) > timestamp(
                        row[col+'__observed_at'])
                    old_pub = timestamp(row[col+'__published_at'])
                    new_pub = timestamp(newrow[col+'__published_at'])
                    forward_pub = new_pub >= old_pub if same_url else new_pub > old_pub
                except (ValueError, TypeError, KeyError):
                    valid_prior = same_definition = same_lineage = later = forward_pub = False
                if not (valid_prior and same_definition and same_lineage and later and forward_pub):
                    unsafe.append(d.strftime('%Y-%m'))
            if unsafe:
                batch.conflicts.append({'table': path, 'column': col, 'periods': unsafe, 'reason': 'unqualified_legacy_value_disagreement'})
                qualified = qualified.drop(columns=[c for c in qualified if c == col or c.startswith(col+'__')])
        if len(qualified.columns):
            # Preserve the existing table's index metadata as well as its values.
            if not existing.empty:
                qualified.index.name = existing.index.name
            # Return only incoming+current-fetch rows; normal runner owns upsert.
            result[table] = qualified.combine_first(result.get(table, pd.DataFrame()))
    return result


def indexed_releases(index_html: str, index_url: str, family: str) -> dict[str, str]:
    """Map publisher-declared reference periods to one exact release URL.

    Period comes from the publisher's anchor title, never page ordering or URL
    date. Duplicate URLs for one period are harmless; competing URLs are not.
    """
    checked_url(index_url, family)
    releases: dict[str, str] = {}
    for a in BeautifulSoup(index_html, 'html.parser').select('a[href]'):
        title = re.sub(r'\s+', '', a.get('title', '') + a.get_text('', strip=True))
        if FAMILIES[family][1] not in title:
            continue
        match = re.search(r'(20\d{2})年(?:1[—–－-])?(\d{1,2})月', title)
        if not match:
            continue
        period = f'{int(match[1]):04d}-{int(match[2]):02d}'
        month_index(period)
        url = checked_url(urljoin(index_url, a['href']), family)
        prior = releases.get(period)
        if prior is not None and prior != url:
            raise ValueError('release_discovery_duplicate_period')
        releases[period] = url
    return releases


def discover_release(index_html: str, index_url: str, family: str, expected_period: str) -> str:
    """Select one exact family/period from a publisher index."""
    month_index(expected_period)
    releases = indexed_releases(index_html, index_url, family)
    if expected_period not in releases:
        raise ValueError('release_discovery_missing_or_ambiguous')
    return releases[expected_period]
