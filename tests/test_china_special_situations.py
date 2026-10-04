"""Engine tests for china_special_situations.py — pure, network-free.

Tests:
  - all inputs missing → every block None / degraded, scan() still returns valid dict
  - empty categories → graceful (no crash, empty lists)
  - happy path from small fixture parquets
  - unlock float_pct scale: ratio column is a fraction (1.0=100%), engine stores percent
  - register_claims lane guard (only fires with CN_LANE=asia)
  - register_claims fires when CN_LANE=asia with correct dict shape (no 'kind' key)
  - sidecar dedup: second run same day and next day for same event does NOT re-register
  - data_asof present in scan() output
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


# ── scan() always returns a valid dict ───────────────────────────────────────

def test_scan_all_missing_still_returns_valid_dict(tmp_path, monkeypatch):
    """When no data exists, scan() returns a valid schema-versioned dict with None blocks."""
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    from engine import china_special_situations as css
    snap = css.scan()

    assert snap["schema"] == "china_special_sits.v1"
    assert snap["is_context_only"] is True
    assert "asof" in snap
    assert "data_asof" in snap
    assert "by_ticker" in snap
    assert isinstance(snap["by_ticker"], dict)
    # blocks may be None or empty-state dicts — none should be missing entirely
    for key in ("unlocks", "inquiry", "contracts", "preannounce", "buyback", "pledge", "st", "block_trades"):
        assert key in snap


def test_scan_empty_categories(tmp_path, monkeypatch):
    """Empty parquets → graceful empty states, no crash."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    # Write empty parquets with asof column
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    for sub, file in (
        ("china_buyback",      "buyback.parquet"),
        ("china_pledge",       "pledge.parquet"),
        ("china_block_trades", "detail.parquet"),
    ):
        p = data_dir / sub / file
        p.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"asof": [today]}).to_parquet(p, index=False)

    from engine import china_special_situations as css
    snap = css.scan()
    assert snap["schema"] == "china_special_sits.v1"


def test_scan_happy_path_buyback(tmp_path, monkeypatch):
    """Small buyback fixture → top list populated."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    p = data_dir / "china_buyback" / "buyback.parquet"
    _make_parquet(p, [
        {"ticker": "600519.SS", "name": "贵州茅台", "plan_amt_yi": 20.0,
         "done_amt_yi": 5.0, "pct_shares": 0.5, "progress": "实施中", "asof": today},
        {"ticker": "000001.SZ", "name": "平安银行", "plan_amt_yi": 10.0,
         "done_amt_yi": 2.0, "pct_shares": 0.3, "progress": "实施中", "asof": today},
    ])

    from engine import china_special_situations as css
    snap = css.scan()
    bb = snap.get("buyback") or {}
    assert bb.get("n_active") == 2
    assert len(bb.get("top") or []) == 2
    assert bb["top"][0]["ticker"] == "600519.SS"


def test_scan_happy_path_pledge(tmp_path, monkeypatch):
    """Small pledge fixture → high-pledge count correct."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    p = data_dir / "china_pledge" / "pledge.parquet"
    _make_parquet(p, [
        {"ticker": "600000.SS", "name": "浦发银行", "pledge_ratio": 72.0,
         "pledge_mktcap_yi": 8.5, "sector": "Banks", "quarter": "20231231", "asof": today},
        {"ticker": "000002.SZ", "name": "万科A", "pledge_ratio": 35.0,
         "pledge_mktcap_yi": 3.2, "sector": "Real Estate", "quarter": "20231231", "asof": today},
    ])

    from engine import china_special_situations as css
    snap = css.scan()
    pl = snap.get("pledge") or {}
    assert pl.get("n_high") == 1  # only pledge_ratio >= 50
    assert pl["top"][0]["ticker"] == "600000.SS"


