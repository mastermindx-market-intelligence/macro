"""LEAF · CONTEXT-ONLY · KEYLESS · NO-LLM. Non-China regional PIT event-bus module
on the existing qbus join surface (spec A-F02-W2-4, ledger row MO-PAID-034).

Nothing in the scoring path imports this module; every public function returns
plain data or None and NEVER raises into the build. No ambient-time calls in
library code — `asof` and `crawled_at` are always passed in by the caller
(PIT discipline; the sole exception is `ingest`'s own single `crawled_at`
default line, which is the ingest boundary).

This is the EUROPE sibling of engine/china_news_intel.py's PIT event-bus leg —
first-print, keep-FIRST accrual of official EU/UK press headlines, joined into
the ONE event system via engine/qbus.py's public API (`append_items` /
`assign_event_keys`). This module mints NO event_key and owns NO second event
database. `data/europe_news_vector/events.parquet` is a desk artifact: it
carries a locally-minted `event_id` plus title/url/provenance columns, and
an `item_id` keyed on source|url|title (so same-title restatements stay
distinct items). `event_key` lives only in qbus (minted by
`qbus.assign_event_keys`). `read_events()` returns the desk parquet and
never queries qbus.

Resolves F02 owner-map UNRESOLVED-2 — research/market_intelligence_productization/
MARKET_ONTOLOGY_F02_OWNER_SOURCE_RIGHTS_MAP_2026-09-05.md :73 ("non-China
geopolitical event producer ... Resolves when: one non-China region has a
producer whose rows join through qbus.assign_event_keys()"). Does NOT close
UNRESOLVED-3/3a/4/6.

Sources: public official EU/UK press wires only, each with an explicit,
machine-quotable reuse-rights basis (spec §3). At the 2026-09-06 preflight
exactly two tier-1 sources passed BOTH the reachability check and the rights
quote requirement:
  - ec_presscorner (European Commission) — CC BY 4.0 / Commission Decision
    2011/833/EU, "reuse is allowed, provided appropriate credit is given".
  - boe_news (Bank of England) — Open Government Licence v3.0, "commercial
    re-use of the Resources" explicitly named.
Three candidates are excluded and recorded as printed nulls (§7), never
silently dropped and never replaced with an unlisted feed:
  - ecb_press — rights_state UNVERIFIED_EXCLUDED: the ECB disclaimer grants
    "free use ... subject to conditions" but never uses the word "commercial",
    and its one content-specific carve-out is a *restriction* (prior written
    authorisation), not a grant.
  - council_eu — rights_state UNVERIFIED_EXCLUDED: the RSS candidate AND the
    legal-notice page both returned HTTP 403 (Imperva/Akamai bot wall) — rights
    could not even be checked.
  - eurlex_oj_l — rights_state UNVERIFIED_EXCLUDED: the feed endpoint itself is
    dead/reconfigured (redirects to an HTML page, not RSS/XML).
A source whose rights_state is not VERIFIED_PUBLIC_REUSE is NEVER fetched over
the network (§7: "the source is never fetched") — its coverage_state is the
printed null "SOURCE_OUTAGE" rather than a live network result.
"""
from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

from lib import config
from engine import qkernel

log = logging.getLogger(__name__)

SCHEMA = "europe_news_intel.v1"
DESK = "europe_news_intel"
REGION = "europe"

COVERAGE_STATES = ("COVERED", "NO_COVERAGE", "SOURCE_OUTAGE", "DELAYED_SOURCE")
JURISDICTIONS = ("EU", "EA", "UK", "EFTA", "AMBIGUOUS_JURISDICTION")
RIGHTS_STATES = ("VERIFIED_PUBLIC_REUSE", "UNVERIFIED_EXCLUDED")

# Desk artifact schema. `event_key` is intentionally absent — it lives only in
# qbus. `body_sha256` here is a hash of the RSS <description> (summary), never
# an article body: this desk does not fetch bodies (§3.4), so the column will
# not join to another desk's article-body hash. Kept as `body_sha256` for
# qbus-row field parity with china_news_intel, not as a cross-desk content key.
_COLUMNS: tuple[str, ...] = (
    "event_id", "item_id", "first_seen_utc", "seendate", "fetch_clock_utc", "asof",
    "title", "url", "source", "domain", "source_tier", "lang", "theme",
    "jurisdiction", "coverage_state", "timestamp_quality", "body_sha256", "rights_basis",
)

