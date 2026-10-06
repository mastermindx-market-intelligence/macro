"""E1 qualification: fiscal period, null refusal, point-in-time, basis/currency seams."""
from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from collectors.equity_revisions import _apply_lineage
from engine.k3e_expectation_surface import (
    ATTEMPTS_PATH,
    OBSERVATIONS_PATH,
    inspect_expectation_surface,
)

BASE_PIN = "13910854fbd652dcdf975301bdc8c6728c2e4767"

CUT = "2026-10-02T12:00:00Z"
PROVENANCE = {
    "source_revision": "a" * 40,
    "inputs": {
        OBSERVATIONS_PATH: {"sha256": "1" * 64, "git_blob_id": "1" * 40},
        ATTEMPTS_PATH: {"sha256": "2" * 64, "git_blob_id": "2" * 40},
    },
}


def _attempt(label: str, time: str = "2026-10-02T10:00:00Z") -> dict:
    return {
        "attempt_id": label,
        "collection_session_id": label,
        "provider": "yfinance",
        "ticker_compat": "V",
        "attempted_at": time,
        "completed_at": time,
        "status": "success",
        "response_payload_hash": label,
        "observation_count": 2,
    }


def _observation(
    label: str,
    *,
    time: str = "2026-10-02T10:00:00Z",
    value: float | None = 2.5,
    period_end: str | None = "2026-09-30",
    fiscal_period: str | None = None,
    unit: str | None = "USD/sh",
    currency: str | None = "USD",
    basis: str | None = "GAAP",
    missingness_reason: str | None = None,
) -> dict:
    miss = missingness_reason
    if value is None and miss is None:
        miss = "UNESTIMABLE"
    return {
        "observation_id": f"{label}-average",
        "collection_session_id": label,
        "attempt_id": label,
        "provider": "yfinance",
        "provider_record_class": "earnings_estimate",
        "provider_payload_hash": label,
        "ticker_compat": "V",
        "issuer_ref": "ISS:V",
        "security_ref": "SEC:V",
        "metric": "EPS",
        "horizon_label_raw": "0q",
        "period_end": period_end,
        "fiscal_period": fiscal_period,
        "fiscal_year": None,
        "observation_type": "average",
        "value": value,
        "unit": unit,
        "currency": currency,
        "basis": basis,
        "aggregation_level": "single_contributor",
        "contributor_id": "contrib-1",
        "source_effective_at": None,
        "source_published_at": None,
        "provider_observed_at": time,
        "system_observed_at": time,
        "market_session": "2026-10-02",
        "missingness_reason": miss,
        "correction_state": "original",
        "supersedes_observation_id": None,
        "rights_class": "UNKNOWN",
        "provenance_note": "qualification-fixture",
    }


def _count_row(label: str, time: str, count: int = 10) -> dict:
    row = _observation(label, time=time, value=count)
    row["observation_type"] = "covering_analyst_count"
    row["observation_id"] = f"{label}-count"
    row["missingness_reason"] = None
    return row


def _payload(rows, attempts, as_of: str = CUT):
    return inspect_expectation_surface(
        rows,
        attempts,
        source_provenance=PROVENANCE,
        ticker="V",
        metric="EPS",
        horizon="0q",
        as_of=as_of,
        composed_at="2026-10-03T12:00:00Z",
    )["semantic_payload"]


def _selected(result, key: str = "last_structurally_supported_snapshot"):
    snap = result[key]["snapshot"]
    return snap["selected_observation"] if snap else None


def _lineage_row(**kwargs) -> dict:
    base = _observation("row", **kwargs)
    base.update(
        {
            "provider": "yfinance",
            "provider_record_class": "earnings_estimate",
            "ticker_compat": "V",
            "metric": "EPS",
            "horizon_label_raw": "0q",
            "observation_type": "average",
            "correction_state": "original",
            "supersedes_observation_id": None,
        }
    )
    return base


def test_e_f_fiscal_rollover_by_period_end_not_a_revision():
    """E-F: FY2026Q3→Q4 period-end change is not a revision of Q3 (period_end labeling)."""
    prior = _lineage_row(value=1.0, period_end="2026-09-30")
    current = _lineage_row(value=2.0, period_end="2026-12-31")
    er_frame = pd.DataFrame([prior])
    _apply_lineage([current], er_frame)
    assert current["correction_state"] == "original"
    assert current["supersedes_observation_id"] is None


def test_e_f_fiscal_rollover_by_fiscal_period_label_not_a_revision():
    """E-F: normalized fiscal_period labels differ while horizon key is unchanged."""
    prior = _lineage_row(value=1.0, period_end="2026-09-30", fiscal_period="FY2026Q3")
    current = _lineage_row(value=2.0, period_end="2026-12-31", fiscal_period="FY2026Q4")
    er_frame = pd.DataFrame([prior])
    _apply_lineage([current], er_frame)
    assert current["correction_state"] == "original"
    assert current["supersedes_observation_id"] is None


