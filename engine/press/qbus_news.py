"""Private Press grounding from the existing, permission-qualified qbus reader.

This module neither publishes nor owns security identity. Each provider attempt
qualifies the incumbent universe and blog_draft receipts at its actual call time.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata
from urllib.parse import urlsplit

SOURCE_PREFIX = "qbus-news:"
SLOT_PREFIX = "press-qbus-news-"
RAIL = "private_qbus_news"


class PrivateNewsUnavailable(ValueError):
    """A private candidate cannot qualify; the caller must not invoke its writer."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_source_url(value: object) -> str | None:
    """Project a source link into trusted prompt text without repairing it.

    Check the original bytes before urlsplit, which silently discards some
    controls. Rejected source URLs remain only in private bundle provenance.
    """
    if not isinstance(value, str) or not value or "\\" in value or any(
        char.isspace() or unicodedata.category(char).startswith("C") for char in value
    ):
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme.lower() not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.netloc.endswith(":")
        ):
            return None
        # Accessing port validates non-numeric, malformed and out-of-range ports.
        _ = parts.port
    except ValueError:
        return None
    return value


def private_slot(slot: dict) -> dict:
    """Give a copy its own private identity; never alter the planner's original."""
    if (
        not isinstance(slot, dict)
        or any(not isinstance(slot.get(key), str) or not slot[key]
               for key in ("id", "desk", "as_of"))
        or not isinstance(slot.get("story"), dict)
    ):
        raise PrivateNewsUnavailable("qbus_draft_invalid_slot")
    for key in ("sources", "seed_refs", "allowed_links"):
        value = slot.get(key)
        if value is not None and (
            not isinstance(value, list) or any(not isinstance(item, str) for item in value)
        ):
            raise PrivateNewsUnavailable(f"qbus_draft_invalid_slot_collection:{key}")
    for key in ("facts", "raw_documents"):
        value = slot.get(key)
        if value is not None and (
            not isinstance(value, list) or any(not isinstance(item, dict) for item in value)
        ):
            raise PrivateNewsUnavailable(f"qbus_draft_invalid_slot_collection:{key}")
    revisions = slot.get("source_revisions")
    if revisions is not None and (
        not isinstance(revisions, dict)
        or any(not isinstance(ref, str) or not isinstance(revision, str)
               for ref, revision in revisions.items())
    ):
        raise PrivateNewsUnavailable("qbus_draft_invalid_slot_collection:source_revisions")
    if is_private_stage({"slot": slot}):
        raise PrivateNewsUnavailable("qbus_draft_requires_original_planned_slot")
    result = copy.deepcopy(slot)
    result["qbus_news_origin_slot_id"] = slot["id"]
    digest = hashlib.sha256(slot["id"].encode()).hexdigest()[:24]
    result["id"] = SLOT_PREFIX + digest
    result["publication_authorized"] = False
    result["qbus_news_rail"] = RAIL
    # Survives removal of the superficial permission/provenance flags.
    marker = SOURCE_PREFIX + "candidate:" + digest
    result["sources"] = list(dict.fromkeys([*(result.get("sources") or []), marker]))
    result["seed_refs"] = list(dict.fromkeys([*(result.get("seed_refs") or []), marker]))
    return result


def is_private_stage(item: object) -> bool:
    """Refuse private qbus copy even if its permission flag was removed."""
    if not isinstance(item, dict):
        return False
    slot = item.get("slot")
    for holder in [item] + ([slot] if isinstance(slot, dict) else []):
        if (
            str(holder.get("id") or "").startswith(SLOT_PREFIX)
            or holder.get("qbus_news_rail") == RAIL
            or "qbus_news_evidence" in holder
        ):
            return True
        for key in ("sources", "seed_refs"):
            refs = holder.get(key)
            if isinstance(refs, str):
                refs = [refs]
            elif not isinstance(refs, (dict, list, tuple, set)):
                refs = []
            if any(isinstance(ref, str) and ref.startswith(SOURCE_PREFIX)
                   for ref in refs):
                return True
        for key in ("facts", "raw_documents"):
            facts = holder.get(key)
            if isinstance(facts, (dict, str)):
                facts = [facts]
            elif not isinstance(facts, (list, tuple, set)):
                facts = []
            if any(
                (isinstance(fact, dict) and str(fact.get("ref") or "").startswith(SOURCE_PREFIX))
                or (isinstance(fact, str) and fact.startswith(SOURCE_PREFIX))
                for fact in facts
            ):
                return True
        revisions = holder.get("source_revisions")
        if isinstance(revisions, str):
            revisions = [revisions]
        elif not isinstance(revisions, (dict, list, tuple, set)):
            revisions = []
        if any(isinstance(ref, str) and ref.startswith(SOURCE_PREFIX) for ref in revisions):
            return True
    return False


