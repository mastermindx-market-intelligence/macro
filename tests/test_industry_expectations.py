import pytest
from copy import deepcopy
from engine.industry_expectations import expectation_changes, lag_sensitivity, aggregate_industry_context


def observation(id="a", value=1., date="2000-01-01T00:00:00Z", **extra):
    return dict(observation_id=id, value=value, historical_effective_at=date,
                source_available_at=date, system_observed_at="2026-11-14T00:00:00Z",
                security_ref="sec:one", metric="eps", period_end="2000-12-31", currency="USD",
                basis="GAAP_PER_SHARE", source_ref="historical-series", missingness_reason=None, **extra)


def test_reconstruction_is_usable_not_falsely_pit():
    rows = [observation(), observation("b", 1.2, "2000-04-01T00:00:00Z")]
    result = expectation_changes(rows, as_of="2000-08-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["nodes"][0]["change"] == pytest.approx(.2)
    assert result["nodes"][0]["clock_assumed"]
    assert not result["nodes"][0]["historical_knowability_proven"]
    assert result["nodes"][0]["actual_capture_at"].startswith("2026")


def test_as_captured_excludes_future_observation():
    result = expectation_changes([observation()], as_of="2000-08-01T00:00:00Z", mode="AS_CAPTURED")
    assert result["records_used"] == 0
    assert result["exclusions"]["NOT_AVAILABLE_AT_CUTOFF"] == 1


def test_current_snapshot_cannot_be_backdated_without_history():
    row = observation(); del row["historical_effective_at"]
    result = expectation_changes([row], as_of="2000-08-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["nodes"] == []


def test_future_effective_value_excluded_and_delay_sensitivity():
    rows = [observation(), observation("b", 1.2, "2000-04-01T00:00:00Z"),
            observation("future", 10., "2001-01-01T00:00:00Z")]
    result = lag_sensitivity(rows, as_of="2000-07-15T00:00:00Z")
    assert set(result["readings"]) == {"0", "30", "60"}
    assert result["readings"]["0"]["nodes"][0]["change"] == pytest.approx(.2)
    assert result["readings"]["30"]["nodes"][0]["change"] is None
    assert result["selected_best_lag"] is None


def test_period_and_basis_changes_are_not_revisions():
    a, b = observation(), observation("b", 8., "2000-04-01T00:00:00Z")
    b["period_end"] = "2001-12-31"
    result = expectation_changes([a, b], as_of="2000-08-01T00:00:00Z", mode="RECONSTRUCTED")
    assert len(result["nodes"]) == 2
    assert all(n["change"] is None for n in result["nodes"])


def test_zero_missing_and_negative_values_remain_distinct():
    rows = [observation(value=-1.), observation("b", 0., "2000-04-01T00:00:00Z")]
    result = expectation_changes(rows, as_of="2000-08-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["nodes"][0]["change"] == 1.
    bad = observation("missing"); bad["missingness_reason"] = "NO_COVERAGE"; bad["value"] = 0
    assert expectation_changes([bad], as_of="2000-08-01T00:00:00Z", mode="RECONSTRUCTED")["nodes"] == []


def test_duplicate_identity_cannot_fabricate_change():
    a = observation()
    result = expectation_changes([a, a], as_of="2000-05-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["records_used"] == 1
    b = deepcopy(a); b["value"] = 2
    with pytest.raises(ValueError, match="conflicting"):
        expectation_changes([a, b], as_of="2000-05-01T00:00:00Z", mode="RECONSTRUCTED")


def test_same_clock_ambiguity_and_stale_not_positive():
    result = expectation_changes([observation(), observation("b", 2.)],
                                as_of="2000-05-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["nodes"][0]["state"] == "AMBIGUOUS"
    result = expectation_changes([observation()], as_of="2005-01-01T00:00:00Z", mode="RECONSTRUCTED")
    assert result["nodes"][0]["state"] == "STALE" and result["nodes"][0]["change"] is None


def test_industry_aggregation_preserves_denominators_and_basis():
    rows = [observation(), observation("b", 1.2, "2000-04-01T00:00:00Z")]
    asof = "2000-08-01T00:00:00Z"
    result = expectation_changes(rows, as_of=asof, mode="RECONSTRUCTED")
    members = [{"security_ref": "sec:one", "industry": "Meals", "valid_from": "1990-01-01T00:00:00Z"},
               {"security_ref": "sec:two", "industry": "Meals", "valid_from": "1990-01-01T00:00:00Z"}]
    out = aggregate_industry_context(result, members, as_of=asof)
    assert out["groups"][0]["revision_breadth"] == 1.
    assert out["groups"][0]["industry_members"] == 2
    assert out["groups"][0]["comparable_changes"] == 1
    assert not out["financial_influence"]


@pytest.mark.parametrize("lag", [-1, 1.5, True])
def test_invalid_lags(lag):
    with pytest.raises(ValueError):
        expectation_changes([], as_of="2000-01-01T00:00:00Z", mode="RECONSTRUCTED", assumed_lag_days=lag)
