# Bonds duration R11 — actual route integration candidate

Status: **SOURCE CANDIDATE — NOT DEPLOYED; browser and independent visual acceptance outstanding.**

Parent: Macro #8147. Operation: `bonds-forex-research-design-20260928-sol-c1-001`.
Base: `a7e00a9af0f437a4907a32b4591d965e438ca42a` (also observed as main immediately before publication preparation).
Branch: `claude/bonds-duration-r11-20260930-sol-c1`.

## User journey and preserved ownership

The existing `bonds.html` route gains **Preview price impact** inside **Real rates & duration**. It opens a native dialog using the corrected Paper R11 desktop drawer, tablet sheet and mobile full-height composition. It does not replace the Bonds dashboard, its navigation, market signals or scientific models.

A user reviews the +50 bp example, edits the yield shock, sees updated illustrative estimates, and returns to the same brief. Returning preserves the draft only in the current page; reopening an invalid draft does not revive the last valid result. Reloading creates a fresh default example. There is no watch, alert, trade, holding, market-state or persistent-storage write.

The two positions are explicitly illustrative: $10,000 each, with 5.0-year and 14.8-year modified durations. They are not actual holdings or sourced live instrument durations. This first slice **does not implement sourced holdings**. An absent or changed input-origin identity withholds the preview instead of borrowing illustrative values and labelling them as sourced.

The existing `scripts/build_bonds.py` remains the route builder. It already renders `bonds.html.j2`, so the template includes make the feature reachable without adding a publisher, endpoint, market engine, asset-copy service or second calculation owner. `templates/theme.css`, shared navigation and all engine/data paths are unchanged.

## Exact source boundary

| Path | Change |
|---|---|
| `templates/bonds.html.j2` | Entry button/unavailable notice within the existing duration panel; one markup include and one module include. |
| `templates/_bonds_duration.html.j2` | Local review/editor, explicit example identity, two result slots, correction/unavailable states, EN/ZH and scoped responsive theme styling. |
| `templates/_bonds_duration.mjs.j2` | Reused R11 calculation/projection, strict DOM input adapter, native-dialog lifecycle and local draft rendering. |
| `tests/test_bonds_duration_workflow.py` | Actual-route wiring, fail-closed markup, identity, styling, Node invocation and real page-writer/asset-sweep integration. |
| `tests/bonds_duration_workflow.test.mjs` | Model and DOM-port tests against the unmodified production module. |
| `.github/ci/legacy-jobs.yml` | Existing `ccw-w4-credit-desk` job runs the duration suite with Node20 and tracks all four component/test paths. No waiver or new workflow. |
| `research/BONDS_DURATION_R11_INTEGRATION.md` | This implementation and verification receipt. |

No generated `site/` or runtime `data/` file is part of this candidate. A production release still needs the existing admitted render/publish path; changing a template does not prove the served page has changed.

## Input, result and failure contract

The supported shock entry range is −300 to +300 basis points, inclusive. A basis point is 0.01 percentage point. The text entry accepts the R11 plain-decimal grammar, not scientific notation, hexadecimal, booleans, non-finite values or partially parsed strings. It never silently clamps the entered value. The range control uses `step="any"` so a valid fractional text shock is not rounded into a different selected shock.

Every update clears both result slots before validating all positions. A +350 bp shock therefore shows **Result unavailable** and two **Not calculated** states, never old −$250/−$740 figures with a warning pasted alongside them. Invalid position/duration metadata, duplicated position identity or numerical overflow withholds the entire comparison. Correcting the input recomputes it through the same R11 projection.

Missing convexity and complete cash flows stay missing. The result remains a first-order, parallel-yield price estimate that excludes convexity, coupon income, fees, transaction costs and credit-spread changes. The input range is not an accuracy guarantee. No probabilities, investment recommendations or prediction calibration are introduced.

The markup emits disabled entry/input controls and no dollar estimates before the controller is available. JavaScript/native-dialog unavailability is local to the calculator; the independent rate/credit display is left alone. Native opening failure clears the estimates and exposes the unavailable notice. Mounting is idempotent, and disposal removes handlers, clears results, closes the review and restores focus to its trigger.

EN and ZH copy are emitted together through the existing language-class convention, including error/state updates. No new language or global theme system is created. Native dialog semantics are used for focus containment and Escape; their real browser behavior remains an explicit acceptance gate, not a result inferred from DOM test doubles.

## R11 reuse and provenance

