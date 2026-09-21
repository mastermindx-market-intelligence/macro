"""Discovery: enumerate MarketDesk papers, dedup against SQLite, score, persist.

Primary path uses the JSON API browse-tree (deterministic, robust). The ``latest`` /
``picks`` / ``saved`` feeds are merged in for freshness + membership flags. Every new
paper is scored (``score.py``) and upserted as ``DISCOVERED``; already-seen papers are
counted as ``SKIPPED_SEEN`` and left untouched.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import db
from .config import Config
from .filters import classify_exclusion_tagged, default_tagged_patterns
from .marketdesk import MarketDeskClient, SessionExpired, build_meta
from .publish_vault import extra_title, looks_truncated
from .schemas import ArticleMeta, Status
from .score import compute_priority
from .utils import get_logger, normalize_ws

log = get_logger("discover")


@dataclass
class DiscoverResult:
    new: list[ArticleMeta] = field(default_factory=list)
    discovered_new: int = 0
    skipped_seen: int = 0
    total_scanned: int = 0
    healed: int = 0
    excluded: int = 0

    def summary(self) -> str:
        return (
            f"scanned={self.total_scanned} new={self.discovered_new} "
            f"skipped_seen={self.skipped_seen} excluded={self.excluded} "
            f"healed={self.healed}"
        )


def _feed_flags(client: MarketDeskClient) -> tuple[set[str], set[str], set[str]]:
    """Best-effort membership sets for latest / picks / saved.

    Best-effort covers a flaky feed, NOT a dead session: ``SessionExpired``
    propagates so the caller parks the account. Swallowing it here would restore
    the original defect one layer up — empty flag sets plus an empty walk read as
    a quiet day, and the daemon keeps ticking politely against a logged-out site.
    """
    def safe(fn) -> set[str]:
        try:
            return set(fn())
        except SessionExpired:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("feed fetch failed: %s", e)
            return set()
    return safe(client.latest), safe(client.picks), safe(client.saved)


def discover(
    cfg: Config,
    conn,
    client: MarketDeskClient,
    *,
    limit: int | None = None,
    since_hours: int | None = None,
    backfill: bool = False,
    fetch_summary: bool = True,
    heal_limit: int = 50,
) -> DiscoverResult:
    now = int(time.time())
    limit = limit or cfg.max_articles_per_run

    if since_hours is not None:
        since_unix: int | None = now - since_hours * 3600
        max_days = max(2, since_hours // 24 + 2)
    elif backfill:
        since_unix, max_days = None, 400
    else:
        since_unix, max_days = None, 3  # default: newest few days -> "top N visible"

    latest_ids, pick_ids, saved_ids = _feed_flags(client)
    log.info(
        "discovery: limit=%s since_hours=%s backfill=%s (latest=%d picks=%d saved=%d)",
        limit, since_hours, backfill, len(latest_ids), len(pick_ids), len(saved_ids),
    )

    result = DiscoverResult()
    seen_this_run: set[str] = set()

    # exclusion filter rules (resolved once per run from config).
    exclude_institutions = set(cfg.exclude_institutions)
    exclude_patterns = (
        default_tagged_patterns() if cfg.exclude_title_patterns_enabled else []
    )

    def self_heal(blob_id: str, row) -> None:
        """Backfill a paper first seen before its data was ready.

        MarketDesk generates the AI summary ASYNCHRONOUSLY (so a freshly-posted
        paper is discovered with none) and ships some titles truncated (dropped
        ``.EX)`` suffix). Because a seen blob_id short-circuits before item_extra
        is ever called again — and cleanup preserves the "seen" memory — such a
        paper would otherwise be stuck forever. Re-fetch ``/extra`` ONCE (capped
        per run) and push the fix; if it was already vaulted, null ``vaulted_at``
        so the vault pass re-publishes the corrected sidecar (JSON only)."""
        if not fetch_summary or result.healed >= heal_limit:
            return
        cur_summary = (row["marketdesk_summary"] or "").strip()
        cur_title = row["title"] or ""
        need_summary = not cur_summary
        need_title = looks_truncated(cur_title)
        if not (need_summary or need_title):
            return
        extra = client.item_extra(blob_id) or {}
        updates: dict = {}
        if need_summary:
            s = extra.get("summary")
            if s and str(s).strip():
                updates["marketdesk_summary"] = normalize_ws(str(s))
        if need_title:
            t = extra_title(extra, cur_title)
            if t:
                updates["title"] = t
        if not updates:
            return
        db.update_fields(conn, blob_id, **updates)
        if row["vault_key"]:                     # already vaulted → queue re-publish
            db.update_fields(conn, blob_id, vaulted_at=None)
        result.healed += 1
        log.info("self-heal %s: %s", blob_id, ",".join(sorted(updates)))

    def handle(item: dict) -> bool:
        """Process one paper dict. Returns True if a NEW row was created."""
        blob_id = item.get("pathId")
        if not blob_id or blob_id in seen_this_run:
            return False
        seen_this_run.add(blob_id)
        result.total_scanned += 1
        existing = db.get_by_blob_id(conn, blob_id)
        if existing is not None:
            result.skipped_seen += 1
            self_heal(blob_id, existing)
            return False

        # EXCLUSION FILTER: decide from cheap already-known metadata (institution +
        # title) BEFORE the AI-summary fetch, so an excluded paper never costs an
        # /extra API call. Record it (so we know it exists + can re-include later)
        # but mark it terminal SKIPPED_EXCLUDED — never a download candidate.
        reason = classify_exclusion_tagged(
            item.get("institution"), item.get("name"),
            exclude_institutions=exclude_institutions,
            tagged_patterns=exclude_patterns,
        )
        if reason is not None:
            meta = build_meta(
                cfg, item, summary=None,
                is_latest=blob_id in latest_ids,
                is_top_pick=blob_id in pick_ids,
                is_saved=blob_id in saved_ids,
            )
            meta.local_priority_score = compute_priority(meta, cfg.watchlist)
            db.upsert_discovered(conn, meta)
            db.set_status(conn, blob_id, Status.SKIPPED_EXCLUDED)
            result.excluded += 1
            log.debug("excluded %s (%s): %s", blob_id, reason, meta.title)
            return True

        summary = None
        if fetch_summary:
            summary = (client.item_extra(blob_id) or {}).get("summary")
        meta = build_meta(
            cfg, item, summary=summary,
            is_latest=blob_id in latest_ids,
            is_top_pick=blob_id in pick_ids,
            is_saved=blob_id in saved_ids,
        )
        meta.local_priority_score = compute_priority(meta, cfg.watchlist)
        db.upsert_discovered(conn, meta)
        result.new.append(meta)
        result.discovered_new += 1
        return True

    # 1) browse-tree walk (comprehensive, newest-first)
    for item in client.walk_papers(since_unix=since_unix, limit=limit, max_days=max_days):
        handle(item)
        if result.discovered_new >= limit:
            break

    # 2) latest-feed merge (catch the newest handful the tree index may lag on)
    if result.discovered_new < limit and latest_ids:
        fresh = [i for i in latest_ids if i not in seen_this_run
                 and not db.exists_blob_id(conn, i)]
        if fresh:
            for item in client.provision(fresh):
                if item.get("type") == "application/pdf":
                    handle(item)
                    if result.discovered_new >= limit:
                        break

    log.info("discovery done: %s", result.summary())
    return result
