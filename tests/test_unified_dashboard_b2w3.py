"""Tests for the UD-B2-W3 Unified Macro Dashboard Drivers fold.

Pins the three folds per META-CEO A packet UD-B2-W3 (2026-09-21):

  1. R1 / census #6 — Leadership context strip folds into the Drivers block
     as the defense-vs-cyclical DRIVER TILE. SIGNAL-ORIGINATION LAW: there
     is no vm['leadership'] contract. The live strip in
     templates/dashboard.html.j2 reads MS.radar.cycle.sector_bias
     (favor/avoid lists with .en + .zh), composed by
     engine.election_cycle.sector_bias() → risk_radar.cycle_context →
     engine.market_state._radar_to_rd()['cycle']. When that key is absent
     the tile is designed-null — never an invented rotation read.

  2. Census #33 + #34 — Fear/Euphoria dial + Froth/Fragility bar fold into
     ONE sentiment driver tile. Display-tier; never a signal. Existing
     engine keys: fear_euphoria.{fe_score, band} and
     froth_fragility.{band, band_zh, quadrant_en, quadrant_zh, face_a.score,
     face_b.score}. Glance prints WORDS only (one-integer law).

  3. R6 / census #36 — AI / non-AI breadth split RELOCATES to
     advanced.html#vsb-breadth-split-section with a chip link from the
     hero breadth driver. Move, do not duplicate; vm['breadth_split']
     contract unchanged.

Also pins: one-integer law on the new tiles, bilingual EN/ZH parity,
and the designed-null honesty of the leadership tile.
"""
from __future__ import annotations

import re
from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

# Glance-tier banned machine text (plain-word gate).
BANNED_GLANCE = (
    "falsifier", "refuted", "证伪",
    "vm['leadership']", "percentile rank", "z-score",
)


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=jinja2.ChainableUndefined,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    except Exception:  # noqa: BLE001 — i18n is optional in unit tests
        env.globals.update(td=lambda en, zh=None: en, tr=lambda en: en, zip=zip)
    return env


def _base_vm() -> dict:
    return {
        "market_state": {
            "verdict": "MIXED",
            "color": "yellow",
            "score": 55,
            "raw_score": 55,
            "label_en": "Mixed",
            "label_zh": "混合",
            "headline_en": "Buyers are still showing up.",
            "headline_zh": "买盘仍在。",
            "flip_en": "Windows, not certainties.",
            "flip_zh": "是窗口，不是定论。",
            "asof": "2026-09-20",
            "mtf": {"indices": [{"confluence_en": "Held", "confluence_zh": "企稳"}]},
            "radar": {},
        },
        "stance": {"key": "shift"},
        "alerts": [],
        "event_strip": [],
        "ms_history": [],
        "risk_envelope": {},
        "fear_greed": {"label_en": "Neutral", "label_zh": "中性", "dial": 50},
        "fear_euphoria": None,
        "froth_fragility": None,
        "latest": {"date": "2026-09-20", "quad_name": "Mixed"},
    }


def _render_hero(vm: dict) -> str:
    return _env().get_template("_unified_dashboard_hero.html.j2").render(**vm)


def _latest_stub() -> dict:
    return {
        "date": "2026-09-20",
        "growth_score": 0.1,
        "growth_confidence": 0.5,
        "inflation_score": -0.1,
        "inflation_confidence": 0.5,
        "preference_check": None,
        "quad_name": "Mixed",
    }


def _render_advanced(ctx: dict) -> str:
    ctx = dict(ctx)
    latest = dict(_latest_stub())
    latest.update(ctx.get("latest") or {})
    ctx["latest"] = latest
    return _env().get_template("advanced.html.j2").render(**ctx)


def _driver_slice(html: str, driver: str) -> str:
    """Slice one .ud-driver panel by data-driver= value."""
    needle = f'data-driver="{driver}"'
    start = html.find(needle)
    assert start >= 0, f"driver {driver!r} not found"
    div_start = html.rfind("<div", 0, start)
    assert div_start >= 0
    depth = 0
    i = div_start
    n = len(html)
    while i < n:
        if html.startswith("<div ", i) or html.startswith("<div>", i):
            depth += 1
            i += 5
        elif html.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return html[div_start:i]
        else:
            i += 1
    raise AssertionError(f"unterminated driver {driver!r}")


