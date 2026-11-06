from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import engine.global_liquidity_transmission as glt
from scripts.build_global_liquidity_transmission import preserve_first_known


def _cfg() -> dict:
    monetary = {}
    for name in ("fed", "ecb", "boj"):
        monetary[name] = {
            "provider": name,
            "source_id": name.upper(),
            "frequency": "weekly",
            "period_anchor": "observation_date",
            "release_lag_bdays": 1,
            "stale_after_calendar_days": 14,
            "unit_multiplier": 1.0,
            "fx": None,
            "weight": 1.0,
            "pit_status": "fixture",
            "revision_risk": "low",
        }
    funding = {}
    for name in ("broad_dollar", "real_yield_10y", "high_yield_oas"):
        funding[name] = {
            "provider": name,
            "source_id": name.upper(),
            "frequency": "weekly",
            "period_anchor": "observation_date",
            "release_lag_bdays": 1,
            "stale_after_calendar_days": 14,
            "change_transform": "level_change",
            "change_periods": 4,
            "direction_multiplier": -1.0,
            "weight": 1.0,
            "pit_status": "fixture",
            "revision_risk": "low",
        }
    return {
        "contract_schema": glt.CONTRACT_SCHEMA,
        "producer_version": "fixture.1",
        "authority": "measurement_only",
        "frequency": "W-FRI",
        "min_history_periods": 12,
        "orthogonal_min_history_periods": 24,
        "min_monetary_coverage_ratio": 2 / 3,
        "min_funding_coverage_ratio": 2 / 3,
        "monetary_components": monetary,
        "usd_funding_components": funding,
        "quality_thresholds": {"monetary_impulse_flat_band": 0.05},
    }


def _inputs(periods: int = 180) -> tuple[dict, dict, dict]:
    idx = pd.date_range("2018-01-03", periods=periods, freq="W-WED")
    t = np.arange(periods, dtype=float)
    monetary = {
        "fed": pd.Series(100 + 0.30 * t + np.sin(t / 9), index=idx),
        "ecb": pd.Series(90 + 0.20 * t + np.cos(t / 7), index=idx),
        "boj": pd.Series(80 + 0.10 * t + np.sin(t / 11), index=idx),
    }
    funding = {
        "broad_dollar": pd.Series(100 + np.sin(t / 5), index=idx),
        "real_yield_10y": pd.Series(1.0 + np.cos(t / 8), index=idx),
        "high_yield_oas": pd.Series(3.0 + np.sin(t / 6), index=idx),
    }
    return monetary, {name: None for name in monetary}, funding


def test_boj_monthly_label_is_anchored_to_month_end_before_release() -> None:
    raw = pd.Series([500.0], index=pd.to_datetime(["2026-07-01"]))
    fx = pd.Series(
        [150.0, 155.0],
        index=pd.to_datetime(["2026-07-01", "2026-07-31"]),
    )
    spec = {
        "period_anchor": "month_end",
        "release_lag_bdays": 2,
        "stale_after_calendar_days": 45,
        "unit_multiplier": 1.0,
        "fx": {"invert": True},
    }
    grid = pd.DatetimeIndex(["2026-07-31", "2026-08-07"])

    aligned = glt.align_component(raw, spec, grid, fx)

    assert pd.isna(aligned.value.loc["2026-07-31"])
    assert aligned.reference_date.loc["2026-08-07"] == pd.Timestamp("2026-07-31")
    assert aligned.available_date.loc["2026-08-07"] == pd.Timestamp("2026-08-04")
    assert aligned.value.loc["2026-08-07"] == pytest.approx(500.0 / 155.0)


