"""scripts/marketing_metrics_poll.py — D02 per-post metrics poller.

Reads back per-post analytics for recently-posted marketing items and appends
them to an append-only ledger. Posts today are fire-and-forget: this closes the
loop so the admin console can show impressions/likes/reposts/comments/clicks and
the post's public x.com permalink (which createPost never returns).

DARK BY DEFAULT — exactly like scripts/marketing_publisher.py. With BUFFER_TOKEN
unset the poller prints one line and exits 0 (no network, no ledger write), so
the marketing-publish workflow can run it unconditionally after the publish step.

Sources of "what to poll" (deduped by remote id = Buffer post id):
  * data/marketing/outbox/status_ledger.jsonl — every `posted` transition
    carries receipt.external_id (the Buffer post id) and the row `at`.
  * data/marketing/publications.jsonl — the publications bridge; rows carry
    remote_id (platform post id) + account + published_at.
Only posts newer than --max-age-days (default 7, matching the Sentinel
receipt-age window) are polled; older analytics have stopped moving.

Output — append-only data/marketing/post_metrics.jsonl, one row per
(remote_id, poll date):
  {remote_id, account, external_url, metrics: {impressions?, likes?, reposts?,
   comments?, clicks?, engagement_rate?}, metrics_raw: [{type,name,value,unit}],
   metrics_updated_at, polled_at, ok, note?}
Re-runs re-poll (metrics refresh ~daily); a same-day re-run overwrites nothing —
each run appends a fresh dated row (append-only ledger law). Empty/absent
metrics produce an honest row with metrics={} and a note.

external_url backfill: when a polled post's publications.jsonl row lacks an
external_url and Buffer returns one, the appended metrics row carries it. We do
NOT rewrite publications.jsonl (append-only) — the metrics ledger is the
external_url of record for the console join.

Usage:
    # dry-run (default network-free listing of what WOULD be polled)
    python -m scripts.marketing_metrics_poll --dry-run

    # live poll (needs BUFFER_TOKEN in env; dark/no-op without it)
    BUFFER_TOKEN=... python -m scripts.marketing_metrics_poll
    BUFFER_TOKEN=... python -m scripts.marketing_metrics_poll --max-age-days 7
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

log = logging.getLogger("marketing_metrics_poll")


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrapping helpers (mirror scripts/marketing_publisher.py)
# ─────────────────────────────────────────────────────────────────────────────

def _code_root() -> Path:
    """Directory containing engine/ — always where this script lives (../)."""
    return Path(__file__).resolve().parent.parent


def _data_root(root_arg: str | None) -> Path:
    return Path(root_arg) if root_arg is not None else _code_root()


#: A Buffer refusal that is about the TOKEN, not about the post. Matched on the
#: error text because `fetch_post_metrics` collapses transport, HTTP and GraphQL
#: failures into one `error` string — there is no status code to branch on by
#: the time it reaches here. Deliberately broad: a false positive costs one
#: deferred poll, a false negative costs the day's posting allowance.
_RATE_LIMIT_MARKERS: tuple[str, ...] = (
    "429", "rate limit", "rate-limit", "ratelimit",
    "too many requests", "retry-after", "quota",
)


def _is_rate_limited(error: object) -> bool:
    """True when this failure means the shared token is throttled."""
    text = str(error or "").lower()
    return any(m in text for m in _RATE_LIMIT_MARKERS)


#: Per-run ceiling on Buffer metric calls. Metrics refresh roughly daily, so
#: polling one post on all 30 sweeps buys nothing and spends the posting budget
#: 30x over. Sized so a full day of polling stays a small fraction of the token's
#: allowance even if the once-a-day workflow gate is ever removed.
#:
#: 25 -> 8 (2026-08-11). The cap must stay WELL under the Buffer plan's daily API
#: allowance, because the publisher posts on this same token and a call spent
#: here is a post refused there — measured: run 31453875632 took `429 retry after
#: 37768s` on a live post attempt, and that retry-after resolves to the previous
#: day's metrics poll + 24h. The workflow gate had also been double-firing, so
#: the real spend was 2x this number. Eight covers the freshest posts (the target
#: list is newest-first) and the rest keep until tomorrow — this loop stops and
#: keeps rather than dropping, so a capped run loses nothing but latency.
_MAX_CALLS_PER_RUN = 8
# Rolling budget across every workflow sweep. This preserves the previous
# eight-calls-per-day ceiling while removing the brittle wall-clock slot.
_MAX_CALLS_PER_24H = 8
_RECONCILE_INTERVAL_H = 24


def _metrics_ledger_path(root: Path) -> Path:
    return root / "data" / "marketing" / "post_metrics.jsonl"


def _publications_path(root: Path) -> Path:
    return root / "data" / "marketing" / "publications.jsonl"


def _configured_channel_ids(root: Path) -> dict[str, str]:
    """Account → Buffer channel id from the existing marketing config.

    Read-only and fail-soft. A missing account mapping does not invent an
    identity; the provider adapter still verifies the post id and the response's
    own channelId/channel.id pair. Lane B retains ownership of the config file.
    """
    try:
        import yaml  # noqa: PLC0415

        raw = yaml.safe_load((root / "config" / "marketing.yml").read_text(
            encoding="utf-8")) or {}
        publish = raw.get("publish") if isinstance(raw, dict) else {}
        channels = publish.get("channels") if isinstance(publish, dict) else {}
        if not isinstance(channels, dict):
            return {}
        return {
            str(account): str(channel_id).strip()
            for account, channel_id in channels.items()
            if str(account).strip() and str(channel_id or "").strip()
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("configured channel read failed: %s", exc)
        return {}


_ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_iso(ts: str | None) -> datetime | None:
    """Parse an iso8601-ish timestamp to an aware UTC datetime, or None."""
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    # Tolerate a trailing Z and fractional seconds; fall back to date-only.
    for candidate in (s, s.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Gather targets — dedupe by remote id across both ledgers
# ─────────────────────────────────────────────────────────────────────────────

def gather_targets(root: Path, *, now: datetime, max_age_days: int) -> list[dict]:
    """Collect {remote_id, account, source_ts, external_url} rows to poll.

    Deduped by remote_id (Buffer post id). status_ledger.jsonl wins the account
    field when both sources carry the same id (the outbox is the actuation
    source of truth). Only ids whose source timestamp is within max_age_days of
    `now` are returned. Fail-soft: unreadable ledgers contribute nothing.
    """
    from engine.marketing import outbox as _outbox  # noqa: PLC0415
    from engine.marketing.ledgers import read_jsonl  # noqa: PLC0415

    cutoff = now - timedelta(days=max_age_days)
    by_id: dict[str, dict] = {}

    # (1) Outbox status ledger: posted transitions carry receipt.external_id.
    try:
        state = _outbox.fold_state(root)
        items = state.get("items") or {}
        last = state.get("last") or {}
        status = state.get("status") or {}
        for iid, st in status.items():
            if st != "posted":
                continue
            lr = last.get(iid) or {}
            rec = lr.get("receipt")
            rec = rec if isinstance(rec, dict) else {}
            remote_id = str(rec.get("external_id") or "").strip()
            if not remote_id:
                continue
            src_ts = _parse_iso(rec.get("at") or lr.get("at"))
            if src_ts is None or src_ts < cutoff:
                continue
            it = items.get(iid) or {}
            by_id[remote_id] = {
                "remote_id": remote_id,
                "account": it.get("account", "") or "",
                "source_ts": src_ts,
                "external_url": (rec.get("external_url") or None),
                "origin": "status_ledger",
            }
    except Exception as exc:  # noqa: BLE001
        log.warning("gather_targets: outbox ledger read failed: %s", exc)

    # (2) Publications bridge ledger: rows carry remote_id + account.
    try:
        pub_rows = [r for r in read_jsonl(_publications_path(root)) if isinstance(r, dict)]
        # A post RECALLED before it sent (scripts/marketing_recall.py) leaves a
        # `retracted` correction row beside its original `clean` one — the ledger
        # is append-only, so both survive. It never reached X, so it has no
        # analytics to poll and asking Buffer for them would be noise at best.
        # Collected up front because the retraction is appended AFTER the row it
        # corrects, so an in-order scan would have already admitted the post.
        retracted = {
            str(r.get("remote_id") or "").strip()
            for r in pub_rows
            if str(r.get("correction_state") or "") == "retracted"
        } - {""}
        for rid in retracted & set(by_id):
            del by_id[rid]

        for row in pub_rows:
            remote_id = str(row.get("remote_id") or "").strip()
            if not remote_id or remote_id in retracted:
                continue
            src_ts = _parse_iso(row.get("published_at"))
            if src_ts is None or src_ts < cutoff:
                continue
            if remote_id in by_id:
                # Outbox already claimed this id; only backfill a missing url.
                if not by_id[remote_id].get("external_url") and row.get("external_url"):
                    by_id[remote_id]["external_url"] = row.get("external_url")
                continue
            by_id[remote_id] = {
                "remote_id": remote_id,
                "account": row.get("account", "") or "",
                "source_ts": src_ts,
                "external_url": (row.get("external_url") or None),
                "origin": "publications",
            }
    except Exception as exc:  # noqa: BLE001
        log.warning("gather_targets: publications ledger read failed: %s", exc)

    return sorted(by_id.values(), key=lambda r: r["source_ts"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Due-since-success reconciliation
# ─────────────────────────────────────────────────────────────────────────────

def _reconciliation_due_state(
    root: Path,
    targets: list[dict],
    *,
    now: datetime,
    interval_hours: int = _RECONCILE_INTERVAL_H,
) -> tuple[list[dict], int, int]:
    """Return (due targets, fresh count, calls in the last rolling 24h).

    Success is per provider id and requires both the transport/GraphQL result
    and the normalized delivery observation to be successful. There is no global
    watermark: an unfinished target stays due even when siblings complete. Every
    attempted network read writes one row, so all rows with a recent valid
    ``polled_at`` count against the rolling budget, including failures.
    """
    from engine.marketing.ledgers import read_jsonl  # noqa: PLC0415

    rows = read_jsonl(_metrics_ledger_path(root))
    latest_success: dict[str, datetime] = {}
    recent_calls = 0
    rolling_cutoff = now - timedelta(hours=24)
    success_cutoff = now - timedelta(hours=max(1, int(interval_hours)))
    future_tolerance = now + timedelta(minutes=5)

    for row in rows:
        if not isinstance(row, dict):
            continue
        polled_at = _parse_iso(row.get("polled_at"))
        if polled_at is None or polled_at > future_tolerance:
            continue
        if polled_at >= rolling_cutoff:
            recent_calls += 1

        remote_id = str(row.get("remote_id") or "").strip()
        delivery = row.get("delivery")
        if (not remote_id or row.get("ok") is not True
                or not isinstance(delivery, dict)
                or delivery.get("read_ok") is not True
                or str(delivery.get("provider_id") or "").strip() != remote_id):
            continue
        observed_at = _parse_iso(delivery.get("observed_at")) or polled_at
        if observed_at > future_tolerance:
            continue
        prior = latest_success.get(remote_id)
        if prior is None or observed_at > prior:
            latest_success[remote_id] = observed_at

    due: list[dict] = []
    fresh = 0
    for target in targets:
        remote_id = str(target.get("remote_id") or "").strip()
        last_success = latest_success.get(remote_id)
        if last_success is not None and last_success >= success_cutoff:
            fresh += 1
        else:
            due.append(target)

    def _due_key(target: dict) -> tuple[datetime, str]:
        remote_id = str(target.get("remote_id") or "").strip()
        obligation_at = latest_success.get(remote_id) or target.get("source_ts")
        if not isinstance(obligation_at, datetime):
            obligation_at = _parse_iso(str(obligation_at or ""))
        if obligation_at is None:
            obligation_at = datetime.min.replace(tzinfo=timezone.utc)
        elif obligation_at.tzinfo is None:
            obligation_at = obligation_at.replace(tzinfo=timezone.utc)
        return obligation_at, remote_id

    due.sort(key=_due_key)
    return due, fresh, recent_calls


# ─────────────────────────────────────────────────────────────────────────────
# Bounded one-item provider delivery readback
# ─────────────────────────────────────────────────────────────────────────────

def delivery_readback(
    root: Path,
    *,
    item_id: str,
    now: datetime | None = None,
    publisher=None,
) -> dict:
    """Read one canonically accepted outbox item from Buffer without mutation.

    The caller supplies an outbox item id, not an arbitrary provider id. The
    canonical fold binds that item to its accepted receipt, account, and the
    account's configured channel before any provider call. This path never
    appends to ``post_metrics.jsonl``, never transitions the outbox, and contains
    no create/schedule/edit/delete/retry operation.
    """
    from engine.marketing import outbox as _outbox  # noqa: PLC0415
    from engine.marketing.social_publisher import (  # noqa: PLC0415
        BUFFER_TOKEN_ENV, BufferPublisher,
    )

    ts_now = now if now is not None else datetime.now(timezone.utc)
    observed_at = ts_now.strftime(_ISO_FMT)
    iid = str(item_id or "").strip()
    result: dict = {
        "ok": False,
        "read_only": True,
        "network_attempted": False,
        "item_id": iid or None,
        "observed_at": observed_at,
    }
    if not iid:
        result["error"] = "empty_item_id"
        return result

    try:
        state = _outbox.fold_state(root)
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"outbox_read_failed: {str(exc)[:300]}"
        return result

    item = (state.get("items") or {}).get(iid)
    if not isinstance(item, dict):
        result["error"] = "item_not_found"
        return result

    outbox_status = str((state.get("status") or {}).get(iid) or "")
    result["outbox_status"] = outbox_status or None
    result["account"] = str(item.get("account") or "").strip() or None
    if outbox_status != "posted":
        result["error"] = "item_not_provider_accepted"
        return result

    row = (state.get("last") or {}).get(iid) or {}
    receipt = row.get("receipt")
    receipt = receipt if isinstance(receipt, dict) else {}
    provider_id = str(receipt.get("external_id") or "").strip()
    backend = str(receipt.get("backend") or "").strip()
    accepted_at = str(
        receipt.get("at") or row.get("at") or ""
    ).strip() or None
    booked_at = str(receipt.get("booked_at") or "").strip() or None
    result["provider_id"] = provider_id or None
    result["acceptance"] = {
        "outbox_status": outbox_status,
        "backend": backend or None,
        "accepted_at": accepted_at,
        "booked_at": booked_at,
        "external_url": receipt.get("external_url") or None,
    }
    if backend != "buffer":
        result["error"] = "unsupported_provider_backend"
        return result
    if not provider_id:
        result["error"] = "accepted_receipt_missing_provider_id"
        return result

    account = str(item.get("account") or "").strip()
    expected_channel_id = _configured_channel_ids(root).get(account)
    result["expected_channel_id"] = expected_channel_id or None
    if not expected_channel_id:
        result["error"] = "configured_channel_id_unavailable"
        return result

    pub = publisher
    if pub is None:
        token = os.environ.get(BUFFER_TOKEN_ENV, "").strip()
        if not token:
            result["error"] = "buffer_token_unavailable"
            return result
        pub = BufferPublisher(token=token)

    result["network_attempted"] = True
    response = pub.fetch_post_metrics(
        provider_id, expected_channel_id=expected_channel_id, now=ts_now)
    delivery = getattr(response, "delivery", None)
    result["lookup_ok"] = bool(getattr(response, "ok", False))
    result["delivery"] = delivery if isinstance(delivery, dict) else None
    result["metrics_present"] = bool(getattr(response, "metrics", {}) or {})

    if not result["lookup_ok"]:
        result["error"] = str(getattr(response, "error", None)
                              or "provider_lookup_failed")[:700]
        return result
    if not isinstance(delivery, dict):
        result["error"] = "provider_delivery_observation_missing"
        return result
    if delivery.get("read_ok") is not True:
        result["error"] = str(delivery.get("error")
                              or "provider_delivery_observation_degraded")[:700]
        return result

    result["ok"] = True
    result["observed_at"] = delivery.get("observed_at") or observed_at
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Poll
# ─────────────────────────────────────────────────────────────────────────────

def poll(
    root: Path,
    *,
    now: datetime | None = None,
    max_age_days: int = 7,
    dry_run: bool = False,
    publisher=None,
    max_calls: int = _MAX_CALLS_PER_RUN,
    due_only: bool = False,
    reconcile_interval_hours: int = _RECONCILE_INTERVAL_H,
    daily_call_budget: int = _MAX_CALLS_PER_24H,
) -> dict:
    """Poll metrics for recently-posted items; append rows to post_metrics.jsonl.

    With ``due_only=True``, select work per provider id from successful delivery
    observations rather than wall clock. A rolling call budget preserves posting
    and recall capacity across repeated workflow sweeps.

    Returns a summary dict {targets, polled, ok, empty, failed, dry_run, dark}.
    Fail-soft everywhere — one bad post never aborts the batch.
    """
    from engine.marketing.ledgers import append_jsonl  # noqa: PLC0415
    from engine.marketing.social_publisher import BUFFER_TOKEN_ENV, BufferPublisher  # noqa: PLC0415

    ts_now = now if now is not None else datetime.now(timezone.utc)
    polled_at = ts_now.strftime(_ISO_FMT)

    all_targets = gather_targets(root, now=ts_now, max_age_days=max_age_days)
    targets = all_targets
    fresh_count = 0
    recent_calls = 0
    if due_only:
        targets, fresh_count, recent_calls = _reconciliation_due_state(
            root, all_targets, now=ts_now,
            interval_hours=reconcile_interval_hours)

    summary = {
        "targets": len(all_targets),
        "polled": 0,
        "ok": 0,
        "empty": 0,
        "failed": 0,
        "dry_run": bool(dry_run),
        "dark": False,
        # None = ran to the end of the target list. "rate_limited" / "max_calls"
        # say the run left targets deliberately un-polled, so a short `polled`
        # count is never mistaken for "there was nothing to poll".
        "stopped": None,
    }
    if due_only:
        summary.update({
            "due": len(targets),
            "deferred_fresh": fresh_count,
            "recent_calls": recent_calls,
            "budget_remaining": max(0, int(daily_call_budget) - recent_calls),
        })

    if dry_run:
        for t in targets:
            log.info("DRY-RUN would poll remote_id=%s account=%s posted=%s",
                     t["remote_id"], t["account"] or "?",
                     t["source_ts"].strftime(_ISO_FMT))
        log.info("marketing_metrics_poll: DRY-RUN — %d target(s), no network, no write",
                 len(targets))
        return summary

    effective_call_cap = max(0, int(max_calls))
    cap_reason = "max_calls"
    if due_only:
        rolling_remaining = int(summary["budget_remaining"])
        if rolling_remaining <= effective_call_cap:
            cap_reason = "rolling_budget"
        effective_call_cap = min(effective_call_cap, rolling_remaining)
        if targets and effective_call_cap <= 0:
            summary["stopped"] = "rolling_budget"
            log.info(
                "marketing_metrics_poll: %d reconciliation target(s) due, but "
                "the rolling 24h telemetry budget is exhausted", len(targets))
            return summary

    # Dark by default: no token → one line + exit 0 (workflow-safe).
    token = os.environ.get(BUFFER_TOKEN_ENV, "").strip()
    if publisher is None and not token:
        summary["dark"] = True
        log.info("marketing_metrics_poll: no %s in env — dark, %d posted item(s) "
                 "left un-polled (no-op, exit 0)", BUFFER_TOKEN_ENV, len(targets))
        return summary

    pub = publisher if publisher is not None else BufferPublisher(token=token)
    ledger_path = _metrics_ledger_path(root)
    channel_ids = _configured_channel_ids(root)

    # ── THE POSTING ALLOWANCE IS NOT OURS TO SPEND (2026-08-03) ──────────────
    # The publisher and this poller share ONE Buffer token and ONE 24h quota.
    # This loop had no rate-limit awareness: on 2026-08-03 it polled 54 posts,
    # took a 429 on the second, and then made 52 MORE doomed calls — each one
    # still counted. Buffer answered Retry-After: 20696 (5.7 hours), and the
    # publisher's very next sweep had an approved, due, audited post refused
    # with `rate_limited=1`. Telemetry had eaten the product's allowance.
    #
    # At 30 sweeps/day x ~54 targets this lane alone asks for ~1,600 calls a
    # day, so the quota could never survive it. Two bounds now:
    #   * STOP on the first rate-limit. A 429 is a statement about the whole
    #     token, not about one post, so every later call in the run is known
    #     doomed before it is made.
    #   * CAP the run regardless. Metrics refresh ~daily; polling the same post
    #     30 times a day buys nothing and costs the posting budget.
    # Metrics are diagnostics. Posting is the product. When they compete, the
    # product wins — that is the whole ruling.
    for t in targets:
        if summary["polled"] >= effective_call_cap:
            summary["stopped"] = cap_reason
            log.info("marketing_metrics_poll: stopping at the %d-call cap (%s) — "
                     "the rest keep until the next run",
                     effective_call_cap, cap_reason)
            break
        res = pub.fetch_post_metrics(
            t["remote_id"],
            expected_channel_id=channel_ids.get(str(t.get("account") or "")),
            now=ts_now,
        )
        summary["polled"] += 1
        if due_only:
            summary["budget_remaining"] = max(
                0, int(summary["budget_remaining"]) - 1)

        if not res.ok and _is_rate_limited(res.error):
            summary["failed"] += 1
            summary["stopped"] = "rate_limited"
            append_jsonl(ledger_path, {
                "remote_id": t["remote_id"], "account": t["account"] or "",
                "external_url": t.get("external_url") or None, "metrics": {},
                "metrics_raw": None, "metrics_updated_at": None,
                "delivery": getattr(res, "delivery", None),
                "polled_at": polled_at, "ok": False,
                "note": f"poll_failed: {res.error}",
            })
            print(
                "::warning title=marketing-metrics-poll-rate-limited::Buffer "
                f"rate-limited the metrics poll after {summary['polled']} call(s); "
                f"{len(targets) - summary['polled']} target(s) left un-polled ON "
                "PURPOSE. The publisher shares this token — every further poll "
                "would spend the POSTING allowance.",
                flush=True,
            )
            break

        row: dict = {
            "remote_id": t["remote_id"],
            "account": t["account"] or "",
            # Prefer the freshly-fetched permalink; else carry any known url.
            "external_url": res.external_url or t.get("external_url") or None,
            "metrics": res.metrics,
            "metrics_raw": res.raw,
            "metrics_updated_at": res.metrics_updated_at,
            # Same append-only owner: lifecycle/readiness evidence is additive to
            # the metrics row, never a second queue or status database.
            "delivery": getattr(res, "delivery", None),
            "polled_at": polled_at,
            "ok": bool(res.ok),
        }
        if not res.ok:
            summary["failed"] += 1
            row["note"] = f"poll_failed: {res.error}"
        elif not res.metrics:
            summary["empty"] += 1
            summary["ok"] += 1
            row["note"] = "metrics_empty (not yet refreshed by backend)"
        else:
            summary["ok"] += 1

        append_jsonl(ledger_path, row)

    log.info("marketing_metrics_poll: polled=%d ok=%d empty=%d failed=%d stopped=%s → %s",
             summary["polled"], summary["ok"], summary["empty"], summary["failed"],
             summary["stopped"] or "-", ledger_path)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Marketing per-post metrics poller (D02 — dark by default)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="list what WOULD be polled; zero network, zero write")
    parser.add_argument(
        "--if-due", action="store_true",
        help=("reconcile only provider ids without a successful observation in "
              "the last 24h; enforces the rolling telemetry call budget"),
    )
    parser.add_argument(
        "--delivery-readback-item", default=None, metavar="OUTBOX_ID",
        help=("read one canonically accepted outbox item from Buffer and print "
              "safe delivery/channel evidence; zero ledger mutation"),
    )
    parser.add_argument("--max-age-days", type=int, default=7,
                        help="only poll posts newer than this many days (default 7)")
    parser.add_argument("--root", default=None,
                        help="Repo root directory (default: derived from script location)")
    parser.add_argument("--now", default=None,
                        help="Override 'now' as ISO8601 (testing/determinism)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Make engine.* importable when run as a module OR as a file.

    root = _data_root(args.root)
    now = None
    if args.now:
        from engine.marketing.social_publisher import _iso_now  # noqa: PLC0415,F401
        parsed = _parse_iso(args.now)
        if parsed is None:
            log.warning("bad --now %r; using wall-clock", args.now)
        now = parsed

    if args.delivery_readback_item:
        if args.dry_run:
            parser.error("--delivery-readback-item and --dry-run are mutually exclusive")
        result = delivery_readback(
            root, item_id=args.delivery_readback_item, now=now)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result.get("ok") is True else 2

    poll(
        root, now=now, max_age_days=args.max_age_days,
        dry_run=bool(args.dry_run), due_only=bool(args.if_due))
    return 0


if __name__ == "__main__":
    sys.exit(main())
