"""The us_stocks.html tier gate — the split IS the boundary.

Before this fix, us_stocks.html server-rendered ALL of us_standouts.buy into
#us-stocktable-data (a JSON <script> block) and the .nbgrid card grid, while
templates/tier_preview.js only capped rows CLIENT-SIDE (anon=1, free=3). Every
row — ticker, conviction score, alpha, entry status, the whole ranked board —
was one view-source away from an anonymous visitor. docs/TIER_PREVIEW_PATTERN.md
is explicit: "Hiding rows with CSS or a JS tier check is a marketing wall, not a
gate... If the content is what you charge for, the shipped bytes have to differ."

The fix follows the ratified split (reference implementation:
templates/special_situations.html.j2 / scripts/build_site.py's _etf_gated /
_write_etf_payload): the shell bakes only `preview_rows` of us_standouts.buy
(system order preserved, never resorted); the withheld remainder renders into
site/premiumdata/us_stocks.json from the SAME partial
(templates/_us_board_cards.html.j2) the shell {% include %}s, so the two can
never drift apart.

Two layers, deliberately (mirrors tests/test_etfs_gate.py):

* the SPLIT is proven hermetically (fake rows, real templates), so the contract
  holds even before a render lane has rebaked the desk;
* the SHIPPED BYTES are then checked against the same invariant, skipping
  (loudly) until the desk has actually been rebaked in the gated shape.

Kept import-light where possible (jinja2-only template checks import nothing
from scripts.build_site); the splitter/payload-writer tests import
scripts.build_site, which pulls pandas/plotly, so those are guarded with
pytest.importorskip the same way test_etfs_gate.py's builder test is.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SHELL = ROOT / "site" / "us_stocks.html"
PAYLOAD = ROOT / "site" / "premiumdata" / "us_stocks.json"

from tests.test_dashboard_template_render import _env, _board_row, _base_vm  # noqa: E402

# A card's identity is its whole rendered body (the `<a class="pvcard …">…</a>`
# block: ticker, name, price, verb, edge, marks — everything), NOT its ticker.
# This is a single flat board (unlike the ETF/China multi-panel desks where one
# ticker legitimately appears in several boards), so ticker and row happen to
# coincide here — but keying on the full body is still what
# docs/TIER_PREVIEW_PATTERN.md's checklist step 7 requires, and it is what
# actually catches a markup regression that keys the wrong span.
CARD_ROW = re.compile(r'<a class="pvcard.*?</a>', re.S)
TICKER_ATTR = re.compile(r'data-ticker="([^"]*)"')
SCRIPT_TAG = re.compile(r'<script\b.*?</script>', re.S)


def _strip_scripts(html: str) -> str:
    """dashboard.html.j2 carries a client-side card builder (W-L1 board-state
    JS, ~line 18704) whose JS source literally contains the text
    `<a class="pvcard …" … data-ticker="'+_pvcE(c.tk)+'"` as a template-string
    literal — a real match for CARD_ROW that is not a rendered card at all.
    Strip <script> blocks before hunting for cards so JS source can never be
    mistaken for shipped markup."""
    return SCRIPT_TAG.sub("", html)


def _keys(html: str) -> list[str]:
    return [" ".join(m.group(0).split()) for m in CARD_ROW.finditer(_strip_scripts(html))]


def _candidate_card_surface(html: str) -> str:
    """A full dashboard has separate plan and candidate cards; snippets have only rows.

    Preserve the real two-population fixture. Scope membership assertions to the
    candidate grid, while _keys remains whole-document for paid-row leak controls.
    """
    clean = _strip_scripts(html)
    if "<html" not in clean.lower():
        return clean

    class CandidateGrid(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.depth = 0
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag == "div":
                if self.depth:
                    self.depth += 1
                elif dict(attrs).get("id") == "us-cand-grid":
                    self.depth = 1
            if self.depth:
                self.parts.append(self.get_starttag_text())

        def handle_endtag(self, tag):
            if self.depth:
                self.parts.append("</" + tag + ">")
                if tag == "div":
                    self.depth -= 1

        def handle_data(self, data):
            if self.depth:
                self.parts.append(data)

        def handle_startendtag(self, tag, attrs):
            if self.depth:
                self.parts.append(self.get_starttag_text())

        def handle_entityref(self, name):
            if self.depth:
                self.parts.append("&" + name + ";")

        def handle_charref(self, name):
            if self.depth:
                self.parts.append("&#" + name + ";")

    parser = CandidateGrid()
    parser.feed(clean)
    return "".join(parser.parts)


def _tickers_in(html: str) -> set[str]:
    """Tickers carried by actual server-rendered CARDS only — not any bare
    `data-ticker="…"` substring, which also appears inside inlined JS source
    (see _strip_scripts)."""
    out = set()
    for card in CARD_ROW.finditer(_candidate_card_surface(html)):
        m = TICKER_ATTR.search(card.group(0))
        if m:
            out.add(m.group(1))
    return out


# ── fixtures ────────────────────────────────────────────────────────────────
# lane path (stage=None) exercises the legacy `_render_list` construction the
# same way _base_vm's own ACME/ZEUS fixture rows do; one row (lane=None) takes
# the ungrouped branch, matching ZEUS.
_LANES = ["bottoming", "continuation", "trend", "recovery", "watch", None, "bottoming"]


def _rows(n: int = 7) -> list[dict]:
    return [_board_row(ticker=f"TIC{i}", name=f"Ticker {i} Inc",
                       lane=_LANES[i % len(_LANES)], price=10.0 + i)
            for i in range(n)]


# priority-engine path (G0.1): a row carrying `stage` flips `_sg.any` true and
# takes the stage_hd grouping + the #us-stage-filter chip bar — a different
# branch from the legacy lane path _rows() exercises above.
_STAGES = ["live", "setting_up", "ran", "basing", "blocked", "live", "setting_up"]


def _rows_with_stage(n: int = 7) -> list[dict]:
    return [_board_row(ticker=f"TIC{i}", name=f"Ticker {i} Inc",
                       lane=_LANES[i % len(_LANES)], stage=_STAGES[i % len(_STAGES)],
                       price=10.0 + i)
            for i in range(n)]


def _render_shell(us_standouts: dict, gate: dict | None) -> str:
    """The exact build_site.py override shape for the stocks-mode render call —
    vm["us_standouts"] replaced by the shallow-copied shell, `gate` added."""
    vm = _base_vm()
    vm["us_standouts"] = us_standouts
    vm["gate"] = gate
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


# ── the split (hermetic) ────────────────────────────────────────────────────

def test_split_shell_has_only_preview_rows_payload_has_exact_remainder():
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board

    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    assert gate is not None
    assert [r["ticker"] for r in shell_su["buy"]] == ["TIC0", "TIC1", "TIC2"]
    assert [r["ticker"] for r in locked] == ["TIC3", "TIC4", "TIC5", "TIC6"]
    assert gate["preview"] == 3 and gate["locked"] == 4 and gate["total"] == 7
    # the original object is untouched — vm["us_standouts"] is shared with
    # other page renders (macro.html)
    assert len(rows) == 7 and rows[0]["ticker"] == "TIC0"


def test_shell_html_contains_only_the_preview_rows():
    """End-to-end through the real template: renders dashboard.html.j2 with the
    sliced shell + gate exactly the way build_site.py's stocks-mode call does,
    and checks the shipped bytes — both surfaces named in the mission
    (#us-stocktable-data JSON and the .nbgrid card grid)."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board

    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    html = _render_shell(shell_su, gate)

    preview_tickers = {"TIC0", "TIC1", "TIC2"}
    locked_tickers = {"TIC3", "TIC4", "TIC5", "TIC6"}

    # .nbgrid card grid
    card_tickers = _tickers_in(html)
    assert card_tickers == preview_tickers, (
        f"card grid leaked/lost rows: {card_tickers ^ preview_tickers}")
    for tk in locked_tickers:
        assert tk not in html, f"{tk} is withheld content but reached the shell"

    # #us-stocktable-data JSON block
    m = re.search(r'<script type="application/json" id="us-stocktable-data">(.*?)</script>',
                  html, re.S)
    assert m, "the stocktable JSON block must still be present, just sliced"
    payload = json.loads(m.group(1))
    json_tickers = {r["ticker"] for r in payload["rows"]}
    assert json_tickers == preview_tickers, (
        f"#us-stocktable-data leaked/lost rows: {json_tickers ^ preview_tickers}")


def test_ungated_path_writes_empty_payload_and_leaves_the_board_whole():
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board, _write_us_payload

    rows = _rows(7)
    original = {"buy": rows, "eligible": 7}
    shell_su, gate, locked = _split_us_board(original, 3, gated=False)
    assert gate is None and locked == []
    assert shell_su is original, "ungated path must ship the board whole, untouched"

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        site = Path(td)
        _write_us_payload(_env(), site, gate, locked_rows=locked,
                          us_standouts=original, top_setups=None, built="2026-08-17 00:00")
        payload = json.loads((site / "premiumdata" / "us_stocks.json").read_text())
        assert payload["gated"] is False
        assert payload["rows"] == []
        assert payload["cards_html"] == ""
        assert payload["schema"] == "tier_payload.v1"
        assert payload["page"] == "us_stocks"

    # and the shell itself renders the whole board when there is no gate
    html = _render_shell(original, None)
    assert _tickers_in(html) == {f"TIC{i}" for i in range(7)}


def test_board_smaller_than_the_preview_cap_ships_whole():
    """preview_rows >= len(rows): nothing withheld, so this must ship the board
    whole rather than bake a wall over nothing — same rule the ETF board's
    "genuinely empty" branch enforces."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board

    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 100, gated=True)
    assert gate is None and locked == []
    assert shell_su["buy"] == rows


def test_us_board_gate_cfg_reads_config_yml_and_is_fail_soft():
    """Config read is fail-soft and the switch actually works — the same shape
    scripts.build_site._etf_gated() is modelled on."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _us_board_gate_cfg
    import scripts.build_site as bs

    cfg = _us_board_gate_cfg()
    assert cfg == {"gated": True, "preview_rows": 3,
                   "panels": True, "panel_preview_rows": 3}, (
        "config.yml us_board_gate must be {gated: true, preview_rows: 3, "
        "panels: true, panel_preview_rows: 3} — update this test deliberately "
        "if that switch changes")

    real_config = bs.config

    class _Boom:
        @staticmethod
        def load():
            raise RuntimeError("config unreadable")

    try:
        bs.config = _Boom()
        assert _us_board_gate_cfg() == {"gated": False, "preview_rows": 3,
                                        "panels": False,
                                        "panel_preview_rows": 3}, (
            "a config read must NEVER fail the render")
    finally:
        bs.config = real_config


# ── the leak check, keyed on the row ────────────────────────────────────────

def test_payload_cards_never_leak_into_the_shell_row_identity():
    """The mission-critical check: no withheld row's rendered body reaches the
    shell. Keyed on the row (docs/TIER_PREVIEW_PATTERN.md checklist step 7),
    paired with a coverage assertion so a markup change can never quietly turn
    this vacuous."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board, _us_board_group_items

    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    shell_html = _render_shell(shell_su, gate)

    items = _us_board_group_items(locked, sg_any=False, stage_counts=gate["stage_counts"])
    cards_html = _env().get_template("_us_board_cards.html.j2").render(
        items=items, sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={},
        rw_en="", rw_zh="")

    locked_keys = set(_keys(cards_html))
    assert locked_keys, "fixture produced no locked cards — vacuous test"
    assert len(locked_keys) == gate["locked"], (
        "row identities must cover the whole locked remainder or this check is "
        f"vacuous: keyed {len(locked_keys)} of {gate['locked']} locked rows")
    leaked = locked_keys & set(_keys(shell_html))
    assert leaked == [] or leaked == set(), f"locked rows readable in the free shell: {leaked}"


def test_the_leak_check_can_actually_see_a_duplicated_row():
    """A control, so the assertion above can never pass because the keying
    stopped matching the markup. Plant one locked row into a copy of the shell:
    it must bite (mirrors tests/test_etfs_gate.py's equivalent control)."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board, _us_board_group_items

    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    shell_html = _render_shell(shell_su, gate)

    items = _us_board_group_items(locked, sg_any=False, stage_counts=gate["stage_counts"])
    cards_html = _env().get_template("_us_board_cards.html.j2").render(
        items=items, sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={},
        rw_en="", rw_zh="")
    one_card = CARD_ROW.search(cards_html)
    assert one_card, "fixture markup changed — the card pattern no longer matches"

    planted = shell_html + one_card.group(0)
    leaked = set(_keys(cards_html)) & set(_keys(planted))
    assert leaked, "control failed to plant a detectable duplicate — the leak check is vacuous"


# ── honest totals ───────────────────────────────────────────────────────────

def test_honest_totals_survive_the_gate():
    """The Candidates census, not the retired dot-legend count, owns this total."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board
    rows = _rows(7)
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    html = _render_shell(shell_su, gate)
    candidate = html.split('id="us-candidates"', 1)[1]
    m = re.search(r'class="mx-sec-total"[^>]*>\s*<span class="l-en"><b>(\d+)</b>', candidate)
    assert m and int(m.group(1)) == 7
    assert "first 3 of 7 screened candidates" in candidate
    assert "当前显示本次筛出的 7 只候选中的前 3 只" in candidate
    for lane, true_count in (("bottoming", 2), ("continuation", 1), ("trend", 1)):
        m = re.search(r'<div class="nb-lane-hd" data-lane="' + lane
                      + r'"[^>]*>\s*<span class="l-en">[^<]* · (\d+)</span>', candidate)
        assert m and int(m.group(1)) == true_count


def test_ungated_shell_shows_the_same_true_total_the_gated_shell_does():
    rows = _rows(7)
    html = _render_shell({"buy": rows, "eligible": 7}, None)
    candidate = html.split('id="us-candidates"', 1)[1]
    m = re.search(r'class="mx-sec-total"[^>]*>\s*<span class="l-en"><b>(\d+)</b>', candidate)
    assert m and int(m.group(1)) == 7
    assert 'id="us-gate-note"' not in candidate


# ── controls stay inert while gated ─────────────────────────────────────────

def test_candidate_stage_shelves_report_full_counts_while_gated():
    """Retired stage buttons became non-interactive aggregate shelves; retain all counts."""
    rows = _rows_with_stage(7)
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    gated_html = _render_shell(shell_su, gate)
    ungated_html = _render_shell({"buy": rows, "eligible": 7}, None)
    pattern = r'<span class="cand-shelf"><b class="fig">(\d+)</b><span><span class="l-en">([^<]+)</span>'
    expected = [("2", "Live now"), ("2", "Setting up"), ("1", "Ran — don’t chase"),
                ("1", "Basing"), ("1", "Blocked")]
    assert re.findall(pattern, gated_html) == re.findall(pattern, ungated_html) == expected
    assert sum(int(n) for n, _ in expected) == gate["total"]
    assert 'id="us-gate-note"' in gated_html and 'id="us-gate-note"' not in ungated_html
    # No obsolete clickable control should advertise access to withheld cards.
    assert 'id="us-stage-filter"' not in gated_html


def test_stages_missing_from_preview_keep_counts_and_protected_headings():
    """A withheld-only stage stays in the full census and in its proper payload group."""
    rows = _rows_with_stage(7)
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board, _us_board_group_items
    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    html = _render_shell(shell_su, gate)
    missing = {r["stage"] for r in locked} - {r["stage"] for r in shell_su["buy"]}
    assert missing == {"basing", "blocked"}
    payload = _env().get_template("_us_board_cards.html.j2").render(
        items=_us_board_group_items(locked, True, gate["stage_counts"]), sg_any=True,
        bs_adj=False, xu_allfeat=False, trg_map={}, rw_en="", rw_zh="")
    for stage in missing:
        label = {"basing": "Basing", "blocked": "Blocked"}[stage]
        assert '<b class="fig">1</b><span><span class="l-en">' + label in html
        assert 'data-stage="' + stage + '"' in payload
    for row in locked:
        assert row["ticker"] not in html
        assert 'data-ticker="' + row["ticker"] + '"' in payload


def test_hydrate_recounts_the_stage_chips():
    """The baked counts describe the preview. Hydration makes the bar interactive
    over the WHOLE board, so it must re-derive them from the elements the
    data-stagef CSS actually filters — otherwise the chip states exactly the
    defect the baked counts exist to avoid."""
    rows = _rows_with_stage(7)
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board

    shell_su, gate, _ = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    html = _render_shell(shell_su, gate)

    assert "recountStageChips" in html, "hydrate path must re-derive the chip counts"
    # counted from the DOM the filter acts on, headings (which also carry
    # data-stage) excluded — not from the payload, so markup drift cannot
    # desynchronise the chip from the filtered result.
    assert "[data-stage]:not(.nb-stage-hd)" in html
    assert re.search(r"bar\.classList\.remove\('gated'\);\s*recountStageChips\(bar\)", html), (
        "the recount must run when the bar becomes interactive")


def test_tier_wall_and_hydrate_script_present_only_when_gated():
    rows = _rows(7)
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _split_us_board

    shell_su, gate, locked = _split_us_board({"buy": rows, "eligible": 7}, 3, gated=True)
    gated_html = _render_shell(shell_su, gate)
    ungated_html = _render_shell({"buy": rows, "eligible": 7}, None)

    assert 'id="us-tier-wall"' in gated_html
    assert "4 more names" in gated_html or ">4</span>" in gated_html
    assert 'id="us-tier-wall"' not in ungated_html
    assert "See plans" in gated_html and "查看方案" in gated_html
    assert 'id="us-tw-signin"' in gated_html


# ── shipped artifacts ───────────────────────────────────────────────────────

def _shipped_payload():
    if not PAYLOAD.exists():
        pytest.skip("us_stocks not yet rebaked in the gated shape "
                    "(render.yml emits site/premiumdata/us_stocks.json)")
    payload = json.loads(PAYLOAD.read_text())
    if not payload.get("gated"):
        pytest.skip("us_stocks is running ungated (config.yml us_board_gate.gated=false)")
    return payload


def test_shipped_shell_leaks_no_locked_ticker():
    payload = _shipped_payload()
    if not SHELL.exists():
        pytest.skip("site/us_stocks.html not built in this checkout")
    shell = SHELL.read_text(encoding="utf-8")
    locked_tickers = {r["ticker"] for r in payload.get("rows", []) if r.get("ticker")}
    assert locked_tickers, "a gated payload with no locked rows is a vacuous pass"
    leaked = sorted(tk for tk in locked_tickers if f'data-ticker="{tk}"' in shell)
    assert leaked == [], f"locked tickers reachable in the shipped shell: {leaked[:5]}"


def _shell_board_blocks():
    """The shell's TWO renderings of the same preview slice: the card grid
    (`data-ticker` attrs, from _us_board_cards.html.j2) and the StockTable JSON
    island (#us-stocktable-data). Both iterate `us_standouts.buy`, so in any real
    render they carry the SAME tickers in the SAME order."""
    payload = _shipped_payload()
    if not SHELL.exists():
        pytest.skip("site/us_stocks.html not built in this checkout")
    shell = SHELL.read_text(encoding="utf-8")
    cards = re.findall(r'<a class="pvcard[^"]*" href="stock\.html#[A-Z0-9.\-]+"\s*\n?\s*'
                       r'data-ticker="([^"]+)"', shell)
    start = shell.find('id="us-stocktable-data"')
    table = (re.findall(r'"ticker":\s*"([^"]+)"', shell[start:shell.find("</script>", start)])
             if start >= 0 else [])
    return payload, cards, table


def test_shipped_shell_stocktable_leaks_no_locked_ticker():
    """The card grid is not the only place the board ships. #us-stocktable-data
    serializes the SAME rows flat — ticker, conviction score, alpha, factor_z,
    sue_z, entry status — so a locked row reaching that island is the paid record
    itself in view-source, not merely a name. The `data-ticker=` assertion above
    cannot see it (the island spells the key `"ticker"`), which is exactly how the
    2026-08-18 splice shipped ONTO's full row while only the grid tripped CI."""
    payload, _cards, table = _shell_board_blocks()
    locked = {r["ticker"] for r in payload.get("rows", []) if r.get("ticker")}
    assert locked, "a gated payload with no locked rows is a vacuous pass"
    leaked = sorted(set(table) & locked)
    assert leaked == [], f"locked tickers in the shipped #us-stocktable-data: {leaked[:5]}"


def test_shipped_shell_board_blocks_agree_with_the_payload_split():
    """A GIT MERGE can publish a board no render ever produced.

    Every render lane pushes via `git pull --rebase --autostash -X theirs origin
    main`. `-X theirs` only decides CONFLICTING hunks, so when two renders of this
    page race, non-conflicting hunks from BOTH survive and git assembles a shell
    that is neither generation. Measured 2026-08-18 (33f7bdde0c3a): the grid held
    FOUR cards against the payload's own `preview: 3`, the 4th being locked row 0,
    while #us-stocktable-data still held the previous generation's three.

    No per-block leak check catches that shape on its own — each block can look
    individually plausible. The invariant that does is AGREEMENT: both blocks
    render `us_standouts.buy`, and the split guarantees its length is `preview`.
    A shell whose two board blocks disagree has been spliced, whether or not this
    particular splice happened to expose a paid row. `.gitattributes` marks these
    shells `-merge` so a rebase takes one render whole; this is the assertion that
    fails if that ever regresses."""
    payload, cards, table = _shell_board_blocks()
    assert cards == table, (
        "the shell's card grid and #us-stocktable-data disagree — the page is a "
        f"merge of two renders, not one render: grid={cards[:6]} table={table[:6]}")
    assert len(cards) == payload["preview"], (
        f"shell ships {len(cards)} board rows against payload preview="
        f"{payload['preview']} (locked={payload['locked']}, total={payload['total']})")


def test_shipped_payload_declares_the_contract():
    payload = _shipped_payload()
    assert payload["schema"] == "tier_payload.v1"
    assert payload["page"] == "us_stocks"
    assert payload["required_tier"] == "essential"
    assert payload["locked"] > 0
    assert payload["cards_html"], "payload is missing cards_html — hydration would half-restore"


# ── the serving boundary ─────────────────────────────────────────────────────

def test_us_stocks_page_is_public_and_payload_prefix_is_enforced_early():
    """us_stocks.html stays anonymous-public (docs/TIER_PREVIEW_PATTERN.md: "The
    US Stocks and Research Vault shells are likewise public acquisition
    surfaces"); the new payload rides the /premiumdata/ prefix that already
    enforces Essential+ regardless of PAYWALL_ENABLED — config/site_access.yml
    needs NO change for this gate to be real."""
    import yaml

    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text())
    assert "/us_stocks.html" in policy["public"]["exact"]
    prefixes = policy["premium"]["enforced_early"]["prefixes"]
    assert "/premiumdata/" in prefixes
    public = policy["public"]
    assert "/premiumdata/us_stocks.json" not in (public.get("exact") or [])
    assert not any(p.startswith("/premiumdata") for p in (public.get("prefixes") or []))


# ══ the four ADJACENT panels ═════════════════════════════════════════════════
# PR #5840 gated `us_standouts.buy` and nothing else. Four sibling panels on the
# same page are fed by DIFFERENT artifacts, so the board's split never reached
# them and they stayed gated only by templates/tier_preview.js — a DOM overlay,
# every row readable in view-source (measured live 2026-08-17: 24 `tr.ts-row`,
# 43 `.actitem`, 12 `.pbr-r`, 15 `.tt-names`). Plus #plv-names, a ticker ->
# company-name island built from watch u buy u leaders u laggards, which
# re-published by name every leader the leaders strip withholds.

TS_ROW = re.compile(r'<tr class="ts-row".*?</tr>', re.S)
PBR_ROW = re.compile(r'<a class="pbr-r.*?</a>', re.S)
ACT_ROW = re.compile(r'<a class="actitem.*?</a>', re.S)
TT_LIST = re.compile(r'<span class="tt-names" data-ttl="([^"]+)">(.*?)</span>\s*</div>', re.S)
TT_LOCKED = re.compile(r'<div class="tt-locked" data-ttl="([^"]+)">(.*?)</div>', re.S)


def _panel_vm(*, setups=12, leaders=11, ran=9, actnow=7, watch=6, laggards=5):
    """A view-model with every adjacent panel populated past the preview cap.

    Deliberately distinct ticker namespaces per panel (TSX/LEDX/RANX/ACTX/WCHX/
    LAGX and the ZMSFTZ tape symbols) so a leak assertion names the panel that
    leaked instead of reporting a bare 'a ticker appears twice'."""
    vm = _base_vm()
    vm["top_setups"] = {"buy": [
        {"ticker": f"TSX{i}", "name": f"Setup {i}", "sector": "Financials",
         "alpha": 1.0 + i, "sector_rank": i + 1, "sector_n": 262,
         "signal": {"tier_cascade": "T1"}, "label": "up", "alpha_entry": "pullback",
         "factor_z": 0.5, "setup": 1.2, "insider_buyers": None,
         "insider_net_mn": None, "sue_z": None} for i in range(setups)]}
    su = dict(vm["us_standouts"])
    su["buy"] = [dict(_board_row(ticker=f"BRD{i}", name=f"Board {i}"), stage="live")
                 for i in range(8)]
    su["ran"] = [{"ticker": f"RANX{i}", "name": f"Ran {i}", "pct_since": 3.0,
                  "sessions_since": 4, "anchor": "marker", "theme": None,
                  "theme_confirmed": False} for i in range(ran)]
    su["leaders"] = [{"ticker": f"LEDX{i}", "name": f"Lead {i}", "sector": "Industrials",
                      "alpha": 2.0, "off_high": -1.0, "label": "trend",
                      "entry_signal": None, "ext_z": 0.1, "theme": None,
                      "theme_confirmed": False} for i in range(leaders)]
    su["watch"] = [{"ticker": f"WCHX{i}", "name": f"Watch {i}"} for i in range(watch)]
    su["laggards"] = [{"ticker": f"LAGX{i}", "name": f"Lag {i}"} for i in range(laggards)]
    vm["us_standouts"] = su
    vm["action_board"] = {
        "buy_now": [{"kind": "sector", "ticker": f"ACTX{i}", "name": f"Act {i}",
                     "href": "x.html", "label": "L"} for i in range(actnow)],
        "buy_soon": [], "on_the_run": [], "take_profits": [], "hold": [], "avoid": []}
    vm["theme_tape"] = {"as_of": "2026-08-17", "rank_of": 8, "rows": [
        {"name": "Software", "name_zh": "软件", "rank": 1, "n_members": 60,
         "n_on_board": 6, "say_en": "act", "say_zh": "行动",
         "counts": {"live": 2, "quiet": 50},
         "members": {"live": [{"t": "ZMSFTZ"}, {"t": "ZNOWZ"}]},
         "quiet_sample": ["QQAX", "QQBX"], "quiet_more": 5}]}
    return vm


def _render_panels(vm, pgate):
    """The exact build_site override shape for the stocks-mode render call with
    the adjacent-panel gate applied — the board itself left whole, so a failure
    here can only be about the panels."""
    return _env().get_template("dashboard.html.j2").render(
        **{**vm, "gate": None, "pgate": pgate}, mode="stocks")


def _split_panels(vm, preview=3, gated=True):
    from scripts.build_site import _split_us_panels
    return _split_us_panels(vm, preview, gated=gated)


def test_every_adjacent_panel_ships_only_its_preview_slice():
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    assert pgate, "a page with every panel over the cap must produce a gate"
    html = _render_panels(vm, pgate)

    # .topsetups (fresh triggers) + .topsetups.leaders-strip share the ts-row class,
    # so the two tables are counted together against their two previews.
    assert len(TS_ROW.findall(_strip_scripts(html))) == \
        pgate["setups"]["preview"] + pgate["leaders"]["preview"]
    assert len(PBR_ROW.findall(_strip_scripts(html))) == pgate["ran"]["preview"]
    assert len(ACT_ROW.findall(_strip_scripts(html))) == pgate["actnow"]["preview"]
    # The tape's lists are REPLACED by their count, not truncated, so the slot
    # count is unchanged and what must be gone is the member markup.
    assert '<span class="tt-n">' not in html and 'class="tt-sym"' not in html

    for key, n in (("setups", 7), ("leaders", 8), ("ran", 6), ("actnow", 4)):
        assert pgate[key]["locked"] == n, (key, pgate[key])
        assert len(locked[key] if key != "actnow"
                   else [r for L in locked[key] for r in L["rows"]]) == n


def test_no_withheld_panel_row_survives_in_the_shell():
    """The split IS the gate: a withheld row must not be in the shipped bytes at
    all. Keyed on the row's own identity (its whole rendered block), not on the
    ticker — docs/TIER_PREVIEW_PATTERN.md checklist step 7."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    shell = _strip_scripts(_render_panels(vm, pgate))

    withheld = ([r["ticker"] for r in locked["setups"]]
                + [r["ticker"] for r in locked["leaders"]]
                + [r["ticker"] for r in locked["ran"]]
                + [r["ticker"] for L in locked["actnow"] for r in L["rows"]]
                + ["ZMSFTZ", "ZNOWZ", "QQAX", "QQBX"]
                + sorted(locked["plv_names"]))
    assert len(withheld) >= 30, "a vacuous fixture would pass this test for free"
    leaked = sorted({t for t in withheld if t in shell})
    assert leaked == [], f"withheld rows reachable in the shell: {leaked[:8]}"


def test_the_panel_leak_check_can_actually_see_a_leak():
    """Hermetic control for the assertion above: a shell rendered WITHOUT the gate
    must trip it, or the check is vacuous and would pass on a reopened leak."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    ungated = _strip_scripts(_render_panels(vm, None))
    withheld = ([r["ticker"] for r in locked["setups"]]
                + [r["ticker"] for r in locked["leaders"]]
                + [r["ticker"] for r in locked["ran"]]
                + [r["ticker"] for L in locked["actnow"] for r in L["rows"]]
)
    assert sorted({t for t in withheld if t in ungated}) == sorted(set(withheld)), (
        "the ungated shell must carry every row the gated one withholds — "
        "otherwise the leak assertion is testing nothing")


def test_the_payload_carries_exactly_what_the_shell_withheld():
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _render_us_panel_payload
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    blocks = _render_us_panel_payload(_env(), pgate, locked, vm)

    assert set(blocks) == {"setups_html", "leaders_html", "ran_html",
                           "actnow_html", "tape_html", "plv_names"}
    assert len(TS_ROW.findall(blocks["setups_html"])) == pgate["setups"]["locked"]
    assert len(TS_ROW.findall(blocks["leaders_html"])) == pgate["leaders"]["locked"]
    assert len(PBR_ROW.findall(blocks["ran_html"])) == pgate["ran"]["locked"]
    assert len(ACT_ROW.findall(blocks["actnow_html"])) == pgate["actnow"]["locked"]
    for tk in ("ZMSFTZ", "ZNOWZ", "QQAX", "QQBX"):
        assert tk in blocks["tape_html"]
    # The payload is rows, never chrome: shipping the panel CSS to every hydrating
    # reader is how a 500-byte block becomes a 25 KB one.
    assert "<style" not in blocks["actnow_html"]
    assert "<style" not in blocks["tape_html"]
    assert "id=\"action-board\"" not in blocks["actnow_html"]


def test_tape_payload_lists_are_byte_identical_to_the_ungated_panel():
    """The tape renders from ONE source in three shapes. If the names-only mode
    ever drifts from the panel's own markup, a hydrated reader silently gets a
    different member list from the one a full server render would have produced."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _render_us_panel_payload
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    tape_html = _render_us_panel_payload(_env(), pgate, locked, vm)["tape_html"]
    ungated = _env().get_template("_theme_tape.html.j2").render(
        theme_tape=vm["theme_tape"])

    panel = dict(TT_LIST.findall(ungated))
    paid = dict(TT_LOCKED.findall(tape_html))
    assert panel and panel.keys() == paid.keys(), (sorted(panel), sorted(paid))
    for slot, markup in panel.items():
        assert markup == paid[slot], f"tape list {slot} drifted between the two renders"


def test_panel_headings_and_counts_stay_honest():
    """State and totals are free, names are paid — every count on a gated panel
    reports the FULL list, exactly as the board's own split does."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, _ = _split_panels(vm)
    html = _render_panels(vm, pgate)

    # "Recently fired" header count = every ran row, not the three shown.
    assert f'<span class="pbr-n">{len(vm["us_standouts"]["ran"])}</span>' in html
    # Act-Now lane heading count = the whole lane.
    assert f'<span class="acth-count">{len(vm["action_board"]["buy_now"])}</span>' in html
    # The tape keeps every count on its ladder — the panel's whole argument.
    assert 'id="theme-tape"' not in html
    # The surviving tape partial still preserves its full count at its actual owner.
    tape = _env().get_template("_theme_tape.html.j2").render(
        theme_tape=vm["theme_tape"], tt_collapse_names=True)
    assert 'class="tt-quiet">50/60<' in tape
    # Each gated panel says how many names it is holding back, in both languages.
    for n in (pgate["setups"]["locked"], pgate["leaders"]["locked"], pgate["ran"]["locked"]):
        assert f'{n} more names here' in html
    assert '此处还有' in html


def test_plv_name_island_withholds_the_locked_population():
    """#plv-names is a ticker -> COMPANY NAME map over watch u buy u leaders u
    laggards. Gating the leaders strip while this island still names every leader
    would be a wall with a door beside it."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, locked = _split_panels(vm)
    html = _render_panels(vm, pgate)
    island = json.loads(re.search(r'id="plv-names">(.*?)</script>', html, re.S).group(1))

    assert not any(k.startswith(("WCHX", "LAGX")) for k in island), (
        "watch/laggard names have no panel on this page and must not ship")
    shown = {f"LEDX{i}" for i in range(pgate["leaders"]["preview"])}
    assert {k for k in island if k.startswith("LEDX")} == shown, (
        "the island must name the leaders the document shows, and only those")
    assert set(locked["plv_names"]) & set(island) == set(), (
        "no withheld label may appear on both sides of the wall")
    assert len(locked["plv_names"]) == 8 + 6 + 5, "locked leaders + watch + laggards"


def test_ungated_build_renders_the_page_exactly_as_before():
    """`panels: false` (and every host that passes no pgate at all) must produce
    byte-identical output — the switch can always be flipped back."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    overrides, pgate, locked = _split_panels(vm, gated=False)
    assert (overrides, pgate, locked) == ({}, None, {})
    assert _render_panels(vm, None) == _render_panels(vm, pgate)


def test_a_panel_at_or_under_the_cap_grows_no_wall():
    """docs/TIER_PREVIEW_PATTERN.md: a plane with nothing withheld must not grow a
    skeleton. Here that means no disclosure line and no payload block for it."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    from scripts.build_site import _render_us_panel_payload
    vm = _panel_vm(setups=2, leaders=1, ran=3, actnow=3, watch=0, laggards=0)
    _, pgate, locked = _split_panels(vm)
    assert pgate is None or not any(k in pgate for k in ("setups", "leaders", "ran", "actnow")), pgate
    if pgate:
        assert set(_render_us_panel_payload(_env(), pgate, locked, vm)) <= {"tape_html"}


def test_act_now_board_is_untouched_for_its_other_host():
    """_us_act_now_board.html.j2 is a SHARED include — sector_central.html renders
    the same board and passes no pgate. Gating one host must not thin the other."""
    ab = {"buy_now": [{"kind": "sector", "ticker": f"S{i}", "name": f"N {i}",
                       "href": "x.html", "label": "L"} for i in range(7)],
          "buy_soon": [], "on_the_run": [], "take_profits": [], "hold": [], "avoid": []}
    tpl = _env().get_template("_us_act_now_board.html.j2")
    assert len(ACT_ROW.findall(tpl.render(action_board=ab))) == 7
    assert len(ACT_ROW.findall(tpl.render(action_board=ab, pgate={"actnow": {"preview": 3}}))) == 3


def test_fold_controls_are_suppressed_while_gated_and_rebuilt_on_hydrate():
    """A "Show more (4)" button over a lane holding three rows promises content
    the document does not contain. It goes while gated and the hydration script
    rebuilds it from the rows that actually arrived."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, _ = _split_panels(vm)
    gated = _render_panels(vm, pgate)
    plain = _render_panels(vm, None)
    assert '<button class="lst-more act-more"' in plain
    assert '<button class="lst-more act-more"' not in gated
    assert "function restoreFold(" in gated
    assert "hydratePanels(payload)" in gated


def test_hydration_targets_every_panel_it_withholds():
    """Each withheld block needs a landing site, or a paying reader hydrates into a
    half-restored page and the gate reads as data loss."""
    pytest.importorskip("pandas")
    pytest.importorskip("plotly")
    vm = _panel_vm()
    _, pgate, _ = _split_panels(vm)
    html = _render_panels(vm, pgate)
    for block, target in (
            ("payload.setups_html", "#us-standouts .topsetups:not(.leaders-strip) .ts-tbl tbody"),
            ("payload.leaders_html", "#us-standouts .topsetups.leaders-strip .ts-tbl tbody"),
            ("payload.ran_html", "#us-standouts .pbr-l")):
        assert block in html and target in html
    assert "data-ab-lane" in html and ".tt-locked[data-ttl]" in html
    assert "payload.plv_names" in html and "window.__plvNames" in html
    # every act-now lane the splitter can fill must exist as a DOM id
    for _key, dest, _wrap in __import__("scripts.build_site", fromlist=["x"])._US_ACTNOW_LANES:
        assert f'id="{dest}"' in html, dest


def test_shipped_shell_leaks_no_locked_panel_row():
    payload = _shipped_payload()
    panels = payload.get("panels") or {}
    if not panels:
        pytest.skip("us_stocks not yet rebaked with the adjacent-panel gate")
    if not SHELL.exists():
        pytest.skip("site/us_stocks.html not built in this checkout")
    shell = _strip_scripts(SHELL.read_text(encoding="utf-8"))
    leaked = []
    for block in ("setups_html", "leaders_html", "ran_html", "actnow_html"):
        for m in re.finditer(r'data-tkr="([^"]+)"|href="stock\.html#([^"]+)"',
                             payload.get(block) or ""):
            tk = m.group(1) or m.group(2)
            if tk and (f'data-tkr="{tk}"' in shell or f'>{tk}</span>' in shell):
                leaked.append(tk)
    assert leaked == [], f"locked panel rows reachable in the shipped shell: {leaked[:5]}"
    for tk in (payload.get("plv_names") or {}):
        assert f'"{tk}"' not in re.search(
            r'id="plv-names">(.*?)</script>', SHELL.read_text(encoding="utf-8"), re.S).group(1)


def test_tier_preview_leaves_a_server_collapsed_tape_list_alone():
    """templates/tier_preview.js collapses `#theme-tape .tt-names` to "N names" by
    COUNTING the .tt-n spans. On a gated build those spans are not in the document,
    so an unguarded pass would rewrite a truthful "7 names" to "0 names" — and would
    stash that text, letting a later pass restore it over the names hydration just
    put back. Both halves are the same one-line guard, so both are pinned here."""
    for path in (ROOT / "templates" / "tier_preview.js", ROOT / "site" / "tier_preview.js"):
        js = path.read_text(encoding="utf-8")
        fn = js[js.index("function applyTapeMembers()"):js.index("function placeSurfaceGates(")]
        assert 'if (!list.querySelector(".tt-n")) return;' in fn, path
        # ...and it has to come BEFORE the stash, or the restore path still fires.
        assert fn.index('if (!list.querySelector(".tt-n")) return;') < \
               fn.index('list.setAttribute("data-mx-old-html"'), path


# Lossless candidate visibility must use the existing protected payload boundary.
def _candidate_visibility_vm():
    from tests.test_us_candidate_lanes import _visibility_board
    from engine.us_candidate_lanes import project_candidate_visibility
    return {"us_candidate_visibility": project_candidate_visibility(_visibility_board())}


def test_candidate_pool_split_keeps_withheld_identity_out_of_shell():
    from copy import deepcopy
    from scripts import build_site as bs
    vm = _candidate_visibility_vm()
    before = deepcopy(vm)
    overrides, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    html = _env().get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=overrides["us_candidate_visibility"], pgate=gate)
    payload = bs._render_us_panel_payload(_env(), gate, locked, vm)
    assert vm == before
    assert 'data-ticker="AAA"' in html
    assert 'data-ticker="AMD"' not in html
    assert "Advanced Micro Devices" not in html
    assert 'data-ticker="AMD"' in payload["candidate_pool_html"]
    assert "Sector display limit reached" in payload["candidate_pool_html"]
    assert "Not scored" in payload["candidate_pool_html"]
    assert gate["candidate_pool"] == {"preview": 1, "locked": 1, "total": 2}


def test_candidate_pool_payload_writer_uses_same_auth_contract(tmp_path):
    from scripts import build_site as bs
    vm = _candidate_visibility_vm()
    _, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    blocks = bs._render_us_panel_payload(_env(), gate, locked, vm)
    bs._write_us_payload(_env(), tmp_path, None, locked_rows=[], us_standouts=None,
                         top_setups=None, built="2026-09-18", pgate=gate, panel_blocks=blocks)
    data = json.loads((tmp_path / bs.US_PAYLOAD_DIR / bs.US_PAYLOAD_NAME).read_text())
    assert data["schema"] == "tier_payload.v1"
    assert data["panels"]["candidate_pool"]["locked"] == 1
    assert 'data-ticker="AMD"' in data["candidate_pool_html"]


def test_candidate_visibility_empty_and_unavailable_are_distinct():
    from engine.us_candidate_lanes import project_candidate_visibility
    env = _env()
    absent = env.get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=project_candidate_visibility(None), pgate=None)
    assert "coverage cannot be verified" in absent
    assert "No eligible candidates in this snapshot" not in absent
    board = {"as_of": "2026-09-18", "candidate_pool": {
        "pool_definition": "us_candidate_pool_v1", "as_of": "2026-09-18", "eligible": 0, "rows": []}}
    empty = env.get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=project_candidate_visibility(board), pgate=None)
    assert "No eligible candidates in this snapshot" in empty


