"""Hermetic P0B zero-FOUC contracts for the HK and Canada dashboards.

This suite reads only source-controlled template, composer, stylesheet, and
loader bytes.  It belongs in the PR ``gate: code`` lane.  Assertions over
generated pages and their current data populations live separately in
``test_stock_dashboard_first_frame_data.py`` so they remain in ``gate: data``.
"""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment

import scripts.check_p0b_receipt_closure as receipt_closure


ROOT = Path(__file__).resolve().parents[1]
BROWSER_RECEIPT = ROOT / "scripts" / "verify_stock_dashboard_mobile_layout.cjs"
FIXTURE_RECIPE = ROOT / "scripts" / "render_stock_dashboard_fixture.py"
EVIDENCE_DIR = ROOT / "mockups" / "evidence" / "prophet-p0b-zero-fouc"
FIXTURE_ASSETS = EVIDENCE_DIR / "inputs" / "browser-data"

MARKETS = {
    "hk": {
        "template": ROOT / "templates" / "hk.html.j2",
        "composer": ROOT / "site" / "hk-stock-v36.js",
        "main": "hk-v37",
        "landmarks": (
            "hk-v37-head",
            "hk-v37-actnow",
            "hk-v37-prophet",
            "hk-v37-leadership",
            "hk-v37-evidence",
            "hk-v37-tools",
        ),
        "owner_actnow": "act-now",
        "owner_board": "standouts",
        "owner_evidence": "track-record",
        "owner_evidence_marker": 'id="track-record"',
        "mounted": "hk-v37-mounted",
    },
    "ca": {
        "template": ROOT / "templates" / "canada.html.j2",
        "composer": ROOT / "site" / "canada-stock-v36.js",
        "main": "ca-v36",
        "landmarks": (
            "ca-v36-head",
            "ca-v36-actnow",
            "ca-v36-prophet",
            "ca-v36-leadership",
            "ca-v36-evidence",
            "ca-v36-tools",
        ),
        "owner_actnow": "act-now",
        "owner_board": "standouts",
        "owner_evidence": "ca-track-record",
        "owner_evidence_marker": "ca_track_record_surface()",
        "mounted": "ca-v36-mounted",
    },
}


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"sparse checkout omits {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _function_source(text: str, name: str) -> str:
    match = re.search(
        rf"  function {re.escape(name)}\b.*?(?=\n  function |\n  if \(document\.readyState)",
        text,
        re.S,
    )
    assert match, f"{name}() missing"
    return match.group(0)


def _run_node_function(text: str, name: str, program: str) -> object:
    """Execute the real production function with tiny DOM-owner fixtures."""
    return _run_node_functions(text, (name,), program)


