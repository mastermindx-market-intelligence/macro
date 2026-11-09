from __future__ import annotations

from datetime import date
import json

import pandas as pd

from research.rates_direction import inflation_catalyst_rate_response_shadow as s


def _projection(release, period, release_date, median, sigma, *, asof=None):
    rd = date.fromisoformat(release_date)
    if asof is None:
        asof = (rd - pd.Timedelta(days=1)).isoformat()
    return {
        "row_type": "projection",
        "model": None,
        "asof_night": asof,
        "release": release,
        "period": period,
        "release_date": release_date,
        "expectation_read": {
            "expectation_median": median,
            "sources": ["cleveland_nowcast"],
        },
        "sigma_scale_pp": sigma,
        "prediction_id": f"p:{release}:{period}",
        "inputs_hash": "a" * 64,
        "model_epoch": "champion_v1",
        "target_epoch": "target_v1",
    }


def _actual(
    release,
    period,
    release_date,
    actual,
    observed_at,
    receipt,
    *,
    model=None,
    basis="official_published_metric",
):
    return {
        "row_type": "scored",
        "model": model,
        "release": release,
        "period": period,
        "release_date": release_date,
        "actual_first": actual,
        "actual": actual,
        "actual_basis": basis,
        "actual_source": "official_release_document",
        "actual_receipt_id": receipt,
        "actual_observed_at": observed_at,
        "actual_source_url": "https://example.invalid/official",
        "actual_source_sha256": "b" * 64,
    }


def test_expectation_requires_exact_tminus1_and_nonempty_sources():
    rows = [
        _projection("cpi_headline", "2026-09", "2026-10-14", 0.3, 0.2),
        _projection(
            "cpi_core",
            "2026-09",
            "2026-10-14",
            0.2,
            0.1,
            asof="2026-10-12",
        ),
    ]
    got = s._expectation_rows(rows)
    assert ("cpi_headline", "2026-09", "2026-10-14") in got
    assert ("cpi_core", "2026-09", "2026-10-14") not in got


def test_official_actual_dedups_model_copies_and_rejects_late_capture():
    rows = [
        _actual(
            "cpi_headline",
            "2026-09",
            "2026-10-14",
            0.4,
            "2026-10-14T12:30:03+00:00",
            "official_actual:one",
            model=None,
        ),
        _actual(
            "cpi_headline",
            "2026-09",
            "2026-10-14",
            0.4,
            "2026-10-14T12:30:03+00:00",
            "official_actual:one",
            model="coherent_ridge_v1",
        ),
        _actual(
            "cpi_core",
            "2026-09",
            "2026-10-14",
            0.3,
            "2026-10-15T12:30:03+00:00",
            "official_actual:late",
        ),
    ]
    got = s._official_actual_rows(rows)
    assert got[("cpi_headline", "2026-09", "2026-10-14")]["actual"] == 0.4
    assert ("cpi_core", "2026-09", "2026-10-14") not in got


def test_official_actual_uses_earliest_same_day_receipt():
    rows = [
        _actual(
            "pce_headline",
            "2026-08",
            "2026-09-30",
            0.3,
            "2026-09-30T12:31:00+00:00",
            "official_actual:first",
        ),
        _actual(
            "pce_headline",
            "2026-08",
            "2026-09-30",
            0.4,
            "2026-09-30T14:00:00+00:00",
            "official_actual:later",
        ),
    ]
    got = s._official_actual_rows(rows)
    assert got[("pce_headline", "2026-08", "2026-09-30")]["actual_receipt_id"] == "official_actual:first"


def test_build_event_combines_components_and_preserves_receipts():
    rows = [
        _projection("pce_headline", "2026-08", "2026-09-30", 0.20, 0.10),
        _projection("pce_core", "2026-08", "2026-09-30", 0.25, 0.10),
        _actual(
            "pce_headline",
            "2026-08",
            "2026-09-30",
            0.30,
            "2026-09-30T12:30:02+00:00",
            "official_actual:h",
        ),
        _actual(
            "pce_core",
            "2026-08",
            "2026-09-30",
            0.26,
            "2026-09-30T12:30:03+00:00",
            "official_actual:c",
        ),
    ]
    events = s.build_events(rows)
    assert len(events) == 1
    event = events[0]
    assert event["family"] == "pce"
    assert event["prospective_eligible"] is True
    assert event["signal"] == 1
    assert event["availability"] == "observable"
    assert {c["actual_receipt_id"] for c in event["components"]} == {
        "official_actual:h",
        "official_actual:c",
    }


def test_component_conflict_abstains():
    assert s.combine_states(1, -1) == 0
    assert s.combine_states(-1, 1) == 0
    assert s.combine_states(1, 0) == 1
    assert s.combine_states(0, -1) == -1
    assert s.combine_states(0, 0) == 0


def test_missing_official_component_waits_instead_of_fabricating_signal():
    rows = [
        _projection("cpi_headline", "2026-09", "2026-10-14", 0.2, 0.1),
        _projection("cpi_core", "2026-09", "2026-10-14", 0.2, 0.1),
        _actual(
            "cpi_headline",
            "2026-09",
            "2026-10-14",
            0.3,
            "2026-10-14T12:30:02+00:00",
            "official_actual:h",
        ),
    ]
    event = s.build_events(rows)[0]
    assert event["signal"] is None
    assert event["availability"] == "waiting_official_actual"
    assert event["missing_components"] == ["cpi_core"]


def _outcome(state, baseline):
    return {
        "h0_state": state,
        "h1_state": state,
        "h5_state": state,
        "baseline_state": baseline,
    }


def test_summary_excludes_prefreeze_and_counts_inline_as_miss():
    events = [
        {
            "family": "cpi",
            "prospective_eligible": False,
            "signal": 1,
            "outcome": _outcome(1, 1),
        },
        {
            "family": "cpi",
            "prospective_eligible": True,
            "signal": 1,
            "outcome": _outcome(0, -1),
        },
        {
            "family": "pce",
            "prospective_eligible": True,
            "signal": -1,
            "outcome": _outcome(-1, 1),
        },
        {
            "family": "pce",
            "prospective_eligible": True,
            "signal": 0,
            "outcome": _outcome(1, 1),
        },
        {
            "family": "pce",
            "prospective_eligible": True,
            "signal": None,
            "outcome": None,
        },
    ]
    got = s.summarize(events)
    assert got["pre_freeze_excluded"] == 1
    assert got["events"] == 4
    assert got["signal_observable"] == 3
    assert got["active"] == 2
    assert got["abstained"] == 1
    assert got["waiting_official_actual"] == 1
    assert got["h0"]["catalyst_hits"] == 1
    assert got["h0"]["catalyst_accuracy"] == 0.5
    assert got["h0"]["baseline_hits"] == 0
    assert got["descriptive_floor_met"] is False
