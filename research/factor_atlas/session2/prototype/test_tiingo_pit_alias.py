"""S2 consumes incumbent Data OS Tiingo alias selections without minting IDs.

All tuples are invented. Real Data OS snapshot lacks any 'tiingo' binding as of
2026-10-09, including an unselected ETF SPY; this native checker cannot fix it.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import pytest
import pressure as m

from tiingo_pit_alias import review_tiingo_pit_aliases

NAMES=("AAPL","MSFT","NVDA","SPY")
NOW="2026-10-09T20:00:00+00:00"
SNAP="dataos.reference.vendor_aliases:2026-10-09:synthetic"
MAP={"AAPL":"SEC:US-XNAS-AAPL",
     "MSFT":"SEC:US-XNAS-MSFT",
     "NVDA":"SEC:US-XNAS-NVDA",
     "SPY":"SEC:US-ARCX-SPY"}  # INVENTED SPY in tests, not a verified listing


def signed(symbol,*,known_at="2026-10-08T14:00:00+00:00",
           valid_from="2026-10-01",valid_to=None,security_id=None,
           owner_vendor="tiingo",evidence_sha256="a"*64):
    d=dict(vendor=owner_vendor,vendor_symbol=symbol,
           security_id=security_id or MAP[symbol],
           valid_from=valid_from,valid_to=valid_to,
           known_at=known_at,evidence_sha256=evidence_sha256)
    body={
      "vendor":d["vendor"],"vendor_symbol":d["vendor_symbol"],
      "security_id":d["security_id"],"valid_from":valid_from,
      "valid_to":valid_to,"known_at":known_at,"evidence_sha256":evidence_sha256
    }
    d["binding_sha256"]=sha256(json.dumps(body,sort_keys=True,
      separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    return d


def review(rows=(),*,on="2026-10-09",decision_at=NOW,source_ref=SNAP):
    return review_tiingo_pit_aliases(
      tuple(rows),required_symbols=NAMES,on=on,
      decision_at_utc=decision_at,
      incumbent_identity_snapshot_ref=source_ref)


def test_actual_empty_tiingo_alias_snapshot_refuses_all_pilot_symbols():
    v=review()
    assert v.schema=="factor_atlas.tiingo_pit_alias_owner_review.v1"
    assert v.status=="NO_SELECTED_TIINGO_ALIASES"
    assert v.required_symbols==NAMES
    assert v.missing_tiingo_symbols==NAMES
    assert v.spylisting_explicitly_unselected is True
    assert v.selected_candidate_symbols==()
    assert v.pit_vendor_aliases_admitted is False
    assert v.original_owner_identity_authenticated is False
    assert v.market_pilot_admitted is False
    assert v.customer_publishable is False
    assert v.authority==m.AUTHORITY


def test_cross_vendor_AAPL_security_id_is_not_a_tiingo_alias():
    a=signed("AAPL",owner_vendor="yahoo")
    with pytest.raises(ValueError,match="not_tiingo"):
        review((a,))


def test_three_tech_candidates_do_not_forge_missing_etf_spy():
    v=review(tuple(signed(s) for s in NAMES[:3]))
    assert v.status=="NO_SELECTED_TIINGO_ALIASES"
    assert v.missing_tiingo_symbols==("SPY",)
    assert v.spylisting_explicitly_unselected
    assert len(v.selected_candidate_symbols)==3
    assert v.pit_vendor_aliases_admitted is False


def test_even_four_consistent_self_sealed_aliases_cannot_grant_source_authority():
    v=review(tuple(signed(s) for s in NAMES))
    assert v.status=="OWNER_PIT_CANDIDATES_NOT_AUTHENTICATED"
    assert v.missing_tiingo_symbols==()
    assert v.selected_candidate_symbols==NAMES
    assert len(v.candidate_security_ids)==4
    assert v.spylisting_explicitly_unselected is False
    assert v.all_four_temporally_applicable_claims is True
    assert v.pit_vendor_aliases_admitted is False
    assert v.source_rights_or_monetary_basis_admitted is False
    assert v.may_use_alias_for_trading is False


def test_alias_known_after_market_event_is_not_a_pit_binding():
    rows=[signed(s) for s in NAMES]
    rows[0]=signed("AAPL",known_at="2026-10-11T23:09:08+00:00")
    v=review(rows)
    assert v.status=="SELECTED_ALIASES_NOT_KNOWN_AT_DECISION"
    assert v.late_known_symbols==("AAPL",)
    assert v.all_four_temporally_applicable_claims is False
    assert v.market_pilot_admitted is False


def test_null_alias_known_at_never_promotes_existing_legacy_ticker_maps():
    rows=[signed(s) for s in NAMES]
    rows[0]["known_at"]=None
    rows[0]["binding_sha256"]=None
    v=review(rows)
    assert v.status=="MISSING_ALIAS_TEMPORAL_PROOF"
    assert v.missing_known_at_symbols==("AAPL",)
    assert v.all_four_temporally_applicable_claims is False


def test_candidate_outside_validity_window_refused_not_reselected():
    rows=[signed(s) for s in NAMES]
    rows[0]=signed("AAPL",valid_to="2026-10-09")
    v=review(rows)
    assert v.status=="ALIAS_OUTSIDE_HISTORICAL_VALIDITY"
    assert v.out_of_validity_symbols==("AAPL",)


def test_future_valid_from_cannot_be_backdated_into_oct_9():
    rows=[signed(s) for s in NAMES]
    rows[-1]=signed("SPY",valid_from="2026-10-10")
    v=review(rows)
    assert v.status=="ALIAS_OUTSIDE_HISTORICAL_VALIDITY"
    assert v.out_of_validity_symbols==("SPY",)


def test_missing_valid_from_is_not_a_selected_pit_alias():
    rows=[signed(s) for s in NAMES]
    rows[1]["valid_from"]=None
    rows[1]["binding_sha256"]=None
    v=review(rows)
    assert v.status=="MISSING_ALIAS_TEMPORAL_PROOF"
    assert v.missing_valid_from_symbols==("MSFT",)


def test_invalid_native_binding_digest_is_refused_even_if_syntactically_valid():
    rows=[signed(s) for s in NAMES]
    rows[0]["security_id"]="SEC:US-XNAS-OTHER"
    with pytest.raises(ValueError,match="native_alias_binding_mismatch"):
        review(rows)


def test_identical_binding_identity_reused_for_different_security_refuses():
    rows=[signed(s) for s in NAMES]
    rows[-1]=signed("SPY",security_id=MAP["AAPL"])
    with pytest.raises(ValueError,match="duplicate_security_id"):
        review(rows)


def test_two_selected_aliases_for_one_symbol_do_not_auto_pick_latest():
    rows=[signed(s) for s in NAMES]
    rows.append(signed("AAPL",known_at="2026-10-09T16:00:00+00:00"))
    with pytest.raises(ValueError,match="duplicate_owner_selected_alias"):
        review(rows)


def test_unknown_extra_vendor_symbol_cannot_expand_source_cohort():
    rows=[signed(s) for s in NAMES]
    rows.append(signed("NVDA",known_at="2026-10-09T14:00:00+00:00"))
    rows[-1]["vendor_symbol"]="OTHER"
    with pytest.raises(ValueError,match="outside_pilot"):
        review(rows)


@pytest.mark.parametrize("invalid",[
    "not-a-date","2026-10-10T08:00:00+00:00",None,True
])
def test_bad_or_future_asof_market_date_fails_closed(invalid):
    with pytest.raises(ValueError,match="decision|date"):
        review(on=invalid)


def test_naive_decision_clock_cannot_be_promoted_to_utc():
    with pytest.raises(ValueError,match="decision_clock"):
        review(decision_at="2026-10-09T20:00:00")


def test_owner_alias_input_order_does_not_change_qualification_digest():
    rows=[signed(s) for s in NAMES]
    a=review(rows)
    b=review(tuple(reversed(rows)))
    assert a==b
    assert a.input_digest==b.input_digest


def test_self_sealed_alias_provenance_change_alters_research_fingerprint():
    rows=[signed(s) for s in NAMES]
    a=review(rows)
    rows[0]=signed("AAPL",evidence_sha256="b"*64)
    b=review(rows)
    assert a.input_digest!=b.input_digest
    assert a.pit_vendor_aliases_admitted is False and not b.pit_vendor_aliases_admitted


def test_alleged_snapshot_name_is_a_claim_and_cannot_authenticate_original_identity():
    rows=[signed(s) for s in NAMES]
    a=review(rows)
    b=review(rows,source_ref="pretend:production:SPY-PIT-APPROVED")
    assert a.input_digest!=b.input_digest
    assert a.pit_vendor_aliases_admitted==b.pit_vendor_aliases_admitted is False
    assert b.original_owner_identity_authenticated is False


def test_legacy_open_validity_and_null_evidence_never_mints_pit():
    rows=[signed(s) for s in NAMES]
    rows[0]["evidence_sha256"]=None
    rows[0]["binding_sha256"]=None
    with pytest.raises(ValueError,match="missing_identity_evidence"):
        review(rows)


def test_retrospective_alias_selection_is_not_the_actual_original_event_time():
    rows=[signed(s) for s in NAMES]
    v=review(rows,decision_at="2026-10-09T20:00:00+00:00")
    assert v.status=="OWNER_PIT_CANDIDATES_NOT_AUTHENTICATED"
    assert v.market_pilot_admitted is False
    assert v.customer_publishable is False


def test_nanosecond_alias_known_at_rounds_up_to_native_dataos_microsecond_clock():
    # The incumbent Data OS alias binding conservatively CEILS submicrosecond
    # known-at fractions; Python's datetime.fromisoformat truncates them.
    # This is a real lookahead boundary, not a tokenizer-style string choice.
    rows=[signed(s) for s in NAMES]
    correctly_sealed=signed("AAPL",known_at="2026-10-09T20:00:00+00:00")
    correctly_sealed["known_at"]="2026-10-09T19:59:59.999999001+00:00"
    rows[0]=correctly_sealed
    v=review(rows,decision_at="2026-10-09T19:59:59.999999+00:00")
    assert v.status=="SELECTED_ALIASES_NOT_KNOWN_AT_DECISION"
    assert v.late_known_symbols==("AAPL",)
    assert not v.all_four_temporally_applicable_claims


def test_submicrosecond_decision_cutoff_is_not_rounded_forward():
    rows=[signed(s) for s in NAMES]
    rows[0]=signed("AAPL",known_at="2026-10-09T20:00:00+00:00")
    v=review(rows,decision_at="2026-10-09T19:59:59.999999999+00:00")
    assert v.late_known_symbols==("AAPL",)
    assert v.status=="SELECTED_ALIASES_NOT_KNOWN_AT_DECISION"
