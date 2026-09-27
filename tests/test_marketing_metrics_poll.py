"""tests/test_marketing_metrics_poll.py — per-post metrics poller + admin join.

Mirrors tests/test_marketing_social_publisher.py: tmp_path for all I/O, injected
now= for determinism, engine modules imported inside each test, ZERO live network
(the Buffer transport is mocked via _transport, or a fully-stubbed publisher is
injected into poll()).

Covers:
  * BufferPublisher.fetch_post_metrics: success (metrics + externalLink),
    empty-metrics honesty, no_post, GraphQL error, empty id — all fail-soft
  * _normalize_metrics maps Buffer tokens → console keys, drops junk, keeps raw
  * poller gather_targets: dedupe across status_ledger + publications, 7-day filter
  * poller --dry-run lists targets, writes nothing
  * poller no-token → dark no-op (exit 0, no write)
  * poller happy path (stub publisher) → post_metrics.jsonl row shape, empty-row note
  * external_url backfill lands on the metrics row (publications.jsonl not rewritten)
  * admin publisher() join: fail-soft when ledger absent; joins latest metrics + url
  * publisher media attach: config gate off → no attach; on → public URL only
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

_NOW = datetime(2026, 7, 23, 15, 0, 0, tzinfo=timezone.utc)
_ISO = "%Y-%m-%dT%H:%M:%SZ"


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers
# ─────────────────────────────────────────────────────────────────────────────

def _seed_posted(tmp_path: Path, *, external_id: str, account: str = "flagship",
                 as_of: str = "2026-07-23", at: datetime = _NOW, text: str = "signal post") -> str:
    """Drive one item queued→approved→posting→posted with a Buffer receipt."""
    from engine.marketing.outbox import make_item, enqueue, transition
    it = make_item(account=account, kind="signal", text=text, as_of=as_of,
                   provenance="content_studio", now=at)
    enqueue(it, root=tmp_path, max_per_account_day=99)
    transition(it["id"], "approved", actor="t", root=tmp_path)
    transition(it["id"], "posting", actor="t", root=tmp_path)
    transition(it["id"], "posted", actor="publisher", root=tmp_path, note="published",
               receipt={"backend": "buffer", "external_id": external_id,
                        "external_url": None, "at": at.strftime(_ISO)})
    return it["id"]


def _write_publications(tmp_path: Path, rows: list[dict]) -> None:
    import json
    p = tmp_path / "data" / "marketing" / "publications.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _read_metrics_rows(tmp_path: Path) -> list[dict]:
    from engine.marketing.ledgers import read_jsonl
    return read_jsonl(tmp_path / "data" / "marketing" / "post_metrics.jsonl")


class _StubPub:
    """A publisher whose fetch_post_metrics returns canned MetricsResults by id."""

    backend = "buffer"

    def __init__(self, by_id: dict):
        self._by_id = by_id
        self.calls: list[str] = []

    def fetch_post_metrics(self, pid, *, expected_channel_id=None, now=None):
        from engine.marketing.social_publisher import MetricsResult
        self.calls.append(pid)
        r = self._by_id.get(pid)
        if r is not None:
            return r
        return MetricsResult(False, None, {}, [], None, "no_post_returned", "buffer",
                             (now or _NOW).strftime(_ISO))


def _metrics_ok(url, metrics, raw=None, updated="2026-07-23T12:00:00Z",
                delivery=None):
    from engine.marketing.social_publisher import MetricsResult
    return MetricsResult(True, url, metrics, raw or [], updated, None, "buffer",
                         _NOW.strftime(_ISO), delivery=delivery)


# ─────────────────────────────────────────────────────────────────────────────
# BufferPublisher.fetch_post_metrics (transport mocked)
# ─────────────────────────────────────────────────────────────────────────────

def test_fetch_metrics_success(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    pub = BufferPublisher(token="tkn")
    captured: dict = {}

    def fake_transport(payload):
        captured["payload"] = payload
        return {"data": {"post": {
            "id": "buf-1",
            "externalLink": "https://x.com/mastermindx001/status/1",
            "metricsUpdatedAt": "2026-07-23T12:00:00Z",
            "metrics": [
                {"type": "impressions", "name": "Impressions", "value": 1200, "unit": "count"},
                {"type": "reactions", "name": "Likes", "value": 88, "unit": "count"},
                {"type": "retweets", "name": "Reposts", "value": 7, "unit": "count"},
                {"type": "replies", "name": "Comments", "value": 3, "unit": "count"},
                {"type": "urlClicks", "name": "Clicks", "value": 14, "unit": "count"},
                {"type": "engagementRate", "name": "Engagement Rate", "value": 0.081, "unit": "percent"},
            ],
        }}}

    monkeypatch.setattr(pub, "_transport", fake_transport)
    res = pub.fetch_post_metrics("buf-1", now=_NOW)
    assert res.ok is True
    assert res.external_url == "https://x.com/mastermindx001/status/1"
    assert res.metrics == {"impressions": 1200, "likes": 88, "reposts": 7,
                           "comments": 3, "clicks": 14, "engagement_rate": 0.081}
    assert res.metrics_updated_at == "2026-07-23T12:00:00Z"
    assert len(res.raw) == 6  # nothing dropped
    # Query carried the post id.
    assert captured["payload"]["variables"]["input"]["id"] == "buf-1"


def test_fetch_metrics_normalizes_provider_sent_and_channel_readiness(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher

    pub = BufferPublisher(token="tkn")
    captured: dict = {}

    def fake_transport(payload):
        captured["payload"] = payload
        return {"data": {"post": {
            "id": "buf-1",
            "channelId": "chan-1",
            "status": "sent",
            "schedulingType": "automatic",
            "dueAt": "2026-07-23T14:55:00Z",
            "sentAt": "2026-07-23T15:00:00Z",
            "externalLink": "https://x.com/mastermindx001/status/1",
            "notificationStatus": None,
            "error": None,
            "channel": {
                "id": "chan-1",
                "isDisconnected": False,
                "isLocked": False,
                "isQueuePaused": False,
                "hasActiveMemberDevice": True,
            },
            "metricsUpdatedAt": None,
            "metrics": [],
        }}}

    monkeypatch.setattr(pub, "_transport", fake_transport)
    res = pub.fetch_post_metrics(
        "buf-1", expected_channel_id="chan-1", now=_NOW)

    assert res.ok is True
    assert res.delivery is not None
    assert res.delivery["state"] == "provider_sent"
    assert res.delivery["provider_id"] == "buf-1"
    assert res.delivery["channel_id"] == "chan-1"
    assert res.delivery["provider_status"] == "sent"
    assert res.delivery["scheduling_type"] == "automatic"
    assert res.delivery["provider_sent"] is True
    assert res.delivery["provider_sent_at"] == "2026-07-23T15:00:00Z"
    assert res.delivery["external_url"].startswith("https://x.com/")
    assert res.delivery["x_visible"] is None
    assert res.delivery["channel_ready"] is True
    assert res.delivery["read_ok"] is True
    query = captured["payload"]["query"]
    assert query.lstrip().startswith("query ")
    assert "mutation" not in query
    assert "rawError" not in query


def test_fetch_metrics_empty_is_honest(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    pub = BufferPublisher(token="tkn")
    monkeypatch.setattr(pub, "_transport", lambda payload: {"data": {"post": {
        "id": "buf-2", "externalLink": "https://x.com/mastermindx001/status/2",
        "metricsUpdatedAt": None, "metrics": []}}})
    res = pub.fetch_post_metrics("buf-2", now=_NOW)
    assert res.ok is True            # empty metrics is NOT a failure
    assert res.metrics == {}
    assert res.raw == []
    assert res.external_url.endswith("/2")


def test_fetch_metrics_no_post(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    pub = BufferPublisher(token="tkn")
    monkeypatch.setattr(pub, "_transport", lambda payload: {"data": {"post": None}})
    res = pub.fetch_post_metrics("buf-x", now=_NOW)
    assert res.ok is False
    assert "no_post" in (res.error or "")


def test_fetch_metrics_graphql_error(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    pub = BufferPublisher(token="tkn")
    monkeypatch.setattr(pub, "_transport",
                        lambda payload: {"errors": [{"message": "bad id"}]})
    res = pub.fetch_post_metrics("buf-x", now=_NOW)
    assert res.ok is False and "bad id" in (res.error or "")


def test_fetch_metrics_empty_id():
    from engine.marketing.social_publisher import BufferPublisher
    res = BufferPublisher(token="tkn").fetch_post_metrics("", now=_NOW)
    assert res.ok is False and res.error == "empty_post_id"


def test_fetch_metrics_network_error_no_raise(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    from urllib.error import URLError
    pub = BufferPublisher(token="tkn")

    def boom(payload):
        raise URLError("refused")

    monkeypatch.setattr(pub, "_transport", boom)
    res = pub.fetch_post_metrics("buf-1", now=_NOW)  # must not raise
    assert res.ok is False and "network_error" in (res.error or "")


def test_normalize_metrics_maps_and_drops():
    from engine.marketing.social_publisher import _normalize_metrics
    out = _normalize_metrics([
        {"type": "impressions", "value": 10},
        {"type": "somethingWeird", "value": 99},         # unmapped → dropped from keys
        {"type": "likes", "value": True},                # bool is not numeric → dropped
        {"type": "clicks", "value": "x"},                # non-numeric → dropped
        {"type": "reposts", "value": 4},
    ])
    assert out == {"impressions": 10, "reposts": 4}


# ─────────────────────────────────────────────────────────────────────────────
# Poller: gather_targets / dry-run / dark / happy path
# ─────────────────────────────────────────────────────────────────────────────

def test_gather_targets_dedupes_and_age_filters(tmp_path):
    import scripts.marketing_metrics_poll as poller
    _seed_posted(tmp_path, external_id="buf-777", at=_NOW)
    _write_publications(tmp_path, [
        {"publication_id": "p1", "account": "flagship", "remote_id": "buf-999",
         "published_at": "2026-07-22T06:00:00Z", "channel": "x"},
        {"publication_id": "p0", "account": "flagship", "remote_id": "buf-OLD",
         "published_at": "2026-07-01T06:00:00Z", "channel": "x"},  # stale > 7d
    ])
    ids = [t["remote_id"] for t in poller.gather_targets(tmp_path, now=_NOW, max_age_days=7)]
    assert set(ids) == {"buf-777", "buf-999"}
    assert "buf-OLD" not in ids


def test_dry_run_lists_and_writes_nothing(tmp_path):
    import scripts.marketing_metrics_poll as poller
    _seed_posted(tmp_path, external_id="buf-777")
    s = poller.poll(tmp_path, now=_NOW, dry_run=True)
    assert s["dry_run"] is True and s["targets"] == 1 and s["polled"] == 0
    assert not (tmp_path / "data" / "marketing" / "post_metrics.jsonl").exists()


def test_no_token_is_dark_noop(tmp_path, monkeypatch):
    import scripts.marketing_metrics_poll as poller
    monkeypatch.delenv("BUFFER_TOKEN", raising=False)
    _seed_posted(tmp_path, external_id="buf-777")
    s = poller.poll(tmp_path, now=_NOW, dry_run=False)  # publisher=None + no token
    assert s["dark"] is True and s["polled"] == 0
    assert not (tmp_path / "data" / "marketing" / "post_metrics.jsonl").exists()


def test_happy_path_row_shape_and_empty_note(tmp_path):
    import scripts.marketing_metrics_poll as poller
    _seed_posted(tmp_path, external_id="buf-777", at=_NOW)
    _write_publications(tmp_path, [
        {"publication_id": "p1", "account": "flagship", "remote_id": "buf-999",
         "published_at": "2026-07-22T06:00:00Z", "channel": "x"}])
    stub = _StubPub({
        "buf-777": _metrics_ok("https://x.com/mastermindx001/status/777",
                               {"impressions": 1200, "likes": 88, "reposts": 7,
                                "comments": 3, "clicks": 14, "engagement_rate": 0.081},
                               raw=[{"type": "impressions", "value": 1200}]),
        "buf-999": _metrics_ok("https://x.com/mastermindx001/status/999", {}, raw=[], updated=None),
    })
    s = poller.poll(tmp_path, now=_NOW, dry_run=False, publisher=stub)
    # `stopped` joined the summary on 2026-08-03: a short `polled` count now has
    # to say WHY it is short (rate_limited / max_calls) so a throttled run can
    # never be misread as "there was nothing to poll". None = ran to completion.
    assert s == {"targets": 2, "polled": 2, "ok": 2, "empty": 1, "failed": 0,
                 "dry_run": False, "dark": False, "stopped": None}
    rows = {r["remote_id"]: r for r in _read_metrics_rows(tmp_path)}

    full = rows["buf-777"]
    # Console contract keys.
    assert set(full["metrics"]) >= {"impressions", "likes", "reposts", "comments",
                                    "clicks", "engagement_rate"}
    assert full["account"] == "flagship"
    assert full["external_url"].endswith("/777")
    assert full["metrics_raw"] == [{"type": "impressions", "value": 1200}]
    assert full["metrics_updated_at"] == "2026-07-23T12:00:00Z"
    assert full["polled_at"] == _NOW.strftime(_ISO)
    assert full["ok"] is True and "note" not in full

    empty = rows["buf-999"]
    assert empty["metrics"] == {} and "metrics_empty" in empty["note"]
    assert empty["ok"] is True  # empty-but-fetched is ok


def test_poller_passes_configured_expected_channel_to_provider_read(tmp_path):
    import scripts.marketing_metrics_poll as poller

    _seed_posted(tmp_path, external_id="buf-channel", account="flagship", at=_NOW)
    cfg = tmp_path / "config" / "marketing.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "publish:\n  channels:\n    flagship: chan-expected\n",
        encoding="utf-8",
    )

    class CapturingPublisher:
        def __init__(self):
            self.calls = []

        def fetch_post_metrics(self, remote_id, *, expected_channel_id=None, now=None):
            self.calls.append((remote_id, expected_channel_id))
            return _metrics_ok("https://x.com/mm/status/1", {}, updated=None)

    publisher = CapturingPublisher()
    poller.poll(tmp_path, now=_NOW, dry_run=False, publisher=publisher)

    assert publisher.calls == [("buf-channel", "chan-expected")]


def test_poller_persists_provider_delivery_observation_in_existing_ledger(tmp_path):
    import scripts.marketing_metrics_poll as poller

    _seed_posted(tmp_path, external_id="buf-delivery", at=_NOW)
    delivery = {
        "schema": "marketing.provider_delivery/v1",
        "read_ok": True,
        "state": "provider_sent",
        "provider_id": "buf-delivery",
        "channel_id": "chan-1",
        "provider_status": "sent",
        "scheduling_type": "automatic",
        "notification_status": None,
        "due_at": "2026-07-23T14:55:00Z",
        "provider_sent": True,
        "provider_sent_at": "2026-07-23T15:00:00Z",
        "external_url": "https://x.com/mastermindx001/status/777",
        "x_visible": None,
        "x_visible_at": None,
        "channel_ready": True,
        "channel": {
            "id": "chan-1", "is_disconnected": False, "is_locked": False,
            "is_queue_paused": False, "has_active_member_device": True,
        },
        "publishing_error": None,
        "observed_at": _NOW.strftime(_ISO),
        "error": None,
    }
    stub = _StubPub({
        "buf-delivery": _metrics_ok(
            delivery["external_url"], {}, updated=None, delivery=delivery),
    })

    poller.poll(tmp_path, now=_NOW, dry_run=False, publisher=stub)

    rows = _read_metrics_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["delivery"] == delivery


def test_failed_poll_writes_honest_row(tmp_path):
    import scripts.marketing_metrics_poll as poller
    from engine.marketing.social_publisher import MetricsResult
    _seed_posted(tmp_path, external_id="buf-777")
    stub = _StubPub({"buf-777": MetricsResult(False, None, {}, [], None,
                                              "no_post_returned", "buffer", _NOW.strftime(_ISO))})
    s = poller.poll(tmp_path, now=_NOW, dry_run=False, publisher=stub)
    assert s["failed"] == 1 and s["ok"] == 0
    row = _read_metrics_rows(tmp_path)[0]
    assert row["ok"] is False and "poll_failed" in row["note"]


def test_external_url_backfill_from_publications(tmp_path):
    # A publications row lacking external_url; Buffer returns one → it lands on
    # the metrics row (publications.jsonl is NOT rewritten).
    import scripts.marketing_metrics_poll as poller
    import json
    _write_publications(tmp_path, [
        {"publication_id": "p1", "account": "flagship", "remote_id": "buf-999",
         "published_at": "2026-07-22T06:00:00Z", "channel": "x"}])
    pubs_before = (tmp_path / "data" / "marketing" / "publications.jsonl").read_text()
    stub = _StubPub({"buf-999": _metrics_ok("https://x.com/mastermindx001/status/999",
                                            {"impressions": 5})})
    poller.poll(tmp_path, now=_NOW, dry_run=False, publisher=stub)
    row = _read_metrics_rows(tmp_path)[0]
    assert row["external_url"].endswith("/999")
    # publications.jsonl untouched (append-only law)
    assert (tmp_path / "data" / "marketing" / "publications.jsonl").read_text() == pubs_before


# ─────────────────────────────────────────────────────────────────────────────
# Admin publisher() metrics join (fail-soft + latest-wins)
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_join_failsoft_when_ledger_absent(tmp_path):
    import admin.marketing as am
    _seed_posted(tmp_path, external_id="buf-777")
    payload = am.publisher(root=tmp_path)
    assert payload["ok"] is True
    row = payload["recent_posted"][0]
    assert "metrics" not in row          # no ledger → no metrics key
    assert row["external_url"] is None


def test_admin_join_uses_latest_metrics_and_backfills_url(tmp_path):
    import admin.marketing as am
    import json
    _seed_posted(tmp_path, external_id="buf-777")
    mp = tmp_path / "data" / "marketing" / "post_metrics.jsonl"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text("\n".join(json.dumps(r) for r in [
        {"remote_id": "buf-777", "account": "flagship", "external_url": None,
         "metrics": {"impressions": 10}, "polled_at": "2026-07-23T06:00:00Z", "ok": True},
        {"remote_id": "buf-777", "account": "flagship",
         "external_url": "https://x.com/mastermindx001/status/777",
         "metrics": {"impressions": 1200, "likes": 88, "reposts": 7, "comments": 3,
                     "clicks": 14, "engagement_rate": 0.081},
         "polled_at": "2026-07-23T14:00:00Z", "ok": True},
    ]) + "\n", encoding="utf-8")
    row = am.publisher(root=tmp_path)["recent_posted"][0]
    assert row["metrics"]["impressions"] == 1200          # newest poll wins
    assert row["external_url"].endswith("/777")            # backfilled from ledger


# ─────────────────────────────────────────────────────────────────────────────
# Publisher media attach — config gate
# ─────────────────────────────────────────────────────────────────────────────

def test_publisher_media_gate_off_is_text_only():
    import scripts.marketing_publisher as P
    it = {"media": [{"kind": "chart_svg", "path": "data/x.svg", "chart_id": "c1",
                     "media_url": "https://pub-x.r2.dev/marketing/charts/2026-07-23/c1.png"}]}
    assert P._media_paths_for(it, {"media_enabled": False}) == []


def test_publisher_media_gate_on_passes_public_url():
    import scripts.marketing_publisher as P
    it = {"media": [{"kind": "chart_svg", "path": "data/x.svg", "chart_id": "c1",
                     "media_url": "https://pub-x.r2.dev/marketing/charts/2026-07-23/c1.png"}]}
    assert P._media_paths_for(it, {"media_enabled": True}) == \
        ["https://pub-x.r2.dev/marketing/charts/2026-07-23/c1.png"]
    # local-only media (no public url) → text-only even with the gate on
    it2 = {"media": [{"kind": "chart_svg", "path": "data/x.svg", "chart_id": "c1",
                      "media_png_path": "data/marketing/outbox/media/x/c1.png"}]}
    assert P._media_paths_for(it2, {"media_enabled": True}) == []


def test_publisher_attach_flows_through_build_assets(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher
    import scripts.marketing_publisher as P
    it = {"media": [{"kind": "chart_svg", "path": "data/x.svg", "chart_id": "c1",
                     "media_url": "https://pub-x.r2.dev/marketing/charts/2026-07-23/c1.png"}]}
    media_paths = P._media_paths_for(it, {"media_enabled": True})

    pub = BufferPublisher(token="tkn", organization_id="org-1")
    captured: dict = {}

    def fake_transport(payload):
        captured["payload"] = payload
        return {"data": {"createPost": {"__typename": "PostActionSuccess",
                                        "post": {"id": "buf-1"}}}}

    monkeypatch.setattr(pub, "_transport", fake_transport)
    r = pub.publish(text="hi", channel_id="c9", media_paths=media_paths)
    assert r.ok is True
    assert captured["payload"]["variables"]["input"]["assets"] == \
        [{"image": {"url": "https://pub-x.r2.dev/marketing/charts/2026-07-23/c1.png"}}]


class TestBufferRateLimitIsNameable:
    """The publisher and the engagement poller share ONE token and ONE quota.

    `publish` and `fetch_post_metrics` both go through BufferPublisher._transport
    with the same BUFFER_TOKEN, so a metrics sweep over a few hundred posted
    items can spend the 24h allowance the publisher needs to post at all.

    Before this, a 429 arrived as a bare HTTPError, the public callers turned it
    into a fail-soft "did not send", and it was indistinguishable from Buffer
    being down. Fail-soft is right; indistinguishable is not — a rate limit is
    self-inflicted and fixed by spacing our own calls out, an outage is not.
    """

    @staticmethod
    def _raise(code, headers=None):
        import io
        from urllib.error import HTTPError

        def _fake(req, timeout=None):
            raise HTTPError(req.full_url, code, "boom", headers or {}, io.BytesIO(b""))

        return _fake

    def test_a_429_becomes_a_named_rate_limit_carrying_retry_after(self, monkeypatch):
        from engine.marketing import social_publisher as SP

        monkeypatch.setattr(SP, "urlopen", self._raise(429, {"Retry-After": "900"}))
        client = SP.BufferPublisher(token="t")
        try:
            client._transport({"query": "{}"})
        except SP.BufferRateLimited as exc:
            assert exc.retry_after == "900"
        else:
            raise AssertionError("a 429 did not raise BufferRateLimited")

    def test_it_stays_a_RuntimeError_so_fail_soft_callers_are_unchanged(self, monkeypatch):
        """Every caller catches broadly and must keep doing so.

        This change makes the reason legible; it must not turn a rate limit into
        a crash that takes down a publish sweep.
        """
        from engine.marketing import social_publisher as SP

        assert issubclass(SP.BufferRateLimited, RuntimeError)
        monkeypatch.setattr(SP, "urlopen", self._raise(429))
        try:
            SP.BufferPublisher(token="t")._transport({"query": "{}"})
        except Exception as exc:  # noqa: BLE001 — the shape every caller uses
            assert isinstance(exc, RuntimeError)

    def test_other_http_errors_are_not_reclassified(self, monkeypatch):
        """A 500 is Buffer's problem and must not be blamed on our quota."""
        from urllib.error import HTTPError

        from engine.marketing import social_publisher as SP

        monkeypatch.setattr(SP, "urlopen", self._raise(500))
        try:
            SP.BufferPublisher(token="t")._transport({"query": "{}"})
        except SP.BufferRateLimited:
            raise AssertionError("a 500 was misreported as a rate limit")
        except HTTPError as exc:
            assert exc.code == 500

    def test_the_shared_quota_is_named_on_the_console(self, monkeypatch, capsys):
        """Bare line-start annotation per CLAUDE.md, or GitHub drops it."""
        from engine.marketing import social_publisher as SP

        monkeypatch.setattr(SP, "urlopen", self._raise(429))
        try:
            SP.BufferPublisher(token="t")._transport({"query": "{}"})
        except SP.BufferRateLimited:
            pass
        out = capsys.readouterr().out
        line = next(ln for ln in out.splitlines() if "buffer-rate-limited" in ln)
        assert line.startswith("::warning title=marketing-buffer-rate-limited::")
        assert "ONE token" in line and "poller" in line


