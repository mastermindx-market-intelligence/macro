"""Focused incumbent SRC-A1 acceptance gaps; synthetic inputs only.

No provider package or network is needed: source collection receives an explicit
ticker_factory and legacy accessors receive the existing ticker_client argument.
All parquet output is confined to pytest's tmp_path fixture. This suite does not
modify the collector or the separately owned test_equity_revisions_w2a module.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from collectors import equity_revisions as revisions


def _estimates(metric: str, *, average: float | None = 10.0) -> pd.DataFrame:
    year_ago = "yearAgoEps" if metric == "EPS" else "yearAgoRevenue"
    return pd.DataFrame({
        "avg": [average], "median": [9.5], "high": [12.0], "low": [8.0],
        "numberOfAnalysts": [20], "growth": [0.1], year_ago: [9.0],
    }, index=["0q"])


def _lineage_row(session: str, minute: int) -> dict:
    payload = revisions._canonical_sha256({"synthetic_session": session})
    rows = revisions._expectation_rows(
        ticker="ACME", collection_session_id=session,
        attempt_id=revisions._canonical_sha256((session, "yfinance", "ACME", payload)),
        payload_hash=payload,
        frames={"earnings_estimate": _estimates("EPS"), "revenue_estimate": _estimates("revenue")},
        provider_observed_at=f"2026-10-03T10:{minute:02d}:01Z",
        system_observed_at=f"2026-10-03T10:{minute:02d}:02Z",
        period_end_by_horizon={"0q": "2026-12-31"},
    )
    row = next(row for row in rows if row["metric"] == "EPS" and row["observation_type"] == "average")
    # These are explicit synthetic provider facts supplied to the native lineage
    # helper; the current live accessor does not promise populated basis fields.
    row.update(unit="USD/share", currency="USD", basis="GAAP")
    return row


@pytest.mark.parametrize(("field", "changed_fact"), [
    ("unit", "cents/share"),
    ("currency", "EUR"),
    ("basis", "adjusted"),
])
def test_populated_economic_fact_change_is_noncomparable_without_mutating_prior(field, changed_fact):
    # DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07: a differing non-null
    # unit, currency or basis is a new original, never a supersession.
    prior_row = _lineage_row("old", 0)
    prior = pd.DataFrame([prior_row], columns=revisions._OBSERVATION_COLUMNS)
    immutable_before = prior.copy(deep=True)

    unchanged = _lineage_row("same", 1)
    unchanged_input = deepcopy(unchanged)
    revisions._apply_lineage([unchanged], prior)
    assert unchanged["correction_state"] == "unchanged"
    assert unchanged["supersedes_observation_id"] is None
    assert unchanged["observation_id"] == unchanged_input["observation_id"]

    changed = _lineage_row("changed", 2)
    changed[field] = changed_fact
    new_id = changed["observation_id"]
    revisions._apply_lineage([changed], prior)
    assert changed["value"] == prior_row["value"]  # field-only discriminator
    assert changed[field] == changed_fact
    assert changed["correction_state"] == "original"
    assert not changed["supersedes_observation_id"]
    assert changed["observation_id"] == new_id
    assert new_id != prior_row["observation_id"]
    for other in {"unit", "currency", "basis"} - {field}:
        assert changed[other] == prior_row[other]
    pd.testing.assert_frame_equal(prior, immutable_before)
    assert prior.iloc[0][field] == prior_row[field]


@pytest.mark.parametrize(("field", "enriched_fact"), [
    ("unit", "USD/share"),
    ("currency", "USD"),
    ("basis", "GAAP"),
])
def test_null_to_value_economic_fact_enrichment_still_supersedes(field, enriched_fact):
    # DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07 gates only a change
    # between two non-null facts; a null prior enriched to a value still supersedes.
    prior_row = _lineage_row("old", 0)
    prior_row[field] = None
    prior = pd.DataFrame([prior_row], columns=revisions._OBSERVATION_COLUMNS)
    immutable_before = prior.copy(deep=True)

    enriched = _lineage_row("enriched", 1)
    enriched[field] = enriched_fact
    revisions._apply_lineage([enriched], prior)
    assert enriched["correction_state"] == "supersedes"
    assert enriched["supersedes_observation_id"] == prior_row["observation_id"]
    pd.testing.assert_frame_equal(prior, immutable_before)


class _SourceClient:
    def __init__(self, earnings, revenue):
        self.earnings_estimate = earnings
        self.revenue_estimate = revenue


def _collect(output_dir: Path, session: str, client) -> dict:
    return revisions.accrue_expectation_observations(
        ["ACME"], output_dir=output_dir, collection_session_id=session,
        ticker_factory=lambda _: client,
    )


@pytest.mark.parametrize("status", ["partial", "null"])
def test_partial_or_null_after_good_collection_preserves_prior_rows(tmp_path, status):
    good = _SourceClient(_estimates("EPS"), _estimates("revenue"))
    assert _collect(tmp_path, "good", good) == {"attempts": 1, "observations": 14}
    observation_path = tmp_path / "expectation_observations.parquet"
    before = pd.read_parquet(observation_path, dtype_backend="pyarrow").copy(deep=True)
    before_bytes = observation_path.read_bytes()

    # Partial includes typed absent EPS average and no revenue accessor data.
    # Null includes no estimates at all. Neither may erase the good session.
    next_client = _SourceClient(_estimates("EPS", average=None), None) if status == "partial" else _SourceClient(None, None)
    added = _collect(tmp_path, "later", next_client)
    after = pd.read_parquet(observation_path, dtype_backend="pyarrow")
    prior_after = after[after["collection_session_id"] == "good"].reset_index(drop=True)
    # Nullable Arrow decoding keeps genuine NULLs stable even when appending
    # the first non-null string changes the physical parquet column type.
    assert before.to_dict("records") == prior_after.to_dict("records")
    assert set(before["observation_id"]).issubset(set(after["observation_id"]))
    attempts = pd.read_parquet(tmp_path / "expectation_attempts.parquet")
    assert len(attempts) == 2
    assert attempts.iloc[0]["status"] == "success"
    assert attempts.iloc[-1]["status"] == status
    expected_new = 7 if status == "partial" else 0
    assert added == {"attempts": 1, "observations": expected_new}
    assert attempts.iloc[-1]["observation_count"] == expected_new
    assert len(after) == len(before) + expected_new
    if status == "null":
        assert observation_path.read_bytes() == before_bytes
    else:
        missing_average = after[
            (after["collection_session_id"] == "later")
            & (after["observation_type"] == "average")
        ].iloc[0]
        assert pd.isna(missing_average["value"])
        assert missing_average["missingness_reason"] == "UNESTIMABLE"


class _LegacyClient:
    def __init__(self, earnings, *, raises=False, up=4.0, down=0.0):
        self.eps_revisions = pd.DataFrame({"upLast30days": [up], "downLast30days": [down]}, index=["+1y"])
        self.eps_trend = pd.DataFrame({"current": [10.0], "30daysAgo": [9.0], "90daysAgo": [8.0]}, index=["+1y"])
        self._earnings = earnings
        self._raises = raises
        self.revenue_estimate = None

    @property
    def earnings_estimate(self):
        if self._raises:
            raise AttributeError("synthetic unavailable accessor")
        return self._earnings


@pytest.mark.parametrize(("case", "expected_covering", "expected_cov"), [
    ("positive", 20, 0.2),
    ("accessor_unavailable", None, None),
    ("field_missing", None, None),
    ("nan", None, None),
    ("zero", None, None),
    ("fallback_0y", 15, round(2 / 15, 4)),
])
def test_legacy_direct_client_keeps_coverage_separate_from_reviser_count(case, expected_covering, expected_cov):
    earnings = pd.DataFrame({"numberOfAnalysts": [20.0]}, index=["+1y"])
    if case == "field_missing":
        earnings = pd.DataFrame({"unrelatedField": [5]}, index=["+1y"])
    elif case in {"nan", "zero"}:
        earnings.loc["+1y", "numberOfAnalysts"] = float("nan") if case == "nan" else 0
    elif case == "fallback_0y":
        earnings = pd.DataFrame({"numberOfAnalysts": [15.0]}, index=["0y"])
    client = _LegacyClient(
        earnings, raises=case == "accessor_unavailable",
        up=3.0 if case == "fallback_0y" else 4.0,
        down=1.0 if case == "fallback_0y" else 0.0,
    )
    result = revisions._one("ACME", ticker_client=client)
    assert result is not None
    assert result["n_analysts"] == 4
    assert result["breadth"] == (0.5 if case == "fallback_0y" else 1.0)
    assert result["n_covering"] == expected_covering
    assert result["breadth_cov"] == expected_cov