def test_future_source_mutation_cannot_change_past_state() -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    cutoff = pd.Timestamp("2020-12-25")
    before, *_ = glt.build_state_history(monetary, fx, funding, cfg, asof=cutoff)

    mutated = {name: series.copy() for name, series in monetary.items()}
    future_idx = mutated["fed"].index > cutoff
    mutated["fed"].loc[future_idx] *= 50.0
    after, *_ = glt.build_state_history(mutated, fx, funding, cfg)

    pd.testing.assert_frame_equal(
        before,
        after.loc[before.index],
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


def test_missing_components_reduce_coverage_and_never_become_supportive_zero() -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    cutoff = monetary["ecb"].index[-30]
    monetary["ecb"] = monetary["ecb"].loc[:cutoff]
    monetary["boj"] = monetary["boj"].loc[:cutoff]

    history, *_ = glt.build_state_history(monetary, fx, funding, cfg)

    latest = history.iloc[-1]
    assert latest["monetary_coverage_ratio"] == pytest.approx(1 / 3)
    assert pd.isna(latest["monetary_stance"])
    assert pd.isna(latest["monetary_impulse"])
    assert pd.isna(latest["liquidity_breadth"])


def test_orthogonal_residual_uses_only_prior_pairs() -> None:
    idx = pd.date_range("2020-01-03", periods=60, freq="W-FRI")
    stance = pd.Series(np.linspace(-2, 2, 60), index=idx)
    impulse = 0.5 + 0.25 * stance + pd.Series(np.sin(np.arange(60)), index=idx)
    baseline = glt.causal_orthogonal_residual(impulse, stance, min_periods=20)
    changed = impulse.copy()
    changed.iloc[-1] += 1000
    replay = glt.causal_orthogonal_residual(changed, stance, min_periods=20)

    pd.testing.assert_series_equal(baseline.iloc[:-1], replay.iloc[:-1])
    expected_delta = changed.iloc[-1] - impulse.iloc[-1]
    assert replay.iloc[-1] - baseline.iloc[-1] == pytest.approx(expected_delta)


def test_contract_is_state_only_and_reports_null_global_credit(monkeypatch, tmp_path) -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))

    payload, history = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )

    assert set(payload) == {"meta", "state", "quality", "freshness"}
    assert payload["meta"]["schema"] == "global_liquidity_transmission.v1"
    assert payload["meta"]["authority"] == "measurement_only"
    assert payload["state"]["credit_impulse_global"] is None
    assert payload["quality"]["global_credit"]["status"] == "insufficient_comparable_pit_coverage"
    event = payload["state"]["event_reference"]
    assert event["producer_schema"] == "global_liquidity_transmission.v1"
    assert event["state_family"] == "monetary_impulse"
    assert event["shock_type"] == "policy_liquidity_impulse"
    assert event["direction"] in (-1, 1)
    assert 0 <= event["breadth"] <= 1
    assert 0 <= event["confidence"] <= 1
    assert 0 <= event["coverage"] <= 1
    assert event["freshness"] == "fresh"
    assert len(event["source_snapshot_hash"]) == 64
    assert event["data_version"].startswith("glt_data:")
    assert event["clocks"]["adapter_observed_at_field"] == "evidence_available_at"
    assert event["clocks"]["adapter_known_at_field"] == "first_known_at"
    assert event["clocks"]["release_at"] == event["clocks"]["evidence_available_at"]
    assert "transmission" not in payload
    assert "repricing_gap" not in payload
    assert history["orthogonalised_impulse"].notna().any()


def test_source_snapshot_hash_excludes_first_known_clock(monkeypatch, tmp_path) -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))
    first, _ = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, 10, tzinfo=timezone.utc),
    )
    replay, _ = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, 11, tzinfo=timezone.utc),
    )

    assert first["meta"]["source_snapshot_hash"] == replay["meta"]["source_snapshot_hash"]
    assert first["meta"]["data_version"] == replay["meta"]["data_version"]
    assert (
        first["state"]["event_reference"]["clocks"]["first_known_at"]
        != replay["state"]["event_reference"]["clocks"]["first_known_at"]
    )
    preserved = preserve_first_known(replay, first)
    assert (
        preserved["state"]["event_reference"]["clocks"]["first_known_at"]
        == first["state"]["event_reference"]["clocks"]["first_known_at"]
    )
    assert (
        preserved["freshness"]["clocks"]["first_known_at"]
        == first["state"]["event_reference"]["clocks"]["first_known_at"]
    )


def test_frozen_fixture_reproduces_historical_window() -> None:
    fixture_path = Path(__file__).parent / "fixtures/global_liquidity_transmission_wliq1_window.json"
    fixture = json.loads(fixture_path.read_text())
    idx = pd.DatetimeIndex(fixture["dates"])
    monetary = {name: pd.Series(values, index=idx) for name, values in fixture["monetary"].items()}
    funding = {name: pd.Series(values, index=idx) for name, values in fixture["funding"].items()}
    cfg = _cfg()
    cfg["orthogonal_min_history_periods"] = fixture["orthogonal_min_history_periods"]

    history, *_ = glt.build_state_history(
        monetary,
        {name: None for name in monetary},
        funding,
        cfg,
    )

    assert str(history.index[-1].date()) == fixture["expected_last_asof"]
    for field, expected in fixture["expected_last"].items():
        assert history.iloc[-1][field] == pytest.approx(expected, abs=1e-12)


