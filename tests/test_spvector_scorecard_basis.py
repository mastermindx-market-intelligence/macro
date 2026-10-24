"""Scorecard-basis lane tests for the S&P Vector page (wave W23-L13).

Pins: the overlay forward-log reader ``_overlay_log_summary`` (rows, distinct
asof days, veto days — a day counts as a veto day when ANY row logged that day
carried veto True), the header's backtest-window line, the bootstrap resample
range / above-zero share / resample-basis lines on the scorecard, and the
turnover-bound tax note. Synthetic fixtures only: ``build()`` is never run,
``site/``/``data/`` are never read, no network; log files live under tmp_path.

Run: python -m tests.test_spvector_scorecard_basis
"""
from __future__ import annotations

import copy
import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_vector import C  # noqa: E402
from tests.test_spvector_page import _env, _spvector_vm  # noqa: E402

# Shape of the committed bootstrap record (reports/spvector-phase3-audit.md).
BOOT = {"sharpe_ci": [0.58, 0.88, 1.2], "maxdd_ci_pct": [-44.5, -28.2, -17.7],
        "sharpe_gt0_prob": 1.0, "block": 21, "B": 5000, "n": 8487}
# Shape of the committed forward log (430 rows / 76 distinct asof days).
LOG = {"rows": 430, "days": 76, "vetoes": 0,
       "first": "Jun 12, 2026", "last": "Oct 16, 2026"}
NOVETO = {"enabled": True, "veto": False, "veto_reason": "",
          "mechanical_weight": 1.0, "overlay_weight": 1.0,
          "note": "LLM context — Fed guidance tightening, tone +0.60, risk D +0.40",
          "disclaimer": "Context overlay — NOT in the backtest; advisory + tracked forward."}


def _row(asof, veto=False):
    return {"asof": asof, "logged": "2026-10-16T22:00:00+00:00", "veto": veto,
            "mechanical_weight": 1.0, "overlay_weight": 1.0,
            "shock_reversible": "unknown", "tone_score": 0.0,
            "confidence": "high", "note": "n"}


def _log_file(tmp_path, lines):
    p = tmp_path / "overlay_log.jsonl"
    p.write_text("".join(ln + "\n" for ln in lines), encoding="utf-8")
    return p


def _summary(tmp_path):
    """The lane helper under test — attribute accessed lazily so HEAD is red."""
    from scripts import build_spvector
    return build_spvector._overlay_log_summary(tmp_path)


def _vm(bootstrap=None, **updates):
    """Deep copy of the page fixture with optional bootstrap-dict / vm overrides."""
    vm = copy.deepcopy(_spvector_vm())
    if bootstrap is not None:
        vm["sc"]["bootstrap"] = bootstrap
    vm["sc"]["years"] = 33.7
    vm.update(updates)
    return vm


def _render(bootstrap=None, **updates):
    return _env().get_template("spvector.html.j2").render(**_vm(bootstrap, **updates), C=C)


def _region(html, start, end):
    s = html.index(start)
    return html[s:html.index(end, s)]


def _header(html):
    return _region(html, '<div class="h1">', '<div class="tag">')


def _scorecard(html):
    return _region(html, "<!-- ===== scorecard tiles ===== -->",
                   "<!-- ===== allocation rule-book ===== -->")


def _overlay_card(extra, overlay):
    """Render with the overlay card present; return just that card's region."""
    vm = _vm()
    vm["overlay"] = overlay
    vm.update(extra)
    html = _env().get_template("spvector.html.j2").render(**vm, C=C)
    return _region(html, "<!-- ===== LLM context",
                   "<!-- ===== risk-score leg breakdown")


def _tile(html, label):
    lines = [ln for ln in html.splitlines()
             if '<div class="card score">' in ln and label in ln]
    assert len(lines) == 1, f"expected exactly one {label!r} tile, got {len(lines)}"
    return lines[0]


def test_log_summary_counts_days_rows_and_veto_days(tmp_path):
    # rows deliberately OUT of date order; one date has mixed veto rows and the
    # day still counts once (rule: ANY row for the day with veto True).
    p = _log_file(tmp_path, [json.dumps(r) for r in (
        _row("2026-06-15"), _row("2026-06-12", True),
        _row("2026-06-12", True), _row("2026-06-12"))])
    assert _summary(p) == {"rows": 4, "days": 2, "vetoes": 1,
                           "first": "Jun 12, 2026", "last": "Jun 15, 2026"}


def test_log_summary_skips_bad_lines(tmp_path):
    good = [json.dumps(r) for r in (
        _row("2026-06-15"), _row("2026-06-12", True),
        _row("2026-06-12", True), _row("2026-06-12"))]
    bad = ["not json at all", "", "[1, 2]", '"text"',
           json.dumps({"asof": "garbage", "veto": True}),
           json.dumps({"veto": True})]
    p = _log_file(tmp_path, bad[:3] + good + bad[3:])
    assert _summary(p) == {"rows": 4, "days": 2, "vetoes": 1,
                           "first": "Jun 12, 2026", "last": "Jun 15, 2026"}


