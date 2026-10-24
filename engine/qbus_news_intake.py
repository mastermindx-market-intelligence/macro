"""Additional publisher intake driven by the existing news runner.

Only network acquisition runs in a bounded background future. The incumbent
runner thread owns routing, receipt revalidation and every store commit. This is
not another daemon, durable queue, publisher or truth store.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import re
import time

from collectors.benzinga_news import route_revision
from engine.qbus_news_receipts import combine_news_rights


class SupplementalNewsIntake:
    def __init__(
        self, *, client, store, rights_provider, universe_provider,
        clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic,
        interval_seconds=60.0, overlap_seconds=86400.0,
    ):
        if interval_seconds < 1 or overlap_seconds < 0:
            raise ValueError("invalid_supplemental_interval")
        self.client, self.store = client, store
        self.rights_provider, self.universe_provider = rights_provider, universe_provider
        self.clock, self.monotonic = clock, monotonic
        self.interval_seconds, self.overlap_seconds = interval_seconds, overlap_seconds
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="news-acquisition")
        self._pending = None
        self._expected_cursor = None
        self._checkpoint = None
        self._since = None
        self._next_poll = 0.0
        self.state = "waiting"
        self.last_successful_poll = None
        self.last_error = None
        self.accepted_reports = 0
        self.publishers = ()
        self._closed = False

    def _allowed(self):
        receipts = tuple(
            receipt for receipt in self.rights_provider()
            if receipt.provider == "massive" and receipt.source.startswith("massive:")
        )
        rights = combine_news_rights(receipts)
        return rights.allowed_sources

    def _failed(self, code):
        self.state = "degraded"
        self.last_error = code
        self._next_poll = self.monotonic() + self.interval_seconds

    def pump(self):
        """Nonblocking scheduler/drain, called exclusively by the runner thread."""
        if self._closed:
            return
        if self._pending is not None and self._pending.done():
            future, self._pending = self._pending, None
            try:
                batch = future.result()
                allowed = self._allowed()  # revoke/expire before any durable write
                self.publishers = tuple(sorted(source.partition(":")[2] for source in allowed))
                if not allowed:
                    self.state = "restricted"
                    self.last_error = "rights_unavailable"
                    return
                universe = self.universe_provider()
                routed = [
                    route_revision(revision, universe)
                    for revision in batch.revisions
                    if revision.source in allowed
                ]
                # The provider exposes publication time, not an update clock.
                # Always overlap the next acquisition window; an incomplete page
                # budget never advances the checkpoint past unobserved content.
                next_cursor = json.dumps({
                    "checkpoint": batch.through.isoformat() if batch.complete else self._checkpoint,
                    "since": self._since.isoformat(),
                    "through": batch.through.isoformat(),
                    "next_url": None if batch.complete else batch.next_url,
                    "publishers": list(self.publishers),
                }, sort_keys=True, separators=(",", ":"))
                receipt = self.store.commit(
                    routed, expected_cursor=self._expected_cursor, next_cursor=next_cursor,
                )
                self.accepted_reports += receipt.applied_states
                if batch.complete:
                    self.state = "available"
                    self.last_successful_poll = self.clock()
                    self.last_error = None
                else:
                    self.state = "degraded"
                    self.last_error = "page_budget_exhausted"
            except Exception as exc:
                code = getattr(exc, "code", None)
                code = code.lower() if isinstance(code, str) else None
                safe = code if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,64}", code) else "supplemental_acquisition_failed"
                self._failed(safe)
            self._next_poll = self.monotonic() + self.interval_seconds
        if self._pending is not None or self.monotonic() < self._next_poll:
            return
        try:
            allowed = self._allowed()
        except Exception:
            self._failed("supplemental_rights_unavailable")
            return
        self.publishers = tuple(sorted(source.partition(":")[2] for source in allowed))
        if not allowed:
            self.state = "restricted"
            self.last_error = "rights_unavailable"
            self._next_poll = self.monotonic() + self.interval_seconds
            return
        now = self.clock()
        self._expected_cursor = self.store.current_cursor()
        resume_url = None
        through = None
        try:
            state = json.loads(self._expected_cursor) if self._expected_cursor else {}
            checkpoint = datetime.fromisoformat(state["checkpoint"]) if state.get("checkpoint") else now
            if checkpoint.tzinfo is None or checkpoint > now:
                raise ValueError
            since = checkpoint - timedelta(seconds=self.overlap_seconds)
            if state.get("next_url") and state.get("publishers") == list(self.publishers):
                resume_url = state["next_url"]
                through = datetime.fromisoformat(state["through"])
                since = datetime.fromisoformat(state["since"])
                if through.tzinfo is None or since.tzinfo is None or since > through or through > now:
                    raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError):
            self._failed("invalid_supplemental_cursor")
            return
        self._checkpoint = checkpoint.isoformat()
        self._since = since
        self.state = "catching_up"
        self._pending = self._pool.submit(
            self.client.poll, since=since, next_url=resume_url, through=through,
            allowed_publishers=frozenset(self.publishers),
        )

    def health(self):
        last = self.last_successful_poll
        return {
            "provider": "massive",
            "state": self.state,
            "last_successful_poll": last.isoformat() if last else None,
            "last_error": self.last_error,
            "accepted_reports": self.accepted_reports,
            "publishers": list(self.publishers),
            "delivery": "polled",
        }

    def close(self):
        self._closed = True
        self.state = "unavailable"
        if self._pending is not None:
            self._pending.cancel()
        self._pool.shutdown(wait=False, cancel_futures=True)
