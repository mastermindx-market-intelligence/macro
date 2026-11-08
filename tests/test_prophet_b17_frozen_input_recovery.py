"""Discriminators for B-17 input completeness, clocks and the frozen ruler."""
import io

import pandas as pd
import pytest

from research.prophet_v4.b17_frozen_input_recovery import (
    GitReader, InputUnavailable, dedup_positions, first_eligible_surfaces,
    frozen_coverage, git_blob_sha, normalized_prices, qualify_snapshot,
)

DECISION = "2026-08-11T12:36:43+00:00"
KNOWN = "2026-08-10T23:56:39+00:00"


def row(ticker="A"):
    return {
        "ticker": ticker, "dir": "up", "conviction": {"band": "high"},
        "entry_signal": {"status": "buy_now", "act_level": 3},
        "signal": {"tier_cascade": "T1"}, "prophet": {"score": 70},
    }


def qualify(body, *, complete=True, known=KNOWN, panel=None):
    return qualify_snapshot(
        body, complete_original=complete, known_at=known, decision_at=DECISION,
        cutoff="2026-08-10", panel=panel or ["A", "B"],
    )


def test_missing_snapshot_is_unknown_but_complete_empty_buy_proves_refusal():
    missing = qualify(None)
    empty = qualify({"as_of": "2026-08-10", "buy": []})
    assert missing["unknown"] == ["A", "B"]
    assert missing["refused"] == []
    assert empty["unknown"] == []
    assert empty["refused"] == ["A", "B"]


def test_reconstruction_cannot_manufacture_admission_with_legacy_defaults():
    body = {"as_of": "2026-08-10", "buy": [{"ticker": "A", "entry_signal": {"status": "buy_now"}}]}
    reconstructed = qualify(body, complete=False)
    original = qualify(body, complete=True)
    assert reconstructed["admitted"] == []
    assert reconstructed["unknown"] == ["A", "B"]
    # Canonical compatibility defaults remain valid for verified original bytes.
    assert original["admitted"] == ["A"]


def test_canonical_selector_is_uncapped_and_preserves_full_board_membership():
    names = [f"T{x:02}" for x in range(20)]
    result = qualify({"as_of": "2026-08-10", "buy": [row(t) for t in names]},
                     panel=names + ["ABSENT"])
    assert result["admitted"] == names
    assert result["admitted_all_count"] == 20
    assert result["refused"] == ["ABSENT"]


@pytest.mark.parametrize("changed", [
    {"dir": "down"}, {"conviction": {"band": "low"}},
    {"signal": {"tier_cascade": "T4"}},
    {"entry_signal": {"status": "buy_soon"}},
    {"entry_signal": None},
])
def test_real_canonical_refusals_are_not_relaxed_by_recovery(changed):
    candidate = {**row(), **changed}
    result = qualify({"as_of": "2026-08-10", "buy": [candidate]})
    assert result["admitted"] == []
    assert result["refused"] == ["A", "B"]


@pytest.mark.parametrize("known", [None, "2026-08-11T12:36:44Z"])
def test_unavailable_or_post_decision_archive_is_unknown(known):
    result = qualify({"as_of": "2026-08-10", "buy": [row()]}, known=known)
    assert result["state"] == "unknown_input"
    assert result["admitted"] == []
    assert result["refused"] == []


def test_source_after_price_cutoff_is_not_admitted_even_when_archive_is_known():
    result = qualify({"as_of": "2026-08-11", "buy": [row()]},
                     known="2026-08-11T12:00:00Z")
    assert result["reason"] == "source_after_frozen_price_edge"


def test_source_cannot_predate_its_claimed_archive_availability():
    result = qualify({"as_of": "2026-08-10", "buy": [row()]},
                     known="2026-08-09T23:00:00Z")
    assert result["reason"] == "source_after_archive_availability"


def test_invalid_source_date_and_duplicate_identities_remain_unknown():
    bad_date = qualify({"as_of": "2026-00-00", "buy": [row()]})
    duplicate = qualify({"as_of": "2026-08-10", "buy": [row(), row()]})
    assert bad_date["state"] == "unknown_input"
    assert duplicate["state"] == "unknown_input"


def test_naive_availability_clock_is_rejected():
    with pytest.raises(InputUnavailable, match="timezone"):
        qualify({"as_of": "2026-08-10", "buy": [row()]}, known="2026-08-10T23:00:00")


def test_r2i_preserves_zero_and_thirty_day_boundaries_and_excludes_future():
    anchors = pd.DataFrame({"ticker": ["A", "B", "C"], "pos": [100, 100, 100]})
    candidates = pd.DataFrame({
        "ticker": ["A", "A", "A", "B", "C", "C"],
        "pos": [80, 100, 101, 70, 69, 101],
    })
    result = frozen_coverage(anchors, candidates)
    assert result["denominator"] == 3
    assert result["covered"] == 2
    assert result["median_lead_sessions"] == 15
    assert result["same_day_covered"] == 1


def test_r2i_uses_latest_candidate_and_same_ticker_session_positions():
    anchors = pd.DataFrame({"ticker": ["A"], "pos": [100]})
    candidates = pd.DataFrame({"ticker": ["A", "A", "B"], "pos": [70, 95, 100]})
    assert frozen_coverage(anchors, candidates)["median_lead_sessions"] == 5


def test_keep_first_dedup_is_not_rolling_and_exact_gap_ten_survives():
    assert dedup_positions([20, 9, 10, 19, 0, 10]) == [0, 10, 20]


def observations(states):
    return [
        {"ticker": "A", "date": f"2026-08-{5 + i:02}", "pos": 10 + i,
         "union_fired": True, "fire_date": "2026-08-05", "fire_pos": 10,
         "admission_state": state}
        for i, state in enumerate(states)
    ]


