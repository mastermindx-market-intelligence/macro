"""AI Desk page (templates/ai_desk.html.j2 + ai_desk.js + scripts/build_ai_desk_page).

The page is client-rendered (ai_desk.js fetches ai_desk.json), so here we assert the
static chrome renders cleanly (nav, bilingual labels, the desk-root mount, the script
includes) with no unrendered Jinja, that the renderer covers the key surfaces (track
record, theses, falsifier, panel), and that the builder ships the renderer asset."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


def _render():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False)
    return env.get_template("ai_desk.html.j2").render(as_of="2026-06-15 12:00 UTC")


def test_page_renders_without_unrendered_jinja():
    html = _render()
    assert "{{" not in html and "{%" not in html and "{#" not in html


def test_page_has_chrome_and_mount_and_assets():
    html = _render()
    assert "AI Desk" in html and 'class="site-nav"' in html
    assert 'id="desk-root"' in html and 'data-src="ai_desk.json"' in html
    assert '<script src="theme.js">' in html and '<script src="ai_desk.js">' in html
    # bilingual: the t() macro must emit the zh label alongside the en one
    assert "AI交易台" in html and 'class="l-zh"' in html
    # The header is now the shared one (_site_nav.html.j2), whose only external
    # entry is Terminal. Two per-page pills were removed here on 2026-08-01:
    #   · "Mastermind" — theme.js injects mm_brain.js sitewide, which mounts its
    #     own bottom-right launcher, so the nav pill was a duplicate entry point.
    #   · "🖥️ AI Desk" — a self-link marked .active on the page it points at.
    # NOTE: dropping the self-link orphans nothing. ai_desk.html is absent from
    # _navlinks.html.j2 and site-wide exactly ONE page links to it — itself. It
    # was already unreachable from the navigation; the pill only ever said "you
    # are here". Giving it a real home in the menu is a product decision, not a
    # chrome fix.
    #
    # Scoped to `.nav-ctrls` since 2026-08-07: the guard was written when NO Bot
    # link existed anywhere, so a whole-page substring read as "the header has no
    # Bot pill". The Bot now has a legitimate Research mega-menu card, and the
    # header contract is what this line always meant. theme.js:1492 strips any
    # `.nav-ctrls a[href*="bot.mastermind-x.com"]` at runtime; the SOURCE must not
    # lean on that, so the control cluster ships without one.
    ctrls = html[html.find('<div class="nav-ctrls">'):]
    ctrls = ctrls[:ctrls.find("</nav>")]
    assert ctrls, "the shared header lost its .nav-ctrls control cluster"
    assert 'href="https://app.mastermind-x.com"' in ctrls
    assert "bot.mastermind-x.com" not in ctrls


def test_renderer_covers_the_key_surfaces():
    js = (TEMPLATES / "ai_desk.js").read_text()
    for token in ("ai_desk.json", "track_record", "theses", "falsifier",
                  "panel", "dissent", "check_by"):
        assert token in js, token
    assert "esc(" in js                              # model content is HTML-escaped


def test_builder_ships_the_renderer_asset():
    from scripts import build_ai_desk_page as b
    assert "ai_desk.js" in b.ASSETS and "theme.js" in b.ASSETS and "theme.css" in b.ASSETS

# --------------------------------------------------------------------------- #
# W19-D1 (AID-W19D-1..5): the track badge must print the fields it drops. The
# page is client-rendered, so these tests slice the real function bodies out of
# templates/ai_desk.js and run them under node against synthetic fixtures shaped
# like the committed site/ai_desk.json (that file is NOT read here).
# --------------------------------------------------------------------------- #
_w19d_needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                      reason="node not on PATH")

_W19D_JS = (TEMPLATES / "ai_desk.js").read_text()

# strings in the producer's committed note format (engine/ai_desk_scorer.py:48-63)
_W19D_NOTE = "63 scored, hit-rate 0.921 (directional accuracy 0.651)."
_W19D_NOTE_ZH = "已评分 63 条，命中率 0.921（方向准确率 0.651）。"

_W19D_TRACK = {
    "scored_total": 63, "open": 5, "expired": 0, "unscored_soft": 0,
    "overall": {"n": 63, "hits": 58, "misses": 5, "hit_rate": 0.921,
                "dir_accuracy": 0.651},
    "by_conviction": {"high": {"n": 0, "hits": 0, "misses": 0, "hit_rate": None},
                      "medium": {"n": 0, "hits": 0, "misses": 0, "hit_rate": None},
                      "low": {"n": 63, "hits": 58, "misses": 5, "hit_rate": 0.921}},
    "by_kind": {"rel_return": {"n": 59, "hits": 58, "misses": 1, "hit_rate": 0.983,
                                "dir_accuracy": 0.661},
                "level": {"n": 4, "hits": 0, "misses": 4, "hit_rate": 0.0,
                          "dir_accuracy": 0.5}},
    "recent": [{"subject": "VIX", "lean": "fade-fear", "conviction": "low",
                "outcome": "miss", "realized": 0.2278, "check_by": "2026-10-02"}],
    "calibration_note": _W19D_NOTE, "calibration_note_zh": _W19D_NOTE_ZH,
}

_W19D_BADGE = ("esc", "bi", "pct", "trackBadge")
_W19D_RENDER = ("esc", "bi", "pct", "checkText", "thesisCard", "trackBadge",
                "panelAccordion", "render")

# comment | string | regex-literal | one char of code | whitespace
_W19D_TOK = re.compile(r"/\*.*?\*/|//[^\n]*|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\""
                       r"|/(?:\\.|[^/\\\n])+/[gimsuy]*|\S|\s", re.S)


def _w19d_slice(src, name):
    """One `function <name>` declaration, brace-matched over code tokens only."""
    m = re.search(r"\bfunction\s+%s\s*\(" % re.escape(name), src)
    assert m, "templates/ai_desk.js has no function %s" % name
    depth = 0
    for tok in _W19D_TOK.finditer(src, src.index("{", m.end())):
        d = tok.group(0)
        if d == "{":
            depth += 1
        elif d == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():tok.end()]
    raise AssertionError("unbalanced braces in function %s" % name)


def _w19d_js(src, *names):
    return "\n".join(_w19d_slice(src, n) for n in names) + "\n"


def _w19d_run(js):
    """Evaluate `js` with `node -e`; return stdout."""
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr[:2000]
    return r.stdout


def _w19d_html(expr, names):
    """Evaluate `expr` under node with the named renderer functions and their globals."""
    return _w19d_run("var root = { innerHTML: '' };\nvar LEAN = {};\n" +
                     _w19d_js(_W19D_JS, *names) + "console.log(%s);\n" % expr)


def _w19d_fx(**over):
    fx = json.loads(json.dumps(_W19D_TRACK))
    fx.update(over)
    return fx


@_w19d_needs_node
def test_w19d_track_badge_prints_by_kind():
    html = _w19d_html("trackBadge(%s)" % json.dumps(_W19D_TRACK), _W19D_BADGE)
    assert "58/59" in html and "0/4" in html, html
    assert "relative-return calls" in html and "相对收益类" in html
    assert "price-level calls" in html and "价位类" in html
    rel = [c for c in re.findall(r'<div class="tr-cell">.*?</div></div>', html) if "58/59" in c]
    assert rel and "relative-return calls" in rel[0] and "98%" in rel[0], rel
    assert "98%" in html and "0%" in html
    fx = _w19d_fx()
    fx["by_kind"]["level"]["hit_rate"] = None
    dash = _w19d_html("trackBadge(%s)" % json.dumps(fx), _W19D_BADGE)
    assert '<div class="v">—</div>' in dash and "NaN" not in dash, dash


@_w19d_needs_node
def test_w19d_track_badge_prints_open_on_populated_record():
    html = _w19d_html("trackBadge(%s)" % json.dumps(_W19D_TRACK), _W19D_BADGE)
    cells = re.findall(r'<div class="tr-cell">.*?</div></div>', html)
    open_cells = [c for c in cells if "进行中" in c]
    assert open_cells, "populated badge prints no 进行中 cell:\n" + html
    assert '<div class="v">5</div>' in open_cells[0], open_cells
    assert "expired" not in html and "已过期" not in html
    two = _w19d_html("trackBadge(%s)" % json.dumps(_w19d_fx(expired=2)), _W19D_BADGE)
    assert "已过期" in two and '<div class="v">2</div>' in two, two
    fx = _w19d_fx()
    fx.pop("open")
    shut = _w19d_html("trackBadge(%s)" % json.dumps(fx), _W19D_BADGE)
    assert "进行中" not in shut and "undefined" not in shut, shut


@_w19d_needs_node
def test_w19d_calibration_note_is_bilingual():
    html = _w19d_html("trackBadge(%s)" % json.dumps(_W19D_TRACK), _W19D_BADGE)
    assert 'class="l-zh">已评分 63 条' in html, html
    empty = {"scored_total": 0, "overall": {"n": 0}, "open": 5, "unscored_soft": 0,
             "calibration_note": "x en", "calibration_note_zh": "x zh"}
    empty_html = _w19d_html("trackBadge(%s)" % json.dumps(empty), _W19D_BADGE)
    assert 'class="l-zh">x zh' in empty_html, empty_html
    fb = _w19d_html("trackBadge(%s)" % json.dumps(_w19d_fx(calibration_note_zh=None)),
                    _W19D_BADGE)
    assert 'class="l-zh">63 scored, hit-rate' in fb, fb
    assert "undefined" not in fb, fb


@_w19d_needs_node
def test_w19d_recent_table_prints_check_by():
    html = _w19d_html("trackBadge(%s)" % json.dumps(_W19D_TRACK), _W19D_BADGE)
    assert "2026-10-02" in html and "检验日" in html, html
    fx = json.loads(json.dumps(_W19D_TRACK))
    fx["recent"][0].pop("check_by")
    bare = _w19d_html("trackBadge(%s)" % json.dumps(fx), _W19D_BADGE)
    assert "<td>—</td>" in bare, bare
    assert "undefined" not in bare, bare


@_w19d_needs_node
def test_w19d_render_prints_note_dates():
    fx = {"generated_at": "2026-10-17T06:43:21.373739+00:00", "state_asof": "2026-10-14",
          "theses": [], "track_record": {"scored_total": 0, "overall": {"n": 0}},
          "regime_context": "x"}
    html = _w19d_html("(render(%s), root.innerHTML)" % json.dumps(fx), _W19D_RENDER)
    assert "2026-10-17 06:43 UTC" in html and "2026-10-14" in html, html
    assert "笔记生成于" in html and "状态截至" in html, html
    odd = _w19d_html("(render(%s), root.innerHTML)" % json.dumps(dict(fx, state_asof="<b>")),
                     _W19D_RENDER)
    assert "&lt;b&gt;" in odd and "<b>" not in odd, odd
    bare = json.loads(json.dumps(fx))
    bare.pop("generated_at")
    bare.pop("state_asof")
    out = _w19d_html("(render(%s), root.innerHTML)" % json.dumps(bare), _W19D_RENDER)
    for gone in ("Note generated", "detector state as of", "笔记生成于", "状态截至"):
        assert gone not in out, (gone, out)
    assert "undefined" not in out, out


def test_w19d_page_does_not_claim_daily_regen():
    html = _render()
    for banned in ("Regenerated each day", "regenerates daily", "每个交易日收盘后更新"):
        assert banned not in html, banned
        assert banned not in _W19D_JS, banned