def test_scan_happy_path_inquiry(tmp_path, monkeypatch):
    """Small inquiry fixture → letters block populated.

    Titles must genuinely NAME the same inquiry thread (either 《》-quoted or a
    well-formed inline span ending at 问询函/关注函/监管函/质询函) for the reply to
    resolve — reply identity is scoped to (issuer, inquiry thread), not issuer
    alone. A title like "关于问询函的回复" names no inquiry and would resolve as
    'undetermined', not 'replied' (see tests/test_china_special_situations_truth_
    wave1.py for the full reply-identity regression suite).
    """
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    p = data_dir / "china_inquiry" / "inquiry.parquet"
    _make_parquet(p, [
        {"secCode": "000001", "secName": "平安银行",
         "announcementTitle": "关于收到深圳证券交易所《关于平安银行2025年年报的问询函》的公告",
         "announcementTime": today,
         "adjunctUrl": "/x/PDF.pdf", "announcementTypeName": "问询函",
         "kind": "letter", "asof": today},
        {"secCode": "000001", "secName": "平安银行",
         "announcementTitle": "平安银行关于深圳证券交易所《关于平安银行2025年年报的问询函》的回复公告",
         "announcementTime": today,
         "adjunctUrl": "/x/reply.pdf", "announcementTypeName": "回复",
         "kind": "reply", "asof": today},
    ])

    from engine import china_special_situations as css
    snap = css.scan()
    inq = snap.get("inquiry") or {}
    assert inq.get("n_letters") == 1
    assert inq.get("n_replies") == 1
    # letter should have has_reply=True because the reply names the SAME inquiry
    assert inq["letters"][0]["has_reply"] is True
    # letter dict must NOT have a 'kind' key (register_claims must not filter on it)
    assert "kind" not in inq["letters"][0]



# ── CIE-10 contract/order metadata truth ─────────────────────────────────────

def test_contract_title_state_precedence_is_title_only():
    from engine import china_special_situations as css

    assert css._contract_title_state(
        "关于重大合同终止暨中标项目取消的公告"
    )["state"] == "cancelled_or_terminated"
    assert css._contract_title_state(
        "关于重大合同履行进展暨签订补充协议的公告"
    )["state"] == "amendment_or_progress"
    assert css._contract_title_state(
        "项目中标候选人公示"
    )["state"] == "award_or_candidate_notice"
    assert css._contract_title_state(
        "关于签订重大合同的公告"
    )["state"] == "contract_announcement"
    assert css._contract_title_state(pd.NA)["state"] == "contract_metadata_unclassified"


def test_contract_order_block_preserves_source_clocks_and_unknown_economics(
    tmp_path, monkeypatch
):
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr(
        "lib.config.load",
        lambda: {"storage": {"site_dir": str(tmp_path / "site")}},
    )

    now = pd.Timestamp.now(tz="UTC")
    day = now.strftime("%Y-%m-%d")
    collected = now.isoformat()
    p = data_dir / "china_filings" / "filings.parquet"
    _make_parquet(p, [
        {
            "announcementId": "C1", "sec_code": "600001", "sec_name": "测试公司A",
            "title": "关于签订重大合同的公告",
            "publish_ts": f"{day}T09:00:00+08:00",
            "exchange": "sse", "category": "major_contract", "kind": None,
            "announcement_type_raw": "contract",
            "adjunct_url": "finalpage/2026-10-03/C1.PDF",
            "_collected_at": collected,
        },
        {
            "announcementId": "C2", "sec_code": "000002", "sec_name": "测试公司B",
            "title": "关于中标项目终止的公告",
            "publish_ts": f"{day}T10:00:00+08:00",
            "exchange": "szse", "category": "major_contract", "kind": None,
            "announcement_type_raw": "award",
            "adjunct_url": "finalpage/2026-10-03/C2.PDF",
            "_collected_at": collected,
        },
        {
            "announcementId": "I1", "sec_code": "000003", "sec_name": "测试公司C",
            "title": "交易所问询函",
            "publish_ts": f"{day}T11:00:00+08:00",
            "exchange": "szse", "category": "inquiry_letter", "kind": "letter",
            "announcement_type_raw": "inquiry",
            "adjunct_url": "finalpage/2026-10-03/I1.PDF",
            "_collected_at": collected,
        },
    ])

    from engine import china_special_situations as css
    block = css._contract_order_block(window_days=90)

    assert block["status"] == "ok"
    assert block["n_total"] == 2
    assert block["n_shown"] == 2
    assert block["by_state"]["contract_announcement"] == 1
    assert block["by_state"]["cancelled_or_terminated"] == 1

    by_id = {e["announcement_id"]: e for e in block["events"]}
    assert set(by_id) == {"C1", "C2"}
    assert by_id["C1"]["published_at"] == f"{day}T09:00:00+08:00"
    assert by_id["C1"]["first_collected_at"] == collected
    assert by_id["C1"]["source_url"] == "finalpage/2026-10-03/C1.PDF"
    assert by_id["C2"]["state"] == "cancelled_or_terminated"

    for event in by_id.values():
        assert event["project_key"] is None
        assert event["thread_identity_state"] == "unresolved_without_project_key"
        assert event["materiality_state"] == "unknown_without_denominator"
        assert event["economic_realization_state"] == \
            "not_inferred_from_filing_metadata"


