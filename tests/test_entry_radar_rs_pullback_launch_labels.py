"""Synthetic label conformance. No market rows, source publication or ledger writes."""
from __future__ import annotations
import copy
from datetime import timedelta
import pytest
from engine.entry_radar.replay import rs_pullback_launch_labels as labels
from engine.entry_radar.replay import rs_pullback_launch_data as owner
from tests import test_entry_radar_rs_pullback_phase1 as f

DECISION="2026-10-06T14:00:00Z"
ENTRY="2026-10-06T14:01:00Z"
EVAL="2026-10-06T16:02:00Z"


def fixture(decision=DECISION, closing="2026-10-06T20:00:00Z"):
    b=f.fixture(candidates=[f.candidate(decision=decision)],closing=closing)
    for r in b["minutes"]:
        if r["stream"]=="stock" and f.clock(r["start"])>=f.clock(ENTRY):
            r.update(open=100.,high=100.1,low=99.9,close=100.)
    scales={"earlier":f.receipt(value=1.,kind="true_range_wilder_atr14_30m",
        basis_id="fixture-unadjusted",origin_at="2026-10-06T13:59:00Z",
        known_at="2026-10-06T13:58:00Z",asof_end="2026-10-06T13:30:00Z")}
    return b,scales


def at(b,offset=0):
    t=f.clock(ENTRY)+timedelta(minutes=offset)
    return f.minute(b,f.iso(t))


def read(b,scales,evaluation_at=EVAL):
    p=labels.build_label_panel(b,scales,evaluation_at)
    assert p["population_count"]==p["retained_count"]==len(b["candidates"])
    assert p["status"]=="SYNTHETIC_LABEL_CONFORMANCE_ONLY"
    assert p["market_experiment_enrolled"] is False
    assert not any(p["authority"].values())
    return p["frames"][0]


def test_complete_neither_is_nonlaunch_not_missing():
    b,s=fixture();o=read(b,s)
    assert o["entry_start"]==ENTRY and o["label_end"]=="2026-10-06T16:01:00Z"
    assert o["observed_minutes"]==o["expected_minutes"]==120
    assert o["path_state"]=="NEITHER_BY_HORIZON"
    assert o["launch"] is False and o["low_in"] is True
    assert o["mae_atr"]==pytest.approx(.1) and o["mfe_atr"]==pytest.approx(.1)
    assert o["primary_eligible"] is True and o["entry_price"]==100.


def test_upper_first_survives_later_failure_but_lowin_does_not():
    b,s=fixture();at(b,1).update(high=101.2,close=101.)
    at(b,2).update(low=99.4,close=99.6)
    o=read(b,s)
    assert o["path_state"]=="UPPER_FIRST" and o["launch"] is True
    assert o["low_in"] is False
    assert o["first_event_interval_start"]=="2026-10-06T14:02:00Z"
    assert o["first_event_interval_end"]=="2026-10-06T14:03:00Z"
    assert o["first_event_known_at"]=="2026-10-06T14:03:00Z"


def test_lower_first_is_competing_failure_not_censoring():
    b,s=fixture();at(b,1).update(low=99.5,close=99.6)
    at(b,2).update(high=101.3,close=101.1)
    o=read(b,s)
    assert o["path_state"]=="LOWER_FIRST" and o["launch"] is False
    assert o["low_in"] is False


def test_same_bar_both_hits_retains_ambiguity():
    b,s=fixture();at(b,1).update(high=101.,low=99.5)
    o=read(b,s)
    assert o["path_state"]=="ORDER_AMBIGUOUS" and o["launch"] is None
    assert o["low_in"] is False
    assert o["first_event_order_basis"]=="BOTH_BARRIERS_WITH_OPEN_INSIDE"


@pytest.mark.parametrize("op,state",[(101.,"UPPER_FIRST"),(99.5,"LOWER_FIRST")])
def test_reported_open_resolves_same_minute_order(op,state):
    b,s=fixture();at(b,1).update(open=op,high=101.2,low=99.4)
    o=read(b,s)
    assert o["path_state"]==state and o["launch"] is (state=="UPPER_FIRST")
    assert o["first_event_order_basis"]=="REPORTED_OPEN"


def test_missing_before_hit_blocks_order_even_with_later_clear_hit():
    b,s=fixture();b["minutes"].remove(at(b,1));at(b,2).update(high=101.1)
    o=read(b,s)
    assert o["path_state"]=="PATH_UNKNOWN" and o["launch"] is None
    assert o["low_in"] is None and o["mae_atr"] is None
    assert o["observed_minutes"]==119


