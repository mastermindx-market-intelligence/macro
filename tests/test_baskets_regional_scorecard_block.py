"""Display contract for the HK / Canada ignition-scoreboard block (W28B SPEC 1).

scripts/build_baskets_{hk,canada}.py attach engine/ignition_audit.py scorecard() to the
ignition payload, but only the partial's one JS line ever reached the reader; the per-state
beat rates, the graded window and the alert denominator stayed invisible. These tests render
the REAL templates with the committed scoreboard values and pin the new server-side section.

Render-only by law: the seat's CI job for this file installs pytest + jinja2 only, so this
module imports NO builder (scripts/build_*.py), NO engine.*, NO lib.*, no pandas/numpy. The
helper import in test_builder_forwards_only_the_scoreboard_subset is deliberately lazy so the
RED-first run fails on render assertions, not on module collection.

Fixture values are the committed artifacts (site/hkbasketdata + canadabasketdata ignition
scoreboards) quoted by the commission: HK 532 graded / 324 alerts / 0.562 precision,
igniting 130/0.354, running 194/0.51, fading 137/0.518, idle 71/0.535, 2026-06-18..2026-08-20;
CA 336/165/0.594, 63/0.54, 102/0.5, 81/0.222, 90/0.333, 2026-06-30..2026-08-17.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_BLOCK_OPEN = '<section class="panel pad" id="ignition-reliability">'
_NR_TAIL_HK = 'data-page="allocation_hk.html"></section>'
_NR_TAIL_CA = 'data-page="allocation_canada.html"></section>'

_HK = {"market": "hk", "n_graded": 532, "n_alerts": 324, "alert_precision_4w": 0.562,
       "by_state": {"igniting": {"n": 130, "beat_rate_4w": 0.354},
                    "running": {"n": 194, "beat_rate_4w": 0.51},
                    "fading": {"n": 137, "beat_rate_4w": 0.518},
                    "idle": {"n": 71, "beat_rate_4w": 0.535}},
       "asof_range": ["2026-06-18", "2026-08-20"]}
_CA = {"market": "canada", "n_graded": 336, "n_alerts": 165, "alert_precision_4w": 0.594,
       "by_state": {"igniting": {"n": 63, "beat_rate_4w": 0.54},
                    "running": {"n": 102, "beat_rate_4w": 0.5},
                    "fading": {"n": 81, "beat_rate_4w": 0.222},
                    "idle": {"n": 90, "beat_rate_4w": 0.333}},
       "asof_range": ["2026-06-30", "2026-08-17"]}


def _render(tpl: str, **extra) -> str:
    """The builders' own env (autoescape=True) + exactly the context their render calls pass."""
    ctx = {"baskets_json": "{}", "chart_json": "[]", "ignition_json": "{}",
           "provenance_json": "{}", "freshness_json": "{}", "radar_json": "{}",
           "bench_en": "Hang Seng", "bench_zh": "恒生指数", "generated_utc": "TEST"}
    ctx.update(extra)
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template(tpl).render(**ctx)


def _block(html: str) -> str:
    """The new section's own bytes, open tag excluded, up to its closing </section>."""
    i = html.index(_BLOCK_OPEN) + len(_BLOCK_OPEN)
    return html[i:html.index("</section>", i)]


def _langs(fragment: str) -> tuple[str, str]:
    en = " ".join(re.findall(r'<span class="l-en">([^<]*)</span>', fragment))
    zh = " ".join(re.findall(r'<span class="l-zh">([^<]*)</span>', fragment))
    return en, zh


def test_hk_page_prints_each_state_beat_rate_from_the_committed_scoreboard():
    blk = _block(_render("baskets_hk.html.j2", scorecard=_HK))
    for s in ("532", "324", "56.2%", "130", "35.4%", "194", "51.0%",
              "137", "51.8%", "71", "53.5%", "2026-06-18", "2026-08-20"):
        assert s in blk, s
    for lab in ("Igniting", "点火", "Running", "运行", "Fading", "退潮", "Idle", "静止"):
        assert lab in blk, lab
    idxs = [blk.index(x) for x in ("Igniting", "Running", "Fading", "Idle")]
    assert idxs == sorted(idxs), idxs


def test_canada_page_prints_each_state_beat_rate():
    blk = _block(_render("baskets_canada.html.j2", scorecard=_CA))
    for s in ("336", "165", "59.4%", "63", "54.0%", "102", "50.0%",
              "81", "22.2%", "90", "33.3%", "2026-06-30", "2026-08-17"):
        assert s in blk, s
    for lab in ("Igniting", "点火", "Running", "运行", "Fading", "退潮", "Idle", "静止"):
        assert lab in blk, lab
    idxs = [blk.index(x) for x in ("Igniting", "Running", "Fading", "Idle")]
    assert idxs == sorted(idxs), idxs