def _real_sector_bias(asof: str):
    """Lawful fixture: call the engine that the live strip already reads."""
    from engine.election_cycle import sector_bias
    return sector_bias(asof)


# --------------------------------------------------------------------------- #
# Fold 1 — R1 leadership tile, real-or-designed-null honesty
# --------------------------------------------------------------------------- #


def test_leadership_contract_is_radar_cycle_sector_bias_not_vm_leadership():
    """SIGNAL-ORIGINATION LAW: the census found no vm['leadership']. The
    live strip in dashboard.html.j2 names MS.radar.cycle.sector_bias, and
    the hero tile must read that same key — never invent vm['leadership']."""
    dash = (TEMPLATES / "dashboard.html.j2").read_text(encoding="utf-8")
    hero = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    assert "MS.radar.cycle.sector_bias" in dash, (
        "legacy strip must still name MS.radar.cycle.sector_bias (the live contract)"
    )
    assert "data-contract=\"market_state.radar.cycle.sector_bias\"" in hero
    assert "sector_bias" in hero
    assert 'vm["leadership"]' not in hero
    # Comments may name the absent contract; rendered markup must not
    # invent a leadership view-model key.
    rendered = _render_hero(_base_vm())
    assert "leadership" in rendered  # the tile's data-driver
    assert 'data-driver="leadership"' in rendered
    # Composer: engine.election_cycle.sector_bias → radar.cycle_context →
    # market_state._radar_to_rd()['cycle']
    radar_src = (ROOT / "engine" / "risk_radar.py").read_text(encoding="utf-8")
    ms_src = (ROOT / "engine" / "market_state.py").read_text(encoding="utf-8")
    assert '"cycle_context": cyc' in radar_src
    assert '"cycle": rr.get("cycle_context")' in ms_src


def test_leadership_tile_renders_real_sector_bias_from_election_cycle():
    """When the engine publishes sector_bias (midterm H2), the tile surfaces
    the favor/avoid names from that return — not invented copy."""
    sb = _real_sector_bias("2026-09-20")
    assert sb is not None, "2026-09-20 is midterm H2; sector_bias must resolve"
    assert sb.get("favor") and sb.get("avoid")
    vm = _base_vm()
    vm["market_state"]["radar"] = {"cycle": {"sector_bias": sb}}
    html = _render_hero(vm)
    tile = _driver_slice(html, "leadership")
    assert 'data-designed-null="1"' not in tile
    favor_en = " / ".join(x["en"] for x in sb["favor"])
    avoid_en = " / ".join(x["en"] for x in sb["avoid"])
    favor_zh = "／".join(x["zh"] for x in sb["favor"])
    avoid_zh = "／".join(x["zh"] for x in sb["avoid"])
    assert favor_en in tile
    assert avoid_en in tile
    assert favor_zh in tile
    assert avoid_zh in tile
    assert "Under the surface:" in tile
    assert "表面之下：" in tile


def test_leadership_tile_designed_null_when_sector_bias_absent():
    """When sector_bias is None (not midterm H2) the tile is designed-null.
    Never invent Health Care / Staples / Utilities as a live read."""
    sb = _real_sector_bias("2026-03-01")
    assert sb is None, "2026-03-01 is not midterm H2; sector_bias must be None"
    vm = _base_vm()
    vm["market_state"]["radar"] = {"cycle": {"sector_bias": None}}
    html = _render_hero(vm)
    tile = _driver_slice(html, "leadership")
    assert 'data-designed-null="1"' in tile
    assert "Health Care" not in tile
    assert "Staples" not in tile
    assert "Utilities" not in tile
    assert "医疗保健" not in tile
    assert "Read being updated" in tile
    assert "判读更新中" in tile


def test_leadership_tile_designed_null_when_radar_cycle_missing():
    """Missing radar.cycle entirely is also designed-null — never approximate."""
    vm = _base_vm()
    vm["market_state"]["radar"] = {}
    html = _render_hero(vm)
    tile = _driver_slice(html, "leadership")
    assert 'data-designed-null="1"' in tile
    assert "Health Care" not in tile
    assert "Read being updated" in tile