class TestPostedIsNotProofItWentOut:
    """`posted` means Buffer ACCEPTED the item, not that it reached X.

    telemetry.join_provenance walks METRICS ROWS and flags any with no outbox
    item (`orphans`) — "we measured something we did not plan". The opposite and
    more damaging case, "we marked it posted and it never went out", produces no
    metrics row to walk, so nothing was looking for it. One direction was guarded
    because it once broke; the quiet half stayed open.

    The join already existed and nothing performed it: `receipt.external_id` on
    the posted transition is `remote_id` in post_metrics.jsonl. On the committed
    ledgers 2026-07-31 it is 48 posted / 48 confirmed / 0 unconfirmed, so this
    guards a live risk rather than reporting an active fire.
    """

    @staticmethod
    def _root(tmp_path, *, ledger, metrics):
        import json

        d = tmp_path / "data" / "marketing" / "outbox"
        d.mkdir(parents=True, exist_ok=True)
        (d / "status_ledger.jsonl").write_text(
            "\n".join(json.dumps(r) for r in ledger), encoding="utf-8")
        (tmp_path / "data" / "marketing" / "post_metrics.jsonl").write_text(
            "\n".join(json.dumps(r) for r in metrics), encoding="utf-8")
        return tmp_path

    @staticmethod
    def _posted(item_id, external_id, at):
        return {"id": item_id, "from": "posting", "to": "posted", "at": at,
                "actor": "publisher", "note": "published",
                "receipt": {"backend": "buffer", "external_id": external_id,
                            "at": at, "booked_at": at}}

    def test_legacy_posted_with_buffer_id_projects_accepted_unconfirmed_not_sent(
            self, tmp_path):
        """Creation acceptance is not provider-send or X-visibility evidence."""
        import json

        from engine.marketing.telemetry import delivery_projection

        at = "2026-07-01T10:00:00Z"
        root = self._root(
            tmp_path,
            ledger=[
                {"id": "ob-legacy", "from": "queued", "to": "approved",
                 "at": at, "actor": "test", "note": "approved", "receipt": None},
                {"id": "ob-legacy", "from": "approved", "to": "posting",
                 "at": at, "actor": "publisher", "note": "in-flight",
                 "receipt": None},
                self._posted("ob-legacy", "buf-legacy", at),
            ],
            metrics=[],
        )
        (root / "data" / "marketing" / "outbox" / "items.jsonl").write_text(
            json.dumps({"id": "ob-legacy", "status": "queued",
                        "account": "flagship"}) + "\n", encoding="utf-8")

        out = delivery_projection(root)

        assert out["accepted"] == 1
        assert out["provider_sent"] == 0
        assert out["accepted_unconfirmed"] == 1
        row = out["items"][0]
        assert row["id"] == "ob-legacy"
        assert row["provider_id"] == "buf-legacy"
        assert row["accepted_at"] == at
        assert row["state"] == "accepted_unconfirmed"
        assert row["provider_sent"] is None
        assert row["provider_sent_at"] is None
        assert row["x_visible"] is None

    def test_acceptance_time_is_not_the_future_booked_send_time(self, tmp_path):
        import json
        from engine.marketing.telemetry import delivery_projection

        accepted_at = "2026-07-01T10:00:00Z"
        booked_at = "2026-07-01T10:30:00Z"
        posted = self._posted("ob-booked", "buf-booked", accepted_at)
        posted["receipt"]["booked_at"] = booked_at
        root = self._root(tmp_path, ledger=[
            {"id": "ob-booked", "from": "queued", "to": "approved",
             "at": accepted_at, "actor": "test", "note": "approved", "receipt": None},
            {"id": "ob-booked", "from": "approved", "to": "posting",
             "at": accepted_at, "actor": "publisher", "note": "in-flight", "receipt": None},
            posted,
        ], metrics=[])
        (root / "data" / "marketing" / "outbox" / "items.jsonl").write_text(
            json.dumps({"id": "ob-booked", "status": "queued",
                        "account": "flagship"}) + "\n", encoding="utf-8")

        row = delivery_projection(root)["items"][0]

        assert row["accepted_at"] == accepted_at
        assert row["booked_at"] == booked_at

    def test_provider_sent_survives_a_later_failed_lookup_as_stale_evidence(
            self, tmp_path):
        import json

        from engine.marketing.telemetry import delivery_projection

        accepted_at = "2026-07-01T10:00:00Z"
        sent_at = "2026-07-01T10:02:00Z"
        root = self._root(
            tmp_path,
            ledger=[
                {"id": "ob-sent", "from": "queued", "to": "approved",
                 "at": accepted_at, "actor": "test", "note": "approved",
                 "receipt": None},
                {"id": "ob-sent", "from": "approved", "to": "posting",
                 "at": accepted_at, "actor": "publisher", "note": "in-flight",
                 "receipt": None},
                self._posted("ob-sent", "buf-sent", accepted_at),
            ],
            metrics=[
                {
                    "remote_id": "buf-sent",
                    "polled_at": "2026-07-01T10:03:00Z",
                    "ok": True,
                    "metrics": {},
                    "delivery": {
                        "schema": "marketing.provider_delivery/v1",
                        "read_ok": True,
                        "state": "provider_sent",
                        "provider_id": "buf-sent",
                        "channel_id": "chan-1",
                        "provider_status": "sent",
                        "scheduling_type": "automatic",
                        "notification_status": None,
                        "due_at": accepted_at,
                        "provider_sent": True,
                        "provider_sent_at": sent_at,
                        "external_url": "https://x.com/mm/status/1",
                        "x_visible": None,
                        "x_visible_at": None,
                        "channel_ready": True,
                        "channel": {"id": "chan-1"},
                        "publishing_error": None,
                        "observed_at": "2026-07-01T10:03:00Z",
                        "error": None,
                    },
                },
                {
                    "remote_id": "buf-sent",
                    "polled_at": "2026-07-01T10:04:00Z",
                    "ok": False,
                    "metrics": {},
                    "delivery": {
                        "schema": "marketing.provider_delivery/v1",
                        "read_ok": False,
                        "state": "unknown_degraded",
                        "provider_id": "buf-sent",
                        "channel_id": "chan-1",
                        "provider_status": None,
                        "provider_sent": None,
                        "provider_sent_at": None,
                        "x_visible": None,
                        "x_visible_at": None,
                        "observed_at": "2026-07-01T10:04:00Z",
                        "error": "network_error: timeout",
                    },
                },
            ],
        )
        (root / "data" / "marketing" / "outbox" / "items.jsonl").write_text(
            json.dumps({"id": "ob-sent", "status": "queued",
                        "account": "flagship"}) + "\n", encoding="utf-8")

        out = delivery_projection(root)

        assert out["accepted"] == 1
        assert out["provider_sent"] == 1
        assert out["accepted_unconfirmed"] == 0
        row = out["items"][0]
        assert row["state"] == "provider_sent"
        assert row["provider_sent"] is True
        assert row["provider_sent_at"] == sent_at
        assert row["observed_at"] == "2026-07-01T10:03:00Z"
        assert row["observation_stale"] is True
        assert row["latest_lookup_error"] == "network_error: timeout"
        assert row["x_visible"] is None

    def test_a_post_with_real_metrics_is_confirmed(self, tmp_path):
        from datetime import datetime, timezone

        from engine.marketing.telemetry import unconfirmed_sends

        root = self._root(
            tmp_path,
            ledger=[self._posted("ob-1", "buf-1", "2026-07-01T10:00:00Z")],
            metrics=[{"remote_id": "buf-1", "metrics": {"impressions": 12}}])
        out = unconfirmed_sends(root, now=datetime(2026, 7, 31, tzinfo=timezone.utc))
        assert (out["posted"], out["confirmed"], out["unconfirmed"]) == (1, 1, 0)

    def test_a_stale_post_with_no_metric_at_all_is_flagged(self, tmp_path, capsys):
        from datetime import datetime, timezone

        from engine.marketing.telemetry import unconfirmed_sends

        root = self._root(
            tmp_path,
            ledger=[self._posted("ob-2", "buf-2", "2026-07-01T10:00:00Z")],
            metrics=[])
        out = unconfirmed_sends(root, now=datetime(2026, 7, 31, tzinfo=timezone.utc))
        assert out["unconfirmed"] == 1
        assert out["items"][0]["id"] == "ob-2"
        line = capsys.readouterr().out
        assert line.startswith("::warning title=marketing-unconfirmed-sends::")
        assert "ACCEPTED" in line

    def test_a_fresh_post_is_PENDING_not_a_fault(self, tmp_path, capsys):
        """Buffer's analytics lag is hours. Flagging inside it would cry wolf
        every single night on the posts that just went out."""
        from datetime import datetime, timezone

        from engine.marketing.telemetry import unconfirmed_sends

        root = self._root(
            tmp_path,
            ledger=[self._posted("ob-3", "buf-3", "2026-07-31T09:00:00Z")],
            metrics=[])
        out = unconfirmed_sends(root, now=datetime(2026, 7, 31, 12, tzinfo=timezone.utc))
        assert (out["pending"], out["unconfirmed"]) == (1, 0)
        assert capsys.readouterr().out == ""

    def test_a_polled_but_EMPTY_metrics_row_does_not_count_as_confirmation(self, tmp_path):
        """An `ok` poll that returned no numbers is not evidence of a send."""
        from datetime import datetime, timezone

        from engine.marketing.telemetry import unconfirmed_sends

        root = self._root(
            tmp_path,
            ledger=[self._posted("ob-4", "buf-4", "2026-07-01T10:00:00Z")],
            metrics=[{"remote_id": "buf-4", "ok": True, "metrics": {}}])
        out = unconfirmed_sends(root, now=datetime(2026, 7, 31, tzinfo=timezone.utc))
        assert out["unconfirmed"] == 1

    def test_it_never_raises_on_a_missing_ledger(self, tmp_path):
        """Telemetry is never-raise; a missing file must not break the nightly."""
        from engine.marketing.telemetry import unconfirmed_sends

        out = unconfirmed_sends(tmp_path / "nope")
        assert out["posted"] == 0 and out["unconfirmed"] == 0

    def test_the_nightly_actually_runs_it(self):
        """A scan nothing calls is the defect it was written to fix."""
        import pathlib

        src = pathlib.Path("scripts/build_marketing.py").read_text(encoding="utf-8")
        assert "unconfirmed_sends" in src
        assert "send_confirmed=" in src


