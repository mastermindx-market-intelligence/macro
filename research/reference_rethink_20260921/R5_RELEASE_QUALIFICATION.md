# R5 — release qualification and remaining user-flow gate

Mission remains incomplete. This is the current standalone guide qualification, not production integration or independent acceptance.

## Material advancement

Both Python suites and both Node suites are now enrolled in the existing `public-render-fastlane` help/glossary **code** gate. The old reference-only `engine-render-guards` job is data-tier; merely inserting test names there would not provide the intended merge-gating coverage. Existing jobs, policy and tests are preserved; BeautifulSoup was added for the new HTML assertions. No waiver, alternate runner, queue or publication owner was introduced. An enrollment regression test checks the actual commands and preserves the existing help/glossary suites.

The existing census now reports no unrun Market Guide suite. The existing `run_ci_pack.select_jobs` selects that code gate when any of the five guide producer/reader/presentation/adapter paths changes. Local tests: 68 Python + 53 Node = 121 passing, with six inherited temporary-browser cleanup warnings.

The expanded original browser qualifier retains its keyboard assertion and requires a new evidence output directory outside `site/`. It passed 13 check groups, including 184 real definition routes, native focus/Escape/return behavior, exact history, alias/coverage recovery, no external requests, and no-JavaScript reading. It captured 48 theme/locale/width view states plus unknown, empty and no-JS states. Evidence and exact source hashes are under `r5-evidence/browser-verified/` and `r5-evidence/source-binding.json`.

The first matrix attempt exposed a harness error: same-document hash navigation preserves the theme, so blindly toggling Dark again changed it back to Light. The repaired harness selects the requested theme from its current value, retaining the exact target-theme assertion. The failed run is recorded separately and was not called a pass.

Dark desktop home, light Chinese mobile home and dark Chinese mobile help were visually inspected. This is author inspection, not independent visual approval. The review-only banner/header is not proposed global product navigation. Full-page modal captures include content below the viewport; the actual modal remains height-bounded.

## Remaining gates and precise source finding

The fresh same-device Macro navigation diagnostic was refused by the tool's safety-status check. That diagnostic was not rerouted. The discrepancy remains unresolved; none of the standalone success clears actual Macro embedding.

Source inspection found a separate usability defect in `guide-view.js::home`: the results heading is constructed from the selected question, but typing clears `route.topic` and updates only membership/count. Thus a global search entered after choosing a question can retain that question's old heading. The intended RED test append was refused; readback confirms the test file unchanged. This finding is source-derived, not a new browser reproduction. Next repair: hold the heading node and refresh its text inside `results()`, then prove topic → typed search → correct heading/membership/URL in both unit and browser tests. Do not silently label the defect fixed.

Native GitHub independent review was requested from `mastermindx-2` on #7647 while retaining Draft/Hold. Requested review is not reviewer pickup, START, acceptance, or a wake path.

Production integration still requires the held Macro diagnosis, the source-derived heading repair, independent code/visual review, current-base checks and normal release/live proof. The incumbent #6792 source/evidence obligations remain unreplaced. Do not remove LOOK UP before its real replacement is verified. No production page, shared navigation, engine, auth or deployment setting was changed by this packet.
