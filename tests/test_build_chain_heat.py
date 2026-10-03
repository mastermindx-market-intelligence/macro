"""tests/test_build_chain_heat.py — unit tests for the chain-heat envelope wrapper.

Tests the pure parts of scripts/build_chain_heat.py:
  - build_envelope: shape, key renames, nullable fields
  - _enrich_events: side → ask_share mapping
  - end-to-end: aggregate_chain_heat + build_envelope integration (no I/O)
"""
from __future__ import annotations

import json

import pytest

from scripts.build_chain_heat import (
    build_envelope,
    _enrich_events,
    _SIDE_TO_ASK_SHARE,
    _SIDE_TO_CATEGORY_PROXY_SHARE,
)
from engine.options_structure import aggregate_chain_heat


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_events(n: int, root: str = "SMH", right: str = "C", exp: str = "2026-09-18",
                 strike: float = 530.0, premium: float = 1_500_000.0,
                 side: str = "~buy") -> list[dict]:
    """Produce n synthetic feed/v1 events."""
    return [
        {
            "id": f"ev{i}",
            "ts": f"2026-07-08T1{i % 6}:00:00Z",
            "root": root,
            "right": right,
            "exp": exp,
            "strike": strike,
            "premium": premium,
            "side": side,
        }
        for i in range(n)
    ]


# ─── _enrich_events ───────────────────────────────────────────────────────────

class TestEnrichEvents:
    def test_buy_side_mapped(self):
        events = [{"side": "~buy"}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] == pytest.approx(0.80)

    def test_sell_side_mapped(self):
        events = [{"side": "~sell"}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] == pytest.approx(0.20)

    def test_mixed_side_mapped(self):
        events = [{"side": "mixed"}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] == pytest.approx(0.50)

    def test_none_side_stays_none(self):
        events = [{"side": None}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] is None

    def test_existing_ask_share_not_overwritten(self):
        events = [{"side": "~buy", "ask_share": 0.42}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] == pytest.approx(0.42)

    def test_original_not_mutated(self):
        events = [{"side": "~buy"}]
        _enrich_events(events)
        assert "ask_share" not in events[0]

    # ── category_proxy_share seam (additive, independent of ask_share) ────────

    def test_category_proxy_buy_side_mapped(self):
        out = _enrich_events([{"side": "~buy"}])
        assert out[0]["category_proxy_share"] == pytest.approx(0.80)

    def test_category_proxy_sell_side_mapped(self):
        out = _enrich_events([{"side": "~sell"}])
        assert out[0]["category_proxy_share"] == pytest.approx(0.20)

    def test_category_proxy_mixed_is_known_half(self):
        out = _enrich_events([{"side": "mixed"}])
        assert out[0]["category_proxy_share"] == pytest.approx(0.50)

    def test_category_proxy_unknown_side_is_none(self):
        out = _enrich_events([{"side": None}])
        assert out[0]["category_proxy_share"] is None

    def test_category_proxy_key_always_present(self):
        out = _enrich_events([{"side": "mystery"}])
        assert "category_proxy_share" in out[0]
        assert out[0]["category_proxy_share"] is None

    def test_preexisting_category_proxy_share_is_not_trusted(self):
        events = [{"side": "~sell", "category_proxy_share": 0.99}]
        out = _enrich_events(events)
        assert out[0]["category_proxy_share"] == pytest.approx(0.20)

    def test_category_proxy_independent_of_legacy_ask_share(self):
        events = [{"side": "~buy", "ask_share": 0.42}]
        out = _enrich_events(events)
        assert out[0]["ask_share"] == pytest.approx(0.42)            # legacy kept
        assert out[0]["category_proxy_share"] == pytest.approx(0.80)  # seam recomputed

    def test_category_proxy_mapping_values(self):
        assert _SIDE_TO_CATEGORY_PROXY_SHARE["~buy"] == pytest.approx(0.80)
        assert _SIDE_TO_CATEGORY_PROXY_SHARE["~sell"] == pytest.approx(0.20)
        assert _SIDE_TO_CATEGORY_PROXY_SHARE["mixed"] == pytest.approx(0.50)


