"""INTL-GS §14 graph-boundary label rule (ORCH-5 SPEC_A1 part A).

An out-of-graph market displays structural research or a qualified candidate
label, never an invented graph score. Every fixture feeds a REAL
``engine.intl_transmission_evidence.market_summary`` receipt through
``graph_boundary_label``; nothing here invents a summary by hand. Fixture
helpers are copied from the IM17/IM15 suites' shapes, never imported from a
test module.
"""
import copy
import hashlib
import json
from datetime import date, timedelta

import pytest

import engine.intl_transmission_evidence as te
from engine.intl_global_graph_boundary import (
    CONTRACT_VERSION,
    GraphBoundaryError,
    graph_boundary_label,
)

COMPUTED_AT = "2026-10-09T20:30:00+00:00"
BASE_END = date(2026, 10, 7)

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"


# --------------------------------------------------------------------------
# Fixtures (shapes copied from tests/test_intl_transmission_evidence.py and
# tests/test_intl_global_dislocation.py — copied, never imported)
# --------------------------------------------------------------------------

def doc_edge(origin="BR", **kw):
    base = dict(
        origin_market=origin, receiver="us_broad_equity",
        channel="dollar_funding", pathway="documented_exposure",
        model_status="documented_source", source_id="bis.statistics",
        measure_id="cross_border_usd_claims", units="usd_bn",
        interpretation_en="Cross-border USD claims of reporting banks on the market.",
        interpretation_zh="报告银行对该市场的跨境美元债权。",
        evidence_family="funding", as_of="2026-09-30",
        denominator="reporting_bank_usd_claims",
        exposure_kind="direct_financial_claims", amount=12.5)
    base.update(kw)
    return te.build_edge(**base)


def dy_edge(origin="BR", **kw):
    base = dict(
        origin_market=origin, receiver="us_broad_equity",
        channel="portfolio_fund_ownership", pathway="statistical_association",
        model_status="statistical_estimate_frozen",
        source_id="contagion_dy_var_14etf", measure_id="gfevd_to_us",
        units="share",
        interpretation_en="Frozen 14-ETF connectedness estimate of association with the US market.",
        interpretation_zh="冻结的14只ETF关联度估计。",
        evidence_family="equity", direction="down",
        direction_support="statistical_candidate",
        coverage_state="qualified", coverage_basis="synthetic fixture")
    base.update(kw)
    return te.build_edge(**base)