def test_missing_after_upper_does_not_erase_observed_first_event():
    b,s=fixture();at(b,1).update(high=101.1);b["minutes"].remove(at(b,2))
    o=read(b,s)
    assert o["path_state"]=="UPPER_FIRST" and o["launch"] is True
    assert o["low_in"] is None and o["mfe_atr"] is None


def test_partial_path_can_falsify_lowin_but_not_prove_it():
    b,s=fixture();b["minutes"].remove(at(b,1));at(b,2).update(low=99.7)
    o=read(b,s)
    assert o["path_state"]=="PATH_UNKNOWN" and o["low_in"] is False
    assert o["mae_atr"] is None


def test_missing_entry_does_not_select_next_available_open():
    b,s=fixture();b["minutes"].remove(at(b,0));o=read(b,s)
    assert o["path_state"]=="ENTRY_UNAVAILABLE"
    assert o["entry_price"] is None and o["launch"] is None


@pytest.mark.parametrize("decision",["2026-10-06T14:00:00Z","2026-10-06T14:00:00.000001Z","2026-10-06T14:00:59.999999Z"])
def test_reference_open_is_strictly_after_issue(decision):
    b,s=fixture(decision);assert read(b,s)["entry_start"]==ENTRY


def test_issue_at_next_exact_minute_needs_following_open():
    b,s=fixture("2026-10-06T14:01:00Z");o=read(b,s)
    assert o["entry_start"]=="2026-10-06T14:02:00Z"
    assert o["label_end"]=="2026-10-06T16:02:00Z"


def test_one_minute_short_is_remainder_not_a_full_horizon():
    b,s=fixture(closing="2026-10-06T16:00:00Z");at(b,1).update(high=101.1)
    o=read(b,s)
    assert o["expected_minutes"]==119 and o["primary_eligible"] is False
    assert o["path_state"]=="UPPER_FIRST"
    assert o["launch"] is None and o["low_in"] is None
    assert o["label_scope"]=="SESSION_REMAINDER_ONLY"


def test_exactly_enough_session_time_is_primary_eligible():
    b,s=fixture(closing="2026-10-06T16:01:00Z");o=read(b,s)
    assert o["primary_eligible"] is True and o["launch"] is False


def test_no_reference_open_after_close():
    b,s=fixture("2026-10-06T20:00:00Z");o=read(b,s,"2026-10-06T20:02:00Z")
    assert o["path_state"]=="NO_SESSION_ENTRY" and o["expected_minutes"]==0
    assert o["launch"] is None


def test_future_correction_cannot_rewrite_earlier_label_snapshot():
    b,s=fixture();original=read(b,s)
    later=copy.deepcopy(at(b,1));later.update(high=104.,revision_id="v2",known_at="2026-10-06T17:00:00Z")
    b["minutes"].append(later)
    assert read(b,s)==original
    assert read(b,s,"2026-10-06T17:00:00Z")["launch"] is True


def test_prefix_receipt_time_delays_first_event_knowability():
    b,s=fixture();at(b,1).update(known_at="2026-10-06T15:00:00Z")
    at(b,2).update(high=101.1)
    assert read(b,s,"2026-10-06T14:30:00Z")["path_state"]=="PATH_UNKNOWN"
    o=read(b,s);assert o["launch"] is True
    assert o["first_event_known_at"]=="2026-10-06T15:00:00Z"


def test_evaluation_before_issue_retains_candidate_as_unavailable():
    b,s=fixture();o=read(b,s,"2026-10-06T13:59:00Z")
    assert o["path_state"]=="EVALUATION_BEFORE_DECISION"


def test_actual_clock_does_not_reuse_newer_incumbent_for_old_issue():
    b,s=fixture();base=read(b,s)
    new=copy.deepcopy(next(x for x in b["contexts"] if x["kind"]=="incumbent"))
    new["known_at"]="2026-10-06T14:10:00Z";new["payload"]["assessment"]={"changed":True}
    b["contexts"].append(new);assert read(b,s)==base


def test_original_ineligible_is_not_silently_scored():
    b,s=fixture();b["contexts"][0]["payload"]["is_leader"]=False
    o=read(b,s);assert o["path_state"]=="NOT_ELIGIBLE" and o["launch"] is None


def test_missing_issue_context_is_not_repaired_by_future_data():
    b,s=fixture();b["contexts"]=[x for x in b["contexts"] if x["kind"]!="daily"]
    o=read(b,s);assert o["path_state"]=="INPUT_UNAVAILABLE" and o["launch"] is None


