"""Build-notes + SEO-display contract for the 同花顺 basket browser page.

site/baskets_china_ths.html is the ONLY production render of
templates/baskets_china_factorwatch.html.j2 (scripts/build_baskets_china_ths.py
passes lite=True). Two defects are pinned here:

  * the payload already carries `construction` / `history_note` (printed via the
    new server-side build_notes helper into a <details id="build-notes"> on the
    lite page only), and
  * the lite page's meta description / canonical / og:url must describe and
    point at THIS page, not the redirect-stub surfaces they were copied from.

Tests import only the stdlib, jinja2 and scripts._ths_build_notes — never a
scripts/build_*.py builder, engine.*, lib.*, pandas or numpy. Fixtures are the
committed payload strings (inline dicts; no data/, no site/, no network).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent

# The committed payload strings (scripts/seed_china_ths_baskets.py producer).
CONSTRUCTION = (
    "Equal-weighted, point-in-time dated membership, buy-and-hold between "
    "changes. Members are 同花顺 (Tonghuashun) concept-board constituents, "
    "filtered to the free china_search price cache. Benchmark = CSI 300 "
    "(沪深300)."
)
HISTORY = (
    "Membership is THS's, snapshotted over time; `added`/`removed` reflect when "
    "a name entered/left the THS board (first-run members seed at the cache "
    "start). Series before a name's add date is a backtest of the membership "
    "at that point."
)
# The seed's single seo_desc (templates/baskets_china_factorwatch.html.j2:12),
# which must survive UNCHANGED on the non-lite render.
SEED_DESC = ("China thematic baskets tracked against the CSI 300 — theme scores, "
             "leadership health and entry radar, updated after each Asia close.")


def _render(**extra) -> str:
    """Render the real template with the builder's minimal context."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")),
                      autoescape=True)
    ctx = dict(baskets_json="{}", chart_json="{}", basket_base="",
               bench_en="CSI 300", bench_zh="沪深300",
               generated_utc="2026-10-20 05:30 UTC")
    ctx.update(extra)
    return env.get_template("baskets_china_factorwatch.html.j2").render(**ctx)


def _between(html: str, start: str, end: str) -> str:
    i = html.index(start)
    return html[i + len(start):html.index(end, i)]


def _notes(payload: dict) -> list:
    """Route the fixture through the shipped helper. Before the helper exists
    (RED), feed the same two payload strings in so the template-side failure
    surfaces on its own; the GREEN path always imports the helper."""
    try:
        from scripts._ths_build_notes import build_notes
    except ImportError:
        return [v for v in (payload.get("construction"), payload.get("history_note"))
                if isinstance(v, str) and v.strip()]
    return build_notes(payload)


def _payload() -> dict:
    return {"construction": CONSTRUCTION, "history_note": HISTORY,
            "note": "n", "baskets": []}


def test_build_notes_returns_construction_then_history() -> None:
    from scripts._ths_build_notes import build_notes
    assert build_notes(_payload()) == [CONSTRUCTION, HISTORY]


def test_build_notes_skips_missing_blank_and_non_string() -> None:
    from scripts._ths_build_notes import build_notes
    assert build_notes(None) == []
    assert build_notes([]) == []
    assert build_notes({}) == []
    assert build_notes({"construction": "   ", "history_note": 5}) == []
    assert build_notes({"history_note": HISTORY}) == [HISTORY]


def test_lite_page_paints_the_committed_notes() -> None:
    html = _render(lite=True, build_notes=_notes(_payload()))
    seg = _between(html, 'id="build-notes"', "</details>")
    order = ["How these baskets are built", "篮子构建说明",
             "point-in-time dated membership",
             "Series before a name&#39;s add date is a backtest"]
    for needle in order:
        assert needle in seg, f"missing from the build-notes block: {needle!r}"
    idx = [seg.index(n) for n in order]
    assert idx == sorted(idx), f"wrong order in the block: {order}"


def test_notes_are_escaped() -> None:
    html = _render(lite=True, build_notes=["<script>alert(1)</script>"])
    seg = _between(html, 'id="build-notes"', "</details>")
    assert "<script>alert(1)" not in seg
    assert "&lt;script&gt;" in seg


def test_no_block_without_notes_or_off_the_lite_page() -> None:
    for ctx in (dict(lite=True, build_notes=[]),
                dict(lite=True),
                dict(lite=False, build_notes=[CONSTRUCTION, HISTORY])):
        html = _render(**ctx)
        assert 'id="build-notes"' not in html, f"block leaked: {ctx}"
        assert "<div id=\"details\"></div>\n  </div>" in html, (
            f"whitespace residue with no block: {ctx}")
    html = _render(lite=True, build_notes=[CONSTRUCTION, HISTORY])
    assert "</details>\n  </div>" in html, "whitespace residue with the block"


def test_lite_canonical_and_og_url_point_at_the_ths_page() -> None:
    html = _render(lite=True)
    canonical = _between(html, '<link rel="canonical" href="', '">')
    assert canonical.endswith("/baskets_china_ths.html"), canonical
    og_url = _between(html, '<meta property="og:url" content="', '">')
    assert og_url.endswith("/baskets_china_ths.html"), og_url


def test_lite_description_claims_no_absent_surface() -> None:
    html = _render(lite=True)
    desc = _between(html, '<meta name="description" content="', '">')
    for absent in ("theme scores", "leadership health", "entry radar",
                   "Asia close"):
        assert absent not in desc, f"lite description still claims {absent!r}"
    assert 50 <= len(desc) <= 170, f"description length {len(desc)} out of range"
    og_desc = _between(html, '<meta property="og:description" content="', '">')
    assert og_desc == desc


def test_non_lite_seo_is_unchanged() -> None:
    html = _render(lite=False)
    canonical = _between(html, '<link rel="canonical" href="', '">')
    assert canonical.endswith("/baskets_china.html"), canonical
    desc = _between(html, '<meta name="description" content="', '">')
    assert desc == SEED_DESC


def test_new_template_lines_add_no_style_or_colour_literal() -> None:
    src = (_ROOT / "templates" / "baskets_china_factorwatch.html.j2").read_text(
        encoding="utf-8").splitlines()

    def _block(start_needle: str, end_needle: str) -> list:
        out, started = [], False
        for line in src:
            if not started and start_needle in line:
                started = True
            if started:
                out.append(line)
                if end_needle in line:
                    break
        return out

    # Locate the two inserted blocks by their unique markers. The SEO marker
    # includes the ``set seo_path`` form: the bare filename also appears on two
    # pre-existing link lines (:259, :369) that are not part of this change.
    checked = (_block('seo_path = "baskets_china_ths.html"', "{% endif %}")
               + _block('id="build-notes"', "</details>"))
    for line in checked:
        assert "style=" not in line, line
        assert "<style" not in line, line
        assert not re.search(r"#[0-9a-fA-F]{3,6}", line), line
        assert "rgb(" not in line and "hsl(" not in line, line
        assert "|safe" not in line, line
