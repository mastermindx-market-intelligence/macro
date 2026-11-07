"""Synthetic-only read-boundary and frozen reference regressions; no replay artifacts."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.stock_identity.replay import naive, sea, starter


def _parquet(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_parquet(path)


def test_sea_projects_before_reading_and_keeps_first(tmp_path, monkeypatch):
    row = dict.fromkeys(sea._KEEP, 1)
    row.update(ticker="SYNTH", grid="W", date="2020-01-03", direction="up", era="first")
    _parquet(tmp_path / sea.BACKFILL_PATH, {**row, "fwd_13w": 999})
    _parquet(tmp_path / sea.LIVE_DIR / "2020-01.parquet", {**row, "era": "later", "fwd_13w": -999})
    # A second live schema legitimately lacks optional classification fields.
    _parquet(tmp_path / sea.LIVE_DIR / "2020-02.parquet",
             {k: v for k, v in {**row, "date": "2020-02-07"}.items() if k in sea._KEY})
    original = pd.read_parquet
    calls = []

    def guarded(path, *, columns=None, **kw):
        assert columns and set(columns) <= set(sea._KEEP)
        calls.append((Path(path).name, columns))
        return original(path, columns=columns, **kw)

    monkeypatch.setattr(pd, "read_parquet", guarded)
    result = sea.load_store(tmp_path, ["SYNTH"])
    assert len(calls) == 3
    assert len(result) == 2
    assert result.iloc[0].era == "first"
    assert "fwd_13w" not in result


def test_sea_missing_key_fails_before_materialization(tmp_path, monkeypatch):
    _parquet(tmp_path / sea.LIVE_DIR / "2020-01.parquet", {"ticker": "SYNTH", "fwd_13w": 1})
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: pytest.fail("must reject schema first"))
    with pytest.raises(ValueError, match="missing.*classification"):
        sea.load_store(tmp_path)


@pytest.mark.parametrize("payload", [
    {"as_of": "2020-01-03", "states": {"20200103": "irrelevant"}},
    {"unknown_schema": {"2020-01-03": {"state": "TURNING"}}},
    ["not a state object"],
    "unrecognized",
])
def test_starter_does_not_license_from_names_or_date_keys(tmp_path, payload):
    p = tmp_path / starter._CONTEXT_ARTIFACTS[0][1]
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(payload))
    (tmp_path / "data" / "basket_turn_history.parquet").mkdir(parents=True)
    result = starter.investigate_licensing_context(tmp_path)
    assert result["verdict"] == "NOT_PIT_RECONSTRUCTABLE"
    assert all(not r["carries_history"] for r in result["context_state_evidence"])
    assert "not established" in result["reasoning"]


def test_membership_only_projects_snapshot_metadata(tmp_path, monkeypatch):
    p = tmp_path / starter._MEMBERSHIP_ARTIFACTS[1][1]
    _parquet(p, {"snapshot_date": "2020-01-03", "added": "2020-01-01", "removed": None,
                 "ticker": "SYNTH", "outcome": 999})
    original = pd.read_parquet
    calls = []

    def guarded(path, *, columns=None, **kw):
        assert columns == ["snapshot_date"]
        calls.append(columns)
        return original(path, columns=columns, **kw)

    monkeypatch.setattr(pd, "read_parquet", guarded)
    result = starter.investigate_licensing_context(tmp_path)
    assert calls == [["snapshot_date"]]
    assert result["membership_evidence"][1]["n_snapshot_dates"] == 1
    assert result["membership_evidence"][1]["has_added_removed"] is True
    assert result["verdict"] == "NOT_PIT_RECONSTRUCTABLE"


@pytest.mark.parametrize("content", ["not-json", "{}"])
def test_unqualified_context_cannot_grant_replay(tmp_path, content):
    p = tmp_path / starter._CONTEXT_ARTIFACTS[0][1]
    p.parent.mkdir(parents=True)
    p.write_text(content)
    result = starter.investigate_licensing_context(tmp_path)
    assert result["verdict"] == "NOT_PIT_RECONSTRUCTABLE"
    assert "Class P" in result["consequence"]


def test_membership_without_snapshot_column_never_loads_values(tmp_path, monkeypatch):
    p = tmp_path / starter._MEMBERSHIP_ARTIFACTS[1][1]
    _parquet(p, {"ticker": "SYNTH", "added": "2020-01-01", "removed": None})
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: pytest.fail("no projected metadata to read"))
    result = starter.investigate_licensing_context(tmp_path)
    assert result["membership_evidence"][1]["has_added_removed"] is True
    assert result["membership_evidence"][1]["n_snapshot_dates"] == 0
    assert result["verdict"] == "NOT_PIT_RECONSTRUCTABLE"


@pytest.mark.parametrize("prior,current,expected", [
    ((17, 18), (21, 19), True),
    ((21, 22), (19, 18), False),
    ((20, 21), (22, 21), False),
    ((18, 20), (21, 19), False),
    ((18, 19), (19, 19), False),
    ((np.nan, 18), (21, 19), False),
])
def test_stoch2w_uses_prior_completed_bar(tmp_path, monkeypatch, prior, current, expected):
    dates = pd.bdate_range("2020-01-01", periods=80)
    close = pd.Series(np.arange(80, dtype=float) + 100, index=dates)
    bars = pd.DataFrame({"close": close.iloc[:30].to_numpy(), "open": dates[:30],
                         "known": dates[:30], "label": dates[:30]})
    k, d = pd.Series(50.0, index=range(30)), pd.Series(50.0, index=range(30))
    k.iloc[-2], d.iloc[-2] = prior
    k.iloc[-1], d.iloc[-1] = current
    monkeypatch.setattr(naive, "two_week_bars", lambda _: bars)
    monkeypatch.setattr(naive.canon, "stoch_rsi_kd", lambda _: (k, d))
    rows = naive.fires(pd.DataFrame({"close": close}), symbol="SYNTH", price_plane_id="synthetic",
                       spec_hashes=dict.fromkeys(naive.FAMILY_KEYS, "synthetic"), family_first_available={})
    hits = [r for r in rows if r["family_key"] == "stoch2w_cross"]
    assert bool(hits) is expected
    if hits:
        assert hits[0]["scored_authority"] is False


def test_reference_spec_describes_prior_bar():
    assert "prior completed 2W bar" in naive.constants("stoch2w_cross")["rule"]