class TestPostingOutbidsTelemetry:
    """`marketing-publish.yml` polls metrics on the SAME Buffer token and the
    SAME 24h quota the publisher posts with, so every telemetry call is a post
    the desk may not get to make.

    2026-08-11: the once-daily gate was hour-only, and `date -u +%H` reads "13"
    for the whole hour — so BOTH the 13:00Z and the 13:30Z sweep polled, at 2x
    the per-run cap. Run 31453875632 is the receipt: a live post attempt came
    back `429 retry after 37768s`, and 02:56Z + 37768s = 13:25Z, the minute the
    previous day's poll rolls out of Buffer's rolling 24h window. Buffer named
    whose calls were in the way of the post.

    (tests/test_marketing_metrics_poll_quota.py pins the poller's own two
    bounds — stop-on-429 and cap-the-run — but is baselined in
    config/unrun_test_baseline.json, i.e. no CI job runs it. These three live
    here so the ruling has a guard that actually executes.)
    """

    WF = Path(__file__).resolve().parents[1] / ".github/workflows/marketing-publish.yml"

    def _poll_step(self) -> dict:
        import yaml

        steps = yaml.safe_load(self.WF.read_text(encoding="utf-8"))["jobs"]["publish"]["steps"]
        return [s for s in steps if "poll post metrics" in str(s.get("name", ""))][0]

    def test_the_workflow_uses_due_since_success_not_a_wall_clock_slot(self):
        """A delayed sweep must reconcile due work instead of missing the day."""
        run = self._poll_step()["run"]
        assert "--if-due" in run
        assert "date -u +%H" not in run
        assert "date -u +%M" not in run
        assert '"13"' not in run

    def test_a_breaking_post_now_dispatch_spends_nothing_on_telemetry(self):
        """A `post_now` click is an operator trying to get ONE post out NOW.
        Every other manual dispatch still polls."""
        step = self._poll_step()
        assert "post_now_item" in str((step.get("env") or {}).get("POST_NOW_ITEM", "")), \
            "the step must see the breaking-dispatch input to be able to skip on it"
        run = step["run"]
        assert "POST_NOW_ITEM" in run and "exit 0" in run
        assert run.index("POST_NOW_ITEM") < run.index("scripts.marketing_metrics_poll"), (
            "the post_now bail must precede the reconciliation call")
        assert "github.event_name" not in run, (
            "due-since-success replaced the brittle schedule-clock branch")

    def test_the_per_run_call_cap_stays_well_under_the_daily_allowance(self):
        import scripts.marketing_metrics_poll as MP

        assert MP._MAX_CALLS_PER_RUN <= 8, (
            "the publisher shares this token; a telemetry cap large enough to "
            "matter is a posting outage waiting for a busy day")

    def _step(self, needle: str) -> dict:
        import yaml

        steps = yaml.safe_load(self.WF.read_text(encoding="utf-8"))["jobs"]["publish"]["steps"]
        return [s for s in steps if needle in str(s.get("name", ""))][0]

    def test_a_recall_dispatch_spends_nothing_on_telemetry(self):
        """A recall is the KILL-SWITCH: the operator is cancelling posts already
        booked at Buffer, and every one of those deletes is a call on this same
        rolling 24h allowance. The post that cannot be PULLED is worse than the
        post that cannot be sent, so telemetry may not stand in front of it.

        Pinned as a NEGATED guard rather than by string equality: what matters is
        that a recall dispatch turns the step OFF, not the spelling."""
        poll_if = str(self._poll_step().get("if", ""))
        assert "recall_pending" in poll_if, (
            "the poll step must see the recall input to be able to skip on it — "
            "a recall run polling telemetry is the 2026-08-03 failure class "
            "pointed at an emergency stop")
        assert re.search(r"!\s*\(.*recall_pending", poll_if, re.S), (
            "the recall guard must NEGATE the dispatch (skip when recalling), "
            f"not select for it: {poll_if!r}")

    def test_the_publisher_and_the_poller_sit_out_the_same_recall(self):
        """The two steps that spend Buffer calls must agree about a recall. If
        the publisher's guard is ever reworded, the poller's moves with it —
        otherwise the quieter half silently starts spending again."""
        poll_if = str(self._poll_step().get("if", ""))
        pub_if = str(self._step("run publisher").get("if", ""))
        assert "recall_pending" in pub_if, (
            "publisher recall guard vanished — re-derive the poller's from it")
        assert re.search(r"!\s*\(.*recall_pending", pub_if, re.S), pub_if
        clause = "github.event_name == 'workflow_dispatch' && inputs.recall_pending"
        assert clause in pub_if and clause in poll_if, (
            "both Buffer-spending steps carry the same recall clause so a "
            f"recall run makes ZERO calls: publisher={pub_if!r} poll={poll_if!r}")

