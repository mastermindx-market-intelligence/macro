"""Offline FDA drug-release document reader for the Macro press official-feed consumer.

This is a pure reader: it validates and extracts the clean text of one FDA
"On this page" style drug-approval release plus its website-policy page, both
supplied as bounded local files. It performs no network, publication or
dispatch work and grants no rights or publication authority; the caller retains editorial
and source-specific rights qualification.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from engine.press.external_candidate import _read_bound

FDA_POLICY_URL = "https://www.fda.gov/about-fda/about-website/website-policies"

_RELEASE_ROUTE_PREFIX = "/drugs/resources-information-approved-drugs/"
_MAX_INPUT_BYTES = 1_000_000
_MAX_RELEASE_BODY_CHARS = 20_000
_MAX_QUALIFIERS = 10

# Publisher/event metadata. Only ``article:published_time`` may establish the
# event day; content-current/updated metadata is never a substitute.
_PUBLISHED_TIME_PROPERTY = "article:published_time"
_PUBLISHED_TIME_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{2})/(\d{2})/(\d{4}) - \d{2}:\d{2}$"
)
_PUBLISHED_TIME_STRPTIME = "%a, %m/%d/%Y - %H:%M"

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Literal, complete policy sentences that qualify FDA website content itself.
_POLICY_COPYRIGHT_SENTENCE = (
    "Unless otherwise noted, the contents of the FDA website (www.fda.gov) "
    "— both text and graphics — are not copyrighted."
)
_POLICY_PUBLIC_DOMAIN_SENTENCE = (
    "They are in the public domain and may be republished, reprinted and "
    "otherwise used freely by anyone without the need to obtain permission "
    "from FDA."
)
_POLICY_COPIED_DATE_PHRASE = "lists the date that the material was copied"
_POLICY_SOURCE_LINK_PHRASE = "provides a link back to its source"

def _require_policy_url(url: object) -> None:
    """Require the exact, current FDA website-policy URL."""
    if url != FDA_POLICY_URL:
        raise ValueError("rights_basis must cite the exact FDA website policy URL")


def _canonical_fda_release_url(item_url: object) -> str:
    """Validate the raw RSS item URL and return its canonical https form.

    Only ``http`` or ``https`` on ``www.fda.gov`` under the
    ``/drugs/resources-information-approved-drugs/<slug>`` route is accepted,
    with no userinfo, port, query or fragment. The canonical URL is the exact
    https twin of the accepted host and path; the raw RSS identity is never
    rewritten and redirects are never inferred.
    """
    if not isinstance(item_url, str) or not item_url:
        raise ValueError("item_url must be a nonempty string")
    if any(ord(char) <= 32 or ord(char) == 127 for char in item_url):
        raise ValueError("item_url must not contain whitespace or control characters")
    parts = urlsplit(item_url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("item_url must be an http or https www.fda.gov URL")
    if parts.netloc != "www.fda.gov":
        raise ValueError("item_url host must be exactly www.fda.gov")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise ValueError("item_url must not carry userinfo")
    if parts.port is not None:
        raise ValueError("item_url must not carry a port")
    if "?" in item_url:
        raise ValueError("item_url must not carry a query string")
    if "#" in item_url:
        raise ValueError("item_url must not carry a fragment")
    path = parts.path
    if not path.startswith(_RELEASE_ROUTE_PREFIX):
        raise ValueError("item_url must use the FDA resources-information route")
    slug = path[len(_RELEASE_ROUTE_PREFIX):]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("item_url must end in a single release slug")
    return "https://www.fda.gov" + path


def _require_event_day(value: object) -> date:
    """Parse the ISO event day carried by the feed item."""
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError("event_date must be an ISO calendar day")


def _require_aware_published(published: object) -> datetime:
    """Require a timezone-qualified published instant."""
    if not isinstance(published, datetime):
        raise ValueError("published must be a datetime")
    if published.tzinfo is None or published.utcoffset() is None:
        raise ValueError("published must carry an explicit timezone")
    return published


def _canonical_links(soup: BeautifulSoup) -> list:
    links = []
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        if isinstance(rel, str):
            rel = rel.split()
        if "canonical" in rel:
            links.append(link)
    return links


def _require_canonical_link(soup: BeautifulSoup, expected: str, label: str) -> None:
    """Require exactly one canonical link with the exact expected href."""
    links = _canonical_links(soup)
    if not links:
        raise ValueError(f"{label} document has no canonical link")
    if len(links) > 1:
        raise ValueError(f"{label} document has more than one canonical link")
    href = links[0].get("href")
    if href != expected:
        raise ValueError(f"{label} canonical link does not match the canonical URL")


def _extract_clean_article(soup: BeautifulSoup, expected_canonical: str, label: str) -> str:
    """Read the unique FDA article body, excluding navigation and footer text."""
    _require_canonical_link(soup, expected_canonical, label)
    bodies = soup.select("article > div.col-md-8")
    if len(bodies) != 1:
        raise ValueError(f"{label} document must have one article > div.col-md-8")
    body = bodies[0]
    for stray in body.select("script, style, template, noscript"):
        stray.decompose()
    text = " ".join(body.get_text(" ", strip=True).split())
    if not text:
        raise ValueError(f"{label} body is empty")
    if len(text) > _MAX_RELEASE_BODY_CHARS:
        raise ValueError(f"{label} body exceeds 20,000 characters")
    return text


def _expanded_initialisms(text: str) -> str:
    """For summary comparison only, omit an initialism with its exact expansion.

    FDA RSS sometimes omits '(NMIBC)' after 'non-muscle invasive bladder cancer'.
    All expansion words, quantities and qualifiers stay intact. Returned source
    text is never normalized this way.
    """
    def omit(match):
        abbreviation = match[1]
        words = re.findall(r"[^\W\d_]+", text[:match.start()], re.UNICODE)
        initials = "".join(word[0].upper() for word in words[-len(abbreviation):])
        return "" if initials == abbreviation else match[0]
    return re.sub(r" \(([A-Z]{2,12})\)", omit, text)


def _published_meta_day(soup: BeautifulSoup, label: str) -> date:
    """Read the single ``article:published_time`` meta and return its day.

    Only the calendar date is used; the metadata supplies neither a timezone
    nor exact seconds.
    """
    metas = soup.find_all("meta", attrs={"property": _PUBLISHED_TIME_PROPERTY})
    if not metas:
        raise ValueError(f"{label} has no article:published_time metadata")
    if len(metas) > 1:
        raise ValueError(f"{label} has more than one article:published_time metadata")
    content = metas[0].get("content")
    if not isinstance(content, str) or not _PUBLISHED_TIME_RE.match(content):
        raise ValueError(f"{label} published_time is not in the observed FDA format")
    try:
        moment = datetime.strptime(content, _PUBLISHED_TIME_STRPTIME)
    except ValueError as exc:
        raise ValueError(f"{label} published_time is not a real date/time: {exc}") from exc
    return moment.date()


def _norm_ws(text: str) -> str:
    return " ".join(text.split())


def _require_qualifiers(qualifiers: object, body_norm: str) -> None:
    """Require 1..10 distinct nonempty literal qualifiers present in the body."""
    if not isinstance(qualifiers, list):
        raise ValueError("source_qualifiers must be a list of literal strings")
    if not 1 <= len(qualifiers) <= _MAX_QUALIFIERS:
        raise ValueError(f"source_qualifiers must hold 1..{_MAX_QUALIFIERS} entries")
    seen: list[str] = []
    for entry in qualifiers:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("source_qualifiers entries must be nonempty strings")
        if len(entry) > 1000:
            raise ValueError("source_qualifiers entries must be at most 1000 chars")
        if entry in seen:
            raise ValueError("source_qualifiers entries must be distinct")
        seen.append(entry)
        if entry != _norm_ws(entry) or entry not in body_norm:
            raise ValueError(f"source_qualifier not present in release body: {entry!r}")


def read_fda_drug_release(
    q: dict,
    summary: str,
    published: datetime,
    release_path: Path,
    policy_path: Path,
) -> str:
    """Read and qualify one FDA drug-release document offline.

    Returns the entire clean release body. Refuses anything that fails the
    source, structure, publisher-date, summary, qualifier or policy checks;
    the caller retains relevance, rights and editorial authority.
    """
    if not isinstance(q, dict):
        raise ValueError("q must be a dict")
    rights = q.get("rights_basis")
    if not isinstance(rights, dict):
        raise ValueError("q.rights_basis must be a dict")
    _require_policy_url(rights.get("policy_url"))

    canonical_url = _canonical_fda_release_url(q.get("item_url"))
    event_day = _require_event_day(q.get("event_date"))
    published = _require_aware_published(published)
    if not isinstance(summary, str):
        raise ValueError("summary must be a string")

    release_html = _read_bound(Path(release_path), q.get("release_sha256"), _MAX_INPUT_BYTES)
    policy_html = _read_bound(Path(policy_path), q.get("policy_sha256"), _MAX_INPUT_BYTES)

    release_soup = BeautifulSoup(release_html, "html.parser")
    body = _extract_clean_article(release_soup, canonical_url, "release")

    if len(body) > _MAX_RELEASE_BODY_CHARS:
        raise ValueError("release body exceeds 20,000 characters")

    # Publisher day comes only from article:published_time; the RSS instant
    # supplies the timezone-qualified day, and both must equal the event day.
    # A cross-UTC-midnight disagreement is refused; no timezone is invented.
    meta_day = _published_meta_day(release_soup, "release")
    rss_day = published.astimezone(timezone.utc).date()
    if meta_day != rss_day or meta_day != published.date() or meta_day != event_day:
        raise ValueError(
            "publisher day, RSS published day and event_date must be the same day"
        )

    spelled = f"{_MONTH_NAMES[meta_day.month - 1]} {meta_day.day}, {meta_day.year}"
    body_norm = _norm_ws(body)
    if spelled not in body_norm:
        raise ValueError(f"release body does not state the full event date: {spelled}")

    if not summary.strip() or _expanded_initialisms(_norm_ws(summary)) not in _expanded_initialisms(body_norm):
        raise ValueError("summary is not contained in the release body")

    _require_qualifiers(q.get("source_qualifiers"), body_norm)

    policy_soup = BeautifulSoup(policy_html, "html.parser")
    policy_text = _extract_clean_article(policy_soup, FDA_POLICY_URL, "policy")
    policy_norm = _norm_ws(policy_text)

    if _POLICY_COPYRIGHT_SENTENCE not in policy_norm:
        raise ValueError("policy is missing the literal not-copyrighted sentence")
    if _POLICY_PUBLIC_DOMAIN_SENTENCE not in policy_norm:
        raise ValueError("policy is missing the literal public-domain sentence")
    if _POLICY_COPIED_DATE_PHRASE not in policy_norm:
        raise ValueError("policy is missing the copied-date recommendation")
    if _POLICY_SOURCE_LINK_PHRASE not in policy_norm:
        raise ValueError("policy is missing the link-back-to-source recommendation")

    return body