@pytest.mark.parametrize("field,value",[("value",0),("value",float("nan")),("value",True),
    ("basis_id","wrong"),("kind","close_proxy"),("known_at","2026-10-06T14:01:00Z"),
    ("origin_at","2026-10-06T14:01:00Z"),("asof_end","2026-10-06T13:59:00Z"),
    ("receipt_sha256","wrong")])
def test_scale_not_frozen_correctly_retains_unscored_row(field,value):
    b,s=fixture();s["earlier"][field]=value;o=read(b,s)
    assert o["path_state"]=="SCALE_UNAVAILABLE" and o["launch"] is None


def test_original_terminal_basis_refusal_stays_effective():
    b,s=fixture();at(b,1)["source_ref"]="terminal-minute-capture:observed"
    o=read(b,s);assert o["path_state"]=="PATH_UNKNOWN"
    assert any("TERMINAL_BASIS_UNPROVEN" in x for x in o["refusals"])


def test_future_minute_identity_or_basis_mismatch_is_not_filled():
    b,s=fixture();at(b,1)["basis_id"]="other";o=read(b,s)
    assert o["observed_minutes"]==119 and o["launch"] is None


def test_conflicting_latest_revision_refuses():
    b,s=fixture();dupe=copy.deepcopy(at(b,1));dupe["high"]=101.2;b["minutes"].append(dupe)
    o=read(b,s);assert o["path_state"]=="PATH_UNKNOWN"
    assert any("CONFLICTING_MINUTE_REVISION" in x for x in o["refusals"])


def test_malformed_ohlc_remains_unknown_not_an_imagined_touch():
    b,s=fixture();at(b,1).update(low=102.,high=101.);o=read(b,s)
    assert o["path_state"]=="PATH_UNKNOWN" and o["launch"] is None


def test_lowin_equality_is_included():
    b,s=fixture();at(b,1)["low"]=99.75;assert read(b,s)["low_in"] is True
    at(b,1)["low"]=99.749;assert read(b,s)["low_in"] is False


def test_all_candidates_are_retained_and_duplicate_scale_is_not_borrowed():
    b,s=fixture();b["candidates"].append(f.candidate("missing_scale"))
    p=labels.build_label_panel(b,s,EVAL)
    assert p["retained_count"]==2
    assert p["frames"][1]["path_state"]=="SCALE_UNAVAILABLE"


def test_input_objects_and_daily_api_are_unchanged():
    b,s=fixture();before=copy.deepcopy((b,s));panel=owner.build_input_panel(b)
    read(b,s)
    assert (b,s)==before and owner.build_input_panel(b)==panel


def test_observed_market_cannot_be_enrolled_by_this_conformance_api():
    b,s=fixture();b["input_kind"]="OBSERVED_MARKET"
    with pytest.raises(owner.InputContractError,match="not enrolled"):
        labels.build_label_panel(b,s,EVAL)


def test_ohlc_inferred_order_matches_all_compatible_finite_trade_paths():
    # Independent path enumeration: 5**4 actual four-print paths collapsed to OHLC.
    from itertools import product
    grouped={}
    for path in product((99.4,99.6,100.,100.5,101.1),repeat=4):
        key=(path[0],max(path),min(path),path[-1])
        first=next(("UPPER_FIRST" if p>=101. else "LOWER_FIRST"
                    for p in path if p>=101. or p<=99.5),None)
        grouped.setdefault(key,set()).add(first)
    assert len(grouped)>100
    for (op,hi,lo,cl),possible in grouped.items():
        result,_=labels._event({"ohlcv":dict(open=op,high=hi,low=lo,close=cl)},101.,99.5)
        if result=="ORDER_AMBIGUOUS":
            assert possible=={"UPPER_FIRST","LOWER_FIRST"}
        else:
            assert possible=={result}


def test_future_malformed_payload_does_not_change_earlier_snapshot():
    b,s=fixture();original=read(b,s)
    later=copy.deepcopy(at(b,1));later.update(high=-1,low=None,volume="bad",
        known_at="2026-10-06T17:00:00Z",revision_id="broken-future")
    b["minutes"].append(later);assert read(b,s)==original
    assert read(b,s,"2026-10-06T17:00:00Z")["path_state"]=="PATH_UNKNOWN"


