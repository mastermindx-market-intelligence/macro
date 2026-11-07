"""Literal grader parity, frozen-only history and acquisition-free calculation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import basket_freeze, sector_central_grader as grader
from tests.fixtures import base_sector_central_grader_1f3f605 as original
from tests.test_sector_central_grader_v2 import IDX, _se_frame, _call


def captured(case="stable", versions="mixed"):
    rows, paths = _se_frame()
    for pos in (1, 60, 195):
        row = _call(100 + pos, pos, None, "up", 70)
        row.update(id=f"b-a-{pos}", kind="basket", basket_id="a")
        rows.append(row)
    calls = pd.DataFrame(rows)
    if versions == "mixed": calls["score_version"] = [1 if i % 2 else 2 for i in range(len(calls))]
    elif versions == "only_v2": calls["score_version"] = 2
    elif versions == "normalized": calls["score_version"] = [None, "bad", "1", "2"] * (len(calls) // 4) + [None] * (len(calls) % 4)
    panel = pd.DataFrame(paths, index=IDX); panel["SPY"] = 100.0
    frozen = pd.DataFrame({"a__level_tr": 100 * 1.001 ** np.arange(len(IDX)),
        "a__mhash": "members-v1", "a__anchor": [None] * 40 + [str(IDX[40].date())] * (len(IDX) - 40)}, index=IDX)
    if case == "membership_changed": frozen.loc[IDX[70]:, "a__mhash"] = "members-v2"
    elif case == "missing_anchor": frozen["a__anchor"] = None
    elif case == "legacy_tail": frozen.loc[IDX[-1], "a__anchor"] = None
    elif case == "absent": frozen = None
    elif case == "empty": frozen = frozen.iloc[:0]
    return calls, panel, frozen


def canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


def legacy_result(owner, calls, panel, frozen, monkeypatch, tmp_path):
    p = tmp_path / "sector_central/calls.parquet"; p.parent.mkdir(parents=True, exist_ok=True)
    calls.to_parquet(p, index=False)
    monkeypatch.setattr(owner.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(owner, "_yahoo_panel", lambda: panel.copy(deep=True))
    monkeypatch.setattr(basket_freeze, "read_frozen", lambda domain: None if frozen is None else frozen.copy(deep=True))
    return owner.grade()


@pytest.mark.parametrize("case", ["stable", "membership_changed", "missing_anchor", "legacy_tail", "absent", "empty"])
@pytest.mark.parametrize("versions", ["none", "mixed", "only_v2", "normalized"])
def test_original_adapter_new_adapter_and_explicit_grader_match(case, versions, monkeypatch, tmp_path):
    calls, panel, frozen = captured(case, versions)
    before = legacy_result(original, calls, panel, frozen, monkeypatch, tmp_path)
    after = legacy_result(grader, calls, panel, frozen, monkeypatch, tmp_path)
    levels = grader.frozen_basket_levels_from_inputs(frozen)
    start = str(frozen.index[0].date()) if frozen is not None and not frozen.empty else None
    explicit = grader.grade_from_inputs(calls, yahoo_panel=panel, basket_levels=levels,
        frozen_df=frozen, freeze_start=start)
    assert canonical(explicit) == canonical(before) == canonical(after)
    if versions == "only_v2":
        assert explicit["available"] and explicit["n_calls"] == 0
        assert explicit["by_score_version"]["2"]["n_calls"] == len(calls)
    if case in ("missing_anchor", "legacy_tail"):
        assert not levels
        assert any(value["counts"]["excluded_pre_chain"] > 0 for value in
            (explicit["by_score_version"].get("2", explicit))["by_horizon"].values())


def test_real_grading_uses_only_captured_inputs_and_detaches_values(monkeypatch):
    calls, panel, frozen = captured()
    before = (calls.copy(deep=True), panel.copy(deep=True), frozen.copy(deep=True))
    def forbidden(*a, **k): raise AssertionError("ambient grading dependency reached")
    for owner, name in ((grader.config, "data_dir"), (grader.config, "load"),
                        (grader, "_yahoo_panel"), (grader, "_basket_levels"),
                        (grader, "append_central_log"), (basket_freeze, "read_frozen"),
                        (basket_freeze, "freeze_start_date"), (pd, "read_parquet")):
        monkeypatch.setattr(owner, name, forbidden)
    levels = grader.frozen_basket_levels_from_inputs(frozen)
    kwargs = dict(yahoo_panel=panel, basket_levels=levels, frozen_df=frozen, freeze_start=str(IDX[0].date()))
    result = grader.grade_from_inputs(calls, **kwargs)
    assert result["by_score_version"]["2"]["n_graded"] > 0
    result["by_score_version"]["2"]["dates"].append("changed return")
    assert "changed return" not in grader.grade_from_inputs(calls, **kwargs)["by_score_version"]["2"]["dates"]
    for value, initial in zip((calls, panel, frozen), before): pd.testing.assert_frame_equal(value, initial)
    levels["a"][0].iloc[-1] = -1
    pd.testing.assert_frame_equal(frozen, before[2])


@pytest.mark.parametrize("failure", ["membership_absent", "freeze_start_error"])
def test_legacy_preserves_three_independent_frozen_reads_and_failure_boundaries(failure, monkeypatch, tmp_path):
    calls, panel, frozen = captured()
    p = tmp_path / "sector_central/calls.parquet"; p.parent.mkdir(parents=True); calls.to_parquet(p, index=False)
    monkeypatch.setattr(grader.config, "data_dir", lambda: tmp_path)
    observed = []
    def run(owner):
        calls_seen = []
        monkeypatch.setattr(owner, "_yahoo_panel", lambda: panel.copy(deep=True))
        def read(domain):
            calls_seen.append(domain)
            if len(calls_seen) == 2 and failure == "membership_absent": return None
            if len(calls_seen) == 3 and failure == "freeze_start_error": raise OSError("controlled third read")
            return frozen.copy(deep=True)
        monkeypatch.setattr(basket_freeze, "read_frozen", read)
        result = owner.grade(); observed.append(calls_seen); return result
    assert canonical(run(grader)) == canonical(run(original))
    assert observed == [["us", "us", "us"], ["us", "us", "us"]]


def test_partial_frozen_projection_survives_later_bad_column(monkeypatch):
    _, _, frozen = captured(); frozen[7] = 1
    monkeypatch.setattr(basket_freeze, "read_frozen", lambda domain: frozen)
    expected = original._basket_levels()
    result = grader.frozen_basket_levels_from_inputs(frozen)
    assert list(result) == list(expected) == ["a"]
    pd.testing.assert_series_equal(result["a"][0], expected["a"][0])
    assert result["a"][1] == expected["a"][1]


@pytest.mark.parametrize("state", ["missing", "unreadable", "empty"])
def test_legacy_early_absence_semantics_are_unchanged(state, monkeypatch, tmp_path):
    p = tmp_path / "sector_central/calls.parquet"; p.parent.mkdir(parents=True)
    if state == "unreadable": p.write_bytes(b"not parquet")
    elif state == "empty": pd.DataFrame().to_parquet(p)
    monkeypatch.setattr(grader.config, "data_dir", lambda: tmp_path)
    def forbidden(*a, **k): raise AssertionError("early absence must not acquire prices")
    monkeypatch.setattr(grader, "_yahoo_panel", forbidden); monkeypatch.setattr(original, "_yahoo_panel", forbidden)
    assert grader.grade() == original.grade()


def test_literal_grader_source_is_frozen():
    p = Path(__file__).parent / "fixtures/base_sector_central_grader_1f3f605.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "83786e3a25830538c50f9b5cf2bdd96ab41ef57a471fc19d52e2cf7c98745032"
