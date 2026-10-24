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

class TiingoSupplementalIntake:
    """Bounded Tiingo acquisition, drained by the incumbent serialized writer.

    Neither HTTP futures nor this object own durable state. All publisher
    admission, issuer rights, universe routing and SQLite commits happen
    synchronously inside the existing runner's pump on its writer thread.
    """

    def __init__(
        self, *, token, store, rights_provider, universe_provider, enabled,
        clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic,
        fetch=None, interval_seconds=60.0, limit=250,
    ):
        from engine.tiingo_news import fetch_articles
        if (not isinstance(limit, int) or isinstance(limit, bool)
                or not 1 <= limit <= 250 or interval_seconds < 1):
            raise ValueError("invalid_tiingo_intake_bounds")
        self.token, self.store = token, store
        self.rights_provider, self.universe_provider = rights_provider, universe_provider
        self.enabled, self.clock, self.monotonic = enabled, clock, monotonic
        self.fetch = fetch if fetch is not None else fetch_articles
        self.limit, self.interval_seconds = limit, interval_seconds
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="news-acquisition")
        self._pending = None
        self._next_poll = 0.0
        self._closed = False
        self.state = "waiting"
        self.last_error = None
        self.accepted_reports = 0
        self.last_successful_poll = None

    def _current_grant(self):
        if self._closed or not self.enabled() or not self.token:
            return None
        grant = self.rights_provider()
        if (grant is None or grant.source != "tiingo"
                or not grant.derivative_processing
                or not grant.rights.allows("tiingo", "title")
                or not any(src.startswith("tiingo:") for src in grant.rights.allowed_sources)):
            return None
        return grant

    def _restricted(self):
        self.state, self.last_error = "restricted", "rights_unavailable"
        self._next_poll = self.monotonic() + self.interval_seconds

    def pump(self):
        """Run exclusively on the primary NewsIngestRunner serialized thread."""
        if self._closed:
            return
        if self._pending is not None and self._pending[0].done():
            future, source_grant = self._pending
            self._pending = None
            try:
                rows, status = future.result()
                active_grant = self._current_grant()
                if active_grant is None or active_grant != source_grant:
                    self._restricted()
                    return
                if status not in ("ok", "no_rows") or not isinstance(rows, list):
                    self.state, self.last_error = "degraded", "acquisition_unavailable"
                else:
                    from engine import tiingo_news
                    from engine.qbus_news_contract import NewsContractError, normalize_tiingo_news
                    from engine.qbus_news_quality import curated_report
                    universe = self.universe_provider()
                    if universe.status != "qualified":
                        self.state, self.last_error = "degraded", "universe_unqualified"
                    else:
                        routed = []
                        for raw in rows[:self.limit]:
                            try:
                                observed = tiingo_news.normalize_article(
                                    raw, received_at=self.clock(),
                                )
                                revision = normalize_tiingo_news(
                                    observed, received_at=datetime.fromisoformat(observed["received_at"]),
                                )
                            except (tiingo_news.TiingoArticleError, NewsContractError):
                                continue
                            source = revision.source
                            rights = active_grant.rights
                            if not rights.allows(source, "title"):
                                continue
                            url = revision.url if rights.allows(source, "url") else ""
                            if not curated_report(source, revision.title, url):
                                continue
                            routed_item = route_revision(revision, universe)
                            if routed_item.security_ids:
                                routed.append(routed_item)
                        if self._current_grant() != source_grant:
                            self._restricted()
                            return
                        if routed:
                            result = self.store.commit_observations(routed)
                            self.accepted_reports += result.applied_states
                        # Read rights are checked again at every API read;
                        # an owner withdrawal never deletes source history.
                        if self._current_grant() != source_grant:
                            self._restricted()
                            return
                        self.state = "available" if routed else "quiet"
                        self.last_error = None
                        self.last_successful_poll = self.clock()
            except Exception:
                # Never log exception messages: HTTP/header errors may contain
                # credential material. All failures are source-local.
                self.state, self.last_error = "degraded", "tiingo_acquisition_failed"
            self._next_poll = self.monotonic() + self.interval_seconds
        if self._pending is not None or self.monotonic() < self._next_poll:
            return
        try:
            grant = self._current_grant()
        except Exception:
            self._restricted()
            return
        if grant is None:
            self._restricted()
            return
        self._pending = (
            self._pool.submit(self.fetch, token=self.token, limit=self.limit),
            grant,
        )
        self.state, self.last_error = "catching_up", None

    def health(self):
        last = self.last_successful_poll
        return {
            "provider": "tiingo",
            "state": self.state,
            "last_successful_poll": last.isoformat() if last else None,
            "accepted_reports": self.accepted_reports,
            "last_error": self.last_error,
            "delivery": "polled_bounded_snapshot_not_complete_history",
        }

    def close(self):
        self._closed = True
        self.state = "unavailable"
        if self._pending is not None:
            self._pending[0].cancel()
        self._pool.shutdown(wait=False, cancel_futures=True)
