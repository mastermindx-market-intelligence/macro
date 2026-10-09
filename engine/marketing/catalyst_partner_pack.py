"""Review-only, source-anchored Catalyst Loop partner distribution packs.

This is a read-model and asset compiler, not an event authority, publisher,
partner registry, email sender, outreach bot, or model caller. The producer and
partner-rights owners must supply positive, verifiable inputs. Drafts are never
marked published. SESSION 00 owns the public scan route.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlsplit

PACK_SCHEMA = "marketing.catalyst_partner_pack.v1"
_UTC = timezone.utc
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,47}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,95}$")
_ALLOWED_RELATIONS = {"DIRECT", "EVIDENCED_INDIRECT"}
_ALLOWED_KINDS = {"earnings", "event", "company_news", "ai_capex", "semiconductor"}
_ALLOWED_CHANNELS = {"newsletter", "community", "social", "research"}
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


def _safe_https(value: Any, *, code: str = "UNSAFE_URL") -> str:
    _require(isinstance(value, str) and len(value) <= 1000, code)
    u = urlsplit(value)
    _require(u.scheme == "https" and bool(u.hostname)
             and u.username is None and u.password is None and not u.fragment
             and not any(c in value for c in '<>"\n\r\t\\'), code)
    return value  # Preserve case-sensitive source links and paths exactly.


def _atom(value: Any, code: str, max_len: int = 220) -> str:
    _require(isinstance(value, str), code)
    value = value.strip()
    _require(bool(value) and len(value) <= max_len and not any(
        ord(c) < 32 for c in value), code)
    return value


def _ticker_list(raw: Any) -> list[str]:
    _require(isinstance(raw, (list, tuple)) and 1 <= len(raw) <= 3,
             "TICKER_COUNT")
    values = [_atom(v, "INVALID_TICKER", 10).upper() for v in raw]
    _require(all(_TICKER.fullmatch(v) for v in values), "INVALID_TICKER")
    _require(len(set(values)) == len(values), "DUPLICATE_TICKER")
    return values


def _sources(packet: dict, as_of: datetime) -> dict[str, dict]:
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
            "url": _safe_https(row.get("url"), code="UNSAFE_SOURCE_URL"),
            "published_at_utc": _iso(published),
            "tier": str(row.get("tier") or "unverified").lower(),
            "public_rehost": rights.get("public_rehost") is True,
        }
    return sources


def _partner(raw: Any, now: datetime) -> dict:
    _require(isinstance(raw, dict), "INVALID_PARTNER")
    slug = _atom(raw.get("slug"), "INVALID_PARTNER_SLUG", 48)
    _require(_SLUG.fullmatch(slug) is not None, "INVALID_PARTNER_SLUG")
    status = raw.get("status")
    _require(status in ("candidate", "approved"), "INVALID_PARTNER_STATUS")
    channel = raw.get("channel")
    _require(channel in _ALLOWED_CHANNELS, "INVALID_PARTNER_CHANNEL")
    _safe_https(raw.get("profile_url"), code="INVALID_PARTNER_PROFILE_URL")
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
    u = _safe_https(scan_url, code="INVALID_SCAN_URL")
    parsed = urlsplit(u)
    _require(not parsed.query and not parsed.fragment and not u.endswith("//"),
             "DUPLICATE_OR_INVALID_UTM")
    _require(parsed.hostname != "preview.invalid", "ROUTE_RECEIPT_FOR_PLACEHOLDER")
    return u, True


def _public_packet(packet: dict, now: datetime) -> tuple[dict, dict[str, dict], dict[str, dict]]:
    _require(isinstance(packet, dict), "INVALID_EVENT_PACKET")
    _require(packet.get("public_safe") in ("PUBLIC_SAFE", "APPROVED_PUBLIC", "ALLOWED"),
             "BLOCKED_PUBLIC")
    v = packet.get("verification")
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
    if generation:
        _require(isinstance(packet.get("corrections"), list)
                 and bool(packet["corrections"]), "MISSING_CORRECTION_HISTORY")
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
    sources = _sources(packet, as_of)
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
        "event_time_utc": _iso(event_time),
        "first_observed_at_utc": _iso(first_seen),
        "as_of_utc": _iso(as_of), "expires_at_utc": _iso(expires),
        "publication_time_utc": _iso(_stamp(publication, "PUBLICATION_TIME"))
                                 if publication else None,
        "correction_generation": generation,
        "corrections": packet.get("corrections") or [],
        "missing_data": packet.get("missing_data") or [],
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
        by_id[key] = {"claim_id": key, "text": text, "tickers": related,
                      "source_ids": refs,
                      "topics": row.get("topics") or []}
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
    event_packet: dict, partner_profile: dict, selected_tickers: list[str],
    *, now_utc: datetime, scan_url: str | None = None,
    route_receipt: str | None = None, angle_plan: dict | None = None,
) -> dict:
    """Compile a gated draft. No network, model, publication or side effects.

    Optional AI-assisted angle_plan is a bounded list of existing claim IDs;
    a model can SELECT evidence, never originate source facts or claim text.
    """
    _require(isinstance(now_utc, datetime) and now_utc.tzinfo is not None
             and now_utc.utcoffset() == timedelta(0), "INVALID_NOW")
    now = now_utc.astimezone(_UTC)
    ticks = _ticker_list(selected_tickers)
    event, sources, relations = _public_packet(event_packet, now)
    partner = _partner(partner_profile, now)
    claims = _claims(event_packet, ticks, relations, sources)
    if angle_plan is not None:
        _require(isinstance(angle_plan, dict)
                 and set(angle_plan) == {"selected_claim_ids"},
                 "INVALID_ANGLE_PLAN")
        ids = angle_plan["selected_claim_ids"]
        available = {x["claim_id"] for x in claims}
        _require(isinstance(ids, list) and bool(ids)
                 and len(ids) == len(set(ids)) and set(ids) <= available,
                 "AI_UNGROUNDED_CLAIM_SELECTION")
        claims = [c for ident in ids for c in claims if c["claim_id"] == ident]
        _require(all(any(t in c["tickers"] for c in claims) for t in ticks),
                 "AI_DROPPED_TICKER_EVIDENCE")
    base_url, route_live = _route(scan_url, route_receipt)
    # Reuse the existing funnel link authority, not a second UTM encoder.
    from engine.marketing.links import canonical_link, is_tagged_canonical
    pack_id = "cp_" + hashlib.sha256(
        (event["event_id"] + "|" + str(event["correction_generation"])
         + "|" + partner["slug"] + "|" + ",".join(ticks)
         + "|" + ",".join(c["claim_id"] for c in claims)).encode("utf-8")
    ).hexdigest()[:18]
    tagged = canonical_link(
        "partner-" + partner["slug"], "catalyst_scan", pack_id,
        base_url=base_url, utm_source="partner",
    )
    _require(is_tagged_canonical(tagged, base_url=base_url),
             "CANONICAL_ATTRIBUTION_FAILED")
    _require(not parse_qsl(urlsplit(base_url).query), "DUPLICATE_OR_INVALID_UTM")
    scan_link = tagged + "&event_id=" + quote(event["event_id"], safe="")
    scan_link += "&tickers=" + quote(",".join(ticks), safe="")
    _require(len(dict(parse_qsl(urlsplit(scan_link).query))) == 6
             and len(parse_qsl(urlsplit(scan_link).query)) == 6,
             "DUPLICATE_OR_INVALID_UTM")
    active_sources = {ref: sources[ref] for c in claims for ref in c["source_ids"]}
    # The SVG can only reproduce source material if ALL contributing receipts
    # affirm rehosting. Textual synthesis still requires public display/link.
    media_rights = all(s["public_rehost"] for s in active_sources.values())
    main_source = next(iter(active_sources.values()))
    card_svg = None
    if media_rights:
        from engine.marketing.chart_render import render_breaking_card
        card_svg = render_breaking_card(
            headline=claims[0]["text"], summary=None,
            source_name=main_source["title"],
            source_tier=main_source["tier"],
            published_at=main_source["published_at_utc"],
            tickers=[{"ticker": t} for t in ticks],
            eyebrow="EVENT EVIDENCE", cta=False, suppress_cta=True,
        )
        _require(isinstance(card_svg, str)
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
        f'- [{s["title"]}]({s["url"]}) ({s["published_at_utc"]})'
        for s in ordered_sources
    ]
    newsletter_lines = [
        f'# {event["primary_subject"]}: sourced event brief',
        "",
        partner["disclosure"], "",
        f'For readers following {partner["audience"]}, this note tracks '
        + ", ".join(ticks) + " against the same event evidence.",
        "",
        "## Confirmed observations", "",
    ]
    newsletter_lines += [
        f'- {c["text"]} [Evidence {c["claim_id"]}; '
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
            "- " + _atom(m, "INVALID_MISSING_DATA", 300)
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
    social_head = event["event_kind"].replace("_", " ").capitalize()
    social_head += " evidence for " + " ".join("$" + t for t in ticks)
    social_body = (
        "Partner concept; no endorsement. " if partner["status"] == "candidate"
        else "Partner distribution with " + partner["name"] + ". "
    )
    social = social_head + "\n" + social_body + scan_link
    _require(len(social) <= 275, "SOCIAL_CHARACTER_BUDGET")
    # Existing publisher/press lexicons and the shared social copy validator.
    from engine.marketing.copywriter import build_context, validate_copy
    from engine.press.validators import (
        check_advice_lexicon, check_banned_lexicon, check_cheese_test,
    )
    ctx = build_context({"type": "chart", "ticker": ticks[0],
                         "account": partner["slug"]})
    violations = validate_copy(social_head, social_body.rstrip(), ctx)
    _require(not violations, "SOCIAL_COPY_REJECTED")
    draft = {"title": event["primary_subject"],
             "body": "<p>" + html.escape(" ".join(c["text"] for c in claims))
                     + "</p>"}
    for gate in (check_banned_lexicon, check_advice_lexicon, check_cheese_test):
        _require(gate(draft, {}, {}).get("passed") is True,
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
        "media_status": "READY_FOR_REVIEW" if media_rights
                        else "REHOST_RIGHTS_BLOCKED",
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
    page = env.get_template(template_path.name).render(pack=pack)
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
    written: list[Path] = []
    for name, data in files.items():
        target = base / name
        temp = base / ("." + name + ".tmp")
        temp.write_text(data, encoding="utf-8")
        temp.replace(target)
        written.append(target)
    return written
