#!/usr/bin/env python3
"""Render the five PR #6932 AIB lede fixture pages.

Writes HTML under mockups/evidence/pr6932-aib-lede/fixtures/. Capture with:

    python3 mockups/evidence/pr6932-aib-lede/render_fixtures.py
    cp mockups/evidence/pr6932-aib-lede/fixtures/pr6932_aib_*.html site/
    python3 scripts/capture_page_evidence.py \\
      --site-dir site \\
      --routes /pr6932_aib_many.html,/pr6932_aib_one.html,/pr6932_aib_quiet.html,/pr6932_aib_degraded.html,/pr6932_aib_stale.html \\
      --viewports desktop,mobile --locales en,zh --themes dark,light \\
      --max-pages 5 --settle-ms 1200 \\
      --output-dir mockups/evidence/pr6932-aib-lede \\
      --manifest mockups/evidence/pr6932-aib-lede/manifest.json \\
      --smells /tmp/pr6932-aib-lede-smells.json \\
      --as-of 2026-09-07T21:00:00+00:00
    rm -f site/pr6932_aib_*.html

Then rewrite absolute /Users/… paths in the manifest to repo-relative forms.
Never git-add anything under site/ or data/.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.build_options_command import build_aib, render  # noqa: E402
from tests.test_build_options_command import EMPTY_STORES  # noqa: E402
from tests.test_options_command_aib import NOW, _brief, _card  # noqa: E402

OUT = Path(__file__).resolve().parent / "fixtures"

# Keep the search box empty for the whole capture settle window. theme.js
# hydrates the unified ticker search after load; a leftover value (seen as
# `60051|` in the round-2 crops) is noise in a receipt.
_CLEAR_NAV_SEARCH = """
<style>.nav-search .idle-ticker{visibility:hidden!important}</style>
<script>
(function () {
  function clearNavSearch() {
    document.querySelectorAll('.nav-search input, .ticker-input').forEach(function (el) {
      el.value = '';
      el.blur();
    });
    document.querySelectorAll('.idle-ticker').forEach(function (el) {
      el.textContent = '';
    });
  }
  clearNavSearch();
  document.addEventListener('DOMContentLoaded', clearNavSearch);
  window.addEventListener('load', function () {
    clearNavSearch();
    var n = 0;
    var id = setInterval(function () {
      clearNavSearch();
      n += 1;
      if (n > 80) clearInterval(id);
    }, 50);
  });
})();
</script>
"""


def _write(name: str, html: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    if "</body>" in html:
        html = html.replace("</body>", _CLEAR_NAV_SEARCH + "</body>", 1)
    else:
        html = html + _CLEAR_NAV_SEARCH
    path = OUT / name
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    many = _brief(
        board_state="OK",
        opportunities=[_card("AAA", r=1), _card("BBB", r=2), _card("CCC", r=3)],
        eligible=10, present=20, as_of="2026-09-03",
    )
    one = _brief(
        board_state="OK",
        opportunities=[_card("AAA", r=1)],
        eligible=10, present=20, as_of="2026-09-03",
    )
    quiet = _brief(
        board_state="NO_SIGNAL",
        opportunities=[],
        eligible=10, present=20, as_of="2026-09-03",
    )
    degraded = _brief(
        board_state="STALE_SOURCE",
        opportunities=[],
        eligible=0, present=20, as_of="2026-09-03",
    )
    # Motivating exemplar: 2026-08-19 / 0/39, plural sessions behind + is-stale.
    stale = _brief(
        board_state="STALE_SOURCE",
        opportunities=[],
        eligible=0, present=39, as_of="2026-08-19",
        receipt_id="637d0c60ec86aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    # Clock after several completed sessions so 2026-08-19 is stale (>3).
    stale_now = datetime(2026, 9, 4, 22, 0, tzinfo=timezone.utc)

    specs = (
        ("pr6932_aib_many.html", many, NOW),
        ("pr6932_aib_one.html", one, NOW),
        ("pr6932_aib_quiet.html", quiet, NOW),
        ("pr6932_aib_degraded.html", degraded, NOW),
        ("pr6932_aib_stale.html", stale, stale_now),
    )
    for name, brief, clock in specs:
        out = build_aib(brief, now=clock)
        fresh = out["freshness"]
        print(
            f"{name}: lede_key cards={len(out['cards'])} healthy={out['healthy']} "
            f"slug={out['lede_stance_slug']!r} word_en={out['lede_stance_word_en']!r} "
            f"said_en={out['lede_stance_en']!r} level={fresh['level']} "
            f"days_behind={fresh['days_behind']} age_en={fresh['age_en']!r}"
        )
        path = _write(name, render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=clock))
        print(f"  wrote {path.relative_to(REPO)} ({path.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