def test_walk_forward_receipt_has_purge_gap_and_no_promotion_authority() -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs(periods=360)
    history, *_ = glt.build_state_history(monetary, fx, funding, cfg)
    btc = pd.Series(
        np.exp(np.linspace(6, 9, 360) + 0.1 * np.sin(np.arange(360) / 8)),
        index=pd.date_range("2018-01-03", periods=360, freq="W-WED"),
    )

    receipt = glt.walk_forward_factor_comparison(
        history,
        btc,
        initial_train_weeks=80,
        test_weeks=26,
        purge_weeks=4,
    )

    assert receipt["authority"] == "research_only_no_promotion"
    assert set(receipt["factors"]) == {
        "monetary_stance",
        "monetary_impulse",
        "orthogonalised_impulse",
    }
    for result in receipt["factors"].values():
        assert result["oos_n"] > 0
        for fold in result["folds"]:
            assert (pd.Timestamp(fold["test_start"]) - pd.Timestamp(fold["train_end"])).days >= 28


# --------------------------------------------------------------------------
# B1 — the combined evidence clock is never earlier than the evidence carried
# --------------------------------------------------------------------------


def _daily_funding(periods: int = 1200) -> dict[str, pd.Series]:
    """Business-daily funding, so its release lands after every weekly monetary one."""
    idx = pd.date_range("2018-01-03", periods=periods, freq="B")
    d = np.arange(periods, dtype=float)
    return {
        "broad_dollar": pd.Series(100 + np.sin(d / 25), index=idx),
        "real_yield_10y": pd.Series(1.0 + np.cos(d / 40), index=idx),
        "high_yield_oas": pd.Series(3.0 + np.sin(d / 30), index=idx),
    }


def test_evidence_clock_moves_when_a_funding_input_postdates_all_monetary_inputs(
    monkeypatch, tmp_path
) -> None:
    cfg = _cfg()
    monetary, fx, _ = _inputs()
    funding = _daily_funding()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))

    payload, _ = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )

    components = payload["freshness"]["components"]
    latest_monetary = max(row["available_date"] for row in components["monetary"].values())
    latest_funding = max(row["available_date"] for row in components["usd_funding"].values())
    # Premise of the test: without it the assertions below prove nothing.
    assert latest_funding > latest_monetary

    clocks = payload["state"]["event_reference"]["clocks"]
    assert clocks["monetary_release_at"] == f"{latest_monetary}T00:00:00Z"
    assert clocks["evidence_available_at"] == f"{latest_funding}T00:00:00Z"
    assert clocks["evidence_available_at"] > clocks["monetary_release_at"]
    # The published adapter clock must be the conservative one, not the narrow one.
    assert clocks["release_at"] == clocks["evidence_available_at"]
    assert clocks["adapter_observed_at_field"] == "evidence_available_at"
    contributions = clocks["evidence_available_at_contributions"]
    assert contributions["usd_funding"] == f"{latest_funding}T00:00:00Z"
    assert contributions["monetary"] == f"{latest_monetary}T00:00:00Z"
    assert payload["freshness"]["clocks"] == clocks


def test_embedded_us_quality_asof_also_raises_the_evidence_clock(monkeypatch, tmp_path) -> None:
    """The exact 2026-08-21 shape Sol flagged: quality newer than the monetary release."""
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))
    generated_at = datetime(2026, 8, 22, tzinfo=timezone.utc)

    without, _ = glt.build_contract(
        producer_cfg=cfg, root=tmp_path, generated_at=generated_at
    )
    baseline = without["state"]["event_reference"]["clocks"]
    state_asof = without["state"]["asof"]
    assert baseline["evidence_available_at"] < f"{state_asof}T00:00:00Z"

    regime = tmp_path / "data/regime/latest.json"
    regime.parent.mkdir(parents=True, exist_ok=True)
    regime.write_text(
        json.dumps({"liquidity_quality": {"asof": state_asof, "label": "contracting"}})
    )
    with_quality, _ = glt.build_contract(
        producer_cfg=cfg, root=tmp_path, generated_at=generated_at
    )

    clocks = with_quality["state"]["event_reference"]["clocks"]
    assert with_quality["quality"]["us_liquidity_quality"]["asof"] == state_asof
    assert clocks["evidence_available_at_contributions"]["us_liquidity_quality"] == (
        f"{state_asof}T00:00:00Z"
    )
    assert clocks["evidence_available_at"] == f"{state_asof}T00:00:00Z"
    assert clocks["evidence_available_at"] > baseline["evidence_available_at"]
    assert clocks["release_at"] == clocks["evidence_available_at"]
    # The narrow monetary-only fact is preserved, not deleted.
    assert clocks["monetary_release_at"] == baseline["monetary_release_at"]