Source artifact: `Bonds_Forex_R11_Audit_and_Corrected_Source.zip`.
SHA-256: `9cbdaa99307ee4d575b7051e1940dd8dc18f09d26452b30bf363ecdb6d54f9b8`.

The following pure function bodies were compared with the source artifact and are byte-identical:

| Function | Body SHA-256 |
|---|---|
| `calculateDurationScenario` | `c330d9d8fd4b7558a37b40f23d4742450d8f7c88272c8999cd90cf5a3ff61490` |
| `buildDurationPreview` | `18c1b04c6cf2ed6daf8a63c8b18cfc1cf5bcba5bb2542ca01b1b82e542f194c9` |
| `describeYieldShock` | `50027ab4393d3e7492a39c803814fc12dae5ea6413e4b4b3055d8a0f41f682ff` |

No R11 fixture market narrative, full multi-market view-model, Forex diagnosis or separate scientific engine was imported.

Paper references: original MASTERMIND PAGES file `01M2WGNCX9475G79JRKJTCM08P`, Bonds page `p-O-1`; desktop `5HWY-1`, tablet `5I6D-1`, mobile `5I9J-1`, invalid state `5LKO-0`. Native R11 closeout is Macro #8147 comment5907721834. These identify the reference, not browser-conformance acceptance for this implementation.

## Verification observed on 2026-09-30

The initial route tests failed7/7 because the production includes/controller were missing, then passed after integration. A separate failing regression found the fractional-slider step mismatch; the step was corrected to `any` and the test passed. The first pipeline check used the wrong expected data-base marker; it was corrected to the existing owner's `DBASE_MARKER` (`data-dbase`), with no shim/publisher change.

Final pre-publication scoped execution (Studio PID17678, exit0):

```sh
python3 -m pytest tests/test_bonds_duration_workflow.py \
  tests/test_bonds_divergence_gate.py tests/test_bonds_glance_copy.py \
  -k 'not committed' -q --tb=short
node --test --test-reporter=spec tests/bonds_duration_workflow.test.mjs
git diff --check
```

- **47 Python checks passed**:9 new route/integration checks plus38 existing checks. One new Python check invokes the Node suite below.
- **36 Node cases passed** in the separately observed invocation. These are model and DOM-port checks, not36 browser scenarios.
- **2 committed-site checks deselected** because `site/` is omitted from the native sparse checkout: `test_committed_bonds_page_matches_contract` and `test_committed_bonds_stylesheet_is_fingerprinted`.
- No full-repository run or authenticated browser run is claimed.

The pipeline test renders the complete existing Bonds template with its existing owner fixture, calls real `lib.pages.write_page`, and executes the existing CSS/JS externalization sweep against temporary pytest output only. It confirms the drawer appears once, the served module retains its exact source and module type, and the new stylesheet is emitted once with a matching content hash. The shim owner is redirected to test output so the test cannot fill the sparse production `site/` tree.

Observed owner-fixture payload before postprocessing:146,375 →173,858 bytes, an increase of27,483 bytes. Whole-document gzip:36,170 →43,476 bytes, an increase of7,306 bytes. These are fixture payload measurements, not production latency or Core Web Vitals.

### Tested source SHA-256 manifest

| Path | SHA-256 |
|---|---|
| `templates/bonds.html.j2` | `a07c5b2b3fefc756332558df4726a490a5a4b431bd3ee46913f97b437548c5dd` |
| `templates/_bonds_duration.html.j2` | `dba8f0ff6d972db808cecccbd72ae35c1c68484880809a05ce0db6a7ea909a96` |
| `templates/_bonds_duration.mjs.j2` | `3d44053d71710a53d3af00cc89f69084286a3b21098eaf1e4e20c9adff7433ec` |
| `tests/test_bonds_duration_workflow.py` | `bb95cda421532978d5b55423b736813d5bfc23e01379cc325a024a0d9b6264ea` |
| `tests/bonds_duration_workflow.test.mjs` | `76eeee6044a4eb8eda581dc58b6fa4e8b3f13841d95ca1b97dc0e6b2c0c7d0f2` |

## CI repair continuation — 2026-09-30

Original-head CI run `36700334712` concluded failure, not a green result. Eleven packs and the fences workflow passed. The two blocking causes were introduced by this candidate:

1. `contract-delta` job `109838012440` found the duration pytest suite was not named by a workflow run step.
2. `ci-pack-9` job `109839134033` failed only its `design-governance` job: four component-local colour functions on newly added lines.