def test_candidate_visibility_full_render_equals_split_plus_tail():
    from scripts import build_site as bs
    vm = _candidate_visibility_vm()
    overrides, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    env = _env()
    template = env.get_template("_us_candidate_pool_rows.html.j2")
    full = template.render(rows=vm["us_candidate_visibility"]["rows"])
    shell = template.render(rows=overrides["us_candidate_visibility"]["rows"])
    tail = bs._render_us_panel_payload(env, gate, locked, vm)["candidate_pool_html"]
    pattern = r'<div class="ucp-row".*?(?=<div class="ucp-row"|\Z)'
    normalize = lambda text: [" ".join(x.split()) for x in re.findall(pattern, text, re.S)]
    assert normalize(full) == normalize(shell) + normalize(tail)


def test_candidate_visibility_untrusted_labels_are_escaped():
    vm = _candidate_visibility_vm()
    row = vm["us_candidate_visibility"]["rows"][1]
    row["name"] = '<img src=x onerror="alert(1)">'
    row["ticker"] = '\"><script>alert(2)</script>'
    html = _env().get_template("_us_candidate_pool_rows.html.j2").render(rows=[row])
    assert '<img src=x' not in html
    assert '<script>alert(2)' not in html
    assert '&lt;img' in html


def test_real_dashboard_consumes_candidate_projection():
    vm = _base_vm()
    vm.update(_candidate_visibility_vm())
    vm["pgate"] = None
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")
    assert 'id="us-candidate-pool"' in html
    assert 'data-ticker="AMD"' in html