# --------------------------------------------------------------------------
# B2 — the standardized shock magnitude is real and prior-only
# --------------------------------------------------------------------------


def test_monetary_impulse_z_is_prior_only_and_is_not_the_raw_delta() -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    cutoff = pd.Timestamp("2020-12-25")
    before, *_ = glt.build_state_history(monetary, fx, funding, cfg, asof=cutoff)

    mutated = {name: series.copy() for name, series in monetary.items()}
    mutated["fed"].loc[mutated["fed"].index > cutoff] *= 50.0
    after, *_ = glt.build_state_history(mutated, fx, funding, cfg)

    pd.testing.assert_series_equal(
        before["monetary_impulse_z"],
        after.loc[before.index, "monetary_impulse_z"],
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )

    standardized = before["monetary_impulse_z"].dropna()
    assert not standardized.empty
    raw = before["monetary_impulse"].reindex(standardized.index)
    # A genuine standardization, not the raw weekly delta wearing a "_z" name.
    assert not np.allclose(standardized.to_numpy(), raw.to_numpy())
    assert standardized.abs().max() > raw.abs().max()


def test_event_reference_publishes_both_magnitudes_with_their_own_units(
    monkeypatch, tmp_path
) -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))

    payload, _ = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )

    state = payload["state"]
    event = state["event_reference"]
    assert event["magnitude"] == state["monetary_impulse"]
    assert event["magnitude_z"] == state["monetary_impulse_z"]
    assert event["magnitude"] != event["magnitude_z"]
    assert event["magnitude_unit"] == glt.MONETARY_IMPULSE_UNIT
    assert event["magnitude_z_unit"] == glt.MONETARY_IMPULSE_Z_UNIT
    assert event["magnitude_unit"] != event["magnitude_z_unit"]
    assert state["units"]["monetary_impulse"] == glt.MONETARY_IMPULSE_UNIT
    assert state["units"]["monetary_impulse_z"] == glt.MONETARY_IMPULSE_Z_UNIT
    # The direction/flat band gates the raw delta and says so.
    assert state["label_rule"]["field"] == "state.monetary_impulse"
    assert state["label_rule"]["unit"] == glt.MONETARY_IMPULSE_UNIT
    assert state["label_rule"]["config_key"] == "quality_thresholds.monetary_impulse_flat_band"
    assert event["direction"] == (1 if state["monetary_impulse"] > 0 else -1)


# --------------------------------------------------------------------------
# B3 — two closed vocabularies, never conflated
# --------------------------------------------------------------------------


def test_every_emitted_label_belongs_to_its_own_closed_vocabulary() -> None:
    us_labels = [
        None,
        "benign-expansion",
        "stress-expansion",
        "neutral",
        "neutral-hollow",
        "contracting",
        "unknown",
        "some-future-label",
    ]
    impulses = [None, -5.0, -0.06, -0.05, 0.0, 0.05, 0.06, 5.0]

    emitted_state: set[str] = set()
    emitted_quality: set[str] = set()
    for impulse in impulses:
        state_label = glt._state_label(impulse, 0.05)
        assert state_label in glt.STATE_LABEL_ENUM
        emitted_state.add(state_label)
        for us_label in us_labels:
            us_quality = None if us_label is None else {"label": us_label}
            quality_label = glt._quality_label(state_label, us_quality)
            assert quality_label in glt.QUALITY_LABEL_ENUM
            emitted_quality.add(quality_label)

    # Every declared member is reachable, so the enums are exact, not aspirational.
    assert emitted_state == set(glt.STATE_LABEL_ENUM)
    assert emitted_quality == set(glt.QUALITY_LABEL_ENUM)
    # The vocabularies overlap in exactly one member and no other.
    assert set(glt.STATE_LABEL_ENUM) & set(glt.QUALITY_LABEL_ENUM) == {"unknown"}


def test_contract_self_documents_both_vocabularies(monkeypatch, tmp_path) -> None:
    cfg = _cfg()
    monetary, fx, funding = _inputs()
    monkeypatch.setattr(glt, "load_inputs", lambda _cfg: (monetary, fx, funding))

    payload, _ = glt.build_contract(
        producer_cfg=cfg,
        root=tmp_path,
        generated_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )

    state = payload["state"]
    event = state["event_reference"]
    assert state["label_enum"] == list(glt.STATE_LABEL_ENUM)
    assert event["direction_label_enum"] == list(glt.STATE_LABEL_ENUM)
    assert event["quality_enum"] == list(glt.QUALITY_LABEL_ENUM)
    assert payload["quality"]["event_quality_enum"] == list(glt.QUALITY_LABEL_ENUM)
    assert state["label"] in state["label_enum"]
    assert event["direction_label"] in event["direction_label_enum"]
    assert event["quality"] in event["quality_enum"]
    assert payload["quality"]["event_quality"] in payload["quality"]["event_quality_enum"]