# --------------------------------------------------------------------------- #
# Fold 2 — #33 + #34 one sentiment tile
# --------------------------------------------------------------------------- #


def test_sentiment_tile_folds_fear_euphoria_and_froth_fragility():
    """#33 and #34 share ONE tile. Glance prints band words, not a second
    integer; the rails are geometry. Existing engine keys only."""
    vm = _base_vm()
    vm["fear_euphoria"] = {"fe_score": 42, "band": "Neutral"}
    vm["froth_fragility"] = {
        "band": "watch",
        "band_zh": "关注",
        "quadrant_en": "Calm & broad",
        "quadrant_zh": "平静且广泛",
        "face_a": {"score": 30},
        "face_b": {"score": 20},
    }
    html = _render_hero(vm)
    tile = _driver_slice(html, "fear_greed")
    assert 'data-fold="sentiment-33-34"' in tile
    assert 'data-driver-leg="fear_euphoria"' in tile
    assert 'data-driver-leg="froth_fragility"' in tile
    assert ">Neutral<" in tile  # fear_euphoria.band (and fear_greed head)
    assert ">中性<" in tile
    assert ">Watch<" in tile or ">watch<" in tile.lower()
    assert ">关注<" in tile
    # Geometry present, integers NOT printed as glance text.
    assert "ud-sent-pin" in tile
    assert "ud-froth-fill" in tile
    # The scores 42 / 30 / 20 must not appear as visible text nodes.
    visible = re.sub(r'style="[^"]*"', "", tile)
    visible = re.sub(r"data-tip-en=\"[^\"]*\"", "", visible)
    visible = re.sub(r"data-tip-zh=\"[^\"]*\"", "", visible)
    assert not re.search(r">\s*42\s*<", visible), "fe_score must not print as glance text"
    assert not re.search(r">\s*30\s*<", visible), "face_a.score must not print as glance text"
    assert not re.search(r">\s*20\s*<", visible), "face_b.score must not print as glance text"


def test_sentiment_tile_designed_null_when_engines_absent():
    """Missing fear_euphoria + froth_fragility → designed-null body. Head
    still reads fear_greed (B1 contract)."""
    vm = _base_vm()
    html = _render_hero(vm)
    tile = _driver_slice(html, "fear_greed")
    assert "Neutral" in tile  # fear_greed head
    assert "中性" in tile
    assert "sentiment context, display only" in tile
    assert "情绪背景，仅展示" in tile
    assert 'data-driver-leg="fear_euphoria"' not in tile


def test_sentiment_tile_keeps_fear_greed_head_from_b1():
    """B1 R-K: driver 3 head still surfaces fear_greed.label_en / label_zh."""
    vm = _base_vm()
    vm["fear_greed"] = {"label_en": "Greed", "label_zh": "贪婪", "dial": 70}
    html = _render_hero(vm)
    tile = _driver_slice(html, "fear_greed")
    assert ">Greed<" in tile
    assert ">贪婪<" in tile


# --------------------------------------------------------------------------- #
# Fold 3 — R6 AI-breadth relocate
# --------------------------------------------------------------------------- #


def test_hero_breadth_chip_links_to_advanced_anchor():
    html = _render_hero(_base_vm())
    mtf = _driver_slice(html, "mtf")
    assert 'href="advanced.html#vsb-breadth-split-section"' in mtf
    assert "See how AI names compare with everyone else." in mtf
    assert "查看 AI 相关个股与其他个股相比如何。" in mtf
    # The module itself must NOT be duplicated on the hero.
    assert 'id="vsb-breadth-split-section"' not in html
    assert 'data-vsb-bs="ai"' not in html


def test_dashboard_no_longer_carries_breadth_split_module():
    """Move, do not duplicate: the dialog section and the glance caveat
    leave dashboard.html.j2."""
    src = (TEMPLATES / "dashboard.html.j2").read_text(encoding="utf-8")
    assert 'id="vsb-breadth-split-section"' not in src
    assert 'id="vsb-sentiment-caveat"' not in src
    assert "UD-B2-W3 R6 relocate" in src


