"""tests/test_prophet_r7_wave_a_guards.py — Prophet R7 Wave A, slice A3.

R7 §6/§10/§13 and R7-24: a name passed on tonight must be readable as "not a
rejection and not a Wait" — ONE disclosure per name on the see-all landing
(``pvr_receipts``), and Today shows only a count and ONE plain link
(``pvr_today_count``; seat ruling OQ4: plain text link, no chevrons). Seat ruling
OQ5: the refusal title already on main is binding and byte-identical, so it is
always read from ``pvr_copy['validation_failed']`` — never retyped in a macro.

Also guards the two cross-template design laws this slice must not break:

  GUARD 2 (Chairman rule 2026-10-18) — no colored container edge accent
  (``border-left`` / ``border-inline-start`` with a non-zero, non-none value, or
  any ``box-shadow`` containing ``inset``) across the receipts estate, with
  exactly one allowlisted site: the ``.seam-gap .over`` dashed band in
  watchlist.html.j2 — a CHART overlay drawn on the chart's own coordinate strip,
  not a container. The CSS ``inset:`` positioning property is not a shadow and is
  deliberately not flagged.

  GUARD 7 (OQ7 ink guard) — semantic ink is never text ink: no ``color:``
  declaration whose OUTER token is ``var(--up…)``, ``var(--down…)`` or
  ``var(--warn…)`` in the receipts + plan-card partials. ``var(--ink-up,
  var(--up))``-style is allowed (the outer token is an ink-* token).
  watchlist.html.j2 is guarded by slice A2's test, not this one.

BROWSER-FREE, like tests/test_prophet_whynot_receipts.py, and for the same
reason: the CI packs install a minimal dependency set. Assertions are on the
rendered markup through the same env shape (FileSystemLoader + autoescape); the
pass-through ``tr`` global matches the packet's prescription — this partial
carries its own ``t()`` and imports nothing from engine or scripts.

LOAD CLOSURE (every repo file this suite opens, reads or imports): the three
templates below via ``Path.read_text``, plus ``_prophet_receipts.html.j2``
loaded by name through the Jinja loader. Nothing else.
"""
from __future__ import annotations

import copy
import html
import re
import sys
from pathlib import Path

import jinja2
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMPLATES = ROOT / "templates"
RECEIPTS_TMPL = "_prophet_receipts.html.j2"
PLAN_CARDS_TMPL = "_us_prophet_plan_cards.html.j2"
WATCHLIST_TMPL = "watchlist.html.j2"

# Explicit paths only — no glob/os.walk/listdir/scandir/iterdir/subprocess in this
# file, and no scripts/build_* import. The load closure is exactly these three.
SRC: dict[str, str] = {
    RECEIPTS_TMPL: (TEMPLATES / RECEIPTS_TMPL).read_text(),
    PLAN_CARDS_TMPL: (TEMPLATES / PLAN_CARDS_TMPL).read_text(),
    WATCHLIST_TMPL: (TEMPLATES / WATCHLIST_TMPL).read_text(),
}

# Seat ruling OQ5: main's pair, straight apostrophes, exactly as pvr_copy carries it.
VF_EN = "Passed the board's checks — tonight's plan data didn't verify"
VF_ZH = "通过了榜单检查 — 但今晚的计划数据未能核验"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals["tr"] = lambda v: v
    return env


def _render_call(call: str, **ctx) -> str:
    """Render one macro call from the receipts partial (packet's env pattern)."""
    out = str(_env().from_string(
        '{% import "_prophet_receipts.html.j2" as r %}{{ ' + call + ' }}'
    ).render(**ctx))
    return out


def _plain(out: str) -> str:
    """Copy assertions run on unescaped text — autoescape turns ' into &#39;."""
    return html.unescape(out)


def _name(tk: str, *, name: str | None = None, score: float | None = None,
          sector: str | None = None, why: tuple[str, ...] = ("plan_not_built",)) -> dict:
    nm: dict = {"ticker": tk, "name": name or f"{tk} Industries", "why": list(why)}
    if score is not None:
        nm["score"] = score
    if sector is not None:
        nm["sector"] = sector
    return nm


def _group(reason: str, names: list[dict]) -> dict:
    return {"reason": reason, "en": f"EN {reason}", "zh": f"ZH {reason}",
            "near": False, "n": len(names), "names": list(names)}


