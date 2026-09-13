"""W16 r1 — sector_central heal: honest nulls, lane-true actions, plain vocab, count truth.

Scratch-render only (SEAT RULING 4). Both language legs ride the page/board t()
macros as l-en/l-zh twins, so one render covers EN and ZH.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
PAGE_TPL = TEMPLATES / "sector_central.html.j2"
BOARD_TPL = TEMPLATES / "_us_act_now_board.html.j2"

pytest.importorskip("jinja2")
import jinja2  # noqa: E402

from engine.cycles import LADDER, STATE_DISPLAY  # noqa: E402
from engine.theme_scoring import RECOS  # noqa: E402
from scripts.build_sector_central import (  # noqa: E402
    _SECTOR_ZH,
    _flow_cell_html,
    _fmt_money_mn,
)
from scripts.build_site import _action_board_stat_chip  # noqa: E402


def _producer_open_verbs() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Buy-signal phrases the producer actually emits on chip/stat/reco.

    Wait-lane sweep uses this list so a new buy-now phrase cannot silently
    escape. Cycle-state labels (BUY ZONE / FRESH BUY) stay in OPEN_TAG and
    are checked against the visible tag, not the demoted body.
    """
    en: set[str] = set()
    zh: set[str] = set()
    for tag in ("", "HALF SIZE"):
        item: dict = {"age_short": "", "age_short_zh": ""}
        _action_board_stat_chip(
            "buy_now", {"tag": tag, "days_hi": None, "urgency": "now"}, item)
        for key, bucket in (("stat_en", en), ("chip_en", en),
                            ("stat_zh", zh), ("chip_zh", zh)):
            raw = (item.get(key) or "").strip()
            if not raw:
                continue
            bucket.add(raw.split(" · ")[0].strip())
    en.add(RECOS["enter"][0])
    en.add(RECOS["accumulate"][0])
    zh.add(RECOS["enter"][1])
    zh.add(RECOS["accumulate"][1])
    en.add("Add on pullbacks")
    zh.update({"回调时加仓", "回调加仓"})
    return tuple(sorted(en)), tuple(sorted(zh))


OPEN_VERBS_EN, OPEN_VERBS_ZH = _producer_open_verbs()
WAIT_LANES = ("buy_soon", "on_the_run")
ALL_LANES = ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid")
THEME_STATES = tuple(RECOS.keys())
SECTOR_STATES = tuple(STATE_DISPLAY[s]["label"] for s in LADDER)
LANE_TAGS = {
    "buy_soon": ("WAIT", "等待"),
    "on_the_run": ("DON'T CHASE", "勿追"),
    "take_profits": ("TRIM", "减仓"),
    "hold": ("HOLD", "持有"),
    "avoid": ("STAND ASIDE", "回避"),
}
OPEN_TAG_EN = ("BUY ZONE", "FRESH BUY", "ENTER", "ACCUMULATE", "RALLY ON")
OPEN_TAG_ZH = ("买入区", "建仓", "加仓")


def hit_in_10(rate: float) -> int:
    """SEAT RULING 5 — x-in-10 is the HIT count. Must match the page's hitIn10()."""
    n = int(round(float(rate) * 10))
    if n < 0:
        n = 0
    if n > 10:
        n = 10
    return n


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals.update(td=lambda en: en, tr=lambda en: en,
                       t=lambda en, zh="": en)
    return env


def _empty_board() -> dict:
    return {k: [] for k in ALL_LANES} | {"total": 0, "more": {}}


def _theme(reco: str = "accumulate", **over) -> dict:
    row = {
        "kind": "theme",
        "name": f"Theme {reco or 'plain'}",
        "name_zh": f"主题{reco or 'plain'}",
        "slug": f"theme-{reco or 'plain'}",
        "href": f"basket/theme_{reco or 'plain'}.html",
        "reco": reco,
        "label": reco.upper() if reco else "HOLD",
        "label_zh": {"enter": "建仓", "accumulate": "加仓", "trim": "减仓",
                     "avoid": "回避"}.get(reco, "持有"),
        "score": 72,
        "perf_20d_rel": 0.01,
        "validated": False,
    }
    row.update(over)
    return row


