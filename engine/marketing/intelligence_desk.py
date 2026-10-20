"""Persistent, evidence-first story packets for the real-time Intelligence Desk.

The press fastlane is an arrival rail. This module turns those arrivals into a
durable newsroom view:

    filtered item -> story packet -> cross-tick merge -> live/intelligence.json

It deliberately does not publish to X. Drafts are review candidates, every
source remains attached, and a score never appears in the public artifact.
SQLite state is host-local and gitignored; the exported JSON is an atomic,
display-tier snapshot served through the registered-user live boundary.

Import closure is stdlib-only so the 75-second daemon and the thin marketing CI
lane can always import it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from engine.marketing import intelligence_history


PACKET_SCHEMA = "intelligence.story_packet/v1"
DESK_SCHEMA = "intelligence.desk/v1"
ACCEPTANCE_SCHEMA = "intelligence.acceptance_receipt/v1"

DEFAULT_DB_PATHS: tuple[str, ...] = (
    "/var/lib/macro-live/state/intelligence/intelligence.db",
    "data/marketing/press/intelligence.db",
)
DEFAULT_SNAPSHOT_PATHS: tuple[str, ...] = (
    "/var/lib/macro-live/public/live/intelligence.json",
    "data/marketing/press/intelligence.json",
)

# V2 honesty defaults. Every one is overridable from
# config/press_sources.yml -> wire.intelligence; the code defaults exist so a
# config-less checkout (and every existing test) behaves exactly as before.
DEFAULT_MARKET_STALE_MIN = 30.0
DEFAULT_TIMELINE_MAX = 12
DEFAULT_PACE_CFG: dict[str, float] = {
    "rising_recent_min": 20.0,
    "rising_sources_60m": 2.0,
    "cooling_h": 6.0,
}
# A story is "New" only while it is both single-sourced and this young.
_NEW_STORY_MAX_MIN = 60.0
# How far ahead of the tick clock an evidence stamp may sit and still count as
# evidence for the pace recompute. See `_recompute_pace`.
_FUTURE_STAMP_TOLERANCE = timedelta(minutes=5)

_WS_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_EVENT_LANES = {
    "macro_print": "macro",
    "policy": "policy",
    "geopolitical": "policy",
    "company_news": "companies",
    "earnings": "companies",
    "none": "markets",
}
_LANE_LABELS = {
    "markets": ("Markets", "市场"),
    "macro": ("Macro", "宏观"),
    "policy": ("Policy", "政策"),
    "companies": ("Companies", "公司"),
}
_WHY = {
    "macro_print": (
        "A fresh macro input that can change the rate and growth narrative.",
        "新的宏观数据可能改变利率与增长叙事。",
    ),
    "policy": (
        "A policy development with potential market or business consequences.",
        "这项政策进展可能影响市场或企业。",
    ),
    "geopolitical": (
        "A geopolitical development where confirmation and market follow-through matter.",
        "地缘事件仍需关注后续确认与市场反应。",
    ),
    "company_news": (
        "A company-specific development that may change the operating narrative.",
        "公司层面的新进展可能改变其经营叙事。",
    ),
    "earnings": (
        "A new company result or outlook update.",
        "新的公司业绩或指引更新。",
    ),
    "none": (
        "A developing market story worth keeping on the desk.",
        "值得持续跟踪的市场动态。",
    ),
}
# The SAME display words news.html already maps for `stage`. A timeline label is
# public copy, so it may never carry the raw slug.
_STAGE_WORDS = {
    "high_impact": ("High impact", "高影响"),
    "confirmed": ("Confirmed", "已确认"),
    "developing": ("Developing", "发展中"),
}


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return _utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _utc(dt)


def _clean(value: object, cap: int) -> str:
    return _WS_RE.sub(" ", str(value or "")).strip()[:cap]


def _story_id(scored: dict, story: dict | None) -> str:
    sid = _clean((story or {}).get("story_id"), 96)
    if sid:
        return sid
    basis = "|".join((
        _clean(scored.get("truth_status_id"), 120),
        _clean(scored.get("url"), 500),
        _clean(scored.get("headline"), 300).lower(),
    ))
    return "intel_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:20]


def _source_key(source: dict) -> str:
    url = str(source.get("url") or "")
    try:
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        host = ""
    return (host or str(source.get("name") or "").lower().lstrip("@")
            or str(source.get("event_id") or ""))


def _plain_brief(scored: dict) -> str:
    headline = _clean(scored.get("headline"), 320)
    body = _clean(scored.get("body_snippet"), 520)
    if not body or body.lower() == headline.lower():
        return headline
    return body


def _evidence_word(*, verified: bool, source_count: int) -> str:
    """The `context.evidence` chip for a story with this much backing.

    ONE definition, used at build time AND re-applied by `_merge_packets`: the
    merge recomputes `source_count` and `stage` from the union of evidence, and a
    chip left at whatever the last-arriving item alone could see contradicted
    them. That is not hypothetical on the V2 path — the claim registry aliases
    items the corroboration ledger never paired (a Truth post keys on
    `truth:<status_id>`, a late arrival falls outside the ledger's window), so a
    genuine two-source story served "Confirmed", "2 sources", "X joined
    coverage" and "Single report" on the same card.
    """
    if verified:
        return "Primary source"
    return "Multiple reports" if int(source_count or 0) >= 2 else "Single report"


def _context(scored: dict, story: dict, source_tier: int,
             *, source_count: int = 0) -> dict:
    source_count = max(
        int(source_count or 0),
        int(story.get("source_count", 0) or 0),
        int(story.get("sources_15m", 0) or 0),
        1,
    )
    evidence = _evidence_word(
        verified=str(scored.get("corroboration_class") or "") == "direct-quote",
        source_count=source_count,
    )

    # Build-time pace is a seed only: `IntelligenceStore.snapshot` recomputes it
    # from the story's own evidence timestamps for EVERY served packet, so a
    # story that was "Rising" two days ago is never still served as Rising.
    recent = int(story.get("sources_15m", 0) or 0)
    pace = "Rising" if recent >= 2 else ("New" if story.get("is_new") else "Active")
    source_quality = {
        1: "Primary / top-tier",
        2: "Established press",
        3: "Aggregator",
    }.get(source_tier, "Unrated source")
    return {"evidence": evidence, "pace": pace, "source_quality": source_quality}


def _market_context(
    scored: dict,
    quotes_store: dict | None,
    *,
    now: datetime,
    tape_cfg: dict | None,
) -> dict | None:
    if not isinstance(quotes_store, dict):
        return None
    try:
        from engine.marketing.tape_stamp import compute_stamp  # noqa: PLC0415
        hit = compute_stamp(scored, quotes_store, now=now, cfg=tape_cfg or {})
    except Exception:  # noqa: BLE001
        return None
    if not hit.get("stamp"):
        return None
    return {
        "label": str(hit["stamp"]),
        "symbol": hit.get("symbol"),
        "move_pct": hit.get("move_pct"),
        # This is a session move from the quote store, never a causal
        # "since the headline" claim.
        "basis": "session vs prior close",
        "as_of": _iso(now),
    }


def _draft(text: object, event_id: str, source_url: str, *,
           now: datetime, origin: str = "wire") -> dict | None:
    """One review candidate. `shape` is its CANONICAL slot on the story.

    `_merge_packets` keeps at most one draft per shape, so a re-arriving draft
    whose text drifted (a tape stamp attached late, a recomposed body) REPLACES
    its shape-mate instead of accreting a near-duplicate in the review queue.
    """
    candidate = _clean(text, 700)
    if not candidate:
        return None
    # A structured tape suffix is useful context but source URLs do not belong
    # inside the draft body unless the copywriter explicitly added one.
    candidate = _URL_RE.sub("", candidate).strip()
    if not candidate:
        return None
    fits_x = len(candidate) <= 280
    return {
        "id": "draft_" + hashlib.sha1(
            f"{event_id}|{candidate}".encode("utf-8")
        ).hexdigest()[:16],
        "shape": "wire" if fits_x else "long_post",
        "text": candidate,
        "status": "review" if fits_x else "needs_edit",
        "characters": len(candidate),
        "requires_review": True,
        "source_url": source_url,
        "origin": origin,
        "updated_at": _iso(now),
    }


def build_story_packet(
    scored: dict,
    *,
    story: dict | None,
    now: datetime,
    corr_sources: Iterable[str] = (),
    draft_text: object = "",
    quotes_store: dict | None = None,
    tape_cfg: dict | None = None,
) -> dict:
    """Build one public-safe story packet from a scored, garbage-cleared item.

    `salience` is used only to choose a broad impact band; neither it nor any
    feature component is copied into the returned packet.
    """
    now = _utc(now)
    story = dict(story or {})
    event_id = _clean(scored.get("id"), 160)
    sid = _story_id(scored, story)
    event_class = _clean(scored.get("event_class"), 40) or "none"
    lane = _EVENT_LANES.get(event_class, "markets")
    label_en, label_zh = _LANE_LABELS[lane]
    headline = _clean(scored.get("headline"), 320)
    source_name = _clean(
        scored.get("source_name") or scored.get("source"), 120
    ) or "Unknown source"
    source_url = _clean(scored.get("url"), 900)
    published_at = (
        _clean(scored.get("published_at"), 40)
        or _clean(story.get("first_seen"), 40)
        or _iso(now)
    )

    try:
        from engine import qkernel  # noqa: PLC0415
        source_tier = qkernel.source_tier(
            (urlsplit(source_url).hostname or "") if source_url else "",
            str(scored.get("source") or source_name),
        )
    except Exception:  # noqa: BLE001
        source_tier = 0

    corr_keys = {str(s) for s in corr_sources if str(s)}
    source_count = max(
        len(corr_keys),
        int(story.get("source_count", 0) or 0),
        1,
    )
    verified = str(scored.get("corroboration_class") or "") == "direct-quote"
    confirmed = verified or source_count >= 2
    try:
        high_impact = float(scored.get("salience", 0.0) or 0.0) >= 70.0
    except (TypeError, ValueError):
        high_impact = False
    stage = "high_impact" if confirmed and high_impact else (
        "confirmed" if confirmed else "developing"
    )

    tickers: list[str] = []
    matched = scored.get("matched")
    if isinstance(matched, dict):
        for ticker in matched.get("tickers") or []:
            token = _clean(ticker, 16).upper().lstrip("$")
            if token and token not in tickers:
                tickers.append(token)

    draft = _draft(draft_text, event_id, source_url, now=now)
    routes = ["wire"]
    if confirmed:
        routes.append("analysis")
    if stage == "high_impact":
        routes.append("thread")

    first_seen = _clean(story.get("first_seen"), 40) or published_at
    updated_at = _clean(story.get("last_seen"), 40) or _iso(now)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "id": sid,
        "stage": stage,
        # MACHINE field: the admin approve flow routes an approved draft to an
        # account by event_class. It is a coarse categorical lane name, not a
        # score, and the news.html client never renders it.
        "event_class": event_class,
        "lane": lane,
        "lane_label_en": label_en,
        "lane_label_zh": label_zh,
        "headline": headline,
        "brief": _plain_brief(scored),
        "why_it_matters_en": _WHY.get(event_class, _WHY["none"])[0],
        "why_it_matters_zh": _WHY.get(event_class, _WHY["none"])[1],
        "first_seen": first_seen,
        "updated_at": updated_at,
        "source_count": source_count,
        "tickers": tickers[:8],
        "context": _context(scored, story, source_tier,
                            source_count=source_count),
        "evidence": [{
            "event_id": event_id,
            "name": source_name,
            "url": source_url,
            "published_at": published_at,
            "headline": headline,
        }],
        "market": _market_context(
            scored, quotes_store, now=now, tape_cfg=tape_cfg
        ),
        "drafts": [draft] if draft else [],
        "content_routes": routes,
        "stance": (
            "Review the draft" if draft and draft["status"] == "review"
            else "Read the evidence" if confirmed
            else "Watch for confirmation"
        ),
        # Merge hints are broad categorical facts, not public scores.
        "_verified": verified,
        "_impact_band": "high" if high_impact else "normal",
    }
    return packet


def _timeline_event(kind: str, ts: str, *, source_name: str = "",
                    stage: str = "") -> dict:
    """One public, bilingual timeline row. Fixed templates — never a raw slug.

    Source names stay Latin in both languages (a wire's masthead is its name in
    any language); everything around them is house copy.
    """
    name = _clean(source_name, 60)
    if kind == "new_source":
        label_en = f"{name} joined coverage" if name else "A new source joined coverage"
        label_zh = f"新增来源：{name}" if name else "新增来源"
    elif kind == "stage":
        word_en, word_zh = _STAGE_WORDS.get(
            str(stage), _STAGE_WORDS["developing"]
        )
        label_en = f"Stage: {word_en}"
        label_zh = f"阶段：{word_zh}"
    else:
        kind = "first_report"
        label_en = f"First report: {name}" if name else "First report"
        label_zh = f"首次报道：{name}" if name else "首次报道"
    row = {"ts": ts, "kind": kind, "label_en": label_en, "label_zh": label_zh}
    if name and kind in ("first_report", "new_source"):
        row["source_name"] = name
    return row


def _coherent_zh(merged: dict, old: dict, new: dict, field: str) -> None:
    """Keep a zh twin only while its English original is still the served one.

    Incoming wins when present. When the merged EN text moved on without a fresh
    translation, the stale zh is DROPPED: an out-of-date Chinese headline next to
    a newer English one is a worse failure than the honest 英文原文 fallback.
    """
    zh_field = f"{field}_zh"
    current = _clean(merged.get(field), 700)
    for candidate in (new, old):
        zh = _clean(candidate.get(zh_field), 700)
        if zh and _clean(candidate.get(field), 700) == current:
            merged[zh_field] = zh
            return
    merged.pop(zh_field, None)


def _merge_why(merged: dict, old: dict, new: dict) -> None:
    """Resolve `why_it_matters` across a merge. A phrased line outranks a canned one.

    Every packet ``build_story_packet`` produces carries the CANNED per-class
    sentence, so a story phrased on tick 1 would have that phrasing overwritten
    on tick 2 by the very next arrival — the LLM pass is cached per headline and
    deliberately does not pay again. The `_why_phrased` marker (internal, never
    served) is what survives in the stored row and defends the phrasing:

        canned  vs phrased(stored)  -> the stored phrasing stands
        phrased vs canned(stored)   -> the phrasing replaces the canned line
        phrased vs phrased(stored)  -> the incoming phrasing wins

    The zh twin travels WITH its English original: it is taken from whichever
    side supplied the winning line, and when that side has none the canned
    per-class zh sentence is used. That sentence is generically true for the
    event class, which makes it an honest fallback beside a phrased English
    line — a Chinese sentence translated from some OTHER English would not be.
    """
    old_phrased = bool(old.get("_why_phrased"))
    new_phrased = bool(new.get("_why_phrased"))
    old_en = _clean(old.get("why_it_matters_en"), 700)
    new_en = _clean(new.get("why_it_matters_en"), 700)

    if old_phrased and not new_phrased and old_en:
        winner, why_en = old, old_en
    elif new_en:
        winner, why_en = new, new_en
    elif old_en:
        winner, why_en = old, old_en
    else:
        return

    merged["why_it_matters_en"] = why_en
    zh = _clean(winner.get("why_it_matters_zh"), 700)
    if not zh:
        event_class = str(merged.get("event_class") or "none")
        zh = _WHY.get(event_class, _WHY["none"])[1]
    merged["why_it_matters_zh"] = zh
    if old_phrased or new_phrased:
        merged["_why_phrased"] = True
    else:
        merged.pop("_why_phrased", None)


def _merge_packets(old: dict | None, new: dict, *, now: datetime | None = None,
                   timeline_max: int = DEFAULT_TIMELINE_MAX) -> dict:
    stamp = (
        _utc(now) if isinstance(now, datetime)
        else (_parse_iso(new.get("updated_at"))
              or datetime.now(timezone.utc))
    )
    cap = max(1, int(timeline_max or DEFAULT_TIMELINE_MAX))

    if not isinstance(old, dict):
        merged = dict(new)
        rows = [r for r in merged.get("evidence") or [] if isinstance(r, dict)]
        first_name = str(rows[0].get("name") or "") if rows else ""
        # Normalized, never the raw upstream stamp: `first_seen` arrives in
        # whatever offset form its producer used and this is public payload.
        first_ts = _iso(_parse_iso(merged.get("first_seen")) or stamp)
        carried = [
            row for row in (merged.get("timeline") or []) if isinstance(row, dict)
        ]
        merged["timeline"] = (carried or [
            _timeline_event("first_report", first_ts, source_name=first_name)
        ])[:cap]
        return merged

    merged = dict(old)
    merged.update({
        key: value for key, value in new.items()
        if value not in (None, "", [], {})
    })

    old_first = _parse_iso(old.get("first_seen"))
    new_first = _parse_iso(new.get("first_seen"))
    if old_first and new_first:
        merged["first_seen"] = _iso(min(old_first, new_first))
    elif old.get("first_seen"):
        merged["first_seen"] = old["first_seen"]

    evidence: dict[str, dict] = {}
    for row in list(old.get("evidence") or []) + list(new.get("evidence") or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("event_id") or row.get("url") or _source_key(row))
        if key:
            evidence[key] = row
    merged["evidence"] = sorted(
        evidence.values(),
        key=lambda row: str(row.get("published_at") or ""),
        reverse=True,
    )[:24]

    distinct_sources = {
        _source_key(row) for row in merged["evidence"] if _source_key(row)
    }
    merged["source_count"] = max(
        int(old.get("source_count", 0) or 0),
        int(new.get("source_count", 0) or 0),
        len(distinct_sources),
        1,
    )

    # CANONICAL DRAFTS: one slot per shape. Keying by draft id let tape-stamp
    # drift accrete five near-identical wire drafts on one story and noise the
    # review queue; keying by shape means a drifted redraft replaces its
    # shape-mate. Unknown/future shapes ("analysis", an LLM shape) get their own
    # slot generically — this dict is never a whitelist.
    #
    # Review N8: within a slot, a stored LLM phrasing OUTRANKS an incoming
    # deterministic draft while the story's headline is unchanged — the LLM pass
    # is budget-capped and cache-keyed, so most ticks re-arrive with only the
    # deterministic wire text, and letting that evict the phrased copy silently
    # reverted the story every quiet tick. A moved headline releases the slot:
    # stale phrasing must not outlive the story text it phrased.
    headline_moved = _clean(old.get("headline"), 320) != _clean(
        new.get("headline"), 320)
    drafts: dict[str, dict] = {}
    for row in list(old.get("drafts") or []) + list(new.get("drafts") or []):
        if not isinstance(row, dict) or not row.get("id"):
            continue
        slot = str(row.get("shape") or "wire")
        held = drafts.get(slot)
        if (held is not None and not headline_moved
                and str(held.get("origin") or "") == "llm"
                and str(row.get("origin") or "") != "llm"):
            continue
        drafts[slot] = row
    merged["drafts"] = list(drafts.values())[:6]
    # A market stamp is a fresh, threshold-gated session observation. Never
    # carry yesterday's/last-tick's stamp forward when the current quote is
    # quiet or stale.
    merged["market"] = new.get("market")

    verified = bool(old.get("_verified")) or bool(new.get("_verified"))
    high = old.get("_impact_band") == "high" or new.get("_impact_band") == "high"
    confirmed = verified or int(merged["source_count"]) >= 2
    merged["_verified"] = verified
    merged["_impact_band"] = "high" if high else "normal"
    merged["stage"] = "high_impact" if confirmed and high else (
        "confirmed" if confirmed else "developing"
    )
    routes = ["wire"]
    if confirmed:
        routes.append("analysis")
    if merged["stage"] == "high_impact":
        routes.append("thread")
    merged["content_routes"] = routes
    # The evidence chip is part of the same verdict as `stage` and
    # `source_count`, so it is re-derived from the merged totals rather than
    # inherited from the incoming packet, which only ever saw its own item.
    # (`pace` is deliberately NOT touched here — `_served_packet` recomputes it
    # from evidence timestamps at snapshot time.)
    merged_context = dict(merged.get("context") or {})
    merged_context["evidence"] = _evidence_word(
        verified=verified, source_count=int(merged["source_count"])
    )
    merged["context"] = merged_context
    if any(d.get("status") == "review" for d in merged["drafts"]):
        merged["stance"] = "Review the draft"
    elif confirmed:
        merged["stance"] = "Read the evidence"
    else:
        merged["stance"] = "Watch for confirmation"

    # TIMELINE: what changed on this story, in public words. Deterministic —
    # derived from the diff between the stored packet and the merged one, never
    # from a score. Newest first, bounded.
    events: list[dict] = []
    old_stage = str(old.get("stage") or "")
    if old_stage and old_stage != str(merged["stage"]):
        events.append(_timeline_event(
            "stage", _iso(stamp), stage=str(merged["stage"])
        ))
    old_keys = {
        _source_key(row) for row in (old.get("evidence") or [])
        if isinstance(row, dict)
    }
    old_keys.discard("")
    fresh: dict[str, str] = {}
    for row in merged["evidence"]:
        key = _source_key(row)
        if key and key not in old_keys and key not in fresh:
            fresh[key] = str(row.get("name") or "")
    for key in sorted(fresh):
        events.append(_timeline_event(
            "new_source", _iso(stamp), source_name=fresh[key]
        ))
    history = [row for row in (old.get("timeline") or []) if isinstance(row, dict)]
    if not history:
        # A v1 row predates the timeline; seed it from what the story already knows.
        first_rows = [r for r in merged["evidence"] if isinstance(r, dict)]
        history = [_timeline_event(
            "first_report",
            _iso(_parse_iso(merged.get("first_seen")) or stamp),
            source_name=str(first_rows[-1].get("name") or "") if first_rows else "",
        )]
    merged["timeline"] = (events + history)[:cap]

    # zh twins last: they must agree with the EN text the merge just settled on.
    _coherent_zh(merged, old, new, "headline")
    _coherent_zh(merged, old, new, "brief")
    _merge_why(merged, old, new)
    return merged


def build_research_packet(item: dict, *, now: datetime) -> dict:
    """An attributed source report, isolated from editorial/publication policy."""
    required = ("id", "feed_id", "source_item_id", "source_revision", "headline", "url")
    if any(not isinstance(item.get(k), str) or not item[k] for k in required):
        raise ValueError("invalid research source item")
    published = _parse_iso(item.get("published_at"))
    updated = _parse_iso(item.get("source_updated_at"))
    packet = {
        "schema": PACKET_SCHEMA, "id": item["id"], "purpose": "research",
        "stage": "reported", "status": "reported", "source_count": 1,
        "headline": item["headline"], "brief": item.get("summary", ""),
        "url": item["url"], "canonical_url": item.get("canonical_url", ""),
        "feed_id": item["feed_id"], "source_item_id": item["source_item_id"],
        "source_revision": item["source_revision"],
        "published_at": _iso(published) if published else "",
        "source_updated_at": _iso(updated) if updated else "",
        "provider_indexed_at": item.get("provider_indexed_at", ""),
        "publisher_country": item.get("publisher_country", ""),
        "timestamp_quality": item.get("timestamp_quality", "published" if published else "unknown"),
        "first_seen": _iso(now), "updated_at": _iso(now),
        "accepted_revision_at": _iso(now),
        "source_name": item.get("source_name", ""),
        "source_type": item.get("source_type", "official"),
        "category": item.get("category", "economy"),
        "language": item.get("language", "en"),
        "coverage_regions": item.get("coverage_regions", []),
        "attribution": item.get("attribution", ""),
        "source_use_url": item.get("source_use_url", ""),
        "content_use": item.get("content_use", "attributed_headline_link"),
        "drafts": [], "content_routes": [], "market": None, "tickers": [],
        "context": {"evidence": "Source report", "pace": "New"},
        "evidence": [{"name": item.get("source_name", ""), "url": item["url"],
                      "headline": item["headline"], "published_at": _iso(published) if published else "",
                      "source_item_id": item["source_item_id"], "source_revision": item["source_revision"]}],
        "timeline": [{"kind": "first_report", "at": _iso(now), "source_name": item.get("source_name", "")}],
    }
    return packet


def _merge_research_packet(old: dict | None, new: dict, *, now: datetime,
                           timeline_max: int) -> dict:
    if old and (old.get("purpose") != "research" or old.get("feed_id") != new.get("feed_id")
                or old.get("source_item_id") != new.get("source_item_id")):
        raise ValueError("research identity collision")
    if old and old.get("source_revision") == new.get("source_revision"):
        return dict(old)
    if old:
        previous_time = _parse_iso(old.get("source_updated_at"))
        incoming_time = _parse_iso(new.get("source_updated_at"))
        if previous_time and incoming_time and incoming_time < previous_time:
            return dict(old)  # an explicitly superseded source version is reconciled
        if previous_time and incoming_time and incoming_time == previous_time:
            raise ValueError("ambiguous source revision order")
    merged = dict(new)
    if old:
        merged["first_seen"] = old.get("first_seen") or new["first_seen"]
        # Revisions are historical versions of ONE source, never corroboration.
        history = [{"revision": old.get("source_revision"), "headline": old.get("headline"),
                    "accepted_at": old.get("accepted_revision_at"), "url": old.get("url")}]
        merged["revision_history"] = (history + list(old.get("revision_history") or []))[:12]
        merged["status"] = "amended"
        merged["timeline"] = ([{"kind": "amendment", "at": _iso(now),
                                "source_name": new.get("source_name", "")}]
                              + list(old.get("timeline") or []))[:max(1, timeline_max)]
    merged.update(purpose="research", stage="reported", drafts=[], content_routes=[],
                  market=None, source_count=1, accepted_revision_at=_iso(now), updated_at=_iso(now))
    return merged


def _accepted_source_revision(packet: dict) -> str:
    if packet.get("source_revision"):
        return str(packet["source_revision"])
    # Only source reporting, not LLM/context/export clocks, advances intake age.
    evidence = [{k: row.get(k) for k in ("event_id", "url", "headline", "published_at")}
                for row in packet.get("evidence") or [] if isinstance(row, dict)]
    basis = [packet.get("headline"), packet.get("published_at"), evidence]
    return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _public_packet(packet: dict) -> dict:
    return {key: value for key, value in packet.items() if not key.startswith("_")}


def _pace_cfg(cfg: object) -> dict[str, float]:
    out = dict(DEFAULT_PACE_CFG)
    if isinstance(cfg, dict):
        for key in list(out):
            try:
                out[key] = float(cfg.get(key, out[key]))
            except (TypeError, ValueError):
                continue
    return out


def _recompute_pace(packet: dict, *, now: datetime, pace_cfg: dict) -> str:
    """The story's pace AS OF NOW, from its own evidence timestamps.

    A packet's pace was frozen at build time, so a story that stopped moving two
    days ago kept serving "Rising" forever. The desk states what is true when the
    reader loads it, which is also the only way `Cooling` can ever be said.
    """
    rows = [row for row in packet.get("evidence") or [] if isinstance(row, dict)]
    stamps = [
        ts for ts in (_parse_iso(row.get("published_at")) for row in rows)
        if ts is not None
        # A FUTURE STAMP WOULD FREEZE THIS STORY AT "Rising" FOREVER. `_age_min`
        # floors at 0, so one clock-skewed or embargo-dated publisher pins
        # `newest_age` at 0: the Rising test always passes and the Cooling test
        # (`newest_age >= cooling_h * 60`) can never pass again, for the whole 72h
        # the row is retained. Snapshot-time honesty is the entire point of this
        # function, so a stamp the clock says has not happened yet is not evidence
        # about how fast the story is moving. The tolerance absorbs ordinary
        # host/publisher clock drift rather than treating it as a fault.
        and ts <= now + _FUTURE_STAMP_TOLERANCE
    ]
    if not stamps:
        fallback = (_parse_iso(packet.get("updated_at"))
                    or _parse_iso(packet.get("first_seen")))
        if fallback is None:
            return str((packet.get("context") or {}).get("pace") or "Active")
        stamps = [fallback]

    def _age_min(ts: datetime) -> float:
        return max(0.0, (now - ts).total_seconds() / 60.0)

    newest_age = min(_age_min(ts) for ts in stamps)
    within_60m = sum(1 for ts in stamps if _age_min(ts) <= 60.0)
    first = _parse_iso(packet.get("first_seen")) or max(stamps)
    story_age = _age_min(first)

    if max(len(rows), 1) <= 1 and story_age < _NEW_STORY_MAX_MIN:
        return "New"
    if (newest_age <= pace_cfg["rising_recent_min"]
            and within_60m >= pace_cfg["rising_sources_60m"]):
        return "Rising"
    if newest_age >= pace_cfg["cooling_h"] * 60.0:
        return "Cooling"
    return "Active"


def _served_packet(packet: dict, *, now: datetime, pace_cfg: dict,
                   market_stale_min: float) -> dict:
    """The public view of a stored packet, recomputed at SERVE time."""
    served = _public_packet(packet)
    context = dict(served.get("context") or {})
    context["pace"] = _recompute_pace(packet, now=now, pace_cfg=pace_cfg)
    served["context"] = context

    market = served.get("market")
    if isinstance(market, dict):
        as_of = _parse_iso(market.get("as_of"))
        # An unstamped block cannot be proven fresh, so it is served as null too:
        # a market chip is a claim about RIGHT NOW or it is nothing.
        if as_of is None or (now - as_of) > timedelta(
            minutes=max(0.0, market_stale_min)
        ):
            served["market"] = None
    return served


class IntelligenceStore:
    """Small SQLite story store with bounded retention and atomic JSON export."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=5.0)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS stories (
                story_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                packet_json TEXT NOT NULL
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS stories_updated_idx ON stories(updated_at DESC)"
        )
        self.db.execute("CREATE TABLE IF NOT EXISTS desk_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()

    def set_source_health(self, rows: list[dict]) -> None:
        with self.db:
            self.db.execute("INSERT INTO desk_metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("source_health", json.dumps(rows, ensure_ascii=False)))

    def source_health(self) -> list:
        row = self.db.execute("SELECT value FROM desk_metadata WHERE key='source_health'").fetchone()
        try:
            value = json.loads(row[0]) if row else []
        except (TypeError, ValueError):
            return []
        return value if isinstance(value, list) else []

    def close(self) -> None:
        self.db.close()

    def upsert(self, packets: Iterable[dict], *, now: datetime,
               timeline_max: int = DEFAULT_TIMELINE_MAX,
               acceptance_receipts: dict | None = None) -> int:
        count = 0
        submitted, receipts = {}, {}
        with self.db:
            for packet in packets:
                if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
                    continue
                sid = str(packet.get("id") or "")
                if not sid:
                    continue
                row = self.db.execute(
                    "SELECT packet_json FROM stories WHERE story_id = ?", (sid,)
                ).fetchone()
                old = None
                if row:
                    try:
                        old = json.loads(row[0])
                    except (TypeError, ValueError):
                        old = None
                if packet.get("purpose") == "research":
                    if not all(isinstance(packet.get(key), str) and packet[key]
                               for key in ("id", "feed_id", "source_revision")):
                        raise ValueError("invalid research acceptance identity")
                    submitted[sid] = {"feed_id": packet["feed_id"],
                                      "submitted_revision": packet["source_revision"]}
                    merged = _merge_research_packet(old, packet, now=now, timeline_max=timeline_max)
                else:
                    if old and old.get("purpose") == "research":
                        raise ValueError("editorial/research identity collision")
                    merged = _merge_packets(old, packet, now=now, timeline_max=timeline_max)
                    merged["updated_at"] = _iso(now)
                    changed = not old or _accepted_source_revision(old) != _accepted_source_revision(merged)
                    merged["accepted_revision_at"] = _iso(now) if changed else old.get("accepted_revision_at", "")
                if old == merged:
                    count += 1  # accepted idempotently; preserve every source clock
                    continue
                self.db.execute(
                    """
                    INSERT INTO stories(story_id, first_seen, updated_at, packet_json)
                    VALUES(?, ?, ?, ?)
                    ON CONFLICT(story_id) DO UPDATE SET
                        first_seen=excluded.first_seen,
                        updated_at=excluded.updated_at,
                        packet_json=excluded.packet_json
                    """,
                    (
                        sid,
                        str(merged.get("first_seen") or _iso(now)),
                        str(merged.get("updated_at") or _iso(now)),
                        json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
                    ),
                )
                count += 1
            # Observe the final row for each submitted identity while the batch
            # transaction is still open and before rolling retention can evict
            # an intentionally accepted row. This includes idempotent replays.
            for sid, incoming in submitted.items():
                row = self.db.execute("SELECT packet_json FROM stories WHERE story_id=?", (sid,)).fetchone()
                current = json.loads(row[0])
                accepted = intelligence_history._at(current.get("accepted_revision_at"))
                receipts[sid] = {
                    **incoming,
                    "source_revision": current["source_revision"],
                    "accepted_revision_at": _iso(accepted) if accepted and accepted <= _utc(now) else "",
                    "disposition": ("current" if current["source_revision"] == incoming["submitted_revision"]
                                    else "superseded"),
                }
        if acceptance_receipts is not None:
            acceptance_receipts.update(receipts)
        return count

    def prune(self, *, now: datetime, retention_h: float = 72.0,
              max_stories: int = 1500) -> None:
        cutoff = _iso(_utc(now) - timedelta(hours=max(1.0, retention_h)))
        with self.db:
            self.db.execute("DELETE FROM stories WHERE updated_at < ?", (cutoff,))
            self.db.execute(
                """
                DELETE FROM stories WHERE story_id IN (
                    SELECT story_id FROM stories
                    ORDER BY updated_at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (max(1, max_stories),),
            )

    def snapshot(self, *, now: datetime, active_h: float = 48.0,
                 max_items: int = 80, pace_cfg: dict | None = None,
                 market_stale_min: float = DEFAULT_MARKET_STALE_MIN,
                 confirmed_max: int = 0, research_max: int = 0) -> dict:
        now = _utc(now)
        pace = _pace_cfg(pace_cfg)
        source_health = self.source_health()
        research_scope = intelligence_history.display_scope(source_health)
        cutoff = _iso(now - timedelta(hours=max(1.0, active_h)))
        rows = self.db.execute(
            """
            SELECT packet_json FROM stories
            WHERE updated_at >= ?
            ORDER BY updated_at DESC
            """,
            (cutoff,),
        ).fetchall()
        stories: list[dict] = []
        for row in rows:
            try:
                packet = json.loads(row[0])
            except (TypeError, ValueError):
                continue
            if isinstance(packet, dict):
                if (packet.get("purpose") == "research"
                        and not intelligence_history.is_displayable(packet, research_scope)):
                    continue
                stories.append(_served_packet(
                    packet, now=now, pace_cfg=pace,
                    market_stale_min=market_stale_min,
                ))
        # Stage priority first; within each stage the latest story leads.
        #
        # confirmed_max (0 = unlimited, the historical shape): at the 2026-08-03
        # admission floors the 48 h window holds MORE confirmed stories than the
        # whole snapshot cap — Truth-mirror direct-quotes alone can fill it — so
        # unbounded stage priority silently evicted every developing story and
        # the "live" desk stopped showing the newest single-source tape at all.
        # A bounded confirmed group keeps the editorial order (impact first)
        # while guaranteeing the fold still carries the live tail. high_impact
        # is deliberately never capped: a desk with 80 genuinely high-impact
        # stories SHOULD be wall-to-wall high impact.
        ordered: list[dict] = []
        for stage in ("high_impact", "confirmed", "developing"):
            group = sorted(
                (p for p in stories if p.get("stage") == stage),
                key=lambda p: str(p.get("updated_at") or ""), reverse=True,
            )
            if stage == "confirmed" and confirmed_max > 0:
                group = group[:confirmed_max]
            ordered.extend(group)
        known_stages = {"high_impact", "confirmed", "developing"}
        ordered.extend(sorted(
            (p for p in stories if p.get("stage") not in known_stages),
            key=lambda p: str(p.get("updated_at") or ""),
            reverse=True,
        ))
        cap = max(1, min(1000, max_items))
        if research_max > 0:
            research = sorted((p for p in ordered if p.get("purpose") == "research"),
                              key=lambda p: str(p.get("accepted_revision_at") or ""), reverse=True)
            reserved = research[:min(research_max, cap)]
            chosen = {p["id"] for p in reserved}
            stories = reserved + [p for p in ordered if p["id"] not in chosen][:cap - len(reserved)]
        else:
            stories = ordered[:cap]

        source_keys: set[str] = set()
        confirmed = 0
        draft_ready = 0
        for packet in stories:
            if packet.get("stage") in ("confirmed", "high_impact"):
                confirmed += 1
            if any(
                isinstance(d, dict) and d.get("status") == "review"
                for d in packet.get("drafts") or []
            ):
                draft_ready += 1
            for source in packet.get("evidence") or []:
                if isinstance(source, dict):
                    key = _source_key(source)
                    if key:
                        source_keys.add(key)

        accepted_clocks = [_parse_iso(p.get("accepted_revision_at")) for p in stories]
        newest = max(
            (at for at in accepted_clocks if at is not None and at <= now),
            default=None,
            key=lambda value: value or datetime.min.replace(tzinfo=timezone.utc),
        )
        state = "quiet"
        if newest and (_utc(now) - newest) <= timedelta(minutes=15):
            state = "live"
        return {
            "source_health": source_health,
            "schema": DESK_SCHEMA,
            "updated_at": _iso(now),
            "health": {
                "state": state,
                "active_stories": len(stories),
                "confirmed": confirmed,
                "draft_ready": draft_ready,
                "sources_present": len(source_keys),
                "freshness_basis": "accepted_source_revision",
                "last_accepted_revision_at": _iso(newest) if newest else "",
                "last_source_published_at": max((str(p.get("published_at") or "") for p in stories), default=""),
            },
            "stories": stories,
        }

    def retained_history(self, *, now: datetime, source_health: list,
                         retention_h: float = 72.0, max_stories: int = 1500,
                         pace_cfg: dict | None = None) -> dict:
        """Project the existing retained owner rows; no new store or read writer."""
        # Match the incumbent aggregate's whole-second export clock exactly.
        now = _utc(now).replace(microsecond=0)
        retention = max(1.0, min(intelligence_history.MAX_RETENTION_HOURS, retention_h))
        cap = max(1, min(intelligence_history.MAX_STORIES, max_stories))
        cutoff = _iso(now - timedelta(hours=retention))
        rows = self.db.execute(
            """
            SELECT CASE WHEN length(CAST(packet_json AS BLOB)) <= ? THEN packet_json ELSE NULL END,
                   length(CAST(packet_json AS BLOB))
            FROM stories WHERE updated_at >= ?
            ORDER BY updated_at DESC, story_id ASC LIMIT ?
            """, (intelligence_history.MAX_BYTES, cutoff, cap),
        )
        packets, read_bytes = [], 0
        pace = _pace_cfg(pace_cfg)
        for raw, size in rows:
            read_bytes += size
            if raw is None or read_bytes > intelligence_history.MAX_BYTES:
                raise intelligence_history.HistoryArtifactError("retained read byte cap")
            try:
                packet = json.loads(raw)
            except (TypeError, ValueError):
                packet = None
            packets.append(_served_packet(packet, now=now, pace_cfg=pace,
                                          market_stale_min=DEFAULT_MARKET_STALE_MIN)
                           if isinstance(packet, dict) else None)
        projection = intelligence_history.build_projection(
            packets, source_health=source_health, as_of=now,
            retention_hours=retention, max_stories=cap,
        )
        intelligence_history.encode(projection)  # preflight before either publication
        return projection


def _first_usable_path(candidates: Iterable[str], *, root: Path) -> Path | None:
    for raw in candidates:
        path = Path(str(raw))
        if not path.is_absolute():
            path = root / path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, probe = tempfile.mkstemp(prefix=".intel-write-", dir=path.parent)
            os.close(fd)
            os.unlink(probe)
            return path
        except OSError:
            continue
    return None


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _quarantine_db(path: Path, *, now: datetime, exc: BaseException) -> None:
    """Move a broken store aside so the next open can create a fresh one.

    A corrupt (or locked-beyond-retry) SQLite file used to freeze the desk
    FOREVER behind a daemon whose logs looked healthy: every tick raised, the
    error was logged, and the snapshot stayed at whatever it last was. Renaming
    keeps the evidence on disk for a postmortem while the desk keeps running —
    the store is host-local derived state, rebuilt from the next few ticks.
    """
    stamp = _utc(now).strftime("%Y%m%dT%H%M%SZ")
    aside = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        if path.exists():
            path.replace(aside)
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
    # WAL/SHM siblings belong to the quarantined file; leaving them next to a
    # fresh database is how a "healed" store corrupts itself again on open.
    for suffix in ("-wal", "-shm"):
        side = path.with_name(path.name + suffix)
        try:
            if side.exists():
                side.replace(aside.with_name(aside.name + suffix))
        except OSError:
            try:
                side.unlink()
            except OSError:
                pass
    print(
        f"::warning title=intelligence-db-quarantined::{type(exc).__name__}: "
        f"{exc} — moved {path.name} aside as {aside.name} and recreated the store",
        flush=True,
    )


def _receipt_source_health(rows: list, previous: list, items: dict, *, now: datetime) -> tuple[list, dict]:
    """Replace proposed acceptance claims with committed owner observations."""
    prior, duplicates = {}, set()
    for row in previous:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        if row["id"] in prior:
            duplicates.add(row["id"])
        prior[row["id"]] = row
    groups: dict[str, list] = {}
    for item in items.values():
        groups.setdefault(item["feed_id"], []).append(item)
    feeds = {}
    for feed_id, group in groups.items():
        previous_at = prior.get(feed_id, {}).get("last_accepted_at") if feed_id not in duplicates else None
        clocks = [intelligence_history._at(previous_at)]
        clocks.extend(intelligence_history._at(item["accepted_revision_at"]) for item in group)
        last = max((at for at in clocks if at is not None and at <= _utc(now)), default=None)
        accepted_count = sum(item["disposition"] == "current" for item in group)
        feeds[feed_id] = {
            "accepted_item_count": accepted_count,
            "superseded_item_count": len(group) - accepted_count,
            "last_accepted_at": _iso(last) if last else "",
            "last_outcome": "accepted" if accepted_count else "unchanged",
        }
    corrected = []
    for row in rows:
        if not isinstance(row, dict):
            corrected.append(row)
            continue
        result = dict(row)
        accepted = feeds.get(row.get("id")) if isinstance(row.get("id"), str) else None
        if accepted is not None:
            result.update(last_changed_item_count=accepted["accepted_item_count"],
                          last_accepted_at=accepted["last_accepted_at"],
                          last_outcome=accepted["last_outcome"], last_acceptance_error="")
        corrected.append(result)
    return corrected, feeds


def _store_cycle(db_target: Path, packets: list[dict], *, now: datetime,
                 cfg: dict) -> tuple[dict, dict | None, dict]:
    """One full store tick: merge, prune, snapshot. Always closes the store."""
    store = IntelligenceStore(db_target)
    try:
        previous_health = store.source_health()
        receipts = {}
        store.upsert(
            packets, now=now,
            timeline_max=int(cfg.get("timeline_max", DEFAULT_TIMELINE_MAX)),
            acceptance_receipts=receipts,
        )
        supplied_health = cfg.get("source_health")
        health, feeds = _receipt_source_health(
            supplied_health if isinstance(supplied_health, list) else previous_health,
            previous_health, receipts, now=now,
        )
        receipt = {"schema": ACCEPTANCE_SCHEMA, "items": receipts, "feeds": feeds}
        if isinstance(supplied_health, list) or receipts:
            store.set_source_health(health)
        store.prune(
            now=now,
            retention_h=float(cfg.get("retention_h", 72.0)),
            max_stories=int(cfg.get("max_stories", 1500)),
        )
        # The same owner connection observes one coherent committed generation.
        # This transaction contains SELECTs only and creates no API DB access.
        store.db.execute("BEGIN")
        try:
            payload = store.snapshot(
                now=now,
                active_h=float(cfg.get("active_h", 48.0)),
                max_items=int(cfg.get("snapshot_max_items", 80)),
                pace_cfg=cfg.get("pace"),
                market_stale_min=float(
                    cfg.get("market_stale_min", DEFAULT_MARKET_STALE_MIN)
                ),
                confirmed_max=int(cfg.get("snapshot_confirmed_max", 0) or 0),
                research_max=int(cfg.get("snapshot_research_max", 0) or 0),
            )
            try:
                retained = store.retained_history(
                    now=now, source_health=payload["source_health"],
                    retention_h=float(cfg.get("retention_h", 72.0)),
                    max_stories=int(cfg.get("max_stories", 1500)), pace_cfg=cfg.get("pace"),
                )
                payload["retained_history"] = intelligence_history.descriptor(retained)
            except (ValueError, TypeError, OverflowError, RecursionError):
                # A bounded optional projection must not stall primary intake.
                # SQLite errors still reach the incumbent quarantine/retry owner.
                retained = None
                payload["retained_history"] = intelligence_history.unavailable("projection_invalid")
            return payload, retained, receipt
        finally:
            store.db.rollback()
    finally:
        try:
            store.close()
        except sqlite3.Error:
            pass


def update_intelligence_desk(
    packets: Iterable[dict],
    *,
    root: Path | str,
    now: datetime,
    cfg: dict | None = None,
    db_path: Path | str | None = None,
    snapshot_path: Path | str | None = None,
    history_path: Path | str | None = None,
    acceptance_receipt: dict | None = None,
) -> dict:
    """Merge a tick and publish a new desk snapshot. Returns the payload.

    Explicit paths are the test/development seam. Production chooses the first
    writable path from the configured candidates, with the gitignored repo path
    as its last fallback.

    An optional receipt dict is cleared before effects and populated only after
    successful aggregate publication. It contains actual owner acknowledgements
    for the submitted research IDs, observed before retention pruning; it is
    never included in either published artifact.
    """
    if acceptance_receipt is not None:
        if not isinstance(acceptance_receipt, dict):
            raise TypeError("acceptance_receipt must be a dict")
        acceptance_receipt.clear()
    root = Path(root)
    cfg = cfg or {}
    db_candidates = cfg.get("db_paths") or DEFAULT_DB_PATHS
    sink_candidates = cfg.get("snapshot_paths") or DEFAULT_SNAPSHOT_PATHS
    db_target = Path(db_path) if db_path is not None else _first_usable_path(
        db_candidates, root=root
    )
    sink_target = (
        Path(snapshot_path) if snapshot_path is not None
        else _first_usable_path(sink_candidates, root=root)
    )
    if db_target is None or sink_target is None:
        raise OSError("no writable Intelligence Desk database/snapshot path")

    # Materialised ONCE: the self-heal retry below re-reads this list, and a
    # generator would hand the second attempt an empty tick.
    batch = [p for p in packets]
    try:
        payload, retained, receipt = _store_cycle(db_target, batch, now=now, cfg=cfg)
    except sqlite3.DatabaseError as exc:
        _quarantine_db(db_target, now=now, exc=exc)
        # Exactly ONE retry. A second failure is not a corrupt file — it is a
        # broken host (read-only mount, full disk) — and it must reach the
        # daemon's log rather than be swallowed into a silently empty desk.
        payload, retained, receipt = _store_cycle(db_target, batch, now=now, cfg=cfg)
    if retained is not None:
        try:
            # Explicit DB tests stay beside that DB, even if production config
            # was supplied. A private history override remains explicit.
            configured = (history_path if history_path is not None else
                          db_target.with_name(intelligence_history.FILENAME) if db_path is not None else
                          cfg.get("history_snapshot_path") or db_target.with_name(intelligence_history.FILENAME))
            history_target = Path(configured)
            if not history_target.is_absolute():
                history_target = root / history_target
            resolved = history_target.resolve()
            protected = (db_target.resolve(), sink_target.resolve())
            public_roots = (Path("/var/lib/macro-live/public"), root.resolve() / "site", root.resolve() / "public")
            if (resolved in protected or any(resolved.is_relative_to(base) for base in public_roots)
                    or any(history_target.exists() and target.exists()
                           and os.path.samefile(history_target, target) for target in (db_target, sink_target))):
                raise ValueError("history path is not private")
            intelligence_history.atomic_write(history_target, retained)
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            # Publishing this descriptor invalidates any older private artifact.
            # A later main-file failure also fails closed through the revision
            # handshake instead of pretending the two files commit atomically.
            payload["retained_history"] = intelligence_history.unavailable("publish_failed")
    _atomic_json(sink_target, payload)
    if acceptance_receipt is not None:
        acceptance_receipt.update(receipt)
    return payload