# ─── build_envelope ───────────────────────────────────────────────────────────

class TestBuildEnvelope:
    def _minimal_campaign(self, right: str = "CALL") -> dict:
        return {
            "option_symbol": "SMH   260918C00530000",
            "ticker": "SMH",
            "right": right,
            "strike": 530.0,
            "expiry": "2026-09-18",
            "dte": 71,
            "total_premium_mn": 5.0,
            "alert_count": 4,
            "span_minutes": 45.0,
            "first_seen": "2026-07-08T09:35:00Z",
            "last_seen": "2026-07-08T10:20:00Z",
            "ask_share": 0.80,
            "lean": "accumulation",
            "direction_reliability": "soft",
            "authority_tier": "display",
        }

    def test_schema_key(self):
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["schema"] == "options_flow.chain_heat/v1"

    def test_required_top_level_keys(self):
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        for key in ("schema", "asof", "source_asof", "built_at", "session_date", "threshold_mn",
                    "note_en", "note_zh", "campaigns"):
            assert key in env, f"missing top-level key: {key!r}"

    def test_session_date_and_asof_threaded(self):
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["session_date"] == "2026-07-08"
        assert env["asof"] == "2026-07-08T20:00:00Z"

    def test_legacy_asof_is_source_clock_not_rebuild_clock(self):
        env = build_envelope(
            [],
            "2026-07-08",
            "2026-07-08T19:55:00Z",
            built_at="2026-07-08T20:05:00Z",
        )
        assert env["asof"] == "2026-07-08T19:55:00Z"
        assert env["source_asof"] == "2026-07-08T19:55:00Z"
        assert env["built_at"] == "2026-07-08T20:05:00Z"

    def test_subsecond_source_identity_is_preserved(self):
        source_asof = "2026-07-08T19:55:00.987654Z"
        env = build_envelope(
            [],
            "2026-07-08",
            source_asof,
            built_at="2026-07-08T19:55:01.000001Z",
        )
        assert env["asof"] == source_asof
        assert env["source_asof"] == source_asof

    @pytest.mark.parametrize(
        "invalid",
        [None, "", "not-a-time", "2026-07-08T20:00:00", "2026-07-08T21:00:00+01:00"],
    )
    def test_invalid_source_time_fails_closed(self, invalid):
        with pytest.raises(ValueError, match="source_asof"):
            build_envelope([], "2026-07-08", invalid)

    def test_build_clock_cannot_precede_source_clock(self):
        with pytest.raises(ValueError, match="cannot precede"):
            build_envelope(
                [],
                "2026-07-08",
                "2026-07-08T20:05:00Z",
                built_at="2026-07-08T20:04:59Z",
            )

    def test_subsecond_clock_order_is_temporal_not_lexical(self):
        with pytest.raises(ValueError, match="cannot precede"):
            build_envelope(
                [],
                "2026-07-08",
                "2026-07-08T20:05:00.9Z",
                built_at="2026-07-08T20:05:00.10Z",
            )

    def test_threshold_mn_default(self):
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["threshold_mn"] == 3

    def test_right_renamed_to_type(self):
        campaigns = [self._minimal_campaign("CALL")]
        env = build_envelope(campaigns, "2026-07-08", "2026-07-08T20:00:00Z")
        c = env["campaigns"][0]
        assert "type" in c, "'type' key missing from campaign"
        assert "right" not in c, "'right' should be renamed to 'type'"
        assert c["type"] == "CALL"

    def test_right_renamed_put(self):
        campaigns = [self._minimal_campaign("PUT")]
        env = build_envelope(campaigns, "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["campaigns"][0]["type"] == "PUT"

    def test_last_seen_removed(self):
        campaigns = [self._minimal_campaign()]
        env = build_envelope(campaigns, "2026-07-08", "2026-07-08T20:00:00Z")
        assert "last_seen" not in env["campaigns"][0]

    def test_note_added_as_null(self):
        campaigns = [self._minimal_campaign()]
        env = build_envelope(campaigns, "2026-07-08", "2026-07-08T20:00:00Z")
        c = env["campaigns"][0]
        assert "note" in c
        assert c["note"] is None

    def test_existing_note_preserved(self):
        campaign = self._minimal_campaign()
        campaign["note"] = "Sustained sweep"
        env = build_envelope([campaign], "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["campaigns"][0]["note"] == "Sustained sweep"

    def test_note_en_not_validated(self):
        """'validated' must never appear in note_en (CI-enforced law)."""
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        assert "validated" not in env.get("note_en", "").lower()
        assert "validated" not in env.get("note_zh", "").lower()

    def test_empty_campaigns(self):
        env = build_envelope([], "2026-07-08", "2026-07-08T20:00:00Z")
        assert env["campaigns"] == []

    def test_original_campaigns_not_mutated(self):
        campaign = self._minimal_campaign()
        original_keys = set(campaign.keys())
        build_envelope([campaign], "2026-07-08", "2026-07-08T20:00:00Z")
        assert set(campaign.keys()) == original_keys

    def test_category_proxy_object_preserved_through_envelope(self):
        """The nested additive object survives build_envelope unchanged."""
        campaign = self._minimal_campaign()
        campaign["category_proxy"] = {
            "schema": "options_flow.category_proxy/v1",
            "basis": "side_category",
            "share": 0.8,
            "known_premium_usd": 4_000_000.0,
            "unknown_premium_usd": 1_000_000.0,
            "source_premium_usd": 5_000_000.0,
            "invalid_premium_count": 0,
            "source_certified_accepted": False,
        }
        env = build_envelope([campaign], "2026-07-08", "2026-07-08T20:00:00Z")
        cp = env["campaigns"][0]["category_proxy"]
        assert cp == campaign["category_proxy"]
        assert cp["schema"] == "options_flow.category_proxy/v1"
        assert cp["basis"] == "side_category"
        assert cp["source_certified_accepted"] is False

    def test_legacy_campaign_without_object_stays_legacy(self):
        """A legacy campaign (no category_proxy) is not silently upgraded."""
        campaign = self._minimal_campaign()
        env = build_envelope([campaign], "2026-07-08", "2026-07-08T20:00:00Z")
        assert "category_proxy" not in env["campaigns"][0]
        assert env["campaigns"][0]["ask_share"] == pytest.approx(0.80)


# ─── end-to-end: aggregate + wrap ─────────────────────────────────────────────

class TestEndToEnd:
    """Ensure aggregate_chain_heat + build_envelope produce a well-formed artifact."""

    def _feed_events(self) -> list[dict]:
        """Two campaigns: SMH Put 530 (big, buy-side) and QQQ Call 640 (smaller, sell)."""
        base = []
        # Campaign A: SMH 530P — 5 events × $1.5M = $7.5M, ~buy
        base += _make_events(5, root="SMH", right="P", exp="2026-09-18",
                              strike=530.0, premium=1_500_000.0, side="~buy")
        # Campaign B: QQQ 640C — 3 events × $1.5M = $4.5M, ~sell
        base += _make_events(3, root="QQQ", right="C", exp="2026-09-18",
                              strike=640.0, premium=1_500_000.0, side="~sell")
        # Too-small campaign: AAPL 200C — 1 event × $1M = $1M (below 3M gate)
        base += _make_events(1, root="AAPL", right="C", exp="2026-09-18",
                              strike=200.0, premium=1_000_000.0, side="~buy")
        return base

    def test_two_campaigns_above_threshold(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        # AAPL below gate, so 2 campaigns expected
        assert len(env["campaigns"]) == 2

    def test_sorted_by_premium_descending(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        prems = [c["total_premium_mn"] for c in env["campaigns"]]
        assert prems == sorted(prems, reverse=True)

    def test_type_field_present_not_right(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        for c in env["campaigns"]:
            assert "type" in c and "right" not in c
            assert c["type"] in ("CALL", "PUT")

    def test_buy_side_lean_accumulation(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        smh_campaign = next(c for c in env["campaigns"] if c["ticker"] == "SMH")
        # SMH was all ~buy → ask_share=0.80 → accumulation
        assert smh_campaign["lean"] == "accumulation"

    def test_sell_side_lean_distribution(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        qqq_campaign = next(c for c in env["campaigns"] if c["ticker"] == "QQQ")
        # QQQ was all ~sell → ask_share=0.20 → distribution
        assert qqq_campaign["lean"] == "distribution"

    def test_dte_computed(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        for c in env["campaigns"]:
            assert c["dte"] is not None and c["dte"] > 0

    def test_required_campaign_keys(self):
        """Every campaign must carry all keys the UI component reads."""
        ui_keys = {
            "option_symbol", "ticker", "type", "strike", "expiry", "dte",
            "total_premium_mn", "alert_count", "span_minutes", "first_seen",
            "ask_share", "lean", "direction_reliability", "authority_tier", "note",
        }
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        for i, c in enumerate(env["campaigns"]):
            missing = ui_keys - set(c.keys())
            assert not missing, f"campaign[{i}] missing keys: {missing}"

    def test_category_proxy_fields_roundtrip_envelope(self):
        """aggregate → build_envelope: the fresh object keeps every field."""
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
        expected_share = {"SMH": 0.80, "QQQ": 0.20}
        for c in env["campaigns"]:
            cp = c["category_proxy"]
            assert set(cp.keys()) == {
                "schema", "basis", "share", "known_premium_usd",
                "unknown_premium_usd", "source_premium_usd",
                "invalid_premium_count", "source_certified_accepted",
            }
            assert cp["schema"] == "options_flow.category_proxy/v1"
            assert cp["basis"] == "side_category"
            assert cp["source_certified_accepted"] is False
            # side category maps deterministically; coverage is complete here
            assert cp["share"] == pytest.approx(expected_share[c["ticker"]])
            assert cp["unknown_premium_usd"] == pytest.approx(0.0)
            assert cp["source_premium_usd"] == pytest.approx(cp["known_premium_usd"])

    def test_legacy_ask_share_042_not_promoted_to_category_proxy(self):
        """A measured-looking legacy ask_share never becomes the new proxy."""
        events = [
            {"id": "a", "ts": "2026-07-08T10:00:00Z", "root": "SMH", "right": "C",
             "exp": "2026-09-18", "strike": 530.0, "premium": 2_000_000.0,
             "side": None, "ask_share": 0.42},
            {"id": "b", "ts": "2026-07-08T10:10:00Z", "root": "SMH", "right": "C",
             "exp": "2026-09-18", "strike": 530.0, "premium": 2_000_000.0,
             "side": None, "ask_share": 0.42},
        ]
        raw = aggregate_chain_heat(_enrich_events(events), min_premium_mn=3.0,
                                   min_alerts=2, session_date="2026-07-08")
        assert len(raw) == 1
        c = raw[0]
        assert c["ask_share"] == pytest.approx(0.42)          # legacy preserved
        assert c["category_proxy"]["share"] is None            # unknown category
        assert c["category_proxy"]["share"] != pytest.approx(0.42)

    def test_equal_premium_same_category_different_quotes_proxy_stays_08(self):
        """Same category, equal premium, different quotes → proxy still .8."""
        events = [
            {"id": "a", "ts": "2026-07-08T10:00:00Z", "root": "SMH", "right": "C",
             "exp": "2026-09-18", "strike": 530.0, "premium": 2_000_000.0,
             "side": "~buy", "ask_share": 0.42},
            {"id": "b", "ts": "2026-07-08T10:10:00Z", "root": "SMH", "right": "C",
             "exp": "2026-09-18", "strike": 530.0, "premium": 2_000_000.0,
             "side": "~buy", "ask_share": 0.91},
        ]
        raw = aggregate_chain_heat(_enrich_events(events), min_premium_mn=3.0,
                                   min_alerts=2, session_date="2026-07-08")
        c = raw[0]
        assert c["category_proxy"]["share"] == pytest.approx(0.80)
        assert c["ask_share"] == pytest.approx(0.665, abs=0.001)
        assert c["category_proxy"]["share"] != pytest.approx(c["ask_share"])

    def test_no_fixture_promotes_source_certified_accepted(self):
        events = _enrich_events(self._feed_events())
        raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                                   session_date="2026-07-08")
        for c in raw:
            assert c["category_proxy"]["source_certified_accepted"] is False


def test_publisher_does_not_write_when_source_time_is_invalid(tmp_path, monkeypatch):
    import scripts.build_chain_heat as builder

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        builder,
        "fetch_feed",
        lambda: {
            "schema": "live_flow.feed/v1",
            "asof": "2026-07-08T20:00:00Z",
            "source_asof": "not-a-time",
            "session_date": "2026-07-08",
            "events": [],
        },
    )
    assert builder.main(["--no-publish"]) == 0
    assert not (tmp_path / "chain_heat_current.json").exists()


# ─── strict JSON emit (allow_nan=False) ───────────────────────────────────────

def test_strict_json_serialization_succeeds_for_valid_campaigns():
    """Valid finite campaigns serialize under allow_nan=False with no tokens."""
    events = _enrich_events(_make_events(2))
    raw = aggregate_chain_heat(events, min_premium_mn=3.0, min_alerts=2,
                               session_date="2026-07-08")
    env = build_envelope(raw, "2026-07-08", "2026-07-08T20:00:00Z")
    body = json.dumps(env, ensure_ascii=False, allow_nan=False)
    assert "Infinity" not in body
    assert "NaN" not in body


def test_publish_r2_rejects_poison_before_write(monkeypatch):
    """A nonfinite payload is refused before any PUT reaches the destination."""
    import scripts.build_chain_heat as builder

    class _FakeClient:
        def __init__(self) -> None:
            self.put_calls: list[dict] = []

        def put_object(self, **kwargs):
            self.put_calls.append(kwargs)

    client = _FakeClient()
    monkeypatch.setattr(builder, "_r2_client", lambda: client)
    poison = {
        "schema": "options_flow.chain_heat/v1",
        "campaigns": [{"ask_share": float("nan")}],
    }
    with pytest.raises(ValueError):
        builder.publish_r2(poison, "bucket")
    assert client.put_calls == []


def test_publisher_does_not_write_when_payload_is_poisoned(tmp_path, monkeypatch):
    """Strict serialization happens BEFORE the destination write (no file)."""
    import scripts.build_chain_heat as builder

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        builder,
        "fetch_feed",
        lambda: {
            "schema": "live_flow.feed/v1",
            "asof": "2026-07-08T20:00:00Z",
            "session_date": "2026-07-08",
            "events": [],
        },
    )
    monkeypatch.setattr(
        builder,
        "build_envelope",
        lambda *a, **k: {
            "schema": "options_flow.chain_heat/v1",
            "asof": float("inf"),
            "campaigns": [],
        },
    )
    assert builder.main(["--no-publish"]) == 0
    assert not (tmp_path / "chain_heat_current.json").exists()


def test_publisher_writes_valid_payload(tmp_path, monkeypatch):
    """The strict path still writes a clean, finite artifact on valid input."""
    import scripts.build_chain_heat as builder

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        builder,
        "fetch_feed",
        lambda: {
            "schema": "live_flow.feed/v1",
            "asof": "2026-07-08T20:00:00Z",
            "session_date": "2026-07-08",
            "events": [
                {"id": "a", "ts": "2026-07-08T10:00:00Z", "root": "SMH",
                 "right": "C", "exp": "2026-09-18", "strike": 530.0,
                 "premium": 1_500_000.0, "side": "~buy"},
                {"id": "b", "ts": "2026-07-08T10:10:00Z", "root": "SMH",
                 "right": "C", "exp": "2026-09-18", "strike": 530.0,
                 "premium": 1_500_000.0, "side": "~buy"},
            ],
        },
    )
    assert builder.main(["--no-publish"]) == 0
    out = tmp_path / "chain_heat_current.json"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Infinity" not in text and "NaN" not in text
    payload = json.loads(text)
    assert payload["campaigns"]