# --------------------------------------------------------------------------
# T23 — the nightly builder is atomic, idempotent, refuses stale/backdated
# promotion with visible receipts, and bounds --asof replay.
# --------------------------------------------------------------------------

import copy
import hashlib
import os
import sys
from datetime import timedelta

import scripts.build_global_liquidity_transmission as glt_builder_mod
from engine.market_os.macro_workspaces import liquidity_central_banks as lcb


def _t23_history():
    idx = pd.date_range("2018-01-03", periods=40, freq="W-WED")
    return pd.DataFrame(
        {
            "monetary_stance": np.linspace(-1.0, 1.0, 40),
            "monetary_impulse": np.sin(np.arange(40) / 5.0),
        },
        index=idx,
    )


def _t23_payload() -> dict:
    clocks = {
        "first_known_at": "2026-10-08T06:00:00Z",
        "evidence_available_at": "2026-10-08T00:00:00Z",
        "monetary_release_at": "2026-10-07T00:00:00Z",
        "release_at": "2026-10-08T00:00:00Z",
        "adapter_observed_at_field": "evidence_available_at",
        "adapter_known_at_field": "first_known_at",
    }
    return {
        "meta": {
            "schema": "global_liquidity_transmission.v1",
            "producer_version": "t23stub.1",
            "model_version": "glt_state.v1",
            "data_version": "glt_data:t23stub",
            "source_snapshot_hash": "a" * 64,
            "config_hash": "c0ffee01",
            "pit_policy": "stub",
            "revision_law": "append_only",
        },
        "state": {
            "asof": "2026-10-07",
            "monetary_impulse": 0.2,
            "monetary_impulse_z": 1.1,
            "monetary_stance": 0.4,
            "liquidity_breadth": 1.0,
            "usd_funding_impulse": -0.1,
            "label": "expansion",
            "event_reference": {
                "producer_schema": "global_liquidity_transmission.v1",
                "state_family": "monetary_impulse",
                "shock_type": "policy_liquidity_impulse",
                "direction": 1,
                "direction_label": "expansion",
                "quality": "ok",
                "breadth": 1.0,
                "confidence": 1.0,
                "coverage": 1.0,
                "freshness": "fresh",
                "magnitude": 0.2,
                "magnitude_z": 1.1,
                "clocks": dict(clocks),
                "source_snapshot_hash": "a" * 64,
                "data_version": "glt_data:t23stub",
            },
        },
        "quality": {
            "status": "ok",
            "degraded": False,
            "confidence": 1.0,
            "event_quality": "ok",
            "missing_or_stale": [],
        },
        "freshness": {
            "asof": "2026-10-07",
            "status": "fresh",
            "degraded": False,
            "monetary_coverage_ratio": 1.0,
            "funding_coverage_ratio": 1.0,
            "component_snapshot": {},
            "clocks": dict(clocks),
            "components": {
                "monetary": {
                    "fed": {"reference_date": "2026-10-07", "available_date": "2026-10-08", "status": "usable"},
                    "ecb": {"reference_date": "2026-10-07", "available_date": "2026-10-08", "status": "usable"},
                },
                "usd_funding": {
                    "broad_dollar": {"reference_date": "2026-10-07", "available_date": "2026-10-08", "status": "usable"},
                },
            },
        },
    }


class _T23Harness:
    def __init__(self, mod, tmp_path):
        self.mod = mod
        self.tmp_path = tmp_path
        self.next_payload = None

    def payload(self) -> dict:
        return copy.deepcopy(_t23_payload())

    def set_next(self, payload: dict) -> None:
        self.next_payload = payload

    def run(self, asof=None, out=None):
        return self.mod.build(asof=asof, out=out)

    def contract(self) -> dict:
        return json.loads(self.mod.CONTRACT_PATH.read_text())

    def paths(self):
        return [self.mod.CONTRACT_PATH, self.mod.HISTORY_PATH,
                self.mod.HISTORY_META_PATH, self.mod.COMPARISON_PATH]


