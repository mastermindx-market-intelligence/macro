"""WHY THIS SUITE EXISTS. Freeze §13 C7 named templates/_us_act_now_board.html.j2
as an untraced second board-like surface contradicting engine/alert_triage.py's
sole-assembler claim. C7 was a name collision, not a producer collision: two
surfaces are both called "board" and share no input, no artifact, and no read.
This file is the standing proof they are not the same producer — the mechanical
guard on research/MARKET_ONTOLOGY_F08_C7_SOLE_ASSEMBLER_AMENDMENT_2026-09-09.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("jinja2")
import jinja2  # noqa: E402

TRIAGE_SRC = ROOT / "engine" / "alert_triage.py"
BUILD_SITE_SRC = ROOT / "scripts" / "build_site.py"
BOARD_TPL = ROOT / "templates" / "_us_act_now_board.html.j2"
ALERTS_TPL = ROOT / "templates" / "alerts.html.j2"
DASHBOARD_TPL = ROOT / "templates" / "dashboard.html.j2"
SECTOR_CENTRAL_TPL = ROOT / "templates" / "sector_central.html.j2"

# Tokens the alert-triage assembler must never carry (R10 case 1).
ACTNOW_TOKENS = (
    "action_board",
    "act_now",
    "us_act_now",
    "basketdata",
    "sector_timing",
)

# Tokens the action_board() slice must never carry (R10 case 2).
TRIAGE_TOKENS = (
    "alert_triage",
    "engine.alerts",
    "alerts_log",
    "alerts_triage",
    "feed.json",
)

# Artifact names the act-now board HTML must never emit (R10 case 3).
TRIAGE_ARTIFACTS = (
    "alerts_triage.json",
    "alertsdata/feed.json",
    "alerts.html",
)

BOARD_INCLUDE = "_us_act_now_board.html.j2"
ALERTS_INCLUDE = "alerts.html.j2"

_INCLUDE_RE = re.compile(
    r"""\{%-?\s*include\s+['\"]([^'\"]+)['\"]""",
)


def _assert_absent(source: str, tokens: tuple[str, ...], label: str) -> None:
    """Fail if any token appears. Empty source is not a pass — the caller must
    prove the file was actually read (R10: a guard that greens on an empty file
    is not a guard)."""
    assert source, f"{label} is empty — the guard cannot pin an absent file"
    hits = [tok for tok in tokens if tok in source]
    assert not hits, f"{label} carries forbidden token(s) {hits!r}"


def _action_board_slice(src: str) -> str:
    """Text slice from `def action_board(` to the next top-level `def `.

    A text slice, not an import: importing scripts.build_site is neither
    hermetic nor cheap (R10 case 2).
    """
    lines = src.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("def action_board(")),
        None,
    )
    assert start is not None, "scripts/build_site.py has no top-level action_board()"
    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].startswith("def ")),
        len(lines),
    )
    return "".join(lines[start:end])


def _included_templates(src: str) -> set[str]:
    return set(_INCLUDE_RE.findall(src))


def _minimal_board() -> dict:
    # Same shape tests/test_us_act_now.py:842 uses: lanes present, rows empty.
    return {
        "buy_now": [],
        "buy_soon": [],
        "on_the_run": [],
        "take_profits": [],
        "hold": [],
        "avoid": [],
        "more": {},
    }


def _render_board(board: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
    )
    env.globals.update(tr=lambda en: en, td=lambda en: en)
    return env.get_template(BOARD_INCLUDE).render(action_board=board)


# --- RED-first: each guard must fire on a deliberately violating fixture ------

def test_guard_fires_when_alert_triage_source_names_the_act_now_board():
    """R10 case 1 self-check. A source that names the other board must fail."""
    for token in ACTNOW_TOKENS:
        with pytest.raises(AssertionError, match=re.escape(token)):
            _assert_absent(f"assembled by {token}", ACTNOW_TOKENS, "fixture")


def test_guard_fires_when_action_board_slice_names_a_triage_engine():
    """R10 case 2 self-check. A slice that reads a triage token must fail."""
    for token in TRIAGE_TOKENS:
        with pytest.raises(AssertionError, match=re.escape(token)):
            _assert_absent(f"calls {token}", TRIAGE_TOKENS, "fixture")


def test_guard_fires_when_board_html_names_a_triage_artifact():
    """R10 case 3 self-check. HTML that names a triage artifact must fail."""
    for token in TRIAGE_ARTIFACTS:
        with pytest.raises(AssertionError, match=re.escape(token)):
            _assert_absent(f"<div>{token}</div>", TRIAGE_ARTIFACTS, "html")


_HOST_FIXTURE_DUMMY = "{# host fixture #}"
_BOARD_INCLUDE_TAG = '{% include "_us_act_now_board.html.j2" %}'


