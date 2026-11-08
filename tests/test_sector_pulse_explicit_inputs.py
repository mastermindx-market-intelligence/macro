"""Pure Pulse parity against literal source and observation-clock counterexamples."""
from copy import deepcopy
from datetime import date
import importlib.util
from pathlib import Path

import pytest

from engine import sector_pulse as pulse
from lib.nyse_calendar import session_n_back


def fixture_module():
    path = Path(__file__).parent / "fixtures/base_sector_pulse_7885.py"
    spec = importlib.util.spec_from_file_location("base_sector_pulse_7885", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def captured(case="normal"):
    themes = []
    for i, label in enumerate(("dominant", "fading", "deteriorating", "emerging", "forming", "dominant"), 1):
        themes.append({"id": f"theme{i}", "name": f"Theme {i}", "name_zh": f"主题{i}",
            "category": "Fixture", "rank": i, "score": 91-i*3, "label": label, "reco": "hold",
            "perf": {"5d": {"rel": .02-i*.001}}, "net_ad": 5-i,
            "breadth": {"pct50": .8-i*.02},
            "textures": {"clean_entry": {"flag": i%2==0, "quality": .7}},
            "mtf": {"momentum_score": .7, "confluence": {"long_sign": 1}},
            "rank_5d": 123, "delta_5d": .456})
    ti = {"as_of": "2026-11-04", "themes": themes, "rotation_5d": {"climbers": [], "fallers": []}}
    archive = [{"asof": session_n_back(date(2026,11,4), offset).isoformat(),
                "themes": [{"id": th["id"], "rank": 9-i, "score": 0 if i==0 else 70+i}
                           for i, th in enumerate(themes)]}
               for offset in range(25,0,-1)]
    calibration = {
        "heating": {"verdict": "no_edge", "claim": "relative_return", "mean_pct": -.3,
                    "t_hac": -1.1, "n_days": 500, "inverted": True},
        "hot": {"verdict": "measurable_edge", "claim": "return", "mean_pct": .5, "n_days": 200},
        "cooling": {"verdict": "no_edge", "claim": "drawdown", "n_days": 300},
        "broken": {"verdict": "measurable_edge", "claim": "drawdown", "mean_pct": -2., "n_days": 250}}
    region = "us"
    if case == "empty_archive": archive = []
    elif case == "empty_calibration": calibration = {}
    elif case == "duplicate":
        duplicate = deepcopy(archive[-5]); duplicate["themes"][0]["score"] = 999
        archive.append(duplicate)
    elif case == "future_and_same_day":
        for when in ("2026-11-04", "2026-11-05"):
            archive.append({"asof": when, "themes": [{"id": "theme1", "rank": 999, "score": 999}]})
    elif case == "missing_endpoint":
        archive = [row for row in archive if row["asof"] != session_n_back(date(2026,11,4),5).isoformat()]
    elif case == "reversed": archive.reverse()
    elif case == "malformed_archive": archive.extend([None, {}, {"asof": "bad", "themes": []}])
    elif case == "ca": region = "canada"
    elif case == "non_session": ti["as_of"] = "2026-11-07"
    elif case == "invalid_date": ti["as_of"] = "2026-02-30"
    elif case == "empty_themes": ti["themes"] = []
    return ti, archive, calibration, region


@pytest.mark.parametrize("case", ["normal", "empty_archive", "empty_calibration", "duplicate",
    "future_and_same_day", "missing_endpoint", "reversed", "malformed_archive", "ca",
    "non_session", "invalid_date", "empty_themes"])
def test_complete_pulse_and_enrichment_match_literal_baseline(case, monkeypatch):
    ti, archive, calibration, region = captured(case)
    before = deepcopy((ti, archive, calibration))
    base = fixture_module()
    monkeypatch.setattr(base, "_load_archive_snapshots", lambda region: deepcopy(archive))
    monkeypatch.setattr(base, "_heat_calibration", lambda: deepcopy(calibration))
    expected = base._build_pulse_from_theme_intel(deepcopy(ti), region)
    expected_ti = deepcopy(ti)
    assert base.merge_pulse_into_theme_intel(expected_ti, region) is None
    actual_ti, actual = pulse.enrich_theme_intel_from_inputs(ti, region,
        archive_snapshots=archive, heat_calibration=calibration)
    assert actual == expected
    assert actual_ti == expected_ti
    assert (ti, archive, calibration) == before


def test_current_clock_exact_us_endpoint_and_zero_score():
    ti, archive, calibration, region = captured()
    result = pulse.build_pulse_from_inputs(ti, region, archive_snapshots=archive, heat_calibration=calibration)
    assert result["themes"][0]["score_delta_5d"] == 88
    target = session_n_back(date(2026,11,4),5).isoformat()
    assert result["history"]["comparison_as_of"]["5d"] == target
    without = [row for row in archive if row["asof"] != target]
    missing = pulse.build_pulse_from_inputs(ti, region, archive_snapshots=without, heat_calibration=calibration)
    assert missing["themes"][0]["score_delta_5d"] is None
    assert missing["history"]["expected_comparison_as_of"]["5d"] == target
    assert missing["history"]["comparison_as_of"]["5d"] is None
    changed = deepcopy(archive)
    next(row for row in changed if row["asof"] == target)["themes"][0]["score"] = None
    null = pulse.build_pulse_from_inputs(ti, region, archive_snapshots=changed, heat_calibration=calibration)
    assert null["themes"][0]["score_delta_5d"] is None


def test_existing_fields_keep_false_zero_and_none():
    ti, archive, calibration, region = captured()
    retained = {"pulse_heat": None, "pulse_rank_delta_1d": 0, "pulse_rank_delta_5d": False,
                "pulse_rank_delta_20d": 991, "pulse_score_delta_5d": -123., "pulse_heat_grade": "sentinel"}
    ti["themes"][0].update(retained)
    enriched, result = pulse.enrich_theme_intel_from_inputs(ti, region,
        archive_snapshots=archive, heat_calibration=calibration)
    assert result is not None
    assert {key: enriched["themes"][0][key] for key in retained} == retained
    for key in ("rank", "score", "reco", "rank_5d", "delta_5d"):
        assert enriched["themes"][0][key] == ti["themes"][0][key]
    assert "pulse_score_delta_20d" not in enriched["themes"][0]


def test_explicit_enrichment_has_one_projection_no_effects_and_detached_values(monkeypatch):
    ti, archive, calibration, region = captured()
    before = deepcopy((ti, archive, calibration))
    attempted = []
    def forbidden(*args, **kwargs):
        attempted.append("effect")
        raise AssertionError("Pure projection reached an effect")
    for name in ("_load_theme_intel", "_load_archive_snapshots", "_heat_calibration", "_load_membership",
                 "write_pulse", "write_score_snapshot"):
        monkeypatch.setattr(pulse, name, forbidden)
    monkeypatch.setattr(pulse.log, "warning", forbidden)
    monkeypatch.setattr(pulse.log, "debug", forbidden)
    original = pulse._project_pulse_from_inputs
    projections = []
    def counted(*args, **kwargs):
        projections.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(pulse, "_project_pulse_from_inputs", counted)
    enriched, result = pulse.enrich_theme_intel_from_inputs(ti, region,
        archive_snapshots=archive, heat_calibration=calibration)
    assert result and len(projections) == 1 and attempted == []
    enriched["themes"][0]["textures"]["clean_entry"]["quality"] = -9
    result["themes"][0]["heat_strength"]["mean_pct"] = -999
    assert (ti, archive, calibration) == before


def test_optional_absence_remains_descriptive_and_unknown():
    ti, _, _, region = captured()
    enriched, result = pulse.enrich_theme_intel_from_inputs(ti, region, archive_snapshots=[], heat_calibration={})
    assert result["as_of"] == ti["as_of"]
    assert result["heat_grades"] == {}
    assert result["themes"][0]["heat"] == "hot"
    assert result["themes"][0]["rank_delta_5d"] is None
    assert result["themes"][0]["heat_strength"] is None
    assert enriched["themes"][0]["pulse_heat_grade"] is None


@pytest.mark.parametrize("ti", [None, {}, {"themes": []}, {"as_of": "bad", "themes": [{"id": "x"}]}])
def test_legacy_empty_or_invalid_observation_never_acquires(ti, monkeypatch):
    calls = []
    monkeypatch.setattr(pulse, "_load_archive_snapshots", lambda region: calls.append("archive") or [])
    monkeypatch.setattr(pulse, "_heat_calibration", lambda: calls.append("calibration") or {})
    assert pulse._build_pulse_from_theme_intel(ti, "us") is None
    assert calls == []


def test_legacy_merge_keeps_in_place_contract_and_one_capture(monkeypatch):
    ti, archive, calibration, region = captured()
    expected, _ = pulse.enrich_theme_intel_from_inputs(ti, region,
        archive_snapshots=archive, heat_calibration=calibration)
    calls = []
    monkeypatch.setattr(pulse, "_load_archive_snapshots", lambda region: calls.append("archive") or archive)
    monkeypatch.setattr(pulse, "_heat_calibration", lambda: calls.append("calibration") or calibration)
    assert pulse.merge_pulse_into_theme_intel(ti, region) is None
    assert ti == expected and calls == ["archive", "calibration"]