def test_candidate_hydration_is_not_a_new_data_or_permission_path():
    source = (ROOT / "templates" / "dashboard.html.j2").read_text()
    fragment = (ROOT / "templates" / "_us_candidate_pool.html.j2").read_text()
    assert "hydrateCandidatePool(payload.candidate_pool_html, payload.candidate_pool_source)" in source
    assert "root.dataset.poolHydrated === 'true'" in source
    assert "candidate-pool-hydrated" in source and "candidate-pool-hydrated" in fragment
    assert "fetch(" not in fragment
    assert "candidate_pool" not in fragment.split('<script>', 1)[1].split('</script>', 1)[0]


def test_candidate_visibility_follows_the_fresh_board_rerender():
    import ast
    from scripts import build_site as bs
    from engine.us_candidate_lanes import project_candidate_visibility
    from tests.test_us_candidate_lanes import _visibility_board
    old = _visibility_board()
    fresh = _visibility_board()
    fresh["as_of"] = fresh["candidate_pool"]["as_of"] = "2026-09-21"
    vm = {"us_standouts": old, "us_candidate_visibility": project_candidate_visibility(old)}
    module = ast.parse((ROOT / "scripts/build_site.py").read_text())
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    updates = [n for n in ast.walk(main) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                       and t.value.id == "vm" and isinstance(t.slice, ast.Constant)
                       and t.slice.value == "us_candidate_visibility" for t in n.targets)]
    assert len(updates) == 1, "fresh-board rerender must refresh the pool view exactly once"
    namespace = {"vm": vm, "_fresh_su": fresh,
                 "project_candidate_visibility": project_candidate_visibility,
                 "_fresh_candidate_visibility": project_candidate_visibility(fresh)}
    exec(compile(ast.Module(body=updates, type_ignores=[]), "<actual-rerender-assignment>", "exec"), namespace)
    override, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    blocks = bs._render_us_panel_payload(_env(), gate, locked, vm)
    assert override["us_candidate_visibility"]["as_of"] == "2026-09-21"
    assert blocks["candidate_pool_source"]["as_of"] == "2026-09-21"
    assert blocks["candidate_pool_source"]["digest"] == vm["us_candidate_visibility"]["source_digest"]