def _cx(groups: list[dict], *, passed: int | None = None) -> dict:
    total = sum(len(g["names"]) for g in groups)
    return {"considered": 79, "planned": 1,
            "passed": passed if passed is not None else total,
            "unmapped": 0, "groups": list(groups)}


def _six() -> dict:
    """R7-24 shape: plan-data refusals mid-board, scores out of order, one unscored."""
    return _cx([
        _group("plan_not_built", [_name("SC30", score=30.0), _name("SC50", score=50.0)]),
        _group("validation_failed", [_name("VFA1", name="Astera Labs", score=12.0,
                                           why=("validation_failed",)),
                                     _name("VFB2", score=11.0, why=("validation_failed",))]),
        _group("ran_too_far", [_name("SC70", score=70.0, why=("ran_too_far",)),
                               _name("NOSCORE", why=("ran_too_far",))]),
    ])


# --------------------------------------------------------------------------- #
# 1. The refusal title is main's pair, byte for byte (seat ruling OQ5)
# --------------------------------------------------------------------------- #

def test_validation_failed_title_is_mains_pair_byte_for_byte():
    out = _plain(_render_call("r.pvr_receipts(cx)", cx=_six()))
    assert VF_EN in out
    assert VF_ZH in out
    # The source keeps exactly one of each literal — pvr_copy's own entry — so no
    # macro retypes the title anywhere else in the file.
    assert SRC[RECEIPTS_TMPL].count(VF_EN) == 1
    assert SRC[RECEIPTS_TMPL].count(VF_ZH) == 1


# --------------------------------------------------------------------------- #
# 2. R7-24 display order; cx is never mutated or re-counted
# --------------------------------------------------------------------------- #

def test_display_order_is_r7_24_and_cx_is_untouched():
    cx = _six()
    before = copy.deepcopy(cx)
    out = _plain(_render_call("r.pvr_receipts(cx)", cx=cx))
    assert cx == before
    # Plan-data refusals lead; the rest by score descending; unscored last.
    firsts = [out.index(tk) for tk in ("VFA1", "VFB2", "SC70", "SC50", "SC30", "NOSCORE")]
    assert firsts == sorted(firsts)
    # The header count is the engine's `passed`, never re-derived from the rows.
    assert ">6 names<" in out
    assert ">6 只<" in out


@pytest.mark.parametrize("bad", [None, "not-a-mapping", 7, {}, {"groups": []},
                                 {"groups": [{"reason": "plan_not_built", "names": []}]}])
def test_receipts_degrade_to_empty_without_names(bad):
    assert _render_call("r.pvr_receipts(cx)", cx=bad) == ""


def test_sector_renders_only_when_the_row_carries_one():
    cx = _cx([_group("plan_not_built",
                     [_name("SECON", sector="Semiconductors", score=44.0),
                      _name("NOSEC", score=45.0)])])
    out = _render_call("r.pvr_receipts(cx)", cx=cx)
    # Rendered when a string sector rides the row…
    assert "Semiconductors" in out and 'pvr-rc-sec' in out
    # …and no empty shell when it does not (the contract today carries none).
    assert out.count('class="pvr-rc-sec"') == 1


# --------------------------------------------------------------------------- #
# 3. limit + the one nested overflow disclosure
# --------------------------------------------------------------------------- #

def test_limit_four_of_six_overflows_into_one_nested_disclosure():
    out = _plain(_render_call("r.pvr_receipts(cx)", cx=_six()))  # default limit=4
    # One disclosure per name — all six are pvr-rc rows — and exactly ONE overflow
    # container carries the two past the limit.
    assert out.count('<details class="pvr-rc">') == 6
    assert out.count('<details class="pvr-rc-more">') == 1
    assert "Show 2 more" in out
    assert "再显示 2 只" in out
    # The first `limit` disclosures sit ABOVE the overflow summary; the rest are
    # inside it — that is what "top-level" means for a nested native disclosure.
    gate = out.index("Show 2 more")
    assert max(out.index(tk) for tk in ("VFA1", "VFB2", "SC70", "SC50")) < gate
    assert min(out.index(tk) for tk in ("SC30", "NOSCORE")) > gate
    assert "Showing 4 of 6. Plan data refusals are listed first, then the rest by original priority." in out
    assert "显示 6 只中的 4 只。计划数据未核实的排在最前，其余按建立时优先级排序。" in out
    # A capped night (passed=20, only 6 rows shipped): M counts names ACTUALLY
    # present — 2, never 16 — and the header keeps the engine's lossless total.
    capped = _plain(_render_call("r.pvr_receipts(cx)", cx=_cx(_six()["groups"], passed=20)))
    assert "Showing 4 of 20." in capped
    assert "Show 2 more" in capped
    assert ">20 names<" in capped
    # No overflow → no nested disclosure and no "Showing…" line to explain one.
    tight = _render_call("r.pvr_receipts(cx, limit=9)", cx=_six())
    assert tight.count('<details class="pvr-rc-more">') == 0
    assert "Showing" not in _plain(tight)


