# Candidate verification

This file reports observed candidate checks. It is not a production/deployment
attestation and does not authorize merge or auto-merge.

## Local regressions

The original implementation selected runs passed **545 tests**, with **2 skips** and **5 explicitly
deselected shipped-artifact tests**. The checkout is an owned sparse Macro
workspace; at that checkpoint the normal workspace helper materialized `site/` for existing tests
that read its committed JavaScript. `data/`, `mockups/` and `verify_shots/`
were omitted. The design-governance repair below subsequently materialized `mockups/`. This is not a claim that the full repository suite ran.

| Command (from repository root) | Result |
| --- | --- |
| `python3 -m pytest tests/test_prophet_source_epochs.py tests/test_prophet_source_epochs_reader.py tests/test_p_mp1_shell_ladder_error_state.py tests/test_prophet_plan_relation.py -q --tb=short -p no:cacheprovider` | 196 passed, 2 skipped |
| `python3 -m pytest tests/test_us_board_gate.py -q --tb=short -p no:cacheprovider -k "not test_shipped"` | 94 passed, 5 deselected |
| `python3 -m pytest tests/test_us_today_source_binding.py -q -x --tb=short -p no:cacheprovider` | 131 passed |
| `python3 -m pytest tests/test_us_board_hydration_merge.py tests/test_dashboard_template_render.py -q --tb=short -p no:cacheprovider -k "not test_shipped"` | 124 passed |

The new source-epoch suites cover 84 synthetic cases with no skip: the helper's
raw-byte/metadata/snapshot failures, the actual express refresh body, single index
read/path advancement, immutable index/snapshot bytes, and the production
hydration entry point refusing mismatched/missing/forged-status evidence before
paid-row or panel mutation.

The initial broad run exposed a missing sparse site asset and outdated unit
fixture inputs, and exceeded its 240-second wrapper limit before reporting a
complete result. It is not counted as passing. The final split runs above resolved
those specific failures without weakening the production admission fence:
the shared predicate fixture holds the new independent variable fixed, and three
existing loader scenes generate genuine source-epoch projections from their
synthetic source bytes and displayed plan books.

## Immutable committed source

`committed_tree_reader.json` records the new projector's result over exact Git
objects at main `9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`:
`SEPARATE_EPOCHS`, `PENDING`, verified frozen snapshot. Its index, board and
snapshot hashes/byte lengths are retained; no raw source rows are published.

## Browser proof

The refreshed browser run passed **8 responsive/theme/language cells and 5 refusal cases** against the real rendered dashboard and existing paid payload route. The receipt binds capture commit `1bddbb45da5c666359e0d2b6d1710ecaa82d8943` and SHA-256 of all five production source files; the subsequent evidence-only commit does not change those bytes. Chromium version: `151.0.7922.34`. No page JavaScript errors were observed. Unrelated live-data/config requests were unavailable in the isolated synthetic fixture; their paths are retained in `browser/receipt.json`, not presented as production health.

Observed journey: actual Plans selector, keyboard Enter open/close, pointer open, matching paid-payload row loading, then return to Screener. The first preliminary attempt tried to focus the disclosure while Plans was hidden and failed; the harness was corrected to use the real selector before the original successful run; the refreshed run repeats that real selector path.

Command: `python3 tests/tools/prove_prophet_source_epochs_browser.py --output research/prophet_v4/epoch_divergence_20261101/browser --visual-output mockups/evidence/prophet-source-epochs-20261101`.

The refreshed run also uses the repository's canonical `scripts.capture_page_evidence.run_capture` emitter with a real Playwright reader driver. Its `mastermind.p0_evidence.v2` manifest contains 16 full-page captures: the required eight rest cells plus eight applied keyboard-focus cells at the canonical 1440×900 and 390×844 viewports. The three-key `EVIDENCE.yml` receipt owns `templates/_prophet_source_epochs.html.j2`. Capture target metadata binds the implementation revision, production hashes, browser-driver hash, and rendered synthetic HTML hash. The screenshots, emitter and guard are not fabricated or weakened. All eight focus scenes were visually inspected after the label repair. A dim refusal screenshot and a floating-control overlap in the full-page capture prompted a capture-only refinement: wait for the page's actual transient effect to finish, center the disclosure, and assert that its ancestor styles are unfiltered/opaque and a nine-point grid across every metadata/refusal row is unobscured. No control or style is suppressed. The final capture repeats all 8 journey cells, 5 refusal cases and 16 canonical cells with those assertions; the corrected refusal and mobile focus captures were checked again. The actual computed radius is 8px in all browser cells.

Passed matrix: 1440px and 390px × dark/light × EN/ZH. Passed refusal cases: different board hash, different index hash, missing source metadata, forged SETTLED, and 403 access denial. Every refusal retained the wall, appended no paid rows, and preserved PENDING. The proof preserved the floating assistant and centered the disclosure by scrolling; no product controls were hidden. All eight scenes satisfied unoccluded metadata, no disclosure overflow, and a native summary target at least 40px tall.

