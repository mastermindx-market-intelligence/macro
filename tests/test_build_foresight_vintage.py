"""Exercise Foresight publication receipts through the real builder and page writer.

All producer calls are synthetic; Jinja rendering and lib.pages.write_page are real.
Every output lives under tmp_path. A successful JSON write says nothing about the
age of its data or whether an existing HTML artifact has matching contents.
"""
from __future__ import annotations

import json
import socket
import sys
import types
from pathlib import Path

import pytest

from lib import pages
from scripts import build_foresight as builder


OLD_JSON = '{"marker":"previous-json"}\n'
OLD_HTML = "<!doctype html><html><head></head><body>previous-html</body></html>\n"
PARTIAL_JSON = '{"marker":'
VALID_TEMPLATE = (
    '<!doctype html><html><head><meta charset="utf-8"></head>'
    '<body>{{ cascade.marker }} / {{ asof }}</body></html>'
)
BROKEN_TEMPLATE = "{% if %}"
PAYLOAD = {"marker": "fixture-cascade", "asof": "2000-01-01", "themes": []}
HEALTH = {"status": "FULL"}
EXPECTED_JSON = {**PAYLOAD, "health": HEALTH}
WARNING_PREFIX = "::warning title=foresight::"


@pytest.fixture
def build_case(tmp_path, monkeypatch):
    """Keep every engine, ledger, collector and model outside this IO fixture."""
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    monkeypatch.setattr(builder.config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(builder.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(pages, "_shim_checked", False)

    def no_network(*args, **kwargs):
        pytest.fail("publication receipt fixture attempted network access")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    # Empty package paths prevent an unlisted producer from importing real code.
    # monkeypatch restores both pre-existing modules and absent keys on teardown.
    for name in ("engine", "engine.research_vault", "collectors"):
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)

    results = {
        "engine.policy_calendar": {"compute_policy_calendar": {}},
        "engine.foresight_cascade": {"compute_foresight_cascade": PAYLOAD},
        "engine.foresight_grader": {"grade": {}},
        "engine.foresight_shadow": {
            "compute_shadow_stages": 0, "grade_shadow": {},
            "shadow_promotion_report": {}, "compute_heat_shadow": 0,
        },
        "engine.theme_emergence": {"compute_theme_emergence": {}},
        "engine.subsector_scan": {"compute_subsector_scan": {}},
        "engine.power_scarcity": {"compute_power_scarcity": {}},
        "engine.foresight_enb": {"compute_enb": {}},
        "engine.foresight_convergence": {"compute_convergence": {}},
        "engine.foresight_analyst": {"load_committed_theses": {"n_theses": 0}},
        "engine.thesis_monitor": {"compute_thesis_monitor": {}},
        "engine.theme_activity": {"compute_real_activity": {}},
        "engine.foresight_divergence": {
            "compute_divergence_board": {}, "grade_divergence_ledger": {},
        },
        "engine.baskets": {"compute_baskets": {}},
        "engine.research_vault.divergence_handoff": {"compute_with_capture": {}},
        "engine.foresight_health": {"compute_foresight_health": HEALTH},
    }
    for name, functions in results.items():
        module = types.ModuleType(name)
        for function, result in functions.items():
            setattr(module, function, lambda *args, _result=result, **kwargs: _result)
        monkeypatch.setitem(sys.modules, name, module)

    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True)
    templates = tmp_path / "templates"
    templates.mkdir()
    # Synthetic local assets let the existing page writer inject its real markers.
    (templates / "data_base.js").write_text("// fixture data-base asset\n")
    (site / "shared_shell_bridge.js").write_text("// fixture shared-shell asset\n")
    (site / "shared_shell.css").write_text("/* fixture shared-shell asset */\n")
    template = templates / "foresight.html.j2"
    template.write_text(VALID_TEMPLATE)
    json_path = site / "basketdata" / "foresight_cascade.json"
    html_path = site / "foresight.html"
    json_path.write_text(OLD_JSON)
    state = {"json_fault": None, "html_fault": False}
    real_write_text = Path.write_text

    def write_with_targeted_fault(path, text, *args, **kwargs):
        if path == json_path and state["json_fault"]:
            if state["json_fault"] == "partial":
                real_write_text(path, PARTIAL_JSON, *args, **kwargs)
            raise OSError("synthetic JSON write failure: " + state["json_fault"])
        if path == html_path and state["html_fault"]:
            raise OSError("synthetic HTML write failure")
        return real_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_with_targeted_fault)
    return types.SimpleNamespace(
        root=tmp_path, site=site, template=template,
        json=json_path, html=html_path, state=state,
    )


