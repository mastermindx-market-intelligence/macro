"""Captured configuration/calibration projections through their incumbent owners."""
from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import cycles, conditions, vol_regime, theme_scoring, narrative_rotation as narrative
from engine import sector_central as central, sector_basket_documents as documents
from lib import config
from tests.fixtures import base_cycles_capture_normalizers_84f1b72 as old_cycles
from tests.fixtures import base_vol_regime_capture_normalizers_84f1b72 as old_vol
from tests.fixtures import base_theme_scoring_capture_normalizers_84f1b72 as old_theme
from tests.fixtures import base_narrative_rotation_capture_normalizers_84f1b72 as old_narrative
from tests.fixtures import base_sector_central_capture_normalizers_84f1b72 as old_central
from tests.test_sector_document_composition import captured


def forbidden(*args, **kwargs):
    raise AssertionError("Ambient source/configuration reached")


@pytest.mark.parametrize("document", [
    {}, None, [], {"risk_size_mult": None},
    {"risk_size_mult": {"us_sector": {"early": .2, "late": 2, "ready": {"risk_size_mult": .8}}}},
    {"risk_size_mult": {"country": {"ready": {}, "late": "1.2"}}, "mult_clamp": [.7, 1.1]},
    {"risk_size_mult": {"us_sector": {"good": .7, "bad": {"risk_size_mult": "bad"}}}},
    {"risk_size_mult": {"us_sector": {"good": .7, "bad": None}}},
    {"risk_size_mult": {"us_sector": "bad"}},
    {"risk_size_mult": {"us_sector": {"early": .2}}, "mult_clamp": [1]},
    {"risk_size_mult": {"us_sector": {"early": .8}}, "validated": False, "any_cell_bound": False},
])
def test_risk_document_projection_matches_literal_original(document, tmp_path, monkeypatch):
    path = tmp_path / "regime" / "ladder_risk_calibration.json"
    path.parent.mkdir()
    path.write_text(json.dumps(document))
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    before = deepcopy(document)
    expected = old_cycles._load_risk_calib()
    assert cycles._load_risk_calib() == expected
    assert cycles.risk_calibration_from_document(document) == expected
    assert document == before


@pytest.mark.parametrize("family", [None, "unknown", "country", "sector", "equity", "us_sector"])
def test_risk_lookup_aliases_and_defaults_match_original(family, monkeypatch):
    risk = {"us_sector": {"EARLY": .8}, "country": {"EARLY": .9}}
    for key, value in {"_CALCULATION_INPUTS": cycles._CALCULATION_INPUTS,
                       "_RISK_FAMILY_ALIAS": cycles._RISK_FAMILY_ALIAS,
                       "_RISK_CALIB": risk, "_RISK_CALIB_LOADED": True,
                       "_RISK_CALIB_LOGGED": set()}.items():
        monkeypatch.setattr(old_cycles, key, value, raising=False)
    assert cycles.risk_size_mult_from_inputs("EARLY", family, risk_calibration=risk) == old_cycles.risk_size_mult("EARLY", family)
    assert cycles.risk_size_mult_from_inputs("UNKNOWN", family, risk_calibration=risk) == 1.0


def test_removed_entry_setting_uses_source_default_not_warmed_import(monkeypatch):
    monkeypatch.setattr(config, "load", lambda: {"engine": {"entry_gate": {}}})
    monkeypatch.setattr(cycles, "_load_fitted_bands", lambda: {})
    monkeypatch.setattr(cycles, "_load_risk_calib", lambda: {})
    monkeypatch.setattr(vol_regime, "load_overlay_gate", lambda: {})
    monkeypatch.setattr(cycles.session_anchor, "capture_reference_sessions",
                        lambda *a, **k: pd.DatetimeIndex(["2026-11-05"]))
    monkeypatch.setattr(cycles, "_EG_STOCH_OS", 20.0)
    for key in ("CycleCalculationInputs", "normalize_evaluation_date", "session_anchor",
                "_load_fitted_bands", "_load_risk_calib", "_EG_STOCH_OS", "_EG_STOCH_OB",
                "_EG_DAILY_RSI_MAX", "_EG_STRETCH_BLOCK", "_EG_APPROACH_DAYS", "_EG_OSC_EXEMPT_BELOW"):
        monkeypatch.setattr(old_cycles, key, getattr(cycles, key), raising=False)
    original = old_cycles.acquire_calculation_inputs(evaluation_date="2026-11-05")
    corrected = cycles.acquire_calculation_inputs(evaluation_date="2026-11-05")
    assert original.entry_gate["stoch_oversold"] == 20
    assert corrected.entry_gate["stoch_oversold"] == 25
    assert cycles._EG_STOCH_OS == 20  # Unbound legacy behavior is not overwritten.