# ─────────────────────────────────────────────────────────────────────────────
# Provider-delivery normalization contract (MX-X recovery Lane A)
# ─────────────────────────────────────────────────────────────────────────────

def _delivery_post(*, status="scheduled", scheduling="automatic",
                   sent_at=None, due_at="2026-07-23T15:30:00Z",
                   channel_id="chan-1", post_id="buf-1", notification=None,
                   active_device=True, disconnected=False, locked=False,
                   paused=False, external="https://x.com/mm/status/1",
                   publishing_error=None):
    return {
        "id": post_id,
        "channelId": channel_id,
        "status": status,
        "schedulingType": scheduling,
        "dueAt": due_at,
        "sentAt": sent_at,
        "externalLink": external,
        "notificationStatus": notification,
        "error": publishing_error,
        "channel": {
            "id": channel_id,
            "isDisconnected": disconnected,
            "isLocked": locked,
            "isQueuePaused": paused,
            "hasActiveMemberDevice": active_device,
        },
    }


@pytest.mark.parametrize(
    ("status", "scheduling", "sent_at", "publishing_error", "state", "sent"),
    [
        ("draft", None, None, None, "accepted_unconfirmed", False),
        ("needs_approval", None, None, None, "accepted_unconfirmed", False),
        ("scheduled", "automatic", None, None, "accepted_unconfirmed", False),
        ("sending", "automatic", None, None, "accepted_unconfirmed", False),
        ("sent", "automatic", "2026-07-23T15:31:00Z", None,
         "provider_sent", True),
        ("error", "automatic", None,
         {"message": "Platform rejected post", "supportUrl": "https://support.buffer.com/help"},
         "provider_failed", False),
    ],
)
def test_delivery_normalizer_covers_documented_buffer_statuses(
        status, scheduling, sent_at, publishing_error, state, sent):
    from engine.marketing.social_publisher import _normalize_delivery_observation

    obs = _normalize_delivery_observation(
        _delivery_post(status=status, scheduling=scheduling, sent_at=sent_at,
                       publishing_error=publishing_error),
        requested_post_id="buf-1", expected_channel_id="chan-1",
        observed_at="2026-07-23T16:00:00Z",
    )

    assert obs["read_ok"] is True
    assert obs["state"] == state
    assert obs["provider_sent"] is sent
    assert obs["x_visible"] is None
    if publishing_error:
        assert obs["publishing_error"] == {
            "message": "Platform rejected post",
            "support_url": "https://support.buffer.com/help",
        }
        assert "rawError" not in obs["publishing_error"]


