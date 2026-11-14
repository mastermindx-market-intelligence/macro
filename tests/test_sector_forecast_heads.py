"""Lane 8 v1.1 — per-head forecast capabilities and the Evaluation / Portfolio contracts.

Cited by name from research/sector_completion_20261021/B12_V11_HEADS_RESULTS.md. Inputs are
synthetic except the frozen-result parity test, which reads the committed result JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import engine.cycle_ontology as onto
import engine.sector_heads as sh

REPO = Path(__file__).resolve().parent.parent
RESULT = REPO / "research" / "sector_completion_20261021" / "b12" / "v11_heads_result.json"
_RESULT_KEY = {"remaining_return_distribution": "H1_remaining_return_distribution",
               "adverse_tail": "H2_adverse_tail",
               "target_before_invalidation": "H3_target_before_invalidation",
               "transition_time": "H4_transition_time"}


def _block(kind="sector", epoch=None, **kw):
    return sh.head_capabilities(record_kind=kind, turn_epoch=epoch, **kw)


def test_frozen_head_research_matches_the_committed_result():
    res = json.loads(RESULT.read_text())["heads"]
    for head, key in _RESULT_KEY.items():
        frozen = sh.HEAD_RESEARCH[head]
        assert frozen["disposition"] == res[key]["disposition"]
        assert frozen["reasons"] == res[key]["reasons"]
        assert frozen["skill"] == res[key]["skill"]
        assert frozen["ci90"] == res[key]["ci90"]


def test_protocol_epoch_is_the_v2_close_price_14pct_epoch():
    assert sh.PROTOCOL_EPOCH == onto.turn_epoch("close_price", 14.0)


def test_every_head_is_present_and_withheld_with_its_own_reason():
    b = _block(epoch=None)
    assert set(b["heads"]) == set(sh.HEADS)
    assert b["observed_cycles"] == "shown"
    for head, h in b["heads"].items():
        assert h["status"] == "withheld"
        assert h["reason_code"]
        assert h["horizon_sessions"] == 20
    _assert_no_number(b)


def _assert_no_number(obj, path="forecast_heads"):
    """No research statistic or forecast rides a record: the only number allowed in the
    block is the horizon length (independent review M2)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "horizon_sessions":
                continue
            _assert_no_number(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _assert_no_number(v, f"{path}[{i}]")
    else:
        assert isinstance(obj, (str, type(None))) or obj is False, f"number leaked at {path}: {obj!r}"


def test_failed_head_carries_research_failure_not_the_epoch_reason():
    b = _block(epoch=sh.PROTOCOL_EPOCH)
    for head, h in b["heads"].items():
        disp = sh.HEAD_RESEARCH[head]["disposition"]
        if disp == "QUALIFIED_RESEARCH":
            assert h["reason_code"] == "live_estimator_not_wired"
        else:
            assert h["reason_code"].startswith("research_")
            assert h["research_reasons"]


def test_live_legacy_epoch_withholds_research_qualified_heads_individually():
    b = _block(epoch=None)          # live records carry turn_knowledge.epoch = None (ZigZag v1)
    for head, h in b["heads"].items():
        if sh.HEAD_RESEARCH[head]["disposition"] == "QUALIFIED_RESEARCH":
            assert h["reason_code"] == "live_state_not_protocol_epoch"


def test_reconstructed_roster_records_withhold_every_head():
    # amalgam records are stamped while still kind="basket" (build_basket), then renamed
    b = _block(kind="basket", epoch=sh.PROTOCOL_EPOCH)
    assert {h["reason_code"] for h in b["heads"].values()} == {"membership_not_point_in_time"}


@pytest.mark.parametrize("kind", ["country", "cn_sector", "ndx", ""])
def test_other_record_kinds_are_not_evaluated_not_mislabelled(kind):
    b = _block(kind=kind, epoch=sh.PROTOCOL_EPOCH)
    assert {h["reason_code"] for h in b["heads"].values()} == {"record_kind_not_evaluated"}


def test_non_us_market_is_not_evaluated():
    b = _block(epoch=sh.PROTOCOL_EPOCH, market="HK")
    assert {h["reason_code"] for h in b["heads"].values()} == {"market_not_evaluated"}


@pytest.mark.parametrize("head", sh.HEADS)
def test_withdrawing_one_head_leaves_its_siblings_untouched(head):        # SP10
    b = _block(epoch=None)
    w = sh.withdraw(b, head, "qualification_withdrawn")
    assert w["heads"][head]["reason_code"] == "qualification_withdrawn"
    for other in sh.HEADS:
        if other != head:
            assert w["heads"][other] == b["heads"][other]
    assert w["observed_cycles"] == "shown"
    assert b["heads"][head]["reason_code"] != "qualification_withdrawn"   # original unchanged


def test_authority_flags_stay_false():
    b = _block(epoch=sh.PROTOCOL_EPOCH, live_estimator_wired=True)
    assert not any(b[k] for k in sh.AUTHORITY)
    assert all(h["status"] == "withheld" for h in b["heads"].values())


def test_live_sector_build_emits_forecast_heads_all_withheld():
    from engine import hazard_parity as hp
    tape = hp.synthetic_tape()
    rec = hp.live_record(tape, tape["index"][-1])
    fh = rec["forecast_heads"]
    assert fh["schema"] == sh.FORECAST_HEADS_SCHEMA
    assert all(h["status"] == "withheld" for h in fh["heads"].values())
    _assert_no_number(fh)
    json.dumps(fh)


# ── Evaluation / Portfolio contracts ─────────────────────────────────────────

def _valid_eval():
    comps = [{"id": cid, "status": "evaluated", "no_entry_periods": 0, "no_fill_signals": 0,
              "costs_paid_total": 0.0, "mean_invested": 1.0} for cid in sh.COMPARATOR_IDS[:3]]
    comps += [{"id": cid, "status": "unavailable", "reason": "no_pit_constituent_membership"}
              for cid in sh.COMPARATOR_IDS[3:]]
    return {"schema": "sector_intelligence.strategy_evaluation.v1",
            "view": "STRATEGY_EVALUATION_VIEW", "comparators": comps,
            "failed_leaders": {"n": 1}, "rebounds": {"n": 1},
            "exposure_matched_reference": {"invested_fraction": 1.0},
            "claims": {k: {"status": "not_established"} for k in sh.CLAIMS}}


def test_valid_evaluation_result_passes():
    assert sh.validate_evaluation_result(_valid_eval()) == []


def test_missing_comparator_or_unexplained_unavailable_is_rejected():
    r = _valid_eval()
    r["comparators"] = r["comparators"][:-1]
    r["comparators"][-1].pop("reason")
    errs = sh.validate_evaluation_result(r)
    assert "missing_comparator:C7_independent_emergence" in errs
    assert any(e.startswith("unavailable_without_reason") for e in errs)


def test_failed_leaders_rebounds_and_no_fill_cannot_be_dropped():          # SP22
    r = _valid_eval()
    r.pop("failed_leaders"); r.pop("rebounds")
    r["comparators"][0].pop("no_fill_signals")
    errs = sh.validate_evaluation_result(r)
    assert {"missing_failed_leaders", "missing_rebounds",
            "missing_no_fill_signals:C1_passive_market"} <= set(errs)


def test_alpha_or_skill_labels_and_true_authority_are_rejected():
    r = _valid_eval()
    r["comparators"][2]["estimated_alpha"] = 0.02
    r["may_trade"] = True
    errs = sh.validate_evaluation_result(r)
    assert "forbidden_label:estimated_alpha" in errs
    assert "authority_flag_true:may_trade" in errs


def test_selection_value_can_never_be_established_here():                 # SP19 / SP21
    r = _valid_eval()
    r["claims"]["incremental_selection_value"] = {"status": "established"}
    assert "selection_value_cannot_be_established_here" in sh.validate_evaluation_result(r)
    assert sh.selection_claim([-0.0173, 0.0059])["status"] == "not_established"
    pos = sh.selection_claim([0.001, 0.02])
    assert pos["status"] == "not_established" and "acceptance" in pos["basis"]
    assert sh.selection_claim(None)["status"] == "unavailable"


@pytest.mark.parametrize("den", [0.0, 0.004, -0.009])
def test_near_zero_benchmark_cannot_fake_capture(den):                    # SP20
    assert sh.capture_ratio(0.05, den) is None
    assert sh.capture_ratio(0.05, 0.10) == pytest.approx(0.5)


@pytest.mark.parametrize("req,reason", [
    ({"holdings_verified": False, "positions": [], "accounting_method": "m"},
     "holdings_not_verified"),
    ({"holdings_verified": True, "positions": None, "accounting_method": "m"},
     "positions_unknown"),
    ({"holdings_verified": True, "positions": [{"instrument": "XLK", "weight": None}],
      "accounting_method": "m"}, "weights_missing"),
    ({"holdings_verified": True, "positions": [{"instrument": "XLK", "weight": 0.5}]},
     "accounting_method_unnamed"),
])
def test_unknown_positions_or_weights_are_unavailable_never_zero(req, reason):   # SP20
    a = sh.attribution(req)
    assert a == {"status": "unavailable", "reason": reason}


def test_all_cash_attribution_is_explicit_not_missing():                  # SP20
    a = sh.attribution({"holdings_verified": True, "positions": [],
                        "accounting_method": "brinson_fachler_geometric_linking"})
    assert a["status"] == "computable" and a["invested_fraction"] == 0 and a["cash_fraction"] == 1