def _render_failure_warning(capsys):
    lines = [
        line for line in capsys.readouterr().out.splitlines()
        if line.startswith(WARNING_PREFIX)
    ]
    assert len(lines) == 1
    warning = lines[0]
    assert "template render failed" in warning
    assert "site/foresight.html was NOT rewritten this run" in warning
    assert "TemplateSyntaxError" in warning
    assert "last-committed" not in warning
    assert "already refreshed" not in warning
    assert "page and JSON now disagree" not in warning
    return warning


def _assert_current_html(case):
    html = case.html.read_text()
    assert "fixture-cascade / 2000-01-01" in html
    assert "data-dbase" in html
    assert 'name="mmx-shell-document"' in html
    assert (case.site / "data_base.js").is_file()


def _assert_json_failure(case, fault):
    assert case.json.read_text() == (PARTIAL_JSON if fault == "partial" else OLD_JSON)


@pytest.mark.parametrize("fault", ["before", "partial"])
@pytest.mark.parametrize("html_exists", [False, True])
def test_json_and_render_failure_report_unconfirmed_contents(
    build_case, fault, html_exists, capsys, caplog,
):
    case = build_case
    if html_exists:
        case.html.write_text(OLD_HTML)
    case.template.write_text(BROKEN_TEMPLATE)
    case.state["json_fault"] = fault

    assert builder.main() == 0

    _assert_json_failure(case, fault)
    if html_exists:
        assert case.html.read_text() == OLD_HTML
    else:
        assert not case.html.exists()
    warning = _render_failure_warning(capsys)
    assert "foresight_cascade.json write completed this run" not in warning
    assert "foresight_cascade.json write did not complete" in warning
    assert "current JSON contents are unconfirmed" in warning
    assert "foresight_cascade.json emit failed" in caplog.text


@pytest.mark.parametrize("html_exists", [False, True])
@pytest.mark.parametrize("identical_json", [False, True])
def test_completed_json_write_does_not_claim_fresh_data_or_changed_vintage(
    build_case, html_exists, identical_json, capsys,
):
    case = build_case
    if html_exists:
        case.html.write_text(OLD_HTML)
    if identical_json:
        case.json.write_text(json.dumps(EXPECTED_JSON, separators=(",", ":")))
    case.template.write_text(BROKEN_TEMPLATE)

    assert builder.main() == 0

    assert json.loads(case.json.read_text()) == EXPECTED_JSON
    if html_exists:
        assert case.html.read_text() == OLD_HTML
    else:
        assert not case.html.exists()
    warning = _render_failure_warning(capsys)
    assert "foresight_cascade.json write completed this run" in warning
    assert "HTML/JSON alignment is unconfirmed" in warning
    assert "refreshed" not in warning
    assert "write did not complete" not in warning


def test_success_uses_existing_page_writer(build_case, capsys):
    assert builder.main() == 0
    assert json.loads(build_case.json.read_text()) == EXPECTED_JSON
    _assert_current_html(build_case)
    assert WARNING_PREFIX not in capsys.readouterr().out


@pytest.mark.parametrize("fault", ["before", "partial"])
def test_json_failure_keeps_existing_nonfatal_html_publication(
    build_case, fault, capsys, caplog,
):
    case = build_case
    case.state["json_fault"] = fault

    assert builder.main() == 0

    _assert_json_failure(case, fault)
    _assert_current_html(case)
    assert "foresight_cascade.json emit failed" in caplog.text
    assert WARNING_PREFIX not in capsys.readouterr().out


def test_each_run_observes_its_own_json_write_and_can_recover(build_case, capsys):
    case = build_case
    assert builder.main() == 0
    _assert_current_html(case)
    published_html = case.html.read_bytes()
    assert WARNING_PREFIX not in capsys.readouterr().out

    case.state["json_fault"] = "partial"
    case.template.write_text(BROKEN_TEMPLATE)
    assert builder.main() == 0
    assert case.html.read_bytes() == published_html
    _assert_json_failure(case, "partial")
    warning = _render_failure_warning(capsys)
    assert "foresight_cascade.json write did not complete" in warning
    assert "foresight_cascade.json write completed this run" not in warning

    case.state["json_fault"] = None
    case.template.write_text(VALID_TEMPLATE)
    assert builder.main() == 0
    assert json.loads(case.json.read_text()) == EXPECTED_JSON
    _assert_current_html(case)
    assert WARNING_PREFIX not in capsys.readouterr().out


def test_html_writer_failure_remains_outside_template_failure_handler(build_case, capsys):
    case = build_case
    case.html.write_text(OLD_HTML)
    case.state["html_fault"] = True

    with pytest.raises(OSError, match="synthetic HTML write failure"):
        builder.main()

    assert json.loads(case.json.read_text()) == EXPECTED_JSON
    assert case.html.read_text() == OLD_HTML
    assert WARNING_PREFIX not in capsys.readouterr().out
