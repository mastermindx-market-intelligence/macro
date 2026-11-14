"""Revision-bound evidence for the existing Brief/research/editorial consumers.

This is a read adapter to qbus, not a generator, job queue, cache or publisher.
Each use needs an explicitly permitted audience and derivative-processing grant.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os

from engine.qbus_news_receipts import (
    combine_news_rights, load_rights_set, load_health_receipt,
    scope_news_health, news_delivery_state,
)
from engine.qbus_news_store import NewsStore

AUDIENCES = frozenset({"site_full", "internal_research", "blog_draft", "marketing_draft"})


def news_evidence_health(*, rights, now: datetime, row_count: int, health_receipt_path=None) -> dict:
    """Observe delivery separately from the immutable report/rights evidence basis."""
    path = health_receipt_path
    if path is None:
        path = os.environ.get("MM_TICKER_NEWS_HEALTH", "").strip() or None
    health = scope_news_health(load_health_receipt(path, now=now), rights)
    state = news_delivery_state(health, row_count=row_count)
    if state == "live":
        note = "News delivery is live for the permitted source view; individual report dates still apply."
    elif state == "quiet":
        note = "No permitted reports in this snapshot; this does not establish that no news exists."
    else:
        note = (
            f"News delivery is {state}; retained reports do not establish current or complete coverage."
        )
    return {"health": health, "delivery_state": state, "coverage_note": note}


def news_evidence_bundle(
    *, database, security_id: str, receipt_paths, audience: str,
    now: datetime | None = None, limit: int = 20, health_receipt_path=None,
) -> dict:
    if audience not in AUDIENCES:
        raise ValueError("unsupported_news_evidence_audience")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 40:
        raise ValueError("invalid_news_evidence_limit")
    current = now if now is not None else datetime.now(timezone.utc)
    # Load/qualify all carriers before derivative filtering so a revoked or
    # conflicting policy cannot disappear and accidentally leave a grant active.
    receipts = load_rights_set(receipt_paths, now=current, audience=audience)
    receipts = tuple(receipt for receipt in receipts if receipt.derivative_processing)
    rights = combine_news_rights(receipts)
    result = {
        "schema": "qbus.news_evidence.v1", "audience": audience,
        "security_id": security_id, "observed_at": current.isoformat(),
        "state": "restricted", "stories": [], "has_more": False,
        "receipt_refs": [], "evidence_sha256": None,
        "publication_authorized": False,
        "health": None, "delivery_state": "restricted",
        "coverage_note": "No derivative news evidence is permitted for this audience.",
    }
    if not rights.allowed_sources:
        return result
    with NewsStore.open_readonly(database, source_key="news-evidence-read") as store:
        evidence = store.evidence_for_security(security_id, limit=limit, rights=rights)
    result.update(state="available", stories=evidence["stories"], has_more=evidence["has_more"])
    # state=available means readable retained evidence, never a live-feed claim.
    result.update(news_evidence_health(
        rights=rights, now=current, row_count=len(result["stories"]),
        health_receipt_path=health_receipt_path,
    ))
    sources = {report["source"] for story in result["stories"] for report in story["reports"]}
    result["receipt_refs"] = [
        {"receipt_id": receipt.receipt_id, "source": receipt.source,
         "provider": receipt.provider, "audience": receipt.audience,
         "expires_at": receipt.expires_at.isoformat()}
        for receipt in receipts if receipt.source in sources
    ]
    # A heartbeat/coverage change must not rewrite a saved research evidence basis.
    identity = {key: result[key] for key in ("schema", "audience", "security_id", "stories", "receipt_refs")}
    result["evidence_sha256"] = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return result