def test_hidden_later_ohlc_never_proves_an_early_outcome():
    b,s=fixture();at(b,1).update(high=101.1,known_at="2026-10-06T17:00:00Z")
    o=read(b,s)
    assert o["launch"] is None and o["path_state"]=="PATH_UNKNOWN"


def test_known_scale_cannot_claim_availability_before_its_bar_ends():
    b,s=fixture();s["earlier"]["known_at"]="2026-10-06T13:29:59Z"
    assert read(b,s)["path_state"]=="SCALE_UNAVAILABLE"


def test_nonpositive_lower_barrier_is_refused():
    b,s=fixture();s["earlier"]["value"]=250.
    assert read(b,s)["path_state"]=="SCALE_UNAVAILABLE"


def test_alien_scale_identity_cannot_be_silently_ignored():
    b,s=fixture();s["other"]=copy.deepcopy(s["earlier"])
    with pytest.raises(owner.InputContractError,match="undeclared candidate"):
        labels.build_label_panel(b,s,EVAL)


def test_late_volume_and_corrupt_known_clock_still_use_native_refusals():
    b,s=fixture();at(b,1)["volume"]=None
    assert read(b,s)["path_state"]=="PATH_UNKNOWN"
    b,s=fixture();at(b,1)["known_at"]="2026-10-06T14:01:30Z"
    o=read(b,s);assert any("MINUTE_CLOCK_VIOLATION" in x for x in o["refusals"])


def test_no_side_effect_systems_are_imported():
    import ast,inspect
    tree=ast.parse(inspect.getsource(labels))
    imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
    roots=set()
    for n in imports:
        if isinstance(n,ast.Import): roots.update(a.name.split(".")[0] for a in n.names)
        else: roots.add((n.module or "").split(".")[0])
    assert roots=={"__future__","math","re","datetime","typing","engine"}


@pytest.mark.parametrize("location",["evaluation","issue","minute_known","minute_start","scale"])
def test_submicrosecond_clock_is_refused_instead_of_rounded_into_availability(location):
    b,s=fixture();evaluation=EVAL
    if location=="evaluation": evaluation="2026-10-06T16:02:00.000000001Z"
    elif location=="issue": b["candidates"][0]["decision_at"]="2026-10-06T14:00:00.000000001Z"
    elif location=="minute_known": at(b,1)["known_at"]="2026-10-06T14:03:00.000000001Z"
    elif location=="minute_start": at(b,1)["start"]="2026-10-06T14:02:00.000000001Z"
    else: s["earlier"]["known_at"]="2026-10-06T13:58:00.000000001Z"
    with pytest.raises(owner.InputContractError,match="submicrosecond"):
        labels.build_label_panel(b,s,evaluation)


@pytest.mark.parametrize("stamp",[
    "2026-10-06 16:02:00.000000001Z",
    "2026-10-06t16:02:00.000000001Z",
    "20261006T160200.000000001Z",
    "2026-10-06T16:02:00,000000001Z",
    "2026-10-06T16:02:00+00:00:00.000000001",
])
def test_every_owner_accepted_clock_spelling_refuses_precision_loss(stamp):
    # These are actually parsed as aware instants by the unchanged native owner.
    assert owner._clock(stamp).utcoffset() is not None
    b,s=fixture()
    with pytest.raises(owner.InputContractError,match="submicrosecond"):
        labels.build_label_panel(b,s,stamp)


def test_issue_refusals_reach_output_and_never_reach_path_attachment():
    b,s=fixture();b["contexts"]=[x for x in b["contexts"] if x["kind"]!="daily"]
    original=owner.build_input_panel(b)["frames"][0]
    assert original["availability"]=="unavailable" and original["refusals"]
    o=read(b,s)
    assert o["refusals"]==original["refusals"] and o["path_snapshot_sha256"] is None


@pytest.mark.parametrize("stamp",["2026-10-06 16:02:00.000001Z","2026-10-06t16:02:00.000001Z",
    "20261006T160200.000001Z","2026-10-06T16:02:00,000001Z"])
def test_losslessly_representable_owner_clock_spellings_stay_supported(stamp):
    b,s=fixture();o=read(b,s,stamp)
    assert o["evaluation_at"]=="2026-10-06T16:02:00.000001Z" and o["launch"] is False


def test_invalid_numeric_price_string_does_not_become_a_clock_format_error():
    b,s=fixture();at(b,1)["open"]="100.123456789"
    o=read(b,s)
    assert o["path_state"]=="PATH_UNKNOWN"
    assert "INVALID_OHLCV" in o["refusals"]