All eight disclosure scenes and the mobile index-refusal scene were visually inspected. Hashes and copy are legible, including mobile EN/ZH and dark/light. Screenshots are synthetic candidate evidence, not deployed-production evidence.

## Design-governance repair and refreshed validation

Hosted CI run `41396482546` at candidate `34d7fd106fb8d11af5d6803c82f96144d2b56086` rejected the new partial's literal `border-radius:8px`. Commit `1f9d1978c7fc6208458bfa56495ada3ec39d172c` changes that one production declaration to `var(--r-ctl,8px)`. This is the existing design-scale convention and documented forward-compatible fallback in `templates/theme.css`; that scale has not yet landed at its global root. No new token root or policy exception is added. The same commit extends only the browser proof harness to emit the canonical visual evidence and assert the computed radius. The source projector, index capture, hydration gate, producer and workflow logic are unchanged.

Over the source bytes committed at that implementation revision, this targeted run passed **350 tests, no skips** in 213.27 seconds:

`python3 -m pytest tests/test_prophet_source_epochs.py tests/test_prophet_source_epochs_reader.py tests/test_dashboard_template_render.py tests/test_check_design_system.py tests/test_check_runtime_style_injection.py tests/test_check_ui_visual_evidence.py tests/test_freshness_chips_language_invariant.py -q --tb=short -p no:cacheprovider`

Five warnings concerned pytest cleanup of an older temporary directory, not failed assertions; no shared temporary files were removed by this fix. These 350 tests overlap the earlier 545 and are not an additive total.

All remaining steps of the existing `design-governance` job passed locally: design-system self-check, runtime-style selftest, visual-evidence selftest, the runtime-style allowance check, the forward-only design ratchet (**zero introduced blocking findings**) and the actual visual-evidence guard over the full candidate template/site diff. The immutable comparison base was `9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`. Fetched main `bca436e58f7069ff8b52d31074f30726cfecf0e4` was reconciled: intervening capital-structure/GMI/other CI changes do not alter this Prophet read path or overlap the repair.

The earlier independent Fabric PASS at `34d7fd…` remains a source assessment of that historical head. It is not relabeled as approval of this repair. A new independent exact-final-head review and fresh hosted CI are required after the evidence commit; their observations will be posted on PR #10509 without modifying the candidate again solely for closeout.

### Remaining pack-3 findings

The same hosted run's final pack exposed two further introduced failures. The source-language guard flagged two Chinese affirmative verification phrases in the new partial. Commit `baa5b0879a3ea07c39c8231b4191526c7410700d` uses the precise EN/ZH statement that the snapshot hash matches, avoiding a claim about broader model or publication validation. The guard and allowlist are unchanged. The complete source scan and its selftest passed with the canonical allowlist read from the immutable Git object (SHA-256 `3149d5c42631c1c6734437986294f4c1e38a6065bca4d74ae81345c05a11ad33`). Only its temporary read path was supplied to the existing guard because `data/` is omitted from the owned sparse checkout; no allowlist entry was added or changed.

Five existing cohort-publication/reader-wiring tests execute a narrow AST slice from `build_site`. Their three isolated namespaces omitted the new `read_source_epochs` global and captured-index holder. The same commit adds the real function and an explicit empty capture to those namespaces. It neither stubs the new reader nor removes/assertion-skips the existing cohort behavior.

The complete failed cohort step plus both new source-epoch suites and the dashboard rendering suite passed **275 tests, no skips**, in 219.57 seconds:

`TZ=UTC python3 -m pytest tests/test_theme_graph_selection_cohort_publication.py tests/test_theme_graph_selection_cohort_reads_wiring.py tests/test_china_standouts_serialization.py tests/test_build_china_library_more_actionable_guard.py tests/test_us_standouts_cascade_gate.py tests/test_prophet_source_epochs.py tests/test_prophet_source_epochs_reader.py tests/test_dashboard_template_render.py -q --tb=short -p no:cacheprovider`

This count overlaps the earlier runs. Five pytest temporary-directory cleanup warnings were non-assertion warnings. Capture commit `1bddbb45da5c666359e0d2b6d1710ecaa82d8943` changes only the browser harness, retaining the production and test bytes from `baa5b087…`. All final PNG hashes, byte lengths and dimensions, production-source hashes and the harness hash were checked. The current template diff passes both the design ratchet and the canonical visual-evidence guard. Fresh hosted CI and a new final-head Fabric review remain the completion gates.

## No-false-SETTLED attestation

The projection emits `settlement_status: PENDING` on every outcome. Equal hashes
establish only the defined source relation, not A2 four-family publication/read
agreement. Mismatched or unavailable page/payload identities are refused before
paid row/panel mutation. The browser also refuses an injected SETTLED field.
No accepted bundle ID, producer timestamp, second publisher or deployment is
created by this change.

## Completion gates

Independent final non-author Fabric review and GitHub PR CI are still pending at
the implementation checkpoint. The pre-implementation audit and helper acceptance
are recorded separately in `FABRIC_ADJUDICATION.md`; neither substitutes for the
final review. The PR remains Draft/unarmed under the Chairman's no-merge boundary.