@pytest.mark.parametrize("entry", [{"stoch_oversold": None}, {"approach_days": "bad"}])
def test_explicit_invalid_entry_setting_is_not_defaulted(entry):
    with pytest.raises((TypeError, ValueError)):
        cycles.effective_entry_settings_from_inputs(entry)


def test_entry_coercions_and_source_defaults_are_detached():
    settings = {"stoch_oversold": "22", "approach_days": 3.9}
    result = cycles.effective_entry_settings_from_inputs(settings)
    assert result == {"stoch_oversold": 22.0, "stoch_overbought": 80.0,
        "daily_rsi_extension_cap": 62.0, "stretch_block_pct": 30.0,
        "approach_days": 3, "overextended_osc_exempt_below_pct": -10.0}
    assert settings == {"stoch_oversold": "22", "approach_days": 3.9}


@pytest.mark.parametrize("site,regime", [
    ({"snapshot": {"asof": "2026-10-01", "regime": "warning"}},
     {"vol_regime": {"asof": "2026-11-05", "regime": "calm"}}),
    ({"snapshot": {"available": False}}, {"vol_regime": {"regime": "warning"}}),
    ({"snapshot": {}}, {"vol_regime": {"regime": "warning"}}),
    ({"snapshot": []}, {"vol_regime": {"regime": "calm"}}),
    (["invalid"], {"vol_regime": {"regime": "calm"}}),
    (None, None), ({}, {}),
])
def test_volatility_snapshot_priority_matches_original(site, regime, tmp_path):
    sp, dp = tmp_path / "site", tmp_path / "data"
    (sp / "vol").mkdir(parents=True)
    (dp / "regime").mkdir(parents=True)
    (sp / "vol/regime.json").write_text(json.dumps(site))
    (dp / "regime/latest.json").write_text(json.dumps(regime))
    expected = old_vol.published_snapshot(data_dir=dp, site_dir=sp)
    assert vol_regime.published_snapshot(data_dir=dp, site_dir=sp) == expected
    assert vol_regime.published_snapshot_from_documents(site_document=site, regime_document=regime) == expected


@pytest.mark.parametrize("gate", [None, [], {}, {"regime_marginal_over_voltarget": True},
    {"regime_marginal_over_voltarget": False, "live_overlay_helps": True}])
def test_overlay_gate_preserves_original_closed_fallback(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(old_vol, "OVERLAY_GATE_PATH", vol_regime.OVERLAY_GATE_PATH, raising=False)
    path = tmp_path / vol_regime.OVERLAY_GATE_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(gate))
    expected = old_vol.load_overlay_gate(data_dir=tmp_path)
    assert vol_regime.load_overlay_gate(data_dir=tmp_path) == expected
    assert vol_regime.overlay_gate_from_document(gate) == expected


@pytest.mark.parametrize("settings", [None, [], {}, {"gross_floor": .5, "enabled": False}, {"warning_haircut": .8}])
def test_overlay_config_preserves_original_defaults(settings, monkeypatch):
    monkeypatch.setattr(old_vol, "OVERLAY_DEFAULTS", deepcopy(vol_regime.OVERLAY_DEFAULTS), raising=False)
    monkeypatch.setattr(config, "load", lambda: {"engine": {"vol_regime_overlay": settings}})
    expected = old_vol.overlay_config()
    assert vol_regime.overlay_config() == expected == vol_regime.overlay_config_from_inputs(settings)


@pytest.mark.parametrize("document", [None, [], {}, {"verdict": None, "sizing": None},
    {"verdict": [], "sizing": []}, {"verdict": {"fading": {"verdict": "measurable_edge"}},
                                 "sizing": {"verdict": "display_only"}}])
def test_theme_and_narrative_use_one_captured_basket_calibration(document, tmp_path, monkeypatch):
    path = tmp_path / "strategies/baskets_calibration.json"
    path.parent.mkdir()
    path.write_text(json.dumps(document))
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    assert theme_scoring._signal_calibration() == old_theme._signal_calibration()
    assert narrative._sizing_calibration() == old_narrative._sizing_calibration()
    assert theme_scoring.signal_calibration_from_document(document) == old_theme._signal_calibration()
    assert narrative.sizing_calibration_from_document(document) == old_narrative._sizing_calibration()