# --------------------------------------------------------------------------- #
# 4. next_build absent — the reassurance still ends, and never prints None
# --------------------------------------------------------------------------- #

def test_no_next_build_ends_the_reassurance_at_verifies():
    out = _plain(_render_call("r.pvr_receipts(cx)", cx=_six()))
    assert "It rejoins the board when its plan data verifies.</span>" in out
    assert "计划数据核实后它会重新回到榜单。</span>" in out
    assert "; the next build is" not in out
    assert "下次构建在" not in out
    assert "None" not in out
    # With both strings the sentence carries them exactly as R7-24 words it.
    got = _plain(_render_call(
        "r.pvr_receipts(cx, next_build_en='after the close, Oct 21', "
        "next_build_zh='10月21日收盘后')", cx=_six()))
    assert "; the next build is after the close, Oct 21.</span>" in got
    assert "下次构建在 10月21日收盘后。</span>" in got


# --------------------------------------------------------------------------- #
# 5. No empty "What passed" heading without per-check rows
# --------------------------------------------------------------------------- #

def test_no_what_passed_heading_without_per_check_rows():
    out = _plain(_render_call("r.pvr_receipts(cx)", cx=_six()))
    assert "What passed" not in out
    assert "已通过的检查" not in out
    # The rows the heading would carry are not invented either.
    assert ">Met<" not in out and ">Formed<" not in out


# --------------------------------------------------------------------------- #
# 6. pvr_today_count — the count and ONE plain link
# --------------------------------------------------------------------------- #

def test_today_count_is_the_count_and_one_plain_link():
    cx = _cx([_group("plan_not_built", [_name("ALAB")])], passed=20)
    out = _plain(_render_call("r.pvr_today_count(cx, href='passed-tonight.html')", cx=cx))
    assert "Passed on tonight" in out and "今晚未纳入" in out
    assert ">20<" in out  # the count itself, as its own node
    assert out.count("<a ") == 1
    assert 'href="passed-tonight.html"' in out
    assert "See all 20 passed names" in out
    assert "查看全部 20 只未纳入标的" in out
    for glyph in ("→", "›", "»", "chevron"):
        assert glyph not in out


@pytest.mark.parametrize("bad", [None, {"passed": 0}, {"passed": True}, {"passed": "3"}, {}])
def test_today_count_degrades_to_empty(bad):
    assert _render_call("r.pvr_today_count(cx, href='x.html')", cx=bad) == ""


# --------------------------------------------------------------------------- #
# 7. The sample footnote is opt-in in BOTH macros (guard 6)
# --------------------------------------------------------------------------- #

def test_sample_footnote_is_opt_in_in_both_macros():
    today = _cx([_group("plan_not_built", [_name("ALAB")])], passed=20)
    on = (
        _render_call("r.pvr_receipts(cx, sample=true)", cx=_six()),
        _render_call("r.pvr_today_count(cx, href='p.html', sample=true)", cx=today),
    )
    off = (
        _render_call("r.pvr_receipts(cx)", cx=_six()),
        _render_call("r.pvr_today_count(cx, href='p.html')", cx=today),
    )
    for out in on:
        assert "Sample names and prices for design review, not live signals." in _plain(out)
        assert "示例名称与价格，仅供设计评审，并非实时信号。" in _plain(out)
    for out in off:
        assert "Sample names" not in _plain(out)
        assert "示例名称与价格" not in _plain(out)


