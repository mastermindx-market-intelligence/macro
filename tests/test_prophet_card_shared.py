"""Shared Prophet-card color and mobile-layout invariants pinned at the source.

`templates/_prophet_card.html.j2` is one partial with five consumers — the US
dashboard, china, hk, canada and intl — but the equivalent assertions live in
`tests/test_us_board_priority_ui.py` and read the US page's RENDERED output. That
covers exactly one caller: the CN board consumes the same partial, ships the same
`pv_css()` block, and had no test at all. A regression in the macro would therefore
be caught on us_stocks.html and land silently on china.html — and the CN board is
where the second invariant actually bites, because `--up` FLIPS to red under
`html[data-lang="zh"]` (theme.css `html[data-lang="zh"] { --up: #e06464 }`) and the
CN page is the one most often read in Chinese mode.

So these assertions grep the partial itself rather than any page render: one file,
every consumer, present and future. Two laws, both stated in the macro's own header:

  1. the featured glow is STATIC. That is what makes "no prefers-reduced-motion kill
     block" compliant rather than a gap — the strongest form of that compliance is
     having nothing to disable, and it only holds while nothing animates.
  2. the aura is pinned to the semantic `--pv-buy` token, never straight to the
     base direction tokens and never to `--pvh` (which follows the card's verb).
     theme.css owns the language convention: bullish green in EN, bullish red in ZH.
  3. at mobile widths, the company name receives its own line so display zoom cannot
     collapse it to zero between the ticker and Edge score.

Run: .venv/bin/python -m pytest tests/test_prophet_card_shared.py -q
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = ROOT / "templates" / "_prophet_card.html.j2"
THEME = ROOT / "templates" / "theme.css"
THEME_CSS = THEME.read_text(encoding="utf-8")

#: Jinja comments are prose — the macro header *discusses* animation at length and a
#: substring test over the raw file would fire on the explanation rather than on a
#: rule. And the markup below the macro carries `{% ... %}` blocks whose braces read
#: as CSS rules to a naive matcher (`{% elif cx.get('triage') %}` did exactly that).
#: So: strip the comments, then narrow to the <style> block pv_css() emits.
_SRC = re.sub(r"\{#.*?#\}", "", PARTIAL.read_text(encoding="utf-8"), flags=re.S)
_STYLE = re.search(r"<style>(.*?)</style>", _SRC, flags=re.S)
assert _STYLE, "pv_css() no longer emits a <style> block — this whole file is vacuous"
CSS = _STYLE.group(1)

#: Base direction tokens. Prophet components consume the semantic --pv-* layer so
#: the language-specific convention stays centralized in theme.css.
DIRECTION_BASE = ("var(--up)", "var(--up-flip)", "var(--down)")


def _featured_rules(css: str) -> list[tuple[str, str]]:
    """(selector, declarations) for every rule whose SELECTOR names pv-featured."""
    return [(m.group(1).strip(), m.group(2))
            for m in re.finditer(r"([^{}]*pv-featured[^{}]*)\{([^{}]*)\}", css)]


def _featured_block(css: str) -> str:
    """The contiguous source region the glow occupies, header rule → next component."""
    start = css.index(".pvcard.pv-featured{")
    return css[start:css.index(".pv-chart{", start)]


RULES = _featured_rules(CSS)
BLOCK = _featured_block(CSS)
#: the aura rules proper — ::before is the card's own hue RAIL and legitimately
#: follows --pvh, so it is held to the animation law but not to the --pv-buy law.
AURA = [(s, b) for s, b in RULES if "::before" not in s]


# --------------------------------------------------------------------------- #
# the extraction itself must be able to fail
# --------------------------------------------------------------------------- #
def test_the_matchers_find_the_glow_and_fire_on_a_planted_offender():
    """A regex that silently matches nothing turns every assertion below green."""
    assert len(BLOCK) > 200, "featured block slice collapsed — the matcher is vacuous"
    assert len(AURA) >= 4, f"expected the 4 aura rules (±light/hover), got {len(AURA)}"
    assert any("::before" in s for s, _ in RULES), "::before rail rule not matched"

    planted = (".pvcard.pv-featured{animation:pv-pulse 2s infinite;"
               "box-shadow:0 0 26px var(--up)}\n.pv-chart{x:1}")
    sel, body = _featured_rules(planted)[0]
    assert "animation" in body and "var(--up)" in body, sel
    assert "animation" in _featured_block(planted)


# --------------------------------------------------------------------------- #
# 1. the glow is static
# --------------------------------------------------------------------------- #
def test_the_featured_glow_carries_no_animation():
    assert "animation" not in BLOCK, "featured glow must not animate"
    assert "@keyframes" not in BLOCK, "no keyframes may live in the featured block"


def test_no_featured_rule_animates_from_anywhere_in_the_partial():
    """The block slice alone is not enough: an `animation:` added to a featured rule
    that moved, or a @keyframes declared further down, would both escape it.
    (`transition` is deliberately NOT banned — the hover lift is a transition on
    .pvcard, which is state-driven and stops; an animation runs unprompted.)"""
    for selector, body in RULES:
        assert "animation" not in body, f"{selector} animates the featured card"
    named = re.findall(r"@keyframes\s+([\w-]+)", CSS)
    for frames in named:
        assert not any(frames in body for _, body in RULES), \
            f"@keyframes {frames} is driven from a featured rule"


# --------------------------------------------------------------------------- #
# 2. the glow hue follows the semantic Prophet buy token
# --------------------------------------------------------------------------- #
def test_the_aura_is_pinned_to_pv_buy():
    for selector, body in AURA:
        assert "var(--pv-buy)" in body, f"{selector} lost the --pv-buy pin"
        assert "var(--pvh)" not in body, \
            f"{selector} follows the card's verb hue; the aura must stay bullish"


def test_no_featured_rule_bypasses_the_prophet_palette():
    for selector, body in RULES:
        for token in DIRECTION_BASE:
            assert token not in body, (
                f"{selector} bypasses --pv-buy with {token}; language-aware Prophet "
                "colors must stay centralized in theme.css")


def test_the_featured_chip_carries_the_same_hue_law():
    """Colour is never the only carrier — the ★ Featured chip is the redundant one —
    so it must not contradict the aura by flipping when the aura does not."""
    chip = re.search(r"\.pv-mk-feat\{([^{}]*)\}", CSS)
    assert chip, ".pv-mk-feat rule not found"
    assert "var(--pv-buy)" in chip.group(1)
    for token in DIRECTION_BASE:
        assert token not in chip.group(1)


def _all_rule_bodies(selector: str) -> str:
    """Join every declaration block for an exact selector in theme.css."""
    return "\n".join(re.findall(re.escape(selector) + r"\s*\{([^{}]*)\}", THEME_CSS))


def test_chinese_mode_rebinds_prophet_bullish_red_and_bearish_green():
    # C8-C (#6011) made the zh direction flip STRUCTURAL: the zh block flips
    # --up/--down themselves, and Buy/Near derive from --up via the base
    # color-mix, so a zh Buy chip is red BY CONSTRUCTION. A zh restatement of
    # --pv-buy/--pv-near would re-create the desync DA-002 cured (a future
    # --up edit silently leaving zh on a stale hand-tuned red). The semantic
    # properties (AA on every consumer, dE floors, Near lighter than Buy)
    # live in tests/test_prophet_verb_ink_contrast.py — change either file
    # only alongside the other.
    zh = _all_rule_bodies('html[data-lang="zh"]')
    assert "--up: #e06464" in zh and "--down: #45b873" in zh
    assert "--pv-buy:" not in zh, "zh must not restate --pv-buy (flip is structural)"
    assert "--pv-near:" not in zh, "zh must not restate --pv-near (flip is structural)"
    # --pv-avoid is a :root literal, so zh still needs its one explicit rebind:
    assert "--pv-avoid: var(--down)" in zh

    light_zh = _all_rule_bodies('html[data-theme="light"][data-lang="zh"]')
    assert "--up: #cf4040" in light_zh and "--down: #1f9a55" in light_zh
    # The light+zh --ink-pv-buy/--ink-pv-near deepening rungs were RETIRED by
    # C8-C (the deepening moved into the token itself); re-adding one would
    # double-mix. --ink-pv-avoid keeps its quadrant rung.
    assert "--ink-pv-buy:" not in light_zh, "retired rung must stay retired (C8-C)"
    assert "--ink-pv-near:" not in light_zh, "retired rung must stay retired (C8-C)"
    assert "--ink-pv-avoid:" in light_zh and "var(--pv-avoid) 62%" in light_zh


def test_mobile_company_name_gets_a_noncollapsing_second_line():
    assert ".pv-idw{flex:1 1 auto;flex-wrap:wrap;row-gap:1px;overflow:visible}" in CSS
    assert ".pv-nm{flex-basis:100%;width:100%}" in CSS


def test_what_to_buy_now_keeps_its_existing_direction_palette():
    """The separate action lanes stay on --ink-up/--ink-down, not Prophet tokens."""
    assert ".anv2-lane--buy   .anv2-lane-title { color:var(--ink-up); }" in THEME_CSS
    assert ".anv2-lane--red   .anv2-lane-title { color:var(--ink-down); }" in THEME_CSS


# --------------------------------------------------------------------------- #
# the ⚠ caution popover must paint above the NEXT card, not just escape its own
# --------------------------------------------------------------------------- #
#: Reported 2026-08-03 on us_stocks.html and hk_stocks.html; the partial is shared, so
#: it was every board. The clip was released long ago (`overflow:visible`), but the
#: popover still rendered BEHIND the neighbouring card and lost its right-hand text.
#:
#: Cause: `.pvcard:hover` sets `transform:translateY(-2px)`, and a non-none transform
#: creates a stacking context — so `.pv-cau-pop{z-index:30}` is resolved INSIDE the
#: hovered card instead of against its siblings, and every later `.pvcard` paints over
#: it. Raising the popover further cannot fix that; the CARD has to be lifted.
#:
#: This pins the CAUSAL rule rather than a literal, so it stays honest under edits:
#: while the hover transform exists, the escape rule must also carry a z-index.
def _escape_rule() -> tuple[str, str]:
    """(selector, declarations) for the rule that lets the caution popover out.

    Narrowed to selectors that style the CARD (`.pvcard:has(…)`): the sibling rule
    `.pv-cau:hover .pv-cau-pop{display:block}` also names `.pv-cau:hover` but merely
    reveals the popover, and matching it here would make these assertions read the
    wrong declarations.
    """
    hits = [(m.group(1).strip(), m.group(2))
            for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", CSS)
            if ".pv-cau:hover" in m.group(1) and ".pvcard" in m.group(1)]
    assert len(hits) == 1, f"expected exactly one card-level caution rule, got {hits}"
    return hits[0]


def test_the_escape_rule_matcher_fires_on_a_planted_offender():
    """The extraction must be able to fail, or every assertion below is vacuous."""
    sel, decls = _escape_rule()
    assert "overflow" in decls, sel
    stripped = CSS.replace(f"{sel}{{{decls}}}", "")
    hits = [m for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", stripped)
            if ".pv-cau:hover" in m.group(1) and ".pvcard" in m.group(1)]
    assert not hits, "removing the rule left a second card-level match — matcher too loose"


def test_the_hover_transform_that_traps_the_popover_still_exists():
    """The premise. If the transform ever goes, this whole guard needs re-deriving —
    fail loudly rather than keep asserting a fix for a cause that moved."""
    hover = re.search(r"\.pvcard:hover\{([^{}]*)\}", CSS)
    assert hover, ".pvcard:hover rule not found"
    assert "transform:" in hover.group(1), (
        "the hover transform is gone — re-check whether .pvcard still needs z-index "
        "to lift the caution popover above its siblings"
    )


def test_releasing_the_clip_also_lifts_the_card_above_its_siblings():
    sel, decls = _escape_rule()
    assert "overflow:visible" in decls.replace(" ", ""), sel
    z = re.search(r"z-index:\s*(\d+)", decls)
    assert z, (
        "the caution escape rule releases the clip but sets no z-index — the popover "
        "escapes the card and then paints UNDER the next card in the grid"
    )
    assert int(z.group(1)) > 0, "z-index must beat sibling cards (z-index:auto)"


def test_the_lift_stays_below_the_modal_and_lens_layers():
    """A hovered CARD must never outrank a dialog. Page chrome on these boards tops
    out around z-index 4; the overlay/LENS layers live at 1200+."""
    _, decls = _escape_rule()
    z = int(re.search(r"z-index:\s*(\d+)", decls).group(1))
    assert 4 < z < 1000, f"card lift z-index={z} is outside the safe band"


def test_the_focus_within_half_is_lifted_too():
    """The ⚠ control is a real <button>: keyboard users open the popover via focus,
    not hover, and that path must not paint underneath the neighbour either."""
    sel, _ = _escape_rule()
    assert ".pv-cau:focus-within" in sel, (
        "the focus-within selector left the escape rule — the keyboard path would "
        "regain the clipping/stacking bug"
    )


# --------------------------------------------------------------------------- #
# the verb chip carries NO hover tip (operator removal, 2026-08-03)
# --------------------------------------------------------------------------- #
#: It restated what the card already shows — the chip reads "Buy", the tracker shows the
#: stage, the footer prints the zone. The ⚡ trigger tip and the ⚠N popover stay, so this
#: asserts the ONE chip, not "no tips on the card".
MARKUP = _SRC[_SRC.index("{% macro pv_card("):]


def test_the_verb_chip_has_no_data_tip():
    chip = re.search(r'<span class="pv-chip"[^>]*>', MARKUP)
    assert chip, "verb chip markup not found — this guard has gone vacuous"
    assert "data-tip" not in chip.group(0), (
        "the verb chip regained a hover tip: " + chip.group(0)
    )


def test_the_trigger_and_caution_disclosures_survived_the_removal():
    """Guard the removal's blast radius — which GREW by a second operator order.

    2026-08-03 took the tip off the verb chip only, and this guard pinned
    .pv-edge as a survivor. 2026-08-05 extended the same call to .pv-edge and to
    the feat/new marks: all three are badges whose whole job is to be read at a
    glance, and their explainers were the longest cards on the board.

    So the radius is re-pinned, not relaxed. What must SURVIVE is unchanged and
    still asserted — the ⚡ trigger tip and the ⚠N caution popover carry facts
    that appear nowhere else on the card. What went is now asserted GONE, so a
    tip creeping back onto a badge fails here rather than passing quietly.
    """
    trg = re.search(r'<span class="pv-trg[^>]*>', MARKUP)
    assert trg and "data-tip-en" in trg.group(0), "the ⚡ trigger tip was removed too"
    assert 'class="pv-cau-pop"' in MARKUP, "the ⚠ caution popover was removed too"

    edge = re.search(r'<span class="pv-edge"[^>]*>', MARKUP)
    assert edge, "the Edge slot markup is gone — this guard has gone vacuous"
    assert "data-tip" not in edge.group(0), (
        "the Edge/Priority badge regained a hover tip (removed 2026-08-05): "
        + edge.group(0)
    )
    assert "_MK_NOTIP" in MARKUP, (
        "the feat/new mark tip suppression is gone — the 2026-08-05 removal "
        "covered those badges too"
    )


# --------------------------------------------------------------------------- #
# the premise of this file
# --------------------------------------------------------------------------- #
def test_the_partial_really_is_shared_beyond_the_us_page():
    """If the CN board ever stopped consuming this partial, the reason this file
    exists alongside tests/test_us_board_priority_ui.py would be stale."""
    consumers = sorted(
        p.name for p in (ROOT / "templates").glob("*.j2")
        if "_prophet_card.html.j2" in p.read_text(encoding="utf-8")
    )
    expected = {"dashboard.html.j2", "china.html.j2", "hk.html.j2",
                "canada.html.j2", "intl.html.j2"}
    assert expected <= set(consumers), consumers


# --------------------------------------------------------------------------- #
# Packet 2 — record-only plan detail must stay presentation-only and collapsed
# --------------------------------------------------------------------------- #
def test_record_only_plan_detail_is_scoped_and_source_bound():
    plan_partial = (ROOT / "templates" / "_us_prophet_plan_cards.html.j2").read_text(
        encoding="utf-8"
    )
    assert "{%- if _record_only and cx.get('record_detail') %}" in _SRC
    assert '<details class="pv-record-detail"' in _SRC
    assert 'data-plan-id="{{ _rd.plan_id|e }}"' in _SRC
    assert "System model plan — not your holdings or fills." in _SRC
    assert "'record_detail': {" in plan_partial
    assert "p.get('what_to_do_now')" not in plan_partial
    assert "'created_date': p.get('plan_asof') or p.get('recorded_at')" in plan_partial
    assert "'lifecycle_en': _LIFE_LABEL_EN.get(_life, 'State unavailable')" in plan_partial
    assert "p.get('management_status') == 'available'" in plan_partial
    assert "does not restate management actions or infer a user position" in _SRC
    assert "'history_available': false" in plan_partial
    assert "'action_unavailable': ('recommended_action' in p) and p.get('recommended_action') is none" in plan_partial
    assert 'data-action-state="unavailable"' in _SRC
    assert "Action guidance unavailable." in _SRC
    assert 'data-history-state="unavailable"' in _SRC
    assert "Not connected in this view yet." in _SRC
    assert "fetch(" not in plan_partial and "XMLHttpRequest" not in plan_partial


# --------------------------------------------------------------------------- #
# Packet 2 — current lifecycle-book denominator must not quote cumulative archive
# --------------------------------------------------------------------------- #
def test_plan_book_denominator_discloses_archived_rows_separately():
    assert "book.get('active_count')" in _SRC
    assert "book.get('plan_count')" in _SRC
    assert "_declared_rows - _book_rows" in _SRC
    assert "effective plan rows" in _SRC
    assert "archived plan publications remain outside this lifecycle book" in _SRC


def test_plan_record_partial_is_valid_jinja_syntax():
    """Packet 2 record details must remain parseable after comment-only edits."""
    from jinja2 import Environment

    plan_partial = (ROOT / "templates" / "_us_prophet_plan_cards.html.j2").read_text(
        encoding="utf-8"
    )
    Environment(autoescape=True).parse(plan_partial)


def test_plan_action_unavailable_requires_explicit_null_key():
    """Absent action evidence stays absent; only an explicit null earns the neutral row."""
    from jinja2 import DictLoader, Environment

    plan_partial = (ROOT / "templates" / "_us_prophet_plan_cards.html.j2").read_text(
        encoding="utf-8"
    )
    shared = (ROOT / "templates" / "_prophet_card.html.j2").read_text(encoding="utf-8")
    env = Environment(
        loader=DictLoader({
            "_us_prophet_plan_cards.html.j2": plan_partial,
            "_prophet_card.html.j2": shared,
        }),
        autoescape=True,
    )
    env.globals["tr"] = lambda value: value
    env.globals["us_stance_projection"] = lambda *_args, **_kwargs: {
        "verb": None, "stance_basis": "no_read",
    }

    base = {
        "id": "TEST-BULL-20260901",
        "asset": "TEST",
        "lifecycle_state": "invalidated",
        "management_status": "available",
        "management_error": None,
        "entry": 10.0,
        "invalidation": 9.0,
        "targets": [11.0, 12.0],
        "horizon_days": 20,
    }
    absent = env.get_template("_us_prophet_plan_cards.html.j2").render(
        items=[dict(base)], cand_map={}, trg_map={}, episode_map={}
    )
    explicit_null = env.get_template("_us_prophet_plan_cards.html.j2").render(
        items=[dict(base, recommended_action=None)],
        cand_map={}, trg_map={}, episode_map={}
    )
    non_null = env.get_template("_us_prophet_plan_cards.html.j2").render(
        items=[dict(base, recommended_action="hold")],
        cand_map={}, trg_map={}, episode_map={}
    )

    assert 'data-action-state="unavailable"' not in absent
    assert "Action guidance unavailable." not in absent
    assert 'data-action-state="unavailable"' in explicit_null
    assert "Action guidance unavailable." in explicit_null
    assert "操作指引暂缺。" in explicit_null
    assert 'data-action-state="unavailable"' not in non_null
    assert "Action guidance unavailable." not in non_null


# R18: single-row display projections ride existing entitled template/payload owners.
def _r18_env():
    from jinja2 import Environment, FileSystemLoader
    e = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    e.globals['tr'] = lambda value: value
    return e


def test_setup_detail_preserves_zero_false_and_missing_as_different_facts():
    from bs4 import BeautifulSoup
    e = _r18_env()
    row = {'ticker': 'TEST_ONLY', 'price': 0, 'stage': 'setting_up', 'lane': 'bottoming',
           'entry_signal': {'status': 'bounce_wait', 'buy_zone': {'low': 0, 'high': None},
                            'stop': 10, 'chase_above': 40},
           'hold': {'invalidation': 7},
           'signal': {'above200': False, 'weekly_bull': True}}
    html = str(e.get_template('_prophet_setup_detail.html.j2').module.body(row, 'board', '2026-09-24'))
    soup = BeautifulSoup(html, 'html.parser')
    def val(path):
        return soup.select_one('[data-source-field="' + path + '"] dd').get_text(' ', strip=True)
    assert val('price') == '$0.00'
    assert val('entry_signal.buy_zone.low') == '$0.00'
    assert 'Not supplied' in val('entry_signal.buy_zone.high')
    assert val('entry_signal.stop') == '$10.00'
    assert val('hold.invalidation') == '$7.00'
    assert val('entry_signal.chase_above') == '$40.00'
    assert val('signal.above200') == 'No 否'
    assert val('signal.weekly_bull') == 'Yes 是'
    assert 'Not supplied' in val('signal.provisional')
    assert 'Not supplied' in val('price_as_of')
    assert val('envelope.as_of') == '2026-09-24'


def test_setup_detail_research_never_borrows_board_levels_or_strategy():
    from bs4 import BeautifulSoup
    row = {'ticker': 'SAME_SYMBOL', 'lane': 'featured', 'stage': 'live',
           'entry_signal': {'status': 'buy_now', 'stop': 11},
           'strategy_sleeve': 'UNBOUND_POLICY', 'horizon_days': 20,
           'targets': [99, 100], 'hold': {'invalidation': 4}}
    html = str(_r18_env().get_template('_prophet_setup_detail.html.j2').module.body(row, 'pool', None))
    soup = BeautifulSoup(html, 'html.parser')
    assert not soup.select('[data-entry-status], [data-source-field="entry_signal.stop"]')
    assert 'UNBOUND_POLICY' not in html
    assert 'buy_now' not in html
    assert not soup.select('.pvs-levels')
    assert 'No model-plan link is available for this candidate.' in soup.get_text()


def test_setup_detail_rejects_nonfinite_or_boolean_prices():
    from bs4 import BeautifulSoup
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    for price in [True, False, float('nan'), float('inf'), -float('inf'), '12.5', {}, []]:
        h = str(m.body({'ticker': 'TEST_ONLY', 'price': price}, 'board', None))
        s = BeautifulSoup(h, 'html.parser')
        assert 'Not supplied' in s.select_one('[data-source-field="price"] dd').get_text()


def test_setup_detail_escapes_source_text_and_attribute_payloads():
    from bs4 import BeautifulSoup
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    attack = '\"><img src=x onerror=alert(1)>'
    h = str(m.body({'ticker': attack, 'stage': attack, 'lane': attack,
                    'signal': {'reason': attack},
                    'entry_signal': {'status': attack, 'headline': attack}}, 'board', attack))
    s = BeautifulSoup(h, 'html.parser')
    assert not s.select('img, script, iframe, [onerror]')
    assert s.select_one('[data-entry-status]')['data-entry-status'] == attack
    assert s.select_one('[data-native-id]')['data-native-id'] == attack
    assert attack in s.get_text()


def test_setup_detail_opt_in_keeps_one_card_and_a_real_native_link():
    from bs4 import BeautifulSoup
    e = _r18_env(); m = e.get_template('_prophet_card.html.j2').module
    cx = {'tk': 'TEST_ONLY', 'href': 'stock.html#TEST_ONLY', 'mkt': 'us',
          'verb': 'wait', 'edge': None, 'stage': 0}
    ordinary = BeautifulSoup(str(m.pv_card(cx)), 'html5lib')
    assert ordinary.select_one('.pvcard').name == 'a'
    assert not ordinary.select('.pv-setup-inline')
    detail = e.get_template('_prophet_setup_detail.html.j2').module.body({'ticker': 'TEST_ONLY'}, 'board', None)
    enhanced = BeautifulSoup(str(m.pv_card(dict(cx, setup_detail=detail))), 'html5lib')
    assert len(enhanced.select('.pvcard')) == 1
    assert enhanced.select_one('.pvcard').name == 'article'
    assert enhanced.select_one('.pv-setup-stock-link')['href'] == 'stock.html#TEST_ONLY'
    assert len(enhanced.select('details.pv-setup-inline > summary')) == 1
    assert not enhanced.select('a a, a summary, a details, a button')
    assert 'pv-wait' in enhanced.select_one('.pvcard')['class']


def test_setup_detail_uses_native_lens_control_exception_and_source_events():
    theme = (ROOT / 'templates' / 'theme.js').read_text(encoding='utf-8')
    assert "var CTRL_SEL = 'button, a, input, select, textarea, label, summary," in theme
    detail = theme.split('/* Packet2: enhance existing entitled row details;', 1)[1]
    assert "candidate-pool-hydrated" in detail and "mmx-access-tier" in detail
    assert "sourceStamp(active.row) !== active.sourceStamp" in detail
    assert "old.row.isConnected" in detail
    assert "row.closest('[aria-hidden=\"true\"],[hidden],.mx-tier-hidden,.mx-tier-blurred')" in detail
    assert 'fetch(' not in detail and 'localStorage' not in detail and 'sessionStorage' not in detail


# R19: the existing dense Table consumes the same entitled single-row presenter.
def test_setup_table_same_row_body_and_clock_match_card_presenter():
    from bs4 import BeautifulSoup
    row = {'ticker': 'SAME_SYMBOL', 'stage': 'setting_up', 'lane': 'bottoming',
           'price': 105., 'entry_signal': {'status': 'bounce_wait',
           'buy_zone': {'low': 100., 'high': 103.}, 'stop': 90., 'chase_above': 110.},
           'hold': {'invalidation': 85.}, 'signal': {'above200': False}}
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    table = BeautifulSoup(str(m.table_action(row, '2026-09-24')), 'html5lib')
    card = BeautifulSoup(str(m.body(row, 'board', '2026-09-24')), 'html5lib')
    assert str(table.select_one('.pv-setup-body')) == str(card.select_one('.pv-setup-body'))
    action = table.select_one('details.pv-setup-table')
    assert action['data-setup-ticker'] == 'SAME_SYMBOL'
    assert action['data-setup-asof'] == '2026-09-24'
    assert table.select_one('[data-entry-status]')['data-entry-status'] == 'bounce_wait'
    assert table.select_one('[data-source-field="entry_signal.stop"] dd').text == '$90.00'
    assert table.select_one('[data-source-field="hold.invalidation"] dd').text == '$85.00'


def test_setup_table_chart_is_inert_text_until_display_guard():
    from bs4 import BeautifulSoup
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    svg = '<svg viewBox="0 0 240 42"><polyline points="0,40 240,5"/></svg>'
    s = BeautifulSoup(str(m.table_action({'ticker': 'TEST', 'spark_svg': svg}, None)), 'html5lib')
    assert not s.select('svg, script, img, [onerror]')
    assert s.select_one('template.pvs-chart-source').string == svg
    assert s.select_one('details')['data-setup-asof'] == ''


def test_setup_table_hostile_source_cannot_break_out_of_serialized_row():
    import json
    from bs4 import BeautifulSoup
    e = _r18_env()
    attack = '</template></script><img src=x onerror=alert(1)>'
    row = {'ticker': 'TEST', 'spark_svg': attack, 'signal': {'reason': attack},
           'entry_signal': {'headline': attack, 'status': 'bounce_wait'}}
    renderer = e.from_string('{% import "_prophet_setup_detail.html.j2" as d %}'
                             '{{ {"setup_detail": d.table_action(row, clock)|string}|tojson }}')
    encoded = renderer.render(row=row, clock='2026-09-24')
    assert '</script>' not in encoded and '<img' not in encoded
    s = BeautifulSoup(json.loads(encoded)['setup_detail'], 'html5lib')
    assert not s.select('script, img, iframe, [onerror]')
    assert attack in s.get_text()


def test_setup_table_fallback_missing_values_never_enrich_from_other_population():
    from bs4 import BeautifulSoup
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    row = {'ticker': 'NO_FIELDS', 'strategy_sleeve': 'UNBOUND', 'horizon_days': 12,
           'targets': [200.], 'plan_id': 'UNRELATED', 'price': None}
    s = BeautifulSoup(str(m.table_action(row, None)), 'html5lib')
    assert 'UNBOUND' not in s.text and 'UNRELATED' not in s.text
    assert 'Not supplied' in s.select_one('[data-source-field="price"] dd').text
    assert 'Not supplied' in s.select_one('[data-source-field="envelope.as_of"] dd').text
    assert s.select_one('[data-entry-status]')['data-entry-status'] == ''


def test_setup_table_keeps_native_navigation_and_one_detail_controller():
    source = (ROOT / 'templates' / 'stocktable.js').read_text(encoding='utf-8')
    assert "e.target.closest('a,button,input,select,textarea,summary,details,[role=\"button\"]')" in source
    assert "T.open(row.ticker || '', tr)" in source
    assert "cfg.linkPattern.replace('{ticker}'" in source
    assert 'StockTable.init' in (ROOT / 'templates' / 'dashboard.html.j2').read_text()
    theme = (ROOT / 'templates' / 'theme.js').read_text()
    detail = theme.split('/* Packet2: enhance existing entitled row details;', 1)[1]
    assert detail.count("dialog.id = 'pv-setup-dialog'") == 1
    assert "details.dataset.setupTicker" in detail
    assert "details.dataset.setupAsof" in detail
    assert "nativeHref !== 'stock.html#' + bound" in detail
    assert 'fetch(' not in detail and 'localStorage' not in detail
    assert 'JSON.parse' not in detail


def test_setup_table_ticker_search_is_us_opt_in_and_detects_regression():
    import json
    import shutil
    import subprocess

    source = (ROOT / 'templates' / 'stocktable.js').read_text()
    begin = source.index('    function applyFilters(rows) {')
    end = source.index('    function sortRows(rows) {', begin)
    native = source[begin:end]
    harness = r'''
const assert = require('node:assert/strict');
const rows=[{ticker:'MPWR',name:'Monolithic Power Systems',sector:'Technology'},
            {ticker:'AAPL',name:'Apple',sector:'Technology',narrative:{theme:'Devices'}},
            {ticker:'TEST',name:'Other'}];
const original=JSON.stringify(rows);
let cfg={},filters={stage:'all',zone:'all',tier:'all',sector:'all',capBucket:'all',lane:'all',freshOnly:false,theme:'MPWR'};
function _isFresh(){return false;}
__FUNCTION__
assert.deepEqual(applyFilters(rows), []);                         // unchanged legacy caller
cfg.searchTicker=false; assert.deepEqual(applyFilters(rows), []);
cfg.searchTicker='true'; assert.deepEqual(applyFilters(rows), []); // explicit bool only
cfg.searchTicker=true; assert.deepEqual(applyFilters(rows).map(x=>x.ticker),['MPWR']);
filters.theme='mpwr'; assert.deepEqual(applyFilters(rows).map(x=>x.ticker),['MPWR']);
filters.theme='Monolithic'; assert.deepEqual(applyFilters(rows).map(x=>x.ticker),['MPWR']);
filters.theme='Devices'; assert.deepEqual(applyFilters(rows).map(x=>x.ticker),['AAPL']);
filters.theme=''; assert.deepEqual(applyFilters(rows),rows);
assert.equal(JSON.stringify(rows),original);
'''
    node = shutil.which('node')
    assert node, 'existing Node runtime is required to verify the native table predicate'
    good = subprocess.run([node, '-e', harness.replace('__FUNCTION__', native)], capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    mutation = native.replace('cfg.searchTicker === true', 'false')
    assert mutation != native
    bad = subprocess.run([node, '-e', harness.replace('__FUNCTION__', mutation)], capture_output=True, text=True)
    assert bad.returncode != 0 and 'AssertionError' in bad.stderr
    assert 'searchTicker: true' in (ROOT / 'templates' / 'dashboard.html.j2').read_text()
    for market in ['china', 'hk', 'canada', 'intl']:
        assert 'searchTicker: true' not in (ROOT / 'templates' / (market + '.html.j2')).read_text()


def test_dense_detail_uses_inert_same_row_body_and_fallback():
    from bs4 import BeautifulSoup
    m = _r18_env().get_template('_prophet_setup_detail.html.j2').module
    row = {'ticker': 'LOCAL', 'entry_signal': {'status': 'bounce_wait', 'stop': 11}}
    markup = str(m.table_action(row, '2026-09-24'))
    soup = BeautifulSoup(markup, 'html5lib')
    detail = soup.select_one('details.pv-setup-table')
    assert detail.select_one(':scope > .pv-setup-body') is None
    inert = detail.select_one(':scope > template.pvs-body-source')
    assert inert.select_one('.pv-setup-body[data-native-id="LOCAL"]')
    assert inert.select_one('[data-entry-status="bounce_wait"]')
    assert detail.select_one(':scope > .pvs-fallback-note')
    assert not detail.select('script,iframe,img,[onerror]')
    # Cards still have a direct native disclosure body when enhancement is absent.
    card = BeautifulSoup(str(m.action(m.body(row, 'board', '2026-09-24'))), 'html5lib')
    assert card.select_one('details.pv-setup-inline > .pv-setup-body')


def test_dense_detail_controller_restores_only_original_live_owner():
    source = (ROOT / 'templates/theme.js').read_text().split('/* Packet2: enhance existing entitled row details;', 1)[1]
    assert "holder.content.querySelector('.pv-setup-body')" in source
    assert 'pair.home.contains(pair.mark)' in source
    assert 'old.row.contains(old.details)' in source
    assert 'pair.owner.isConnected' in source
    assert 'owner:holder || details' in source
    assert 'target.append(n)' in source
    assert 'fetch(' not in source and 'localStorage' not in source


# R21: decision-changing absences are visible; provenance is progressive, not removed.
def test_setup_detail_progressive_disclosure_keeps_facts_and_missing_terms():
    from bs4 import BeautifulSoup
    env = _r18_env()
    row = {"ticker": "FOCUS", "price": 11.0, "lane": "bottoming", "stage": "setting_up",
           "entry_signal": {"status": "bounce_wait", "headline": "Wait for confirmation", "buy_zone": {"low": 10.0, "high": 10.5}, "stop": 9.0, "chase_above": 12.0},
           "hold": {"invalidation": 8.0}, "signal": {"reason": "Confirmation pending", "above200": False, "weekly_bull": False}}
    soup = BeautifulSoup(str(env.get_template("_prophet_setup_detail.html.j2").module.body(row, "board", "2026-09-24")), "html5lib")
    extra = soup.select_one("details.pvs-audit")
    assert extra and not extra.has_attr("open")
    assert soup.select_one(".pvs-summary-clock").find_parent("details") is None
    assert "2026-09-24" in soup.select_one(".pvs-summary-clock").get_text(" ", strip=True)
    assert "Quote time" in soup.select_one(".pvs-summary-clock").get_text()
    assert "Not supplied" in soup.select_one(".pvs-summary-clock").get_text()
    assert soup.select_one("[data-entry-status]")["data-entry-status"] == "bounce_wait"
    assert soup.select_one(".pvs-availability").find_parent("details") is None
    assert "Target and holding period unavailable" in soup.select_one(".pvs-availability").get_text()
    assert "not calculated" in soup.select_one(".pvs-availability").get_text()
    for path, val in [("entry_signal.stop", "$9.00"), ("hold.invalidation", "$8.00"), ("entry_signal.chase_above", "$12.00")]:
        field = soup.select_one('[data-source-field="' + path + '"]')
        assert field.find_parent("details") is None and field.select_one("dd").get_text(strip=True) == val
    for path in ["canonical strategy binding not supplied", "holding duration not supplied", "envelope.as_of", "price_as_of"]:
        assert extra.select_one('[data-source-field="' + path + '"]')
    assert "No model-plan link is available" in extra.get_text()


def test_setup_detail_styles_are_explicit_opt_in_after_acceptance_repair():
    import hashlib
    env = _r18_env()
    card = env.get_template("_prophet_card.html.j2").module
    css = str(card.pv_css())
    assert hashlib.sha256(css.encode()).hexdigest() == "e7dd2cf07a44230d9a1b9a82b335943070ca0bad76e6fc7c1b99aa0625a12258"
    assert ".pvs-audit" not in css
    assert ".pvs-audit" in str(card.pv_css(setup_detail=True))
