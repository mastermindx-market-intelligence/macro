"""XS push lane (engine/marketing/press_stream.py) — rule construction, event
normalization parity with the REST lane, spool round-trip, rule sync
convergence, daemon drain wiring, and the shipped-config pins.

No test here touches the network or the websocket: chunk/normalize/spool are
pure or tmp_path-local, and sync_rules is exercised against a recorded fake
transport. The websockets lib is deliberately NOT imported — CI packs may not
carry it, and the listener degrades to nothing by design.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.marketing import press_stream as ps  # noqa: E402


def _cfg(handles: list[dict], **over) -> dict:
    cfg = {
        "enabled": True,
        "rule_tag_prefix": "mmx-press",
        "tier_intervals_s": {"fast": 5, "mid": 30, "slow": 120},
        "handles": handles,
    }
    cfg.update(over)
    return cfg


def _tweet(tid: str, handle: str, text: str) -> dict:
    return {"id": tid, "text": text, "createdAt": "2026-08-03T12:00:00Z",
            "author": {"userName": handle}}


# ─────────────────────────────────────────────────────────────────────────────
# chunk_rules
# ─────────────────────────────────────────────────────────────────────────────

class TestChunkRules:
    def test_groups_by_tier_with_config_intervals(self):
        rules = ps.chunk_rules(_cfg([
            {"handle": "A", "tier": "fast"},
            {"handle": "B", "tier": "fast"},
            {"handle": "C", "tier": "slow"},
        ]))
        by_tag = {r["tag"]: r for r in rules}
        assert by_tag["mmx-press-fast-1"]["value"] == "from:A OR from:B"
        assert by_tag["mmx-press-fast-1"]["interval_seconds"] == 5.0
        assert by_tag["mmx-press-slow-1"]["value"] == "from:C"
        assert by_tag["mmx-press-slow-1"]["interval_seconds"] == 120.0

    def test_255_char_value_cap_forces_chunking(self):
        handles = [{"handle": f"account_{i:02d}_padded_to_be_long", "tier": "mid"}
                   for i in range(30)]
        rules = ps.chunk_rules(_cfg(handles))
        assert len(rules) > 1
        for rule in rules:
            assert len(rule["value"]) <= 255
        # Every handle survives the chunking exactly once.
        clauses = " OR ".join(r["value"] for r in rules).split(" OR ")
        assert len(clauses) == 30 and len(set(clauses)) == 30

    def test_satire_never_reaches_a_rule(self):
        rules = ps.chunk_rules(
            _cfg([{"handle": "RealDesk", "tier": "fast"},
                  {"handle": "HalfwayPost", "tier": "fast"}]),
            satire_blocklist=["HalfwayPost"],
        )
        assert all("HalfwayPost" not in r["value"] for r in rules)

    def test_deterministic_across_calls(self):
        cfg = _cfg([{"handle": "A", "tier": "fast"},
                    {"handle": "B", "tier": "mid"}])
        assert ps.chunk_rules(cfg) == ps.chunk_rules(cfg)


# ─────────────────────────────────────────────────────────────────────────────
# normalize_event — REST-lane parity is the contract
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeEvent:
    REG = {"deitaone": {"handle": "DeItaone", "tier": "fast",
                        "corroboration_class": "hearsay"},
           "rawsalerts": {"handle": "rawsalerts", "tier": "mid",
                          "corroboration_class": "hearsay",
                          "strict_corroboration": True,
                          "route": "wire"}}

    def test_shapes_top_level_nested_single_and_bare(self):
        tw = _tweet("100", "DeItaone", "CPI PRINTS 2.9%")
        for payload in ({"tweets": [tw]},
                        {"data": {"tweets": [tw]}},
                        {"tweet": tw},
                        tw):
            items = ps.normalize_event(payload, self.REG)
            assert len(items) == 1, payload
            assert items[0]["headline"] == "CPI PRINTS 2.9%"

    def test_output_matches_rest_lane_for_the_same_tweet(self):
        """A pushed tweet and a polled tweet must be the SAME item downstream —
        ids, source keys and corroboration flags all byte-equal, or the shared
        seen-ledger would double-ingest whatever both transports saw."""
        from engine.marketing.press_providers import TwitterApiIoProvider
        handle_cfg = {"handle": "DeItaone", "corroboration_class": "hearsay"}
        prov = TwitterApiIoProvider({"handles": [handle_cfg]}, spend_cap_usd=75.0)
        rest_items, _ = prov.parse_tweets(
            {"tweets": [_tweet("42", "DeItaone", "FED HOLDS RATES")]},
            handle_cfg, since_id=None)
        push_items = ps.normalize_event(
            {"tweets": [_tweet("42", "DeItaone", "FED HOLDS RATES")]}, self.REG)
        assert len(rest_items) == 1 and len(push_items) == 1
        for key in ("id", "source", "source_name", "source_tier", "url",
                    "headline", "body_snippet", "corroboration_class"):
            assert push_items[0][key] == rest_items[0][key], key

    def test_register_gate_drops_unknown_handles(self):
        items = ps.normalize_event(
            {"tweets": [_tweet("7", "SomeRandomAcct", "hello")]}, self.REG)
        assert items == []

    def test_strict_and_route_flags_carried(self):
        items = ps.normalize_event(
            {"tweets": [_tweet("8", "rawsalerts", "BREAKING: thing")]}, self.REG)
        assert items[0]["strict_corroboration"] is True
        assert items[0]["route"] == "wire"

    def test_satire_dropped_even_when_registered(self):
        reg = {"halfwaypost": {"handle": "HalfwayPost", "tier": "fast"}}
        items = ps.normalize_event(
            {"tweets": [_tweet("9", "HalfwayPost", "satire")]},
            reg, satire={"halfwaypost"})
        assert items == []

    def test_garbage_payloads_yield_empty(self):
        for payload in (None, [], "x", {"unrelated": 1}, {"tweets": "nope"}):
            assert ps.normalize_event(payload, self.REG) == []


# ─────────────────────────────────────────────────────────────────────────────
# Spool
# ─────────────────────────────────────────────────────────────────────────────

class TestSpool:
    def test_round_trip_dedupes_and_truncates(self, tmp_path):
        items = [{"id": "a", "headline": "one"},
                 {"id": "b", "headline": "two"},
                 {"id": "a", "headline": "one again"}]
        assert ps.append_spool(tmp_path, items) == 3
        drained = ps.drain_spool(tmp_path)
        assert [i["id"] for i in drained] == ["a", "b"]
        # Drain truncates: a second drain sees nothing.
        assert ps.drain_spool(tmp_path) == []

    def test_missing_spool_is_empty(self, tmp_path):
        assert ps.drain_spool(tmp_path) == []

    def test_corrupt_lines_are_skipped_not_fatal(self, tmp_path):
        spool = tmp_path / "data" / "marketing" / "press" / "stream_spool.jsonl"
        spool.parent.mkdir(parents=True)
        spool.write_text('{"id": "ok"}\nnot-json\n[]\n', encoding="utf-8")
        assert [i["id"] for i in ps.drain_spool(tmp_path)] == ["ok"]


# ─────────────────────────────────────────────────────────────────────────────
# sync_rules against a recorded fake transport
# ─────────────────────────────────────────────────────────────────────────────

class TestSyncRules:
    def _record(self, monkeypatch, remote_rules):
        calls: list[tuple[str, dict | None]] = []

        def fake_request(cfg, path, payload=None):
            calls.append((path, payload))
            if path.endswith("get_rules"):
                return {"rules": remote_rules, "status": "success"}
            if path.endswith("add_rule"):
                return {"rule_id": f"rid-{len(calls)}", "status": "success"}
            return {"status": "success"}

        monkeypatch.setattr(ps, "_rules_request", fake_request)
        return calls

    def test_creates_and_activates_missing_rules(self, monkeypatch):
        calls = self._record(monkeypatch, [])
        report = ps.sync_rules(_cfg([{"handle": "A", "tier": "fast"}]))
        assert report["created"] == ["mmx-press-fast-1"]
        adds = [p for p, body in calls if p.endswith("add_rule")]
        activates = [body for p, body in calls
                     if p.endswith("update_rule") and body and body.get("is_effect") == 1]
        assert len(adds) == 1 and len(activates) == 1

    def test_updates_drifted_and_reactivates_dark_rules(self, monkeypatch):
        remote = [{"rule_id": "r1", "tag": "mmx-press-fast-1",
                   "value": "from:OLD", "interval_seconds": 5, "is_effect": 1},
                  {"rule_id": "r2", "tag": "mmx-press-mid-1",
                   "value": "from:B", "interval_seconds": 30, "is_effect": 0}]
        self._record(monkeypatch, remote)
        report = ps.sync_rules(_cfg([{"handle": "A", "tier": "fast"},
                                     {"handle": "B", "tier": "mid"}]))
        assert sorted(report["updated"]) == ["mmx-press-fast-1", "mmx-press-mid-1"]

    def test_unchanged_rules_are_not_rewritten(self, monkeypatch):
        remote = [{"rule_id": "r1", "tag": "mmx-press-fast-1",
                   "value": "from:A", "interval_seconds": 5, "is_effect": 1}]
        calls = self._record(monkeypatch, remote)
        report = ps.sync_rules(_cfg([{"handle": "A", "tier": "fast"}]))
        assert report["unchanged"] == ["mmx-press-fast-1"]
        assert not [p for p, _ in calls if p.endswith("update_rule")]

    def test_stale_prefixed_rules_deleted_foreign_rules_untouched(self, monkeypatch):
        remote = [{"rule_id": "r9", "tag": "mmx-press-mid-9",
                   "value": "from:GONE", "interval_seconds": 30, "is_effect": 1},
                  {"rule_id": "rX", "tag": "someone-else",
                   "value": "from:other", "interval_seconds": 60, "is_effect": 1}]
        calls = self._record(monkeypatch, remote)
        report = ps.sync_rules(_cfg([{"handle": "A", "tier": "fast"}]))
        assert report["deleted"] == ["mmx-press-mid-9"]
        deletes = [body for p, body in calls if p.endswith("delete_rule")]
        assert deletes == [{"rule_id": "r9"}]

    def test_deactivate_only_flips_is_effect_and_deletes_nothing(self, monkeypatch):
        remote = [{"rule_id": "r1", "tag": "mmx-press-fast-1",
                   "value": "from:A", "interval_seconds": 5, "is_effect": 1}]
        calls = self._record(monkeypatch, remote)
        report = ps.sync_rules(_cfg([{"handle": "A", "tier": "fast"}]),
                               deactivate_only=True)
        assert report["deactivated"] == ["mmx-press-fast-1"]
        assert not [p for p, _ in calls if p.endswith("delete_rule")]
        offs = [body for p, body in calls
                if p.endswith("update_rule") and body]
        assert offs and all(b.get("is_effect") == 0 for b in offs)


# ─────────────────────────────────────────────────────────────────────────────
# Daemon drain wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestDaemonDrain:
    def _daemon(self):
        import importlib
        return importlib.import_module("scripts.marketing_fastlane_daemon")

    def _stub(self, monkeypatch, tmp_path, *, drained: list[dict]):
        d = self._daemon()
        import engine.marketing.breaking_feed as bf
        import engine.marketing.intelligence_desk as idesk
        import engine.marketing.press_lane as pl
        import engine.marketing.press_providers as pp
        import engine.marketing.press_stream as pstream
        monkeypatch.setattr(d, "ROOT", tmp_path)
        monkeypatch.setattr(d, "_PRESS_STATE_PATH", tmp_path / "press" / "state.json")
        monkeypatch.setattr(d, "_PRESS_SEEN_PATH", tmp_path / "press" / "seen.json")
        monkeypatch.setattr(d, "_load_yaml", lambda p: {})
        monkeypatch.setattr(bf, "poll_all", lambda root, cfg: [])
        monkeypatch.setattr(pp, "poll_all",
                            lambda root, cfg, state, *, offline=False, now=None: [])
        monkeypatch.setattr(idesk, "update_intelligence_desk",
                            lambda *a, **k: {"health": {}})
        drain_calls: list = []

        def fake_drain(root):
            drain_calls.append(root)
            return list(drained)

        monkeypatch.setattr(pstream, "drain_spool", fake_drain)
        seen_items: dict = {}

        def fake_tick(items, **kwargs):
            seen_items["items"] = list(items)
            return {"emitted": [], "skipped": [], "digest": [], "blocked": [],
                    "rail": [], "_rail_order": {}, "intelligence": [],
                    "_seen": [], "_emit_allowed": False}

        monkeypatch.setattr(pl, "run_press_tick", fake_tick)
        return d, drain_calls, seen_items

    def test_live_tick_feeds_stream_items_through_the_pipeline(
            self, monkeypatch, tmp_path):
        item = {"id": "x1", "source": "x_DeItaone", "headline": "h"}
        d, drain_calls, seen = self._stub(monkeypatch, tmp_path, drained=[item])
        d._run_press_tick(dry_run=False)
        assert drain_calls, "live tick must drain the stream spool"
        assert item in seen["items"]

    def test_dry_run_never_drains(self, monkeypatch, tmp_path):
        d, drain_calls, _ = self._stub(monkeypatch, tmp_path, drained=[])
        d._run_press_tick(dry_run=True)
        assert drain_calls == [], "a dry-run drain would consume items " \
                                  "the next live tick was owed"


# ─────────────────────────────────────────────────────────────────────────────
# Shipped config pins
# ─────────────────────────────────────────────────────────────────────────────

class TestShippedConfig:
    def _cfg(self):
        import yaml
        return yaml.safe_load(
            (ROOT / "config" / "press_sources.yml").read_text(encoding="utf-8"))

    def test_stream_on_poll_off(self):
        cfg = self._cfg()
        # Operator 2026-08-03: push lane ON (billing scales with news),
        # hot-poll lane OFF (billing scaled with the clock). BOTH pins in one
        # test because flipping either back is the same money decision.
        assert cfg["x_stream"]["enabled"] is True
        assert cfg["x_follow"]["enabled"] is False

    def test_register_carries_v1_and_v2_handles(self):
        cfg = self._cfg()
        handles = {h["handle"] for h in cfg["x_stream"]["handles"]}
        # v1 spine survives the transport change…
        assert {"DeItaone", "FirstSquawk", "financialjuice", "zerohedge",
                "WHPressPool", "unusual_whales", "CoinDesk"} <= handles
        # …and the v2 robustness additions the operator asked for are present.
        assert {"NickTimiraos", "Newsquawk", "BNONews", "KobeissiLetter",
                "WuBlockchain"} <= handles
        assert len(handles) >= 25

    def test_osint_additions_are_strict(self):
        cfg = self._cfg()
        rows = {h["handle"]: h for h in cfg["x_stream"]["handles"]}
        for osint in ("Faytuks", "sentdefender", "rawsalerts", "BRICSinfo"):
            assert rows[osint].get("strict_corroboration") is True, osint

    def test_rules_fit_the_vendor_value_cap(self):
        cfg = self._cfg()
        rules = ps.chunk_rules(cfg["x_stream"],
                               satire_blocklist=cfg.get("satire_blocklist") or [])
        assert rules, "shipped register must produce at least one rule"
        for rule in rules:
            assert len(rule["value"]) <= 255
            assert 0.1 <= float(rule["interval_seconds"]) <= 86400


# ─────────────────────────────────────────────────────────────────────────────
# Non-consuming stream snapshots (WEB-P1 G1; same incumbent spool)
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_spool(root: Path) -> Path:
    return root / "data" / "marketing" / "press" / "stream_spool.jsonl"


def _snapshot_ids(batch: object) -> list[str]:
    return [row["id"] for row in batch.items]


def test_peek_is_non_consuming_and_recovers_after_unacknowledged_crash(tmp_path):
    ps.append_spool(tmp_path, [{"id": "event-1", "headline": "Source A"}])
    first = ps.peek_spool(tmp_path)
    assert _snapshot_ids(first) == ["event-1"]
    assert _snapshot_spool(tmp_path).stat().st_size > 0
    assert _snapshot_ids(ps.peek_spool(tmp_path)) == ["event-1"]
    assert ps.ack_spool(tmp_path, first) is True
    assert _snapshot_ids(ps.peek_spool(tmp_path)) == []


def test_ack_exact_prefix_preserves_arrivals_appended_during_acceptance(tmp_path):
    ps.append_spool(tmp_path, [{"id": "event-before"}])
    before = ps.peek_spool(tmp_path)
    ps.append_spool(tmp_path, [{"id": "event-during"}])
    assert ps.ack_spool(tmp_path, before) is True
    assert _snapshot_ids(ps.peek_spool(tmp_path)) == ["event-during"]


def test_ack_refuses_modified_prefix_without_deleting_data(tmp_path):
    ps.append_spool(tmp_path, [{"id": "original"}])
    original = ps.peek_spool(tmp_path)
    path = _snapshot_spool(tmp_path)
    path.write_text('{"id":"replacement"}' + chr(10), encoding="utf-8")
    assert ps.ack_spool(tmp_path, original) is False
    assert _snapshot_ids(ps.peek_spool(tmp_path)) == ["replacement"]


def test_ack_refuses_stale_batch_after_inode_replacement_even_if_bytes_match(tmp_path):
    ps.append_spool(tmp_path, [{"id": "A"}])
    original = ps.peek_spool(tmp_path)
    path = _snapshot_spool(tmp_path)
    replacement = path.with_name("stream_spool.pending")
    replacement.write_bytes(path.read_bytes())
    os.replace(replacement, path)
    assert ps.ack_spool(tmp_path, original) is False
    assert _snapshot_ids(ps.peek_spool(tmp_path)) == ["A"]


def test_failed_ack_replace_keeps_the_original_unconsumed(tmp_path, monkeypatch):
    ps.append_spool(tmp_path, [{"id": "A"}])
    snapshot = ps.peek_spool(tmp_path)
    before = _snapshot_spool(tmp_path).read_bytes()

    def fail_replace(src, dest):
        raise OSError("controlled replacement failure")

    monkeypatch.setattr(ps.os, "replace", fail_replace)
    assert ps.ack_spool(tmp_path, snapshot) is False
    assert _snapshot_spool(tmp_path).read_bytes() == before


def test_ack_keeps_spool_file_permissions_after_atomic_replace(tmp_path):
    ps.append_spool(tmp_path, [{"id": "A"}])
    path = _snapshot_spool(tmp_path)
    path.chmod(0o640)
    before = ps.peek_spool(tmp_path)
    assert ps.ack_spool(tmp_path, before) is True
    assert path.stat().st_mode & 0o777 == 0o640


def test_pending_partial_tail_is_preserved_on_ack(tmp_path):
    ps.append_spool(tmp_path, [{"id": "complete"}])
    path = _snapshot_spool(tmp_path)
    with path.open("ab") as fh:
        fh.write(b'{"id":"unfinished"')
    before = ps.peek_spool(tmp_path)
    assert _snapshot_ids(before) == ["complete"]
    assert before.blocked_reason == "partial_trailing_row"
    assert before.byte_count < path.stat().st_size
    assert ps.ack_spool(tmp_path, before) is True
    assert path.read_bytes() == b'{"id":"unfinished"'


def test_pending_malformed_complete_row_blocks_later_items(tmp_path):
    ps.append_spool(tmp_path, [{"id": "complete"}])
    path = _snapshot_spool(tmp_path)
    with path.open("ab") as fh:
        fh.write(b'not-json\n{"id":"later"}\n')
    before = ps.peek_spool(tmp_path)
    assert _snapshot_ids(before) == ["complete"]
    assert before.blocked_reason == "malformed_complete_row"
    assert ps.ack_spool(tmp_path, before) is True
    assert path.read_bytes() == b'not-json\n{"id":"later"}\n'


def test_ack_denies_when_entire_spool_is_torn_row(tmp_path):
    path = _snapshot_spool(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"id":"unfinished"')
    snapshot = ps.peek_spool(tmp_path)
    assert snapshot.items == ()
    assert snapshot.byte_count == 0
    assert snapshot.blocked_reason == "partial_trailing_row"
    assert ps.ack_spool(tmp_path, snapshot) is False
    assert path.read_bytes() == b'{"id":"unfinished"'


# ─────────────────────────────────────────────────────────────────────────────
# WEB-P1 G1: default-OFF in-daemon stream-only acceptance pilot
# No provider, X outbox, or second intelligence store may be created.
# ─────────────────────────────────────────────────────────────────────────────

def _canary_setup(monkeypatch, root, *, floor=0.0):
    from datetime import datetime, timezone
    from scripts import marketing_fastlane_daemon as daemon
    from engine.marketing import breaking_feed, press_providers, sentinel

    now = datetime.now(timezone.utc)
    item = {
        "id": "canary-source-001", "source": "x_MarketDesk",
        "source_name": "Market Desk", "source_tier": "x_relay",
        "x_handle": "MarketDesk", "corroboration_class": "hearsay",
        "headline": "Company ABC files updated financial guidance",
        "body_snippet": "Company ABC files updated financial guidance and detailed revenue context.",
        "url": "https://twitter.com/MarketDesk/status/1234",
        "published_at": now.isoformat(), "route": "wire",
        "matched": {"tickers": ["ABC"]},
    }
    intel = {
        "salience_floor": floor,
        "max_packets_per_tick": 10,
        "db_paths": ["data/marketing/press/intelligence.db"],
        "snapshot_paths": ["data/marketing/press/intelligence.json"],
    }
    press_cfg = {"wire": {"intelligence": intel}}
    marketing_cfg = {"breaking": {"llm": {"enabled": False}}}
    monkeypatch.setattr(daemon, "ROOT", root)
    monkeypatch.setattr(daemon, "_PRESS_STATE_PATH", root / "state.json")
    monkeypatch.setattr(daemon, "_PRESS_SEEN_PATH", root / "seen.json")
    monkeypatch.setattr(daemon, "_load_yaml", lambda p: (
        press_cfg if p.name == "press_sources.yml" else marketing_cfg
    ))
    monkeypatch.setenv("PRESS_STREAM_ACCEPTANCE_CANARY", "1")
    monkeypatch.setattr(sentinel, "publish_enabled", lambda: False)
    other_sources = []
    monkeypatch.setattr(breaking_feed, "poll_all",
                        lambda *a, **k: other_sources.append("wire") or [])
    monkeypatch.setattr(press_providers, "poll_all",
                        lambda *a, **k: other_sources.append("providers") or [])
    monkeypatch.setattr(daemon, "_write_wires_sink",
                        lambda *a, **k: other_sources.append("publisher") or [])
    ps.append_spool(root, [item])
    return daemon, press_cfg, other_sources, item


def test_canary_actual_press_packet_to_existing_sqlite_and_snapshot(tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "ACCEPTED"
    assert result["_emit_allowed"] is False
    assert external == []
    assert ps.peek_spool(tmp_path).items == ()
    sink = tmp_path / "data/marketing/press/intelligence.json"
    snapshot = json.loads(sink.read_text(encoding="utf-8"))
    assert item["id"] in {
        e["event_id"] for story in snapshot["stories"] for e in story["evidence"]
    }
    # Story identity is persisted before the Desk write for crash-safe replay;
    # source consumption and provider cursors are NOT checkpointed here.
    assert (tmp_path / "state.json").exists()
    assert "story_spine" in json.loads((tmp_path / "state.json").read_text())
    assert not (tmp_path / "seen.json").exists()
    assert not list(tmp_path.rglob("items.jsonl"))


def test_canary_desk_snapshot_failure_retains_source_then_replays_without_duplicate(
        tmp_path, monkeypatch):
    from engine.marketing import intelligence_desk as desk
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    real_writer = desk._atomic_json

    def fail_projection(*args, **kwargs):
        raise OSError("simulated committed-store / failed-public-snapshot split")

    with monkeypatch.context() as ctx:
        ctx.setattr(desk, "_atomic_json", fail_projection)
        failed = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert failed["_durable_stream_canary"] == "STORE_OR_PROJECTION_FAILED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert "story_spine" in json.loads((tmp_path / "state.json").read_text())
    store = desk.IntelligenceStore(
        tmp_path / "data/marketing/press/intelligence.db"
    )
    try:
        assert len(store.snapshot(now=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc))["stories"]) == 1
    finally:
        store.close()
    recovered = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert recovered["_durable_stream_canary"] == "ACCEPTED"
    snapshot = json.loads((tmp_path /
                           "data/marketing/press/intelligence.json").read_text())
    assert len(snapshot["stories"]) == 1
    assert ps.peek_spool(tmp_path).items == ()
    assert external == []
    assert real_writer is desk._atomic_json


def test_canary_does_not_ack_below_intelligence_threshold(tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(
        monkeypatch, tmp_path, floor=101.0
    )
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "SOURCE_NOT_QUALIFIED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []
    assert not (tmp_path / "data/marketing/press/intelligence.json").exists()


def test_canary_refuses_publisher_armed_before_poll_or_drain(tmp_path, monkeypatch):
    from engine.marketing import sentinel
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(sentinel, "publish_enabled", lambda: True)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "REFUSED_PUBLISH_ARMED"
    assert result["_emit_allowed"] is False
    assert external == []
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]


def test_canary_accepts_qualified_prefix_without_deleting_torn_suffix(
        tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    path = _snapshot_spool(tmp_path)
    with path.open("ab") as output:
        output.write(b'{"id":"torn-row"')
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "ACCEPTED_WITH_BLOCKED_SUFFIX"
    assert path.read_bytes() == b'{"id":"torn-row"'
    assert external == []



def test_canary_identity_checkpoint_never_advances_existing_providers_or_outbox_counters(
        tmp_path, monkeypatch):
    daemon, _, external, _ = _canary_setup(monkeypatch, tmp_path)
    original = {
        "providers": {"alpaca_news": {"since": "2026-10-08T12:00:00Z",
                                      "last_poll": "2026-10-08T12:01:00Z",
                                      "spend_usd": 4.5}},
        "wire_day_counts": {"day": "2026-10-09", "counts": {"flagship": 3}},
        "flagship_counter": {"day": "2026-10-09", "count": 3},
        "corroboration": {"existing": {"sources": ["fixture"]}},
        "wire_headroom": {"day": "2026-10-09", "exhausted": 0},
    }
    (tmp_path / "state.json").write_text(json.dumps(original))
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "ACCEPTED"
    saved = json.loads((tmp_path / "state.json").read_text())
    for key, value in original.items():
        assert saved[key] == value, key
    assert "story_spine" in saved and "intel_claims" in saved
    assert external == []



def test_canary_refuses_before_store_when_identity_checkpoint_fails(
        tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)

    def deny_checkpoint(_state):
        raise OSError("simulated host-local identity writer unavailable")

    monkeypatch.setattr(daemon, "_save_press_state", deny_checkpoint)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "IDENTITY_CHECKPOINT_FAILED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert not (tmp_path / "data/marketing/press/intelligence.db").exists()
    assert external == []


def test_canary_refuses_ack_when_served_snapshot_drops_event(
        tmp_path, monkeypatch):
    from engine.marketing import intelligence_desk as desk
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    def no_visible_event(*args, **kwargs):
        return {"stories": [], "health": {"state": "quiet"}}
    monkeypatch.setattr(desk, "update_intelligence_desk", no_visible_event)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "SOURCE_NOT_SERVED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []


def test_canary_never_invokes_llm_summarizer(tmp_path, monkeypatch):
    from engine.marketing import breaking_summary
    daemon, _, external, _ = _canary_setup(monkeypatch, tmp_path)
    calls = []
    def fake_llm(*args, **kwargs):
        calls.append("provider called")
        return None
    monkeypatch.setattr(breaking_summary, "_llm_summarize", fake_llm)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "ACCEPTED"
    assert calls == []
    assert external == []



def test_canary_unavailable_spool_read_fails_closed_without_consumption(
        tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    def deny_read(_root):
        raise OSError("simulated inaccessible source file")
    with monkeypatch.context() as ctx:
        ctx.setattr(ps, "peek_spool", deny_read)
        result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "SOURCE_READ_FAILED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []


def test_canary_press_pipeline_failure_preserves_original_spool(
        tmp_path, monkeypatch):
    from engine.marketing import press_lane
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    def deny_scoring(*args, **kwargs):
        raise RuntimeError("simulated scoring engine failure")
    monkeypatch.setattr(press_lane, "run_press_tick", deny_scoring)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "PIPELINE_FAILED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []


def test_canary_malformed_desk_packet_fails_closed(
        tmp_path, monkeypatch):
    from engine.marketing import press_lane, intelligence_desk
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    def malformed(*args, **kwargs):
        return {"intelligence": [{
            "schema": intelligence_desk.PACKET_SCHEMA,
            "id": "story-bad", "evidence": None,
        }]}
    monkeypatch.setattr(press_lane, "run_press_tick", malformed)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "SOURCE_NOT_QUALIFIED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []



def test_canary_log_has_explicit_source_acceptance_outcome(caplog):
    import logging
    from datetime import datetime, timezone
    from scripts import marketing_fastlane_daemon as daemon
    with caplog.at_level(logging.INFO, logger="fastlane_daemon"):
        daemon._log_press_tick(
            {"_emit_allowed": False,
             "_durable_stream_canary": "SOURCE_NOT_QUALIFIED",
             "_durable_stream_count": 1},
            datetime.now(timezone.utc), dry_run=False,
        )
    assert "stream_canary=SOURCE_NOT_QUALIFIED" in caplog.text


def test_canary_env_flag_alone_cannot_displace_regular_press_collectors(
        tmp_path, monkeypatch):
    """An inherited flag must not silently starve the ordinary looping feed."""
    daemon, _, external, _ = _canary_setup(monkeypatch, tmp_path)
    result = daemon._run_press_tick(dry_run=False)
    assert "_durable_stream_canary" not in result
    assert "wire" in external
    assert "providers" in external


def test_cli_explicit_one_shot_press_routes_only_one_canary_tick(monkeypatch):
    from scripts import marketing_fastlane_daemon as daemon
    monkeypatch.setenv(daemon._KILL_SWITCH_ENV, "1")
    monkeypatch.setenv("PRESS_STREAM_ACCEPTANCE_CANARY", "1")
    calls = []
    def record_tick(*, dry_run, canary_once=False):
        calls.append((dry_run, canary_once))
        return {"_emit_allowed": False}
    monkeypatch.setattr(daemon, "_run_press_tick", record_tick)
    monkeypatch.setattr(daemon, "_log_press_tick", lambda *args, **kwargs: None)
    monkeypatch.setattr(daemon, "_touch_heartbeat", lambda *args, **kwargs: None)
    assert daemon.main(["--lane", "press", "--once"]) == 0
    assert calls == [(False, True)]


def test_cli_dry_run_cannot_promote_canary_to_consuming_tick(monkeypatch):
    from scripts import marketing_fastlane_daemon as daemon
    monkeypatch.setenv("PRESS_STREAM_ACCEPTANCE_CANARY", "1")
    calls = []
    def record_tick(*, dry_run, canary_once=False):
        calls.append((dry_run, canary_once))
        return {"_emit_allowed": False}
    monkeypatch.setattr(daemon, "_run_press_tick", record_tick)
    monkeypatch.setattr(daemon, "_log_press_tick", lambda *args, **kwargs: None)
    assert daemon.main(["--lane", "press", "--once", "--dry-run"]) == 0
    assert calls == [(True, False)]


def test_canary_refuses_public_desk_snapshot_destination_before_any_source_write(
        tmp_path, monkeypatch):
    """X-relay acquisition is not a public-display rights receipt."""
    daemon, press_cfg, external, item = _canary_setup(monkeypatch, tmp_path)
    press_cfg["wire"]["intelligence"]["snapshot_paths"] = [
        "/var/lib/macro-live/public/live/intelligence.json",
        "data/marketing/press/intelligence.json",
    ]
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "PUBLIC_DESTINATION_NOT_ADMITTED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "data/marketing/press/intelligence.db").exists()
    assert external == []


def test_canary_refuses_path_traversal_into_public_site(tmp_path, monkeypatch):
    daemon, press_cfg, external, item = _canary_setup(monkeypatch, tmp_path)
    press_cfg["wire"]["intelligence"]["snapshot_paths"] = [
        "data/marketing/press/../../../site/live/intelligence.json",
    ]
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "PUBLIC_DESTINATION_NOT_ADMITTED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert not (tmp_path / "state.json").exists()
    assert external == []


def test_canary_refuses_unqualified_default_desk_paths(tmp_path, monkeypatch):
    daemon, press_cfg, external, item = _canary_setup(monkeypatch, tmp_path)
    press_cfg["wire"]["intelligence"].pop("snapshot_paths", None)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "PUBLIC_DESTINATION_NOT_ADMITTED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []


def test_canary_refuses_symlinked_private_snapshot_into_site(tmp_path, monkeypatch):
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    target = tmp_path / "site" / "live" / "intelligence.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    private_sink = tmp_path / "data" / "marketing" / "press" / "intelligence.json"
    private_sink.symlink_to(target)
    result = daemon._run_press_tick(dry_run=False, canary_once=True)
    assert result["_durable_stream_canary"] == "PUBLIC_DESTINATION_NOT_ADMITTED"
    assert [x["id"] for x in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert not target.exists()
    assert not (tmp_path / "state.json").exists()
    assert external == []


def test_cli_one_shot_native_canary_accepts_into_private_desk_only(
        tmp_path, monkeypatch):
    """A real main(argv) turn reaches existing press scorer, store and snapshot."""
    daemon, _, external, item = _canary_setup(monkeypatch, tmp_path)
    monkeypatch.setenv(daemon._KILL_SWITCH_ENV, "1")
    heartbeat = []
    monkeypatch.setattr(daemon, "_touch_heartbeat",
                        lambda now: heartbeat.append(now))
    assert daemon.main(["--lane", "press", "--once"]) == 0
    assert len(heartbeat) == 1
    assert external == []
    sink = tmp_path / "data/marketing/press/intelligence.json"
    published = json.loads(sink.read_text(encoding="utf-8"))
    assert item["id"] in {
        row.get("event_id")
        for story in published["stories"]
        for row in story["evidence"]
    }
    assert ps.peek_spool(tmp_path).items == ()
    assert (tmp_path / "data/marketing/press/intelligence.db").exists()
    assert not (tmp_path / "seen.json").exists()
    assert not list(tmp_path.rglob("items.jsonl"))


def test_cli_one_shot_with_public_sink_refuses_without_source_effect(
        tmp_path, monkeypatch):
    daemon, press_cfg, external, item = _canary_setup(monkeypatch, tmp_path)
    monkeypatch.setenv(daemon._KILL_SWITCH_ENV, "1")
    press_cfg["wire"]["intelligence"]["snapshot_paths"] = [
        "/var/lib/macro-live/public/live/intelligence.json",
    ]
    monkeypatch.setattr(daemon, "_touch_heartbeat", lambda now: None)
    assert daemon.main(["--lane", "press", "--once"]) == 0
    assert [row["id"] for row in ps.peek_spool(tmp_path).items] == [item["id"]]
    assert external == []
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "data/marketing/press/intelligence.db").exists()