# --------------------------------------------------------------------------- #
# 8. No title= attribute; hostile strings stay escaped
# --------------------------------------------------------------------------- #

def test_no_title_attribute_and_hostile_strings_stay_escaped():
    cx = _cx([_group("validation_failed",
                     [_name("X<b>Y", name="Foo<b>Bar Ltd", score=9.0,
                            why=("validation_failed",))])])
    out = _render_call("r.pvr_receipts(cx)", cx=cx)
    assert "title=" not in out
    assert "&lt;b&gt;" in out          # ticker AND name escaped where they render
    assert "<b>" not in out            # nothing reopens as markup
    assert 'href="stock.html#X&lt;b&gt;Y"' in out
    tc = _render_call("r.pvr_today_count(cx, href='a<b>.html')",
                      cx=_cx([_group("plan_not_built", [_name("ALAB")])], passed=3))
    assert "title=" not in tc
    assert 'href="a&lt;b&gt;.html"' in tc


# --------------------------------------------------------------------------- #
# 9. GUARD 2 — no container edge accent (Chairman rule 2026-10-18)
# --------------------------------------------------------------------------- #

GUARD2_FILES = (RECEIPTS_TMPL, PLAN_CARDS_TMPL, WATCHLIST_TMPL)

# The one sanctioned site: the .seam-gap .over band is a dashed CHART overlay on
# the watchlist chart's own coordinate strip — not a container edge. If
# watchlist.html.j2 ever drops it, this pattern stops matching and the tests
# below fail ON PURPOSE so the allowlist cannot quietly go stale.
SEAM_GAP_OVER = re.compile(r"\.seam-gap \.over\s*\{[^}]*border-left:\s*1px dashed")

_BORDER_RE = re.compile(r"border-(?:left|inline-start)\s*:\s*([^;{}]+)", re.IGNORECASE)
_BOX_SHADOW_INSET_RE = re.compile(r"box-shadow\s*:\s*[^;{}]*\binset\b", re.IGNORECASE)
_ZERO_VALUES = {"", "none", "0", "0px"}


def test_guard2_allowlist_still_names_a_real_site():
    # Exactly one allowlisted site, and it must keep matching real bytes: the
    # pattern AND the single border-left it excuses are both pinned here.
    assert SEAM_GAP_OVER.search(SRC[WATCHLIST_TMPL]), (
        "stale allowlist: the .seam-gap .over dashed chart band is gone from "
        "watchlist.html.j2 — update or retire the allowlist")
    assert SRC[WATCHLIST_TMPL].count("border-left") == 1
    assert SRC[WATCHLIST_TMPL].count("border-inline-start") == 0


def test_guard2_no_container_edge_accent_in_the_receipts_estate():
    violations: list[str] = []
    for name in GUARD2_FILES:
        allowed: list[tuple[int, int]] = []
        if name == WATCHLIST_TMPL:
            allowed.append(SEAM_GAP_OVER.search(SRC[name]).span())
        for m in _BORDER_RE.finditer(SRC[name]):
            if any(s <= m.start() < e for s, e in allowed):
                continue
            if m.group(1).strip().lower() in _ZERO_VALUES:
                continue
            violations.append(f"{name}: {m.group(0).strip()}")
        shadow = _BOX_SHADOW_INSET_RE.search(SRC[name])
        if shadow:
            violations.append(f"{name}: {shadow.group(0).strip()}")
    assert not violations, violations


# --------------------------------------------------------------------------- #
# 10. GUARD 7 — OQ7 ink guard: semantic hue is never text ink
# --------------------------------------------------------------------------- #

GUARD7_FILES = (RECEIPTS_TMPL, PLAN_CARDS_TMPL)

_COLOR_RE = re.compile(r"(?<![-\w])color\s*:\s*([^;{}]+)", re.IGNORECASE)
_SEMANTIC_OUTER_RE = re.compile(r"^\s*var\(\s*--(up|down|warn)", re.IGNORECASE)


@pytest.mark.parametrize("name", GUARD7_FILES)
def test_guard7_semantic_ink_is_never_text_color(name):
    bad = [m.group(0).strip() for m in _COLOR_RE.finditer(SRC[name])
           if _SEMANTIC_OUTER_RE.match(m.group(1))]
    assert not bad, bad
