"""Lane C leadership receipt -> Lane A compact consumer integration."""
from __future__ import annotations

from copy import deepcopy

from scripts import build_state_of_themes as sot


def _observation(
    key: str,
    *,
    state: str = "LEADING",
    status: str = "MEASURED",
    asof: str = "2026-09-18",
    input_hash: str | None = None,
) -> dict:
    receipt = {
        "clocks": {
            "observation_session": asof,
            "computation_utc": "2026-09-19T16:00:00Z",
        },
        "bar_status": "CLOSED",
    }
    if input_hash is not None:
        receipt["input_hash"] = input_hash
    return {
        "schema": "subsector_rotation.closed_session_leadership.v1",
        "status": status,
        "asof": asof,
        "bar_status": "CLOSED",
        "reason_codes": ["DESCRIPTIVE_SHADOW_ONLY"],
        "parent": {
            "key": key,
            "strength_level": {"state": state, "excess_vs_market_pct": 4.2},
            "acceleration": {"state": "IMPROVING"},
        },
        "measurement_receipt": receipt,
    }


def _theme_ref(key: str, *, asof: str = "2026-09-18") -> dict:
    escaped = key.replace("~", "~0").replace("/", "~1")
    schema = "subsector_rotation.closed_session_leadership.v1"
    return {
        "theme_id": "ai_semiconductors",
        "subsector_rotation": {
            "subsectors": [{
                "key": key,
                "leadership_observation_ref": {
                    "observation_key": key,
                    "evidence_family_id": f"{schema}:{key}",
                    "observation_id": f"{schema}:{key}:{asof}",
                    "json_pointer": f"/subsector_leadership_observations/{escaped}",
                    "schema": schema,
                    "status": "MEASURED",
                    "asof": asof,
                },
            }]
        },
    }


def test_single_lane_c_source_state_is_preserved_without_rank_authority() -> None:
    key = "Semiconductors"
    joined = sot._lane_c_leadership_context(
        _theme_ref(key), {key: _observation(key)}
    )

    assert joined is not None
    assert joined["state"] == "LEADING"
    assert joined["value"] == [{
        "observation_key": key,
        "status": "MEASURED",
        "state": "LEADING",
        "acceleration": "IMPROVING",
        "asof": "2026-09-18",
    }]
    assert joined["clocks"]["observation"] == "2026-09-18"
    assert joined["bar_status"] == {"closed": True, "provisional": False}
    assert "may_rank" not in joined and "may_trade" not in joined


def test_multiple_lane_c_source_states_remain_observed_not_synthetically_ranked() -> None:
    first = _theme_ref("Semiconductors")
    second_ref = _theme_ref("Memory")
    first["subsector_rotation"]["subsectors"].extend(
        second_ref["subsector_rotation"]["subsectors"]
    )
    joined = sot._lane_c_leadership_context(
        first,
        {
            "Semiconductors": _observation("Semiconductors", state="LEADING"),
            "Memory": _observation("Memory", state="LAGGING"),
        },
    )

    assert joined is not None
    assert joined["state"] == "OBSERVED"
    assert {row["state"] for row in joined["value"]} == {"LEADING", "LAGGING"}
    assert "MULTIPLE_LANE_C_LEADERSHIP_STATES" in joined["reason_codes"]


def test_lane_c_unavailable_stays_unavailable() -> None:
    key = "Semiconductors"
    observation = _observation(key, state="UNAVAILABLE", status="UNAVAILABLE")
    observation["reason_codes"] = ["OWNER_INPUT_LOAD_FAILED"]
    joined = sot._lane_c_leadership_context(_theme_ref(key), {key: observation})

    assert joined is not None
    assert joined["state"] == "UNAVAILABLE"
    assert "OWNER_INPUT_LOAD_FAILED" in joined["reason_codes"]


