"""Deterministic guardrails for the read-only Prophet repeat-admission audit."""
import pytest

from scripts.prophet_readmission_pit_study import study, render_markdown


def _episode(ticker, date, outcome, cohort, *, prior=None, sector=None,
             status=None, exit_date=None, labels=()):
    return {
        "ticker": ticker, "entry_date": date, "board_exit_date": exit_date,
        "maturity": "matured", "outcome_pct": outcome, "cohort": cohort,
        "prior_episode": prior,
        "entry_context": {
            "sector_basket": {"reco": sector} if sector is not None else None,
            "entry_plan": {"status": status} if status is not None else None,
        },
        "labels": list(labels),
    }


def _document(rows):
    return {"schema": "prophet_postmortem/v1", "as_of": "2026-07-31",
            "episodes": rows}


def test_hindsight_outcome_never_becomes_an_entry_time_candidate():
    base = _episode("ABC", "2026-07-01", -15.0, "loser",
                    sector="hold", exit_date="2026-07-02")
    reentry = _episode(
        "ABC", "2026-07-06", -12.0, "loser", sector="avoid",
        status="hold", prior={
            "entry_date": "2026-07-01", "outcome_pct": -15.0,
            "mark_at_readmit_pct": 3.0, "selected_by": "prior_episode_loss",
            "sessions_since_prior_exit": 2,
        }, labels=[{"label": "re_admission", "trigger": {
            "leg": "prior_episode_loss",
        }}],
    )
    result = study(_document([base, reentry]), draws=16)
    groups = result["groups"]
    assert groups["repeat_admission"]["n"] == 1
    assert groups["repeat_open_mark_le_minus8_pit_candidate"]["n"] == 0
    assert groups["repeat_sector_avoid_or_trim_pit_candidate"]["n"] == 1
    assert groups["repeat_sector_shift_into_headwind_pit_candidate"]["n"] == 1
    assert groups["prior_resolved_loss_hindsight_ONLY"]["n"] == 1
    assert groups["repeat_entry_status_buy_now_not_execution_proof"]["n"] == 0
    assert result["authority"].startswith("descriptive_only")
    assert "DO NOT PROMOTE" in render_markdown(result)


def test_sector_shift_does_not_follow_hindsight_selected_prior():
    earlier = _episode("ABC", "2026-07-01", -18, "loser",
                       sector="hold", exit_date="2026-07-02")
    latest = _episode("ABC", "2026-07-03", 1.0, "neutral",
                      sector="avoid", exit_date="2026-07-06")
    readmit = _episode("ABC", "2026-07-07", 9.0, "winner",
                       sector="avoid", status="buy_now",
                       prior={"entry_date": "2026-07-01", "outcome_pct": -18,
                              "mark_at_readmit_pct": 2,
                              "selected_by": "prior_episode_loss"})
    res = study(_document([earlier, latest, readmit]), draws=24)
    assert res["groups"]["repeat_sector_shift_into_headwind_pit_candidate"]["n"] == 0
    assert res["groups"]["repeat_entry_status_buy_now_not_execution_proof"]["n"] == 1
    assert res["groups"]["repeat_sector_avoid_or_trim_pit_candidate"]["winners"] == 1
    assert res["groups"]["repeat_sector_avoid_or_trim_pit_candidate"]["total_return_pp"] == 9.0


def test_symmetric_metrics_preserve_neutrals_and_null_not_clean():
    original = _episode("Q", "2026-07-01", 0.2, "neutral",
                        exit_date="2026-07-02")
    neutral = _episode("Q", "2026-07-06", -2.4, "neutral", sector="avoid",
                       prior={"entry_date": "2026-07-01",
                              "mark_at_readmit_pct": -3.0})
    winner = _episode("W", "2026-07-06", 11.0, "winner")
    res = study(_document([original, neutral, winner]), draws=16)
    measured = res["groups"]["repeat_sector_avoid_or_trim_pit_candidate"]
    assert measured["n"] == 1
    assert measured["losers"] == 0 and measured["winners"] == 0
    assert measured["neutral"] == 1 and measured["neutral_return_pp"] == -2.4
    assert res["groups"]["repeat_open_mark_le_minus8_pit_candidate"]["n"] == 0
    assert res["cohort_integrity"] == "MISSING_no_confirmatory_cross_era_claims"


@pytest.mark.parametrize("as_of", ["2026-13-01", "2026-02-30", "2026-7-31", None])
def test_strict_historical_vintage(as_of):
    doc = _document([_episode("A", "2026-07-01", 1.0, "neutral")])
    doc["as_of"] = as_of
    with pytest.raises(ValueError, match="canonical as_of"):
        study(doc, draws=8)
