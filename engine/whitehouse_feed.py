"""White House announcement feed — the primary-source policy monitor.

Polls the White House's own keyless WordPress RSS feeds (the `/news/feed/`
aggregate plus the `presidential-actions` and `fact-sheets` sections) and
normalises every item into a stable record carrying the FULL announcement body
(`content:encoded`), so the downstream brain reasons over the real text — not a
one-line excerpt.

It also owns the DEDUPE STATE (`data/whitehouse/processed.json`): a record of
which announcements have already been evaluated, so the (paid) Opus brain is only
ever asked about a genuinely NEW White House post. The hourly sentinel calls
`new_items()` → empty list ⇒ nothing changed ⇒ no commit, no LLM call.

Keyless · cached-free (the sentinel wants fresh) · degrade-NEVER-raise. Nothing
here is a scoring input; it feeds the display-only alert desk.
"""
from __future__ import annotations

import concurrent.futures as cf
import html as _html
import hashlib
import os
import stat
import tempfile
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "macro-dashboard/1.0 (+research; whitehouse-monitor)")
_TIMEOUT = 15
_MAX_WORKERS = 4

# Host-local acquisition evidence. Never place unqualified bodies in the public
# repository, site tree, Actions artifacts or the sentinel Git commit scope.
SOURCE_DOCUMENT_ROOT = Path.home() / ".local/share/mastermind/whitehouse/source_documents"

# The White House publishes a free, keyless RSS feed per section (WordPress
# `/feed/`). `/news/feed/` is the AGGREGATE — it already carries presidential
# actions, fact sheets, statements and releases — but the two section feeds are
# polled too so a post that is slow to reach the aggregate is never missed
# (dedupe by guid collapses the overlap). Each item includes <content:encoded>
# with the full body.
FEEDS: list[tuple[str, str]] = [
    ("https://www.whitehouse.gov/news/feed/", "news"),
    ("https://www.whitehouse.gov/presidential-actions/feed/", "presidential-actions"),
    ("https://www.whitehouse.gov/fact-sheets/feed/", "fact-sheets"),
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


# --------------------------------------------------------------------------- #
# fetch + parse
# --------------------------------------------------------------------------- #
def _fetch(url: str) -> bytes | None:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.debug("whitehouse fetch failed %s (%s)", url, e)
        return None


def _to_iso(pubdate: str) -> str:
    if not pubdate:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pubdate)
        if dt.tzinfo is None:
            # WH publishes in Eastern Time; a bare (naive) pubDate should be
            # treated as ET, not UTC.  Assuming UTC introduced up to a +5h
            # recency error (EST) when the WH omits the timezone offset.
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, IndexError):
        return ""


def _clean(text: str | None) -> str:
    """Strip HTML tags, decode entities, collapse whitespace (titles / excerpts)."""
    if not text:
        return ""
    return _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub(" ", text))).strip()


def _body_text(html: str | None, limit: int | None = 12000) -> str:
    """Reduce a content:encoded HTML body to clean paragraph text the LLM can read.
    Block tags become newlines so structure survives; remaining tags are stripped and
    HTML entities decoded. Bounded so one huge proclamation can't blow the prompt."""
    if not html:
        return ""
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|table|ul|ol|blockquote)>", "\n", html)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = _html.unescape(_TAG_RE.sub(" ", t))   # stdlib decodes named + numeric entities
    lines = [_WS_RE.sub(" ", ln).strip() for ln in t.split("\n")]
    normalized = "\n".join(ln for ln in lines if ln)
    return normalized if limit is None else normalized[:limit]


def _child(item, *names):
    for ch in item:
        if ch.tag.split("}")[-1] in names:
            return ch
    return None


def _slug_id(url: str, published: str) -> str:
    """Stable, URL-safe id: <YYYY-MM-DD>-<last-path-segment>. The WH permalink's
    final slug is unique and human-readable; the date prefix keeps the ledger sorted."""
    try:
        seg = [p for p in urlparse(url).path.split("/") if p]
        slug = seg[-1] if seg else "item"
    except Exception:  # noqa: BLE001
        slug = "item"
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:80] or "item"
    day = (published or "")[:10] or "undated"
    return f"wh-{day}-{slug}"


def _parse(raw: bytes, section: str) -> list[dict]:
    out: list[dict] = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.debug("whitehouse parse error (%s)", e)
        return out
    for it in root.findall(".//item"):
        title_el = _child(it, "title")
        title = _clean(title_el.text if title_el is not None else "")
        link_el = _child(it, "link")
        url = (link_el.text or link_el.get("href", "")) if link_el is not None else ""
        guid_el = _child(it, "guid")
        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        date_el = _child(it, "pubDate", "updated", "published", "date")
        published = _to_iso(date_el.text if date_el is not None else "")
        desc_el = _child(it, "description")
        excerpt = _clean(desc_el.text if desc_el is not None else "")
        # full body — content:encoded (namespaced) is the real article text
        ce = it.find(_CONTENT_NS)
        encoded_body = _body_text(ce.text if ce is not None else None, limit=None)
        source_body = encoded_body or excerpt
        body = source_body[:12000]
        cats = [_clean(c.text) for c in it.findall("category") if _clean(c.text)]
        if not title or not url:
            continue
        out.append({
            "id": _slug_id(url, published),
            "guid": guid or url,
            "title": title,
            "url": url,
            "published": published,
            "excerpt": excerpt[:400],
            "body": body,
            "body_origin": "content_encoded" if encoded_body else "description",
            "body_truncated": len(source_body) > len(body),
            "section": section,
            "categories": cats[:8],
        })
    return out