_COVERAGE_COLUMNS: tuple[str, ...] = (
    "asof", "source_key", "coverage_state", "rights_state", "n_items",
    "newest_seendate", "fetch_clock_utc", "detail",
)

_UA = "macro-dashboard/1.0"


# --------------------------------------------------------------------------- #
# config / paths
# --------------------------------------------------------------------------- #
def _cfg() -> dict:
    return config.load().get("europe_news_intel", {}) or {}


def enabled() -> bool:
    return bool(_cfg().get("enabled", False))


def _events_path() -> Path:
    p = config.data_dir() / "europe_news_vector" / "events.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _coverage_path() -> Path:
    p = config.data_dir() / "europe_news_vector" / "coverage.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
# pure helpers (NO network, NO clock)
# --------------------------------------------------------------------------- #
def sources(cfg: dict | None = None) -> list[dict]:
    """Configured source specs (§3.2/§8 config block). Every candidate the spec
    names is present, including excluded ones — a printed null is a row here
    with rights_state UNVERIFIED_EXCLUDED, never an absent entry. PURE."""
    cfg = cfg if cfg is not None else _cfg()
    out: list[dict] = []
    for s in (cfg.get("sources") or []):
        out.append({
            "key": str(s.get("key") or ""),
            "url": str(s.get("url") or ""),
            "publisher": str(s.get("publisher") or ""),
            "tier": int(s.get("tier") or 3),
            "jurisdiction": str(s.get("jurisdiction") or "EU"),
            "lang": str(s.get("lang") or "en"),
            "rights_basis": str(s.get("rights_basis") or ""),
            "rights_state": str(s.get("rights_state") or "UNVERIFIED_EXCLUDED"),
            "expected_cadence_hours": int(s.get("expected_cadence_hours") or 24),
            "detail": str(s.get("detail") or ""),
        })
    return out


def _domain_of(url: str) -> str:
    """Bare lowercased host of a URL, '' on failure. PURE."""
    try:
        netloc = urlparse(str(url or "")).netloc.lower()
    except (ValueError, TypeError):
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def source_tier(source: str, domain: str) -> int:
    """qkernel.source_tier(domain, source) first (the ONE merged tier table);
    fall back to the configured tier for this source key when qkernel has no
    entry for the domain (both live sources here — ec.europa.eu,
    bankofengland.co.uk — are outside qkernel's allowlist, so the config tier
    is the one actually used). PURE."""
    t = qkernel.source_tier(domain or "", source or "")
    if t:
        return t
    for s in sources():
        if s["key"] == source:
            return int(s.get("tier") or 3)
    return 3


def event_id(title: str, domain: str) -> str:
    """Delegate to qkernel (china_news_intel.py:184 precedent: source discriminator
    = domain, url deliberately left blank so the discriminator is the host token,
    not the per-article URL). PURE."""
    return qkernel.event_id(source=(domain or "").lower().strip(), url="",
                            title=title or "", lang="en")


def article_item_id(source: str, url: str, title: str) -> str:
    """Per-article item_id for the qbus row. qkernel.item_id keys on host+title
    only, so two same-title restatements on one host would collide and
    qbus.append_items keep-FIRST would drop one. Include the full URL so both
    items reach the bus and assign_event_keys can cluster them. PURE."""
    basis = "|".join((
        (source or "").lower().strip(),
        (url or "").lower().strip(),
        qkernel.norm_title(title or "", "en"),
    ))
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


# Deterministic keyword buckets. Order matters (first hit wins). Never returns ""
# — an empty theme would silently never cluster in qbus.assign_event_keys (qbus.py
# :176 requires a SHARED entity or theme; this desk emits no entities).
_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "monetary_policy": ("interest rate", "rate decision", "monetary policy",
                        "governing council", "bank rate", "quantitative easing",
                        "quantitative tightening", "mpc "),
    "financial_stability": ("financial stability", "systemic risk", "stress test",
                            "capital requirement", "banking supervision",
                            "prudential", "resolution regime"),
    "trade_policy": ("tariff", "trade agreement", "customs union",
                     "export control", "sanctions", "trade deal", "trade war"),
    "competition_antitrust": ("antitrust", "competition", "merger", "cartel",
                              "dominance", "state aid",
                              # EC Press Corner category slug POLICY_AREA=COMPETY
                              # (not English; "competition" already covers prose).
                              "compety"),
    "fiscal_policy": ("budget", "fiscal", "deficit", "public spending", "tax "),
    "regulatory": ("regulation", "directive", "guideline", "compliance",
                   "supervisory", "legislat"),
}


