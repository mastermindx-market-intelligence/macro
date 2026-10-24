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


# t() emits exactly this pair for every string the page authors, so an assertion
# about English copy can be made against the page as an English reader sees it —
# the Chinese span removed and the English one unwrapped — instead of matching
# around the spans. Chinese parity is asserted separately and directly.
_BILINGUAL = re.compile(
    r'<span class="l-en">(.*?)</span><span class="l-zh">(.*?)</span>', re.S
)


def en_of(html: str) -> str:
    return _BILINGUAL.sub(r"\1", html)


def body_of(html: str) -> str:
    """The workspace body as an English reader sees it."""
    return en_of(main_of(html))


# --------------------------------------------------------------------------- #
# available — the honest happy path
# --------------------------------------------------------------------------- #


def test_available_renders_title_deck_and_stance(available):
    body = body_of(render(available))
    assert "<h1 class=\"ss-title\">Systematic Strategies</h1>" in body
    assert "Test small edges. Keep only evidence." in body
    assert "Observe only" in body


def test_available_shows_no_strategy_is_approved_for_capital(available):
    body = body_of(render(available))
    assert "No strategy is approved for capital." in body
    # The capital count is rendered as a real 0, never hidden or spun.
    assert "<dt>Approved for capital</dt>" in body
    assert re.search(r"Approved for capital</dt>\s*<dd>0</dd>", body)


def test_candidate_labels_are_plain_words_and_real_names_live_in_methodology(available):
    body = body_of(render(available))
    assert ">Trend baseline</h3>" in body
    assert ">Pullback timing</h3>" in body
    # The artifact's own input name is shown under methodology, not as the label.
    assert "<dt>Input name</dt><dd>200-session time-series momentum</dd>" in body
    assert "<dt>Input name</dt><dd>Two-session RSI oversold re-entry</dd>" in body


def test_available_card_shows_state_horizon_prereq_and_evidence_control(available):
    body = body_of(render(available))
    assert body.count('<span class="ss-chip ss-chip--research_only">Research only</span>') == 2
    assert "<dt>Stance</dt>" in body
    assert "<dt>Horizon</dt>" in body
    assert "21 sessions" in body
    assert body.count("<dt>Next unmet prerequisite</dt>") == 2
    assert body.count('class="ss-evidence-toggle"') == 2
    assert body.count("View evidence") == 2


def test_evidence_splits_historical_prospective_and_paper(available):
    body = body_of(render(available))
    for heading in ("Historical record", "Forward testing", "Paper trading", "Method and provenance"):
        assert body.count(f">{heading}</h4>") == 2, heading
    assert "<dt>Forward records registered</dt>" in body
    assert "<dt>Forward records graded</dt>" in body
    assert "Not connected" in body


def test_evidence_carries_costs_limitations_versions_and_invalidators(available):
    body = body_of(render(available))
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
    body = body_of(render(available))
    row_headers = re.findall(r'<th scope="row"[^>]*>(.*?)</th>', body, re.S)
    for _key, label, _places, _scale in renderer.METRIC_LABELS:
        # Matched inside the row header: the turnover row also carries a
        # convention tooltip, so the element is not a fixed string.
        assert any(label in header for header in row_headers), label
    assert "(%)" in body
    assert "basis points" in body
    # M1: turnover is a sample total, never an annual rate.
    assert "in sample" in body
    assert "times per year" not in body
    # Costs are explicitly ONE-WAY, because a round trip cost and a one-way
    # cost differ by a factor of two and a reader cannot see which is shown.
    assert "one way" in body


def test_percent_metrics_are_scaled_from_decimal_fractions(available):
    """B2: rates are decimal fractions; printing them raw under "%" is a lie.

    ``0.0991`` is 9.91% and ``-0.241`` is -24.10%. Rendering the fraction
    unchanged printed "0.10%" for a result that was nearly ten percent.
    """
    body = body_of(render(available))
    assert "3.20" in body and "-11.40" in body and "1.40" in body and "-8.90" in body


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0.0991, "9.91"),   # a fraction shown as a percent
        (-0.241, "-24.10"),  # negative return / drawdown
        (0.0, "0.00"),       # a measured zero is retained, not hidden
        (1.0, "100.00"),      # exactly 100%
        (-0.0005, "-0.05"),   # small negative, two places
    ],
)
def test_percent_scaling_is_exact_for_edge_values(available, raw, expected):
    report = copy.deepcopy(available)
    for strategy in report["strategies"]:
        strategy["historical"]["net_cagr"] = raw
    body = body_of(render(report))
    assert expected in body


