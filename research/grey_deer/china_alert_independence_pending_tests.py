"""Pending evidence-unit acceptance, not part of a passing product-test claim.
Run explicitly against the incumbent audit. This does not modify a policy or ledger.
"""
import pytest
from research.grey_deer.probe_china_alert_independence import examine


@pytest.fixture(scope='module')
def result():
    return examine()


def test_one_alert_cannot_qualify_force_authority(result):
    assert result['synthetic']['one_alert']['can_force'] is False


def test_many_daily_calls_on_one_decline_do_not_establish_independent_evidence(result):
    s = result['synthetic']
    assert s['daily_alert_calls'] == 40
    assert s['maximum_disjoint_21_session_alert_windows'] == 2
    assert s['dense_daily_alerts']['can_force'] is False


def test_diagnostic_does_not_claim_policy_or_forecast_acceptance(result):
    assert result['source_or_policy_changed'] is False
    assert result['forecast_validated'] is False
    assert result['production'] is False