@pytest.mark.parametrize(
    ("kwargs", "expected_ready"),
    [
        ({"disconnected": True}, False),
        ({"locked": True}, False),
        ({"paused": True}, False),
        ({}, True),
    ],
)
def test_delivery_normalizer_exposes_channel_readiness_blocks(kwargs, expected_ready):
    from engine.marketing.social_publisher import _normalize_delivery_observation

    obs = _normalize_delivery_observation(
        _delivery_post(**kwargs), requested_post_id="buf-1",
        expected_channel_id="chan-1", observed_at="2026-07-23T16:00:00Z")

    assert obs["read_ok"] is True
    assert obs["channel_ready"] is expected_ready


def test_notification_mode_requires_an_active_member_device_for_dispatch():
    from engine.marketing.social_publisher import _normalize_delivery_observation

    obs = _normalize_delivery_observation(
        _delivery_post(scheduling="notification", notification="notified",
                       active_device=False),
        requested_post_id="buf-1", expected_channel_id="chan-1",
        observed_at="2026-07-23T16:00:00Z")

    assert obs["read_ok"] is True
    assert obs["state"] == "accepted_unconfirmed"
    assert obs["scheduling_type"] == "notification"
    assert obs["channel_ready"] is False


@pytest.mark.parametrize(
    ("post", "requested", "expected_channel", "reason"),
    [
        (_delivery_post(post_id="wrong"), "buf-1", "chan-1", "provider_id_mismatch"),
        (_delivery_post(channel_id="wrong"), "buf-1", "chan-1", "expected_channel_mismatch"),
        (_delivery_post(status="future_status"), "buf-1", "chan-1", "unknown_provider_status"),
        (_delivery_post(status="sent", sent_at=None), "buf-1", "chan-1", "sent_without_sent_at"),
        (_delivery_post(status="scheduled", sent_at="2026-07-23T15:31:00Z"),
         "buf-1", "chan-1", "non_sent_status_with_sent_at"),
        (_delivery_post(due_at="not-a-time"), "buf-1", "chan-1", "malformed_due_at"),
        (_delivery_post(external="javascript:alert(1)"),
         "buf-1", "chan-1", "unsafe_external_link"),
    ],
)
def test_delivery_normalizer_fails_closed_on_bad_or_mismatched_evidence(
        post, requested, expected_channel, reason):
    from engine.marketing.social_publisher import _normalize_delivery_observation

    obs = _normalize_delivery_observation(
        post, requested_post_id=requested, expected_channel_id=expected_channel,
        observed_at="2026-07-23T16:00:00Z")

    assert obs["read_ok"] is False
    assert obs["state"] == "unknown_degraded"
    assert obs["provider_sent"] is None
    assert reason in (obs["error"] or "")