def test_candidate_membership_detector_preserves_real_plan_population():
    """The fix is structural scoping, not deleting the distinct plan fixture."""
    html = _render_shell({"buy": _rows(3), "eligible": 3}, None)
    assert _tickers_in(html) == {"TIC0", "TIC1", "TIC2"}
    all_cards = "\n".join(CARD_ROW.findall(_strip_scripts(html)))
    assert 'data-ticker="ACME"' in all_cards and 'data-ticker="ZEUS"' in all_cards
    assert set(TICKER_ATTR.findall(_candidate_card_surface(html))) == {"TIC0", "TIC1", "TIC2"}


def _actual_fresh_board_condition(prior, fresh, *, prior_view=None, fresh_view=None):
    """Execute the production rerender predicate, not a test-owned approximation."""
    import ast
    from engine.us_candidate_lanes import project_candidate_visibility
    module = ast.parse((ROOT / "scripts/build_site.py").read_text())
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    guards = []
    for node in ast.walk(main):
        if not isinstance(node, ast.If):
            continue
        for statement in node.body:
            if (isinstance(statement, ast.Assign)
                    and isinstance(statement.value, ast.Name) and statement.value.id == "_fresh_su"
                    and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                            and t.value.id == "vm" and isinstance(t.slice, ast.Constant)
                            and t.slice.value == "us_standouts" for t in statement.targets)):
                guards.append(node)
    assert len(guards) == 1
    namespace = {
        "_fresh_su": fresh,
        "_prior_as_of": prior.get("as_of"),
        "_prior_stale": prior.get("staleness") or {},
        "_fresh_candidate_visibility": fresh_view if fresh_view is not None else project_candidate_visibility(fresh),
        "vm": {"us_standouts": prior,
               "us_candidate_visibility": prior_view if prior_view is not None else project_candidate_visibility(prior)},
    }
    return bool(eval(compile(ast.Expression(guards[0].test), "<actual-rerender-predicate>", "eval"), namespace))


