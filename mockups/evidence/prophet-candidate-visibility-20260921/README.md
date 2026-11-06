# Prophet candidate visibility — current source browser evidence

Status: BUILT_NOT_PROVEN. Local component evidence, not deployment or authenticated service proof.

## Exact scope and source

Runtime/source head under test: `7665039b6eae9deb5fecb574ce958565de60ef74` on macro PR #7572. This evidence-only continuation changes no engine, builder, template, scoring, entry, portfolio, archive writer or workflow byte.

Input ref: `4bf1b3aee532114b0c67e06c532b6e4ed7884549`.
- Board: `site/factordata/us_standouts.json`, Git blob `75dbaa49f475214580fee22fac3322b6913a7fd1`.
- Candidate archive: `data/us_prophet_rank/candidates/2026-09.parquet`, Git blob `db7bad2ebc63986d9111e41df2ba4298ed4d9164`.

The proof script materializes the exact archival blob only in a temporary input fixture and calls the canonical archive reader. No canonical archive is written or repaired. The date, definition, curated tier and saved fields must agree; no exact-generation or investment-performance claim follows.

## Two clearly separate browser proofs

`manifest.json` is emitted by the unchanged `scripts/capture_page_evidence.py` producer using its real Playwright driver. It contains eight anonymous REST cells and eight real focus-interaction cells: desktop/mobile x EN/ZH x dark/light. Only the anonymous preview page is navigated; its three preview rows are unchanged. The REST cells show the collapsed component; focus cells show its actual summary focus. The screenshot files are content-addressed and checked by the existing visual-evidence guard.

`expanded/` contains eight fresh screenshots and the existing proof script's result. This separate semantic browser test expands the component with the keyboard, exercises an explicitly SIMULATED authorized payload callback, searches AMD, filters names outside the main list, tests no-match state, preserves source order, and refuses mixed-generation/partial/repeated data. It is NOT authentication or production proof. These expanded screenshots, not the collapsed REST cells alone, show the history disclosure and the responsive contents a design reviewer must judge.

The observed source pool contains 66 eligible names: 52 on the main list, 14 outside it, with three anonymous preview rows and 63 in the protected remainder. AMD remains T1, sector-cap-displaced, unscored and marked `archive_state=missing`. The rendered history summary is 0/66 matching candidate records. Matching fields would still not prove exact build-generation identity.

## Visual review

The existing design was preserved: compact closed disclosure, readable count/reason hierarchy, row details hidden until requested, white panel/hairline treatment in light and dark panel/text contrast in dark. Desktop light EN and mobile dark ZH expanded captures were visually inspected; the eight expanded views have no horizontal overflow. The native focus matrix separately records actual applied theme/locale/viewport and keyboard-focus state.

No new light/dark palette, navigation, interaction or trading semantics were introduced by this continuation. Independent design/source acceptance remains required.

## Reproduction

From the PR checkout, run the existing `research/prophet/cpu_leadership/prove_visibility.py` with `--source-ref 4bf1b3aee532114b0c67e06c532b6e4ed7884549 --out <isolated proof directory>`.

Then run `scripts/capture_page_evidence.py --site-dir <isolated proof directory> --routes /preview.html --viewports desktop,mobile --locales en,zh --themes light,dark --force-state 'focus:focus(.ucp>summary)'`, binding its output directory, manifest and smell report to this evidence folder. This captures only anonymous preview bytes; do not use an authenticated browser profile.

The previous optional combined proof-script-edit command was platform-blocked and was not retried. Same-file readback confirms those proposed extra edits did not occur. The small already-successful archive-input changes and existing proof runner executed successfully; canonical screenshots were generated separately by the incumbent evidence producer, not by synthesizing a manifest or changing a guard.
