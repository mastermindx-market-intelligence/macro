"""Tests for the china_visits dossier block in engine/china_intel_hub.py (P1).

Descriptive-only surface — NO score, NO rank input (masterplan §11.4 serial
firewall). Covers:
  - _ticker_to_sec_code: SZ/SS mapping, HK/malformed → None (not_applicable)
  - _visit_block: each reachable house failure state (masterplan §9.3):
    not_applicable, no_coverage, source_failure, stale, measured_no_event, ok
  - _visit_block upstream_degraded handling (P1-R1, same-cycle derivation):
    a degraded same-run china_filings refresh reads like a stale refusal when
    no rows exist for a name (never source_failure, never a false
    measured_no_event); rows present still render normally
  - first_seen_since_coverage_start is flagged on the EARLIEST row only, and
    a name first seen mid-coverage still reads "since coverage start", never
    "first ever"
  - _load_visits_context degrades safely against a real (empty) store
  - build() integration: the visits block appears on command rows and never
    moves opportunity_score/edge_remaining/stage (score neutrality)
  - P1-R3 (durable scoped key-exclusion recovery) hub-level hostile items:
    a company-scoped OPEN exception blocks measured_no_event for JUST that
    company (item 1) while an uninvolved company in the SAME ctx still reads
    measured_no_event (item 2, proves scoping is real, not a global block
    wearing a per-company label); an UNSCOPED exception (no usable sec_code)
    blocks EVERY name (item 4); positive rows + an open exception for the
    SAME company render normally AND carry coverage_exception (item 9); an
    unreadable ledger (exceptions_readable=False) fails closed globally
    exactly like an unscoped exception (item 10). A separate
    `_ctx_with_exceptions()` helper is used for all of these — the
    pre-existing `_ctx()` helper and every test built on it are UNCHANGED,
    so absent P1-R3 keys keep degrading to "no scoping" as before.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import china_intel_hub as hub  # noqa: E402
from lib import config  # noqa: E402


# --------------------------------------------------------------------------- #
# _ticker_to_sec_code
# --------------------------------------------------------------------------- #

class TestTickerToSecCode:
    def test_sz_ticker(self):
        assert hub._ticker_to_sec_code("000001.SZ") == ("000001", "szse")

    def test_ss_ticker(self):
        assert hub._ticker_to_sec_code("600519.SS") == ("600519", "sse")

    def test_hk_ticker_is_none(self):
        assert hub._ticker_to_sec_code("0700.HK") is None

    def test_no_dot_is_none(self):
        assert hub._ticker_to_sec_code("000001") is None

    def test_empty_is_none(self):
        assert hub._ticker_to_sec_code("") is None
        assert hub._ticker_to_sec_code(None) is None


# --------------------------------------------------------------------------- #
# _visit_block — house failure-state taxonomy
# --------------------------------------------------------------------------- #

def _ctx(by_code=None, coverage_start=None, health=None):
    return {"by_code": by_code or {}, "coverage_start": coverage_start,
            "health": health or {}}


class TestVisitBlockStates:
    def test_not_applicable_for_hk_ticker(self):
        block = hub._visit_block("0700.HK", _ctx(coverage_start="2026-08-01",
                                                    health={"status": "ok"}))
        assert block["state"] == "not_applicable"
        assert block["recent"] == []

    def test_no_coverage_when_never_started(self):
        block = hub._visit_block("000001.SZ", _ctx(coverage_start=None,
                                                       health={"status": "no_coverage"}))
        assert block["state"] == "no_coverage"
        assert block["recent"] == []

    def test_source_failure_takes_priority(self):
        block = hub._visit_block("000001.SZ", _ctx(
            coverage_start="2026-08-01",
            health={"status": "source_failure", "detail": "filings store unreadable"}))
        assert block["state"] == "source_failure"
        assert "unreadable" in block["detail"]
        assert block["recent"] == []

    def test_measured_no_event_when_healthy_and_absent(self):
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000001.SZ", _ctx(
            coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": fresh}))
        assert block["state"] == "measured_no_event"
        assert block["recent"] == []
        # honest — never claims a real-world "first ever"
        assert "since coverage start" in block["detail"]

    def test_stale_when_healthy_but_last_success_old(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        block = hub._visit_block("000001.SZ", _ctx(
            coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": old}))
        assert block["state"] == "stale"
        assert block["recent"] == []
        assert block["stale_days"] == 10

    def test_ok_with_rows_carries_typed_visitor_fields(self):
        rows = [{
            "announcement_id": "A1", "sec_code": "000001",
            "title": "平安银行：投资者关系活动记录表",
            "source_published_at": "2026-08-19T09:00:00+08:00",
            "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
            "ontology_version": "B0_DRAFT_pin-3d12412e561e", "adjunct_url": "/x.pdf",
        }]
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000001.SZ", _ctx(
            by_code={"000001": rows}, coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": fresh}))
        assert block["state"] == "ok"
        assert len(block["recent"]) == 1
        r = block["recent"][0]
        assert r["visitor_raw"] == "not_yet_available"
        assert r["visitor_class"] == "not_yet_available"
        assert r["ontology_version"] == "B0_DRAFT_pin-3d12412e561e"
        assert r["first_seen_since_coverage_start"] is True   # the only row = earliest
        assert r["kind_en"] == "investor visit"    # default fallback (row carries no kind_*)
        assert r["kind_zh"] == "机构调研"

    def test_ok_row_propagates_kind_label_from_load_visits_context(self):
        # Simulates what _load_visits_context() actually attaches per row.
        rows = [{
            "announcement_id": "A2", "sec_code": "000002",
            "title": "关于接待特定对象调研的公告",
            "source_published_at": "2026-08-19T09:00:00+08:00",
            "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
            "ontology_version": "v1", "adjunct_url": "",
            "kind_en": "site visit", "kind_zh": "特定对象调研",
        }]
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000002.SZ", _ctx(
            by_code={"000002": rows}, coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": fresh}))
        assert block["recent"][0]["kind_en"] == "site visit"
        assert block["recent"][0]["kind_zh"] == "特定对象调研"

    def test_first_seen_flag_only_on_earliest_row(self):
        rows = [
            {"announcement_id": "A1", "sec_code": "000001", "title": "t1",
             "source_published_at": "2026-08-05T09:00:00+08:00",
             "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
             "ontology_version": "v1", "adjunct_url": ""},
            {"announcement_id": "A2", "sec_code": "000001", "title": "t2",
             "source_published_at": "2026-08-15T09:00:00+08:00",
             "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
             "ontology_version": "v1", "adjunct_url": ""},
        ]
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000001.SZ", _ctx(
            by_code={"000001": rows}, coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": fresh}))
        by_id = {r["title"]: r["first_seen_since_coverage_start"] for r in block["recent"]}
        assert by_id["t1"] is True
        assert by_id["t2"] is False

    def test_mid_coverage_first_sighting_still_says_since_not_ever(self):
        # A name whose ONLY observed row lands well after coverage_start —
        # must still be labeled "since coverage start", never "first ever".
        rows = [{"announcement_id": "A9", "sec_code": "000009", "title": "mid",
                  "source_published_at": "2026-08-18T09:00:00+08:00",
                  "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
                  "ontology_version": "v1", "adjunct_url": ""}]
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000009.SZ", _ctx(
            by_code={"000009": rows}, coverage_start="2026-08-01",  # coverage started earlier
            health={"status": "ok", "last_success_utc": fresh}))
        assert block["recent"][0]["first_seen_since_coverage_start"] is True
        # the wording itself never claims "first ever" anywhere in the block
        assert "first ever" not in str(block).lower()

    def test_never_raises_on_malformed_ctx(self):
        # A visit_ctx missing keys entirely must degrade, never crash.
        block = hub._visit_block("000001.SZ", {})
        assert block["state"] in {"no_coverage", "source_failure"}

    def test_upstream_degraded_with_no_rows_reads_stale_not_measured_no_event(self):
        # P1-R1: a degraded same-run china_filings refresh must never look like
        # a clean "measured_no_event" quiet tape, and must not route through
        # source_failure either (tape history stays visible).
        block = hub._visit_block("000001.SZ", _ctx(
            coverage_start="2026-08-01",
            health={"status": "upstream_degraded",
                    "detail": "derived over a DEGRADED same-run china_filings refresh"}))
        assert block["state"] == "stale"
        assert block["state"] != "measured_no_event"
        assert block["state"] != "source_failure"
        assert block["recent"] == []

    def test_upstream_degraded_with_rows_still_renders_normally(self):
        # Positive evidence from a degraded run is still real evidence — rows
        # must render exactly as they would under a clean "ok" health.
        rows = [{
            "announcement_id": "A1", "sec_code": "000001",
            "title": "投资者关系活动记录表",
            "source_published_at": "2026-08-19T09:00:00+08:00",
            "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
            "ontology_version": "v1", "adjunct_url": "",
        }]
        block = hub._visit_block("000001.SZ", _ctx(
            by_code={"000001": rows}, coverage_start="2026-08-01",
            health={"status": "upstream_degraded", "detail": "x"}))
        assert block["state"] == "ok"
        assert len(block["recent"]) == 1


# --------------------------------------------------------------------------- #
# _load_visits_context — degrades against a real (empty) store
# --------------------------------------------------------------------------- #

class TestLoadVisitsContext:
    def test_empty_store_is_no_coverage(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
        ctx = hub._load_visits_context()
        assert ctx["by_code"] == {}
        assert ctx["coverage_start"] is None
        assert ctx["health"]["status"] == "no_coverage"

    def test_after_a_real_refresh_ctx_reflects_it(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
        import collectors.china_filings as cf
        import collectors.china_visits as cv

        cf.write_filings([{
            "announcementId": "A1", "sec_code": "000001", "sec_name": "n",
            "org_id": "o", "title": "投资者关系活动记录表",
            "publish_ts": "2026-08-19T09:00:00+08:00", "exchange": "szse",
            "category": "institutional_visit", "kind": None,
            "announcement_type_raw": "", "adjunct_url": "/x.pdf",
            "adjunct_type": "PDF", "_collected_at": "2026-08-19T09:00:00+08:00",
        }])
        s = cv.refresh()
        assert s["status"] == "ok"

        ctx = hub._load_visits_context()
        assert ctx["coverage_start"] is not None
        assert ctx["health"]["status"] == "ok"
        assert "000001" in ctx["by_code"]
        # kind label is attached at load time, not left for the template to guess
        assert ctx["by_code"]["000001"][0]["kind_en"] == "IR activity record"
        assert ctx["by_code"]["000001"][0]["kind_zh"] == "投资者关系活动记录表"


# --------------------------------------------------------------------------- #
# build() integration — visits block present, score neutrality
# --------------------------------------------------------------------------- #

def _altdata_row(ticker, convergence=0.85, conviction100=90):
    return {"ticker": ticker, "name": ticker, "convergence": convergence,
            "conviction100": conviction100, "reasons": [], "flags": [], "side": "accumulate"}


class TestBuildIntegration:
    def test_visits_block_present_on_every_command_row(self, monkeypatch):
        altdata = {
            "schema": "china_altdata.v1", "is_context_only": True,
            "asof": "2026-08-20", "n_universe": 1, "n_triple": 0,
            "triple": [], "top": [_altdata_row("600519.SS")],
            "bottom": [], "crowding_flags": [],
        }

        def _mock_read(rel):
            if "chinaaltdata" in rel:
                return altdata
            return None

        monkeypatch.setattr(hub, "_read_json", _mock_read)
        monkeypatch.setattr(hub, "_load_closes_and_benchmark", lambda: (None, None))
        monkeypatch.setattr(hub, "_append_snapshot_ledger", lambda *a, **kw: None)
        monkeypatch.setattr(hub, "_load_visits_context",
                             lambda: {"by_code": {}, "coverage_start": None,
                                       "health": {"status": "no_coverage"}})

        result = hub.build(today=date(2026, 8, 20))
        assert len(result["command"]) >= 1
        for d in result["command"]:
            assert "visits" in d
            assert d["visits"]["state"] in {
                "not_applicable", "no_coverage", "source_failure", "stale",
                "measured_no_event", "ok",
            }

    def test_visit_data_never_moves_opportunity_or_stage(self, monkeypatch):
        """Score neutrality: identical desk inputs must produce byte-identical
        opportunity_score/edge_remaining/stage whether the visit tape is
        empty or carries rows — visits are descriptive, never a signal."""
        altdata = {
            "schema": "china_altdata.v1", "is_context_only": True,
            "asof": "2026-08-20", "n_universe": 1, "n_triple": 0,
            "triple": [], "top": [_altdata_row("600519.SS")],
            "bottom": [], "crowding_flags": [],
        }

        def _mock_read(rel):
            if "chinaaltdata" in rel:
                return altdata
            return None

        monkeypatch.setattr(hub, "_read_json", _mock_read)
        monkeypatch.setattr(hub, "_load_closes_and_benchmark", lambda: (None, None))
        monkeypatch.setattr(hub, "_append_snapshot_ledger", lambda *a, **kw: None)

        monkeypatch.setattr(hub, "_load_visits_context",
                             lambda: {"by_code": {}, "coverage_start": None,
                                       "health": {"status": "no_coverage"}})
        no_visits = hub.build(today=date(2026, 8, 20))

        fresh = datetime.now(timezone.utc).isoformat()
        monkeypatch.setattr(hub, "_load_visits_context", lambda: {
            "by_code": {"600519": [{
                "announcement_id": "A1", "sec_code": "600519", "title": "t",
                "source_published_at": "2026-08-19T09:00:00+08:00",
                "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
                "ontology_version": "v1", "adjunct_url": "",
            }]},
            "coverage_start": "2026-08-01",
            "health": {"status": "ok", "last_success_utc": fresh},
        })
        with_visits = hub.build(today=date(2026, 8, 20))

        d0 = no_visits["command"][0]
        d1 = with_visits["command"][0]
        assert d0["opportunity_score"] == d1["opportunity_score"]
        assert d0["edge_remaining"] == d1["edge_remaining"]
        assert d0["stage"] == d1["stage"]
        assert d0["lean"] == d1["lean"]
        # the visits block itself DID change, proving the fixture took effect
        assert d0["visits"]["state"] != d1["visits"]["state"]


# --------------------------------------------------------------------------- #
# CIE-04/05/06 — bounded owner-native company evidence
# --------------------------------------------------------------------------- #

class TestCIECompanyEvidence:
    def test_cninfo_source_url_accepts_only_owner_path_family(self):
        assert hub._cninfo_source_url(
            "finalpage/2026-08-19/1234567890.PDF"
        ) == "https://static.cninfo.com.cn/finalpage/2026-08-19/1234567890.PDF"
        assert hub._cninfo_source_url(
            "/finalpage/2026-08-19/1234567890.PDF"
        ) == "https://static.cninfo.com.cn/finalpage/2026-08-19/1234567890.PDF"

        # A stored source field is evidence, not authority to make an arbitrary
        # outbound link. Absolute URLs, traversal and unrelated paths fail closed.
        assert hub._cninfo_source_url("https://evil.example/x.pdf") is None
        assert hub._cninfo_source_url("../../etc/passwd") is None
        assert hub._cninfo_source_url("other/123.pdf") is None
        assert hub._cninfo_source_url('finalpage/x" onmouseover="alert(1).PDF') is None
        assert hub._cninfo_source_url("finalpage/<script>.PDF") is None

    def test_visit_row_exposes_source_id_link_and_separate_clocks(self):
        fresh = datetime.now(timezone.utc).isoformat()
        block = hub._visit_block("000001.SZ", _ctx(
            by_code={"000001": [{
                "announcement_id": "A-CIE-1", "sec_code": "000001",
                "title": "投资者关系活动记录表",
                "source_published_at": "2026-08-19T09:00:00+08:00",
                "system_recorded_at": "2026-08-19T10:00:00+00:00",
                "visitor_raw": "not_yet_available",
                "visitor_class": "not_yet_available",
                "ontology_version": "v1",
                "adjunct_url": "finalpage/2026-08-19/A-CIE-1.PDF",
            }]},
            coverage_start="2026-08-01",
            health={"status": "ok", "last_success_utc": fresh},
        ))
        row = block["recent"][0]
        assert row["announcement_id"] == "A-CIE-1"
        assert row["source_published_at"] == "2026-08-19T09:00:00+08:00"
        assert row["system_recorded_at"] == "2026-08-19T10:00:00+00:00"
        assert row["source_url"].startswith("https://static.cninfo.com.cn/finalpage/")
        assert row["source_published_at"] != row["system_recorded_at"]

    def test_packet_is_context_only_source_addressable_and_rank_neutral(self):
        visits = {
            "state": "ok",
            "coverage_start": "2026-08-01",
            "recent": [{
                "announcement_id": "A-CIE-2",
                "title": "投资者关系活动记录表",
                "source_published_at": "2026-08-20T09:00:00+08:00",
                "system_recorded_at": "2026-08-20T10:00:00+00:00",
                "source_url": "https://static.cninfo.com.cn/finalpage/2026-08-20/A-CIE-2.PDF",
                "visitor_class": "not_yet_available",
            }],
        }
        traj = {
            "ret_20d": -4.0, "rs_20d": -2.0, "rs_60d": 1.0,
            "off_high_pct": -8.0, "rolling_over": True,
        }
        packet = hub._company_evidence_block(
            visits, traj,
            "price is rolling over (20d drawdown + RS falling)",
            "价格正在转弱（20 日回撤 + 相对强度走低）",
        )

        assert packet["schema"] == "china_intel.company_evidence.v1"
        assert packet["is_context_only"] is True
        assert packet["authority"] == {
            "identity": "existing_hub_ticker",
            "ranking": "none",
            "prophet": "none",
            "trade": "none",
        }
        assert packet["evidence"][0]["source_id"] == "A-CIE-2"
        assert packet["clocks"]["latest_source_published_at"] == \
            "2026-08-20T09:00:00+08:00"
        assert packet["clocks"]["latest_system_recorded_at"] == \
            "2026-08-20T10:00:00+00:00"
        assert "visitor_identity_not_available" in packet["unknowns"]
        assert packet["market_context"]["rolling_over"] is True
        assert packet["contradictions"][0]["basis"] == "existing_hub_risk_context"
        # No accidental second rank/score authority hidden inside the packet.
        assert "score" not in packet
        assert "rank" not in packet

    def test_covered_quiet_is_measured_not_relabelled_unknown(self):
        packet = hub._company_evidence_block(
            {"state": "measured_no_event", "coverage_start": "2026-08-01", "recent": []},
            {"ret_20d": 1.0, "rs_20d": 0.2, "rs_60d": 0.1,
             "off_high_pct": -2.0, "rolling_over": False},
            None, None,
        )
        assert packet["source_state"] == "measured_no_event"
        assert "visit_coverage_not_started" not in packet["unknowns"]
        assert "visit_source_stale" not in packet["unknowns"]
        assert "visit_source_unavailable" not in packet["unknowns"]
        assert packet["evidence"] == []

    def test_degraded_absence_stays_unknown(self):
        for state, expected in [
            ("no_coverage", "visit_coverage_not_started"),
            ("stale", "visit_source_stale"),
            ("source_failure", "visit_source_unavailable"),
            ("not_yet_available", "visit_observation_incomplete"),
        ]:
            packet = hub._company_evidence_block(
                {"state": state, "coverage_start": None, "recent": []},
                None, None, None,
            )
            assert expected in packet["unknowns"]
            assert "market_context_unavailable" in packet["unknowns"]





# --------------------------------------------------------------------------- #
# CIE-14 — recognition / dependence / contradiction composition
# --------------------------------------------------------------------------- #

class TestCIE14RecognitionComposition:
    def test_exact_duplicate_source_event_collapses_without_conviction_multiplication(self):
        rows = [
            {
                "kind": "institutional_visit_filing",
                "source": "CNInfo",
                "source_id": "A14-1",
                "title": "机构调研活动记录表",
                "source_published_at": "2026-10-01T09:00:00+08:00",
                "source_url": "https://static.cninfo.com.cn/finalpage/a.pdf",
            },
            {
                "kind": "institutional_visit_filing",
                "source": "CNInfo",
                "source_id": "A14-1",
                "title": "机构调研活动记录表",
                "source_published_at": "2026-10-01T09:00:00+08:00",
                "source_url": "https://static.cninfo.com.cn/finalpage/a-restored.pdf",
            },
        ]
        rec = hub._evidence_recognition_block(rows)
        assert rec["state"] == "single_source_event"
        assert len(rec["source_event_groups"]) == 1
        group = rec["source_event_groups"][0]
        assert group["member_count"] == 2
        assert group["state"] == "exact_source_identity"
        assert group["source_address_state"] == "multiple_addresses_observed"
        assert rec["independent_event_count"] is None
        assert rec["conviction_multiplier"] is None
        assert rec["authority"]["may_multiply_conviction"] is False

    def test_cross_source_economic_event_links_only_with_explicit_owner_id(self):
        rows = [
            {
                "kind": "procurement_notice",
                "source": "CSG",
                "source_id": "P-1",
                "economic_event_id": "event:power-grid-001",
            },
            {
                "kind": "issuer_contract_filing",
                "source": "CNInfo",
                "source_id": "F-1",
                "economic_event_id": "event:power-grid-001",
            },
        ]
        rec = hub._evidence_recognition_block(rows)
        assert rec["state"] == "cross_source_economic_event_linked"
        assert len(rec["economic_event_groups"]) == 1
        assert rec["economic_event_groups"][0]["source_count"] == 2
        assert rec["economic_event_groups"][0]["basis"] == "explicit_owner_id"
        assert rec["conviction_multiplier"] is None

    def test_translated_or_repeated_copy_does_not_self_assert_dependence(self):
        rows = [
            {
                "kind": "policy_story",
                "source": "Official",
                "source_id": "CN-1",
                "title": "支持先进制造",
            },
            {
                "kind": "policy_story",
                "source": "NewsWire",
                "source_id": "EN-1",
                "title": "Support advanced manufacturing",
            },
        ]
        rec = hub._evidence_recognition_block(rows)
        assert rec["state"] == "multiple_observations_dependency_unresolved"
        assert rec["syndication_groups"] == []
        assert rec["economic_event_groups"] == []
        assert "syndication_linkage_unresolved" in rec["unresolved_dependencies"]
        assert "economic_event_linkage_unresolved" in rec["unresolved_dependencies"]

    def test_explicit_syndication_groups_cross_source_copy_without_event_claim(self):
        rows = [
            {
                "kind": "story",
                "source": "WireA",
                "source_id": "1",
                "syndication_id": "synd:abc",
            },
            {
                "kind": "story",
                "source": "WireB",
                "source_id": "2",
                "syndication_id": "synd:abc",
            },
        ]
        rec = hub._evidence_recognition_block(rows)
        assert rec["state"] == "cross_source_syndication_linked"
        assert rec["syndication_groups"][0]["source_count"] == 2
        assert rec["economic_event_groups"] == []

    def test_conflicting_same_source_identity_is_preserved_as_contradiction(self):
        visits = {
            "state": "ok",
            "coverage_start": "2026-09-01",
            "recent": [
                {
                    "announcement_id": "A14-CONFLICT",
                    "title": "版本一",
                    "source_published_at": "2026-10-01T09:00:00+08:00",
                    "system_recorded_at": "2026-10-01T02:00:00+00:00",
                    "source_url": "https://static.cninfo.com.cn/finalpage/a.pdf",
                    "visitor_class": "not_yet_available",
                },
                {
                    "announcement_id": "A14-CONFLICT",
                    "title": "版本二",
                    "source_published_at": "2026-10-01T09:00:00+08:00",
                    "system_recorded_at": "2026-10-01T03:00:00+00:00",
                    "source_url": "https://static.cninfo.com.cn/finalpage/a.pdf",
                    "visitor_class": "not_yet_available",
                },
            ],
        }
        packet = hub._company_evidence_block(visits, None, None, None)
        assert packet["recognition"]["state"] == "source_event_conflict"
        assert packet["recognition"]["source_event_conflicts"] == [
            "CNInfo:A14-CONFLICT"
        ]
        assert any(
            x["basis"] == "source_event_identity_conflict"
            for x in packet["contradictions"]
        )

    def test_participation_context_never_becomes_actor_identity(self):
        raw = {
            "date": "2026-10-03",
            "regime": "broad_mania",
            "who_controls": "institutional",
            "risk": "frothy",
            "source_contract": {
                "schema": "china_participation.source_contract.v1",
                "legs": {"turnover": {}, "broker_rs": {}},
                "actor_semantics": (
                    "who_controls is a heuristic participation regime label, "
                    "not beneficial-owner identity"
                ),
                "clock_semantics": {
                    "collection_clock": "not exposed by this owner"
                },
            },
        }
        ctx = hub._participation_context_block(raw)
        assert ctx["status"] == "available"
        assert ctx["who_controls"] == "institutional"
        assert ctx["economic_actor_id"] is None
        assert ctx["actor_identity_state"] ==             "not_inferred_from_participation_regime"
        assert ctx["authority"]["actor_identity"] == "none"
        assert ctx["source_contract_schema"] ==             "china_participation.source_contract.v1"

        missing = hub._participation_context_block(None)
        assert missing["status"] == "unavailable"
        assert missing["economic_actor_id"] is None

    def test_participation_recognition_context_never_moves_rank_fields(self, monkeypatch):
        monkeypatch.setattr(hub, "_ths_concepts", lambda _ticker: [])
        visit_ctx = {
            "by_code": {},
            "coverage_start": None,
            "health": {"status": "no_coverage"},
        }
        altdata = _altdata_row("600519.SS")
        base = hub._dossier(
            "600519.SS", altdata, None, None, None, None, None, False,
            gov={}, visit_ctx=visit_ctx, participation_ctx=None,
        )
        enriched = hub._dossier(
            "600519.SS", altdata, None, None, None, None, None, False,
            gov={}, visit_ctx=visit_ctx,
            participation_ctx={
                "date": "2026-10-03",
                "regime": "broad_mania",
                "who_controls": "institutional",
                "risk": "frothy",
                "source_contract": {
                    "schema": "china_participation.source_contract.v1",
                    "legs": {"turnover": {}},
                },
            },
        )
        for field in (
            "opportunity_score", "edge_remaining", "stage", "lean",
            "signal_core", "falsifier_penalty",
        ):
            assert base[field] == enriched[field]
        assert base["company_evidence"]["participation_context"]["status"] ==             "unavailable"
        assert enriched["company_evidence"]["participation_context"]["status"] ==             "available"

    def test_packet_delta_does_not_invent_cross_run_history(self):
        packet = hub._company_evidence_block(
            {"state": "measured_no_event", "coverage_start": "2026-09-01", "recent": []},
            None, None, None,
        )
        assert packet["packet_delta"] == {
            "state": "unavailable_without_prior_packet_receipt",
            "basis": "current_packet_only",
        }

# --------------------------------------------------------------------------- #
# P1-R3 (durable scoped key-exclusion recovery) — hub-level hostile items
# --------------------------------------------------------------------------- #

def _ctx_with_exceptions(by_code=None, coverage_start="2026-08-01", health=None,
                          exception_codes=None, unscoped_exceptions=0,
                          exceptions_readable=True):
    """A SEPARATE helper from _ctx() above — _ctx() itself is NEVER edited,
    so every pre-existing test built on it keeps degrading to "no scoping"
    when the P1-R3 keys are absent entirely, exactly as before P1-R3."""
    return {
        "by_code": by_code or {}, "coverage_start": coverage_start,
        "health": health or {"status": "ok",
                              "last_success_utc": datetime.now(timezone.utc).isoformat()},
        "exception_codes": exception_codes if exception_codes is not None else set(),
        "unscoped_exceptions": unscoped_exceptions,
        "exceptions_readable": exceptions_readable,
    }


class TestVisitBlockScopedExceptionHubLevel:
    """Frozen spec §12 hostile items 1, 2, 4, 9, 10 — proven directly
    against _visit_block() with a hand-built visit_ctx (no collector I/O)."""

    def test_item1_company_scoped_exception_blocks_only_that_company(self):
        ctx = _ctx_with_exceptions(exception_codes={"000001"})
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "not_yet_available"
        assert block["state"] != "measured_no_event"
        assert block["coverage_exception"] == {"scope": "company", "open": 1}

    def test_precedence_scoped_exception_wins_over_upstream_degraded(self):
        """FIX (correction, 2026-08-22): a ctx that is BOTH
        status=='upstream_degraded' AND carries a scoped OPEN exception must
        return 'not_yet_available' (scope 'company'), never the generic
        'stale' — the more specific sentence wins. Pins the no-rows branch
        precedence: stale -> scoped/unscoped -> upstream_degraded ->
        measured_no_event."""
        ctx = _ctx_with_exceptions(
            exception_codes={"000001"},
            health={"status": "upstream_degraded",
                    "detail": "derived over a DEGRADED same-run china_filings refresh",
                    "last_success_utc": datetime.now(timezone.utc).isoformat()},
        )
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "not_yet_available"
        assert block["state"] != "stale"
        assert block["coverage_exception"] == {"scope": "company", "open": 1}

    def test_precedence_transport_degraded_alone_still_reads_stale(self):
        """The swap must NOT change the pre-existing P1-R1 path: a
        transport-degraded run with NO open exception still reads 'stale',
        exactly as before."""
        ctx = _ctx_with_exceptions(
            exception_codes=set(), unscoped_exceptions=0,
            health={"status": "upstream_degraded",
                    "detail": "derived over a DEGRADED same-run china_filings refresh",
                    "last_success_utc": datetime.now(timezone.utc).isoformat()},
        )
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "stale"
        assert block["state"] != "not_yet_available"

    def test_item2_uninvolved_company_in_the_same_ctx_still_measured_no_event(self):
        """Proves scoping is REAL, not a global block wearing a per-company
        label: the SAME ctx that blocks 000001 must NOT block 000002."""
        ctx = _ctx_with_exceptions(exception_codes={"000001"})
        block_a = hub._visit_block("000001.SZ", ctx)
        block_b = hub._visit_block("000002.SZ", ctx)
        assert block_a["state"] == "not_yet_available"
        assert block_b["state"] == "measured_no_event"
        assert "coverage_exception" not in block_b

    def test_item4_unscoped_exception_blocks_every_name(self):
        ctx = _ctx_with_exceptions(exception_codes=set(), unscoped_exceptions=1)
        for ticker in ("000001.SZ", "600519.SS", "000099.SZ"):
            block = hub._visit_block(ticker, ctx)
            assert block["state"] == "not_yet_available"
            assert block["state"] != "measured_no_event"
            assert block["coverage_exception"] == {"scope": "plane", "open": 1}

    def test_item9_positive_rows_plus_open_exception_same_company(self):
        """Rows render normally AND coverage_exception is present —
        completeness is never asserted alongside positive evidence."""
        rows = [{
            "announcement_id": "A1", "sec_code": "000001",
            "title": "投资者关系活动记录表",
            "source_published_at": "2026-08-19T09:00:00+08:00",
            "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
            "ontology_version": "v1", "adjunct_url": "",
            "kind_en": "IR activity record", "kind_zh": "投资者关系活动记录表",
        }]
        ctx = _ctx_with_exceptions(by_code={"000001": rows}, exception_codes={"000001"})
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "ok"
        assert len(block["recent"]) == 1
        assert block["coverage_exception"] == {"scope": "company", "open": 1}

    def test_item10_unreadable_ledger_blocks_every_name_globally(self):
        """exceptions_readable=False fails closed exactly like an unscoped
        exception — an otherwise clean name still cannot confirm absence,
        while positive rows still render for a name that has them."""
        ctx = _ctx_with_exceptions(exception_codes=set(), unscoped_exceptions=0,
                                    exceptions_readable=False)
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "not_yet_available"
        assert block["state"] != "measured_no_event"
        assert block["coverage_exception"]["scope"] == "plane"

        rows = [{
            "announcement_id": "A1", "sec_code": "600519",
            "title": "投资者关系活动记录表",
            "source_published_at": "2026-08-19T09:00:00+08:00",
            "visitor_raw": "not_yet_available", "visitor_class": "not_yet_available",
            "ontology_version": "v1", "adjunct_url": "",
        }]
        ctx_rows = _ctx_with_exceptions(by_code={"600519": rows}, exceptions_readable=False)
        block_rows = hub._visit_block("600519.SS", ctx_rows)
        assert block_rows["state"] == "ok"   # positive evidence still renders
        assert block_rows["coverage_exception"]["scope"] == "plane"


class TestBackwardCompatibilityOfExistingCtxHelper:
    """Checkpoint requirement (a): _ctx() (the pre-existing helper, left
    UNEDITED) must keep degrading absent P1-R3 keys to "no scoping" — never
    a false global block."""

    def test_ctx_without_p1r3_keys_never_blocks_measured_no_event(self):
        fresh = datetime.now(timezone.utc).isoformat()
        ctx = _ctx(coverage_start="2026-08-01",
                    health={"status": "ok", "last_success_utc": fresh})
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "measured_no_event"
        assert "coverage_exception" not in block


class TestNaNSecCodeScopingHubLevel:
    """Checkpoint requirement (b): a ledger row whose sec_code is NaN-like
    must increment unscoped_exceptions and must NEVER appear in
    exception_codes — proven here at the _load_visits_context() level
    against a REAL coverage_exceptions.parquet (not just the pure
    is_unscoped_sec_code() unit in tests/test_china_visits_collector.py).
    A real refresh()-produced ledger can no longer contain a raw NaN sec_code
    (write_visits' upstream _exception_fields() already normalizes with
    _fp_norm()) — this simulates a historical/legacy or hand-corrupted
    ledger row, exactly the defense-in-depth is_unscoped_sec_code() exists
    to cover."""

    def _write_ledger(self, tmp_path, monkeypatch, sec_code):
        import collectors.china_visits as cv
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
        row = {col: "" for col in cv._EXCEPTION_COLUMNS}
        row.update({
            "observation_fingerprint": "obsfp1:" + "a" * 64,
            "fingerprint_version": "obsfp1", "sec_code": sec_code,
            "status": "open", "observed_count": 1,
            "first_seen_utc": "t0", "last_seen_utc": "t0",
        })
        df = pd.DataFrame([row]).reindex(columns=list(cv._EXCEPTION_COLUMNS))
        cv._atomic_write(df, cv._exceptions_path())

    def test_nan_sec_code_is_unscoped_never_a_literal_company(self, tmp_path, monkeypatch):
        self._write_ledger(tmp_path, monkeypatch, float("nan"))
        ctx = hub._load_visits_context()
        assert ctx["unscoped_exceptions"] == 1
        assert ctx["exception_codes"] == set()
        assert "nan" not in ctx["exception_codes"]

    def test_nat_sec_code_is_unscoped(self, tmp_path, monkeypatch):
        self._write_ledger(tmp_path, monkeypatch, pd.NaT)
        ctx = hub._load_visits_context()
        assert ctx["unscoped_exceptions"] == 1
        assert ctx["exception_codes"] == set()

    def test_pd_na_sec_code_is_unscoped_never_raises(self, tmp_path, monkeypatch):
        self._write_ledger(tmp_path, monkeypatch, pd.NA)
        ctx = hub._load_visits_context()   # must not raise
        assert ctx["unscoped_exceptions"] == 1
        assert ctx["exception_codes"] == set()


class TestUnreadableVisitsStoreFailsClosedHubLevel:
    """FIX (correction, 2026-08-22): an unreadable visits.parquet must NOT
    render as measured_no_event for every company. load_visits() swallows a
    read error and answers empty (by design, for its OTHER callers) — the
    hub must use the strict reader and take the EXISTING source_failure
    branch for every name instead."""

    def test_unreadable_visits_parquet_reads_source_failure_never_measured_no_event(
        self, tmp_path, monkeypatch
    ):
        import collectors.china_filings as cf
        import collectors.china_visits as cv

        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

        # A genuine prior successful run — coverage_start stamped,
        # health.json says "ok" — so the ONLY thing distinguishing this
        # from a normal healthy read is the tape itself being unreadable
        # RIGHT NOW (health.json and visits.parquet are two different files).
        cf.write_filings([{
            "announcementId": "A1", "sec_code": "000001", "sec_name": "n",
            "org_id": "o", "title": "投资者关系活动记录表",
            "publish_ts": "2026-08-19T09:00:00+08:00", "exchange": "szse",
            "category": "institutional_visit", "kind": None,
            "announcement_type_raw": "", "adjunct_url": "/x.pdf",
            "adjunct_type": "PDF", "_collected_at": "2026-08-19T09:00:00+08:00",
        }])
        s = cv.refresh()
        assert s["status"] == "ok"
        assert cv.read_health()["status"] == "ok"

        # Corrupt the tape AFTER the successful run.
        cv._visits_path().write_bytes(b"not a parquet file")

        ctx = hub._load_visits_context()
        assert ctx["health"]["status"] == "source_failure"
        # A ticker that would otherwise be genuinely clean (no rows, real
        # coverage_start, health.json says "ok") must read source_failure,
        # NEVER a false clean measured_no_event.
        block = hub._visit_block("000001.SZ", ctx)
        assert block["state"] == "source_failure"
        assert block["state"] != "measured_no_event"
        assert block["recent"] == []