def test_contract_context_never_becomes_special_rank_flag(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr(
        "lib.config.load",
        lambda: {"storage": {"site_dir": str(tmp_path / "site")}},
    )

    now = pd.Timestamp.now(tz="UTC")
    day = now.strftime("%Y-%m-%d")
    p = data_dir / "china_filings" / "filings.parquet"
    _make_parquet(p, [{
        "announcementId": "C3", "sec_code": "600519", "sec_name": "贵州茅台",
        "title": "关于重大合同履行进展的公告",
        "publish_ts": f"{day}T09:00:00+08:00",
        "exchange": "sse", "category": "major_contract", "kind": None,
        "announcement_type_raw": "contract",
        "adjunct_url": "finalpage/2026-10-03/C3.PDF",
        "_collected_at": now.isoformat(),
    }])

    from engine import china_special_situations as css
    snap = css.scan()
    assert snap["contracts"]["n_total"] == 1
    assert snap["contracts"]["events"][0]["state"] == "amendment_or_progress"
    # CIE-10 metadata is context only and is deliberately absent from the
    # command apparatus' by_ticker special flags.
    assert "600519" not in (snap.get("by_ticker") or {})


def test_contract_order_unreadable_store_fails_closed(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    p = data_dir / "china_filings" / "filings.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not-a-parquet")

    from engine import china_special_situations as css
    block = css._contract_order_block()
    assert block["status"] == "source_failure"
    assert block["events"] == []
    assert block["n_total"] == 0
    assert "unreadable" in block["coverage_note"]


def test_scan_st_history_note_when_one_date(tmp_path, monkeypatch):
    """ST snapshot with <2 dates in history → history_note present."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    snap_p = data_dir / "china_st" / "st_snapshot.parquet"
    _make_parquet(snap_p, [
        {"ticker": "600001.SS", "name": "*ST测试", "code": "600001",
         "price": 1.2, "pct_chg": -5.0, "asof": today},
    ])
    hist_p = data_dir / "china_st" / "st_history.parquet"
    _make_parquet(hist_p, [{"date": today, "ticker": "600001.SS", "name": "*ST测试"}])

    from engine import china_special_situations as css
    snap = css.scan()
    st = snap.get("st") or {}
    assert st.get("count") == 1
    assert st.get("history_note") is not None   # only one date → note present


def test_scan_by_ticker_rollup(tmp_path, monkeypatch):
    """by_ticker carries correct category flags."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    p = data_dir / "china_buyback" / "buyback.parquet"
    _make_parquet(p, [
        {"ticker": "600519.SS", "name": "贵州茅台", "plan_amt_yi": 20.0,
         "done_amt_yi": 5.0, "pct_shares": 0.5, "progress": "实施中", "asof": today},
    ])

    from engine import china_special_situations as css
    snap = css.scan()
    bt = snap.get("by_ticker") or {}
    assert "600519.SS" in bt
    assert bt["600519.SS"].get("buyback_active") is True


def test_scan_data_asof_present(tmp_path, monkeypatch):
    """scan() emits data_asof = worst per-input asof across present blocks."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    stale = "2026-01-01"
    # Two parquets: one fresh, one stale
    p1 = data_dir / "china_buyback" / "buyback.parquet"
    _make_parquet(p1, [{"ticker": "600519.SS", "name": "X", "plan_amt_yi": 1.0,
                        "progress": "实施中", "asof": today}])
    p2 = data_dir / "china_pledge" / "pledge.parquet"
    _make_parquet(p2, [{"ticker": "600000.SS", "pledge_ratio": 60.0, "asof": stale}])

    from engine import china_special_situations as css
    snap = css.scan()
    # data_asof = min across present blocks → stale wins
    assert snap["data_asof"] == stale


# ── unlock float_pct scale ────────────────────────────────────────────────────

def test_unlock_ratio_is_fraction_converted_to_pct(tmp_path, monkeypatch):
    """占解禁前流通市值比例 is a FRACTION (1.0=100%). Engine stores float_pct=ratio*100."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    tomorrow = (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    today = pd.Timestamp.today().strftime("%Y-%m-%d")

    p = data_dir / "china_unlocks" / "detail.parquet"
    _make_parquet(p, [
        # ratio=0.08 → float_pct=8.0 → large_flag=True
        {"ticker": "300001.SZ", "简称": "TestA", "解禁时间": tomorrow,
         "限售股类型": "首发原股东限售股", "占解禁前流通市值比例": 0.08,
         "实际解禁市值": 5e8, "asof": today},
        # ratio=0.02 → float_pct=2.0 → large_flag=False
        {"ticker": "300002.SZ", "简称": "TestB", "解禁时间": tomorrow,
         "限售股类型": "首发原股东限售股", "占解禁前流通市值比例": 0.02,
         "实际解禁市值": 1e8, "asof": today},
    ])

    from engine import china_special_situations as css
    snap = css.scan()
    u = snap.get("unlocks") or {}
    events = u.get("events") or []
    assert len(events) == 2
    # sorted by float_pct desc → TestA first
    assert events[0]["ticker"] == "300001.SZ"
    assert abs(events[0]["float_pct"] - 8.0) < 0.01
    assert events[0]["large_flag"] is True
    assert abs(events[1]["float_pct"] - 2.0) < 0.01
    assert events[1]["large_flag"] is False
    assert u["n_large"] == 1


def test_build_writes_json(tmp_path, monkeypatch):
    """build() writes special.json to the site dir."""
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(site_dir)}})
    # no qledger claims (CN_LANE not set)
    monkeypatch.setenv("CN_LANE", "")

    from engine import china_special_situations as css
    result = css.build()
    assert result is not None
    out = site_dir / "chinaspecialdata" / "special.json"
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == "china_special_sits.v1"
    assert loaded["is_context_only"] is True
    assert "data_asof" in loaded


