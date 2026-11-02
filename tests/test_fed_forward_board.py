"""Per-contract evidence and the consumer's dated, accessible fallback."""
from copy import deepcopy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from engine.rates_inflation_command import _c0_board_generation, _c0_qualified_comparisons
from lib.fed_forward_board import fed_forward_board


TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


@pytest.fixture
def board(tmp_path):
    stamp = "2026-10-20"
    source = tmp_path / "bonds" / "bond_health.json"
    source.parent.mkdir()
    source.write_text("{}")
    observed = {"status": "comparable_after_transformation", "difference": -8.25,
                "rule_id": "zq_month_vs_policy_midpoint.v1", "unit": "bp",
                "left_ref": "contract-observation", "right_ref": "policy-observation",
                "left_cutoff": stamp, "right_cutoff": stamp}
    native = {"cutoff_effective": stamp, "months": [{
        "contract": "ZQZ26", "reference_start": "2026-12-01", "reference_end": "2026-12-31",
        "monthly_average": {"obs_id": "contract-observation", "observation_time": stamp},
        "vs_target_midpoint": observed}]}
    fed = {"implied_source_meta": {"effr_meeting_path": native},
           "effr_meeting_path": {"months": [], "cutoff_effective": "old"}}
    basis = {"value_state": "present", "rate_index": "EFFR", "source": "rate_futures:ZQ",
             "target": "effr_monthly_average", "cutoff": stamp}
    common = dict(fed_path=fed, inflation_lenses_block=None, cutoff=stamp,
                  build_time_fallback=False)
    comparisons = _c0_qualified_comparisons(**common, data_dir=tmp_path)
    generation = _c0_board_generation(**common, d1_content_ref=comparisons[0]["content_ref"],
                                      i0_content_ref=None, rate_path_basis=basis)
    return {"asof": stamp, "qualified_comparisons": comparisons, "board_generation": generation,
            "board": {"rate_path_row": {"basis": basis, "gap": {"gap_bp": -999}}},
            "expectations_pressure": {"ease_score": 2, "hawk_score": 0,
                                      "legs": [{"key": "E1_equity_deleveraging", "active": True, "weight": 2}]}}


def render(view):
    return Environment(loader=FileSystemLoader(TEMPLATES)).get_template(
        "_fed_forward_board.html.j2").render(fed_forward=view)


def test_canonical_nested_contract_and_its_cutoff_reach_the_board(board):
    view = fed_forward_board(board)
    assert view["months"] == [{"month": "2026-12", "contract": "ZQZ26", "bp": -8.25, "cutoff": "2026-10-20", "observed": "2026-10-20"}]
    assert "/implied_source_meta/effr_meeting_path/months/0/vs_target_midpoint" in board["qualified_comparisons"][0]["input_id"]
    assert view["sides"][0]["score"] == 2 and len(view["sides"][0]["active"]) == 1
    page = render(view)
    assert "ZQZ26" in page and "-8.25" in page and "-999" not in page


@pytest.mark.parametrize("patch", [
    {"status": "not_comparable"}, {"component": "i0"}, {"rule_id": "sep_vs_market_year_end.v1"},
    {"unit": "pct_ann_rate"}, {"difference": False}, {"difference": float("nan")},
    {"difference": float("inf")}, {"reference_end": "2026-12-30"}, {"contract": None},
    {"input_id": "elsewhere/months/0"}, {"cutoff": "2026-10-22"}, {"content_ref": "stale"}, {"left_cutoff": "2026-11-01"}, {"quote_observed": "2026-11-01"},
])
def test_rejected_rows_never_release_a_graph_or_an_unrelated_gap(board, patch):
    board["qualified_comparisons"][0].update(patch)
    page = render(fed_forward_board(board))
    assert "Awaiting comparable contracts" in page
    assert "ff-chart-title" not in page and "-999" not in page


def test_duplicate_month_or_absent_basis_withholds_comparison(board):
    duplicate = deepcopy(board["qualified_comparisons"][0])
    duplicate["difference"] = 25
    board["qualified_comparisons"].append(duplicate)
    assert not fed_forward_board(board)["months"]
    board["qualified_comparisons"].pop()
    board["board"]["rate_path_row"]["basis"] = None
    assert not fed_forward_board(board)["months"]


def test_absent_pressure_preserves_dated_independent_market_and_escapes_evidence():
    old = {"asof":"2026-09-01", "events":[{"label_en":"Next decision", "label_zh":"下次决议",
           "outcomes":[{"outcome":"<img src=x>", "prob":0, "chg_pp":-1.3},
                       {"outcome":"bad", "prob":101}]}]}
    page = render(fed_forward_board(None, old))
    assert "No reading" in page and "2026-09-01" in page and "0.0%" in page
    assert "-1.3" in page and "&lt;img src=x&gt;" in page and "<img src=x>" not in page


def test_archived_board_recovers_only_the_exact_dated_input(board, tmp_path):
    import hashlib
    import json

    cmp = board["qualified_comparisons"][0]
    old_pointer = "data/bonds/bond_health.json#/fed_path/effr_meeting_path"
    month = {key: cmp[key] for key in ("reference_start", "reference_end", "contract")}
    month["vs_target_midpoint"] = {key: cmp[key] for key in (
        "status", "difference", "rule_id", "unit", "left_ref", "right_ref", "left_cutoff", "right_cutoff")}
    block = {"cutoff_effective": cmp["cutoff"], "months": [month]}
    bond = tmp_path / "bond.json"
    bond.write_text(json.dumps({"fed_path": {"asof": board["asof"],
                    "implied_source_meta": {"effr_meeting_path": block}}}))
    board["board"]["rate_path_row"]["asof"] = board["asof"]
    board["qualified_comparisons"] = []
    board["board_generation"]["components"]["d1"] = {
        "input_id": old_pointer, "state": "missing", "cutoff": None,
        "content_ref": hashlib.sha256(bond.read_bytes()).hexdigest()}
    unchanged = deepcopy(board)
    assert fed_forward_board(board, bond_file=bond)["months"][0]["bp"] == -8.25
    assert board == unchanged
    bond.write_text(bond.read_text() + " ")
    assert fed_forward_board(board, bond_file=bond)["months"] == []
