"""INTL-GS-W2A (IM13 coverage) unit + render tests.

The IM16 binding holds: the matrix's six data columns, every data cell's
state+reason, the per-state legend counts and the "<cells> cells" total come
from engine.intl_global_acceptance_matrix.acceptance_matrix(...)['coverage_board']
— every assertion below recomputes from that engine output, never from typed
numbers.
"""
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine.intl_global_acceptance_matrix import acceptance_matrix  # noqa: E402
from engine.intl_global_universe import load_rights_matrix, load_universe  # noqa: E402
from engine.intl_workspace_overview import build_workspace_overviews  # noqa: E402
from lib.intl_gs_display import CAPABILITY_DISPLAY, COVERAGE_FIELDS, REASON_COPY  # noqa: E402
from lib.intl_surveillance_mount import attach_surveillance  # noqa: E402


def _fixture():
    spec = importlib.util.spec_from_file_location(
        "intl_gs_scanner_fixture_c", REPO / "tests/intl_gs_scanner_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FX = _fixture()
UNIVERSE = load_universe()
RIGHTS = load_rights_matrix()
BOARD = acceptance_matrix(UNIVERSE, RIGHTS)["coverage_board"]
DISPLAY_OF = {state: CAPABILITY_DISPLAY[state] for state in BOARD["by_state_total"]}


def _payload(tmp_path, horizon="1m", basis="usd_unhedged"):
    observations = FX.observation_set(tmp_path)
    workspace = attach_surveillance(build_workspace_overviews(None), observations=observations)
    panel = next(p for p in workspace["surveillance_panels"]
                 if p["view"] == "coverage" and p["context"]["horizon"] == horizon
                 and p["context"]["currency_basis"] == basis)
    return panel["payload"], observations


def _coverage_panel(html, horizon="1m", basis="usd_unhedged"):
    pattern = re.compile(
        r'<section class="intl-gs__panel intl-gs__view intl-gs__view--coverage"'
        r'([^>]*)>(.*?)(?=<section class="intl-gs__panel|<p><a href="#intl-legacy-research")',
        re.DOTALL)
    for attrs, body in pattern.findall(html):
        if f'data-horizon="{horizon}"' in attrs and f'data-basis="{basis}"' in attrs:
            return body
    raise AssertionError("no coverage panel")



from html.parser import HTMLParser  # noqa: E402


class _CovCells(HTMLParser):
    """Collects every .intl-gs__covcell with its attributes and inner HTML
    (nested language spans make regex parsing unreliable)."""

    def __init__(self):
        super().__init__()
        self.cells = []
        self.rows = {}
        self._depth = 0
        self._current = None
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        pairs = dict(attrs)
        classes = (pairs.get("class") or "").split()
        if self._current is None:
            if tag == "div" and "intl-gs__covrow" in classes:
                self.rows[pairs.get("data-gs-cov-row")] = pairs
            if tag == "span" and "intl-gs__covcell" in classes and "data-col" in pairs:
                self._current = {"col": pairs.get("data-col"),
                                 "state": pairs.get("data-gs-state"),
                                 "for": pairs.get("data-gs-cell-for"),
                                 "row": pairs.get("data-gs-cov-row"),
                                 "title": pairs.get("title")}
                self._chunks = []
                self._depth = 1
                return
        else:
            self._depth += 1
            self._chunks.append(self.get_starttag_text())
            if tag == "span" and "intl-gs__covcell" in classes and "data-col" in pairs:
                self._current = {"col": pairs.get("data-col"),
                                 "state": pairs.get("data-gs-state"),
                                 "for": pairs.get("data-gs-cell-for"),
                                 "row": pairs.get("data-gs-cov-row"),
                                 "title": pairs.get("title")}
                self._chunks = []
                self._depth = 1

    def handle_endtag(self, tag):
        if self._current is not None:
            self._depth -= 1
            if self._depth == 0:
                self.cells.append((self._current, "".join(self._chunks)))
                self._current = None
                self._chunks = []
            else:
                self._chunks.append("</%s>" % tag)

    def handle_data(self, data):
        if self._current is not None:
            self._chunks.append(data)


def _cov_cells(html):
    parser = _CovCells()
    parser.feed(html)
    return parser.cells


def _visible_text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---------------------------------------------------------------- A8


def test_a8_cells_total_rows_times_columns_and_legend_sums(tmp_path):
    payload, _observations = _payload(tmp_path)
    matrix = payload["matrix"]
    assert matrix["cells_total"] == BOARD["cell_total"]
    jurisdictions = len(UNIVERSE["jurisdictions"])
    assert matrix["cells_total"] == jurisdictions * len(COVERAGE_FIELDS)
    legend = payload["legend"]
    assert sum(line["count"] for line in legend) == matrix["cells_total"]
    rendered_states = {line["display_state"] for line in legend}
    for state, count in BOARD["by_state_total"].items():
        if count:
            assert CAPABILITY_DISPLAY[state] in rendered_states, state
    text = _visible_text(_coverage_panel(FX.render_production_page()))
    assert f"{matrix['cells_total']} cells" in text, text[:400]


def test_a8b_builder_asserts_legend_sum(tmp_path):
    import lib.intl_gs_coverage_view as view
    original = view._legend_lines
    def broken(by_state_total, cell_total):
        lines = original(by_state_total, cell_total)
        return lines[1:]  # drop the first state line
    view._legend_lines = broken
    try:
        import pytest as _pytest
        with _pytest.raises(AssertionError):
            view._legend_lines_checked(BOARD["by_state_total"], BOARD["cell_total"])
    finally:
        view._legend_lines = original


def test_a8c_no_percentage_no_score_anywhere(tmp_path):
    payload, _observations = _payload(tmp_path)
    text = _visible_text(_coverage_panel(FX.render_production_page()))
    assert "%" not in text.replace("100%", "")
    assert not re.search(r"\d+(\.\d+)?%", text)
    assert "score" not in text.lower()


def test_a8d_clock_only_when_a_qualified_observation_backs_the_cell(tmp_path):
    payload, observations = _payload(tmp_path)
    qualified = set()
    for observation in observations["bases"]["usd_unhedged"]:
        identity = observation["identity"]
        if identity["horizon"] == "1m" and observation["state"] == "qualified":
            qualified.add(identity["market_id"])
    cells = _cov_cells(_coverage_panel(FX.render_production_page()))
    assert cells, "no coverage cells parsed"
    clock_cells = {(cell["for"], cell["col"]) for cell, _inner in cells if cell["for"]}
    for cell, inner in cells:
        row_id, col = cell["for"], cell["col"]
        if row_id is None or row_id == "EZ":
            continue
        if col not in ("index_close", "fx_fix"):
            assert "<time" not in inner, (row_id, col)
        else:
            has_clock = "<time" in inner
            assert has_clock == (row_id in qualified), (row_id, col, has_clock)
    for market in qualified:
        for col in ("index_close", "fx_fix"):
            assert (market, col) in clock_cells, (market, col)


def test_a8e_ez_aggregate_row_and_no_data_markets(tmp_path):
    payload, _observations = _payload(tmp_path)
    matrix = payload["matrix"]
    assert "EZ" not in BOARD["cells"]
    ez = matrix["ez_row"]
    assert ez["id"] == "EZ" and ez["kind"] == "aggregate"
    assert all(cell["excluded"] for cell in ez["cells"].values())
    panel = _coverage_panel(FX.render_production_page())
    ez_cells = {cell["col"]: inner for cell, inner in _cov_cells(panel) if cell["for"] == "EZ"}
    assert set(ez_cells) == set(BOARD["columns"]), sorted(ez_cells)
    for col, inner in ez_cells.items():
        assert "<time" not in inner and "—" in inner, col
    emea = re.search(r'data-cov-group="emea".*?(?=data-cov-group="americas")', panel, re.DOTALL)
    assert emea and 'data-gs-cov-row="EZ"' in emea.group(0), "EZ must close the EMEA group"


def test_a8f_question_impact_integers_from_capabilities(tmp_path):
    payload, _observations = _payload(tmp_path)
    impact = {line["q"]: line["count"] for line in payload["impact"]}
    assert set(impact) == {1, 2, 3, 4, 5, 6}
    # every value is a recomputation from the IM16 board, never typed
    usable = {"complete", "qualified", "partial"}
    columns_of = {"equity_index_fx": ("index_close", "fx_fix"),
                  "local_rates_credit": ("yield_10y", "cds_5y"),
                  "dollar_funding_external": ("usd_funding",),
                  "us_exposure_transmission": ("us_proxy",)}
    import lib.intl_gs_coverage_view as view
    for q, capabilities in view.QUESTION_CAPABILITIES.items():
        blocked = 0
        for jid, cells in BOARD["cells"].items():
            if any(all(CAPABILITY_DISPLAY[cells[col]["state"]] not in usable
                       for col in columns_of[cap]) for cap in capabilities):
                blocked += 1
        assert impact[q] == blocked, (q, impact[q], blocked)
    # Q3 = jurisdictions whose yield/cds/funding cells are not usable (any)
    q3 = sum(1 for cells in BOARD["cells"].values()
             if any(CAPABILITY_DISPLAY[cells[col]["state"]] not in usable
                    for col in ("yield_10y", "cds_5y", "usd_funding")))
    assert impact[3] == q3
    text = _visible_text(_coverage_panel(FX.render_production_page()))
    assert f"Q3" in text and str(impact[3]) in text


def test_a8g_recovery_log_lists_unconfirmed_rows(tmp_path):
    payload, _observations = _payload(tmp_path)
    expected = {row["id"]: row for row in RIGHTS["rows"]
                if (row.get("review") or {}).get("status") != "confirmed"}
    assert expected, "the frozen matrix has unconfirmed rows today"
    ids = {line["id"] for line in payload["recovery"]}
    assert ids == set(expected)
    for line in payload["recovery"]:
        row = expected[line["id"]]
        if row.get("next_action"):
            assert row["next_action"] == line["reason"][0]
    panel = _coverage_panel(FX.render_production_page())
    for line_id in list(ids)[:4]:
        assert line_id in panel


# ---------------------------------------------------------------- A12 IM16


def test_a12_matrix_bound_to_the_im16_coverage_board(tmp_path):
    payload, _observations = _payload(tmp_path)
    matrix = payload["matrix"]
    assert [c["id"] for c in matrix["columns"]] == BOARD["columns"]
    if [f[0] for f in COVERAGE_FIELDS] != list(BOARD["columns"]):
        # recorded GAP: the IM16 column ids govern this panel
        assert set(BOARD["columns"]) == {"index_close", "fx_fix", "yield_10y",
                                         "cds_5y", "usd_funding", "us_proxy"}
    rows = {row["id"]: row for row in matrix["rows"]}
    for jid, board_row in BOARD["cells"].items():
        assert jid in rows, jid
        for col, cell in board_row.items():
            rendered = rows[jid]["cells"][col]
            assert rendered["state"] == CAPABILITY_DISPLAY[cell["state"]], (jid, col)
            assert rendered["reason_token"] == cell["reason"], (jid, col)
    panel = _coverage_panel(FX.render_production_page())
    lookup = {(cell["for"], cell["col"]): cell["state"]
              for cell, _inner in _cov_cells(panel) if cell["for"]}
    for jid, board_row in BOARD["cells"].items():
        for col, cell in board_row.items():
            assert lookup[(jid, col)] == CAPABILITY_DISPLAY[cell["state"]], (jid, col)


def test_a12b_cds_and_funding_columns_show_the_engine_state(tmp_path):
    payload, _observations = _payload(tmp_path)
    # expectation computed from the engine, never typed
    for col in ("cds_5y", "usd_funding"):
        states = {row["cells"][col]["state"] for row in payload["matrix"]["rows"]}
        board_states = {CAPABILITY_DISPLAY[cell[col]["state"]] for cell in BOARD["cells"].values()}
        assert states == board_states, col
        assert "complete" not in states and "qualified" not in states, col


def test_a12c_session_column_and_use_column(tmp_path):
    payload, _observations = _payload(tmp_path)
    rows = {row["id"]: row for row in payload["matrix"]["rows"]}
    jp = rows["JP"]
    assert jp["session"] == UNIVERSE["jurisdictions"]["JP"]["timezone"]
    usable = {"complete", "qualified", "partial"}
    for jid, row in rows.items():
        caps = row["use"]
        expected = [cap for cap, entry in UNIVERSE["jurisdictions"][jid]["capabilities"].items()
                    if CAPABILITY_DISPLAY[entry.get("state", "unavailable")] in usable]
        assert [c for c in caps if c] == expected or caps == [], (jid, caps, expected)
        if not caps:
            assert row["use_copy"] == ("Nothing admitted yet", "尚无已准入数据"), jid
    panel = _coverage_panel(FX.render_production_page())
    assert "Asia/Tokyo" in panel
    assert "Nothing admitted yet" in panel and "尚无已准入数据" in panel
    assert 'session_calendar_unadmitted' in panel
