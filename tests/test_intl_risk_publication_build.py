"""Normal Risk publication joins existing packets without manufacturing grants."""
from copy import deepcopy

from scripts import build_intl
from tests.test_intl_risk_native_publication import native


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


def test_normal_workspace_consumes_only_same_successful_native_publication(tmp_path, native):
    from lib.intl_risk_publication import publish_risk_snapshot
    payload, _ = native
    path = tmp_path/'intl_risk/latest.json'
    path.parent.mkdir()  # The incumbent main creates this same directory first.
    receipt = publish_risk_snapshot(path, payload)
    workspace = publish(tmp_path, risk_desk=payload, risk_publication=receipt)
    assert len(workspace['risks']) == 10
    for panel in workspace['risks']:
        domain = panel['risk_section']['domain_panels']['us_transmission']
        assert domain['summary']['state'] == 'contained'
        assert domain['summary']['quality'] == 'qualified'
        assert domain['observations']['calculation_at'] == payload['two_tier']['built']
        assert domain['observations']['origin_coverage'] == dict(available=3,total=6)
    # The same complete native packet grants nothing without its write receipt.
    withheld = publish(tmp_path, risk_desk=payload)
    assert all(p['risk_section']['domain_panels']['us_transmission']['summary']['state'] is None
               for p in withheld['risks'])
    # A stale receipt must not bless a changed artifact on the actual caller.
    path.write_text(path.read_text()+' ')
    changed = publish(tmp_path, risk_desk=payload, risk_publication=receipt)
    assert all(p['risk_section']['domain_panels']['us_transmission']['summary']['state'] is None
               for p in changed['risks'])


def test_normal_workspace_joins_verified_history_and_native_risk_without_cross_grants(tmp_path, native, monkeypatch):
    from lib import config
    from lib.intl_risk_publication import publish_risk_snapshot
    from tests.test_intl_history_publication_build import _native_history_receipt
    history_read, settings = _native_history_receipt(tmp_path, monkeypatch)
    monkeypatch.setattr(config, 'load', lambda: settings)
    history_sources = build_intl._history_publication_sources({'JP': history_read})
    risk_payload, _ = native
    path=tmp_path/'intl_risk/latest.json';path.parent.mkdir()
    publication=publish_risk_snapshot(path,risk_payload)
    workspace=build_intl._publication_workspace(
        None,data_root=tmp_path,evaluated_at=risk_payload['built'],
        history_sources=history_sources,risk_desk=risk_payload,risk_publication=publication)
    history=next(s for s in workspace['histories'][0]['sections'] if s['selected_market']=='JP')
    assert history['source_read_status']=='ready' and history['snapshot_compare']['selection']['eligible']
    assert history['snapshot_compare']['reason']=='not_requested'
    assert history['events']['records']==[] and history['as_known']['available'] is False
    assert all(p['risk_section']['domain_panels']['us_transmission']['summary']['state']=='contained'
               for p in workspace['risks'])
    assert all(row['country_credit_change']['quality']=='unknown'
               for p in workspace['risks'] for row in p['risk_section']['pressure_rows'])
    assert len(workspace['histories'])==1 and len(workspace['risks'])==10