def test_advanced_html_gains_breadth_split_module():
    ctx = {
        "latest": {"date": "2026-09-20"},
        "generated_utc": "2026-09-20T00:00:00Z",
        "cross_asset": None,
        "portfolio": None,
        "ic_scorecard": None,
        "components_confirming": [],
        "components_contradicting": [],
        "flip_plain": "",
        "internals": [],
        "size_style": [],
        "breadth_div": None,
        "accumulation": [],
        "holdings_changes": [],
        "holdings_threshold": 1,
        "flows_html": None,
        "breadth_split": {
            "stance_en": "AI names leading — watch, don't chase",
            "stance_zh": "AI 相关股领涨，观察而非追高",
            "latest": {"ai_pct50": 72.0, "nonai_pct50": 47.0, "spread_50": 25.0},
            "cohort_sizes": {"ai_total": 100, "universe": 400},
            "young": False,
        },
    }
    html = _render_advanced(ctx)
    assert 'id="vsb-breadth-split-section"' in html
    assert 'data-vsb-bs="ai"' in html
    assert 'data-vsb-bs="nonai"' in html
    assert "AI-linked names above their 50-day trend" in html
    assert "Everyone else" in html
    assert "AI names leading" in html
    assert "watch, don" in html  # apostrophe may be autoescaped
    assert "AI 相关股领涨，观察而非追高" in html
    assert "recycles capital" in html


def test_advanced_html_designed_null_when_breadth_split_absent():
    ctx = {
        "latest": {"date": "2026-09-20"},
        "generated_utc": "",
        "cross_asset": None,
        "portfolio": None,
        "ic_scorecard": None,
        "components_confirming": [],
        "components_contradicting": [],
        "flip_plain": "",
        "internals": [],
        "size_style": [],
        "breadth_div": None,
        "accumulation": [],
        "holdings_changes": [],
        "holdings_threshold": 1,
        "flows_html": None,
        "breadth_split": None,
    }
    html = _render_advanced(ctx)
    assert 'id="vsb-breadth-split-section"' in html, (
        "the chip landing must exist even when the feed is empty"
    )
    assert "Read being updated" in html
    assert "判读更新中" in html
    assert 'data-vsb-bs="ai"' not in html


def test_build_site_passes_breadth_split_to_advanced():
    src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    # The advanced.html.j2 render call must pass breadth_split=_breadth_split_view()
    assert "breadth_split=_breadth_split_view()" in src
    # And the helper itself is the existing JSON-or-None view (unchanged contract).
    assert "def _breadth_split_view()" in src


# --------------------------------------------------------------------------- #
# One-integer law on the new tiles
# --------------------------------------------------------------------------- #


def test_one_integer_law_on_new_driver_tiles():
    """Glance cells: no dates and no second integer. Travel deltas only
    where the spec draws them (spine, not these tiles)."""
    sb = _real_sector_bias("2026-09-20")
    vm = _base_vm()
    vm["market_state"]["radar"] = {"cycle": {"sector_bias": sb}}
    vm["fear_euphoria"] = {"fe_score": 42, "band": "Fear"}
    vm["froth_fragility"] = {
        "band": "watch", "band_zh": "关注",
        "quadrant_en": "Calm & broad", "quadrant_zh": "平静且广泛",
        "face_a": {"score": 30}, "face_b": {"score": 20},
    }
    html = _render_hero(vm)
    for name in ("leadership", "fear_greed", "mtf"):
        tile = _driver_slice(html, name)
        # Strip geometry style attrs and hover tips so leftover digits there
        # are not glance integers.
        glance = re.sub(r'style="[^"]*"', "", tile)
        glance = re.sub(r'data-tip-en="[^"]*"', "", glance)
        glance = re.sub(r'data-tip-zh="[^"]*"', "", glance)
        glance = re.sub(r"data-contract=\"[^\"]*\"", "", glance)
        glance = re.sub(r"data-driver=\"[^\"]*\"", "", glance)
        glance = re.sub(r"data-fold=\"[^\"]*\"", "", glance)
        glance = re.sub(r"data-driver-leg=\"[^\"]*\"", "", glance)
        glance = re.sub(r'href="[^"]*"', "", glance)
        assert not re.search(r"20\d{2}-\d{2}-\d{2}", glance), (
            f"{name} glance cell must not print a date"
        )
        visible_ints = re.findall(r">\s*(\d+)\s*<", glance)
        assert visible_ints == [], (
            f"{name} glance cell must not print a competing integer; got {visible_ints}"
        )