def classify_theme(text: str) -> str:
    """Deterministic keyword-bucket theme classifier. NEVER "" — falls back to
    "policy_geo_other" (spec §2 CRITICAL). PURE."""
    blob = (text or "").lower()
    for theme, kws in _THEME_KEYWORDS.items():
        if any(k in blob for k in kws):
            return theme
    return "policy_geo_other"


_JURISDICTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "UK": ("united kingdom", "bank of england", "britain", "british", "uk",
           "fca", "hm treasury", "westminster", "sterling"),
    "EA": ("euro area", "eurozone", "ecb", "european central bank"),
    "EU": ("european commission", "european union", "brussels", "member state",
           "eu", "eurocrat"),
    "EFTA": ("efta", "european free trade association", "norway", "iceland",
             "liechtenstein", "switzerland"),
}


def _keyword_hit(blob: str, kw: str) -> bool:
    """Word-boundary match for a single token; substring match for a phrase.
    Stops unanchored 'uk ' / 'eu ' from matching any word that merely ends in
    those two letters (luk, chuk, nouveau). PURE."""
    token = (kw or "").strip()
    if not token:
        return False
    if " " in token:
        return token in blob
    return re.search(rf"\b{re.escape(token)}\b", blob) is not None


def jurisdiction_for(source_key: str, text: str) -> str:
    """Source default, overridden only by an unambiguous deterministic match.
    Returns AMBIGUOUS_JURISDICTION when two or more jurisdictions match and
    none dominates (the source's own default is not among the matches). PURE."""
    default = "EU"
    for s in sources():
        if s["key"] == source_key:
            default = s.get("jurisdiction", "EU")
            break
    blob = (text or "").lower()
    matched = {j for j, kws in _JURISDICTION_KEYWORDS.items()
              if any(_keyword_hit(blob, k) for k in kws)}
    if not matched:
        return default
    if len(matched) == 1:
        return next(iter(matched))
    if default in matched:
        return default
    return "AMBIGUOUS_JURISDICTION"


def clean_time(value: str) -> str:
    """RFC-822 pubDate -> tz-aware ISO 8601 (UTC). '' on empty/unparseable input.
    PURE — no clock read."""
    s = " ".join(str(value or "").split())
    if not s:
        return ""
    try:
        dt = parsedate_to_datetime(s)
    except (ValueError, TypeError, IndexError):
        return ""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def timestamp_quality(seendate: str) -> str:
    """RFC-822 pubDate with sub-day precision -> PUBLISHER_STATED; empty or
    unparseable -> CRAWL_BOUNDED. PURE (single-argument, no clock): the
    "future or > 48h before the crawl -> CORRUPTED" refinement described in
    spec §5/§7 needs a crawl-time reference this one-argument helper does not
    receive, so that override is applied by `_corruption_override` inside
    `build_records`, which IS given `crawled_at` — the full three-way rule is
    still honored, without adding a clock read or an ambient default here."""
    return "PUBLISHER_STATED" if clean_time(seendate) else "CRAWL_BOUNDED"


def _corruption_override(tq: str, seendate_iso: str, crawled_at_iso: str) -> str:
    """Demote a PUBLISHER_STATED stamp to CORRUPTED when it lies in the future
    or more than 48h before the injected crawl clock. Both timestamps are
    passed in — PURE, no ambient clock."""
    if tq != "PUBLISHER_STATED" or not seendate_iso or not crawled_at_iso:
        return tq
    try:
        sd = datetime.fromisoformat(seendate_iso)
        ca = datetime.fromisoformat(crawled_at_iso)
    except (ValueError, TypeError):
        return tq
    if sd.tzinfo is None:
        sd = sd.replace(tzinfo=timezone.utc)
    if ca.tzinfo is None:
        ca = ca.replace(tzinfo=timezone.utc)
    if sd > ca or (ca - sd) > timedelta(hours=48):
        return "CORRUPTED"
    return tq