def test_log_summary_missing_or_empty_is_none(tmp_path):
    assert _summary(tmp_path / "absent.jsonl") is None
    empty = _log_file(tmp_path, [])
    assert _summary(empty) is None
    only_bad = _log_file(tmp_path, ["nope", "", "[1, 2]", '"text"'])
    assert _summary(only_bad) is None


def test_overlay_card_shows_the_forward_log():
    card = _overlay_card({"overlay_log": dict(LOG)}, dict(NOVETO))
    for s in ("Forward log", "向前记录", "76", "430", "Jun 12, 2026 → Oct 16, 2026",
              "no veto has fired yet.", "尚未触发否决。"):
        assert s in card, f"overlay card missing forward-log copy: {s!r}"
    assert "the veto fired" not in card


def test_overlay_card_counts_veto_days():
    card = _overlay_card({"overlay_log": dict(LOG, vetoes=3)}, dict(NOVETO))
    assert "the veto fired on 3 of them." in card
    assert "其中 3 天触发否决。" in card
    assert "no veto has fired yet" not in card


def test_forward_log_absent_renders_nothing():
    for extra in ({"overlay_log": None}, {}):
        card = _overlay_card(extra, dict(NOVETO))
        assert "Forward log" not in card, extra
        assert "向前记录" not in card, extra
        assert "None" not in card, extra


def test_forward_log_renders_in_every_overlay_branch():
    veto = {"enabled": True, "veto": True, "veto_reason": "shock judged a regime break",
            "mechanical_weight": 1.0, "overlay_weight": 0.66,
            "note": "", "disclaimer": NOVETO["disclaimer"]}
    for overlay in ({"enabled": False}, veto, dict(NOVETO)):
        card = _overlay_card({"overlay_log": dict(LOG)}, overlay)
        assert "Forward log" in card, f"log line missing from branch {overlay}"


def test_header_states_the_backtest_window():
    html = _render(bench_start="Jan 29, 1993", as_of="Oct 16, 2026")
    header = _header(html)
    assert "Backtest window" in header, header
    assert "回测窗口" in header, header
    assert "Jan 29, 1993 → Oct 16, 2026 (33.7y)" in header, header


def test_header_has_no_window_without_a_start():
    for html in (_render(), _render(bench_start="")):
        header = _header(html)
        assert "Backtest window" not in header, header
        assert "→" not in header, header


def test_builder_reads_the_window_and_log_after_logging():
    from scripts.build_spvector import build
    src = inspect.getsource(build)
    assert re.search(r'"bench_start":\s*spy\.index\[0\]\.strftime\("%b %d, %Y"\)', src)
    needle = '_overlay_log_summary(config.data_dir() / "spvector" / "overlay_log.jsonl")'
    assert src.count(needle) == 1, src.count(needle)
    assert src.index("sov.log_overlay(") < src.index(needle), \
        "the log summary must read the file AFTER today's row was appended"
    for ln in src.splitlines():
        if "bench_start" in ln:
            assert not re.search(r"19\d\d|20\d\d", ln), f"hardcoded year: {ln!r}"


def test_drawdown_tile_shows_the_two_ends():
    tile = _tile(_render(bootstrap=dict(BOOT)), "Max drawdown")
    assert "-44.5%" in tile, tile
    assert "-17.7%" in tile, tile
    assert "置信区间" in tile, tile
    assert "-28.2" not in tile, "the median is the tile's own point estimate"


def test_sharpe_tile_shows_the_share_above_zero():
    tile = _tile(_render(bootstrap=dict(BOOT)), "Sharpe")
    assert "above 0 in 100% of resamples" in tile, tile
    assert "100% 的重抽样高于 0" in tile, tile
    tile = _tile(_render(bootstrap=dict(BOOT, sharpe_gt0_prob=0.996)), "Sharpe")
    assert "99.6% of resamples" in tile, tile
    assert "99.6% 的重抽样高于 0" in tile, tile
    assert "100%" not in tile, tile


def test_scorecard_states_the_resample_basis():
    scorecard = _scorecard(_render(bootstrap=dict(BOOT)))
    assert "5,000 resamples" in scorecard, scorecard
    assert "8,487 daily returns" in scorecard, scorecard
    assert "21-session blocks" in scorecard, scorecard
    assert "8,487 个日收益" in scorecard, scorecard


def test_short_bootstrap_shapes_add_nothing():
    for bootstrap in (None, {}):  # None keeps _spvector_vm()'s short sharpe_ci shape
        scorecard = _scorecard(_render(bootstrap=bootstrap))
        for bad in ("resamples", "置信区间", "above 0", "None"):
            assert bad not in scorecard, (bootstrap, bad)
        assert "-36.5%" in scorecard, bootstrap
        assert "0.9" in scorecard, bootstrap


def test_tax_note_uses_the_rendered_turnover():
    vm = _vm()
    vm["sc"]["turnover_annual"] = 1.65
    html = _env().get_template("spvector.html.j2").render(**vm, C=C)
    note = _region(html, '<div class="note r">', '<div class="foot">')
    assert "1.65×/yr" in note, note
    assert "1.65×/年" in note, note
    assert "Taxable-account warning" in note, note
    assert "~1.5" not in note, note
    assert "约 1.5" not in note, note