def test_register_claims_blocked_outside_asia_lane(tmp_path, monkeypatch):
    """register_claims() returns 0 and does NOT touch qledger when CN_LANE != asia."""
    monkeypatch.setenv("CN_LANE", "")
    called = []

    def _fake_register_batch(claims, **kw):
        called.append(claims)
        return []

    import engine.china_special_situations as css
    monkeypatch.setattr("engine.qledger.register_batch", _fake_register_batch, raising=False)

    snap = {"asof": "2026-07-06",
            "inquiry": {"letters": [{"secCode": "000001", "secName": "测试", "date": "2026-07-05"}]},
            "unlocks": {"events": [{"ticker": "600000.SS", "large_flag": True,
                                    "unlock_date": "2026-07-15", "float_pct": 6.0}]}}
    n = css.register_claims(snap)
    assert n == 0
    assert not called  # qledger should not have been touched


def test_register_claims_fires_in_asia_lane(tmp_path, monkeypatch):
    """register_claims() calls register_batch when CN_LANE=asia.

    Uses the EXACT dict shape _inquiry_block emits: no 'kind' key on letter dicts.
    Asserts a POSITIVE claim count (both inquiry letter + large unlock should register).
    """
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    import engine.qledger as ql_mod
    registered: list = []

    def fake_make(**kw):
        return {"_claim": True, **kw}

    def fake_batch(claims, **kw):
        registered.extend(claims)
        return [{"status": "new"} for _ in claims]

    monkeypatch.setattr(ql_mod, "make_claim", fake_make)
    monkeypatch.setattr(ql_mod, "register_batch", fake_batch)

    # Exact shape that _inquiry_block emits: no 'kind' key
    snap = {
        "asof": "2026-07-06",
        "inquiry": {
            "letters": [
                {
                    "secCode": "000001",
                    "secName": "测试银行",
                    "title": "关注函",
                    "date": "2026-07-05",  # announce_date → event_key
                    "pdf_url": "/x/PDF.pdf",
                    "has_reply": False,
                    "type_name": "问询函",
                    # deliberately NO 'kind' key — matches _inquiry_block output
                }
            ]
        },
        "unlocks": {
            "events": [
                {
                    "ticker": "600000.SS",
                    "name": "浦发银行",
                    "unlock_date": "2026-07-15",
                    "float_pct": 8.0,
                    "float_ratio": 8.0,
                    "large_flag": True,
                }
            ]
        },
    }
    n = css.register_claims(snap)
    # Both the inquiry letter AND the large unlock should have been registered
    assert n == 2, f"Expected 2 claims registered, got {n}"