@pytest.mark.parametrize("change", ["reason", "membership", "unavailable"])
def test_same_session_candidate_correction_triggers_real_rerender(change):
    """A rebuilt pool can change on the SAME date with unchanged freshness metadata."""
    from copy import deepcopy
    from tests.test_us_candidate_lanes import _visibility_board
    prior = _visibility_board()
    fresh = deepcopy(prior)
    if change == "reason":
        fresh["candidate_pool"]["rows"][-1]["headline_reason"] = "event_blackout"
        fresh["candidate_pool"]["rows"][-1]["lane_reasons"] = ["event_blackout"]
    elif change == "membership":
        fresh["candidate_pool"]["rows"][-1]["ticker"] = "NEWCO"
    else:
        fresh.pop("candidate_pool")
    assert prior["as_of"] == fresh["as_of"]
    assert (prior.get("staleness") or {}) == (fresh.get("staleness") or {})
    assert _actual_fresh_board_condition(prior, fresh)


def test_identical_same_session_candidate_pool_does_not_force_rerender():
    from copy import deepcopy
    from tests.test_us_candidate_lanes import _visibility_board
    prior = _visibility_board()
    assert not _actual_fresh_board_condition(prior, deepcopy(prior))


def test_same_session_correction_reaches_both_preview_and_protected_payload():
    import ast
    from copy import deepcopy
    from scripts import build_site as bs
    from engine.us_candidate_lanes import project_candidate_visibility
    from tests.test_us_candidate_lanes import _visibility_board
    prior = _visibility_board()
    original = deepcopy(prior)
    fresh = deepcopy(prior)
    fresh["candidate_pool"]["rows"][-1]["name"] = "Corrected same-session company"
    assert _actual_fresh_board_condition(prior, fresh)
    view = project_candidate_visibility(fresh)
    vm = {"us_standouts": prior, "us_candidate_visibility": project_candidate_visibility(prior)}
    module = ast.parse((ROOT / "scripts/build_site.py").read_text())
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    updates = [node for node in ast.walk(main) if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                       and t.value.id == "vm" and isinstance(t.slice, ast.Constant)
                       and t.slice.value in ("us_standouts", "us_candidate_visibility")
                       for t in node.targets)]
    assert len(updates) == 2
    namespace = {"vm": vm, "_fresh_su": fresh, "_fresh_candidate_visibility": view}
    exec(compile(ast.Module(body=updates, type_ignores=[]), "<actual-refresh-assignments>", "exec"), namespace)
    override, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    blocks = bs._render_us_panel_payload(_env(), gate, locked, vm)
    shell = _env().get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=override["us_candidate_visibility"], pgate=gate)
    assert "Corrected same-session company" not in shell
    assert "Corrected same-session company" in blocks["candidate_pool_html"]
    assert blocks["candidate_pool_source"]["digest"] == view["source_digest"]
    assert override["us_candidate_visibility"]["source_digest"] == view["source_digest"]
    assert view["source_digest"] != project_candidate_visibility(prior)["source_digest"]
    assert prior == original  # neither a correction nor display changes historical input


