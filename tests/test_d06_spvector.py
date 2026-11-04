"""D06 S&P display semantics and publication boundaries; synthetic inputs only."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_spvector as spv
from tests.test_spvector_page import _spvector_vm


def test_score_dates_follow_the_actual_contributor_not_future_rows():
    source = pd.Series([0.0, 21.0, 83.0], index=pd.to_datetime(["2026-10-16", "2026-10-19", "2026-10-22"]))
    target = pd.to_datetime(["2026-10-16", "2026-10-19", "2026-10-20"])
    state = spv._score_reading(source, source.reindex(target, method="ffill"))
    assert state == {"score": 21, "score_as_of": "2026-10-19",
                     "score_aligned_as_of": "2026-10-20", "score_current_available": True}


def test_missing_latest_score_keeps_last_known_date_but_is_not_current():
    source = pd.Series([0.0, np.nan], index=pd.to_datetime(["2026-10-19", "2026-10-20"]))
    assert spv._score_reading(source, source) == {
        "score": 0, "score_as_of": "2026-10-19",
        "score_aligned_as_of": "2026-10-19", "score_current_available": False}


@pytest.mark.parametrize("values", [[np.nan, np.inf], [None, None], [True, False], ["0", "12"]])
def test_unusable_score_is_never_zero(values):
    source = pd.Series(values, index=pd.to_datetime(["2026-10-19", "2026-10-20"]))
    state = spv._score_reading(source, source)
    assert state["score"] is None
    assert state["score_as_of"] is None
    assert state["score_current_available"] is False


def test_zero_is_a_real_numeric_reading():
    s = pd.Series([4.0, 0.0, np.nan], index=pd.to_datetime(["2026-10-16", "2026-10-19", "2026-10-20"]))
    assert spv._number_reading(s) == (0.0, "2026-10-19")


def test_shadow_weight_is_recorded_only_and_rationale_is_escaped():
    vm = copy.deepcopy(_spvector_vm())
    vm.update(overlay={"enabled": True, "veto": True, "overlay_weight": .66,
                       "mechanical_weight": 1.0, "veto_reason": "<script>trade()</script>",
                       "note": ""})
    html = spv.render_page(vm)
    hero = html.split('id="spv-allocation"', 1)[1].split('id="spv-model-readings"', 1)[0]
    shadow = html.split('id="spv-shadow"', 1)[1].split('id="spv-breakdown"', 1)[0]
    assert 'data-equity-weight="100"' in hero
    assert "66%" not in hero.split('class="allocation-split"', 1)[1].split('class="allocbar"', 1)[0]
    assert "66%" in shadow and "100%" in shadow
    assert "Not applied to allocation" in shadow
    assert "&lt;script&gt;trade()&lt;/script&gt;" in shadow
    for old in ("Live recommendation", "veto active", "No DeepSeek key", "verified edge", "p=0.0"):
        assert old not in html


def test_known_zero_false_and_unknown_are_different_rendered_states():
    vm = copy.deepcopy(_spvector_vm())
    vm["disloc"].update(capitulation=0, put_absent=False)
    html = spv.render_page(vm)
    chips = html.split('<div class="chips">', 1)[1].split('</div>', 1)[0]
    assert "0/3" in chips and "false" in chips
    vm["disloc"].update(cap_available=False, put_available=False, gate_model_available=False)
    html = spv.render_page(vm)
    chips = html.split('<div class="chips">', 1)[1].split('</div>', 1)[0]
    assert "0/3" not in chips and "false" not in chips
    assert "Unavailable" in chips
    assert "Underlying input freshness and completeness are not supplied" in html


def test_headline_and_breakdown_keep_their_own_dates_and_values():
    vm = copy.deepcopy(_spvector_vm())
    vm.update(score=21, score_as_of="2026-10-19", score_aligned_as_of="2026-10-20",
              legs_score=24.8, legs_as_of="2026-10-21")
    html = spv.render_page(vm)
    headline = html.split('id="spv-model-readings"', 1)[1].split('id="spv-study"', 1)[0]
    breakdown = html.split('id="spv-breakdown"', 1)[1].split('id="spv-history"', 1)[0]
    assert "2026-10-19" in headline and "2026-10-20" in headline
    assert "2026-10-21" in breakdown and "24.8" in breakdown
    assert "Pub lag" not in breakdown
    assert "Model lag · trading days" in breakdown


def _stub_build(monkeypatch, tmp_path, scores, *, missing_flags=False):
    from engine import inputs, conditions, dislocation, spvector_overlay
    from lib import store
    idx = pd.date_range("2026-10-19", periods=3, freq="B")
    spy = pd.Series([100., 102., 103.], index=idx)
    alloc = pd.Series([1., 1., 1.], index=idx)
    rs = pd.Series(scores, index=idx)
    cf = pd.DataFrame({"capitulation_score": [np.nan]*3 if missing_flags else [1., 0., 0.]}, index=idx)
    msf = pd.DataFrame(index=idx) if missing_flags else pd.DataFrame(
        {"put_absent": [False]*3, "recession": [False]*3, "fedput_off": [False]*3}, index=idx)
    fixture = _spvector_vm()
    calls = []
    captured = {}
    data = tmp_path / "data"
    data.mkdir()
    snap = data / "regime/spvector_latest.json"
    snap.parent.mkdir()
    snap.write_bytes(b'{"accepted":"last-good"}')
    initial = (snap.read_bytes(), snap.stat().st_mtime_ns)
    monkeypatch.setattr(spv.config, "ROOT", tmp_path)
    monkeypatch.setattr(spv.config, "data_dir", lambda: data)
    monkeypatch.setattr(inputs, "build_features", lambda: pd.DataFrame(index=idx))
    monkeypatch.setattr(conditions, "conditions_frame", lambda f: cf)
    monkeypatch.setattr(dislocation, "master_switch_frame", lambda f: msf)
    monkeypatch.setattr(store, "read", lambda *args: pd.DataFrame(index=idx))
    monkeypatch.setattr(spv.ea, "index_close", lambda ticker: spy)
    monkeypatch.setattr(spv.ea, "bill_yield", lambda: pd.Series(.04, index=idx))
    monkeypatch.setattr(spv.ea, "risk_score", lambda *args: rs)
    monkeypatch.setattr(spv.ea, "risk_legs", lambda *args: {"score": pd.Series([24.8], index=[idx[-1]]), "legs": {}})
    monkeypatch.setattr(spv.ea, "vector_alloc", lambda *args, **kwargs: alloc)
    monkeypatch.setattr(spv.ea, "summarize", lambda *args, **kwargs: copy.deepcopy(fixture["sc"]))
    monkeypatch.setattr(spv.ea, "after_tax", lambda *args, **kwargs: copy.deepcopy(fixture["at"]))
    monkeypatch.setattr(spv.ea, "bear_episodes", lambda *args: [])
    monkeypatch.setattr(spv.ea, "glide_path", lambda *args: alloc)
    monkeypatch.setattr(spv, "backtest_core", lambda *args, **kwargs: {"net": pd.Series([0., .02, .01], index=idx), "hold": pd.Series([0., .02, .01], index=idx)})
    for name in ("_chart_strategy", "_chart_growth", "_chart_dd"):
        monkeypatch.setattr(spv, name, lambda *args: "<div>chart fixture</div>")
    def context_snapshot(**kwargs):
        calls.append("context")
        return {}
    def live_overlay(*args, **kwargs):
        calls.append("evaluate")
        return {"enabled": True, "veto": True, "mechanical_weight": 1., "overlay_weight": .66, "note": "fixture"}
    def log_overlay(overlay, asof):
        calls.append("log")
        log = data / "spvector/overlay_log.jsonl"
        log.parent.mkdir()
        log.write_text(json.dumps({"asof": asof, "veto": True})+"\n")
    monkeypatch.setattr(spvector_overlay, "context_snapshot", context_snapshot)
    monkeypatch.setattr(spvector_overlay, "live_overlay", live_overlay)
    monkeypatch.setattr(spvector_overlay, "log_overlay", log_overlay)
    def render(vm):
        captured.update(vm)
        return "<!doctype html><title>fixture</title>"
    def write(path, html):
        path.parent.mkdir()
        path.write_text(html)
    monkeypatch.setattr(spv, "render_page", render)
    monkeypatch.setattr(spv, "write_page", write)
    return calls, captured, snap, initial, data


@pytest.mark.parametrize("scores,page_only", [
    ([np.nan, np.nan, np.nan], False),
    ([10., 0., np.nan], False),
    ([10., 0., 0.], True),
])
def test_page_only_or_missing_current_score_has_no_auxiliary_effects(monkeypatch, tmp_path, scores, page_only):
    calls, vm, snap, initial, data = _stub_build(monkeypatch, tmp_path, scores)
    result = spv.build(page_only=page_only)
    assert Path(result).is_file()
    assert calls == []
    assert (snap.read_bytes(), snap.stat().st_mtime_ns) == initial
    assert not (data / "spvector/overlay_log.jsonl").exists()
    assert vm["auxiliary_allowed"] is False
    if not page_only:
        assert not any(b["cur"] for b in vm["bands"])


def test_normal_current_build_retains_snapshot_contract_and_log_order(monkeypatch, tmp_path):
    calls, vm, snap, initial, data = _stub_build(monkeypatch, tmp_path, [10., 0., 0.])
    spv.build()
    assert calls == ["context", "evaluate", "log"]
    assert vm["overlay_log"]["rows"] == 1
    assert vm["overlay_log"]["vetoes"] == 1
    saved = json.loads(snap.read_text())
    assert saved["date"] == saved["asof"] == "2026-10-21"
    assert saved["score"] == saved["risk_score"] == 0
    assert saved["equity_w"] == saved["equity_weight"] == 100
    assert saved["cash_w"] == 0 and saved["band"] == "low"
    assert vm["disloc"]["cap_available"] is True
    assert vm["disloc"]["put_available"] is True
    assert vm["disloc"]["put_absent"] is False


def test_build_keeps_missing_flags_unavailable(monkeypatch, tmp_path):
    calls, vm, snap, initial, data = _stub_build(monkeypatch, tmp_path, [10., 0., 0.], missing_flags=True)
    spv.build(page_only=True)
    assert vm["disloc"]["put_available"] is False
    assert vm["disloc"]["cap_available"] is False
    assert vm["disloc"]["gate_model_available"] is False
    assert vm["disloc"]["input_coverage_qualified"] is False