def _run_node_functions(
    text: str, names: tuple[str, ...], program: str
) -> object:
    """Execute cooperating production functions with tiny DOM-owner fixtures."""
    node = shutil.which("node")
    assert node, "node is required for the stock-dashboard code gate"
    prelude = ["let qs, qsa, state;"]
    if "bi" not in names:
        prelude.append("function bi(en, _zh) { return en; }")
    harness = "\n".join(
        (*prelude, *(_function_source(text, name) for name in names), program)
    )
    run = subprocess.run(
        [node, "-e", harness],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _template_shell(market: str) -> str:
    spec = MARKETS[market]
    text = _read(spec["template"])
    marker = f'id="{spec["main"]}"'
    start = text.index("<main", text.index(marker) - 100)
    end = text.index("</main>", start)
    return text[start:end]


@pytest.mark.parametrize("market", MARKETS)
def test_template_owns_one_static_canonical_main(market: str) -> None:
    """The deployable source, not JavaScript, owns the complete page skeleton."""
    spec = MARKETS[market]
    template = _read(spec["template"])
    shell = _template_shell(market)
    assert template.count("<main") == 1
    assert f'id="{spec["main"]}"' in shell
    assert "mx-stockdash" in shell
    assert f"mx-stockdash--{market}" in shell
    positions = [shell.index(f'id="{node_id}"') for node_id in spec["landmarks"]]
    assert positions == sorted(positions), (
        f"{market}: first-frame order must be header -> action -> Prophet -> "
        "leadership -> evidence -> tools"
    )


@pytest.mark.parametrize("market", MARKETS)
def test_owner_surfaces_are_inside_their_static_canonical_landmarks(market: str) -> None:
    """P0B composes owner HTML in place; no hidden source page feeds a clone."""
    spec = MARKETS[market]
    shell = _template_shell(market)
    placements = (
        (spec["landmarks"][1], f'id="{spec["owner_actnow"]}"'),
        (spec["landmarks"][2], f'id="{spec["owner_board"]}"'),
        (spec["landmarks"][4], spec["owner_evidence_marker"]),
    )
    for landmark_id, owner_marker in placements:
        start = shell.index(f'id="{landmark_id}"')
        later = [
            shell.find(f'id="{candidate}"', start + 1)
            for candidate in spec["landmarks"]
        ]
        end = min(pos for pos in later if pos > start)
        assert owner_marker in shell[start:end], (
            f"{market}: owner marker {owner_marker!r} is not statically "
            f"composed inside #{landmark_id}"
        )


@pytest.mark.parametrize("market", MARKETS)
def test_template_loads_governed_shell_css_statically(market: str) -> None:
    """A failed composer request cannot remove the first-frame presentation."""
    template = _read(MARKETS[market]["template"])
    assert '<link id="mx-stockdash-css" rel="stylesheet" href="stock-dashboard.css">' in template


def test_governed_shell_assets_are_static_and_deployable() -> None:
    """The deploy pair is byte-identical and loader success never admits paint."""
    for asset in ("stock-dashboard.css", "dashboard-icons.js"):
        assert _read(ROOT / "templates" / asset) == _read(ROOT / "site" / asset)

    loader = _read(ROOT / "templates" / "dashboard-icons.js")
    assert "ensureStockDashCss" not in loader
    assert "stock-dashboard.css" not in loader
    assert loader.count("function inject()") >= 2


@pytest.mark.parametrize("market", MARKETS)
def test_static_shell_accessible_labels_are_plain_attribute_text(market: str) -> None:
    """The bilingual ``t()`` helper emits markup and must never enter an attribute."""
    shell = _template_shell(market)
    assert 'aria-label="{{ t(' not in shell


@pytest.mark.parametrize("market", MARKETS)
def test_composer_only_enhances_existing_dom_in_place(market: str) -> None:
    """Ban every carrier of the superseded replacement-page architecture."""
    spec = MARKETS[market]
    text = _read(spec["composer"])
    assert not re.search(r"createElement\(\s*['\"]main['\"]\s*\)", text)
    assert spec["mounted"] not in text
    for token in (
        'insertAdjacentElement("afterend", main)',
        "insertAdjacentElement('afterend', main)",
        "grid.insertBefore(card",
        "appendChild(tableWrap)",
        "appendChild(trk)",
        "evBody.appendChild",
    ):
        assert token not in text, f"{market}: composer still migrates owner DOM via {token}"

    build = re.search(r"function buildShell\b.*?(?=\n  function )", text, re.S)
    assert build, f"{market}: buildShell() missing"
    assert f'qs("#{spec["main"]}")' in build.group(0), (
        f"{market}: buildShell() must bind the server-owned #{spec['main']}"
    )
    assert "renderActNow" not in text, (
        f"{market}: the composer must adopt the server-owned action DOM, not render it"
    )
    for generator in ("anRowHtml", "anLaneHtml", "anLaneItems"):
        assert f"function {generator}" not in text, (
            f"{market}: action rows and lanes must have exactly one server owner"
        )


def test_canada_optional_fetches_cannot_admit_or_delay_the_shell() -> None:
    """Canada paints/binds first; basket and pulse JSON enhance Leadership later."""
    text = _read(MARKETS["ca"]["composer"])
    start = re.search(r"function start\b.*?(?=\n  if \(document\.readyState)", text, re.S)
    assert start, "Canada start() body missing"
    body = start.group(0)
    bind_at = body.find("buildShell(payload)")
    fetch_at = body.find("Promise.all")
    assert 0 <= bind_at < fetch_at, (
        "Canada must bind the static shell before optional basket/pulse fetches"
    )
    assert "setTimeout(function () { if (!done)" not in body


def test_canada_top_picks_remains_the_first_five_owner_cards() -> None:
    """P0B must not reinterpret the established nine-name board population."""
    text = _read(MARKETS["ca"]["composer"])
    assert "state.cards.slice(0, 5)" in text
    assert 'card.classList.toggle("ca-v36-top-pick", i < 5)' in text


@pytest.mark.parametrize(
    ("market", "owner_selector", "board_phrase"),
    (
        ("hk", "#hk-owner-population-proof", "stage board"),
        ("ca", "#ca-v36-card-grid", "board"),
    ),
)
def test_result_copy_requires_an_identity_proven_unique_population(
    market: str, owner_selector: str, board_phrase: str
) -> None:
    """A combined current-name total is admitted only by the server union proof."""
    text = _read(MARKETS[market]["composer"])
    watch = re.search(r"function watchPopulation\b.*?(?=\n  function )", text, re.S)
    assert watch, f"{market}: watchPopulation() missing"
    assert f'qs("{owner_selector}")' in watch.group(0)
    assert 'getAttribute("data-owner-watch-population")' in watch.group(0)

    unique = re.search(r"function uniquePopulation\b.*?(?=\n  function )", text, re.S)
    assert unique, f"{market}: uniquePopulation() missing"
    assert f'qs("{owner_selector}")' in unique.group(0)
    assert 'getAttribute("data-owner-unique-population")' in unique.group(0)

    apply = _function_source(text, "applyFilter")
    population_copy = _function_source(text, "populationCopy")
    body = apply + population_copy
    assert "watchPopulation()" in body
    assert "uniquePopulation()" in body
    assert "watch === null" in body
    assert "unique === null" in body
    assert "current names (" in body
    assert "unique total unavailable" in body
    assert board_phrase in body
    assert "watch unavailable" in body
    assert "当前共" in body
    assert "去重总数暂不可用" in body
    assert "观察名单暂不可用" in body
    assert "total + watch" not in population_copy
    assert "board + watch" not in population_copy
    assert "47 current names" not in text
    assert "17 current names" not in text


@pytest.mark.parametrize(
    ("market", "empty_selector", "board_function", "top_empty_copy"),
    (
        (
            "hk",
            "#hk-v37-grid-empty",
            "ownerPopulation",
            "No featured names right now.",
        ),
        (
            "ca",
            "#ca-v36-grid-empty",
            "boardPopulation",
            "No Top Picks right now.",
        ),
    ),
)
def test_loaded_zero_card_empty_copy_requires_an_active_projection(
    market: str,
    empty_selector: str,
    board_function: str,
    top_empty_copy: str,
) -> None:
    """Watch-only All is not a failed leadership filter or an empty estate."""
    text = _read(MARKETS[market]["composer"])
    observed = _run_node_functions(
        text,
        ("esc", "bi", "emptyStateHtml", "applyFilter"),
        f"""
function allowed() {{ return true; }}
function ticker(value) {{ return value || ""; }}
function {board_function}() {{ return 0; }}
function watchPopulation() {{ return 8; }}
function uniquePopulation() {{ return 8; }}
function populationCopy() {{ return "0 actionable cards shown · 8 current names"; }}
function markLeadership() {{}}
function applyTableFilter() {{}}

function run(source, membership) {{
  var empty = {{hidden: true, innerHTML: "STATIC_OWNER_STATE"}};
  qs = function (selector) {{
    if (selector === {json.dumps(empty_selector)}) return empty;
    return null;
  }};
  qsa = function () {{ return []; }};
  state = {{cards: [], source: source, filter: membership === null ? null : {{id: "fixture"}}, featuredCount: 0}};
  itemForFilter = function () {{
    return membership === null ? null : {{members: new Set(new Array(membership).fill("WATCH")), href: ""}};
  }};
  applyFilter();
  return {{source: source, membership: membership, hidden: empty.hidden, html: empty.innerHTML}};
}}

console.log(JSON.stringify([
  run("all", null),
  run("all", 1),
  run("all", 0),
  run("top", null)
]));
""",
    )
    assert observed == [
        {
            "source": "all",
            "membership": None,
            "hidden": True,
            "html": "STATIC_OWNER_STATE",
        },
        {
            "source": "all",
            "membership": 1,
            "hidden": False,
            "html": (
                '<span class="l-en">No actionable cards match this leadership '
                'filter; matching watch/stage names remain below.</span>'
                '<span class="l-zh">当前领先筛选下无可操作卡片；匹配的观察/阶段名单仍保留在下方。</span>'
            ),
        },
        {
            "source": "all",
            "membership": 0,
            "hidden": False,
            "html": (
                '<span class="l-en">No current Prophet names in this group.</span>'
                '<span class="l-zh">该组别暂无 Prophet 候选。</span>'
            ),
        },
        {
            "source": "top",
            "membership": None,
            "hidden": False,
            "html": (
                f'<span class="l-en">{top_empty_copy}</span>'
                + (
                    '<span class="l-zh">当前暂无精选个股。</span>'
                    if market == "hk"
                    else '<span class="l-zh">当前暂无首选。</span>'
                )
            ),
        },
    ]


def test_hk_stage_owner_count_is_fail_closed_and_preserves_numeric_zero() -> None:
    text = _read(MARKETS["hk"]["composer"])
    observed = _run_node_function(
        text,
        "ownerPopulation",
        """
const cases = [null, "unavailable", "0", "39"];
console.log(JSON.stringify(cases.map(function (ownerText) {
  state = {rows: new Array(91), cards: new Array(5)};
  qs = function (selector) {
    if (selector !== "#hk-owner-population-proof" || ownerText === null) return null;
    return {getAttribute: function (name) {
      return name === "data-owner-board-population" ? ownerText : null;
    }};
  };
  qsa = function () { return []; };
  return ownerPopulation();
})));
""",
    )
    assert observed == [None, None, 0, 39]


def test_canada_board_count_requires_the_server_owner_marker() -> None:
    template = _read(MARKETS["ca"]["template"])
    assert "{% if _ca_owner.board_valid %}" in template
    assert 'data-owner-population="{{ _ca_board_n }}"' in template

    text = _read(MARKETS["ca"]["composer"])
    observed = _run_node_function(
        text,
        "boardPopulation",
        """
const cases = [null, "unavailable", "0", "9"];
console.log(JSON.stringify(cases.map(function (ownerCount) {
  qs = function (selector) {
    if (selector !== "#ca-v36-card-grid" || ownerCount === null) return null;
    return {getAttribute: function () { return ownerCount; }};
  };
  qsa = function () { return []; };
  state = {cards: new Array(99)};
  return boardPopulation();
})));
""",
    )
    assert observed == [None, None, 0, 9]


_MISSING = object()


def _render_canada_owner_fixture(
    setups: object = _MISSING, actions: object = _MISSING
) -> BeautifulSoup:
    """Render Canada from the bounded frozen-fixture context used by P0B."""
    from engine import i18n
    from scripts.render_stock_dashboard_fixture import (
        TEMPLATES,
        TrackingLoader,
        canada_context,
        load_owner_fixture,
    )

    frozen_setups, _owner_path = load_owner_fixture("ca")
    vm = canada_context(frozen_setups)
    if setups is _MISSING:
        vm.pop("setups")
    else:
        vm["setups"] = setups
    if actions is not _MISSING:
        vm["actions"] = actions
    env = Environment(loader=TrackingLoader(TEMPLATES), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    html = env.get_template("canada.html.j2").render(**vm)
    return BeautifulSoup(html, "html.parser")


def test_canada_static_first_frame_counts_both_proven_owner_lists() -> None:
    """The JS-free first frame names Top and the complete 9+8 estate."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert "5 actionable cards shown" in copy
    assert "17 current names (9 stage board + 8 watch)" in copy
    assert grid.get("data-owner-population") == "9"
    assert grid.get("data-owner-watch-population") == "8"
    assert grid.get("data-owner-unique-population") == "17"
    assert len(soup.select("#standouts .watch-strip .watch-grid a[href]")) == 8


def test_canada_static_first_frame_preserves_explicit_empty_owner_lists() -> None:
    """An explicit empty list is the only shape allowed to prove owner zero."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    setups = {**setups, "buy": [], "watch": []}
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert "0 actionable cards shown" in copy
    assert "0 current names (0 stage board + 0 watch)" in copy
    assert grid.get("data-owner-population") == "0"
    assert grid.get("data-owner-watch-population") == "0"
    assert grid.get("data-owner-unique-population") == "0"


@pytest.mark.parametrize(
    ("buy_owner", "board_state"),
    (
        pytest.param([], "available", id="explicit-empty"),
        pytest.param(_MISSING, "unavailable", id="missing"),
        pytest.param(None, "unavailable", id="null"),
        pytest.param("not-a-list", "unavailable", id="string"),
        pytest.param({"ticker": "not-a-list"}, "unavailable", id="mapping"),
        pytest.param([None], "unavailable", id="null-row"),
        pytest.param([42], "unavailable", id="numeric-row"),
        pytest.param(["invalid-row"], "unavailable", id="string-row"),
        pytest.param([{}], "unavailable", id="empty-mapping-row"),
    ),
)
def test_canada_watch_only_first_frame_preserves_owner_rows_when_buy_is_empty_or_unavailable(
    buy_owner: object, board_state: str
) -> None:
    """Watch is an independent owner lane; missing buy is not an empty board."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    setups = dict(setups)
    expected_watch = list(setups["watch"])
    if buy_owner is _MISSING:
        setups.pop("buy")
    else:
        setups["buy"] = buy_owner

    soup = _render_canada_owner_fixture(setups)
    assert len(soup.find_all("main")) == 1
    prophet = soup.find(id="ca-v36-prophet")
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert prophet is not None and result is not None and grid is not None
    assert prophet.get("data-source-owner-state") == board_state
    assert grid.get("data-owner-watch-population") == str(len(expected_watch))
    assert grid.get("data-owner-population") == (
        "0" if board_state == "available" else None
    )
    assert grid.get("data-owner-unique-population") == (
        str(len(expected_watch)) if board_state == "available" else None
    )

    copy = result.get_text(" ", strip=True)
    expected_count = len(expected_watch)
    if board_state == "available":
        assert f"{expected_count} current names (0 stage board + {expected_count} watch)" in copy
    else:
        assert f"stage board unavailable · {expected_count} watch names" in copy
    assert "No Prophet candidates are published for this board" not in prophet.get_text(
        " ", strip=True
    )
    assert prophet.select_one("#stocktable-data") is None

    links = prophet.select("#standouts .watch-strip .watch-grid a[href]")
    assert [link.get("href") for link in links] == [
        f"canada_stock.html#{row['ticker']}" for row in expected_watch
    ]
    assert [
        link.select_one(".wg-tk").get_text(" ", strip=True).split()[0]
        for link in links
    ] == [row["ticker"] for row in expected_watch]
    for link, row in zip(links, expected_watch, strict=True):
        assert ("wg-knife" in link.get("class", [])) == (
            row.get("watch_reason") == "knife"
        )
        if row.get("block_reason"):
            assert str(row["block_reason"]) in link.get("title", "")


def test_canada_static_first_frame_refuses_an_overlapping_owner_union() -> None:
    """The same ticker on board and watch can never be counted twice as current."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    setups["watch"][0]["ticker"] = setups["buy"][0]["ticker"]
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert "9 stage-board names · 8 watch names · unique total unavailable" in copy
    assert "current names" not in copy
    assert grid.get("data-owner-population") == "9"
    assert grid.get("data-owner-watch-population") == "8"
    assert grid.get("data-owner-unique-population") is None


@pytest.mark.parametrize(
    ("lane", "unavailable", "known_attr"),
    (
        ("buy", "board unavailable", "data-owner-watch-population"),
        ("watch", "watch unavailable", "data-owner-population"),
    ),
)
def test_canada_static_first_frame_rejects_duplicate_owner_identities(
    lane: str, unavailable: str, known_attr: str
) -> None:
    """An owner lane with duplicate stable identities is not a known population."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    setups[lane][1]["ticker"] = setups[lane][0]["ticker"]
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert unavailable in copy
    assert "current names" not in copy
    assert grid.get(known_attr) is not None
    assert grid.get("data-owner-unique-population") is None


def _render_hk_owner_fixture(
    setups: object, actions: object = _MISSING
) -> BeautifulSoup:
    """Render HK from the bounded frozen-fixture context used by P0B."""
    from engine import i18n
    from scripts.render_stock_dashboard_fixture import (
        TEMPLATES,
        TrackingLoader,
        hk_context,
    )

    env = Environment(loader=TrackingLoader(TEMPLATES), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    vm = hk_context(setups)
    if actions is not _MISSING:
        vm["actions"] = actions
    html = env.get_template("hk.html.j2").render(**vm)
    return BeautifulSoup(html, "html.parser")


@pytest.mark.parametrize(
    ("market", "prophet_id", "view_attr", "expected_source", "expected_shown"),
    (
        ("ca", "ca-v36-prophet", "data-ca-view", "top", 5),
        ("hk", "hk-v37-prophet", "data-hk-view", "all", 3),
    ),
)
def test_static_prophet_source_and_chrome_are_truthful_before_composer(
    market: str,
    prophet_id: str,
    view_attr: str,
    expected_source: str,
    expected_shown: int,
) -> None:
    """One header owns source/view/help/vintage before deferred JS can run."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture(market)
    soup = (
        _render_canada_owner_fixture(setups, _actions())
        if market == "ca"
        else _render_hk_owner_fixture(setups, _actions())
    )
    prophet = soup.find(id=prophet_id)
    assert prophet is not None
    assert prophet.get("data-initial-source") == expected_source
    assert prophet.get("data-source-owner-state") == "available"
    selected = prophet.select_one(
        f"[data-{market}-source][aria-selected='true']"
    )
    assert selected is not None
    assert selected.get(f"data-{market}-source") == expected_source
    assert f"{expected_shown} actionable cards shown" in prophet.select_one(
        f"#{market}-v36-result" if market == "ca" else "#hk-v37-result"
    ).get_text(" ", strip=True)

    assert len(prophet.select(":scope > .ca-v36-sec-hd h2, :scope > .hk-v37-sec-hd h2")) == 1
    assert not prophet.select("#standouts > h2")
    assert len(prophet.select("[data-prophet-owner-context]")) == 1
    assert len(prophet.select("[data-prophet-vintage]")) == 1
    assert len(prophet.select("[data-prophet-help]")) == 1

    view_controls = prophet.select("[data-prophet-view-control]")
    assert len(view_controls) == 1
    assert not prophet.select("#st-view-toggle, #st-btn-grid, #st-btn-table")
    view_buttons = view_controls[0].select(f"button[{view_attr}]")
    assert len(view_buttons) == 2
    assert view_buttons[0].get("aria-selected") == "true"
    assert view_buttons[1].get("aria-selected") == "false"
    assert view_buttons[1].has_attr("disabled")
    assert "StockTable._setView" in view_buttons[0].get("onclick", "")
    assert "StockTable._setView" in view_buttons[1].get("onclick", "")


def test_hk_static_source_uses_owner_featured_identity_when_present() -> None:
    """HK Top is the owner pv-featured cohort; zero featured falls back to All."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups["buy"][0]["featured"] = True
    setups["buy"][1]["featured"] = True
    soup = _render_hk_owner_fixture(setups, _actions())
    prophet = soup.find(id="hk-v37-prophet")
    assert prophet is not None
    assert prophet.get("data-initial-source") == "top"
    assert prophet.get("data-initial-top-count") == "2"
    assert prophet.select_one("[data-hk-source='top']").get("aria-selected") == "true"
    assert "2 actionable cards shown" in prophet.select_one(
        "#hk-v37-result"
    ).get_text(" ", strip=True)
    assert len(prophet.select("#standouts .pvcard.pv-featured")) == 2


@pytest.mark.parametrize("market", ("ca", "hk"))
def test_static_grid_and_table_share_one_ordered_source_identity(market: str) -> None:
    """The server serializes the exact card cohort StockTable must project."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture(market)
    soup = (
        _render_canada_owner_fixture(setups, _actions())
        if market == "ca"
        else _render_hk_owner_fixture(setups, _actions())
    )
    prophet = soup.find(id="ca-v36-prophet" if market == "ca" else "hk-v37-prophet")
    cards = prophet.select("#standouts .pvcard")
    card_ids = [card.get("data-ticker") for card in cards]
    payload = json.loads(prophet.select_one("#stocktable-data").get_text())
    row_ids = [row["ticker"] for row in payload["rows"]]
    top_row_ids = [row["ticker"] for row in payload["rows"] if row["_top"]]
    top_card_ids = (
        card_ids[:5]
        if market == "ca"
        else [card.get("data-ticker") for card in cards if "pv-featured" in card.get("class", [])]
    )
    assert row_ids == card_ids
    assert top_row_ids == top_card_ids
    expected_visible = top_card_ids if prophet.get("data-initial-source") == "top" else card_ids
    assert int(prophet.get("data-initial-top-count")) == len(top_card_ids)
    assert f"{len(expected_visible)} actionable cards shown" in prophet.select_one(
        "#ca-v36-result" if market == "ca" else "#hk-v37-result"
    ).get_text(" ", strip=True)


@pytest.mark.parametrize("market", ("ca", "hk"))
def test_malformed_source_owner_fails_to_typed_full_view(market: str) -> None:
    """Duplicate owner identities cannot leave a synthetic Top selection active."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture(market)
    setups["buy"][1]["ticker"] = setups["buy"][0]["ticker"]
    soup = (
        _render_canada_owner_fixture(setups, _actions())
        if market == "ca"
        else _render_hk_owner_fixture(setups, _actions())
    )
    prophet = soup.find(id="ca-v36-prophet" if market == "ca" else "hk-v37-prophet")
    assert prophet.get("data-source-owner-state") == "unavailable"
    assert prophet.get("data-initial-source") == "all"
    assert prophet.select_one(f"[data-{market}-source='all']").get("aria-selected") == "true"
    top = prophet.select_one(f"[data-{market}-source='top']")
    assert top.has_attr("disabled")
    assert top.get("aria-disabled") == "true"
    result = prophet.select_one("#ca-v36-result" if market == "ca" else "#hk-v37-result")
    assert "stage board unavailable" in result.get_text(" ", strip=True)


@pytest.mark.parametrize(
    ("market", "enhanced_attr", "prophet_id", "static_selector"),
    (
        (
            "ca",
            "data-ca-enhanced",
            "ca-v36-prophet",
            ".pvcard:nth-of-type(n+6)",
        ),
        (
            "hk",
            "data-hk-enhanced",
            "hk-v37-prophet",
            ".pvcard:not(.pv-featured)",
        ),
    ),
)
def test_static_top_projection_is_css_owned_until_composer_adopts_it(
    market: str, enhanced_attr: str, prophet_id: str, static_selector: str
) -> None:
    css = _read(ROOT / "templates" / "stock-dashboard.css")
    assert f':not([{enhanced_attr}="true"])' in css
    assert f'#{prophet_id}[data-initial-source="top"]' in css
    assert static_selector in css


@pytest.mark.parametrize(
    ("market", "composer", "view_attr", "event_name"),
    (
        ("ca", "canada-stock-v36.js", "data-ca-view", "stocktable:ca-view"),
        ("hk", "hk-stock-v36.js", "data-hk-view", "stocktable:hk-view"),
    ),
)
def test_composer_adopts_server_source_and_single_stocktable_view_transition(
    market: str, composer: str, view_attr: str, event_name: str
) -> None:
    text = _read(ROOT / "site" / composer)
    start = _function_source(text, "start")
    set_view = _function_source(text, "setView")
    assert "data-initial-source" in start
    assert "state.source" in start
    assert event_name in text
    assert "StockTable._setView" in set_view
    assert f'closest("[{view_attr}]")' not in _function_source(text, "bind")


_ACTION_LANES = (
    "buy_now",
    "buy_soon",
    "on_the_run",
    "take_profits",
    "hold",
    "avoid",
)


def _actions(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {lane: [] for lane in _ACTION_LANES}
    payload.update(overrides)
    return payload


def _action_row(ticker: str, name: str = "Fixture sector") -> dict[str, object]:
    return {
        "ticker": ticker,
        "name": name,
        "label": "Fixture action",
        "days": 2,
        "dir": "up",
    }


def _render_action_fixture(market: str, actions: object) -> BeautifulSoup:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture(market)
    if market == "ca":
        return _render_canada_owner_fixture(setups, actions)
    return _render_hk_owner_fixture(setups, actions)


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize(
    "actions",
    (
        _MISSING,
        None,
        [],
        {},
        _actions(buy_now=None),
        _actions(avoid="not-a-list"),
        _actions(buy_soon={"ticker": "not-a-list"}),
    ),
)
def test_action_owner_unavailable_never_masquerades_as_healthy_empty(
    market: str, actions: object
) -> None:
    """Missing/non-mapping/mixed-invalid owner state is unavailable, never zero."""
    if actions is _MISSING:
        from scripts.render_stock_dashboard_fixture import load_owner_fixture

        setups, _owner_path = load_owner_fixture(market)
        vm_actions = None
        if market == "ca":
            from engine import i18n
            from scripts.render_stock_dashboard_fixture import (
                TEMPLATES,
                TrackingLoader,
                canada_context,
            )

            vm = canada_context(setups)
            vm.pop("actions")
            env = Environment(loader=TrackingLoader(TEMPLATES), autoescape=False)
            env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
            soup = BeautifulSoup(
                env.get_template("canada.html.j2").render(**vm), "html.parser"
            )
        else:
            from engine import i18n
            from scripts.render_stock_dashboard_fixture import (
                TEMPLATES,
                TrackingLoader,
                hk_context,
            )

            vm = hk_context(setups)
            vm.pop("actions")
            env = Environment(loader=TrackingLoader(TEMPLATES), autoescape=False)
            env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
            soup = BeautifulSoup(
                env.get_template("hk.html.j2").render(**vm), "html.parser"
            )
        assert vm_actions is None
    else:
        soup = _render_action_fixture(market, actions)

    panel = soup.find(id="act-now")
    assert panel is not None
    assert panel.get("data-action-owner-state") == "unavailable"
    copy = panel.get_text(" ", strip=True)
    assert "Action owner unavailable" in copy
    assert "No sector actions are open" not in copy
    assert not panel.select("[data-hk-lead-id], [data-ca-lead-id]")


@pytest.mark.parametrize("market", MARKETS)
def test_explicit_empty_action_owner_is_the_only_healthy_empty_state(
    market: str,
) -> None:
    soup = _render_action_fixture(market, _actions())
    panel = soup.find(id="act-now")
    assert panel is not None
    assert panel.get("data-action-owner-state") == "empty"
    copy = panel.get_text(" ", strip=True)
    assert "No sector actions are open" in copy
    assert "Action owner unavailable" not in copy
    tabs = panel.select(f"[data-{market}-an-lane]")
    lanes = panel.select("[data-action-lane-body]")
    assert len(tabs) == 4
    assert len(lanes) == 4
    assert [tab.get("data-hk-an-lane") or tab.get("data-ca-an-lane") for tab in tabs] == [
        "buy",
        "near",
        "wait",
        "avoid",
    ]
    assert [tab.select_one(".l-en").get_text(strip=True) for tab in tabs] == [
        "Buy Now",
        "In Favour",
        "Bottoming Watch",
        "Reduce / Avoid",
    ]
    assert [tab.select_one("b").get_text(strip=True) for tab in tabs] == ["0"] * 4
    assert not panel.select("[role='tablist'], [role='tab']")
    assert all(not tab.has_attr("aria-selected") for tab in tabs)
    assert all(not tab.has_attr("aria-controls") for tab in tabs)
    assert [tab.has_attr(f"data-{market}-an-default") for tab in tabs] == [True, False, False, False]
    assert [lane.get("data-action-lane-body") for lane in lanes] == [
        "buy",
        "near",
        "wait",
        "avoid",
    ]
    assert [lane.get("data-action-lane-body") for lane in lanes if "is-current" in lane.get("class", [])] == ["buy"]


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize(
    ("actions", "selected", "counts", "identities"),
    (
        (_actions(buy_now=[_action_row("buy-a")]), "buy", [1, 0, 0, 0], [["BUY-A"], [], [], []]),
        (_actions(on_the_run=[_action_row("near-a")]), "near", [0, 1, 0, 0], [[], ["NEAR-A"], [], []]),
        (_actions(buy_soon=[_action_row("wait-a")]), "wait", [0, 0, 1, 0], [[], [], ["WAIT-A"], []]),
        (_actions(avoid=[_action_row("avoid-a")]), "avoid", [0, 0, 0, 1], [[], [], [], ["AVOID-A"]]),
        (
            _actions(
                hold=[_action_row("near-a"), _action_row("near-b")],
                buy_soon=[_action_row("wait-a")],
                take_profits=[_action_row("avoid-a")],
            ),
            "near",
            [0, 2, 1, 1],
            [[], ["NEAR-A", "NEAR-B"], ["WAIT-A"], ["AVOID-A"]],
        ),
        (_actions(), "buy", [0, 0, 0, 0], [[], [], [], []]),
    ),
)
def test_server_elects_and_wires_the_complete_action_selector(
    market: str,
    actions: dict[str, object],
    selected: str,
    counts: list[int],
    identities: list[list[str]],
) -> None:
    """The first frame owns lane order, counts, identity, and deterministic election."""
    soup = _render_action_fixture(market, actions)
    panel = soup.find(id="act-now")
    assert panel is not None
    tabs = panel.select(f"[data-{market}-an-lane]")
    lanes = panel.select("[data-action-lane-body]")
    assert len(tabs) == len(lanes) == 4
    assert [int(tab.select_one("b").get_text(strip=True)) for tab in tabs] == counts
    assert [tab.get("href") for tab in tabs] == [f"#{lane.get('id')}" for lane in lanes]
    assert len({tab.get("href") for tab in tabs}) == 4
    assert not panel.select("[role='tablist'], [role='tab']")
    assert all(not tab.has_attr("aria-selected") for tab in tabs)
    assert all(not tab.has_attr("aria-controls") for tab in tabs)
    assert all(not tab.has_attr("aria-current") for tab in tabs)
    assert [
        tab.get(f"data-{market}-an-default") == "true" for tab in tabs
    ].count(True) == 1
    assert next(
        tab.get(f"data-{market}-an-lane")
        for tab in tabs
        if tab.get(f"data-{market}-an-default") == "true"
    ) == selected
    assert [lane.get("data-action-lane-body") for lane in lanes if "is-current" in lane.get("class", [])] == [selected]
    assert [
        [row.get("data-action-id") for row in lane.select("[data-action-id]")]
        for lane in lanes
    ] == identities
    assert not panel.select(".lst-wrap, .lst-collapse, .lst-more")


@pytest.mark.parametrize(
    ("market", "body_id", "row_class", "hook", "count"),
    (
        ("hk", "hk-v37-an-body", "hk-v37-an-row", "data-hk-lead-id", "2"),
        ("ca", "ca-v36-an-body", "ca-v36-an-row", "data-ca-lead-id", "2"),
    ),
)
def test_static_action_rows_bind_only_identity_proven_membership(
    market: str, body_id: str, row_class: str, hook: str, count: str
) -> None:
    actions = _actions(
        buy_now=[
            _action_row("fixture-sector"),
            _action_row("unknown-sector", "Unknown sector"),
        ]
    )
    soup = _render_action_fixture(market, actions)
    panel = soup.find(id="act-now")
    body = soup.find(id=body_id)
    assert panel is not None and body is not None
    assert panel.get("data-action-owner-state") == "available"
    assert len(body.select(f"[data-{market}-an-lane]")) == 4
    assert len(body.select("[data-action-lane-body]")) == 4

    known = body.select_one(f".{row_class}-w[data-action-id='FIXTURE-SECTOR']")
    unknown = body.select_one(f".{row_class}-w[data-action-id='UNKNOWN-SECTOR']")
    assert known is not None and unknown is not None
    assert known.select_one(f"[{hook}='FIXTURE-SECTOR']") is not None
    assert f"{count} · Prophet" in known.get_text(" ", strip=True)
    assert unknown.select_one(f"[{hook}]") is None
    assert "Prophet" not in unknown.get_text(" ", strip=True)
    route = unknown.find("a", href="sectors/unknown-sector.html")
    assert route is not None


@pytest.mark.parametrize(
    ("market", "selector"),
    (("hk", "#standouts .nbgrid"), ("ca", "#standouts .cards")),
)
def test_canonical_prophet_host_has_one_visibility_owner(
    market: str, selector: str
) -> None:
    """Generic show-more must never hide a card selected by dashboard filters."""
    soup = _render_action_fixture(market, _actions())
    host = soup.select_one(selector)
    assert host is not None
    assert host.get("data-showmore") is None
    assert host.get("data-showmore-rows") is None


def test_canada_static_quote_header_is_neutral_until_quote_plane_confirms() -> None:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    soup = _render_canada_owner_fixture(setups, _actions())
    status = soup.find(id="ca-v36-quote-status")
    assert status is not None
    assert status.get("data-quote-state") == "unavailable"
    copy = status.get_text(" ", strip=True)
    assert "Quotes unavailable" in copy
    assert "LIVE QUOTES" not in copy
    assert status.select_one(".ca-v36-live-dot") is None


def test_canada_quote_plane_requires_complete_typed_dom_receipts() -> None:
    """A header claim is admitted only when every owner card has one valid receipt."""
    text = _read(MARKETS["ca"]["composer"])
    observed = _run_node_function(
        text,
        "quotePlaneState",
        """
function node(stateValue, titleValue) {
  return {getAttribute: function (name) {
    return name === "data-live" ? stateValue : (name === "title" ? titleValue : null);
  }};
}
const cases = [
  [],
  [node(null, null)],
  [node("1", "not a quote receipt")],
  [node("1", "live · FixtureFeed · Sep 5, 10:30 ET")],
  [node("delayed", "≥15-min delayed · Yahoo · 15m ago")],
  [node("stale", "stale · Yahoo · 41m ago")],
  [node("closed", "market closed · Yahoo · 481m ago")],
  [node("1", "live · FixtureFeed · 0m ago"), node(null, null)],
  [node("1", "live · FixtureFeed · 0m ago"), node("stale", "stale · FixtureFeed · 41m ago")]
];
console.log(JSON.stringify(cases.map(quotePlaneState)));
""",
    )
    assert observed == [
        {"state": "unavailable", "detail": ""},
        {"state": "unavailable", "detail": ""},
        {"state": "unavailable", "detail": ""},
        {"state": "live", "detail": "live · FixtureFeed · Sep 5, 10:30 ET"},
        {"state": "delayed", "detail": "≥15-min delayed · Yahoo · 15m ago"},
        {"state": "stale", "detail": "stale · Yahoo · 41m ago"},
        {"state": "closed", "detail": "market closed · Yahoo · 481m ago"},
        {"state": "unavailable", "detail": ""},
        {"state": "unavailable", "detail": ""},
    ]


def test_hk_owner_marker_binds_disjoint_identity_proven_populations() -> None:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    soup = _render_hk_owner_fixture(setups)
    proof = soup.find(id="hk-owner-population-proof")
    assert proof is not None
    assert proof.get("data-owner-board-population") == "39"
    assert proof.get("data-owner-watch-population") == "8"
    assert proof.get("data-owner-unique-population") == "47"


def test_hk_owner_marker_refuses_an_overlapping_owner_union() -> None:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups["watch"][0]["ticker"] = setups["buy"][0]["ticker"]
    soup = _render_hk_owner_fixture(setups)
    proof = soup.find(id="hk-owner-population-proof")
    assert proof is not None
    assert proof.get("data-owner-board-population") == "39"
    assert proof.get("data-owner-watch-population") == "8"
    assert proof.get("data-owner-unique-population") is None


def test_hk_owner_marker_rejects_a_duplicate_board_identity() -> None:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups["ripening"][0]["ticker"] = setups["buy"][0]["ticker"]
    soup = _render_hk_owner_fixture(setups)
    proof = soup.find(id="hk-owner-population-proof")
    assert proof is not None
    assert proof.get("data-owner-board-population") is None
    assert proof.get("data-owner-watch-population") == "8"
    assert proof.get("data-owner-unique-population") is None


def test_hk_owner_marker_rejects_a_duplicate_watch_identity() -> None:
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups["watch"][1]["ticker"] = setups["watch"][0]["ticker"]
    soup = _render_hk_owner_fixture(setups)
    proof = soup.find(id="hk-owner-population-proof")
    assert proof is not None
    assert proof.get("data-owner-board-population") == "39"
    assert proof.get("data-owner-watch-population") is None
    assert proof.get("data-owner-unique-population") is None


def test_hk_owner_marker_requires_every_priority_lane_to_be_explicit() -> None:
    """A missing lane is unknown, not proof that the lane is empty."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups.pop("ran")
    soup = _render_hk_owner_fixture(setups)
    proof = soup.find(id="hk-owner-population-proof")
    assert proof is not None
    assert proof.get("data-owner-board-population") is None
    assert proof.get("data-owner-watch-population") == "8"
    assert proof.get("data-owner-unique-population") is None


@pytest.mark.parametrize(
    "buy_owner",
    (
        pytest.param(_MISSING, id="missing"),
        pytest.param(None, id="null"),
        pytest.param("not-a-list", id="string"),
        pytest.param({"ticker": "not-a-list"}, id="mapping"),
        pytest.param([None], id="null-row"),
        pytest.param([42], id="numeric-row"),
        pytest.param(["invalid-row"], id="string-row"),
        pytest.param([{}], id="empty-mapping-row"),
    ),
)
def test_hk_unavailable_buy_preserves_independent_priority_and_watch_lanes(
    buy_owner: object,
) -> None:
    """The normalized buy owner must cross every raw render seam fail-soft."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("hk")
    setups = dict(setups)
    expected_ripening = {row["ticker"] for row in setups["ripening"]}
    expected_ran = [row["ticker"] for row in setups["ran"]]
    expected_vetoed = {row["ticker"] for row in setups["vetoed"]}
    expected_watch = [row["ticker"] for row in setups["watch"]]
    if buy_owner is _MISSING:
        setups.pop("buy")
    else:
        setups["buy"] = buy_owner

    soup = _render_hk_owner_fixture(setups)
    assert len(soup.find_all("main")) == 1
    prophet = soup.find(id="hk-v37-prophet")
    proof = soup.find(id="hk-owner-population-proof")
    result = soup.find(id="hk-v37-result")
    assert prophet is not None and proof is not None and result is not None
    assert prophet.get("data-source-owner-state") == "unavailable"
    assert prophet.get("data-initial-source") == "all"
    assert proof.get("data-owner-board-population") is None
    assert proof.get("data-owner-watch-population") == str(len(expected_watch))
    assert proof.get("data-owner-unique-population") is None
    copy = result.get_text(" ", strip=True)
    assert f"stage board unavailable · {len(expected_watch)} watch names" in copy
    assert "No Prophet candidates are published for this board" not in prophet.get_text(
        " ", strip=True
    )
    assert prophet.select_one("#stocktable-data") is None

    all_count = prophet.select_one(
        '#hk-stage-filter [data-stagepick="all"] .pbf-n'
    )
    assert all_count is not None
    assert all_count.get_text(strip=True) == str(
        len(expected_ripening) + len(expected_ran) + len(expected_vetoed)
    )
    setting_up_count = prophet.select_one(
        '#hk-stage-filter [data-stagepick="setting_up"] .pbf-n'
    )
    assert setting_up_count is not None
    assert setting_up_count.get_text(strip=True) == str(len(expected_ripening))
    assert [
        link.get("href", "").removeprefix("hk_lookup.html#")
        for link in prophet.select('#standouts .pbr[data-stage="ran"] a.pbr-r[href]')
    ] == expected_ran
    assert {
        link.get("href", "").removeprefix("hk_lookup.html#")
        for link in prophet.select('#standouts .pbv[data-stage="blocked"] a.pbr-r[href]')
    } == expected_vetoed
    assert [
        link.get("href", "").removeprefix("hk_lookup.html#")
        for link in prophet.select("#standouts .watch-strip .watch-grid a[href]")
    ] == expected_watch


@pytest.mark.parametrize(
    ("owner", "value"),
    (
        ("buy", _MISSING),
        ("buy", None),
        ("buy", "not-a-list"),
        ("buy", {"ticker": "not-a-list"}),
        ("watch", _MISSING),
        ("watch", None),
        ("watch", "not-a-list"),
        ("watch", {"ticker": "not-a-list"}),
    ),
)
def test_canada_static_first_frame_never_coerces_malformed_owner_to_zero(
    owner: str, value: object
) -> None:
    """Missing/null/string/mapping owners render unavailable without exceptions."""
    from scripts.render_stock_dashboard_fixture import load_owner_fixture

    setups, _owner_path = load_owner_fixture("ca")
    setups = dict(setups)
    if value is _MISSING:
        setups.pop(owner)
    else:
        setups[owner] = value
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert f"{owner if owner == 'watch' else 'board'} unavailable" in copy
    assert "17 current names" not in copy
    if owner == "buy":
        assert grid.get("data-owner-population") is None
    else:
        assert grid.get("data-owner-watch-population") is None
    assert grid.get("data-owner-unique-population") is None


@pytest.mark.parametrize("setups", (_MISSING, None))
def test_canada_static_first_frame_missing_setups_is_unavailable(
    setups: object,
) -> None:
    soup = _render_canada_owner_fixture(setups)
    result = soup.find(id="ca-v36-result")
    grid = soup.find(id="ca-v36-card-grid")
    assert result is not None and grid is not None
    copy = result.get_text(" ", strip=True)
    assert "board unavailable" in copy
    assert "watch unavailable" in copy
    assert grid.get("data-owner-population") is None
    assert grid.get("data-owner-watch-population") is None
    assert grid.get("data-owner-unique-population") is None


def test_action_lane_split_contract_keeps_distinct_code_and_data_owners() -> None:
    """Fourteen hermetic cases run in code; the generated-page case stays in data."""
    manifest = _read(ROOT / ".github" / "ci" / "legacy-jobs.yml")
    suite = "tests/test_action_board_lane_split.py"

    first_frame_start = manifest.index("  stock-dashboard-first-frame:")
    first_frame_end = manifest.index("\n  prophet-lab:", first_frame_start)
    first_frame_job = manifest[first_frame_start:first_frame_end]
    assert suite not in first_frame_job
    assert (
        "python -m pytest tests/test_stock_dashboard_first_frame.py -q"
        in first_frame_job
    )

    code_start = manifest.index("  unrun-template-chips:")
    code_end = manifest.index("\n  unrun-pit-probes:", code_start)
    code_job = manifest[code_start:code_end]
    assert (
        f"python -m pytest {suite} -q "
        "-k 'not test_hk_static_legacy_grid_cannot_override_hidden'"
    ) in code_job

    data_start = manifest.index("  unrun-intl-collectors:")
    data_end = manifest.index("\n  unrun-russell-breadth:", data_start)
    data_job = manifest[data_start:data_end]
    data_lines = [line for line in data_job.splitlines() if suite in line]
    assert len(data_lines) == 1
    assert "-k" not in data_lines[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rendered_fixture_recipe_is_committed_self_binding_and_deterministic(
    tmp_path: Path,
) -> None:
    """Browser inputs reproduce from candidate templates and checked-in fixtures."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    receipts = []
    for out_dir in (first, second):
        receipt = out_dir / "rendered-fixture.json"
        run = subprocess.run(
            [
                sys.executable,
                str(FIXTURE_RECIPE),
                "--market",
                "all",
                "--out-dir",
                str(out_dir),
                "--receipt",
                str(receipt),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert run.returncode == 0, run.stderr
        receipts.append(json.loads(receipt.read_text(encoding="utf-8")))

    assert receipts[0] == receipts[1]
    receipt = receipts[0]
    assert receipt == json.loads(_read(EVIDENCE_DIR / "rendered-fixture.json"))
    assert receipt["schema"] == "mastermind.stock_dashboard_rendered_fixture.v1"
    assert receipt["proof_class"] == "rendered_fixture"
    assert receipt["transform"] == (
        "jinja2_candidate_template_render_from_frozen_owner_and_action_fixtures"
    )
    assert receipt["ambient_inputs"] == []
    for market, expected in (("hk", (39, 8, 47)), ("ca", (9, 8, 17))):
        market_receipt = receipt["markets"][market]
        page = first / market_receipt["output"]
        assert _sha256(page) == receipt["markets"][market]["output_sha256"]
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        assert len(soup.find_all("main")) == 1
        ids = [node.get("id") for node in soup.find_all(attrs={"id": True})]
        assert len(ids) == len(set(ids)), f"{market}: rendered fixture has duplicate ids"
        assert receipt["markets"][market]["owner_population"] == {
            "board": expected[0],
            "watch": expected[1],
            "intersection": [],
            "unique_total": expected[2],
        }
        expected_case_populations = {
            "hk": {
                "normal": {"board": 39, "watch": 8, "intersection": [], "unique_total": 47},
                "watch-only": {"board": 36, "watch": 8, "intersection": [], "unique_total": 44},
                "null-buy": {"board": None, "watch": 8, "intersection": None, "unique_total": None},
            },
            "ca": {
                "normal": {"board": 9, "watch": 8, "intersection": [], "unique_total": 17},
                "watch-only": {"board": 0, "watch": 8, "intersection": [], "unique_total": 8},
                "null-buy": {"board": None, "watch": 8, "intersection": None, "unique_total": None},
            },
        }[market]
        assert set(market_receipt["owner_cases"]) == {
            "normal",
            "watch-only",
            "null-buy",
        }
        for owner_case, case in market_receipt["owner_cases"].items():
            case_page = first / case["output"]
            assert case["route"] == market_receipt["route"]
            assert _sha256(case_page) == case["output_sha256"]
            assert case["owner_population"] == expected_case_populations[owner_case]
            transform = case["input_transform"]
            canonical = json.dumps(
                transform["payload"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            assert transform["bytes"] == len(canonical)
            assert transform["sha256"] == hashlib.sha256(canonical).hexdigest()
            assert transform["payload"]["owner_case"] == owner_case
            rendered_buy = transform["payload"]["rendered_owner_identities"]["buy"]
            if owner_case == "normal":
                assert rendered_buy
            elif owner_case == "watch-only":
                assert rendered_buy == []
            else:
                assert rendered_buy is None

        overlay = market_receipt["diagnostic_membership_overlay"]
        canonical_overlay = json.dumps(
            overlay["payload"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        assert overlay["bytes"] == len(canonical_overlay)
        assert overlay["sha256"] == hashlib.sha256(canonical_overlay).hexdigest()
        assert overlay["payload"]["group"] == {
            "kind": "sector",
            "id": "FIXTURE-FINANCE",
            "name": "Fixture finance",
            "research_href": "sectors/FIXTURE-FINANCE.html",
        }
        assert all(
            member["owner_lane"] != "buy"
            for member in overlay["payload"]["members"]
        )
        assert overlay["payload"]["card_population_mutation"] == "none"
        assert overlay["payload"]["table_population_mutation"] == "none"
        if market == "hk":
            all_count = soup.select_one(
                '#hk-stage-filter [data-stagepick="all"] .pbf-n'
            )
            assert all_count is not None and all_count.get_text(strip=True) == "39"
            stage_counts = {
                button["data-stagepick"]: button.select_one(".pbf-n").get_text(
                    strip=True
                )
                for button in soup.select(
                    "#hk-stage-filter [data-stagepick]:not([data-stagepick='all'])"
                )
            }
            assert stage_counts == {
                "live": "2",
                "setting_up": "13",
                "ran": "12",
                "blocked": "12",
            }
        input_paths = {item["path"] for item in receipt["markets"][market]["inputs"]}
        assert f"templates/{'hk' if market == 'hk' else 'canada'}.html.j2" in input_paths
        owner_name = (
            "hk-owner-fixture.json" if market == "hk" else "canada-owner-fixture.json"
        )
        assert (
            f"mockups/evidence/prophet-p0b-zero-fouc/inputs/{owner_name}"
            in input_paths
        )
        action_name = (
            "hk-action-fixture.json"
            if market == "hk"
            else "canada-action-fixture.json"
        )
        assert (
            f"mockups/evidence/prophet-p0b-zero-fouc/inputs/{action_name}"
            in input_paths
        )
        assert not any(path.startswith("site/factordata/") for path in input_paths)
        for item in receipt["markets"][market]["inputs"]:
            assert _sha256(ROOT / item["path"]) == item["sha256"]


@pytest.mark.parametrize(
    ("market", "receipt_name", "composer"),
    (
        ("hk", "mobile-layout.json", "hk-stock-v36.js"),
        ("ca", "mobile-layout-canada.json", "canada-stock-v36.js"),
    ),
)
def test_committed_browser_receipts_are_self_binding_fixture_proof(
    market: str, receipt_name: str, composer: str
) -> None:
    """Each checked-in browser claim binds bytes, assets, tool, and lineage."""
    fixture = json.loads(
        _read(EVIDENCE_DIR / "rendered-fixture.json")
    )
    browser = json.loads(_read(EVIDENCE_DIR / receipt_name))
    assert browser["proof_class"] == "browser_fixture_proof_reproducible"
    assert browser["claims"] == {
        "source_contract": "browser_fixture",
        "browser_fixture": "reproducible",
        "canonical_build": "unavailable",
        "production": "none",
    }
    assert browser["fixture_market"] == market
    historical_hashes = {
        "hk": "71427ce354ff3f40e2cc7a9e298c840453465fc3a7fcf285ea32b2a486c89a3a",
        "ca": "caffaacaae9d50b4a31be2ee0b6e61fa1cb0463a7c797e8154886f69e7a03fbc",
    }
    historical = browser["historical_baseline"]
    assert historical["schema"] == (
        "mastermind.stock_dashboard_browser_historical_baseline.v1"
    )
    assert historical["candidate_head"] == (
        "3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86"
    )
    assert historical["candidate_tree"] == (
        "b4dd8fd9b29b4eb769239d35df2a7911e793c7ec"
    )
    assert historical["receipt"] == {
        "path": f"mockups/evidence/prophet-p0b-zero-fouc/{receipt_name}",
        "sha256": historical_hashes[market],
        "recovery": (
            "git show 3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86:"
            f"mockups/evidence/prophet-p0b-zero-fouc/{receipt_name}"
        ),
    }
    assert historical["result"] == {
        "pass": True,
        "state_cases": 7,
        "expansion_cases": 8,
        "fragment_cases": 6,
        "desktop_sequence_cases": 11,
        "total_cases": 32,
        "bound_screenshots": 2,
    }
    expected_historical_screenshots = {
        "hk": [
            {
                "state": "js-disabled",
                "path": "mockups/evidence/prophet-p0b-zero-fouc/hk-js-disabled-dark-390.png",
                "sha256": "0c5c56d9783b8d4b4358b117124120a732bf5c7770ead9d9c1b7c370715440bb",
            },
            {
                "state": "composer-failed",
                "path": "mockups/evidence/prophet-p0b-zero-fouc/hk-composer-failed-light-390.png",
                "sha256": "17f9d95a4765f569cc01c074a8a9cd60facdcadbb4fbcf223d345d8e47fdbee4",
            },
        ],
        "ca": [
            {
                "state": "js-disabled",
                "path": "mockups/evidence/prophet-p0b-zero-fouc/ca-js-disabled-dark-390.png",
                "sha256": "17b369e5f17c29d558acc2306d754ea5a9eb33543c6fd47897eb048e7da0a9e2",
            },
            {
                "state": "composer-failed",
                "path": "mockups/evidence/prophet-p0b-zero-fouc/ca-composer-failed-light-390.png",
                "sha256": "ed067c82a490126c908eb9f53202e90e36c15dd27c57c4d464760db3861afe33",
            },
        ],
    }
    assert historical["screenshots"] == expected_historical_screenshots[market]
    for screenshot in historical["screenshots"]:
        assert _sha256(ROOT / screenshot["path"]) == screenshot["sha256"]
    assert browser["verifier"] == {
        "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
        "sha256": _sha256(BROWSER_RECEIPT),
    }
    assert browser["fixture_receipt"]["sha256"] == _sha256(
        EVIDENCE_DIR / "rendered-fixture.json"
    )
    assert browser["fixture_assets_root"] == (
        "mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data"
    )
    assert browser["input_html"]["sha256"] == fixture["markets"][market]["output_sha256"]
    template = "hk.html.j2" if market == "hk" else "canada.html.j2"
    assert browser["construction_inputs"][f"templates/{template}"] == _sha256(
        ROOT / "templates" / template
    )
    # A digest-only asset (receipt_closure.REFRESHABLE_LOADED_ASSETS) may have
    # moved since the browser run when a committed digest-refresh sidecar
    # vouches for its current bytes; every other loaded asset must match the
    # receipt exactly.
    effective = receipt_closure.effective_loaded_assets(
        ROOT, f"{receipt_closure.EVIDENCE_DIR_REL}/{receipt_name}", browser
    )
    assert set(effective) == set(browser["loaded_assets"])
    for relative, digest in effective.items():
        assert _sha256(ROOT / relative) == digest, relative
    assert browser["loaded_assets"]["site/stock-dashboard.css"] == _sha256(
        ROOT / "site" / "stock-dashboard.css"
    )
    assert browser["loaded_assets"][f"site/{composer}"] == _sha256(
        ROOT / "site" / composer
    )
    assert set(browser["rendered_owner_cases"]) == {
        "normal",
        "watch-only",
        "null-buy",
    }
    for owner_case, case in browser["rendered_owner_cases"].items():
        expected = fixture["markets"][market]["owner_cases"][owner_case]
        assert case == {
            "route": expected["route"],
            "output": expected["output"],
            "output_sha256": expected["output_sha256"],
            "owner_population": expected["owner_population"],
            "input_transform": expected["input_transform"],
        }
    action_fixture = (
        "hk-action-fixture.json"
        if market == "hk"
        else "canada-action-fixture.json"
    )
    action_path = (
        "mockups/evidence/prophet-p0b-zero-fouc/inputs/" + action_fixture
    )
    assert browser["construction_inputs"][action_path] == _sha256(
        ROOT / action_path
    )
    frozen_requests = {
        "canadabasketdata/baskets.json",
        "canadabasketdata/sector_pulse_canada.json",
        "live/overlay.json",
        "live/quotes.json",
        "marketdata/rotation_events_hk.json",
    }
    assert not frozen_requests.intersection(
        path.removeprefix("site/") for path in browser["loaded_assets"]
    )
    loaded_fixture_assets = {
        str((ROOT / path).relative_to(FIXTURE_ASSETS))
        for path in browser["loaded_assets"]
        if (ROOT / path).is_relative_to(FIXTURE_ASSETS)
    }
    expected_frozen_assets = {
        "hk": {
            "live/overlay.json",
            "live/quotes.json",
            "marketdata/rotation_events_hk.json",
        },
        "ca": {
            "canadabasketdata/baskets.json",
            "canadabasketdata/sector_pulse_canada.json",
            "live/overlay.json",
            "live/quotes.json",
        },
    }
    assert loaded_fixture_assets == expected_frozen_assets[market]
    assert {row["state"] for row in browser["states"]} >= {
        "en-dark",
        "en-light",
        "zh-dark",
        "zh-light",
        "js-disabled",
        "composer-failed",
        "composer-pending",
    }
    assert browser["pass"] is True
    assert all(row["pass"] and row["behavior"]["pass"] for row in browser["states"])
    projection = browser["owner_projection_matrix"]
    assert projection["contract"] == {
        "markets_in_receipt": 1,
        "languages": ["en", "zh"],
        "themes": ["dark", "light"],
        "viewport_widths": [390, 1440],
        "owner_cases": ["normal", "watch-only", "null-buy"],
        "primary_modes": ["loaded", "js-disabled"],
        "degraded_control_owner_case": "watch-only",
        "degraded_control_modes": ["composer-failed", "composer-pending"],
        "browser_motion_preference": "reduce",
        "screenshot_animation_policy": "disabled",
        "screenshot_caret_policy": "hide",
        "expected_primary_cases": 48,
        "expected_degraded_control_cases": 16,
        "expected_total_cases": 64,
        "expected_loaded_watch_only_screenshots": 8,
    }
    assert projection["primary_passed"] == 48
    assert projection["degraded_controls_passed"] == 16
    assert projection["screenshot_count"] == 8
    assert projection["pass"] is True
    assert len(projection["cases"]) == 64
    assert all(row["pass"] for row in projection["cases"])
    assert len(projection["theme_art_direction_pairs"]) == 4
    assert all(row["pass"] for row in projection["theme_art_direction_pairs"])

    overlay = projection["membership_overlay"]
    assert overlay == fixture["markets"][market]["diagnostic_membership_overlay"]
    normal_loaded = [
        row
        for row in projection["cases"]
        if row["proof_set"] == "primary"
        and row["owner_case"] == "normal"
        and row["mode"] == "loaded"
    ]
    assert len(normal_loaded) == 8
    assert all(row["transition"]["attempted"] for row in normal_loaded)
    assert all(row["transition"]["pass"] for row in normal_loaded)
    assert all(row["transition"]["source_unchanged"] for row in normal_loaded)
    assert all(row["transition"]["card_identity_unchanged"] for row in normal_loaded)
    assert all(row["transition"]["table_identity_unchanged"] for row in normal_loaded)
    assert all(row["transition"]["watch_identity_unchanged"] for row in normal_loaded)

    no_interaction = [
        row
        for row in projection["cases"]
        if row not in normal_loaded
    ]
    assert all(not row["transition"]["attempted"] for row in no_interaction)
    watch_loaded = [
        row
        for row in projection["cases"]
        if row["owner_case"] == "watch-only" and row["mode"] == "loaded"
    ]
    assert len(watch_loaded) == 8
    for row in watch_loaded:
        zero = row["owner_zero_projection"]
        assert zero["pass"] is True
        if market == "ca":
            assert zero["exercised"] is True
            assert zero["initial_source"] == "top"
            assert zero["initial_top_empty"]["visible"] is True
            assert zero["explicit_all"]["selected_source"] == "all"
            assert zero["explicit_all"]["grid_empty"]["visible"] is False
        else:
            assert zero["exercised"] is False
            assert zero["explicit_all"]["selected_source"] == "all"
            assert zero["explicit_all"]["grid_empty"]["visible"] is False
        screenshot = row["screenshot"]
        expected_name = (
            f"owner-empty-{market}-watch-only-{row['locale']}-"
            f"{row['theme']}-{row['viewport']['width']}.png"
        )
        assert screenshot["filename"] == expected_name
        assert screenshot["path"] == (
            "mockups/evidence/prophet-p0b-zero-fouc/" + expected_name
        )
        assert screenshot["width"] == row["viewport"]["width"]
        assert _sha256(ROOT / screenshot["path"]) == screenshot["sha256"]

    null_cases = [
        row for row in projection["cases"] if row["owner_case"] == "null-buy"
    ]
    assert len(null_cases) == 16
    assert all(row["initial"]["source_owner_state"] == "unavailable" for row in null_cases)
    expected_initial_source = "all" if market == "hk" else "top"
    states = {row["state"]: row for row in browser["states"]}
    for row in states.values():
        behavior = row["behavior"]
        source = behavior["source_contract"]
        assert source["pass"] is True
        assert source["initial_source"] == expected_initial_source
        assert source["active_source"] == expected_initial_source
        assert source["selected_source"] == expected_initial_source
        assert source["visible_grid"] == source["expected_grid"]
        assert "actionable cards shown" in source["result_copy"]
        assert "current names" in source["result_copy"]
        assert behavior["prophet_chrome"] == {
            "title_count": 1,
            "result_count": 1,
            "owner_context_count": 1,
            "vintage_count": 1,
            "help_count": 1,
            "legacy_view_count": 0,
            "pass": True,
        }
        view_owner = behavior["view_owner"]
        assert view_owner["control_count"] == 1
        assert view_owner["button_count"] == 2
        assert view_owner["selected"] == "grid"
        assert view_owner["pass"] is True

        wtaon = behavior["wtaon"]
        assert wtaon["selected_lane_key"] == "buy"
        assert wtaon["button_count"] == 4
        assert wtaon["visible_lane_body_count"] == 1
        assert set(wtaon["per_lane_owner_count"]) == {"buy", "near", "wait", "avoid"}
        assert wtaon["rendered_visible_row_count"] >= 0
        assert isinstance(wtaon["expanded"], bool)
        loaded = row["composer"] == "loaded" and row["javascript_enabled"] is True
        assert wtaon["enhanced"] is loaded
        assert wtaon["selector_count"] == (1 if loaded else 0)
        assert wtaon["aria_controls"] == (
            {"unique": 4, "valid": True}
            if loaded
            else {"unique": 0, "valid": False}
        )
        hashes = wtaon["identity_hashes"]
        assert re.fullmatch(r"[0-9a-f]{64}", hashes["before"])
        assert hashes["after"] == hashes["before"]
        identity = wtaon["node_identity"]
        assert identity["pass"] is True
        if row["javascript_enabled"]:
            assert identity["captured"] is True
            assert identity["captured_before_composer"] is True
            assert identity["same_host"] is True
            assert identity["same_controls"] is True
            assert identity["same_lanes"] is True
            assert identity["same_lists"] is True
            assert identity["same_rows"] is True
            assert identity["child_list_mutations"] == 0
            assert identity["payload_hash_after"] == identity["payload_hash_before"]
        else:
            assert identity == {
                "captured": False,
                "reason": "javascript_disabled",
                "pass": True,
            }
        assert wtaon["pass"] is True

    for name in ("en-dark", "en-light", "zh-dark", "zh-light"):
        keyboard = states[name]["behavior"]["wtaon"]["focus_keyboard"]
        assert keyboard["exercised"] is True
        assert keyboard["pass"] is True
        assert keyboard["sequence"] == ["near", "avoid", "buy", "avoid", "wait"]
        assert keyboard["focus_visible"] == [True, True, True, True, True]

    for name in ("js-disabled", "composer-failed", "composer-pending"):
        behavior = states[name]["behavior"]
        wtaon = behavior["wtaon"]
        assert wtaon["focus_keyboard"]["exercised"] is False
        assert wtaon["focus_keyboard"]["focus_visible"] == []
        assert wtaon["expanded"] is False
        fallback = behavior["static_anchor_fallback"]
        assert fallback["pass"] is True
        assert [case["lane"] for case in fallback["cases"]] == [
            "buy", "near", "wait", "avoid"
        ]
        assert all(case["pass"] for case in fallback["cases"])
        assert all(case["enhanced"] is False for case in fallback["cases"])
        assert all(case["highlighted_control"] == case["lane"] for case in fallback["cases"])
        assert all(case["owner_count"] == case["owner_row_count"] for case in fallback["cases"])
        assert all(case["semantics"]["container_role"] is None for case in fallback["cases"])
        assert all(
            all(value is None for value in case["semantics"][field])
            for case in fallback["cases"]
            for field in ("tab_roles", "aria_selected", "aria_current", "aria_controls")
        )

    fragment = browser["fragment_navigation"]
    assert fragment["pass"] is True
    assert [case["label"] for case in fragment["cases"]] == [
        "direct-valid", "click-with-fragment", "second-click", "back", "forward", "direct-invalid"
    ]
    assert all(case["pass"] for case in fragment["cases"])
    assert fragment["console_exceptions"] == []
    assert fragment["node_identity"]["valid_page"]["pass"] is True
    assert fragment["node_identity"]["invalid_page"]["pass"] is True

    expansion = browser["expansion_reachability"]
    assert expansion["pass"] is True
    assert expansion["expected_cases"] == 8
    assert expansion["passed_cases"] == 8
    assert len(expansion["cases"]) == 8
    assert {
        (case["viewport_width"], case["mode"])
        for case in expansion["cases"]
    } == {
        (width, mode)
        for width in (390, 1440)
        for mode in ("js-disabled", "composer-failed", "composer-pending", "loaded")
    }
    for case in expansion["cases"]:
        assert case["market"] == market
        assert case["pass"] is True
        assert case["console_exceptions"] == []
        for phase, visible, opened in (
            ("before", 3, False),
            ("after_click", 4, True),
            ("after_click_close", 3, False),
            ("after_enter", 4, True),
            ("after_enter_close", 3, False),
            ("after_space", 4, True),
        ):
            observed = case[phase]
            assert observed["total"] == 4
            assert observed["visible"] == visible
            assert observed["rich_rows"] == 4
            assert observed["disclosure_count"] == 1
            assert observed["disclosure_open"] is opened
            assert observed["summary_tag"] == "SUMMARY"
            assert observed["other_open_count"] == 0
            assert observed["same_lane"] is True
            assert observed["same_disclosure"] is True
            assert observed["same_summary"] is True
            assert observed["same_rows"] is True
            assert observed["same_payload"] is True
            assert observed["child_list_mutations"] == 0
            assert observed["document_width"] <= observed["viewport_width"]
            if phase != "before":
                assert observed["focus_on_summary"] is True

    for name in ("en-dark", "en-light", "zh-dark", "zh-light"):
        ownership = states[name]["behavior"]["view_all"]["ownership"]
        assert ownership == {
            "same_summary": True,
            "same_disclosure": True,
            "same_list": True,
            "same_parent": True,
            "focus_retained": True,
            "disclosure_stayed_in_lane": True,
            "list_stayed_in_lane": True,
            "global_overlay_count": 0,
        }

    disabled_view = states["js-disabled"]["behavior"]["view_owner"]
    assert disabled_view["stocktable_ready"] is False
    assert disabled_view["table_disabled"] is True
    failed_transition = states["composer-failed"]["behavior"]["view_transition"]
    assert failed_transition["pass"] is True
    assert failed_transition["visible_table"] == failed_transition["expected"]
    assert failed_transition["selected_view"] == "table"
    assert failed_transition["owner_active_view"] == "table"
    assert failed_transition["grid_restored"] is True

    desktop = browser["desktop"]
    assert desktop["pass"] is True
    assert desktop["initial"]["action_panel_height"] <= 240
    assert desktop["initial"]["prophet_top"] < 900
    assert desktop["initial"]["visible_lane_count"] == 4
    assert max(desktop["initial"]["lane_rows"].values()) <= 3
    assert desktop["initial"]["generic_showmore_attribute"] is False
    assert desktop["initial"]["generic_showmore_bar_count"] == 0
    assert desktop["initial"]["initial_source"] == expected_initial_source
    assert desktop["initial"]["selected_source"] == expected_initial_source
    assert desktop["initial"]["source_manifest"]["pass"] is True
    assert desktop["initial"]["source_manifest"]["visible"] == (
        desktop["initial"]["source_manifest"]["expected"]
    )
    assert desktop["initial"]["title_count"] == 1
    assert desktop["initial"]["result_count"] == 1
    assert desktop["initial"]["owner_context_count"] == 1
    assert desktop["initial"]["vintage_count"] == 1
    assert desktop["initial"]["help_count"] == 1
    assert desktop["initial"]["view_control_count"] == 1
    assert desktop["initial"]["legacy_view_count"] == 0
    sequence = {row["label"]: row for row in desktop["sequence"]}
    assert set(sequence) == {
        "initial-table",
        "persisted-table-startup",
        "top-grid",
        "top-table",
        "all-grid",
        "all-table",
        "group",
        "clear",
        "resized-390",
        "resized-1440",
        "legacy-class-healed",
    }
    assert all(row["pass"] for row in sequence.values())
    assert sequence["persisted-table-startup"]["persisted_view"] == "table"
    for source_name in ("top", "all"):
        grid = sequence[f"{source_name}-grid"]
        table = sequence[f"{source_name}-table"]
        assert grid["source"] == source_name
        assert table["source"] == source_name
        assert grid["visible"] == grid["expected"]
        assert table["visible"] == table["expected"]
        assert table["visible_table"] == table["expected"]
        assert grid["owner_active_view"] == "grid"
        assert table["owner_active_view"] == "table"
        assert grid["view_control_count"] == 1
        assert table["view_control_count"] == 1
    assert sequence["group"]["source_unchanged"] is True
    assert len(sequence["group"]["visible"]) == 2
    assert sequence["legacy-class-healed"]["selected_sm_hidden"] == []
    assert sequence["legacy-class-healed"]["animation_delay_residue"] is False
    if market == "ca":
        quote_cases = {row["name"]: row for row in desktop["quote_cases"]}
        expected_quote_states = {
            "missing": "unavailable",
            "malformed": "unavailable",
            "live": "live",
            "delayed": "delayed",
            "stale": "stale",
            "closed": "closed",
        }
        assert {
            name: quote_cases[name].get("state")
            for name in expected_quote_states
        } == expected_quote_states
        assert all(row["pass"] for row in quote_cases.values())
    assert all("screenshot" not in row for row in browser["states"])


# Digest-only tier of scripts/check_p0b_receipt_closure.py.  A loaded script
# may leave the browser re-mint set only while the rendered fixture gives it
# nothing to write into.  The tests below re-prove that on every run, from the
# fixture bytes and the pinned sources, so the allowlist cannot outlive its
# reasons.
DIGEST_ONLY_ASSETS = {
    "site/charts.js",
    "site/chart_i18n.js",
    "site/tablesort.js",
    "site/mtf.js",
    "site/illus.js",
}

# Every handle a digest-only script is reached through: the DOM targets it
# writes into and the globals other scripts call it by.  `ilx` is the bare
# class name (not ilx-in, ilxReveal, or hkx-ilx).
DIGEST_ONLY_TOKENS = {
    "js-plotly-plot": re.compile(r"js-plotly-plot"),
    "Plotly": re.compile(r"Plotly"),
    "__CHART_SWAP__": re.compile(r"__CHART_SWAP__"),
    "data-mtf": re.compile(r"data-mtf"),
    "hydrateMTF": re.compile(r"hydrateMTF"),
    "renderMTF": re.compile(r"renderMTF"),
    "ilxMount": re.compile(r"ilxMount"),
    "ilxReveal": re.compile(r"ilxReveal"),
    "ilx": re.compile(r"(?<![\w-])ilx(?![\w-])"),
    "data-tablesort": re.compile(r"data-tablesort"),
}

# The only pinned layout-tier sources allowed to name one.  theme.js re-themes
# Plotly divs (only when Plotly is loaded) and re-runs hydrateMTF on a theme or
# language flip; the templates replay ilx charts with ilxReveal and style the
# class.  Each is inert on the fixture because the probe below finds no target.
DIGEST_ONLY_TOKEN_ALLOWANCE = {
    "site/theme.js": {"js-plotly-plot", "Plotly", "hydrateMTF"},
    "templates/hk.html.j2": {"ilxReveal", "ilx"},
    "templates/canada.html.j2": {"ilxReveal", "ilx"},
}

TABLE_CONSTRUCTION = re.compile(r"""<table|createElement\(\s*['"]table""")


def _receipt_payloads() -> dict[str, dict]:
    return {
        name: json.loads(_read(EVIDENCE_DIR / name))
        for name in ("mobile-layout.json", "mobile-layout-canada.json")
    }


def _pinned_sources() -> set[str]:
    sources: set[str] = set()
    for payload in _receipt_payloads().values():
        for block in ("construction_inputs", "loaded_assets"):
            sources.update(
                path for path in payload[block] if path.endswith((".js", ".j2", ".html"))
            )
    return sources


def _tablesort_eligible(table) -> bool:
    """site/tablesort.js initAll's skip rules, applied to parsed fixture HTML.

    Rows are counted generously (every <tr> directly under the table or under
    any of its own <tbody>), so a doubtful table reads as eligible and reds.
    """
    node = table
    while node is not None and getattr(node, "name", None):
        if "tip" in (node.get("class") or []):
            return False
        node = node.parent
    classes = table.get("class") or []
    if "sb-table" in classes or "st-table" in classes:
        return False
    if table.get("data-tablesort") == "1":
        return False
    rows = table.find_all("tr", recursive=False)
    for body in table.find_all("tbody", recursive=False):
        rows.extend(body.find_all("tr", recursive=False))
    if table.find("thead", recursive=False) is None:
        rows = rows[1:]
    return len(rows) >= 2


@pytest.fixture(scope="module")
def rendered_fixture_pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Every page the browser receipts measure, rendered fresh from the recipe."""
    out_dir = tmp_path_factory.mktemp("p0b-digest-only-probe")
    receipt = out_dir / "rendered-fixture.json"
    run = subprocess.run(
        [
            sys.executable,
            str(FIXTURE_RECIPE),
            "--market",
            "all",
            "--out-dir",
            str(out_dir),
            "--receipt",
            str(receipt),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    outputs: set[str] = set()
    for row in payload["markets"].values():
        outputs.add(row["output"])
        outputs.update(case["output"] for case in row["owner_cases"].values())
    assert len(outputs) == 6
    return {name: (out_dir / name).read_text(encoding="utf-8") for name in sorted(outputs)}


def test_digest_only_allowlist_is_the_reviewed_set() -> None:
    """Widening the digest-only tier is a reviewed change to this suite too."""
    assert set(receipt_closure.REFRESHABLE_LOADED_ASSETS) == DIGEST_ONLY_ASSETS
    assert all(
        len(reason) > 40 for reason in receipt_closure.REFRESHABLE_LOADED_ASSETS.values()
    )
    loaded = set()
    for payload in _receipt_payloads().values():
        loaded.update(payload["loaded_assets"])
        # A digest-only asset is never also a construction input.
        assert not DIGEST_ONLY_ASSETS & set(payload["construction_inputs"])
    assert DIGEST_ONLY_ASSETS <= loaded


def test_rendered_fixture_gives_digest_only_scripts_nothing_to_touch(
    rendered_fixture_pages: dict[str, str],
) -> None:
    """Each digest-only reason, re-proved on all six measured pages."""
    for name, html in rendered_fixture_pages.items():
        soup = BeautifulSoup(html, "html.parser")
        assert soup.select(".js-plotly-plot") == [], f"{name}: charts.js / chart_i18n.js target"
        assert soup.find_all("script", src=re.compile("plotly", re.I)) == [], name
        assert soup.select("[data-mtf]") == [], f"{name}: mtf.js target"
        assert soup.select(".ilx") == [], f"{name}: illus.js target"
        eligible = [
            str(table)[:120] for table in soup.find_all("table") if _tablesort_eligible(table)
        ]
        assert eligible == [], f"{name}: tablesort.js would enhance {eligible}"


def test_tablesort_eligibility_mirror_is_not_vacuous() -> None:
    """The mirror above must call a real sortable table eligible."""
    soup = BeautifulSoup(
        "<table id=a><thead><tr><th>x</th></tr></thead><tbody>"
        "<tr><td>1</td></tr><tr><td>2</td></tr></tbody></table>"
        "<table id=b><tr><th>x</th></tr><tr><td>1</td></tr><tr><td>2</td></tr></table>"
        "<table id=c><tr><th>x</th></tr><tr><td>1</td></tr></table>"
        "<div class=tip><table id=d><tr><th>x</th></tr><tr><td>1</td></tr>"
        "<tr><td>2</td></tr></table></div>"
        "<table id=e class=st-table><thead><tr><th>x</th></tr></thead><tbody>"
        "<tr><td>1</td></tr><tr><td>2</td></tr></tbody></table>",
        "html.parser",
    )
    verdict = {t["id"]: _tablesort_eligible(t) for t in soup.find_all("table")}
    assert verdict == {"a": True, "b": True, "c": False, "d": False, "e": False}


def test_digest_only_scripts_are_reached_only_through_reviewed_handles() -> None:
    """No layout-tier source can hand a digest-only script a target unreviewed."""
    sources = _pinned_sources()
    assert DIGEST_ONLY_ASSETS <= sources
    verifier = BROWSER_RECEIPT.read_text(encoding="utf-8")
    for asset in sorted(DIGEST_ONLY_ASSETS):
        assert Path(asset).name not in verifier, f"verifier names {asset}"
    for relative in sorted(sources - DIGEST_ONLY_ASSETS):
        text = _read(ROOT / relative)
        found = {name for name, rx in DIGEST_ONLY_TOKENS.items() if rx.search(text)}
        allowed = DIGEST_ONLY_TOKEN_ALLOWANCE.get(relative, set())
        assert found <= allowed, f"{relative} names {sorted(found - allowed)}"
    # Composer tables are modal panes, built on click after tablesort's single
    # initAll pass; StockTable builds an .st-table, which tablesort skips. Any
    # other script-built table could be enhanced in the measured first frame.
    for relative in sorted(sources - DIGEST_ONLY_ASSETS):
        if not relative.startswith("site/"):
            continue
        lines = _read(ROOT / relative).splitlines()
        hits = [n for n, line in enumerate(lines) if TABLE_CONSTRUCTION.search(line)]
        if relative == "site/stocktable.js":
            assert len(hits) == 1
            assert "table.className = 'st-table';" in "\n".join(lines[hits[0] : hits[0] + 3])
            continue
        for n in hits:
            assert "modal" in lines[n], f"{relative}:{n + 1} builds a non-modal table"


def test_digest_refresh_sidecars_are_consistent() -> None:
    """Every committed sidecar is exactly what --refresh-digests would write."""
    assert receipt_closure.sidecar_findings(ROOT) == []


def test_both_receipts_were_measured_by_one_browser_build() -> None:
    """The remaining browser-dependent fields come from a single declared build."""
    payloads = list(_receipt_payloads().values())
    browsers = [payload["browser"] for payload in payloads]
    assert browsers[0] == browsers[1]
    assert set(browsers[0]) >= {"engine", "version"}
    assert browsers[0]["version"] in receipt_closure.environment_hint(ROOT)


# Inertness by execution.  The checks above re-prove the reasons in prose; the
# probe below runs each digest-only script's actual bytes under node against a
# recording model of every measured page, in both languages, through load,
# DOMContentLoaded, window load, its own exported entry points and every other
# event it listens for.  The model answers only what the fixture makes true:
# `document.querySelectorAll('table')` returns the page's real tables, every
# other query returns nothing and is re-checked against the fixture here, and
# any write to a page node, unmodelled read, new global, prototype patch or
# throw is reported.  A script edit that acts in the first frame therefore
# fails here and must drop out of REFRESHABLE_LOADED_ASSETS and re-mint.
DIGEST_ONLY_EXPORTS = {
    "site/charts.js": set(),
    "site/chart_i18n.js": set(),
    "site/tablesort.js": set(),
    "site/mtf.js": {"hydrateMTF", "renderMTF"},
    "site/illus.js": {"ilxMount", "ilxReveal"},
}
PROBE_PHASES = ["load", "DOMContentLoaded", "load-event", "reached-exports", "other-events"]
RECEIPT_PAGES = {"mobile-layout.json": "hk_", "mobile-layout-canada.json": "canada_"}

INERTNESS_PROBE = r"""'use strict';
// Runs one script's real bytes against a recording model of one rendered
// fixture page. Every read the model cannot answer truthfully, every write to
// a page node, every global the script leaves behind and every selector it
// asks for is reported; the Python side judges the report.
const vm = require('vm');
const fs = require('fs');

const BUILTIN_PROTOS = ['Array', 'Object', 'String', 'Number', 'Function', 'Promise',
  'Element', 'Node', 'EventTarget'];

function protoKeys(g) {
  const keys = {};
  for (const name of BUILTIN_PROTOS) {
    const ctor = g[name];
    if (ctor && ctor.prototype) keys[name] = Object.getOwnPropertyNames(ctor.prototype).sort().join(',');
  }
  return keys;
}

async function probe(run) {
  const rep = {page: run.page, asset: run.asset, lang: run.lang, mutations: [], unmodeled: [],
    errors: [], queries: [], exports: [], tablesTouched: 0, phases: []};
  const listeners = [];
  let timers = [];
  let readyState = 'loading';
  const htmlAttrs = Object.assign({}, run.htmlAttrs, {'data-lang': run.lang});

  // A page node: known reads answer from the fixture, writes are mutations,
  // anything else is unmodeled.
  function pageNode(label, model, extra) {
    const attrs = Object.assign({}, model.attrs || {});
    const classes = (model.classes || []).slice();
    const base = Object.assign({
      nodeType: 1,
      tagName: (model.tag || 'div').toUpperCase(),
      nodeName: (model.tag || 'div').toUpperCase(),
      id: model.id || '',
      getAttribute: (n) => (n in attrs ? attrs[n] : null),
      hasAttribute: (n) => n in attrs,
      classList: {
        contains: (c) => classes.includes(c),
        add: () => rep.mutations.push(label + '.classList.add'),
        remove: () => rep.mutations.push(label + '.classList.remove'),
        toggle: () => rep.mutations.push(label + '.classList.toggle'),
        replace: () => rep.mutations.push(label + '.classList.replace'),
      },
      closest: (sel) => closest(label, model, sel),
      matches: (sel) => matchSimple(label, {tag: model.tag, classes, id: model.id}, sel),
      querySelectorAll: (sel) => { rep.queries.push({scope: label, kind: 'qsa', sel}); return []; },
      querySelector: (sel) => { rep.queries.push({scope: label, kind: 'qs', sel}); return null; },
      addEventListener: (type, fn) => listeners.push({target: label, type, fn}),
      removeEventListener: () => {},
    }, extra || {});
    for (const m of ['setAttribute', 'removeAttribute', 'toggleAttribute', 'appendChild',
      'insertBefore', 'removeChild', 'replaceChild', 'append', 'prepend', 'before', 'after',
      'remove', 'replaceWith', 'insertAdjacentHTML', 'insertAdjacentElement',
      'insertAdjacentText', 'replaceChildren', 'attachShadow', 'animate', 'focus', 'scrollIntoView']) {
      base[m] = () => rep.mutations.push(label + '.' + m);
    }
    const style = new Proxy({}, {
      get: (t, p) => (p === 'setProperty' || p === 'removeProperty'
        ? () => rep.mutations.push(label + '.style.' + p)
        : p === 'getPropertyValue' ? () => '' : typeof p === 'symbol' ? undefined : ''),
      set: (t, p) => { rep.mutations.push(label + '.style.' + String(p)); return true; },
    });
    base.style = style;
    return strict(label, base);
  }

  function strict(label, base) {
    return new Proxy(base, {
      get(t, p) {
        if (typeof p === 'symbol') return t[p];
        if (p in t) return t[p];
        rep.unmodeled.push('read ' + label + '.' + p);
        return undefined;
      },
      set(t, p, v) { rep.mutations.push('set ' + label + '.' + String(p)); t[p] = v; return true; },
      deleteProperty(t, p) { rep.mutations.push('delete ' + label + '.' + String(p)); return true; },
      defineProperty(t, p) { rep.mutations.push('define ' + label + '.' + String(p)); return true; },
    });
  }

  // Only the selector shapes these scripts use are answered: .a, tag, #id, tag.a
  function matchSimple(label, node, sel) {
    const m = /^([a-z][a-z0-9]*)?(?:\.([A-Za-z_][\w-]*))?(?:#([A-Za-z_][\w-]*))?$/.exec(sel.trim());
    if (!m || (!m[1] && !m[2] && !m[3])) {
      rep.unmodeled.push('selector ' + label + ' ' + sel);
      return false;
    }
    if (m[1] && m[1] !== (node.tag || '').toLowerCase()) return false;
    if (m[2] && !(node.classes || []).includes(m[2])) return false;
    if (m[3] && m[3] !== node.id) return false;
    return true;
  }

  function closest(label, model, sel) {
    const chain = [{tag: model.tag, classes: model.classes, id: model.id}].concat(model.ancestors || []);
    for (const node of chain) {
      if (matchSimple(label, node, sel)) return pageNode(label + '.closest(' + sel + ')', node);
    }
    return null;
  }

  function rowNodes(label, n) {
    const rows = [];
    for (let i = 0; i < n; i++) rows.push(pageNode(label + '.tr' + i, {tag: 'tr'}));
    return rows;
  }

  const tables = (run.tables || []).map((t, i) => {
    const label = 'table#' + i;
    const tHead = t.theadRows === null ? null
      : strict(label + '.tHead', {rows: rowNodes(label + '.thead', t.theadRows)});
    const tBodies = t.tbodies.map((n, k) => strict(label + '.tBodies' + k, {rows: rowNodes(label + '.tbody' + k, n)}));
    const all = [].concat(tHead ? tHead.rows : [], ...tBodies.map((b) => b.rows));
    const model = Object.assign({tag: 'table', isTable: true}, t);
    let touched = false;
    const node = pageNode(label, model, {tHead, tBodies, rows: all});
    return new Proxy(node, {get(target, p) {
      if (!touched && typeof p === 'string') { touched = true; rep.tablesTouched++; }
      return target[p];
    }});
  });

  function detached(tag) {
    const el = {
      tagName: String(tag).toUpperCase(), nodeType: 1, style: {}, dataset: {}, children: [],
      attributes: {}, textContent: '', innerHTML: '', className: '',
      classList: {add() {}, remove() {}, toggle() {}, contains: () => false},
      setAttribute(n, v) { this.attributes[n] = String(v); },
      getAttribute(n) { return n in this.attributes ? this.attributes[n] : null; },
      removeAttribute(n) { delete this.attributes[n]; },
      appendChild(c) { this.children.push(c); return c; },
      append(...c) { this.children.push(...c); },
      insertBefore(c) { this.children.push(c); return c; },
      addEventListener() {}, removeEventListener() {},
      querySelector: () => null, querySelectorAll: () => [],
    };
    return el;
  }

  const html = pageNode('html', {tag: 'html', attrs: htmlAttrs});
  const head = pageNode('head', {tag: 'head'});
  const body = pageNode('body', {tag: 'body', classes: run.bodyClasses || []});

  const document = strict('document', {
    get readyState() { return readyState; },
    documentElement: html, head, body,
    querySelectorAll(sel) {
      rep.queries.push({scope: 'document', kind: 'qsa', sel});
      return sel.trim() === 'table' ? tables.slice() : [];
    },
    querySelector(sel) { rep.queries.push({scope: 'document', kind: 'qs', sel}); return null; },
    getElementById(id) { rep.queries.push({scope: 'document', kind: 'id', sel: id}); return null; },
    getElementsByClassName(c) { rep.queries.push({scope: 'document', kind: 'class', sel: c}); return []; },
    getElementsByTagName(t) { rep.queries.push({scope: 'document', kind: 'tag', sel: t}); return []; },
    createElement: (tag) => detached(tag),
    createElementNS: (ns, tag) => detached(tag),
    createTextNode: (text) => ({nodeType: 3, textContent: String(text)}),
    createDocumentFragment: () => detached('#fragment'),
    addEventListener: (type, fn) => listeners.push({target: 'document', type, fn}),
    removeEventListener: () => {},
    write: () => rep.mutations.push('document.write'),
    writeln: () => rep.mutations.push('document.writeln'),
    open: () => rep.mutations.push('document.open'),
  });

  function observerClass(kind) {
    return class {
      constructor(cb, opts) { this.cb = cb; this.opts = opts; }
      observe(target) { rep.unmodeled.push(kind + '.observe on a page node'); }
      unobserve() {}
      disconnect() {}
      takeRecords() { return []; }
    };
  }

  const win = {
    document,
    navigator: {userAgent: 'p0b-inertness-probe', language: run.lang === 'zh' ? 'zh-CN' : 'en-US', languages: []},
    location: {href: 'https://fixture.invalid/' + run.page, pathname: '/' + run.page, search: '', hash: '', origin: 'https://fixture.invalid'},
    innerWidth: 390, innerHeight: 844, devicePixelRatio: 3,
    console: {log() {}, info() {}, warn() {}, error() {}, debug() {}},
    getComputedStyle: () => ({getPropertyValue: () => ''}),
    matchMedia: (q) => ({matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}}),
    setTimeout: (fn, ms) => { timers.push({fn, every: 0}); return timers.length; },
    clearTimeout: () => {},
    setInterval: (fn, ms) => { timers.push({fn, every: 3}); return timers.length; },
    clearInterval: () => {},
    requestAnimationFrame: (fn) => { timers.push({fn, every: 0}); return timers.length; },
    cancelAnimationFrame: () => {},
    MutationObserver: observerClass('MutationObserver'),
    IntersectionObserver: observerClass('IntersectionObserver'),
    ResizeObserver: observerClass('ResizeObserver'),
    addEventListener: (type, fn) => listeners.push({target: 'window', type, fn}),
    removeEventListener: () => {},
  };
  const absent = new Set(run.absentGlobals || []);
  const SELF = new Set(['window', 'self', 'globalThis']);
  const context = vm.createContext({});
  const ctxGlobal = vm.runInContext('this', context);
  const windowProxy = new Proxy(win, {
    has(t, p) { return p in t || SELF.has(p) || (typeof p === 'string' && absent.has(p)); },
    get(t, p) {
      if (SELF.has(p)) return windowProxy;
      if (typeof p === 'symbol') return t[p];
      if (p in t) return t[p];
      if (absent.has(p)) return undefined;
      if (p in ctxGlobal) return ctxGlobal[p];
      rep.unmodeled.push('read window.' + p);
      return undefined;
    },
    set(t, p, v) { rep.exports.push(String(p)); t[p] = v; return true; },
  });
  ctxGlobal.__win = windowProxy;
  const globalsBefore = new Set(Object.getOwnPropertyNames(ctxGlobal));
  const protosBefore = protoKeys(ctxGlobal);

  async function settle(phase) {
    rep.phases.push(phase);
    for (let round = 0; round < 20; round++) {
      await new Promise((r) => setImmediate(r));
      const due = timers;
      timers = [];
      if (!due.length) break;
      for (const t of due) {
        try { t.fn(0); } catch (e) { rep.errors.push(phase + ' timer: ' + e); }
        if (t.every > 1) timers.push({fn: t.fn, every: t.every - 1});
      }
    }
  }
  function dispatch(target, type, detail) {
    for (const l of listeners.slice()) {
      if (l.target !== target || l.type !== type) continue;
      const ev = {type, detail: detail || {}, target: target === 'window' ? windowProxy : document,
        preventDefault() {}, stopPropagation() {}};
      try { l.fn.call(ev.target, ev); } catch (e) { rep.errors.push(type + ' on ' + target + ': ' + e); }
    }
  }

  const source = fs.readFileSync(run.path, 'utf8');
  try {
    vm.runInContext('with (__win) { ' + source + '\n}', context, {filename: run.asset});
  } catch (e) {
    rep.errors.push('load: ' + e);
  }
  await settle('load');
  readyState = 'interactive';
  dispatch('document', 'DOMContentLoaded');
  await settle('DOMContentLoaded');
  readyState = 'complete';
  dispatch('window', 'load');
  await settle('load-event');
  for (const name of run.reachedExports || []) {
    if (typeof win[name] !== 'function') continue;
    for (const args of [[], [document]]) {
      try { win[name](...args); } catch (e) { rep.errors.push(name + ': ' + e); }
    }
  }
  await settle('reached-exports');
  htmlAttrs['data-lang'] = run.lang === 'zh' ? 'en' : 'zh';
  const fired = new Set(['DOMContentLoaded', 'load']);
  for (const l of listeners.slice()) {
    const key = l.target + ':' + l.type;
    if (fired.has(l.type) || fired.has(key)) continue;
    fired.add(key);
    dispatch(l.target, l.type, {lang: htmlAttrs['data-lang']});
  }
  await settle('other-events');

  for (const name of Object.getOwnPropertyNames(ctxGlobal)) {
    if (!globalsBefore.has(name)) rep.exports.push(name);
  }
  const protosAfter = protoKeys(ctxGlobal);
  for (const name of Object.keys(protosAfter)) {
    if (protosAfter[name] !== protosBefore[name]) rep.mutations.push(name + '.prototype');
  }
  rep.exports = [...new Set(rep.exports)].sort();
  return rep;
}

(async () => {
  const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
  const out = [];
  for (const run of spec.runs) out.push(await probe(run));
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(2); });
"""


def _attrs(tag) -> dict[str, str]:
    return {k: " ".join(v) if isinstance(v, list) else v for k, v in tag.attrs.items()}


def _probe_table(table) -> dict:
    ancestors = []
    node = table.parent
    while node is not None and node.name not in (None, "[document]"):
        ancestors.append({"tag": node.name, "classes": node.get("class") or [], "id": node.get("id") or ""})
        node = node.parent
    thead = table.find("thead", recursive=False)
    # html.parser adds no implicit <tbody>: a run of bare rows is one.
    tbodies, bare = [], 0
    for child in table.children:
        if child.name == "tr":
            bare += 1
        elif child.name in ("thead", "tbody", "tfoot"):
            if bare:
                tbodies.append(bare)
                bare = 0
            if child.name == "tbody":
                tbodies.append(len(child.find_all("tr", recursive=False)))
    if bare:
        tbodies.append(bare)
    return {
        "tag": "table",
        "classes": table.get("class") or [],
        "id": table.get("id") or "",
        "attrs": _attrs(table),
        "ancestors": ancestors,
        "theadRows": None if thead is None else len(thead.find_all("tr", recursive=False)),
        "tbodies": tbodies,
    }


def _digest_only_scripts(soup) -> set[str]:
    loaded = set()
    for script in soup.find_all("script", src=True):
        asset = "site/" + script["src"].split("?")[0].rsplit("/", 1)[-1]
        if asset in DIGEST_ONLY_ASSETS:
            loaded.add(asset)
    return loaded


def _probe_runs(page: str, soup, sources: dict[str, Path] | None = None) -> list[dict]:
    root = soup.find("html")
    body = soup.find("body")
    tables = [_probe_table(table) for table in soup.find_all("table")]
    return [
        {
            "page": page,
            "asset": asset,
            "lang": lang,
            "path": str((sources or {}).get(asset, ROOT / asset)),
            "htmlAttrs": _attrs(root) if root else {},
            "bodyClasses": (body.get("class") or []) if body else [],
            "tables": tables,
            # Truthful: the fixture loads no Plotly (asserted above).
            "absentGlobals": ["Plotly"],
            "reachedExports": ["hydrateMTF", "ilxMount", "ilxReveal"],
        }
        for asset in sorted(_digest_only_scripts(soup))
        for lang in ("en", "zh")
    ]


def _run_probe(runs: list[dict], tmp_path: Path) -> list[dict]:
    node = shutil.which("node")
    assert node, "node is required for the stock-dashboard code gate"
    script = tmp_path / "p0b_inertness_probe.cjs"
    script.write_text(INERTNESS_PROBE, encoding="utf-8")
    run = subprocess.run(
        [node, str(script)],
        input=json.dumps({"runs": runs}),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    reports = json.loads(run.stdout)
    assert len(reports) == len(runs)
    return reports


def _query_root(soup, scope: str):
    if scope in ("document", "html"):
        return soup
    if scope in ("head", "body"):
        return soup.find(scope)
    match = re.match(r"table#(\d+)", scope)
    return soup.find_all("table")[int(match.group(1))] if match else None


def _probe_findings(report: dict, soup) -> list[str]:
    where = f"{report['page']} {report['asset']} {report['lang']}"
    findings = [f"{where}: {kind} {item}" for kind in ("errors", "mutations", "unmodeled") for item in report[kind]]
    if report["phases"] != PROBE_PHASES:
        findings.append(f"{where}: phases {report['phases']}")
    exports = set(report["exports"])
    if exports != DIGEST_ONLY_EXPORTS[report["asset"]]:
        findings.append(f"{where}: globals {sorted(exports)}")
    for query in report["queries"]:
        if query == {"scope": "document", "kind": "qsa", "sel": "table"}:
            continue
        root = _query_root(soup, query["scope"])
        sel = query["sel"]
        try:
            if root is None:
                raise ValueError("unknown scope")
            if query["kind"] in ("qsa", "qs"):
                hits = root.select(sel)
            elif query["kind"] == "id":
                hits = soup.find_all(id=sel)
            elif query["kind"] == "class":
                hits = root.select("." + ".".join(sel.split()))
            else:
                hits = root.find_all(sel)
        except Exception as exc:  # an unanswerable query fails closed
            findings.append(f"{where}: query {query} unanswerable ({exc})")
            continue
        if hits:
            findings.append(f"{where}: query {query} matches {len(hits)} fixture node(s)")
    return findings


def test_digest_only_scripts_are_inert_on_every_measured_page(
    rendered_fixture_pages: dict[str, str], tmp_path: Path
) -> None:
    """Execute every digest-only script on every page each receipt measures."""
    soups = {name: BeautifulSoup(html, "html.parser") for name, html in rendered_fixture_pages.items()}
    # Probe coverage is exactly the receipts' digest-only loaded assets.
    for receipt, payload in _receipt_payloads().items():
        pinned = DIGEST_ONLY_ASSETS & set(payload["loaded_assets"])
        pages = [soup for name, soup in soups.items() if name.startswith(RECEIPT_PAGES[receipt])]
        assert len(pages) == 3, receipt
        for soup in pages:
            assert _digest_only_scripts(soup) == pinned, receipt
    runs = [run for name, soup in soups.items() for run in _probe_runs(name, soup)]
    assert {run["asset"] for run in runs} == DIGEST_ONLY_ASSETS
    reports = _run_probe(runs, tmp_path)
    findings = [f for report in reports for f in _probe_findings(report, soups[report["page"]])]
    assert findings == [], (
        "a digest-only script acts on the measured first frame; drop it from "
        "REFRESHABLE_LOADED_ASSETS and re-mint the browser receipts:\n" + "\n".join(findings)
    )
    # Not vacuous: tablesort walked every real table it was handed.
    for report in reports:
        if report["asset"] == "site/tablesort.js":
            assert report["tablesTouched"] == len(soups[report["page"]].find_all("table"))
    assert sum(r["tablesTouched"] for r in reports) > 0


PROBE_MUTANTS = {
    "enhances-a-measured-table": (
        "site/tablesort.js",
        lambda src: src.replace("dataRows(t).length < 2", "dataRows(t).length < 0"),
        "mutations",
    ),
    "injects-a-stylesheet": (
        "site/charts.js",
        lambda src: "document.head.appendChild(document.createElement('style'));\n" + src,
        "mutations",
    ),
    "queries-a-fixture-node": (
        "site/mtf.js",
        lambda src: "document.querySelectorAll('div');\n" + src,
        "matches",
    ),
    "claims-a-global": (
        "site/illus.js",
        lambda src: "window.StockTable = null;\n" + src,
        "globals",
    ),
    "reads-the-unmodelled-page": (
        "site/charts.js",
        lambda src: "document.body.children;\n" + src,
        "unmodeled",
    ),
    "observes-the-page": (
        "site/charts.js",
        lambda src: "new MutationObserver(function () {}).observe(document.body, {childList: true});\n" + src,
        "unmodeled",
    ),
    "writes-from-a-timer": (
        "site/mtf.js",
        lambda src: "setTimeout(function () { document.documentElement.classList.add('x'); }, 50);\n" + src,
        "mutations",
    ),
    "writes-on-language-flip": (
        "site/illus.js",
        lambda src: "document.addEventListener('langchange', function () { document.body.style.minHeight = '1px'; });\n" + src,
        "mutations",
    ),
    "patches-a-builtin": (
        "site/tablesort.js",
        lambda src: "Array.prototype.p0bProbe = 1;\n" + src,
        "mutations",
    ),
    "throws-at-load": ("site/charts.js", lambda src: "null.x;\n" + src, "errors"),
}


@pytest.mark.parametrize("mutant", sorted(PROBE_MUTANTS))
def test_inertness_probe_reds_on_a_first_frame_effect(
    mutant: str, rendered_fixture_pages: dict[str, str], tmp_path: Path
) -> None:
    """Red-first: each way a digest-only edit could reach the first frame."""
    asset, mutate, kind = PROBE_MUTANTS[mutant]
    copy = tmp_path / Path(asset).name
    copy.write_text(mutate(_read(ROOT / asset)), encoding="utf-8")
    soup = BeautifulSoup(rendered_fixture_pages["hk_stocks.html"], "html.parser")
    runs = [run for run in _probe_runs("hk_stocks.html", soup, {asset: copy}) if run["asset"] == asset]
    assert runs
    findings = [f for report in _run_probe(runs, tmp_path) for f in _probe_findings(report, soup)]
    assert any(kind in finding for finding in findings), findings


def test_visual_manifest_preserves_history_and_appends_bounded_repair() -> None:
    """The 20/64 baseline stays immutable while the owner repair binds new proof."""
    fixture_path = EVIDENCE_DIR / "rendered-fixture.json"
    manifest = json.loads(_read(EVIDENCE_DIR / "manifest.json"))
    smells = json.loads(_read(EVIDENCE_DIR / "ux-smells.json"))
    target = manifest["target"]
    assert target["kind"] == "rendered_fixture"
    assert target["proof_class"] == "browser_fixture_proof_reproducible"
    assert target["canonical_build_proof"] == "unavailable"
    assert target["production_proof"] == "none"
    assert target["fixture_receipt"] == {
        "path": "mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json",
        "sha256": "c57f03741fb89e5abd9cc5e458a491e5a464b3d0028c5fb7f39301715874f741",
    }
    assert target["rendered_pages"] == {
        "/canada_stocks.html": {
            "output": "canada_stocks.html",
            "sha256": "ca486595e978da3315ea32a0f03a578a28a54e199aa1a8b7d18e06f50c9c420f",
        },
        "/hk_stocks.html": {
            "output": "hk_stocks.html",
            "sha256": "689a64cd29e4e08c3d60f63b59fb1097bb900a0fe1167cfe82e62e6e3c5c26ea",
        },
    }
    assert smells["target"] == target
    assert manifest["totals"] == {
        "pages": 2,
        "states_attempted": 16,
        "states_captured": 16,
    }
    historical = manifest["historical_baseline"]
    assert historical == {
        "schema": "mastermind.prophet_p0b_historical_baseline.v1",
        "candidate_head": "3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86",
        "candidate_tree": "b4dd8fd9b29b4eb769239d35df2a7911e793c7ec",
        "manifest_receipt": {
            "path": "mockups/evidence/prophet-p0b-zero-fouc/manifest.json",
            "sha256": "1a9c62c5726151a76945d69a22e56e6be9b2b91a988db2bc80ec3e7a9cb273a2",
            "recovery": (
                "git show 3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86:"
                "mockups/evidence/prophet-p0b-zero-fouc/manifest.json"
            ),
        },
        "results": {
            "visual_manifest_screenshots": 16,
            "degraded_browser_screenshots": 4,
            "total_screenshots": 20,
            "hk_browser_cases": 32,
            "ca_browser_cases": 32,
            "total_browser_cases": 64,
            "pass": True,
        },
    }
    for page in manifest["pages"]:
        for state in page["states"]:
            screenshot = EVIDENCE_DIR / state["file"]
            assert screenshot.is_file()
            assert _sha256(screenshot) == state["sha256"]

    extension = manifest["repair_extension"]
    assert extension["schema"] == (
        "mastermind.prophet_p0b_owner_empty_repair_extension.v1"
    )
    assert extension["operation"] == (
        "prophet-cockpit-p0b-zero-fouc-20260904-sol-001"
    )
    assert extension["pass"] is True
    assert extension["claims"] == {
        "source_contract": "browser_fixture",
        "browser_fixture": "reproducible",
        "canonical_build": "unavailable",
        "production": "none",
    }
    assert extension["fixture_receipt"] == {
        "path": "mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json",
        "sha256": _sha256(fixture_path),
    }
    browser_receipts = {
        "hk": EVIDENCE_DIR / "mobile-layout.json",
        "ca": EVIDENCE_DIR / "mobile-layout-canada.json",
    }
    for market, receipt_path in browser_receipts.items():
        receipt = json.loads(_read(receipt_path))
        binding = extension["browser_receipts"][market]
        assert binding == {
            "path": str(receipt_path.relative_to(ROOT)),
            "sha256": _sha256(receipt_path),
            "primary_cases": 48,
            "degraded_control_cases": 16,
            "screenshots": 8,
            "pass": True,
        }
        assert receipt["owner_projection_matrix"]["pass"] is True
    assert extension["totals"] == {
        "markets": 2,
        "owner_cases_per_market": 3,
        "primary_cases": 96,
        "degraded_control_cases": 32,
        "total_cases": 128,
        "screenshots": 16,
    }
    screenshots = extension["screenshots"]
    assert len(screenshots) == 16
    assert len({row["path"] for row in screenshots}) == 16
    for row in screenshots:
        screenshot = ROOT / row["path"]
        assert re.fullmatch(
            r"owner-empty-(hk|ca)-watch-only-(en|zh)-(dark|light)-(390|1440)\.png",
            screenshot.name,
        )
        assert _sha256(screenshot) == row["sha256"]


@pytest.mark.parametrize(
    ("market", "cases", "expected"),
    (
        (
            "hk",
            [
                [3, 39, 8, 47],
                [3, 39, 8, None],
                [3, None, 8, None],
                [3, None, None, None],
                [0, 0, 8, 8],
            ],
            [
                "3 actionable cards shown · 47 current names (39 stage board + 8 watch)",
                "3 actionable cards shown · 39 stage-board names · 8 watch names · unique total unavailable",
                "3 actionable cards shown · stage board unavailable · 8 watch names",
                "3 actionable cards shown · stage board unavailable · watch unavailable",
                "0 actionable cards shown · 8 current names (0 stage board + 8 watch)",
            ],
        ),
        (
            "ca",
            [
                [3, 9, 8, 17],
                [3, 9, 8, None],
                [3, None, 8, None],
                [3, None, None, None],
                [0, 0, 8, 8],
            ],
            [
                "3 actionable cards shown · 17 current names (9 stage board + 8 watch)",
                "3 actionable cards shown · 9 stage-board names · 8 watch names · unique total unavailable",
                "3 actionable cards shown · stage board unavailable · 8 watch names",
                "3 actionable cards shown · stage board unavailable · watch unavailable",
                "0 actionable cards shown · 8 current names (0 stage board + 8 watch)",
            ],
        ),
    ),
)
def test_population_copy_never_adds_an_unknown_owner_count(
    market: str, cases: list[list[int | None]], expected: list[str]
) -> None:
    text = _read(MARKETS[market]["composer"])
    observed = _run_node_function(
        text,
        "populationCopy",
        f"console.log(JSON.stringify({json.dumps(cases)}.map(function (args) {{ return populationCopy.apply(null, args); }})));",
    )
    assert observed == expected


@pytest.mark.parametrize(
    "selector", (".ca-v36-result", ".hk-v37-result")
)
def test_complete_population_copy_wraps_on_mobile(selector: str) -> None:
    """The longer honest population read must not widen the 390px canvas."""
    css = _read(ROOT / "templates" / "stock-dashboard.css")
    rule = selector + " { width: 100%; white-space: normal; }"
    assert rule in css


def test_hk_mobile_owner_surfaces_cannot_widen_the_document() -> None:
    """The full screener becomes readable cards instead of a crushed wide table."""
    css = _read(ROOT / "templates" / "stock-dashboard.css")
    template = _read(MARKETS["hk"]["template"])
    assert ".mx-stockdash--hk .flows-grid > .flow-col { min-width: 0; }" in css
    assert ".mx-stockdash--hk #hk-screener .tbl-scroll > .sb-table" in css
    assert ".mx-stockdash--hk #hk-screener > .sb-table" in css
    assert "display: block; width: 100%; max-width: 100%; table-layout: auto;" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert "content: attr(data-label-en);" in css
    assert "content: attr(data-label-zh);" in css
    assert 'data-label-en="' in template
    assert 'data-label-zh="' in template


def test_mobile_layout_receipt_has_valid_javascript() -> None:
    node = shutil.which("node")
    assert node, "node is required for the stock-dashboard code gate"
    run = subprocess.run(
        [node, "--check", str(BROWSER_RECEIPT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert run.returncode == 0, run.stderr


def test_owner_empty_capture_disables_skia_runtime_opts() -> None:
    """Owner-empty PNGs are exact bytes. Skia runtime opts move a few
    antialiased chrome-icon pixels between otherwise identical runs, so the
    verifier has to launch Chromium with the stable-raster switches.
    """
    source = _read(BROWSER_RECEIPT)
    for flag in (
        "--disable-skia-runtime-opts",
        "--disable-partial-raster",
        "--disable-gpu",
        "--force-color-profile=srgb",
        "--disable-font-subpixel-positioning",
        "--font-render-hinting=none",
        "--disable-lcd-text",
    ):
        assert flag in source, flag
    assert "backdrop-filter:none!important" in source


@pytest.mark.parametrize("market", MARKETS)
def test_zero_cards_do_not_abort_static_shell_enhancement(market: str) -> None:
    text = _read(MARKETS[market]["composer"])
    start = re.search(r"function start\b.*?(?=\n  if \(document\.readyState)", text, re.S)
    assert start
    assert "if (!state.cards.length) return" not in start.group(0)