def _sector(label: str = "BOTTOMING", lane: str | None = None, **over) -> dict:
    row = {
        "kind": "sector",
        "name": "Financials",
        "ticker": "XLF",
        "href": "basket/us_sector_financials.html",
        "label": label,
    }
    e = {
        "tag": over.pop("tag", ""),
        "days_hi": over.pop("days", over.pop("days_hi", None)),
        "urgency": over.pop("urgency", ""),
    }
    if lane is not None:
        _action_board_stat_chip(lane, e, row)
    row.update(over)
    return row


def _render_board(board: dict, *, host: str | None = None, pgate=None,
                  locked=None, bottoming=None) -> str:
    kw = {"action_board": board}
    if host is not None:
        kw["ab_host"] = host
    if pgate is not None:
        kw["pgate"] = pgate
    if locked is not None:
        kw["ab_locked"] = locked
    if bottoming is not None:
        kw["bottoming"] = bottoming
    return _env().get_template(BOARD_TPL.name).render(**kw)


def _render_page(board: dict | None = None, **over) -> str:
    kw = dict(flows_html=None, bottoming=None, theme_context=None,
              factor_season=None, flow=None, basket_member_syms=[],
              action_board=board if board is not None else _empty_board(),
              generated_utc="2026-09-11T00:00:00Z")
    kw.update(over)
    return _env().get_template(PAGE_TPL.name).render(**kw)


def _visible_pop(html: str) -> str:
    """Popover source is hidden; still the action-verb home. Strip receipt tips."""
    html = re.sub(r'data-tip-rc-(?:en|zh)="[^"]*"', "", html)
    html = re.sub(r'data-tip-(?:en|zh)="[^"]*"', "", html)
    return html


def _row_pop_tag(html: str) -> str:
    """Outer .row-pop-tag element, both language legs."""
    m = re.search(
        r'<span class="row-pop-tag[^"]*">.*?</span>',
        html, re.S)
    if not m:
        return ""
    chunk = m.group(0)
    # 2-tuple tags wrap two inner spans; extend to the outer closer.
    if chunk.count("<span") > 1:
        start = html.index(m.group(0))
        rest = html[start:]
        m2 = re.match(
            r'<span class="row-pop-tag[^"]*"><span class="l-en">[^<]*</span>'
            r'<span class="l-zh">[^<]*</span></span>', rest)
        if m2:
            return m2.group(0)
    return chunk


# ── B1 ──────────────────────────────────────────────────────────────────────

def test_b1_missing_verdict_never_prints_mixed_en_or_zh():
    html = _render_page()
    src = html[html.index("function renderInternals"):html.index("function boot()")]
    assert "||vmap.mixed" not in src.replace(" ", "")
    assert "lanes above are unaffected" in html
    assert "广度不在今晚的构建中" in html
    assert "mx-empty" in src
    assert "empty-why" in src
    internals = html[html.index('id="internals-section"'):html.index('id="sc-heatmap"')]
    assert ">Mixed<" not in internals
    assert "No strong consensus" not in internals


def test_b1_alien_verdict_branches_to_empty_why():
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert "mc.verdict==='narrow'" in src and "mc.verdict==='broad'" in src and "mc.verdict==='mixed'" in src
    assert "lanes above are unaffected" in src
    assert "广度不在今晚的构建中" in src
    assert "||vmap.mixed" not in src.replace(" ", "")


# ── B2 ──────────────────────────────────────────────────────────────────────

def test_b2_lane_state_sweep_no_open_verb_in_wait_lanes():
    table = []
    for lane in ALL_LANES:
        for reco in THEME_STATES:
            row = _theme(reco)
            board = _empty_board()
            board[lane] = [row]
            html = _visible_pop(_render_board(board, host="sector_central"))
            hits = []
            if lane in WAIT_LANES:
                for v in OPEN_VERBS_EN + OPEN_VERBS_ZH:
                    if v in html:
                        hits.append(v)
            table.append((lane, "theme", reco, hits))
            if lane in WAIT_LANES:
                assert hits == [], f"{lane} × theme/{reco} carried open verbs {hits}"
        for label in SECTOR_STATES:
            row = _sector(label, lane=lane)
            board = _empty_board()
            board[lane] = [row]
            html = _visible_pop(_render_board(board, host="sector_central"))
            hits = []
            if lane in WAIT_LANES:
                for v in OPEN_VERBS_EN + OPEN_VERBS_ZH:
                    if v in html:
                        hits.append(v)
            table.append((lane, "sector", label, hits))
            if lane in WAIT_LANES:
                assert hits == [], f"{lane} × sector/{label} carried open verbs {hits}"
    # Stand-aside HOLD rows may keep HOLD (X8) — not in OPEN_VERBS.
    hold_html = _visible_pop(_render_board(
        {**_empty_board(), "hold": [_theme("accumulate", label="HOLD", label_zh="持有")]},
        host="sector_central"))
    assert "HOLD" in hold_html or "持有" in hold_html


