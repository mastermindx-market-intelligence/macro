"""Actual bridge -> existing manifest build -> admin panel connection."""
import copy
import json

import pytest

from admin import experiments as panel
from engine import experiments_registry as registry
from tests.test_research_codegen_bridge import make_case, persist


def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry, "_read_json", lambda _: {"audited": "2010-07-01", "experiments": []})
    monkeypatch.setattr(registry, "_load_machine_registry_entries", lambda: [])
    # Test publication never sends a notification.
    monkeypatch.setattr(registry, "_notify_newly_ready", lambda *a: None)


def test_actual_bridge_build_panel_and_no_ready_alert(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    isolated_registry(monkeypatch)
    site = tmp_path / "site"
    assert registry.build(site, trusted_codegen_bindings=(binding,), commission=commission) == 1
    artifact = site / "marketdata/experiments.json"
    monkeypatch.setattr(panel, "_REGISTRY", artifact)
    result = panel.panel()
    assert result["ok"] is True and result["n"] == result["ready_count"] == 0
    assert result["experiments"] == [] and result["research_diagnostics_state"] == "AVAILABLE"
    diagnostic = result["research_diagnostics"][0]
    assert diagnostic["aggregates"]["paired_mean_improvement"] == pytest.approx(.175)
    assert diagnostic["execution_enabled"] is False
    assert "actions" not in diagnostic and "ready" not in diagnostic
    assert panel.alert_summary()["ready"] == []
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize("damage", ["extra", "nan", "flag", "oversize", "partial", "duck"])
def test_published_projection_rejects_all_dispositions_on_damage(tmp_path, monkeypatch, damage):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    isolated_registry(monkeypatch)
    payload = registry.compute(trusted_codegen_bindings=(binding,), commission=commission)
    row = payload["research_diagnostics"][0]
    if damage == "extra":
        row["candidate_source"] = "private-code"
    elif damage == "nan":
        row["aggregates"]["paired_mean_improvement"] = float("nan")
    elif damage == "flag":
        row["execution_enabled"] = True
    elif damage == "oversize":
        payload["research_diagnostics"] = [row] * 33
    elif damage == "partial":
        payload["research_diagnostics"].append({"status": "REFUSED"})
    else:
        class Foreign(dict):
            def items(self):
                pytest.fail("subclass hook invoked")
        payload["research_diagnostics"] = [Foreign(row)]
    assert panel._research_diagnostics(payload) == ([], "UNAVAILABLE")


def test_default_build_has_no_diagnostic_read_and_legacy_counts_unchanged(tmp_path, monkeypatch):
    from engine.research_codegen import bridge
    monkeypatch.setattr(bridge, "load_diagnostics", lambda *a, **k: pytest.fail("implicit read"))
    isolated_registry(monkeypatch)
    assert registry.compute()["research_diagnostics"] == []
    legacy = {"experiments": [{"id": "old", "name": "Old", "status": "accruing", "come_back_on": "2001-01-01"}]}
    monkeypatch.setattr(panel, "_read_json", lambda _: copy.deepcopy(legacy))
    got = panel.panel()
    assert got["n"] == 1 and got["ready_count"] == 1
    assert got["research_diagnostics_state"] == "DISABLED"


def test_explicit_binding_without_commission_does_not_overwrite_previous_manifest(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    isolated_registry(monkeypatch)
    site = tmp_path / "site"
    target = site / "marketdata/experiments.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b'"prior"')
    assert registry.build(site, trusted_codegen_bindings=(binding,)) == 0
    assert target.read_bytes() == b'"prior"'


def test_missing_bridge_dependency_preserves_legacy_panel(monkeypatch):
    import builtins
    original_import = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name == "engine.research_codegen.bridge":
            raise ImportError("simulated incomplete installation")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", blocked)
    monkeypatch.setattr(panel, "_read_json", lambda _: {"experiments": [{"id": "old", "name": "Old"}], "research_diagnostics": [{}]})
    result = panel.panel()
    assert result["ok"] and result["n"] == 1
    assert result["research_diagnostics"] == [] and result["research_diagnostics_state"] == "UNAVAILABLE"
    assert panel._research_diagnostics({"research_diagnostics": [], "research_diagnostics_state": "UNAVAILABLE"}) == ([], "UNAVAILABLE")


def test_actual_site_publisher_reprojects_retained_queue_without_changing_measurement(tmp_path, monkeypatch):
    import sys
    from scripts import build_research_factory_review_queue as queue_builder
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    isolated_registry(monkeypatch)
    rf = tmp_path / 'data/research_factory'
    monkeypatch.setattr(sys, 'argv', ['queue', '--rf-dir', str(rf), '--write'])
    assert queue_builder.main(trusted_codegen_artifacts=(binding,), synthetic_commission=commission) == 0
    before = json.loads((rf / 'review/queue.json').read_text())['research_diagnostics']
    monkeypatch.setattr(registry, '_root', lambda: tmp_path)
    assert registry.build_published(tmp_path / 'site') == 1
    result = json.loads((tmp_path / 'site/marketdata/experiments.json').read_text())
    assert result['research_diagnostics'] == before
    assert result['n'] == result['ready_count'] == 0
    # A subsequent queue writer must deliberately retain or retire the publication.
    prior = (rf / 'review/queue.json').read_bytes()
    assert queue_builder.main() == 2
    assert (rf / 'review/queue.json').read_bytes() == prior
    monkeypatch.setattr(sys, 'argv', ['queue', '--rf-dir', str(rf), '--write', '--retain-diagnostics'])
    assert queue_builder.main() == 0
    assert json.loads((rf / 'review/queue.json').read_text())['research_diagnostics'] == before
    monkeypatch.setattr(sys, 'argv', ['queue', '--rf-dir', str(rf), '--write', '--retire-diagnostics'])
    assert queue_builder.main() == 0
    assert registry.build_published(tmp_path / 'site') == 1
    assert json.loads((tmp_path / 'site/marketdata/experiments.json').read_text())['research_diagnostics'] == []


def test_invalid_retained_queue_preserves_legacy_publish_with_unavailable(tmp_path, monkeypatch):
    isolated_registry(monkeypatch)
    source = tmp_path / 'data/research_factory/review/queue.json'
    source.parent.mkdir(parents=True)
    source.write_text('{"research_diagnostics":[],"research_diagnostics":[]}')
    monkeypatch.setattr(registry, '_root', lambda: tmp_path)
    assert registry.build_published(tmp_path / 'site') == 1
    result = json.loads((tmp_path / 'site/marketdata/experiments.json').read_text())
    assert result['research_diagnostics_state'] == 'UNAVAILABLE'
    assert result['experiments'] == []