def _assert_hosts_disjoint(alerts_src, board_src, dashboard_src, sector_src):
    """Standing R10 case 4 assertions. Shared by the real-repo test and the
    cross-read self-check so inverting one assertion cannot leave the
    self-check green."""
    assert alerts_src and board_src and dashboard_src and sector_src

    alerts_includes = _included_templates(alerts_src)
    assert BOARD_INCLUDE not in alerts_includes, (
        "templates/alerts.html.j2 includes _us_act_now_board.html.j2 — "
        "the two boards' hosts are no longer disjoint"
    )

    dashboard_includes = _included_templates(dashboard_src)
    sector_includes = _included_templates(sector_src)
    board_includes = _included_templates(board_src)

    assert BOARD_INCLUDE in dashboard_includes, (
        "templates/dashboard.html.j2 no longer includes _us_act_now_board.html.j2"
    )
    assert BOARD_INCLUDE in sector_includes, (
        "templates/sector_central.html.j2 no longer includes _us_act_now_board.html.j2"
    )

    for label, included in (
        ("_us_act_now_board.html.j2", board_includes),
        ("dashboard.html.j2", dashboard_includes),
        ("sector_central.html.j2", sector_includes),
    ):
        assert ALERTS_INCLUDE not in included, (
            f"templates/{label} includes alerts.html.j2 — the two boards' hosts "
            "are no longer disjoint"
        )


@pytest.mark.parametrize(
    "host, read, match",
    [
        (
            "alerts",
            '{% include "_us_act_now_board.html.j2" %}',
            r"templates/alerts\.html\.j2",
        ),
        ("board", '{% include "alerts.html.j2" %}', r"templates/_us_act_now_board\.html\.j2"),
        ("board", '{% import "alerts.html.j2" as at %}', r"templates/_us_act_now_board\.html\.j2"),
        ("board", '{% from "alerts.html.j2" import x %}', r"templates/_us_act_now_board\.html\.j2"),
        ("board", '{% extends "alerts.html.j2" %}', r"templates/_us_act_now_board\.html\.j2"),
        ("dashboard", '{% include "alerts.html.j2" %}', r"templates/dashboard\.html\.j2"),
        ("dashboard", '{% import "alerts.html.j2" as at %}', r"templates/dashboard\.html\.j2"),
        ("dashboard", '{% from "alerts.html.j2" import x %}', r"templates/dashboard\.html\.j2"),
        ("dashboard", '{% extends "alerts.html.j2" %}', r"templates/dashboard\.html\.j2"),
        ("sector", '{% include "alerts.html.j2" %}', r"templates/sector_central\.html\.j2"),
        ("sector", '{% import "alerts.html.j2" as at %}', r"templates/sector_central\.html\.j2"),
        ("sector", '{% from "alerts.html.j2" import x %}', r"templates/sector_central\.html\.j2"),
        ("sector", '{% extends "alerts.html.j2" %}', r"templates/sector_central\.html\.j2"),
    ],
    ids=[
        "alerts-include-board",
        "board-include-alerts",
        "board-import-alerts",
        "board-from-alerts",
        "board-extends-alerts",
        "dashboard-include-alerts",
        "dashboard-import-alerts",
        "dashboard-from-alerts",
        "dashboard-extends-alerts",
        "sector-include-alerts",
        "sector-import-alerts",
        "sector-from-alerts",
        "sector-extends-alerts",
    ],
)
def test_guard_fires_when_hosts_cross_read(host, read, match):
    """R10 case 4 self-check. A host that reads the other board must fail."""
    dummy = _HOST_FIXTURE_DUMMY
    board_inc = _BOARD_INCLUDE_TAG
    if host == "alerts":
        args = (read, dummy, board_inc, board_inc)
    elif host == "board":
        args = (dummy, read, board_inc, board_inc)
    elif host == "dashboard":
        args = (dummy, dummy, board_inc + read, board_inc)
    else:
        args = (dummy, dummy, board_inc, board_inc + read)
    with pytest.raises(AssertionError, match=match):
        _assert_hosts_disjoint(*args)


# --- Standing proof against the two real producers ----------------------------

def test_alert_triage_knows_nothing_of_the_act_now_board():
    """R10 case 1. engine/alert_triage.py carries none of the act-now tokens."""
    src = TRIAGE_SRC.read_text(encoding="utf-8")
    _assert_absent(src, ACTNOW_TOKENS, "engine/alert_triage.py")


def test_action_board_knows_nothing_of_the_alert_engines():
    """R10 case 2. The action_board() slice carries none of the triage tokens."""
    src = BUILD_SITE_SRC.read_text(encoding="utf-8")
    slice_src = _action_board_slice(src)
    assert slice_src.startswith("def action_board("), (
        "slice did not start at action_board() — the extractor drifted"
    )
    _assert_absent(slice_src, TRIAGE_TOKENS, "scripts/build_site.py::action_board")


def test_board_template_is_self_sufficient_and_writes_none_of_the_triage_artifacts():
    """R10 case 3. Render with action_board only; output names no triage artifact."""
    html = _render_board(_minimal_board())
    assert html.strip(), "board template rendered empty — the include is not self-sufficient"
    _assert_absent(html, TRIAGE_ARTIFACTS, "rendered _us_act_now_board.html.j2")


def test_the_two_boards_hosts_are_disjoint():
    """R10 case 4. alerts.html.j2 does not include the act-now board; neither
    the board template nor its two hosts include alerts.html.j2."""
    _assert_hosts_disjoint(
        ALERTS_TPL.read_text(encoding="utf-8"),
        BOARD_TPL.read_text(encoding="utf-8"),
        DASHBOARD_TPL.read_text(encoding="utf-8"),
        SECTOR_CENTRAL_TPL.read_text(encoding="utf-8"),
    )