def test_e_g_null_partial_after_good_refuses_baseline_none_not_zero():
    """E-G: null after good observation — refusal None per E0, no downward revision."""
    good_rows = [_observation("one", time="2026-10-02T09:00:00Z", value=2.5),
                 _count_row("one", "2026-10-02T09:00:00Z")]
    null_rows = [_observation("two", time="2026-10-02T11:00:00Z", value=None,
                              missingness_reason="UNESTIMABLE"),
                 _count_row("two", "2026-10-02T11:00:00Z")]
    attempts = [_attempt("one", "2026-10-02T09:00:00Z"), _attempt("two", "2026-10-02T11:00:00Z")]
    result = _payload(good_rows + null_rows, attempts)
    selected = _selected(result)
    assert selected is not None
    assert selected["value"] == 2.5
    baseline = result["normalized_baseline"]
    assert baseline["value"] is None
    assert baseline["value"] != 0


def test_e_h_correction_after_cutoff_does_not_change_surface_at_cutoff():
    """E-H: correction published after cutoff C cannot change evaluation at C."""
    early = [_observation("early", time="2026-10-02T09:00:00Z", value=2.0),
             _count_row("early", "2026-10-02T09:00:00Z")]
    late = [_observation("late", time="2026-10-02T13:00:00Z", value=9.0),
            _count_row("late", "2026-10-02T13:00:00Z")]
    attempts = [_attempt("early", "2026-10-02T09:00:00Z"), _attempt("late", "2026-10-02T13:00:00Z")]
    at_cutoff = _payload(early + late, attempts, as_of=CUT)
    assert _selected(at_cutoff)["value"] == 2.0
    assert at_cutoff["denominators"]["capture_clock_bounded_relevant_records"] == 2


def test_e_h_correction_after_cutoff_visible_when_evaluated_later():
    """E-H mirror: after the correction clock, the newer capture may surface."""
    early = [_observation("early", time="2026-10-02T09:00:00Z", value=2.0),
             _count_row("early", "2026-10-02T09:00:00Z")]
    late = [_observation("late", time="2026-10-02T13:00:00Z", value=9.0),
            _count_row("late", "2026-10-02T13:00:00Z")]
    attempts = [_attempt("early", "2026-10-02T09:00:00Z"), _attempt("late", "2026-10-02T13:00:00Z")]
    later = _payload(early + late, attempts, as_of="2026-10-02T14:00:00Z")
    latest = _selected(later, "latest_captured_snapshot")
    assert latest["value"] == 9.0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-BASIS: GAAP vs non-GAAP value change still yields supersedes at "
        f"collectors/equity_revisions.py:412-421 ({BASE_PIN})"
    ),
)
def test_e_i_incompatible_gaap_basis_produces_no_revision_delta():
    """E-I: GAAP vs non-GAAP observations are noncomparable — no revision event."""
    prior = _lineage_row(value=1.0, basis="GAAP")
    current = _lineage_row(value=1.1, basis="non-GAAP")
    _apply_lineage([current], pd.DataFrame([prior]))
    assert current["correction_state"] != "supersedes"
    assert current["supersedes_observation_id"] is None


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-BASIS: diluted vs basic EPS basis change still yields supersedes at "
        f"collectors/equity_revisions.py:412-421 ({BASE_PIN})"
    ),
)
def test_e_i_incompatible_eps_share_basis_produces_no_revision_delta():
    """E-I: diluted vs basic EPS must not produce a revision across the basis boundary."""
    prior = _lineage_row(value=1.0, basis="basic")
    current = _lineage_row(value=1.0, basis="diluted")
    _apply_lineage([current], pd.DataFrame([prior]))
    assert current["correction_state"] != "supersedes"


def test_e_i_missing_unit_or_currency_yields_refusal_not_substitution():
    """E-I: missing unit/currency refuses normalized admission (E0 refusal, not zero)."""
    rows = [_observation("one", unit=None, currency=None), _count_row("one", "2026-10-02T10:00:00Z")]
    result = _payload(rows, [_attempt("one")])
    baseline = result["normalized_baseline"]
    assert baseline["value"] is None
    reasons = baseline["reasons"]
    assert "CANONICAL_UNIT_UNAVAILABLE" in reasons
    assert "CANONICAL_CURRENCY_UNAVAILABLE" in reasons


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-BASIS: cross-currency observations are not refused at comparison seam "
        f"collectors/equity_revisions.py:412-416 ({BASE_PIN})"
    ),
)
def test_e_i_usd_estimate_never_silently_converted_against_foreign_price_currency():
    """E-I: USD estimate paired with foreign currency must refuse, never convert."""
    prior = _lineage_row(value=1.0, currency="USD", unit="USD/sh")
    current = _lineage_row(value=1.0, currency="EUR", unit="EUR/sh")
    _apply_lineage([current], pd.DataFrame([prior]))
    assert current["correction_state"] != "supersedes"
    assert current["correction_state"] != "unchanged" or current["currency"] == "USD"