def test_turnover_is_labelled_a_sample_total_with_its_convention(available):
    """M1: the figure cannot carry its own convention, so the label states it."""
    body = body_of(render(available))
    assert "Traded notional in sample (times)" in body
    # A tooltip on the row itself...
    assert f'title="{renderer.TURNOVER_CONVENTION}"' in body
    # ...and a visible statement, because a convention reachable only on hover
    # is a convention a keyboard and a screen-reader user never meets.
    assert renderer.TURNOVER_CONVENTION in body


def test_cost_label_states_the_one_way_basis(available):
    body = body_of(render(available))
    assert "Assumed cost per trade, one way (basis points)" in body


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


def test_both_timestamps_are_shown_once_each_with_the_mode_stamp(available):
    """M8: the information cutoff and the generation stamp answer different
    questions. A page carrying only the generation stamp lets a record compiled
    yesterday from month-old data read as "up to date"."""
    body = body_of(render(available))
    # One mode stamp; the per-candidate chips carry each candidate's own state
    # and are not a repeated page stamp.
    assert body.count('<span class="ss-meta-mode">Research only</span>') == 1
    assert body.count("2026-10-22 18:26 UTC") == 1   # generated
    assert body.count("2026-10-21 20:00 UTC") == 1   # information cutoff
    assert body.count("<time ") == 2
    assert "Information cutoff" in body
    assert "Generated" in body


def test_blocked_page_states_no_timestamp_at_all():
    """M5: an unreadable record has no known age.

    Stamping the renderer's own clock into a <time datetime=...> would present
    "now" as the age of a research record that does not exist.
    """
    body = body_of(render(None))
    assert "<time " not in body
    assert body.count("Not available") >= 2


def test_render_with_an_injected_clock_is_byte_identical(available):
    """M5: same inputs + same clock => same HTML, including the blocked page."""
    assert renderer.render_report(available, now=NOW) == renderer.render_report(
        available, now=NOW
    )
    # The blocked page too: it used to embed an ambient clock, which made it the
    # one page whose bytes changed on every render.
    assert renderer.render_report(None, now=NOW) == renderer.render_report(None, now=NOW)


def test_cli_now_pins_the_reference_clock(tmp_path, available):
    """--now makes a render reproducible instead of wall-clock dependent."""
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(available), encoding="utf-8")
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
            "--now",
            "2026-10-22T18:00:00Z",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    first = out.read_text(encoding="utf-8")
    # The fixture is stamped 18:26Z, so a clock of 18:00Z puts it in the future:
    # this proves the INJECTED clock is the one every decision is made against,
    # not the wall clock the runner happens to have.
    assert "This record could not be read" in first

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.render_systematic_strategies",
            "--input",
            str(path),
            "--output",
            str(out),
            "--now",
            "2026-10-24T19:00:00Z",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "This record could not be read" not in out.read_text(encoding="utf-8")


def test_cli_rejects_an_unreadable_now(tmp_path, available):
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(available), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.render_systematic_strategies",
            "--input",
            str(path),
            "--now",
            "not-a-timestamp",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "not an ISO 8601 timestamp" in proc.stderr


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
    # Neither candidate is measurable, so the record's own evaluated count has
    # to agree (M7) or it blocks instead of showing an honest empty history.
    report["summary"]["evaluated_count"] = 0
    body = body_of(render(report))
    assert "Historical record unavailable" in body
    assert body.count("Not available") >= 12
    assert "0.41" not in body and "3.20" not in body
    assert "has no historical record" in body


