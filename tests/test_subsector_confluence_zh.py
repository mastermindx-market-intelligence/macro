"""tests/test_subsector_confluence_zh.py — Chinese labels on the S&P subsector-confluence
desk, sourced ONLY from tables the repo already owns.

The rule under test (independent-review finding 2026-11): `site/marketdata/
subsector_confluence.json` shipped `label_zh`/`sector_zh` null on all 76 S&P rows while
the basket/partition desks thread theirs. The fix carries a Chinese name ONLY where an
existing owner table already has one — never an authored translation:

  • sub-industry names  → config/sp500_subindustry_zh.json, a character-for-character
    copy of `templates/heatmap.js` INDUSTRY_ZH (the renderer's own table, pinned by the
    parity test below so the two can never drift);
  • sector words        → engine.sp500_heatmap.SECTOR_ZH, imported directly by the
    builder — the SAME table the S&P heatmap renders from, so no second copy exists.

A key with no owned Chinese name stays null (exact string match; unknown key → None).
The engine takes one optional `zh_names` mapping argument defaulting to None; without it
the S&P payload is byte-identical to the pre-change output (the no-mapping path passes
label_zh=None/sector_zh=None where they already defaulted to None).
"""
from __future__ import annotations

import json
import re

import pytest

from engine import sp500_heatmap as hm
from engine import subsector_confluence as sc
from lib import config

TABLE_PATH = config.ROOT / "config" / "sp500_subindustry_zh.json"
BOARD_JSON = config.ROOT / "site" / "marketdata" / "subsector_confluence.json"
HEATMAP_JSON = config.ROOT / "site" / "marketdata" / "sp500_heatmap.json"


def _table() -> dict[str, str]:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def _industry_zh_js() -> dict[str, str]:
    """Parse `templates/heatmap.js` INDUSTRY_ZH verbatim (the owner table)."""
    js = (config.ROOT / "templates" / "heatmap.js").read_text(encoding="utf-8")
    m = re.search(r"var INDUSTRY_ZH = \{(.*?)\n  \};", js, re.S)
    assert m, "INDUSTRY_ZH block not found in templates/heatmap.js"
    pairs = re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1))
    out: dict[str, str] = {}
    for k, v in pairs:
        assert k not in out, f"duplicate key in INDUSTRY_ZH: {k}"
        out[k] = v
    return out


# --------------------------------------------------------------- parity ----

def test_table_parity_with_heatmap_js_industry_zh():
    """Both directions: the config table IS heatmap.js INDUSTRY_ZH, character for
    character. If the renderer's table gains/edits a name, this file must be regenerated
    from it (never hand-edited) — and vice versa."""
    tbl, js = _table(), _industry_zh_js()
    missing = sorted(set(js) - set(tbl))
    extra = sorted(set(tbl) - set(js))
    differing = sorted(k for k in set(tbl) & set(js) if tbl[k] != js[k])
    assert not missing, f"names in heatmap.js INDUSTRY_ZH missing from the config table: {missing}"
    assert not extra, f"names in the config table not present in heatmap.js INDUSTRY_ZH: {extra}"
    assert not differing, f"Chinese values differ from heatmap.js INDUSTRY_ZH: {differing}"


def test_shared_keys_agree_between_industry_table_and_sector_zh():
    """The Finviz vocabulary has one string that is both a sector and a sub-industry
    ('Industrials'). The two owner tables must agree on it so the builder's merged
    mapping is order-independent."""
    tbl = _table()
    overlap = sorted(set(tbl) & set(hm.SECTOR_ZH))
    differing = [k for k in overlap if tbl[k] != hm.SECTOR_ZH[k]]
    assert not differing, f"owner tables disagree on shared keys {differing}: " \
                          + ", ".join(f"{k}: table={tbl[k]!r} SECTOR_ZH={hm.SECTOR_ZH[k]!r}"
                                      for k in differing)


# ------------------------------------------------- builder-side mapping ----

def test_builder_mapping_merges_table_and_sector_zh():
    """scripts/build_subsector_confluence._sp500_zh_names() = the config table + the
    heatmap engine's own SECTOR_ZH, with the sector words winning only where the tables
    already agree (pinned above)."""
    from scripts.build_subsector_confluence import _sp500_zh_names
    got = _sp500_zh_names()
    assert got, "builder mapping came back empty"
    tbl = _table()
    for k, v in tbl.items():
        if k in hm.SECTOR_ZH:
            assert got[k] == hm.SECTOR_ZH[k]
        else:
            assert got[k] == v
    for k, v in hm.SECTOR_ZH.items():
        assert got[k] == v