@pytest.fixture
def glt_builder(tmp_path, monkeypatch):
    mod = glt_builder_mod
    monkeypatch.setattr(mod, "CONTRACT_PATH", tmp_path / "global_liquidity_transmission.json")
    monkeypatch.setattr(mod, "HISTORY_PATH", tmp_path / "state_history.parquet")
    monkeypatch.setattr(mod, "HISTORY_META_PATH", tmp_path / "state_history_meta.json")
    monkeypatch.setattr(mod, "COMPARISON_PATH", tmp_path / "factor_comparison_btc_4w.json")
    monkeypatch.setattr(mod, "load_producer_config", lambda: {})
    monkeypatch.setattr(mod.store, "read", lambda provider, sid: None)
    harness = _T23Harness(mod, tmp_path)
    harness.set_next(harness.payload())

    def _stub_contract(**kwargs):
        payload = copy.deepcopy(harness.next_payload)
        payload["meta"]["generated_at"] = kwargs["generated_at"].isoformat()
        return payload, _t23_history()

    monkeypatch.setattr(mod, "build_contract", _stub_contract)
    return harness


def test_t23_atomic_write_leaves_no_partial_artifact(glt_builder, monkeypatch):
    glt_builder.run()  # seed the stored artifact set
    before = glt_builder.mod.CONTRACT_PATH.read_bytes()

    real_replace = os.replace
    contract_path = glt_builder.mod.CONTRACT_PATH

    def _replace(src, dst):
        if Path(dst) == contract_path:
            raise OSError("simulated replace failure on the contract")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _replace)
    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64  # force a fresh write
    glt_builder.set_next(payload)
    with pytest.raises(OSError):
        glt_builder.run()

    assert glt_builder.mod.CONTRACT_PATH.read_bytes() == before
    leftovers = [p.name for p in glt_builder.tmp_path.iterdir() if ".tmp-" in p.name]
    assert leftovers == []


def test_t23_idempotent_same_asof_and_hash_writes_nothing(glt_builder, capsys):
    glt_builder.run()
    snap = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in glt_builder.paths()}
    rows_before = len(pd.read_parquet(glt_builder.mod.HISTORY_PATH))

    capsys.readouterr()
    glt_builder.run()  # identical asof + source_snapshot_hash
    out = capsys.readouterr().out

    for p in glt_builder.paths():
        assert (p.read_bytes(), p.stat().st_mtime_ns) == snap[p]
    assert len(pd.read_parquet(glt_builder.mod.HISTORY_PATH)) == rows_before
    notices = [ln for ln in out.splitlines() if ln.startswith("::notice title=glt-nightly::")]
    assert len(notices) == 1 and "outcome=unchanged" in notices[0]


def test_t23_new_hash_same_evidence_carries_first_known_at(glt_builder):
    glt_builder.run()
    previous_fk = glt_builder.contract()["state"]["event_reference"]["clocks"]["first_known_at"]

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64
    payload["state"]["event_reference"]["source_snapshot_hash"] = "b" * 64
    payload["state"]["event_reference"]["clocks"]["first_known_at"] = "2026-10-16T06:00:00Z"
    payload["freshness"]["clocks"]["first_known_at"] = "2026-10-16T06:00:00Z"
    glt_builder.set_next(payload)
    glt_builder.run()

    contract = glt_builder.contract()
    assert contract["meta"]["source_snapshot_hash"] == "b" * 64
    assert contract["state"]["event_reference"]["clocks"]["first_known_at"] == previous_fk
    assert contract["freshness"]["clocks"]["first_known_at"] == previous_fk


