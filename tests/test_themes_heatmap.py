"""Pure-function tests for the Finviz themes treemap engine.

Covers the theme → subsector → member assembly: the contract shape the shared
``heatmap.js`` renderer consumes (``map_type='themes'``, sectors=themes, tiles=
subsectors carrying a member list), subsector/member perf wiring, count-based
sizing, bilingual theme labels, and graceful handling of missing perf. No
network; everything is driven by small in-memory fixtures.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import themes_heatmap as th  # noqa: E402
import copy
import hashlib
import json
import pytest


def _tree():
    return [
        {"theme": "Artificial Intelligence", "key": "Artificial Intelligence", "subsectors": [
            {"key": "aicompute", "name": "Compute", "description": "Compute & Acceleration",
             "members": ["NVDA", "AMD", "MSFT"]},
            {"key": "aimodels", "name": "Models", "description": "Foundation Models",
             "members": ["GOOGL", "META"]},
        ]},
        {"theme": "FinTech", "key": "FinTech", "subsectors": [
            {"key": "fintechpayments", "name": "Payments", "description": "Payments",
             "members": ["V", "MA"]},
        ]},
    ]


def _sub_perf():
    return {
        "aicompute": {"1D": -3.1, "1W": -6.32},
        "aimodels": {"1D": 2.05},
        "fintechpayments": {"1D": 3.75, "1W": 1.1},
    }


def _mem_perf():
    return {
        "NVDA": {"1D": -1.64}, "AMD": {"1D": -2.06}, "MSFT": {"1D": 5.71},
        "GOOGL": {"1D": -1.84}, "META": {"1D": 0.4},
        "V": {"1D": 0.9}, "MA": {"1D": 1.2},
    }


def test_contract_shape():
    p = th.build_themes_heatmap(_tree(), _sub_perf(), _mem_perf(), asof="2026-06-28")
    assert p["map_type"] == "themes"
    assert p["size_basis"] == "count"
    assert p["default_tf"] == "1D"
    # eight daily-group timeframes, all available
    assert [tf["key"] for tf in p["timeframes"]] == ["1D", "1W", "MTD", "1M", "3M", "6M", "YTD", "1Y"]
    assert all(tf["available"] for tf in p["timeframes"])
    # sectors = themes, in tree order, bilingual
    assert [s["key"] for s in p["sectors"]] == ["Artificial Intelligence", "FinTech"]
    assert p["sectors"][0]["zh"] == "人工智能"
    assert p["n_tiles"] == 3
    assert p["n_members"] == 7


def test_tile_is_subsector_with_members():
    p = th.build_themes_heatmap(_tree(), _sub_perf(), _mem_perf())
    compute = next(t for t in p["tiles"] if t["t"] == "aicompute")
    assert compute["name"] == "Compute"
    assert compute["sector"] == "Artificial Intelligence"       # theme is the group
    assert compute["desc"] == "Compute & Acceleration"
    assert compute["size"] == 3                                  # member count
    assert compute["perf"]["1D"] == -3.1                         # subsector colour
    assert compute["perf"]["1W"] == -6.32
    mem = {m["t"]: m["perf"] for m in compute["members"]}
    assert mem["NVDA"]["1D"] == -1.64 and mem["MSFT"]["1D"] == 5.71  # member rows


def test_missing_perf_is_dropped_not_nulled():
    # subsector with no perf entry, member with no perf entry
    tree = [{"theme": "X", "key": "X", "subsectors": [
        {"key": "xsub", "name": "Sub", "description": "", "members": ["AAA", "BBB"]},
    ]}]
    p = th.build_themes_heatmap(tree, {"xsub": {}}, {"AAA": {"1D": 1.0}})
    tile = p["tiles"][0]
    assert tile["perf"] == {}                                    # no perf → empty, not None
    rows = {m["t"]: m["perf"] for m in tile["members"]}
    assert rows["AAA"] == {"1D": 1.0}
    assert rows["BBB"] == {}                                     # uncovered member still listed
    assert tile["size"] == 2                                     # floors at member count
    # unknown theme falls back to its own name for the zh label
    assert p["sectors"][0]["zh"] == "X"


def test_empty_inputs():
    p = th.build_themes_heatmap([], {}, {})
    assert p["n_tiles"] == 0 and p["sectors"] == [] and p["tiles"] == []
    assert p["map_type"] == "themes"


def _receipt(tree):
    return {"parser_version": "finviz_tree_refresh.v1", "promoted": True,
            "mode": "refresh", "error": None, "refusal_reasons": [],
            "asof": "2026-08-15", "refreshed_at_utc": "2026-08-15T02:01:34+00:00",
            "new_tree_sha256": hashlib.sha256(json.dumps(tree, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(),
            "counts": {"themes": 2, "subthemes": 3, "memberships": 7, "unique_tickers": 7}}


def _build(tree=None, receipt=None, generated="2026-10-10 14:38", member_perf=None):
    return th.build_themes_heatmap(_tree() if tree is None else tree,
        _sub_perf(), _mem_perf() if member_perf is None else member_perf,
        generated_utc=generated, asof="2026-10-09", membership_receipt=receipt)


def test_manifest_reconciles_input_and_keeps_unknown_distinct_from_missing_prices():
    p = _build(member_perf={"NVDA": {"1D": 0.0}})
    m = p["membership_manifest"]
    assert m["schema"] == "finviz.membership_manifest.v1"
    assert m["counts"] == {"themes": 2, "subthemes": 3, "appearances": 7, "distinct_tickers": 7}
    assert m["reconciliation"] == {"status": "conserved", "reasons": []}
    assert m["coverage"]["1D"] == {"measured_members": 1, "total_members": 7, "measured_groups": 3, "total_groups": 3}
    assert m["unpriced_members"] == 6
    assert p["n_members"] == 7
    for key in ("unresolved_identity_count", "source_declared_partial_groups", "source_declared_missing_groups"):
        assert m[key] is None
    assert m["membership"]["status"] == "unknown"
    assert m["membership"]["asof"] is None


@pytest.mark.parametrize("change", ["empty_theme", "empty_group", "duplicate_theme", "duplicate_group", "duplicate_member", "blank_member"])
def test_input_integrity_cannot_become_conserved(change):
    tree = _tree()
    if change == "empty_theme": tree[0].update(theme="", key="")
    if change == "empty_group": tree[0]["subsectors"][0]["key"] = ""
    if change == "duplicate_theme": tree.append(copy.deepcopy(tree[0]))
    if change == "duplicate_group": tree[0]["subsectors"].append(copy.deepcopy(tree[0]["subsectors"][0]))
    if change == "duplicate_member": tree[0]["subsectors"][0]["members"].append("NVDA")
    if change == "blank_member": tree[0]["subsectors"][0]["members"].append("")
    m = _build(tree)["membership_manifest"]
    assert m["reconciliation"]["status"] == "invalid"
    assert m["reconciliation"]["reasons"]


def test_receipt_clocks_are_membership_clocks_and_not_market_or_build_clocks():
    r = _receipt(_tree())
    a = _build(receipt=r)["membership_manifest"]
    b = _build(receipt=r, generated="2026-10-11 14:38")["membership_manifest"]
    assert a["membership"] == b["membership"]
    assert a["membership"]["status"] == "bound"
    assert a["membership"]["asof"] == "2026-08-15"
    assert a["tree_sha256"] == r["new_tree_sha256"]
    assert a["corrections"]["current_proposal_adjudication"] is None


@pytest.mark.parametrize("key,value", [
    ("promoted", False), ("promoted", 1), ("parser_version", "wrong"),
    ("new_tree_sha256", "0" * 64), ("asof", "2026-02-30"),
    ("asof", "2026-10-09"), ("refreshed_at_utc", "2026-08-15T02:01:34"),
    ("refreshed_at_utc", "2026-10-11T00:00:00Z"),
    ("refreshed_at_utc", "0001-01-01T00:00:00+01:00"),
    ("refreshed_at_utc", "9999-12-31T23:59:59-01:00"),
    ("error", "failed"), ("refusal_reasons", ["refused"]),
    ("counts", {"themes": True, "subthemes": 3, "memberships": 7, "unique_tickers": 7}),
])
def test_invalid_receipt_never_binds_membership(key, value):
    r = _receipt(_tree()); r[key] = value
    m = _build(receipt=r)["membership_manifest"]
    assert m["membership"]["status"] == "unknown"
    assert m["membership"]["asof"] is None
    assert m["membership"]["reason"]


def test_nonfinite_boolean_and_missing_values_are_not_measured():
    perf = {k: {"1D": v} for k, v in zip(["NVDA", "AMD", "MSFT", "GOOGL", "META", "V", "MA"],
                                        [True, None, float("nan"), float("inf"), "1", 0, -1])}
    m = _build(member_perf=perf)["membership_manifest"]
    assert m["coverage"]["1D"]["measured_members"] == 2
    assert m["unpriced_members"] == 5


def test_wrapper_selects_only_matching_past_receipt_by_embedded_clock(tmp_path):
    from scripts.build_themes_heatmap import select_membership_receipt
    good = _receipt(_tree()); newer = dict(good, refreshed_at_utc="2026-08-16T01:00:00Z")
    (tmp_path / "zzz.json").write_text(json.dumps(good))
    (tmp_path / "aaa.json").write_text(json.dumps(newer))
    (tmp_path / "future.json").write_text(json.dumps(dict(good, refreshed_at_utc="2027-01-01T00:00:00Z")))
    (tmp_path / "bad.json").write_text("{")
    (tmp_path / "linked.json").symlink_to(tmp_path / "future.json")
    selected = select_membership_receipt(tmp_path, _tree(), "2026-10-10 14:38")
    assert selected == newer
    assert select_membership_receipt(tmp_path / "absent", _tree(), "2026-10-10 14:38") is None
    assert select_membership_receipt(tmp_path, _tree(), "invalid") is None


def test_wrapper_refuses_ambiguous_json_receipt(tmp_path):
    from scripts.build_themes_heatmap import select_membership_receipt
    raw = json.dumps(_receipt(_tree()))
    (tmp_path / "ambiguous.json").write_text(raw.replace('"promoted": true', '"promoted": false, "promoted": true'))
    assert select_membership_receipt(tmp_path, _tree(), "2026-10-10 14:38") is None


def test_wrapper_writes_manifest_without_changing_market_payload(tmp_path, monkeypatch):
    from scripts import build_themes_heatmap as wrapper
    source = tmp_path / "data" / "themes_heatmap"
    source.mkdir(parents=True)
    (source / "themes_tree.json").write_text(json.dumps(_tree()))
    (source / "perf_snapshot.json").write_text(json.dumps({
        "asof": "2026-10-09", "subsector_perf": _sub_perf(), "member_perf": _mem_perf()}))
    receipts = source / "tree_refresh_receipts"
    receipts.mkdir()
    (receipts / "20260815.json").write_text(json.dumps(_receipt(_tree())))
    monkeypatch.setattr(wrapper.config, "data_dir", lambda: tmp_path / "data")
    p = wrapper.build(tmp_path / "site", generated_utc="2026-10-10 14:38")
    assert json.loads((tmp_path / "site/marketdata/themes_heatmap.json").read_text()) == p
    assert p["membership_manifest"]["membership"]["asof"] == "2026-08-15"
    assert p["asof"] == "2026-10-09"
    expected = _build()
    assert {k: v for k, v in p.items() if k != "membership_manifest"} == {
        k: v for k, v in expected.items() if k != "membership_manifest"}


def test_unrepresentable_metric_does_not_crash_accounting():
    p = _build(member_perf={"NVDA": {"1D": 10 ** 400}})
    assert p["membership_manifest"]["coverage"]["1D"]["measured_members"] == 0


@pytest.mark.parametrize("members", [False, 0, "", None])
def test_falsey_malformed_roster_is_not_conserved(members):
    tree = [{"theme": "Fixture", "subsectors": [{"key": "fixture", "members": members}]}]
    result = _build(tree)["membership_manifest"]["reconciliation"]
    assert result["status"] == "invalid"
    assert "invalid_member_collection" in result["reasons"]


def test_subtheme_identity_is_globally_unique_as_required_by_source_graph():
    tree = _tree()
    tree[1]["subsectors"][0]["key"] = tree[0]["subsectors"][0]["key"]
    result = _build(tree)["membership_manifest"]["reconciliation"]
    assert result["status"] == "invalid"
    assert "duplicate_subtheme" in result["reasons"]


def test_input_accounting_does_not_hide_a_dropped_invalid_member():
    tree = _tree()
    tree[0]["subsectors"][0]["members"].append("")
    p = _build(tree)
    assert p["n_members"] == 7
    assert p["membership_manifest"]["counts"]["appearances"] == 8
    assert p["membership_manifest"]["reconciliation"]["status"] == "invalid"


@pytest.mark.parametrize("tree", [[], [{"theme": "X", "subsectors": []}],
    [{"theme": "X", "subsectors": [{"key": "x", "members": []}]}]])
def test_incomplete_tree_cannot_bind_a_promoted_receipt(tree):
    r = _receipt(tree)
    r["counts"] = {"themes": len(tree), "subthemes": sum(len(t["subsectors"]) for t in tree),
                   "memberships": 0, "unique_tickers": 0}
    m = _build(tree, receipt=r)["membership_manifest"]
    assert m["reconciliation"]["status"] == "invalid"
    assert m["membership"]["status"] == "unknown"
