"""CN-PR-1 — armed pack: universe screen, per-class band, frozen legs, isolation."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.prophet_live import cn_clock
from engine.prophet_live import cn_pack as CP
from engine.prophet_live import r2io
from engine.prophet_live.interval import ADJUSTED

ROOT = Path(__file__).resolve().parent.parent
IDX = pd.bdate_range("2024-01-02", periods=80)
NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def _close(last: float = 10.0) -> pd.Series:
    vals = [float(last) * (1.0 + 0.001 * (i % 5 - 2)) for i in range(len(IDX))]
    vals[-1] = float(last)
    return pd.Series(vals, index=IDX)


def _gate(threshold: float = 10.0):
    def g(_ticker: str, close) -> dict:
        px = float(close.iloc[-1])
        buy = px >= threshold
        return {"eligible": True, "tier": "T2", "tier_cascade": "T2" if buy else None,
                "sub": "confirmed"}
    return g


def test_is_cn_stock_drops_etfs_indices_and_bj() -> None:
    assert CP.is_cn_stock("600519.SS", "Consumer")
    assert CP.is_cn_stock("300750.SZ", "Industrials")
    assert not CP.is_cn_stock("510300.SS", "Sector ETF")
    assert not CP.is_cn_stock("000300.SS", "Index")
    assert not CP.is_cn_stock("920000.BJ", "Consumer")
    assert not CP.is_cn_stock("AAPL", "Tech")


def test_filter_universe_keeps_only_mainland_stocks() -> None:
    rows = [
        ("600519.SS", _close(), None, "Kweichow", "Consumer"),
        ("510300.SS", _close(), None, "CSI300", "Sector ETF"),
        ("000001.SZ", _close(), None, "PAB", "Financials"),
        ("920001.BJ", _close(), None, "BJ", "Consumer"),
    ]
    kept = [r[0] for r in CP.filter_universe(rows)]
    assert kept == ["600519.SS", "000001.SZ"]


def test_band_pct_follows_the_board_class() -> None:
    assert CP.band_pct_for("600519.SS") == 10.0
    assert CP.band_pct_for("688981.SS") == 20.0
    assert CP.band_pct_for("300750.SZ") == 20.0
    assert CP.band_pct_for("301269.SZ") == 20.0


def test_centre_record_uses_the_class_band_not_the_us_15() -> None:
    rec = CP.centre_record("301269.SZ", _close(20.0), cfg=CP.pack_cfg(None),
                           gate_fn=_gate(99.0))
    assert rec["band_pct"] == 20.0
    lo, hi = rec["span"]
    # Up-only (not buyable at 20 vs threshold 99): span is [as_of, as_of * 1.20]
    assert abs(lo - 20.0) < 1e-9
    assert abs(hi - 24.0) < 1e-6


def test_assemble_stamps_cn_schema_and_frozen_legs() -> None:
    rec = CP.centre_record("600519.SS", _close(10.0), cfg=CP.pack_cfg(None),
                           gate_fn=_gate(5.0))
    entry = __import__("engine.prophet_live.armed_pack", fromlist=["name_entry"]).name_entry(
        rec, None)
    payload = CP.assemble(
        {"600519.SS": entry}, as_of="2026-08-14", cfg=CP.pack_cfg(None),
        universe_n=1, wanted_n=1, gate_calls=1, build_seconds=0.1, skipped={},
        frozen={"600519.SS": {"prophet_score": 81.2, "prophet_rank": 3,
                              "lane": "featured"}},
        now=NOW,
    )
    assert payload["schema"] == CP.SCHEMA
    assert payload["market"] == "CN"
    assert payload["price_adjustment"] == ADJUSTED
    frozen = payload["names"]["600519.SS"]["frozen"]
    assert frozen["score"] == 81.2 and frozen["lane"] == "featured"
    assert payload["names"]["600519.SS"]["repaint_disclosure"]["live_derived"]


def test_r2_keys_are_distinct_from_the_us_lane() -> None:
    assert r2io.CN_PACK_KEY == "live_flow/cn_prophet_live_armed.json"
    assert r2io.CN_LIVE_KEY == "live_flow/cn_prophet_live.json"
    assert r2io.CN_PACK_KEY != r2io.PACK_KEY
    assert r2io.CN_LIVE_KEY != r2io.LIVE_KEY
    assert r2io.PACK_KEY == "live_flow/prophet_live_armed.json"


def test_cn_modules_import_no_limit_alpha_research() -> None:
    forbidden = ("cn_prophet_audit", "china_intelligence", "washout_program")
    for rel in ("engine/prophet_live/cn_pack.py", "engine/prophet_live/cn_states.py",
                "engine/prophet_live/cn_clock.py", "scripts/build_cn_live_pack.py",
                "scripts/cn_live_evaluator.py"):
        src = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(src):
            if isinstance(node, ast.Import):
                imported.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        blob = " ".join(imported)
        for token in forbidden:
            assert token not in blob, f"{rel} imports {token}"


def test_stock_tradability_ok_matches_the_nightly_predicate() -> None:
    from scripts.build_china_library import stock_tradability_ok

    assert stock_tradability_ok("600000.SS") is None
    assert stock_tradability_ok("600000.SS", st_flag=True) == "st"
    assert stock_tradability_ok("600000.SS", name_zh="*ST 示例") == "st"
    assert stock_tradability_ok("600000.SS", mktcap=10.0) == "mcap"
    assert stock_tradability_ok("600000.SS", mktcap=30.0) is None  # placeholder
    assert stock_tradability_ok("600000.SS", adv_yi=0.01) == "adv"


# --- tradability gate on the live pack path (P1) ----------------------------
# The nightly board applies stock_tradability_ok with maps loaded inline in
# build_china_library.main; these lock the extracted read-only helper, the strict
# Boolean map, and the main() wiring that puts the gate on the pack's path.


def test_load_tradability_metadata_placeholder_and_latest_st_row(
        tmp_path, monkeypatch) -> None:
    from scripts import build_china_library as bcl

    (tmp_path / "china_search").mkdir(parents=True)
    pd.DataFrame({
        "ticker": ["600001.SS", "600002.SS"],
        "mktcap_yi": [500.0, 30.0],          # 30.0 exactly = the placeholder sentinel
        "name_zh": ["名称一", "名称二"],
        "name_en": ["One Co", "Two Co"],
    }).to_parquet(tmp_path / "china_search" / "members.parquet")
    (tmp_path / "tushare").mkdir(parents=True)
    pd.DataFrame({
        "ticker": ["600003.SS", "600003.SS", "600004.SS"],
        "name": ["ST旧名", "正常名", "*ST新潮"],
        "trade_date": ["20261001", "20261009", "20261009"],
    }).to_parquet(tmp_path / "tushare" / "moneyflow.parquet")
    monkeypatch.setattr(bcl.config, "data_dir", lambda: tmp_path)

    meta = bcl.load_tradability_metadata()

    assert meta["mktcap_by"] == {"600001.SS": 500.0}              # placeholder absent
    assert meta["name_zh_by"] == {"600001.SS": "名称一", "600002.SS": "名称二"}
    assert meta["name_en_by"] == {"600001.SS": "One Co", "600002.SS": "Two Co"}
    assert meta["st_flag_by"] == {"600003.SS": False, "600004.SS": True}  # latest row


def test_load_tradability_metadata_missing_files_stay_empty(
        tmp_path, monkeypatch) -> None:
    from scripts import build_china_library as bcl

    monkeypatch.setattr(bcl.config, "data_dir", lambda: tmp_path)  # nothing written

    meta = bcl.load_tradability_metadata()

    assert meta == {"mktcap_by": {}, "name_zh_by": {},
                    "name_en_by": {}, "st_flag_by": {}}


def test_tradability_map_is_bool_pass_covers_every_ticker() -> None:
    from scripts.build_cn_live_pack import tradability_map

    meta = {
        "mktcap_by": {"600006.SS": 10.0, "600007.SS": 30.0},
        "name_zh_by": {"600005.SS": "ST天成"},
        "name_en_by": {},
        "st_flag_by": {"600004.SS": True},
    }
    liq_by = {"600008.SS": {"adv_yi": 0.38}}
    tickers = ["600001.SS", "600004.SS", "600005.SS", "600006.SS",
               "600007.SS", "600008.SS", "600009.SS"]

    m = tradability_map(tickers, meta=meta, liq_by=liq_by)

    assert set(m) == set(tickers)                    # every input ticker present
    assert all(isinstance(v, bool) for v in m.values())  # raw reasons would fail here
    assert m["600001.SS"] is True                    # nothing known -> passes through
    assert m["600004.SS"] is False                   # ST flag
    assert m["600005.SS"] is False                   # ST name_zh
    assert m["600006.SS"] is False                   # cap 10.0 < 30 亿 floor
    assert m["600007.SS"] is True                    # 30.0 exactly = placeholder -> unknown
    assert m["600008.SS"] is False                   # ADV 0.38 < 0.5 亿/day floor
    assert m["600009.SS"] is True                    # missing cap AND ADV -> passes


def test_main_wires_full_tradability_map_and_universe_rows(monkeypatch) -> None:
    import scripts.build_cn_live_pack as B
    from scripts import build_china_library as bcl

    rows = [
        ("600519.SS", _close(), None, "Kweichow", "Consumer"),
        ("510300.SS", _close(), None, "CSI300", "Sector ETF"),   # filtered out
        ("000001.SZ", _close(), None, "PAB", "Financials"),
    ]
    seen: dict = {}
    payload = {"meta": {}}

    def fake_build(**kwargs):
        seen.update(kwargs)
        return payload

    published: list = []
    monkeypatch.setattr(bcl, "universe", lambda: rows)
    monkeypatch.setattr(bcl, "load_tradability_metadata",
                        lambda: {"mktcap_by": {}, "name_zh_by": {},
                                 "name_en_by": {}, "st_flag_by": {}})
    monkeypatch.setattr("engine.china_liquidity.liquidity_map", lambda ts: {})
    monkeypatch.setattr(B, "build", fake_build)
    monkeypatch.setattr(B.r2io, "put_json", lambda *a, **k: published.append(a))

    assert B.main([]) == 0

    assert set(seen["tradable"]) == {"600519.SS", "000001.SZ"}   # exactly the stocks
    assert all(v is True for v in seen["tradable"].values())
    assert [r[0] for r in seen["universe_rows"]] == ["600519.SS", "000001.SZ"]
    assert seen["limit"] is None and seen["now"] is None
    assert published == []                                       # no --publish, no --out
    assert payload["meta"]["tradability"] == {"universe": 2, "pass": 2,
                                              "drop": {"st": 0, "mcap": 0, "adv": 0}}


def test_build_refuses_a_map_missing_a_universe_ticker() -> None:
    import scripts.build_cn_live_pack as B

    rows = [("600519.SS", _close(), None, "K", "Consumer"),
            ("000001.SZ", _close(), None, "P", "Financials")]
    with pytest.raises(RuntimeError) as ei:
        B.build(universe_rows=rows, tradable={"600519.SS": True},
                gate_fn=_gate(), frozen={})
    assert "000001.SZ" in str(ei.value) and "1/2" in str(ei.value)
    with pytest.raises(RuntimeError):
        B.build(universe_rows=rows, tradable={},          # empty map, non-empty rows
                gate_fn=_gate(), frozen={})


def test_main_returns_rc1_when_the_map_cannot_cover_the_universe(
        monkeypatch) -> None:
    import scripts.build_cn_live_pack as B
    from scripts import build_china_library as bcl

    rows = [("600519.SS", _close(), None, "K", "Consumer"),
            ("000001.SZ", _close(), None, "P", "Financials")]
    built: list = []
    monkeypatch.setattr(bcl, "universe", lambda: rows)
    monkeypatch.setattr(bcl, "load_tradability_metadata",
                        lambda: {"mktcap_by": {}, "name_zh_by": {},
                                 "name_en_by": {}, "st_flag_by": {}})
    monkeypatch.setattr("engine.china_liquidity.liquidity_map", lambda ts: {})
    monkeypatch.setattr(B, "tradability_map",
                        lambda ts, *, meta, liq_by: {"600519.SS": True})  # partial
    monkeypatch.setattr(B, "build", lambda **kw: built.append(kw))

    assert B.main([]) == 1            # ::error + rc 1 — no pack published
    assert built == []                # the refusal fires before build


def test_build_filters_untradable_names_from_the_pack() -> None:
    import scripts.build_cn_live_pack as B

    rows = [("600519.SS", _close(10.0), None, "Kweichow", "Consumer"),
            ("000001.SZ", _close(12.0), None, "PAB", "Financials")]
    payload = B.build(universe_rows=rows,
                      tradable={"600519.SS": True, "000001.SZ": False},
                      gate_fn=_gate(), frozen={})

    assert "600519.SS" in payload["names"]
    assert "000001.SZ" not in payload["names"]     # the one False never reaches the pack
    assert payload["meta"]["universe_n"] == 1