# --------------------------------------------------------------------------- #
# Bilingual parity + plain-word gate
# --------------------------------------------------------------------------- #


def test_new_tiles_bilingual_en_zh_parity():
    """Every new visible string is a plain sentence in EN and ZH. No
    translated text in title= attributes."""
    sb = _real_sector_bias("2026-09-20")
    vm = _base_vm()
    vm["market_state"]["radar"] = {"cycle": {"sector_bias": sb}}
    vm["fear_euphoria"] = {"fe_score": 42, "band": "Fear"}
    vm["froth_fragility"] = {
        "band": "watch", "band_zh": "关注",
        "quadrant_en": "Calm & broad", "quadrant_zh": "平静且广泛",
        "face_a": {"score": 30}, "face_b": {"score": 20},
    }
    html = _render_hero(vm)
    for name in ("leadership", "fear_greed", "mtf"):
        tile = _driver_slice(html, name)
        en_spans = len(re.findall(r'class="[^"]*l-en[^"]*"', tile)) + tile.count('class="l-en"')
        zh_spans = len(re.findall(r'class="[^"]*l-zh[^"]*"', tile)) + tile.count('class="l-zh"')
        # Count opening spans more simply.
        en_count = tile.count("l-en")
        zh_count = tile.count("l-zh")
        assert en_count > 0 and zh_count > 0, f"{name} must carry both locales"
        assert en_count == zh_count, (
            f"{name} EN/ZH span counts must match exactly "
            f"(en={en_count}, zh={zh_count})"
        )
        assert "title=" not in tile, (
            f"{name} must not put translated text in title= attributes"
        )
    hero_src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    for banned in BANNED_GLANCE:
        # Skip the comment that names the absent vm['leadership'] contract.
        if banned.startswith("vm["):
            continue
        assert banned not in _driver_slice(html, "leadership")
        assert banned not in _driver_slice(html, "fear_greed")


def test_hero_template_has_no_hex_or_color_mix_in_w3_block():
    """DESIGN-RATCHET: new W3 CSS is token-true."""
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    # The W3 block starts at the UD-B2-W3 comment.
    start = src.find("UD-B2-W3 Drivers fold")
    assert start > 0
    block = src[start: src.find("</style>", start)]
    assert "color-mix" not in block
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", block)
    assert "rgba(" not in block
    assert "rgb(" not in block
    assert "border-radius:" not in block or "var(--r-" in block


# --------------------------------------------------------------------------- #
# MAJOR-1 — three live driver tiles + locked fourth (spec §6/§7, disposition R1)
# --------------------------------------------------------------------------- #


def test_drivers_are_three_live_plus_locked_fourth():
    """Disposition R1 is 'one of three driver tiles'. Spec §6/§7 driver 4
    is TierLock (390 hides .ud-driver--locked, counter 1 / 3). Leadership
    folds into the breadth tile; it must not occupy the locked slot."""
    html = _render_hero(_base_vm())
    panels = re.findall(r'<div class="panel ud-driver[^"]*"', html)
    locked = [p for p in panels if "ud-driver--locked" in p]
    live = [p for p in panels if "ud-driver--locked" not in p]
    assert len(live) == 3, f"expected 3 live driver panels, got {live}"
    assert len(locked) == 1, f"expected 1 locked driver panel, got {locked}"
    assert "Full sector narrative is locked." in html
    assert "完整板块叙事已锁定。" in html
    assert "1 of 3" in html
    assert "1 / 3" in html
    assert "1 of 4" not in html
    assert "1 / 4" not in html
    # Leadership is a leg of the breadth tile, not a fourth live panel.
    mtf = _driver_slice(html, "mtf")
    lead = _driver_slice(html, "leadership")
    assert 'data-driver="leadership"' in mtf
    assert 'data-contract="market_state.radar.cycle.sector_bias"' in lead
    assert "ud-driver--locked" not in lead
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    style = src[src.find("UD-B2-W3 Drivers fold"): src.find("</style>", src.find("UD-B2-W3 Drivers fold"))]
    assert ".ud-driver--locked" in style and "display:none" in style.replace(" ", "")


