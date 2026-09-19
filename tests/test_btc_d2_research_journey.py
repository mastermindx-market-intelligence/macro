"""Prospective D2 research journey: immutable source, outcome, and correction generations."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from engine import btc_impulse_ledger as LED


def _d2():
    spec = importlib.util.find_spec("engine.btc_d2_research")
    assert spec is not None, "engine.btc_d2_research contract is not implemented"
    return importlib.import_module("engine.btc_d2_research")


def _frames(*, fired: bool = True):
    """Exact 62-bar D2 input ending one bar before the prediction entry."""
    source_idx = pd.date_range("2024-01-01", periods=62, freq="D")
    entry = source_idx[-1] + pd.Timedelta(days=1)
    # Non-zero trailing dispersion; last range is either a decisive jolt or ordinary.
    ranges = pd.Series(
        [0.10 + ((i % 5) - 2) * 0.002 for i in range(61)]
        + ([0.40] if fired else [0.10]),
        index=source_idx,
        dtype=float,
    )
    dvol = pd.DataFrame(
        {
            "dvol_high": 90.0 + ranges * 100.0,
            "dvol_low": 90.0,
            "dvol_close": 100.0,
        },
        index=source_idx,
    )
    sig_idx = source_idx.append(pd.DatetimeIndex([entry]))
    sig = pd.DataFrame({"close": 100.0}, index=sig_idx)
    return entry, sig, dvol


def _capture_available(*, fired: bool = True):
    d2 = _d2()
    entry, sig, dvol = _frames(fired=fired)
    journey = d2.new_journey()
    changed = d2.capture_source(
        journey,
        entry_asof=str(entry.date()),
        sig_df=sig,
        dvol_df=dvol,
        recorded_at="2026-09-17T05:00:00Z",
    )
    assert changed is True
    return d2, journey, entry, sig, dvol


def test_generation_identity_binds_semantics_not_lifecycle_metadata():
    d2 = _d2()
    semantic = {
        "spec": {"identity": "d2", "horizon_bars": 3},
        "inputs": {"source_rows": [{"asof": "2024-01-01", "range": 0.1}]},
        "evaluator": {"collector": "btc_impulse_radar._d2_cond.v1"},
        "prediction": {"fired": True},
    }
    a = d2.make_generation("source", semantic, recorded_at="2026-09-17T05:00:00Z")
    b = d2.make_generation("source", semantic, recorded_at="2026-09-17T06:00:00Z")
    assert a["generation_id"] == b["generation_id"]
    assert a["lifecycle"] != b["lifecycle"]

    changed = copy.deepcopy(semantic)
    changed["inputs"]["source_rows"][0]["range"] = 0.2
    c = d2.make_generation("source", changed, recorded_at="2026-09-17T05:00:00Z")
    assert c["generation_id"] != a["generation_id"]

    changed = copy.deepcopy(semantic)
    changed["evaluator"]["collector"] = "btc_impulse_radar._d2_cond.v2"
    d = d2.make_generation("source", changed, recorded_at="2026-09-17T05:00:00Z")
    assert d["generation_id"] != a["generation_id"]


def test_append_is_idempotent_and_rejects_a_tampered_same_identity():
    d2 = _d2()
    journey = d2.new_journey()
    gen = d2.make_generation(
        "source",
        {"entry_asof": "2024-03-03", "status": "unavailable"},
        recorded_at="2026-09-17T05:00:00Z",
    )
    assert d2.append_generation(journey, gen) is True
    assert d2.append_generation(journey, copy.deepcopy(gen)) is False
    assert len(journey["generations"]) == 1

    tampered = copy.deepcopy(gen)
    tampered["semantic"]["status"] = "available"
    with pytest.raises(d2.GenerationConflict):
        d2.append_generation(journey, tampered)


def test_source_generation_freezes_previous_complete_d2_observation():
    d2, journey, entry, _sig, _dvol = _capture_available(fired=True)
    projection = d2.project(journey)
    assert projection["schema"] == "btc_d2_forward.v1"
    assert projection["status"] == "pending"
    assert projection["entry_asof"] == str(entry.date())
    assert projection["entry_close"] == 100.0
    assert projection["source_asof"] == str((entry - pd.Timedelta(days=1)).date())
    assert projection["check_after"] == str((entry + pd.Timedelta(days=3)).date())
    assert projection["fired"] is True
    assert projection["trigger_evidence"]["current_z"] >= 2.0
    assert projection["trigger_evidence"]["previous_z"] < 1.5
    assert projection["trigger_evidence"]["mode"] == "single_z_ge_2"
    assert projection["trigger_evidence"]["recomputed_fired"] is True
    assert projection["trading_authority"] is False
    assert projection["outcome"] is None

    source = journey["generations"][0]
    assert source["kind"] == "source"
    semantic = source["semantic"]
    assert semantic["spec"]["identity"] == "d2"
    assert semantic["spec"]["horizon_bars"] == 3
    assert semantic["spec"]["threshold_pct"] == -5.0
    assert semantic["evaluator"]["collector"] == "btc_impulse_radar._d2_cond.v1"
    assert len(semantic["inputs"]["source_rows"]) == 62
    assert semantic["inputs"]["source_rows"][-1]["asof"] == projection["source_asof"]


def test_projection_explains_a_non_fire_without_changing_generation_identity():
    d2, journey, _entry, _sig, _dvol = _capture_available(fired=False)
    before = copy.deepcopy(journey)
    projection = d2.project(journey)
    assert journey == before
    assert projection["fired"] is False
    assert projection["trigger_evidence"]["current_z"] < 1.5
    assert projection["trigger_evidence"]["mode"] == "threshold_not_met"
    assert projection["trigger_evidence"]["recomputed_fired"] is False
    assert projection["trigger_evidence"]["rule"] == "z>=2.0 or second consecutive z>=1.5"


def test_projection_fails_closed_when_hashed_fire_flag_conflicts_with_frozen_rows():
    d2, journey, _entry, _sig, _dvol = _capture_available(fired=True)
    semantic = copy.deepcopy(journey["generations"][0]["semantic"])
    semantic["prediction"]["fired"] = False
    inconsistent = d2.new_journey()
    assert d2.append_generation(
        inconsistent,
        d2.make_generation("source", semantic, recorded_at="2026-09-17T05:00:00Z"),
    )
    projection = d2.project(inconsistent)
    assert projection["status"] == "unavailable"
    assert projection["fired"] is None
    assert projection["reason"] == "source_evaluator_mismatch"
    assert projection["trigger_evidence"]["recomputed_fired"] is True
    assert projection["trading_authority"] is False


def test_projection_fails_closed_when_hashed_available_source_cannot_be_replayed():
    d2, journey, _entry, _sig, _dvol = _capture_available(fired=True)
    semantic = copy.deepcopy(journey["generations"][0]["semantic"])
    semantic["inputs"].pop("evaluation_dates")
    unreplayable = d2.new_journey()
    assert d2.append_generation(
        unreplayable,
        d2.make_generation("source", semantic, recorded_at="2026-09-17T05:00:00Z"),
    )
    projection = d2.project(unreplayable)
    assert projection["status"] == "unavailable"
    assert projection["fired"] is None
    assert projection["reason"] == "source_trigger_evidence_unavailable"
    assert projection["trigger_evidence"] is None
    assert projection["trading_authority"] is False


def test_late_source_arrival_appends_correction_without_rewriting_first_generation():
    d2 = _d2()
    entry, sig, dvol = _frames(fired=True)
    journey = d2.new_journey()
    assert d2.capture_source(
        journey,
        entry_asof=str(entry.date()),
        sig_df=sig,
        dvol_df=pd.DataFrame(),
        recorded_at="2026-09-17T05:00:00Z",
    ) is True
    first = copy.deepcopy(journey["generations"][0])
    assert d2.project(journey)["status"] == "unavailable"

    assert d2.capture_source(
        journey,
        entry_asof=str(entry.date()),
        sig_df=sig,
        dvol_df=dvol,
        recorded_at="2026-09-17T06:00:00Z",
    ) is True
    assert journey["generations"][0] == first
    assert [g["kind"] for g in journey["generations"]] == ["source", "correction"]
    correction = journey["generations"][1]
    assert correction["semantic"]["target_kind"] == "source"
    assert correction["semantic"]["supersedes_generation_id"] == first["generation_id"]
    projection = d2.project(journey)
    assert projection["status"] == "pending"
    assert projection["fired"] is True
    assert projection["source_generation_id"] == correction["generation_id"]


def test_outcome_and_later_data_restatement_are_append_only_generations():
    d2, journey, entry, sig, _dvol = _capture_available(fired=True)
    short = sig.loc[entry:].copy()
    short = pd.concat([
        short,
        pd.DataFrame(
            {"close": [98.0, 94.0]},
            index=[entry + pd.Timedelta(days=1), entry + pd.Timedelta(days=2)],
        ),
    ])
    assert d2.mature_outcome(
        journey, short, recorded_at="2026-09-19T05:00:00Z"
    ) is False
    assert d2.project(journey)["status"] == "pending"

    matured = pd.concat([
        short,
        pd.DataFrame(
            {"close": [93.0]},
            index=[entry + pd.Timedelta(days=3)],
        ),
    ])
    assert d2.mature_outcome(
        journey, matured, recorded_at="2026-09-21T05:00:00Z"
    ) is True
    original_outcome = copy.deepcopy(journey["generations"][-1])
    projection = d2.project(journey)
    assert projection["status"] == "matured"
    assert projection["outcome"]["down_hit"] is True
    assert projection["outcome"]["fwd_min_pct"] == -7.0
    assert projection["outcome_evidence"]["result_consistent"] is True
    assert projection["outcome_evidence"]["threshold_pct"] == -5.0
    assert [row["close"] for row in projection["outcome_evidence"]["close_rows"]] == [
        100.0, 98.0, 94.0, 93.0,
    ]

    restated = matured.copy()
    restated.loc[entry + pd.Timedelta(days=1):, "close"] = [101.0, 102.0, 103.0]
    assert d2.mature_outcome(
        journey, restated, recorded_at="2026-09-22T05:00:00Z"
    ) is True
    assert original_outcome in journey["generations"]
    assert [g["kind"] for g in journey["generations"]] == [
        "source", "outcome", "correction",
    ]
    correction = journey["generations"][-1]
    assert correction["semantic"]["target_kind"] == "outcome"
    assert correction["semantic"]["supersedes_generation_id"] == original_outcome["generation_id"]
    projection = d2.project(journey)
    assert projection["outcome"]["down_hit"] is False
    assert projection["outcome_generation_id"] == correction["generation_id"]


def test_impulse_ledger_persists_and_grades_the_d2_journey_in_its_existing_row():
    d2 = _d2()
    entry, sig, dvol = _frames(fired=True)
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    original_path = LED._path
    LED._path = lambda: tmp
    try:
        radar = {
            "ok": True,
            "asof": str(entry.date()),
            "down": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
            "up": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
        }
        LED.stamp(
            radar,
            sig,
            dvol_df=dvol,
            recorded_at=str((entry + pd.Timedelta(days=1)).date()) + "T05:00:00Z",
        )
        row = LED.load()[0]
        assert "research_d2" in row
        assert d2.project(row["research_d2"])["fired"] is True
        assert row["fires"]["d2"] is False  # current authority is separate from raw research fact

        full = pd.concat([
            sig,
            pd.DataFrame(
                {"close": [98.0, 94.0, 93.0]},
                index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
            ),
        ])
        LED.grade(full, recorded_at="2026-09-21T05:00:00Z")
        row = LED.load()[0]
        projection = d2.project(row["research_d2"])
        assert projection["status"] == "matured"
        assert projection["outcome"]["down_hit"] is True
        assert LED.latest_d2_journey()["outcome_generation_id"] == projection["outcome_generation_id"]
    finally:
        LED._path = original_path


def test_projection_fails_closed_when_hashed_outcome_conflicts_with_close_path():
    d2, journey, entry, sig, _dvol = _capture_available(fired=True)
    full = pd.concat([
        sig,
        pd.DataFrame(
            {"close": [98.0, 94.0, 93.0]},
            index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
        ),
    ])
    assert d2.mature_outcome(journey, full, recorded_at="2026-09-21T05:00:00Z")
    source = copy.deepcopy(journey["generations"][0])
    semantic = copy.deepcopy(journey["generations"][1]["semantic"])
    semantic["result"]["fwd_min_pct"] = -1.0
    inconsistent = d2.new_journey()
    assert d2.append_generation(inconsistent, source)
    assert d2.append_generation(
        inconsistent,
        d2.make_generation("outcome", semantic, recorded_at="2026-09-21T05:00:00Z"),
    )
    projection = d2.project(inconsistent)
    assert projection["status"] == "unavailable"
    assert projection["outcome"] is None
    assert projection["reason"] == "outcome_evaluator_mismatch"
    assert projection["outcome_evidence"]["result_consistent"] is False
    assert projection["fired"] is True
    assert projection["trading_authority"] is False


def test_projection_fails_closed_when_hashed_outcome_close_path_cannot_be_replayed():
    d2, journey, entry, sig, _dvol = _capture_available(fired=True)
    full = pd.concat([
        sig,
        pd.DataFrame(
            {"close": [98.0, 94.0, 93.0]},
            index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
        ),
    ])
    assert d2.mature_outcome(journey, full, recorded_at="2026-09-21T05:00:00Z")
    source = copy.deepcopy(journey["generations"][0])
    semantic = copy.deepcopy(journey["generations"][1]["semantic"])
    semantic["inputs"]["close_rows"] = semantic["inputs"]["close_rows"][:-1]
    unreplayable = d2.new_journey()
    assert d2.append_generation(unreplayable, source)
    assert d2.append_generation(
        unreplayable,
        d2.make_generation("outcome", semantic, recorded_at="2026-09-21T05:00:00Z"),
    )
    projection = d2.project(unreplayable)
    assert projection["status"] == "unavailable"
    assert projection["outcome"] is None
    assert projection["reason"] == "outcome_evidence_unavailable"
    assert projection["outcome_evidence"] is None
    assert projection["fired"] is True
    assert projection["trading_authority"] is False


def test_projection_fails_closed_on_tampered_persisted_generation():
    d2, journey, _entry, _sig, _dvol = _capture_available(fired=True)
    tampered = copy.deepcopy(journey)
    tampered["generations"][0]["semantic"]["prediction"]["fired"] = False
    projection = d2.project(tampered)
    assert projection["status"] == "unavailable"
    assert projection["fired"] is None
    assert projection["source_generation_id"] is None
    assert projection["reason"] == "generation_integrity_error"


def test_append_rejects_an_orphan_correction_chain():
    d2 = _d2()
    journey = d2.new_journey()
    orphan = d2.make_generation(
        "correction",
        {
            "target_kind": "source",
            "supersedes_generation_id": "sha256:not-present",
            "reason": "source_restatement",
            "replacement": {"status": "available"},
        },
        recorded_at="2026-09-17T05:00:00Z",
    )
    with pytest.raises(d2.GenerationConflict):
        d2.append_generation(journey, orphan)



def test_next_stamp_repairs_only_an_already_enrolled_unavailable_source():
    """A late DVOL row repairs its prospective journey, never legacy history."""
    d2 = _d2()
    entry, sig, dvol = _frames(fired=True)
    next_entry = entry + pd.Timedelta(days=1)
    sig_next = pd.concat([
        sig,
        pd.DataFrame({"close": [101.0]}, index=[next_entry]),
    ])
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    original_path = LED._path
    LED._path = lambda: tmp
    try:
        legacy = {
            "asof": "2023-12-31",
            "fires": {"d2": False, "d3": False, "u1": False},
            "outcome": None,
        }
        LED._write([legacy])
        day1 = {
            "ok": True,
            "asof": str(entry.date()),
            "down": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
            "up": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
        }
        LED.stamp(
            day1, sig, dvol_df=pd.DataFrame(),
            recorded_at=str((entry + pd.Timedelta(days=1)).date()) + "T05:00:00Z",
        )
        rows = LED.load()
        enrolled = next(row for row in rows if row["asof"] == str(entry.date()))
        first = copy.deepcopy(enrolled["research_d2"]["generations"][0])
        assert d2.project(enrolled["research_d2"])["status"] == "unavailable"

        day2 = copy.deepcopy(day1)
        day2["asof"] = str(next_entry.date())
        LED.stamp(
            day2, sig_next, dvol_df=dvol,
            recorded_at=str((next_entry + pd.Timedelta(days=1)).date()) + "T05:00:00Z",
        )
        rows = LED.load()
        assert "research_d2" not in rows[0]
        enrolled = next(row for row in rows if row["asof"] == str(entry.date()))
        assert enrolled["research_d2"]["generations"][0] == first
        assert [g["kind"] for g in enrolled["research_d2"]["generations"]] == [
            "source", "correction",
        ]
        projection = d2.project(enrolled["research_d2"])
        assert projection["status"] == "pending"
        assert projection["fired"] is True
    finally:
        LED._path = original_path



def test_later_source_outage_never_replaces_a_frozen_available_generation():
    d2, journey, entry, sig, _dvol = _capture_available(fired=True)
    before = copy.deepcopy(journey)
    assert d2.capture_source(
        journey,
        entry_asof=str(entry.date()),
        sig_df=sig,
        dvol_df=pd.DataFrame(),
        recorded_at="2026-09-18T05:00:00Z",
    ) is False
    assert journey == before
    projection = d2.project(journey)
    assert projection["status"] == "pending"
    assert projection["fired"] is True



def test_stamp_preserves_an_existing_unknown_research_envelope():
    """A bad/foreign envelope is evidence to fail closed on, never overwrite."""
    entry, sig, dvol = _frames(fired=True)
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    original_path = LED._path
    LED._path = lambda: tmp
    try:
        unknown = {"schema": "future-or-corrupt", "generations": [{"opaque": True}]}
        row = {
            "asof": str(entry.date()),
            "fires": {"d2": False, "d3": False, "u1": False},
            "outcome": None,
            "research_d2": copy.deepcopy(unknown),
        }
        LED._write([row])
        radar = {
            "ok": True,
            "asof": str(entry.date()),
            "down": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
            "up": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
        }
        LED.stamp(radar, sig, dvol_df=dvol, recorded_at="2026-09-17T05:00:00Z")
        assert LED.load()[0]["research_d2"] == unknown
    finally:
        LED._path = original_path



def test_stamp_never_enrolls_an_existing_legacy_current_row():
    """Existing rows are historical facts, even when their asof equals radar.asof."""
    entry, sig, dvol = _frames(fired=True)
    full = pd.concat([
        sig,
        pd.DataFrame(
            {"close": [98.0, 94.0, 93.0]},
            index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
        ),
    ])
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    original_path = LED._path
    LED._path = lambda: tmp
    try:
        legacy = {
            "asof": str(entry.date()),
            "fires": {"d2": False, "d3": False, "u1": False},
            "btc_close": 100.0,
            "outcome": None,
        }
        LED._write([legacy])
        radar = {
            "ok": True,
            "asof": str(entry.date()),
            "down": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
            "up": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []},
        }
        LED.stamp(radar, full, dvol_df=dvol, recorded_at="2026-09-21T05:00:00Z")
        row = LED.load()[0]
        assert "research_d2" not in row
    finally:
        LED._path = original_path


def test_source_refuses_to_skip_a_missing_previous_daily_btc_close():
    """An older BTC close cannot impersonate the exact day before entry."""
    d2 = _d2()
    entry, sig, dvol = _frames(fired=True)
    extra_day = dvol.index[0] - pd.Timedelta(days=1)
    extra_dvol = dvol.iloc[[0]].copy()
    extra_dvol.index = pd.DatetimeIndex([extra_day])
    extra_sig = pd.DataFrame({"close": [100.0]}, index=[extra_day])
    gapped_sig = pd.concat([extra_sig, sig.drop(entry - pd.Timedelta(days=1))]).sort_index()
    extended_dvol = pd.concat([extra_dvol, dvol]).sort_index()

    journey = d2.new_journey()
    assert d2.capture_source(
        journey,
        entry_asof=str(entry.date()),
        sig_df=gapped_sig,
        dvol_df=extended_dvol,
        recorded_at="2026-09-17T05:00:00Z",
    ) is True
    projection = d2.project(journey)
    assert projection["status"] == "unavailable"
    assert projection["reason"] == "previous_daily_btc_close_missing"


def test_outcome_refuses_to_compress_a_missing_future_daily_close():
    """The first three available rows cannot impersonate t+1,t+2,t+3 daily closes."""
    d2, journey, entry, sig, _dvol = _capture_available(fired=True)
    gapped = pd.concat([
        sig.loc[[entry]],
        pd.DataFrame(
            {"close": [98.0, 94.0, 93.0]},
            index=[
                entry + pd.Timedelta(days=1),
                entry + pd.Timedelta(days=3),
                entry + pd.Timedelta(days=4),
            ],
        ),
    ])
    assert d2.mature_outcome(
        journey,
        gapped,
        recorded_at="2026-09-21T05:00:00Z",
    ) is False
    assert d2.project(journey)["status"] == "pending"


def _rollover_rows():
    d2, completed, entry, sig, _ = _capture_available(fired=True)
    full = pd.concat([sig, pd.DataFrame(
        {"close": [98.0, 94.0, 93.0]},
        index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
    )])
    assert d2.mature_outcome(completed, full)
    next_entry, next_sig, next_dvol = _frames(fired=False)
    shift = pd.Timedelta(days=4)
    next_sig.index += shift
    next_dvol.index += shift
    current = d2.new_journey()
    d2.capture_source(current, entry_asof=str((next_entry + shift).date()),
                      sig_df=next_sig, dvol_df=next_dvol)
    return [
        {"asof": str(entry.date()), "research_d2": completed},
        {"asof": str((next_entry + shift).date()), "research_d2": current},
    ]


def test_latest_projection_retains_completed_observation_after_rollover():
    rows = _rollover_rows()
    before = copy.deepcopy(rows)
    projected = LED.latest_d2_journey(rows)
    assert projected["status"] == "pending"
    assert projected["last_matured"] == _d2().project(rows[0]["research_d2"])
    projected["last_matured"]["outcome"]["down_hit"] = False
    assert rows == before


@pytest.mark.parametrize("broken", [None, [], 17, {"schema": "btc_d2_forward.v1", "generations": None}])
def test_corrupt_current_observation_never_impersonates_completed_history(broken):
    rows = _rollover_rows()
    rows[-1]["research_d2"] = broken
    before = copy.deepcopy(rows)
    projected = LED.latest_d2_journey(rows)
    assert projected["status"] == "unavailable"
    assert projected["reason"] == "generation_integrity_error"
    assert projected["source_generation_id"] is None
    assert projected["last_matured"]["entry_asof"] == rows[0]["asof"]
    assert rows == before


@pytest.mark.parametrize("generations", [None, 17, "broken"])
def test_projection_fails_closed_on_invalid_generation_container(generations):
    projected = _d2().project({"schema": "btc_d2_forward.v1", "generations": generations})
    assert projected["status"] == "unavailable"
    assert projected["reason"] == "generation_integrity_error"
    assert projected["fired"] is None


def test_completed_current_observation_is_not_duplicated_as_history():
    rows = _rollover_rows()[:1]
    projected = LED.latest_d2_journey(rows)
    assert projected["status"] == "matured"
    assert projected.get("last_matured") is None


def test_nonfinite_research_generation_does_not_destroy_incumbent_summary():
    rows = _rollover_rows()
    rows[-1]["research_d2"]["generations"][0]["semantic"]["inputs"]["entry_close"] = float("nan")
    summary = LED.render_summary(rows)
    assert summary["ok"] is True
    assert summary["n_rows"] == 2
    assert summary["research_d2"]["reason"] == "generation_integrity_error"


def test_source_correction_is_inspectable_and_invalidates_earlier_outcome():
    d2 = _d2()
    rows = _rollover_rows()
    journey = rows[0]["research_d2"]
    old_outcome_id = d2.project(journey)["outcome_generation_id"]
    entry, sig, dvol = _frames(fired=False)
    assert d2.capture_source(journey, entry_asof=str(entry.date()), sig_df=sig, dvol_df=dvol)
    result = d2.project(journey)
    assert result["status"] == "pending"
    assert result["outcome_generation_id"] is None
    assert result["corrected"] is True
    assert result["corrections"][-1]["reason"] == "source_restatement"
    assert result["corrections"][-1]["target_kind"] == "source"
    assert result["corrections"][-1]["supersedes_generation_id"] == journey["generations"][0]["generation_id"]
    assert any(g["generation_id"] == old_outcome_id for g in journey["generations"])


def test_raw_fire_matches_incumbent_when_dvol_skips_a_btc_day():
    from engine import btc_impulse_radar as radar
    import math
    days = pd.date_range("2024-01-01", periods=80, freq="D")
    ranges = pd.Series([0.1 + 0.01 * math.sin(i) for i in range(80)], index=days)
    ranges = ranges.drop(days[-2])
    for day in (days[-3], days[-1]):
        prior = ranges.loc[ranges.index < day].tail(60)
        ranges.loc[day] = prior.mean() + 1.7 * prior.std()
    entry = days[-1] + pd.Timedelta(days=1)
    sig = pd.DataFrame({"close": 100.0}, index=days.append(pd.DatetimeIndex([entry])))
    dvol = pd.DataFrame({"dvol_high": 90.0 + ranges * 100.0,
                         "dvol_low": 90.0, "dvol_close": 100.0}, index=ranges.index)
    expected = bool(radar._d2_cond(ranges, 60, days).iloc[-1])
    assert expected is False
    result = _d2().build_source_semantic(
        entry_asof=str(entry.date()), sig_df=sig, dvol_df=dvol,
    )
    assert result["status"] == "available"
    assert result["prediction"]["fired"] == expected
    assert result["inputs"]["evaluation_dates"] == [str(days[-2].date()), str(days[-1].date())]


@pytest.mark.parametrize("recorded_at", ["2026-09-17T05:00:00Z", "not-a-time"])
def test_stale_or_invalid_recording_clock_cannot_mint_prospective_evidence(tmp_path, monkeypatch, recorded_at):
    entry, sig, dvol = _frames(fired=True)
    monkeypatch.setattr(LED, "_path", lambda: tmp_path / "ledger.jsonl")
    radar = {"ok": True, "asof": str(entry.date()), "down": {}, "up": {}}
    LED.stamp(radar, sig, dvol_df=dvol, recorded_at=recorded_at)
    assert len(LED.load()) == 1
    assert "research_d2" not in LED.load()[0]


def test_tape_with_future_closes_cannot_be_enrolled_as_prospective(tmp_path, monkeypatch):
    entry, sig, dvol = _frames(fired=True)
    full = pd.concat([sig, pd.DataFrame(
        {"close": [98.0]}, index=[entry + pd.Timedelta(days=1)],
    )])
    monkeypatch.setattr(LED, "_path", lambda: tmp_path / "ledger.jsonl")
    radar = {"ok": True, "asof": str(entry.date()), "down": {}, "up": {}}
    recorded_at = str((entry + pd.Timedelta(days=1)).date()) + "T05:00:00Z"
    LED.stamp(radar, full, dvol_df=dvol, recorded_at=recorded_at)
    assert "research_d2" not in LED.load()[0]


def test_ledger_write_cannot_truncate_a_retained_generation_chain(tmp_path, monkeypatch):
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(LED, "_path", lambda: target)
    rows = _rollover_rows()
    LED._write(rows)
    before = target.read_bytes()
    rows[0]["research_d2"]["generations"].pop()
    with pytest.raises(ValueError):
        LED._write(rows)
    assert target.read_bytes() == before


def test_ledger_write_preserves_original_when_atomic_replace_fails(tmp_path, monkeypatch):
    import os
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(LED, "_path", lambda: target)
    rows = _rollover_rows()
    LED._write(rows[:1])
    before = target.read_bytes()
    def fail_replace(*args, **kwargs):
        raise OSError("simulated replacement failure")
    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError):
        LED._write(rows)
    assert target.read_bytes() == before


def test_ledger_write_never_discards_an_unparseable_original_line(tmp_path, monkeypatch):
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(LED, "_path", lambda: target)
    target.write_text('{"asof":"2024-03-03"}\n{"torn":')
    before = target.read_bytes()
    with pytest.raises(ValueError):
        LED._write(LED.load())
    assert target.read_bytes() == before


@pytest.mark.parametrize("field,value", [("entry_asof", "2040-01-01"), ("spec", {"identity": "different-rule"})])
def test_source_correction_cannot_retarget_the_frozen_question(field, value):
    d2, journey, _, _, _ = _capture_available()
    before = copy.deepcopy(journey)
    root = journey["generations"][0]
    replacement = copy.deepcopy(root["semantic"])
    replacement[field] = value
    correction = d2.make_generation("correction", {
        "target_kind": "source", "supersedes_generation_id": root["generation_id"],
        "reason": "source_restatement", "replacement": replacement,
    })
    with pytest.raises(d2.GenerationConflict):
        d2.append_generation(journey, correction)
    assert journey == before


def test_new_ledger_observation_uses_incumbent_configured_dvol_window(tmp_path, monkeypatch):
    from lib import store
    entry, sig, dvol = _frames()
    monkeypatch.setattr(LED, "_path", lambda: tmp_path / "ledger.jsonl")
    monkeypatch.setattr(LED.config, "load", lambda: {"btc_impulse_radar": {"dvol_z_w": 30}})
    monkeypatch.setattr(store, "read", lambda group, name: dvol if (group, name) == ("deribit", "dvol") else None)
    radar = {"ok": True, "asof": str(entry.date()), "down": {}, "up": {}}
    LED.stamp(radar, sig, recorded_at=str((entry + pd.Timedelta(days=1)).date()) + "T05:00:00Z")
    source = LED.load()[0]["research_d2"]["generations"][0]["semantic"]
    assert source["spec"]["dvol_z_window"] == 30
    assert len(source["inputs"]["source_rows"]) == 32


def test_config_change_does_not_rewrite_an_existing_frozen_window():
    d2, journey, entry, sig, dvol = _capture_available()
    before = copy.deepcopy(journey)
    assert d2.capture_source(journey, entry_asof=str(entry.date()),
                             sig_df=sig, dvol_df=dvol, dvol_w=30) is False
    assert journey == before
