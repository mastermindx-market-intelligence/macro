"""Review-only, source-anchored Catalyst Loop partner distribution packs.

This is a read-model and asset compiler, not an event authority, publisher,
partner registry, email sender, outreach bot, or model caller. The producer and
partner-rights owners must supply positive, verifiable inputs. Drafts are never
marked published. SESSION 00 owns the public scan route.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlsplit

PACK_SCHEMA = "marketing.catalyst_partner_pack.v1"
_UTC = timezone.utc
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,47}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,95}$")
_EMAIL = re.compile(r"[\w.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ALLOWED_RELATIONS = {"DIRECT", "EVIDENCED_INDIRECT"}
_ALLOWED_KINDS = {"earnings", "event", "company_news", "ai_capex", "semiconductor", "semiconductor_event"}
_ALLOWED_CHANNELS = {"newsletter", "community", "social", "research", "podcast"}
_DEMO_SCAN_URL = "https://preview.invalid/catalyst/scan/"


class PackRejected(ValueError):
    """Typed public-safety refusal; never includes untrusted content or PII."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise PackRejected(code)


def _stamp(value: Any, name: str) -> datetime:
    _require(isinstance(value, str) and bool(value.strip()), "MISSING_" + name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackRejected("INVALID_" + name) from exc
    _require(dt.tzinfo is not None and dt.utcoffset() == timedelta(0),
             "NON_UTC_" + name)
    return dt.astimezone(_UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_https(
    value: Any, *, code: str = "UNSAFE_URL",
    allow_fixture_hosts: bool = False,
) -> str:
    """Public-facing HTTPS link validation; never fetch or normalize the URL.

    The public scan privacy review exposed percent-encoded emails in innocent
    query keys. Decode only for inspection, including bounded nested encoding,
    while preserving case-sensitive original URLs verbatim in valid outputs.
    """
    _require(isinstance(value, str) and 0 < len(value) <= 1000, code)
    try:
        u = urlsplit(value)
        host = (u.hostname or "").lower().rstrip(".")
        port = u.port
    except ValueError as exc:
        raise PackRejected(code) from exc
    _require(u.scheme == "https" and host
             and u.username is None and u.password is None
             and not u.fragment and port in (None, 443)
             and not any(ch in value for ch in '<>"\n\r\t\\[]`')
             and not any(ch.isspace() for ch in value),
             code)
    decoded = value
    for _ in range(6):
        unwrapped = unquote(decoded)
        if unwrapped == decoded:
            break
        decoded = unwrapped
    _require(unquote(decoded) == decoded, code)
    folded = unicodedata.normalize("NFKC", decoded)
    _require(not _EMAIL.search(folded)
             and not any(ch in folded for ch in '<>"\n\r\t\\'), code)
    # HTML anchor links may be opened by public readers; block local/private
    # destinations even though this compiler itself performs no network fetch.
    _require(bool(re.fullmatch(r"[a-z0-9.-]+", host))
             and "." in host
             and not host.startswith(".") and not host.endswith(".")
             and not any(host == suffix or host.endswith("." + suffix)
                         for suffix in ("localhost", "local", "internal", "test"))
             and (allow_fixture_hosts or not (
                 host == "invalid" or host.endswith(".invalid"))), code)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise PackRejected(code)
    return value  # Source link/path casing and allowed query are unchanged.


def _atom(value: Any, code: str, max_len: int = 220) -> str:
    _require(isinstance(value, str), code)
    value = value.strip()
    _require(bool(value) and len(value) <= max_len and not any(
        ord(c) < 32 for c in value) and not _EMAIL.search(value), code)
    return value


def _markdown_text(value: str) -> str:
    """Quote source-controlled prose for newsletter Markdown, not for facts.

    Markdown inputs are immutable public source assertions. Brackets and raw
    HTML must be displayed as inert text, never parsed as advertiser-authored
    links, scripts or formatting that the event's sources did not authorize.
    """
    inert = html.escape(value, quote=False)
    return re.sub(r"([\\\[\]`*_])", r"\\\1", inert)


def _markdown_url(value: str) -> str:
    """Keep approved URL bytes except link-delimiter parentheses in Markdown."""
    return value.replace("(", "%28").replace(")", "%29")


def _ticker_list(raw: Any) -> list[str]:
    _require(isinstance(raw, (list, tuple)) and 1 <= len(raw) <= 3,
             "TICKER_COUNT")
    values = [_atom(v, "INVALID_TICKER", 10).upper() for v in raw]
    _require(all(_TICKER.fullmatch(v) for v in values), "INVALID_TICKER")
    _require(len(set(values)) == len(values), "DUPLICATE_TICKER")
    return values


def _sources(packet: dict, as_of: datetime, *, demo_only: bool) -> dict[str, dict]:
    raw = packet.get("sources")
    _require(isinstance(raw, list) and 1 <= len(raw) <= 30,
             "MISSING_SOURCES")
    sources: dict[str, dict] = {}
    for row in raw:
        _require(isinstance(row, dict), "INVALID_SOURCE")
        key = _atom(row.get("source_id"), "INVALID_SOURCE_ID", 96)
        _require(_ID.fullmatch(key) is not None and key not in sources,
                 "DUPLICATE_OR_INVALID_SOURCE_ID")
        rights = row.get("rights")
        _require(isinstance(rights, dict)
                 and rights.get("public_display") is True
                 and rights.get("public_link") is True
                 and _atom(rights.get("receipt_id"), "RIGHTS_RECEIPT_MISSING"),
                 "BLOCKED_PUBLIC_RIGHTS")
        published = _stamp(row.get("published_at_utc"), "SOURCE_TIME")
        _require(published <= as_of, "FUTURE_SOURCE")
        sources[key] = {
            "source_id": key,
            "title": _atom(row.get("title"), "INVALID_SOURCE_TITLE", 160),
            "url": _safe_https(row.get("url"), code="UNSAFE_SOURCE_URL",
                               allow_fixture_hosts=demo_only),
            "published_at_utc": _iso(published),
            "tier": str(row.get("tier") or "unverified").lower(),
            "public_rehost": rights.get("public_rehost") is True,
        }
    return sources


def _partner(raw: Any, now: datetime, *, demo_only: bool) -> dict:
    _require(isinstance(raw, dict), "INVALID_PARTNER")
    slug = _atom(raw.get("slug"), "INVALID_PARTNER_SLUG", 48)
    _require(_SLUG.fullmatch(slug) is not None, "INVALID_PARTNER_SLUG")
    status = raw.get("status")
    _require(status in ("candidate", "approved"), "INVALID_PARTNER_STATUS")
    channel = raw.get("channel")
    _require(channel in _ALLOWED_CHANNELS, "INVALID_PARTNER_CHANNEL")
    _safe_https(raw.get("profile_url"), code="INVALID_PARTNER_PROFILE_URL",
                allow_fixture_hosts=demo_only)
    verified = _stamp(raw.get("profile_verified_at_utc"),
                      "PARTNER_PROFILE_TIME")
    _require(verified <= now and now - verified <= timedelta(days=90),
             "STALE_PARTNER_PROFILE")
    name = _atom(raw.get("name"), "INVALID_PARTNER_NAME", 100)
    audience = _atom(raw.get("audience"), "INVALID_AUDIENCE", 150)
    receipt = raw.get("brand_permission_receipt")
    if status == "approved":
        _require(isinstance(receipt, str) and _ID.fullmatch(receipt) is not None,
                 "PARTNER_BRAND_PERMISSION_MISSING")
        disclosure = "Partner distribution preview with " + name + ". Not published."
    else:
        _require(not receipt, "CANDIDATE_MUST_NOT_CLAIM_PERMISSION")
        disclosure = (
            "Unsolicited concept prepared for " + name
            + ". No partnership, endorsement, or approval is implied."
        )
    return {
        "slug": slug, "name": name, "audience": audience, "status": status,
        "channel": channel, "profile_url": raw["profile_url"],
        "profile_verified_at_utc": _iso(verified), "disclosure": disclosure,
        # This is a display-only descriptor. No partner logos are imported.
    }


def _route(scan_url: str | None, route_receipt: str | None) -> tuple[str, bool]:
    if scan_url is None and route_receipt is None:
        return _DEMO_SCAN_URL, False
    _require(bool(scan_url) and bool(route_receipt), "SCAN_ROUTE_UNREGISTERED")
    _require(_ID.fullmatch(str(route_receipt)) is not None, "INVALID_ROUTE_RECEIPT")
    # Preserve the distinct placeholder denial; the host/path allowlist below
    # still forbids an invented .invalid route from carrying approval status.
    u = _safe_https(scan_url, code="INVALID_SCAN_URL",
                    allow_fixture_hosts=True)
    parsed = urlsplit(u)
    _require(not parsed.query and not parsed.fragment and not u.endswith("//"),
             "DUPLICATE_OR_INVALID_UTM")
    _require(parsed.hostname != "preview.invalid", "ROUTE_RECEIPT_FOR_PLACEHOLDER")
    # Partner readers must land on the accessible HTML first-value experience,
    # never the machine-readable JSON scan endpoint.
    _require(parsed.hostname in ("www.mastermind-x.com", "mastermind-x.com")
             and parsed.path == "/api/catalyst",
             "INVALID_SCAN_ROUTE")
    return u, True


def _public_packet(packet: dict, now: datetime) -> tuple[dict, dict[str, dict], dict[str, dict]]:
    _require(isinstance(packet, dict), "INVALID_EVENT_PACKET")
    _require(packet.get("public_safe") in ("PUBLIC_SAFE", "APPROVED_PUBLIC", "ALLOWED"),
             "BLOCKED_PUBLIC")
    v = packet.get("verification")
    if packet.get("demo_only") is True:
        _require(isinstance(v, dict)
                 and v.get("status") == "SYNTHETIC_FIXTURE"
                 and v.get("source_owner") == "fixture.only",
                 "INVALID_SYNTHETIC_FIXTURE")
    else:
        _require(isinstance(v, dict) and v.get("status") == "VERIFIED"
                 and v.get("source_owner") == "engine.marketing.catalyst_packets"
                 and isinstance(v.get("receipt_id"), str)
                 and bool(v["receipt_id"].strip()), "EVENT_VERIFICATION_MISSING")
    event_id = _atom(packet.get("event_id"), "INVALID_EVENT_ID", 96)
    _require(_ID.fullmatch(event_id) is not None, "INVALID_EVENT_ID")
    kind = _atom(packet.get("event_kind"), "INVALID_EVENT_KIND", 35).lower()
    _require(kind in _ALLOWED_KINDS, "UNSUPPORTED_EVENT_KIND")
    state = packet.get("status")
    _require(state == "active", "RETRACTED_OR_SUPERSEDED_EVENT")
    generation = packet.get("correction_generation")
    _require(type(generation) is int and generation >= 0, "INVALID_CORRECTION")
    corrections = packet.get("corrections") or []
    _require(isinstance(corrections, list) and len(corrections) <= 20,
             "INVALID_CORRECTION_HISTORY")
    if generation:
        _require(bool(corrections), "MISSING_CORRECTION_HISTORY")
    missing = packet.get("missing_data") or []
    _require(isinstance(missing, list) and len(missing) <= 10,
             "INVALID_MISSING_DATA")
    missing = [_atom(s, "INVALID_MISSING_DATA", 300) for s in missing]
    event_time = _stamp(packet.get("event_time_utc"), "EVENT_TIME")
    first_seen = _stamp(packet.get("first_observed_at_utc"), "OBSERVED_TIME")
    as_of = _stamp(packet.get("as_of_utc"), "AS_OF")
    expires = _stamp(packet.get("expires_at_utc"), "EXPIRES")
    _require(event_time <= as_of and first_seen <= as_of <= now
             and now < expires and now - as_of <= timedelta(hours=72),
             "STALE_OR_FUTURE_EVENT")
    publication = packet.get("publication_time_utc")
    if publication:
        _require(_stamp(publication, "PUBLICATION_TIME") <= as_of,
                 "FUTURE_PUBLICATION")
    sources = _sources(packet, as_of, demo_only=packet.get("demo_only") is True)
    headline_receipts = packet.get("headline_evidence_ids")
    _require(isinstance(headline_receipts, list) and bool(headline_receipts)
             and all(isinstance(ref, str) and ref in sources
                     for ref in headline_receipts),
             "HEADLINE_EVIDENCE_MISSING")
    _require(len(headline_receipts) == len(set(headline_receipts)),
             "HEADLINE_EVIDENCE_MISSING")
    ticker_rows = packet.get("affected_tickers")
    _require(isinstance(ticker_rows, list), "MISSING_TICKER_RELATIONS")
    relations: dict[str, dict] = {}
    for row in ticker_rows:
        _require(isinstance(row, dict), "INVALID_TICKER_RELATION")
        ticker = _atom(row.get("ticker"), "INVALID_TICKER", 10).upper()
        _require(_TICKER.fullmatch(ticker) is not None and ticker not in relations,
                 "DUPLICATE_OR_INVALID_TICKER_RELATION")
        relations[ticker] = row
    return ({
        "event_id": event_id, "event_kind": kind,
        "primary_subject": _atom(packet.get("primary_subject"),
                                 "INVALID_SUBJECT", 140),
        "headline_evidence_ids": list(headline_receipts),
        "event_time_utc": _iso(event_time),
        "first_observed_at_utc": _iso(first_seen),
        "as_of_utc": _iso(as_of), "expires_at_utc": _iso(expires),
        "publication_time_utc": _iso(_stamp(publication, "PUBLICATION_TIME"))
                                 if publication else None,
        "correction_generation": generation,
        # Never export upstream correction objects: they may carry internal
        # evidence or editor details not cleared for partner re-distribution.
        "correction_count": len(corrections),
        "missing_data": missing,
        "demo_only": packet.get("demo_only") is True,
    }, sources, relations)


def _claims(packet: dict, tickers: list[str],
            relations: dict[str, dict], sources: dict[str, dict]) -> list[dict]:
    raw = packet.get("claims")
    _require(isinstance(raw, list) and 1 <= len(raw) <= 50,
             "MISSING_EVIDENCED_CLAIMS")
    by_id: dict[str, dict] = {}
    for row in raw:
        _require(isinstance(row, dict), "INVALID_CLAIM")
        key = _atom(row.get("claim_id"), "INVALID_CLAIM_ID", 96)
        refs = row.get("source_ids")
        _require(_ID.fullmatch(key) is not None and key not in by_id
                 and isinstance(refs, list) and bool(refs)
                 and all(isinstance(r, str) and r in sources for r in refs),
                 "UNSOURCED_OR_DUPLICATE_CLAIM")
        related = row.get("tickers")
        _require(isinstance(related, list), "UNSCOPED_CLAIM")
        text = _atom(row.get("text"), "EMPTY_CLAIM", 600)
        _require(all(isinstance(t, str) and _TICKER.fullmatch(t)
                     for t in related), "INVALID_CLAIM_TICKERS")
        by_id[key] = {"claim_id": key, "text": text, "tickers": related,
                      "source_ids": refs}
    included: list[dict] = []
    for t in tickers:
        relation = relations.get(t)
        _require(relation is not None, "UNSUPPORTED_TICKER")
        _require(relation.get("relationship") in _ALLOWED_RELATIONS,
                 "UNSUPPORTED_OR_UNKNOWN_RELATION")
        ev = relation.get("evidence_ids")
        _require(isinstance(ev, list) and bool(ev)
                 and all(isinstance(e, str) and e in by_id for e in ev),
                 "RELATION_EVIDENCE_MISSING")
        _require(any(t in by_id[e]["tickers"] for e in ev),
                 "TICKER_EVIDENCE_MISMATCH")
        for e in ev:
            if t in by_id[e]["tickers"] and e not in {c["claim_id"] for c in included}:
                included.append(by_id[e])
    _require(bool(included), "NO_APPLICABLE_CLAIMS")
    return included


def build_partner_pack(
    event_packet: dict, partner_profile: dict,
    selected_tickers: list[str] | None = None,
    *, preview_only: bool = True, now_utc: datetime | None = None,
    scan_url: str | None = None, route_receipt: str | None = None,
    angle_plan: dict | None = None,
) -> dict:
    """Compile a gated draft. No network, model, publication or side effects.

    Optional AI-assisted angle_plan is a bounded list of existing claim IDs;
    a model can SELECT evidence, never originate source facts or claim text.
    """
    # Match the frozen Session 00 consumer signature, with its selected
    # ticker list carried by the reviewed partner descriptor. Explicitly
    # selected tickers remain permitted for test/CLI use. This is NEVER a
    # publishing API, even if a caller attempts to toggle preview_only.
    _require(preview_only is True, "PUBLICATION_UNAUTHORIZED")
    if selected_tickers is None and isinstance(partner_profile, dict):
        selected_tickers = partner_profile.get("selected_tickers")
    now_utc = now_utc or datetime.now(_UTC)
    _require(isinstance(now_utc, datetime) and now_utc.tzinfo is not None
             and now_utc.utcoffset() == timedelta(0), "INVALID_NOW")
    now = now_utc.astimezone(_UTC)
    ticks = _ticker_list(selected_tickers)
    event, sources, relations = _public_packet(event_packet, now)
    partner = _partner(partner_profile, now, demo_only=event["demo_only"])
    claims = _claims(event_packet, ticks, relations, sources)
    if angle_plan is not None:
        _require(isinstance(angle_plan, dict)
                 and set(angle_plan) == {"selected_claim_ids"},
                 "INVALID_ANGLE_PLAN")
        ids = angle_plan["selected_claim_ids"]
        available = {x["claim_id"] for x in claims}
        _require(isinstance(ids, list) and bool(ids)
                 and all(isinstance(ident, str) for ident in ids),
                 "AI_UNGROUNDED_CLAIM_SELECTION")
        _require(len(ids) == len(set(ids)) and set(ids) <= available,
                 "AI_UNGROUNDED_CLAIM_SELECTION")
        claims = [c for ident in ids for c in claims if c["claim_id"] == ident]
        _require(all(any(t in c["tickers"] for c in claims) for t in ticks),
                 "AI_DROPPED_TICKER_EVIDENCE")
    base_url, route_live = _route(scan_url, route_receipt)
    # Reuse the existing funnel link authority, not a second UTM encoder.
    from engine.marketing.links import canonical_link, is_tagged_canonical
    # Identity is content-addressed over exactly the public evidence and
    # partner copy used by this pack. Claim IDs alone are NOT enough: a
    # corrected fact with an accidentally unchanged claim ID must never reuse
    # the attribution key of the earlier creative.
    active_ids = list(dict.fromkeys(event["headline_evidence_ids"] + [
        source_id for claim in claims for source_id in claim["source_ids"]
    ]))
    active_sources = {source_id: sources[source_id] for source_id in active_ids}
    identity = {
        "event": event, "partner": partner, "tickers": ticks,
        "claims": claims,
        "sources": list(active_sources.values()),
        "relationships": [
            {
                "ticker": ticker,
                "relationship": relations[ticker]["relationship"],
                "evidence_ids": relations[ticker]["evidence_ids"],
            }
            for ticker in ticks
        ],
    }
    pack_id = "cp_" + hashlib.sha256(json.dumps(
        identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()[:18]
    canonical = canonical_link(
        "partner-" + partner["slug"], "catalyst_scan", pack_id,
        base_url=base_url, utm_source="partner",
    )
    # links.canonical_link owns the query encoding but normalizes the base
    # path with a slash; Session 00's exact FastAPI route /api/catalyst MUST
    # not silently become /api/catalyst/ (redirect or unexpected 404).
    tagged = base_url + "?" + canonical.split("?", 1)[1]
    _require(is_tagged_canonical(tagged, base_url=base_url),
             "CANONICAL_ATTRIBUTION_FAILED")
    _require(not parse_qsl(urlsplit(base_url).query), "DUPLICATE_OR_INVALID_UTM")
    scan_link = tagged + "&event_id=" + quote(event["event_id"], safe="")
    scan_link += "&tickers=" + quote(",".join(ticks), safe="")
    _require(len(dict(parse_qsl(urlsplit(scan_link).query))) == 6
             and len(parse_qsl(urlsplit(scan_link).query)) == 6,
             "DUPLICATE_OR_INVALID_UTM")
    # Social and card readers must see distinct evidential value: the card may
    # be withheld where a single claim would merely repeat the social draft.
    lead_ticker = ticks[-1]
    lead_claim = next(c for c in reversed(claims) if lead_ticker in c["tickers"])
    social_hook = "$" + lead_ticker + ": " + lead_claim["text"]
    # Both the event headline and the actual included claims contribute to
    # this asset. A headline-only source with public_display=True but
    # public_rehost=False must withhold the SVG, not disappear from the ledger.
    media_rights = all(s["public_rehost"] for s in active_sources.values())
    main_source = sources[claims[0]["source_ids"][0]]
    card_svg = None
    media_fit: dict[str, Any] = {}
    media_status = "REHOST_RIGHTS_BLOCKED"
    if media_rights:
        from engine.marketing.chart_render import render_breaking_card
        card_svg = render_breaking_card(
            headline=claims[0]["text"], summary=None,
            source_name=main_source["title"],
            source_tier=main_source["tier"],
            published_at=main_source["published_at_utc"],
            tickers=[{"ticker": t} for t in ticks],
            eyebrow="EVENT EVIDENCE", cta=False, suppress_cta=True,
            fit=media_fit,
        )
        _require("headline_drawn" in media_fit
                 and isinstance(card_svg, str)
                 and card_svg.lstrip().startswith("<svg")
                 and "MASTERMIND" in card_svg
                 and len(card_svg) <= 250_000
                 and not re.search(r"<script\b|<foreignObject\b",
                                   card_svg, re.IGNORECASE),
                 "CHART_RENDER_FAILED")
    # Claims are used verbatim from the verified read-model, never rewritten into
    # new numbers, causal relations, targets, odds or investment advice.
    ordered_sources = list(active_sources.values())
    citations = [
        f'- [{_markdown_text(s["title"])}]({_markdown_url(s["url"])}) '
        f'({s["published_at_utc"]})'
        for s in ordered_sources
    ]
    direct = [t for t in ticks if relations[t]["relationship"] == "DIRECT"]
    indirect = [t for t in ticks
                if relations[t]["relationship"] == "EVIDENCED_INDIRECT"]
    scope_lines = [
        "These are evidence-qualified relationships, not estimated market "
        "moves or trading recommendations.",
    ]
    if direct:
        scope_lines.insert(0, "Direct event relationship: " + ", ".join(direct) + ".")
    if indirect:
        scope_lines.insert(1 if direct else 0,
                           "Evidenced indirect relationship: "
                           + ", ".join(indirect) + ".")
    newsletter_lines = [
        f'# {_markdown_text(event["primary_subject"])}: sourced event brief',
        "",
        _markdown_text(partner["disclosure"]), "",
        "Headline source evidence: " + ", ".join(event["headline_evidence_ids"]) + ".",
        "",
        f'For readers following {_markdown_text(partner["audience"])}, this note tracks '
        + ", ".join(ticks) + " against the same event evidence.",
        "",
        "## Relationship scope", "",
        *scope_lines,
        "",
        "## Confirmed observations", "",
    ]
    newsletter_lines += [
        f'- {_markdown_text(c["text"])} [Evidence {c["claim_id"]}; '
        + ", ".join(c["source_ids"]) + "]"
        for c in claims
    ]
    newsletter_lines += ["", "## Source references", ""]
    newsletter_lines += citations
    if event["correction_generation"]:
        newsletter_lines += ["", "## Correction status", "",
                             "This event has a revised generation. Review the "
                             "underlying correction trail before distribution."]
    if event["missing_data"]:
        newsletter_lines += ["", "## Coverage limitations", ""]
        newsletter_lines += [
            "- " + _markdown_text(_atom(m, "INVALID_MISSING_DATA", 300))
            for m in event["missing_data"][:10] if isinstance(m, str)
        ]
    newsletter_lines += [
        "", f'Information as of {event["as_of_utc"]}; '
        + f'event dated {event["event_time_utc"]}.',
        "Conditional context only. Not investment advice.",
        "Scan the cited event and selected tickers: " + scan_link,
        "", "DRAFT PREVIEW - NOT APPROVED FOR DISTRIBUTION.",
    ]
    newsletter = "\n".join(newsletter_lines) + "\n"
    # Two individually length-checked draft posts prevent the long, canonical
    # attributed link from crowding out the ACTUAL verified observation.
    # Never clip a sentence: clipping may invert a material qualifier.
    _require(not re.search(r"<[^>]+>|\[[^]]+\]\([^)]+\)", social_hook),
             "SOCIAL_UNSAFE_MARKUP")
    social_disclosure = (
        "Concept; no endorsement. " if partner["status"] == "candidate"
        else "Partner: " + partner["name"] + ". "
    )
    social_link_post = social_disclosure + scan_link
    _require(len(social_hook) <= 275 and len(social_link_post) <= 275,
             "SOCIAL_CHARACTER_BUDGET")
    social = ("DRAFT THREAD 1/2\n" + social_hook
              + "\n\nDRAFT THREAD 2/2\n" + social_link_post)
    # Existing publisher/press lexicons and the shared social copy validator.
    # Number tokens in this exact, verified source claim are not LLM inventions.
    from engine.marketing.copywriter import (
        _extract_number_tokens, banned_language, build_context, validate_copy,
    )
    from engine.press.validators import (
        check_advice_lexicon, check_banned_lexicon, check_cheese_test,
    )
    ctx = build_context({"type": "chart", "ticker": lead_ticker,
                         "account": partner["slug"]})
    ctx["numbers_whitelist"] = _extract_number_tokens(lead_claim["text"])
    violations = validate_copy(social_hook, "", ctx)
    violations += banned_language(social_disclosure)
    _require(not violations, "SOCIAL_COPY_REJECTED")
    if card_svg:
        # Reuse the incumbent card-value gate. Compare the SAME social
        # message we propose to distribute against the text that renderer
        # actually drew, never the untruncated producer claim.
        from engine.marketing.breaking_summary import card_earns_attachment
        attaches, _ = card_earns_attachment(
            social_hook,
            str(media_fit["headline_drawn"]),
            str(media_fit.get("summary_drawn") or ""),
            [],
        )
        if attaches:
            media_status = "READY_FOR_REVIEW"
        else:
            card_svg = None
            media_status = "CARD_WITHHELD_NO_ADDITIONAL_VALUE"
    draft = {"title": event["primary_subject"],
             "body_html": "<p>" + html.escape(" ".join(c["text"] for c in claims))
                          + "</p>"}
    for gate in (check_banned_lexicon, check_advice_lexicon, check_cheese_test):
        _require(gate(draft, {}, {}).get("ok") is True,
                 "EDITORIAL_COPY_REJECTED")
    # Embed is an operator-reviewed concept, not an installed widget/publisher.
    embed = (
        '<div class="mm-catalyst-embed" role="group" '
        'aria-label="Mastermind event scan proposal"><p>'
        + html.escape(event["primary_subject"])
        + '</p><a rel="nofollow sponsored noopener" href="'
        + html.escape(scan_link, quote=True)
        + '">Review the sourced event scan</a><small>'
        + html.escape(partner["disclosure"])
        + "</small></div>"
    )
    return {
        "schema": PACK_SCHEMA, "pack_id": pack_id,
        "event": event, "partner": partner,
        "selected_tickers": ticks,
        "relationships": [
            {"ticker": t, "relationship": relations[t]["relationship"]}
            for t in ticks
        ],
        "claims": claims, "sources": ordered_sources,
        "scan_link": scan_link,
        "link_is_placeholder": not route_live,
        "card_svg": card_svg,
        "media_status": media_status,
        "newsletter": newsletter, "social": social,
        "embed": embed,
        "publication_status": "DRAFT_HOLD",
        "disclosure": partner["disclosure"],
        "needs_review": [
            "Verify live scan route and scan response before publishing."
            if not route_live else "Verify scan runtime and attribution.",
            "Independent rights, facts, freshness and copy review.",
            "Partner permission and editor signoff before any distribution.",
        ],
    }



def build_partner_pack_from_native_event(
    native_event: dict, native_scan: dict, partner_profile: dict,
    selected_tickers: list[str] | None = None,
    *, now_utc: datetime | None = None, preview_only: bool = True,
    scan_url: str | None = None, route_receipt: str | None = None,
    angle_plan: dict | None = None,
) -> dict:
    """Bridge the Session 01 PUBLIC read-model to this held asset compiler.

    Session 01 is the sole event/source/issuer/rights owner. This adapter
    rechecks identity, provenance and public-scan correspondence; it NEVER
    issues a new grant, claims that a fixture grant is licensed, or invents an
    indirect issuer relationship. Native rights allow factual display/link
    only: no native source row grants image rehosting, so SVG stays WITHHELD.
    Both source owner and public scan must have been supplied by a trusted
    server-side caller; an arbitrary request body is NOT an admitted source.
    """
    _require(preview_only is True, "PUBLICATION_UNAUTHORIZED")
    _require(isinstance(native_event, dict) and isinstance(native_scan, dict),
             "NATIVE_PACKET_INVALID")
    _require(native_event.get("schema") == "catalyst.public_event/v1"
             and type(native_event.get("schema_version")) is int
             and native_event["schema_version"] == 1
             and native_scan.get("schema") == "catalyst.scan/v1"
             and type(native_scan.get("schema_version")) is int
             and native_scan["schema_version"] == 1,
             "NATIVE_SCHEMA_UNSUPPORTED")
    _require(native_event.get("public_safe") is True
             and native_event.get("public_disposition") == "PUBLIC_READY",
             "NATIVE_PUBLIC_RIGHTS_BLOCKED")
    _require(native_scan.get("publication_state") == "PUBLIC_QUALIFIED",
             "NATIVE_SCAN_NOT_ALL_SUPPORTED")
    if selected_tickers is None and isinstance(partner_profile, dict):
        selected_tickers = partner_profile.get("selected_tickers")
    ticks = _ticker_list(selected_tickers)
    _require(native_scan.get("requested_tickers") == ticks,
             "NATIVE_SCAN_TICKER_MISMATCH")
    identity = _atom(native_event.get("event_id"), "NATIVE_EVENT_ID", 96)
    _require(_ID.fullmatch(identity) is not None
             and native_scan.get("event_id") == identity,
             "NATIVE_EVENT_ID_MISMATCH")
    generation = native_event.get("generation")
    _require(type(generation) is int and generation >= 0
             and native_scan.get("generation") == generation,
             "NATIVE_GENERATION_MISMATCH")
    revision = native_event.get("correction_state")
    correction = native_event.get("correction")
    _require(isinstance(correction, dict)
             and correction.get("generation") == generation
             and ((revision == "CURRENT" and generation == 0
                   and correction.get("status") == "active")
                  or (revision == "CORRECTED" and generation > 0
                      and correction.get("status") == "corrected")),
             "NATIVE_CORRECTION_NOT_CURRENT")
    native_kind = _atom(native_event.get("event_kind"),
                        "NATIVE_EVENT_KIND", 40)
    _require(native_kind in ("earnings", "ai_capex", "semiconductor_event"),
             "NATIVE_EVENT_KIND_UNSUPPORTED")
    now = now_utc or datetime.now(_UTC)
    _require(isinstance(now, datetime) and now.tzinfo is not None
             and now.utcoffset() == timedelta(0), "INVALID_NOW")
    event_asof = _stamp(native_event.get("as_of_utc"), "NATIVE_EVENT_AS_OF")
    scan_asof = _stamp(native_scan.get("as_of_utc"), "NATIVE_SCAN_AS_OF")
    expires = _stamp(native_event.get("cache_expires_at_utc"),
                     "NATIVE_CACHE_EXPIRY")
    _require(event_asof <= scan_asof <= now and now < expires
             and now - event_asof <= timedelta(hours=72),
             "NATIVE_STALE_OR_MISMATCHED_CLOCK")
    subject = native_event.get("primary_subject")
    _require(isinstance(subject, dict), "NATIVE_SUBJECT_INVALID")
    primary_ticker = _atom(subject.get("ticker"),
                           "NATIVE_SUBJECT_INVALID", 10)
    _require(_TICKER.fullmatch(primary_ticker) is not None
             and _atom(subject.get("issuer_id"),
                       "NATIVE_SUBJECT_INVALID", 100),
             "NATIVE_SUBJECT_INVALID")
    company = _atom(subject.get("company_name"),
                    "NATIVE_SUBJECT_INVALID", 120)

    # Native source grant covers title/link/facts, never SVG rehosting. The
    # receipt identifier is copied from the existing source owner untouched.
    records = native_event.get("sources")
    receipts = native_event.get("rights_receipt_ids")
    _require(isinstance(records, list) and 1 <= len(records) <= 12
             and isinstance(receipts, list) and bool(receipts)
             and all(isinstance(r, str) and _ID.fullmatch(r)
                     for r in receipts),
             "NATIVE_SOURCE_GRANTS_MISSING")
    _require(not any(r.lower().startswith(("fixture", "test", "fake"))
                     for r in receipts),
             "NATIVE_FIXTURE_RIGHTS_NOT_AUTHORIZED")
    native_byid: dict[str, dict] = {}
    normalized_sources: list[dict] = []
    for row in records:
        _require(isinstance(row, dict), "NATIVE_SOURCE_INVALID")
        source_id = _atom(row.get("source_id"), "NATIVE_SOURCE_INVALID", 96)
        _require(_ID.fullmatch(source_id) is not None
                 and source_id not in native_byid, "NATIVE_SOURCE_INVALID")
        source_receipt = _atom(row.get("rights_receipt_id"),
                               "NATIVE_SOURCE_GRANTS_MISSING", 96)
        _require(row.get("display_rights") == "ALLOWED"
                 and source_receipt in receipts,
                 "NATIVE_SOURCE_GRANTS_MISSING")
        title = _atom(row.get("title"), "NATIVE_SOURCE_INVALID", 160)
        link = _safe_https(row.get("url"), code="NATIVE_SOURCE_URL_INVALID")
        published = _stamp(row.get("published_at_utc"),
                           "NATIVE_SOURCE_PUBLISHED")
        _require(published <= event_asof, "NATIVE_FUTURE_SOURCE")
        native_byid[source_id] = {
            "source_id": source_id, "url": link, "title": title,
            "published_at_utc": _iso(published),
            "display_rights": "ALLOWED", "rights_receipt_id": source_receipt,
        }
        normalized_sources.append({
            "source_id": source_id, "title": title, "url": link,
            "published_at_utc": _iso(published), "tier": "unverified",
            "rights": {"public_display": True, "public_link": True,
                       "public_rehost": False, "receipt_id": source_receipt},
        })
    _require(len(set(receipts)) == len(receipts)
             and set(receipts) == {r["rights_receipt_id"]
                                   for r in native_byid.values()},
             "NATIVE_SOURCE_GRANTS_MISSING")

    # The producer evidence ledger maps opaque evidence IDs to actually
    # accepted source IDs. Never use a model-produced relation as an anchor.
    evidence_lookup: dict[str, str] = {}
    raw_evidence = native_event.get("evidence")
    _require(isinstance(raw_evidence, list) and len(raw_evidence) <= 100,
             "NATIVE_EVIDENCE_INVALID")
    for row in raw_evidence:
        _require(isinstance(row, dict), "NATIVE_EVIDENCE_INVALID")
        eid = _atom(row.get("evidence_id"), "NATIVE_EVIDENCE_INVALID", 96)
        sid = row.get("source_id")
        _require(_ID.fullmatch(eid) is not None and sid in native_byid
                 and eid not in evidence_lookup, "NATIVE_EVIDENCE_INVALID")
        evidence_lookup[eid] = sid

    def source_refs(claim: dict) -> list[str]:
        _require(isinstance(claim, dict), "NATIVE_CLAIM_INVALID")
        evidence_ids = claim.get("evidence_ids") or []
        source_ids = claim.get("source_ids") or []
        _require(isinstance(evidence_ids, list)
                 and isinstance(source_ids, list)
                 and all(isinstance(e, str) and e in evidence_lookup
                         for e in evidence_ids)
                 and all(isinstance(s, str) and s in native_byid
                         for s in source_ids),
                 "NATIVE_CLAIM_EVIDENCE_INVALID")
        refs = sorted({evidence_lookup[e] for e in evidence_ids} |
                      set(source_ids))
        _require(bool(refs), "NATIVE_CLAIM_EVIDENCE_INVALID")
        return refs

    original = native_event.get("what_changed")
    _require(isinstance(original, list) and len(original) <= 30,
             "NATIVE_CLAIM_INVALID")
    permitted_facts = set()
    for claim in original:
        text = _atom(claim.get("text") if isinstance(claim, dict) else None,
                     "NATIVE_CLAIM_INVALID", 600)
        permitted_facts.add((text, tuple(source_refs(claim))))

    relations_raw = native_event.get("affected_tickers")
    _require(isinstance(relations_raw, list), "NATIVE_RELATIONS_MISSING")
    native_relations = {}
    for rel in relations_raw:
        _require(isinstance(rel, dict), "NATIVE_RELATIONS_MISSING")
        ticker = _atom(rel.get("ticker"), "NATIVE_RELATIONS_MISSING", 10)
        _require(_TICKER.fullmatch(ticker) and ticker not in native_relations,
                 "NATIVE_RELATIONS_MISSING")
        native_relations[ticker] = rel

    out_claims: list[dict] = []
    out_relations: list[dict] = []
    headline_sources: set[str] = set()
    results = native_scan.get("results")
    _require(isinstance(results, list) and len(results) == len(ticks),
             "NATIVE_SCAN_TICKER_MISMATCH")
    for ticker, result in zip(ticks, results):
        _require(isinstance(result, dict) and result.get("ticker") == ticker,
                 "NATIVE_SCAN_TICKER_MISMATCH")
        _require(result.get("status") == "SUPPORTED"
                 and result.get("public_safe") is True
                 and result.get("correction_state") == revision,
                 "NATIVE_SCAN_NOT_ALL_SUPPORTED")
        relation = native_relations.get(ticker)
        kind = result.get("relationship")
        _require(isinstance(relation, dict)
                 and kind in _ALLOWED_RELATIONS
                 and relation.get("relationship") == kind,
                 "NATIVE_RELATION_UNSUPPORTED")
        scanned_sources = result.get("sources")
        _require(isinstance(scanned_sources, list)
                 and len(scanned_sources) == len(native_byid)
                 and all(isinstance(s, dict)
                         and native_byid.get(s.get("source_id")) == {
                             k: s.get(k) for k in native_byid.get(
                                 s.get("source_id"), {}
                             )
                         } for s in scanned_sources),
                 "NATIVE_SCAN_SOURCE_MISMATCH")
        # All scan source IDs, including headline/indirect evidence, must
        # correspond byte-for-byte to the rights-qualified source projection.
        headlines = result.get("headline_evidence_ids")
        _require(isinstance(headlines, list) and bool(headlines)
                 and all(isinstance(s, str) and s in native_byid for s in headlines),
                 "NATIVE_HEADLINE_UNSOURCED")
        headline_sources.update(headlines)
        relation_refs = result.get("relationship_evidence_ids") or []
        _require(isinstance(relation_refs, list)
                 and all(isinstance(s, str) and s in native_byid for s in relation_refs),
                 "NATIVE_RELATION_UNSUPPORTED")
        if kind == "EVIDENCED_INDIRECT":
            raw_relation_ids = relation.get("relation_evidence_ids")
            _require(isinstance(raw_relation_ids, list) and bool(raw_relation_ids)
                     and set(relation_refs) == {evidence_lookup.get(e)
                         for e in raw_relation_ids},
                     "NATIVE_RELATION_UNSUPPORTED")

        observations = result.get("what_changed")
        _require(isinstance(observations, list)
                 and 1 <= len(observations) <= 10,
                 "NATIVE_CLAIM_INVALID")
        relation_claim_ids = []
        for i, observation in enumerate(observations):
            text = _atom(
                observation.get("text") if isinstance(observation, dict) else None,
                "NATIVE_CLAIM_INVALID", 600,
            )
            claimed_refs = source_refs(observation)
            allowed_fact = (text, tuple(claimed_refs)) in permitted_facts
            if kind == "EVIDENCED_INDIRECT" and not allowed_fact:
                summary = relation.get("summary")
                allowed_fact = (
                    isinstance(summary, str)
                    and text == f"{summary}; any financial effect on {ticker} is unverified."
                    and set(claimed_refs) == set(relation_refs)
                )
            _require(allowed_fact, "NATIVE_CLAIM_NOT_IN_PRODUCER")
            claim_id = "native-" + hashlib.sha256(
                json.dumps([identity, generation, ticker, i, text, claimed_refs],
                           ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()[:20]
            out_claims.append({
                "claim_id": claim_id, "text": text,
                "tickers": [ticker], "source_ids": claimed_refs,
            })
            relation_claim_ids.append(claim_id)
        _require(bool(relation_claim_ids), "NATIVE_RELATION_UNSUPPORTED")
        out_relations.append({
            "ticker": ticker, "relationship": kind,
            "evidence_ids": relation_claim_ids,
        })

    missing = native_event.get("missing_data") or []
    _require(isinstance(missing, list) and len(missing) <= 10
             and all(isinstance(x, str) and len(x) <= 300 for x in missing),
             "NATIVE_MISSING_DATA_INVALID")
    native_correction = native_event.get("correction")
    corrections = ([{
        "generation": generation,
        "supersedes_generation": native_correction.get("supersedes_generation"),
        "reason": native_correction.get("reason"),
    }] if generation else [])
    read_model = {
        "schema_version": "catalyst.public_event/v1",
        "event_id": identity,
        "event_kind": native_kind,
        "primary_subject": f"{company} ({primary_ticker}) — {native_kind.replace('_', ' ')}",
        "event_time_utc": native_event.get("event_time_utc"),
        "first_observed_at_utc": native_event.get("first_observed_at_utc"),
        "publication_time_utc": native_event.get("publication_time_utc"),
        "as_of_utc": native_event.get("as_of_utc"),
        "expires_at_utc": native_event.get("cache_expires_at_utc"),
        "status": "active",
        "correction_generation": generation,
        "corrections": corrections, "missing_data": missing,
        "affected_tickers": out_relations,
        "sources": normalized_sources,
        "claims": out_claims,
        "headline_evidence_ids": sorted(headline_sources),
        "public_safe": "PUBLIC_SAFE",
        "verification": {
            # This is an upstream owner-asserted public read, NOT independent
            # proof of a real-world license. The rights receipts are copied
            # verbatim, never minted in this marketing adapter.
            "status": "VERIFIED",
            "source_owner": "engine.marketing.catalyst_packets",
            "receipt_id": receipts[0],
        },
    }
    return build_partner_pack(
        read_model, partner_profile, ticks, preview_only=preview_only,
        now_utc=now, scan_url=scan_url, route_receipt=route_receipt,
        angle_plan=angle_plan,
    )

def write_partner_pack(pack: dict, destination: Path | str,
                       *, template_path: Path | str | None = None) -> list[Path]:
    """Write a private draft set, atomically per file; never send or publish."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    base = Path(destination)
    _require(not base.is_symlink(), "UNSAFE_OUTPUT_PATH")
    base.mkdir(parents=True, exist_ok=True)
    template_path = Path(template_path) if template_path else (
        Path(__file__).resolve().parents[2] / "templates" / "catalyst_partner.html.j2"
    )
    env = Environment(loader=FileSystemLoader(str(template_path.parent)),
                      autoescape=True, undefined=StrictUndefined)
    # These are the ACTUAL canonical theme tokens. Extract from theme.css,
    # rather than declaring a second colour/font/radius palette in the new
    # preview template. Copy only the :root token block into the self-contained
    # private preview; nothing from third-party assets or request data.
    token_path = Path(__file__).resolve().parents[2] / "templates" / "theme.css"
    try:
        canonical_css = token_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PackRejected("DESIGN_TOKENS_UNAVAILABLE") from exc
    first = canonical_css.find(":root {")
    last = canonical_css.find("\n}\n", first)
    _require(first >= 0 and last > first
             and last - first < 25000, "DESIGN_TOKENS_INVALID")
    theme_tokens = canonical_css[first:last + 2]
    # Carry the exact stock light-palette override from the SAME canonical
    # stylesheet, not a second invented palette. The first matching block
    # only alters global buttons; the next one carries bg/panel/text tokens.
    marker = 'html[data-theme="light"] {'
    search_at = last + 2
    light_block = ""
    for _ in range(7):
        offset = canonical_css.find(marker, search_at)
        if offset < 0:
            break
        finish = canonical_css.find("\n}", offset)
        _require(finish > offset and finish - offset < 8000,
                 "DESIGN_TOKENS_INVALID")
        block = canonical_css[offset:finish + 2]
        search_at = finish + 2
        if all(name in block for name in ("--bg:", "--panel:", "--text:")):
            light_block = block
            break
    _require(bool(light_block), "DESIGN_TOKENS_INVALID")
    theme_tokens += "\n" + light_block
    _require(all(name in theme_tokens for name in (
                 "--font-ui:", "--bg:", "--panel:", "--text:", "--muted:"))
             and "</style" not in theme_tokens.lower(), "DESIGN_TOKENS_INVALID")
    page = env.get_template(template_path.name).render(
        pack=pack, theme_tokens=theme_tokens,
    )
    _require("DRAFT PREVIEW" in page and pack["scan_link"].replace("&", "&amp;") in page,
             "TEMPLATE_DISCLOSURE_OR_LINK_MISSING")
    files = {
        "index.html": page,
        "newsletter.md": pack["newsletter"],
        "social.txt": pack["social"] + "\n",
        "embed-concept.html": pack["embed"] + "\n",
    }
    if pack["card_svg"]:
        files["intelligence-card.svg"] = pack["card_svg"]
    manifest = {k: v for k, v in pack.items()
                if k not in ("card_svg", "newsletter", "social", "embed")}
    files["manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2,
                                       ensure_ascii=False) + "\n"
    # Refuse predictable unsafe destinations before writing *any* asset,
    # including a symlink placed at a later output name.
    _require(not any((base / name).is_symlink() for name in files),
             "UNSAFE_OUTPUT_PATH")
    # A previous generation may contain an SVG when updated source rights
    # withhold it. The asset is not in this version's file set; retaining the
    # old SVG would leak rights-withdrawn evidence from the same review folder.
    previous_card = base / "intelligence-card.svg"
    retire_previous_card = "intelligence-card.svg" not in files and (
        previous_card.exists() or previous_card.is_symlink()
    )
    if retire_previous_card:
        _require(previous_card.is_file() and not previous_card.is_symlink(),
                 "UNSAFE_OUTPUT_PATH")
    written: list[Path] = []
    for name, data in files.items():
        target = base / name
        # Never write through a caller-planted predictable temp-file symlink.
        # A unique O_EXCL tempfile keeps the existing atomic per-file publish
        # behavior without touching any pre-existing .<name>.tmp path.
        fd, temporary = tempfile.mkstemp(
            dir=base, prefix="." + name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(data)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
        written.append(target)
    if retire_previous_card:
        previous_card.unlink()
    return written
