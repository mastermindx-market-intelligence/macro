"""RED contract tests for the Prophet leader-observation projection.

Test-first packet: production functions intentionally do not exist on the pinned base.
Run this file first and confirm failures name the missing projection/loader API.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from engine import us_leader_pullback as organ
from engine import us_leader_pullback_coverage as cov


ASOF = "2026-09-18"


def _row(state: str | None, *, asof: str = ASOF, **extra) -> dict:
    row = {
        "schema": organ.SCHEMA,
        "construction_era": organ.CONSTRUCTION_ERA,
        "asof": asof,
        "state": state,
    }
    row.update(extra)
    if state is None:
        row["null_reason"] = row.get("null_reason") or "insufficient history"
    return {key: value for key, value in row.items() if value is not None}


def _artifact(*, states: dict | None = None, session: str | None = ASOF,
              schema: str | None = None, authority: dict | None = None) -> dict:
    states = states if states is not None else {
        "ZZZ": _row("RESUMED", rs_pct=0.88),
        "AAA": _row("LEADER", rs_pct=0.95),
        "CCC": _row("RESET_TURN", zone_low=91.0, zone_high=94.0,
                    reset_low=90.0, pullback_age=8),
        "BBB": _row("PULLBACK", pullback_depth=0.11, zone_low=82.0,
                    zone_high=86.0, pullback_age=6),
        "NULL": _row(None),
    }
    state_counts: dict[str, int] = {}
    null_count = 0
    for row in states.values():
        state = row.get("state")
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
        else:
            null_count += 1
    return {
        "schema": schema or cov.SCHEMA,
        "as_of": session,
        "data_session": session,
        "max_session": session,
        "session_note": None,
        "selection_era": cov.SELECTION_ERA,
        "construction_era": organ.CONSTRUCTION_ERA,
        "authority": deepcopy(authority or cov.AUTHORITY),
        "coverage": {
            "states_published": len(states),
            "state_counts": state_counts,
            "null_counts": {"insufficient history": null_count} if null_count else {},
            "publishable": True,
        },
        "states": states,
    }


def test_projection_is_display_only_alphabetical_and_lossless():
    projection = cov.project_prophet_observations(
        _artifact(), reference_session=ASOF
    )

    assert projection["schema"] == "prophet.leader_observations/v1"
    assert projection["status"] == "available"
    assert projection["reason_code"] is None
    assert projection["source_relation"] == "aligned"
    assert projection["ordering"] == "ticker_asc_no_rank"
    assert [row["ticker"] for row in projection["rows"]] == [
        "AAA", "BBB", "CCC", "ZZZ"
    ]
    assert projection["counts"] == {
        "source_rows": 5,
        "active": 4,
        "non_active": 0,
        "nulled": 1,
        "invalid": 0,
        "by_state": {
            "LEADER": 1,
            "PULLBACK": 1,
            "RESET_TURN": 1,
            "RESUMED": 1,
        },
    }
    assert {row["disposition"] for row in projection["rows"]} == {
        "OBSERVED_LEADER_WAIT",
        "OBSERVED_PULLBACK_WAIT_SIGNATURE",
        "OBSERVED_RESET_WAIT_SIGNATURE",
        "OBSERVED_RESUMED_DO_NOT_CHASE",
    }
    banned = {
        "rank", "score", "probability", "confidence", "priority", "entry",
        "current_price", "target", "size", "trade", "recommendation",
    }
    assert all(row["plan_authority"] is False for row in projection["rows"])
    assert all(not (set(row) & banned) for row in projection["rows"])


@pytest.mark.parametrize(
    ("session", "reference", "relation"),
    [
        ("2026-09-18", "2026-09-18", "aligned"),
        ("2026-09-17", "2026-09-18", "behind"),
        ("2026-09-19", "2026-09-18", "ahead_conflict"),
        ("2026-09-18", None, "unknown"),
    ],
)
def test_projection_names_source_clock_relation(session, reference, relation):
    projection = cov.project_prophet_observations(
        _artifact(session=session), reference_session=reference
    )
    assert projection["source_relation"] == relation


def test_valid_empty_is_not_unavailable():
    projection = cov.project_prophet_observations(
        _artifact(states={"NULL": _row(None)}), reference_session=ASOF
    )
    assert projection["status"] == "empty"
    assert projection["reason_code"] == "no_active_states"
    assert projection["rows"] == []
    assert projection["counts"]["nulled"] == 1


def test_unknown_state_is_named_degradation_not_a_silent_drop():
    artifact = _artifact(states={
        "AAA": _row("LEADER"),
        "FUTR": _row("FUTURE_STATE"),
    })
    projection = cov.project_prophet_observations(
        artifact, reference_session=ASOF
    )
    assert projection["status"] == "degraded"
    assert projection["reason_code"] == "unknown_state_rows"
    assert projection["counts"]["invalid"] == 1
    assert [row["ticker"] for row in projection["rows"]] == ["AAA"]


def test_authority_drift_fails_closed():
    authority = deepcopy(cov.AUTHORITY)
    authority["may_rank"] = True
    projection = cov.project_prophet_observations(
        _artifact(authority=authority), reference_session=ASOF
    )
    assert projection["status"] == "unavailable"
    assert projection["reason_code"] == "authority_drift"
    assert projection["rows"] == []


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"schema": "wrong", "states": {}}, "schema_mismatch"),
        ({"schema": cov.SCHEMA, "states": {}, "authority": cov.AUTHORITY},
         "source_session_missing"),
    ],
)
def test_malformed_source_contract_fails_closed(payload, reason):
    projection = cov.project_prophet_observations(
        payload, reference_session=ASOF
    )
    assert projection["status"] == "unavailable"
    assert projection["reason_code"] == reason
    assert projection["rows"] == []


def test_loader_distinguishes_absent_unreadable_and_valid_empty(tmp_path: Path):
    absent = cov.load_prophet_observations(
        site_root=tmp_path, reference_session=ASOF
    )
    assert (absent["status"], absent["reason_code"]) == (
        "unavailable", "artifact_absent"
    )

    path = cov.artifact_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    unreadable = cov.load_prophet_observations(
        site_root=tmp_path, reference_session=ASOF
    )
    assert (unreadable["status"], unreadable["reason_code"]) == (
        "unavailable", "artifact_unreadable"
    )

    cov.write_artifact(_artifact(states={"NULL": _row(None)}), tmp_path)
    empty = cov.load_prophet_observations(
        site_root=tmp_path, reference_session=ASOF
    )
    assert (empty["status"], empty["reason_code"]) == (
        "empty", "no_active_states"
    )


def test_summary_never_contains_the_roster():
    projection = cov.project_prophet_observations(
        _artifact(), reference_session=ASOF
    )
    summary = cov.prophet_observation_summary(projection)
    assert summary["counts"] == projection["counts"]
    assert summary["source"] == projection["source"]
    assert "rows" not in summary
    encoded = json.dumps(summary, sort_keys=True)
    for ticker in ("AAA", "BBB", "CCC", "ZZZ"):
        assert ticker not in encoded

def test_casefold_duplicate_ticker_is_named_invalid_not_emitted_twice():
    artifact = _artifact(states={
        "abc": _row("LEADER"),
        "ABC": _row("PULLBACK"),
    })

    projection = cov.project_prophet_observations(
        artifact, reference_session=ASOF
    )

    assert projection["status"] == "degraded"
    assert projection["reason_code"] == "invalid_rows"
    assert projection["counts"]["invalid"] == 1
    assert projection["counts"]["active"] == 1
    assert [row["ticker"] for row in projection["rows"]] == ["ABC"]


def test_summary_is_detached_from_the_full_projection():
    projection = cov.project_prophet_observations(
        _artifact(), reference_session=ASOF
    )
    summary = cov.prophet_observation_summary(projection)

    summary["counts"]["by_state"]["LEADER"] = 999
    summary["source"]["coverage"]["states_published"] = 999

    assert projection["counts"]["by_state"]["LEADER"] == 1
    assert projection["source"]["coverage"]["states_published"] == 5