def test_archive_history_summary_and_diagnostics_respect_preview_boundary():
    from copy import deepcopy
    from engine import us_candidate_lanes as pool
    from scripts import build_site as bs
    from tests.test_us_candidate_lanes import _archive_fixture
    board, records = _archive_fixture()
    before = deepcopy(board)
    view = pool.project_candidate_visibility(
        board, archive=pool.reconcile_candidate_archive(board, records[:1]))
    vm = {"us_standouts": board, "us_candidate_visibility": view}
    override, gate, locked = bs._split_us_panels(vm, 1, gated=True)
    html = _env().get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=override["us_candidate_visibility"], pgate=gate)
    assert 'data-archive-status="incomplete"' in html
    assert '1/2' in html and 'Saved history' in html and '历史记录' in html
    assert 'AMD' not in html
    blocks = bs._render_us_panel_payload(_env(), gate, locked, vm)
    assert 'AMD' in blocks['candidate_pool_html']
    assert 'No matching saved candidate record.' in blocks['candidate_pool_html']
    assert blocks['candidate_pool_source']['digest'] == view['source_digest']
    assert board == before


def test_both_real_builder_reads_use_the_canonical_archive_reader():
    import ast
    from scripts import build_site as bs
    from engine.us_candidate_lanes import project_candidate_visibility
    from tests.test_us_candidate_lanes import _archive_fixture
    board, _ = _archive_fixture()
    tree = ast.parse((ROOT / "scripts/build_site.py").read_text())
    wanted = {"us_candidate_visibility", "_fresh_candidate_visibility"}
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id in wanted
                           for target in node.targets)]
    assert len(assignments) == 2
    calls = []
    def archive_read(actual):
        calls.append(actual)
        return {"as_of": board['as_of'], "board_definition": board['board_definition'],
                "status": "incomplete", "counts": {"expected": 2, "matched": 0,
                "missing": 2, "mismatched": 0, "extra_pool_rows": 0, "duplicate_tickers": 0},
                "by_ticker": {row['ticker']: 'missing' for row in board['candidate_pool']['rows']}}
    scope = {"us_standouts": board, "_fresh_su": board,
             "project_candidate_visibility": project_candidate_visibility,
             "load_candidate_archive_status": archive_read}
    exec(compile(ast.Module(body=assignments, type_ignores=[]), "<production-archive-reads>", "exec"), scope)
    assert calls == [board, board]
    assert scope['us_candidate_visibility'] == scope['_fresh_candidate_visibility']
    assert scope['us_candidate_visibility']['archive']['counts']['matched'] == 0


def test_archive_unavailable_is_visible_without_hiding_candidates():
    from engine import us_candidate_lanes as pool
    from tests.test_us_candidate_lanes import _archive_fixture
    board, _ = _archive_fixture()
    view = pool.project_candidate_visibility(board, archive=pool.reconcile_candidate_archive(board, None))
    html = _env().get_template("_us_candidate_pool.html.j2").render(
        us_candidate_visibility=view, pgate=None)
    assert 'data-archive-status="unavailable"' in html
    assert 'AMD' in html
    assert 'Historical comparisons are not established.' in html
    assert 'candidate records match' not in html


def test_archive_recovery_alone_refreshes_the_same_day_screen():
    from engine import us_candidate_lanes as pool
    from tests.test_us_candidate_lanes import _archive_fixture
    board, records = _archive_fixture()
    old = pool.project_candidate_visibility(board, archive=pool.reconcile_candidate_archive(board, records[:1]))
    fresh = pool.project_candidate_visibility(board, archive=pool.reconcile_candidate_archive(board, records))
    assert _actual_fresh_board_condition(board, board, prior_view=old, fresh_view=fresh)
    assert not _actual_fresh_board_condition(board, board, prior_view=fresh, fresh_view=fresh)
