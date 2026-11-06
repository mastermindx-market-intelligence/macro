"""Bounded normal-publisher and template acceptance for R10 EOD values."""
from tests.test_intl_eod_publication import _setup, _panel, _overview, EVALUATED, GRANT, GENERATION
from lib.intl_eod_publication import build_eod_inputs

def test_normal_international_publisher_consumes_completed_eod_package(tmp_path):
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path)
    ws = publisher._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert ws is not None
    usd = _panel(ws)
    assert usd["eligible_count"] == 7
    assert ws["binding_version"] == 2
    assert "intl-supplied-close:sha256:" in usd["context"]["source_reference"]


def test_normal_publisher_keeps_safe_unavailable_on_status_failure(tmp_path):
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path, late=False)
    ws = publisher._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert ws is not None
    usd = _panel(ws)
    assert usd["eligible_count"] == 0
    assert usd["ranking_reason"] == "no_qualified_returns"


def test_delayed_source_notice_and_actual_window_dates_are_rendered(tmp_path):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    frame, _ = _setup(tmp_path)
    delayed, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, rights=GRANT)
    panel = _panel(_overview(delayed, inputs))
    loader = FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates"))
    page = Environment(loader=loader, autoescape=True).get_template(
        "intl_workspace/overview.html.j2").render(
        overview=panel, context_id="test-eod", generation=GENERATION)
    assert 'data-im-eod-disclosure' not in page  # The shared shell owns the notice.
    assert "2026-10-07" in page
    assert "<time " in page


def test_delayed_notice_is_owned_by_publisher_and_outside_switchable_panels(tmp_path):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from scripts import build_intl as publisher
    frame, _ = _setup(tmp_path)
    ws = publisher._publication_workspace(frame, data_root=tmp_path, evaluated_at=EVALUATED)
    assert ws['eod_snapshot']['as_of'] == '2026-10-07'
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / 'templates')),
                      autoescape=True)
    page = env.from_string("{% macro t(en,zh) %}{{en}} / {{zh}}{% endmacro %}"
                           "{% include 'intl_workspace/shell.html.j2' %}").render(intl_workspace=ws)
    assert page.count('data-im-eod-disclosure') == 1
    assert page.index('data-im-eod-disclosure') < page.index('data-im-panel')
    assert '2026-10-07' in page and 'not live prices' in page


def test_source_hash_prefix_alone_does_not_assert_a_delayed_data_policy(tmp_path):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    frame, _ = _setup(tmp_path)
    delayed, inputs = build_eod_inputs(frame, data_root=tmp_path,
                                      evaluated_at=EVALUATED, rights=GRANT)
    overview = _panel(_overview(delayed, inputs))
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / 'templates')),
                      autoescape=True)
    page = env.get_template('intl_workspace/overview.html.j2').render(
        overview=overview, context_id='source-hash-only', generation=GENERATION)
    assert 'data-im-eod-disclosure' not in page
    assert '2026-10-07' in page