@pytest.mark.parametrize("beta,risk", [
    ({"XLK": .8}, {"us_sector": {"EARLY": .7}}),
    ({" information technology ": -.2}, {"us_sector": {"EARLY": .7}}),
    ({"XLK": "bad"}, {"us_sector": {"EARLY": .7}}),
    ({"XLK": .8}, {"us_sector": "bad"}),
    ({}, {}),
])
def test_fusion_independent_defaults_match_literal_original(beta, risk, monkeypatch):
    rec = {"kind": "sector", "ticker": "XLK", "name": "Information Technology", "now": {"timing_state": "EARLY"}}
    monkeypatch.setattr(old_central, "fusion_calibration_key", central.fusion_calibration_key, raising=False)
    monkeypatch.setattr(conditions, "sector_macro_beta",
                        lambda key: conditions.sector_macro_beta_from_inputs(key, table=beta))
    monkeypatch.setattr(cycles, "risk_size_mult",
                        lambda state, family: cycles.risk_size_mult_from_inputs(state, family, risk_calibration=risk))
    expected = old_central._resolve_fusion_calibration(rec)
    assert central._resolve_fusion_calibration(rec) == expected
    assert central.fusion_calibration_from_inputs(rec, macro_beta_table=beta, risk_calibration=risk) == expected


def test_captured_helpers_and_sizing_do_not_load_or_mutate_globals(monkeypatch):
    risk_cache, fitted_cache = deepcopy(cycles._RISK_CALIB), deepcopy(cycles._FITTED_BANDS)
    with monkeypatch.context() as mp:
        mp.setattr(config, "load", forbidden)
        mp.setattr(config, "data_dir", forbidden)
        mp.setattr(Path, "read_text", forbidden)
        mp.setattr(vol_regime, "load_overlay_gate", forbidden)
        gate = vol_regime.overlay_gate_from_document({})
        snap = vol_regime.published_snapshot_from_documents(
            site_document={"snapshot": {"regime": "warning", "vol_target_scalar": .8}}, regime_document={})
        size = vol_regime.sizing_overlay(snap, vol_regime.overlay_config_from_inputs({}), overlay_gate=gate)
        assert size["gross_scalar"] == .8 and not vol_regime.regime_caution_scored(gate=gate)
        assert cycles.risk_calibration_from_document({"risk_size_mult": {"us_sector": {"EARLY": .8}}})
        assert cycles.effective_entry_settings_from_inputs({})["stoch_oversold"] == 25
        assert central.fusion_calibration_from_inputs(
            {"kind": "sector", "ticker": "XLK", "now": {"timing_state": "EARLY"}},
            macro_beta_table={"XLK": .5}, risk_calibration={"us_sector": {"EARLY": .8}}) == (.5, .8)
    assert cycles._RISK_CALIB == risk_cache and cycles._FITTED_BANDS == fitted_cache


def test_real_composer_derives_fusion_from_actual_cycle_spine_and_shared_risk(monkeypatch):
    args = captured()
    original = documents.compose_sector_documents(**args)
    table = {key[0]: value[0] for key, value in args["context"].fusion_calibrations.items() if key[0]}
    args["context"] = replace(args["context"], fusion_calibrations={}, fusion_macro_beta_table=table)
    seen = []
    derive = central.fusion_calibrations_from_inputs
    def observe(spine, **kwargs):
        seen.append(deepcopy(kwargs["risk_calibration"]))
        assert spine["sectors"]
        return derive(spine, **kwargs)
    monkeypatch.setattr(central, "fusion_calibrations_from_inputs", observe)
    actual = documents.compose_sector_documents(**args)
    assert dict(actual.member_bytes) == dict(original.member_bytes)
    assert seen == [args["cycle_inputs"].calculation_inputs.risk_calibration]


@pytest.mark.parametrize("table", [{}, [], "invalid"])
def test_ambiguous_or_invalid_fusion_source_refuses_before_calculation(monkeypatch, table):
    from engine import baskets
    args = captured()
    args["context"] = replace(args["context"], fusion_macro_beta_table=table)
    monkeypatch.setattr(baskets, "compute_baskets_from_inputs", forbidden)
    with pytest.raises(ValueError, match="ambiguous_or_invalid_fusion_source"):
        documents.compose_sector_documents(**args)
