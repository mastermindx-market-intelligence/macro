"""Normal Risk publication joins existing packets without manufacturing grants."""
from copy import deepcopy

from scripts import build_intl


def publish(root, **kwargs):
    return build_intl._publication_workspace(
        None, data_root=root, evaluated_at="2026-10-08T23:00:00Z", **kwargs)


def test_missing_sources_keep_complete_risk_roster_and_generation(tmp_path):
    workspace = publish(tmp_path)
    assert len(workspace["risks"]) == len(workspace["panels"]) == 10
    assert len(workspace["risk_registry"]["markets"]) == 7
    for panel in workspace["risks"]:
        assert panel["generation"] == workspace["config"]["source_reference"]
        section = panel["risk_section"]
        assert section["context"]["selected_market"] is None
        assert len(section["pressure_rows"]) == 7
        assert section["domain_panels"]["us_transmission"]["summary"]["state"] is None
        assert all(row["country_credit_change"]["quality"] == "unknown"
                   for row in section["pressure_rows"])


def test_raw_owned_packets_are_not_publication_permission(tmp_path):
    risk = {"two_tier": {"state": "CALM", "us_from_others": 42}, "private": "not approved"}
    cgl = {"pressure": {"KR": {"pct": 88}}, "private": "not approved"}
    before = deepcopy((risk, cgl))
    workspace = publish(tmp_path, risk_desk=risk, cgl=cgl)
    assert (risk, cgl) == before
    for panel in workspace["risks"]:
        section = panel["risk_section"]
        assert section["domain_panels"]["us_transmission"]["summary"]["state"] is None
        assert "not approved" not in repr(section)


def test_risk_mount_failure_preserves_macro_and_overview(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("owned Risk failure")
    monkeypatch.setattr(build_intl, "attach_risks", fail)
    workspace = publish(tmp_path)
    assert len(workspace["panels"]) == len(workspace["macros"]) == 10
    assert "risks" not in workspace


def test_macro_mount_failure_still_publishes_independent_risk(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("owned Macro failure")
    monkeypatch.setattr(build_intl, "attach_macros", fail)
    workspace = publish(tmp_path)
    assert len(workspace["panels"]) == len(workspace["risks"]) == 10
    assert "macros" not in workspace


def test_invalid_raw_risk_does_not_remove_valid_macro(tmp_path):
    workspace = publish(tmp_path, risk_desk=[], cgl=None)
    assert len(workspace["panels"]) == len(workspace["macros"]) == 10
    assert "risks" not in workspace