# --------------------------------------------------------------------------- #
# MAJOR-2 — RED-first pin: Jinja `{#` must not swallow advanced.html chrome
# --------------------------------------------------------------------------- #


def test_advanced_style_block_does_not_open_a_jinja_comment():
    """RED-first pin for 20620b6766. c38c46673f shipped
    `@media(max-width:820px){#vsb-breadth-split-section` which Jinja
    treats as `{#` … `#}` and drops `</style></head><body>` plus the
    nav include. test_advanced_html_gains_breadth_split_module stayed
    green on that broken HTML because the `<div id=…>` sat AFTER the
    closing `#}`. Reintroducing `{#id` inside <style> must go RED.
    """
    src = (TEMPLATES / "advanced.html.j2").read_text(encoding="utf-8")
    style_start = src.index("<style>")
    style_end = src.index("</style>", style_start)
    style = src[style_start:style_end]
    assert "{#" not in style, (
        "a `{#` inside <style> is a Jinja comment opener; CSS id "
        "selectors after `{` must be spaced or on their own line"
    )
    assert "{#vsb-breadth-split-section" not in src

    ctx = {
        "latest": {"date": "2026-09-20"},
        "generated_utc": "2026-09-20T00:00:00Z",
        "cross_asset": None,
        "portfolio": None,
        "ic_scorecard": None,
        "components_confirming": [],
        "components_contradicting": [],
        "flip_plain": "",
        "internals": [],
        "size_style": [],
        "breadth_div": None,
        "accumulation": [],
        "holdings_changes": [],
        "holdings_threshold": 1,
        "flows_html": None,
        "breadth_split": {
            "stance_en": "AI names leading — watch, don't chase",
            "stance_zh": "AI 相关股领涨，观察而非追高",
            "latest": {"ai_pct50": 72.0, "nonai_pct50": 47.0, "spread_50": 25.0},
            "cohort_sizes": {"ai_total": 100, "universe": 400},
            "young": False,
        },
    }
    html = _render_advanced(ctx)
    lower = html.lower()
    style_i = lower.index("</style>")
    head_i = lower.index("</head>")
    body_i = lower.index("<body")
    nav_i = html.index('class="site-nav"')
    sec_i = html.index('id="vsb-breadth-split-section"')
    assert style_i < head_i < body_i < nav_i < sec_i, (
        "Jinja must not comment-out </style></head><body> or the nav "
        f"(style={style_i}, head={head_i}, body={body_i}, nav={nav_i}, sec={sec_i})"
    )


# --------------------------------------------------------------------------- #
# Evidence capture honesty (BLOCKER-1/2, MINOR-3) — pin the capture script
# --------------------------------------------------------------------------- #


def test_capture_script_paints_body_from_tokens_and_crops_w3_tiles():
    """Hero dark evidence must paint `--bg`/`--text` onto the canvas (the
    rule lives at templates/dashboard.html.j2:326 and the isolated fixture
    must include it). 390 cells must element-crop the W3 tiles, not only
    `page.screenshot(full_page=False)` of the first swipe card. applied_*
    attestations must be measured from computed paint, not set-then-read.
    """
    src = (ROOT / "mockups" / "evidence" / "unified-dashboard-b2w3" / "capture.py").read_text(
        encoding="utf-8"
    )
    compact = src.replace(" ", "")
    assert "background:var(--bg)" in compact
    assert "color:var(--text)" in compact
    assert "getComputedStyle" in src
    assert "generated_at" in src and "2026-09-21T00:00:00Z" not in src
    assert "data-driver=\"leadership\"" in src or "data-driver='leadership'" in src
    assert "data-driver=\"fear_greed\"" in src or "data-driver='fear_greed'" in src
    assert ".screenshot" in src
    # Must not be viewport-only after a scroll of .ud-drivers.
    assert "full_page=False" not in src or "locator(" in src