def retain_source_document(root: Path, item: dict, *, capture_dir: Path | None = None) -> dict:
    """Keep the exact normalized feed text independently of generated analysis.

    The existing sentinel writes a mode-0700 host-local capture directory outside
    all Git checkouts; files are mode 0600. No public artifact upload is added. Content-addressed revisions are published atomically and never
    replaced. This is neither raw HTTP capture nor upstream authentication,
    completeness of the publisher's page, rights qualification or Press admission.
    Excerpt fallbacks and truncated bodies are explicitly retained as such.
    No network, model, processed-state, alert-ledger or site write occurs here.
    """
    fields = ("id", "guid", "title", "url", "published", "section", "body")
    if not isinstance(item, dict) or any(
        not isinstance(item.get(key), str) or not item[key].strip() for key in fields
    ):
        raise ValueError("source document lacks required feed fields")
    url = urlparse(item["url"])
    if (url.scheme != "https" or url.netloc != "www.whitehouse.gov"
            or not url.path.startswith("/") or url.query or url.fragment):
        raise ValueError("source document is not on the official White House origin")
    published = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
    if published.tzinfo is None:
        raise ValueError("source document publication time must be timezone-aware")
    if item["id"] != _slug_id(item["url"], item["published"]):
        raise ValueError("source document id does not match its publication identity")
    if item["section"] not in {section for _, section in FEEDS}:
        raise ValueError("source document section is not an existing feed")
    if (item.get("body_origin") not in {"content_encoded", "description"}
            or type(item.get("body_truncated")) is not bool
            or len(item["body"]) > 12000):
        raise ValueError("source document has unknown body provenance or bound")
    record = {key: item[key] for key in fields}
    record.update(
        schema="whitehouse.source_document.v1",
        normalization="whitehouse-feed-text/v1",
        body_origin=item["body_origin"], body_truncated=item["body_truncated"],
        body_sha256=hashlib.sha256(item["body"].encode("utf-8")).hexdigest(),
        rights_status="unqualified", allow_stage=False, allow_emit=False,
    )
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    directory = Path(capture_dir if capture_dir is not None else SOURCE_DOCUMENT_ROOT).expanduser().resolve()
    if directory.is_relative_to(Path(root).resolve()) or any(
        (ancestor / ".git").exists() or (ancestor / ".git").is_symlink()
        for ancestor in (directory, *directory.parents)
    ):
        raise ValueError("source capture directory must be outside all Git checkouts")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(directory.stat().st_mode) != 0o700:
        raise ValueError("source capture directory must have mode 0700")
    target = directory / f"{digest}.json"
    fd, temporary = tempfile.mkstemp(prefix=".source-", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # A same-directory hard link publishes a complete file exclusively.
            # os.replace would silently heal/overwrite corrupted prior evidence.
            os.link(temporary, target)
        except FileExistsError:
            if (target.is_symlink() or not target.is_file()
                    or stat.S_IMODE(target.stat().st_mode) != 0o600
                    or target.read_bytes() != raw):
                raise ValueError("existing source document differs from its content address")
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(target), "sha256": digest,
            "body_sha256": record["body_sha256"]}


# --------------------------------------------------------------------------- #
# collect + dedupe
# --------------------------------------------------------------------------- #
def collect(max_age_days: float = 4.0) -> list[dict]:
    """All current White House items across the polled feeds, deduped by guid and
    filtered to the recent window (a sentinel must never resurface a week-old post).
    Sorted newest-first. Never raises."""
    def _pull(url, section):
        return _parse(_fetch(url) or b"", section)

    items: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        for res in ex.map(lambda f: _pull(*f), FEEDS):
            items.extend(res)

    # dedupe by guid; the aggregate + section feeds overlap heavily
    seen: set[str] = set()
    uniq: list[dict] = []
    for it in items:
        if it["guid"] in seen:
            continue
        seen.add(it["guid"])
        uniq.append(it)

    uniq = _recent(uniq, max_age_days)
    uniq.sort(key=lambda x: x.get("published", ""), reverse=True)
    return uniq


def _recent(items: list[dict], max_age_days: float) -> list[dict]:
    if not max_age_days:
        return items
    now = datetime.now(timezone.utc)
    out = []
    for it in items:
        p = it.get("published", "")
        try:
            dt = datetime.fromisoformat(p) if p else None
        except (TypeError, ValueError):
            dt = None
        if dt is None or (now - dt).total_seconds() <= max_age_days * 86400:
            out.append(it)
    return out


# --------------------------------------------------------------------------- #
# dedupe state — which announcements were already evaluated by the brain
# --------------------------------------------------------------------------- #
def _state_path(root: Path) -> Path:
    return Path(root) / "data" / "whitehouse" / "processed.json"


def load_processed(root: Path) -> dict:
    """{'seen': {guid: {at, id, activated, importance}}}. Missing/corrupt -> empty."""
    p = _state_path(root)
    try:
        d = json.loads(p.read_text())
        if isinstance(d, dict) and isinstance(d.get("seen"), dict):
            return d
    except Exception:  # noqa: BLE001
        pass
    return {"seen": {}}


def save_processed(root: Path, state: dict) -> None:
    p = _state_path(root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:  # noqa: BLE001 — never fatal
        log.warning("whitehouse: processed.json write failed (%s)", e)


def mark_seen(state: dict, item: dict, *, activated: bool, importance: int | None) -> None:
    state.setdefault("seen", {})[item["guid"]] = {
        "id": item["id"],
        "at": datetime.now(timezone.utc).isoformat(),
        "activated": bool(activated),
        "importance": importance,
    }


def new_items(items: list[dict], state: dict) -> list[dict]:
    """Items whose guid has not been evaluated before — the brain's worklist."""
    seen = (state or {}).get("seen", {})
    return [it for it in items if it.get("guid") not in seen]