The suite is now wired into the existing `ccw-w4-credit-desk` job, with Node20 and explicit component/test dependencies. No suite is waived and no checker or workflow gate is weakened. The component now uses the existing glass backdrop/border and panel/health tokens instead of defining new colour mixes. This is a scoped material change; visual conformance must still be checked in a real browser.

Fresh scoped run (Studio PID32837, exit0): **127 passed, 2 deselected** across the complete owning job's four Python suites, with only the same two committed-site tests excluded. The duration suite invokes the existing36 Node cases. The actual forward-only design checker reports **0 introduced blockers**, and `gated_unrun_suites()` reports **0 orphaned suites**. The regression forbidding component-local colour functions was observed failing before correction (PID25723).

These local results repair the observed failures but do not stand in for the next exact-head hosted CI result, an independent review, generated-site proof or browser acceptance. The Executive V2 read preflight currently reports `mode=readonly`; no reviewer job was submitted or claimed. Browser administrator denial is unchanged and is not retried or delegated around.

## Complete runner and page-path qualification

The first CI repair at `768ff5d9aece4ebc9c3c01bf861d7510b0b033f4` declared Node22. The shared pack runner accepts only its existing Node20 action contract, so current-run contract-delta job `109850983984` correctly refused the manifest. This follow-on changes the one declaration to Node20; it does not upgrade the shared runtime or change a checker.

The exact failure was reproduced with `scripts.run_ci_pack.load_legacy_jobs()`, then the corrected complete manifest was accepted (239 jobs). The full real command was then run against the corrected working tree:

```sh
python3 scripts/check_contract_delta.py --base a7e00a9af0f437a4907a32b4591d965e438ca42a
```

**Studio PID70436, exit0: 0 introduced and 0 inherited contract findings.** Full probe ceilings stayed satisfied: index134 jobs /5,524 estimated seconds /10 packs; free-content132 /5,293 /9; Prophet plan-book127 /5,242 /9. Total observed checker wall time204.7 seconds. These are the existing checker measurements, not product performance claims. The next exact-head CI run still owns hosted qualification, including actual execution under Node20. A local Homebrew Node20 binary was not present at the inspected standard path; no dependency was installed or an alternate provider used.

On the unchanged product-source blob set at768ff…, **PID59344 exit0** exercised complete Jinja→`write_page`→externalize→asset optimizer in temporary output. A second optimizer pass changed0 bytes; the module body/type survived unchanged and Node's ES-module parser accepted it. All7 component IDs were unique and all7 control/ARIA references resolved. Exactly one component stylesheet and its one matching preload were emitted, with CSS SHA256 `1820ffed2ebbf317745be951261d72109cad9d52c83887386780b16d06d97df0`. Served owner-fixture bytes103,723; SHA256 `53f6cef73577af84c8f7f0e3f82583970a531bfc07e8febde181defc71d87571`. The first diagnostic had counted the preload as a second stylesheet; classifying link `rel` corrected that test-only assertion, with no product changes.

**PID71841 exit0** additionally ran the two previously deselected inherited committed-page/stylesheet tests against the exact768ff… repository blobs, materialized only into temporary test output. Both passed. That committed page does not yet contain the new component: these two checks prove preservation of its existing contract, not a regeneration, deployment or live proof for the new workflow. No worktree `site/` files were written.

The three product-source files and the36-case Node controller suite remain unchanged by this one-line environment correction. Independent source/visual review, real browser proof, the new exact-head hosted CI result and production publication remain outstanding. Do not call the temporary output a deployed dashboard.

## Release gates and rollback

This candidate stays Draft/HOLD until independent source/visual review and the owed real browser checks are available: desktop/tablet/mobile opening; invalid→corrected→close→reopen; keyboard/focus/Escape; EN/ZH; dark/light; actual contrast and overflow; reduced motion; unsupported/unavailable behavior. The earlier browser administrator denial has not been retried or routed around. Paper screenshots and DOM ports do not substitute for these checks.

After acceptance, the existing production builder/render and publication chain must produce and serve the changed route, with a real-path receipt. No merge-on-green or native auto-merge is authorized by this document. No registry row is promoted to compliant by this source-only result.

Rollback is a normal revert of this bounded source change: remove the entry and two includes, and the new partials become unused. No persisted user data, market state, storage schema or financial engine needs rollback.
