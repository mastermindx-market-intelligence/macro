# Macro workspace — source verification checkpoint

Authority and intended outcome are in [PLAN.md](PLAN.md). This is source/fixture verification, not production acceptance.

## What changed

- A US-scoped page identity, passive sticky section index, six semantic reading groups and physical DOM order matching visual/keyboard order.
- A calmer neutral material system in both themes, compact outlook and gauges, explicit native detail actions, readable full-length bilingual agenda, improved tape and research links.
- Mobile history with keyboard and touch inspection; selected dates survive live replacement; invalid data clears stale interaction, disables the control and safely restores focus; provisional/latest state is explicit in both languages.
- A native phone driver rail with next-card affordance, stable heights, keyboard reachability and verified dialog return.
- Honest missing sentiment/history/outlook states, with real sentiment zero preserved. Producer semantics, score calculations, account/access behavior and existing dialog lifecycle remain with their current owners.

## Verification completed before source commit

- `tests/test_macro_workspace_browser.py`: **31 passed** in 33.98 seconds on the final populated/unavailable fixture and runtime bytes. Ten viewport/theme/language combinations include 1440, 768, 390 and 320px; interaction cases cover native anchors/Back/focus, nine detail buttons, keyboard/touch history, live replacement, invalid-data recovery, language switching, real zero, unavailable data and no-JavaScript reading.
- Affected existing analytical/render/interaction checks: initial run **200 passed, 2 failed, 1 deselected**. The failures were legacy card-slicing assumptions after actual DOM reordering. `_face` now uses the real HTML element; **five targeted checks passed** after repair. The deselected source-receipt check awaits genuine recapture from committed source.
- New CI owner/curated scope closure: **2 passed** in 313.30 seconds. Browser fixture uses a frozen explicit VM to avoid importing unrelated collectors.
- Shared design guard: zero blocking findings; incumbent nonblocking findings remain unchanged in scope. Runtime style-injection guard passed. Both new JS includes passed `node --check`; whitespace checks passed.
- Visual self-check: desktop/light and dark, phone/light and dark, EN/ZH; scrolled desktop Briefing and mobile driver dialog return inspected from actual browser PNGs. Chinese date wrapping, gauge contrast/size, driver rail height and populated alert-row overflow were corrected before the final 31-case pass.

## Fixture honesty and limits

The fixture inputs are identified in `tests/fixtures/macro_workspace/SOURCE.md`. Headlines, history, market values and account state are explicit test observations; collectors and service polling are stopped only in the local harness. Captures do not prove authenticated production behavior or market correctness. Existing canonical EW/W9 suites provide their separate established fixture coverage.

The shared navigation cold-load shift remains with held carrier #10261 (approximately 0.723 baseline versus 0.702 candidate in the same local laboratory). The frozen rate-card semantic discrepancy remains with #10493. Neither is concealed by a new page controller or an assertion of full production readiness.

The first source-bound full-page capture revealed an empty priorities card when all contributing observations were absent. A final bilingual unavailable message now fills that specific state while retaining the evidence action. The affected browser and incumbent priorities suites passed **8/8** in 5.87 seconds. Earlier captures remain intermediate; the release packet is recaptured after this correction.

## Release path

Source commit, genuine recapture and receipt binding are complete below. Publish the ready PR through the existing merge controller. Then obtain the merged SHA, covering Jinja render, and actual live browser proof. Source/CI alone are insufficient.

## Committed-source capture and final checks

Capture source: `fca9114d922d21a3b88e6406b02e2368da66db9c`.

- Full workspace: **16/16** populated/unavailable × desktop/mobile × EN/ZH × light/dark, using `scripts/capture_page_evidence.py`. No page console errors, failed responses, duplicate visible headings, raw slugs, placeholders or horizontal overflow in the recorded viewport measurements. The heuristic as-of/source flags are not a semantic verdict; the measured path visibly identifies its settled date, while supporting source detail remains in the existing evidence destinations.
- Full browser suite rerun on that source: **31 passed** in 31.91 seconds. Five screenshots were captured inside asserted interaction states, with actual source blobs and image hashes recorded in `journeys.json`.
- Existing W9 capture owner: **74/74** states, source SHA recorded in `mockups/evidence/macro-w9/manifest.json`; no fabricated receipt or screenshot reuse.
- Existing EW probe: **68/68** states, with 34 render/fixture input blobs verified against the capture source and current workspace. The three extracted includes remain bound by the existing receipt and required-path test.
- Both exact-source EW/W9 binding checks: **2 passed** in 2.15 seconds.
- P0B closure returned success: this Macro-only composition does not change its pinned regional construction inputs. No redundant regional capture was minted for this branch.
- Actual CI matcher confirms all three new includes select `dashboard-render-contract`, `ew-p4-descriptive-ui`, and the new workspace browser owner. The existing data-gated engine-render owner already covers them through inference; its assignment is preserved.

[Workspace visual gallery](../../../mockups/evidence/macro-workspace-20261109/README.md) and [capture manifest](../../../mockups/evidence/macro-workspace-20261109/manifest.json) are the reviewable main-page artifacts. Bounded source/ownership and visual advisors supplied findings; the implementing principal performed self-check and verification. No independent GitHub approval or production acceptance is claimed.

Final visual-evidence guard and forward-only design ratchet returned success after the unavailable-priorities correction (zero blocking design findings). Runtime style-injection allowance is unchanged and passed. The source/evidence packet is ready for the normal PR/CI/merge/render path; it has not yet been accepted on the served production page.