def test_b2_sector_leg_tag_is_lane_word_cycle_state_in_body():
    """B2 is absolute and per-language on the SECTOR leg: the visible tag is the
    lane word; cycle state (BUY ZONE / 买入区) is body context, never the tag."""
    rows = []
    for lane, (en, zh) in LANE_TAGS.items():
        for label in SECTOR_STATES:
            board = _empty_board()
            board[lane] = [_sector(label)]
            html = _render_board(board, host="sector_central")
            tag = _row_pop_tag(html)
            tag_txt = tag.replace("&#39;", "'").replace("&amp;", "&")
            assert en in tag_txt, f"{lane} × {label}: tag missing {en!r}: {tag}"
            assert zh in tag_txt, f"{lane} × {label}: tag missing {zh!r}: {tag}"
            for v in OPEN_TAG_EN + OPEN_TAG_ZH:
                assert v not in tag, f"{lane} × {label}: open word {v!r} in tag {tag}"
            # Cycle state demoted into the popover body (stats), both legs.
            assert f'class="l-en">{label}<' in html or f">{label}<" in html
            rows.append((lane, label, en, zh))
    assert len(rows) == len(LANE_TAGS) * len(SECTOR_STATES)


def test_b2_buy_now_may_still_open():
    html = _visible_pop(_render_board(
        {**_empty_board(), "buy_now": [_theme("enter", label="ENTER", label_zh="建仓")]},
        host="sector_central"))
    assert "ENTER" in html
    assert "建仓" in html


# ── P1 ──────────────────────────────────────────────────────────────────────

def test_p1_1_no_n_or_rank_ic_at_rest_x_in_10_form():
    html = _render_page()
    grader = html[html.index("function renderGrader"):html.index("function focusDelegate")]
    assert "cross-sectional rank-IC" not in grader
    assert grader.count("rank-IC") == 1  # receipt line only
    assert "data-tip-rc-" not in grader
    assert 'class="ftr-t1-help" data-tip-en="' in grader
    assert 'data-tip-zh="' in grader
    assert "about '" in grader and " in 10" in grader
    assert "约10次中有" in grader
    assert " · n=" not in grader
    assert hit_in_10(0.55) == 6
    assert hit_in_10(0.54) == 5
    assert "Math.round(Number(rate)*10)" in html.replace(" ", "")


def test_p1_2_no_bare_las_pctile_slug_at_rest():
    src = PAGE_TPL.read_text(encoding="utf-8")
    lead = src[src.index("function leadershipStrip"):src.index("fetch('marketdata/index_leadership.json'")]
    rest = re.sub(r'data-tip-(?:en|zh)="[^"]*"', "", lead)
    assert ">LAS<" not in rest and "'LAS " not in rest and '"LAS ' not in rest
    assert "pctile" not in rest
    assert "分位" not in rest
    assert "RS level" not in rest
    assert "RS mom" not in rest
    assert "RS水平" not in rest
    assert "highest RS level" not in rest
    assert "coil✓" not in rest
    assert "coil calls held back" not in rest
    assert "蓄势信号已收敛" not in rest
    assert "Lead pace" in lead
    assert "领先节奏" in lead
    track = src[src.index("function trackBox"):src.index("function leadershipStrip")]
    assert "about " in track and " in 10" in track
    assert "约10次中有" in track
    assert "data-tip-en=" in track and "data-tip-zh=" in track
    assert "data-tip-rc-" not in track
    assert "n=" in track  # receipt, not at rest
    assert "Relative strength" in lead
    assert "相对强度" in lead
    assert "STAGE_WORD" in src


