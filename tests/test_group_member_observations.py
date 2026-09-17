"""Closed-contract tests for the Group Pulse complete-member companion."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine.company_intelligence.contracts import ContractError, canonical_json_bytes
from engine import group_member_observations as GMO


AS_OF = "2026-09-15"
GENERATED_AT = "2026-09-16T07:32:35+00:00"
GROUP_ID = "test_group"


def _fixture() -> tuple[dict, list[dict], dict, list[dict]]:
    idx = pd.bdate_range(end=AS_OF, periods=220)
    closes = pd.DataFrame(
        {
            "A": np.linspace(100.0, 220.0, len(idx)),
            "B": np.linspace(220.0, 100.0, len(idx)),
            "C": np.linspace(80.0, 120.0, len(idx)),
        },
        index=idx,
    )
    closes.loc[idx[-1], "C"] = np.nan
    shape = closes.shape
    false = pd.DataFrame(False, index=idx, columns=closes.columns)
    covered = false.copy()
    active = false.copy()
    has50 = false.copy()
    has200 = false.copy()
    above50 = false.copy()
    above200 = false.copy()
    covered.loc[idx[-1], ["A", "B"]] = True
    active.loc[idx[-1], "A"] = True
    has50.loc[idx[-1], ["A", "B"]] = True
    has200.loc[idx[-1], ["A", "B"]] = True
    above50.loc[idx[-1], "A"] = True
    above200.loc[idx[-1], "A"] = True
    panel = {
        "index": idx,
        "closes": closes,
        "covered": covered,
        "active": active,
        "has_ma50": has50,
        "has_ma200": has200,
        "above_ma50": above50,
        "above_ma200": above200,
        "activity_z": pd.DataFrame(np.zeros(shape), index=idx, columns=closes.columns),
    }
    members = [
        {"member_key": key, "source_symbol": key, "identity_ref": f"source:{key}"}
        for key in ("A", "B", "C")
    ]
    legacy = {
        "schema": "group_pulse.v1",
        "authority": "context_only",
        "generated_at": GENERATED_AT,
        "basket_id": GROUP_ID,
        "as_of": AS_OF,
        "n_members": 3,
        "n_covered": 2,
        "participation": {
            "activity_share": 0.5,
            "activity_n": 1,
            "trend_share_50d": 0.5,
            "trend_n_50d": 2,
            "trend_share_200d": 0.5,
            "trend_n_200d": 2,
            "activity_basis": {"ret_only": 1, "ret_and_volume": 0},
        },
    }
    receipts = [{
        "kind": "normalized_frame",
        "source_ref": "group_pulse:test-panel",
        "sha256": "1" * 64,
        "bytes": 1234,
        "effective_at": AS_OF,
        "basis": "total_return_close",
    }]
    return panel, members, legacy, receipts


def _bundle() -> dict:
    panel, members, legacy, receipts = _fixture()
    group = GMO.project_group_members(
        group_id=GROUP_ID,
        member_records=members,
        panel=panel,
        as_of=AS_OF,
        covered_members=["A", "B"],
        active_members=["A"],
        legacy_pulse=legacy,
        source_receipts=receipts,
        generated_at=GENERATED_AT,
    )
    return GMO.assemble_member_bundle(
        groups={GROUP_ID: group},
        as_of=AS_OF,
        generated_at=GENERATED_AT,
        source_receipts=receipts,
        legacy_pulse_bytes=canonical_json_bytes({GROUP_ID: legacy}),
    )


def _rehash(bundle: dict) -> dict:
    out = deepcopy(bundle)
    out["projection_digest"] = GMO.projection_digest(out)
    return out


def test_complete_roster_and_metric_partition_are_explicit():
    bundle = _bundle()
    assert GMO.validate_member_bundle(bundle) == []
    group = bundle["groups"][GROUP_ID]
    assert set(group["member_keys"]) == {"A", "B", "C"}
    metric = group["metrics"]["legacy_trend_200"]
    assert metric["observed_member_keys"] == ["A", "B"]
    assert [row["member_key"] for row in metric["excluded_members"]] == ["C"]
    assert metric["numerator_member_keys"] == ["A"]
    assert metric["numerator"] == 1
    assert metric["denominator"] == 2
    assert metric["value"] == 0.5
    assert group["members"]["B"]["metrics"]["legacy_trend_200"]["value"] is False
    assert group["members"]["C"]["metrics"]["legacy_trend_200"]["value"] is None
    assert group["members"]["C"]["metrics"]["legacy_trend_200"]["estimability_reason"] == "missing_effective_observation"


def test_group_for_detail_requires_the_bound_legacy_bytes():
    bundle = _bundle()
    expected = bundle["source"]["legacy_pulse_sha256"]
    assert GMO.group_for_detail(bundle, GROUP_ID, expected)["group_id"] == GROUP_ID
    assert GMO.group_for_detail(bundle, GROUP_ID, "0" * 64) is None
    assert GMO.group_for_detail(None, GROUP_ID, expected) is None


def test_projection_is_deterministic_and_context_only():
    first = _bundle()
    second = _bundle()
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["schema"] == "group_member_observations.v1"
    assert first["authority"] == "context_only"


def test_duplicate_catalogue_member_is_refused():
    panel, members, legacy, receipts = _fixture()
    with pytest.raises(ContractError, match="duplicate member"):
        GMO.project_group_members(
            group_id=GROUP_ID,
            member_records=members + [members[0]],
            panel=panel,
            as_of=AS_OF,
            covered_members=["A", "B"],
            active_members=["A"],
            legacy_pulse=legacy,
            source_receipts=receipts,
            generated_at=GENERATED_AT,
        )


@pytest.mark.parametrize(
    "mutate,needle",
    [
        (lambda b: b["groups"][GROUP_ID]["metrics"]["legacy_trend_200"].__setitem__("denominator", 3), "denominator"),
        (lambda b: b["groups"][GROUP_ID]["metrics"]["legacy_trend_200"]["numerator_member_keys"].append("C"), "numerator"),
        (lambda b: b["groups"][GROUP_ID]["metrics"]["legacy_trend_200"].__setitem__("excluded_members", []), "partition"),
        (lambda b: b["groups"][GROUP_ID]["members"]["A"]["metrics"]["legacy_trend_200"].__setitem__("recipe_id", "wrong"), "recipe"),
        (lambda b: b["groups"][GROUP_ID].__setitem__("legacy_pulse_digest", "0" * 64), "legacy"),
        (lambda b: b["groups"][GROUP_ID]["members"]["C"]["metrics"]["legacy_trend_200"].__setitem__("effective_at", "2026-09-16"), "future"),
    ],
)
def test_forged_contract_states_are_rejected(mutate, needle):
    forged = _bundle()
    mutate(forged)
    forged = _rehash(forged)
    errors = GMO.validate_member_bundle(forged)
    assert any(needle in error.lower() for error in errors), errors


def test_non_finite_numeric_value_is_rejected_without_validator_crash():
    forged = _bundle()
    forged["groups"][GROUP_ID]["metrics"]["legacy_trend_200"]["value"] = float("nan")
    errors = GMO.validate_member_bundle(forged)
    assert any("finite" in error.lower() for error in errors), errors


def test_unknown_fields_are_rejected_at_every_boundary():
    forged = _bundle()
    forged["surprise"] = True
    assert any("unknown" in error.lower() for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    forged["groups"][GROUP_ID]["metrics"]["legacy_trend_200"]["score"] = 99
    forged = _rehash(forged)
    assert any("unknown" in error.lower() for error in GMO.validate_member_bundle(forged))


def test_projector_refuses_disagreement_with_legacy_pulse():
    panel, members, legacy, receipts = _fixture()
    legacy["participation"]["trend_share_200d"] = 0.75
    with pytest.raises(ContractError, match="legacy_trend_200"):
        GMO.project_group_members(
            group_id=GROUP_ID,
            member_records=members,
            panel=panel,
            as_of=AS_OF,
            covered_members=["A", "B"],
            active_members=["A"],
            legacy_pulse=legacy,
            source_receipts=receipts,
            generated_at=GENERATED_AT,
        )