def test_graphql_failure_returns_explicit_degraded_delivery_without_mutation(monkeypatch):
    from engine.marketing.social_publisher import BufferPublisher

    pub = BufferPublisher(token="tkn")
    captured = {}

    def fake_transport(payload):
        captured.update(payload)
        return {"errors": [{"message": "provider unavailable"}]}

    monkeypatch.setattr(pub, "_transport", fake_transport)
    res = pub.fetch_post_metrics(
        "buf-1", expected_channel_id="chan-1", now=_NOW)

    assert res.ok is False
    assert res.delivery["read_ok"] is False
    assert res.delivery["state"] == "unknown_degraded"
    assert res.delivery["provider_sent"] is None
    assert "graphql_error" in (res.delivery["error"] or "")
    assert captured["query"].lstrip().startswith("query ")
    assert "mutation" not in captured["query"]

# ─────────────────────────────────────────────────────────────────────────────
# Bounded one-item provider readback (zero mutation / zero retry-create)
# ─────────────────────────────────────────────────────────────────────────────

def test_delivery_readback_binds_canonical_item_provider_and_channel_without_writes(tmp_path):
    import scripts.marketing_metrics_poll as poller

    item_id = _seed_posted(
        tmp_path, external_id="buf-readback", account="mastermind_news", at=_NOW)
    cfg = tmp_path / "config" / "marketing.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "publish:\n  channels:\n    mastermind_news: chan-news\n",
        encoding="utf-8",
    )
    metrics_path = tmp_path / "data" / "marketing" / "post_metrics.jsonl"
    metrics_path.write_text(
        '{"remote_id":"older","polled_at":"2026-07-22T00:00:00Z"}\n',
        encoding="utf-8",
    )
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in (tmp_path / "data" / "marketing").rglob("*")
        if path.is_file()
    }

    delivery = {
        "schema": "marketing.provider_delivery/v1",
        "read_ok": True,
        "state": "provider_sent",
        "provider_id": "buf-readback",
        "channel_id": "chan-news",
        "provider_status": "sent",
        "scheduling_type": "automatic",
        "notification_status": None,
        "due_at": "2026-07-23T14:55:00Z",
        "provider_sent": True,
        "provider_sent_at": "2026-07-23T15:00:00Z",
        "external_url": "https://x.com/mastermind_news/status/777",
        "x_visible": None,
        "x_visible_at": None,
        "channel_ready": True,
        "channel": {
            "id": "chan-news", "is_disconnected": False, "is_locked": False,
            "is_queue_paused": False, "has_active_member_device": True,
        },
        "publishing_error": None,
        "observed_at": _NOW.strftime(_ISO),
        "error": None,
    }

    class ReadOnlyPublisher:
        def __init__(self):
            self.calls = []

        def fetch_post_metrics(self, remote_id, *, expected_channel_id=None, now=None):
            self.calls.append((remote_id, expected_channel_id, now))
            return _metrics_ok(delivery["external_url"], {}, updated=None,
                               delivery=delivery)

    publisher = ReadOnlyPublisher()
    result = poller.delivery_readback(
        tmp_path, item_id=item_id, now=_NOW, publisher=publisher)

    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in (tmp_path / "data" / "marketing").rglob("*")
        if path.is_file()
    }
    assert result["ok"] is True
    assert result["read_only"] is True
    assert result["item_id"] == item_id
    assert result["account"] == "mastermind_news"
    assert result["provider_id"] == "buf-readback"
    assert result["expected_channel_id"] == "chan-news"
    assert result["acceptance"]["outbox_status"] == "posted"
    assert result["delivery"] == delivery
    assert result["delivery"]["x_visible"] is None
    assert publisher.calls == [("buf-readback", "chan-news", _NOW)]
    assert after == before, "readback must not append metrics or mutate any live ledger"


