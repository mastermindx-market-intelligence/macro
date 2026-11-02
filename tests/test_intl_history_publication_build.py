"""The existing publisher mounts History without implying source disclosure."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

from lib.intl_library_mount import render_international_pages
from scripts import build_intl


def _fixture(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_shell = _fixture("history_publication_shell", "test_intl_inspector_mount.py")
_history = _fixture("history_publication_data", "test_intl_history_mount.py")


def publish(root, **kwargs):
    return build_intl._publication_workspace(
        None, data_root=root, evaluated_at="2026-10-09T01:30:00Z", **kwargs)


def test_normal_publication_has_one_history_catalogue_and_no_invented_grants(tmp_path):
    workspace = publish(tmp_path)
    assert len(workspace["histories"]) == 1
    panel = workspace["histories"][0]
    assert panel["generation"] == workspace["config"]["source_reference"]
    assert [s["selected_market"] for s in panel["sections"]] == workspace["config"]["markets"]
    assert len(panel["sections"]) == 7
    assert all(s["source_read_status"] == "unknown" and s["points"] == [] for s in panel["sections"])
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_explicit_supplied_projection_remains_detached_and_market_bound(tmp_path):
    _, args = _history.fixture()
    sources = args["sources"]
    before = deepcopy(sources)
    workspace = publish(tmp_path, history_sources=sources)
    jp = next(s for s in workspace["histories"][0]["sections"] if s["selected_market"] == "JP")
    assert jp["source_read_status"] == "ready" and jp["points"]
    assert all(s["points"] == [] for s in workspace["histories"][0]["sections"] if s["selected_market"] != "JP")
    jp["points"][0]["growth_score"] = 999
    assert sources == before


def test_history_failure_preserves_other_complete_panels(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("private History error")
    monkeypatch.setattr(build_intl, "attach_history", fail)
    workspace = publish(tmp_path)
    assert "histories" not in workspace
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_malformed_history_input_does_not_remove_the_workspace(tmp_path):
    workspace = publish(tmp_path, history_sources=[])
    assert "histories" not in workspace
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_real_shell_keeps_all_owners_and_exposes_blank_disabled_scenario(tmp_path):
    workspace = publish(tmp_path)
    before = deepcopy(workspace)
    catalogue = json.loads((Path(__file__).parents[1] / "config/intl_library_catalogue.json").read_text())
    html, stocks = render_international_pages(
        _shell.ActualShell(), {"intl_workspace": workspace}, catalogue=catalogue)
    nodes = _shell.Document(html).nodes
    assert stocks == "Incumbent stocks" and workspace == before
    assert len([a for _, a in nodes if "data-im-history-panel" in a]) == 1
    assert len([a for _, a in nodes if "data-im-inspector-shell" in a]) == 1
    assert "data-im-library-static" in html and "data-im-compare-panel" in html
    assert html.count('data-view="macro"') == html.count('data-view="risk"') == 10
    history_button = next(a for tag, a in nodes if tag == "button" and a.get("data-im-view") == "history")
    assert "disabled" not in history_button
    inputs = [a for tag, a in nodes if tag == "input" and a.get("name") in {"local", "fx"}]
    assert len(inputs) == 2 and all(a.get("value", "") == "" for a in inputs)
    assert "disabled" in next(a for _, a in nodes if "data-im-scenario-fields" in a)
    ids = [a["id"] for _, a in nodes if "id" in a]
    assert len(ids) == len(set(ids))


def test_receipt_bridge_reuses_exact_receipts_without_new_disclosure(tmp_path, monkeypatch):
    from engine import international_macro_dashboard as owner
    _, args = _history.fixture()
    projected = deepcopy(args['sources']['JP']['history_read'])
    supplied = {'status': 'ready', 'frame': object()}
    seen = []
    def project(value):
        seen.append(value)
        return projected
    monkeypatch.setattr(owner, 'project_history_read', project, raising=False)
    sources = build_intl._history_publication_sources({'JP': supplied})
    assert len(seen) == 1 and seen[0] is supplied
    assert sources['JP']['history_read'] == projected
    for key in ('history_source', 'events', 'track_record'):
        assert sources['JP']['capabilities'][key] == dict(metadata='unknown', value='unknown')
    assert sources['JP']['turn_events'] == [] and sources['JP']['track_record'] is None
    assert sources['JP']['destinations'] == {}
    workspace = publish(tmp_path, history_sources=sources)
    for section in workspace['histories'][0]['sections']:
        assert section['points'] == [] and section['source_read_status'] == 'unknown'


def test_receipt_bridge_contains_one_bad_market_and_rejects_wrong_binding(monkeypatch, caplog):
    from engine import international_macro_dashboard as owner
    _, args = _history.fixture()
    projected = deepcopy(args['sources']['JP']['history_read'])
    bad, good = object(), object()
    def project(value):
        if value is bad:
            raise ValueError('private secret cannot appear in log')
        return deepcopy(projected)
    monkeypatch.setattr(owner, 'project_history_read', project, raising=False)
    sources = build_intl._history_publication_sources({'GB': bad, 'JP': good, 'KR': good})
    assert set(sources) == {'JP'}
    assert 'private secret' not in caplog.text


def test_receipt_bridge_does_not_invoke_projector_for_unknown_market(monkeypatch):
    from engine import international_macro_dashboard as owner
    def forbidden(*args, **kwargs):
        raise AssertionError('unknown market must not reach reader projector')
    monkeypatch.setattr(owner, 'project_history_read', forbidden, raising=False)
    assert build_intl._history_publication_sources({'UNKNOWN': object()}) == {}


def test_receipt_bridge_empty_and_invalid_sink():
    import pytest
    assert build_intl._history_publication_sources({}) == {}
    for invalid in ([], None, {'JP': object(), 7: object()}):
        with pytest.raises(ValueError, match='^invalid_history_receipts$'):
            build_intl._history_publication_sources(invalid)
