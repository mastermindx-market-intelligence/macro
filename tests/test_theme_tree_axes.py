"""Tests for U4: the six-axis "Company profile" in the /theme_tree.html ticker panel.

Covers the "not done unless" clauses of SPEC_U4:

  1. Parity — the batched identity resolver equals the incumbent
     ``resolve_graph_node_identity``, and ``read_axes`` with injected frames
     equals ``read_axes`` with its default per-call readers.
  2. Point-in-time — a profile row observed after ``as_of`` is not used.
  3. Typed statuses — every non-available cell ships a typed status with null
     labels; every available cell ships a non-empty label; the page carries a
     reason line for every status.
  4. Forbidden keys — no FORBIDDEN_VALUE_KEY_WORDS key, and no raw
     value/source/provenance/rights_context key, in the shipped table; a
     forbidden key drops the whole profile.
  5. No THS/finviz/ltheme strings in the shipped table.
  6. Budget — the profile share stays ≤ 120 KB and the whole blob ≤ 400 KB on
     real data; an over-budget table ships without the profile.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine.classification_axes import cell, registry  # noqa: E402
from scripts import build_theme_tree_page as mod  # noqa: E402

_AS_OF = "2026-10-17"
_VENDOR = re.compile(r"ltheme:|ths_concepts|finviz_themes|basket_china_ths|china_ths|finviz|THS")
_RAW_KEYS = {"value", "source", "provenance", "rights_context"}
_TEMPLATE = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")

_NODES = REPO / "data" / "theme_graph" / "nodes.parquet"
_EDGES = REPO / "data" / "theme_graph" / "edges.parquet"
_PROFILES = REPO / "data" / "profile" / "profiles.parquet"


def _need_real_data() -> None:
    if not (_NODES.exists() and _EDGES.exists() and _PROFILES.exists()):
        pytest.skip("theme_graph / profile parquets missing in this sparse tree")


@pytest.fixture(scope="module")
def real_blob() -> dict:
    _need_real_data()
    nodes = pd.read_parquet(_NODES)
    edges = pd.read_parquet(_EDGES)
    raw = mod._ticker_lookup_json(REPO, nodes, edges, as_of=_AS_OF, knowledge_cutoff=_AS_OF)
    assert raw
    return {"raw": raw, "data": json.loads(raw.replace("<\\/", "</"))}


# ---------------------------------------------------------------------------
# 1. Parity
# ---------------------------------------------------------------------------


def test_batched_resolver_matches_incumbent(real_blob):
    from engine.theme_graph import identity_resolution as ir

    resolve = mod._batched_identity_resolver(_AS_OF)
    keys = sorted(real_blob["data"]["records"])[:: max(1, len(real_blob["data"]["records"]) // 25)]
    assert keys
    for key in keys:
        market, _, symbol = key.partition(":")
        node_id = f"co:{market}:{symbol}"
        try:
            want = ir.resolve_graph_node_identity(node_id, asof=_AS_OF)
        except ir.UnknownGraphNodeError:
            with pytest.raises(ir.UnknownGraphNodeError):
                resolve(node_id, asof=_AS_OF)
            continue
        got = resolve(node_id, asof=_AS_OF)
        drop = {"computed_at"}
        assert {k: v for k, v in got.items() if k not in drop} == {
            k: v for k, v in want.items() if k not in drop
        }, key


def test_injected_readers_match_default_readers(real_blob):
    static, geography_for = mod._axis_readers(REPO, _AS_OF)
    keys = sorted(real_blob["data"]["records"])
    # Every market present, plus a stride across the rest.
    sample = sorted(set(keys[:: max(1, len(keys) // 30)]) | {
        next(k for k in keys if k.startswith(m)) for m in {k.split(":")[0] for k in keys}
    })
    for key in sample:
        market, _, symbol = key.partition(":")
        sid = f"co:{market}:{symbol}"
        readers = dict(static)
        readers["geography"] = geography_for(sid)
        injected = registry.read_axes(sid, as_of=_AS_OF, root=REPO, readers=readers)
        default = registry.read_axes(sid, as_of=_AS_OF, root=REPO)
        for axis in cell.AXES:
            a, b = injected["cells"][axis], default["cells"][axis]
            assert (a["status"], a.get("reason_code")) == (b["status"], b.get("reason_code")), (key, axis)
            assert json.dumps(a.get("value"), sort_keys=True) == json.dumps(b.get("value"), sort_keys=True), (key, axis)


# ---------------------------------------------------------------------------
# 2. Point-in-time
# ---------------------------------------------------------------------------


def test_profile_row_after_as_of_is_not_used():
    _need_real_data()
    profiles = pd.read_parquet(_PROFILES)
    if "NVDA" not in profiles.index:
        pytest.skip("NVDA absent from profiles.parquet")
    observed = pd.Timestamp(str(profiles.loc["NVDA", "as_of"])[:10])
    before = (observed - pd.Timedelta(days=1)).date().isoformat()
    on = mod._company_axes(REPO, ["us:NVDA"], observed.date().isoformat())["us:NVDA"]
    early = mod._company_axes(REPO, ["us:NVDA"], before)["us:NVDA"]
    sic_on = next(e for e in on if e["axis"] == "sic_industry")
    sic_early = next(e for e in early if e["axis"] == "sic_industry")
    assert sic_on["status"] == "available" and sic_on["label_en"]
    assert sic_early["status"] != "available"
    assert sic_early["label_en"] is None and sic_early["label_zh"] is None


# ---------------------------------------------------------------------------
# 3. Typed statuses
# ---------------------------------------------------------------------------


def test_every_record_lists_six_axes_in_order(real_blob):
    data = real_blob["data"]
    table = data["axis_cells"]
    for key, rec in data["records"].items():
        refs = rec["axes"]
        assert [table[i]["axis"] for i in refs] == list(cell.AXES), key


def test_typed_status_entries_never_ship_empty_or_zero_labels(real_blob):
    statuses = set()
    for entry in real_blob["data"]["axis_cells"]:
        assert set(entry) == {"axis", "status", "reason_code", "label_en", "label_zh"}
        statuses.add(entry["status"])
        if entry["status"] == "available":
            assert entry["label_en"] and entry["label_en"].strip() not in {"0", "0.0"}
            assert entry["label_zh"] and entry["label_zh"].strip() not in {"0", "0.0"}
        else:
            assert entry["status"] in {"unknown", "unavailable", "stale", "not_applicable", "rights_blocked"}
            assert entry["label_en"] is None and entry["label_zh"] is None
            assert entry["reason_code"]
    assert {"available", "not_applicable"} <= statuses


@pytest.mark.parametrize(
    "status,en,zh",
    [
        ("unknown", "Not recorded yet", "暂无记录"),
        ("unavailable", "Source not available on this build", "本次构建无此数据源"),
        ("stale", "Out of date", "数据过期"),
        ("not_applicable", "Not tracked for this market", "该市场暂不跟踪"),
        ("rights_blocked", "Not shown (licence)", "因授权不显示"),
    ],
)
def test_template_has_reason_line_for_every_status(status, en, zh):
    assert f"{status}:['{en}','{zh}']" in _TEMPLATE


def test_value_chain_not_applicable_is_not_blamed_on_the_market():
    assert "value_chain:{not_applicable:['Describes themes, not single companies','描述主题，不适用于单个公司']}" in _TEMPLATE
    assert "(REASON_AXIS[c.axis]||{})[c.status]||REASON[c.status]" in _TEMPLATE


def test_template_profile_uses_text_content_only():
    start = _TEMPLATE.index("function profile(")
    body = _TEMPLATE[start:_TEMPLATE.index("function match(", start)]
    assert "innerHTML" not in body
    assert "Company profile" in body and "公司概况" in body
    assert "Context only — not a rating" in body and "仅供参考，非评级" in body


def test_cn_company_shows_not_applicable_rows(real_blob):
    data = real_blob["data"]
    cn = [k for k in data["records"] if k.startswith("cn:")]
    if not cn:
        pytest.skip("no CN record with a theme path")
    entries = [data["axis_cells"][i] for i in data["records"][cn[0]]["axes"]]
    assert any(e["status"] == "not_applicable" for e in entries)


def test_axis_labels():
    assert mod._axis_label("lifecycle", {"node_status": "canonical"}) == ("Active", "存续")
    geo = mod._axis_label("geography", {"listing_mic": "XNAS", "listing_country": "US", "domicile": "CN"})
    assert geo and "Nasdaq" in geo[0] and "United States" in geo[0] and "China" in geo[0]
    assert mod._axis_label("sic_industry", {}) is None


# ---------------------------------------------------------------------------
# 4/5. Forbidden keys and vendor strings
# ---------------------------------------------------------------------------


def test_shipped_table_has_no_forbidden_or_raw_keys(real_blob):
    from engine.theme_graph import hierarchy_breadth_display as hb

    table = real_blob["data"]["axis_cells"]
    assert hb.validate_no_forbidden_keys(table) == []
    assert mod._axes_key_findings(table) == []
    for entry in table:
        assert not (_RAW_KEYS & set(entry))


def test_shipped_table_has_no_vendor_strings(real_blob):
    text = json.dumps(real_blob["data"]["axis_cells"], ensure_ascii=False)
    assert not _VENDOR.search(text)


def test_key_walk_finds_forbidden_words():
    word = sorted(cell.FORBIDDEN_VALUE_KEY_WORDS)[0]
    assert mod._axes_key_findings({"a": [{f"x_{word}": 1}]}) == [f"x_{word}"]


def test_forbidden_key_drops_whole_profile(monkeypatch):
    word = sorted(cell.FORBIDDEN_VALUE_KEY_WORDS)[0]
    monkeypatch.setattr(
        mod, "_company_axes",
        lambda root, keys, as_of: {k: [{"axis": "lifecycle", word: 1}] for k in keys},
    )
    records = {"us:AAA": {"paths": []}}
    assert mod._attach_axes(REPO, records, _AS_OF) is None
    assert "axes" not in records["us:AAA"]


# ---------------------------------------------------------------------------
# 6. Budget
# ---------------------------------------------------------------------------


def test_profile_and_blob_within_budget_on_real_data(real_blob):
    data = real_blob["data"]
    refs = {k: r["axes"] for k, r in data["records"].items()}
    share = len(json.dumps([data["axis_cells"], refs], ensure_ascii=False, sort_keys=True).encode("utf-8"))
    assert share <= mod._AXES_BLOB_BUDGET_BYTES
    assert len(real_blob["raw"].encode("utf-8")) <= mod._TICKER_BLOB_BUDGET_BYTES


def test_over_budget_profile_ships_without_axes(monkeypatch):
    monkeypatch.setattr(mod, "_AXES_BLOB_BUDGET_BYTES", 1)
    entry = {"axis": "lifecycle", "status": "available", "reason_code": None,
             "label_en": "Active", "label_zh": "存续"}
    monkeypatch.setattr(mod, "_company_axes", lambda root, keys, as_of: {k: [entry] for k in keys})
    records = {"us:AAA": {"paths": []}}
    assert mod._attach_axes(REPO, records, _AS_OF) is None
    assert "axes" not in records["us:AAA"]