def test_register_claims_sidecar_dedup_same_day(tmp_path, monkeypatch):
    """Second call on the same day with the same events must NOT re-register (sidecar dedup)."""
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    import engine.china_special_situations as css
    import engine.qledger as ql_mod
    registered_calls: list[int] = []

    def fake_make(**kw):
        return {"_claim": True, **kw}

    def fake_batch(claims, **kw):
        registered_calls.append(len(claims))
        return [{"status": "new"} for _ in claims]

    monkeypatch.setattr(ql_mod, "make_claim", fake_make)
    monkeypatch.setattr(ql_mod, "register_batch", fake_batch)

    snap = {
        "asof": "2026-07-06",
        "inquiry": {
            "letters": [
                {"secCode": "000001", "secName": "X", "title": "T",
                 "date": "2026-07-05", "pdf_url": "", "has_reply": False, "type_name": ""}
            ]
        },
        "unlocks": {"events": []},
    }

    # First run: should register 1 claim
    n1 = css.register_claims(snap)
    assert n1 == 1

    # Second run same day, same snap: sidecar exists → 0 new claims
    n2 = css.register_claims(snap)
    assert n2 == 0, f"Second run should be 0 (sidecar dedup), got {n2}"


def test_register_claims_sidecar_dedup_next_day(tmp_path, monkeypatch):
    """Next-day re-run with same event identity must NOT re-register (sidecar dedup)."""
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.setattr("lib.config.data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})

    import engine.china_special_situations as css
    import engine.qledger as ql_mod
    registered_calls: list[int] = []

    def fake_make(**kw):
        return {"_claim": True, **kw}

    def fake_batch(claims, **kw):
        registered_calls.append(len(claims))
        return [{"status": "new"} for _ in claims]

    monkeypatch.setattr(ql_mod, "make_claim", fake_make)
    monkeypatch.setattr(ql_mod, "register_batch", fake_batch)

    # Simulate a pre-existing sidecar entry from "yesterday"
    sidecar_path = tmp_path / "data" / "china_special_sits" / "claims_registered.parquet"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"event_key": "inq_000001_2026-07-05", "first_registered": "2026-07-05"}
    ]).to_parquet(sidecar_path, index=False)

    snap = {
        "asof": "2026-07-06",
        "inquiry": {
            "letters": [
                {"secCode": "000001", "secName": "X", "title": "T",
                 "date": "2026-07-05", "pdf_url": "", "has_reply": False, "type_name": ""}
            ]
        },
        "unlocks": {"events": []},
    }

    # Run on "today" (day after sidecar entry) — same event_key → must not re-register
    n = css.register_claims(snap)
    assert n == 0, f"Next-day re-run should be 0 (sidecar dedup), got {n}"


import engine.china_special_situations as css


# ── W5: cycle-context regime chips ────────────────────────────────────────────

def test_regime_chip_missing_parquet(monkeypatch, tmp_path):
    """Missing regime_history.parquet → _regime_chip_for_date returns None, no crash."""
    import engine.china_special_situations as _css
    import lib.config as cfg
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    _css._REGIME_HISTORY_CACHE.clear()
    result = _css._regime_chip_for_date("2026-07-01")
    assert result is None