def test_delayed_gate_uses_surface_time_without_backdating_signature():
    events = first_eligible_surfaces(observations(["refused", "refused", "admitted", "admitted"]))
    assert len(events) == 1
    event = events[0]
    assert event["signature_pos"] == 10
    assert event["surface_pos"] == 12
    assert event["first_visibility_proven"]
    anchors = pd.DataFrame({"ticker": ["A"], "pos": [13]})
    measured = frozen_coverage(anchors, pd.DataFrame({"ticker": ["A"], "pos": [event["surface_pos"]]}))
    assert measured["median_lead_sessions"] == 1


@pytest.mark.parametrize("missing_row", [False, True])
def test_unknown_or_missing_liveness_input_cannot_prove_first_visibility(missing_row):
    rows = observations(["refused", "unknown_input", "admitted"])
    if missing_row:
        rows.pop(1)
    events = first_eligible_surfaces(rows)
    assert events[0]["surface_pos"] == 12
    assert not events[0]["first_visibility_proven"]


def test_expired_union_or_conflicting_same_session_evidence_is_rejected():
    rows = observations(["refused"] * 4 + ["admitted"])
    with pytest.raises(InputUnavailable, match="liveness"):
        first_eligible_surfaces(rows)
    rows = observations(["admitted"])
    with pytest.raises(InputUnavailable, match="duplicate"):
        first_eligible_surfaces(rows + rows)


def parquet(close_after_cutoff):
    frame = pd.DataFrame(
        {"close": [10.0, 11.0, close_after_cutoff], "high": [11.0, 12.0, close_after_cutoff + 1],
         "low": [9.0, 10.0, close_after_cutoff - 1]},
        index=pd.to_datetime(["2026-08-07", "2026-08-10", "2026-08-11"]),
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


def test_post_cutoff_price_poison_cannot_change_recovered_prefix():
    ordinary, excluded = normalized_prices(parquet(12.0), "2026-08-10")
    poison, excluded_poison = normalized_prices(parquet(1e9), "2026-08-10")
    pd.testing.assert_frame_equal(ordinary, poison)
    assert excluded == excluded_poison == 1


def test_git_source_bytes_must_match_the_bound_blob(monkeypatch, tmp_path):
    reader = GitReader(tmp_path)
    expected = git_blob_sha(b"expected")
    monkeypatch.setattr(reader, "command",
                        lambda args, timeout=120: expected.encode() if args[0] == "rev-parse" else b"changed")
    with pytest.raises(InputUnavailable, match="identity mismatch"):
        reader.read("1" * 40, "research/input.json")


def test_unknown_state_vocabulary_cannot_prove_first_surface():
    rows = observations(["new_unqualified_status", "admitted"])
    with pytest.raises(InputUnavailable, match="vocabulary"):
        first_eligible_surfaces(rows)


def test_explicit_git_access_refusal_does_not_fall_back_to_another_client(monkeypatch, tmp_path):
    import subprocess
    from research.prophet_v4.b17_frozen_input_recovery import SourceAccessRefused
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if "rev-parse" in args:
            return subprocess.CompletedProcess(args, 0, b"1" * 40 + b"\n", b"")
        return subprocess.CompletedProcess(args, 128, b"", b"fatal: Authentication failed (HTTP 403)")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(SourceAccessRefused, match="no fallback"):
        GitReader(tmp_path, github_fallback=True).read("2" * 40, "research/input.json")
    assert len(calls) == 2
    assert all(args[0] == "git" for args in calls)


def test_cutoff_replay_retains_unknown_union_inputs_and_archive_clock(monkeypatch):
    from research.prophet_v4.b17_frozen_input_recovery import replay_cutoff_intersection
    snapshot = {
        "state": "known_snapshot_selection", "source_asof": "2026-08-10",
        "known_at": "2026-08-11T12:24:47Z", "ref": "1" * 40,
        "git_blob": "2" * 40, "sha256": "3" * 64,
        "admitted": ["A", "B"], "buy_rows": 69, "admitted_all_count": 40,
    }
    frames = {t: pd.DataFrame({"close": [v]}, index=pd.to_datetime(["2026-08-10"]))
              for t, v in [("A", 1.0), ("B", 2.0)]}

    def union(frame, asof):
        assert asof == "2026-08-10"
        if frame.iloc[0]["close"] == 1:
            return {"fired": False, "reason": "union admission unavailable: missing state"}
        return {"fired": True, "fire_date": "2026-08-07", "age_bars": 1,
                "legs": ["relaxed_cross"], "reason": None}

    monkeypatch.setattr("engine.us_early_turn.union_admission", union)
    result = replay_cutoff_intersection([snapshot], frames)
    assert result["unknown_primary_panel"] == ["A"]
    assert result["union_live_primary_panel"] == ["B"]
    assert result["snapshot_known_at"] == "2026-08-11T12:24:47Z"
    assert result["coverage_result"] is None and result["lead_result"] is None


def test_missing_original_cutoff_snapshot_does_not_substitute_a_later_window():
    from research.prophet_v4.b17_frozen_input_recovery import replay_cutoff_intersection
    result = replay_cutoff_intersection(
        [{"state": "known_snapshot_selection", "source_asof": "2026-10-23"}], {})
    assert result["state"] == "unknown_input"


def test_recovery_cannot_bind_another_checkouts_head_to_local_rules(tmp_path):
    from research.prophet_v4.b17_frozen_input_recovery import (
        FROZEN_REF, SOURCE_REF, GitReader, recover,
    )
    with pytest.raises(InputUnavailable, match="reader must match the implementation checkout"):
        recover(GitReader(tmp_path), frozen_ref=FROZEN_REF, source_ref=SOURCE_REF)
