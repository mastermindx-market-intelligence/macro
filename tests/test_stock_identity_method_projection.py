"""Synthetic metadata only: no events, outcomes, participants or stores are read."""
from copy import deepcopy

import pytest

from engine.stock_identity.replay.method_projection import project_registered_methods


R = "grey_dot_macro confirmed_buy rebuy reclaim_waiver weekly_washout_turn sea_event_classes starter_signature rsi30_cross low20d_bounce stoch2w_cross".split()
B = "grey_dot_terminal bottom_watch_terminal tier_cascade_t1 tier_cascade_t2 tier_cascade_t3 tier_cascade_t4".split()
P = "starter_pending starter_failed starter_converted amber_early door_r_rearm turn_watch_deck gc_v2_scores radar_c1_c2".split()


@pytest.fixture
def metadata():
    return [{"family_key": k, "provenance_class": c, "producer": "synthetic:test",
             "era_pins": ["synthetic-era"], "spec_hash": None if c == "P" else "a" * 64}
            for c, keys in (("R", R), ("B", B), ("P", P)) for k in keys]


def test_methods_never_grant_coverage_or_authority(metadata):
    for row in metadata:
        row.update(family_first_available="1900-01-01", event_count=999,
                   historical_coverage_status=True, live_availability_status=True)
    before = deepcopy(metadata)
    result = project_registered_methods(metadata)
    assert metadata == before
    assert len(result["rows"]) == 24
    assert all(value is False for value in result["authority"].values())
    assert result["clean_pool_count"] is result["clean_pool_hash"] is None
    assert result["scientific_acceptance"] is result["P2_executed"] is False
    for row in result["rows"]:
        expected = False if row["family_key"] in P else None
        assert row["historical_eligibility"] is expected
        assert row["historical_coverage_status"] is expected
        assert row["live_availability_status"] is None
        assert row["identity_qualified"] is False
        assert all(m["coverage_status"] is expected for m in row["methods"])
    result["rows"][0]["registry_identity"]["era_pins"].append("mutated")
    assert metadata == before


def test_registered_special_cases_and_separate_arms(metadata):
    rows = {r["family_key"]: r for r in project_registered_methods(metadata)["rows"]}
    def bases(key):
        return [m["basis"] for m in rows[key]["methods"]]
    assert bases("grey_dot_macro") == ["PIT_RECOMPUTE"]
    assert bases("rebuy") == ["LEDGER_COVERAGE"]
    assert bases("reclaim_waiver") == ["STORE_VINTAGE"]
    for key in ("confirmed_buy", "weekly_washout_turn"):
        assert bases(key) == ["LEDGER_COVERAGE", "PIT_RECOMPUTE"]
        assert rows[key]["methods"][0]["constraint"] != rows[key]["methods"][1]["constraint"]
    for key in B:
        assert bases(key) == ["LOCKED_SPEC_BACKCAST"]
        assert rows[key]["methods"][0]["spec_postdates_history_requirement"] == "ALWAYS"
        assert rows[key]["methods"][0]["preserve_registered_era_and_deviations"] is True
    for key in P:
        assert bases(key) == ["PROSPECTIVE_ONLY"]
        assert rows[key]["registry_identity"]["spec_hash"] is None
    assert bases("starter_signature") == ["PIT_RECOMPUTE"]
    assert "no STARTER licensing" in rows["starter_signature"]["methods"][0]["constraint"]


def test_confirmed_buy_preledger_annotation_is_conditional_not_false(metadata):
    row = next(r for r in project_registered_methods(metadata)["rows"]
               if r["family_key"] == "confirmed_buy")
    arms = {m["basis"]: m for m in row["methods"]}
    assert arms["PIT_RECOMPUTE"]["spec_postdates_history_requirement"] == "PRE_LEDGER_RECOMPUTE"
    assert arms["LEDGER_COVERAGE"]["spec_postdates_history_requirement"] == "NOT_APPLICABLE"
    assert all(m["coverage_status"] is None for m in arms.values())


@pytest.mark.parametrize("field,value", [
    ("family_key", "unregistered"), ("family_key", []),
    ("provenance_class", "P"), ("producer", ""),
    ("era_pins", []), ("era_pins", [None]), ("era_pins", ["a", "a"]),
    ("spec_hash", None), ("spec_hash", "x" * 64),
])
def test_malformed_or_drifted_metadata_fails_closed(metadata, field, value):
    metadata[0][field] = value
    with pytest.raises(ValueError):
        project_registered_methods(metadata)


def test_missing_duplicate_and_wrong_class_p_fail_closed(metadata):
    with pytest.raises(ValueError):
        project_registered_methods(metadata[:-1])
    duplicate = deepcopy(metadata)
    duplicate[-1] = deepcopy(duplicate[0])
    with pytest.raises(ValueError):
        project_registered_methods(duplicate)
    metadata[-1]["provenance_class"] = "R"
    with pytest.raises(ValueError):
        project_registered_methods(metadata)


def test_order_determinism(metadata):
    assert project_registered_methods(metadata) == project_registered_methods(list(reversed(metadata)))