def test_delivery_readback_separates_acceptance_from_booked_send_time(tmp_path):
    import scripts.marketing_metrics_poll as poller
    from engine.marketing.outbox import enqueue, make_item, transition

    accepted = datetime(2026, 7, 23, 14, 0, tzinfo=timezone.utc)
    booked_at = "2026-07-23T14:30:00Z"
    item = make_item(account="flagship", kind="signal", text="booked later",
                     as_of="2026-07-23", provenance="test", now=accepted)
    enqueue(item, root=tmp_path, max_per_account_day=99)
    transition(item["id"], "approved", actor="t", root=tmp_path)
    transition(item["id"], "posting", actor="t", root=tmp_path)
    transition(item["id"], "posted", actor="publisher", root=tmp_path,
               receipt={"backend": "buffer", "external_id": "buf-booked-readback",
                        "at": accepted.strftime(_ISO), "booked_at": booked_at})
    _write_flagship_channel(tmp_path)

    class Publisher:
        def fetch_post_metrics(self, remote_id, *, expected_channel_id=None, now=None):
            delivery = _successful_delivery(remote_id, _NOW.strftime(_ISO))
            return _metrics_ok(None, {}, updated=None, delivery=delivery)

    result = poller.delivery_readback(
        tmp_path, item_id=item["id"], now=_NOW, publisher=Publisher())

    assert result["ok"] is True
    assert result["acceptance"]["accepted_at"] == accepted.strftime(_ISO)
    assert result["acceptance"]["booked_at"] == booked_at


def test_delivery_readback_refuses_non_posted_item_without_provider_call(tmp_path):
    import scripts.marketing_metrics_poll as poller
    from engine.marketing.outbox import enqueue, make_item

    item = make_item(
        account="flagship", kind="signal", text="queued only", as_of="2026-07-23",
        provenance="test", now=_NOW)
    enqueue(item, root=tmp_path, max_per_account_day=99)

    class MustNotCall:
        def fetch_post_metrics(self, *args, **kwargs):
            raise AssertionError("provider read must not run for an unaccepted item")

    result = poller.delivery_readback(
        tmp_path, item_id=item["id"], now=_NOW, publisher=MustNotCall())

    assert result["ok"] is False
    assert result["error"] == "item_not_provider_accepted"
    assert result["outbox_status"] == "queued"


def test_delivery_readback_without_authorized_token_is_explicit_dark_noop(
        tmp_path, monkeypatch):
    import scripts.marketing_metrics_poll as poller

    item_id = _seed_posted(tmp_path, external_id="buf-dark", account="flagship", at=_NOW)
    cfg = tmp_path / "config" / "marketing.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "publish:\n  channels:\n    flagship: chan-flagship\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("BUFFER_TOKEN", raising=False)

    result = poller.delivery_readback(tmp_path, item_id=item_id, now=_NOW)

    assert result["ok"] is False
    assert result["read_only"] is True
    assert result["error"] == "buffer_token_unavailable"
    assert result["network_attempted"] is False

class TestDeliveryReadbackWorkflowIsolation:
    WF = Path(__file__).resolve().parents[1] / ".github/workflows/marketing-publish.yml"

    def _workflow(self):
        import yaml
        return yaml.safe_load(self.WF.read_text(encoding="utf-8"))

    def test_workflow_exposes_a_bounded_readback_input(self):
        workflow = self._workflow()
        inputs = workflow[True]["workflow_dispatch"]["inputs"]
        assert "delivery_readback_item" in inputs
        assert inputs["delivery_readback_item"]["default"] == ""

    def test_readback_runs_in_a_read_only_job_and_publish_job_is_excluded(self):
        workflow = self._workflow()
        jobs = workflow["jobs"]
        assert "delivery-readback" in jobs
        readback = jobs["delivery-readback"]
        assert readback["permissions"] == {"contents": "read"}
        assert "delivery_readback_item" in str(readback.get("if", ""))
        assert "delivery_readback_item" in str(jobs["publish"].get("if", ""))
        assert re.search(r"!\s*=\s*''|!=\s*''", str(readback.get("if", "")))
        assert re.search(r"==\s*''", str(jobs["publish"].get("if", "")))

    def test_readback_job_has_one_query_command_and_no_sender_or_writer(self):
        workflow = self._workflow()
        readback = workflow["jobs"]["delivery-readback"]
        steps = readback["steps"]
        checkout = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")][0]
        assert checkout.get("with", {}).get("persist-credentials") is False
        all_run = "\n".join(str(s.get("run") or "") for s in steps)
        assert all_run.count("--delivery-readback-item") == 1
        assert "scripts.marketing_metrics_poll" in all_run
        for forbidden in (
            "scripts.marketing_publisher", "scripts.marketing_recall",
            "git push", "git commit", "--live", "createPost", "deletePost",
        ):
            assert forbidden not in all_run

