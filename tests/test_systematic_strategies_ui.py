"""Contract tests for the Systematic Strategies research workspace UI.

The workspace consumes a compiled ``systematic_research.v1`` artifact and is the
only place a research result reaches a reader. These tests pin the properties
that make that safe, and the design properties that make it readable. They are
deliberately split into two groups:

**Contract / honesty (the defects that would be serious).**
A malformed, hostile or partial artifact must fail closed to inputs-blocked with
metrics unavailable — never to a synthesized successful result. Specifically:
no ``NaN``/``Infinity`` on the page, no absent metric shown as ``0``, no
``research`` copy presented as ``validated``, no live-order affordance, and no
unknown account/fill field escaping through the allowlist.

**Structure / accessibility (the defects that would be visible).**
The required hierarchy and copy, one timestamp and one mode stamp, native
disclosure instead of inert buttons, scoped stylesheet with no colored
container edge and no gradient, and the responsive rules that keep 390px free
of horizontal overflow.

Static structure is asserted against the rendered HTML with regexes — this repo
has no HTML parser dependency and adding one is not in scope. Every render
writes to ``tmp_path``; nothing here writes into the repository or a site tree.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import render_systematic_strategies as renderer  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "systematic_research"
CSS = (ROOT / "templates" / "systematic_strategies.css").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates" / "systematic_strategies.html.j2").read_text(encoding="utf-8")

# Every fixture is stamped inside the day before the tests were written; pin it
# so the future-timestamp guard does not fire on a fixture that was valid once.
NOW = datetime(2026, 10, 22, 19, 0, tzinfo=timezone.utc)


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def available() -> dict:
    return load("research_available.json")


def render(report, *, now: datetime | None = None) -> str:
    return renderer.render_report(report, now=now or NOW)


def main_of(html: str) -> str:
    """The workspace body, minus the shared navigation chrome."""
    return html[html.index("<main") : html.index("</main>")]


# --------------------------------------------------------------------------- #
# available — the honest happy path
# --------------------------------------------------------------------------- #


def test_available_renders_title_deck_and_stance(available):
    body = main_of(render(available))
    assert "<h1 class=\"ss-title\">Systematic Strategies</h1>" in body
    assert "Test small edges. Keep only evidence." in body
    assert "Observe only" in body


def test_available_shows_no_strategy_is_approved_for_capital(available):
    body = main_of(render(available))
    assert "No strategy is approved for capital." in body
    # The capital count is rendered as a real 0, never hidden or spun.
    assert "<dt>Approved for capital</dt>" in body
    assert re.search(r"Approved for capital</dt>\s*<dd>0</dd>", body)


def test_candidate_labels_are_plain_words_and_real_names_live_in_methodology(available):
    body = main_of(render(available))
    assert ">Trend baseline</h3>" in body
    assert ">Pullback timing</h3>" in body
    # The artifact's own input name is shown under methodology, not as the label.
    assert "<dt>Input name</dt><dd>200-session time-series momentum</dd>" in body
    assert "<dt>Input name</dt><dd>Two-session RSI oversold re-entry</dd>" in body


def test_available_card_shows_state_horizon_prereq_and_evidence_control(available):
    body = main_of(render(available))
    assert body.count('<span class="ss-chip ss-chip--research_only">Research only</span>') == 2
    assert "<dt>Stance</dt>" in body
    assert "<dt>Horizon</dt>" in body
    assert "21 sessions" in body
    assert body.count("<dt>Next unmet prerequisite</dt>") == 2
    assert body.count('class="ss-evidence-toggle"') == 2
    assert body.count("View evidence") == 2


def test_evidence_splits_historical_prospective_and_paper(available):
    body = main_of(render(available))
    for heading in ("Historical record", "Forward testing", "Paper trading", "Method and provenance"):
        assert body.count(f">{heading}</h4>") == 2, heading
    assert "<dt>Forward records registered</dt>" in body
    assert "<dt>Forward records graded</dt>" in body
    assert "Not connected" in body


def test_evidence_carries_costs_limitations_versions_and_invalidators(available):
    body = main_of(render(available))
    assert "Costs and limitations" in body
    assert "Assumed cost" in body
    assert "synthetic0000" in body and "synthetic0001" in body
    assert "<dt>Sample start</dt><dd>2010-01-04</dd>" in body
    assert "What would invalidate this" in body
    assert "The edge disappears once realistic costs rise" in body


def test_every_displayed_metric_carries_its_unit(available):
    """A bare number under an unlabelled heading is a reader guessing.

    Law 3 (numbers carry meaning): only the two Sharpe ratios are unitless, and
    every other measure must state whether it is a percentage, a multiple or a
    cost in basis points.
    """
    body = main_of(render(available))
    for _key, label, _places in renderer.METRIC_LABELS:
        assert f"<th scope=\"row\">{label}</th>" in body, label
    assert "(%)" in body
    assert "basis points" in body
    assert "times per year" in body


def test_research_is_never_presented_as_validated(available):
    body = main_of(render(available)).lower()
    # The repo has a CI guard on this word in user copy; assert it directly so
    # this surface can never quietly join the offender list.
    assert "validated" not in body
    assert not re.search(r"approved for capital</dt>\s*<dd>no", body)


def test_no_live_trading_control_and_no_fabricated_chart(available):
    body = main_of(render(available))
    assert "Live orders disabled" in body
    for banned in ("<form", "<button", "type=\"submit\"", "<canvas", "<svg", "equity curve"):
        assert banned not in body, banned


def test_page_has_no_script_and_uses_native_disclosure(available):
    body = main_of(render(available))
    assert "<script" not in body
    assert body.count("<details") == body.count("</details>") == 2
    assert "<summary" in body


def test_timestamp_and_mode_are_shown_exactly_once(available):
    body = main_of(render(available))
    # One mode stamp and one as-of in the page header; the per-candidate chips
    # carry each candidate's own state and are not a repeated page stamp.
    assert body.count('<span class="ss-meta-mode">Research only</span>') == 1
    assert body.count("2026-10-22 18:26 UTC") == 1
    assert body.count("<time ") == 1


def test_reuses_the_shared_header_and_never_mints_another_one(available):
    html = render(available)
    assert '<nav class="site-nav">' in html
    assert html.count("<nav") == 1
    # SEO + theme conventions are reused, not re-implemented.
    assert 'name="description"' in html and 'rel="canonical"' in html
    assert '<link rel="stylesheet" href="theme.css">' in html
    assert '<link rel="stylesheet" href="systematic_strategies.css">' in html
    # Taking the header means taking its behaviour: without theme.js every
    # control in _site_nav.html.j2 (menus, search, theme + language toggles) is
    # dead markup. Pinned here so this page cannot regress that.
    assert 'src="theme.js"' in html
    assert '<link rel="stylesheet" href="navigation-refresh.css">' in html


def test_page_carries_no_site_side_effects_of_its_own():
    """The builder writes the page; the CSS asset copy stays opt-in."""
    assert "--copy-assets" in Path(renderer.__file__).read_text(encoding="utf-8")
    # No default output path anywhere in the CLI.
    source = Path(renderer.__file__).read_text(encoding="utf-8")
    assert 'default="site/' not in source
    assert "/site/systematic_strategies.html" not in source


# --------------------------------------------------------------------------- #
# unavailable / blocked / stale variants
# --------------------------------------------------------------------------- #


def test_historical_unavailable_never_renders_a_number(available):
    report = copy.deepcopy(available)
    for strategy in report["strategies"]:
        strategy["historical"].update(
            {
                "state": "unavailable",
                "sample_start": None,
                "sample_end": None,
                "net_sharpe": None,
                "net_cagr": None,
                "max_drawdown": None,
                "turnover": None,
                "cost_bps": None,
                "benchmark_sharpe": None,
            }
        )
    body = main_of(render(report))
    assert "Historical record unavailable" in body
    assert body.count("Not available") >= 12
    assert "0.41" not in body and "3.20" not in body
    assert "has no historical record" in body


def test_inputs_blocked_lists_what_is_missing_rather_than_an_empty_plot():
    body = main_of(render(load("inputs_blocked.json")))
    assert "Inputs blocked" in body or "Blocked" in body
    assert "Why the inputs are blocked" in body
    assert "Incomplete daily history" in body
    assert "<canvas" not in body and "<svg" not in body
    # Blocked candidates still name their own blocker.
    assert "<dt>Next unmet prerequisite</dt>" in body


def test_data_stale_variant_keeps_reasons_visible_beside_cards():
    body = main_of(render(load("data_stale.json")))
    assert "Why the inputs are blocked" in body
    assert "one revision behind the current one" in body
    # A stale page still shows its candidate — and still says it is stale.
    assert ">Trend baseline</h3>" in body
    assert "2026-10-08" in body


def test_empty_candidate_list_produces_a_useful_empty_state(available):
    report = copy.deepcopy(available)
    report["strategies"] = []
    body = main_of(render(report))
    assert "No candidates to show" in body
    assert "What is missing" in body
    assert "No strategy is approved for capital." in body
    assert "ss-card" not in body


# --------------------------------------------------------------------------- #
# fail closed — structural violations
# --------------------------------------------------------------------------- #


def fail_closed(html: str) -> str:
    body = main_of(html)
    assert "This record could not be read" in body
    assert "No strategy is approved for capital." in body
    # Nothing is estimated in the place of the record.
    assert "ss-card" not in body and "ss-metrics" not in body
    return body


@pytest.mark.parametrize(
    "mutate, expected",
    [
        # A missing required key is "missing required fields"; a present-but-wrong
        # value gets its own precise reason.
        (lambda r: r.pop("schema"), "required fields"),
        (lambda r: r.__setitem__("schema", "systematic_research.v2"), "does not read"),
        (lambda r: r.__setitem__("schema", "systematic_research.v1_extra"), "does not read"),
        (lambda r: r.__setitem__("mode", "LIVE"), "research-only"),
        (lambda r: r.pop("mode"), "required fields"),
        (lambda r: r.pop("live_orders_enabled"), "explicitly confirm"),
        (lambda r: r.__setitem__("live_orders_enabled", True), "live orders enabled"),
        (lambda r: r.__setitem__("live_orders_enabled", "false"), "live orders enabled"),
        (lambda r: r.__setitem__("status", "live"), "state this page can read"),
        (lambda r: r.pop("summary"), "required fields"),
        (lambda r: r.__setitem__("summary", {"candidate_count": -1}), "malformed"),
        (lambda r: r.__setitem__("summary", {**r["summary"], "capital_eligible_count": 1}), "approved for capital"),
        (lambda r: r.__setitem__("strategies", {}), "malformed"),
        (lambda r: r.pop("data_health"), "required fields"),
        (lambda r: r.pop("limitations"), "malformed"),
        (lambda r: r.pop("as_of"), "required fields"),
        (lambda r: r.pop("source"), "required fields"),
        (lambda r: r.pop("generated_at"), "required fields"),
    ],
)
def test_structural_violations_fail_closed(available, mutate, expected):
    report = copy.deepcopy(available)
    mutate(report)
    body = fail_closed(render(report))
    assert expected in body


def test_none_artifact_fails_closed():
    fail_closed(render(None))


def test_non_mapping_artifact_fails_closed():
    for bogus in ([], "string", 7, True):
        fail_closed(render(bogus))


def test_strategy_claiming_capital_eligibility_fails_closed(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["capital_eligible"] = True
    body = fail_closed(render(report))
    assert "claims capital eligibility" in body


def test_mixed_unsupported_schema_fails_closed(available):
    """A v1 envelope carrying a v2-shaped strategy must not half-render."""
    report = copy.deepcopy(available)
    report["strategies"][0]["universe"] = "v2 only"
    report["strategies"][0]["horizon_sessions"] = "twenty-one"
    fail_closed(render(report))


def test_future_timestamp_fails_closed(available):
    report = copy.deepcopy(available)
    report["generated_at"] = (NOW + timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "stamped in the future" in fail_closed(render(report))

    report["generated_at"] = (NOW + timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["as_of"] = (NOW + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "stamped in the future" in fail_closed(render(report))


def test_invalid_timestamp_fails_closed(available):
    report = copy.deepcopy(available)
    report["generated_at"] = "not-a-timestamp"
    assert "cannot read" in fail_closed(render(report))

    report["generated_at"] = 1758600000  # epoch int is not the contract's ISO string
    fail_closed(render(report))


def test_timestamp_within_tolerance_is_accepted(available):
    report = copy.deepcopy(available)
    report["generated_at"] = (NOW + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "This record could not be read" not in render(report)


def test_unreadable_artifact_renders_the_fail_closed_page(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{ this is not json", encoding="utf-8")
    out, contract_ok = renderer.render_file(path, tmp_path / "page.html")
    assert contract_ok is False
    fail_closed(out.read_text(encoding="utf-8"))

    missing, ok = renderer.render_file(tmp_path / "nope.json", tmp_path / "page2.html")
    assert ok is False
    fail_closed(missing.read_text(encoding="utf-8"))


def test_unknown_strategy_id_is_counted_not_shown(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["id"] = "grid_momentum_50"
    body = main_of(render(report))
    assert "not ones this page recognises and were not shown" in body
    assert body.count("<article class=\"ss-card\"") == 1


# --------------------------------------------------------------------------- #
# NaN / Infinity / null vs zero / omitted metrics
# --------------------------------------------------------------------------- #


def test_json_nan_constant_is_rejected_before_projection(available, tmp_path):
    payload = json.dumps(available).replace('"net_sharpe": 0.41', '"net_sharpe": NaN')
    path = tmp_path / "nan.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        renderer.load_artifact(path)
    # And through the file API it renders fail-closed rather than throwing.
    out, contract_ok = renderer.render_file(path, tmp_path / "page.html")
    assert contract_ok is False
    fail_closed(out.read_text(encoding="utf-8"))


def numeric_cells(html: str) -> list[str]:
    """Every rendered value from a right-aligned metrics cell."""
    return re.findall(r'<td class="ss-num">([^<]*)</td>', html)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e999, -1e999])
def test_non_finite_metric_never_reaches_the_page(available, value):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["net_sharpe"] = value
    cells = numeric_cells(render(report))
    assert cells, "no metrics rendered"
    # Checked against the rendered VALUES, not the page text: a substring scan
    # would trip over ordinary words like "prove-nan-ce".
    for cell in cells:
        assert cell == "Not available" or re.fullmatch(r"-?\d+\.\d+", cell), cell
        assert "nan" not in cell.lower() and "inf" not in cell.lower()


def test_non_finite_metric_degrades_to_unavailable_with_a_note(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["net_sharpe"] = float("inf")
    body = main_of(render(report))
    assert "Net Sharpe ratio" in body
    assert "was not a usable number" in body
    assert "Not available" in body


def test_null_metric_is_unavailable_while_a_real_zero_is_shown(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["net_cagr"] = None
    report["strategies"][1]["historical"]["net_cagr"] = 0
    body = main_of(render(report))
    # null -> "Not available", and 0 -> "0.00". These must never be conflated.
    assert "Not available" in body
    assert "0.00" in body
    assert "<td class=\"ss-num\">0.00</td>" in body


def test_omitted_metric_is_unavailable_not_zero(available):
    report = copy.deepcopy(available)
    del report["strategies"][0]["historical"]["turnover"]
    del report["strategies"][1]["historical"]["cost_bps"]
    body = main_of(render(report))
    assert body.count("Not available") >= 2
    assert "<td class=\"ss-num\">0.00</td>" not in body


def test_wrong_typed_metric_degrades_to_unavailable(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["benchmark_sharpe"] = "0.28"
    body = main_of(render(report))
    assert "was not a usable number" in body


def test_unreadable_sample_date_degrades_to_unavailable(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["sample_start"] = "sometime in 2010"
    body = main_of(render(report))
    assert "not a readable date" in body
    assert "Not available" in body
    assert "sometime in 2010" not in body


def test_boolean_is_not_read_as_a_metric(available):
    """``True`` is an int in Python; a metric must not render as 1.00."""
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["net_sharpe"] = True
    body = main_of(render(report))
    assert "was not a usable number" in body


# --------------------------------------------------------------------------- #
# injection, allowlist, path traversal
# --------------------------------------------------------------------------- #


def test_injected_html_in_every_free_text_field_is_escaped(available):
    report = copy.deepcopy(available)
    payload = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    report["strategies"][0]["reason"] = payload
    report["strategies"][0]["name"] = payload
    report["strategies"][0]["family"] = payload
    report["strategies"][0]["instruments"] = [payload]
    report["strategies"][0]["invalidation"] = [payload]
    report["strategies"][0]["blockers"] = [payload]
    report["strategies"][0]["historical"]["limitations"] = [payload]
    report["data_health"]["reasons"] = [payload]
    report["limitations"] = [payload]
    report["source"]["code_revision"] = payload
    body = main_of(render(report))
    # The payload must be INERT: no live tag, no live event handler. It is
    # expected to appear as escaped text — that is the proof it was escaped
    # rather than dropped, and `=` / letters legitimately stay literal.
    assert "<script" not in body
    assert "<img" not in body
    assert "onerror=" not in re.sub(r"&lt;[^&]*&gt;", "", body)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "&lt;img src=x onerror=alert(2)&gt;" in body


def test_symbols_and_quotes_in_text_are_escaped_not_dropped(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["reason"] = 'Costs — 4bps "net" & <gross>'
    body = main_of(render(report))
    assert "4bps" in body and "net" in body and "gross" in body
    assert '"net" & <gross>' not in body


def test_unknown_account_and_fill_fields_never_reach_the_page(available):
    report = copy.deepcopy(available)
    report["account_number"] = "ACC-SECRET-4471"
    report["api_key"] = "sk-live-DO-NOT-LEAK"
    report["fills"] = [{"account_number": "ACC-SECRET-4471", "fill_id": "FILL-9"}]
    report["credentials"] = {"password": "hunter2"}
    report["source"]["vault_path"] = "/etc/shadow"
    strategy = report["strategies"][0]
    strategy["account_number"] = "ACC-SECRET-4471"
    strategy["fills"] = [{"fill_id": "FILL-9", "shares": 100}]
    strategy["historical"]["broker_account"] = "ACC-SECRET-4471"
    body = main_of(render(report))
    for secret in (
        "ACC-SECRET-4471",
        "sk-live-DO-NOT-LEAK",
        "FILL-9",
        "hunter2",
        "/etc/shadow",
    ):
        assert secret not in body


def test_fixture_marker_key_is_ignored(available):
    """The allowlist is tested against a real fixture, not a synthetic one."""
    assert available["_fixture_note"].startswith("SYNTHETIC")
    assert "SYNTHETIC TEST DATA" not in render(available)


def test_revision_values_cannot_become_a_path_or_a_link(available):
    report = copy.deepcopy(available)
    traversal = "../../../../etc/passwd"
    report["source"]["code_revision"] = traversal
    report["source"]["data_revision"] = traversal
    html = render(report)
    # Present as text, never as a locator: no href/src/action points at it.
    assert "etc/passwd" in html
    for attr in ("href", "src", "action", "data-src"):
        for value in re.findall(rf'{attr}="([^"]*)"', html):
            assert "passwd" not in value
            assert ".." not in value


def test_control_characters_cannot_forge_a_line_break(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["reason"] = "line one\n</dd><td>injected cell</td>"
    body = main_of(render(report))
    # The value survives as inert text and no tag in it becomes live.
    assert "line one" in body
    assert "<td>injected cell" not in body
    assert "&lt;/dd&gt;&lt;td&gt;injected cell" in body


# --------------------------------------------------------------------------- #
# builder / CLI
# --------------------------------------------------------------------------- #


def test_render_report_is_pure_and_deterministic(available):
    assert render(available) == render(available)


def test_cli_writes_only_when_output_is_given(tmp_path, available):
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(available), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "scripts.render_systematic_strategies", "--input", str(path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "<main" in proc.stdout
    assert not list(tmp_path.glob("*.html")), "no file written without --output"

    out = tmp_path / "page.html"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.render_systematic_strategies",
            "--input",
            str(path),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    assert "<main" in out.read_text(encoding="utf-8")


def test_copy_assets_is_opt_in(tmp_path, available):
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(available), encoding="utf-8")
    out = tmp_path / "page.html"
    renderer.render_file(path, out)
    assert not (tmp_path / "systematic_strategies.css").exists()

    renderer.render_file(path, out, copy_assets=True)
    shipped = tmp_path / "systematic_strategies.css"
    assert shipped.is_file()
    assert shipped.read_text(encoding="utf-8") == CSS


def test_cli_requires_input():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.render_systematic_strategies"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode != 0
    assert "--input" in proc.stderr


def test_site_write_refuses_to_create_a_site_tree(tmp_path, available):
    """--site must never invent a production tree; it writes into an existing one."""
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(available), encoding="utf-8")
    absent = tmp_path / "site" / "page.html"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.render_systematic_strategies",
            "--input",
            str(path),
            "--output",
            str(absent),
            "--site",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "refusing to create the site directory" in proc.stderr
    assert not absent.parent.exists()


# --------------------------------------------------------------------------- #
# static structure / accessibility / responsive
# --------------------------------------------------------------------------- #


def test_type_scale_matches_the_shared_tokens():
    assert "--fs-h1" in CSS  # 28px page title
    assert "--fs-body" in CSS
    assert "--fs-sm" in CSS  # 12.5px metadata floor
    assert "font-size: 28px" not in CSS, "sizes come from the shared scale, not literals"
    assert "font-size: 14px" not in CSS


def test_no_colored_container_edge_and_no_gradient():
    # The retired house idiom is a colored STRIPE on a container edge: a
    # one-sided border, or an inset box-shadow rail.
    assert "border-left" not in CSS
    assert "box-shadow" not in CSS or "inset" not in CSS
    # Every border colour in the sheet must be neutral or currentColor. A
    # semantic ink (--up/--down/--warn/--act/--ok) may carry STATUS as TEXT, but
    # it may never become a container edge.
    for color in re.findall(r"border(?:-[a-z]+)?:\s*[^;]*?(var\([^)]*\)|currentColor|inherit|none)", CSS):
        assert color in ("currentColor", "inherit", "none") or color.startswith(
            "var(--ss-line"
        ), color
    for banned in ("linear-gradient", "radial-gradient", "conic-gradient"):
        assert banned not in CSS, banned


def test_colours_come_only_from_shared_theme_tokens():
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", CSS)
    assert literals == [], f"literal colour in a scoped sheet: {literals}"
    # Every colour is a token reference; `--ss-*` tokens are themselves derived.
    for token in ("--ss-line", "--ss-warn-ink", "--ss-focus", "--ss-stance-fill"):
        assert f"var({token})" in CSS


def test_both_themes_are_addressed():
    assert 'html[data-theme="light"] .ss-page' in CSS
    assert ":root" not in CSS.split("html[data-theme")[0], "no page-local dark-only palette"


def test_numeric_columns_are_aligned():
    assert ".ss-metrics .ss-num" in CSS
    assert "font-variant-numeric: tabular-nums" in CSS
    assert "text-align: right" in CSS


def test_focus_outline_is_present_and_complete():
    assert ":focus-visible" in CSS
    assert "outline: 2px solid" in CSS
    assert "outline-offset" in CSS


def test_responsive_rules_cover_desktop_and_390():
    assert "@media (max-width: 860px)" in CSS
    assert "@media (max-width: 560px)" in CSS
    narrow = CSS[CSS.index("@media (max-width: 560px)") :]
    # Every track collapses to a shrinkable single column, which is what keeps
    # the page free of horizontal overflow at 390px.
    assert "grid-template-columns: minmax(0, 1fr)" in narrow
    assert "min-width: 0" in CSS


def test_no_auto_fit_grid_uses_a_zero_minimum_track():
    """`repeat(auto-fit, minmax(0, 1fr))` maximises TRACK COUNT, not fill.

    With a 0px minimum the browser fits as many tracks as will fit — measured
    564 tracks on the evidence strip and 44 one-pixel tracks on the card facts,
    which collapsed "Stance" and "Horizon" to one character per line. Every
    repeating auto-fit must carry a minimum a label is readable at.
    """
    offenders = [
        line.strip()
        for line in re.sub(r"/\*.*?\*/", "", CSS, flags=re.S).splitlines()
        if "auto-fit" in line or "auto-fill" in line
    ]
    assert offenders, "expected repeating auto-fit grids"
    for rule in offenders:
        minimum = re.search(r"minmax\(\s*([0-9.]+)(px|rem|em|%)", rule)
        assert minimum, rule
        assert float(minimum.group(1)) > 0, rule


def test_single_column_overrides_still_use_a_shrinkable_track():
    """The mobile collapse is a PLAIN track, where minmax(0, 1fr) is correct:
    a non-repeating track sizes to the container and may shrink to nothing."""
    narrow = CSS[CSS.index("@media (max-width: 560px)") :]
    for line in narrow.splitlines():
        if "grid-template-columns" in line:
            assert "repeat(" not in line, line


def test_reduced_motion_is_respected():
    assert "@media (prefers-reduced-motion: reduce)" in CSS


def test_landmarks_and_labels_are_present():
    html = render(load("research_available.json"))
    assert '<main class="ss-workspace"' in html
    assert "<h1" in html and "<h2" in html and "<h3" in html
    assert 'aria-labelledby=' in html
    assert "<caption" in html
    assert 'scope="col"' in html and 'scope="row"' in html


def test_visually_hidden_helper_is_scoped_not_global():
    assert ".ss-visually-hidden" in CSS
    assert "display: none" not in CSS.split(".ss-visually-hidden")[1][:400]


def test_template_never_creates_another_header():
    """The header markup comes from _site_nav.html.j2 and nowhere else.

    Linking the shared header's own stylesheet is required (it owns the header's
    appearance); authoring any header markup is not.
    """
    assert "site-nav" not in TEMPLATE.replace('{% include "_site_nav.html.j2" %}', "")
    assert "<nav" not in TEMPLATE
    assert "nav-ctrls" not in TEMPLATE
    assert "navlinks" not in TEMPLATE.replace('{% include "_site_nav.html.j2" %}', "")


def test_template_has_no_script_and_no_inert_control():
    # The shared <head> carries the site's theme/lang bootstrap (every page in
    # the repo does); the page BODY adds no script of its own.
    body_src = TEMPLATE.split("<body", 1)[1]
    assert "<script" not in body_src
    for banned in ("<button", "<form", "onclick", "javascript:", "addEventListener"):
        assert banned not in body_src, banned


def test_no_strategy_performance_numbers_are_hardcoded_in_source():
    """Numbers in the page are labels and counts, never a performance figure."""
    for pattern in (r"Sharpe[^<]*\d", r"\b\d+\.\d{2}\b", r"drawdown[^<]*\d", r"\bCAGR\b"):
        assert not re.search(pattern, TEMPLATE), pattern