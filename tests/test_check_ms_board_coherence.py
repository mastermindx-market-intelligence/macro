"""ui.ms_board_coherence guard — unit tests for scripts/check_ms_board_coherence.

Three duties:
  1. The guard catches the REAL 2026-07-07 hybrid (commit 5bf116a3b3: upstream's
     score 56/"Mixed" stitched beside the replayed render's stale Risk-off thesis,
     "Risk Radar forces Risk-off." note and Risk-off flip line) and passes both
     coherent boards it was stitched from (7a1c30ced4 / d944f0d713 shapes).
  2. Drift-pin: every constant the guard mirrors from engine/market_state.py
     (score bands, verdict labels, headline prefixes, override note strings,
     flip-line shapes) is asserted against the engine, so an engine reword
     cannot silently defang the guard. Skips where pandas is unavailable.
  3. --heal-from restores an incoherent page wholesale from a git ref.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import check_ms_board_coherence as guard

SCRIPT = Path(guard.__file__).resolve()

# The ms-verdict section of commit 5bf116a3b3's site/macro.html, verbatim
# (the incident this guard exists for — do not "fix" this fixture).
HYBRID_5BF116A3B3 = """<section class="ms-verdict">
          <p class="v-label"><span class="l-en">Verdict</span><span class="l-zh">结论</span></p>
          <p class="v-word" id="ms-word"><span class="l-en">Mixed</span><span class="l-zh">混合</span><span class="arr">▶</span></p>
          <div class="v-scorerow"><span class="v-score" id="ms-score">56</span><span class="v-outof">/ 100</span></div>
          <div class="v-meter"><span class="tick" id="ms-tick" style="left:56%"></span></div>
          <div class="v-scale"><span>0</span><span>42</span><span>60</span><span>100</span></div>
          <p class="v-thesis"><span class="l-en">Risk-off — stress is elevated; defend capital first.</span><span class="l-zh">避险 — 压力升高；优先防守。</span></p>
          <p class="v-override"><span class="ic">⚠</span><span class="l-en">Risk Radar forces Risk-off.</span><span class="l-zh">风险雷达强制为「避险」。</span></p>
          <p class="v-flip"><span class="l-en">→ Mixed when trend & technicals stabilises and stress fades.</span><span class="l-zh">→ 待趋势与技术企稳且压力护栏解除后转为「混合」。</span></p>
        </section>"""


# ── 1. incident + fixture behaviour ──────────────────────────────────────────

def test_real_hybrid_fails():
    v = guard.check_text("hybrid", HYBRID_5BF116A3B3)
    kinds = {line.split(")")[0].strip("( ") for line in v}
    assert {"c", "d", "g"} <= kinds, v  # thesis, forces-note, flip-shape all trip


def test_coherent_boards_pass():
    assert guard.check_text("mixed", guard.FIX_COHERENT_MIXED) == []
    assert guard.check_text("riskoff", guard.FIX_COHERENT_RISKOFF) == []
    assert guard.check_text("intl", guard.FIX_INTL_FORCES_OK) == []


def test_selftest_green():
    assert guard._selftest() == 0


def test_pages_without_board_skip():
    assert guard.check_text("none", "<html><body>hi</body></html>") == []


def test_garbled_board_is_loud():
    v = guard.check_text("garbled", '<section class="ms-verdict"><p>x</p></section>')
    assert v and "unparseable" in v[0]


def test_styled_live_thesis_class_still_catches_cross_band_contradiction():
    html = guard._board(
        "Risk-on", 61,
        "Risk-off — stress is elevated; defend capital first.",
        "", "→ Mixed if risk appetite breaks down."
    ).replace('class="v-thesis"', 'class="v-thesis ms-green"')
    v = guard.check_text("styled-thesis", html)
    assert any(line.startswith("(c)") for line in v), v


def test_styled_thesis_with_other_attributes_still_catches_contradiction():
    html = guard._board(
        "Risk-on", 61,
        "Risk-off — stress is elevated; defend capital first.",
        "", "→ Mixed if risk appetite breaks down."
    ).replace(
        'class="v-thesis"',
        'data-live="1" class="ms-green v-thesis emphasized" aria-live="polite"',
    )
    v = guard.check_text("attributed-styled-thesis", html)
    assert any(line.startswith("(c)") for line in v), v


def test_participation_qualified_risk_on_theses_remain_in_formal_risk_on_band():
    for headline in (
        "Broad risk-on — participation confirms the move.",
        "Selective risk-on — participation is weak.",
        "Risk-on — participation is unverified.",
    ):
        html = guard._board(
            "Risk-on", 61, headline, "", "→ Mixed if risk appetite breaks down."
        ).replace('class="v-thesis"', 'class="v-thesis ms-green"')
        assert guard.check_text("qualified-risk-on", html) == []


def test_macro_path_cannot_lag_settled_board_date():
    html = """
    <span id="regime-asof">2026-09-14</span>
    <span id="ms-score">56</span>
    <svg class="mx5-path-svg" data-points='[{"d":"2026-09-11","s":66,"v":"Risk-on"}]'></svg>
    """
    v = guard.check_text("site/macro.html", html)
    assert len(v) == 1 and "stale versus settled board" in v[0]


def test_non_macro_path_may_keep_independent_history_clock():
    html = """
    <span id="regime-asof">2026-09-14</span>
    <span id="ms-score">56</span>
    <svg class="mx5-path-svg" data-points='[{"d":"2026-09-11","s":66,"v":"Risk-on"}]'></svg>
    """
    assert guard.check_text("site/china.html", html) == []


def test_macro_path_uses_measured_blend_when_display_score_is_capped():
    html = """
    <span id="regime-asof">2026-09-08</span>
    <span id="ms-score" data-measured-score="77">59</span>
    <svg class="mx5-path-svg" data-points='[{"d":"2026-09-08","s":77,"v":"Risk-on"}]'></svg>
    """
    assert guard.check_text("site/macro.html", html) == []


# ── 2. drift-pin against engine/market_state.py ──────────────────────────────

ms = pytest.importorskip("engine.market_state", reason="engine deps (pandas) unavailable")


def test_bands_match_engine():
    for word, (lo, hi) in guard.BANDS.items():
        assert ms._LABEL[ms._verdict_from_score(lo)][0] == word
        assert ms._LABEL[ms._verdict_from_score(hi)][0] == word
    # band edges are exactly the engine's thresholds
    assert ms._verdict_from_score(41) == "RISK_OFF" and ms._verdict_from_score(42) == "MIXED"
    assert ms._verdict_from_score(59) == "MIXED" and ms._verdict_from_score(60) == "RISK_ON"
    assert set(guard.BANDS) == {v[0] for v in ms._LABEL.values()}


def test_headline_prefixes_match_engine():
    label_of = {k: v[0] for k, v in ms._LABEL.items()}
    for verdict, (head_en, _zh) in ms._HEADLINES.items():
        assert head_en.startswith(guard.HEADLINE_ALLOWED_PREFIX[label_of[verdict]])

    asof = "2026-09-18"
    fresh = {"pct_above_200": {"asof": asof, "stale": False}}
    for breadth in (0, 50, 75):
        comps = [{"key": "breadth", "score": breadth, "degraded": False}]
        head_en, _ = ms._headline_for(
            "RISK_ON",
            comps,
            market="us",
            asof=asof,
            input_vintages=fresh,
        )
        assert head_en.startswith(guard.HEADLINE_ALLOWED_PREFIX["Risk-on"])

    unverified, _ = ms._headline_for(
        "RISK_ON", [], market="us", asof=asof, input_vintages={}
    )
    assert unverified.startswith(guard.HEADLINE_ALLOWED_PREFIX["Risk-on"])


def test_note_strings_match_engine():
    src = inspect.getsource(ms)
    assert guard.NOTE_FORCES in src            # _radar_override + _radar_override_intl
    assert guard.NOTE_CAPPED in src            # _radar_override
    assert guard.NOTE_FORCED_GENERIC in src    # stress / dislocation overrides
    assert guard.NOTE_CAPPED_GENERIC in src.lower()  # alert / regime overrides


def test_flip_shapes_match_engine():
    comps = [
        {"score": 10, "label_en": "Trend & technicals", "label_zh": "趋势"},
        {"score": 80, "label_en": "Breadth", "label_zh": "广度"},
    ]
    label_of = {k: v[0] for k, v in ms._LABEL.items()}
    seen = {}
    for verdict in ("RISK_ON", "MIXED", "RISK_OFF"):
        flip_en, _ = ms._flip_text(comps, verdict)
        for prefix, expected_word in guard.FLIP_PREFIX.items():
            if flip_en.startswith(prefix):
                seen[verdict] = prefix
                assert expected_word == label_of[verdict], (verdict, flip_en)
    assert set(seen) == {"RISK_ON", "MIXED", "RISK_OFF"}, seen


def test_radar_ceiling_note_boundary_matches_engine():
    # The "forces" note fires strictly below the Mixed floor — the same 42 the
    # guard's Risk-off band ends under (score = min(score, ceiling) <= 41).
    src = inspect.getsource(ms._radar_override)
    assert "if ceiling < 42" in src
    assert guard.BANDS["Risk-off"][1] == 41 and guard.BANDS["Mixed"][0] == 42


# ── 3. --heal-from restores from a git ref ───────────────────────────────────

def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_heal_from_restores_coherent_page(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    page = tmp_path / "macro.html"
    page.write_text(guard.FIX_COHERENT_MIXED, encoding="utf-8")
    _git(tmp_path, "add", "macro.html")
    _git(tmp_path, "commit", "-q", "-m", "coherent")
    page.write_text(HYBRID_5BF116A3B3, encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--heal-from", "HEAD", str(page)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert guard.check_page(page) == []
    assert "healed" in res.stdout


def test_heal_from_reports_unhealable(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    page = tmp_path / "macro.html"
    page.write_text(HYBRID_5BF116A3B3, encoding="utf-8")  # incoherent at the ref too
    _git(tmp_path, "add", "macro.html")
    _git(tmp_path, "commit", "-q", "-m", "already broken")

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--heal-from", "HEAD", str(page)],
        capture_output=True, text=True,
    )
    assert res.returncode == 1
    assert "STILL INCOHERENT" in res.stdout


def test_board_score_parser_accepts_runtime_metadata_after_id():
    html = """<section class="ms-verdict">
      <p class="v-thesis"><span class="l-en">Risk-on — the tape is constructive.</span></p>
      <p class="v-flip"><span class="l-en">→ Mixed if risk appetite breaks down.</span></p>
      <span class="v-score" id="ms-score" data-measured-score="61">61</span>
      <p class="v-word" id="ms-word"><span class="l-en">Risk-on</span></p>
      <span id="ms-tick" style="left:61%"></span>
    </section>"""
    assert guard.check_text("site/macro.html", html) == []