# --------------------------------------------------------------------------- #
# Round-3 review — Major (direction token as severity) + two minors
# RED-first against c79fdb867369c4f3c8a479dd9a56cbb3b91f908c:
#   * hidden-selling rail painted with var(--down) (flips green in ZH)
#   * aria-label="locked depth" (English-only machine text)
#   * froth glance EN was {{ _ff_band|capitalize }} (slug title-case)
# --------------------------------------------------------------------------- #


def _w3_style_block() -> str:
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    start = src.find("UD-B2-W3 Drivers fold")
    assert start > 0
    return src[start: src.find("</style>", start)]


def test_hidden_selling_rail_uses_severity_token_not_direction():
    """R-W3-R3-1. Hidden selling is a health/severity read (red=bad in
    both languages). var(--down) is a DIRECTION token and swaps to green
    under html[data-lang="zh"] (theme.css). Paint with --act, which stays
    red. RED on c79fdb8673: `.ud-froth-fill--b{ background:var(--down); }`.
    """
    block = _w3_style_block()
    assert "var(--down)" not in block, (
        "W3 CSS must not paint severity with a direction token; --down "
        "flips to green in ZH"
    )
    assert "var(--up)" not in block, (
        "W3 CSS must not paint severity with a direction token"
    )
    compact = block.replace(" ", "")
    assert ".ud-froth-fill--b{background:var(--act);}" in compact
    assert ".ud-froth-fill{height:100%;background:var(--warn);}" in compact


def test_locked_driver_aria_is_bilingual_plain_sentences():
    """R-W3-R3-2. Screen-reader copy is user-facing. Follow the hero's
    existing bilingual aria pattern (l-en / l-zh each carry aria-label).
    RED on c79fdb8673: aria-label=\"locked depth\".
    """
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    assert 'aria-label="locked depth"' not in src
    html = _render_hero(_base_vm())
    assert 'aria-label="Full sector narrative is locked."' in html
    assert 'aria-label="完整板块叙事已锁定。"' in html
    lock_en = re.search(
        r'<span class="l-en" aria-label="Full sector narrative is locked\.">',
        html,
    )
    lock_zh = re.search(
        r'<span class="l-zh" aria-label="完整板块叙事已锁定。">',
        html,
    )
    assert lock_en, "EN lock copy must carry its own aria-label sentence"
    assert lock_zh, "ZH lock copy must carry its own aria-label sentence"


def test_froth_glance_en_maps_band_slug_not_capitalize():
    """R-W3-R3-3. Fear/Euphoria glance maps engine bands through a dict
    (Panic/Fear/Neutral/…). Froth EN must do the same — never |capitalize
    on a slug. ZH already uses band_zh. RED on c79fdb8673:
    `{{ _ff_band|capitalize if _ff_band else _null_word_en }}`.
    """
    src = (TEMPLATES / "_unified_dashboard_hero.html.j2").read_text(encoding="utf-8")
    assert "_ff_band|capitalize" not in src
    assert "|capitalize" not in src.split("data-driver-leg=\"froth_fragility\"")[1].split("ud-froth-row")[0]
    assert "'calm':" in src and "'watch':" in src and "'extreme':" in src

    vm = _base_vm()
    vm["fear_euphoria"] = {"fe_score": 42, "band": "Neutral"}
    vm["froth_fragility"] = {
        "band": "watch",
        "band_zh": "关注",
        "quadrant_en": "Calm & broad",
        "quadrant_zh": "平静且广泛",
        "face_a": {"score": 30},
        "face_b": {"score": 20},
    }
    tile = _driver_slice(_render_hero(vm), "fear_greed")
    assert ">Watch<" in tile
    assert ">watch<" not in tile
    assert ">关注<" in tile

    vm["froth_fragility"]["band"] = "elevated"
    vm["froth_fragility"]["band_zh"] = "升高"
    tile = _driver_slice(_render_hero(vm), "fear_greed")
    assert ">Elevated<" in tile
    assert ">升高<" in tile