def build_records(articles: list[dict], crawled_at: str, asof: date,
                  source_states: dict[str, str]) -> list[dict]:
    """Raw RSS items -> desk event records. PURE (no network/clock; crawled_at
    and asof injected). `source_states` is the coverage dict from `fetch_all`,
    stamped onto every row from that source (spec §6.1: every row carries
    source_tier, fetch_clock_utc and coverage_state)."""
    src_by_key = {s["key"]: s for s in sources()}
    out: list[dict] = []
    for a in (articles or []):
        title = (a.get("title") or "").strip()
        if not title:
            continue
        url = (a.get("link") or "").strip()
        source_key = str(a.get("source_key") or "")
        spec = src_by_key.get(source_key, {})
        domain = _domain_of(url)
        summary = (a.get("description") or "").strip()
        category = (a.get("category") or "").strip()
        blob = f"{title} {summary} {category}"
        # No intra-batch skip on event_id: same-title restatements with different
        # URLs must all reach qbus so assign_event_keys can cluster them. Desk
        # keep-FIRST on event_id happens only in accrue() / the desk parquet.
        eid = event_id(title, domain or source_key)

        pubdate_raw = a.get("pubDate", "")
        seendate = clean_time(pubdate_raw)
        tq = _corruption_override(timestamp_quality(pubdate_raw), seendate, crawled_at)
        tier = source_tier(source_key, domain)
        theme = classify_theme(blob)
        juris = jurisdiction_for(source_key, blob)
        cov_state = source_states.get(source_key, "SOURCE_OUTAGE")

        # RSS-<description> hash for tier-1 rows only (never an article body —
        # this desk does not fetch bodies; §3.4). Same column name as the china
        # Missing-Tape field for qbus-row parity; it will not join to another
        # desk's article-body hash. See _COLUMNS.
        bhash = ""
        if tier == 1 and summary:
            try:
                from engine.qbus import body_sha256 as _sha256
                bhash = _sha256(summary)
            except Exception:  # noqa: BLE001
                bhash = ""

        out.append({
            "event_id": eid,
            "item_id": article_item_id(source_key, url, title),
            "first_seen_utc": crawled_at,
            "seendate": seendate,
            "fetch_clock_utc": crawled_at,
            "asof": asof.isoformat(),
            "title": title,
            "url": url,
            "source": source_key,
            "domain": domain,
            "source_tier": tier,
            "lang": "en",
            "theme": theme,
            "jurisdiction": juris,
            "coverage_state": cov_state,
            "timestamp_quality": tq,
            "body_sha256": bhash,
            "rights_basis": spec.get("rights_basis", ""),
        })
    return out


def accrue(existing, new_records: list[dict]):
    """Append-only merge, keep-FIRST on event_id. Byte-for-byte the
    engine/china_news_intel.py:495-511 contract (§6.2). PURE."""
    import pandas as pd
    new_df = pd.DataFrame(new_records, columns=list(_COLUMNS))
    if existing is None or len(existing) == 0:
        merged = new_df
    else:
        merged = pd.concat([existing.reindex(columns=list(_COLUMNS)), new_df],
                           ignore_index=True)
    merged = merged.drop_duplicates(subset=["event_id"], keep="first")
    merged = merged.sort_values(["first_seen_utc", "event_id"]).reset_index(drop=True)
    return merged


def build_qbus_rows(records: list[dict], raw_articles: list[dict],
                    crawled_at: str) -> list[dict]:
    """qbus row mapping (spec §6.3). PURE given the injected crawled_at.

    `records` is the full pre-dedup article batch (same-title restatements
    included). Desk keep-FIRST on event_id is accrue()'s job, not this
    mapper's. `raw_articles` is accepted for signature parity with the
    engine/china_news_intel.py:720 precedent; body_sha256 is already on
    `records`. item_id / event_key are LEFT UNSET — filled by
    qbus.normalize_row / qbus.assign_event_keys (engine/qbus.py:113, :176)."""
    del raw_articles  # kept for signature parity with the china precedent
    rows: list[dict] = []
    for rec in records:
        tier = int(rec.get("source_tier") or 3)
        theme = rec.get("theme") or "policy_geo_other"
        rows.append({
            "desk": DESK,
            "item_id": rec.get("item_id") or article_item_id(
                str(rec.get("source") or ""), str(rec.get("url") or ""),
                str(rec.get("title") or "")),
            "source": rec.get("source", ""),
            "source_tier": tier,
            "lang": "en",
            "url": rec.get("url", ""),
            "title": rec.get("title", ""),
            "body_sha256": rec.get("body_sha256", ""),
            "seendate": rec.get("seendate", ""),
            "_crawled_at": crawled_at,
            "timestamp_quality": rec.get("timestamp_quality", "CRAWL_BOUNDED"),
            "entities": [],
            "themes": [theme],
            # deterministic tier proxy — engine/news_vector.py:585. No model, no LLM.
            "importance_raw": float(2 - tier) if tier in (1, 2) else 0.0,
        })
    return rows