def test_builder_mapping_degrades_to_none_when_table_missing(tmp_path, monkeypatch):
    """Additive-never-fatal: an unreadable table logs + returns None (rows stay null),
    it never kills the nightly."""
    from scripts import build_subsector_confluence as b
    monkeypatch.setattr(b, "_ZH_TABLE_PATH", tmp_path / "nope.json")
    assert b._sp500_zh_names() is None


# --------------------------------------------- real-input coverage (site) ----

@pytest.mark.needs_full_checkout("site")
def test_real_board_keys_resolve_to_owned_chinese_names():
    """Tonight's committed board: every S&P subsector key resolves in the sub-industry
    table and every sector key resolves in SECTOR_ZH. Anything unmatched is LISTED here
    (stays null by design) — the assert is not loosened to hide it."""
    board = json.loads(BOARD_JSON.read_text(encoding="utf-8"))
    assert board["universe"] == "sp500_subsectors"
    tbl = _table()
    subs, secs = board["subsectors"], board["sectors"]
    unmatched_labels = sorted({r["label"] for r in subs} - set(tbl))
    unmatched_sectors = sorted({r["sector"] for r in subs} - set(hm.SECTOR_ZH))
    assert not unmatched_labels, f"sub-industry names with no owned Chinese (stay null): {unmatched_labels}"
    assert not unmatched_sectors, f"sector names with no owned Chinese (stay null): {unmatched_sectors}"
    # the 11 sector words also equal what the heatmap payload itself ships
    heat = json.loads(HEATMAP_JSON.read_text(encoding="utf-8"))
    heat_zh = {s["en"]: s["zh"] for s in heat.get("sectors", [])}
    for r in secs:
        assert r["label"] in hm.SECTOR_ZH
        assert heat_zh.get(r["label"]) == hm.SECTOR_ZH[r["label"]], r["label"]
    print(f"resolved {len(subs)}/{len(subs)} subsector labels, {len(secs)}/{len(secs)} sector words")


# ------------------------------------------------------- engine wiring ----

def _fake_industry_map():
    return {
        ("Technology", "Semiconductors"): ["AAA", "BBB", "CCC"],
        ("Financial", "Banks - Regional"): ["DDD", "EEE", "FFF"],
        ("Technology", "Unknown Sub Industry"): ["GGG", "HHH", "III"],
    }


def _fake_safe(calls):
    def _score(label, *args, **kw):
        calls.append({"label": label, "args": args, "kw": kw})
        key, lab, sector, tickers, spy, cache = args
        return {
            "key": key, "kind": kw.get("kind", "subsector"), "label": lab,
            "label_zh": kw.get("label_zh"), "sector": sector, "sector_zh": kw.get("sector_zh"),
            "n_members": len(set(tickers)), "n_priced": len(set(tickers)),
            "reliability": "high", "coverage_pct": 100.0, "n_live": len(set(tickers)),
            "start": "2020-01-01", "as_of": "2026-11-06", "price_level": 1.0,
            "class": "tailwind",
            "entry": {"tier": "T2", "weight": 0.8, "buyable": True},
            "regime": {"state": "SETUP_BUY", "side": "buy", "tailwind": True,
                       "headwind": False, "rs_60d": 1.0},
            "members": [{"ticker": t, "name_zh": None, "price": 1.0, "ret_20d": 0.0,
                         "vs_basket": 0.0, "stock_tier": "T2", "stock_weight": 0.8,
                         "stock_ticks": 1, "stock_bars_to_cross": None,
                         "stock_buyable": True, "stock_state": "SETUP_BUY"}
                        for t in sorted(set(tickers))],
        }
    return _score


_ZH = {"Semiconductors": "半导体", "Technology": "信息技术",
       "Banks - Regional": "区域性银行", "Financial": "金融"}


def test_no_mapping_passes_null_zh_at_both_call_sites(monkeypatch):
    """Identity: with no mapping the two S&P call sites pass label_zh=None/sector_zh=None
    (the pre-change defaults) — the payload is byte-identical to the old output."""
    calls: list[dict] = []
    monkeypatch.setattr(sc.subsector_scan, "_industry_map", _fake_industry_map)
    monkeypatch.setattr(sc, "_safe_score", _fake_safe(calls))
    out = sc.compute_subsector_confluence()
    assert out["ok"] is True
    for c in calls:
        assert c["kw"].get("label_zh") is None and c["kw"].get("sector_zh") is None
    for row in out["subsectors"] + out["sectors"]:
        assert row["label_zh"] is None and row["sector_zh"] is None
    for r in out["double_gated"]["double_buy"] + out["double_gated"]["headwind_warn"]:
        assert r["subsector_zh"] is None


