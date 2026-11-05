---
key: FDA-UNAVAILABLE-CHIP-IS-CORRECT-THE-DRIP-NEVER-QUALIFIED
claim: >
  The foresight FDA supply chip reading "FDA source unavailable — no qualified generation on
  file, refresh failed" is CORRECT behaviour, not a rendering or semantics defect, and three
  non-obvious facts are why. (1) The observation sidecar is `data/fda/shortages.observation.json`
  — NOT `data/fda/shortages.parquet.observation.json`. The parquet and its sidecar are siblings,
  not a path plus a suffix, so a watcher that derives the sidecar path by concatenating
  `.observation.json` onto the parquet path watches a file that does not exist and never will.
  (2) That sidecar is refreshed ONLY by a bounded, keyless, explicitly NON-FATAL drip inside
  `scripts/build_foresight.py` (`except Exception: log.warning("fda_shortages drip failed
  (non-fatal)")`), and `RENDER_NO_DRIP=1` skips the drip entirely because that lane "makes no
  network calls and discards data/ writes". So a `daily.yml` run concluding SUCCESS is NOT
  evidence that the FDA drip ran, and a render can never advance this artifact at all.
  (3) As of 2026-09-28 the sidecar has never held a qualified generation: `selected_capture:
  null`, `parquet_sha256: null`, `predecessor: null`, and `last_refresh` = `{attempted_at:
  2026-09-27T06:08:08Z, failure_code: "PAGE_FAILED", partial_rows_observed: 0, qualified:
  false}`. `collect_shortage_sweep` increments `pages` only after a page fully parses and clears
  the repeated-page check (`collectors/fda_shortages.py:229`), and every failure branch spells
  `"PAGE_FAILED" if pages else "FIRST_PAGE_OUTAGE"` — so `PAGE_FAILED` with zero retained rows
  means page 1 parsed cleanly and yielded nothing, then a later page failed. `qualified: false`
  then drives `summarize_supply` (`engine/fda_scarcity.py:243`) to `_UNAVAILABLE`, and with no
  generation on file `_label` selects exactly the leaf the live chip shows. The public seam is
  doing the job D1 built it to do: refuse to state supply from an unqualified capture
  (`NO_SOURCE_GENERATION`). The live data-availability condition is upstream in the openFDA
  sweep, not in the theme feed.
falsifier: >
  Read `data/fda/shortages.observation.json` on `origin/main`. If `selected_capture` is
  non-null and `last_refresh.qualified` is true while the served foresight chip still reads
  "source unavailable", this claim is refuted and the defect IS in the seam. Equally refuting:
  a `data/fda/shortages.parquet.observation.json` appearing on `origin/main` (the path claim),
  or a `fda_shortages` drip failure that fails a `daily.yml` run (the non-fatality claim).
so_what: >
  Stops two expensive misreads. A session that treats the UNAVAILABLE chip as a D1 regression
  will go rewrite a public seam that is already correct, and re-introduce the exact defect D1
  removed — asserting supply from an unqualified capture. A session that waits on the sidecar
  to change after a green nightly will wait forever on a non-fatal drip, and one that watches
  `<parquet>.observation.json` will wait forever on a path that does not exist (measured: an
  18 h capture window expired against that path while the real sidecar sat on main the whole
  time). Also scopes the banned-substring gate: D1's ban is CHIP-scoped, and a page-wide grep
  of foresight.html finds `glut` and `catching up` in the pre-existing cross-theme lifecycle
  legend ("7/18 themes have a glut read", "supply catching up — exit clock") and in the page
  methodology prose — neither is healthcare copy and neither is a regression.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  `git ls-tree -r --name-only origin/main -- data/fda` (two entries: `shortages.observation.json`,
  `shortages.parquet`; no `.parquet.observation.json` anywhere in the tree) ·
  `git show origin/main:data/fda/shortages.observation.json` (the null capture + PAGE_FAILED
  body quoted above) · `sed -n '84,118p' scripts/build_foresight.py` (the NO_DRIP skip and the
  non-fatal `except`) · `sed -n '160,235p' collectors/fda_shortages.py` (`pages = 0`,
  `pages += 1` at 229, the `if pages else` failure-code branches) ·
  `sed -n '225,262p' engine/fda_scarcity.py` (`if qualified is False: source_status =
  _UNAVAILABLE`) · live capture of https://www.mastermind-x.com/foresight.html 2026-09-28T06:0xZ
  with a nested-span-aware matcher: 43 `fx-chip` anchors, 1 medical chip, EN+ZH both present,
  zero `U+1F48A` pill glyphs, banned substrings 0 inside the chip.
scope: macro
confidence: verified
---

## Why the sequencing hypothesis was wrong

D1 shipped with a published falsifier: *after the first post-merge nightly writes the FDA
observation sidecar and a later render bakes it, the chip MUST leave `UNAVAILABLE`; if it still
reads "source unavailable" then the cause is NOT sequencing.* The post-merge nightly
(`daily.yml` run `36367461114`) concluded **success** at 2026-09-28T01:49:36Z and wrote no new
sidecar at all — the recorded `attempted_at` stayed at 2026-09-27T06:08:08Z, one day stale.

So the falsifier's antecedent never fired, and the reason is structural rather than incidental:
a non-fatal drip cannot make its own failure visible in the run conclusion that contains it.
The sequencing hypothesis was not merely unproven — it was unprovable by the instrument chosen,
because the nightly's exit code is blind to the only step that matters here.

## What is actually owed, and to whom

Nothing in `engine/fda_scarcity.py` or the theme feed. The seam's refusal is the designed
`NO_SOURCE_GENERATION` behaviour and its copy is accurate down to the leaf.

The open condition belongs to the openFDA sweep in `collectors/fda_shortages.py`: no qualified
generation has ever been selected. That is deliberately degraded-not-fatal by design, so it is
a feed-availability matter for the collector's owner and NOT a Healthcare product change — the
Healthcare program consumes this feed and mints no part of it. Fixing paging behaviour against
an upstream endpoint whose failure cannot be reproduced from here would be speculative repair
of production collector code, which is why this record reports the condition with exact evidence
instead of changing the sweep.
