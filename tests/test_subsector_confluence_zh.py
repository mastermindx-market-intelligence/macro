"""tests/test_subsector_confluence_zh.py — Chinese labels on the S&P subsector-confluence
desk, sourced ONLY from tables the repo already owns.

The rule under test (independent-review finding 2026-11): `site/marketdata/
subsector_confluence.json` shipped `label_zh`/`sector_zh` null on all 76 S&P rows while
the basket/partition desks thread theirs. The fix carries a Chinese name ONLY where an
existing owner table already has one — never an authored translation:

  • sub-industry names  → config/sp500_subindustry_zh.json, a character-for-character
    copy of `templates/heatmap.js` INDUSTRY_ZH (the renderer's own table, pinned by the
    parity test below so the two can never drift);
  • sector words        → engine.sp500_heatmap.SECTOR_ZH, merged in by the light loader
    engine/sp500_zh_names.py — the SAME table the S&P heatmap renders from, so no second
    copy exists.

Review r1 (2026-11-10): the loader moved from scripts/build_subsector_confluence.py into
engine/sp500_zh_names.py (B1) and this file imports ONLY the light module and the
engines — NEVER scripts.build_subsector_confluence, whose import closure pulls 23 files
the curated-exclusive CI job `unrun-subsector-themes` does not name, reddening the
`contract-delta` check. The builder's wiring is pinned at source level via `ast` below
instead of by import.

A key with no owned Chinese name stays null (exact string match — case-folded and
whitespace-padded near keys included; unknown key → None). The engine takes one optional
`zh_names` mapping argument defaulting to None; without it the S&P payload is
byte-identical to the pre-change output. The loader is all-or-nothing (S2): any table
that is not a non-empty flat str→str object → None for the whole mapping.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from engine import sp500_heatmap as hm
from engine import subsector_confluence as sc
from engine.sp500_zh_names import DEFAULT_TABLE_PATH as TABLE_PATH
from engine.sp500_zh_names import load_sp500_zh_names

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_subsector_confluence.py"
DETAIL_TEMPLATE_PATH = ROOT / "templates" / "subsector_detail.html.j2"
BOARD_JSON = ROOT / "site" / "marketdata" / "subsector_confluence.json"
HEATMAP_JSON = ROOT / "site" / "marketdata" / "sp500_heatmap.json"


def _table() -> dict[str, str]:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def _industry_zh_js() -> dict[str, str]:
    """Parse `templates/heatmap.js` INDUSTRY_ZH verbatim (the owner table)."""
    js = (ROOT / "templates" / "heatmap.js").read_text(encoding="utf-8")
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
    # N5 (review r1): the parity is not vacuous — both owner tables are sizeable, so
    # emptying BOTH cannot green this test.
    assert len(tbl) >= 100, f"config table unexpectedly small ({len(tbl)} entries)"
    assert len(js) >= 100, f"INDUSTRY_ZH unexpectedly small ({len(js)} entries)"
    missing = sorted(set(js) - set(tbl))
    extra = sorted(set(tbl) - set(js))
    differing = sorted(k for k in set(tbl) & set(js) if tbl[k] != js[k])
    assert not missing, f"names in heatmap.js INDUSTRY_ZH missing from the config table: {missing}"
    assert not extra, f"names in the config table not present in heatmap.js INDUSTRY_ZH: {extra}"
    assert not differing, f"Chinese values differ from heatmap.js INDUSTRY_ZH: {differing}"


def test_shared_keys_agree_between_industry_table_and_sector_zh():
    """The Finviz vocabulary has one string that is both a sector and a sub-industry
    ('Industrials'). The two owner tables must agree on it so the loader's merged
    mapping is order-independent."""
    tbl = _table()
    overlap = sorted(set(tbl) & set(hm.SECTOR_ZH))
    differing = [k for k in overlap if tbl[k] != hm.SECTOR_ZH[k]]
    assert not differing, f"owner tables disagree on shared keys {differing}: " \
                          + ", ".join(f"{k}: table={tbl[k]!r} SECTOR_ZH={hm.SECTOR_ZH[k]!r}"
                                      for k in differing)


# ------------------------------------------------- loader (light module) ----

def test_loader_merges_table_and_sector_zh():
    """engine.sp500_zh_names.load_sp500_zh_names() = the config table + the heatmap
    engine's own SECTOR_ZH, with the sector words winning only where the tables already
    agree (pinned above)."""
    got = load_sp500_zh_names()
    assert got, "loader mapping came back empty"
    tbl = _table()
    for k, v in tbl.items():
        if k in hm.SECTOR_ZH:
            assert got[k] == hm.SECTOR_ZH[k]
        else:
            assert got[k] == v
    for k, v in hm.SECTOR_ZH.items():
        assert got[k] == v


def test_loader_degrades_to_none_when_table_missing(tmp_path):
    """Additive-never-fatal: an unreadable table logs + returns None (rows stay null),
    it never kills the nightly."""
    assert load_sp500_zh_names(table_path=tmp_path / "nope.json") is None


_BAD_TABLES = [
    ("json-null", "null"),
    ("list", "[1, 2]"),
    ("string", '"abc"'),
    ("number", "5"),
    ("list-of-pairs", '[["Semiconductors", "X"]]'),
    ("non-string-value", '{"Semiconductors": 5}'),
    ("nested-value", '{"Semiconductors": {"a": 1}}'),
    ("empty-string-value", '{"Semiconductors": ""}'),
    ("empty-string-key", '{"": "半导体"}'),
    ("empty-object", "{}"),
    ("empty-file", ""),
    ("invalid-json", "{not json"),
]


@pytest.mark.parametrize("case,contents", _BAD_TABLES, ids=[c for c, _ in _BAD_TABLES])
def test_loader_is_all_or_nothing_on_wrong_shape_tables(tmp_path, case, contents):
    """S2 (review r1): anything other than a non-empty flat str→str object → None for
    the WHOLE mapping — never a crash, never a non-string value reaching `label_zh`."""
    p = tmp_path / "table.json"
    p.write_text(contents, encoding="utf-8")
    assert load_sp500_zh_names(table_path=p) is None, case


def test_builder_wires_the_light_loader_into_the_engine_call():
    """B1 (review r1), pinned at source level so this suite never imports the heavy
    builder: scripts/build_subsector_confluence.py imports load_sp500_zh_names from
    engine.sp500_zh_names and passes zh_names= at the S&P compute call."""
    tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "engine.sp500_zh_names"
        and any(alias.name == "load_sp500_zh_names" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert imported, "builder no longer imports load_sp500_zh_names from engine.sp500_zh_names"

    wired = False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "compute_subsector_confluence"):
            continue
        for kw in node.keywords:
            if kw.arg != "zh_names":
                continue
            value = kw.value
            if (isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "load_sp500_zh_names"):
                wired = True
    assert wired, "the S&P compute call no longer passes zh_names=load_sp500_zh_names(...)"


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


def test_case_folded_and_whitespace_keys_stay_null(monkeypatch):
    """N3 (review r1): matching is exact string. A case-different key and a key with a
    trailing space NEVER resolve — those rows stay null rather than fuzzy-matching a
    near key someone might add to the mapping."""
    calls: list[dict] = []
    monkeypatch.setattr(sc.subsector_scan, "_industry_map", _fake_industry_map)
    monkeypatch.setattr(sc, "_safe_score", _fake_safe(calls))
    near = {
        "semiconductors": "半导体", "Semiconductors ": "半导体",
        "banks - regional": "区域性银行", "technology": "信息技术", "Technology ": "信息技术",
        "financial": "金融", "Financial ": "金融",
    }
    out = sc.compute_subsector_confluence(zh_names=near)
    for c in calls:
        assert c["kw"].get("label_zh") is None, f"near key matched at {c['label']!r}"
        assert c["kw"].get("sector_zh") is None, f"near key matched at {c['label']!r}"
    for row in out["subsectors"] + out["sectors"]:
        assert row["label_zh"] is None and row["sector_zh"] is None
    for r in out["double_gated"]["double_buy"] + out["double_gated"]["headwind_warn"]:
        assert r["subsector_zh"] is None


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


# ----------------------------------------------- detail-page consumer (B2) ----

def test_detail_subtitle_sector_word_respects_the_language_toggle():
    """B2 (review r1): the id-subtitle's sector word renders through L() — the file's own
    regEn/regZh convention — so English mode shows the English sector word and Chinese
    mode the Chinese one. The behavioural pin (a real S&P row executed through the
    template's script) lives beside this suite's existing executor in
    tests/test_product_chrome.py."""
    tpl = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8")
    line = next((l for l in tpl.splitlines() if '<div class="id-subtitle">' in l), "")
    assert "L(esc(g.sector || g.sector_zh || '—'), esc(g.sector_zh || g.sector || '—'))" in line, \
        "id-subtitle sector word no longer renders through L()"
    # the pre-fix bare form (Chinese word in BOTH modes) must not come back
    assert "'<span>' + esc(g.sector_zh || g.sector || '—') + '</span>'" not in tpl


# ------------------------------------------------------- real data (slow) ----

def _has_ohlcv():
    return (ROOT / "data" / "baskets" / "ohlcv").exists()


@pytest.mark.skipif(not _has_ohlcv(), reason="OHLCV store not present")
def test_real_group_score_lands_owned_zh_names():
    """score_group on a real S&P sub-industry with the loader mapping: the two fields
    land verbatim (same contract the basket/partition desks already use)."""
    from engine import subsector_scan
    zh = load_sp500_zh_names() or {}
    groups = subsector_scan._industry_map()
    (sector, sub), tickers = next(((k, v) for k, v in sorted(groups.items())
                                   if k[1] == "Semiconductors" and len(set(v)) >= 3))
    g = sc.score_group(sc._slug(sub), sub, sector, tickers, None, {},
                       label_zh=zh.get(sub), sector_zh=zh.get(sector))
    assert g is not None
    assert g["label_zh"] == zh["Semiconductors"]
    assert g["sector_zh"] == hm.SECTOR_ZH["Technology"]
    assert g["sector"] == "Technology" and g["label"] == "Semiconductors"