def _month(k: int) -> date:
    total = BASE_END.year * 12 + BASE_END.month - 1 - k
    return date(total // 12, total % 12 + 1, BASE_END.day)


def _clocks(k: int) -> dict:
    stamp = f"{_month(k) + timedelta(days=2)}T15:00:00+00:00"
    return {
        "observation": {"at": f"{_month(k)}T00:00:00", "precision": "session_date"},
        "source_publication": {"at": stamp, "precision": "exact"},
        "ingestion": {"at": stamp, "precision": "exact"},
        "computation": {"at": stamp, "precision": "exact"},
    }


def _observation(market_id: str = "JP", k: int = 0, *, tag: str = "") -> dict:
    from engine.intl_global_observation import build_observation
    identity = {
        "universe_id": market_id, "market_id": market_id,
        "index_id": f"^T{market_id}", "fx_id": f"{market_id}FX=X",
        "horizon": "1m", "currency_basis": "usd_unhedged",
        "return_basis": "price",
        "window_start": f"{_month(k + 1)}T00:00:00",
        "window_end": f"{_month(k)}T00:00:00",
        "source_content_sha256": hashlib.sha256(
            f"{market_id}:{k}:{tag}".encode()).hexdigest(),
    }
    return build_observation(
        identity=identity, clocks=_clocks(k),
        values={"local_pct": -4.0, "fx_pct": -1.0, "usd_pct": -4.96},
        rights=dict(RIGHTS), incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def summary(market_id, edges=(), observations=()):
    return te.market_summary(market_id, edges=list(edges),
                             observations=list(observations))


def summary_with_qualified_observation(market_id: str = "DE"):
    """A real out-of-graph market_summary receipt carrying one real id.

    ``build_observation``'s legacy identity map mints ids only for the seven
    legacy markets — every one a structural-graph member today — so an
    out-of-graph summary with a qualified observation cannot be produced
    end-to-end yet. The seeded id is a real ``build_observation`` id; the
    guard it exercises (qualified observations never promote a market to a
    candidate) is the §14 rule pinned here ahead of that widening.
    """
    obs = _observation("JP", 0)
    assert obs["state"] == "qualified"
    ms = summary(market_id, observations=[obs])
    assert ms["qualified_observations"]["observation_ids"] == []
    ms["qualified_observations"]["observation_ids"] = [obs["observation_id"]]
    return ms


OUTPUT_KEYS = {"contract_version", "market_id", "label", "label_en", "label_zh",
               "graph_member", "structural_version", "candidate_basis",
               "reasons", "has_qualified_observations", "interpretation_limits"}

LABEL_TEXT = {
    "structural_graph_member": ("In structural graph", "结构图成员"),
    "qualified_candidate": ("Qualified candidate, outside structural graph",
                            "合格候选（结构图外）"),
    "structural_research": ("Structural research only", "仅结构研究"),
}


def _numeric_paths(node, prefix=""):
    """Dotted paths of every bare int/float value (bools are flags, not numbers)."""
    found = []
    if isinstance(node, dict):
        for key, val in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.extend(_numeric_paths(val, path))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_numeric_paths(item, f"{prefix}.{i}" if prefix else str(i)))
    elif isinstance(node, bool):
        pass
    elif isinstance(node, (int, float)):
        found.append(prefix)
    return found


# --------------------------------------------------------------------------
# Label rule over real market_summary receipts
# --------------------------------------------------------------------------

def test_graph_member_market_labels_as_in_structural_graph():
    ms = summary("JP")
    out = graph_boundary_label(ms)
    assert set(out) == OUTPUT_KEYS
    assert out["contract_version"] == CONTRACT_VERSION
    assert out["market_id"] == "JP"
    assert out["label"] == "structural_graph_member"
    assert out["label_en"] == "In structural graph"
    assert out["label_zh"] == "结构图成员"
    assert out["graph_member"] is True
    assert out["structural_version"] == ms["structural_graph"]["structural_version"]
    assert out["candidate_basis"] == []
    assert out["reasons"] == []
    assert out["has_qualified_observations"] is False


def test_member_label_wins_over_candidate_evidence():
    # First match wins: a graph member carrying a statistical_association edge
    # is still labelled by membership, never as an outside candidate.
    ms = summary("JP", edges=[dy_edge(origin="JP")])
    out = graph_boundary_label(ms)
    assert out["label"] == "structural_graph_member"
    assert out["label_en"] == LABEL_TEXT["structural_graph_member"][0]
    assert out["label_zh"] == LABEL_TEXT["structural_graph_member"][1]
    assert out["graph_member"] is True
    assert out["candidate_basis"] == []


def test_out_of_graph_market_with_statistical_edge_is_qualified_candidate():
    dy = dy_edge(origin="BR")
    ms = summary("BR", edges=[dy])
    out = graph_boundary_label(ms)
    assert out["label"] == "qualified_candidate"
    assert out["label_en"] == "Qualified candidate, outside structural graph"
    assert out["label_zh"] == "合格候选（结构图外）"
    assert out["graph_member"] is False
    assert out["structural_version"] == ms["structural_graph"]["structural_version"]
    assert out["candidate_basis"] == [{"edge_id": dy["edge_id"],
                                       "model_status": dy["model_status"]}]
    assert out["reasons"] == []


def test_candidate_basis_is_sorted_by_edge_id_and_carries_only_two_keys():
    wide = dy_edge(origin="BR", receiver="us_credit")
    broad = dy_edge(origin="BR", receiver="us_broad_equity")
    assert wide["edge_id"] != broad["edge_id"]
    constructed = [broad, wide]  # deliberately not in edge_id order
    ms = summary("BR", edges=constructed)
    out = graph_boundary_label(ms)
    assert [item["edge_id"] for item in out["candidate_basis"]] == \
        sorted(item["edge_id"] for item in
               (wide, broad))
    for item in out["candidate_basis"]:
        assert set(item) == {"edge_id", "model_status"}
        assert item["model_status"] == "statistical_estimate_frozen"


def test_candidate_basis_two_channel_fixture_pins_ascending_edge_id_order():
    # Two statistical edges on TWO channels (portfolio_fund_ownership and
    # dollar_funding), offered deliberately in DESCENDING edge_id order: the
    # basis must come back ascending by edge_id whatever the input order or
    # channel mix (kills survivor M1 — a stable sort on the shared
    # model_status would preserve the descending input order here).
    portfolio = dy_edge(origin="BR", receiver="us_broad_equity")
    funding = dy_edge(origin="BR", receiver="us_broad_equity",
                      channel="dollar_funding")
    assert portfolio["channel"] == "portfolio_fund_ownership"
    assert funding["channel"] == "dollar_funding"
    ascending = sorted((portfolio["edge_id"], funding["edge_id"]))
    assert len(set(ascending)) == 2
    by_id = {edge["edge_id"]: edge for edge in (portfolio, funding)}
    offered = [by_id[ascending[1]], by_id[ascending[0]]]  # descending order
    assert [edge["edge_id"] for edge in offered] == ascending[::-1]
    out = graph_boundary_label(summary("BR", edges=offered))
    assert [item["edge_id"] for item in out["candidate_basis"]] == ascending
    assert {item["model_status"] for item in out["candidate_basis"]} == \
        {"statistical_estimate_frozen"}


def test_out_of_graph_market_with_only_documented_edges_is_structural_research():
    ms = summary("BR", edges=[doc_edge(origin="BR")])
    out = graph_boundary_label(ms)
    assert out["label"] == "structural_research"
    assert out["label_en"] == "Structural research only"
    assert out["label_zh"] == "仅结构研究"
    assert out["graph_member"] is False
    assert out["candidate_basis"] == []
    assert out["reasons"] == ["no_candidate_evidence"]


def test_out_of_graph_market_with_nothing_is_research_with_both_reasons():
    ms = summary("DE")
    out = graph_boundary_label(ms)
    assert out["label"] == "structural_research"
    assert out["label_en"] == LABEL_TEXT["structural_research"][0]
    assert out["label_zh"] == LABEL_TEXT["structural_research"][1]
    assert out["graph_member"] is False
    assert out["candidate_basis"] == []
    # Order is pinned: no_candidate_evidence first, no_structural_research second.
    assert out["reasons"] == ["no_candidate_evidence", "no_structural_research"]


def test_qualified_observations_never_promote_to_candidate():
    # Qualified observations are observations, not a model: an out-of-graph
    # market holding one and no statistical evidence stays structural research.
    ms = summary_with_qualified_observation("DE")
    out = graph_boundary_label(ms)
    assert out["label"] == "structural_research"
    assert out["label_en"] == "Structural research only"
    assert out["candidate_basis"] == []
    assert out["reasons"] == ["no_candidate_evidence", "no_structural_research"]
    assert out["has_qualified_observations"] is True


def test_has_qualified_observations_follows_observation_ids():
    member_with_obs = summary("JP", observations=[_observation("JP", 0)])
    assert member_with_obs["qualified_observations"]["observation_ids"]
    out = graph_boundary_label(member_with_obs)
    assert out["has_qualified_observations"] is True
    assert out["label"] == "structural_graph_member"  # unaffected by the obs
    empty = graph_boundary_label(summary("BR"))
    assert empty["has_qualified_observations"] is False


# --------------------------------------------------------------------------
# Honesty scans: no forbidden keys, no causal language, no invented numbers
# --------------------------------------------------------------------------

@pytest.mark.parametrize("case", [
    "jp_member", "jp_member_with_statistical_edge", "br_candidate",
    "br_documented_only", "de_nothing", "de_with_qualified_observation",
])
def test_output_scans_clean_and_carries_no_numeric_values(case):
    receipts = {
        "jp_member": lambda: summary("JP"),
        "jp_member_with_statistical_edge": lambda: summary(
            "JP", edges=[dy_edge(origin="JP")]),
        "br_candidate": lambda: summary("BR", edges=[dy_edge(origin="BR")]),
        "br_documented_only": lambda: summary("BR", edges=[doc_edge(origin="BR")]),
        "de_nothing": lambda: summary("DE"),
        "de_with_qualified_observation": summary_with_qualified_observation,
    }
    ms = receipts[case]()
    out = graph_boundary_label(ms)
    assert te.forbidden_keys(out) == []
    assert te.scan_causal_language(out) == []
    # No numeric value anywhere: ids and versions are strings; the only
    # booleans are the two closed flags. Edge ids may contain digits as text.
    assert _numeric_paths(out) == []
    assert out["label"] in LABEL_TEXT
    assert (out["label_en"], out["label_zh"]) == LABEL_TEXT[out["label"]]
    assert isinstance(out["interpretation_limits"], list)
    assert out["interpretation_limits"]
    assert all(isinstance(line, str) and line
               for line in out["interpretation_limits"])
    assert _numeric_paths(out["interpretation_limits"]) == []


def test_input_summary_is_never_mutated():
    for ms in (summary("JP"), summary("BR", edges=[dy_edge(origin="BR")]),
               summary("JP", observations=[_observation("JP", 0)]),
               summary_with_qualified_observation("DE")):
        before = copy.deepcopy(ms)
        graph_boundary_label(ms)
        assert ms == before
        assert json.dumps(ms, sort_keys=True) == json.dumps(before,
                                                            sort_keys=True)


def test_graph_boundary_module_declares_closed_contract_version():
    assert CONTRACT_VERSION == "intl-global-graph-boundary-v1"
    assert issubclass(GraphBoundaryError, ValueError)


# --------------------------------------------------------------------------
# Shape gate
# --------------------------------------------------------------------------

def test_missing_structural_graph_or_market_id_is_summary_shape_error():
    with pytest.raises(GraphBoundaryError, match="summary_shape"):
        graph_boundary_label({})
    with pytest.raises(GraphBoundaryError, match="summary_shape"):
        graph_boundary_label({"market_id": "JP"})
    with pytest.raises(GraphBoundaryError, match="summary_shape"):
        graph_boundary_label({"structural_graph": {"member": True}})
    with pytest.raises(GraphBoundaryError, match="summary_shape"):
        graph_boundary_label(None)


@pytest.mark.parametrize("structural_graph", [None, [], "frozen-v1", 7])
def test_non_dict_structural_graph_is_summary_shape_error(structural_graph):
    # Kills survivor M5: a gate that only rejects a None/absent
    # structural_graph would let a non-dict value reach the label rule and
    # invent a label instead of raising summary_shape. The None case carries
    # the key explicitly, which the absent-key cases above never exercise.
    with pytest.raises(GraphBoundaryError, match="summary_shape"):
        graph_boundary_label({"market_id": "JP",
                              "structural_graph": structural_graph})