def test_mapping_reaches_both_call_sites_and_unknown_stays_null(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(sc.subsector_scan, "_industry_map", _fake_industry_map)
    monkeypatch.setattr(sc, "_safe_score", _fake_safe(calls))
    out = sc.compute_subsector_confluence(zh_names=_ZH)
    by_kind = {}
    for c in calls:
        by_kind.setdefault(c["kw"]["kind"], []).append(c)
    # subsector rows: label_zh = the sub-industry's owned name, sector_zh = the sector's
    for c in by_kind["subsector"]:
        key, lab, sector = c["args"][0], c["args"][1], c["args"][2]
        assert c["kw"]["label_zh"] == _ZH.get(lab)
        assert c["kw"]["sector_zh"] == _ZH.get(sector)
    # sector roll-up rows carry the sector name in English today (label == sector),
    # so both fields get the owned sector word
    for c in by_kind["sector"]:
        lab = c["args"][1]
        assert c["kw"]["label_zh"] == _ZH.get(lab)
        assert c["kw"]["sector_zh"] == _ZH.get(lab)
    rows = {r["key"]: r for r in out["subsectors"]}
    assert rows["semiconductors"]["label_zh"] == "半导体"
    assert rows["semiconductors"]["sector_zh"] == "信息技术"
    assert rows["banks-regional"]["label_zh"] == "区域性银行"
    assert rows["banks-regional"]["sector_zh"] == "金融"
    # a key with no owned Chinese name stays null — nothing guessed
    assert rows["unknown-sub-industry"]["label_zh"] is None
    assert rows["unknown-sub-industry"]["sector_zh"] == "信息技术"
    # the funnel's derived bilingual join key follows the subsector's owned name
    for r in out["double_gated"]["double_buy"]:
        assert r["subsector_zh"] == _ZH.get(r["subsector"])


def _strip_zh(payload: dict) -> dict:
    """Remove exactly the fields this change populates: label_zh/sector_zh on group rows
    and the funnel's derived subsector_zh (which funnel() copies from label_zh)."""
    out = json.loads(json.dumps(payload, default=str))
    for row in out["subsectors"] + out["sectors"]:
        row.pop("label_zh", None)
        row.pop("sector_zh", None)
    for row in out["double_gated"]["double_buy"] + out["double_gated"]["headwind_warn"]:
        row.pop("subsector_zh", None)
    return out


def test_payload_invariance_once_zh_stripped(monkeypatch):
    """With the mapping vs without it: identical payload once the zh fields are removed —
    no number, count, order, id or English label changes."""
    monkeypatch.setattr(sc.subsector_scan, "_industry_map", _fake_industry_map)
    shots: list[dict] = []

    def _recording_safe(calls):
        return _fake_safe(calls)

    monkeypatch.setattr(sc, "_safe_score", _recording_safe(shots))
    without = sc.compute_subsector_confluence()
    with_zh = sc.compute_subsector_confluence(zh_names=_ZH)
    assert _strip_zh(without) == _strip_zh(with_zh)
    # and the mapping really did populate (the invariance is not vacuous)
    assert any(r["label_zh"] for r in with_zh["subsectors"])


def test_engine_signature_defaults_zh_names_to_none():
    import inspect
    sig = inspect.signature(sc.compute_subsector_confluence)
    p = sig.parameters.get("zh_names")
    assert p is not None and p.default is None


# ------------------------------------------------------- real data (slow) ----

def _has_ohlcv():
    return (config.data_dir() / "baskets" / "ohlcv").exists()


@pytest.mark.skipif(not _has_ohlcv(), reason="OHLCV store not present")
def test_real_group_score_lands_owned_zh_names():
    """score_group on a real S&P sub-industry with the builder mapping: the two fields
    land verbatim (same contract the basket/partition desks already use)."""
    from engine import subsector_scan
    from scripts.build_subsector_confluence import _sp500_zh_names
    zh = _sp500_zh_names() or {}
    groups = subsector_scan._industry_map()
    (sector, sub), tickers = next(((k, v) for k, v in sorted(groups.items())
                                   if k[1] == "Semiconductors" and len(set(v)) >= 3))
    g = sc.score_group(sc._slug(sub), sub, sector, tickers, None, {},
                       label_zh=zh.get(sub), sector_zh=zh.get(sector))
    assert g is not None
    assert g["label_zh"] == zh["Semiconductors"]
    assert g["sector_zh"] == hm.SECTOR_ZH["Technology"]
    assert g["sector"] == "Technology" and g["label"] == "Semiconductors"