def test_regime_chip_happy_path(tmp_path, monkeypatch):
    """Valid parquet → _regime_chip_for_date returns correct chip dict."""
    import pandas as pd
    import engine.china_special_situations as _css
    import lib.config as cfg

    p = tmp_path / "data" / "china_regime"
    p.mkdir(parents=True)
    df = pd.DataFrame({
        "quad": ["Q3"],
        "quad_name": ["Stagflation"],
        "liquidity": ["contracting"],
        "cycle": ["late"],
    }, index=pd.DatetimeIndex(["2026-06-15"]))
    df.to_parquet(p / "regime_history.parquet")

    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    _css._REGIME_HISTORY_CACHE.clear()

    result = _css._regime_chip_for_date("2026-06-15")
    assert result is not None
    assert result["quad"] == "Q3"
    assert result["quad_name"] == "Stagflation"
    assert result["liquidity"] == "contracting"
    assert result["cycle"] == "late"


def test_unlock_events_get_regime_chips(tmp_path, monkeypatch):
    """FUTURE-dated unlock events map back to the latest available regime row.

    Production shape: regime_history ends TODAY (the nightly cannot write future
    rows), while unlock events are filtered to date >= today. The backward
    as-of join must stamp the latest known regime, not KeyError on the future date.
    """
    import pandas as pd
    import lib.config as cfg
    import engine.china_special_situations as _css

    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    _css._REGIME_HISTORY_CACHE.clear()

    tomorrow = (pd.Timestamp.today() + pd.Timedelta(days=1))
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    last_trading = (pd.Timestamp.today() - pd.Timedelta(days=3)).strftime("%Y-%m-%d")

    # Regime history ends BEFORE the unlock date (the only shape the nightly emits)
    rp = data_dir / "china_regime"
    rp.mkdir(parents=True)
    rdf = pd.DataFrame({
        "quad": ["Q1"],
        "quad_name": ["Goldilocks"],
        "liquidity": ["expanding"],
        "cycle": ["early"],
    }, index=pd.DatetimeIndex([last_trading]))
    rdf.to_parquet(rp / "regime_history.parquet")

    # Write unlock fixture
    up = data_dir / "china_unlocks" / "detail.parquet"
    up.parent.mkdir(parents=True, exist_ok=True)
    _make_parquet(up, [{
        "ticker": "600519.SS", "简称": "TestA", "解禁时间": tomorrow_str,
        "限售股类型": "首发原股东限售股", "占解禁前流通市值比例": 0.10,
        "实际解禁市值": 5e8, "asof": today,
    }])

    snap = _css.scan()
    events = (snap.get("unlocks") or {}).get("events") or []
    assert len(events) == 1
    assert "regime_chip" in events[0]
    assert events[0]["regime_chip"]["quad"] == "Q1"


def test_unlock_events_no_chip_when_no_parquet(tmp_path, monkeypatch):
    """Unlock events have no regime_chip when parquet absent — no crash."""
    import pandas as pd
    import lib.config as cfg
    import engine.china_special_situations as _css

    data_dir = tmp_path / "data"
    monkeypatch.setattr("lib.config.data_dir", lambda: data_dir)
    monkeypatch.setattr("lib.config.load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})
    # Use tmp_path as ROOT → no regime_history.parquet exists there
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    _css._REGIME_HISTORY_CACHE.clear()

    tomorrow = (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    today = pd.Timestamp.today().strftime("%Y-%m-%d")

    up = data_dir / "china_unlocks" / "detail.parquet"
    up.parent.mkdir(parents=True, exist_ok=True)
    _make_parquet(up, [{
        "ticker": "600519.SS", "简称": "TestA", "解禁时间": tomorrow,
        "限售股类型": "首发原股东限售股", "占解禁前流通市值比例": 0.06,
        "实际解禁市值": 2e8, "asof": today,
    }])

    snap = _css.scan()
    events = (snap.get("unlocks") or {}).get("events") or []
    assert len(events) == 1
    assert "regime_chip" not in events[0]  # no parquet → no chip, no crash