def test_block_silent_when_nothing_graded():
    for tpl, tail in (("baskets_hk.html.j2", _NR_TAIL_HK),
                      ("baskets_canada.html.j2", _NR_TAIL_CA)):
        r1 = _render(tpl, scorecard={})
        r2 = _render(tpl)
        r3 = _render(tpl, scorecard={"market": "x", "n_graded": 0, "by_state": {}})
        assert r1 == r2 == r3
        assert _BLOCK_OPEN not in r1
        i = r1.index(tail)
        assert r1[i + len(tail): i + len(tail) + 4] == "\n\n  ", repr(
            r1[i + len(tail): i + len(tail) + 12])
        present = _render(tpl, scorecard=_HK)
        assert _BLOCK_OPEN in present
        assert "</section>\n  \n" not in present


def test_builder_forwards_only_the_scoreboard_subset():
    from scripts import _baskets_scorecard as BS
    full = {"market": "hk", "n_graded": 532, "n_alerts": 324, "alert_precision_4w": 0.562,
            "by_state": {"igniting": {"n": 130, "beat_rate_4w": 0.354}},
            "asof_range": ["2026-06-18", "2026-08-20"], "note": "n/a", "extra": 1}
    out = BS.scorecard_subset({"scoreboard": full})
    assert set(out) == {"market", "n_graded", "n_alerts", "alert_precision_4w",
                        "by_state", "asof_range"}
    assert BS.scorecard_subset({"scoreboard": {}}) == {}
    assert BS.scorecard_subset({"scoreboard": {"market": "hk", "n_graded": 0,
                                               "by_state": {}}}) == {}
    assert BS.scorecard_subset(None) == {}
    assert BS.scorecard_subset("not-a-dict") == {}
    assert BS.scorecard_subset({}) == {}


def test_copy_is_bilingual_and_never_claims_episodes():
    blk = _block(_render("baskets_hk.html.j2", scorecard=_HK))
    en, zh = _langs(blk)
    assert "basket-day" in en.lower(), en
    assert "篮子日" in zh, zh
    for w in ("episode", "independent", "trade", "signal"):
        assert w not in en.lower(), w
    for w in ("申报", "实时", "独立", "证伪"):
        assert w not in zh, w
    for w in ("falsifier", "refuted", "z-score", "percentile"):
        assert w not in en.lower() and w not in zh.lower(), w


def test_section_id_never_shadows_the_partial_js_target():
    """_baskets_desk.html.j2 writes its one-line summary into getElementById('ign-scoreboard').

    That lookup returns the FIRST element with the id, and this section renders above the
    partial, so sharing the id would let the script overwrite the whole table with one line.
    """
    for tpl, sc in (("baskets_hk.html.j2", _HK), ("baskets_canada.html.j2", _CA)):
        html = _render(tpl, scorecard=sc)
        assert html.count('id="ign-scoreboard"') == 1, tpl
        assert html.count('id="ignition-reliability"') == 1, tpl
        assert html.index('id="ignition-reliability"') < html.index('id="ign-scoreboard"'), tpl

def test_states_absent_from_by_state_are_skipped():
    sc = {"market": "hk", "n_graded": 102,
          "by_state": {"running": {"n": 102, "beat_rate_4w": None}}}
    blk = _block(_render("baskets_hk.html.j2", scorecard=sc))
    assert blk.count("<tr>") == 2, blk
    assert "Running" in blk and "运行" in blk
    assert "Igniting" not in blk and ">点火<" not in blk
    assert "Fading" not in blk and "Idle" not in blk
    assert "<td>—</td>" in blk and "None" not in blk, blk
    assert "Graded window" not in blk
    assert "alert state" not in blk


def test_no_new_css_colour_literal():
    for p in ("templates/baskets_hk.html.j2", "templates/baskets_canada.html.j2"):
        lines = (_ROOT / p).read_text().splitlines()
        assert any(_BLOCK_OPEN in ln for ln in lines), p
        i = next(n for n, ln in enumerate(lines) if _BLOCK_OPEN in ln)
        j = next(n for n in range(i + 1, len(lines)) if "</section>" in lines[n])
        seg = "\n".join(lines[i:j + 1])
        for bad in ("style=", "<style", "rgb(", "hsl(", "color-mix"):
            assert bad not in seg, (p, bad)
        assert not re.search(r"#[0-9a-fA-F]{3,6}", seg), p
