"""RED-first proof for the UD-B2-W1 vol-weather fold.

The fold's central claim: `data-sx-vw-strip` (and its `data-sx-vw-chip` rows)
now live INSIDE `#sx-risk-v2` as a sub-row. Before the fold (pre-fold main),
the chips lived inside `#dlg-sentiment` as `#vsb-vol-weather-section`.

This test is RED-first evidence: when we read site/macro.html from PRE-FOLD
main (the parent of the fold commit, c22864f80967e77e6e42cd926ef00f11f7197d06),
the fold claim MUST FAIL — the pre-fold page has no `data-sx-vw-strip` inside
the risk isle, and still carries the old `#vsb-vol-weather-section` inside
`#dlg-sentiment`.

Run with: PYTHONPATH=. python -m pytest -q tests/test_ud_b2_w1_red_first_proof.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Pre-fold main = parent of the round-2 fold commit. The fold moved chips
# from #dlg-sentiment into #sx-risk-v2; pre-fold, the chips only existed
# inside the dialog.
PRE_FOLD_HEAD = "c22864f80967e77e6e42cd926ef00f11f7197d06"


def _git_show(path: str, head: str = PRE_FOLD_HEAD) -> str:
    """Read a file's contents at a given git ref without touching the worktree."""
    out = subprocess.run(
        ["git", "show", f"{head}:{path}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout


class TestUDB2W1RedFirst:
    """RED-first proof: pre-fold main MUST fail the fold claim."""

    def test_pre_fold_macro_html_has_no_vol_weather_strip_in_risk_isle(self):
        """Pre-fold main: site/macro.html has #sx-risk-v2 but NO data-sx-vw-strip
        inside it. The chips still live in #dlg-sentiment as
        #vsb-vol-weather-section + vsb-vw-row rows."""
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        # Risk isle must exist (the fold didn't delete it; it just didn't add
        # the strip to it yet)
        assert 'id="sx-risk-v2"' in macro_html, (
            "Sanity: risk isle itself must exist on pre-fold main"
        )
        # The fold's NEW marker must NOT exist in pre-fold's risk isle
        start = macro_html.index('<div class="sx" id="sx-risk-v2"')
        # Walk to matching close (depth-1)
        depth = 0
        i = start
        n = len(macro_html)
        while i < n:
            if macro_html.startswith("<div ", i) or macro_html.startswith("<div>", i):
                depth += 1
                i += 5
            elif macro_html.startswith("</div>", i):
                depth -= 1
                i += 6
                if depth == 0:
                    isle = macro_html[start:i]
                    break
            else:
                i += 1
        else:
            raise AssertionError("pre-fold risk isle never closed")
        assert "data-sx-vw-strip" not in isle, (
            "RED-first PROOF: pre-fold main must NOT have data-sx-vw-strip "
            "inside #sx-risk-v2 — that's the fold's entire claim. If this "
            "assertion fails, the pre-fold head was misidentified."
        )
        assert "data-sx-vw-chip=" not in isle, (
            "RED-first PROOF: pre-fold main must NOT have any data-sx-vw-chip "
            "rows inside #sx-risk-v2"
        )

    def test_pre_fold_macro_html_still_has_vsb_vol_weather_in_dlg_sentiment(self):
        """Pre-fold main: #vsb-vol-weather-section is still inside #dlg-sentiment.
        The fold removes it — pre-fold must still have it."""
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        assert 'id="dlg-sentiment"' in macro_html, (
            "Sanity: dlg-sentiment must exist on pre-fold main"
        )
        assert 'id="vsb-vol-weather-section"' in macro_html, (
            "RED-first PROOF: pre-fold main must STILL carry "
            "#vsb-vol-weather-section (it lives inside #dlg-sentiment pre-fold). "
            "The fold moves this out of dlg-sentiment; pre-fold must still have it."
        )
        # Old dialog-row marker must still exist pre-fold
        assert 'data-vsb-chip="' in macro_html, (
            "RED-first PROOF: pre-fold main must still carry the old "
            "data-vsb-chip= dialog-row marker (the fold retires it)"
        )

    def test_pre_fold_risk_isle_face_collapsed(self):
        """Pre-fold main: the risk isle face is hidden (display:none!important)
        and the card collapses when not expanded. The fold retires both rules
        so the dial + scar chips stay visible on glance."""
        # The collapse rules live in the inline `<style>` block of
        # site/macro.html on pre-fold (templates/theme.css at pre-fold did
        # not yet have sx-risk-v2 specific selectors). The CSS is minified
        # so we use a regex that matches any selector ending in
        # `#sx-risk-v2 .sxg-face` and containing `display:none!important`.
        import re as _re
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        # Pattern A: sx-risk-v2 .sxg-face{display:none!important;}
        collapse_rule = _re.compile(
            r"[^{}]*#sx-risk-v2\s+\.sxg-face\s*\{\s*display\s*:\s*none\s*!\s*important\s*;?\s*\}",
        )
        assert collapse_rule.search(macro_html), (
            "RED-first PROOF: pre-fold main must still hide the risk face "
            "via display:none!important — the fold retires this rule"
        )
        # Pattern B: #sx-risk-v2:not([data-open]){ ... }
        collapse_card = _re.compile(
            r"#sx-risk-v2\s*:\s*not\s*\(\s*\[data-open\]\s*\)\s*\{",
        )
        assert collapse_card.search(macro_html), (
            "RED-first PROOF: pre-fold main must still collapse "
            "#sx-risk-v2 when not expanded — the fold retires this rule"
        )

    def test_pre_fold_macro_html_chips_use_old_inline_color(self):
        """Pre-fold main: rows carry inline `style="--sg-wx-c:..."` for color.
        The fold (R-W1-F) retires this — class-based color only."""
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        # Pre-fold rows must carry inline --sg-wx-c keying
        matches = re.findall(
            r'<div\s+class="mx5-dlg-factor-row\s+vsb-vw-row"[^>]*style="[^"]*--sg-wx-c[^"]*"',
            macro_html,
        )
        assert matches, (
            "RED-first PROOF: pre-fold main rows must carry inline "
            "style=\"--sg-wx-c:...\" — the fold retires inline color keying"
        )

    def test_pre_fold_macro_html_has_internal_metric_names_on_page(self):
        """Pre-fold main: the dialog's row labels carry the engine's
        internal metric names (VIX term structure, VIX1D (intraday vol
        demand), DSPX (single-stock vol vs index)). The fold (R-W1-B)
        replaces these on the glance tier with plain clauses."""
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        # The pre-fold dialog labels carry internal metric names. The fold
        # replaces them on the glance tier.
        for phrase in (
            "VIX term structure",
            "VIX1D (intraday vol demand)",
            "DSPX (single-stock vol vs index)",
            "VIX 期限结构",
            "盘中波动需求",
            "个股波动",
        ):
            assert phrase in macro_html, (
                f"RED-first PROOF: pre-fold main must still carry {phrase!r} "
                f"on the page — the fold replaces these on the glance tier "
                f"with plain clauses (R-W1-B)"
            )

    def test_pre_fold_macro_html_has_pctile_scoreboard_on_dialog_rows(self):
        """Pre-fold main: the dialog rows carry the 'higher than N% of days'
        pctile scoreboard phrases. The fold (one-integer law) removes the
        scoreboard from the glance tier entirely."""
        macro_html = _git_show("site/macro.html", PRE_FOLD_HEAD)
        # Pre-fold has both "higher than N% of days" and "lower than N% of days"
        assert "higher than" in macro_html, (
            "RED-first PROOF: pre-fold main must still carry 'higher than N% of days' "
            "pctile scoreboard phrases — the fold retires them on the glance tier"
        )
        assert "lower than" in macro_html, (
            "RED-first PROOF: pre-fold main must still carry 'lower than N% of days' "
            "pctile scoreboard phrases — the fold retires them on the glance tier"
        )