def test_lane_c_receipt_identity_is_preserved_and_independence_fails_closed() -> None:
    key = "Semiconductors"
    joined = sot._lane_c_leadership_context(
        _theme_ref(key), {key: _observation(key)}
    )
    assert joined is not None

    theme = {
        "theme_id": "ai_semiconductors",
        "leadership_context": joined,
        "entry_context": None,
        "falsifier_any_fired": False,
        "falsifier_n_data_missing": 0,
        "stage_key": "WATCH",
        "lane": "early",
        "div_label_en": "—",
        "asym_legs_section": [],
        "evidence_refs": [],
        "foresight_observation_asof": "2026-09-18",
    }
    row = sot._consumer_contract_row(
        theme,
        basket_id="ai_semiconductors",
        snapshot_asof="2026-09-19",
        page_stale_legs=0,
    )
    leadership = row["dimensions"]["leadership"]

    assert leadership["state"] == "LEADING"
    assert leadership["source_records"][0]["source_family"] == (
        "subsector_rotation.closed_session_leadership.v1"
    )
    assert leadership["source_records"][0]["parent_identity"] == key
    assert leadership["source_records"][0]["observation_session"] == "2026-09-18"
    assert leadership["source_records"][0]["observation_id"].endswith(
        ":Semiconductors:2026-09-18"
    )
    assert row["evidence_identity"]["available"] is False
    assert row["independent_evidence_families"] == []
    assert all(
        row["authority"][name] is False
        for name in ("may_rank", "may_gate", "may_size", "may_escalate", "may_trade")
    )


def test_lane_c_owner_input_hash_enables_identity_without_inventing_one() -> None:
    key = "Semiconductors"
    joined = sot._lane_c_leadership_context(
        _theme_ref(key),
        {key: _observation(key, input_hash="sha256:owner-input")},
    )
    assert joined is not None
    theme = {
        "theme_id": "ai_semiconductors",
        "leadership_context": joined,
        "entry_context": None,
        "falsifier_any_fired": False,
        "falsifier_n_data_missing": 0,
        "stage_key": "WATCH",
        "lane": "early",
        "div_label_en": "—",
        "asym_legs_section": [],
        "evidence_refs": [],
        "foresight_observation_asof": "2026-09-18",
    }
    row = sot._consumer_contract_row(
        theme,
        basket_id="ai_semiconductors",
        snapshot_asof="2026-09-19",
        page_stale_legs=0,
    )

    assert row["evidence_identity"]["available"] is True
    assert row["evidence_identity"]["records"][0]["input_hash"] == "sha256:owner-input"


def test_missing_or_mismatched_lane_c_reference_does_not_fabricate_leadership() -> None:
    assert sot._lane_c_leadership_context(
        {"subsector_rotation": {"subsectors": []}},
        {"Semiconductors": _observation("Semiconductors")},
    ) is None

    bad = _theme_ref("Semiconductors")
    bad["subsector_rotation"]["subsectors"][0]["leadership_observation_ref"][
        "json_pointer"
    ] = "/subsector_leadership_observations/Other"
    assert sot._lane_c_leadership_context(
        bad, {"Semiconductors": _observation("Semiconductors")}
    ) is None


def test_compose_consumes_lane_c_store_through_existing_theme_state_path(tmp_path) -> None:
    import json

    key = "Semiconductors"
    nwd = tmp_path / "site/neuralwebdata"
    nwd.mkdir(parents=True)
    ref_theme = _theme_ref(key)
    (nwd / "theme_state.json").write_text(json.dumps({
        "schema": "theme_state.v1",
        "as_of": "2026-09-18",
        "n_themes": 1,
        "stale_legs": [],
        "themes": [{
            "theme_id": "ai_semiconductors",
            "name_en": "AI Semiconductors",
            "name_zh": "AI半导体",
            "foresight": {"stage": "WATCH"},
            "subsector_rotation": ref_theme["subsector_rotation"],
        }],
        "subsector_leadership_observations": {
            key: _observation(key, state="LEADING"),
        },
    }))

    ctx = sot.compose(tmp_path)
    assert len(ctx["themes"]) == 1
    row = ctx["themes"][0]
    assert row["theme_id"] == "ai_semiconductors"
    assert row["leadership_context"]["state"] == "LEADING"
    assert row["leadership_context"]["value"][0]["observation_key"] == key
    assert row["leadership_context"]["source_records"][0]["parent_identity"] == key