# ─────────────────────────────────────────────────────────────────────────────
# Due-since-success reconciliation (no clock-only/global-watermark semantics)
# ─────────────────────────────────────────────────────────────────────────────

def _successful_delivery(provider_id: str, observed_at: str) -> dict:
    return {
        "schema": "marketing.provider_delivery/v1",
        "read_ok": True,
        "state": "accepted_unconfirmed",
        "provider_id": provider_id,
        "channel_id": "chan-flagship",
        "provider_status": "scheduled",
        "scheduling_type": "automatic",
        "notification_status": None,
        "due_at": observed_at,
        "provider_sent": False,
        "provider_sent_at": None,
        "external_url": None,
        "x_visible": None,
        "x_visible_at": None,
        "channel_ready": True,
        "channel": {
            "id": "chan-flagship", "is_disconnected": False,
            "is_locked": False, "is_queue_paused": False,
            "has_active_member_device": True,
        },
        "publishing_error": None,
        "observed_at": observed_at,
        "error": None,
    }


class _DuePublisher:
    def __init__(self):
        self.calls = []

    def fetch_post_metrics(self, remote_id, *, expected_channel_id=None, now=None):
        self.calls.append(remote_id)
        observed_at = (now or _NOW).strftime(_ISO)
        delivery = _successful_delivery(remote_id, observed_at)
        return _metrics_ok(None, {}, updated=None, delivery=delivery)


def _write_flagship_channel(tmp_path: Path) -> None:
    cfg = tmp_path / "config" / "marketing.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "publish:\n  channels:\n    flagship: chan-flagship\n",
        encoding="utf-8",
    )


def test_due_reconciliation_runs_after_a_missed_clock_slot(tmp_path):
    import scripts.marketing_metrics_poll as poller

    late = datetime(2026, 7, 23, 19, 34, tzinfo=timezone.utc)
    _seed_posted(tmp_path, external_id="buf-late", at=late)
    _write_flagship_channel(tmp_path)
    publisher = _DuePublisher()

    summary = poller.poll(
        tmp_path, now=late, publisher=publisher, due_only=True,
        daily_call_budget=8)

    assert publisher.calls == ["buf-late"]
    assert summary["due"] == 1
    assert summary["polled"] == 1
    assert summary["stopped"] is None


def test_due_reconciliation_services_oldest_unobserved_item_first(tmp_path):
    import scripts.marketing_metrics_poll as poller

    for hour, remote_id in [(12, "buf-old"), (13, "buf-mid"), (14, "buf-new")]:
        at = datetime(2026, 7, 23, hour, 0, tzinfo=timezone.utc)
        _seed_posted(tmp_path, external_id=remote_id, at=at, text=remote_id)
    _write_flagship_channel(tmp_path)
    publisher = _DuePublisher()

    summary = poller.poll(
        tmp_path, now=_NOW, publisher=publisher, due_only=True,
        max_calls=1, daily_call_budget=99)

    assert summary["due"] == 3
    assert publisher.calls == ["buf-old"]


def test_fresh_successful_observation_is_not_polled_again(tmp_path):
    import json
    import scripts.marketing_metrics_poll as poller

    _seed_posted(tmp_path, external_id="buf-fresh", at=_NOW)
    _write_flagship_channel(tmp_path)
    p = tmp_path / "data" / "marketing" / "post_metrics.jsonl"
    p.write_text(json.dumps({
        "remote_id": "buf-fresh", "account": "flagship",
        "polled_at": "2026-07-23T14:30:00Z", "ok": True, "metrics": {},
        "delivery": _successful_delivery("buf-fresh", "2026-07-23T14:30:00Z"),
    }) + "\n", encoding="utf-8")
    publisher = _DuePublisher()

    summary = poller.poll(
        tmp_path, now=_NOW, publisher=publisher, due_only=True,
        daily_call_budget=8)

    assert publisher.calls == []
    assert summary["due"] == 0
    assert summary["deferred_fresh"] == 1
    assert summary["polled"] == 0


def test_graphql_or_http_failure_never_counts_as_successful_reconciliation(tmp_path):
    import json
    import scripts.marketing_metrics_poll as poller

    _seed_posted(tmp_path, external_id="buf-failed", at=_NOW)
    _write_flagship_channel(tmp_path)
    p = tmp_path / "data" / "marketing" / "post_metrics.jsonl"
    p.write_text(json.dumps({
        "remote_id": "buf-failed", "account": "flagship",
        "polled_at": "2026-07-23T14:55:00Z", "ok": False, "metrics": {},
        "delivery": {
            "schema": "marketing.provider_delivery/v1", "read_ok": False,
            "state": "unknown_degraded", "provider_id": "buf-failed",
            "observed_at": "2026-07-23T14:55:00Z",
            "error": "graphql_error: provider unavailable",
        },
    }) + "\n", encoding="utf-8")
    publisher = _DuePublisher()

    summary = poller.poll(
        tmp_path, now=_NOW, publisher=publisher, due_only=True,
        daily_call_budget=8)

    assert publisher.calls == ["buf-failed"]
    assert summary["due"] == 1


def test_partial_batch_does_not_advance_past_unfinished_targets(tmp_path):
    import scripts.marketing_metrics_poll as poller

    for index in range(3):
        _seed_posted(
            tmp_path, external_id=f"buf-partial-{index}", at=_NOW,
            text=f"distinct reconciliation item {index}")
    _write_flagship_channel(tmp_path)
    first = _DuePublisher()

    first_summary = poller.poll(
        tmp_path, now=_NOW, publisher=first, due_only=True,
        max_calls=1, daily_call_budget=99)
    second = _DuePublisher()
    second_summary = poller.poll(
        tmp_path, now=_NOW, publisher=second, due_only=True,
        max_calls=2, daily_call_budget=99)

    assert first_summary["polled"] == 1
    assert first_summary["stopped"] == "max_calls"
    assert len(first.calls) == 1
    assert set(second.calls).isdisjoint(first.calls)
    assert len(second.calls) == 2
    assert second_summary["polled"] == 2
    assert second_summary["stopped"] is None


def test_rolling_budget_reserves_shared_token_capacity(tmp_path):
    import json
    import scripts.marketing_metrics_poll as poller

    _seed_posted(tmp_path, external_id="buf-budget", at=_NOW)
    _write_flagship_channel(tmp_path)
    p = tmp_path / "data" / "marketing" / "post_metrics.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"remote_id": f"older-{i}", "polled_at": "2026-07-23T14:45:00Z",
         "ok": False, "metrics": {}, "note": "poll_failed: timeout"}
        for i in range(8)
    ]
    p.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    publisher = _DuePublisher()

    summary = poller.poll(
        tmp_path, now=_NOW, publisher=publisher, due_only=True,
        daily_call_budget=8)

    assert publisher.calls == []
    assert summary["due"] == 1
    assert summary["recent_calls"] == 8
    assert summary["budget_remaining"] == 0
    assert summary["stopped"] == "rolling_budget"