def test_p1_4_display_only_family_gone_at_four_sites():
    page = PAGE_TPL.read_text(encoding="utf-8")
    build = (ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
    assert "display only" not in page.split("Cards are ordered by the fast rotation lens")[1][:400].lower()
    assert "display-only" not in page.split("269 subsectors")[1][:200].lower()
    heat = page[page.index("Market heat"):page.index("Coincident color") + 180]
    assert "display context" not in heat
    assert "Display-only." not in build
    assert "仅作展示" not in build
    assert "a heads-up, not a buy signal" in page
    assert "仅为提示，非买入信号" in page
    # n1: flows footnote no longer repeats the heatmap's heads-up line.
    assert "A heads-up, not a buy signal." not in build
    assert "a heads-up, not a buy signal" in heat


def test_p1_3_zh_zscore_matches_plain_en():
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert "篮子自身 z 分数" not in src
    assert "篮子相对自身历史的异常程度" in src


def test_p1_5_confluence_jargon_gone_from_three_sites():
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert '<span class="l-en">Sub-industries</span>' in src
    assert "子行业汇聚" in src
    assert "Sub-industry map" in src
    assert "the confluence cross" not in src
    assert "(T1 freshest)" in src
    html = _render_page()
    rail = html[html.index('href="#confluence"'):html.index('id="si-side-asof"')]
    assert "Sub-industries" in rail
    assert ">Confluence<" not in rail


def test_p1_6_no_gate_architecture_at_rest():
    html = _render_page()
    assert "One gated read per sector" not in html
    assert "gated, graded calls" not in html
    assert "gated conviction" not in html
    assert "One scored read per sector" in html
    assert "Lanes are the only scored calls" in html
    assert "scored conviction" in html


def test_p1_7_backtested_gate_promoted_to_plain_stat():
    src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert 'stat_en = "backtested gate: trim"' not in src
    assert 'stat_zh = "回测门槛：减仓"' not in src
    assert 'stat_en = "risk check: trim"' in src
    assert 'stat_zh = "风险检查：减仓"' in src
    html = _render_board(
        {**_empty_board(), "take_profits": [
            _sector("ROLLING OVER", stat_en="risk check: trim",
                    stat_zh="风险检查：减仓", gate_override=True)]},
        host="sector_central")
    assert "backtested gate: trim" not in html
    assert "回测门槛：减仓" not in html
    assert "risk check: trim" in html
    assert "风险检查：减仓" in html


# ── P2 ──────────────────────────────────────────────────────────────────────

def test_p2_1_sp500_renders_clean():
    html = _render_page()
    assert "S&amp;amp;P 500" not in html
    # autoescape of 'S&P 500' is the clean form
    assert "S&amp;P 500" in html or "S&P 500" in html
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert "t('S&P 500'" in src
    assert "t('S&amp;P 500'" not in src


def test_p2_2_eleven_zh_sector_names():
    assert len(_SECTOR_ZH) == 11
    for zh in _SECTOR_ZH.values():
        assert any("\u4e00" <= c <= "\u9fff" for c in zh)
    assert _SECTOR_ZH["XLV"] == "医疗保健"
    assert _SECTOR_ZH["XLY"] == "非必需消费"


def test_p2_2_flow_table_emits_cjk(monkeypatch):
    from scripts import build_sector_central as B

    def fake_t(en, zh=None):
        return f"{en}|{zh if zh is not None else en}"

    monkeypatch.setattr("engine.i18n.t", fake_t)
    monkeypatch.setattr(
        "collectors.sponsors.sector_flow_periods",
        lambda: {
            "labels": ["1D"],
            "asof": "2026-09-10",
            "depth": 20,
            "net": {"1D": -5100.0},
            "rows": [
                {"ticker": t, "vals": {"1D": -100.0}}
                for t in _SECTOR_ZH
            ],
        },
    )
    html = B._flows_section_html()
    assert html is not None
    for zh in _SECTOR_ZH.values():
        assert zh in html, f"missing ZH name {zh!r}"


def test_p2_3_host_flag_sector_central_has_no_self_cta():
    board = {**_empty_board(), "buy_now": [_theme("enter")],
             "more": {"buy_now": 5}}
    html = _render_board(board, host="sector_central")
    assert "Theme reasons → Sector Intelligence" not in html
    assert "full list on Sector Intelligence" not in html
    assert "+5 more" not in html
    page = _render_page(board)
    assert "Theme reasons → Sector Intelligence" not in page
    assert "full list on Sector Intelligence" not in page


def test_p2_3_host_flag_us_stocks_unchanged():
    board = {**_empty_board(), "buy_now": [_theme("enter")],
             "more": {"buy_now": 5}}
    html = _render_board(board)  # default host = us_stocks
    assert "Theme reasons → Sector Intelligence" in html
    assert "full list on Sector Intelligence" in html
    assert "+5 more" in html
    # Permanent cross-page overflow must NOT carry .pg-more (dashboard hydration
    # would strip a correct link). The sign-in ab_more() still uses .pg-more.
    assert 'class="pg-more' not in html


def test_p2_4_watch_strip_separated_counts_untouched():
    src = BOARD_TPL.read_text(encoding="utf-8")
    assert "act-watch-strip" in src
    assert "action_board.total" in src
    assert "acth-count" in src
    # Do not change either authored integer — the composition is the fix.
    html = _render_board(
        {**_empty_board(), "total": 44, "buy_now": [_theme("enter")] * 2},
        host="sector_central",
        bottoming={"bottoming_watch": [
            {"id": "b-gold_miners", "cid": "gold_miners", "kind": "BASKET",
             "name": "Gold Miners", "name_zh": "黄金矿业", "href": "basket/x.html",
             "osc_slope": 1.3, "pos": 2.0, "cycle_signal": True,
             "gate_conflict": False}],
            "dual_read_ids": [], "recovering_ids": [],
            "bottoming_authority": {}},
    )
    assert "44" in html
    assert 'class="act-watch-strip"' in html
    assert "Bottoming watch" in html
    assert html.index("actiongrid") < html.index("act-watch-strip")
    assert "Gold Miners" in html


def test_p2_5_breadth_tiles_bake_skeleton_not_null_sentence():
    html = _render_page()
    chunk = html[html.index('id="internals-section"'):html.index('id="sc-heatmap"')]
    assert 'id="mkt-breadth">—<' not in chunk.replace(" ", "")
    assert "Not in tonight" not in chunk
    assert "不在今晚的构建中" not in chunk
    assert "class=\"skel\"" in chunk or "class='skel'" in chunk
    src = PAGE_TPL.read_text(encoding="utf-8")
    ri = src[src.index("function renderInternals"):src.index("function boot()",
             src.index("function renderInternals"))]
    assert "Not in tonight" in ri
    assert "不在今晚的构建中" in ri
    assert "lanes above are unaffected" in ri


def test_p2_5_breadth_tiles_bake_values_when_builder_has_them():
    html = _render_page(market_concentration={
        "verdict": "narrow", "adv": 1200, "dec": 1800, "ad_ratio": 0.67,
        "nh": 40, "nl": 90, "pct_above_200": 35.0,
    })
    chunk = html[html.index('id="internals-section"'):html.index('id="sc-heatmap"')]
    assert "Not in tonight" not in chunk
    assert "Narrow" in chunk and "狭窄" in chunk
    assert "1200" in chunk and "1800" in chunk
    assert ">40<" in chunk and ">90<" in chunk
    assert "35" in chunk


def test_p2_5_js_branch_map_empty_vs_reject():
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert "function __siBreadthFail" in src
    assert "This read is being updated." in src
    assert "该读数更新中。" in src
    boot = src[src.index("function __siBoot"):src.index("function __siWireTrace")]
    assert "__siBreadthFail" in boot
    ri = src[src.index("function renderInternals"):src.index("function boot()",
             src.index("function renderInternals"))]
    assert "Not in tonight" in ri
    assert "lanes above are unaffected" in ri


def test_p2_6_as_of_bakes_value_or_skeleton_unknown_only_post_resolve():
    html = _render_page()
    src = PAGE_TPL.read_text(encoding="utf-8")
    assert "BASKETS.as_of||'—'" not in src.replace(" ", "")
    asof = html[html.index('id="asof"'):html.index('id="asof"') + 280]
    assert "date unknown" not in asof
    assert "日期未知" not in asof
    assert "skel" in asof
    populated = _render_page(baskets_as_of="2026-09-10")
    asof_p = populated[populated.index('id="asof"'):populated.index('id="asof"') + 80]
    assert "2026-09-10" in asof_p
    assert "date unknown" not in asof_p
    assert "date unknown" in src and "日期未知" in src
    assert "BASKETS.as_of" in src
    fail = src[src.index("function __siBreadthFail"):src.index("function __siBoot")]
    assert "This read is being updated." in fail
    assert "getElementById('asof')" in fail
    assert "querySelector('.skel')" in fail


def test_p2_7_geometry_true_skeleton_not_empty_loading():
    html = _render_page()
    app = html[html.index('id="sc-app"'):html.index('id="sc-app"') + 600]
    assert "Loading…" not in app
    assert "加载中…" not in app
    assert 'class="empty"' not in app
    assert "sc-skel" in app
    assert "skel" in app


# ── P3 / D1 ─────────────────────────────────────────────────────────────────

def test_p3_1_exactly_one_h1():
    html = _render_page()
    assert html.lower().count("<h1") == 1
    assert "US Sector Intelligence" in html
    assert "美国行业情报" in html
    populated = _render_page(theme_context={
        "leadership": {
            "trailing_leader": {"name": "Tech", "name_zh": "科技", "id": "xlk"},
            "state": "steady", "stance_en": "Stay with leaders",
            "stance_zh": "跟随领涨", "days_in_state": 3,
            "strength": [{"name": "Health", "name_zh": "医疗", "id": "xlv"}],
        }})
    assert populated.lower().count("<h1") == 1


def test_p3_2_score_demoted_from_rest():
    html = _render_board(
        {**_empty_board(), "buy_now": [_theme("accumulate", score=72)]},
        host="sector_central")
    assert 'class="act-row-score' not in html
    assert "row-pop-score" in html
    assert ">72<" in html or ">72</strong>" in html
    assert html.count("&asymp;") == 0
    assert html.count("≈") == 0


def test_p3_2_score_kept_on_us_stocks_host():
    html = _render_board(
        {**_empty_board(), "buy_now": [_theme("accumulate", score=72)]})
    assert 'class="act-row-score' in html
    assert ">72<" in html
    assert html.count("&asymp;") == 1


def test_us_stocks_host_zero_unintended_delta():
    """Sibling host keeps CTA, +N (without .pg-more), score chips; no empty watch strip."""
    board = {**_empty_board(), "buy_now": [_theme("accumulate", score=72)],
             "more": {"buy_now": 5}}
    stocks = _render_board(board)
    si = _render_board(board, host="sector_central")
    assert "Theme reasons → Sector Intelligence" in stocks
    assert "Theme reasons → Sector Intelligence" not in si
    assert "+5 more" in stocks and "full list on Sector Intelligence" in stocks
    assert "+5 more" not in si
    assert 'class="pg-more' not in stocks
    assert 'class="act-row-score' in stocks
    assert 'class="act-row-score' not in si
    assert stocks.count("&asymp;") == 1
    assert si.count("&asymp;") == 0
    assert si.count("≈") == 0
    assert 'class="act-watch-strip"' not in stocks
    empty_si = _render_board(_empty_board(), host="sector_central")
    assert 'class="act-watch-strip"' not in empty_si


def test_nit12_flag_restored_on_h1():
    html = _render_page()
    assert "US Sector Intelligence 🇺🇸" in html
    assert "美国行业情报 🇺🇸" in html


def test_p3_3_emoji_replaced_with_monoline():
    src = PAGE_TPL.read_text(encoding="utf-8")
    for ch in ("🧭", "🧺", "📊", "⭐", "🌐", "🔴", "🟡", "🟢", "⚪"):
        assert ch not in src, f"emoji {ch} still in producer"
    html = _render_page()
    assert "sc-icon-bank" in html
    assert 'data-ic="star"' in html
    assert "mac-dot" in html


def test_d1_xlf_tinted_net_untinted():
    xlf = _flow_cell_html(-4100.0, 4100.0, tint=True)
    net = _flow_cell_html(-5100.0, 4100.0, tint=False)
    assert "background:color-mix" in xlf
    assert _fmt_money_mn(-4100.0) in xlf
    assert "background" not in net
    assert _fmt_money_mn(-5100.0) in net
    assert _fmt_money_mn(-4100.0) == "−$4.1B"
    assert _fmt_money_mn(-5100.0) == "−$5.1B"


def test_m3_enumeration_equals_producer_universe():
    assert THEME_STATES == tuple(RECOS.keys())
    assert SECTOR_STATES == tuple(STATE_DISPLAY[s]["label"] for s in LADDER)
    assert "clean entry" in OPEN_VERBS_EN
    assert "入场干净" in OPEN_VERBS_ZH
    assert "HALF SIZE" in OPEN_VERBS_EN
    assert "半仓" in OPEN_VERBS_ZH