# --------------------------------------------------------------------------- #
# network (each returns data or None; NEVER raises)
# --------------------------------------------------------------------------- #
def fetch_rss(url: str, timeout: int = 20) -> list[dict] | None:
    """None on ANY failure (DNS/HTTP/timeout/parse) — None means OUTAGE, []
    means the feed answered with no items. These two are NEVER collapsed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read()
        root = ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001
        log.debug("europe_news_intel: fetch_rss(%s) failed (%s)", url, e)
        return None
    items: list[dict] = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        items.append({
            "title": title,
            "link": (it.findtext("link") or "").strip(),
            "description": (it.findtext("description") or "").strip(),
            "pubDate": (it.findtext("pubDate") or "").strip(),
            "category": (it.findtext("category") or "").strip(),
        })
    return items


def _is_delayed(newest_iso: str, asof: date, cadence_hours: int,
                crawled_at: str | None = None) -> bool:
    """True when the newest item is older than the source's staleness grace,
    anchored on the injected fetch clock (`crawled_at`) when provided — never
    on the end of `asof`'s day (that systematically mis-ages a mid-day
    collect.py ingest by up to ~24h). When `crawled_at` is absent or
    unparseable, fall back to the START of `asof`'s day. PURE.

    Daily sources keep a 3x cadence grace (72h on a 24h cadence) so a weekend
    gap is not DELAYED. Weekly-or-slower sources (cadence >= 168h) use 1x:
    one missed cadence is DELAYED (a 168h cadence with 3x would hide an
    8-day-stale BoE feed for 21 days)."""
    if not newest_iso:
        return False
    try:
        newest_dt = datetime.fromisoformat(newest_iso)
    except (ValueError, TypeError):
        return False
    if newest_dt.tzinfo is None:
        newest_dt = newest_dt.replace(tzinfo=timezone.utc)
    anchor = datetime.combine(asof, time(0, 0, 0), tzinfo=timezone.utc)
    if crawled_at:
        try:
            parsed = datetime.fromisoformat(crawled_at)
        except (ValueError, TypeError):
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            anchor = parsed
    age_hours = (anchor - newest_dt).total_seconds() / 3600.0
    grace = 1 if cadence_hours >= 168 else 3
    return age_hours > (cadence_hours * grace)


def fetch_all(cfg: dict, asof: date,
              crawled_at: str | None = None) -> tuple[list[dict], dict[str, str]]:
    """-> (items, {source_key: coverage_state}); every configured source has a
    key in the state map, always (printed nulls, §7). A source whose
    rights_state is not VERIFIED_PUBLIC_REUSE is never fetched (§7:
    "the source is never fetched") and reports SOURCE_OUTAGE.
    `crawled_at` is the injected fetch-clock for DELAYED_SOURCE (PIT)."""
    cap = int(cfg.get("max_per_source", 60))
    coverage: dict[str, str] = {}
    items: list[dict] = []
    for s in sources(cfg):
        key = s["key"]
        if s.get("rights_state") != "VERIFIED_PUBLIC_REUSE":
            coverage[key] = "SOURCE_OUTAGE"
            continue
        raw = fetch_rss(s.get("url", ""))
        if raw is None:
            coverage[key] = "SOURCE_OUTAGE"
            continue
        raw = raw[:cap]
        if not raw:
            coverage[key] = "NO_COVERAGE"
            continue
        newest_iso = ""
        for it in raw:
            it["source_key"] = key
            cleaned = clean_time(it.get("pubDate", ""))
            if cleaned and (not newest_iso or cleaned > newest_iso):
                newest_iso = cleaned
        cadence = int(s.get("expected_cadence_hours") or 24)
        coverage[key] = ("DELAYED_SOURCE" if _is_delayed(newest_iso, asof, cadence,
                                                          crawled_at)
                         else "COVERED")
        items.extend(raw)
    return items, coverage


def _write_coverage(asof: date, cov: dict[str, str], records: list[dict],
                    crawled_at: str) -> None:
    """Append-only keep-FIRST on (asof, source_key) state ledger (§7). NOT a
    second event database: no event_id, no item_id, no title/url, never joined
    as events. Non-fatal — a write failure degrades the ledger, never the build."""
    try:
        import pandas as pd
        by_source: dict[str, list[dict]] = {}
        for r in records:
            by_source.setdefault(r.get("source", ""), []).append(r)
        src_by_key = {s["key"]: s for s in sources()}
        rows = []
        for key, state in cov.items():
            recs = by_source.get(key, [])
            newest = max((r.get("seendate") or "" for r in recs), default="")
            spec = src_by_key.get(key, {})
            rows.append({
                "asof": asof.isoformat(),
                "source_key": key,
                "coverage_state": state,
                "rights_state": spec.get("rights_state", "UNVERIFIED_EXCLUDED"),
                "n_items": len(recs),
                "newest_seendate": newest,
                "fetch_clock_utc": crawled_at,
                "detail": "" if state == "COVERED" else spec.get("detail", ""),
            })
        new_df = pd.DataFrame(rows, columns=list(_COVERAGE_COLUMNS))
        path = _coverage_path()
        if path.exists():
            existing = pd.read_parquet(path).reindex(columns=list(_COVERAGE_COLUMNS))
            merged = pd.concat([existing, new_df], ignore_index=True)
        else:
            merged = new_df
        merged = merged.drop_duplicates(subset=["asof", "source_key"], keep="first")
        merged.to_parquet(path, index=False)
    except Exception as e:  # noqa: BLE001
        log.warning("europe_news_intel: coverage ledger write failed (%s) — continuing", e)


# --------------------------------------------------------------------------- #
# ingest boundary (the ONLY place a clock may be read)
# --------------------------------------------------------------------------- #
def ingest(asof: date, crawled_at: str | None = None) -> dict | None:
    """asof is REQUIRED and positional — no `asof or date.today()` default.
    crawled_at defaults to datetime.now(timezone.utc).isoformat() AT THIS
    BOUNDARY only (mirrors engine/china_news_intel.py:786). Returns a summary
    dict, or None ONLY on an unexpected internal failure (logged, never
    raised)."""
    cfg = _cfg()
    if not cfg.get("enabled", False):
        return None
    try:
        import pandas as pd
        ts = crawled_at or datetime.now(timezone.utc).isoformat()
        raw, cov = fetch_all(cfg, asof, ts)
        records = build_records(raw, ts, asof, cov)
        qbus_rows = build_qbus_rows(records, raw, ts)

        # item_id is recovered for the desk artifact by re-normalizing the SAME
        # qbus rows (pure) — not by re-reading the parquet (§6.3).
        try:
            from engine.qbus import normalize_row
            for rec, qrow in zip(records, qbus_rows):
                rec["item_id"] = normalize_row(qrow).get("item_id", "")
        except Exception as e:  # noqa: BLE001
            log.warning("europe_news_intel: item_id recovery failed (%s)", e)

        path = _events_path()
        existing = pd.read_parquet(path) if path.exists() else None
        before = 0 if existing is None else len(existing)
        merged = accrue(existing, records)
        merged.to_parquet(path, index=False)
        n_new = len(merged) - before

        # Emit to the unified qbus item store — best-effort, never fatal.
        n_qbus = 0
        if records:
            try:
                from engine import qbus
                qbus.append_items(qbus_rows, assign_keys=True)
                n_qbus = len(qbus_rows)
            except Exception as e:  # noqa: BLE001
                log.warning("europe_news_intel: qbus emit failed (%s) — continuing", e)

        _write_coverage(asof, cov, records, ts)

        bad = {k: v for k, v in cov.items() if v != "COVERED"}
        degraded_reason = ("; ".join(f"{k}={v}" for k, v in sorted(bad.items()))
                           if bad else None)

        log.info("europe_news_intel: %d raw -> %d new (%d total, %d->qbus) coverage=%s",
                 len(raw), n_new, int(len(merged)), n_qbus, cov)
        return {"schema": SCHEMA, "is_context_only": True, "region": REGION,
                "asof": asof.isoformat(), "n_raw": len(raw), "n_gated": len(records),
                "n_new": n_new, "n_total": int(len(merged)), "n_qbus": n_qbus,
                "coverage": cov, "degraded_reason": degraded_reason}
    except Exception as e:  # noqa: BLE001
        log.error("europe_news_intel ingest failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# read (no rendering; for the LATER ui packet)
# --------------------------------------------------------------------------- #
def read_events(asof: date | None = None):
    """The accrued desk artifact as a DataFrame, or None. Never raises."""
    try:
        import pandas as pd
        path = _events_path()
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        if asof is not None:
            df = df[df["asof"] <= asof.isoformat()]
        return df
    except Exception as e:  # noqa: BLE001
        log.error("europe_news_intel.read_events failed (%s)", e)
        return None