def _binding(slot: dict, universe_path, now: datetime) -> dict:
    from engine.company_intelligence.contracts import ContractError, safe_ticker
    from engine.qbus_news_universe import qualify_universe

    # The qbus store is current-state, not an as-of replay. Date-only UTC scope
    # is explicit so a past research run cannot borrow today's corrected news.
    if slot.get("as_of") != now.date().isoformat():
        raise PrivateNewsUnavailable("qbus_draft_requires_current_utc_date")
    tickers = (slot.get("story") or {}).get("tickers")
    if not isinstance(tickers, list) or not tickers or not all(isinstance(t, str) for t in tickers):
        raise PrivateNewsUnavailable("qbus_draft_requires_explicit_ticker")
    try:
        normalized = {safe_ticker(ticker) for ticker in tickers}
    except ContractError:
        raise PrivateNewsUnavailable("qbus_draft_invalid_ticker") from None
    if len(normalized) != 1:
        raise PrivateNewsUnavailable("qbus_draft_requires_one_ticker")
    ticker = next(iter(normalized))
    try:
        snapshot = json.loads(Path(universe_path).read_text(encoding="utf-8"))
        qualified = qualify_universe(snapshot, asof=now)
    except (OSError, ValueError, TypeError):
        raise PrivateNewsUnavailable("qbus_draft_universe_unavailable") from None
    if qualified.status != "qualified":
        raise PrivateNewsUnavailable("qbus_draft_universe_unqualified")
    # Match the serving path's case-insensitive ambiguity check after the
    # canonical universe owner has qualified economic and knowledge clocks.
    hits = {binding.security_id for binding in qualified.alias_bindings
            if binding.alias.upper() == ticker.upper()}
    if len(hits) != 1:
        raise PrivateNewsUnavailable("qbus_draft_ticker_unresolved_or_ambiguous")
    security_id = next(iter(hits))
    security = next(s for s in qualified.securities if s.security_id == security_id)
    return {
        "ticker": ticker, "security_id": security_id,
        "universe_owner": qualified.owner, "universe_revision": qualified.revision,
        "universe_asof": qualified.asof.isoformat(),
        "security_known_at": security.known_at.isoformat(),
    }


def _fresh_rights(bundle: dict, receipt_paths, now: datetime) -> None:
    """Do not carry a permission changed during the database read to the writer."""
    from engine.qbus_news_receipts import combine_news_rights, load_rights_set

    receipts = tuple(receipt for receipt in load_rights_set(
        receipt_paths, now=now, audience="blog_draft"
    ) if receipt.derivative_processing)
    rights = combine_news_rights(receipts)
    sources = {report["source"] for story in bundle["stories"] for report in story["reports"]}
    refs = [
        {"receipt_id": receipt.receipt_id, "source": receipt.source,
         "provider": receipt.provider, "audience": receipt.audience,
         "expires_at": receipt.expires_at.isoformat()}
        for receipt in receipts if receipt.source in sources
    ]
    if refs != bundle["receipt_refs"]:
        raise PrivateNewsUnavailable("qbus_draft_rights_changed")
    for story in bundle["stories"]:
        for report in story["reports"]:
            source = report["source"]
            if source not in rights.allowed_sources or any(
                report.get(field) and not rights.allows(source, field)
                for field in ("title", "url", "teaser")
            ):
                raise PrivateNewsUnavailable("qbus_draft_rights_changed")


def prepare_slot(slot: dict, *, database, universe_path, receipt_paths) -> dict:
    """Fresh, bounded evidence for one writer call; never enrich an earlier copy."""
    from engine.qbus_news_context import news_evidence_bundle
    from engine.qbus_news_quality import publisher_identity

    current = _utcnow()
    binding = _binding(slot, universe_path, current)
    try:
        bundle = news_evidence_bundle(
            database=database, security_id=binding["security_id"],
            receipt_paths=receipt_paths, audience="blog_draft", now=current, limit=3,
        )
    except (OSError, ValueError, sqlite3.Error):
        raise PrivateNewsUnavailable("qbus_draft_evidence_unavailable") from None
    if bundle["state"] != "available" or not bundle["stories"]:
        raise PrivateNewsUnavailable("qbus_draft_evidence_restricted_or_empty")

    result = private_slot(slot)
    result["qbus_news_evidence"] = bundle
    result["qbus_news_binding"] = binding
    result["facts"] = list(result.get("facts") or [])
    result["raw_documents"] = list(result.get("raw_documents") or [])
    links = list(result.get("allowed_links") or [])
    for story in bundle["stories"]:
        for report in story["reports"]:
            identity = json.dumps(
                [report["source"], report["source_item_id"], report["revision_id"]],
                ensure_ascii=False, separators=(",", ":"),
            )
            ref = SOURCE_PREFIX + hashlib.sha256(identity.encode()).hexdigest()
            title, teaser = report["title"], report["teaser"]
            text = title + ("\n" + teaser if teaser else "")
            safe_url = _safe_source_url(report["url"])
            publisher = publisher_identity(report["source"], safe_url or "")
            limits = [
                "Third-party publisher reporting; retain attribution and differing accounts.",
                "Current-state context, not a historical replay or an independent confirmation.",
            ]
            if bundle["has_more"] or story["reports_truncated"] or report["teaser_truncated"]:
                limits.append("The supplied news evidence is incomplete.")
            result["facts"].append({
                "id": ref, "ref": ref, "tier": "third_party", "values": [],
                "text": text, "source_name": publisher, "url": safe_url,
                "dated": (report["published_at"] or "")[:10] or None,
                "context_relevance": " ".join(limits),
            })
            result["raw_documents"].append({"ref": ref, "text": text})
            result["sources"].append(ref)
            result["seed_refs"].append(ref)
            if safe_url:
                links.append(safe_url)
    result["allowed_links"] = list(dict.fromkeys(links))

    return result


def verify_slot(slot: dict, *, universe_path, receipt_paths) -> None:
    """Last check after checkpoint IO and directly before the provider call."""
    checked_at = _utcnow()
    binding = slot["qbus_news_binding"]
    if _binding(slot, universe_path, checked_at) != {
        **binding, "universe_asof": checked_at.isoformat()
    }:
        raise PrivateNewsUnavailable("qbus_draft_identity_changed")
    try:
        _fresh_rights(slot["qbus_news_evidence"], receipt_paths, checked_at)
    except (OSError, ValueError):
        raise PrivateNewsUnavailable("qbus_draft_rights_changed") from None
