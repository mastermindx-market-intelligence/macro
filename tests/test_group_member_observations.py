"""Closed-contract tests for the Group Pulse complete-member companion."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine.company_intelligence.contracts import ContractError, canonical_json_bytes
from engine import group_member_observations as GMO
from engine import group_pulse as GP


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
    rets = closes.pct_change(fill_method=None)
    panel = {
        "index": idx,
        "closes": closes,
        "rets": rets,
        "spy_adj": rets - 0.001,
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



def _pulse_panel() -> tuple[dict, dict, pd.Timestamp, dict, list[dict]]:
    idx = pd.bdate_range(end=AS_OF, periods=420)
    rng = np.random.default_rng(42)
    closes = pd.DataFrame(index=idx)
    volumes = pd.DataFrame(index=idx)
    tickers = ["A", "B", "C", "D", "E", "F"]
    for offset, ticker in enumerate(tickers):
        returns = rng.normal(0.0004 + offset * 0.00002, 0.012, len(idx))
        closes[ticker] = 100.0 * np.cumprod(1.0 + returns)
        volumes[ticker] = 1_000_000.0 * (1.0 + rng.normal(0.0, 0.05, len(idx)))
    closes.loc[idx[-1], "A"] = closes.loc[idx[-2], "A"] * 1.25
    benchmark = pd.Series(
        400.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.008, len(idx))),
        index=idx,
    )
    panel = GP.build_member_panel(closes, volumes, benchmark)
    basket = {
        "name": "Capture test",
        "members": [
            {"ticker": ticker, "added": "2020-01-01", "removed": None}
            for ticker in tickers
        ],
    }
    as_of = panel["index"].max()
    frames = GP.basket_frames(basket, panel, as_of)
    episodes = GP.episodes_from_series(
        GROUP_ID,
        list(frames["daily"].index),
        frames["daily"]["activity_share"].tolist(),
        frames["daily"]["activity_n"].tolist(),
        frames["members_by_day"],
    )
    receipts = [{
        "kind": "normalized_frame",
        "source_ref": "group_pulse:test-panel",
        "sha256": "2" * 64,
        "bytes": 4321,
        "effective_at": AS_OF,
        "basis": "total_return_close",
    }]
    return panel, basket, as_of, frames, episodes, receipts


def test_same_invocation_capture_preserves_the_frozen_legacy_object():
    panel, basket, as_of, frames, episodes, receipts = _pulse_panel()
    washouts = {ticker: None for ticker in panel["closes"].columns}
    stages = {ticker: 2 for ticker in panel["closes"].columns}
    baseline = GP.basket_pulse(
        GROUP_ID, basket, panel, as_of, washouts, stages, GENERATED_AT,
        frames, episodes,
    )
    captured: dict[str, dict] = {}
    actual = GP.basket_pulse(
        GROUP_ID, basket, panel, as_of, washouts, stages, GENERATED_AT,
        frames, episodes, member_observation_out=captured, source_receipts=receipts,
    )
    assert actual == baseline
    assert set(captured) == {GROUP_ID}
    projected = captured[GROUP_ID]
    assert projected["member_keys"] == sorted(panel["closes"].columns)
    assert projected["legacy_pulse_digest"] is None
    assert projected["metrics"]["legacy_activity"]["denominator"] == baseline["n_covered"]
    assert projected["metrics"]["legacy_activity"]["numerator"] == baseline["participation"]["activity_n"]


def test_receipts_bind_original_bytes_and_normalized_frame_values():
    raw = GMO.raw_bytes_receipt(
        b'{"version":"2026-08-07"}\n',
        source_ref="data/baskets/membership.json",
        basis="curated_membership",
        effective_at="2026-08-07",
    )
    assert raw["kind"] == "raw_bytes"
    assert raw["bytes"] == 25
    assert raw["sha256"] != "0" * 64

    panel, _, as_of, _, _, _ = _pulse_panel()
    first = GMO.normalized_frame_receipt(
        panel["closes"], source_ref="group_pulse:member_close_panel",
        basis="total_return_close", effective_at=as_of,
    )
    second = GMO.normalized_frame_receipt(
        panel["closes"].copy(), source_ref="group_pulse:member_close_panel",
        basis="total_return_close", effective_at=as_of,
    )
    changed_frame = panel["closes"].copy()
    changed_frame.iloc[-1, 0] += 0.01
    changed = GMO.normalized_frame_receipt(
        changed_frame, source_ref="group_pulse:member_close_panel",
        basis="total_return_close", effective_at=as_of,
    )
    assert first == second
    assert changed["sha256"] != first["sha256"]
    assert first["kind"] == "normalized_frame"
    assert first["bytes"] > 0


def test_compute_returns_companion_from_the_same_in_memory_panel(monkeypatch, tmp_path):
    panel, basket, _, _, _, _ = _pulse_panel()
    closes = panel["closes"]
    volumes = pd.DataFrame(1_000_000.0, index=closes.index, columns=closes.columns)
    benchmark = closes.mean(axis=1)

    def fake_membership(_root, receipt_out=None):
        if receipt_out is not None:
            receipt_out.append(GMO.raw_bytes_receipt(
                b'{"version":"2026-08-07","baskets":{}}\n',
                source_ref="data/baskets/membership.json",
                basis="curated_membership",
                effective_at="2026-08-07",
            ))
        return {GROUP_ID: basket}

    monkeypatch.setattr(GP, "load_membership", fake_membership)
    monkeypatch.setattr(GP, "load_member_tape", lambda _tickers, _root: (closes, volumes, []))
    monkeypatch.setattr(GP, "load_benchmark", lambda _root: benchmark)
    monkeypatch.setattr(GP, "member_washouts", lambda frame: {key: None for key in frame.columns})
    monkeypatch.setattr(GP, "member_stages", lambda frame, _vol, _bench: {key: 2 for key in frame.columns})

    result = GP.compute(tmp_path)
    assert set(result["member_observation_groups"]) == {GROUP_ID}
    assert result["member_observation_groups"][GROUP_ID]["member_count"] == len(closes.columns)
    assert result["member_observation_groups"][GROUP_ID]["legacy_pulse_digest"] is None
    assert result["source_receipts"][0]["kind"] == "normalized_frame"
    bases = {row["basis"] for row in result["source_receipts"]}
    assert {"raw_daily_change", "benchmark_relative_daily_change"} <= bases
    assert any(row["kind"] == "raw_bytes" for row in result["source_receipts"])
    assert GP.validate_payload(result["payload"]) == []


def _projected_fixture_group() -> tuple[dict, dict, list[dict]]:
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
    return group, legacy, receipts


def test_run_writes_companion_bound_to_exact_pulse_bytes(monkeypatch, tmp_path):
    import hashlib
    import json

    group, legacy, receipts = _projected_fixture_group()
    computed = {
        "payload": {GROUP_ID: legacy},
        "episodes": {GROUP_ID: []},
        "as_of": AS_OF,
        "elapsed_s": 0.01,
        "n_baskets": 1,
        "member_observation_groups": {GROUP_ID: group},
        "source_receipts": receipts,
        "member_observation_errors": [],
    }
    monkeypatch.setattr(GP, "compute", lambda _root=None: deepcopy(computed))
    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    data_root.mkdir()

    result = GP.run(data_root=data_root, site_root=site_root, require_nightly_lane=False)
    pulse_path = site_root / "basketdata" / "pulse.json"
    companion_path = site_root / "basketdata" / "member_observations.json"
    assert pulse_path.exists() and companion_path.exists()
    pulse_bytes = pulse_path.read_bytes()
    companion = json.loads(companion_path.read_text(encoding="utf-8"))
    assert companion["source"]["legacy_pulse_sha256"] == hashlib.sha256(pulse_bytes).hexdigest()
    assert companion["source"]["legacy_pulse_bytes"] == len(pulse_bytes)
    assert companion["groups"][GROUP_ID]["legacy_pulse_digest"] == hashlib.sha256(pulse_bytes).hexdigest()
    assert GMO.validate_member_bundle(companion) == []
    assert result["member_observations_artifact"] == str(companion_path)
    assert result["member_observations_digest"] == companion["projection_digest"]


def test_failed_current_capture_does_not_overwrite_a_stale_companion(monkeypatch, tmp_path):
    group, legacy, receipts = _projected_fixture_group()
    computed = {
        "payload": {GROUP_ID: legacy},
        "episodes": {GROUP_ID: []},
        "as_of": AS_OF,
        "elapsed_s": 0.01,
        "n_baskets": 1,
        "member_observation_groups": {},
        "source_receipts": receipts,
        "member_observation_errors": ["test_group: capture failed"],
    }
    monkeypatch.setattr(GP, "compute", lambda _root=None: deepcopy(computed))
    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    stale = site_root / "basketdata" / "member_observations.json"
    data_root.mkdir()
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale-companion\n")

    result = GP.run(data_root=data_root, site_root=site_root, require_nightly_lane=False)
    assert stale.read_bytes() == b"stale-companion\n"
    assert result["member_observations_artifact"] is None
    assert result["member_observation_errors"] == ["test_group: capture failed"]


def test_strict_price_metrics_do_not_inherit_the_activity_cohort():
    panel, members, legacy, receipts = _fixture()
    as_of = panel["index"].max()
    panel["closes"].loc[as_of, "C"] = 120.0
    panel["rets"] = panel["closes"].pct_change(fill_method=None)
    panel["spy_adj"] = panel["rets"] - 0.001
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
    assert group["metrics"]["legacy_trend_200"]["observed_member_keys"] == ["A", "B"]
    assert group["metrics"]["strict_trend_200"]["observed_member_keys"] == ["A", "B", "C"]
    assert group["metrics"]["strict_trend_200"]["numerator_member_keys"] == ["A", "C"]


def test_missing_benchmark_preserves_raw_change_and_refuses_relative_change():
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
        benchmark_available=False,
    )
    raw = group["members"]["A"]["metrics"]["raw_daily_change"]
    relative = group["members"]["A"]["metrics"]["benchmark_relative_daily_change"]
    assert isinstance(raw["value"], float)
    assert raw["null_reason"] == "OK"
    assert relative["value"] is None
    assert relative["estimability_reason"] == "benchmark_unavailable"
    assert group["metrics"]["raw_daily_change"]["aggregation"] == "none"
    assert group["metrics"]["raw_daily_change"]["value"] is None


def test_legacy_partial_warmup_is_not_a_strict_200_observation():
    idx = pd.bdate_range(end=AS_OF, periods=220)
    closes = pd.DataFrame({
        "A": np.linspace(100.0, 220.0, len(idx)),
        "B": np.linspace(220.0, 100.0, len(idx)),
        "C": np.r_[np.full(74, np.nan), np.linspace(50.0, 120.0, 146)],
    }, index=idx)
    false = pd.DataFrame(False, index=idx, columns=closes.columns)
    covered = false.copy(); covered.loc[idx[-1], :] = True
    active = false.copy(); active.loc[idx[-1], "A"] = True
    has50 = false.copy(); has50.loc[idx[-1], :] = True
    has200 = false.copy(); has200.loc[idx[-1], :] = True
    above50 = false.copy(); above50.loc[idx[-1], ["A", "C"]] = True
    above200 = false.copy(); above200.loc[idx[-1], ["A", "C"]] = True
    rets = closes.pct_change(fill_method=None)
    panel = {
        "index": idx, "closes": closes, "rets": rets, "spy_adj": rets - 0.001,
        "covered": covered, "active": active,
        "has_ma50": has50, "has_ma200": has200,
        "above_ma50": above50, "above_ma200": above200,
        "activity_z": pd.DataFrame(0.0, index=idx, columns=closes.columns),
    }
    members = [
        {"member_key": key, "source_symbol": key, "identity_ref": f"source:{key}"}
        for key in ("A", "B", "C")
    ]
    legacy = {
        "basket_id": GROUP_ID, "as_of": AS_OF, "generated_at": GENERATED_AT,
        "n_members": 3, "n_covered": 3,
        "participation": {
            "activity_share": round(1 / 3, 4), "activity_n": 1,
            "trend_share_50d": round(2 / 3, 4), "trend_n_50d": 3,
            "trend_share_200d": round(2 / 3, 4), "trend_n_200d": 3,
            "activity_basis": {"ret_only": 1, "ret_and_volume": 0},
        },
    }
    receipts = [{
        "kind": "normalized_frame", "source_ref": "group_pulse:test-panel",
        "sha256": "3" * 64, "bytes": 999, "effective_at": AS_OF,
        "basis": "total_return_close",
    }]
    group = GMO.project_group_members(
        group_id=GROUP_ID, member_records=members, panel=panel, as_of=AS_OF,
        covered_members=["A", "B", "C"], active_members=["A"],
        legacy_pulse=legacy, source_receipts=receipts, generated_at=GENERATED_AT,
    )
    assert group["metrics"]["legacy_trend_200"]["observed_member_keys"] == ["A", "B", "C"]
    assert group["metrics"]["strict_trend_200"]["observed_member_keys"] == ["A", "B"]
    c_cell = group["members"]["C"]["metrics"]["strict_trend_200"]
    assert c_cell["value"] is None
    assert c_cell["observations_available"] == 146
    assert c_cell["observations_required"] == 200
    assert c_cell["estimability_reason"] == "insufficient_lookback"


def test_compute_discloses_benchmark_hole_without_erasing_raw_change(monkeypatch, tmp_path):
    panel, basket, _, _, _, _ = _pulse_panel()
    closes = panel["closes"]
    volumes = pd.DataFrame(1_000_000.0, index=closes.index, columns=closes.columns)

    def fake_membership(_root, receipt_out=None):
        if receipt_out is not None:
            receipt_out.append(GMO.raw_bytes_receipt(
                b'{"version":"2026-08-07","baskets":{}}\n',
                source_ref="data/baskets/membership.json",
                basis="curated_membership",
                effective_at="2026-08-07",
            ))
        return {GROUP_ID: basket}

    monkeypatch.setattr(GP, "load_membership", fake_membership)
    monkeypatch.setattr(GP, "load_member_tape", lambda _tickers, _root: (closes, volumes, []))
    monkeypatch.setattr(GP, "load_benchmark", lambda _root: None)
    monkeypatch.setattr(GP, "member_washouts", lambda frame: {key: None for key in frame.columns})
    monkeypatch.setattr(GP, "member_stages", lambda frame, _vol, _bench: {key: 2 for key in frame.columns})

    result = GP.compute(tmp_path)
    group = result["member_observation_groups"][GROUP_ID]
    assert "benchmark_relative_daily_change" not in {
        row["basis"] for row in result["source_receipts"]
    }
    for ticker in group["member_keys"]:
        raw = group["members"][ticker]["metrics"]["raw_daily_change"]
        relative = group["members"][ticker]["metrics"]["benchmark_relative_daily_change"]
        if raw["value"] is not None:
            assert raw["null_reason"] == "OK"
        assert relative["value"] is None
        assert relative["estimability_reason"] == "benchmark_unavailable"
    assert "benchmark_unavailable_returns_unadjusted" in result["payload"][GROUP_ID]["coverage_warnings"]


def test_source_receipts_bind_membership_and_metric_cells():
    forged = _bundle()
    forged["groups"][GROUP_ID]["source_membership_digest"] = "f" * 64
    forged = _rehash(forged)
    assert any("membership receipt" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["legacy_activity"]["source_ref"] = "unknown:source"
    forged = _rehash(forged)
    assert any("source receipt" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_refuses_unknown_or_missing_metric_definitions():
    forged = _bundle()
    group = forged["groups"][GROUP_ID]
    sample = deepcopy(group["metrics"]["raw_daily_change"])
    sample["recipe_id"] = "forged.buy_signal.v1"
    group["metrics"]["buy_signal"] = sample
    for member in group["members"].values():
        cell = deepcopy(member["metrics"]["raw_daily_change"])
        cell["recipe_id"] = "forged.buy_signal.v1"
        member["metrics"]["buy_signal"] = cell
    group["coverage_details"]["metrics"]["buy_signal"] = deepcopy(
        group["coverage_details"]["metrics"]["raw_daily_change"]
    )
    forged = _rehash(forged)
    assert any("metric set" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    group = forged["groups"][GROUP_ID]
    group["metrics"].pop("strict_trend_200")
    group["coverage_details"]["metrics"].pop("strict_trend_200")
    for member in group["members"].values():
        member["metrics"].pop("strict_trend_200")
    forged = _rehash(forged)
    assert any("metric set" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_refuses_metric_definition_drift_and_ambiguous_receipts():
    forged = _bundle()
    metric = forged["groups"][GROUP_ID]["metrics"]["strict_trend_200"]
    metric["minimum_observations"] = 100
    forged = _rehash(forged)
    assert any("definition" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    receipt = deepcopy(forged["source"]["receipts"][0])
    receipt["sha256"] = "e" * 64
    forged["source"]["receipts"].append(receipt)
    forged = _rehash(forged)
    assert any("duplicate source_ref" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_binds_member_cells_to_aggregate_and_effective_date():
    forged = _bundle()
    group = forged["groups"][GROUP_ID]
    cell = group["members"]["A"]["metrics"]["legacy_activity"]
    cell["value"] = False
    forged = _rehash(forged)
    assert any("numerator membership" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    group = forged["groups"][GROUP_ID]
    cell = group["members"]["A"]["metrics"]["legacy_activity"]
    cell["value"] = None
    cell["null_reason"] = "NO_COVERAGE"
    cell["estimability_reason"] = "unavailable_in_owner_projection"
    forged = _rehash(forged)
    assert any("included cell" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["raw_daily_change"]["effective_at"] = "2026-09-14"
    forged = _rehash(forged)
    assert any("effective_at must equal" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_validates_member_identity_fields_and_deterministic_sets():
    forged = _bundle()
    forged["groups"][GROUP_ID]["members"]["A"]["source_symbol"] = ""
    forged = _rehash(forged)
    assert any("source_symbol" in error
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    metric = forged["groups"][GROUP_ID]["metrics"]["legacy_activity"]
    metric["observed_member_keys"] = list(reversed(metric["observed_member_keys"]))
    metric["cohort_digest"] = GMO.canonical_json_sha256(metric["observed_member_keys"])
    forged = _rehash(forged)
    assert any("observed_member_keys must be deterministic" in error
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_validates_estimability_and_observation_counts():
    forged = _bundle()
    cell = forged["groups"][GROUP_ID]["members"]["C"]["metrics"]["strict_trend_200"]
    cell["estimability_reason"] = "made_up_reason"
    forged = _rehash(forged)
    assert any("estimability_reason" in error
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    cell = forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["legacy_activity"]
    cell["estimability_reason"] = "unavailable_in_owner_projection"
    forged = _rehash(forged)
    assert any("observed cell cannot carry" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    cell = forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["strict_trend_50"]
    cell["observations_required"] = 49
    forged = _rehash(forged)
    assert any("observations_required" in error
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    cell = forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["strict_trend_50"]
    cell["observations_available"] = 51
    forged = _rehash(forged)
    assert any("observations_available exceeds" in error
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_binds_excluded_member_details_to_member_cells():
    forged = _bundle()
    excluded = forged["groups"][GROUP_ID]["metrics"]["strict_trend_200"]["excluded_members"]
    assert excluded
    original_reason = excluded[0]["estimability_reason"]
    excluded[0]["estimability_reason"] = (
        "benchmark_unavailable"
        if original_reason != "benchmark_unavailable"
        else "unavailable_in_owner_projection"
    )
    forged = _rehash(forged)
    assert any("excluded member detail mismatch" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_binds_null_reason_and_coverage_to_estimability():
    forged = _bundle()
    group = forged["groups"][GROUP_ID]
    cell = group["members"]["C"]["metrics"]["strict_trend_200"]
    cell["null_reason"] = "NOT_YET_AVAILABLE"
    group["metrics"]["strict_trend_200"]["excluded_members"][0]["null_reason"] = "NOT_YET_AVAILABLE"
    forged = _rehash(forged)
    assert any("null_reason disagrees with estimability_reason" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    cell = forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["strict_trend_50"]
    cell["observations_available"] = 10
    forged = _rehash(forged)
    assert any("included cell has insufficient observations" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_refuses_future_or_misbound_source_receipts():
    forged = _bundle()
    forged["source"]["receipts"][0]["effective_at"] = "2026-09-16"
    forged = _rehash(forged)
    assert any("source receipt" in error.lower() and "future" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    forged["source"]["receipts"][0]["effective_at"] = "2026-09-14"
    forged = _rehash(forged)
    assert any("referenced source receipt" in error.lower()
               for error in GMO.validate_member_bundle(forged))


def test_closed_contract_requires_nonempty_receipts_and_frame_backed_cells():
    forged = _bundle()
    forged["source"]["receipts"][0]["bytes"] = 0
    forged = _rehash(forged)
    assert any("bytes invalid" in error.lower()
               for error in GMO.validate_member_bundle(forged))

    forged = _bundle()
    forged["source"]["receipts"].append({
        "kind": "raw_bytes",
        "source_ref": "raw:unrelated",
        "sha256": "d" * 64,
        "bytes": 12,
        "effective_at": None,
        "basis": "unrelated_source",
    })
    forged["groups"][GROUP_ID]["members"]["A"]["metrics"]["raw_daily_change"]["source_ref"] = "raw:unrelated"
    forged = _rehash(forged)
    assert any("normalized_frame" in error.lower()
               for error in GMO.validate_member_bundle(forged))