def test_inputs_blocked_lists_what_is_missing_rather_than_an_empty_plot():
    body = body_of(render(load("inputs_blocked.json")))
    assert "Inputs blocked" in body or "Blocked" in body
    assert "Why the inputs are blocked" in body
    assert "Incomplete daily history" in body
    assert "<canvas" not in body and "<svg" not in body
    # Blocked candidates still name their own blocker.
    assert "<dt>Next unmet prerequisite</dt>" in body


def test_data_stale_variant_keeps_reasons_visible_beside_cards():
    body = body_of(render(load("data_stale.json")))
    assert "Why the inputs are blocked" in body
    assert "one revision behind the current one" in body
    # A stale page still shows its candidate — and still says it is stale.
    assert ">Trend baseline</h3>" in body
    assert "2026-10-08" in body


def test_empty_candidate_list_produces_a_useful_empty_state(available):
    report = copy.deepcopy(available)
    report["strategies"] = []
    # The counts describe the rows; a record claiming two candidates beside an
    # empty list is inconsistent and blocks (M7). The useful empty state is
    # reached by a record that actually reports none.
    report["summary"]["candidate_count"] = 0
    report["summary"]["evaluated_count"] = 0
    body = body_of(render(report))
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
    assert "after the reference clock" in fail_closed(render(report))

    report["generated_at"] = (NOW + timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["as_of"] = (NOW + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "after the reference clock" in fail_closed(render(report))


def test_no_future_tolerance_window(available):
    """M5: a 15-hour-ahead stamp is future information, not clock skew.

    The retired 24h tolerance accepted exactly this record — the one whose
    as-of cannot be verified — so the tolerance is gone, not narrowed.
    """
    report = copy.deepcopy(available)
    report["generated_at"] = (NOW + timedelta(hours=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["as_of"] = (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "after the reference clock" in fail_closed(render(report))

    # One second ahead is still ahead.
    report["generated_at"] = (NOW + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "after the reference clock" in fail_closed(render(report))

    # Exactly at the clock is not ahead.
    report["generated_at"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "This record could not be read" not in render(report)


def test_generated_at_must_not_precede_its_own_cutoff(available):
    """M2: a record generated before the information it reports is not a record."""
    report = copy.deepcopy(available)
    report["as_of"] = (NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["generated_at"] = (NOW - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "cannot both be true" in fail_closed(render(report))


def test_timestamp_ordering_survives_mixed_timezone_offsets(available):
    """M2: both values are normalised to UTC before they are compared."""
    # The same instant the other side of the Atlantic: 2026-10-21T20:00Z.
    report = copy.deepcopy(available)
    report["as_of"] = "2026-10-21T16:00:00-04:00"
    assert "This record could not be read" not in render(report)

    # Written as +08:00, 2026-10-22T04:00+08:00 == 2026-10-21T20:00Z: still the
    # real cutoff, so ordering still holds and nothing blocks.
    report["as_of"] = "2026-10-22T04:00:00+08:00"
    assert "This record could not be read" not in render(report)

    # An offset that genuinely moves as_of ahead of generated_at must block,
    # even though the two strings compare fine as text.
    report["as_of"] = "2026-10-22T14:00:00+08:00"   # == 2026-10-22T06:00Z
    report["generated_at"] = "2026-10-22T02:00:00Z"
    assert "cannot both be true" in fail_closed(render(report))


def test_invalid_timestamp_fails_closed(available):
    report = copy.deepcopy(available)
    report["generated_at"] = "not-a-timestamp"
    assert "cannot read" in fail_closed(render(report))

    report["generated_at"] = 1758600000  # epoch int is not the contract's ISO string
    fail_closed(render(report))


def test_timestamp_within_tolerance_is_accepted(available):
    """A stamp an hour in the PAST is ordinary and must still render."""
    report = copy.deepcopy(available)
    report["generated_at"] = (NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["as_of"] = (NOW - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "This record could not be read" not in render(report)


def test_unknown_strategy_id_fails_closed_with_a_useful_reason(available):
    """B1: an id this page cannot label is a structural fault, not a row to hide.

    Dropping it silently would make the summary counts describe a record that no
    longer exists — and, with a duplicate, would have let two cards share one DOM
    id while the second real candidate was truncated away.
    """
    report = copy.deepcopy(available)
    report["strategies"][0]["id"] = "grid_momentum_50"
    body = fail_closed(render(report))
    assert "does not recognise" in body
    assert "ss-card" not in body


def test_duplicate_candidate_id_fails_closed(available):
    """B1: the defect that hid RSI behind a duplicated tsmom card."""
    report = copy.deepcopy(available)
    report["strategies"][1] = copy.deepcopy(report["strategies"][0])
    body = fail_closed(render(report))
    assert "more than once" in body
    assert "ss-card" not in body


def test_duplicate_dom_id_cannot_reach_the_page(available):
    report = copy.deepcopy(available)
    report["strategies"].append(copy.deepcopy(report["strategies"][0]))
    body = main_of(render(report))
    # Either it fails closed, or it never mints two elements with one id.
    if "ss-card-tsmom_200" in body:
        assert body.count('id="ss-card-tsmom_200"') == 1
    else:
        assert "This record could not be read" in en_of(body)


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
    assert "does not recognise" in en_of(body)


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
    """M4: measured performance is not shown over a window that cannot be read."""
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["sample_start"] = "sometime in 2010"
    # Only one candidate is left measurable, so the record must say so (M7);
    # with the stale count it blocks outright — see the test below.
    report["summary"]["evaluated_count"] = 1
    body = body_of(render(report))
    assert "not a readable date" in body
    assert "Not available" in body
    assert "sometime in 2010" not in body
    # The card still renders — the candidate is real, its measurement is not.
    assert ">Trend baseline</h3>" in body


def test_broken_sample_date_with_a_stale_count_blocks(available):
    """A record whose rows no longer match its own counts is not shown at all."""
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"]["sample_start"] = "sometime in 2010"
    assert "do not match the candidates" in fail_closed(render(report))


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda h: h.__setitem__("sample_start", "2026-11-01"),
            id="inverted",
        ),
        pytest.param(lambda h: h.__setitem__("observations", 0), id="zero-observations"),
        pytest.param(lambda h: h.__setitem__("sample_end", "2030-01-01"), id="future"),
    ],
)
def test_measured_performance_is_withheld_when_the_window_is_unusable(available, mutate):
    """M3/M4: no measured performance over a window that cannot be trusted."""
    report = copy.deepcopy(available)
    mutate(report["strategies"][0]["historical"])
    report["summary"]["evaluated_count"] = 1  # one candidate is no longer measurable
    body = body_of(render(report))
    assert "Not available" in body
    # The real Sharpe of the OTHER candidate is untouched and still shown.
    assert "0.22" in body


def test_a_missing_observation_count_is_not_read_as_zero(available):
    report = copy.deepcopy(available)
    report["strategies"][0]["historical"].pop("observations")
    assert "missing or malformed" in fail_closed(render(report))


def test_missing_prospective_counts_are_not_read_as_zero(available):
    """M6: a defaulted count is a guessed zero beside a real measurement."""
    report = copy.deepcopy(available)
    report["strategies"][0]["prospective"].pop("registered")
    assert "missing or malformed" in fail_closed(render(report))
    report = copy.deepcopy(available)
    report["strategies"][0]["prospective"].pop("graded")
    assert "missing or malformed" in fail_closed(render(report))


@pytest.mark.parametrize("field", ["registered", "graded"])
def test_not_started_cannot_also_report_records(available, field):
    """M6: 'not started' and 'seven records registered' cannot both be true."""
    report = copy.deepcopy(available)
    report["strategies"][0]["prospective"][field] = 7
    assert "missing or malformed" in fail_closed(render(report))


def test_summary_counts_must_match_the_rows_actually_present(available):
    """M7: counts that describe another record do not get to borrow this one's cards."""
    report = copy.deepcopy(available)
    report["summary"]["candidate_count"] = 17
    report["summary"]["evaluated_count"] = 99
    body = fail_closed(render(report))
    assert "do not match the candidates" in body
    assert "ss-card" not in body


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

# --------------------------------------------------------------------------- #
# review repairs — duplicate JSON keys, freshness against the real calendar,
# session-date labels, and Chinese parity
# --------------------------------------------------------------------------- #


def test_duplicate_json_key_is_rejected_before_projection(available, tmp_path):
    """json.loads keeps the LAST duplicate, so a repeated claim reads as agreed.

    An artifact carrying ``"capital_eligible_count": 0`` twice with a different
    value in between would otherwise parse as the clean zero.
    """
    payload = (
        '{"schema":"systematic_research.v1","mode":"RESEARCH_ONLY",'
        '"live_orders_enabled":false,"status":"research_available",'
        '"generated_at":"2026-10-22T18:26:00Z","as_of":"2026-10-21T20:00:00Z",'
        '"capital_eligible_count":4,"capital_eligible_count":0}'
    )
    path = tmp_path / "dup.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        renderer.load_artifact(path)
    # Through the file API it renders fail-closed rather than believing a number.
    out, contract_ok = renderer.render_file(path, tmp_path / "page.html")
    assert contract_ok is False
    fail_closed(out.read_text(encoding="utf-8"))


def test_duplicate_key_inside_a_strategy_is_also_rejected(available, tmp_path):
    payload = json.dumps(available)
    # Re-open the first strategy's metrics with a second, different value.
    payload = payload.replace(
        '"net_sharpe": 0.41,', '"net_sharpe": 0.41, "net_sharpe": 9.99,', 1
    )
    path = tmp_path / "dup2.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        renderer.load_artifact(path)


def test_stale_record_stays_readable_but_is_never_called_current():
    """M8: a historical result may remain visible — labelled historic, not current."""
    body = body_of(render(load("data_stale.json")))
    assert "This record is out of date" in body
    assert "historical reconstruction, not current data" in body
    # The measured candidate is still shown, still with its real numbers...
    assert ">Trend baseline</h3>" in body
    assert "3.00" in body
    # ...but the Inputs stat does not read "Ready", and nothing claims a signal.
    assert '<dd class="ss-stat-text">Stale</dd>' in body
    assert "no current signal is claimed" in body


def test_fresh_record_is_not_labelled_stale(available):
    body = body_of(render(available))
    assert "This record is out of date" not in body
    assert '<dd class="ss-stat-text">Ready</dd>' in body


def test_a_weekend_alone_does_not_make_a_record_stale(available):
    """M8: no universal weekend-days rule.

    On Saturday 2026-10-24 the newest DUE session is Friday the 23rd, so a
    record through Friday is current. A rule that simply skipped two weekend
    days would call this record stale, and one that assumed Monday would call a
    Friday record fresh when it is two sessions behind.
    """
    report = copy.deepcopy(available)
    report["as_of"] = "2026-10-23T20:00:00Z"
    report["generated_at"] = "2026-10-24T12:00:00Z"
    saturday = datetime(2026, 10, 24, 15, 0, tzinfo=timezone.utc)
    body = body_of(renderer.render_report(report, now=saturday))
    assert "This record is out of date" not in body


def test_an_exchange_holiday_is_not_treated_as_a_session(available):
    """M8: Thanksgiving 2026-11-26 closed; the newest due session is the 27th.

    A weekday-only rule would name Monday the 30th as expected and declare a
    record through Friday the 27th stale.
    """
    report = copy.deepcopy(available)
    report["as_of"] = "2026-11-27T20:00:00Z"
    report["generated_at"] = "2026-11-28T12:00:00Z"
    thanksgiving_monday = datetime(2026, 11, 30, 15, 0, tzinfo=timezone.utc)
    body = body_of(renderer.render_report(report, now=thanksgiving_monday))
    assert "This record is out of date" not in body


def test_session_date_labels_are_not_shifted_by_a_utc_conversion(available):
    """M3: a session label is the exchange's date, not a receipt instant.

    ``2010-01-04`` is that session. Read as UTC and projected into New York it
    becomes 2010-01-03 — the previous session, on the wrong side of midnight.
    """
    body = body_of(render(available))
    assert "<dd>2010-01-04</dd>" in body
    assert "<dd>2016-01-04</dd>" in body
    assert "2010-01-03" not in body


def test_offset_session_labels_are_read_in_exchange_time(available):
    """A session label carrying an offset is an instant; take the ET date."""
    report = copy.deepcopy(available)
    # 2026-10-22T02:00+09:00 == 2026-10-21T13:00 ET -> session 2026-10-21.
    report["strategies"][0]["historical"]["sample_end"] = "2026-10-22T02:00:00+09:00"
    body = body_of(render(report))
    assert "<dd>2026-10-21</dd>" in body


def test_every_chinese_label_has_an_english_pair():
    """Parity is structural: no English string without a Chinese counterpart."""
    assert set(renderer.BLOCK_REASONS) == set(renderer.BLOCK_REASONS_ZH)
    assert set(renderer.CANDIDATE_LABELS) == set(renderer.CANDIDATE_LABELS_ZH)
    assert set(renderer.STATE_LABELS) == set(renderer.STATE_LABELS_ZH)
    assert set(renderer.HISTORICAL_LABELS) == set(renderer.HISTORICAL_LABELS_ZH)
    assert set(renderer.PROSPECTIVE_LABELS) == set(renderer.PROSPECTIVE_LABELS_ZH)
    assert set(renderer.PAPER_LABELS) == set(renderer.PAPER_LABELS_ZH)
    assert set(renderer.DATA_HEALTH_LABELS) == set(renderer.DATA_HEALTH_LABELS_ZH)
    assert {key for key, _l, _p, _s in renderer.METRIC_LABELS} == set(
        renderer.METRIC_LABELS_ZH
    )
    for table in (
        renderer.BLOCK_REASONS_ZH,
        renderer.CANDIDATE_LABELS_ZH,
        renderer.STATE_LABELS_ZH,
        renderer.HISTORICAL_LABELS_ZH,
        renderer.PROSPECTIVE_LABELS_ZH,
        renderer.PAPER_LABELS_ZH,
        renderer.DATA_HEALTH_LABELS_ZH,
        renderer.METRIC_LABELS_ZH,
    ):
        for key, value in table.items():
            assert value.strip(), key


def test_no_rendered_chinese_span_is_empty(available):
    """The language toggle is on screen, so no span may render blank in Chinese."""
    html = render(available)
    zh_spans = re.findall(r'<span class="l-zh">(.*?)</span>', html, re.S)
    assert len(zh_spans) > 40, len(zh_spans)
    for span in zh_spans:
        assert span.strip(), span


def test_every_t_call_in_the_template_supplies_chinese():
    """A t() call with no Chinese string would fall back to English in zh."""
    calls = re.findall(r"\{\{\s*t\((.*?)\)\s*\}\}", TEMPLATE, re.S)
    assert len(calls) > 30, len(calls)
    for call in calls:
        assert call.count(",") >= 1, call


def test_chinese_visibility_rules_are_present():
    """Without these the shared language toggle is dead markup on this page."""
    assert 'html:not([data-lang="zh"]) .l-zh' in CSS
    assert 'html[data-lang="zh"] .l-en' in CSS


def test_synthetic_fixtures_are_marked_as_synthetic():
    """No fixture may read as a measured result."""
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "SYNTHETIC" in payload.get("_fixture_note", ""), path.name


def test_artifact_note_key_never_reaches_the_page(available):
    assert "_fixture_note" not in render(available)
    assert "SYNTHETIC" not in render(available)


def test_no_t_call_is_used_inside_an_html_attribute():
    """An attribute is plain text; the dual-span mechanism cannot run there.

    Putting t() in an aria-label emits the literal markup as the accessible
    name, and the nested quotes break the attribute outright.
    """
    for match in re.finditer(r'([a-zA-Z-]+)="([^"]*)"', TEMPLATE):
        if re.search(r"\{\{\s*t\(", match.group(2)):
            raise AssertionError(f"{match.group(1)} carries t(): {match.group(2)!r}")


def test_rendered_attributes_contain_no_markup(available):
    html = render(available)
    for match in re.finditer(r'<[^>]+>', html):
        tag = match.group(0)
        for attr in re.findall(r'="([^"]*)"', tag):
            assert "<span" not in attr, tag