def test_t23_stale_source_promotion_refused(glt_builder, capsys):
    glt_builder.run()
    previous_bytes = glt_builder.mod.CONTRACT_PATH.read_bytes()

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64
    payload["freshness"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    payload["state"]["event_reference"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    glt_builder.set_next(payload)
    capsys.readouterr()
    glt_builder.run()
    out = capsys.readouterr().out
    refused = [ln for ln in out.splitlines() if ln.startswith("::warning title=glt-stale-source-refused::")]
    assert len(refused) == 1
    assert "evidence_available_at" in refused[0]
    assert glt_builder.mod.CONTRACT_PATH.read_bytes() == previous_bytes
    assert any(ln.startswith("::notice title=glt-nightly::") and "outcome=refused" in ln
               for ln in out.splitlines())

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "c" * 64
    payload["state"]["asof"] = "2026-10-06"
    payload["freshness"]["asof"] = "2026-10-06"
    glt_builder.set_next(payload)
    capsys.readouterr()
    glt_builder.run()
    out = capsys.readouterr().out
    refused = [ln for ln in out.splitlines() if ln.startswith("::warning title=glt-stale-source-refused::")]
    assert len(refused) == 1 and "state.asof" in refused[0]
    assert glt_builder.mod.CONTRACT_PATH.read_bytes() == previous_bytes


def test_t23_backdated_receipt_refused_keeps_previous(glt_builder, capsys):
    glt_builder.run()
    previous_bytes = glt_builder.mod.CONTRACT_PATH.read_bytes()

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64
    payload["freshness"]["components"]["monetary"]["fed"]["available_date"] = "2026-10-06"
    glt_builder.set_next(payload)
    capsys.readouterr()
    glt_builder.run()
    out = capsys.readouterr().out
    refused = [ln for ln in out.splitlines() if ln.startswith("::warning title=glt-backdated-receipt-refused::")]
    assert len(refused) == 1 and "monetary.fed.available_date" in refused[0]
    assert glt_builder.mod.CONTRACT_PATH.read_bytes() == previous_bytes
    assert any(ln.startswith("::notice title=glt-nightly::") and "outcome=refused" in ln
               for ln in out.splitlines())


def test_t23_future_clock_not_inherited_c11(glt_builder, capsys):
    glt_builder.run()
    future_fk = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    contract = glt_builder.contract()
    contract["state"]["event_reference"]["clocks"]["first_known_at"] = future_fk
    contract["freshness"]["clocks"]["first_known_at"] = future_fk
    glt_builder.mod.CONTRACT_PATH.write_text(json.dumps(contract))

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64
    payload["state"]["event_reference"]["source_snapshot_hash"] = "b" * 64
    glt_builder.set_next(payload)
    capsys.readouterr()
    glt_builder.run()
    out = capsys.readouterr().out

    assert len([ln for ln in out.splitlines()
                if ln.startswith("::warning title=glt-future-clock-refused::")]) == 1
    fresh = glt_builder.contract()
    fresh_fk = _t23_payload()["state"]["event_reference"]["clocks"]["first_known_at"]
    assert fresh["state"]["event_reference"]["clocks"]["first_known_at"] == fresh_fk
    assert fresh["freshness"]["clocks"]["first_known_at"] == fresh_fk


def test_t23_aged_rerun_keeps_first_known_and_reads_stale_c11(glt_builder):
    glt_builder.run()
    previous_fk = glt_builder.contract()["state"]["event_reference"]["clocks"]["first_known_at"]

    payload = glt_builder.payload()  # same hash, asof moved
    payload["state"]["asof"] = "2026-10-09"
    payload["freshness"]["asof"] = "2026-10-09"
    glt_builder.set_next(payload)
    glt_builder.run()

    contract = glt_builder.contract()
    assert contract["state"]["asof"] == "2026-10-09"
    assert contract["state"]["event_reference"]["clocks"]["first_known_at"] == previous_fk
    assert contract["freshness"]["clocks"]["first_known_at"] == previous_fk

    # The LCB composer, fed that artifact 12 days after its asof, reads STALE_SOURCE
    # (same compose-call pattern as test_global_liquidity_transmission_liveness_v2).
    body = lcb.compose(contract, {}, built_at="2026-10-21")
    rows = {row.get("source_id"): row for row in body["sources"]["items"]}
    assert rows["glt_state"]["freshness"] == "STALE_SOURCE"


def test_t23_replay_asof_bounded_and_never_rewrites_store(glt_builder, monkeypatch, capsys):
    mod = glt_builder.mod
    glt_builder.run()
    stored = glt_builder.paths()
    digests = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in stored}

    def _main(*argv):
        monkeypatch.setattr(sys, "argv", ["build_global_liquidity_transmission", *argv])
        return mod.main()

    out = glt_builder.tmp_path / "replay.json"
    assert _main("--asof", "2015-01-01", "--out", str(out)) == 2  # before first_asof
    assert not out.exists()
    assert _main("--asof", "2026-10-07") == 2  # missing --out
    assert _main("--asof", "2026-10-07", "--out", str(mod.ROOT / "site" / "liquiditydata" / "replay.json")) == 2
    assert not (mod.ROOT / "site" / "liquiditydata" / "replay.json").exists()
    assert capsys.readouterr().err.count("\n") >= 3  # one-line stderr error each

    assert _main("--asof", "2018-02-07", "--out", str(out)) == 0
    assert out.exists()
    assert json.loads(out.read_text())["meta"]["source_snapshot_hash"] == "a" * 64
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in stored} == digests
    assert not any(".tmp-" in p.name for p in glt_builder.tmp_path.iterdir())


