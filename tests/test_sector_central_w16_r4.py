"""W16 r4 — producer-faithful fixtures, guarded glyph, truth-preserving reject."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
PAGE_TPL = TEMPLATES / "sector_central.html.j2"
BOARD_TPL = TEMPLATES / "_us_act_now_board.html.j2"
BOTTOMING_TPL = TEMPLATES / "_us_bottoming_watch.html.j2"

from tests.test_sector_central_w16_r1 import (  # noqa: E402
    OPEN_VERBS_EN,
    OPEN_VERBS_ZH,
    SECTOR_STATES,
    THEME_STATES,
    _empty_board,
    _render_board,
    _render_page,
    _sector,
    _visible_pop,
)
from scripts.capture_sector_central_w16_r3_evidence import (  # noqa: E402
    populated_board,
    render_page,
)

DAY_WORD_RE = re.compile(
    r"today|tonight|yesterday|今日|今天|今晚|昨日|昨天", re.I)
# Contract-exempt: B2 null sentence + the cycle-tape date field (not copy).
EXEMPT_RE = re.compile(
    r"tonight'?s build|今晚的构建中|cyc\.meta\.today|\bvar today\b", re.I)


def _day_word_hits(text: str) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if not DAY_WORD_RE.search(line):
            continue
        if EXEMPT_RE.search(line):
            continue
        hits.append((i, line.strip()))
    return hits


def test_m1_glyph_count_zero_on_si_unchanged_on_us_stocks():
    board = populated_board()
    si = _render_board(board, host="sector_central")
    stocks = _render_board(board)
    assert si.count("&asymp;") == 0
    assert si.count("≈") == 0
    assert 'class="act-row-score' not in si
    n_themes = sum(
        1 for lane in ("buy_now", "buy_soon", "on_the_run",
                       "take_profits", "hold", "avoid")
        for row in board[lane]
        if row.get("kind") == "theme" and not row.get("validated")
    )
    assert n_themes >= 3
    assert stocks.count("&asymp;") == n_themes
    assert 'class="act-row-score' in stocks


def test_m2_populated_board_is_producer_emitted():
    board = populated_board()
    soon = board["buy_soon"][0]
    assert soon["kind"] == "sector"
    assert soon["stat_en"] == "unconfirmed — wait"
    assert soon["stat_zh"] == "未确认 — 等待"
    assert soon["chip_en"] == "WAIT"
    assert soon["stat_en"] != "clean entry"
    html = render_page(action_board=board)
    assert "clean entry" not in html
    assert "入场干净" not in html
    assert "unconfirmed — wait" in html
    assert "未确认 — 等待" in html
    bn = board["buy_now"][0]
    assert bn["kind"] == "theme"
    assert bn["reco"] == "accumulate"
    assert bn.get("clean_entry") is True
    tp = board["take_profits"][0]
    assert tp["stat_en"] == "risk check: trim"
    assert tp.get("gate_override") is True


def test_m2_wait_lane_open_verbs_include_producer_buy_phrases():
    assert "clean entry" in OPEN_VERBS_EN
    assert "入场干净" in OPEN_VERBS_ZH
    html = _visible_pop(_render_board(
        {**_empty_board(), "buy_soon": [
            _sector("BOTTOMING", lane="buy_soon",
                    tag="BOTTOMING · UNCONFIRMED — WAIT")]},
        host="sector_central"))
    for v in OPEN_VERBS_EN + OPEN_VERBS_ZH:
        assert v not in html, f"wait-lane carried {v!r}"


def test_m2_robustness_illegal_combo_is_template_dumb_not_populated():
    """A producer-impossible combo may exist only as a labeled robustness case."""
    illegal = _sector("BUY ZONE", stat_en="clean entry", stat_zh="入场干净")
    html = _visible_pop(_render_board(
        {**_empty_board(), "buy_soon": [illegal]}, host="sector_central"))
    assert "clean entry" in html
    assert any(v in html for v in OPEN_VERBS_EN)
    populated = populated_board()
    assert populated["buy_soon"][0]["stat_en"] != "clean entry"


def test_m3_states_coupled_to_producer():
    from engine.cycles import LADDER, STATE_DISPLAY
    from engine.theme_scoring import RECOS
    assert THEME_STATES == tuple(RECOS.keys())
    assert SECTOR_STATES == tuple(STATE_DISPLAY[s]["label"] for s in LADDER)


def test_m5_reject_keeps_baked_truth_in_source():
    src = PAGE_TPL.read_text(encoding="utf-8")
    fail = src[src.index("function __siBreadthFail"):src.index("function __siBoot")]
    assert "querySelector('.skel')" in fail
    compact = fail.replace(" ", "").replace("\n", "")
    assert "if(!e.querySelector('.skel'))return;" in compact
    # Baked page: values present, no skeleton in the four tiles.
    baked = _render_page(
        market_concentration={
            "verdict": "narrow", "adv": 1200, "dec": 1800, "ad_ratio": 0.67,
            "nh": 40, "nl": 90, "pct_above_200": 35.0,
        },
        baskets_as_of="2026-09-10",
    )
    chunk = baked[baked.index('id="internals-section"'):baked.index('id="sc-heatmap"')]
    assert "Narrow" in chunk
    assert "1200" in chunk
    breadth = chunk[chunk.index('id="mkt-breadth"'):chunk.index('id="mkt-breadth-sub"')]
    assert "skel" not in breadth
    asof = baked[baked.index('id="asof"'):baked.index('id="asof"') + 80]
    assert "2026-09-10" in asof
    assert "skel" not in asof
    # Skeleton page: tiles carry .skel so reject may write the cautious sentence.
    skel = _render_page()
    skel_chunk = skel[skel.index('id="internals-section"'):skel.index('id="sc-heatmap"')]
    assert "class=\"skel\"" in skel_chunk or "class='skel'" in skel_chunk
    assert "This read is being updated." in fail
    assert "该读数更新中。" in fail


def test_m1_day_words_grep_zero_on_partials():
    board_hits = _day_word_hits(BOARD_TPL.read_text(encoding="utf-8"))
    watch_hits = _day_word_hits(BOTTOMING_TPL.read_text(encoding="utf-8"))
    assert board_hits == [], board_hits
    assert watch_hits == [], watch_hits


def test_m1_day_words_grep_zero_on_host_copy():
    hits = _day_word_hits(PAGE_TPL.read_text(encoding="utf-8"))
    assert hits == [], hits


def test_m1_includer_render_only_intended_copy_deltas():
    board = populated_board()
    si = _render_board(board, host="sector_central")
    stocks = _render_board(board)
    for html in (si, stocks):
        assert "Entry confirmed today" not in html
        assert "今日已确认入场" not in html
        assert "None today" not in html
        assert "今日无" not in html
        assert "Entry confirmed" in html
        assert "已确认入场" in html
    page = render_page(action_board=None)
    assert "tonight’s close" not in page and "tonight's close" not in page
    assert "今晚收盘后再查看" not in page
    assert "next close" in page
    assert "下次收盘后再查看" in page


def test_n1_flows_footnote_does_not_repeat_heatmap_heads_up():
    from scripts.build_sector_central import _SECTOR_ZH  # noqa: F401
    build = (ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
    page = PAGE_TPL.read_text(encoding="utf-8")
    heat = page[page.index("id=\"sc-heatmap\""):page.index("id=\"sc-heatmap\"") + 800]
    assert "a heads-up, not a buy signal" in heat
    assert "A heads-up, not a buy signal." not in build


def test_m4_tri_skel_zh_cells_exist():
    from scripts.capture_sector_central_w16_r3_evidence import cell_matrix
    ids = [c["id"] for c in cell_matrix()]
    assert "tri-skel-dark-zh" in ids
    assert "tri-skel-light-zh" in ids


def test_m6_readme_writer_discloses_deselect():
    src = (ROOT / "scripts" / "capture_sector_central_w16_r3_evidence.py").read_text(
        encoding="utf-8")
    assert "1 deselected" in src
    assert "REFUSES on a sparse" in src