def test_t23_exactly_one_notice_per_run(glt_builder, monkeypatch, capsys):
    def _notices():
        return [ln for ln in capsys.readouterr().out.splitlines()
                if ln.startswith("::notice title=glt-nightly::")]

    monkeypatch.setattr(sys, "argv", ["build_global_liquidity_transmission"])
    capsys.readouterr()
    assert glt_builder.mod.main() == 0  # written, through the nightly main() path
    notices = _notices()
    assert len(notices) == 1 and "outcome=written" in notices[0]

    capsys.readouterr()
    glt_builder.run()  # unchanged, through build()
    notices = _notices()
    assert len(notices) == 1 and "outcome=unchanged" in notices[0]

    payload = glt_builder.payload()
    payload["meta"]["source_snapshot_hash"] = "b" * 64
    payload["freshness"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    payload["state"]["event_reference"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    glt_builder.set_next(payload)
    capsys.readouterr()
    glt_builder.run()  # refused, through build()
    notices = _notices()
    assert len(notices) == 1 and "outcome=refused" in notices[0]

    capsys.readouterr()
    glt_builder.run(asof="2018-02-07", out=str(glt_builder.tmp_path / "replay.json"))
    notices = _notices()  # replayed, through build()
    assert len(notices) == 1 and "outcome=replayed" in notices[0]


def test_t23_unchanged_and_refused_notice_reports_the_kept_artifact(glt_builder, capsys):
    """The run's one notice describes the artifact of record. The producer stamps a fresh
    first_known_at on every candidate (the source hash excludes it), so an unchanged or a
    refused run must never report the unwritten candidate's clock."""
    glt_builder.run()
    stored = glt_builder.contract()
    stored_fk = stored["state"]["event_reference"]["clocks"]["first_known_at"]

    def _notice_and_result(payload):
        glt_builder.set_next(payload)
        capsys.readouterr()
        result = glt_builder.run()
        notices = [ln for ln in capsys.readouterr().out.splitlines()
                   if ln.startswith("::notice title=glt-nightly::")]
        assert len(notices) == 1
        return notices[0], result

    rerun = glt_builder.payload()  # same asof + hash; candidate carries a re-stamped clock
    rerun["state"]["event_reference"]["clocks"]["first_known_at"] = "2026-10-18T06:00:00Z"
    rerun["freshness"]["clocks"]["first_known_at"] = "2026-10-18T06:00:00Z"
    notice, result = _notice_and_result(rerun)
    assert "outcome=unchanged" in notice
    assert f"first_known_at={stored_fk} " in notice
    assert result["first_known_at"] == stored_fk

    stale = glt_builder.payload()  # new hash, regressed evidence clock: refused
    stale["meta"]["source_snapshot_hash"] = "b" * 64
    stale["freshness"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    stale["state"]["event_reference"]["clocks"]["evidence_available_at"] = "2026-10-07T00:00:00Z"
    stale["state"]["event_reference"]["clocks"]["first_known_at"] = "2026-10-18T06:00:00Z"
    stale["freshness"]["clocks"]["first_known_at"] = "2026-10-18T06:00:00Z"
    notice, result = _notice_and_result(stale)
    assert "outcome=refused" in notice
    assert f"source_snapshot_hash={stored['meta']['source_snapshot_hash']} " in notice
    assert f"first_known_at={stored_fk} " in notice
    assert result["first_known_at"] == stored_fk
    assert glt_builder.contract() == stored


def test_t23_same_hash_future_clocked_artifact_is_rewritten_not_kept_c11(glt_builder, capsys):
    glt_builder.run()
    future_fk = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    contract = glt_builder.contract()
    contract["state"]["event_reference"]["clocks"]["first_known_at"] = future_fk
    contract["freshness"]["clocks"]["first_known_at"] = future_fk
    glt_builder.mod.CONTRACT_PATH.write_text(json.dumps(contract))

    glt_builder.set_next(glt_builder.payload())  # same asof + same source hash
    capsys.readouterr()
    result = glt_builder.run()
    out = capsys.readouterr().out

    assert len([ln for ln in out.splitlines()
                if ln.startswith("::warning title=glt-future-clock-refused::")]) == 1
    notices = [ln for ln in out.splitlines() if ln.startswith("::notice title=glt-nightly::")]
    assert len(notices) == 1 and "outcome=written" in notices[0] and future_fk not in notices[0]
    assert result["outcome"] == "written"
    fresh_fk = _t23_payload()["state"]["event_reference"]["clocks"]["first_known_at"]
    stored = glt_builder.contract()
    assert stored["state"]["event_reference"]["clocks"]["first_known_at"] == fresh_fk
    assert stored["freshness"]["clocks"]["first_known_at"] == fresh_fk
